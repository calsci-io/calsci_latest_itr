import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

try:
    import utime as time  # type: ignore
except ImportError:
    import time  # type: ignore

try:
    import ujson as json  # type: ignore
except Exception:
    import json  # type: ignore

try:
    import usocket as socket  # type: ignore
except Exception:
    import socket  # type: ignore

try:
    import _thread  # type: ignore
except Exception:
    _thread = None

try:
    import webrepl  # type: ignore
except Exception:
    webrepl = None

from data_modules.object_handler import data_bucket, sta_if
from process_modules.auto_wifi_connector import auto_wifi_connector


DEFAULT_PASSWORD = "calsci"
DEFAULT_WEBREPL_PORT = 8266
DEFAULT_STATUS_PORT = 8267
_LISTENER_TIMEOUT_MS = 250
_STALE_AFTER_MS = 4000
_IDLE_MESSAGE = "Waiting for desktop upload"

_state_lock = None
if _thread is not None:
    try:
        _state_lock = _thread.allocate_lock()
    except Exception:
        _state_lock = None


def _lock():
    if _state_lock is not None:
        try:
            _state_lock.acquire()
        except Exception:
            pass


def _unlock():
    if _state_lock is not None:
        try:
            _state_lock.release()
        except Exception:
            pass


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def _ticks_ms():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _ticks_diff(now_ms, past_ms):
    try:
        return time.ticks_diff(now_ms, past_ms)
    except Exception:
        return now_ms - past_ms


_status = {
    "wifi_connected": False,
    "wifi_ssid": "",
    "ip": "",
    "password": DEFAULT_PASSWORD,
    "webrepl_port": DEFAULT_WEBREPL_PORT,
    "status_port": DEFAULT_STATUS_PORT,
    "webrepl_ready": False,
    "webrepl_error": "",
    "listener_ready": False,
    "state": "idle",
    "operation": "",
    "message": "Open this app to enable Wi-Fi REPL",
    "current_file": "",
    "current_file_name": "",
    "current_index": 0,
    "total_files": 0,
    "files_done": 0,
    "files_remaining": 0,
    "bytes_total": 0,
    "bytes_sent": 0,
    "bytes_remaining": 0,
    "percent": 0.0,
    "remaining_percent": 100.0,
    "session_id": "",
    "sender_host": "",
    "auto_reset": False,
    "reset_delay_ms": 0,
    "updated_at_ms": 0,
    "last_packet_at_ms": 0,
}

_listener_started = False
_listener_running = False
_listener_socket = None
_webrepl_started = False


def _update_status(**kwargs):
    _lock()
    try:
        for key, value in kwargs.items():
            _status[key] = value
    finally:
        _unlock()


def _transfer_defaults():
    ready = bool(_status.get("wifi_connected")) and bool(_status.get("webrepl_ready"))
    return {
        "state": "ready" if ready else "idle",
        "operation": "",
        "message": _IDLE_MESSAGE if ready else "Connect Wi-Fi to enable WebREPL",
        "current_file": "",
        "current_file_name": "",
        "current_index": 0,
        "total_files": 0,
        "files_done": 0,
        "files_remaining": 0,
        "bytes_total": 0,
        "bytes_sent": 0,
        "bytes_remaining": 0,
        "percent": 0.0,
        "remaining_percent": 100.0,
        "session_id": "",
        "sender_host": "",
        "auto_reset": False,
        "reset_delay_ms": 0,
        "updated_at_ms": 0,
        "last_packet_at_ms": 0,
    }


def clear_transfer_state():
    _update_status(**_transfer_defaults())


def _current_network_snapshot():
    connected = False
    ssid = ""
    ip = ""
    try:
        connected = bool(sta_if.isconnected())
    except Exception:
        connected = False

    if connected:
        try:
            ssid_now = sta_if.config("essid")
            if isinstance(ssid_now, str):
                ssid = ssid_now
        except Exception:
            ssid = ""
        try:
            info = sta_if.ifconfig()
            if isinstance(info, (tuple, list)) and info:
                ip = str(info[0])
        except Exception:
            ip = ""

    data_bucket["connection_status_g"] = connected
    data_bucket["ssid_g"] = ssid if connected else ""
    return connected, ssid, ip


