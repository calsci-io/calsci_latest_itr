import unittest

from _helpers import fake_device_modules


class AppContractTests(unittest.TestCase):
    def test_enabled_installed_apps_create_and_render(self):
        with fake_device_modules():
            from core.bootstrap import build_container
            from core.contracts import BaseApp

            container = build_container()
            ctx = container["ctx"]

            for manifest in container["ctx"].registry._manifests.values():
                if not manifest.enabled or not manifest.installed:
                    continue
                app = ctx.registry.create(manifest.app_id)
                self.assertIsInstance(app, BaseApp)
                app.enter(ctx, {})
                screen = app.render(ctx)
                self.assertTrue(hasattr(screen, "screen_type"))


if __name__ == "__main__":
    unittest.main()
