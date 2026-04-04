# Copyright (c) 2025 CalSci
# Licensed under the MIT License.
#
# Graphing engine optimized for ST7565 + MicroPython:
# - Compiled expression cache
# - Adaptive per-column sampling
# - Discontinuity-safe line joining
# - Partial cursor refresh (column + bottom page)

try:
    import framebuf  # type: ignore
except ImportError:
    from mocking import framebuf  # type: ignore

import builtins
import gc
import math
import utime as time  # type:ignore

import process_modules.form_buffer_uploader as form_buffer_uploader_mod
from data_modules.object_handler import (
    current_app,
    chrs,
    display,
    form,
    form_refresh,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)
from process_modules.form_buffer import Form
from process_modules.form_buffer_uploader import Tbf as FormTbf
from process_modules.navigation import NavigationRequest, register_app_entry
from process_modules.ui_context import set_active_view

DEBUG_GRAPH = False

def _dprint(*args):
    if DEBUG_GRAPH:
        print(*args)


def _ticks_diff(now_ms, start_ms):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(now_ms, start_ms)
    return now_ms - start_ms


def _ticks_add(base_ms, delta_ms):
    if hasattr(time, "ticks_add"):
        return time.ticks_add(base_ms, delta_ms)
    return base_ms + delta_ms


def _back_guard_duration_ms(base_delay_sec=None):
    debounce_ms = 0
    try:
        debounce_ms = int(max(0.0, float(base_delay_sec or 0.0)) * 1000)
    except Exception:
        debounce_ms = 0

    duration_ms = debounce_ms + BACK_KEY_GUARD_EXTRA_MS
    if duration_ms < BACK_KEY_GUARD_MS:
        return BACK_KEY_GUARD_MS
    return duration_ms


def _translate_navigation_request(nav_request, consume_local_back=False):
    target = (nav_request.app_name, nav_request.group_name)
    if target == ("home", "root"):
        return "home"
    if target == ("installed_apps", "root"):
        if consume_local_back:
            register_app_entry("old_graph", "installed_apps")
        return "back"
    raise nav_request


def _start_typing_with_navigation_fallback(consume_local_back=False):
    try:
        return typer.start_typing()
    except NavigationRequest as nav_request:
        return _translate_navigation_request(
            nav_request,
            consume_local_back=consume_local_back,
        )


def _restore_old_graph_navigation_entry():
    register_app_entry("old_graph", "installed_apps")


# Display config
DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_PAGES = DISPLAY_HEIGHT // 8
PLOT_HEIGHT_WITH_CURSOR = 56
PLOT_PAGES = (PLOT_HEIGHT_WITH_CURSOR + 7) // 8
BOTTOM_PAGE_INDEX = DISPLAY_PAGES - 1
CHAR_HEIGHT = 8
CHAR_ADVANCE = 6

# Navigation / interaction config
ZOOM_IN_FACTOR = 0.9
ZOOM_OUT_FACTOR = 1.1
PAN_SHIFT_FACTOR = 0.09       #  set 
INPUT_POLL_MS = 0.5
INPUT_POLL_SEC = INPUT_POLL_MS / 1000.0
FAST_POLL_RESUME_DELAY_MS = 500
BACK_KEY_GUARD_MS = 180
BACK_KEY_GUARD_EXTRA_MS = 120

# Plot quality config
SAMPLES_PER_PX_MIN = 5
SAMPLES_PER_PX_MAX = 100
EVAL_ABS_CLAMP = 1e10

# Overlay menu config
MENU_TITLE_Y = 1
MENU_BOX_X = 2
MENU_BOX_Y = 11
MENU_BOX_W = 124
MENU_BOX_H = 44
TOOLBOX_BOX_X = MENU_BOX_X
TOOLBOX_BOX_Y = MENU_BOX_Y
TOOLBOX_BOX_W = MENU_BOX_W
TOOLBOX_BOX_H = 47


class OldGraphFormTbf(FormTbf):
    def __init__(self, disp_out, chrs, f_b, nav=None):
        super().__init__(disp_out=disp_out, chrs=chrs, f_b=f_b, nav=nav)
        self.steady_bottom_page = False

    def _flush_partial(self, framebuffer, flush_kwargs, force=False):
        graphics_callable = self.disp_out.graphics

        if not force:
            graphics_callable(framebuffer, **flush_kwargs)
            return

        wrapped_flushed = False
        try:
            graphics_callable(framebuffer, **flush_kwargs)
            wrapped_flushed = True
        except Exception:
            wrapped_flushed = False

        raw_graphics = self._unwrap_graphics(graphics_callable)
        if callable(raw_graphics) and raw_graphics is not graphics_callable:
            try:
                raw_graphics(framebuffer, **flush_kwargs)
                return
            except Exception:
                if wrapped_flushed:
                    return
                raise

        if not wrapped_flushed:
            graphics_callable(framebuffer, **flush_kwargs)

    def _flush(self, force=False):
        if not getattr(self, "steady_bottom_page", False):
            super()._flush(force=force)
            return

        flush_pages = max(1, DISPLAY_PAGES - 1)
        flush_len = DISPLAY_WIDTH * flush_pages
        self._flush_partial(
            memoryview(self.buf)[:flush_len],
            {
                "page": 0,
                "column": 0,
                "width": DISPLAY_WIDTH,
                "pages": flush_pages,
            },
            force=force,
        )

    def _layout_metrics(self, blocks):
        metrics = super()._layout_metrics(blocks)
        if not getattr(self.f_b, "old_graph_show_scrollbar", False):
            return metrics
        if not metrics.get("compact"):
            return metrics

        metrics = dict(metrics)
        if getattr(self.f_b, "old_graph_window_section_focus", False):
            uniform_h = max(metrics["row_h"], metrics["hfield_h"])
            metrics["show_scrollbar"] = True
            metrics["panel_h"] = form_buffer_uploader_mod.COMPACT_PANEL_H
            metrics["content_y"] = metrics["panel_y"] + 2
            metrics["content_h"] = max(12, metrics["panel_h"] - 4)
            metrics["row_h"] = uniform_h
            metrics["hfield_h"] = uniform_h
            metrics["vfield_h"] = uniform_h
            metrics["row_gap"] = 0
            metrics["content_w"] = max(
                12,
                metrics["panel_w"] - form_buffer_uploader_mod.SCROLL_W - 6,
            )
            metrics["scroll_x"] = (
                metrics["panel_x"]
                + metrics["panel_w"]
                - form_buffer_uploader_mod.SCROLL_W
                - 1
            )
            metrics["scroll_y"] = metrics["panel_y"] + 2
            metrics["scroll_h"] = metrics["content_h"]
            return metrics

        footer_top = form_buffer_uploader_mod.STATUS_Y
        panel_h = max(24, footer_top - metrics["panel_y"] - 1)
        metrics["show_scrollbar"] = True
        metrics["panel_h"] = panel_h
        metrics["content_h"] = max(12, panel_h - 4)
        metrics["row_gap"] = 0
        metrics["content_w"] = max(
            12,
            metrics["panel_w"] - form_buffer_uploader_mod.SCROLL_W - 6,
        )
        metrics["scroll_x"] = (
            metrics["panel_x"]
            + metrics["panel_w"]
            - form_buffer_uploader_mod.SCROLL_W
            - 1
        )
        metrics["scroll_y"] = metrics["panel_y"] + 2
        metrics["scroll_h"] = metrics["content_h"]
        return metrics

    def _draw_compact_horizontal_field(self, field_y, block, selected, metrics):
        if not getattr(self.f_b, "old_graph_home_tight_labels", False):
            return super()._draw_compact_horizontal_field(field_y, block, selected, metrics)

        field_y = int(field_y)
        content_x = metrics["content_x"]
        content_w = metrics["content_w"]
        field_h = metrics["hfield_h"]
        label = block.get("label", "")
        input_active = getattr(self.f_b, "menu_cursor", -1) == block.get("input_index")
        label_w = max(1, form_buffer_uploader_mod._text_width(label) + 1)
        max_label_w = max(
            1,
            content_w - form_buffer_uploader_mod.COMPACT_HFIELD_MIN_INPUT_W,
        )
        if label_w > max_label_w:
            label_w = max_label_w

        input_x = content_x + label_w + 1
        input_w = max(
            form_buffer_uploader_mod.COMPACT_HFIELD_MIN_INPUT_W,
            content_w - label_w - 1,
        )
        input_y = field_y + form_buffer_uploader_mod.COMPACT_HFIELD_INPUT_Y_OFFSET
        input_h = min(
            field_h,
            max(8, form_buffer_uploader_mod.COMPACT_HFIELD_INPUT_H),
        )
        text_x = input_x + form_buffer_uploader_mod.COMPACT_HFIELD_INPUT_INSET_X
        text_max_w = max(
            6,
            input_w
            - (
                form_buffer_uploader_mod.COMPACT_HFIELD_INPUT_INSET_X
                + form_buffer_uploader_mod.COMPACT_HFIELD_INPUT_RIGHT_PAD
            ),
        )
        view = self._input_view(
            block,
            input_active,
            visible_chars=form_buffer_uploader_mod._max_chars_for_width(text_max_w),
        )

        if selected:
            self._fill_rect(content_x, field_y, label_w, field_h, 1)

        self._draw_text_in_rect(
            label,
            content_x,
            field_y + form_buffer_uploader_mod.COMPACT_HFIELD_LABEL_PAD_Y,
            label_w,
            max(1, field_h - form_buffer_uploader_mod.COMPACT_HFIELD_LABEL_PAD_Y),
            color=0 if selected else 1,
            align="left",
        )

        if form_buffer_uploader_mod.COMPACT_HFIELD_INPUT_RADIUS > 0:
            self._rounded_rect(
                input_x,
                input_y,
                input_w,
                input_h,
                color=1,
                fill=False,
                radius=form_buffer_uploader_mod.COMPACT_HFIELD_INPUT_RADIUS,
            )
        else:
            self._rect(input_x, input_y, input_w, input_h, 1)
        self._draw_text(
            view["visible_text"],
            text_x,
            input_y
            + max(0, (input_h - form_buffer_uploader_mod.CHAR_HEIGHT) // 2),
            color=1,
            max_width=text_max_w,
        )

        if input_active and self._cursor_visible:
            visible_cursor = self.f_b.inp_cursor() - view["display_pos"]
            if visible_cursor < 0:
                visible_cursor = 0
            if visible_cursor > view["visible_chars"]:
                visible_cursor = view["visible_chars"]
            cursor_x = min(
                input_x + input_w - form_buffer_uploader_mod.COMPACT_HFIELD_CURSOR_RIGHT_PAD,
                text_x + visible_cursor * form_buffer_uploader_mod.CHAR_ADVANCE,
            )
            self._draw_input_cursor(cursor_x, input_y, input_h)

        if view["has_overflow"]:
            self._draw_horizontal_scrollbar(
                input_x + form_buffer_uploader_mod.COMPACT_HFIELD_SCROLL_INSET_X,
                input_y + input_h - 2,
                max(
                    8,
                    input_w
                    - (
                        form_buffer_uploader_mod.COMPACT_HFIELD_SCROLL_INSET_X
                        + form_buffer_uploader_mod.COMPACT_HFIELD_SCROLL_RIGHT_PAD
                    ),
                ),
                max(view["visible_chars"], len(view["value_text"])),
                view["visible_chars"],
                view["display_pos"],
                color=1,
        )

    def _draw_boxed_row(self, row_y, text_value, selected, metrics):
        if not getattr(self.f_b, "old_graph_window_section_focus", False):
            return super()._draw_boxed_row(row_y, text_value, selected, metrics)

        text_value = str(text_value or "")
        if text_value not in ("RECT System", "POLAR System"):
            return super()._draw_boxed_row(row_y, text_value, selected, metrics)

        row_y = int(row_y)
        content_x = metrics["content_x"]
        content_w = metrics["content_w"]
        row_h = metrics["row_h"]

        self._fill_rect(content_x, row_y, content_w, row_h, 0)
        self._rect(content_x, row_y, content_w, row_h, 1)
        self._draw_text_in_rect(
            self._row_text_value(
                text_value,
                content_w - (form_buffer_uploader_mod.COMPACT_ROW_TEXT_PAD_X * 2),
                selected=False,
            ),
            content_x + form_buffer_uploader_mod.COMPACT_ROW_TEXT_PAD_X,
            row_y + 2,
            content_w - (form_buffer_uploader_mod.COMPACT_ROW_TEXT_PAD_X * 2),
            max(1, row_h - 2),
            color=1,
            align="left",
        )

    def _refresh_boxed(self, state="", force=False):
        if not getattr(self.f_b, "old_graph_window_section_focus", False):
            return super()._refresh_boxed(state=state, force=force)

        self._sync_blink_signature()
        state = self._normalized_state(state)
        blocks = self._boxed_blocks()
        metrics = self._layout_metrics(blocks)
        selected_index = self._selected_block_index(blocks)
        top_index, bottom_index = self._visible_block_window(blocks, selected_index, metrics)

        self._clear()
        if metrics.get("show_title"):
            self._draw_text_center(self._title_text(), form_buffer_uploader_mod.TITLE_Y, color=1)
        self._rect(
            metrics["panel_x"],
            metrics["panel_y"],
            metrics["panel_w"],
            metrics["panel_h"],
            1,
        )

        visible_blocks = blocks[top_index:bottom_index]
        used_h = 0
        for block in visible_blocks:
            used_h += self._block_height(block, metrics)

        gap_count = max(1, len(visible_blocks) + 1)
        extra_h = max(0, metrics["content_h"] - used_h)
        base_gap = extra_h // gap_count
        remainder = extra_h % gap_count
        gap_sizes = [
            base_gap + (1 if gap_index < remainder else 0)
            for gap_index in range(gap_count)
        ]

        current_y = metrics["content_y"] + gap_sizes[0]
        for local_index, block in enumerate(visible_blocks):
            block_index = top_index + local_index
            selected = block_index == selected_index
            block_type = block.get("type")
            if block_type == "field":
                self._draw_boxed_field(current_y, block, selected, metrics)
            elif block_type == "link":
                self._draw_link_row(current_y, block, selected, metrics)
            elif block_type == "button":
                self._draw_button_row(current_y, block, selected, metrics)
            else:
                self._draw_boxed_row(current_y, block.get("text", ""), selected, metrics)
            current_y += self._block_height(block, metrics)
            if local_index + 1 < len(visible_blocks):
                current_y += gap_sizes[local_index + 1]

        self._draw_vertical_scrollbar(metrics, len(blocks), top_index, bottom_index - top_index)
        if state != "":
            self._draw_footer(state=state)
        self._flush(force=force)

        if self.nav is not None:
            nav_overlay_visible = (
                state != ""
                and state == self.nav.current_state()
                and self.nav.is_visible()
            )
            self.nav.set_restore_callback(
                self.restore_bottom_row if nav_overlay_visible else None
            )

        self.last_state = state

MENU_VISIBLE_ROWS = 3
MENU_SCROLL_W = 4
MENU_ROW_X = MENU_BOX_X + 2
MENU_ROW_Y = MENU_BOX_Y + 2
MENU_ROW_W = MENU_BOX_W - MENU_SCROLL_W - 5
MENU_ROW_H = 13
MENU_ROW_GAP = 1
MENU_CHECKBOX_SIZE = 7
TOOLBOX_VISIBLE_ROWS = 4
TOOLBOX_ROW_X = TOOLBOX_BOX_X + 2
TOOLBOX_ROW_Y = TOOLBOX_BOX_Y + 2
TOOLBOX_ROW_W = TOOLBOX_BOX_W - MENU_SCROLL_W - 5
TOOLBOX_ROW_H = 10
TOOLBOX_ROW_GAP = 1

# Reused tiny buffers for partial column updates.
_CURSOR_COL_BUF_A = bytearray(PLOT_PAGES)
_CURSOR_COL_BUF_B = bytearray(PLOT_PAGES)

# Expression compile cache
_EVAL_CACHE = {}


EVAL_GLOBALS = {
    "__builtins__": {},
    # Functions
    "abs": abs,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "ceil": math.ceil,
    "copysign": math.copysign,
    "degrees": math.degrees,
    "exp": math.exp,
    "fabs": math.fabs,
    "floor": math.floor,
    "fmod": math.fmod,
    "frexp": math.frexp,
    "ldexp": math.ldexp,
    "log": math.log,
    "modf": math.modf,
    "pow": math.pow,
    "radians": math.radians,
    "sqrt": math.sqrt,
    "trunc": math.trunc,
    # Constants
    "pi": math.pi,
    "e": math.e,
}


class MediumDigits:
    """5x7 font for cursor coordinate text."""

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
        "x": [0x44, 0x28, 0x10, 0x28, 0x44],
        "y": [0x0C, 0x50, 0x50, 0x50, 0x3C],
        "u": [0x3C, 0x40, 0x40, 0x20, 0x7C],
        "n": [0x7C, 0x08, 0x04, 0x04, 0x78],
        "d": [0x38, 0x54, 0x54, 0x54, 0x18],
        "e": [0x38, 0x54, 0x54, 0x54, 0x18],
        "f": [0x08, 0x7E, 0x09, 0x01, 0x02],
    }

    @classmethod
    def get_char(cls, char):
        return cls.data.get(char, cls.data[" "])


