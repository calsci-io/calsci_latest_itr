import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

try:
    import utime as time  # type: ignore
except ImportError:
    import time  # type: ignore

try:
    import machine  # type: ignore
except ImportError:
    from mocking import machine  # type: ignore

from apps.installed_apps._mono_ui import MonoCanvas, clip_text_px, text_width
from data_modules.object_handler import keyin, keymap, keypad_state_manager_reset
from process_modules import boot_up_data_update
from process_modules.navigation import request_navigation_from_key


_WIDTH = 128
_CHAR_ADVANCE = 6
_FIELD_X = 4
_FIELD_W = 120
_FIELD_H = 15
_FIELD_LABEL_W = 28
_FIELD_INPUT_X = _FIELD_X + _FIELD_LABEL_W + 2
_FIELD_INPUT_W = _FIELD_W - _FIELD_LABEL_W - 5
_FIELD_Y = (11, 28)
_RESULT_X = 4
_RESULT_Y = 45
_RESULT_W = 120
_RESULT_H = 18
_MAX_INPUT_CHARS = 18


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def _read_key():
    _sleep_ms(120)
    col, row = keyin.keypad_loop()
    return keymap.key_out(col=int(col), row=int(row))


def _parse_number(text_value):
    text_value = str(text_value or "").strip()
    if text_value in ("", "+", "-", ".", "+.", "-.", "e", "+e", "-e"):
        return None
    try:
        return float(text_value)
    except Exception:
        return None


def _format_number(value):
    try:
        value = float(value)
    except Exception:
        return "error"

    text_value = "{:.10g}".format(value)
    if len(text_value) > 14:
        text_value = "{:.6e}".format(value)
    if text_value == "-0":
        text_value = "0"
    return text_value


def _visible_slice(text_value, cursor, max_chars):
    text_value = str(text_value or "")
    max_chars = max(1, int(max_chars))
    cursor = max(0, min(int(cursor), len(text_value)))
    if len(text_value) <= max_chars:
        return text_value, cursor

    start = max(0, cursor - max_chars + 1)
    max_start = len(text_value) - max_chars
    if start > max_start:
        start = max_start
    return text_value[start : start + max_chars], cursor - start


def _result_preview(values):
    left_value = _parse_number(values[0])
    right_value = _parse_number(values[1])
    if left_value is None or right_value is None:
        return None
    return (
        "{} + {}".format(_format_number(left_value), _format_number(right_value)),
        "= {}".format(_format_number(left_value + right_value)),
    )


