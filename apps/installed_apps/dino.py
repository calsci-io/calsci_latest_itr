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
from data_modules.object_handler import keymap, keypad_state_manager_reset

from dino_game.game import DinoGame
from process_modules.navigation import request_navigation_from_key

try:
    import sim_ui  # type: ignore
except Exception:
    sim_ui = None


_ROWS = [14, 21, 47, 48, 38, 39, 40, 41, 42, 1]
_COLS = [8, 18, 17, 15, 7]

JUMP_KEY = "nav_u"
DUCK_KEY = "nav_d"
NAVIGATION_KEYS = ("home", "settings", "back")


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
    duck_pressed = False
    if key is None:
        if sim_ui is not None:
            try:
                duck_pressed = bool(sim_ui.is_key_active(DUCK_KEY))
            except Exception:
                duck_pressed = False
        return False, duck_pressed, False

    key_name = keymap.key_out(col=int(key[0]), row=int(key[1]))
    if key_name in NAVIGATION_KEYS:
        request_navigation_from_key(key_name)

    if key_name == DUCK_KEY:
        duck_pressed = True
    elif sim_ui is not None:
        try:
            duck_pressed = bool(sim_ui.is_key_active(DUCK_KEY))
        except Exception:
            duck_pressed = False

    return key_name == JUMP_KEY, duck_pressed, False


def dino():
    keypad_state_manager_reset()
    _init_keypad()
    game = DinoGame(display=display, read_input=_read_input)

    try:
        while True:
            result = game.play_round()
            if result is None:
                request_navigation_from_key("back")
            utime.sleep_ms(200)
    finally:
        try:
            game._set_inverse(False)
        except Exception:
            pass
