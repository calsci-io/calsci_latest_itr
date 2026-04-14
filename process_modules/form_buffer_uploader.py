import os

import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

try:
    import framebuf  # type: ignore
except ImportError:
    from mocking import framebuf  # type: ignore

try:
    import time as _time
except Exception:
    _time = None

try:
    import json as _json
except Exception:
    try:
        import ujson as _json
    except Exception:
        _json = None

from process_modules.ui_context import get_active_view, set_active_view

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.


DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_PAGES = DISPLAY_HEIGHT // 8
CHAR_HEIGHT = 8
CHAR_ADVANCE = 6
TITLE_Y = 1
PANEL_X = 2
PANEL_Y = 9
PANEL_W = 124
PANEL_H = 53
FIELD_H = 24
FIELD_GAP = 2
VISIBLE_FIELDS = 2
ROW_H = 13
ROW_GAP = 1
SCROLL_W = 4
CONTENT_X = PANEL_X + 2
CONTENT_Y = PANEL_Y + 2
CONTENT_W = PANEL_W - SCROLL_W - 5
STATUS_Y = 56
CURSOR_BLINK_MS = 450
LABEL_H = 10
INPUT_H = 12
INPUT_Y_OFFSET = 11
SCROLLBAR_H = 1
COMPACT_PANEL_X = 1
COMPACT_PANEL_Y = 1
COMPACT_PANEL_W = 126
COMPACT_PANEL_H = 62
COMPACT_CONTENT_X = COMPACT_PANEL_X + 2
COMPACT_CONTENT_Y = COMPACT_PANEL_Y + 2
COMPACT_CONTENT_W = COMPACT_PANEL_W - 4
COMPACT_CONTENT_H = COMPACT_PANEL_H - 4
COMPACT_ROW_H = 11
COMPACT_HFIELD_H = 12
COMPACT_VFIELD_H = 20
COMPACT_LABEL_H = 9
COMPACT_INPUT_H = 10
COMPACT_BUTTON_H = 10
COMPACT_BUTTON_BLOCK_H = 12
COMPACT_ROW_GAP = 1
COMPACT_LINK_ARROW_W = 9
COMPACT_ROUND_RADIUS = 5
COMPACT_BUTTON_PAD_X = 14
COMPACT_BUTTON_MIN_W = 38
COMPACT_ROW_TEXT_PAD_X = 4
COMPACT_ROW_TEXT_PAD_Y = 1
COMPACT_LINK_TEXT_PAD_X = 4
COMPACT_LINK_TEXT_PAD_Y = 2
COMPACT_LINK_TRI_PAD_X = 2
COMPACT_LINK_TRI_PAD_Y = 2
COMPACT_BUTTON_TEXT_PAD_X = 3
COMPACT_BUTTON_TEXT_PAD_Y = 1
COMPACT_BUTTON_Y_OFFSET = 1
COMPACT_HFIELD_LABEL_PAD_X = 3
COMPACT_HFIELD_LABEL_PAD_Y = 1
COMPACT_HFIELD_LABEL_W = 42
COMPACT_HFIELD_MIN_INPUT_W = 22
COMPACT_HFIELD_GAP_X = 0
COMPACT_HFIELD_INPUT_Y_OFFSET = 0
COMPACT_HFIELD_INPUT_H = COMPACT_HFIELD_H
COMPACT_HFIELD_INPUT_RADIUS = 0
COMPACT_HFIELD_INPUT_INSET_X = 6
COMPACT_HFIELD_INPUT_RIGHT_PAD = 6
COMPACT_HFIELD_CURSOR_RIGHT_PAD = 4
COMPACT_HFIELD_SCROLL_INSET_X = 3
COMPACT_HFIELD_SCROLL_RIGHT_PAD = 3
COMPACT_VFIELD_LABEL_PAD_X = 2
COMPACT_VFIELD_LABEL_PAD_Y = 1
COMPACT_VFIELD_LABEL_INPUT_GAP = 0
COMPACT_VFIELD_INPUT_INSET_X = 5
COMPACT_VFIELD_INPUT_RIGHT_PAD = 5
COMPACT_VFIELD_CURSOR_RIGHT_PAD = 4
COMPACT_VFIELD_SCROLL_INSET_X = 1
COMPACT_VFIELD_SCROLL_RIGHT_PAD = 1
ROW_SCROLL_STEP_MS = CURSOR_BLINK_MS


def _path_dirname(path_value):
    path_value = str(path_value or "")
    if path_value == "":
        return ""
    trimmed = path_value.rstrip("/")
    if trimmed == "":
        return ""
    cut = trimmed.rfind("/")
    if cut < 0:
        return ""
    if cut == 0:
        return "/"
    return trimmed[:cut]


def _path_join(*parts):
    result = ""
    for part in parts:
        part = str(part or "")
        if part == "":
            continue
        if result == "":
            result = part.rstrip("/")
        else:
            result = result.rstrip("/") + "/" + part.lstrip("/")
    return result


def _open_text_file(path_value, mode):
    try:
        return open(path_value, mode, encoding="utf-8")
    except TypeError:
        return open(path_value, mode)


_MODULE_ROOT = _path_dirname(_path_dirname(globals().get("__file__", "")))
COMPACT_TUNE_FILE = _path_join(
    _MODULE_ROOT,
    "settings",
    "form_buffer_uploader_compact.json",
)
COMPACT_TUNE_KEYS = (
    "COMPACT_PANEL_X",
    "COMPACT_PANEL_Y",
    "COMPACT_PANEL_W",
    "COMPACT_PANEL_H",
    "COMPACT_CONTENT_X",
    "COMPACT_CONTENT_Y",
    "COMPACT_CONTENT_W",
    "COMPACT_CONTENT_H",
    "COMPACT_ROW_H",
    "COMPACT_HFIELD_H",
    "COMPACT_VFIELD_H",
    "COMPACT_LABEL_H",
    "COMPACT_INPUT_H",
    "COMPACT_BUTTON_H",
    "COMPACT_BUTTON_BLOCK_H",
    "COMPACT_ROW_GAP",
    "COMPACT_LINK_ARROW_W",
    "COMPACT_ROUND_RADIUS",
    "COMPACT_BUTTON_PAD_X",
    "COMPACT_BUTTON_MIN_W",
    "COMPACT_ROW_TEXT_PAD_X",
    "COMPACT_ROW_TEXT_PAD_Y",
    "COMPACT_LINK_TEXT_PAD_X",
    "COMPACT_LINK_TEXT_PAD_Y",
    "COMPACT_LINK_TRI_PAD_X",
    "COMPACT_LINK_TRI_PAD_Y",
    "COMPACT_BUTTON_TEXT_PAD_X",
    "COMPACT_BUTTON_TEXT_PAD_Y",
    "COMPACT_BUTTON_Y_OFFSET",
    "COMPACT_HFIELD_LABEL_PAD_X",
    "COMPACT_HFIELD_LABEL_PAD_Y",
    "COMPACT_HFIELD_LABEL_W",
    "COMPACT_HFIELD_MIN_INPUT_W",
    "COMPACT_HFIELD_GAP_X",
    "COMPACT_HFIELD_INPUT_Y_OFFSET",
    "COMPACT_HFIELD_INPUT_H",
    "COMPACT_HFIELD_INPUT_RADIUS",
    "COMPACT_HFIELD_INPUT_INSET_X",
    "COMPACT_HFIELD_INPUT_RIGHT_PAD",
    "COMPACT_HFIELD_CURSOR_RIGHT_PAD",
    "COMPACT_HFIELD_SCROLL_INSET_X",
    "COMPACT_HFIELD_SCROLL_RIGHT_PAD",
    "COMPACT_VFIELD_LABEL_PAD_X",
    "COMPACT_VFIELD_LABEL_PAD_Y",
    "COMPACT_VFIELD_LABEL_INPUT_GAP",
    "COMPACT_VFIELD_INPUT_INSET_X",
    "COMPACT_VFIELD_INPUT_RIGHT_PAD",
    "COMPACT_VFIELD_CURSOR_RIGHT_PAD",
    "COMPACT_VFIELD_SCROLL_INSET_X",
    "COMPACT_VFIELD_SCROLL_RIGHT_PAD",
    "ROW_SCROLL_STEP_MS",
)
COMPACT_TUNE_DEFAULTS = {
    key: int(globals()[key]) for key in COMPACT_TUNE_KEYS if key in globals()
}


