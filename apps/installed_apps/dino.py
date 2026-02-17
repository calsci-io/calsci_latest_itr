import st7565 as display

# try:
#     import tools
#     if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
#         display.graphics = tools.refresh(display.graphics, pixels_changed=200)
# except Exception:
#     pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import utime
from machine import Pin  # type: ignore
from data_modules.object_handler import app

from dino_game.game import DinoGame


_ROWS = [14, 21, 47, 48, 38, 39, 40, 41, 42, 1]
_COLS = [8, 18, 17, 15, 7]

JUMP_KEY = (4, 2)
DUCK_KEY = (1, 2)
BACK_KEY = (1, 1)


def _init_keypad():
    for row in _ROWS:
        Pin(row, Pin.OUT).value(1)
    for col in _COLS:
        Pin(col, Pin.IN, Pin.PULL_UP)


def _scan_key():
    for row_index, row_pin in enumerate(_ROWS):
        row = Pin(row_pin, Pin.OUT)
        row.value(0)
        for col_index, col_pin in enumerate(_COLS):
            if Pin(col_pin, Pin.IN, Pin.PULL_UP).value() == 0:
                row.value(1)
                return col_index, row_index
        row.value(1)
    return None


def _read_input():
    key = _scan_key()
    return key == JUMP_KEY, key == DUCK_KEY, key == BACK_KEY


def _exit_to_installed_apps():
    display.clear_display()
    app.set_app_name("installed_apps")
    app.set_group_name("root")


def dino():
    _init_keypad()
    game = DinoGame(display=display, read_input=_read_input)

    while True:
        should_start = game.splash_screen()
        if not should_start:
            _exit_to_installed_apps()
            return

        result = game.play_round()
        if result is None:
            _exit_to_installed_apps()
            return

        utime.sleep_ms(200)
