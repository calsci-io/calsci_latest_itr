import unittest

from sim_new.main import SimInputAdapter, build_sim_container
from sim_new.pygame_shell import SimulatorShell, matrix_token, token_from_key


class SimNewTests(unittest.TestCase):
    def test_key_mapping_matches_sim_contract(self):
        self.assertEqual(token_from_key("up"), "nav_u")
        self.assertEqual(token_from_key("return"), "ok")
        self.assertEqual(token_from_key("space"), "exe")
        self.assertEqual(token_from_key("backspace"), "nav_b")
        self.assertEqual(token_from_key("escape"), "back")
        self.assertEqual(token_from_key("tab"), "tab")
        self.assertEqual(token_from_key("a"), "alpha")
        self.assertEqual(token_from_key("b"), "beta")
        self.assertEqual(token_from_key("c"), "caps")
        self.assertEqual(token_from_key("f1"), "diff()")
        self.assertEqual(token_from_key("f2"), "ln()")
        self.assertEqual(token_from_key("f3"), "module")
        self.assertEqual(token_from_key("h"), "home")
        self.assertEqual(token_from_key("w"), "wifi")
        self.assertEqual(token_from_key("t"), "toolbox")
        self.assertEqual(token_from_key("", "7"), "7")
        self.assertEqual(token_from_key("", "+"), "+")

    def test_matrix_layout_maps_old_faceplate_to_calsci_new_tokens(self):
        self.assertEqual(matrix_token("d", 1, 4), "diff()")
        self.assertEqual(matrix_token("d", 3, 2), "sin()")
        self.assertEqual(matrix_token("d", 4, 0), "pow(,)")
        self.assertEqual(matrix_token("d", 5, 0), "ln()")
        self.assertEqual(matrix_token("b", 3, 2), "asin(")
        self.assertEqual(matrix_token("A", 8, 1), "Y")
        self.assertIsNone(matrix_token("a", 9, 2))

    def test_sim_input_adapter_handles_click_matrix_and_direct_tokens(self):
        shell = SimulatorShell(headless=True)
        adapter = SimInputAdapter(shell)

        shell.push_matrix_key(3, 2)
        self.assertEqual(adapter.poll_token("d"), "sin()")

        shell.push_matrix_key(3, 2)
        self.assertEqual(adapter.poll_token("b"), "asin(")

        shell.queue_token("nav_u")
        self.assertEqual(adapter.poll_token("d"), "nav_u")

    def test_build_sim_container_headless_and_render_launcher(self):
        container = build_sim_container(headless=True, initial_route="launcher")
        ctx = container["ctx"]
        app = ctx.registry.create("launcher")
        app.enter(ctx, {})
        screen = app.render(ctx)
        ctx.render.render(screen)

        frame = container["shell"].framebuffer_bytes()
        self.assertEqual(len(frame), 1024)
        self.assertTrue(any(value != 0 for value in frame))

    def test_sim_smoke_renders_multiple_routes(self):
        container = build_sim_container(headless=True, initial_route="launcher")
        ctx = container["ctx"]

        for app_id in ("calculate", "wifi_manager", "add_2_nums"):
            app = ctx.registry.create(app_id)
            app.enter(ctx, {})
            screen = app.render(ctx)
            ctx.render.render(screen)
            frame = container["shell"].framebuffer_bytes()
            self.assertTrue(any(value != 0 for value in frame), app_id)


if __name__ == "__main__":
    unittest.main()
