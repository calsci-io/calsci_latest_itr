from core.contracts import BaseApp
from services.power_service import BACKLIGHT_MAX_LEVEL
from ui.models import TextScreen

from .common import go_back, level_bar


class BacklightSettingApp(BaseApp):
    def enter(self, ctx, params=None):
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "settings_hub")
            return

        level = ctx.power.get_backlight_level()
        if token in ("nav_l", "nav_d", "-"):
            ctx.power.set_backlight_level(level - 1)
            self.mark_dirty()
        elif token in ("nav_r", "nav_u", "+"):
            ctx.power.set_backlight_level(level + 1)
            self.mark_dirty()

    def render(self, ctx):
        level = ctx.power.get_backlight_level()
        lines = [
            "Level: %s/%s" % (level, BACKLIGHT_MAX_LEVEL),
            level_bar(level, total=BACKLIGHT_MAX_LEVEL),
            "left/down: dim",
            "right/up: raise",
        ]
        return TextScreen(self.manifest.title, lines, footer=ctx.input.mode_label())


def create_app(manifest):
    return BacklightSettingApp(manifest)
