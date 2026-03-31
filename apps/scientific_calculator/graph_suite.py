import json
import math
import gc

try:
    import framebuf  # type: ignore
except ImportError:
    from mocking import framebuf  # type: ignore

import utime as time  # type: ignore

from data_modules.object_handler import (
    app,
    current_app,
    display,
    form,
    form_refresh,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)


DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_PAGES = DISPLAY_HEIGHT // 8
PLOT_HEIGHT = 56
PLOT_PAGES = (PLOT_HEIGHT + 7) // 8
PLOT_BUFFER_BYTES = PLOT_PAGES * DISPLAY_WIDTH
BOTTOM_PAGE_INDEX = DISPLAY_PAGES - 1
_CURSOR_COL_BUF_A = bytearray(PLOT_PAGES)
_CURSOR_COL_BUF_B = bytearray(PLOT_PAGES)

RELATION_TYPE_Y = "Y="
RELATION_TYPE_R = "r="
RELATION_TYPE_PARAM = "Parm"
RELATION_TYPE_X = "X="
RELATION_TYPE_Y_GT = "Y>"
RELATION_TYPE_Y_LT = "Y<"
RELATION_TYPE_Y_GE = "Y>="
RELATION_TYPE_Y_LE = "Y<="
RELATION_TYPE_X_GT = "X>"
RELATION_TYPE_X_LT = "X<"
RELATION_TYPE_X_GE = "X>="
RELATION_TYPE_X_LE = "X<="

RELATION_TYPES = (
    RELATION_TYPE_Y,
    RELATION_TYPE_R,
    RELATION_TYPE_PARAM,
    RELATION_TYPE_X,
    RELATION_TYPE_Y_GT,
    RELATION_TYPE_Y_LT,
    RELATION_TYPE_Y_GE,
    RELATION_TYPE_Y_LE,
    RELATION_TYPE_X_GT,
    RELATION_TYPE_X_LT,
    RELATION_TYPE_X_GE,
    RELATION_TYPE_X_LE,
)

STYLE_NORMAL = "normal"
STYLE_THICK = "thick"
STYLE_BROKEN = "broken"
STYLE_DOT = "dot"
STYLES = (STYLE_NORMAL, STYLE_THICK, STYLE_BROKEN, STYLE_DOT)

TOOL_NONE = 0
TOOL_AREA = 1
TOOL_TANGENT = 2
TOOL_NORMAL = 3
TOOL_VERTICAL = 4
TOOL_HORIZONTAL = 5

TOOL_MENU_ITEMS = (
    TOOL_AREA,
    TOOL_TANGENT,
    TOOL_NORMAL,
    TOOL_VERTICAL,
    TOOL_HORIZONTAL,
)

TOOL_LABELS = {
    TOOL_AREA: "Area",
    TOOL_TANGENT: "Tangent",
    TOOL_NORMAL: "Normal",
    TOOL_VERTICAL: "Vertical",
    TOOL_HORIZONTAL: "Horizontal",
}

TOOL_SHORT_LABELS = {
    TOOL_AREA: "A",
    TOOL_TANGENT: "T",
    TOOL_NORMAL: "N",
    TOOL_VERTICAL: "V",
    TOOL_HORIZONTAL: "H",
}

GRAPH_TOOLBOX_ITEMS = [
    "Functions",
    "Draw",
    "V-Window",
    "Zoom",
    "Trace",
    "G-Solve",
    "Table",
    "Dynamic",
    "Recursion",
    "Conics",
    "Features",
    "Used Tools",
    "Appearance",
    "Graph Memory",
    "Picture Memory",
]

MAX_RELATIONS = 20
MAX_VWINDOWS = 6
MAX_GRAPH_MEMORIES = 20
MAX_PICTURE_MEMORIES = 20
GRAPH_STATE_PATH = "/db/graph_suite_state.json"

ZOOM_IN_FACTOR = 0.82
ZOOM_OUT_FACTOR = 1.18
PAN_SHIFT_FACTOR = 0.10
INPUT_POLL_MS = 0.5
INPUT_POLL_SEC = INPUT_POLL_MS / 1000.0
SAMPLES_PER_PX_MIN = 4
SAMPLES_PER_PX_MAX = 32
EVAL_ABS_CLAMP = 1e12
DEFAULT_T_MIN = 0.0
DEFAULT_T_MAX = math.pi * 2.0
DEFAULT_T_STEP = math.pi / 60.0

RECUR_TYPE_TERM = "an"
RECUR_TYPE_TWO = "an+1"
RECUR_TYPE_THREE = "an+2"

CONIC_PARABOLA_X = "Parabola X"
CONIC_PARABOLA_Y = "Parabola Y"
CONIC_CIRCLE = "Circle"
CONIC_ELLIPSE_X = "Ellipse X"
CONIC_ELLIPSE_Y = "Ellipse Y"
CONIC_HYPERBOLA_X = "Hyperbola X"
CONIC_HYPERBOLA_Y = "Hyperbola Y"

CONIC_TYPES = (
    CONIC_PARABOLA_X,
    CONIC_PARABOLA_Y,
    CONIC_CIRCLE,
    CONIC_ELLIPSE_X,
    CONIC_ELLIPSE_Y,
    CONIC_HYPERBOLA_X,
    CONIC_HYPERBOLA_Y,
)

DEBUG_GRAPH = False


def _dprint(*args):
    if DEBUG_GRAPH:
        print(*args)


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _ticks_add(base_ms, delta_ms):
    if hasattr(time, "ticks_add"):
        return time.ticks_add(base_ms, delta_ms)
    return base_ms + delta_ms


def _ticks_diff(now_ms, start_ms):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(now_ms, start_ms)
    return now_ms - start_ms


def _clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def _copy_bounds(bounds):
    return {
        "x_min": float(bounds["x_min"]),
        "x_max": float(bounds["x_max"]),
        "y_min": float(bounds["y_min"]),
        "y_max": float(bounds["y_max"]),
        "x_scale": float(bounds.get("x_scale", 1.0)),
        "y_scale": float(bounds.get("y_scale", 1.0)),
        "t_min": float(bounds.get("t_min", DEFAULT_T_MIN)),
        "t_max": float(bounds.get("t_max", DEFAULT_T_MAX)),
        "t_step": float(bounds.get("t_step", DEFAULT_T_STEP)),
    }


def default_bounds():
    return {
        "x_min": -20.0,
        "x_max": 20.0,
        "y_min": -10.0,
        "y_max": 10.0,
        "x_scale": 5.0,
        "y_scale": 5.0,
        "t_min": DEFAULT_T_MIN,
        "t_max": DEFAULT_T_MAX,
        "t_step": DEFAULT_T_STEP,
    }


def default_relation(index=0):
    relation_type = RELATION_TYPE_Y
    expr = "x*sin(x)" if index == 0 else ""
    return {
        "name": relation_type + str(index + 1),
        "type": relation_type,
        "expr": expr,
        "expr_y": "",
        "enabled": index == 0,
        "style": STYLE_NORMAL,
        "range_start": "",
        "range_end": "",
    }


def _ensure_relations(relations):
    out = []
    src = relations or []
    for idx in range(MAX_RELATIONS):
        if idx < len(src):
            item = src[idx]
            out.append(
                {
                    "name": str(item.get("name") or (RELATION_TYPE_Y + str(idx + 1))),
                    "type": str(item.get("type") or RELATION_TYPE_Y),
                    "expr": str(item.get("expr") or ""),
                    "expr_y": str(item.get("expr_y") or ""),
                    "enabled": bool(item.get("enabled")),
                    "style": str(item.get("style") or STYLE_NORMAL),
                    "range_start": str(item.get("range_start") or ""),
                    "range_end": str(item.get("range_end") or ""),
                }
            )
        else:
            out.append(default_relation(idx))
    return out


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return float(fallback)


EVAL_GLOBALS = {
    "__builtins__": {},
    "abs": abs,
    "min": min,
    "max": max,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "asinh": getattr(math, "asinh", None),
    "acosh": getattr(math, "acosh", None),
    "atanh": getattr(math, "atanh", None),
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "pow": math.pow,
    "floor": math.floor,
    "ceil": math.ceil,
    "radians": math.radians,
    "degrees": math.degrees,
    "pi": math.pi,
    "e": math.e,
}
for _name in ("asinh", "acosh", "atanh"):
    if EVAL_GLOBALS.get(_name) is None:
        del EVAL_GLOBALS[_name]


def _clean_expr(value):
    return str(value or "").strip()


def _eval_number(text_value):
    value = eval(str(text_value or "0"), EVAL_GLOBALS)
    if isinstance(value, complex):
        raise ValueError("complex value not supported")
    return float(value)


def _make_eval_fn(expression, variable_name):
    expression = _clean_expr(expression)
    if not expression:
        return None

    try:
        compiled = compile(expression, "<graph_expr>", "eval")
    except Exception:
        return None

    def _eval_value(value, extra=None):
        env = {}
        env.update(EVAL_GLOBALS)
        env[variable_name] = value
        if extra:
            for key, val in extra.items():
                env[key] = val
        return eval(compiled, env)

    return _eval_value


def _get_relation_eval_fn(session, relation_index, cache_name, expression, variable_name):
    cache = session.eval_cache[relation_index]
    expr_key = cache_name + "_expr"
    fn_key = cache_name + "_fn"
    expression = _clean_expr(expression)
    if cache.get(expr_key) != expression:
        cache[expr_key] = expression
        cache[fn_key] = _make_eval_fn(expression, variable_name)
    return cache.get(fn_key)


def _safe_eval(fn, value, extra=None):
    if fn is None:
        return None
    try:
        result = fn(value, extra)
        if isinstance(result, complex):
            return None
        if result != result:
            return None
        if result > EVAL_ABS_CLAMP or result < -EVAL_ABS_CLAMP:
            return None
        return float(result)
    except Exception:
        return None


class MediumDigits:
    data = {
        " ": [0x00, 0x00, 0x00, 0x00, 0x00],
        "0": [0x3E, 0x51, 0x49, 0x45, 0x3E],
        "1": [0x00, 0x42, 0x7F, 0x40, 0x00],
        "2": [0x42, 0x61, 0x51, 0x49, 0x46],
        "3": [0x21, 0x41, 0x45, 0x4B, 0x31],
        "4": [0x18, 0x14, 0x12, 0x7F, 0x10],
        "5": [0x27, 0x45, 0x45, 0x45, 0x39],
        "6": [0x3C, 0x4A, 0x49, 0x49, 0x30],
        "7": [0x01, 0x71, 0x09, 0x05, 0x03],
        "8": [0x36, 0x49, 0x49, 0x49, 0x36],
        "9": [0x06, 0x49, 0x49, 0x29, 0x1E],
        ".": [0x00, 0x60, 0x60, 0x00, 0x00],
        "-": [0x08, 0x08, 0x08, 0x08, 0x08],
        "=": [0x14, 0x14, 0x14, 0x14, 0x14],
        "x": [0x44, 0x28, 0x10, 0x28, 0x44],
        "y": [0x0C, 0x50, 0x50, 0x50, 0x3C],
        "m": [0x7C, 0x08, 0x10, 0x08, 0x78],
        "A": [0x7E, 0x09, 0x09, 0x09, 0x7E],
        "T": [0x01, 0x01, 0x7F, 0x01, 0x01],
        "N": [0x7F, 0x04, 0x08, 0x10, 0x7F],
        "V": [0x1F, 0x20, 0x40, 0x20, 0x1F],
        "H": [0x7F, 0x08, 0x08, 0x08, 0x7F],
        "u": [0x3C, 0x40, 0x40, 0x20, 0x7C],
        "n": [0x7C, 0x08, 0x04, 0x04, 0x78],
        "d": [0x38, 0x44, 0x44, 0x44, 0x7F],
        "e": [0x38, 0x54, 0x54, 0x54, 0x18],
        "f": [0x08, 0x7E, 0x09, 0x01, 0x02],
    }

    @classmethod
    def get_char(cls, char):
        return cls.data.get(char, cls.data[" "])


def draw_medium_text(fb, text_value, x, y):
    for char in str(text_value):
        data = MediumDigits.get_char(char)
        for col in range(5):
            bits = data[col]
            for row in range(7):
                if bits & (1 << row):
                    fb.pixel(x + col, y + row, 1)
        x += 6


def _format_short(value, digits=3):
    try:
        value = float(value)
    except Exception:
        return "undef"
    abs_v = abs(value)
    if abs_v < 0.001:
        return "0"
    if abs_v < 10:
        return str(round(value, digits))
    if abs_v < 1000:
        return str(round(value, 2))
    return "{:.3g}".format(value)


def _format_status_value(prefix, value):
    if value is None:
        return prefix + "=undef"
    return prefix + "=" + _format_short(value)


def format_number(value):
    try:
        value = float(value)
    except Exception:
        return "0 "
    pi_multiple = value / math.pi
    if abs(pi_multiple - round(pi_multiple)) < 0.001:
        multiple = int(round(pi_multiple))
        if multiple == 0:
            return "0 "
        if multiple == 1:
            return "pi "
        if multiple == -1:
            return "-pi "
        return str(multiple) + "*pi "
    abs_v = abs(value)
    if abs_v < 0.01:
        return "0 "
    if abs_v < 100:
        return str(round(value, 2)) + " "
    if abs_v < 100000:
        return str(int(value)) + " "
    return "{:.3g} ".format(value)


