import unittest

from _helpers import fake_device_modules


class BootstrapDevicePathTests(unittest.TestCase):
    def test_build_container_with_fake_device_modules(self):
        with fake_device_modules():
            from core.bootstrap import build_container

            container = build_container()
            ctx = container["ctx"]

            launcher_titles = [item.title for item in ctx.list_apps("launcher")]
            installed_ids = [item.app_id for item in ctx.list_apps("installed")]

            self.assertIn("Calculate", launcher_titles)
            self.assertIn("Settings", launcher_titles)
            self.assertIn("add_2_nums", installed_ids)
            self.assertNotIn("dino", installed_ids)


if __name__ == "__main__":
    unittest.main()
