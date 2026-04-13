from core.contracts import BaseApp
from ui.components import menu_move
from ui.models import MenuScreen

from .common import format_on_off, format_minutes, go_back


class AutoSleepSettingApp(BaseApp):
    PRESET_MINUTES = [1, 5, 15, 30, 60, 180]

    def __init__(self, manifest):
        super().__init__(manifest)
        self.selected = 0
        self.preset_index = 1
        self.enabled = True

    def enter(self, ctx, params=None):
        self.selected = 0
        self.enabled = bool(ctx.storage.get_setting("auto_sleep", True))
        current_minutes = format_minutes(ctx.storage.get_setting("sleep_timer_ms", 300000))
        if current_minutes in self.PRESET_MINUTES:
            self.preset_index = self.PRESET_MINUTES.index(current_minutes)
        else:
            self.preset_index = 1
        self.mark_dirty()

    def _save(self, ctx):
        ctx.storage.set_setting("auto_sleep", self.enabled)
        ctx.storage.set_setting("sleep_timer_ms", self.PRESET_MINUTES[self.preset_index] * 60000)

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            self._save(ctx)
            go_back(ctx, "settings_hub")
            return

        previous = self.selected
        self.selected = menu_move(token, self.selected, 3)
        if self.selected != previous:
            self.mark_dirty()
            return

        if token in ("nav_l", "nav_r", "ok", "exe"):
            if self.selected == 0:
                self.enabled = not self.enabled
            elif self.selected == 1:
                shift = -1 if token == "nav_l" else 1
                self.preset_index = (self.preset_index + shift) % len(self.PRESET_MINUTES)
            else:
                self._save(ctx)
                go_back(ctx, "settings_hub")
                return
            self._save(ctx)
            self.mark_dirty()

    def render(self, ctx):
        items = [
            "Enabled: %s" % format_on_off(self.enabled),
            "Timer: %s min" % self.PRESET_MINUTES[self.preset_index],
            "Save + Back",
        ]
        return MenuScreen(self.manifest.title, items, selected=self.selected, footer=ctx.input.mode_label())


def create_app(manifest):
    return AutoSleepSettingApp(manifest)
