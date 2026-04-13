from core.contracts import BaseApp
from ui.components import apply_text_edit, fields_from_pairs
from ui.models import FormScreen, TextScreen

from .common import clamp_scroll, go_back


class ChatGPTApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.query = ""
        self.status = ""
        self.result_lines = ["Type a query and press OK."]
        self.view = "input"
        self.scroll = 0

    def enter(self, ctx, params=None):
        self.mark_dirty()

    def _task_name(self):
        return self.manifest.app_id + ".search"

    def _start_search(self, ctx):
        self.status = "Searching..."
        self.view = "loading"
        submitted = ctx.tasks.submit(
            self._task_name(),
            ctx.search.search,
            args=(self.query.strip(),),
        )
        if not submitted:
            self.view = "results"
            self.result_lines = ["Task pool full.", "Try again in a moment."]
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") == "task" and event.get("name") == self._task_name():
            self.view = "results"
            self.scroll = 0
            if event.get("status") == "completed":
                self.result_lines = event.get("payload") or ["No results."]
            else:
                self.result_lines = ["Search failed.", event.get("error") or "Unknown error"]
            self.status = ""
            self.mark_dirty()
            return
        if event.get("type") != "input":
            return

        token = event.get("token")
        if self.view in ("results", "loading"):
            if token == "back":
                self.view = "input"
                self.mark_dirty()
                return
            if token == "nav_u":
                self.scroll = clamp_scroll(self.result_lines, self.scroll - 1)
                self.mark_dirty()
                return
            if token == "nav_d":
                self.scroll = clamp_scroll(self.result_lines, self.scroll + 1)
                self.mark_dirty()
                return
            if token in ("ok", "exe") and self.query.strip():
                self._start_search(ctx)
            return

        if token == "back":
            go_back(ctx, "launcher")
            return
        if token in ("ok", "exe"):
            self._start_search(ctx)
            return
        updated = apply_text_edit(self.query, token)
        if updated != self.query:
            self.query = updated
            self.mark_dirty()

    def render(self, ctx):
        if self.view == "input":
            return FormScreen(
                self.manifest.title,
                fields_from_pairs([("query", "Query", self.query)]),
                selected=0,
                footer=ctx.input.mode_label(),
                message=self.status or "Search via WiFi",
            )
        if self.view == "loading":
            return TextScreen(
                self.manifest.title,
                ["Searching...", self.query or "_"],
                footer="back=cancel",
            )
        return TextScreen(self.manifest.title, self.result_lines, footer="back=query", scroll=self.scroll)


def create_app(manifest):
    return ChatGPTApp(manifest)
