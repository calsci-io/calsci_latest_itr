from core.contracts import BaseApp
from ui.models import TextScreen

from apps.builtins.common import go_back


class UtcTimeApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.lines = ["Press OK to refresh."]
        self.loading = False

    def enter(self, ctx, params=None):
        self._refresh(ctx)

    def _task_name(self):
        return self.manifest.app_id + ".refresh"

    def _refresh(self, ctx):
        self.loading = True
        self.lines = ["Refreshing time..."]
        if not ctx.tasks.submit(self._task_name(), ctx.time.indian_time):
            self.loading = False
            self.lines = ["Task pool full.", "Try again."]
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") == "task" and event.get("name") == self._task_name():
            self.loading = False
            if event.get("status") == "completed":
                payload = event.get("payload") or {}
                self.lines = [
                    "Indian Time",
                    "Date: %s" % payload.get("date", "?"),
                    "Time: %s" % payload.get("time", "?"),
                ]
            else:
                self.lines = ["Time sync failed.", event.get("error") or "Unknown error"]
            self.mark_dirty()
            return

        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "installed_hub")
            return
        if token in ("ok", "exe") and not self.loading:
            self._refresh(ctx)

    def render(self, ctx):
        return TextScreen(self.manifest.title, self.lines, footer="OK refresh")


def create_app(manifest):
    return UtcTimeApp(manifest)
