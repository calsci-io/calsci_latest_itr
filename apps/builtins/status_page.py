from core.contracts import BaseApp
from ui.models import TextScreen

from .common import go_back


class StatusPageApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.lines = []
        self.kind = manifest.metadata.get("status_kind", "device")

    def enter(self, ctx, params=None):
        self._refresh(ctx)

    def _refresh(self, ctx):
        if self.kind == "network":
            status = ctx.network.status()
            if not status.get("connected"):
                self.lines = ["WiFi disconnected.", "Open WiFi manager."]
            else:
                self.lines = [
                    "Connected: yes",
                    "SSID: %s" % (status.get("ssid") or "?"),
                ]
                if status.get("ifconfig"):
                    self.lines.extend(
                        [
                            "IP: %s" % status["ifconfig"][0],
                            "GW: %s" % status["ifconfig"][2],
                        ]
                    )
        elif self.kind == "battery":
            info = ctx.power.battery_info()
            self.lines = [
                "Voltage: %s" % info.get("voltage"),
                "Charging: %s" % info.get("charging"),
            ]
        else:
            self.lines = [
                "Unique ID:",
                ctx.power.unique_id_hex() or "Unavailable",
                "Default route:",
                ctx.storage.get_setting("default_route", "launcher"),
            ]
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "settings_hub")
            return
        if token in ("ok", "exe"):
            self._refresh(ctx)

    def render(self, ctx):
        return TextScreen(self.manifest.title, self.lines, footer="OK refresh")


def create_app(manifest):
    return StatusPageApp(manifest)
