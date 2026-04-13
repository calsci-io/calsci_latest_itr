from ui.canvas import MonoCanvas
from ui.theme import DISPLAY_HEIGHT, DISPLAY_WIDTH


class GraphService:
    def __init__(self):
        self.safe_globals = {
            "__builtins__": {},
            "sin": __import__("math").sin,
            "cos": __import__("math").cos,
            "tan": __import__("math").tan,
            "asin": __import__("math").asin,
            "acos": __import__("math").acos,
            "atan": __import__("math").atan,
            "sqrt": __import__("math").sqrt,
            "log": __import__("math").log,
            "log10": __import__("math").log10,
            "pi": __import__("math").pi,
            "e": __import__("math").e,
            "abs": abs,
        }

    def render_expression(self, expression, x_min=-10.0, x_max=10.0, y_min=-10.0, y_max=10.0):
        canvas = MonoCanvas()
        canvas.clear()
        self._draw_axes(canvas, x_min, x_max, y_min, y_max)
        compiled = compile(str(expression).replace("^", "**"), "<graph>", "eval")
        previous = None
        for x_pixel in range(DISPLAY_WIDTH):
            x_value = x_min + (x_pixel / float(DISPLAY_WIDTH - 1)) * (x_max - x_min)
            try:
                y_value = eval(compiled, self.safe_globals, {"x": x_value})
            except Exception:
                previous = None
                continue
            if not isinstance(y_value, (int, float)):
                previous = None
                continue
            if y_value < y_min or y_value > y_max:
                previous = None
                continue
            y_pixel = int((y_max - y_value) * (DISPLAY_HEIGHT - 1) / (y_max - y_min))
            if previous is not None:
                canvas.line(previous[0], previous[1], x_pixel, y_pixel, 1)
            previous = (x_pixel, y_pixel)
        return canvas.buffer

    def _draw_axes(self, canvas, x_min, x_max, y_min, y_max):
        if x_min <= 0 <= x_max:
            x_zero = int((0 - x_min) * (DISPLAY_WIDTH - 1) / (x_max - x_min))
            canvas.line(x_zero, 0, x_zero, DISPLAY_HEIGHT - 1, 1)
        if y_min <= 0 <= y_max:
            y_zero = int((y_max - 0) * (DISPLAY_HEIGHT - 1) / (y_max - y_min))
            canvas.line(0, y_zero, DISPLAY_WIDTH - 1, y_zero, 1)