class CursorState:
    """Cursor state for interactive graph mode."""

    def __init__(self):
        self.active = False
        self.x_pixel = DISPLAY_WIDTH // 2
        self.prev_x_pixel = self.x_pixel

    def toggle(self):
        self.active = not self.active
        self.prev_x_pixel = self.x_pixel

    def move(self, direction):
        self.prev_x_pixel = self.x_pixel
        if direction == "left" and self.x_pixel > 0:
            self.x_pixel -= 1
            return True
        if direction == "right" and self.x_pixel < DISPLAY_WIDTH - 1:
            self.x_pixel += 1
            return True
        return False


TOOL_NONE = 0
TOOL_AREA = 1
TOOL_TANGENT = 2
TOOL_NORMAL = 3
TOOL_COORDINATES = 4
TOOL_MENU_ITEMS = (TOOL_AREA, TOOL_TANGENT, TOOL_NORMAL, TOOL_COORDINATES)
TOOL_LABELS = {
    TOOL_AREA: "Area",
    TOOL_TANGENT: "Tangent",
    TOOL_NORMAL: "Normal",
    TOOL_COORDINATES: "Coordinates",
}
TOOL_SHORT_LABELS = {
    TOOL_AREA: "A",
    TOOL_TANGENT: "T",
    TOOL_NORMAL: "N",
    TOOL_COORDINATES: "C",
}
TOOLBOX_CANCEL_BACK = "__toolbox_cancel_back__"
TOOLBOX_CLEAR_SELECTION = "__toolbox_clear_selection__"

MAX_GRAPH_COUNT = 10
HOME_INPUT_COLS = 16
HOME_HFIELD_LABEL_W = 15
HOME_HFIELD_LABEL_PAD_X = 0

GRAPH_TYPE_RECT = "rect"
GRAPH_TYPE_POLAR = "polar"
GRAPH_TYPES = (GRAPH_TYPE_RECT, GRAPH_TYPE_POLAR)
GRAPH_TYPE_LABELS = {
    GRAPH_TYPE_RECT: "RECT",
    GRAPH_TYPE_POLAR: "POLAR",
}

GRAPH_STYLE_NORMAL = "normal"
GRAPH_STYLE_THICK = "thick"
GRAPH_STYLE_BROKEN = "broken"
GRAPH_STYLE_DOTTED = "dot"
GRAPH_STYLES = (
    GRAPH_STYLE_NORMAL,
    GRAPH_STYLE_THICK,
    GRAPH_STYLE_BROKEN,
    GRAPH_STYLE_DOTTED,
)
GRAPH_STYLE_LABELS = {
    GRAPH_STYLE_NORMAL: "NORMAL",
    GRAPH_STYLE_THICK: "THICK",
    GRAPH_STYLE_BROKEN: "BROKEN",
    GRAPH_STYLE_DOTTED: "DOTTED",
}
GRAPH_STYLE_ICONS = {
    GRAPH_STYLE_NORMAL: "(------)",
    GRAPH_STYLE_THICK: "(======)",
    GRAPH_STYLE_BROKEN: "(== ==)",
    GRAPH_STYLE_DOTTED: "(- - -)",
}

HOME_TOOLBOX_TYPE_ROW = 0
HOME_TOOLBOX_STYLE_ROW = 1
HOME_TOOLBOX_WINDOW_ROW = 2
GRAPH_CONFIG_BOX_X = 2
GRAPH_CONFIG_BOX_Y = 9
GRAPH_CONFIG_BOX_W = 124
GRAPH_CONFIG_BOX_H = 54
GRAPH_CONFIG_CONTENT_X = GRAPH_CONFIG_BOX_X + 2
GRAPH_CONFIG_CONTENT_Y = GRAPH_CONFIG_BOX_Y + 2
GRAPH_CONFIG_CONTENT_W = GRAPH_CONFIG_BOX_W - 4
GRAPH_CONFIG_LABEL_H = 8
GRAPH_CONFIG_VALUE_H = 8
GRAPH_CONFIG_LABEL_VALUE_GAP = 2
GRAPH_CONFIG_PAIR_H = (
    GRAPH_CONFIG_LABEL_H + GRAPH_CONFIG_LABEL_VALUE_GAP + GRAPH_CONFIG_VALUE_H
)
GRAPH_CONFIG_VIEW_H = 8
GRAPH_CONFIG_OUTER_GAP = 1
GRAPH_CONFIG_ITEM_GAP = 2


def _graph_input_key(index):
    return "inp_" + str(index)


def _graph_label(index):
    return "Y" + str(index + 1)


def _copy_bounds_dict(bounds):
    return {
        "x_min": float(bounds["x_min"]),
        "x_max": float(bounds["x_max"]),
        "y_min": float(bounds["y_min"]),
        "y_max": float(bounds["y_max"]),
    }


def _copy_polar_bounds(bounds):
    return {
        "theta_min": float(bounds["theta_min"]),
        "theta_max": float(bounds["theta_max"]),
        "r_max": float(bounds["r_max"]),
        "r_min": float(bounds["r_min"]),
    }


def _default_rect_bounds():
    return {
        "x_min": -12.0,
        "x_max": 12.0,
        "y_min": -6.0,
        "y_max": 6.0,
    }


def _default_polar_bounds():
    return {
        "theta_min": 0.0,
        "theta_max": math.pi,
        "r_max": 12.0,
        "r_min": -12.0,
    }


def _default_graph_entry(index):
    expr = "x*sin(x)" if index == 0 else ""
    return {
        "expr": expr,
        "type": GRAPH_TYPE_RECT,
        "style": GRAPH_STYLE_NORMAL,
    }


def _create_graph_home_state():
    graphs = []
    for index in range(MAX_GRAPH_COUNT):
        graphs.append(_default_graph_entry(index))
    return {
        "graphs": graphs,
        "rect_bounds": _default_rect_bounds(),
        "polar_bounds": _default_polar_bounds(),
        "focus_graph_index": 0,
    }


def _capture_form_state():
    return {
        "ui_style": getattr(form, "ui_style", "classic"),
        "focus_inputs_only": getattr(form, "focus_inputs_only", False),
        "blink_cursor": getattr(form, "blink_cursor", False),
        "title": getattr(form, "title", ""),
        "input_cols": getattr(form, "input_cols", 19),
        "compact_hfield_label_w_present": hasattr(form, "compact_hfield_label_w"),
        "compact_hfield_label_w": getattr(form, "compact_hfield_label_w", None),
        "compact_hfield_label_pad_x_present": hasattr(form, "compact_hfield_label_pad_x"),
        "compact_hfield_label_pad_x": getattr(form, "compact_hfield_label_pad_x", None),
        "old_graph_home_tight_labels_present": hasattr(form, "old_graph_home_tight_labels"),
        "old_graph_home_tight_labels": getattr(form, "old_graph_home_tight_labels", None),
        "old_graph_window_section_focus_present": hasattr(form, "old_graph_window_section_focus"),
        "old_graph_window_section_focus": getattr(form, "old_graph_window_section_focus", None),
        "old_graph_show_scrollbar_present": hasattr(form, "old_graph_show_scrollbar"),
        "old_graph_show_scrollbar": getattr(form, "old_graph_show_scrollbar", None),
        "bottom_page_text_provider_present": hasattr(form, "bottom_page_text_provider"),
        "bottom_page_text_provider": getattr(form, "bottom_page_text_provider", None),
        "form_list": list(getattr(form, "form_list", [])),
        "input_list": dict(getattr(form, "input_list", {})),
        "menu_cursor": getattr(form, "menu_cursor", 0),
        "input_cursor": getattr(form, "input_cursor", 0),
        "input_display_position": getattr(form, "input_display_position", 0),
    }


