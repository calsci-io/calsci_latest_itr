import st7565 as display

# try:
#     import tools
#     if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
#         display.graphics = tools.refresh(display.graphics, pixels_changed=200)
# except Exception:
#     pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from machine import Pin, PWM  # type: ignore
from tinydb import TinyDB, Query

from data_modules.object_handler import (
    app,
    display,
    keypad_state_manager,
    keypad_state_manager_reset,
    menu,
    menu_refresh,
    nav,
    typer,
)

db = TinyDB("db/settings.json")
q = Query()

BACKLIGHT_GPIO = 5
BACKLIGHT_LEVEL_MIN = 0
BACKLIGHT_LEVEL_MAX = 10
BACKLIGHT_PWM_MAX = 1023
BACKLIGHT_PWM_FREQ = 1000

backlight_pin = Pin(BACKLIGHT_GPIO, Pin.OUT)
backlight_pwm = PWM(backlight_pin)

try:
    backlight_pwm.freq(BACKLIGHT_PWM_FREQ)
except Exception:
    pass


def _normalize_level(level):
    try:
        level = int(level)
    except Exception:
        level = BACKLIGHT_LEVEL_MAX
    if level < BACKLIGHT_LEVEL_MIN:
        return BACKLIGHT_LEVEL_MIN
    if level > BACKLIGHT_LEVEL_MAX:
        return BACKLIGHT_LEVEL_MAX
    return level


def _setting_value(feature, default):
    result = db.search(q.feature == feature)
    if len(result) == 0:
        db.insert({"feature": feature, "value": default})
        return default
    return result[0]["value"]


def _update_setting(feature, value):
    if len(db.search(q.feature == feature)) == 0:
        db.insert({"feature": feature, "value": value})
    else:
        db.update({"value": value}, q.feature == feature)


def _load_saved_level():
    backlight_enabled = bool(_setting_value("backlight", True))
    saved_level = db.search(q.feature == "backlight_level")
    if len(saved_level) == 0:
        level = BACKLIGHT_LEVEL_MAX if backlight_enabled else BACKLIGHT_LEVEL_MIN
        _update_setting("backlight_level", level)
        return level
    return _normalize_level(saved_level[0]["value"])


def _level_to_duty(level):
    level = _normalize_level(level)
    return int((BACKLIGHT_PWM_MAX * (BACKLIGHT_LEVEL_MAX - level)) / BACKLIGHT_LEVEL_MAX)


def set_backlight_level(level, persist=True):
    level = _normalize_level(level)
    duty = _level_to_duty(level)
    try:
        backlight_pwm.duty(duty)
    except Exception:
        if level <= 0:
            backlight_pin.on()
        else:
            backlight_pin.off()
    if persist:
        _update_setting("backlight_level", level)
        _update_setting("backlight", level > 0)
    return level


def get_backlight_level():
    return _load_saved_level()


def apply_saved_backlight():
    return set_backlight_level(_load_saved_level(), persist=False)


def _level_label(level):
    if level <= 0:
        return "OFF"
    return str(level) + "/10"


def _bar(level):
    filled = _normalize_level(level)
    return "[" + ("#" * filled) + ("-" * (BACKLIGHT_LEVEL_MAX - filled)) + "]"


def _refresh_screen(level):
    menu.menu_list = [
        "Backlight",
        "Level: " + _level_label(level),
        _bar(level),
        "",
        "L/R: adjust",
        "OK: save",
        "Back: cancel",
    ]
    menu.update()
    menu.menu_cursor = 1
    menu.display_cursor = 1
    menu.refresh_rows = (0, menu.menu_display_size)
    display.clear_display()
    menu_refresh.refresh(state=nav.current_state())


def backlight(db_data={}):
    keypad_state_manager_reset()
    saved_level = get_backlight_level()
    preview_level = saved_level
    set_backlight_level(preview_level, persist=False)
    _refresh_screen(preview_level)

    while True:
        inp = typer.start_typing()

        if inp == "back":
            set_backlight_level(saved_level, persist=False)
            app.set_app_name("settings")
            app.set_group_name("root")
            break

        if inp == "ok":
            saved_level = set_backlight_level(preview_level, persist=True)
            app.set_app_name("settings")
            app.set_group_name("root")
            break

        if inp == "nav_l":
            preview_level = set_backlight_level(preview_level - 1, persist=False)
            _refresh_screen(preview_level)
            continue

        if inp == "nav_r":
            preview_level = set_backlight_level(preview_level + 1, persist=False)
            _refresh_screen(preview_level)
            continue

        if inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            menu.update_buffer("")
            menu_refresh.refresh(state=nav.current_state())
            continue

        if inp in ("nav_u", "nav_d"):
            _refresh_screen(preview_level)

