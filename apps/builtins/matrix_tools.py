from core.contracts import BaseApp
from ui.components import apply_text_edit, fields_from_pairs, menu_move
from ui.models import FormScreen, MenuScreen, TextScreen

from .common import clamp_scroll, go_back


class MatrixToolsApp(BaseApp):
    OPERATIONS = [
        ("add", "Add A+B"),
        ("multiply", "Multiply A*B"),
        ("inverse", "Inverse A"),
        ("transpose", "Transpose A"),
        ("determinant", "Determinant A"),
        ("rank", "Rank A"),
    ]

    def __init__(self, manifest):
        super().__init__(manifest)
        self.view = "menu"
        self.menu_index = 0
        self.form_selected = 0
        self.scroll = 0
        self.operation = self.OPERATIONS[0][0]
        self.message = ""
        self.inputs = {
            "a": "1,2;3,4",
            "b": "5,6;7,8",
        }
        self.result_lines = ["Use row syntax: 1,2;3,4"]

    def enter(self, ctx, params=None):
        self.view = "menu"
        self.message = "row syntax: 1,2;3,4"
        self.mark_dirty()

    def _needs_b(self):
        return self.operation in ("add", "multiply")

    def _compute(self, ctx):
        a = ctx.matrix.parse(self.inputs["a"])
        b = ctx.matrix.parse(self.inputs["b"]) if self._needs_b() else None
        if self.operation == "add":
            result = ctx.matrix.add(a, b)
        elif self.operation == "multiply":
            result = ctx.matrix.multiply(a, b)
        elif self.operation == "inverse":
            result = ctx.matrix.inverse(a)
        elif self.operation == "transpose":
            result = ctx.matrix.transpose(a)
        elif self.operation == "determinant":
            result = ctx.matrix.determinant(a)
        else:
            result = ctx.matrix.rank(a)

        label = dict(self.OPERATIONS)[self.operation]
        lines = [label]
        if isinstance(result, list):
            lines.extend(ctx.matrix.format(result))
        else:
            lines.append(str(result))
        self.result_lines = lines
        self.scroll = 0
        self.view = "result"
        self.mark_dirty()

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if self.view == "menu":
            self._handle_menu(ctx, token)
        elif self.view == "form":
            self._handle_form(ctx, token)
        else:
            self._handle_result(ctx, token)

    def _handle_menu(self, ctx, token):
        if token == "back":
            go_back(ctx, "scientific_hub")
            return
        previous = self.menu_index
        self.menu_index = menu_move(token, self.menu_index, len(self.OPERATIONS))
        if previous != self.menu_index:
            self.mark_dirty()
            return
        if token in ("ok", "exe"):
            self.operation = self.OPERATIONS[self.menu_index][0]
            self.form_selected = 0
            self.view = "form"
            self.message = "OK computes"
            self.mark_dirty()

    def _handle_form(self, ctx, token):
        field_count = 2 if self._needs_b() else 1
        if token == "back":
            self.view = "menu"
            self.mark_dirty()
            return
        previous = self.form_selected
        self.form_selected = menu_move(token, self.form_selected, field_count)
        if previous != self.form_selected:
            self.mark_dirty()
            return
        if token == "exe" or (token == "ok" and self.form_selected == field_count - 1):
            try:
                self._compute(ctx)
            except Exception as exc:
                self.message = str(exc)
                self.mark_dirty()
            return
        if token == "ok":
            self.form_selected = min(field_count - 1, self.form_selected + 1)
            self.mark_dirty()
            return
        key = "a" if self.form_selected == 0 else "b"
        updated = apply_text_edit(self.inputs[key], token)
        if updated != self.inputs[key]:
            self.inputs[key] = updated
            self.mark_dirty()

    def _handle_result(self, ctx, token):
        if token == "back":
            self.view = "form"
            self.mark_dirty()
            return
        if token == "nav_u":
            self.scroll = clamp_scroll(self.result_lines, self.scroll - 1)
            self.mark_dirty()
            return
        if token == "nav_d":
            self.scroll = clamp_scroll(self.result_lines, self.scroll + 1)
            self.mark_dirty()

    def render(self, ctx):
        if self.view == "menu":
            items = [item[1] for item in self.OPERATIONS]
            return MenuScreen(self.manifest.title, items, selected=self.menu_index, footer=ctx.input.mode_label())
        if self.view == "form":
            pairs = [("a", "A", self.inputs["a"])]
            if self._needs_b():
                pairs.append(("b", "B", self.inputs["b"]))
            return FormScreen(
                self.manifest.title,
                fields_from_pairs(pairs),
                selected=self.form_selected,
                footer=ctx.input.mode_label(),
                message=self.message,
            )
        return TextScreen(self.manifest.title, self.result_lines, footer="back=form", scroll=self.scroll)


def create_app(manifest):
    return MatrixToolsApp(manifest)
