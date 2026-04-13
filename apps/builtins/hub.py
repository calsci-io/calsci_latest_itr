from core.contracts import BaseApp
from ui.components import menu_move
from ui.models import MenuScreen

from .common import go_back


class GroupHubApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.selected = 0

    def enter(self, ctx, params=None):
        self.selected = 0
        self.mark_dirty()

    def _manifests(self, ctx):
        return ctx.list_apps(self.manifest.metadata.get("child_group", "launcher"))

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        manifests = self._manifests(ctx)
        if token == "back":
            fallback = self.manifest.metadata.get("back_route")
            if fallback:
                go_back(ctx, fallback)
            return
        if not manifests:
            return
        previous = self.selected
        self.selected = menu_move(token, self.selected, len(manifests))
        if self.selected != previous:
            self.mark_dirty()
            return
        if token in ("ok", "exe"):
            ctx.router.navigate(manifests[self.selected].app_id)

    def render(self, ctx):
        manifests = self._manifests(ctx)
        if not manifests:
            items = [self.manifest.metadata.get("empty_message", "No apps available")]
            selected = 0
        else:
            items = [item.title for item in manifests]
            if self.selected >= len(items):
                self.selected = len(items) - 1
            selected = self.selected
        return MenuScreen(
            self.manifest.title,
            items,
            selected=selected,
            subtitle=self.manifest.metadata.get("subtitle", ""),
            footer=ctx.input.mode_label(),
        )
