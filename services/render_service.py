from ui.legacy_shell import LegacyShellRenderer


class RenderService:
    def __init__(self, display_adapter, storage):
        self.display = display_adapter
        self.storage = storage
        self.shell = LegacyShellRenderer()

    def render(self, screen):
        self.display.set_invert(bool(self.storage.get_setting("dark_mode", False)))
        if screen is None:
            return
        if screen.screen_type == "canvas":
            self.display.draw_canvas(screen.buffer_bytes)
            return
        self.display.draw_canvas(self.shell.render(screen))

    def render_exception(self, exc):
        self.display.draw_canvas(self.shell.render_exception(exc))
