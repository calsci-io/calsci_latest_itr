import json
import os
import tempfile
import unittest

from adapters.device.storage import DeviceStorageAdapter
from services.storage_service import StorageService


class StorageTests(unittest.TestCase):
    def test_bootstrap_from_legacy_maps_settings_and_optional_apps(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_root = os.path.join(tmpdir, "legacy")
            os.makedirs(os.path.join(legacy_root, "db"))

            with open(os.path.join(legacy_root, "db", "settings.json"), "w") as handle:
                json.dump(
                    {
                        "_default": {
                            "1": {"feature": "dark_mode", "value": True},
                            "2": {"feature": "default_app", "value": {"app_name": "settings"}},
                            "3": {"feature": "sleep_timer", "value": 300000},
                        }
                    },
                    handle,
                )
            with open(os.path.join(legacy_root, "db", "wifi.json"), "w") as handle:
                json.dump([{"ssid": "Lab", "password": "secret"}], handle)
            with open(os.path.join(legacy_root, "db", "functions_data.json"), "w") as handle:
                json.dump(
                    {
                        "_default": {
                            "1": {"name": "f", "variables": ["x"], "expression": "x*x"},
                        }
                    },
                    handle,
                )
            with open(os.path.join(legacy_root, "db", "installed_apps.json"), "w") as handle:
                json.dump(
                    {
                        "_default": {
                            "1": {"app_name": "add_2_nums"},
                            "2": {"app_name": "dino"},
                        }
                    },
                    handle,
                )

            config = {"data_dir": "data", "legacy_root": legacy_root}
            adapter = DeviceStorageAdapter(tmpdir, config)
            storage = StorageService(adapter, config)
            storage.bootstrap_from_legacy()

            self.assertEqual(storage.get_setting("default_route"), "settings_hub")
            self.assertEqual(storage.get_setting("backlight_level"), 15)
            self.assertEqual(storage.get_wifi_credentials()[0]["ssid"], "Lab")
            self.assertEqual(storage.get_functions()[0]["name"], "f")
            self.assertEqual(storage.get_installed_apps(), ["add_2_nums"])


if __name__ == "__main__":
    unittest.main()
