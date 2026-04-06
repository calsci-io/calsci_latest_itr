import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import utime as time  # type: ignore
from urandom import getrandbits  # type: ignore

try:
    from sleeping_features import swdt, test_deep_sleep_awake
except Exception:
    class _DummySwdt:
        def feed(self):
            return None

    swdt = _DummySwdt()

    def test_deep_sleep_awake():
        return None


from apps.installed_apps._mono_ui import (
    CHAR_ADVANCE,
    CHAR_HEIGHT,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    MonoCanvas,
)
from data_modules.object_handler import (
    keyin,
    keymap,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)
from process_modules.keypad_modes import reset_mode, should_auto_reset_after_input, toggle_mode_lock
from process_modules.navigation import request_navigation_from_key
from process_modules.ui_context import set_active_view


OUTPUT_X = 0
OUTPUT_Y = 0
OUTPUT_W = DISPLAY_WIDTH
OUTPUT_H = 45

INPUT_X = 0
INPUT_Y = 47
INPUT_W = DISPLAY_WIDTH
INPUT_H = DISPLAY_HEIGHT - INPUT_Y

OUTPUT_TEXT_X = OUTPUT_X + 3
OUTPUT_TEXT_Y = OUTPUT_Y + 2
OUTPUT_SCROLLBAR_W = 5
OUTPUT_TEXT_W = OUTPUT_W - 3 - OUTPUT_SCROLLBAR_W - 3
OUTPUT_TEXT_H = OUTPUT_H - 4
OUTPUT_LINE_HEIGHT = CHAR_HEIGHT

INPUT_TEXT_X = INPUT_X + 4
INPUT_TEXT_W = INPUT_W - 8
INPUT_SCROLLBAR_X = INPUT_X + 3
INPUT_SCROLLBAR_Y = INPUT_Y + INPUT_H - 3
INPUT_SCROLLBAR_W = INPUT_W - 6

CURSOR_BLINK_MS = 450
NOISE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

DUMMY_REPLY = (
    "An amino acid is a small organic molecule that usually contains an amino "
    "group, a carboxyl group, a hydrogen atom, and a variable side chain around "
    "a central carbon. Amino acids join through peptide bonds to form proteins, "
    "which help build tissues, enzymes, hormones, and many essential cell structures."
)


def _show_startup_logo():
    try:
        from apps.root.chatbot_ai import _show_startup_logo as _legacy_logo

        _legacy_logo()
    except Exception:
        pass


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    return int(time.time() * 1000)


def _ticks_diff(now_ms, prev_ms):
    if hasattr(time, "ticks_diff"):
        return time.ticks_diff(now_ms, prev_ms)
    return now_ms - prev_ms


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(float(ms) / 1000.0)


def _sleep_s(seconds):
    seconds = float(seconds)
    if seconds <= 0:
        return
    time.sleep(seconds)


def _rand_idx(limit):
    if limit <= 0:
        return 0
    return getrandbits(16) % limit


def _rand_ms(min_ms, max_ms):
    if max_ms <= min_ms:
        return min_ms
    return min_ms + (getrandbits(16) % (max_ms - min_ms + 1))


def _split_word(word, limit):
    if limit <= 0:
        return [word]
    chunks = []
    index = 0
    while index < len(word):
        chunks.append(word[index : index + limit])
        index += limit
    return chunks or [""]


def _wrap_text(text_value, max_chars):
    max_chars = max(1, int(max_chars or 1))
    lines = []
    paragraphs = str(text_value or "").split("\n")

    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current = ""
        for word in words:
            if len(word) > max_chars:
                if current:
                    lines.append(current)
                    current = ""
                chunks = _split_word(word, max_chars)
                for chunk in chunks[:-1]:
                    lines.append(chunk)
                current = chunks[-1]
                continue

            candidate = word if not current else current + " " + word
            if len(candidate) <= max_chars:
                current = candidate
            else:
                lines.append(current)
                current = word

        if current:
            lines.append(current)

    return lines or [""]


def _read_key_with_local_back(idle_callback=None):
    _sleep_s(max(0.2, float(typer.debounce_delay())))
    col, row = keyin.keypad_loop(idle_callback=idle_callback)
    token = keymap.key_out(col=int(col), row=int(row))
    swdt.feed()

    if token in ("off", "on"):
        test_deep_sleep_awake()
        return "off"

    if token == "lock":
        toggle_mode_lock(keymap=keymap, nav=nav)
        return ""

    if should_auto_reset_after_input(keymap=keymap, nav=nav, key_name=token):
        reset_mode(keymap=keymap, nav=nav)

    return token


