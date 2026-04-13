from core.contracts import BaseApp
from ui.models import TextScreen

from .common import go_back


class SoftwareUpdateApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.loading = False
        self.action = ""

    def enter(self, ctx, params=None):
        self.loading = False
        self.action = ""
        self.mark_dirty()

    def _check_task(self):
        return self.manifest.app_id + ".check"

    def _download_task(self):
        return self.manifest.app_id + ".download"

    def _record_error(self, ctx, message):
        state = ctx.update.state()
        state.update(
            {
                "status": "error",
                "last_error": str(message or "update failed"),
            }
        )
        ctx.storage.save_update_state(state)
        self.mark_dirty()

    def _start_check(self, ctx):
        self.loading = True
        self.action = "Checking GitHub..."
        if not ctx.tasks.submit(self._check_task(), ctx.update.check_for_update):
            self.loading = False
            self._record_error(ctx, "task pool full")
            return
        self.mark_dirty()

    def _start_download(self, ctx):
        self.loading = True
        self.action = "Downloading update..."
        if not ctx.tasks.submit(self._download_task(), ctx.update.download_update):
            self.loading = False
            self._record_error(ctx, "task pool full")
            return
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") == "task":
            name = event.get("name")
            if name in (self._check_task(), self._download_task()):
                self.loading = False
                self.action = ""
                if event.get("status") != "completed":
                    self._record_error(ctx, event.get("error"))
                else:
                    self.mark_dirty()
                return

        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "settings_hub")
            return
        if self.loading or token not in ("ok", "exe"):
            return

        state = ctx.update.state()
        if state.get("status") == "ready":
            ctx.power.restart()
            return
        if state.get("update_available"):
            self._start_download(ctx)
            return
        self._start_check(ctx)

    def render(self, ctx):
        state = ctx.update.state()
        current_version = state.get("current_version", ctx.update.current_version())
        lines = [
            "Current: %s" % current_version,
            "Source: %s" % ctx.update.source_label(),
        ]
        if self.loading:
            lines.extend(
                [
                    self.action or "Working...",
                    "Wait for completion.",
                ]
            )
        elif state.get("status") == "ready":
            lines.extend(
                [
                    "Ready: %s" % (state.get("pending_version") or state.get("available_version") or "?"),
                    "Downloaded to stage.",
                    "OK reboot apply.",
                ]
            )
        elif state.get("update_available"):
            lines.extend(
                [
                    "Available: %s" % (state.get("available_version") or "?"),
                    "OK downloads update.",
                ]
            )
        elif state.get("status") in ("error", "apply_failed"):
            lines.extend(
                [
                    "Update error:",
                    str(state.get("last_error") or "unknown")[:24],
                    "OK retries check.",
                ]
            )
        elif state.get("last_checked_version"):
            lines.extend(
                [
                    "No newer version.",
                    "Checked: %s" % state.get("last_checked_version"),
                    "OK check again.",
                ]
            )
        else:
            lines.extend(
                [
                    "Press OK to check",
                    "for software update.",
                ]
            )
        return TextScreen(self.manifest.title, lines, footer="OK next")


def create_app(manifest):
    return SoftwareUpdateApp(manifest)
