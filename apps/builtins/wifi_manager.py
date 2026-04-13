from core.contracts import BaseApp
from ui.components import apply_text_edit, fields_from_pairs, menu_move
from ui.models import FormScreen, MenuScreen, TextScreen

from .common import get_saved_password, go_back


class WifiManagerApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.view = "scan"
        self.loading = False
        self.networks = []
        self.selected = 0
        self.message = ""
        self.ssid = ""
        self.password = ""
        self.result_lines = []

    def enter(self, ctx, params=None):
        self._start_scan(ctx)

    def _scan_task(self):
        return self.manifest.app_id + ".scan"

    def _connect_task(self):
        return self.manifest.app_id + ".connect"

    def _start_scan(self, ctx):
        self.view = "scan"
        self.loading = True
        self.message = "Scanning..."
        if not ctx.tasks.submit(self._scan_task(), ctx.network.scan):
            self.loading = False
            self.message = "Task pool full."
        self.mark_dirty()

    def _start_connect(self, ctx):
        self.view = "password"
        self.loading = True
        self.message = "Connecting..."
        if not ctx.tasks.submit(self._connect_task(), ctx.network.connect, args=(self.ssid, self.password)):
            self.loading = False
            self.message = "Task pool full."
        self.mark_dirty()

    def _set_status(self, ctx, success):
        status = ctx.network.status()
        self.view = "status"
        self.loading = False
        if success and status.get("connected"):
            self.result_lines = [
                "Connected: yes",
                "SSID: %s" % (status.get("ssid") or self.ssid),
            ]
            if status.get("ifconfig"):
                self.result_lines.append("IP: %s" % status["ifconfig"][0])
        else:
            self.result_lines = [
                "Connection failed.",
                self.ssid or "Unknown SSID",
            ]
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") == "task":
            name = event.get("name")
            if name == self._scan_task():
                self.loading = False
                if event.get("status") == "completed":
                    self.networks = list(event.get("payload") or [])
                    self.networks.sort()
                    self.message = "%s networks" % len(self.networks)
                else:
                    self.networks = []
                    self.message = event.get("error") or "Scan failed"
                self.selected = 0
                self.mark_dirty()
                return
            if name == self._connect_task():
                self._set_status(ctx, event.get("status") == "completed" and bool(event.get("payload")))
                return

        if event.get("type") != "input":
            return

        token = event.get("token")
        if self.view == "scan":
            self._handle_scan(ctx, token)
        elif self.view == "password":
            self._handle_password(ctx, token)
        else:
            self._handle_status(ctx, token)

    def _handle_scan(self, ctx, token):
        if token == "back":
            go_back(ctx, "settings_hub")
            return
        if self.loading:
            return
        items = ["Refresh Scan"] + self.networks
        previous = self.selected
        self.selected = menu_move(token, self.selected, len(items))
        if previous != self.selected:
            self.mark_dirty()
            return
        if token in ("ok", "exe"):
            if self.selected == 0:
                self._start_scan(ctx)
                return
            self.ssid = items[self.selected]
            self.password = get_saved_password(ctx, self.ssid)
            self.view = "password"
            self.message = "Enter password"
            self.mark_dirty()

    def _handle_password(self, ctx, token):
        if token == "back":
            self.view = "scan"
            self.loading = False
            self.mark_dirty()
            return
        if self.loading:
            return
        if token in ("ok", "exe"):
            self._start_connect(ctx)
            return
        updated = apply_text_edit(self.password, token)
        if updated != self.password:
            self.password = updated
            self.mark_dirty()

    def _handle_status(self, ctx, token):
        if token == "back":
            self.view = "scan"
            self.mark_dirty()
            return
        if token in ("ok", "exe"):
            self._start_scan(ctx)

    def render(self, ctx):
        if self.view == "scan":
            if self.loading:
                return TextScreen(self.manifest.title, ["Scanning...", self.message], footer="back=settings")
            items = ["Refresh Scan"] + self.networks
            if len(items) == 1:
                items.append("No networks found")
            return MenuScreen(
                self.manifest.title,
                items,
                selected=min(self.selected, len(items) - 1),
                subtitle=self.message,
                footer=ctx.input.mode_label(),
            )
        if self.view == "password":
            return FormScreen(
                self.manifest.title,
                fields_from_pairs(
                    [
                        ("ssid", "SSID", self.ssid),
                        ("password", "Pass", self.password),
                    ]
                ),
                selected=1,
                footer=ctx.input.mode_label(),
                message=self.message,
            )
        return TextScreen(self.manifest.title, self.result_lines, footer="OK rescan")


def create_app(manifest):
    return WifiManagerApp(manifest)
