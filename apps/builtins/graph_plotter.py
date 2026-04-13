from core.contracts import BaseApp
from ui.components import apply_text_edit, fields_from_pairs, menu_move
from ui.models import CanvasScreen, FormScreen

from .common import format_number, go_back


class GraphPlotterApp(BaseApp):
    def __init__(self, manifest):
        super().__init__(manifest)
        self.view = "form"
        self.selected = 0
        self.message = ""
        self.buffer = bytearray()
        self.fields = {
            "expression": "sin(x)",
            "x_min": "-10",
            "x_max": "10",
            "y_min": "-10",
            "y_max": "10",
        }

    def enter(self, ctx, params=None):
        self.view = "form"
        self.message = "OK draws graph"
        self.mark_dirty()

    def _parse_scalar(self, ctx, text):
        value = ctx.calc.evaluate(str(text).replace("^", "**"))
        return float(value)

    def _draw(self, ctx):
        expression = self.fields["expression"].strip()
        if not expression:
            raise ValueError("expression required")
        x_min = self._parse_scalar(ctx, self.fields["x_min"])
        x_max = self._parse_scalar(ctx, self.fields["x_max"])
        y_min = self._parse_scalar(ctx, self.fields["y_min"])
        y_max = self._parse_scalar(ctx, self.fields["y_max"])
        self.buffer = ctx.graph.render_expression(expression.replace("^", "**"), x_min, x_max, y_min, y_max)
        self.fields["x_min"] = format_number(x_min)
        self.fields["x_max"] = format_number(x_max)
        self.fields["y_min"] = format_number(y_min)
        self.fields["y_max"] = format_number(y_max)
        self.view = "graph"
        self.message = "nav pans +/- zooms"
        self.mark_dirty()

    def _mutate_bounds(self, zoom=None, pan_x=0.0, pan_y=0.0):
        x_min = float(self.fields["x_min"])
        x_max = float(self.fields["x_max"])
        y_min = float(self.fields["y_min"])
        y_max = float(self.fields["y_max"])
        span_x = x_max - x_min
        span_y = y_max - y_min
        if zoom is not None:
            center_x = (x_min + x_max) / 2.0
            center_y = (y_min + y_max) / 2.0
            span_x *= zoom
            span_y *= zoom
            x_min = center_x - span_x / 2.0
            x_max = center_x + span_x / 2.0
            y_min = center_y - span_y / 2.0
            y_max = center_y + span_y / 2.0
        x_min += span_x * pan_x
        x_max += span_x * pan_x
        y_min += span_y * pan_y
        y_max += span_y * pan_y
        self.fields["x_min"] = format_number(x_min)
        self.fields["x_max"] = format_number(x_max)
        self.fields["y_min"] = format_number(y_min)
        self.fields["y_max"] = format_number(y_max)

    def handle_event(self, ctx, event):
        if event.get("type") != "input":
            return
        token = event.get("token")
        if self.view == "form":
            self._handle_form(ctx, token)
        else:
            self._handle_graph(ctx, token)

    def _handle_form(self, ctx, token):
        keys = ("expression", "x_min", "x_max", "y_min", "y_max")
        if token == "back":
            go_back(ctx, "scientific_hub")
            return
        previous = self.selected
        self.selected = menu_move(token, self.selected, len(keys))
        if previous != self.selected:
            self.mark_dirty()
            return
        if token == "exe" or (token == "ok" and self.selected == len(keys) - 1):
            try:
                self._draw(ctx)
            except Exception as exc:
                self.message = str(exc)
                self.mark_dirty()
            return
        if token == "ok":
            self.selected = min(len(keys) - 1, self.selected + 1)
            self.mark_dirty()
            return
        key = keys[self.selected]
        updated = apply_text_edit(self.fields[key], token)
        if updated != self.fields[key]:
            self.fields[key] = updated
            self.mark_dirty()

    def _handle_graph(self, ctx, token):
        if token == "back":
            self.view = "form"
            self.mark_dirty()
            return
        if token in ("ok", "exe"):
            self.view = "form"
            self.mark_dirty()
            return
        try:
            if token == "nav_l":
                self._mutate_bounds(pan_x=-0.1)
            elif token == "nav_r":
                self._mutate_bounds(pan_x=0.1)
            elif token == "nav_u":
                self._mutate_bounds(pan_y=0.1)
            elif token == "nav_d":
                self._mutate_bounds(pan_y=-0.1)
            elif token in ("+", "*"):
                self._mutate_bounds(zoom=0.8)
            elif token in ("-", "/"):
                self._mutate_bounds(zoom=1.25)
            else:
                return
            self._draw(ctx)
        except Exception as exc:
            self.view = "form"
            self.message = str(exc)
            self.mark_dirty()

    def render(self, ctx):
        if self.view == "form":
            return FormScreen(
                self.manifest.title,
                fields_from_pairs(
                    [
                        ("expression", "Expr", self.fields["expression"]),
                        ("x_min", "Xmin", self.fields["x_min"]),
                        ("x_max", "Xmax", self.fields["x_max"]),
                        ("y_min", "Ymin", self.fields["y_min"]),
                        ("y_max", "Ymax", self.fields["y_max"]),
                    ]
                ),
                selected=self.selected,
                footer=ctx.input.mode_label(),
                message=self.message,
            )
        return CanvasScreen(self.manifest.title, self.buffer, meta={"footer": self.message})


def create_app(manifest):
    return GraphPlotterApp(manifest)