class _AddTwoNumsApp:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.values = ["", ""]
        self.cursors = [0, 0]
        self.active_index = 0
        self.last_answer = ""
        self.notice_lines = ("NAV U/D SELECT", "OK SAVES ANS")

    def build(self):
        self.render()

    def _active_value(self):
        return self.values[self.active_index]

    def _set_active_value(self, value, cursor=None):
        value = str(value)
        self.values[self.active_index] = value[:_MAX_INPUT_CHARS]
        if cursor is None:
            cursor = len(self.values[self.active_index])
        self.cursors[self.active_index] = max(
            0, min(int(cursor), len(self.values[self.active_index]))
        )

    def _clear_notice(self):
        self.notice_lines = None

    def switch_field(self, step):
        self.active_index = (self.active_index + int(step)) % 2
        self._clear_notice()
        self.render()

    def move_cursor(self, step):
        current = self._active_value()
        cursor = self.cursors[self.active_index] + int(step)
        self.cursors[self.active_index] = max(0, min(cursor, len(current)))
        self._clear_notice()
        self.render()

    def backspace(self):
        current = self._active_value()
        cursor = self.cursors[self.active_index]
        if cursor <= 0:
            self.notice_lines = ("CURSOR AT START", "USE NAV R TO MOVE")
            self.render()
            return

        new_value = current[: cursor - 1] + current[cursor:]
        self._set_active_value(new_value, cursor - 1)
        self._clear_notice()
        self.render()

    def clear_field(self):
        current = self._active_value()
        if current:
            self._set_active_value("", 0)
            self.notice_lines = ("FIELD CLEARED", "ENTER A NUMBER")
        else:
            self.values = ["", ""]
            self.cursors = [0, 0]
            self.notice_lines = ("ALL CLEARED", "READY FOR NEW SUM")
        self.render()

    def paste_last_answer(self):
        if not self.last_answer:
            self.notice_lines = ("NO SAVED ANS", "PRESS OK AFTER SUM")
            self.render()
            return
        self._set_active_value(self.last_answer, len(self.last_answer))
        self.notice_lines = ("ANS PASTED", "EDIT OR PRESS OK")
        self.render()

    def calculate(self):
        preview = _result_preview(self.values)
        if preview is None:
            self.notice_lines = ("NEED VALID NUMS", "USE DIGITS . E -")
            self.render()
            return

        self.last_answer = preview[1][2:]
        self.notice_lines = ("SAVED TO ANS", preview[1])
        self.render()

    def insert_token(self, token):
        token = str(token)
        current = self._active_value()
        cursor = self.cursors[self.active_index]

        if token == "+" and self.active_index == 0 and current:
            self.switch_field(1)
            return

        if len(current) + len(token) > _MAX_INPUT_CHARS:
            self.notice_lines = ("FIELD IS FULL", "USE NAV_B TO EDIT")
            self.render()
            return

        if token in "+-":
            if cursor == 0:
                if current[:1] in ("+", "-"):
                    self.notice_lines = ("SIGN EXISTS", "DELETE TO CHANGE")
                    self.render()
                    return
            elif current[cursor - 1 : cursor] in "eE":
                if current[cursor : cursor + 1] in ("+", "-"):
                    self.notice_lines = ("EXP SIGN EXISTS", "TYPE DIGITS NEXT")
                    self.render()
                    return
            else:
                self.notice_lines = ("SIGN ONLY FIRST", "OR AFTER E")
                self.render()
                return

        elif token == ".":
            exponent_at = current.lower().find("e")
            if exponent_at != -1 and cursor > exponent_at:
                self.notice_lines = ("DOT BEFORE E", "EXP NEEDS INTEGER")
                self.render()
                return
            base_text = current if exponent_at == -1 else current[:exponent_at]
            if "." in base_text:
                self.notice_lines = ("DOT ALREADY USED", "ENTER DIGITS")
                self.render()
                return

        elif token == "e":
            if not current or "e" in current.lower():
                self.notice_lines = ("E NOT ALLOWED", "USE ONE EXPONENT")
                self.render()
                return
            if not any(char.isdigit() for char in current[:cursor]):
                self.notice_lines = ("ADD DIGITS FIRST", "THEN INSERT E")
                self.render()
                return

        new_value = current[:cursor] + token + current[cursor:]
        self._set_active_value(new_value, cursor + len(token))
        self._clear_notice()
        self.render()

    def _field_value_for_draw(self, field_index):
        raw_value = self.values[field_index]
        max_chars = max(1, (_FIELD_INPUT_W - 4) // _CHAR_ADVANCE)
        return _visible_slice(raw_value, self.cursors[field_index], max_chars)

    def _draw_cursor(self, x, y, field_index, visible_cursor):
        if field_index != self.active_index:
            return
        cursor_x = x + 2 + visible_cursor * _CHAR_ADVANCE
        max_cursor_x = _FIELD_INPUT_X + _FIELD_INPUT_W - 4
        if cursor_x > max_cursor_x:
            cursor_x = max_cursor_x
        self.canvas.vline(cursor_x, y + 3, _FIELD_H - 6, 1)

    def _render_field(self, field_index, title, y):
        is_active = field_index == self.active_index
        visible_text, visible_cursor = self._field_value_for_draw(field_index)

        self.canvas.rect(_FIELD_X, y, _FIELD_W, _FIELD_H, 1)
        if is_active:
            self.canvas.rect(_FIELD_X + 1, y + 1, _FIELD_W - 2, _FIELD_H - 2, 1)
            self.canvas.fill_rect(_FIELD_X + 1, y + 1, _FIELD_LABEL_W - 1, _FIELD_H - 2, 1)
            self.canvas.draw_text_in_rect(
                title,
                _FIELD_X + 1,
                y + 1,
                _FIELD_LABEL_W - 1,
                _FIELD_H - 2,
                color=0,
                align="center",
            )
        else:
            self.canvas.draw_text_in_rect(
                title,
                _FIELD_X + 1,
                y + 1,
                _FIELD_LABEL_W - 1,
                _FIELD_H - 2,
                color=1,
                align="center",
            )

        self.canvas.vline(_FIELD_X + _FIELD_LABEL_W, y + 1, _FIELD_H - 2, 1)
        if is_active:
            self.canvas.hline(_FIELD_INPUT_X, y + _FIELD_H - 3, _FIELD_INPUT_W - 2, 1)

        if visible_text:
            self.canvas.draw_text(
                visible_text,
                _FIELD_INPUT_X + 2,
                y + 3,
                color=1,
                max_width=_FIELD_INPUT_W - 4,
            )
        self._draw_cursor(_FIELD_INPUT_X, y, field_index, visible_cursor)

    def _draw_result_panel(self):
        self.canvas.rect(_RESULT_X, _RESULT_Y, _RESULT_W, _RESULT_H, 1)
        self.canvas.fill_rect(_RESULT_X + 1, _RESULT_Y + 1, 24, _RESULT_H - 2, 1)
        self.canvas.draw_text_in_rect(
            "SUM",
            _RESULT_X + 1,
            _RESULT_Y + 1,
            24,
            _RESULT_H - 2,
            color=0,
            align="center",
        )

        lines = _result_preview(self.values)
        if lines is None:
            if self.notice_lines is not None:
                lines = self.notice_lines
            elif self.values[0] or self.values[1]:
                lines = ("NEED VALID NUMS", "OK SAVES LAST SUM")
            else:
                lines = ("ENTER TWO NUMS", "OK SAVES LAST SUM")

        line_width = _RESULT_W - 30
        self.canvas.draw_text(
            clip_text_px(lines[0], line_width),
            _RESULT_X + 28,
            _RESULT_Y + 2,
            color=1,
        )
        self.canvas.draw_text(
            clip_text_px(lines[1], line_width),
            _RESULT_X + 28,
            _RESULT_Y + 10,
            color=1,
        )

    def render(self):
        self.canvas.clear()
        self.canvas.fill_rect(0, 0, _WIDTH, 9, 1)
        self.canvas.draw_text_center("Add Two Numbers", 1, color=0)
        self.canvas.pixel(62, 25, 1)
        self.canvas.hline(59, 28, 7, 1)
        self.canvas.vline(62, 25, 7, 1)

        self._render_field(0, "ONE", _FIELD_Y[0])
        self._render_field(1, "TWO", _FIELD_Y[1])
        self._draw_result_panel()
        self.canvas.flush()


def add_2_nums(db={}):
    _ = db
    keypad_state_manager_reset()

    display.clear_display()
    app = _AddTwoNumsApp()
    app.build()

    while True:
        key_name = _read_key()

        if key_name in ("back", "home", "settings"):
            request_navigation_from_key(key_name)

        if key_name in ("on", "off"):
            boot_up_data_update.main()
            machine.deepsleep()

        if key_name == "nav_u":
            app.switch_field(-1)
            continue

        if key_name == "nav_d":
            app.switch_field(1)
            continue

        if key_name == "nav_l":
            app.move_cursor(-1)
            continue

        if key_name == "nav_r":
            app.move_cursor(1)
            continue

        if key_name == "nav_b":
            app.backspace()
            continue

        if key_name == "AC":
            app.clear_field()
            continue

        if key_name in ("ok", "exe"):
            app.calculate()
            continue

        if key_name == "ans":
            app.paste_last_answer()
            continue

        if key_name == "*pow(10, )":
            app.insert_token("e")
            continue

        if key_name in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "-", "+"):
            app.insert_token(key_name)
