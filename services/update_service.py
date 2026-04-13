try:
    import uhashlib as _hash_mod  # type: ignore
except Exception:
    try:
        import hashlib as _hash_mod  # type: ignore
    except Exception:
        _hash_mod = None

from core.update_common import normalize_update_path, stage_relative_path


def _join_url(base_url, relative_path):
    base = str(base_url or "").rstrip("/")
    rel = str(relative_path or "").lstrip("/")
    if not base:
        return rel
    return base + "/" + rel


def _sha256_hex(text):
    if _hash_mod is None or not hasattr(_hash_mod, "sha256"):
        raise RuntimeError("sha256 unavailable")
    if isinstance(text, str):
        payload = text.encode("utf-8")
    else:
        payload = bytes(text)
    try:
        hasher = _hash_mod.sha256()
        hasher.update(payload)
    except TypeError:
        hasher = _hash_mod.sha256(payload)
    digest = hasher.digest()
    return "".join("{:02x}".format(item) for item in digest)


class UpdateService:
    def __init__(self, network, storage, config):
        self.network = network
        self.storage = storage
        self.config = config

    def current_version(self):
        return self.storage.get_update_state().get("current_version", self.config.get("software_version", "dev"))

    def manifest_url(self):
        return str(self.config.get("update_manifest_url", "") or "")

    def state(self):
        return self.storage.get_update_state()

    def source_label(self):
        url = self.manifest_url()
        if not url:
            return "No source"
        marker = "://"
        if marker in url:
            url = url.split(marker, 1)[1]
        if len(url) <= 32:
            return url
        return url[:29] + "..."

    def _ensure_connected(self):
        status = self.network.status()
        if not status.get("connected"):
            raise RuntimeError("wifi not connected")

    def _validate_manifest(self, manifest):
        if not isinstance(manifest, dict):
            raise RuntimeError("invalid manifest")
        product = str(manifest.get("product", "") or "")
        expected_product = str(self.config.get("update_product", self.config.get("software_version", "calsci_v1")) or "")
        if product != expected_product:
            raise RuntimeError("manifest product mismatch")
        version = str(manifest.get("version", "") or "")
        if not version:
            raise RuntimeError("manifest version missing")
        files = list(manifest.get("files") or [])
        if not files:
            raise RuntimeError("manifest has no files")
        base_url = str(manifest.get("base_url", "") or "")
        normalized = []
        for item in files:
            if not isinstance(item, dict):
                raise RuntimeError("invalid manifest file entry")
            relative_path = normalize_update_path(item.get("path", ""))
            download_url = str(item.get("url", "") or "")
            if not download_url:
                download_url = _join_url(base_url, relative_path)
            if not download_url:
                raise RuntimeError("missing download url for %s" % relative_path)
            normalized.append(
                {
                    "path": relative_path,
                    "url": download_url,
                    "sha256": str(item.get("sha256", "") or "").lower(),
                }
            )
        return {
            "product": product,
            "version": version,
            "files": normalized,
        }

    def _load_manifest(self):
        manifest_url = self.manifest_url()
        if not manifest_url:
            raise RuntimeError("update manifest url not configured")
        self._ensure_connected()
        payload = self.network.http_get_json(manifest_url)
        return self._validate_manifest(payload)

    def check_for_update(self):
        manifest = self._load_manifest()
        current_version = self.current_version()
        update_available = manifest["version"] != current_version
        state = self.storage.get_update_state()
        state.update(
            {
                "available_version": manifest["version"] if update_available else "",
                "update_available": bool(update_available),
                "status": "available" if update_available else "idle",
                "last_checked_version": manifest["version"],
                "last_error": "",
                "pending_version": state.get("pending_version", ""),
            }
        )
        self.storage.save_update_state(state)
        return {
            "current_version": current_version,
            "available_version": manifest["version"],
            "update_available": update_available,
            "file_count": len(manifest["files"]),
        }

    def download_update(self):
        manifest = self._load_manifest()
        current_version = self.current_version()
        if manifest["version"] == current_version:
            state = self.storage.get_update_state()
            state.update(
                {
                    "available_version": "",
                    "update_available": False,
                    "status": "idle",
                    "last_checked_version": manifest["version"],
                    "last_error": "",
                    "pending_version": "",
                }
            )
            self.storage.save_update_state(state)
            self.storage.clear_pending_update()
            return {
                "current_version": current_version,
                "available_version": manifest["version"],
                "staged": False,
                "file_count": 0,
            }

        stage_root = self.storage.adapter.path("update_stage")
        self.storage.adapter.remove_tree_path(stage_root)
        self.storage.adapter.ensure_dir(stage_root)

        staged_files = []
        for item in manifest["files"]:
            text = self.network.http_get_text(item["url"])
            expected_hash = item.get("sha256", "")
            if expected_hash:
                actual_hash = _sha256_hex(text)
                if actual_hash != expected_hash:
                    raise RuntimeError("checksum mismatch for %s" % item["path"])
            stage_path = self.storage.adapter.path(stage_relative_path(item["path"]))
            self.storage.adapter.write_text_path(stage_path, text)
            staged_files.append(item["path"])

        self.storage.save_pending_update(
            {
                "product": manifest["product"],
                "version": manifest["version"],
                "files": staged_files,
                "manifest_url": self.manifest_url(),
            }
        )

        state = self.storage.get_update_state()
        state.update(
            {
                "available_version": manifest["version"],
                "update_available": True,
                "status": "ready",
                "last_checked_version": manifest["version"],
                "last_error": "",
                "pending_version": manifest["version"],
            }
        )
        self.storage.save_update_state(state)
        return {
            "current_version": current_version,
            "available_version": manifest["version"],
            "staged": True,
            "file_count": len(staged_files),
        }