def _sync_network_status():
    connected, ssid, ip = _current_network_snapshot()
    _update_status(wifi_connected=connected, wifi_ssid=ssid, ip=ip)
    return connected


def _ensure_wifi_connected():
    if _sync_network_status():
        return True

    try:
        auto_wifi_connector()
    except Exception as err:
        _update_status(
            state="error",
            message="Wi-Fi connect failed",
            webrepl_error=str(err),
        )
        return False

    connected = _sync_network_status()
    if not connected:
        _update_status(
            state="error",
            message="Wi-Fi not connected",
        )
    return connected


def _start_webrepl(force_restart=False):
    global _webrepl_started

    if webrepl is None:
        _update_status(
            webrepl_ready=False,
            webrepl_error="webrepl module not available",
            state="error",
            message="WebREPL module missing",
        )
        return False

    if _webrepl_started and not force_restart:
        _update_status(webrepl_ready=True, webrepl_error="")
        return True

    try:
        if force_restart and hasattr(webrepl, "stop"):
            try:
                webrepl.stop()
                _sleep_ms(80)
            except Exception:
                pass
        webrepl.start(port=DEFAULT_WEBREPL_PORT, password=DEFAULT_PASSWORD)
    except Exception as err:
        _webrepl_started = False
        _update_status(
            webrepl_ready=False,
            webrepl_error=str(err),
            state="error",
            message="Failed to start WebREPL",
        )
        return False

    _webrepl_started = True
    _update_status(
        password=DEFAULT_PASSWORD,
        webrepl_port=DEFAULT_WEBREPL_PORT,
        webrepl_ready=True,
        webrepl_error="",
    )
    return True


def _socket_timeout(sock, timeout_ms):
    try:
        sock.settimeout(int(timeout_ms) / 1000.0)
    except Exception:
        pass


def _create_listener_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass
    _socket_timeout(sock, _LISTENER_TIMEOUT_MS)
    sock.bind(("0.0.0.0", DEFAULT_STATUS_PORT))
    return sock


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return int(default)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _apply_status_packet(payload, sender_host=""):
    if not isinstance(payload, dict):
        return

    total_files = max(0, _safe_int(payload.get("total_files", 0)))
    files_done = max(0, _safe_int(payload.get("files_done", 0)))
    files_remaining = _safe_int(payload.get("files_remaining", total_files - files_done))
    if files_remaining < 0:
        files_remaining = max(total_files - files_done, 0)

    bytes_total = max(0, _safe_int(payload.get("bytes_total", 0)))
    bytes_sent = max(0, _safe_int(payload.get("bytes_sent", 0)))
    bytes_remaining = _safe_int(payload.get("bytes_remaining", bytes_total - bytes_sent))
    if bytes_remaining < 0:
        bytes_remaining = max(bytes_total - bytes_sent, 0)

    percent = _safe_float(payload.get("percent", 0.0))
    if bytes_total > 0:
        percent = (bytes_sent / max(bytes_total, 1)) * 100.0 if percent <= 0 else percent
    if percent < 0:
        percent = 0.0
    if percent > 100:
        percent = 100.0

    current_file = str(payload.get("current_file", ""))
    current_file_name = current_file.rsplit("/", 1)[-1] if current_file else ""
    now_ms = _ticks_ms()

    _update_status(
        state=str(payload.get("state", "uploading") or "uploading"),
        operation=str(payload.get("operation", "") or ""),
        message=str(payload.get("message", "") or ""),
        current_file=current_file,
        current_file_name=current_file_name,
        current_index=max(0, _safe_int(payload.get("current_index", files_done))),
        total_files=total_files,
        files_done=files_done,
        files_remaining=files_remaining,
        bytes_total=bytes_total,
        bytes_sent=bytes_sent,
        bytes_remaining=bytes_remaining,
        percent=round(percent, 2),
        remaining_percent=round(max(0.0, 100.0 - percent), 2),
        session_id=str(payload.get("session_id", "") or ""),
        sender_host=str(sender_host or ""),
        auto_reset=bool(payload.get("auto_reset", False)),
        reset_delay_ms=max(0, _safe_int(payload.get("reset_delay_ms", 0))),
        updated_at_ms=max(0, _safe_int(payload.get("updated_at_ms", 0))),
        last_packet_at_ms=now_ms,
    )


