import unittest

from _helpers import ROOT_DIR

from core.router import Router


class RouterTests(unittest.TestCase):
    def test_navigation_history_and_replace(self):
        router = Router(initial_route="launcher")
        self.assertEqual(router.consume_pending(), ("launcher", {}))
        router.set_current("launcher", {})
        router.navigate("settings_hub", {"tab": "wifi"})
        self.assertEqual(router.consume_pending(), ("settings_hub", {"tab": "wifi"}))
        router.set_current("settings_hub", {"tab": "wifi"})
        self.assertTrue(router.back())
        self.assertEqual(router.consume_pending(), ("launcher", {}))
        router.replace("calculate")
        self.assertEqual(router.consume_pending(), ("calculate", {}))


if __name__ == "__main__":
    unittest.main()