class CursorState:
    def __init__(self):
        self.active = False
        self.x_pixel = DISPLAY_WIDTH // 2
        self.prev_x_pixel = self.x_pixel
        self.graph_index = 0

    def toggle(self):
        self.active = not self.active
        self.prev_x_pixel = self.x_pixel

    def move(self, delta):
        self.prev_x_pixel = self.x_pixel
        next_value = _clamp(self.x_pixel + delta, 0, DISPLAY_WIDTH - 1)
        changed = next_value != self.x_pixel
        self.x_pixel = next_value
        return changed


class ToolFeature:
    def __init__(self, mode, instance_number, graph_index):
        self.mode = mode
        self.instance_number = instance_number
        self.graph_index = graph_index
        self.area_x_left = 0.0
        self.area_x_right = 0.0
        self.area_focus = "right"
        self.single_x = 0.0
        self.constant = 0.0

    def focused_x_value(self):
        if self.mode == TOOL_AREA:
            if self.area_focus == "left":
                return self.area_x_left
            return self.area_x_right
        return self.single_x

    def area_interval(self):
        if self.area_x_left <= self.area_x_right:
            return self.area_x_left, self.area_x_right
        return self.area_x_right, self.area_x_left


class ToolState:
    def __init__(self):
        self.features = []
        self.selected_index = None
        self._counters = {
            TOOL_AREA: 0,
            TOOL_TANGENT: 0,
            TOOL_NORMAL: 0,
            TOOL_VERTICAL: 0,
            TOOL_HORIZONTAL: 0,
        }

    @property
    def active(self):
        return len(self.features) > 0

    def selected_feature(self):
        if self.selected_index is None:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.features):
            return None
        return self.features[self.selected_index]

    def add_feature(self, mode, graph_index, x_value):
        count = self._counters.get(mode, 0) + 1
        self._counters[mode] = count
        feature = ToolFeature(mode, count, graph_index)
        if mode == TOOL_AREA:
            feature.area_x_left = x_value - 1.0
            feature.area_x_right = x_value + 1.0
            feature.area_focus = "right"
        else:
            feature.single_x = x_value
        self.features.append(feature)
        self.selected_index = len(self.features) - 1
        return feature

    def remove_index(self, index):
        if index < 0 or index >= len(self.features):
            return False
        del self.features[index]
        if not self.features:
            self.selected_index = None
            return True
        if self.selected_index is None:
            self.selected_index = 0
            return True
        if self.selected_index >= len(self.features):
            self.selected_index = len(self.features) - 1
        return True