def current_compact_tuning():
    return {key: int(globals()[key]) for key in COMPACT_TUNE_KEYS if key in globals()}


def apply_compact_tuning(values):
    changed = {}
    if not isinstance(values, dict):
        return changed

    for key in COMPACT_TUNE_KEYS:
        if key not in values:
            continue
        try:
            new_value = int(values[key])
        except Exception:
            continue
        globals()[key] = new_value
        changed[key] = new_value
    return changed


def load_compact_tuning():
    if _json is None:
        return {}
    try:
        with _open_text_file(COMPACT_TUNE_FILE, "r") as handle:
            values = _json.load(handle)
    except Exception:
        return {}
    return apply_compact_tuning(values)


def save_compact_tuning(values=None):
    if _json is None:
        return ""
    if values is None:
        values = current_compact_tuning()
    try:
        tune_dir = _path_dirname(COMPACT_TUNE_FILE)
        if tune_dir != "" and hasattr(os, "makedirs"):
            try:
                os.makedirs(tune_dir, exist_ok=True)
            except TypeError:
                os.makedirs(tune_dir)
        with _open_text_file(COMPACT_TUNE_FILE, "w") as handle:
            _json.dump(values, handle, indent=2, sort_keys=True)
    except Exception:
        return ""
    return COMPACT_TUNE_FILE


load_compact_tuning()


def _ticks_ms():
    if _time is None:
        return 0
    try:
        return int(_time.ticks_ms())
    except AttributeError:
        pass
    try:
        return int(_time.monotonic() * 1000)
    except Exception:
        pass
    try:
        return int(_time.time() * 1000)
    except Exception:
        return 0


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


