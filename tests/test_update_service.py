import hashlib
import os
import tempfile
import unittest

from adapters.device.storage import DeviceStorageAdapter
from core.update_boot import apply_pending_update
from services.storage_service import StorageService
from services.update_service import UpdateService


class _FakeNetwork:
    def __init__(self, manifest, text_by_url, connected=True):
        self._manifest = manifest
        self._text_by_url = dict(text_by_url)
        self._connected = bool(connected)
        self.json_urls = []
        self.text_urls = []

    def status(self):
        return {"connected": self._connected}

    def http_get_json(self, url):
        self.json_urls.append(url)
        return dict(self._manifest)

    def http_get_text(self, url):
        self.text_urls.append(url)
        return self._text_by_url[url]


class UpdateServiceTests(unittest.TestCase):
    def _storage(self, tmpdir, version="1.0.0"):
        config = {
            "data_dir": "data",
            "legacy_root": os.path.join(tmpdir, "legacy"),
            "software_version": version,
            "update_product": "calsci_v1",
            "update_manifest_url": "https://example.test/manifest.json",
        }
        adapter = DeviceStorageAdapter(tmpdir, config)
        storage = StorageService(adapter, config)
        storage.ensure_runtime_ready()
        return storage, config

    def test_check_for_update_marks_available_version(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage, config = self._storage(tmpdir, version="1.0.0")
            manifest = {
                "product": "calsci_v1",
                "version": "1.1.0",
                "files": [
                    {"path": "apps/builtins/calculate.py", "url": "https://example.test/calculate.py"},
                ],
            }
            network = _FakeNetwork(manifest, {"https://example.test/calculate.py": "print('ok')\n"})
            service = UpdateService(network, storage, config)

            result = service.check_for_update()

            self.assertTrue(result["update_available"])
            self.assertEqual(result["available_version"], "1.1.0")
            state = storage.get_update_state()
            self.assertEqual(state["available_version"], "1.1.0")
            self.assertTrue(state["update_available"])
            self.assertEqual(network.json_urls, ["https://example.test/manifest.json"])

    def test_download_and_apply_pending_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage, config = self._storage(tmpdir, version="1.0.0")
            payload = "VALUE = 42\n"
            payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            manifest = {
                "product": "calsci_v1",
                "version": "1.1.0",
                "base_url": "https://example.test/files",
                "files": [
                    {"path": "apps/builtins/update_probe.py", "sha256": payload_hash},
                ],
            }
            network = _FakeNetwork(manifest, {"https://example.test/files/apps/builtins/update_probe.py": payload})
            service = UpdateService(network, storage, config)

            result = service.download_update()

            self.assertTrue(result["staged"])
            staged_path = os.path.join(tmpdir, "data", "update_stage", "apps", "builtins", "update_probe.py")
            self.assertTrue(os.path.exists(staged_path))
            self.assertEqual(storage.get_pending_update()["version"], "1.1.0")
            self.assertEqual(storage.get_update_state()["status"], "ready")

            applied = apply_pending_update(tmpdir)

            self.assertTrue(applied)
            target_path = os.path.join(tmpdir, "apps", "builtins", "update_probe.py")
            with open(target_path, "r") as handle:
                self.assertEqual(handle.read(), payload)
            state = storage.get_update_state()
            self.assertEqual(state["current_version"], "1.1.0")
            self.assertEqual(state["status"], "applied")
            self.assertIsNone(storage.get_pending_update())


if __name__ == "__main__":
    unittest.main()
