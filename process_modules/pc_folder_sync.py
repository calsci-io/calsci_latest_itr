try:
    import uos as os  # type: ignore
except ImportError:
    import os  # type: ignore

try:
    import usocket as socket  # type: ignore
except ImportError:
    import socket  # type: ignore

try:
    import urequests as http_requests  # type: ignore
except ImportError:
    try:
        import requests as http_requests  # type: ignore
    except ImportError:
        from mocking import urequests as http_requests  # type: ignore

import json


SETTINGS_PATH = "db/pc_folder_sync.json"
DEFAULT_PORT = 9080
_SAFE_URL_CHARS = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~/"


class SyncError(Exception):
    pass


def load_settings():
    settings = {"host": "", "port": DEFAULT_PORT, "folder_name": ""}
    try:
        with open(SETTINGS_PATH, "r") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, dict):
            settings["host"] = str(loaded.get("host", "") or "")
            settings["port"] = int(loaded.get("port", DEFAULT_PORT) or DEFAULT_PORT)
            settings["folder_name"] = str(loaded.get("folder_name", "") or "")
    except Exception:
        pass
    return settings


def save_settings(host="", port=DEFAULT_PORT, folder_name=""):
    payload = {
        "host": str(host or "").strip(),
        "port": int(port or DEFAULT_PORT),
        "folder_name": str(folder_name or "").strip(),
    }
    with open(SETTINGS_PATH, "w") as handle:
        json.dump(payload, handle)
    return payload


def _quote_component(value):
    if value is None:
        return ""
    raw = str(value).encode("utf-8")
    parts = []
    for byte_value in raw:
        if byte_value in _SAFE_URL_CHARS:
            parts.append(chr(byte_value))
        else:
            parts.append("%{:02X}".format(byte_value))
    return "".join(parts)


def _normalize_host(host):
    host = str(host or "").strip()
    if not host:
        raise SyncError("Enter the PC IP first")
    return host


def _normalize_port(port):
    try:
        port = int(port)
    except Exception as exc:
        raise SyncError("Port must be a number") from exc
    if port < 1 or port > 65535:
        raise SyncError("Port must be between 1 and 65535")
    return port


def _normalize_relative_path(relative_path):
    relative_path = str(relative_path or "").replace("\\", "/").strip("/")
    if not relative_path:
        raise SyncError("Manifest contains an empty path")
    parts = [part for part in relative_path.split("/") if part]
    if not parts or any(part in (".", "..") for part in parts):
        raise SyncError("Manifest contains an invalid path")
    return "/".join(parts)


def _path_exists(path_value):
    try:
        os.stat(path_value)
        return True
    except Exception:
        return False


def _mkdir_p(path_value):
    path_value = str(path_value or "").replace("\\", "/").rstrip("/")
    if not path_value or path_value == "/":
        return
    absolute = path_value.startswith("/")
    current = "/" if absolute else ""
    for part in [part for part in path_value.split("/") if part]:
        if current in ("", "/"):
            current = ("/" + part) if absolute else part
        else:
            current = current + "/" + part
        try:
            os.mkdir(current)
        except Exception:
            pass


def _remove_if_exists(path_value):
    if not _path_exists(path_value):
        return
    try:
        os.remove(path_value)
    except Exception as exc:
        raise SyncError("Cannot replace {}".format(path_value)) from exc


def _target_path(relative_path, install_root="/"):
    relative_path = _normalize_relative_path(relative_path)
    install_root = str(install_root or "/").replace("\\", "/").rstrip("/")
    if not install_root or install_root == "/":
        return "/" + relative_path
    return install_root + "/" + relative_path


def _request_target(endpoint, folder_name="", relative_path=""):
    params = []
    folder_name = str(folder_name or "").strip()
    if folder_name:
        params.append("folder=" + _quote_component(folder_name))
    relative_path = str(relative_path or "").strip()
    if relative_path:
        params.append("path=" + _quote_component(relative_path))
    if not params:
        return endpoint
    return endpoint + "?" + "&".join(params)


def _request_json(host, port, endpoint, folder_name=""):
    url = "http://{}:{}{}".format(host, port, _request_target(endpoint, folder_name=folder_name))
    response = None
    try:
        response = http_requests.get(url)
        status_code = int(getattr(response, "status_code", 200) or 200)
        payload = response.json()
    except Exception as exc:
        raise SyncError("Cannot reach PC server") from exc
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass

    if status_code >= 400:
        detail = ""
        if isinstance(payload, dict):
            detail = str(payload.get("error", "") or "")
        raise SyncError(detail or "PC server returned HTTP {}".format(status_code))
    if not isinstance(payload, dict):
        raise SyncError("PC server returned invalid data")
    return payload


def fetch_manifest(host, port, folder_name=""):
    host = _normalize_host(host)
    port = _normalize_port(port)
    payload = _request_json(host, port, "/manifest", folder_name=folder_name)
    files = payload.get("files", [])
    if not isinstance(files, list):
        raise SyncError("Manifest file list is invalid")

    cleaned_files = []
    total_bytes = 0
    for item in files:
        if not isinstance(item, dict):
            raise SyncError("Manifest entry is invalid")
        rel_path = _normalize_relative_path(item.get("path", ""))
        size_value = int(item.get("size", 0) or 0)
        cleaned_files.append({"path": rel_path, "size": size_value})
        total_bytes += size_value

    folder_name = str(payload.get("folder_name", "") or folder_name or "").strip()
    if not folder_name:
        raise SyncError("PC server did not provide a folder name")

    return {
        "folder_name": folder_name,
        "files": cleaned_files,
        "file_count": len(cleaned_files),
        "total_bytes": int(payload.get("total_bytes", total_bytes) or total_bytes),
    }


