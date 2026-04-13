from core.contracts import BaseApp
from ui.components import apply_text_edit
from ui.models import TextScreen

from .common import go_back


class CalculateApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.expression = ""
        self.result_lines = ["Enter an expression.", "Press OK or EXE."]

    def enter(self, ctx, params=None):
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "launcher")
            return
        if token == "toolbox":
            ctx.router.navigate("scientific_hub")
            return
        if token in ("ok", "exe"):
            self._evaluate(ctx)
            return
        updated = apply_text_edit(self.expression, token)
        if updated != self.expression:
            self.expression = updated
            self.mark_dirty()

    def _evaluate(self, ctx):
        expression = self.expression.strip().replace("^", "**")
        if not expression:
            self.result_lines = ["Enter an expression.", "Press OK or EXE."]
            self.mark_dirty()
            return
        try:
            result = ctx.calc.evaluate(expression)
            self.result_lines = ["= %s" % result]
        except Exception as exc:
            self.result_lines = ["Error:", str(exc)]
        self.mark_dirty()

    def render(self, ctx):
        lines = [
            "Expr: %s" % (self.expression or "_"),
        ]
        lines.extend(self.result_lines)
        lines.append("toolbox -> scientific")
        return TextScreen(self.manifest.title, lines, footer=ctx.input.mode_label())


def create_app(manifest):
    return CalculateApp(manifest)