class GraphSuiteState:
    def __init__(self):
        self.relations = _ensure_relations(None)
        self.bounds = default_bounds()
        self.previous_bounds = _copy_bounds(self.bounds)
        self.initial_bounds = _copy_bounds(self.bounds)
        self.vwindow_memories = [_copy_bounds(self.bounds) for _ in range(MAX_VWINDOWS)]
        self.graph_memories = [None] * MAX_GRAPH_MEMORIES
        self.picture_memories = [None] * MAX_PICTURE_MEMORIES
        self.current_relation = 0
        self.cursor = CursorState()
        self.tool_state = ToolState()
        self.current_graph_samples = {}
        self.status_message = "Graph ready"
        self.status_until_ms = None
        self.show_grid = False
        self.show_axes = True
        self.show_labels = False
        self.show_coords = True
        self.show_derivative = True
        self.inequality_mode = "AND"
        self.fb_buf = bytearray((DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8)
        self.plot_cache_buf = bytearray(len(self.fb_buf))
        self.fb = framebuf.FrameBuffer(
            self.fb_buf,
            DISPLAY_WIDTH,
            DISPLAY_HEIGHT,
            framebuf.MONO_VLSB,
        )
        self.eval_cache = [{} for _ in range(MAX_RELATIONS)]
        self.fast_render = {
            "enabled": False,
            "relation_index": None,
            "eval_fn": None,
        }
        self.table_rows = []
        self.table_headers = []
        self.table_title = "Table"
        self.dynamic_config = {
            "relation_index": 0,
            "parameter": "A",
            "start": 1.0,
            "end": 4.0,
            "step": 1.0,
            "locus": False,
            "speed_ms": 220,
        }
        self.recur_config = {
            "type": RECUR_TYPE_TWO,
            "expr_a": "2*a+1",
            "expr_b": "",
            "start_n": 1,
            "end_n": 8,
            "a1": 1.0,
            "a2": 1.0,
            "graph_style": "line",
            "phase": False,
        }
        self.conic_config = {
            "type": CONIC_CIRCLE,
            "h": 0.0,
            "k": 0.0,
            "a": 2.0,
            "b": 1.0,
            "p": 1.0,
        }
        self.load()

    def set_status(self, message, duration_ms=2200):
        self.status_message = str(message or "")
        if duration_ms is None:
            self.status_until_ms = None
        else:
            self.status_until_ms = _ticks_add(_ticks_ms(), int(duration_ms))

    def status_text(self):
        if self.status_until_ms is not None and _ticks_diff(self.status_until_ms, _ticks_ms()) <= 0:
            self.status_until_ms = None
            self.status_message = ""
        return self.status_message

    def relation(self, index=None):
        if index is None:
            index = self.current_relation
        return self.relations[index]

    def enabled_relation_indices(self):
        out = []
        for idx, relation in enumerate(self.relations):
            if relation["enabled"] and relation["expr"]:
                out.append(idx)
        return out

    def serialize(self):
        pictures = []
        for picture in self.picture_memories:
            if picture is None:
                pictures.append(None)
            else:
                pictures.append(picture.hex())
        return {
            "relations": self.relations,
            "bounds": self.bounds,
            "current_relation": self.current_relation,
            "vwindow_memories": self.vwindow_memories,
            "graph_memories": self.graph_memories,
            "picture_memories": pictures,
            "appearance": {
                "grid": self.show_grid,
                "axes": self.show_axes,
                "labels": self.show_labels,
                "coords": self.show_coords,
                "derivative": self.show_derivative,
                "ineq": self.inequality_mode,
            },
            "dynamic_config": self.dynamic_config,
            "recur_config": self.recur_config,
            "conic_config": self.conic_config,
        }

    def load(self):
        try:
            with open(GRAPH_STATE_PATH, "r") as fh:
                data = json.load(fh)
        except Exception:
            return

        self.relations = _ensure_relations(data.get("relations"))
        bounds = data.get("bounds") or {}
        merged = default_bounds()
        for key, value in bounds.items():
            merged[key] = _safe_float(value, merged.get(key, 0.0))
        self.bounds = merged
        self.initial_bounds = _copy_bounds(self.bounds)
        self.previous_bounds = _copy_bounds(self.bounds)

        self.current_relation = int(data.get("current_relation", 0))
        if self.current_relation < 0 or self.current_relation >= MAX_RELATIONS:
            self.current_relation = 0

        memories = data.get("vwindow_memories") or []
        self.vwindow_memories = []
        for idx in range(MAX_VWINDOWS):
            if idx < len(memories):
                self.vwindow_memories.append(_copy_bounds(memories[idx]))
            else:
                self.vwindow_memories.append(_copy_bounds(self.bounds))

        self.graph_memories = data.get("graph_memories") or [None] * MAX_GRAPH_MEMORIES
        if len(self.graph_memories) < MAX_GRAPH_MEMORIES:
            self.graph_memories.extend([None] * (MAX_GRAPH_MEMORIES - len(self.graph_memories)))
        self.graph_memories = self.graph_memories[:MAX_GRAPH_MEMORIES]

        pictures = data.get("picture_memories") or []
        self.picture_memories = [None] * MAX_PICTURE_MEMORIES
        for idx in range(min(MAX_PICTURE_MEMORIES, len(pictures))):
            item = pictures[idx]
            if item is None:
                self.picture_memories[idx] = None
            else:
                try:
                    self.picture_memories[idx] = bytes.fromhex(item)
                except Exception:
                    self.picture_memories[idx] = None

        appearance = data.get("appearance") or {}
        self.show_grid = bool(appearance.get("grid", False))
        self.show_axes = bool(appearance.get("axes", True))
        self.show_labels = bool(appearance.get("labels", False))
        self.show_coords = bool(appearance.get("coords", True))
        self.show_derivative = bool(appearance.get("derivative", True))
        self.inequality_mode = str(appearance.get("ineq", "AND") or "AND")

        self.dynamic_config.update(data.get("dynamic_config") or {})
        self.recur_config.update(data.get("recur_config") or {})
        self.conic_config.update(data.get("conic_config") or {})

    def save(self):
        try:
            with open(GRAPH_STATE_PATH, "w") as fh:
                json.dump(self.serialize(), fh)
        except Exception:
            pass


SESSION = GraphSuiteState()


def _display_full_raw(fb_buf):
    display.graphics(fb_buf, page=0, column=0, width=DISPLAY_WIDTH, pages=DISPLAY_PAGES)


def _display_page_raw(fb_buf, page_index):
    start = page_index * DISPLAY_WIDTH
    end = start + DISPLAY_WIDTH
    display.graphics(memoryview(fb_buf)[start:end], page=page_index, column=0, width=DISPLAY_WIDTH, pages=1)


def _refresh_nav_overlay(fb_buf):
    overlay_state = nav.current_state()
    nav.set_restore_callback(
        (lambda: _display_page_raw(fb_buf, BOTTOM_PAGE_INDEX)) if overlay_state else None
    )
    if overlay_state:
        nav.draw_state(overlay_state)


def _display_full(fb_buf):
    _display_full_raw(fb_buf)
    _refresh_nav_overlay(fb_buf)


def _display_page(fb_buf, page_index):
    _display_page_raw(fb_buf, page_index)
    if page_index == BOTTOM_PAGE_INDEX:
        _refresh_nav_overlay(fb_buf)


def _display_plot_column(fb_buf, x_pixel, out_col_buf):
    if x_pixel < 0 or x_pixel >= DISPLAY_WIDTH:
        return
    idx = x_pixel
    for page in range(PLOT_PAGES):
        out_col_buf[page] = fb_buf[idx]
        idx += DISPLAY_WIDTH
    display.graphics(out_col_buf, page=0, column=x_pixel, width=1, pages=PLOT_PAGES)


def _x_pixel_to_value(x_pixel, bounds):
    x_range = bounds["x_max"] - bounds["x_min"]
    if DISPLAY_WIDTH < 2:
        return bounds["x_min"]
    return bounds["x_min"] + (x_pixel / (DISPLAY_WIDTH - 1)) * x_range


def _y_pixel_to_value(y_pixel, bounds, plot_height=PLOT_HEIGHT):
    y_range = bounds["y_max"] - bounds["y_min"]
    if plot_height < 2:
        return bounds["y_max"]
    return bounds["y_max"] - (y_pixel / (plot_height - 1)) * y_range


def _x_value_to_pixel(x_value, bounds, clamp=False):
    x_range = bounds["x_max"] - bounds["x_min"]
    if DISPLAY_WIDTH < 2 or x_range == 0:
        return 0 if clamp else None
    x_pos = ((x_value - bounds["x_min"]) / x_range) * (DISPLAY_WIDTH - 1)
    x_px = int(x_pos + 0.5)
    if clamp:
        return _clamp(x_px, 0, DISPLAY_WIDTH - 1)
    if x_px < 0 or x_px >= DISPLAY_WIDTH:
        return None
    return x_px


def _y_value_to_pixel(y_value, bounds, plot_height=PLOT_HEIGHT, clamp=False):
    y_range = bounds["y_max"] - bounds["y_min"]
    if plot_height < 2 or y_range == 0:
        return 0 if clamp else None
    y_pos = ((bounds["y_max"] - y_value) / y_range) * (plot_height - 1)
    y_px = int(y_pos + 0.5)
    if clamp:
        return _clamp(y_px, 0, plot_height - 1)
    if y_px < 0 or y_px >= plot_height:
        return None
    return y_px


def _x_step_for_one_pixel(bounds):
    if DISPLAY_WIDTH < 2:
        return 0.0
    return (bounds["x_max"] - bounds["x_min"]) / (DISPLAY_WIDTH - 1)


def _samples_per_px_for_view(x_range):
    if DISPLAY_WIDTH < 2:
        return 1
    units_per_px = abs(x_range) / (DISPLAY_WIDTH - 1)
    if units_per_px <= 0.03:
        return 6
    if units_per_px <= 0.08:
        return 5
    if units_per_px <= 0.20:
        return 4
    if units_per_px <= 0.60:
        return 3
    if units_per_px <= 1.5:
        return 2
    return 1


def _can_use_fast_single_y(session, relation_index, relation, draw_features, extra, prefer_fast):
    if not prefer_fast or extra is not None:
        return False
    if len(session.enabled_relation_indices()) != 1:
        return False
    if relation_index != session.enabled_relation_indices()[0]:
        return False
    if relation["type"] != RELATION_TYPE_Y:
        return False
    if relation["style"] != STYLE_NORMAL:
        return False
    if relation["range_start"] or relation["range_end"]:
        return False
    if draw_features and session.tool_state.active:
        return False
    return True


def _estimate_derivative_fast(eval_fn, x_value, bounds):
    x_step = _x_step_for_one_pixel(bounds)
    if x_step == 0:
        return None
    h = abs(x_step) * 0.5
    if h < 1e-6:
        h = 1e-6
    left = _safe_eval(eval_fn, x_value - h)
    right = _safe_eval(eval_fn, x_value + h)
    if left is None or right is None:
        return None
    return (right - left) / (2.0 * h)


def _plot_single_y_fast(session, relation_index, eval_fn):
    bounds = session.bounds
    x_min = bounds["x_min"]
    x_max = bounds["x_max"]
    y_min = bounds["y_min"]
    y_max = bounds["y_max"]

    if DISPLAY_WIDTH < 2 or PLOT_HEIGHT < 2:
        return False

    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range == 0 or y_range == 0:
        return False

    x_scale = x_range / (DISPLAY_WIDTH - 1)
    y_scale = y_range / (PLOT_HEIGHT - 1)
    inv_y_scale = 1.0 / y_scale

    spp = _samples_per_px_for_view(x_range)
    if spp < SAMPLES_PER_PX_MIN:
        spp = SAMPLES_PER_PX_MIN
    if spp > SAMPLES_PER_PX_MAX:
        spp = SAMPLES_PER_PX_MAX

    pixel = session.fb.pixel
    line = session.fb.line if hasattr(session.fb, "line") else None
    vline = session.fb.vline

    sample_step = x_scale / spp
    left_shift = x_scale * 0.5
    connect_limit = (PLOT_HEIGHT * 3) // 5
    steep_span_limit = (PLOT_HEIGHT * 3) // 4
    discontinuity_span_limit = (PLOT_HEIGHT * 5) // 6
    center_idx = spp >> 1

    prev_valid = False
    prev_steep = False
    prev_x = 0
    prev_y = 0

    for x_px in range(DISPLAY_WIDTH):
        x_center = x_min + (x_px * x_scale)
        x_left = x_center - left_shift

        col_min = PLOT_HEIGHT
        col_max = -1
        rep_y = -1
        valid_count = 0

        for sample_idx in range(spp):
            x_value = x_left + ((sample_idx + 0.5) * sample_step)
            y_value = _safe_eval(eval_fn, x_value)
            if y_value is None or y_value < y_min or y_value > y_max:
                continue

            y_px = int(((y_max - y_value) * inv_y_scale) + 0.5)
            if y_px < 0 or y_px >= PLOT_HEIGHT:
                continue

            valid_count += 1
            if y_px < col_min:
                col_min = y_px
            if y_px > col_max:
                col_max = y_px
            if sample_idx == center_idx:
                rep_y = y_px

        if col_max < 0:
            prev_valid = False
            prev_steep = False
            continue

        if rep_y < 0:
            rep_y = (col_min + col_max) >> 1

        col_span = col_max - col_min
        if col_span >= discontinuity_span_limit and valid_count <= (spp - 1):
            pixel(x_px, rep_y, 1)
            prev_valid = False
            prev_steep = True
            prev_x = x_px
            prev_y = rep_y
            continue

        if col_min == col_max:
            pixel(x_px, col_min, 1)
        else:
            vline(x_px, col_min, col_max - col_min + 1, 1)

        is_steep = col_span > steep_span_limit

        if prev_valid and (not prev_steep) and (not is_steep):
            if abs(rep_y - prev_y) <= connect_limit:
                if line is not None:
                    line(prev_x, prev_y, x_px, rep_y, 1)
                else:
                    _styled_line(session.fb, prev_x, prev_y, x_px, rep_y, STYLE_NORMAL)

        prev_valid = True
        prev_steep = is_steep
        prev_x = x_px
        prev_y = rep_y

    session.current_graph_samples[relation_index] = []
    return True


def _fast_cursor_values(session):
    if not session.fast_render["enabled"]:
        return None
    relation_index = session.fast_render["relation_index"]
    if relation_index is None or session.cursor.graph_index != relation_index:
        return None
    eval_fn = session.fast_render["eval_fn"]
    if eval_fn is None:
        return None
    x_value = _x_pixel_to_value(session.cursor.x_pixel, session.bounds)
    y_value = _safe_eval(eval_fn, x_value)
    slope = None
    if session.show_derivative and y_value is not None:
        slope = _estimate_derivative_fast(eval_fn, x_value, session.bounds)
    y_px = None
    if y_value is not None:
        y_px = _y_value_to_pixel(y_value, session.bounds, clamp=False)
    return {
        "relation_index": relation_index,
        "x": x_value,
        "y": y_value,
        "y_px": y_px,
        "m": slope,
    }


def _draw_status_bar(session, extra_text=None):
    session.fb.fill_rect(0, PLOT_HEIGHT, DISPLAY_WIDTH, DISPLAY_HEIGHT - PLOT_HEIGHT, 0)
    status = extra_text
    if status is None or status == "":
        status = _status_line(session)
    draw_medium_text(session.fb, status[:21], 1, PLOT_HEIGHT + 1)


def _draw_axes_and_grid(session):
    fb = session.fb
    bounds = session.bounds
    x_min = bounds["x_min"]
    x_max = bounds["x_max"]
    y_min = bounds["y_min"]
    y_max = bounds["y_max"]
    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range == 0 or y_range == 0:
        return

    if session.show_grid:
        x_scale = abs(bounds.get("x_scale", 1.0))
        y_scale = abs(bounds.get("y_scale", 1.0))
        if x_scale > 0:
            grid_x = math.floor(x_min / x_scale) * x_scale
            count = 0
            while grid_x <= x_max and count < 256:
                x_px = _x_value_to_pixel(grid_x, bounds, clamp=False)
                if x_px is not None:
                    for y_px in range(0, PLOT_HEIGHT, 2):
                        fb.pixel(x_px, y_px, 1)
                grid_x += x_scale
                count += 1
        if y_scale > 0:
            grid_y = math.floor(y_min / y_scale) * y_scale
            count = 0
            while grid_y <= y_max and count < 256:
                y_px = _y_value_to_pixel(grid_y, bounds, clamp=False)
                if y_px is not None:
                    for x_px in range(0, DISPLAY_WIDTH, 2):
                        fb.pixel(x_px, y_px, 1)
                grid_y += y_scale
                count += 1

    if session.show_axes:
        if y_min <= 0 <= y_max:
            y_axis = _y_value_to_pixel(0.0, bounds, clamp=False)
            if y_axis is not None:
                fb.hline(0, y_axis, DISPLAY_WIDTH, 1)
        if x_min <= 0 <= x_max:
            x_axis = _x_value_to_pixel(0.0, bounds, clamp=False)
            if x_axis is not None:
                fb.vline(x_axis, 0, PLOT_HEIGHT, 1)

    if session.show_labels:
        if x_min <= 0 <= x_max:
            x_axis = _x_value_to_pixel(0.0, bounds, clamp=False)
            if x_axis is not None and x_axis < DISPLAY_WIDTH - 8:
                session.fb.text("y", x_axis + 1, 0, 1)
        if y_min <= 0 <= y_max:
            y_axis = _y_value_to_pixel(0.0, bounds, clamp=False)
            if y_axis is not None and y_axis > 7:
                session.fb.text("x", DISPLAY_WIDTH - 7, y_axis - 7, 1)


def _styled_point(fb, x_px, y_px, style, seed):
    if x_px < 0 or x_px >= DISPLAY_WIDTH or y_px < 0 or y_px >= PLOT_HEIGHT:
        return
    if style == STYLE_DOT and (seed & 1):
        return
    fb.pixel(x_px, y_px, 1)
    if style == STYLE_THICK and x_px + 1 < DISPLAY_WIDTH:
        fb.pixel(x_px + 1, y_px, 1)
    elif style == STYLE_BROKEN and (seed % 4) < 2:
        if x_px + 1 < DISPLAY_WIDTH:
            fb.pixel(x_px + 1, y_px, 1)


def _styled_line(fb, x0, y0, x1, y1, style):
    if style == STYLE_NORMAL and hasattr(fb, "line"):
        fb.line(x0, y0, x1, y1, 1)
        return
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    steps = dx if dx > dy else dy
    if steps <= 0:
        _styled_point(fb, x0, y0, style, 0)
        return
    for idx in range(steps + 1):
        x_px = x0 + ((x1 - x0) * idx) // steps
        y_px = y0 + ((y1 - y0) * idx) // steps
        _styled_point(fb, x_px, y_px, style, idx)


def _draw_y_relation(session, relation, relation_index, eval_fn, extra=None):
    bounds = session.bounds
    x_min = bounds["x_min"]
    x_max = bounds["x_max"]
    y_min = bounds["y_min"]
    y_max = bounds["y_max"]
    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range == 0 or y_range == 0:
        return []

    samples = []
    spp = _samples_per_px_for_view(x_range)
    spp = _clamp(spp, SAMPLES_PER_PX_MIN, SAMPLES_PER_PX_MAX)
    x_scale = x_range / (DISPLAY_WIDTH - 1)
    step = x_scale / spp
    left_shift = x_scale * 0.5
    range_start_eval = _get_relation_eval_fn(session, relation_index, "range_start", relation["range_start"], "x")
    range_end_eval = _get_relation_eval_fn(session, relation_index, "range_end", relation["range_end"], "x")

    prev = None
    for x_px in range(DISPLAY_WIDTH):
        x_center = x_min + (x_px * x_scale)
        x_left = x_center - left_shift
        col_points = []
        for sample_idx in range(spp):
            x_value = x_left + ((sample_idx + 0.5) * step)
            if range_start_eval is not None:
                start_value = _safe_eval(range_start_eval, x_value, extra)
                if start_value is not None and x_value < start_value:
                    continue
            if range_end_eval is not None:
                end_value = _safe_eval(range_end_eval, x_value, extra)
                if end_value is not None and x_value > end_value:
                    continue
            y_value = _safe_eval(eval_fn, x_value, extra)
            if y_value is None:
                continue
            y_px = _y_value_to_pixel(y_value, bounds, clamp=False)
            if y_px is None:
                continue
            col_points.append((x_value, y_value, y_px))
        if not col_points:
            prev = None
            continue
        rep = col_points[len(col_points) // 2]
        samples.append({"x_px": x_px, "x": rep[0], "y": rep[1], "y_px": rep[2], "relation_index": relation_index})
        top = col_points[0][2]
        bottom = col_points[0][2]
        for _, _, y_px in col_points[1:]:
            if y_px < top:
                top = y_px
            elif y_px > bottom:
                bottom = y_px
        if top == bottom:
            _styled_point(session.fb, x_px, top, relation["style"], x_px)
        elif relation["style"] == STYLE_NORMAL:
            session.fb.vline(x_px, top, bottom - top + 1, 1)
        else:
            for y_px in range(top, bottom + 1):
                _styled_point(session.fb, x_px, y_px, relation["style"], x_px + y_px)
        if prev is not None:
            if abs(rep[2] - prev[1]) <= (PLOT_HEIGHT * 3) // 5:
                _styled_line(session.fb, prev[0], prev[1], x_px, rep[2], relation["style"])
        prev = (x_px, rep[2])
    return samples


def _draw_x_relation(session, relation, relation_index, eval_fn, extra=None):
    bounds = session.bounds
    y_min = bounds["y_min"]
    y_max = bounds["y_max"]
    y_range = y_max - y_min
    if y_range == 0:
        return []
    samples = []
    step = y_range / (PLOT_HEIGHT * 2.0)
    if step == 0:
        step = 0.1
    prev = None
    idx = 0
    y_value = y_min
    while y_value <= y_max:
        x_value = _safe_eval(eval_fn, y_value, extra)
        if x_value is not None:
            x_px = _x_value_to_pixel(x_value, bounds, clamp=False)
            y_px = _y_value_to_pixel(y_value, bounds, clamp=False)
            if x_px is not None and y_px is not None:
                samples.append({"x_px": x_px, "x": x_value, "y": y_value, "y_px": y_px, "relation_index": relation_index})
                _styled_point(session.fb, x_px, y_px, relation["style"], idx)
                if prev is not None and abs(y_px - prev[1]) < (PLOT_HEIGHT * 3) // 5:
                    _styled_line(session.fb, prev[0], prev[1], x_px, y_px, relation["style"])
                prev = (x_px, y_px)
        y_value += step
        idx += 1
    return samples


def _draw_param_relation(session, relation, relation_index, eval_x, eval_y, extra=None):
    bounds = session.bounds
    t_min = bounds.get("t_min", DEFAULT_T_MIN)
    t_max = bounds.get("t_max", DEFAULT_T_MAX)
    t_step = abs(bounds.get("t_step", DEFAULT_T_STEP))
    if t_step <= 0:
        t_step = DEFAULT_T_STEP
    if t_max < t_min:
        t_step = -t_step
    samples = []
    prev = None
    index = 0
    t_value = t_min
    limit = 0
    while (t_value <= t_max and t_step > 0) or (t_value >= t_max and t_step < 0):
        x_value = _safe_eval(eval_x, t_value, extra)
        y_value = _safe_eval(eval_y, t_value, extra)
        if x_value is not None and y_value is not None:
            x_px = _x_value_to_pixel(x_value, bounds, clamp=False)
            y_px = _y_value_to_pixel(y_value, bounds, clamp=False)
            if x_px is not None and y_px is not None:
                samples.append({"x_px": x_px, "x": x_value, "y": y_value, "y_px": y_px, "relation_index": relation_index})
                _styled_point(session.fb, x_px, y_px, relation["style"], index)
                if prev is not None:
                    _styled_line(session.fb, prev[0], prev[1], x_px, y_px, relation["style"])
                prev = (x_px, y_px)
        t_value += t_step
        index += 1
        limit += 1
        if limit > 3000:
            break
    return samples


def _draw_polar_relation(session, relation, relation_index, eval_r, extra=None):
    def _eval_x(theta_value, extra_inner):
        radius = _safe_eval(eval_r, theta_value, extra_inner)
        if radius is None:
            return None
        return radius * math.cos(theta_value)

    def _eval_y(theta_value, extra_inner):
        radius = _safe_eval(eval_r, theta_value, extra_inner)
        if radius is None:
            return None
        return radius * math.sin(theta_value)

    return _draw_param_relation(session, relation, relation_index, _eval_x, _eval_y, extra)


def _fill_y_inequality(session, relation, eval_fn, relation_index, mode):
    bounds = session.bounds
    samples = _draw_y_relation(session, relation, relation_index, eval_fn)
    for point in samples:
        x_px = point["x_px"]
        y_px = point["y_px"]
        if relation["type"] in (RELATION_TYPE_Y_GT, RELATION_TYPE_Y_GE):
            top = 0
            bottom = y_px
        else:
            top = y_px
            bottom = PLOT_HEIGHT - 1
        step = 1 if mode == "OR" else 2
        for draw_y in range(top, bottom + 1, step):
            session.fb.pixel(x_px, draw_y, 1)
    return samples


def _fill_x_inequality(session, relation, eval_fn, relation_index, mode):
    bounds = session.bounds
    samples = _draw_x_relation(session, relation, relation_index, eval_fn)
    for point in samples:
        x_px = point["x_px"]
        y_px = point["y_px"]
        if relation["type"] in (RELATION_TYPE_X_GT, RELATION_TYPE_X_GE):
            left = x_px
            right = DISPLAY_WIDTH - 1
        else:
            left = 0
            right = x_px
        step = 1 if mode == "OR" else 2
        for draw_x in range(left, right + 1, step):
            session.fb.pixel(draw_x, y_px, 1)
    return samples


def _relation_label(index, relation):
    relation_type = relation["type"]
    if relation_type == RELATION_TYPE_PARAM:
        return "Pt" + str(index + 1)
    return relation_type + str(index + 1)


def _build_relation_summary(index, relation):
    label = _relation_label(index, relation)
    marker = "*" if relation["enabled"] and relation["expr"] else "-"
    expr = relation["expr"]
    if relation["type"] == RELATION_TYPE_PARAM:
        expr = relation["expr"] + "," + relation["expr_y"]
    if not expr:
        expr = "<empty>"
    return (marker + " " + label + " " + expr)[:21]


def _nearest_sample(samples, x_pixel):
    if not samples:
        return None
    best = samples[0]
    best_dist = abs(best["x_px"] - x_pixel)
    for item in samples[1:]:
        dist = abs(item["x_px"] - x_pixel)
        if dist < best_dist:
            best = item
            best_dist = dist
    return best


def _selected_relation_sample(session):
    relation_index = session.cursor.graph_index
    samples = session.current_graph_samples.get(relation_index) or []
    return _nearest_sample(samples, session.cursor.x_pixel)


def _estimate_slope(samples, x_pixel):
    if not samples or len(samples) < 3:
        return None
    center = _nearest_sample(samples, x_pixel)
    if center is None:
        return None
    idx = samples.index(center)
    left = samples[idx - 1] if idx > 0 else None
    right = samples[idx + 1] if idx + 1 < len(samples) else None
    if left is None or right is None:
        return None
    dx = right["x"] - left["x"]
    if dx == 0:
        return None
    return (right["y"] - left["y"]) / dx


def _status_line(session):
    relation = session.relation(session.cursor.graph_index if session.cursor.active else session.current_relation)
    label = _relation_label(session.cursor.graph_index if session.cursor.active else session.current_relation, relation)
    if session.cursor.active:
        fast_values = _fast_cursor_values(session)
        if fast_values is not None:
            status = label + " " + _format_status_value("x", fast_values["x"]) + " " + _format_status_value("y", fast_values["y"])
            if session.show_derivative and fast_values["m"] is not None:
                status = status + " " + _format_status_value("m", fast_values["m"])
            return status[:21]
        sample = _selected_relation_sample(session)
        if sample is not None:
            status = label + " " + _format_status_value("x", sample["x"]) + " " + _format_status_value("y", sample["y"])
            if session.show_derivative:
                slope = _estimate_slope(session.current_graph_samples.get(sample["relation_index"]), session.cursor.x_pixel)
                if slope is not None:
                    status = status + " " + _format_status_value("m", slope)
            return status[:21]
    if session.status_text():
        return session.status_text()[:21]
    return (label + " ready")[:21]


def _draw_cursor_overlay(session):
    if not session.cursor.active:
        return
    fast_values = _fast_cursor_values(session)
    if fast_values is not None:
        session.fb.vline(session.cursor.x_pixel, 0, PLOT_HEIGHT, 1)
        if fast_values["y_px"] is not None:
            x_px = session.cursor.x_pixel
            y_px = fast_values["y_px"]
            session.fb.hline(max(0, x_px - 1), y_px, min(3, DISPLAY_WIDTH - max(0, x_px - 1)), 1)
            session.fb.vline(x_px, max(0, y_px - 1), min(3, PLOT_HEIGHT - max(0, y_px - 1)), 1)
        return
    sample = _selected_relation_sample(session)
    if sample is None:
        return
    session.fb.vline(session.cursor.x_pixel, 0, PLOT_HEIGHT, 1)
    if sample["y_px"] is not None:
        x_px = session.cursor.x_pixel
        y_px = sample["y_px"]
        session.fb.hline(max(0, x_px - 1), y_px, min(3, DISPLAY_WIDTH - max(0, x_px - 1)), 1)
        session.fb.vline(x_px, max(0, y_px - 1), min(3, PLOT_HEIGHT - max(0, y_px - 1)), 1)


def _compute_area_value(samples, x0, x1):
    if not samples:
        return None
    if x1 < x0:
        x0, x1 = x1, x0
    points = []
    for item in samples:
        if item["x"] >= x0 and item["x"] <= x1:
            points.append(item)
    if len(points) < 2:
        return None
    area = 0.0
    prev = points[0]
    for item in points[1:]:
        area += (prev["y"] + item["y"]) * 0.5 * (item["x"] - prev["x"])
        prev = item
    return area


def _draw_tool_features(session):
    for feature in session.tool_state.features:
        samples = session.current_graph_samples.get(feature.graph_index) or []
        if not samples:
            continue
        relation = session.relations[feature.graph_index]
        if feature.mode == TOOL_AREA:
            left_px = _x_value_to_pixel(feature.area_x_left, session.bounds, clamp=True)
            right_px = _x_value_to_pixel(feature.area_x_right, session.bounds, clamp=True)
            for x_px in range(min(left_px, right_px), max(left_px, right_px) + 1, 2):
                sample = _nearest_sample(samples, x_px)
                if sample is None:
                    continue
                axis_y = _y_value_to_pixel(0.0, session.bounds, clamp=True)
                top = axis_y if axis_y < sample["y_px"] else sample["y_px"]
                height = abs(sample["y_px"] - axis_y) + 1
                session.fb.vline(x_px, top, height, 1)
            session.fb.vline(left_px, 0, PLOT_HEIGHT, 1)
            session.fb.vline(right_px, 0, PLOT_HEIGHT, 1)
        elif feature.mode == TOOL_VERTICAL:
            x_px = _x_value_to_pixel(feature.single_x, session.bounds, clamp=False)
            if x_px is not None:
                session.fb.vline(x_px, 0, PLOT_HEIGHT, 1)
        elif feature.mode == TOOL_HORIZONTAL:
            y_sample = _nearest_sample(samples, _x_value_to_pixel(feature.single_x, session.bounds, clamp=True))
            if y_sample is not None:
                session.fb.hline(0, y_sample["y_px"], DISPLAY_WIDTH, 1)
        else:
            sample = _nearest_sample(samples, _x_value_to_pixel(feature.single_x, session.bounds, clamp=True))
            if sample is None:
                continue
            slope = _estimate_slope(samples, sample["x_px"])
            if slope is None:
                continue
            if feature.mode == TOOL_NORMAL:
                if abs(slope) < 1e-9:
                    session.fb.vline(sample["x_px"], 0, PLOT_HEIGHT, 1)
                    continue
                slope = -1.0 / slope
            prev = None
            for x_px in range(DISPLAY_WIDTH):
                x_value = _x_pixel_to_value(x_px, session.bounds)
                y_value = sample["y"] + slope * (x_value - sample["x"])
                y_px = _y_value_to_pixel(y_value, session.bounds, clamp=False)
                if y_px is None:
                    prev = None
                    continue
                session.fb.pixel(x_px, y_px, 1)
                if prev is not None:
                    _styled_line(session.fb, prev[0], prev[1], x_px, y_px, STYLE_BROKEN)
                prev = (x_px, y_px)
            session.fb.hline(max(0, sample["x_px"] - 1), sample["y_px"], min(3, DISPLAY_WIDTH - max(0, sample["x_px"] - 1)), 1)
            session.fb.vline(sample["x_px"], max(0, sample["y_px"] - 1), min(3, PLOT_HEIGHT - max(0, sample["y_px"] - 1)), 1)


def _render_graph(session, extra=None, draw_features=True, custom_status=None, present=True, prefer_fast=True):
    session.fb.fill(0)
    _draw_axes_and_grid(session)
    session.current_graph_samples = {}
    session.fast_render["enabled"] = False
    session.fast_render["relation_index"] = None
    session.fast_render["eval_fn"] = None

    for relation_index in session.enabled_relation_indices():
        relation = session.relations[relation_index]
        relation_type = relation["type"]
        samples = []
        if relation_type in (RELATION_TYPE_Y, RELATION_TYPE_Y_GT, RELATION_TYPE_Y_LT, RELATION_TYPE_Y_GE, RELATION_TYPE_Y_LE):
            eval_fn = _get_relation_eval_fn(session, relation_index, "expr_x", relation["expr"], "x")
            if relation_type == RELATION_TYPE_Y and _can_use_fast_single_y(session, relation_index, relation, draw_features, extra, prefer_fast):
                _plot_single_y_fast(session, relation_index, eval_fn)
                session.fast_render["enabled"] = True
                session.fast_render["relation_index"] = relation_index
                session.fast_render["eval_fn"] = eval_fn
                samples = session.current_graph_samples.get(relation_index) or []
            elif relation_type == RELATION_TYPE_Y:
                samples = _draw_y_relation(session, relation, relation_index, eval_fn, extra)
            else:
                samples = _fill_y_inequality(session, relation, eval_fn, relation_index, session.inequality_mode)
        elif relation_type in (RELATION_TYPE_X, RELATION_TYPE_X_GT, RELATION_TYPE_X_LT, RELATION_TYPE_X_GE, RELATION_TYPE_X_LE):
            eval_fn = _get_relation_eval_fn(session, relation_index, "expr_y", relation["expr"], "y")
            if relation_type == RELATION_TYPE_X:
                samples = _draw_x_relation(session, relation, relation_index, eval_fn, extra)
            else:
                samples = _fill_x_inequality(session, relation, eval_fn, relation_index, session.inequality_mode)
        elif relation_type == RELATION_TYPE_PARAM:
            eval_x = _get_relation_eval_fn(session, relation_index, "expr_t_x", relation["expr"], "t")
            eval_y = _get_relation_eval_fn(session, relation_index, "expr_t_y", relation["expr_y"], "t")
            samples = _draw_param_relation(session, relation, relation_index, eval_x, eval_y, extra)
        elif relation_type == RELATION_TYPE_R:
            eval_r = _get_relation_eval_fn(session, relation_index, "expr_t_r", relation["expr"], "t")
            samples = _draw_polar_relation(session, relation, relation_index, eval_r, extra)
        session.current_graph_samples[relation_index] = samples

    if draw_features:
        _draw_tool_features(session)
    session.plot_cache_buf[:] = session.fb_buf

    _draw_cursor_overlay(session)

    _draw_status_bar(session, custom_status)
    if present:
        _display_full(session.fb_buf)


def _ensure_analysis_samples(session):
    if session.fast_render["enabled"]:
        _render_graph(session, present=False, prefer_fast=False)


def _refresh_overlay(session, custom_status=None):
    session.fb_buf[:] = session.plot_cache_buf
    _draw_cursor_overlay(session)
    _draw_status_bar(session, custom_status)
    if session.cursor.active:
        _display_plot_column(session.fb_buf, session.cursor.prev_x_pixel, _CURSOR_COL_BUF_A)
        if session.cursor.x_pixel != session.cursor.prev_x_pixel:
            _display_plot_column(session.fb_buf, session.cursor.x_pixel, _CURSOR_COL_BUF_B)
    _display_page(session.fb_buf, BOTTOM_PAGE_INDEX)


def _relation_menu_items():
    items = []
    for idx in range(MAX_RELATIONS):
        items.append(_build_relation_summary(idx, SESSION.relations[idx]))
    return items


def _open_simple_menu(title, items, footer="OK=select"):
    fb_buf = bytearray((DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8)
    fb = framebuf.FrameBuffer(fb_buf, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_VLSB)
    selected = 0
    top = 0
    visible_rows = 3
    while True:
        fb.fill(0)
        fb.text(str(title)[:20], 0, 0, 1)
        total = len(items)
        if total:
            if selected < top:
                top = selected
            elif selected >= top + visible_rows:
                top = selected - visible_rows + 1
        for row in range(visible_rows):
            idx = top + row
            if idx >= total:
                break
            y_pos = 15 + row * 13
            prefix = ">" if idx == selected else " "
            fb.text((prefix + str(items[idx]))[:21], 0, y_pos, 1)
        fb.text(str(footer)[:21], 0, 56, 1)
        _display_full(fb_buf)

        key = typer.start_typing()
        if key == "nav_u" and items:
            selected = (selected - 1) % len(items)
        elif key == "nav_d" and items:
            selected = (selected + 1) % len(items)
        elif key in ("ok", "exe") and items:
            return selected
        elif key in ("toolbox", "nav_b", "AC"):
            return None
        elif key in ("alpha", "beta"):
            keypad_state_manager(x=key)


def _run_form(title, field_specs, initial_values=None, footer="OK=save"):
    initial_values = initial_values or {}
    input_list = {}
    form_list = [str(title)]
    for index, spec in enumerate(field_specs):
        key = "inp_" + str(index)
        input_list[key] = str(initial_values.get(spec[0], spec[1])) + " "
        form_list.append(str(spec[0]))
        form_list.append(key)

    form.input_list = input_list
    form.form_list = form_list
    form.update()
    form_refresh.refresh(state=nav.current_state())

    while True:
        key = typer.start_typing()
        if key in ("ok", "exe"):
            result = {}
            for index, spec in enumerate(field_specs):
                result[spec[0]] = form.input_list["inp_" + str(index)].strip()
            return result
        if key in ("toolbox",):
            return None
        if key in ("alpha", "beta"):
            keypad_state_manager(x=key)
            form.update_buffer("")
        else:
            form.update_buffer(key)
        form_refresh.refresh(state=nav.current_state())


def _edit_relation(session, relation_index):
    relation = session.relations[relation_index]
    type_name = relation["type"]
    if type_name == RELATION_TYPE_PARAM:
        fields = [("expr", relation["expr"]), ("expr_y", relation["expr_y"]), ("range_start", relation["range_start"]), ("range_end", relation["range_end"])]
    else:
        fields = [("expr", relation["expr"]), ("range_start", relation["range_start"]), ("range_end", relation["range_end"])]
    result = _run_form("Edit " + _relation_label(relation_index, relation), fields, relation)
    if result is None:
        session.set_status("Edit cancelled")
        return
    relation["expr"] = result.get("expr", relation["expr"])
    if type_name == RELATION_TYPE_PARAM:
        relation["expr_y"] = result.get("expr_y", relation["expr_y"])
    relation["range_start"] = result.get("range_start", relation["range_start"])
    relation["range_end"] = result.get("range_end", relation["range_end"])
    if relation["expr"]:
        relation["enabled"] = True
    session.current_relation = relation_index
    session.save()
    session.set_status(_relation_label(relation_index, relation) + " saved")


def _relation_actions(session, relation_index):
    while True:
        relation = session.relations[relation_index]
        items = [
            "Edit expression",
            "Change type",
            "Toggle draw",
            "Change style",
            "Rename",
            "Delete",
            "Set current",
        ]
        selection = _open_simple_menu(_relation_label(relation_index, relation), items, "OK=run")
        if selection is None:
            return
        if selection == 0:
            _edit_relation(session, relation_index)
        elif selection == 1:
            selected = _open_simple_menu("Type", RELATION_TYPES, "OK=type")
            if selected is not None:
                relation["type"] = RELATION_TYPES[selected]
                if relation["type"] != RELATION_TYPE_PARAM:
                    relation["expr_y"] = ""
                relation["name"] = _relation_label(relation_index, relation)
                session.save()
                session.set_status("Type set")
        elif selection == 2:
            relation["enabled"] = not relation["enabled"]
            session.save()
            session.set_status("Draw on" if relation["enabled"] else "Draw off")
        elif selection == 3:
            selected = _open_simple_menu("Style", STYLES, "OK=style")
            if selected is not None:
                relation["style"] = STYLES[selected]
                session.save()
                session.set_status("Style updated")
        elif selection == 4:
            result = _run_form("Rename", [("name", relation["name"])], relation)
            if result is not None and result.get("name"):
                relation["name"] = result["name"]
                session.save()
                session.set_status("Renamed")
        elif selection == 5:
            session.relations[relation_index] = default_relation(relation_index)
            session.save()
            session.set_status("Relation cleared")
        elif selection == 6:
            session.current_relation = relation_index
            session.cursor.graph_index = relation_index
            session.save()
            session.set_status("Current " + _relation_label(relation_index, relation))


def _open_relations_menu(session):
    while True:
        items = _relation_menu_items()
        selected = _open_simple_menu("Relations", items, "OK=edit")
        if selected is None:
            return
        _relation_actions(session, selected)


def _edit_bounds(session):
    fields = [
        ("x_min", format_number(session.bounds["x_min"]).strip()),
        ("x_max", format_number(session.bounds["x_max"]).strip()),
        ("y_min", format_number(session.bounds["y_min"]).strip()),
        ("y_max", format_number(session.bounds["y_max"]).strip()),
        ("x_scale", format_number(session.bounds["x_scale"]).strip()),
        ("y_scale", format_number(session.bounds["y_scale"]).strip()),
        ("t_min", format_number(session.bounds["t_min"]).strip()),
        ("t_max", format_number(session.bounds["t_max"]).strip()),
        ("t_step", format_number(session.bounds["t_step"]).strip()),
    ]
    result = _run_form("V-Window", fields, session.bounds)
    if result is None:
        session.set_status("Window cancelled")
        return
    try:
        new_bounds = {
            "x_min": _eval_number(result["x_min"]),
            "x_max": _eval_number(result["x_max"]),
            "y_min": _eval_number(result["y_min"]),
            "y_max": _eval_number(result["y_max"]),
            "x_scale": abs(_eval_number(result["x_scale"] or "1")),
            "y_scale": abs(_eval_number(result["y_scale"] or "1")),
            "t_min": _eval_number(result["t_min"]),
            "t_max": _eval_number(result["t_max"]),
            "t_step": _eval_number(result["t_step"]),
        }
    except Exception:
        session.set_status("Window input error")
        return
    if new_bounds["x_max"] == new_bounds["x_min"] or new_bounds["y_max"] == new_bounds["y_min"]:
        session.set_status("Range error")
        return
    session.previous_bounds = _copy_bounds(session.bounds)
    session.bounds = new_bounds
    session.save()
    session.set_status("V-Window updated")


def _store_vwindow(session):
    items = []
    for idx in range(MAX_VWINDOWS):
        items.append("V-Win" + str(idx + 1))
    selected = _open_simple_menu("Store V-Win", items, "OK=store")
    if selected is None:
        return
    session.vwindow_memories[selected] = _copy_bounds(session.bounds)
    session.save()
    session.set_status("Stored V" + str(selected + 1))


def _recall_vwindow(session):
    items = []
    for idx in range(MAX_VWINDOWS):
        items.append("V-Win" + str(idx + 1))
    selected = _open_simple_menu("Recall V-Win", items, "OK=load")
    if selected is None:
        return
    session.previous_bounds = _copy_bounds(session.bounds)
    session.bounds = _copy_bounds(session.vwindow_memories[selected])
    session.set_status("Loaded V" + str(selected + 1))


def _apply_zoom(session, factor):
    bounds = session.bounds
    x_range = bounds["x_max"] - bounds["x_min"]
    y_range = bounds["y_max"] - bounds["y_min"]
    x_center = (bounds["x_max"] + bounds["x_min"]) * 0.5
    y_center = (bounds["y_max"] + bounds["y_min"]) * 0.5
    session.previous_bounds = _copy_bounds(bounds)
    session.bounds["x_min"] = x_center - (x_range * factor * 0.5)
    session.bounds["x_max"] = x_center + (x_range * factor * 0.5)
    session.bounds["y_min"] = y_center - (y_range * factor * 0.5)
    session.bounds["y_max"] = y_center + (y_range * factor * 0.5)


def _apply_pan(session, direction):
    bounds = session.bounds
    x_range = bounds["x_max"] - bounds["x_min"]
    y_range = bounds["y_max"] - bounds["y_min"]
    session.previous_bounds = _copy_bounds(bounds)
    if direction == "left":
        delta = x_range * PAN_SHIFT_FACTOR
        bounds["x_min"] -= delta
        bounds["x_max"] -= delta
    elif direction == "right":
        delta = x_range * PAN_SHIFT_FACTOR
        bounds["x_min"] += delta
        bounds["x_max"] += delta
    elif direction == "up":
        delta = y_range * PAN_SHIFT_FACTOR
        bounds["y_min"] += delta
        bounds["y_max"] += delta
    elif direction == "down":
        delta = y_range * PAN_SHIFT_FACTOR
        bounds["y_min"] -= delta
        bounds["y_max"] -= delta


def _auto_zoom_y(session):
    _ensure_analysis_samples(session)
    best_min = None
    best_max = None
    for relation_index in session.enabled_relation_indices():
        samples = session.current_graph_samples.get(relation_index) or []
        for sample in samples:
            y_value = sample["y"]
            if best_min is None or y_value < best_min:
                best_min = y_value
            if best_max is None or y_value > best_max:
                best_max = y_value
    if best_min is None or best_max is None or best_min == best_max:
        session.set_status("Auto zoom unavailable")
        return
    span = best_max - best_min
    if span == 0:
        span = 1.0
    session.previous_bounds = _copy_bounds(session.bounds)
    session.bounds["y_min"] = best_min - span * 0.15
    session.bounds["y_max"] = best_max + span * 0.15
    session.set_status("Auto zoom")


def _square_zoom(session):
    bounds = session.bounds
    x_range = bounds["x_max"] - bounds["x_min"]
    if x_range == 0:
        return
    desired_y_range = x_range * (PLOT_HEIGHT / float(DISPLAY_WIDTH))
    y_center = (bounds["y_min"] + bounds["y_max"]) * 0.5
    session.previous_bounds = _copy_bounds(bounds)
    session.bounds["y_min"] = y_center - desired_y_range * 0.5
    session.bounds["y_max"] = y_center + desired_y_range * 0.5
    session.set_status("Square view")


def _zoom_menu(session):
    items = [
        "Zoom In",
        "Zoom Out",
        "Auto Y",
        "Original",
        "Previous",
        "Square",
        "Store V-Window",
        "Recall V-Window",
    ]
    selected = _open_simple_menu("Zoom", items, "OK=run")
    if selected is None:
        return
    if selected == 0:
        _apply_zoom(session, ZOOM_IN_FACTOR)
    elif selected == 1:
        _apply_zoom(session, ZOOM_OUT_FACTOR)
    elif selected == 2:
        _auto_zoom_y(session)
        return
    elif selected == 3:
        session.previous_bounds = _copy_bounds(session.bounds)
        session.bounds = _copy_bounds(session.initial_bounds)
    elif selected == 4:
        current = _copy_bounds(session.bounds)
        session.bounds = _copy_bounds(session.previous_bounds)
        session.previous_bounds = current
    elif selected == 5:
        _square_zoom(session)
        return
    elif selected == 6:
        _store_vwindow(session)
        return
    elif selected == 7:
        _recall_vwindow(session)
        return
    session.save()
    session.set_status("Zoom updated")


def _toggle_trace(session):
    session.cursor.toggle()
    if session.cursor.graph_index not in session.enabled_relation_indices():
        enabled = session.enabled_relation_indices()
        session.cursor.graph_index = enabled[0] if enabled else 0
    session.set_status("Trace on" if session.cursor.active else "Trace off")


def _solve_root(samples):
    if not samples:
        return []
    roots = []
    prev = samples[0]
    for item in samples[1:]:
        if prev["y"] == 0:
            roots.append((prev["x"], 0.0))
        elif item["y"] == 0:
            roots.append((item["x"], 0.0))
        elif (prev["y"] < 0 < item["y"]) or (prev["y"] > 0 > item["y"]):
            dx = item["x"] - prev["x"]
            dy = item["y"] - prev["y"]
            if dy != 0:
                x_root = prev["x"] - prev["y"] * dx / dy
                roots.append((x_root, 0.0))
        prev = item
    return roots


def _solve_extrema(samples, want_max):
    results = []
    if len(samples) < 3:
        return results
    for idx in range(1, len(samples) - 1):
        prev = samples[idx - 1]["y"]
        cur = samples[idx]["y"]
        nxt = samples[idx + 1]["y"]
        if want_max and cur >= prev and cur >= nxt:
            results.append((samples[idx]["x"], cur))
        if (not want_max) and cur <= prev and cur <= nxt:
            results.append((samples[idx]["x"], cur))
    return results


def _solve_y_intercept(samples):
    roots = []
    for item in samples:
        if abs(item["x"]) <= abs(_x_step_for_one_pixel(SESSION.bounds)):
            roots.append((0.0, item["y"]))
    return roots


def _solve_intersections(samples_a, samples_b):
    if not samples_a or not samples_b:
        return []
    results = []
    length = min(len(samples_a), len(samples_b))
    prev_diff = None
    prev_x = None
    for idx in range(length):
        a = samples_a[idx]
        b = samples_b[idx]
        diff = a["y"] - b["y"]
        if prev_diff is not None:
            if diff == 0:
                results.append((a["x"], a["y"]))
            elif (prev_diff < 0 < diff) or (prev_diff > 0 > diff):
                dx = a["x"] - prev_x
                dy = diff - prev_diff
                if dy != 0:
                    x_value = prev_x - prev_diff * dx / dy
                    y_value = a["y"]
                    results.append((x_value, y_value))
        prev_diff = diff
        prev_x = a["x"]
    return results


def _input_single_value(title, field_name, default_text="0"):
    result = _run_form(title, [(field_name, default_text)], {field_name: default_text})
    if result is None:
        return None
    try:
        return _eval_number(result[field_name])
    except Exception:
        return None


def _show_result_screen(title, lines):
    items = [title]
    for line in lines:
        items.append(line)
    menu_items = items + ["toolbox/nav_b=close"]
    _open_simple_menu("Result", menu_items, "close")


def _gsolve_menu(session):
    _ensure_analysis_samples(session)
    items = [
        "Root",
        "Max",
        "Min",
        "Y-Intercept",
        "Intersect",
        "Y-Cal",
        "X-Cal",
        "Integral",
    ]
    selected = _open_simple_menu("G-Solve", items, "OK=run")
    if selected is None:
        return

    relation_index = session.cursor.graph_index if session.cursor.active else session.current_relation
    samples = session.current_graph_samples.get(relation_index) or []
    label = _relation_label(relation_index, session.relations[relation_index])

    if selected == 0:
        results = _solve_root(samples)
        lines = [label]
        if results:
            for x_value, y_value in results[:4]:
                lines.append("x=" + _format_short(x_value))
        else:
            lines.append("No root")
        _show_result_screen("Root", lines)
    elif selected == 1:
        results = _solve_extrema(samples, True)
        lines = [label]
        if results:
            for x_value, y_value in results[:4]:
                lines.append("x=" + _format_short(x_value) + " y=" + _format_short(y_value))
        else:
            lines.append("No local max")
        _show_result_screen("Maximum", lines)
    elif selected == 2:
        results = _solve_extrema(samples, False)
        lines = [label]
        if results:
            for x_value, y_value in results[:4]:
                lines.append("x=" + _format_short(x_value) + " y=" + _format_short(y_value))
        else:
            lines.append("No local min")
        _show_result_screen("Minimum", lines)
    elif selected == 3:
        results = _solve_y_intercept(samples)
        lines = [label]
        if results:
            for x_value, y_value in results[:4]:
                lines.append("y=" + _format_short(y_value))
        else:
            lines.append("No intercept")
        _show_result_screen("Y-Intercept", lines)
    elif selected == 4:
        other_items = []
        enabled = session.enabled_relation_indices()
        for idx in enabled:
            if idx != relation_index:
                other_items.append(_relation_label(idx, session.relations[idx]))
        if not other_items:
            session.set_status("Need 2 graphs")
            return
        other_pick = _open_simple_menu("2nd graph", other_items, "OK=pick")
        if other_pick is None:
            return
        other_indices = [idx for idx in enabled if idx != relation_index]
        other_index = other_indices[other_pick]
        results = _solve_intersections(samples, session.current_graph_samples.get(other_index) or [])
        lines = [label + " & " + _relation_label(other_index, session.relations[other_index])]
        if results:
            for x_value, y_value in results[:4]:
                lines.append("x=" + _format_short(x_value) + " y=" + _format_short(y_value))
        else:
            lines.append("No intersection")
        _show_result_screen("Intersect", lines)
    elif selected == 5:
        x_value = _input_single_value("Y-Cal", "x", "0")
        if x_value is None:
            session.set_status("Bad x")
            return
        sample = _nearest_sample(samples, _x_value_to_pixel(x_value, session.bounds, clamp=True))
        lines = [label, "x=" + _format_short(x_value)]
        lines.append(_format_status_value("y", sample["y"] if sample is not None else None))
        _show_result_screen("Y-Cal", lines)
    elif selected == 6:
        y_value = _input_single_value("X-Cal", "y", "0")
        if y_value is None:
            session.set_status("Bad y")
            return
        hits = []
        prev = None
        for item in samples:
            if prev is not None:
                if (prev["y"] < y_value < item["y"]) or (prev["y"] > y_value > item["y"]) or item["y"] == y_value:
                    hits.append(item["x"])
            prev = item
        lines = [label, "y=" + _format_short(y_value)]
        if hits:
            for hit in hits[:4]:
                lines.append("x=" + _format_short(hit))
        else:
            lines.append("No x")
        _show_result_screen("X-Cal", lines)
    elif selected == 7:
        lower = _input_single_value("Integral", "x0", "-1")
        if lower is None:
            session.set_status("Bad lower")
            return
        upper = _input_single_value("Integral", "x1", "1")
        if upper is None:
            session.set_status("Bad upper")
            return
        value = _compute_area_value(samples, lower, upper)
        lines = [label, "x0=" + _format_short(lower), "x1=" + _format_short(upper), _format_status_value("A", value)]
        _show_result_screen("Integral", lines)


def _table_generate(session):
    result = _run_form(
        "Table",
        [
            ("start", "-3"),
            ("end", "3"),
            ("step", "1"),
        ],
        {"start": "-3", "end": "3", "step": "1"},
    )
    if result is None:
        session.set_status("Table cancelled")
        return
    try:
        start_value = _eval_number(result["start"])
        end_value = _eval_number(result["end"])
        step_value = _eval_number(result["step"])
    except Exception:
        session.set_status("Table input error")
        return
    if step_value == 0:
        session.set_status("Step cannot be 0")
        return
    relation_index = session.current_relation
    relation = session.relations[relation_index]
    relation_type = relation["type"]
    rows = []
    headers = ["x", _relation_label(relation_index, relation)]
    if relation_type == RELATION_TYPE_PARAM:
        headers = ["t", "x(t)", "y(t)"]
        eval_x = _make_eval_fn(relation["expr"], "t")
        eval_y = _make_eval_fn(relation["expr_y"], "t")
    elif relation_type == RELATION_TYPE_R:
        headers = ["t", "r(t)"]
        eval_x = _make_eval_fn(relation["expr"], "t")
        eval_y = None
    elif relation_type in (RELATION_TYPE_X, RELATION_TYPE_X_GT, RELATION_TYPE_X_LT, RELATION_TYPE_X_GE, RELATION_TYPE_X_LE):
        headers = ["y", "x(y)"]
        eval_x = _make_eval_fn(relation["expr"], "y")
        eval_y = None
    else:
        eval_x = _make_eval_fn(relation["expr"], "x")
        eval_y = None

    current_value = start_value
    guard = 0
    forward = step_value > 0
    while ((current_value <= end_value) if forward else (current_value >= end_value)) and guard < 512:
        if relation_type == RELATION_TYPE_PARAM:
            x_value = _safe_eval(eval_x, current_value)
            y_value = _safe_eval(eval_y, current_value)
            rows.append([_format_short(current_value), _format_short(x_value), _format_short(y_value)])
        elif relation_type == RELATION_TYPE_R:
            rows.append([_format_short(current_value), _format_short(_safe_eval(eval_x, current_value))])
        elif relation_type in (RELATION_TYPE_X, RELATION_TYPE_X_GT, RELATION_TYPE_X_LT, RELATION_TYPE_X_GE, RELATION_TYPE_X_LE):
            rows.append([_format_short(current_value), _format_short(_safe_eval(eval_x, current_value))])
        else:
            y_value = _safe_eval(eval_x, current_value)
            slope = None
            if eval_y is None and relation_type == RELATION_TYPE_Y and session.show_derivative:
                x_step = max(1e-6, abs(_x_step_for_one_pixel(session.bounds)))
                left = _safe_eval(eval_x, current_value - x_step)
                right = _safe_eval(eval_x, current_value + x_step)
                if left is not None and right is not None:
                    slope = (right - left) / (2.0 * x_step)
            if slope is not None:
                if "dy/dx" not in headers:
                    headers.append("dy/dx")
                rows.append([_format_short(current_value), _format_short(y_value), _format_short(slope)])
            else:
                rows.append([_format_short(current_value), _format_short(y_value)])
        current_value += step_value
        guard += 1

    session.table_rows = rows
    session.table_headers = headers
    session.table_title = "Table " + _relation_label(relation_index, relation)
    _table_viewer(session)


def _table_viewer(session):
    if not session.table_rows:
        session.set_status("No table")
        return
    index = 0
    top = 0
    visible = 3
    fb_buf = bytearray((DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8)
    fb = framebuf.FrameBuffer(fb_buf, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_VLSB)
    headers = " ".join(session.table_headers)[:21]
    while True:
        fb.fill(0)
        fb.text(session.table_title[:21], 0, 0, 1)
        fb.text(headers, 0, 8, 1)
        if index < top:
            top = index
        elif index >= top + visible:
            top = index - visible + 1
        for row in range(visible):
            row_index = top + row
            if row_index >= len(session.table_rows):
                break
            text = " ".join(session.table_rows[row_index])[:21]
            prefix = ">" if row_index == index else " "
            fb.text((prefix + text)[:21], 0, 18 + row * 12, 1)
        fb.text("OK graph AC close", 0, 56, 1)
        _display_full(fb_buf)
        key = typer.start_typing()
        if key == "nav_u":
            index = (index - 1) % len(session.table_rows)
        elif key == "nav_d":
            index = (index + 1) % len(session.table_rows)
        elif key in ("toolbox", "nav_b", "AC"):
            return
        elif key in ("ok", "exe"):
            _plot_table_rows(session)
            return
        elif key in ("alpha", "beta"):
            keypad_state_manager(x=key)


def _plot_table_rows(session):
    if not session.table_rows or len(session.table_rows[0]) < 2:
        return
    session.fb.fill(0)
    _draw_axes_and_grid(session)
    prev = None
    for index, row in enumerate(session.table_rows):
        try:
            x_value = float(row[0])
            y_value = float(row[1])
        except Exception:
            continue
        x_px = _x_value_to_pixel(x_value, session.bounds, clamp=False)
        y_px = _y_value_to_pixel(y_value, session.bounds, clamp=False)
        if x_px is None or y_px is None:
            prev = None
            continue
        session.fb.pixel(x_px, y_px, 1)
        if prev is not None:
            _styled_line(session.fb, prev[0], prev[1], x_px, y_px, STYLE_NORMAL)
        prev = (x_px, y_px)
    _draw_status_bar(session, "Table graph")
    _display_full(session.fb_buf)
    session.set_status("Table graph")


def _dynamic_menu(session):
    relation_index = session.current_relation
    relation = session.relations[relation_index]
    result = _run_form(
        "Dynamic",
        [
            ("parameter", session.dynamic_config["parameter"]),
            ("start", str(session.dynamic_config["start"])),
            ("end", str(session.dynamic_config["end"])),
            ("step", str(session.dynamic_config["step"])),
            ("locus", "1" if session.dynamic_config["locus"] else "0"),
            ("speed_ms", str(session.dynamic_config["speed_ms"])),
        ],
        session.dynamic_config,
    )
    if result is None:
        session.set_status("Dynamic cancelled")
        return
    try:
        session.dynamic_config["parameter"] = (result["parameter"] or "A")[:1]
        session.dynamic_config["start"] = _eval_number(result["start"])
        session.dynamic_config["end"] = _eval_number(result["end"])
        session.dynamic_config["step"] = _eval_number(result["step"])
        session.dynamic_config["locus"] = str(result["locus"]).strip() not in ("0", "false", "False", "")
        session.dynamic_config["speed_ms"] = int(_eval_number(result["speed_ms"]))
    except Exception:
        session.set_status("Dynamic input error")
        return
    session.save()
    _run_dynamic_graph(session, relation_index)


def _run_dynamic_graph(session, relation_index):
    relation = session.relations[relation_index]
    param = session.dynamic_config["parameter"]
    start_value = session.dynamic_config["start"]
    end_value = session.dynamic_config["end"]
    step_value = session.dynamic_config["step"]
    if step_value == 0:
        session.set_status("Dynamic step 0")
        return
    forward = step_value > 0
    current_value = start_value
    locus_buffer = bytearray(PLOT_BUFFER_BYTES)
    while (current_value <= end_value if forward else current_value >= end_value):
        extra = {param: current_value}
        _render_graph(
            session,
            extra=extra,
            draw_features=False,
            custom_status="{}={}".format(param, _format_short(current_value)),
            present=False,
        )
        if session.dynamic_config["locus"]:
            for idx in range(PLOT_BUFFER_BYTES):
                locus_buffer[idx] |= session.fb_buf[idx]
                session.fb_buf[idx] = locus_buffer[idx]
        _display_full(session.fb_buf)
        time.sleep_ms(max(10, int(session.dynamic_config["speed_ms"])))
        current_value += step_value
    session.set_status("Dynamic done")


def _poll_escape_keys():
    return False


def _recur_generate(session):
    result = _run_form(
        "Recursion",
        [
            ("type", session.recur_config["type"]),
            ("expr_a", session.recur_config["expr_a"]),
            ("expr_b", session.recur_config["expr_b"]),
            ("start_n", str(session.recur_config["start_n"])),
            ("end_n", str(session.recur_config["end_n"])),
            ("a1", str(session.recur_config["a1"])),
            ("a2", str(session.recur_config["a2"])),
            ("phase", "1" if session.recur_config["phase"] else "0"),
        ],
        session.recur_config,
    )
    if result is None:
        session.set_status("Recursion cancelled")
        return
    session.recur_config["type"] = result["type"] or RECUR_TYPE_TWO
    session.recur_config["expr_a"] = result["expr_a"]
    session.recur_config["expr_b"] = result["expr_b"]
    try:
        session.recur_config["start_n"] = int(_eval_number(result["start_n"]))
        session.recur_config["end_n"] = int(_eval_number(result["end_n"]))
        session.recur_config["a1"] = _eval_number(result["a1"])
        session.recur_config["a2"] = _eval_number(result["a2"])
    except Exception:
        session.set_status("Recursion input error")
        return
    session.recur_config["phase"] = str(result["phase"]).strip() not in ("0", "false", "False", "")
    session.save()
    rows = _generate_recur_rows(session.recur_config)
    if not rows:
        session.set_status("Recursion failed")
        return
    session.table_headers = ["n", "a(n)"]
    session.table_rows = rows
    session.table_title = "Recursion"
    _recur_viewer(session, rows)


def _generate_recur_rows(config):
    kind = config["type"]
    start_n = int(config["start_n"])
    end_n = int(config["end_n"])
    if end_n < start_n:
        start_n, end_n = end_n, start_n
    rows = []
    if kind == RECUR_TYPE_TERM:
        fn = _make_eval_fn(config["expr_a"], "n")
        for n_value in range(start_n, end_n + 1):
            rows.append([str(n_value), _format_short(_safe_eval(fn, n_value))])
        return rows

    values = {1: float(config["a1"]), 2: float(config["a2"])}
    if start_n <= 1 <= end_n:
        rows.append(["1", _format_short(values[1])])
    if start_n <= 2 <= end_n:
        rows.append(["2", _format_short(values[2])])
    if kind == RECUR_TYPE_TWO:
        fn = _make_eval_fn(config["expr_a"], "a")
        for n_value in range(1, end_n):
            if n_value + 1 not in values:
                values[n_value + 1] = _safe_eval(fn, values[n_value], {"n": n_value})
            if n_value + 1 >= max(3, start_n) and n_value + 1 <= end_n:
                rows.append([str(n_value + 1), _format_short(values[n_value + 1])])
    else:
        fn = _make_eval_fn(config["expr_a"], "a")
        for n_value in range(1, end_n - 1):
            extra = {"b": values[n_value + 1], "n": n_value}
            values[n_value + 2] = _safe_eval(fn, values[n_value], extra)
            if n_value + 2 >= start_n and n_value + 2 <= end_n:
                rows.append([str(n_value + 2), _format_short(values[n_value + 2])])
    rows.sort(key=lambda item: int(item[0]))
    out = []
    for row in rows:
        if int(row[0]) >= start_n and int(row[0]) <= end_n:
            out.append(row)
    return out


def _recur_viewer(session, rows):
    index = 0
    top = 0
    visible = 3
    fb_buf = bytearray((DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8)
    fb = framebuf.FrameBuffer(fb_buf, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_VLSB)
    while True:
        fb.fill(0)
        fb.text("Recursion Table", 0, 0, 1)
        fb.text("n  a(n)", 0, 8, 1)
        if index < top:
            top = index
        elif index >= top + visible:
            top = index - visible + 1
        for row in range(visible):
            row_index = top + row
            if row_index >= len(rows):
                break
            prefix = ">" if row_index == index else " "
            text = prefix + rows[row_index][0] + " " + rows[row_index][1]
            fb.text(text[:21], 0, 18 + row * 12, 1)
        fb.text("OK graph 3 phase", 0, 56, 1)
        _display_full(fb_buf)
        key = typer.start_typing()
        if key == "nav_u":
            index = (index - 1) % len(rows)
        elif key == "nav_d":
            index = (index + 1) % len(rows)
        elif key in ("toolbox", "nav_b", "AC"):
            return
        elif key in ("ok", "exe"):
            _plot_recur_rows(session, rows, False)
            return
        elif key == "F3" or key == "3":
            _plot_recur_rows(session, rows, True)
            return
        elif key in ("alpha", "beta"):
            keypad_state_manager(x=key)


def _plot_recur_rows(session, rows, phase_plot):
    session.fb.fill(0)
    _draw_axes_and_grid(session)
    prev = None
    if phase_plot and len(rows) > 1:
        for idx in range(len(rows) - 1):
            try:
                x_value = float(rows[idx][1])
                y_value = float(rows[idx + 1][1])
            except Exception:
                continue
            x_px = _x_value_to_pixel(x_value, session.bounds, clamp=False)
            y_px = _y_value_to_pixel(y_value, session.bounds, clamp=False)
            if x_px is None or y_px is None:
                prev = None
                continue
            session.fb.pixel(x_px, y_px, 1)
            if prev is not None:
                _styled_line(session.fb, prev[0], prev[1], x_px, y_px, STYLE_NORMAL)
            prev = (x_px, y_px)
        _draw_status_bar(session, "Phase plot")
    else:
        for row in rows:
            try:
                x_value = float(row[0])
                y_value = float(row[1])
            except Exception:
                continue
            x_px = _x_value_to_pixel(x_value, session.bounds, clamp=False)
            y_px = _y_value_to_pixel(y_value, session.bounds, clamp=False)
            if x_px is None or y_px is None:
                prev = None
                continue
            session.fb.pixel(x_px, y_px, 1)
            if prev is not None:
                _styled_line(session.fb, prev[0], prev[1], x_px, y_px, STYLE_NORMAL)
            prev = (x_px, y_px)
        _draw_status_bar(session, "Recursion graph")
    _display_full(session.fb_buf)
    session.set_status("Recursion plotted")


def _conic_menu(session):
    selected = _open_simple_menu("Conics", CONIC_TYPES, "OK=pick")
    if selected is None:
        return
    conic_type = CONIC_TYPES[selected]
    session.conic_config["type"] = conic_type
    fields = [("h", str(session.conic_config["h"])), ("k", str(session.conic_config["k"]))]
    if conic_type in (CONIC_PARABOLA_X, CONIC_PARABOLA_Y):
        fields.append(("p", str(session.conic_config["p"])))
    elif conic_type == CONIC_CIRCLE:
        fields.append(("a", str(session.conic_config["a"])))
    else:
        fields.append(("a", str(session.conic_config["a"])))
        fields.append(("b", str(session.conic_config["b"])))

    result = _run_form("Conic " + conic_type, fields, session.conic_config)
    if result is None:
        session.set_status("Conic cancelled")
        return
    for key in ("h", "k", "a", "b", "p"):
        if key in result:
            try:
                session.conic_config[key] = _eval_number(result[key])
            except Exception:
                session.set_status("Conic input error")
                return
    session.save()
    _draw_conic(session)


def _draw_conic(session):
    session.fb.fill(0)
    _draw_axes_and_grid(session)
    cfg = session.conic_config
    conic_type = cfg["type"]
    points = []
    if conic_type == CONIC_CIRCLE:
        angle = 0.0
        while angle <= math.pi * 2.0 + 0.01:
            x_value = cfg["h"] + cfg["a"] * math.cos(angle)
            y_value = cfg["k"] + cfg["a"] * math.sin(angle)
            points.append((x_value, y_value))
            angle += math.pi / 90.0
    elif conic_type == CONIC_PARABOLA_X:
        y_value = session.bounds["y_min"]
        step = (session.bounds["y_max"] - session.bounds["y_min"]) / 180.0
        if step == 0:
            step = 0.1
        while y_value <= session.bounds["y_max"]:
            x_value = cfg["h"] + ((y_value - cfg["k"]) ** 2) / max(1e-6, 4.0 * cfg["p"])
            points.append((x_value, y_value))
            y_value += step
    elif conic_type == CONIC_PARABOLA_Y:
        x_value = session.bounds["x_min"]
        step = (session.bounds["x_max"] - session.bounds["x_min"]) / 180.0
        if step == 0:
            step = 0.1
        while x_value <= session.bounds["x_max"]:
            y_value = cfg["k"] + ((x_value - cfg["h"]) ** 2) / max(1e-6, 4.0 * cfg["p"])
            points.append((x_value, y_value))
            x_value += step
    elif conic_type in (CONIC_ELLIPSE_X, CONIC_ELLIPSE_Y, CONIC_HYPERBOLA_X, CONIC_HYPERBOLA_Y):
        t_value = 0.0
        while t_value <= math.pi * 2.0 + 0.01:
            if conic_type == CONIC_ELLIPSE_X:
                x_value = cfg["h"] + cfg["a"] * math.cos(t_value)
                y_value = cfg["k"] + cfg["b"] * math.sin(t_value)
            elif conic_type == CONIC_ELLIPSE_Y:
                x_value = cfg["h"] + cfg["b"] * math.cos(t_value)
                y_value = cfg["k"] + cfg["a"] * math.sin(t_value)
            elif conic_type == CONIC_HYPERBOLA_X:
                if abs(math.cos(t_value)) < 0.2:
                    t_value += math.pi / 90.0
                    continue
                x_value = cfg["h"] + cfg["a"] / math.cos(t_value)
                y_value = cfg["k"] + cfg["b"] * math.tan(t_value)
            else:
                if abs(math.sin(t_value)) < 0.2:
                    t_value += math.pi / 90.0
                    continue
                x_value = cfg["h"] + cfg["a"] * math.tan(t_value)
                y_value = cfg["k"] + cfg["b"] / math.sin(t_value)
            points.append((x_value, y_value))
            t_value += math.pi / 90.0

    prev = None
    for x_value, y_value in points:
        x_px = _x_value_to_pixel(x_value, session.bounds, clamp=False)
        y_px = _y_value_to_pixel(y_value, session.bounds, clamp=False)
        if x_px is None or y_px is None:
            prev = None
            continue
        session.fb.pixel(x_px, y_px, 1)
        if prev is not None:
            _styled_line(session.fb, prev[0], prev[1], x_px, y_px, STYLE_NORMAL)
        prev = (x_px, y_px)

    _draw_status_bar(session, "Conic " + conic_type[:11])
    _display_full(session.fb_buf)
    _show_conic_analysis(session)


def _show_conic_analysis(session):
    cfg = session.conic_config
    conic_type = cfg["type"]
    lines = [conic_type]
    if conic_type == CONIC_CIRCLE:
        lines.append("center " + _format_short(cfg["h"]) + "," + _format_short(cfg["k"]))
        lines.append("radius " + _format_short(cfg["a"]))
    elif conic_type in (CONIC_ELLIPSE_X, CONIC_ELLIPSE_Y):
        major = cfg["a"] if conic_type == CONIC_ELLIPSE_X else cfg["b"]
        minor = cfg["b"] if conic_type == CONIC_ELLIPSE_X else cfg["a"]
        c_value = math.sqrt(abs((major * major) - (minor * minor)))
        lines.append("center " + _format_short(cfg["h"]) + "," + _format_short(cfg["k"]))
        lines.append("focus c=" + _format_short(c_value))
        lines.append("ecc=" + _format_short(c_value / max(1e-6, abs(major))))
    elif conic_type in (CONIC_HYPERBOLA_X, CONIC_HYPERBOLA_Y):
        c_value = math.sqrt(abs((cfg["a"] * cfg["a"]) + (cfg["b"] * cfg["b"])))
        lines.append("center " + _format_short(cfg["h"]) + "," + _format_short(cfg["k"]))
        lines.append("focus c=" + _format_short(c_value))
        lines.append("ecc=" + _format_short(c_value / max(1e-6, abs(cfg["a"]))))
    else:
        lines.append("vertex " + _format_short(cfg["h"]) + "," + _format_short(cfg["k"]))
        lines.append("focus p=" + _format_short(cfg["p"]))
        lines.append("directrix")
    _show_result_screen("Conic Info", lines)


def _graph_memory_menu(session):
    items = []
    for idx in range(MAX_GRAPH_MEMORIES):
        if session.graph_memories[idx] is None:
            items.append("G-Mem" + str(idx + 1) + " empty")
        else:
            items.append("G-Mem" + str(idx + 1) + " saved")
    selected = _open_simple_menu("Graph Mem", items, "OK=pick")
    if selected is None:
        return
    action = _open_simple_menu("Action", ["Store", "Recall"], "OK=run")
    if action is None:
        return
    if action == 0:
        session.graph_memories[selected] = {
            "relations": _ensure_relations(session.relations),
            "bounds": _copy_bounds(session.bounds),
            "appearance": {
                "grid": session.show_grid,
                "axes": session.show_axes,
                "labels": session.show_labels,
                "coords": session.show_coords,
                "derivative": session.show_derivative,
                "ineq": session.inequality_mode,
            },
        }
        session.save()
        session.set_status("Stored G" + str(selected + 1))
    else:
        stored = session.graph_memories[selected]
        if stored is None:
            session.set_status("Memory empty")
            return
        session.relations = _ensure_relations(stored.get("relations"))
        session.bounds = _copy_bounds(stored.get("bounds") or default_bounds())
        appearance = stored.get("appearance") or {}
        session.show_grid = bool(appearance.get("grid", False))
        session.show_axes = bool(appearance.get("axes", True))
        session.show_labels = bool(appearance.get("labels", False))
        session.show_coords = bool(appearance.get("coords", True))
        session.show_derivative = bool(appearance.get("derivative", True))
        session.inequality_mode = str(appearance.get("ineq", "AND"))
        session.save()
        session.set_status("Loaded G" + str(selected + 1))


def _picture_memory_menu(session):
    items = []
    for idx in range(MAX_PICTURE_MEMORIES):
        items.append("Pict " + str(idx + 1) + (" saved" if session.picture_memories[idx] else " empty"))
    selected = _open_simple_menu("Picture Mem", items, "OK=pick")
    if selected is None:
        return
    action = _open_simple_menu("Action", ["Store", "Recall"], "OK=run")
    if action is None:
        return
    if action == 0:
        session.picture_memories[selected] = bytes(session.fb_buf)
        session.save()
        session.set_status("Stored P" + str(selected + 1))
    else:
        picture = session.picture_memories[selected]
        if picture is None:
            session.set_status("Picture empty")
            return
        session.fb_buf[:] = picture[: len(session.fb_buf)]
        _display_full(session.fb_buf)
        session.set_status("Recalled P" + str(selected + 1))


def _appearance_menu(session):
    while True:
        items = [
            "Grid " + ("On" if session.show_grid else "Off"),
            "Axes " + ("On" if session.show_axes else "Off"),
            "Label " + ("On" if session.show_labels else "Off"),
            "Coord " + ("On" if session.show_coords else "Off"),
            "Slope " + ("On" if session.show_derivative else "Off"),
            "Ineq " + session.inequality_mode,
        ]
        selected = _open_simple_menu("Appearance", items, "OK=toggle")
        if selected is None:
            session.save()
            return
        if selected == 0:
            session.show_grid = not session.show_grid
        elif selected == 1:
            session.show_axes = not session.show_axes
        elif selected == 2:
            session.show_labels = not session.show_labels
        elif selected == 3:
            session.show_coords = not session.show_coords
        elif selected == 4:
            session.show_derivative = not session.show_derivative
        elif selected == 5:
            session.inequality_mode = "OR" if session.inequality_mode == "AND" else "AND"
        session.set_status("Appearance updated")


def _feature_add_menu(session):
    selected = _open_simple_menu("Features", [TOOL_LABELS[item] for item in TOOL_MENU_ITEMS], "OK=add")
    if selected is None:
        return
    relation_index = session.cursor.graph_index if session.cursor.active else session.current_relation
    samples = session.current_graph_samples.get(relation_index) or []
    focus_x_pixel = session.cursor.x_pixel if session.cursor.active else (DISPLAY_WIDTH // 2)
    if samples:
        sample = _nearest_sample(samples, focus_x_pixel)
        if sample is not None:
            x_value = sample["x"]
        else:
            x_value = _x_pixel_to_value(focus_x_pixel, session.bounds)
    else:
        x_value = _x_pixel_to_value(focus_x_pixel, session.bounds)
    feature = session.tool_state.add_feature(TOOL_MENU_ITEMS[selected], relation_index, x_value)
    session.cursor.active = True
    session.cursor.graph_index = relation_index
    session.cursor.x_pixel = _x_value_to_pixel(feature.focused_x_value(), session.bounds, clamp=True)
    session.set_status(TOOL_LABELS[feature.mode] + " added")


def _used_tools_menu(session):
    while True:
        items = []
        for feature in session.tool_state.features:
            items.append(TOOL_SHORT_LABELS[feature.mode] + str(feature.instance_number) + " " + _relation_label(feature.graph_index, session.relations[feature.graph_index]))
        if not items:
            items = ["No tools"]
        selected = _open_simple_menu("Used Tools", items, "OK=select")
        if selected is None:
            return
        if not session.tool_state.features:
            return
        action = _open_simple_menu("Tool Action", ["Select", "Delete"], "OK=run")
        if action is None:
            return
        if action == 0:
            session.tool_state.selected_index = selected
            feature = session.tool_state.selected_feature()
            session.cursor.active = True
            session.cursor.graph_index = feature.graph_index
            session.cursor.x_pixel = _x_value_to_pixel(feature.focused_x_value(), session.bounds, clamp=True)
            session.set_status("Tool selected")
            return
        session.tool_state.remove_index(selected)
        session.set_status("Tool deleted")


def _move_selected_tool(session, delta):
    feature = session.tool_state.selected_feature()
    if feature is None:
        return False
    step = _x_step_for_one_pixel(session.bounds)
    if step == 0:
        return False
    delta_x = step * delta
    if feature.mode == TOOL_AREA:
        if feature.area_focus == "left":
            feature.area_x_left += delta_x
        else:
            feature.area_x_right += delta_x
        if feature.area_x_left > feature.area_x_right:
            feature.area_x_left, feature.area_x_right = feature.area_x_right, feature.area_x_left
            feature.area_focus = "left" if feature.area_focus == "right" else "right"
    else:
        feature.single_x += delta_x
    session.cursor.x_pixel = _x_value_to_pixel(feature.focused_x_value(), session.bounds, clamp=True)
    return True


def _toggle_area_focus(session, side):
    feature = session.tool_state.selected_feature()
    if feature is None or feature.mode != TOOL_AREA:
        return False
    feature.area_focus = side
    session.cursor.x_pixel = _x_value_to_pixel(feature.focused_x_value(), session.bounds, clamp=True)
    return True


def _handle_toolbox(session):
    selected = _open_simple_menu("Toolbox", GRAPH_TOOLBOX_ITEMS, "OK=run")
    if selected is None:
        return
    command = GRAPH_TOOLBOX_ITEMS[selected]
    if command == "Functions":
        _open_relations_menu(session)
    elif command == "Draw":
        session.set_status("Graph redrawn")
    elif command == "V-Window":
        _edit_bounds(session)
    elif command == "Zoom":
        _zoom_menu(session)
    elif command == "Trace":
        _toggle_trace(session)
    elif command == "G-Solve":
        _gsolve_menu(session)
    elif command == "Table":
        _table_generate(session)
    elif command == "Dynamic":
        _dynamic_menu(session)
    elif command == "Recursion":
        _recur_generate(session)
    elif command == "Conics":
        _conic_menu(session)
    elif command == "Features":
        _feature_add_menu(session)
    elif command == "Used Tools":
        _used_tools_menu(session)
    elif command == "Appearance":
        _appearance_menu(session)
    elif command == "Graph Memory":
        _graph_memory_menu(session)
    elif command == "Picture Memory":
        _picture_memory_menu(session)


def _relation_cycle(session, delta):
    enabled = session.enabled_relation_indices()
    if not enabled:
        return
    if session.cursor.graph_index not in enabled:
        session.cursor.graph_index = enabled[0]
        return
    current = enabled.index(session.cursor.graph_index)
    current = (current + delta) % len(enabled)
    session.cursor.graph_index = enabled[current]


def _run_graph_loop(session):
    keypad_state_manager_reset()
    session.cursor.graph_index = session.current_relation
    session.set_status("Toolbox for commands")
    prev_debounce = getattr(typer, "debounce_delay_time", None)

    def _set_fast_poll():
        if prev_debounce is not None:
            typer.debounce_delay_time = INPUT_POLL_SEC

    def _restore_default_poll():
        if prev_debounce is not None:
            typer.debounce_delay_time = prev_debounce

    try:
        _set_fast_poll()
        _render_graph(session)
        gc.collect()
        while True:
            key = typer.start_typing()
            full_replot = False
            overlay_refresh = False

            if key in ("alpha", "beta"):
                keypad_state_manager(x=key)
                continue

            if key in ("a", "A", "copy", "module"):
                _toggle_trace(session)
                full_replot = True

            elif key == "toolbox":
                _restore_default_poll()
                _handle_toolbox(session)
                _set_fast_poll()
                full_replot = True

            elif key == "+":
                _apply_zoom(session, ZOOM_IN_FACTOR)
                session.set_status("Zoom in")
                session.save()
                full_replot = True

            elif key == "-":
                _apply_zoom(session, ZOOM_OUT_FACTOR)
                session.set_status("Zoom out")
                session.save()
                full_replot = True

            elif key == ",":
                _restore_default_poll()
                _used_tools_menu(session)
                _set_fast_poll()
                full_replot = True

            elif key == "nav_l":
                if session.tool_state.selected_feature() is not None:
                    if _move_selected_tool(session, -1):
                        session.set_status("Tool moved")
                        full_replot = True
                elif session.cursor.active:
                    overlay_refresh = session.cursor.move(-1)
                else:
                    _apply_pan(session, "left")
                    session.set_status("Pan left")
                    session.save()
                    full_replot = True

            elif key == "nav_r":
                if session.tool_state.selected_feature() is not None:
                    if _move_selected_tool(session, 1):
                        session.set_status("Tool moved")
                        full_replot = True
                elif session.cursor.active:
                    overlay_refresh = session.cursor.move(1)
                else:
                    _apply_pan(session, "right")
                    session.set_status("Pan right")
                    session.save()
                    full_replot = True

            elif key == "nav_u":
                feature = session.tool_state.selected_feature()
                if feature is not None and feature.mode == TOOL_AREA:
                    _toggle_area_focus(session, "left")
                    session.set_status("Area left")
                    full_replot = True
                elif session.cursor.active:
                    _relation_cycle(session, -1)
                    session.set_status("Graph " + _relation_label(session.cursor.graph_index, session.relations[session.cursor.graph_index]))
                    overlay_refresh = True
                else:
                    _apply_pan(session, "up")
                    session.set_status("Pan up")
                    session.save()
                    full_replot = True

            elif key == "nav_d":
                feature = session.tool_state.selected_feature()
                if feature is not None and feature.mode == TOOL_AREA:
                    _toggle_area_focus(session, "right")
                    session.set_status("Area right")
                    full_replot = True
                elif session.cursor.active:
                    _relation_cycle(session, 1)
                    session.set_status("Graph " + _relation_label(session.cursor.graph_index, session.relations[session.cursor.graph_index]))
                    overlay_refresh = True
                else:
                    _apply_pan(session, "down")
                    session.set_status("Pan down")
                    session.save()
                    full_replot = True

            elif key == "F1":
                session.current_relation = (session.current_relation - 1) % MAX_RELATIONS
                session.cursor.graph_index = session.current_relation
                session.set_status("Current " + _relation_label(session.current_relation, session.relation()))
                overlay_refresh = True

            elif key == "F2":
                session.current_relation = (session.current_relation + 1) % MAX_RELATIONS
                session.cursor.graph_index = session.current_relation
                session.set_status("Current " + _relation_label(session.current_relation, session.relation()))
                overlay_refresh = True

            elif key == "F3":
                _restore_default_poll()
                _table_generate(session)
                _set_fast_poll()
                full_replot = True

            elif key == "F4":
                _restore_default_poll()
                _gsolve_menu(session)
                _set_fast_poll()
                full_replot = True

            elif key == "F5":
                _toggle_trace(session)
                full_replot = True

            elif key == "F6":
                _restore_default_poll()
                _handle_toolbox(session)
                _set_fast_poll()
                full_replot = True

            if full_replot:
                _render_graph(session)
                gc.collect()
            elif overlay_refresh:
                _refresh_overlay(session)
    finally:
        _restore_default_poll()


def graph(db={}):
    current_app[0] = "graph"
    current_app[1] = "scientific_calculator"
    try:
        _run_graph_loop(SESSION)
    finally:
        SESSION.save()
