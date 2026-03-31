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

    def _use_boxed_layout(self):
        return str(getattr(self.f_b, "ui_style", "") or "") == "boxed"

    def _blink_enabled(self):
        return self._use_boxed_layout() and bool(getattr(self.f_b, "blink_cursor", False))

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

    def _flush(self, force=False):
        graphics_callable = self.disp_out.graphics
        flush_kwargs = {
            "page": 0,
            "column": 0,
            "width": DISPLAY_WIDTH,
            "pages": DISPLAY_PAGES,
        }

        if not force:
            graphics_callable(self.buf, **flush_kwargs)
            return

        wrapped_flushed = False
        try:
            graphics_callable(self.buf, **flush_kwargs)
            wrapped_flushed = True
        except Exception:
            wrapped_flushed = False

        raw_graphics = self._unwrap_graphics(graphics_callable)
        if callable(raw_graphics) and raw_graphics is not graphics_callable:
            try:
                raw_graphics(self.buf, **flush_kwargs)
                return
            except Exception:
                if wrapped_flushed:
                    return
                raise

        if not wrapped_flushed:
            graphics_callable(self.buf, **flush_kwargs)

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

    def _boxed_fields(self):
        if hasattr(self.f_b, "_input_indices"):
            input_indices = self.f_b._input_indices()
        else:
            input_indices = [
                index
                for index, item in enumerate(getattr(self.f_b, "form_list", []))
                if "inp_" in str(item)
            ]

        fields = []
        for input_index in input_indices:
            label = ""
            if input_index > 0:
                label = self.f_b.form_list[input_index - 1]
            fields.append((input_index, _display_text(label), self.f_b.form_list[input_index]))
        return fields

    def _selected_field_index(self, fields):
        if not fields:
            return 0
        selected_form_index = getattr(self.f_b, "menu_cursor", 0)
        for field_pos, field in enumerate(fields):
            if field[0] == selected_form_index:
                return field_pos
        return 0

    def _top_field_index(self, field_count, selected_index):
        if field_count <= VISIBLE_FIELDS:
            return 0
        top_index = selected_index - VISIBLE_FIELDS + 1
        if top_index < 0:
            top_index = 0
        max_top = field_count - VISIBLE_FIELDS
        if top_index > max_top:
            top_index = max_top
        return top_index

    def _field_y(self, field_slot):
        field_slot = max(0, int(field_slot))
        inner_y = CONTENT_Y
        inner_h = PANEL_H - 4
        if VISIBLE_FIELDS <= 1:
            return inner_y
        total_h = VISIBLE_FIELDS * FIELD_H
        gap_space = max(0, inner_h - total_h)
        gap = gap_space // (VISIBLE_FIELDS - 1)
        return inner_y + field_slot * (FIELD_H + gap)

    def _draw_vertical_scrollbar(self, item_count, top_index):
        track_x = PANEL_X + PANEL_W - SCROLL_W - 2
        track_y = PANEL_Y + 2
        track_h = PANEL_H - 4
        self._fill_rect(track_x, track_y, SCROLL_W, track_h, 0)
        self._rect(track_x, track_y, SCROLL_W, track_h, 1)

        if item_count <= VISIBLE_FIELDS:
            thumb_h = track_h - 2
            thumb_y = track_y + 1
        else:
            thumb_h = max(8, ((track_h - 2) * VISIBLE_FIELDS) // item_count)
            max_top = item_count - VISIBLE_FIELDS
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

    def _draw_boxed_field(self, field_slot, field_index, label, key):
        field_y = self._field_y(field_slot)
        label_x = CONTENT_X
        label_y = field_y
        label_w = CONTENT_W
        input_x = CONTENT_X
        input_y = field_y + INPUT_Y_OFFSET
        input_w = CONTENT_W
        input_h = INPUT_H
        selected = field_index == getattr(self.f_b, "menu_cursor", -1)

        if selected:
            self._fill_rect(label_x, label_y, label_w, LABEL_H, 1)
            self._rect(label_x, label_y, label_w, LABEL_H, 1)
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

        raw_value = str(self.f_b.inp_list().get(key, " ") or " ")
        value_text = raw_value.rstrip()
        display_pos = self.f_b.inp_display_position() if selected else 0
        visible_chars = max(1, self.f_b.inp_cols())
        visible_text = value_text[display_pos : display_pos + visible_chars]
        has_overflow = len(value_text) >= visible_chars

        self._fill_rect(input_x, input_y, input_w, input_h, 0)
        text_color = 1
        scroll_color = 1

        text_x = input_x + 2
        text_y = input_y + 2
        scroll_y = field_y + FIELD_H - 1

        self._draw_text(
            visible_text,
            text_x,
            text_y,
            color=text_color,
            max_width=input_w - 2,
        )

        if selected and self._cursor_visible:
            visible_cursor = self.f_b.inp_cursor() - display_pos
            if visible_cursor < 0:
                visible_cursor = 0
            if visible_cursor > visible_chars:
                visible_cursor = visible_chars
            cursor_x = text_x + visible_cursor * CHAR_ADVANCE
            max_cursor_x = input_x + input_w - 2
            if cursor_x > max_cursor_x:
                cursor_x = max_cursor_x
            self._fill_rect(cursor_x, input_y + 2, 2, input_h - 4, 1)

        if has_overflow:
            self._draw_horizontal_scrollbar(
                input_x + 1,
                scroll_y,
                input_w - 2,
                max(visible_chars, len(value_text)),
                visible_chars,
                display_pos,
                color=scroll_color,
            )

        self._rect(input_x, input_y, input_w, input_h, 1)

    def _refresh_boxed(self, state="", force=False):
        self._sync_blink_signature()
        state = str(state or "")
        fields = self._boxed_fields()
        selected_index = self._selected_field_index(fields)
        top_index = self._top_field_index(len(fields), selected_index)

        self._clear()
        self._draw_text_center(self._title_text(), TITLE_Y, color=1)
        self._rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, 1)

        for slot in range(VISIBLE_FIELDS):
            field_pos = top_index + slot
            if field_pos >= len(fields):
                break
            field_index, label, key = fields[field_pos]
            self._draw_boxed_field(slot, field_index, label, key)

        self._draw_vertical_scrollbar(len(fields), top_index)
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

    def restore_bottom_row(self):
        if self._use_boxed_layout():
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