class _ChatScreen:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.focus = "input"
        self.response_text = ""
        self.response_lines = [""]
        self.response_scroll = 0
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()
        self._configure_form()
        self.clear_response()

    def _configure_form(self):
        self.input_text = ""
        self.input_cursor = 0
        self.input_display_position = 0
        self.stream_preview_char = ""

    def _input_visible_chars(self):
        return max(1, (INPUT_TEXT_W + 1) // CHAR_ADVANCE)

    def _input_value(self):
        return str(getattr(self, "input_text", "") or "")

    def _reset_cursor_blink(self):
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()

    def _sync_input_view(self):
        visible_cols = self._input_visible_chars()
        text_len = len(self._input_value())
        self.input_cursor = min(max(0, int(self.input_cursor)), text_len)
        max_display = max(0, text_len - visible_cols)
        self.input_display_position = min(
            max(0, int(self.input_display_position)),
            max_display,
        )
        if self.input_cursor < self.input_display_position:
            self.input_display_position = self.input_cursor
        elif self.input_cursor > self.input_display_position + visible_cols:
            self.input_display_position = self.input_cursor - visible_cols
        elif self.input_cursor == self.input_display_position + visible_cols:
            self.input_display_position = max(0, self.input_cursor - visible_cols + 1)

    def handle_input_key(self, token):
        token = str(token or "")
        if token == "":
            return

        if token == "nav_l":
            if self.input_cursor > 0:
                self.input_cursor -= 1
        elif token == "nav_r":
            if self.input_cursor < len(self.input_text):
                self.input_cursor += 1
        elif token in ("nav_b", "undo"):
            if self.input_cursor > 0:
                self.input_text = (
                    self.input_text[: self.input_cursor - 1]
                    + self.input_text[self.input_cursor :]
                )
                self.input_cursor -= 1
        elif token == "AC":
            self.input_text = ""
            self.input_cursor = 0
            self.input_display_position = 0
        else:
            if token == "tab":
                token = " "
            self.input_text = (
                self.input_text[: self.input_cursor]
                + token
                + self.input_text[self.input_cursor :]
            )
            self.input_cursor += len(token)

        self._sync_input_view()
        self._reset_cursor_blink()

    def set_response(self, text_value):
        self.response_text = str(text_value or "")
        max_chars = max(1, OUTPUT_TEXT_W // CHAR_ADVANCE)
        self.response_lines = _wrap_text(self.response_text, max_chars)
        self.response_scroll = 0

    def clear_response(self):
        self.response_text = ""
        self.response_lines = []
        self.response_scroll = 0
        self.clear_stream_preview()

    def append_response_char(self, char):
        self.response_text += str(char or "")
        max_chars = max(1, OUTPUT_TEXT_W // CHAR_ADVANCE)
        self.response_lines = _wrap_text(self.response_text, max_chars)
        self.response_scroll = self.max_output_scroll()

    def set_stream_preview(self, char):
        self.stream_preview_char = str(char or "")

    def clear_stream_preview(self):
        self.stream_preview_char = ""

    def _output_visible_scroll(self):
        visible = self.visible_output_lines()
        scroll = self.response_scroll
        preview_row = None

        if self.stream_preview_char:
            preview_row, _ = self._preview_position()
            if preview_row < scroll:
                scroll = preview_row
            elif preview_row >= scroll + visible:
                scroll = preview_row - visible + 1

        return max(0, scroll), preview_row

    def _preview_position(self):
        max_cols = max(1, OUTPUT_TEXT_W // CHAR_ADVANCE)
        lines = self.response_lines if self.response_lines else [""]
        last_line = lines[-1]
        row = len(lines) - 1
        col = len(last_line)
        if col >= max_cols:
            row += 1
            col = 0
        return row, col

    def max_output_scroll(self):
        visible = self.visible_output_lines()
        return max(0, len(self.response_lines) - visible)

    def visible_output_lines(self):
        return max(1, OUTPUT_TEXT_H // OUTPUT_LINE_HEIGHT)

    def focus_input(self):
        self.focus = "input"
        self._reset_cursor_blink()

    def focus_output(self):
        self.focus = "output"

    def scroll_output(self, step):
        self.response_scroll = min(
            max(0, self.response_scroll + int(step or 0)),
            self.max_output_scroll(),
        )

    def is_output_at_bottom(self):
        return self.response_scroll >= self.max_output_scroll()

    def idle(self):
        nav.maybe_hide()
        if self.focus != "input":
            return
        if nav.is_visible():
            self._reset_cursor_blink()
            return

        now_ms = _ticks_ms()
        if _ticks_diff(now_ms, self._cursor_last_toggle) >= CURSOR_BLINK_MS:
            self._cursor_visible = not self._cursor_visible
            self._cursor_last_toggle = now_ms
            self.render()

    def _draw_focus_frame(self, x, y, width, height):
        self.canvas.rect(x + 1, y + 1, width - 2, height - 2, 1)

    def _draw_vertical_scrollbar(self, x, y, width, height, total_rows, visible_rows, start_row):
        self.canvas.rect(x, y, width, height, 1)
        if total_rows <= 0:
            return

        inner_y = y + 1
        inner_h = max(1, height - 2)
        if total_rows <= visible_rows:
            thumb_h = inner_h
            thumb_y = inner_y
        else:
            thumb_h = max(4, (inner_h * visible_rows) // total_rows)
            max_thumb_y = inner_h - thumb_h
            thumb_y = inner_y + (max_thumb_y * start_row) // max(1, total_rows - visible_rows)

        fill_w = max(1, width - 2)
        self.canvas.fill_rect(x + 1, thumb_y, fill_w, thumb_h, 1)

    def _draw_horizontal_scrollbar(self, x, y, width, total_cols, visible_cols, start_col):
        self.canvas.hline(x, y, width, 1)
        if total_cols <= 0:
            return

        if total_cols <= visible_cols:
            thumb_w = width
            thumb_x = x
        else:
            thumb_w = max(8, (width * visible_cols) // total_cols)
            max_thumb_x = width - thumb_w
            thumb_x = x + (max_thumb_x * start_col) // max(1, total_cols - visible_cols)

        self.canvas.fill_rect(thumb_x, y - 1, thumb_w, 3, 1)

    def _draw_output_pane(self):
        self.canvas.rect(OUTPUT_X, OUTPUT_Y, OUTPUT_W, OUTPUT_H, 1)
        if self.focus == "output":
            self._draw_focus_frame(OUTPUT_X, OUTPUT_Y, OUTPUT_W, OUTPUT_H)

        visible = self.visible_output_lines()
        draw_scroll, preview_row = self._output_visible_scroll()
        lines = self.response_lines[draw_scroll : draw_scroll + visible]
        for index, line in enumerate(lines):
            y = OUTPUT_TEXT_Y + index * OUTPUT_LINE_HEIGHT
            self.canvas.draw_text(line, OUTPUT_TEXT_X, y, 1)

        if self.stream_preview_char and preview_row is not None:
            preview_view_row = preview_row - draw_scroll
            if 0 <= preview_view_row < visible:
                _, preview_col = self._preview_position()
                preview_x = OUTPUT_TEXT_X + preview_col * CHAR_ADVANCE
                preview_y = OUTPUT_TEXT_Y + preview_view_row * OUTPUT_LINE_HEIGHT
                self.canvas.fill_rect(preview_x, preview_y, CHAR_ADVANCE - 1, CHAR_HEIGHT, 1)
                self.canvas.draw_text(self.stream_preview_char[:1], preview_x, preview_y, 0)

        total_rows = len(self.response_lines)
        if self.stream_preview_char and preview_row is not None:
            total_rows = max(total_rows, preview_row + 1)

        if total_rows > visible:
            self._draw_vertical_scrollbar(
                OUTPUT_X + OUTPUT_W - OUTPUT_SCROLLBAR_W,
                OUTPUT_Y + 2,
                4,
                OUTPUT_H - 4,
                total_rows,
                visible,
                draw_scroll,
            )

    def _draw_input_cursor(self, visible_start, visible_text):
        if self.focus != "input" or not self._cursor_visible:
            return

        cursor_index = max(0, self.input_cursor - visible_start)
        cursor_index = min(cursor_index, len(visible_text))
        cursor_x = INPUT_TEXT_X + cursor_index * CHAR_ADVANCE
        cursor_x = min(cursor_x, INPUT_X + INPUT_W - 4)
        cursor_y = self._input_text_y(self._should_show_input_scrollbar())
        self.canvas.vline(cursor_x, cursor_y - 1, CHAR_HEIGHT + 2, 1)

    def _should_show_input_scrollbar(self):
        input_value = self._input_value()
        return len(input_value) > self._input_visible_chars()

    def _input_text_y(self, show_scrollbar):
        text_top = INPUT_Y + 1
        text_bottom = INPUT_Y + INPUT_H - 2
        if show_scrollbar:
            text_bottom -= 4
        text_area_h = max(CHAR_HEIGHT, text_bottom - text_top + 1)
        return text_top + max(0, (text_area_h - CHAR_HEIGHT) // 2)

    def _draw_input_pane(self):
        self.canvas.rect(INPUT_X, INPUT_Y, INPUT_W, INPUT_H, 1)
        self._sync_input_view()
        input_value = self._input_value()
        visible_start = self.input_display_position
        visible_cols = self._input_visible_chars()
        visible_text = input_value[visible_start : visible_start + visible_cols]
        show_scrollbar = self._should_show_input_scrollbar()
        input_text_y = self._input_text_y(show_scrollbar)
        self.canvas.draw_text(visible_text, INPUT_TEXT_X, input_text_y, 1)
        self._draw_input_cursor(visible_start, visible_text)
        if show_scrollbar:
            self._draw_horizontal_scrollbar(
                INPUT_SCROLLBAR_X,
                INPUT_SCROLLBAR_Y,
                INPUT_SCROLLBAR_W,
                len(input_value),
                visible_cols,
                visible_start,
            )

    def render(self):
        set_active_view("form")
        self.canvas.clear(0)
        self._draw_output_pane()
        self._draw_input_pane()
        self.canvas.flush()
        self._draw_nav_overlay()

    def _draw_nav_overlay(self):
        state = str(nav.current_state() or "")
        nav_overlay_visible = state != "" and nav.is_visible()
        nav.set_restore_callback(self.render if nav_overlay_visible else None)
        if nav_overlay_visible:
            nav.draw_state(state)


def _build_dummy_reply(_prompt):
    return DUMMY_REPLY


def _stream_dummy_reply(screen, prompt_text):
    reply = _build_dummy_reply(prompt_text)
    screen.clear_response()
    screen.focus_output()
    screen.render()

    for char in reply:
        if char not in " \n":
            fake_char = NOISE_CHARS[_rand_idx(len(NOISE_CHARS))]
            screen.set_stream_preview(fake_char)
            screen.render()
            _sleep_ms(_rand_ms(4, 10))
            screen.clear_stream_preview()

        screen.append_response_char(char)
        screen.render()
        if char in " ,.;:!?":
            _sleep_ms(_rand_ms(36, 72))
        else:
            _sleep_ms(_rand_ms(8, 18))

    screen.focus_output()
    screen.render()


def _handle_mode_key(token, screen):
    if token in ("alpha", "beta"):
        keypad_state_manager(x=token)
        screen._reset_cursor_blink()
        screen.render()
        return True
    if token == "caps":
        keypad_state_manager(x="A")
        screen._reset_cursor_blink()
        screen.render()
        return True
    if token == "":
        screen._reset_cursor_blink()
        screen.render()
        return True
    return False


def ChatGPT():
    keypad_state_manager_reset()
    set_active_view("form")
    nav.set_restore_callback(None)
    display.clear_display()
    _show_startup_logo()

    screen = _ChatScreen()
    screen.render()

    while True:
        token = _read_key_with_local_back(idle_callback=screen.idle)
        if _handle_mode_key(token, screen):
            continue

        if token == "home":
            nav.set_restore_callback(None)
            request_navigation_from_key("home")
        if token == "settings":
            nav.set_restore_callback(None)
            request_navigation_from_key("settings")
        if token == "off":
            nav.set_restore_callback(None)
            break

        if token == "back":
            if screen.focus == "output":
                screen.focus_input()
                screen.render()
                continue
            nav.set_restore_callback(None)
            request_navigation_from_key("back")

        if token in ("ok", "exe"):
            if screen.focus == "input":
                prompt_text = screen._input_value().strip()
                if prompt_text:
                    _stream_dummy_reply(screen, prompt_text)
            else:
                screen.focus_input()
            screen.render()
            continue

        if token == "nav_u":
            if screen.focus == "input":
                screen.focus_output()
            else:
                screen.scroll_output(-1)
            screen.render()
            continue

        if token == "nav_d":
            if screen.focus == "output":
                if screen.is_output_at_bottom():
                    screen.focus_input()
                else:
                    screen.scroll_output(1)
            screen.render()
            continue

        if screen.focus == "output":
            screen.focus_input()
        screen.handle_input_key(token)
        screen.render()


def chatbot_ai():
    ChatGPT()