def _status_listener():
    global _listener_socket, _listener_running, _listener_started

    try:
        sock = _create_listener_socket()
    except Exception as err:
        _listener_started = False
        _listener_running = False
        _update_status(
            listener_ready=False,
            state="error",
            message="Status listener failed",
            webrepl_error=str(err),
        )
        return

    _listener_socket = sock
    _update_status(listener_ready=True, status_port=DEFAULT_STATUS_PORT)

    while _listener_running:
        try:
            data, addr = sock.recvfrom(2048)
        except Exception:
            now_ms = _ticks_ms()
            stale = _ticks_diff(now_ms, int(_status.get("last_packet_at_ms", 0) or 0))
            if stale > _STALE_AFTER_MS and _status.get("state") == "uploading":
                _update_status(
                    state="ready",
                    message=_IDLE_MESSAGE,
                    current_file="",
                    current_file_name="",
                    current_index=0,
                    total_files=0,
                    files_done=0,
                    files_remaining=0,
                    bytes_total=0,
                    bytes_sent=0,
                    bytes_remaining=0,
                    percent=0.0,
                    remaining_percent=100.0,
                    session_id="",
                    sender_host="",
                    auto_reset=False,
                    reset_delay_ms=0,
                )
            continue

        try:
            decoded = data.decode()
        except Exception:
            continue

        try:
            payload = json.loads(decoded)
        except Exception:
            continue

        sender_host = ""
        try:
            sender_host = addr[0]
        except Exception:
            pass
        _apply_status_packet(payload, sender_host=sender_host)

    try:
        sock.close()
    except Exception:
        pass
    _listener_socket = None
    _update_status(listener_ready=False)


def _start_listener():
    global _listener_started, _listener_running

    if _listener_started:
        return True
    if _thread is None:
        _update_status(
            listener_ready=False,
            state="error",
            message="Threading unavailable",
        )
        return False

    try:
        _listener_running = True
        _thread.start_new_thread(_status_listener, ())
    except Exception as err:
        _listener_running = False
        _update_status(
            listener_ready=False,
            state="error",
            message="Status listener unavailable",
            webrepl_error=str(err),
        )
        return False

    _listener_started = True
    return True


def ensure_service(force_restart=False):
    wifi_ok = _ensure_wifi_connected()
    if not wifi_ok:
        clear_transfer_state()
        _update_status(
            wifi_connected=False,
            message="Connect CalSci to Wi-Fi first",
            state="error",
        )
        return False

    _start_listener()
    repl_ok = _start_webrepl(force_restart=force_restart)
    _sync_network_status()

    if repl_ok:
        if _status.get("state") in ("idle", "error"):
            clear_transfer_state()
        _update_status(
            message=_status.get("message") or _IDLE_MESSAGE,
            state=_status.get("state") or "ready",
        )
    return bool(repl_ok)


def snapshot():
    _sync_network_status()
    _lock()
    try:
        snap = dict(_status)
    finally:
        _unlock()

    if snap.get("state") in ("ready", "idle") and snap.get("webrepl_ready") and snap.get("wifi_connected"):
        if not snap.get("message") or snap.get("message") == "Connect Wi-Fi to enable WebREPL":
            snap["message"] = _IDLE_MESSAGE
            snap["state"] = "ready"

    reset_wait_ms = 0
    if snap.get("state") == "complete" and snap.get("auto_reset"):
        packet_ms = int(snap.get("last_packet_at_ms", 0) or 0)
        if packet_ms > 0:
            reset_wait_ms = max(0, int(snap.get("reset_delay_ms", 0) or 0) - _ticks_diff(_ticks_ms(), packet_ms))
    snap["reset_wait_ms"] = reset_wait_ms
    return snap