def _max_chars_for_width(max_width):
    if max_width <= 0:
        return 1
    return max(1, (int(max_width) + 1) // CHAR_ADVANCE)


def _scroll_slice(text_value, visible_chars, tick_ms):
    text_value = _display_text(text_value)
    visible_chars = max(1, int(visible_chars))
    if len(text_value) <= visible_chars:
        return text_value

    max_start = len(text_value) - visible_chars
    if max_start <= 0:
        return text_value[:visible_chars]

    step = max(0, int(tick_ms) // ROW_SCROLL_STEP_MS)
    cycle = max_start * 2
    if cycle <= 0:
        start = 0
    else:
        start = step % cycle
        if start > max_start:
            start = cycle - start
    return text_value[start : start + visible_chars]


def _title_case(text_value):
    parts = str(text_value or "").split(" ")
    titled = []
    for part in parts:
        if not part:
            continue
        titled.append(part[:1].upper() + part[1:].lower())
    return " ".join(titled)


class Tbf:
    def __init__(self, disp_out, chrs, f_b, nav=None):
        self.disp_out = disp_out
        self.chrs = chrs
        self.f_b = f_b
        self.nav = nav
        self.disp_out.clear_display()
        self.last_state = ""
        self.buf = bytearray((DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8)
        self.fb = framebuf.FrameBuffer(
            self.buf,
            DISPLAY_WIDTH,
            DISPLAY_HEIGHT,
            framebuf.MONO_VLSB,
        )
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()
        self._cursor_signature = None
        self.steady_bottom_page = True

    def _ui_style(self):
        return str(getattr(self.f_b, "ui_style", "") or "").strip().lower()

    def _use_boxed_layout(self):
        return self._ui_style() in ("boxed", "buffer", "compact", "widgets")

    def _use_table_layout(self):
        return self._ui_style() in ("table", "sheet", "grid")

    def _blink_enabled(self):
        return (self._use_boxed_layout() or self._use_table_layout()) and bool(
            getattr(self.f_b, "blink_cursor", False)
        )

    def _reset_cursor_blink(self):
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()

    def _update_cursor_blink(self):
        if not self._blink_enabled():
            return False
        now = _ticks_ms()
        elapsed = now - self._cursor_last_toggle
        if elapsed < CURSOR_BLINK_MS:
            return False
        toggles = max(1, elapsed // CURSOR_BLINK_MS)
        changed = False
        if toggles % 2:
            self._cursor_visible = not self._cursor_visible
            changed = True
        self._cursor_last_toggle += toggles * CURSOR_BLINK_MS
        return changed

    def _cursor_state_signature(self):
        active_key = None
        if hasattr(self.f_b, "active_input_key"):
            active_key = self.f_b.active_input_key()
        return (
            getattr(self.f_b, "menu_cursor", 0),
            active_key,
            self.f_b.inp_cursor(),
            self.f_b.inp_display_position(),
        )

    def _sync_blink_signature(self):
        signature = self._cursor_state_signature()
        if signature != self._cursor_signature:
            self._cursor_signature = signature
            self._reset_cursor_blink()

    def idle(self):
        if get_active_view() != "form":
            return
        if not self._blink_enabled():
            return
        if self._update_cursor_blink():
            state = self.nav.current_state() if self.nav is not None else ""
            self.refresh(state=state, force=True)

    def _clear_page(self, page_index):
        self.disp_out.set_page_address(page_index)
        self.disp_out.set_column_address(0)
        for _ in range(128):
            self.disp_out.write_data(0b00000000)

    def _draw_page(self, buf, page_index):
        self._clear_page(page_index)
        if page_index < 0 or page_index >= self.f_b.rows or page_index >= len(buf):
            return

        if "inp_" in buf[page_index]:
            row_text = (
                "=>"
                + self.f_b.inp_list()[self.f_b.buffer()[page_index]][
                    self.f_b.inp_display_position() : self.f_b.inp_display_position()
                    + self.f_b.inp_cols()
                ]
            )
        else:
            row_text = buf[page_index]
        max_cols = self.f_b.inp_cols() + 2
        row_text = row_text[:max_cols]
        if len(row_text) < max_cols:
            row_text += " " * (max_cols - len(row_text))

        self.disp_out.set_page_address(page_index)
        self.disp_out.set_column_address(0)
        for col_index, char in enumerate(row_text):
            if page_index == self.f_b.cursor() and "inp_" not in buf[page_index]:
                char_bytes = self.chrs.invert_letter(char)
                cursor_line = 0b11111111
            elif page_index == self.f_b.cursor() and "inp_" in buf[page_index]:
                if col_index + self.f_b.inp_display_position() == self.f_b.inp_cursor() + 2:
                    char_bytes = self.chrs.invert_letter(char)
                    cursor_line = 0b11111111
                else:
                    char_bytes = self.chrs.Chr2bytes(char)
                    cursor_line = 0b00000000
            else:
                char_bytes = self.chrs.Chr2bytes(char)
                cursor_line = 0b00000000
            for byte in char_bytes:
                self.disp_out.write_data(byte)
            self.disp_out.write_data(cursor_line)
        for _ in range(max(0, 128 - (len(row_text) * 6))):
            self.disp_out.write_data(0b00000000)

    def _draw_state(self, state):
        if self.nav is not None:
            self.nav.draw_state(state)
            return
        self._clear_page(7)
        state = str(state or "")
        if state == "":
            return
        self.disp_out.set_column_address(0)
        for char in state:
            char_bytes = self.chrs.invert_letter(char)
            for byte in char_bytes:
                self.disp_out.write_data(byte)
            self.disp_out.write_data(0b11111111)

    def _clear(self, color=0):
        self.fb.fill(1 if color else 0)

    def _rect(self, x, y, width, height, color=1):
        self.fb.rect(int(x), int(y), int(width), int(height), 1 if color else 0)

    def _fill_rect(self, x, y, width, height, color=1):
        self.fb.fill_rect(int(x), int(y), int(width), int(height), 1 if color else 0)

    def _hline(self, x, y, width, color=1):
        self.fb.hline(int(x), int(y), int(width), 1 if color else 0)

    def _vline(self, x, y, height, color=1):
        self.fb.vline(int(x), int(y), int(height), 1 if color else 0)

    def _rounded_rect(self, x, y, width, height, color=1, fill=False, radius=3):
        x = int(x)
        y = int(y)
        width = int(width)
        height = int(height)
        radius = max(0, min(int(radius), width // 2, height // 2))
        color = 1 if color else 0

        if width <= 0 or height <= 0:
            return
        if radius <= 0:
            if fill:
                self._fill_rect(x, y, width, height, color)
            else:
                self._rect(x, y, width, height, color)
            return

        if hasattr(self.fb, "ellipse"):
            if fill:
                self._fill_rect(x + radius, y, max(0, width - radius * 2), height, color)
                self._fill_rect(x, y + radius, width, max(0, height - radius * 2), color)
                self.fb.ellipse(x + radius, y + radius, radius, radius, color, fill=True, mask=0x02)
                self.fb.ellipse(
                    x + width - 1 - radius,
                    y + radius,
                    radius,
                    radius,
                    color,
                    fill=True,
                    mask=0x01,
                )
                self.fb.ellipse(
                    x + radius,
                    y + height - 1 - radius,
                    radius,
                    radius,
                    color,
                    fill=True,
                    mask=0x04,
                )
                self.fb.ellipse(
                    x + width - 1 - radius,
                    y + height - 1 - radius,
                    radius,
                    radius,
                    color,
                    fill=True,
                    mask=0x08,
                )
                return

            self._hline(x + radius, y, max(0, width - radius * 2), color)
            self._hline(x + radius, y + height - 1, max(0, width - radius * 2), color)
            self._vline(x, y + radius, max(0, height - radius * 2), color)
            self._vline(x + width - 1, y + radius, max(0, height - radius * 2), color)
            self.fb.ellipse(x + radius, y + radius, radius, radius, color, mask=0x02)
            self.fb.ellipse(
                x + width - 1 - radius,
                y + radius,
                radius,
                radius,
                color,
                mask=0x01,
            )
            self.fb.ellipse(
                x + radius,
                y + height - 1 - radius,
                radius,
                radius,
                color,
                mask=0x04,
            )
            self.fb.ellipse(
                x + width - 1 - radius,
                y + height - 1 - radius,
                radius,
                radius,
                color,
                mask=0x08,
            )
            return

        if radius <= 2:
            corner_offsets = [1, 0]
        elif radius == 3:
            corner_offsets = [1, 0, 0]
        elif radius == 4:
            corner_offsets = [2, 1, 0, 0]
        else:
            corner_offsets = [2, 1, 1, 0, 0]
        corner_offsets = corner_offsets[:radius]

        if fill:
            for offset in range(height):
                inset = 0
                if offset < radius:
                    inset = corner_offsets[offset]
                elif offset >= height - radius:
                    inset = corner_offsets[height - 1 - offset]
                span = max(0, width - inset * 2)
                if span <= 0:
                    continue
                self._hline(x + inset, y + offset, span, color)
            return

        for offset in range(radius):
            inset = corner_offsets[offset]
            span = max(0, width - inset * 2)
            if span > 0:
                self._hline(x + inset, y + offset, span, color)
                self._hline(x + inset, y + height - 1 - offset, span, color)
            px_left = x + inset
            px_right = x + width - 1 - inset
            py_top = y + offset
            py_bottom = y + height - 1 - offset
            self.fb.pixel(px_left, py_top, color)
            self.fb.pixel(px_right, py_top, color)
            self.fb.pixel(px_left, py_bottom, color)
            self.fb.pixel(px_right, py_bottom, color)
        if height > radius * 2:
            self._vline(x, y + radius, height - radius * 2, color)
            self._vline(x + width - 1, y + radius, height - radius * 2, color)

    def _draw_text(self, text_value, x, y, color=1, max_width=None):
        text_value = _display_text(text_value)
        if max_width is not None:
            text_value = _clip_text_px(text_value, max_width)

        cursor_x = int(x)
        y = int(y)
        color = 1 if color else 0
        for char in text_value:
            glyph = self.chrs.Chr2bytes(char)
            for col_idx, col_bits in enumerate(glyph):
                px = cursor_x + col_idx
                if px < 0 or px >= DISPLAY_WIDTH:
                    continue
                for bit_idx in range(CHAR_HEIGHT):
                    py = y + bit_idx
                    if py < 0 or py >= DISPLAY_HEIGHT:
                        continue
                    if col_bits & (1 << bit_idx):
                        self.fb.pixel(px, py, color)
            cursor_x += CHAR_ADVANCE
        return text_value

    def _draw_text_in_rect(self, text_value, x, y, width, height, color=1, align="left"):
        text_value = _clip_text_px(text_value, width)
        tw = _text_width(text_value)
        if align == "center":
            text_x = int(x) + max(0, (int(width) - tw) // 2)
        elif align == "right":
            text_x = int(x) + max(0, int(width) - tw)
        else:
            text_x = int(x)
        text_y = int(y) + max(0, (int(height) - CHAR_HEIGHT) // 2)
        self._draw_text(text_value, text_x, text_y, color=color)
        return text_value

    def _draw_text_center(self, text_value, y, color=1):
        text_value = _clip_text_px(text_value, DISPLAY_WIDTH - 2)
        tw = _text_width(text_value)
        text_x = max(0, (DISPLAY_WIDTH - tw) // 2)
        self._draw_text(text_value, text_x, int(y), color=color)
        return text_value

    def _unwrap_graphics(self, graphics_callable):
        current = graphics_callable
        seen = []
        for _ in range(4):
            if current is None:
                break
            current_id = id(current)
            if current_id in seen:
                break
            seen.append(current_id)

            wrapped = getattr(current, "__wrapped__", None)
            if callable(wrapped) and wrapped is not current:
                current = wrapped
                continue

            closure = getattr(current, "__closure__", None)
            next_callable = None
            if closure is not None:
                for cell in closure:
                    try:
                        cell_value = cell.cell_contents
                    except Exception:
                        continue
                    if callable(cell_value) and cell_value is not current:
                        next_callable = cell_value
                        break
            if next_callable is None:
                break
            current = next_callable
        return current

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

    def _flush_bottom_page(self, force=False):
        bottom_page = max(0, DISPLAY_PAGES - 1)
        start = bottom_page * DISPLAY_WIDTH
        end = start + DISPLAY_WIDTH
        page_buf = memoryview(self.buf)[start:end]
        if self.nav is not None and hasattr(self.nav, "draw_bottom_page"):
            self.nav.draw_bottom_page(page_buf, force=force)
            return
        self._flush_partial(
            page_buf,
            {
                "page": bottom_page,
                "column": 0,
                "width": DISPLAY_WIDTH,
                "pages": 1,
            },
            force=force,
        )

    def _flush(self, force=False):
        flush_pages = DISPLAY_PAGES
        if getattr(self, "steady_bottom_page", False):
            flush_pages = max(1, DISPLAY_PAGES - 1)

        flush_len = DISPLAY_WIDTH * flush_pages
        flush_kwargs = {
            "page": 0,
            "column": 0,
            "width": DISPLAY_WIDTH,
            "pages": flush_pages,
        }
        self._flush_partial(memoryview(self.buf)[:flush_len], flush_kwargs, force=force)

    def _title_text(self):
        form_title = str(getattr(self.f_b, "title", "") or "").strip()
        if form_title:
            return _display_text(form_title)

        try:
            from data_modules.object_handler import current_app

            app_name = str(current_app[0] or "").strip()
        except Exception:
            app_name = ""

        if not app_name:
            return "Form"

        formatted = _display_text(app_name)
        if "_" in app_name or app_name.islower():
            return _title_case(formatted)
        return formatted

    def _normalized_state(self, state):
        state = str(state or "")
        if state == "" or self.nav is None:
            return state

        try:
            nav_label = str(self.nav._label() or "")
        except Exception:
            nav_label = ""

        try:
            nav_visible = bool(self.nav.is_visible())
        except Exception:
            nav_visible = False

        if not nav_visible and nav_label != "" and state == nav_label:
            return ""
        return state

    def _table_headers(self):
        headers = list(getattr(self.f_b, "table_headers", []) or [])
        table_keys = getattr(self.f_b, "table_keys", []) or []
        max_cols = len(headers)
        for row in table_keys:
            if isinstance(row, (list, tuple)) and len(row) > max_cols:
                max_cols = len(row)
        if len(headers) < max_cols:
            headers.extend([""] * (max_cols - len(headers)))
        return headers

    def _table_cell_key(self, row_index, col_index):
        if hasattr(self.f_b, "_table_cell_key"):
            return self.f_b._table_cell_key(row_index, col_index)
        table_keys = getattr(self.f_b, "table_keys", []) or []
        if row_index < 0 or col_index < 0 or row_index >= len(table_keys):
            return None
        row_keys = table_keys[row_index]
        if not isinstance(row_keys, (list, tuple)) or col_index >= len(row_keys):
            return None
        cell_key = row_keys[col_index]
        if cell_key in (None, ""):
            return None
        return str(cell_key)

    def _table_cell_value(self, row_index, col_index):
        cell_key = self._table_cell_key(row_index, col_index)
        if cell_key is None:
            return ""
        return str(self.f_b.inp_list().get(cell_key, " ") or " ").rstrip()

    def _table_row_label(self, row_index, selected_col):
        provider = getattr(self.f_b, "table_row_label_provider", None)
        if callable(provider):
            try:
                return _display_text(provider(int(row_index), int(selected_col)))
            except Exception:
                pass

        row_labels = list(getattr(self.f_b, "table_row_labels", []) or [])
        if 0 <= int(row_index) < len(row_labels):
            return _display_text(row_labels[int(row_index)])
        return ""

    def _table_active_label(self, selected_row, selected_col, default_text):
        active_label = str(getattr(self.f_b, "table_active_label", "") or "")
        if active_label != "":
            return _display_text(active_label)

        row_label = self._table_row_label(selected_row, selected_col)
        if row_label != "":
            return row_label

        return _display_text(default_text)

    def _draw_table_grid_cell(
        self,
        x,
        y,
        width,
        height,
        text_value,
        selected=False,
        header=False,
        draw_left=True,
        draw_top=True,
        draw_right=False,
        draw_bottom=False,
    ):
        x = int(x)
        y = int(y)
        width = max(1, int(width))
        height = max(1, int(height))
        if selected:
            self._fill_rect(x, y, width, height, 1)
            text_color = 0
        else:
            self._fill_rect(x, y, width, height, 0)
            text_color = 1
        if draw_top:
            self.fb.hline(x, y, width, 1)
        if draw_left:
            self.fb.vline(x, y, height, 1)
        if draw_right:
            self.fb.vline(x + width - 1, y, height, 1)
        if draw_bottom:
            self.fb.hline(x, y + height - 1, width, 1)
        pad_x = 1 if width > 2 else 0
        pad_y = 1 if height > 2 else 0
        self._draw_text_in_rect(
            text_value,
            x + pad_x,
            y + pad_y,
            max(1, width - (2 * pad_x)),
            max(1, height - (2 * pad_y)),
            color=text_color,
            align="center",
        )

    def _refresh_table(self, state="", force=False):
        self._sync_blink_signature()
        state = self._normalized_state(state)

        if hasattr(self.f_b, "_ensure_table_grid"):
            self.f_b._ensure_table_grid()
        if hasattr(self.f_b, "_sync_table_view"):
            self.f_b._sync_table_view()

        headers = self._table_headers()
        row_count = len(getattr(self.f_b, "table_keys", []) or [])
        col_count = len(headers)

        self._clear()
        if row_count <= 0 or col_count <= 0:
            self._flush(force=force)
            self.last_state = state
            return

        selected_row = min(max(0, int(getattr(self.f_b, "table_cursor_row", 0) or 0)), row_count - 1)
        selected_col = min(max(0, int(getattr(self.f_b, "table_cursor_col", 0) or 0)), col_count - 1)
        visible_rows = min(max(1, int(getattr(self.f_b, "table_visible_rows", 4) or 1)), row_count)
        visible_cols = min(max(1, int(getattr(self.f_b, "table_visible_cols", 5) or 1)), col_count)
        row_offset = min(
            max(0, int(getattr(self.f_b, "table_row_offset", 0) or 0)),
            max(0, row_count - visible_rows),
        )
        col_offset = min(
            max(0, int(getattr(self.f_b, "table_col_offset", 0) or 0)),
            max(0, col_count - visible_cols),
        )

        label_text = self._table_active_label(
            selected_row,
            selected_col,
            headers[selected_col] if selected_col < len(headers) else "",
        )
        if label_text == "":
            label_text = "Cell"

        top_y = 0
        top_h = 10
        gap = 1
        label_w = min(32, max(18, _text_width(label_text) + 8))
        show_button = bool(getattr(self.f_b, "table_show_button", True))
        button_label = _display_text(getattr(self.f_b, "table_button_text", "Ok") or "Ok")
        button_w = 0
        if show_button:
            button_w = min(26, max(20, _text_width(button_label) + 12))
        input_x = label_w + gap
        input_w = DISPLAY_WIDTH - input_x - (button_w + gap if show_button else 0)
        if input_w < 18:
            shortage = 18 - input_w
            label_w = max(16, label_w - shortage)
            input_x = label_w + gap
            input_w = DISPLAY_WIDTH - input_x - (button_w + gap if show_button else 0)

        self._fill_rect(0, top_y, label_w, top_h, 1)
        self._rect(0, top_y, label_w, top_h, 1)
        self._draw_text_in_rect(
            label_text,
            2,
            top_y,
            max(1, label_w - 4),
            top_h,
            color=0,
            align="center",
        )

        self._rect(input_x, top_y, input_w, top_h, 1)
        active_key = self.f_b.active_input_key() if hasattr(self.f_b, "active_input_key") else None
        input_block = {"key": active_key}
        if hasattr(self.f_b, "table_editor_text"):
            input_block["raw_value"] = getattr(self.f_b, "table_editor_text", "")
            input_block["cursor_pos"] = int(getattr(self.f_b, "table_editor_cursor", 0) or 0)
            input_block["display_pos"] = int(getattr(self.f_b, "table_editor_display_position", 0) or 0)
        editor_text_w = max(8, input_w - 10)
        view = self._input_view(
            input_block,
            True,
            visible_chars=_max_chars_for_width(editor_text_w),
        )
        text_x = input_x + 4
        input_y = top_y
        self._draw_text(
            view["visible_text"],
            text_x,
            input_y + 1,
            color=1,
            max_width=editor_text_w,
        )
        if self._blink_enabled() and self._cursor_visible:
            visible_cursor = view["cursor_pos"] - view["display_pos"]
            if visible_cursor < 0:
                visible_cursor = 0
            if visible_cursor > view["visible_chars"]:
                visible_cursor = view["visible_chars"]
            cursor_x = min(input_x + input_w - 4, text_x + visible_cursor * CHAR_ADVANCE)
            self._draw_input_cursor(cursor_x, input_y, top_h)

        if show_button:
            button_x = DISPLAY_WIDTH - button_w
            self._rounded_rect(button_x, top_y, button_w, top_h, color=1, fill=False, radius=5)
            self._draw_text_in_rect(
                button_label,
                button_x + 2,
                top_y,
                max(1, button_w - 4),
                top_h,
                color=1,
                align="center",
            )

        show_scrollbars = bool(getattr(self.f_b, "table_show_scrollbars", False))
        row_header_w = max(0, int(getattr(self.f_b, "table_row_header_w", 0) or 0))
        if row_header_w > DISPLAY_WIDTH - 24:
            row_header_w = max(0, DISPLAY_WIDTH - 24)
        v_scroll_w = 4 if show_scrollbars and row_count > visible_rows else 0
        h_scroll_h = 4 if show_scrollbars and col_count > visible_cols else 0

        grid_y = 12
        grid_x = row_header_w
        grid_w = DISPLAY_WIDTH - grid_x - v_scroll_w
        grid_h = DISPLAY_HEIGHT - grid_y - h_scroll_h
        if grid_w < max(16, visible_cols * 10):
            grid_w = max(16, DISPLAY_WIDTH - grid_x)
            v_scroll_w = 0
        if grid_h < max(12, (visible_rows + 1) * 6):
            grid_h = DISPLAY_HEIGHT - grid_y
            h_scroll_h = 0

        total_grid_rows = visible_rows + 1
        header_y = grid_y
        next_header_y = grid_y + (grid_h // total_grid_rows)
        header_h = max(1, next_header_y - header_y)

        if row_header_w > 0:
            row_header_title = _display_text(getattr(self.f_b, "table_row_header_title", "") or "")
            if row_header_title == "":
                row_header_title = "#"
            self._draw_table_grid_cell(
                0,
                header_y,
                row_header_w,
                header_h,
                row_header_title,
                selected=False,
                header=True,
                draw_left=True,
                draw_top=True,
                draw_right=True,
                draw_bottom=False,
            )

        for visible_col in range(visible_cols):
            global_col = col_offset + visible_col
            cell_x = grid_x + (grid_w * visible_col) // visible_cols
            next_x = grid_x + (grid_w * (visible_col + 1)) // visible_cols
            cell_w = max(1, next_x - cell_x)
            self._draw_table_grid_cell(
                cell_x,
                header_y,
                cell_w,
                header_h,
                headers[global_col] if global_col < len(headers) else "",
                selected=False,
                header=True,
                draw_left=(visible_col > 0 or row_header_w == 0),
                draw_top=True,
                draw_right=visible_col == (visible_cols - 1),
                draw_bottom=False,
            )

            for visible_row in range(visible_rows):
                global_row = row_offset + visible_row
                row_y = grid_y + (grid_h * (visible_row + 1)) // total_grid_rows
                next_row_y = grid_y + (grid_h * (visible_row + 2)) // total_grid_rows
                row_h = max(1, next_row_y - row_y)
                if row_header_w > 0 and visible_col == 0:
                    self._draw_table_grid_cell(
                        0,
                        row_y,
                        row_header_w,
                        row_h,
                        self._table_row_label(global_row, selected_col),
                        selected=False,
                        header=False,
                        draw_left=True,
                        draw_top=True,
                        draw_right=True,
                        draw_bottom=visible_row == (visible_rows - 1),
                    )
                self._draw_table_grid_cell(
                    cell_x,
                    row_y,
                    cell_w,
                    row_h,
                    self._table_cell_value(global_row, global_col),
                    selected=global_row == selected_row and global_col == selected_col,
                    header=False,
                    draw_left=(visible_col > 0 or row_header_w == 0),
                    draw_top=True,
                    draw_right=visible_col == (visible_cols - 1),
                    draw_bottom=visible_row == (visible_rows - 1),
                )

        if v_scroll_w > 0:
            track_x = DISPLAY_WIDTH - v_scroll_w
            track_y = header_y + header_h
            track_h = max(6, grid_h - header_h)
            self._rect(track_x, track_y, v_scroll_w, track_h, 1)
            thumb_h = max(8, ((track_h - 2) * visible_rows) // max(1, row_count))
            thumb_h = min(max(1, track_h - 2), thumb_h)
            max_top = max(1, row_count - visible_rows)
            thumb_range = max(0, (track_h - 2) - thumb_h)
            thumb_y = track_y + 1 + (row_offset * thumb_range // max_top)
            self._fill_rect(track_x + 1, thumb_y, max(1, v_scroll_w - 2), thumb_h, 1)

        if h_scroll_h > 0:
            track_x = grid_x
            track_y = DISPLAY_HEIGHT - h_scroll_h
            track_w = max(8, grid_w)
            self._rect(track_x, track_y, track_w, h_scroll_h, 1)
            thumb_w = max(8, ((track_w - 2) * visible_cols) // max(1, col_count))
            thumb_w = min(max(1, track_w - 2), thumb_w)
            max_left = max(1, col_count - visible_cols)
            thumb_range = max(0, (track_w - 2) - thumb_w)
            thumb_x = track_x + 1 + (col_offset * thumb_range // max_left)
            self._fill_rect(thumb_x, track_y + 1, thumb_w, max(1, h_scroll_h - 2), 1)

        self._flush(force=force)

        if self.nav is not None:
            nav_overlay_visible = (
                str(state or "") != ""
                and str(state or "") == self.nav.current_state()
                and self.nav.is_visible()
            )
            self.nav.set_restore_callback(
                self.restore_bottom_row if nav_overlay_visible else None
            )

        state = str(state or "")
        if state != "":
            self._draw_state(state)
        elif getattr(self, "steady_bottom_page", False):
            self._flush_bottom_page(force=False)

        self.last_state = state

    def _is_input_row(self, index):
        if hasattr(self.f_b, "_is_input_row"):
            return bool(self.f_b._is_input_row(index))
        form_list = getattr(self.f_b, "form_list", [])
        if index < 0 or index >= len(form_list):
            return False
        return "inp_" in str(form_list[index])

    def _normalize_align(self, value, default="left"):
        value = str(value or default).strip().lower()
        if value == "centre":
            value = "center"
        if value not in ("left", "center", "right"):
            return default
        return value

    def _item_text(self, item, default=""):
        if isinstance(item, dict):
            for key in ("text", "label", "title", "name"):
                if item.get(key) not in (None, ""):
                    return _display_text(item.get(key))
        return _display_text(default)

    def _parse_button_text(self, stripped_text):
        rest = stripped_text[len("@button") :].strip()
        if rest.startswith(":"):
            rest = rest[1:].strip()

        align = "center"
        label = rest
        if rest != "":
            first, sep, remainder = rest.partition(" ")
            candidate = self._normalize_align(first.rstrip(":"), default="")
            if candidate != "":
                align = candidate
                label = remainder.strip()
        return align, _display_text(label)

    def _row_definition(self, item):
        if isinstance(item, dict):
            item_type = str(item.get("type", "") or "").strip().lower()
            if item_type == "" and "layout" in item:
                item_type = "field"

            if item_type in ("field", "input", "input_field"):
                layout = str(item.get("layout", "vertical") or "vertical").strip().lower()
                if layout in ("h", "horizontal", "inline"):
                    layout = "horizontal"
                else:
                    layout = "vertical"
                return {
                    "type": "field_label",
                    "layout": layout,
                    "label": self._item_text(item),
                }

            if item_type in ("link", "page_link", "nav"):
                return {"type": "link", "text": self._item_text(item)}

            if item_type in ("button", "btn"):
                return {
                    "type": "button",
                    "text": self._item_text(item),
                    "align": self._normalize_align(item.get("align"), default="center"),
                }

            return {"type": "row", "text": self._item_text(item, default=item)}

        text_value = str(item or "")
        stripped = text_value.strip()
        if stripped.startswith("@link "):
            return {"type": "link", "text": _display_text(stripped[6:])}
        if stripped.startswith("@input_h "):
            return {
                "type": "field_label",
                "layout": "horizontal",
                "label": _display_text(stripped[9:]),
            }
        if stripped.startswith("@input_v "):
            return {
                "type": "field_label",
                "layout": "vertical",
                "label": _display_text(stripped[9:]),
            }
        if stripped.startswith("@button"):
            align, label = self._parse_button_text(stripped)
            return {"type": "button", "text": label, "align": align}
        return {"type": "row", "text": _display_text(text_value)}

    def _boxed_blocks(self):
        form_list = list(getattr(self.f_b, "form_list", []) or [])
        blocks = []
        index = 0
        while index < len(form_list):
            row_def = self._row_definition(form_list[index])
            if (
                index + 1 < len(form_list)
                and not self._is_input_row(index)
                and self._is_input_row(index + 1)
            ):
                if row_def.get("type") == "field_label":
                    label = row_def.get("label", "")
                    layout = row_def.get("layout", "vertical")
                else:
                    label = row_def.get("text", "")
                    layout = "vertical"
                blocks.append(
                    {
                        "type": "field",
                        "label_index": index,
                        "input_index": index + 1,
                        "layout": layout,
                        "label": label,
                        "key": form_list[index + 1],
                    }
                )
                index += 2
                continue

            if self._is_input_row(index):
                blocks.append(
                    {
                        "type": "field",
                        "label_index": None,
                        "input_index": index,
                        "layout": "vertical",
                        "label": "",
                        "key": form_list[index],
                    }
                )
            else:
                row_type = row_def.get("type", "row")
                if row_type == "field_label":
                    row_type = "row"
                blocks.append(
                    {
                        "type": row_type,
                        "row_index": index,
                        "text": row_def.get("text", row_def.get("label", "")),
                        "align": row_def.get("align", "left"),
                    }
                )
            index += 1
        return blocks

    def _uses_compact_layout(self, blocks):
        style = self._ui_style()
        if style in ("buffer", "compact", "widgets"):
            return True
        for block in blocks:
            if block.get("type") in ("link", "button"):
                return True
            if block.get("type") == "field" and block.get("layout") == "horizontal":
                return True
        return False

    def _layout_metrics(self, blocks):
        if self._uses_compact_layout(blocks):
            return {
                "compact": True,
                "show_title": False,
                "show_footer": False,
                "show_scrollbar": False,
                "panel_x": COMPACT_PANEL_X,
                "panel_y": COMPACT_PANEL_Y,
                "panel_w": COMPACT_PANEL_W,
                "panel_h": COMPACT_PANEL_H,
                "content_x": COMPACT_CONTENT_X,
                "content_y": COMPACT_CONTENT_Y,
                "content_w": COMPACT_CONTENT_W,
                "content_h": COMPACT_CONTENT_H,
                "row_h": COMPACT_ROW_H,
                "row_gap": COMPACT_ROW_GAP,
                "hfield_h": COMPACT_HFIELD_H,
                "vfield_h": COMPACT_VFIELD_H,
                "label_h": COMPACT_LABEL_H,
                "input_h": COMPACT_INPUT_H,
                "button_h": COMPACT_BUTTON_H,
                "button_block_h": COMPACT_BUTTON_BLOCK_H,
                "arrow_w": COMPACT_LINK_ARROW_W,
                "radius": COMPACT_ROUND_RADIUS,
            }

        return {
            "compact": False,
            "show_title": True,
            "show_footer": True,
            "show_scrollbar": True,
            "panel_x": PANEL_X,
            "panel_y": PANEL_Y,
            "panel_w": PANEL_W,
            "panel_h": PANEL_H,
            "content_x": CONTENT_X,
            "content_y": CONTENT_Y,
            "content_w": CONTENT_W,
            "content_h": PANEL_H - 4,
            "row_h": ROW_H,
            "row_gap": ROW_GAP,
            "hfield_h": FIELD_H,
            "vfield_h": FIELD_H,
            "label_h": LABEL_H,
            "input_h": INPUT_H,
            "button_h": ROW_H,
            "button_block_h": ROW_H,
            "arrow_w": COMPACT_LINK_ARROW_W,
            "radius": 0,
            "scroll_x": PANEL_X + PANEL_W - SCROLL_W - 2,
            "scroll_y": PANEL_Y + 2,
            "scroll_h": PANEL_H - 4,
        }

    def _selected_block_index(self, blocks):
        if not blocks:
            return 0
        selected_form_index = getattr(self.f_b, "menu_cursor", 0)
        for block_index, block in enumerate(blocks):
            if block["type"] == "field":
                if selected_form_index in (
                    block.get("label_index"),
                    block.get("input_index"),
                ):
                    return block_index
            elif block.get("row_index") == selected_form_index:
                return block_index
        return 0

    def _block_height(self, block, metrics):
        if block.get("type") == "field":
            if block.get("layout") == "horizontal" and metrics.get("compact"):
                return metrics["hfield_h"]
            return metrics["vfield_h"]
        if block.get("type") == "button":
            return metrics["button_block_h"]
        return metrics["row_h"]

    def _visible_block_window(self, blocks, selected_index, metrics):
        if not blocks:
            return 0, 0

        inner_h = metrics["content_h"]
        top_index = min(max(0, int(selected_index)), len(blocks) - 1)
        total_h = self._block_height(blocks[top_index], metrics)

        while top_index > 0:
            next_h = self._block_height(blocks[top_index - 1], metrics) + metrics["row_gap"]
            if total_h + next_h > inner_h:
                break
            top_index -= 1
            total_h += next_h

        bottom_index = top_index
        used_h = 0
        while bottom_index < len(blocks):
            block_h = self._block_height(blocks[bottom_index], metrics)
            add_h = block_h if bottom_index == top_index else block_h + metrics["row_gap"]
            if used_h + add_h > inner_h:
                break
            used_h += add_h
            bottom_index += 1
        return top_index, bottom_index

    def _draw_vertical_scrollbar(self, metrics, item_count, top_index, visible_count):
        if not metrics.get("show_scrollbar", False):
            return

        track_x = metrics["scroll_x"]
        track_y = metrics["scroll_y"]
        track_h = metrics["scroll_h"]
        self._fill_rect(track_x, track_y, SCROLL_W, track_h, 0)
        self._rect(track_x, track_y, SCROLL_W, track_h, 1)

        visible_count = max(1, int(visible_count))
        if item_count <= visible_count:
            thumb_h = track_h - 2
            thumb_y = track_y + 1
        else:
            thumb_h = max(8, ((track_h - 2) * visible_count) // item_count)
            max_top = item_count - visible_count
            thumb_range = max(0, (track_h - 2) - thumb_h)
            thumb_y = track_y + 1 + (top_index * thumb_range // max_top)

        self._fill_rect(track_x + 1, thumb_y, max(1, SCROLL_W - 2), thumb_h, 1)

    def _draw_horizontal_scrollbar(
        self,
        x,
        y,
        width,
        total_chars,
        visible_chars,
        display_position,
        color=1,
    ):
        total_chars = max(1, int(total_chars))
        visible_chars = max(1, int(visible_chars))
        display_position = max(0, int(display_position))

        if total_chars < visible_chars:
            return False

        track_x = int(x)
        track_y = int(y)
        track_w = max(8, int(width))
        max_start = max(1, total_chars - visible_chars)
        thumb_w = max(8, (track_w * visible_chars) // total_chars)
        thumb_range = max(0, track_w - thumb_w)
        thumb_x = track_x + (min(display_position, max_start) * thumb_range // max_start)
        self._fill_rect(track_x, track_y, track_w, SCROLLBAR_H, 0)
        self._fill_rect(thumb_x, track_y, thumb_w, SCROLLBAR_H, color)
        return True

    def _draw_footer(self, state=""):
        state = str(state or "")
        if state == "":
            return
        self._fill_rect(0, STATUS_Y - 1, DISPLAY_WIDTH, 9, 1)
        self._draw_text_center(state, STATUS_Y, color=0)

    def _custom_bottom_text(self):
        provider = getattr(self.f_b, "bottom_page_text_provider", None)
        if callable(provider):
            try:
                value = provider()
            except Exception:
                value = ""
        else:
            value = provider
        return str(value or "")

    def _draw_custom_bottom_text(self):
        text_value = self._custom_bottom_text()
        if text_value == "":
            return False
        self._fill_rect(0, STATUS_Y, DISPLAY_WIDTH, 8, 0)
        self._draw_text_center(text_value[:21], STATUS_Y, color=1)
        return True

    def _input_view(self, block, input_active, visible_chars=None):
        key = block.get("key")
        if "raw_value" in block:
            raw_value = str(block.get("raw_value", "") or "")
            if raw_value == "":
                raw_value = " "
        else:
            raw_value = str(self.f_b.inp_list().get(key, " ") or " ")
        value_text = raw_value.rstrip()
        visible_chars = max(1, int(visible_chars or self.f_b.inp_cols()))
        if input_active:
            display_pos = int(block.get("display_pos", self.f_b.inp_display_position()))
            cursor_pos = int(block.get("cursor_pos", self.f_b.inp_cursor()))
            max_display = max(0, len(value_text) - visible_chars)
            if cursor_pos < display_pos:
                display_pos = cursor_pos
            elif cursor_pos >= display_pos + visible_chars:
                display_pos = cursor_pos - visible_chars + 1
            display_pos = min(max(0, display_pos), max_display)
        else:
            display_pos = 0
            cursor_pos = 0
        visible_text = value_text[display_pos : display_pos + visible_chars]
        has_overflow = len(value_text) > visible_chars
        return {
            "value_text": value_text,
            "cursor_pos": cursor_pos,
            "display_pos": display_pos,
            "visible_chars": visible_chars,
            "visible_text": visible_text,
            "has_overflow": has_overflow,
        }

    def _draw_input_cursor(self, cursor_x, input_y, input_h):
        self._fill_rect(cursor_x, input_y + 2, 2, max(1, input_h - 4), 1)

    def _row_text_value(self, text_value, max_width, selected=False):
        text_value = _display_text(text_value)
        visible_chars = _max_chars_for_width(max_width)
        if len(text_value) <= visible_chars:
            return text_value
        if selected:
            return _scroll_slice(text_value, visible_chars, _ticks_ms())
        return text_value[:visible_chars]

    def _draw_boxed_row(self, row_y, text_value, selected, metrics):
        row_y = int(row_y)
        row_fill = 1 if selected else 0
        text_color = 0 if selected else 1
        content_x = metrics["content_x"]
        content_w = metrics["content_w"]
        row_h = metrics["row_h"]
        self._fill_rect(content_x, row_y, content_w, row_h, row_fill)
        self._rect(content_x, row_y, content_w, row_h, 1)
        self._draw_text_in_rect(
            self._row_text_value(
                text_value,
                content_w - (COMPACT_ROW_TEXT_PAD_X * 2),
                selected=selected,
            ),
            content_x + COMPACT_ROW_TEXT_PAD_X,
            row_y + COMPACT_ROW_TEXT_PAD_Y,
            content_w - (COMPACT_ROW_TEXT_PAD_X * 2),
            row_h - 2,
            color=text_color,
            align="left",
        )

    def _draw_link_row(self, row_y, block, selected, metrics):
        row_y = int(row_y)
        content_x = metrics["content_x"]
        content_w = metrics["content_w"]
        row_h = metrics["row_h"]
        arrow_w = min(metrics["arrow_w"], max(8, content_w // 5))
        main_w = max(12, content_w - arrow_w)
        row_fill = 1 if selected else 0
        text_color = 0 if selected else 1

        self._fill_rect(content_x, row_y, main_w, row_h, row_fill)
        self._rect(content_x, row_y, main_w, row_h, 1)
        self._rect(content_x + main_w, row_y, arrow_w, row_h, 1)
        tri_x = content_x + main_w + COMPACT_LINK_TRI_PAD_X
        tri_right = content_x + content_w - COMPACT_LINK_TRI_PAD_X
        tri_top = row_y + COMPACT_LINK_TRI_PAD_Y
        tri_bottom = row_y + row_h - (COMPACT_LINK_TRI_PAD_Y + 1)
        tri_mid = row_y + row_h // 2
        self.fb.line(tri_x, tri_top, tri_right, tri_mid, 1)
        self.fb.line(tri_right, tri_mid, tri_x, tri_bottom, 1)
        self.fb.line(tri_x, tri_bottom, tri_x, tri_top, 1)
        self._draw_text_in_rect(
            self._row_text_value(
                block.get("text", ""),
                main_w - (COMPACT_LINK_TEXT_PAD_X * 2),
                selected=selected,
            ),
            content_x + COMPACT_LINK_TEXT_PAD_X,
            row_y + COMPACT_LINK_TEXT_PAD_Y,
            main_w - (COMPACT_LINK_TEXT_PAD_X * 2),
            row_h - 2,
            color=text_color,
            align="center",
        )

    def _draw_button_row(self, row_y, block, selected, metrics):
        row_y = int(row_y)
        content_x = metrics["content_x"]
        content_w = metrics["content_w"]
        button_h = metrics["button_h"]
        label = block.get("text", "")
        align = self._normalize_align(block.get("align"), default="center")
        button_w = min(
            content_w,
            max(COMPACT_BUTTON_MIN_W, _text_width(label) + COMPACT_BUTTON_PAD_X * 2),
        )
        if align == "left":
            button_x = content_x
        elif align == "right":
            button_x = content_x + content_w - button_w
        else:
            button_x = content_x + max(0, (content_w - button_w) // 2)
        button_y = row_y + max(0, (metrics["button_block_h"] - button_h) // 2) + COMPACT_BUTTON_Y_OFFSET

        if metrics.get("compact"):
            if selected:
                self._rounded_rect(
                    button_x,
                    button_y,
                    button_w,
                    button_h,
                    color=1,
                    fill=True,
                    radius=metrics["radius"],
                )
                text_color = 0
            else:
                self._rounded_rect(
                    button_x,
                    button_y,
                    button_w,
                    button_h,
                    color=1,
                    fill=False,
                    radius=metrics["radius"],
                )
                text_color = 1
        else:
            if selected:
                self._rounded_rect(
                    button_x,
                    button_y,
                    button_w,
                    button_h,
                    color=1,
                    fill=True,
                    radius=metrics["radius"],
                )
                text_color = 0
            else:
                self._rounded_rect(
                    button_x,
                    button_y,
                    button_w,
                    button_h,
                    color=1,
                    fill=False,
                    radius=metrics["radius"],
                )
                text_color = 1

        self._draw_text_in_rect(
            label,
            button_x + COMPACT_BUTTON_TEXT_PAD_X,
            button_y + COMPACT_BUTTON_TEXT_PAD_Y,
            button_w - (COMPACT_BUTTON_TEXT_PAD_X * 2),
            max(1, button_h - COMPACT_BUTTON_TEXT_PAD_Y),
            color=text_color,
            align="center",
        )

    def _draw_compact_horizontal_field(self, field_y, block, selected, metrics):
        field_y = int(field_y)
        content_x = metrics["content_x"]
        content_w = metrics["content_w"]
        field_h = metrics["hfield_h"]
        label = block.get("label", "")
        input_active = getattr(self.f_b, "menu_cursor", -1) == block.get("input_index")
        preferred_label_w = getattr(
            self.f_b, "compact_hfield_label_w", COMPACT_HFIELD_LABEL_W
        )
        label_pad_x = getattr(
            self.f_b, "compact_hfield_label_pad_x", COMPACT_HFIELD_LABEL_PAD_X
        )
        try:
            preferred_label_w = int(preferred_label_w or COMPACT_HFIELD_LABEL_W)
        except Exception:
            preferred_label_w = COMPACT_HFIELD_LABEL_W
        try:
            label_pad_x = int(label_pad_x or 0)
        except Exception:
            label_pad_x = COMPACT_HFIELD_LABEL_PAD_X
        if label_pad_x < 0:
            label_pad_x = 0
        label_min_w = max(
            12,
            _text_width(label) + (label_pad_x * 2) + 2,
        )

        label_w = min(
            max(label_min_w, preferred_label_w),
            max(label_min_w, content_w - COMPACT_HFIELD_MIN_INPUT_W),
        )
        input_x = content_x + label_w + COMPACT_HFIELD_GAP_X
        input_w = max(
            COMPACT_HFIELD_MIN_INPUT_W,
            content_w - label_w - COMPACT_HFIELD_GAP_X,
        )
        input_y = field_y + COMPACT_HFIELD_INPUT_Y_OFFSET
        input_h = min(field_h, max(8, COMPACT_HFIELD_INPUT_H))
        text_x = input_x + COMPACT_HFIELD_INPUT_INSET_X
        text_max_w = max(
            6,
            input_w - (COMPACT_HFIELD_INPUT_INSET_X + COMPACT_HFIELD_INPUT_RIGHT_PAD),
        )
        view = self._input_view(
            block,
            input_active,
            visible_chars=_max_chars_for_width(text_max_w),
        )

        self._fill_rect(content_x, field_y, label_w, field_h, 1)
        self._rect(content_x, field_y, label_w, field_h, 1)
        self._draw_text_in_rect(
            label,
            content_x + label_pad_x,
            field_y + COMPACT_HFIELD_LABEL_PAD_Y,
            label_w - (label_pad_x * 2),
            max(1, field_h - COMPACT_HFIELD_LABEL_PAD_Y),
            color=0,
            align="center",
        )

        if COMPACT_HFIELD_INPUT_RADIUS > 0:
            self._rounded_rect(
                input_x,
                input_y,
                input_w,
                input_h,
                color=1,
                fill=False,
                radius=COMPACT_HFIELD_INPUT_RADIUS,
            )
        else:
            self._rect(input_x, input_y, input_w, input_h, 1)
        self._draw_text(
            view["visible_text"],
            text_x,
            input_y + max(0, (input_h - CHAR_HEIGHT) // 2),
            color=1,
            max_width=text_max_w,
        )

        if input_active and self._blink_enabled() and self._cursor_visible:
            visible_cursor = self.f_b.inp_cursor() - view["display_pos"]
            if visible_cursor < 0:
                visible_cursor = 0
            if visible_cursor > view["visible_chars"]:
                visible_cursor = view["visible_chars"]
            cursor_x = min(
                input_x + input_w - COMPACT_HFIELD_CURSOR_RIGHT_PAD,
                text_x + visible_cursor * CHAR_ADVANCE,
            )
            self._draw_input_cursor(cursor_x, input_y, input_h)

        if view["has_overflow"]:
            self._draw_horizontal_scrollbar(
                input_x + COMPACT_HFIELD_SCROLL_INSET_X,
                input_y + input_h - 2,
                max(
                    8,
                    input_w
                    - (COMPACT_HFIELD_SCROLL_INSET_X + COMPACT_HFIELD_SCROLL_RIGHT_PAD),
                ),
                max(view["visible_chars"], len(view["value_text"])),
                view["visible_chars"],
                view["display_pos"],
                color=1,
            )

    def _draw_boxed_field(self, field_y, block, selected, metrics):
        if metrics.get("compact") and block.get("layout") == "horizontal":
            self._draw_compact_horizontal_field(field_y, block, selected, metrics)
            return

        label_x = metrics["content_x"]
        label_y = field_y
        label_w = metrics["content_w"]
        label_h = metrics["label_h"]
        input_x = metrics["content_x"]
        if metrics.get("compact"):
            input_y = field_y + label_h + COMPACT_VFIELD_LABEL_INPUT_GAP
        else:
            input_y = field_y + INPUT_Y_OFFSET
        input_w = metrics["content_w"]
        input_h = metrics["input_h"]
        label = block.get("label", "")
        input_active = getattr(self.f_b, "menu_cursor", -1) == block.get("input_index")
        compact_box = metrics.get("compact")
        text_x = input_x + (COMPACT_VFIELD_INPUT_INSET_X if compact_box else 2)
        text_max_w = input_w - (
            COMPACT_VFIELD_INPUT_INSET_X + COMPACT_VFIELD_INPUT_RIGHT_PAD
            if compact_box
            else 2
        )
        view = self._input_view(
            block,
            input_active,
            visible_chars=_max_chars_for_width(text_max_w) if compact_box else None,
        )

        if metrics.get("compact"):
            self._fill_rect(label_x, label_y, label_w, label_h, 1)
            self._rect(label_x, label_y, label_w, label_h, 1)
            self._draw_text_in_rect(
                label,
                label_x + COMPACT_VFIELD_LABEL_PAD_X,
                label_y + COMPACT_VFIELD_LABEL_PAD_Y,
                label_w - (COMPACT_VFIELD_LABEL_PAD_X * 2),
                max(1, label_h - COMPACT_VFIELD_LABEL_PAD_Y),
                color=0,
                align="center",
            )
        else:
            if selected:
                self._fill_rect(label_x, label_y, label_w, label_h, 1)
                self._rect(label_x, label_y, label_w, label_h, 1)
                label_color = 0
            else:
                label_color = 1
            self._draw_text(
                label,
                label_x + 1,
                label_y + 1,
                color=label_color,
                max_width=label_w - 2,
            )

        self._fill_rect(input_x, input_y, input_w, input_h, 0)
        text_y = input_y + max(1, (input_h - CHAR_HEIGHT) // 2)
        scroll_y = input_y + input_h - 1

        self._draw_text(
            view["visible_text"],
            text_x,
            text_y,
            color=1,
            max_width=text_max_w,
        )

        if input_active and self._blink_enabled() and self._cursor_visible:
            visible_cursor = self.f_b.inp_cursor() - view["display_pos"]
            if visible_cursor < 0:
                visible_cursor = 0
            if visible_cursor > view["visible_chars"]:
                visible_cursor = view["visible_chars"]
            cursor_x = text_x + visible_cursor * CHAR_ADVANCE
            max_cursor_x = (
                input_x + input_w - COMPACT_VFIELD_CURSOR_RIGHT_PAD
                if compact_box
                else input_x + input_w - 2
            )
            if cursor_x > max_cursor_x:
                cursor_x = max_cursor_x
            self._draw_input_cursor(cursor_x, input_y, input_h)

        if view["has_overflow"]:
            self._draw_horizontal_scrollbar(
                input_x + (COMPACT_VFIELD_SCROLL_INSET_X if compact_box else 1),
                scroll_y,
                input_w
                - (
                    COMPACT_VFIELD_SCROLL_INSET_X + COMPACT_VFIELD_SCROLL_RIGHT_PAD
                    if compact_box
                    else 2
                ),
                max(view["visible_chars"], len(view["value_text"])),
                view["visible_chars"],
                view["display_pos"],
                color=1,
            )

        if metrics.get("compact"):
            self._rect(input_x, input_y, input_w, input_h, 1)
        else:
            self._rect(input_x, input_y, input_w, input_h, 1)

    def _refresh_boxed(self, state="", force=False):
        self._sync_blink_signature()
        state = self._normalized_state(state)
        blocks = self._boxed_blocks()
        metrics = self._layout_metrics(blocks)
        selected_index = self._selected_block_index(blocks)
        top_index, bottom_index = self._visible_block_window(blocks, selected_index, metrics)

        self._clear()
        if metrics.get("show_title"):
            self._draw_text_center(self._title_text(), TITLE_Y, color=1)
        self._rect(
            metrics["panel_x"],
            metrics["panel_y"],
            metrics["panel_w"],
            metrics["panel_h"],
            1,
        )

        current_y = metrics["content_y"]
        for block_index in range(top_index, bottom_index):
            block = blocks[block_index]
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
            current_y += self._block_height(block, metrics) + metrics["row_gap"]

        self._draw_vertical_scrollbar(metrics, len(blocks), top_index, bottom_index - top_index)
        if metrics.get("show_footer"):
            self._draw_footer(state=state)
        elif state == "":
            self._draw_custom_bottom_text()
        self._flush(force=force)
        if getattr(self, "steady_bottom_page", False) and state == "":
            self._flush_bottom_page(force=False)

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

    def restore_bottom_row(self):
        if getattr(self, "steady_bottom_page", False):
            self._flush_bottom_page(force=False)
            self.last_state = ""
            return
        if self._use_boxed_layout() or self._use_table_layout():
            self.refresh(state="")
            return
        try:
            self._draw_page(self.f_b.buffer(), self.f_b.rows - 1)
        except Exception:
            self._clear_page(7)
        self.last_state = ""

    def refresh(self, state=None, force=False):
        set_active_view("form")

        if state is None:
            state = self.nav.current_state() if self.nav is not None else ""
        state = self._normalized_state(state)

        if self._use_table_layout():
            self._refresh_table(state=state, force=force)
            return

        if self._use_boxed_layout():
            self._refresh_boxed(state=state, force=force)
            return

        buf = self.f_b.buffer()
        ref_rows = self.f_b.ref_ar()
        for page_index in range(ref_rows[0], min(ref_rows[1], self.f_b.rows)):
            self._draw_page(buf, page_index)

        if self.nav is not None:
            nav_overlay_visible = (
                str(state or "") != ""
                and str(state or "") == self.nav.current_state()
                and self.nav.is_visible()
            )
            self.nav.set_restore_callback(
                self.restore_bottom_row if nav_overlay_visible else None
            )

        state = str(state or "")
        if state != "":
            self._draw_state(state)
        elif self.last_state != "":
            self.restore_bottom_row()

        self.last_state = state
