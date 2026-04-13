from core.contracts import BaseApp
from ui.components import apply_text_edit, fields_from_pairs, menu_move
from ui.models import FormScreen

from apps.builtins.common import go_back


class AddTwoNumsApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.selected = 0
        self.inputs = {"a": "", "b": ""}
        self.message = "Enter both numbers."

    def enter(self, ctx, params=None):
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "installed_hub")
            return
        previous = self.selected
        self.selected = menu_move(token, self.selected, 2)
        if self.selected != previous:
            self.mark_dirty()
            return
        if token == "exe" or (token == "ok" and self.selected == 1):
            try:
                result = float(self.inputs["a"] or 0) + float(self.inputs["b"] or 0)
                self.message = "= %s" % result
            except Exception:
                self.message = "Invalid number."
            self.mark_dirty()
            return
        if token == "ok":
            self.selected = 1
            self.mark_dirty()
            return
        key = "a" if self.selected == 0 else "b"
        updated = apply_text_edit(self.inputs[key], token)
        if updated != self.inputs[key]:
            self.inputs[key] = updated
            self.mark_dirty()

    def render(self, ctx):
        return FormScreen(
            self.manifest.title,
            fields_from_pairs(
                [
                    ("a", "Num1", self.inputs["a"]),
                    ("b", "Num2", self.inputs["b"]),
                ]
            ),
            selected=self.selected,
            footer=ctx.input.mode_label(),
            message=self.message,
        )


def create_app(manifest):
    return AddTwoNumsApp(manifest)
