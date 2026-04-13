import unittest

from _helpers import ROOT_DIR

from core.registry import AppRegistry


class RegistryTests(unittest.TestCase):
    def test_manifest_loading_and_optional_sync(self):
        registry = AppRegistry()
        registry.load_manifest_dir(ROOT_DIR + "/config/apps")
        registry.sync_installed(["add_2_nums"])

        launcher = [item.app_id for item in registry.list_group("launcher")]
        installed = [item.app_id for item in registry.list_group("installed")]

        self.assertIn("calculate", launcher)
        self.assertIn("scientific_hub", launcher)
        self.assertEqual(installed, ["add_2_nums"])


if __name__ == "__main__":
    unittest.main()