def _restore_form_state(previous):
    form.ui_style = previous["ui_style"]
    form.focus_inputs_only = previous["focus_inputs_only"]
    form.blink_cursor = previous["blink_cursor"]
    form.title = previous["title"]
    form.input_cols = previous["input_cols"]
    if previous.get("compact_hfield_label_w_present"):
        form.compact_hfield_label_w = previous.get("compact_hfield_label_w")
    elif hasattr(form, "compact_hfield_label_w"):
        delattr(form, "compact_hfield_label_w")
    if previous.get("compact_hfield_label_pad_x_present"):
        form.compact_hfield_label_pad_x = previous.get("compact_hfield_label_pad_x")
    elif hasattr(form, "compact_hfield_label_pad_x"):
        delattr(form, "compact_hfield_label_pad_x")
    if previous.get("old_graph_home_tight_labels_present"):
        form.old_graph_home_tight_labels = previous.get("old_graph_home_tight_labels")
    elif hasattr(form, "old_graph_home_tight_labels"):
        delattr(form, "old_graph_home_tight_labels")
    if previous.get("old_graph_window_section_focus_present"):
        form.old_graph_window_section_focus = previous.get("old_graph_window_section_focus")
    elif hasattr(form, "old_graph_window_section_focus"):
        delattr(form, "old_graph_window_section_focus")
    if previous.get("old_graph_show_scrollbar_present"):
        form.old_graph_show_scrollbar = previous.get("old_graph_show_scrollbar")
    elif hasattr(form, "old_graph_show_scrollbar"):
        delattr(form, "old_graph_show_scrollbar")
    if previous.get("bottom_page_text_provider_present"):
        form.bottom_page_text_provider = previous.get("bottom_page_text_provider")
    elif hasattr(form, "bottom_page_text_provider"):
        delattr(form, "bottom_page_text_provider")
    form.form_list = previous["form_list"]
    form.input_list = previous["input_list"]
    form.update()
    form.menu_cursor = previous["menu_cursor"]
    form.input_cursor = previous["input_cursor"]
    form.input_display_position = previous["input_display_position"]
    try:
        form._sync_input_view(prefer_end=False)
    except Exception:
        pass


def _graph_index_from_form():
    active_key = None
    if hasattr(form, "active_input_key"):
        active_key = form.active_input_key()
    if active_key is None:
        return None
    if not str(active_key).startswith("inp_"):
        return None
    try:
        return int(str(active_key)[4:])
    except Exception:
        return None


def _sync_graph_state_from_form(graph_state):
    for index, graph in enumerate(graph_state["graphs"]):
        value = str(form.input_list.get(_graph_input_key(index), " ") or " ").strip()
        graph["expr"] = value
    focus_index = _graph_index_from_form()
    if focus_index is not None and 0 <= focus_index < len(graph_state["graphs"]):
        graph_state["focus_graph_index"] = focus_index


def _apply_home_form(graph_state):
    form.ui_style = "buffer"
    form.focus_inputs_only = True
    form.blink_cursor = True
    form.title = ""
    form.input_cols = HOME_INPUT_COLS
    form.compact_hfield_label_w = HOME_HFIELD_LABEL_W
    form.compact_hfield_label_pad_x = HOME_HFIELD_LABEL_PAD_X
    form.old_graph_home_tight_labels = True
    if hasattr(form, "old_graph_window_section_focus"):
        delattr(form, "old_graph_window_section_focus")
    form.old_graph_show_scrollbar = True
    if hasattr(form, "bottom_page_text_provider"):
        delattr(form, "bottom_page_text_provider")

    input_list = {}
    form_list = []
    for index, graph in enumerate(graph_state["graphs"]):
        key = _graph_input_key(index)
        input_list[key] = str(graph.get("expr", "") or "").rstrip() + " "
        form_list.append("@input_h " + _graph_label(index))
        form_list.append(key)

    form.input_list = input_list
    form.form_list = form_list
    form.update()

    focus_index = min(
        max(0, int(graph_state.get("focus_graph_index", 0) or 0)),
        len(graph_state["graphs"]) - 1,
    )
    form.menu_cursor = focus_index * 2 + 1
    try:
        form._sync_input_view(prefer_end=False)
    except Exception:
        pass


def _focused_graph_entry(graph_state):
    focus_index = int(graph_state.get("focus_graph_index", 0) or 0)
    if focus_index < 0 or focus_index >= len(graph_state["graphs"]):
        focus_index = 0
    return graph_state["graphs"][focus_index]


def _home_footer_text(graph_state):
    graph = _focused_graph_entry(graph_state)
    graph_type = GRAPH_TYPE_LABELS.get(graph.get("type"), "RECT")
    style = graph.get("style", GRAPH_STYLE_NORMAL)
    style_icon = GRAPH_STYLE_ICONS.get(style, GRAPH_STYLE_ICONS[GRAPH_STYLE_NORMAL])
    base = graph_type + " "
    padding = 21 - len(base) - len(style_icon)
    if padding < 1:
        padding = 1
    return (base + (" " * padding) + style_icon)[:21]


