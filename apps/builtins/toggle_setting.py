from core.contracts import BaseApp
from ui.models import TextScreen

from .common import format_on_off, go_back


class ToggleSettingApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.key = manifest.metadata.get("setting_key")
        self.description = manifest.metadata.get("description", "")

    def enter(self, ctx, params=None):
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "settings_hub")
            return
        if token in ("ok", "exe", "nav_l", "nav_r"):
            current = bool(ctx.storage.get_setting(self.key, False))
            ctx.storage.set_setting(self.key, not current)
            self.mark_dirty()

    def render(self, ctx):
        current = bool(ctx.storage.get_setting(self.key, False))
        lines = [
            "Current: %s" % format_on_off(current),
        ]
        if self.description:
            lines.append(self.description)
        lines.append("OK toggles value.")
        return TextScreen(self.manifest.title, lines, footer=ctx.input.mode_label())


def create_app(manifest):
    return ToggleSettingApp(manifest)
