from core.contracts import BaseApp
from ui.components import apply_text_edit
from ui.models import TextScreen

from .common import go_back


class LatexCalcApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.expression = ""
        self.normalized = ""
        self.result = "Enter a LaTeX expression."

    def enter(self, ctx, params=None):
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if token == "back":
            go_back(ctx, "launcher")
            return
        if token in ("ok", "exe"):
            self._evaluate(ctx)
            return
        updated = apply_text_edit(self.expression, token)
        if updated != self.expression:
            self.expression = updated
            self.mark_dirty()

    def _evaluate(self, ctx):
        source = self.expression.strip()
        if not source:
            self.normalized = ""
            self.result = "Enter a LaTeX expression."
            self.mark_dirty()
            return
        try:
            self.normalized = ctx.latex.normalize(source)
            self.result = "= %s" % ctx.calc.evaluate(self.normalized.replace("^", "**"))
        except Exception as exc:
            self.result = "Error: %s" % exc
        self.mark_dirty()

    def render(self, ctx):
        lines = [
            "Input: %s" % (self.expression or "_"),
            "Expr: %s" % (self.normalized or "_"),
            self.result,
            "Use OK to evaluate.",
        ]
        return TextScreen(self.manifest.title, lines, footer=ctx.input.mode_label())


def create_app(manifest):
    return LatexCalcApp(manifest)