def _stream_http_file(host, port, request_target, output_path, progress_cb=None):
    sock = None
    stream = None
    bytes_written = 0
    content_length = 0
    try:
        address = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0][-1]
        sock = socket.socket()
        sock.connect(address)
        request = (
            "GET {} HTTP/1.0\r\n"
            "Host: {}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).format(request_target, host)
        sock.send(request.encode("utf-8"))
        stream = sock.makefile("rb")

        status_line = stream.readline()
        if not status_line:
            raise SyncError("PC server closed the connection")
        try:
            status_code = int(status_line.split(None, 2)[1])
        except Exception as exc:
            raise SyncError("Invalid HTTP response from PC server") from exc

        while True:
            header_line = stream.readline()
            if not header_line or header_line == b"\r\n":
                break
            header_lower = header_line.lower()
            if header_lower.startswith(b"content-length:"):
                try:
                    content_length = int(header_line.split(b":", 1)[1].strip())
                except Exception:
                    content_length = 0

        if status_code >= 400:
            raise SyncError("PC server returned HTTP {}".format(status_code))

        with open(output_path, "wb") as handle:
            while True:
                chunk = stream.read(1024)
                if not chunk:
                    break
                handle.write(chunk)
                bytes_written += len(chunk)
                if progress_cb is not None:
                    progress_cb(bytes_written, content_length)
    except SyncError:
        raise
    except Exception as exc:
        raise SyncError("File download failed") from exc
    finally:
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass
        if sock is not None:
            try:
                sock.close()
            except Exception:
                pass

    return bytes_written


def _discovered_installed_apps(files):
    app_names = []
    prefix = "apps/installed_apps/"
    for file_info in files:
        rel_path = str(file_info.get("path", "") or "")
        if not rel_path.startswith(prefix) or not rel_path.endswith(".py"):
            continue
        app_name = rel_path.rsplit("/", 1)[-1][:-3]
        if app_name and not app_name.startswith("_"):
            app_names.append(app_name)
    return sorted(set(app_names))


def _register_installed_apps(app_names):
    if not app_names:
        return
    try:
        from process_modules.app_downloader import Apps

        apps_db = Apps()
        for app_name in app_names:
            apps_db.insert_new_app(app_name)
    except Exception:
        pass


def sync_folder(host, port=DEFAULT_PORT, folder_name="", progress_cb=None, install_root="/", register_installed_apps=True):
    host = _normalize_host(host)
    port = _normalize_port(port)
    folder_name = str(folder_name or "").strip()

    if progress_cb is not None:
        progress_cb(
            {
                "stage": "manifest",
                "message": "Fetching manifest",
                "folder_name": folder_name,
                "file_index": 0,
                "file_count": 0,
                "bytes_done": 0,
                "bytes_total": 0,
                "current_file": "",
            }
        )

    manifest = fetch_manifest(host, port, folder_name=folder_name)
    files = manifest["files"]
    total_files = manifest["file_count"]
    total_bytes = manifest["total_bytes"]
    resolved_folder_name = manifest["folder_name"]
    bytes_done = 0

    if progress_cb is not None:
        progress_cb(
            {
                "stage": "ready",
                "message": "Downloading files",
                "folder_name": resolved_folder_name,
                "file_index": 0,
                "file_count": total_files,
                "bytes_done": 0,
                "bytes_total": total_bytes,
                "current_file": "",
            }
        )

    for index, file_info in enumerate(files, 1):
        rel_path = file_info["path"]
        final_path = _target_path(rel_path, install_root=install_root)
        temp_path = final_path + ".part"
        parent_dir = final_path.rsplit("/", 1)[0] if "/" in final_path else ""
        _mkdir_p(parent_dir)
        _remove_if_exists(temp_path)

        def _on_progress(current_bytes, current_total):
            if progress_cb is None:
                return
            progress_cb(
                {
                    "stage": "downloading",
                    "message": "Downloading {}".format(index),
                    "folder_name": resolved_folder_name,
                    "file_index": index,
                    "file_count": total_files,
                    "bytes_done": bytes_done + current_bytes,
                    "bytes_total": total_bytes if total_bytes > 0 else current_total,
                    "current_file": rel_path,
                }
            )

        actual_size = 0
        try:
            actual_size = _stream_http_file(
                host,
                port,
                _request_target("/file", folder_name=resolved_folder_name, relative_path=rel_path),
                temp_path,
                progress_cb=_on_progress,
            )
            _remove_if_exists(final_path)
            os.rename(temp_path, final_path)
        except Exception:
            _remove_if_exists(temp_path)
            raise

        bytes_done += actual_size
        if progress_cb is not None:
            progress_cb(
                {
                    "stage": "downloading",
                    "message": "Downloaded {}".format(index),
                    "folder_name": resolved_folder_name,
                    "file_index": index,
                    "file_count": total_files,
                    "bytes_done": bytes_done,
                    "bytes_total": total_bytes,
                    "current_file": rel_path,
                }
            )

    installed_apps = _discovered_installed_apps(files)
    if register_installed_apps:
        _register_installed_apps(installed_apps)

    summary = {
        "folder_name": resolved_folder_name,
        "file_count": total_files,
        "total_bytes": bytes_done,
        "installed_apps": installed_apps,
    }
    if progress_cb is not None:
        progress_cb(
            {
                "stage": "complete",
                "message": "Download complete",
                "folder_name": resolved_folder_name,
                "file_index": total_files,
                "file_count": total_files,
                "bytes_done": bytes_done,
                "bytes_total": total_bytes,
                "current_file": "",
            }
        )
    return summary
