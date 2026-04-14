import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

try:
    import utime as time  # type: ignore
except ImportError:
    import time  # type: ignore

import machine

from apps.installed_apps._mono_ui import MonoCanvas
from apps.installed_apps.professor_panda_frame import professor_panda as _PANDA_FRAME
from data_modules.object_handler import app, keyin, keymap, keypad_state_manager_reset
from process_modules import boot_up_data_update
from process_modules.navigation import request_navigation_from_key


_WIDTH = 128
_HEIGHT = 64
_FRAME_INTERVAL_MS = 220
_BOB_SEQUENCE = (0, 1, 2, 1)
_NAVIGATION_KEYS = ("home", "settings", "back")
_BOOK_PAGE_LINES = (
    ((4, 3, 10), (4, 6, 8), (4, 9, 9)),
    ((4, 3, 8), (4, 6, 10), (4, 9, 7)),
)
_CALC_DIGITS = (
    "12+7",
    "19x2",
    "38-4",
    "34/2",
)
_ANIMATION_CYCLE_FRAMES = 18


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def _ticks_ms():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _ticks_diff(now_ms, past_ms):
    try:
        return time.ticks_diff(now_ms, past_ms)
    except Exception:
        return now_ms - past_ms


class _ProfessorPandaApp:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.frame_index = 0
        self.last_frame_ms = _ticks_ms()

    def _draw_shifted_sprite(self, y_offset):
        y_offset = int(y_offset)
        dest = self.canvas.buf
        source = _PANDA_FRAME
        page_count = _HEIGHT // 8

        if y_offset == 0:
            dest[:] = source
            return

        for idx in range(len(dest)):
            dest[idx] = 0

        if y_offset > 0:
            page_offset = y_offset // 8
            bit_offset = y_offset % 8

            for dest_page in range(page_count):
                src_page = dest_page - page_offset
                dest_row = dest_page * _WIDTH
                src_row = src_page * _WIDTH
                carry_row = (src_page - 1) * _WIDTH

                for x in range(_WIDTH):
                    pixel_byte = 0
                    if 0 <= src_page < page_count:
                        pixel_byte |= (source[src_row + x] << bit_offset) & 0xFF
                    if bit_offset and 0 <= src_page - 1 < page_count:
                        pixel_byte |= source[carry_row + x] >> (8 - bit_offset)
                    dest[dest_row + x] = pixel_byte
            return

        shift = -y_offset
        page_offset = shift // 8
        bit_offset = shift % 8

        for dest_page in range(page_count):
            src_page = dest_page + page_offset
            dest_row = dest_page * _WIDTH
            src_row = src_page * _WIDTH
            carry_row = (src_page + 1) * _WIDTH

            for x in range(_WIDTH):
                pixel_byte = 0
                if 0 <= src_page < page_count:
                    pixel_byte |= source[src_row + x] >> bit_offset
                if bit_offset and 0 <= src_page + 1 < page_count:
                    pixel_byte |= (source[carry_row + x] << (8 - bit_offset)) & 0xFF
                dest[dest_row + x] = pixel_byte

    def _draw_frame(self):
        self._draw_shifted_sprite(_BOB_SEQUENCE[self.frame_index % len(_BOB_SEQUENCE)])
        self._draw_scene_overlay()
        self.canvas.flush()

    def _phase_index(self):
        return self.frame_index % 18

    def _scene_name(self):
        phase = self._phase_index()
        if phase == 0:
            return "idle"
        if phase < 7:
            return "dance"
        if phase < 12:
            return "book"
        return "calc"

    def _scene_step(self):
        phase = self._phase_index()
        if phase < 7:
            return max(0, phase - 1)
        if phase < 12:
            return phase - 7
        return phase - 12

    def _note(self, x, y, flip=False):
        x = int(x)
        y = int(y)
        if flip:
            self.canvas.vline(x + 1, y - 2, 7, 1)
            self.canvas.vline(x + 6, y, 6, 1)
            self.canvas.hline(x + 1, y - 2, 6, 1)
            self.canvas.fill_rect(x - 1, y + 4, 3, 2, 1)
            self.canvas.fill_rect(x + 4, y + 2, 3, 2, 1)
            return
        self.canvas.vline(x + 1, y, 7, 1)
        self.canvas.vline(x + 6, y - 2, 6, 1)
        self.canvas.hline(x + 1, y - 2, 6, 1)
        self.canvas.fill_rect(x, y + 5, 3, 2, 1)
        self.canvas.fill_rect(x + 5, y + 3, 3, 2, 1)

    def _draw_dance_overlay(self, bob, step):
        left_note_x = 20 + ((step % 3) * 3)
        right_note_x = 98 - ((step % 3) * 3)
        left_note_y = 13 + bob + ((step + 1) % 2)
        right_note_y = 11 + bob + (step % 2)
        self._note(left_note_x, left_note_y, flip=False)
        self._note(right_note_x, right_note_y, flip=True)

        # Wrist flicks and foot taps to give the static sprite a dance feel.
        if step % 2 == 0:
            self.canvas.hline(21, 45 + bob, 7, 1)
            self.canvas.hline(71, 50 + bob, 7, 1)
            self.canvas.vline(63, 52 + bob, 5, 1)
        else:
            self.canvas.hline(20, 49 + bob, 7, 1)
            self.canvas.hline(72, 45 + bob, 7, 1)
            self.canvas.vline(55, 52 + bob, 5, 1)

        if step in (2, 5):
            self.canvas.hline(31, 29 + bob, 6, 1)
            self.canvas.hline(78, 30 + bob, 6, 1)

    def _draw_book_overlay(self, bob, step):
        y = 33 + bob
        spread = 16 + (step % 2)
        page_h = 14
        left_x = 24
        right_x = left_x + spread

        # Cover the old prop and redraw an open book between both paws.
        self.canvas.fill_rect(22, 31 + bob, 48, 21, 0)
        self.canvas.fill_rect(left_x, y, spread, page_h, 1)
        self.canvas.fill_rect(right_x, y, spread, page_h, 1)
        self.canvas.vline(right_x - 1, y + 1, page_h - 2, 0)
        self.canvas.vline(right_x, y + 1, page_h - 2, 0)
        self.canvas.rect(left_x, y, spread, page_h, 1)
        self.canvas.rect(right_x, y, spread, page_h, 1)

        line_set = _BOOK_PAGE_LINES[step % len(_BOOK_PAGE_LINES)]
        for start_x, line_y, line_w in line_set:
            self.canvas.hline(left_x + start_x, y + line_y, line_w, 0)
            self.canvas.hline(right_x + 2, y + line_y, line_w, 0)

        # Paws holding the book.
        self.canvas.fill_rect(left_x - 3, y + 4, 4, 8, 1)
        self.canvas.fill_rect(right_x + spread - 1, y + 4, 4, 8, 1)
        self.canvas.pixel(left_x - 4, y + 7, 1)
        self.canvas.pixel(right_x + spread + 3, y + 7, 1)

        # Reading marks above the pages.
        if step % 2 == 0:
            self.canvas.hline(43, 29 + bob, 5, 1)
            self.canvas.hline(52, 28 + bob, 5, 1)
        else:
            self.canvas.hline(44, 28 + bob, 5, 1)
            self.canvas.hline(53, 29 + bob, 5, 1)

    def _draw_calc_digits(self, x, y, text):
        x = int(x)
        y = int(y)
        text = str(text)
        if len(text) > 4:
            text = text[:4]
        glyphs = {
            "0": ((1, 1, 1), (1, 0, 1), (1, 0, 1), (1, 1, 1)),
            "1": ((0, 1, 0), (1, 1, 0), (0, 1, 0), (1, 1, 1)),
            "2": ((1, 1, 1), (0, 0, 1), (1, 1, 1), (1, 0, 0), (1, 1, 1)),
            "3": ((1, 1, 1), (0, 0, 1), (0, 1, 1), (0, 0, 1), (1, 1, 1)),
            "4": ((1, 0, 1), (1, 0, 1), (1, 1, 1), (0, 0, 1), (0, 0, 1)),
            "7": ((1, 1, 1), (0, 0, 1), (0, 1, 0), (0, 1, 0), (0, 1, 0)),
            "8": ((1, 1, 1), (1, 0, 1), (1, 1, 1), (1, 0, 1), (1, 1, 1)),
            "9": ((1, 1, 1), (1, 0, 1), (1, 1, 1), (0, 0, 1), (1, 1, 1)),
            "+": ((0, 1, 0), (1, 1, 1), (0, 1, 0)),
            "-": ((1, 1, 1),),
            "x": ((1, 0, 1), (0, 1, 0), (1, 0, 1)),
            "/": ((0, 0, 1), (0, 1, 0), (1, 0, 0)),
        }

        cursor_x = x
        for char in text:
            pattern = glyphs.get(char)
            if pattern is None:
                cursor_x += 4
                continue
            for row_idx, row in enumerate(pattern):
                for col_idx, value in enumerate(row):
                    self.canvas.pixel(cursor_x + col_idx, y + row_idx, 0 if value else 1)
            cursor_x += len(pattern[0]) + 1

    def _draw_calculator_overlay(self, bob, step):
        calc_x = 29
        calc_y = 33 + bob
        calc_w = 18
        calc_h = 22
        press_index = step % 4

        self.canvas.fill_rect(24, 30 + bob, 43, 27, 0)
        self.canvas.fill_rect(calc_x, calc_y, calc_w, calc_h, 1)
        self.canvas.rect(calc_x, calc_y, calc_w, calc_h, 1)
        self.canvas.fill_rect(calc_x + 2, calc_y + 2, calc_w - 4, 5, 1)
        self.canvas.rect(calc_x + 2, calc_y + 2, calc_w - 4, 5, 0)
        self._draw_calc_digits(calc_x + 4, calc_y + 3, _CALC_DIGITS[step % len(_CALC_DIGITS)])

        button_y = calc_y + 9
        for row in range(3):
            for col in range(3):
                bx = calc_x + 3 + (col * 4)
                by = button_y + (row * 4)
                pressed = (row * 3 + col) == press_index
                if pressed:
                    self.canvas.fill_rect(bx, by, 3, 2, 1)
                    self.canvas.rect(bx, by, 3, 2, 0)
                else:
                    self.canvas.fill_rect(bx, by, 3, 2, 0)

        # Panda's free paw pressing the active key.
        paw_y = calc_y + 9 + ((press_index // 2) * 2)
        self.canvas.fill_rect(calc_x + calc_w + 1, paw_y + 1, 7, 3, 1)
        self.canvas.pixel(calc_x + calc_w + 8, paw_y + 2, 1)
        self.canvas.pixel(calc_x + calc_w + 9, paw_y + 2, 1)

        # Small maths sparkle above the calculator.
        self.canvas.hline(51, 29 + bob, 5, 1)
        if step % 2 == 0:
            self.canvas.vline(53, 27 + bob, 5, 1)
        else:
            self.canvas.pixel(58, 28 + bob, 1)
            self.canvas.pixel(60, 30 + bob, 1)

    def _draw_scene_overlay(self):
        bob = _BOB_SEQUENCE[self.frame_index % len(_BOB_SEQUENCE)]
        scene = self._scene_name()
        step = self._scene_step()
        if scene == "dance":
            self._draw_dance_overlay(bob, step)
        elif scene == "book":
            self._draw_book_overlay(bob, step)
        elif scene == "calc":
            self._draw_calculator_overlay(bob, step)

    def refresh(self, force=False):
        now_ms = _ticks_ms()
        if force or _ticks_diff(now_ms, self.last_frame_ms) >= _FRAME_INTERVAL_MS:
            if not force:
                self.frame_index = (self.frame_index + 1) % _ANIMATION_CYCLE_FRAMES
            self.last_frame_ms = now_ms
            self._draw_frame()

    def _idle_tasks(self):
        self.refresh(force=False)

    def _read_key(self):
        _sleep_ms(110)
        col, row = keyin.keypad_loop(idle_callback=self._idle_tasks)
        return keymap.key_out(col=int(col), row=int(row))

    def run(self):
        keypad_state_manager_reset()
        self.refresh(force=True)

        while True:
            inp = self._read_key()

            if inp in ("alpha", "beta", "caps", "toolbox", ""):
                continue

            if inp == "off":
                boot_up_data_update.main()
                machine.deepsleep()
                return

            if inp in _NAVIGATION_KEYS:
                request_navigation_from_key(inp)
                if inp == "back":
                    app.set_app_name("installed_apps")
                    app.set_group_name("root")
                return

            if inp in ("ok", "exe"):
                app.set_app_name("installed_apps")
                app.set_group_name("root")
                return


def professor_panda(db={}):
    del db
    viewer = _ProfessorPandaApp()
    viewer.run()