def _draw_status_page(text_value):
    text_value = str(text_value or "")[:21]
    page_buf = bytearray(DISPLAY_WIDTH)
    page_fb = framebuf.FrameBuffer(page_buf, DISPLAY_WIDTH, 8, framebuf.MONO_VLSB)
    page_fb.fill(0)
    if text_value:
        text_x = max(0, (DISPLAY_WIDTH - len(text_value) * 8) // 2)
        page_fb.text(text_value, text_x, 0, 1)
    display.graphics(page_buf, page=BOTTOM_PAGE_INDEX, column=0, width=DISPLAY_WIDTH, pages=1)
    set_active_view("form")


def _visible_nav_overlay_state():
    try:
        state = str(nav.current_state() or "")
    except Exception:
        return ""

    if hasattr(form_refresh, "_normalized_state"):
        try:
            return str(form_refresh._normalized_state(state) or "")
        except Exception:
            pass

    try:
        if not nav.is_visible():
            return ""
    except Exception:
        pass
    return state


def _draw_home_navbar(graph_state):
    footer_text = _home_footer_text(graph_state)
    overlay_state = _visible_nav_overlay_state()
    if overlay_state != "":
        try:
            nav.set_restore_callback(lambda: _draw_status_page(footer_text))
        except Exception:
            pass
        nav.draw_state(overlay_state)
        return

    try:
        nav.set_restore_callback(None)
    except Exception:
        pass
    _draw_status_page(footer_text)


def _set_home_footer_steady(enabled):
    if hasattr(form_refresh, "steady_bottom_page"):
        form_refresh.steady_bottom_page = bool(enabled)


def _refresh_home_form(graph_state, force=False):
    _sync_graph_state_from_form(graph_state)
    _set_home_footer_steady(True)
    form_refresh.refresh(state="", force=force)
    _draw_home_navbar(graph_state)


def _cycle_sequence_value(sequence, current, step):
    if current in sequence:
        index = sequence.index(current)
    else:
        index = 0
    return sequence[(index + step) % len(sequence)]


class ToolFeature:
    """Single graph feature instance with x-value locking."""

    def __init__(self, mode, instance_number):
        self.mode = mode
        self.instance_number = instance_number
        self.area_x_left = 0.0
        self.area_x_right = 0.0
        self.area_focus = "right"
        self.single_x = 0.0

    def focused_x_value(self):
        if self.mode == TOOL_AREA:
            return self.area_x_left if self.area_focus == "left" else self.area_x_right
        return self.single_x

    def area_interval(self):
        if self.area_x_left <= self.area_x_right:
            return self.area_x_left, self.area_x_right
        return self.area_x_right, self.area_x_left

    def _sync_cursor(self, cursor, bounds):
        cursor.prev_x_pixel = cursor.x_pixel
        cursor.x_pixel = _x_value_to_pixel(self.focused_x_value(), bounds, clamp=True)

    def sync_cursor(self, cursor, bounds):
        self._sync_cursor(cursor, bounds)

    def initialize_from_cursor(self, cursor, bounds):
        x_center = _x_pixel_to_value(cursor.x_pixel, bounds)
        if self.mode == TOOL_AREA:
            x_step = _x_step_for_one_pixel(bounds)
            if x_step <= 0:
                x_step = 1e-6
            self.area_x_left = x_center - (10 * x_step)
            self.area_x_right = x_center + (10 * x_step)
            self.area_focus = "right"
        else:
            self.single_x = x_center

        self._sync_cursor(cursor, bounds)
        return True

    def focus_left(self, cursor, bounds):
        if self.mode != TOOL_AREA:
            return False
        self.area_focus = "left"
        self._sync_cursor(cursor, bounds)
        return True

    def focus_right(self, cursor, bounds):
        if self.mode != TOOL_AREA:
            return False
        self.area_focus = "right"
        self._sync_cursor(cursor, bounds)
        return True

    def move_focus(self, delta_px, bounds, cursor):
        x_step = _x_step_for_one_pixel(bounds)
        if x_step == 0:
            return False
        delta_x = delta_px * x_step

        if self.mode == TOOL_AREA:
            if self.area_focus == "left":
                self.area_x_left += delta_x
            else:
                self.area_x_right += delta_x

            if self.area_x_left > self.area_x_right:
                self.area_x_left, self.area_x_right = self.area_x_right, self.area_x_left
                self.area_focus = "left" if self.area_focus == "right" else "right"
        else:
            self.single_x += delta_x

        self._sync_cursor(cursor, bounds)
        return True


class ToolState:
    """Collection of graph features with one selected feature for editing."""

    def __init__(self):
        self.features = []
        self.selected_index = None
        self._counters = {
            TOOL_AREA: 0,
            TOOL_TANGENT: 0,
            TOOL_NORMAL: 0,
            TOOL_COORDINATES: 0,
        }

    @property
    def active(self):
        return len(self.features) > 0

    @property
    def mode(self):
        feature = self.selected_feature()
        if feature is None:
            return TOOL_NONE
        return feature.mode

    def selected_feature(self):
        if self.selected_index is None:
            return None
        if self.selected_index < 0 or self.selected_index >= len(self.features):
            return None
        return self.features[self.selected_index]

    def clear(self):
        self.features[:] = []
        self.selected_index = None
        for mode in self._counters:
            self._counters[mode] = 0

    def set_mode(self, mode, cursor, bounds):
        next_number = self._counters.get(mode, 0) + 1
        self._counters[mode] = next_number

        feature = ToolFeature(mode, next_number)
        feature.initialize_from_cursor(cursor, bounds)
        self.features.append(feature)
        self.selected_index = len(self.features) - 1
        feature.sync_cursor(cursor, bounds)
        return True

    def replace_mode(self, mode, cursor, bounds):
        self.clear()
        return self.set_mode(mode, cursor, bounds)

    def sync_cursor(self, cursor, bounds):
        feature = self.selected_feature()
        if feature is not None:
            feature.sync_cursor(cursor, bounds)

    def focus_left(self, cursor, bounds):
        feature = self.selected_feature()
        if feature is None:
            return False
        return feature.focus_left(cursor, bounds)

    def focus_right(self, cursor, bounds):
        feature = self.selected_feature()
        if feature is None:
            return False
        return feature.focus_right(cursor, bounds)

    def move_focus(self, delta_px, bounds, cursor):
        feature = self.selected_feature()
        if feature is None:
            return False
        return feature.move_focus(delta_px, bounds, cursor)

    def select_index(self, index):
        if index < 0 or index >= len(self.features):
            return False
        changed = self.selected_index != index
        self.selected_index = index
        return changed

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

        if self.selected_index > index:
            self.selected_index -= 1
        elif self.selected_index == index and self.selected_index >= len(self.features):
            self.selected_index = len(self.features) - 1
        return True

    def count_by_mode(self, mode):
        count = 0
        for feature in self.features:
            if feature.mode == mode:
                count += 1
        return count


def draw_medium_text(fb, text_value, x, y):
    for char in text_value:
        char_data = MediumDigits.get_char(char)
        for col in range(5):
            byte = char_data[col]
            for row in range(7):
                if byte & (1 << row):
                    fb.pixel(x + col, y + row, 1)
        x += 6


def format_number(value):
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


def _display_full(fb_buf):
    set_active_view("graphics")
    display.graphics(fb_buf, page=0, column=0, width=DISPLAY_WIDTH, pages=DISPLAY_PAGES)


def _display_page(fb_buf, page_index):
    start = page_index * DISPLAY_WIDTH
    end = start + DISPLAY_WIDTH
    set_active_view("graphics")
    display.graphics(memoryview(fb_buf)[start:end], page=page_index, column=0, width=DISPLAY_WIDTH, pages=1)


def _display_plot_column(fb_buf, x_pixel, out_col_buf):
    if x_pixel < 0 or x_pixel >= DISPLAY_WIDTH:
        return
    idx = x_pixel
    for page in range(PLOT_PAGES):
        out_col_buf[page] = fb_buf[idx]
        idx += DISPLAY_WIDTH
    set_active_view("graphics")
    display.graphics(out_col_buf, page=0, column=x_pixel, width=1, pages=PLOT_PAGES)


def _samples_per_px_for_view(x_range):
    """Adaptive sampling by world-units per pixel (zoom-aware quality control)."""
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


def _make_eval_fn(expression, variable_names=("x",)):
    expression = str(expression or "").strip()
    if not expression:
        return None
    try:
        compiled = compile(expression, "<graph_expr>", "eval")
    except Exception:
        return None

    env = {}
    env.update(EVAL_GLOBALS)
    names = tuple(variable_names or ("x",))

    def _eval_value(value):
        for name in names:
            env[name] = value
        return eval(compiled, env)

    return _eval_value


def get_eval_fn(expression, variable_names=("x",)):
    cache_key = (str(expression or "").strip(), tuple(variable_names or ("x",)))
    if cache_key not in _EVAL_CACHE:
        _EVAL_CACHE[cache_key] = _make_eval_fn(cache_key[0], cache_key[1])
    return _EVAL_CACHE.get(cache_key)


def safe_eval(eval_fn, x_value):
    try:
        y_value = eval_fn(x_value)
        if y_value != y_value:
            return None
        if y_value > EVAL_ABS_CLAMP or y_value < -EVAL_ABS_CLAMP:
            return None
        return y_value
    except Exception:
        return None


def get_bounds():
    return {
        "x_min": eval(form.inp_list()["inp_1"], EVAL_GLOBALS),
        "x_max": eval(form.inp_list()["inp_2"], EVAL_GLOBALS),
        "y_min": eval(form.inp_list()["inp_3"], EVAL_GLOBALS),
        "y_max": eval(form.inp_list()["inp_4"], EVAL_GLOBALS),
    }


def update_bounds(bounds):
    form.input_list["inp_1"] = format_number(bounds["x_min"])
    form.input_list["inp_2"] = format_number(bounds["x_max"])
    form.input_list["inp_3"] = format_number(bounds["y_min"])
    form.input_list["inp_4"] = format_number(bounds["y_max"])


def apply_zoom(bounds, factor):
    x_range = bounds["x_max"] - bounds["x_min"]
    y_range = bounds["y_max"] - bounds["y_min"]
    x_center = (bounds["x_min"] + bounds["x_max"]) * 0.5
    y_center = (bounds["y_min"] + bounds["y_max"]) * 0.5
    new_x_range = x_range * factor
    new_y_range = y_range * factor
    return {
        "x_min": x_center - (new_x_range * 0.5),
        "x_max": x_center + (new_x_range * 0.5),
        "y_min": y_center - (new_y_range * 0.5),
        "y_max": y_center + (new_y_range * 0.5),
    }


def apply_pan(bounds, direction):
    x_range = bounds["x_max"] - bounds["x_min"]
    y_range = bounds["y_max"] - bounds["y_min"]
    out = bounds.copy()
    if direction == "up":
        delta = y_range * PAN_SHIFT_FACTOR
        out["y_min"] += delta
        out["y_max"] += delta
    elif direction == "down":
        delta = y_range * PAN_SHIFT_FACTOR
        out["y_min"] -= delta
        out["y_max"] -= delta
    elif direction == "left":
        delta = x_range * PAN_SHIFT_FACTOR
        out["x_min"] -= delta
        out["x_max"] -= delta
    elif direction == "right":
        delta = x_range * PAN_SHIFT_FACTOR
        out["x_min"] += delta
        out["x_max"] += delta
    return out


def _draw_axes(fb, x_min, x_max, y_min, y_max, x_scale, y_scale, plot_height):
    x_axis_y = -1
    y_axis_x = -1

    if y_min <= 0 <= y_max:
        x_axis_y = int((y_max / y_scale) + 0.5)
    if x_min <= 0 <= x_max:
        y_axis_x = int((0 - x_min) / x_scale + 0.5)

    if 0 <= x_axis_y < plot_height:
        fb.hline(0, x_axis_y, DISPLAY_WIDTH, 1)
    if 0 <= y_axis_x < DISPLAY_WIDTH:
        fb.vline(y_axis_x, 0, plot_height, 1)

def _styled_point(fb, x_px, y_px, style, seed, plot_height):
    if x_px < 0 or x_px >= DISPLAY_WIDTH or y_px < 0 or y_px >= plot_height:
        return
    if style == GRAPH_STYLE_DOTTED and (seed & 1):
        return
    fb.pixel(x_px, y_px, 1)
    if style == GRAPH_STYLE_THICK and x_px + 1 < DISPLAY_WIDTH:
        fb.pixel(x_px + 1, y_px, 1)
    elif style == GRAPH_STYLE_BROKEN and (seed % 4) < 2:
        if x_px + 1 < DISPLAY_WIDTH:
            fb.pixel(x_px + 1, y_px, 1)


def _styled_line(fb, x0, y0, x1, y1, style, plot_height):
    if style == GRAPH_STYLE_NORMAL and hasattr(fb, "line"):
        fb.line(x0, y0, x1, y1, 1)
        return

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    steps = dx if dx > dy else dy
    if steps <= 0:
        _styled_point(fb, x0, y0, style, 0, plot_height)
        return

    for idx in range(steps + 1):
        x_px = x0 + ((x1 - x0) * idx) // steps
        y_px = y0 + ((y1 - y0) * idx) // steps
        _styled_point(fb, x_px, y_px, style, idx, plot_height)


def plot_function(fb, eval_fn, bounds, plot_height, style=GRAPH_STYLE_NORMAL):
    x_min = bounds["x_min"]
    x_max = bounds["x_max"]
    y_min = bounds["y_min"]
    y_max = bounds["y_max"]

    if DISPLAY_WIDTH < 2 or plot_height < 2:
        return False

    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range == 0 or y_range == 0:
        return False

    x_scale = x_range / (DISPLAY_WIDTH - 1)
    y_scale = y_range / (plot_height - 1)
    inv_y_scale = 1.0 / y_scale

    spp = _samples_per_px_for_view(x_range)
    if spp < SAMPLES_PER_PX_MIN:
        spp = SAMPLES_PER_PX_MIN
    if spp > SAMPLES_PER_PX_MAX:
        spp = SAMPLES_PER_PX_MAX

    sample_step = x_scale / spp
    left_shift = x_scale * 0.5
    connect_limit = (plot_height * 3) // 5
    steep_span_limit = (plot_height * 3) // 4
    discontinuity_span_limit = (plot_height * 5) // 6
    center_idx = spp >> 1

    prev_valid = False
    prev_steep = False
    prev_x = 0
    prev_y = 0
    drawn_any = False

    for x_px in range(DISPLAY_WIDTH):
        x_center = x_min + (x_px * x_scale)
        x_left = x_center - left_shift

        col_min = plot_height
        col_max = -1
        rep_y = -1
        valid_count = 0

        for sample_idx in range(spp):
            x_val = x_left + ((sample_idx + 0.5) * sample_step)
            y_val = safe_eval(eval_fn, x_val)
            if y_val is None or y_val < y_min or y_val > y_max:
                continue

            y_px = int(((y_max - y_val) * inv_y_scale) + 0.5)
            if y_px < 0 or y_px >= plot_height:
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
            _styled_point(fb, x_px, rep_y, style, x_px, plot_height)
            drawn_any = True
            prev_valid = False
            prev_steep = True
            prev_x = x_px
            prev_y = rep_y
            continue

        if col_min == col_max:
            _styled_point(fb, x_px, col_min, style, x_px, plot_height)
            drawn_any = True
        else:
            for draw_y in range(col_min, col_max + 1):
                _styled_point(fb, x_px, draw_y, style, x_px + draw_y, plot_height)
            drawn_any = True

        is_steep = col_span > steep_span_limit

        if prev_valid and (not prev_steep) and (not is_steep):
            if abs(rep_y - prev_y) <= connect_limit:
                _styled_line(fb, prev_x, prev_y, x_px, rep_y, style, plot_height)

        prev_valid = True
        prev_steep = is_steep
        prev_x = x_px
        prev_y = rep_y

    return drawn_any


def _plot_polar_function(fb, eval_fn, display_bounds, polar_bounds, plot_height, style):
    theta_min = polar_bounds["theta_min"]
    theta_max = polar_bounds["theta_max"]
    r_min = polar_bounds["r_min"]
    r_max = polar_bounds["r_max"]
    theta_span = theta_max - theta_min
    if theta_span == 0:
        return False

    steps = int(abs(theta_span) * 48)
    if steps < 128:
        steps = 128
    elif steps > 720:
        steps = 720

    prev_valid = False
    prev_x = 0
    prev_y = 0
    drawn_any = False

    for index in range(steps + 1):
        theta_value = theta_min + (theta_span * index / steps)
        radius = safe_eval(eval_fn, theta_value)
        if radius is None or radius < r_min or radius > r_max:
            prev_valid = False
            continue

        x_value = radius * math.cos(theta_value)
        y_value = radius * math.sin(theta_value)
        x_px = _x_value_to_pixel(x_value, display_bounds, clamp=False)
        y_px = _y_value_to_pixel(y_value, display_bounds, plot_height)
        if x_px is None or y_px is None:
            prev_valid = False
            continue

        if prev_valid:
            _styled_line(fb, prev_x, prev_y, x_px, y_px, style, plot_height)
        else:
            _styled_point(fb, x_px, y_px, style, index, plot_height)

        drawn_any = True
        prev_valid = True
        prev_x = x_px
        prev_y = y_px

    return drawn_any


def _graph_eval_fn(graph):
    graph_type = graph.get("type", GRAPH_TYPE_RECT)
    expr = graph.get("expr", "")
    if graph_type == GRAPH_TYPE_POLAR:
        return get_eval_fn(expr, ("t", "theta", "x"))
    return get_eval_fn(expr, ("x",))


def _active_graph_indices(graph_state):
    indices = []
    for index, graph in enumerate(graph_state["graphs"]):
        if str(graph.get("expr", "") or "").strip():
            indices.append(index)
    return indices


def _primary_rect_graph_index(graph_state):
    focus_index = int(graph_state.get("focus_graph_index", 0) or 0)
    if 0 <= focus_index < len(graph_state["graphs"]):
        graph = graph_state["graphs"][focus_index]
        if (
            graph.get("type") == GRAPH_TYPE_RECT
            and str(graph.get("expr", "") or "").strip()
        ):
            return focus_index

    for index, graph in enumerate(graph_state["graphs"]):
        if (
            graph.get("type") == GRAPH_TYPE_RECT
            and str(graph.get("expr", "") or "").strip()
        ):
            return index
    return None


def _fmt_cursor_coord(value, prefix):
    if abs(value) < 0.01:
        text_value = prefix + " 0"
    elif abs(value) < 10:
        text_value = prefix + str(round(value, 2))
    else:
        text_value = prefix + str(int(value))
    return text_value[:8]


def _x_pixel_to_value(x_pixel, bounds):
    x_range = bounds["x_max"] - bounds["x_min"]
    if DISPLAY_WIDTH < 2:
        return bounds["x_min"]
    return bounds["x_min"] + (x_pixel / (DISPLAY_WIDTH - 1)) * x_range


def _x_step_for_one_pixel(bounds):
    if DISPLAY_WIDTH < 2:
        return 0.0
    return (bounds["x_max"] - bounds["x_min"]) / (DISPLAY_WIDTH - 1)


def _x_value_to_pixel(x_value, bounds, clamp=False):
    x_range = bounds["x_max"] - bounds["x_min"]
    if DISPLAY_WIDTH < 2 or x_range == 0:
        return 0 if clamp else None

    x_pos = ((x_value - bounds["x_min"]) / x_range) * (DISPLAY_WIDTH - 1)
    x_px = int(x_pos + 0.5)

    if clamp:
        if x_px < 0:
            return 0
        if x_px >= DISPLAY_WIDTH:
            return DISPLAY_WIDTH - 1
        return x_px

    if x_px < 0 or x_px >= DISPLAY_WIDTH:
        return None
    return x_px


def _y_value_to_pixel(y_value, bounds, plot_height):
    y_range = bounds["y_max"] - bounds["y_min"]
    if y_range == 0 or plot_height < 2:
        return None
    if y_value < bounds["y_min"] or y_value > bounds["y_max"]:
        return None
    y_px = int(((bounds["y_max"] - y_value) / y_range) * (plot_height - 1) + 0.5)
    if y_px < 0 or y_px >= plot_height:
        return None
    return y_px


def _compute_area_value(eval_fn, tool_feature):
    x0, x1 = tool_feature.area_interval()
    if x1 == x0:
        return 0.0

    span = x1 - x0
    samples = int(abs(span) * 32)
    if samples < 64:
        samples = 64
    elif samples > 2048:
        samples = 2048

    step = span / samples
    x = x0
    y_prev = safe_eval(eval_fn, x)
    if y_prev is None:
        return None

    area = 0.0
    for _ in range(samples):
        x += step
        y_now = safe_eval(eval_fn, x)
        if y_now is None:
            return None
        area += (y_prev + y_now) * 0.5 * step
        y_prev = y_now

    return area


def _draw_area_shade(fb, eval_fn, bounds, tool_feature, plot_height):
    x_left_val, x_right_val = tool_feature.area_interval()
    if x_right_val < bounds["x_min"] or x_left_val > bounds["x_max"]:
        return

    y_min = bounds["y_min"]
    y_max = bounds["y_max"]
    if y_min > 0 or y_max < 0:
        return

    y_range = y_max - y_min
    if y_range == 0:
        return

    y_scale = y_range / (plot_height - 1)
    axis_y = int((y_max / y_scale) + 0.5)
    if axis_y < 0 or axis_y >= plot_height:
        return

    draw_left_val = x_left_val if x_left_val > bounds["x_min"] else bounds["x_min"]
    draw_right_val = x_right_val if x_right_val < bounds["x_max"] else bounds["x_max"]
    x_left_px = _x_value_to_pixel(draw_left_val, bounds, clamp=True)
    x_right_px = _x_value_to_pixel(draw_right_val, bounds, clamp=True)
    if x_right_px < x_left_px:
        return

    for x_px in range(x_left_px, x_right_px + 1):
        if (x_px - x_left_px) & 1:
            continue

        x_val = _x_pixel_to_value(x_px, bounds)
        y_val = safe_eval(eval_fn, x_val)
        if y_val is None or y_val < y_min or y_val > y_max:
            continue

        y_px = int(((y_max - y_val) / y_scale) + 0.5)
        if y_px < 0 or y_px >= plot_height:
            continue

        top = axis_y if axis_y < y_px else y_px
        h = y_px - axis_y if y_px > axis_y else axis_y - y_px
        fb.vline(x_px, top, h + 1, 1)

    # Draw interval edges for easier identification when multiple areas are active.
    fb.vline(x_left_px, 0, plot_height, 1)
    if x_right_px != x_left_px:
        fb.vline(x_right_px, 0, plot_height, 1)


def _estimate_derivative(eval_fn, x_value, bounds):
    x_step = _x_step_for_one_pixel(bounds)
    if x_step == 0:
        return None
    h = abs(x_step) * 0.5
    if h < 1e-6:
        h = 1e-6

    y_prev = safe_eval(eval_fn, x_value - h)
    y_next = safe_eval(eval_fn, x_value + h)
    if y_prev is None or y_next is None:
        return None
    return (y_next - y_prev) / (2.0 * h)


def _draw_linear_feature(fb, bounds, plot_height, x0, y0, slope):
    x_min = bounds["x_min"]
    x_max = bounds["x_max"]
    y_min = bounds["y_min"]
    y_max = bounds["y_max"]
    x_range = x_max - x_min
    y_range = y_max - y_min
    if x_range == 0 or y_range == 0 or DISPLAY_WIDTH < 2:
        return

    prev_valid = False
    prev_x = 0
    prev_y = 0
    for x_px in range(DISPLAY_WIDTH):
        x_val = _x_pixel_to_value(x_px, bounds)
        y_val = y0 + (slope * (x_val - x0))
        if y_val < y_min or y_val > y_max:
            prev_valid = False
            continue

        y_px = _y_value_to_pixel(y_val, bounds, plot_height)
        if y_px is None:
            prev_valid = False
            continue

        fb.pixel(x_px, y_px, 1)
        if prev_valid:
            fb.line(prev_x, prev_y, x_px, y_px, 1)
        prev_valid = True
        prev_x = x_px
        prev_y = y_px


def _get_tangent_info(eval_fn, bounds, x_value):
    y_value = safe_eval(eval_fn, x_value)
    if y_value is None:
        return None, None
    slope = _estimate_derivative(eval_fn, x_value, bounds)
    return y_value, slope


def _draw_tangent_or_normal(fb, eval_fn, bounds, tool_feature, plot_height):
    x_value = tool_feature.single_x
    y_value, tan_slope = _get_tangent_info(eval_fn, bounds, x_value)
    if y_value is None or tan_slope is None:
        return

    if tool_feature.mode == TOOL_TANGENT:
        _draw_linear_feature(fb, bounds, plot_height, x_value, y_value, tan_slope)
    elif tool_feature.mode == TOOL_NORMAL:
        if abs(tan_slope) < 1e-9:
            x_px = _x_value_to_pixel(x_value, bounds, clamp=False)
            if x_px is not None:
                fb.vline(x_px, 0, plot_height, 1)
        else:
            _draw_linear_feature(fb, bounds, plot_height, x_value, y_value, -1.0 / tan_slope)

    x_px = _x_value_to_pixel(x_value, bounds, clamp=False)
    y_px = _y_value_to_pixel(y_value, bounds, plot_height)
    if x_px is None or y_px is None:
        return

    marker_x = x_px - 1 if x_px > 0 else 0
    marker_w = 3
    if marker_x + marker_w > DISPLAY_WIDTH:
        marker_w = DISPLAY_WIDTH - marker_x
    fb.hline(marker_x, y_px, marker_w, 1)

    marker_y = y_px - 1 if y_px > 0 else 0
    marker_h = 3
    if marker_y + marker_h > plot_height:
        marker_h = plot_height - marker_y
    fb.vline(x_px, marker_y, marker_h, 1)


def _format_value_short(value):
    abs_v = abs(value)
    if abs_v < 10:
        return str(round(value, 3))
    if abs_v < 1000:
        return str(round(value, 2))
    return "{:.3g}".format(value)


def _format_area_text(area_value):
    if area_value is None:
        return "A=undef"
    a = abs(area_value)
    if a < 1000:
        return "A=" + str(round(area_value, 4))
    return "A={:.4g}".format(area_value)


def _format_optional_value(value):
    if value is None:
        return "undef"
    return _format_value_short(value)


def _format_xy_text(x_value, y_value):
    return "x=" + _format_value_short(x_value) + " y=" + _format_optional_value(y_value)


def _format_area_info_text(tool_feature, area_value):
    x1_value, x2_value = tool_feature.area_interval()
    return (
        "x1="
        + _format_value_short(x1_value)
        + " x2="
        + _format_value_short(x2_value)
        + " area="
        + _format_optional_value(area_value)
    )


def _format_line_tool_text(tool_feature, x_value, y_value, tan_slope):
    info_text = _format_xy_text(x_value, y_value)
    if tool_feature.mode == TOOL_TANGENT:
        metric_value = None if tan_slope is None else tan_slope
        return info_text + " m=" + _format_optional_value(metric_value)

    if tan_slope is None:
        normal_value = None
    elif abs(tan_slope) < 1e-9:
        normal_value = "inf"
    else:
        normal_value = _format_value_short(-1.0 / tan_slope)

    if normal_value is None:
        normal_text = "undef"
    else:
        normal_text = str(normal_value)
    return info_text + " n=" + normal_text


def _tool_instance_label(tool_feature):
    return TOOL_SHORT_LABELS[tool_feature.mode] + str(tool_feature.instance_number)


def _tool_row_text(tool_feature, bounds):
    x_px = _x_value_to_pixel(tool_feature.focused_x_value(), bounds, clamp=True)
    row = _tool_instance_label(tool_feature)
    if tool_feature.mode == TOOL_AREA:
        side = "L" if tool_feature.area_focus == "left" else "R"
        row = row + " " + side
    row = row + " px" + str(x_px)
    return row


def _menu_top_index(item_count, selected_index, visible_rows=MENU_VISIBLE_ROWS):
    if item_count <= visible_rows:
        return 0
    if selected_index < 0:
        return 0
    if selected_index >= item_count:
        selected_index = item_count - 1
    top_index = selected_index - visible_rows + 1
    if top_index < 0:
        top_index = 0
    max_top = item_count - visible_rows
    if top_index > max_top:
        top_index = max_top
    return top_index


def _display_text(text_value):
    return str(text_value or "").replace("_", " ")


def _text_width(text_value):
    text_value = str(text_value or "")
    if not text_value:
        return 0
    return len(text_value) * CHAR_ADVANCE - 1


def _clip_text_px(text_value, max_width):
    text_value = _display_text(text_value)
    if max_width <= 0:
        return ""
    max_chars = max(1, (int(max_width) + 1) // CHAR_ADVANCE)
    if len(text_value) <= max_chars:
        return text_value
    if max_chars <= 3:
        return text_value[:max_chars]
    return text_value[: max_chars - 3] + "..."


def _draw_ui_text(fb, text_value, x, y, color=1, max_width=None):
    text_value = _display_text(text_value)
    if max_width is not None:
        text_value = _clip_text_px(text_value, max_width)

    color = 1 if color else 0
    cursor_x = int(x)
    y = int(y)
    for char in text_value:
        glyph = chrs.Chr2bytes(char)
        for col_idx, col_bits in enumerate(glyph):
            px = cursor_x + col_idx
            if px < 0 or px >= DISPLAY_WIDTH:
                continue
            for bit_idx in range(CHAR_HEIGHT):
                py = y + bit_idx
                if py < 0 or py >= DISPLAY_HEIGHT:
                    continue
                if col_bits & (1 << bit_idx):
                    fb.pixel(px, py, color)
        cursor_x += CHAR_ADVANCE
    return text_value


def _draw_menu_title(fb, text_value):
    text_value = str(text_value or "")
    title_x = max(0, (DISPLAY_WIDTH - _text_width(text_value)) // 2)
    _draw_ui_text(fb, text_value, title_x, MENU_TITLE_Y, 1)


def _draw_menu_shell(fb, title):
    fb.fill(0)
    _draw_menu_title(fb, title)
    fb.rect(MENU_BOX_X, MENU_BOX_Y, MENU_BOX_W, MENU_BOX_H, 1)


def _draw_toolbox_shell(fb, title):
    fb.fill(0)
    _draw_menu_title(fb, title)
    fb.rect(TOOLBOX_BOX_X, TOOLBOX_BOX_Y, TOOLBOX_BOX_W, TOOLBOX_BOX_H, 1)


def _draw_menu_scrollbar(fb, item_count, top_index, visible_rows=MENU_VISIBLE_ROWS):
    track_x = MENU_BOX_X + MENU_BOX_W - MENU_SCROLL_W - 1
    track_y = MENU_BOX_Y + 2
    track_h = MENU_BOX_H - 4

    fb.rect(track_x, track_y, MENU_SCROLL_W, track_h, 1)

    if item_count <= visible_rows:
        thumb_h = track_h - 2
        thumb_y = track_y + 1
    else:
        thumb_h = max(8, ((track_h - 2) * visible_rows) // item_count)
        max_top = item_count - visible_rows
        thumb_range = max(0, (track_h - 2) - thumb_h)
        thumb_y = track_y + 1 + (top_index * thumb_range // max_top)

    fb.fill_rect(track_x + 1, thumb_y, max(1, MENU_SCROLL_W - 2), thumb_h, 1)


def _draw_toolbox_scrollbar(fb, item_count, top_index):
    track_x = TOOLBOX_BOX_X + TOOLBOX_BOX_W - MENU_SCROLL_W - 1
    track_y = TOOLBOX_BOX_Y + 2
    track_h = TOOLBOX_BOX_H - 4

    fb.rect(track_x, track_y, MENU_SCROLL_W, track_h, 1)

    if item_count <= TOOLBOX_VISIBLE_ROWS:
        thumb_h = track_h - 2
        thumb_y = track_y + 1
    else:
        thumb_h = max(8, ((track_h - 2) * TOOLBOX_VISIBLE_ROWS) // item_count)
        max_top = item_count - TOOLBOX_VISIBLE_ROWS
        thumb_range = max(0, (track_h - 2) - thumb_h)
        thumb_y = track_y + 1 + (top_index * thumb_range // max_top)

    fb.fill_rect(track_x + 1, thumb_y, max(1, MENU_SCROLL_W - 2), thumb_h, 1)


def _draw_checkbox(fb, x, y, checked, color):
    color = 1 if color else 0
    fb.rect(x, y, MENU_CHECKBOX_SIZE, MENU_CHECKBOX_SIZE, color)
    if checked:
        fb.fill_rect(x + 2, y + 2, MENU_CHECKBOX_SIZE - 4, MENU_CHECKBOX_SIZE - 4, color)


def _draw_toolbox_row(fb, row_index, label, selected, checked):
    row_y = TOOLBOX_ROW_Y + row_index * (TOOLBOX_ROW_H + TOOLBOX_ROW_GAP)
    row_fill = 1 if selected else 0
    text_color = 0 if selected else 1
    checkbox_color = 0 if selected else 1

    fb.fill_rect(TOOLBOX_ROW_X, row_y, TOOLBOX_ROW_W, TOOLBOX_ROW_H, row_fill)
    fb.rect(TOOLBOX_ROW_X, row_y, TOOLBOX_ROW_W, TOOLBOX_ROW_H, 1)

    checkbox_x = TOOLBOX_ROW_X + 2
    checkbox_y = row_y + max(0, (TOOLBOX_ROW_H - MENU_CHECKBOX_SIZE) // 2)
    _draw_checkbox(fb, checkbox_x, checkbox_y, checked, checkbox_color)

    label_x = checkbox_x + MENU_CHECKBOX_SIZE + 4
    label_y = row_y + 1
    max_width = TOOLBOX_ROW_W - (label_x - TOOLBOX_ROW_X) - 2
    _draw_ui_text(fb, label, label_x, label_y, text_color, max_width=max_width)


def _draw_toolbox_menu(fb, fb_buf, selected_mode, tool_state):
    _draw_toolbox_shell(fb, "Toolbox")
    active_mode = tool_state.mode
    selected_index = TOOL_MENU_ITEMS.index(selected_mode)
    top_index = _menu_top_index(
        len(TOOL_MENU_ITEMS),
        selected_index,
        visible_rows=TOOLBOX_VISIBLE_ROWS,
    )

    for row_index in range(TOOLBOX_VISIBLE_ROWS):
        item_index = top_index + row_index
        if item_index >= len(TOOL_MENU_ITEMS):
            break
        mode = TOOL_MENU_ITEMS[item_index]
        is_selected = item_index == selected_index
        _draw_toolbox_row(
            fb,
            row_index,
            TOOL_LABELS[mode],
            selected=is_selected,
            checked=(mode == active_mode),
        )

    _draw_toolbox_scrollbar(fb, len(TOOL_MENU_ITEMS), top_index)
    _display_full(fb_buf)


def _open_toolbox_menu(fb, fb_buf, tool_state):
    if tool_state.mode in TOOL_MENU_ITEMS:
        selected_mode = tool_state.mode
    else:
        selected_mode = TOOL_AREA
    ignore_open_key = True

    while True:
        _draw_toolbox_menu(fb, fb_buf, selected_mode, tool_state)
        key = _start_typing_with_navigation_fallback(consume_local_back=True)

        if ignore_open_key and key == "toolbox":
            ignore_open_key = False
            continue
        ignore_open_key = False

        if key == "nav_u":
            idx = TOOL_MENU_ITEMS.index(selected_mode)
            selected_mode = TOOL_MENU_ITEMS[(idx - 1) % len(TOOL_MENU_ITEMS)]
        elif key == "nav_d":
            idx = TOOL_MENU_ITEMS.index(selected_mode)
            selected_mode = TOOL_MENU_ITEMS[(idx + 1) % len(TOOL_MENU_ITEMS)]
        elif key == "ok":
            if tool_state.active and tool_state.mode == selected_mode:
                return TOOLBOX_CLEAR_SELECTION
            return selected_mode
        elif key in ("AC", "nav_b", "-"):
            if tool_state.active:
                return TOOLBOX_CLEAR_SELECTION
        elif key == "back":
            return TOOLBOX_CANCEL_BACK
        elif key == "home":
            return "home"
        elif key in ("alpha", "beta"):
            keypad_state_manager(x=key)


def _draw_used_tools_menu(fb, fb_buf, tool_state, bounds, selected_index, scroll_index):
    fb.fill(0)
    fb.text("USED TOOLS", 28, 2, 1)

    total = len(tool_state.features)
    if total == 0:
        fb.text("No active tools", 20, 24, 1)
        fb.text("BACK=exit", 28, 54, 1)
        _display_full(fb_buf)
        return

    visible_rows = 3
    y = 14
    for row in range(visible_rows):
        idx = scroll_index + row
        if idx >= total:
            break
        tool_feature = tool_state.features[idx]
        prefix = ">" if idx == selected_index else " "
        marker = "*" if idx == tool_state.selected_index else " "
        line = prefix + marker + _tool_row_text(tool_feature, bounds)
        fb.text(line[:21], 0, y, 1)
        y += 13

    position_text = str(selected_index + 1) + "/" + str(total)
    fb.text(position_text[:5], 102, 2, 1)
    fb.text("OK=sel AC=del", 0, 54, 1)
    _display_full(fb_buf)


def _open_used_tools_menu(fb, fb_buf, tool_state, bounds):
    selected_index = tool_state.selected_index if tool_state.selected_index is not None else 0
    scroll_index = 0
    changed = False
    ignore_open_key = True

    while True:
        total = len(tool_state.features)
        if total > 0:
            if selected_index < 0:
                selected_index = 0
            elif selected_index >= total:
                selected_index = total - 1

            if selected_index < scroll_index:
                scroll_index = selected_index
            elif selected_index >= scroll_index + 3:
                scroll_index = selected_index - 2
        else:
            selected_index = 0
            scroll_index = 0

        _draw_used_tools_menu(fb, fb_buf, tool_state, bounds, selected_index, scroll_index)
        key = _start_typing_with_navigation_fallback(consume_local_back=True)

        if ignore_open_key and key == ",":
            ignore_open_key = False
            continue
        ignore_open_key = False

        if key == "nav_u" and total > 0:
            selected_index = (selected_index - 1) % total
        elif key == "nav_d" and total > 0:
            selected_index = (selected_index + 1) % total
        elif key in ("ok", "exe") and total > 0:
            if tool_state.select_index(selected_index):
                changed = True
            return changed
        elif key in ("AC", "nav_b", "-") and total > 0:
            tool_state.remove_index(selected_index)
            changed = True
        elif key in ("back", ",", "toolbox"):
            return changed
        elif key == "home":
            return "home"
        elif key in ("alpha", "beta"):
            keypad_state_manager(x=key)


def _draw_graph_config_shell(fb, title):
    fb.fill(0)
    _draw_menu_title(fb, title)
    fb.rect(
        GRAPH_CONFIG_BOX_X,
        GRAPH_CONFIG_BOX_Y,
        GRAPH_CONFIG_BOX_W,
        GRAPH_CONFIG_BOX_H,
        1,
    )


def _draw_graph_config_focus_text(fb, text_value, x, y, max_width=None):
    text_value = _display_text(text_value)
    if max_width is not None:
        text_value = _clip_text_px(text_value, max_width)
    text_w = _text_width(text_value)
    fill_x = max(0, int(x) - 1)
    fill_y = max(0, int(y) - 1)
    fill_w = min(DISPLAY_WIDTH - fill_x, text_w + 2)
    fill_h = min(DISPLAY_HEIGHT - fill_y, CHAR_HEIGHT + 1)
    if fill_w > 0:
        fb.fill_rect(fill_x, fill_y, fill_w, fill_h, 1)
    _draw_ui_text(fb, text_value, x, y, 0, max_width=max_width)


def _draw_graph_config_pair(fb, top_y, label_text, value_text, selected):
    value_y = top_y + GRAPH_CONFIG_LABEL_H + GRAPH_CONFIG_LABEL_VALUE_GAP

    _draw_ui_text(
        fb,
        label_text,
        GRAPH_CONFIG_CONTENT_X + 3,
        top_y,
        1,
        max_width=GRAPH_CONFIG_CONTENT_W - 6,
    )

    centered_x = GRAPH_CONFIG_CONTENT_X + max(
        0,
        (GRAPH_CONFIG_CONTENT_W - _text_width(value_text)) // 2,
    )
    if selected:
        _draw_graph_config_focus_text(
            fb,
            value_text,
            centered_x,
            value_y,
            max_width=GRAPH_CONFIG_CONTENT_W - 4,
        )
    else:
        _draw_ui_text(
            fb,
            value_text,
            centered_x,
            value_y,
            1,
            max_width=GRAPH_CONFIG_CONTENT_W - 4,
        )


def _draw_graph_config_link_row(fb, top_y, text_value, selected):
    text_x = GRAPH_CONFIG_CONTENT_X + 3
    text_y = top_y
    if selected:
        _draw_graph_config_focus_text(
            fb,
            text_value,
            text_x,
            text_y,
            max_width=GRAPH_CONFIG_CONTENT_W - 6,
        )
    else:
        _draw_ui_text(
            fb,
            text_value,
            text_x,
            text_y,
            1,
            max_width=GRAPH_CONFIG_CONTENT_W - 6,
        )


def _draw_graph_config_menu(fb, fb_buf, graph_index, graph_config):
    _draw_graph_config_shell(fb, _graph_label(graph_index))
    top_y = GRAPH_CONFIG_CONTENT_Y + GRAPH_CONFIG_OUTER_GAP
    _draw_graph_config_pair(
        fb,
        top_y,
        "Graph Type",
        "<" + GRAPH_TYPE_LABELS.get(graph_config["type"], "RECT") + ">",
        graph_config.get("_selected_row", 0) == HOME_TOOLBOX_TYPE_ROW,
    )
    top_y += GRAPH_CONFIG_PAIR_H + GRAPH_CONFIG_ITEM_GAP
    _draw_graph_config_pair(
        fb,
        top_y,
        "Graph Style",
        "<" + GRAPH_STYLE_LABELS.get(graph_config["style"], "NORMAL") + ">",
        graph_config.get("_selected_row", 0) == HOME_TOOLBOX_STYLE_ROW,
    )
    top_y += GRAPH_CONFIG_PAIR_H + GRAPH_CONFIG_ITEM_GAP
    _draw_graph_config_link_row(
        fb,
        top_y,
        "View Window >",
        graph_config.get("_selected_row", 0) == HOME_TOOLBOX_WINDOW_ROW,
    )
    _display_full(fb_buf)


def _configure_view_window_form(rect_bounds, polar_bounds):
    form.ui_style = "buffer"
    form.focus_inputs_only = True
    form.blink_cursor = True
    form.title = ""
    form.input_cols = HOME_INPUT_COLS
    form.old_graph_home_tight_labels = True
    form.old_graph_window_section_focus = True
    form.old_graph_show_scrollbar = True
    if hasattr(form, "compact_hfield_label_w"):
        delattr(form, "compact_hfield_label_w")
    if hasattr(form, "compact_hfield_label_pad_x"):
        delattr(form, "compact_hfield_label_pad_x")
    form.input_list = {
        "inp_0": format_number(rect_bounds["x_min"]),
        "inp_1": format_number(rect_bounds["x_max"]),
        "inp_2": format_number(rect_bounds["y_min"]),
        "inp_3": format_number(rect_bounds["y_max"]),
        "inp_4": format_number(polar_bounds["theta_min"]),
        "inp_5": format_number(polar_bounds["theta_max"]),
        "inp_6": format_number(polar_bounds["r_max"]),
        "inp_7": format_number(polar_bounds["r_min"]),
    }
    form.form_list = [
        "RECT System",
        "@input_h x min",
        "inp_0",
        "@input_h x max",
        "inp_1",
        "@input_h y min",
        "inp_2",
        "@input_h y max",
        "inp_3",
        "POLAR System",
        "@input_h T min",
        "inp_4",
        "@input_h T max",
        "inp_5",
        "@input_h R max",
        "inp_6",
        "@input_h R min",
        "inp_7",
    ]
    form.update()


def _parse_window_form_values():
    rect_bounds = {
        "x_min": float(eval(str(form.input_list["inp_0"]).strip() or "0", EVAL_GLOBALS)),
        "x_max": float(eval(str(form.input_list["inp_1"]).strip() or "0", EVAL_GLOBALS)),
        "y_min": float(eval(str(form.input_list["inp_2"]).strip() or "0", EVAL_GLOBALS)),
        "y_max": float(eval(str(form.input_list["inp_3"]).strip() or "0", EVAL_GLOBALS)),
    }
    polar_bounds = {
        "theta_min": float(eval(str(form.input_list["inp_4"]).strip() or "0", EVAL_GLOBALS)),
        "theta_max": float(eval(str(form.input_list["inp_5"]).strip() or "0", EVAL_GLOBALS)),
        "r_max": float(eval(str(form.input_list["inp_6"]).strip() or "0", EVAL_GLOBALS)),
        "r_min": float(eval(str(form.input_list["inp_7"]).strip() or "0", EVAL_GLOBALS)),
    }
    if rect_bounds["x_max"] == rect_bounds["x_min"]:
        raise ValueError("x range")
    if rect_bounds["y_max"] == rect_bounds["y_min"]:
        raise ValueError("y range")
    if polar_bounds["theta_max"] == polar_bounds["theta_min"]:
        raise ValueError("theta range")
    if polar_bounds["r_max"] == polar_bounds["r_min"]:
        raise ValueError("radius range")
    return rect_bounds, polar_bounds


def _edit_view_window(rect_bounds, polar_bounds):
    previous_form = _capture_form_state()
    status_text = [""]
    last_valid = [
        _copy_bounds_dict(rect_bounds),
        _copy_polar_bounds(polar_bounds),
    ]

    def _refresh_window_form():
        _set_home_footer_steady(False)
        form_refresh.refresh(state=nav.current_state())

    def _start_typing_with_window_idle():
        return _start_typing_with_navigation_fallback(consume_local_back=True)

    def _update_last_valid():
        try:
            parsed_rect, parsed_polar = _parse_window_form_values()
        except Exception:
            return False
        last_valid[0] = parsed_rect
        last_valid[1] = parsed_polar
        return True

    try:
        _configure_view_window_form(rect_bounds, polar_bounds)
        form.bottom_page_text_provider = lambda: status_text[0]
        _refresh_window_form()

        while True:
            key = _start_typing_with_window_idle()
            if key in ("ok", "exe"):
                if not _update_last_valid():
                    status_text[0] = "INPUT ERROR"
                    _refresh_window_form()
                    continue
                status_text[0] = ""
                return last_valid[0], last_valid[1]
            if key in ("back", "toolbox"):
                _update_last_valid()
                status_text[0] = ""
                return last_valid[0], last_valid[1]
            if key == "home":
                return "home"
            if key in ("alpha", "beta"):
                keypad_state_manager(x=key)
                form.update_buffer("")
            else:
                form.update_buffer(key)
            if _update_last_valid():
                status_text[0] = ""
            _refresh_window_form()
    finally:
        _restore_form_state(previous_form)


def _open_graph_config_menu(fb, fb_buf, graph_state, graph_index):
    graph = graph_state["graphs"][graph_index]
    temp_graph = {
        "type": graph.get("type", GRAPH_TYPE_RECT),
        "style": graph.get("style", GRAPH_STYLE_NORMAL),
        "_selected_row": 0,
    }
    temp_rect = _copy_bounds_dict(graph_state["rect_bounds"])
    temp_polar = _copy_polar_bounds(graph_state["polar_bounds"])
    ignore_open_key = True

    def _commit_graph_config():
        graph["type"] = temp_graph["type"]
        graph["style"] = temp_graph["style"]
        graph_state["rect_bounds"] = _copy_bounds_dict(temp_rect)
        graph_state["polar_bounds"] = _copy_polar_bounds(temp_polar)

    while True:
        _draw_graph_config_menu(fb, fb_buf, graph_index, temp_graph)
        key = _start_typing_with_navigation_fallback(consume_local_back=True)

        if ignore_open_key and key == "toolbox":
            ignore_open_key = False
            continue
        ignore_open_key = False

        if key == "nav_u":
            temp_graph["_selected_row"] = (temp_graph["_selected_row"] - 1) % 3
        elif key == "nav_d":
            temp_graph["_selected_row"] = (temp_graph["_selected_row"] + 1) % 3
        elif key == "nav_l":
            if temp_graph["_selected_row"] == HOME_TOOLBOX_TYPE_ROW:
                temp_graph["type"] = _cycle_sequence_value(GRAPH_TYPES, temp_graph["type"], -1)
                _commit_graph_config()
            elif temp_graph["_selected_row"] == HOME_TOOLBOX_STYLE_ROW:
                temp_graph["style"] = _cycle_sequence_value(GRAPH_STYLES, temp_graph["style"], -1)
                _commit_graph_config()
        elif key == "nav_r":
            if temp_graph["_selected_row"] == HOME_TOOLBOX_TYPE_ROW:
                temp_graph["type"] = _cycle_sequence_value(GRAPH_TYPES, temp_graph["type"], 1)
                _commit_graph_config()
            elif temp_graph["_selected_row"] == HOME_TOOLBOX_STYLE_ROW:
                temp_graph["style"] = _cycle_sequence_value(GRAPH_STYLES, temp_graph["style"], 1)
                _commit_graph_config()
        elif key in ("ok", "exe"):
            if temp_graph["_selected_row"] == HOME_TOOLBOX_WINDOW_ROW:
                view_window = _edit_view_window(temp_rect, temp_polar)
                if view_window == "home":
                    return "home"
                if view_window is None:
                    continue
                temp_rect, temp_polar = view_window
                _commit_graph_config()
            else:
                _commit_graph_config()
                return True
        elif key in ("back", "toolbox"):
            return False
        elif key == "home":
            return "home"
        elif key in ("alpha", "beta"):
            keypad_state_manager(x=key)


def _draw_navbar_text(fb, text_value, plot_height):
    fb.fill_rect(0, plot_height, DISPLAY_WIDTH, DISPLAY_HEIGHT - plot_height, 0)
    _draw_ui_text(fb, text_value, 0, plot_height, 1, max_width=DISPLAY_WIDTH)


def draw_cursor_overlay(fb, cursor, bounds, eval_fn, plot_height, tool_state=None):
    tool_active = tool_state is not None and tool_state.active
    if not cursor.active and not tool_active:
        return

    selected_tool = None
    if tool_active:
        selected_tool = tool_state.selected_feature()

    if selected_tool is not None and selected_tool.mode == TOOL_AREA:
        x_left_val, x_right_val = selected_tool.area_interval()
        x_left = _x_value_to_pixel(x_left_val, bounds, clamp=False)
        x_right = _x_value_to_pixel(x_right_val, bounds, clamp=False)
        if x_left is not None:
            fb.vline(x_left, 0, plot_height, 1)
        if x_right is not None and x_right != x_left:
            fb.vline(x_right, 0, plot_height, 1)
        focus_x = _x_value_to_pixel(selected_tool.focused_x_value(), bounds, clamp=False)
        if focus_x is not None and cursor.active:
            marker_x = focus_x - 1 if focus_x > 0 else 0
            marker_w = 3
            if marker_x + marker_w > DISPLAY_WIDTH:
                marker_w = DISPLAY_WIDTH - marker_x
            fb.hline(marker_x, 0, marker_w, 1)
        area_value = _compute_area_value(eval_fn, selected_tool)
        _draw_navbar_text(fb, _format_area_info_text(selected_tool, area_value), plot_height)
        return

    if selected_tool is not None and selected_tool.mode in (
        TOOL_TANGENT,
        TOOL_NORMAL,
        TOOL_COORDINATES,
    ):
        x_value = selected_tool.single_x
        x_px = _x_value_to_pixel(x_value, bounds, clamp=False)
        if x_px is not None:
            fb.vline(x_px, 0, plot_height, 1)
        y_value = safe_eval(eval_fn, x_value)
        if selected_tool.mode == TOOL_COORDINATES:
            _draw_navbar_text(fb, _format_xy_text(x_value, y_value), plot_height)
            return

        _, tan_slope = _get_tangent_info(eval_fn, bounds, x_value)
        _draw_navbar_text(
            fb,
            _format_line_tool_text(selected_tool, x_value, y_value, tan_slope),
            plot_height,
        )
        return

    x_range = bounds["x_max"] - bounds["x_min"]
    if x_range == 0 or DISPLAY_WIDTH < 2:
        return

    x_coord = bounds["x_min"] + (cursor.x_pixel / (DISPLAY_WIDTH - 1)) * x_range
    fb.vline(cursor.x_pixel, 0, plot_height, 1)

    draw_medium_text(fb, _fmt_cursor_coord(x_coord, "x"), 2, plot_height + 1)
    y_coord = safe_eval(eval_fn, x_coord)
    if y_coord is None:
        draw_medium_text(fb, "y undef", DISPLAY_WIDTH - 42, plot_height + 1)
    else:
        draw_medium_text(fb, _fmt_cursor_coord(y_coord, "y"), DISPLAY_WIDTH - 42, plot_height + 1)


def replot(fb, fb_buf, graph_state, cursor, cache_buf=None, tool_state=None):
    start_ms = time.ticks_ms()
    display_bounds = graph_state["rect_bounds"]
    primary_index = _primary_rect_graph_index(graph_state)
    primary_eval_fn = None
    if primary_index is not None:
        primary_eval_fn = _graph_eval_fn(graph_state["graphs"][primary_index])

    fb.fill(0)
    tool_active = (
        tool_state is not None and tool_state.active and primary_eval_fn is not None
    )
    plot_height = DISPLAY_HEIGHT if not (cursor.active or tool_active) else PLOT_HEIGHT_WITH_CURSOR

    x_min = display_bounds["x_min"]
    x_max = display_bounds["x_max"]
    y_min = display_bounds["y_min"]
    y_max = display_bounds["y_max"]
    x_range = x_max - x_min
    y_range = y_max - y_min

    if x_range == 0 or y_range == 0:
        draw_medium_text(fb, "range err", 2, 57)
        _display_full(fb_buf)
        return False

    x_scale = x_range / (DISPLAY_WIDTH - 1)
    y_scale = y_range / (plot_height - 1)
    _draw_axes(fb, x_min, x_max, y_min, y_max, x_scale, y_scale, plot_height)

    plotted_any = False
    for graph in graph_state["graphs"]:
        if not str(graph.get("expr", "") or "").strip():
            continue
        eval_fn = _graph_eval_fn(graph)
        if eval_fn is None:
            continue
        if graph.get("type") == GRAPH_TYPE_POLAR:
            if _plot_polar_function(
                fb,
                eval_fn,
                display_bounds,
                graph_state["polar_bounds"],
                plot_height,
                graph.get("style", GRAPH_STYLE_NORMAL),
            ):
                plotted_any = True
        else:
            if plot_function(
                fb,
                eval_fn,
                display_bounds,
                plot_height,
                graph.get("style", GRAPH_STYLE_NORMAL),
            ):
                plotted_any = True

    if not plotted_any:
        draw_medium_text(fb, "no graph", 2, 57)

    if tool_active:
        for tool_feature in tool_state.features:
            if tool_feature.mode == TOOL_AREA:
                _draw_area_shade(
                    fb,
                    primary_eval_fn,
                    display_bounds,
                    tool_feature,
                    PLOT_HEIGHT_WITH_CURSOR,
                )
            elif tool_feature.mode in (TOOL_TANGENT, TOOL_NORMAL):
                _draw_tangent_or_normal(
                    fb,
                    primary_eval_fn,
                    display_bounds,
                    tool_feature,
                    PLOT_HEIGHT_WITH_CURSOR,
                )

    if cache_buf is not None:
        cache_buf[:] = fb_buf

    if cursor.active or tool_active:
        draw_cursor_overlay(
            fb,
            cursor,
            display_bounds,
            primary_eval_fn,
            PLOT_HEIGHT_WITH_CURSOR,
            tool_state,
        )

    _display_full(fb_buf)
    _dprint("Replot:", _ticks_diff(time.ticks_ms(), start_ms), "ms")
    return plotted_any


def update_cursor_only(fb, fb_buf, cache_buf, cursor, graph_state, tool_state=None):
    start_ms = time.ticks_ms()
    primary_index = _primary_rect_graph_index(graph_state)
    primary_eval_fn = None
    if primary_index is not None:
        primary_eval_fn = _graph_eval_fn(graph_state["graphs"][primary_index])

    if tool_state is not None and tool_state.active:
        replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)
        return

    fb_buf[:] = cache_buf

    if cursor.active:
        draw_cursor_overlay(
            fb,
            cursor,
            graph_state["rect_bounds"],
            primary_eval_fn,
            PLOT_HEIGHT_WITH_CURSOR,
            tool_state,
        )
        _display_plot_column(fb_buf, cursor.prev_x_pixel, _CURSOR_COL_BUF_A)
        if cursor.x_pixel != cursor.prev_x_pixel:
            _display_plot_column(fb_buf, cursor.x_pixel, _CURSOR_COL_BUF_B)
        _display_page(fb_buf, BOTTOM_PAGE_INDEX)
    else:
        _display_full(fb_buf)

    _dprint("Cursor update:", _ticks_diff(time.ticks_ms(), start_ms), "ms")


def _set_initial_form():
    graph_state = _create_graph_home_state()
    _apply_home_form(graph_state)
    return graph_state


def old_graph(db={}):
    global form, form_refresh
    _dprint("Graph start, mem:", gc.mem_free())
    keypad_state_manager_reset()
    current_app[0] = "old_graph"
    current_app[1] = "installed_apps"

    prev_form_obj = form
    prev_form_refresh_obj = form_refresh
    app_form = Form()
    app_form_refresh = OldGraphFormTbf(
        disp_out=display,
        chrs=chrs,
        f_b=app_form,
        nav=nav,
    )
    form = app_form
    form_refresh = app_form_refresh
    builtins.form = app_form
    builtins.form_refresh = app_form_refresh

    form.ui_style = "buffer"
    form.focus_inputs_only = True
    form.blink_cursor = True
    form.title = ""
    form.input_cols = HOME_INPUT_COLS
    form.compact_hfield_label_w = HOME_HFIELD_LABEL_W
    form.compact_hfield_label_pad_x = HOME_HFIELD_LABEL_PAD_X

    prev_debounce = getattr(typer, "debounce_delay_time", None)

    def _set_fast_poll():
        if prev_debounce is not None:
            typer.debounce_delay_time = INPUT_POLL_SEC

    def _restore_default_poll():
        if prev_debounce is not None:
            typer.debounce_delay_time = prev_debounce

    def _home_form_idle(graph_state):
        if nav is not None:
            try:
                nav.maybe_hide()
            except Exception:
                pass

        if form_refresh is None:
            return
        if not hasattr(form_refresh, "_blink_enabled") or not hasattr(
            form_refresh, "_update_cursor_blink"
        ):
            return
        try:
            if not form_refresh._blink_enabled():
                return
            if form_refresh._update_cursor_blink():
                _refresh_home_form(graph_state, force=True)
        except Exception:
            pass

    def _start_typing_with_form_idle(graph_state):
        prev_idle_tasks = getattr(typer, "_idle_tasks", None)
        try:
            typer._idle_tasks = lambda: _home_form_idle(graph_state)
            return _start_typing_with_navigation_fallback()
        finally:
            if prev_idle_tasks is not None:
                typer._idle_tasks = prev_idle_tasks

    try:
        graph_state = _set_initial_form()
        _refresh_home_form(graph_state)

        fb_buf = bytearray((DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8)
        fb = framebuf.FrameBuffer(fb_buf, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_VLSB)
        cache_buf = bytearray(len(fb_buf))
        cursor = CursorState()
        tool_state = ToolState()
        ignore_form_back_until_ms = None

        while True:
            _restore_default_poll()
            inp = _start_typing_with_form_idle(graph_state)

            if ignore_form_back_until_ms is not None:
                if _ticks_diff(time.ticks_ms(), ignore_form_back_until_ms) < 0:
                    if inp == "back":
                        _restore_old_graph_navigation_entry()
                        _refresh_home_form(graph_state)
                        continue
                else:
                    ignore_form_back_until_ms = None

            if inp == "back":
                try:
                    nav.set_restore_callback(None)
                except Exception:
                    pass
                current_app[0] = "installed_apps"
                current_app[1] = "root"
                break
	
            if inp == "home":
                try:
                    nav.set_restore_callback(None)
                except Exception:
                    pass
                current_app[0] = "home"
                current_app[1] = "root"
                return

            if inp == "ok":
                _sync_graph_state_from_form(graph_state)
                bounds = graph_state["rect_bounds"]
                try:
                    nav.set_restore_callback(None)
                except Exception:
                    pass
                gc.collect()
                replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)
                fast_poll_block_until_ms = None
                ignore_graph_back_until_ms = None

                try:
                    while True:
                        feature_active = cursor.active or tool_state.active
                        if feature_active:
                            _restore_default_poll()
                        else:
                            if (
                                fast_poll_block_until_ms is not None
                                and _ticks_diff(time.ticks_ms(), fast_poll_block_until_ms) < 0
                            ):
                                _restore_default_poll()
                            else:
                                _set_fast_poll()

                        key = _start_typing_with_navigation_fallback(consume_local_back=True)
                        if ignore_graph_back_until_ms is not None:
                            if _ticks_diff(time.ticks_ms(), ignore_graph_back_until_ms) < 0:
                                if key == "back":
                                    _restore_old_graph_navigation_entry()
                                    continue
                            else:
                                ignore_graph_back_until_ms = None

                        if key in ("a", "A", "module", "copy"):
                            cursor.toggle()
                            if cursor.active and tool_state.active:
                                tool_state.sync_cursor(cursor, bounds)
                            feature_active = cursor.active or tool_state.active
                            if feature_active:
                                _restore_default_poll()
                                fast_poll_block_until_ms = None
                            else:
                                _restore_default_poll()
                                fast_poll_block_until_ms = _ticks_add(
                                    time.ticks_ms(), FAST_POLL_RESUME_DELAY_MS
                                )
                            replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == "+":
                            bounds = apply_zoom(bounds, ZOOM_IN_FACTOR)
                            graph_state["rect_bounds"] = bounds
                            if cursor.active and tool_state.active:
                                tool_state.sync_cursor(cursor, bounds)
                            replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == "-":
                            bounds = apply_zoom(bounds, ZOOM_OUT_FACTOR)
                            graph_state["rect_bounds"] = bounds
                            if cursor.active and tool_state.active:
                                tool_state.sync_cursor(cursor, bounds)
                            replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == "nav_u":
                            handled = False
                            if cursor.active and tool_state.mode == TOOL_AREA:
                                handled = tool_state.focus_left(cursor, bounds)
                            if handled:
                                replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)
                            else:
                                bounds = apply_pan(bounds, "up")
                                graph_state["rect_bounds"] = bounds
                                if tool_state.active:
                                    tool_state.sync_cursor(cursor, bounds)
                                replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == "nav_d":
                            handled = False
                            if cursor.active and tool_state.mode == TOOL_AREA:
                                handled = tool_state.focus_right(cursor, bounds)
                            if handled:
                                replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)
                            else:
                                bounds = apply_pan(bounds, "down")
                                graph_state["rect_bounds"] = bounds
                                if tool_state.active:
                                    tool_state.sync_cursor(cursor, bounds)
                                replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == "nav_l":
                            if cursor.active:
                                if tool_state.active:
                                    moved = tool_state.move_focus(-1, bounds, cursor)
                                else:
                                    moved = cursor.move("left")
                                if moved:
                                    update_cursor_only(fb, fb_buf, cache_buf, cursor, graph_state, tool_state)
                            else:
                                bounds = apply_pan(bounds, "left")
                                graph_state["rect_bounds"] = bounds
                                if tool_state.active:
                                    tool_state.sync_cursor(cursor, bounds)
                                replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == "nav_r":
                            if cursor.active:
                                if tool_state.active:
                                    moved = tool_state.move_focus(1, bounds, cursor)
                                else:
                                    moved = cursor.move("right")
                                if moved:
                                    update_cursor_only(fb, fb_buf, cache_buf, cursor, graph_state, tool_state)
                            else:
                                bounds = apply_pan(bounds, "right")
                                graph_state["rect_bounds"] = bounds
                                if tool_state.active:
                                    tool_state.sync_cursor(cursor, bounds)
                                replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == "toolbox":
                            _restore_default_poll()
                            toolbox_action = _open_toolbox_menu(fb, fb_buf, tool_state)
                            if toolbox_action == "home":
                                try:
                                    nav.set_restore_callback(None)
                                except Exception:
                                    pass
                                current_app[0] = "home"
                                current_app[1] = "root"
                                return
                            if toolbox_action == TOOLBOX_CANCEL_BACK:
                                ignore_graph_back_until_ms = _ticks_add(
                                    time.ticks_ms(), _back_guard_duration_ms(prev_debounce)
                                )
                            elif toolbox_action == TOOLBOX_CLEAR_SELECTION:
                                tool_state.clear()
                                cursor.active = False
                                cursor.prev_x_pixel = cursor.x_pixel
                            elif toolbox_action is not None:
                                if not cursor.active:
                                    cursor.toggle()
                                tool_state.replace_mode(toolbox_action, cursor, bounds)
                            feature_active = cursor.active or tool_state.active
                            if feature_active:
                                _restore_default_poll()
                                fast_poll_block_until_ms = None
                            else:
                                _restore_default_poll()
                                fast_poll_block_until_ms = _ticks_add(
                                    time.ticks_ms(), FAST_POLL_RESUME_DELAY_MS
                                )
                            replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key == ",":
                            _restore_default_poll()
                            menu_status = _open_used_tools_menu(fb, fb_buf, tool_state, bounds)
                            if menu_status == "home":
                                try:
                                    nav.set_restore_callback(None)
                                except Exception:
                                    pass
                                current_app[0] = "home"
                                current_app[1] = "root"
                                return
                            if cursor.active and tool_state.active:
                                tool_state.sync_cursor(cursor, bounds)
                            feature_active = cursor.active or tool_state.active
                            if feature_active:
                                _restore_default_poll()
                                fast_poll_block_until_ms = None
                            else:
                                _restore_default_poll()
                                fast_poll_block_until_ms = _ticks_add(
                                    time.ticks_ms(), FAST_POLL_RESUME_DELAY_MS
                                )
                            replot(fb, fb_buf, graph_state, cursor, cache_buf, tool_state)

                        elif key in ("alpha", "beta"):
                            keypad_state_manager(x=key)

                        elif key == "back":
                            ignore_form_back_until_ms = _ticks_add(
                                time.ticks_ms(), _back_guard_duration_ms(prev_debounce)
                            )
                            break

                        elif key == "home":
                            try:
                                nav.set_restore_callback(None)
                            except Exception:
                                pass
                            current_app[0] = "home"
                            current_app[1] = "root"
                            return
                finally:
                    _restore_default_poll()

                fb.fill(0)
                form.refresh_rows = (0, form.actual_rows)
                display.clear_display()
                _refresh_home_form(graph_state)

            elif inp in ("alpha", "beta"):
                keypad_state_manager(x=inp)
                form.update_buffer("")

            elif inp == "toolbox":
                _sync_graph_state_from_form(graph_state)
                graph_index = int(graph_state.get("focus_graph_index", 0) or 0)
                config_status = _open_graph_config_menu(fb, fb_buf, graph_state, graph_index)
                if config_status == "home":
                    try:
                        nav.set_restore_callback(None)
                    except Exception:
                        pass
                    current_app[0] = "home"
                    current_app[1] = "root"
                    return
                display.clear_display()

            elif inp not in ("ok",):
                form.update_buffer(inp)

            _refresh_home_form(graph_state)

    finally:
        try:
            nav.set_restore_callback(None)
        except Exception:
            pass
        form = prev_form_obj
        form_refresh = prev_form_refresh_obj
        builtins.form = prev_form_obj
        builtins.form_refresh = prev_form_refresh_obj
        if prev_debounce is not None:
            typer.debounce_delay_time = prev_debounce
        gc.collect()
        _dprint("Graph end, mem:", gc.mem_free())


def polynom1(exp, x):
    """Backward-compatible evaluator."""
    eval_fn = get_eval_fn(exp)
    if eval_fn is None:
        raise ValueError("Invalid expression")
    return eval_fn(x)
