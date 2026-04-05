import builtins

import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

from process_modules.ui_context import set_active_view

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

try:
    import framebuf  # type: ignore
except ImportError:
    from mocking import framebuf  # type: ignore


DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_PAGES = DISPLAY_HEIGHT // 8
CHAR_HEIGHT = 8
CHAR_ADVANCE = 6

VISIBLE_ROWS = 3
LIST_X = 2
LIST_Y = 11
LIST_W = 124
LIST_H = 44
ROW_HEIGHT = 13
ROW_GAP = 1
SCROLL_W = 4
CONTENT_X = LIST_X + 2
CONTENT_Y = LIST_Y + 2
CONTENT_W = LIST_W - SCROLL_W - 5
STATUS_Y = 56


def _text_width(text_value):
    text_value = str(text_value)
    if not text_value:
        return 0
    return len(text_value) * CHAR_ADVANCE - 1


def _display_text(text_value):
    return str(text_value or "").replace("_", " ")


def _clip_text(text_value, max_chars):
    text_value = _display_text(text_value)
    if max_chars <= 0:
        return ""
    if len(text_value) <= max_chars:
        return text_value
    if max_chars <= 3:
        return text_value[:max_chars]
    return text_value[: max_chars - 3] + "..."


def _clip_text_px(text_value, max_width):
    if max_width <= 0:
        return ""
    max_chars = max(1, (int(max_width) + 1) // CHAR_ADVANCE)
    return _clip_text(text_value, max_chars)


def _title_case(text_value):
    parts = str(text_value or "").split(" ")
    titled = []
    for part in parts:
        if not part:
            continue
        first = part[:1]
        rest = part[1:]
        titled.append(first.upper() + rest.lower())
    return " ".join(titled)


class Tbf:
    def __init__(self, disp_out, chrs, m_b, nav=None):
        self.disp_out = disp_out
        self.chrs = chrs
        self.m_b = m_b
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

    def _title_text(self):
        try:
            from data_modules.object_handler import current_app

            app_name = str(current_app[0] or "").strip()
        except Exception:
            app_name = ""

        if not app_name:
            return "Menu"

        formatted = _display_text(app_name)
        if "_" in app_name or app_name.islower():
            return _title_case(formatted)
        return formatted

    def _force_default_keypad(self):
        try:
            typer = getattr(builtins, "typer", None)
            keymap = getattr(typer, "keypad_map", None)
            if keymap is not None:
                keymap.key_change("d")
        except Exception:
            pass

        if self.nav is not None:
            try:
                self.nav.state_change(state="d", locked=False, show=False)
            except Exception:
                pass

    def _normalize_cursor(self, items):
        if not items:
            self.m_b.menu_cursor = 0
            if hasattr(self.m_b, "menu_display_position"):
                self.m_b.menu_display_position = 0
            if hasattr(self.m_b, "display_cursor"):
                self.m_b.display_cursor = 0
            return 0

        if self.m_b.menu_cursor < 0:
            self.m_b.menu_cursor = 0
        elif self.m_b.menu_cursor >= len(items):
            self.m_b.menu_cursor = len(items) - 1

        return self.m_b.menu_cursor

    def _visible_window(self, item_count, selected_index):
        if item_count <= VISIBLE_ROWS:
            top_index = 0
        else:
            max_top = item_count - VISIBLE_ROWS
            try:
                top_index = int(getattr(self.m_b, "menu_display_position", 0) or 0)
            except Exception:
                top_index = 0
            top_index = min(max(0, top_index), max_top)
            if selected_index < top_index or selected_index >= top_index + VISIBLE_ROWS:
                top_index = self._top_index(item_count, selected_index)

        if hasattr(self.m_b, "menu_display_position"):
            self.m_b.menu_display_position = top_index
        if hasattr(self.m_b, "display_cursor"):
            self.m_b.display_cursor = selected_index - top_index
        return top_index

    def _top_index(self, item_count, selected_index):
        if item_count <= VISIBLE_ROWS:
            return 0
        if selected_index < 0:
            return 0
        if selected_index >= item_count:
            selected_index = item_count - 1
        top_index = selected_index - VISIBLE_ROWS + 1
        if top_index < 0:
            top_index = 0
        max_top = item_count - VISIBLE_ROWS
        if top_index > max_top:
            top_index = max_top
        return top_index

    def _clear(self, color=0):
        self.fb.fill(1 if color else 0)

    def _rect(self, x, y, width, height, color=1):
        self.fb.rect(int(x), int(y), int(width), int(height), 1 if color else 0)

    def _fill_rect(self, x, y, width, height, color=1):
        self.fb.fill_rect(int(x), int(y), int(width), int(height), 1 if color else 0)

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

    def _draw_scrollbar(self, item_count, top_index):
        track_x = LIST_X + LIST_W - SCROLL_W - 1
        track_y = LIST_Y + 2
        track_h = LIST_H - 4

        self._rect(track_x, track_y, SCROLL_W, track_h, 1)

        if item_count <= VISIBLE_ROWS:
            thumb_h = track_h - 2
            thumb_y = track_y + 1
        else:
            thumb_h = max(8, ((track_h - 2) * VISIBLE_ROWS) // item_count)
            max_top = item_count - VISIBLE_ROWS
            thumb_range = max(0, (track_h - 2) - thumb_h)
            thumb_y = track_y + 1 + (top_index * thumb_range // max_top)

        self._fill_rect(track_x + 1, thumb_y, max(1, SCROLL_W - 2), thumb_h, 1)

    def _draw_footer(self, state=""):
        state = str(state or "")
        if state == "":
            return
        self._fill_rect(0, STATUS_Y - 1, DISPLAY_WIDTH, 9, 1)
        self._draw_text_center(state, STATUS_Y, color=0)

    def _flush(self):
        self.disp_out.graphics(
            self.buf,
            page=0,
            column=0,
            width=DISPLAY_WIDTH,
            pages=DISPLAY_PAGES,
        )

    def restore_bottom_row(self):
        self.refresh(state="")

    def refresh(self, state=None):
        set_active_view("menu")
        self._force_default_keypad()

        state = self.nav.current_state() if self.nav is not None else ""

        items = [_display_text(item) for item in getattr(self.m_b, "menu_list", [])]
        selected_index = self._normalize_cursor(items)
        top_index = self._visible_window(len(items), selected_index)
        state = str(state or "")

        self._clear()
        self._draw_text_center(self._title_text(), 1, color=1)
        self._rect(LIST_X, LIST_Y, LIST_W, LIST_H, 1)

        for slot in range(VISIBLE_ROWS):
            item_index = top_index + slot
            if item_index >= len(items):
                break

            row_y = CONTENT_Y + slot * (ROW_HEIGHT + ROW_GAP)
            selected = item_index == selected_index
            row_color = 1 if selected else 0
            text_color = 0 if selected else 1

            self._fill_rect(CONTENT_X, row_y, CONTENT_W, ROW_HEIGHT, row_color)
            self._rect(CONTENT_X, row_y, CONTENT_W, ROW_HEIGHT, 1)
            self._draw_text_in_rect(
                items[item_index],
                CONTENT_X + 2,
                row_y + 1,
                CONTENT_W - 4,
                ROW_HEIGHT - 2,
                color=text_color,
                align="left",
            )

        self._draw_scrollbar(len(items), top_index)
        self._draw_footer(state=state)
        self._flush()

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
