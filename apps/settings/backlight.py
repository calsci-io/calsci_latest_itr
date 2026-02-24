import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from machine import Pin  # type: ignore

try:
    from machine import PWM  # type: ignore
except Exception:
    PWM = None

from tinydb import TinyDB, Query

db = TinyDB('db/settings.json')
q = Query()

BACKLIGHT_PIN = 5
BACKLIGHT_LEVEL_MIN = 1
BACKLIGHT_LEVEL_MAX = 5
BACKLIGHT_DEFAULT_LEVEL = 5
PWM_FREQ_HZ = 1000
PWM_DUTY_MAX = 1023

# Active-low backlight driver map (higher level => brighter => lower duty).
LEVEL_TO_DUTY = {
    1: 820,
    2: 620,
    3: 420,
    4: 220,
    5: 0,
}

backlight_pin = Pin(BACKLIGHT_PIN, Pin.OUT)  # 2.9

backlight_pwm = None
if PWM is not None:
    try:
        backlight_pwm = PWM(backlight_pin, freq=PWM_FREQ_HZ, duty=0)
    except TypeError:
        try:
            backlight_pwm = PWM(backlight_pin)
            if hasattr(backlight_pwm, "freq"):
                backlight_pwm.freq(PWM_FREQ_HZ)
            if hasattr(backlight_pwm, "duty"):
                backlight_pwm.duty(0)
        except Exception:
            backlight_pwm = None
    except Exception:
        backlight_pwm = None


def _db_get(feature, default):
    row = db.search(q.feature == feature)
    if row:
        return row[0].get("value", default)
    db.insert({"feature": feature, "value": default})
    return default


def _db_set(feature, value):
    if db.search(q.feature == feature):
        db.update({"value": value}, q.feature == feature)
    else:
        db.insert({"feature": feature, "value": value})


def _coerce_bool(value, default=True):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on"):
            return True
        if text in ("0", "false", "no", "off", ""):
            return False
    return default


def _clamp_level(level):
    try:
        level = int(level)
    except Exception:
        level = BACKLIGHT_DEFAULT_LEVEL

    if level < BACKLIGHT_LEVEL_MIN:
        return BACKLIGHT_LEVEL_MIN
    if level > BACKLIGHT_LEVEL_MAX:
        return BACKLIGHT_LEVEL_MAX
    return level


def get_backlight_enabled():
    return _coerce_bool(_db_get("backlight", True), default=True)


def get_backlight_level():
    return _clamp_level(_db_get("backlight_level", BACKLIGHT_DEFAULT_LEVEL))


def _set_pwm_duty_10bit(duty_10bit):
    if backlight_pwm is None:
        return False

    if duty_10bit < 0:
        duty_10bit = 0
    elif duty_10bit > PWM_DUTY_MAX:
        duty_10bit = PWM_DUTY_MAX

    try:
        if hasattr(backlight_pwm, "duty"):
            backlight_pwm.duty(int(duty_10bit))
            return True
        if hasattr(backlight_pwm, "duty_u16"):
            duty_u16 = int((int(duty_10bit) * 65535) / PWM_DUTY_MAX)
            backlight_pwm.duty_u16(duty_u16)
            return True
    except Exception:
        return False
    return False


def _apply_backlight_hw(enabled, level):
    level = _clamp_level(level)

    if not enabled:
        if not _set_pwm_duty_10bit(PWM_DUTY_MAX):
            backlight_pin.on()
        return

    duty = LEVEL_TO_DUTY.get(level, LEVEL_TO_DUTY[BACKLIGHT_DEFAULT_LEVEL])
    if not _set_pwm_duty_10bit(duty):
        backlight_pin.off()


def set_backlight_state(enabled=True, level=None, persist=True):
    if level is None:
        level = get_backlight_level()
    level = _clamp_level(level)
    enabled = _coerce_bool(enabled, default=True)

    _apply_backlight_hw(enabled, level)

    if persist:
        _db_set("backlight", enabled)
        _db_set("backlight_level", level)

    return enabled, level


def apply_saved_backlight():
    enabled = get_backlight_enabled()
    level = get_backlight_level()
    _apply_backlight_hw(enabled, level)
    return enabled, level


# 5-level brightness app (preview while editing, save on OK, revert on BACK).
def backlight():
    from data_modules.object_handler import menu, menu_refresh, nav, typer, keypad_state_manager

    original_enabled = get_backlight_enabled()
    original_level = get_backlight_level()

    current_enabled = original_enabled
    current_level = original_level

    def _bar(level_value, enabled_value):
        if not enabled_value:
            return "[-----]"
        return "[" + ("#" * level_value) + ("-" * (BACKLIGHT_LEVEL_MAX - level_value)) + "]"

    def _refresh_ui():
        state = "ON" if current_enabled else "OFF"
        menu.menu_list = [
            "backlight: " + state,
            "level " + str(current_level) + "/5 " + _bar(current_level, current_enabled),
            "L/R=level AC=power",
            "OK=save BACK=cancel",
        ]
        menu.update()
        menu_refresh.refresh(state=nav.current_state())

    _refresh_ui()
    set_backlight_state(current_enabled, current_level, persist=False)

    while True:
        inp = typer.start_typing()

        if inp == "back":
            set_backlight_state(original_enabled, original_level, persist=False)
            break

        if inp in ("ok", "exe"):
            set_backlight_state(current_enabled, current_level, persist=True)
            break

        if inp in ("nav_l", "nav_d", "-"):
            if current_level > BACKLIGHT_LEVEL_MIN:
                current_level -= 1
            current_enabled = True
            set_backlight_state(current_enabled, current_level, persist=False)
            _refresh_ui()
            continue

        if inp in ("nav_r", "nav_u", "+"):
            if current_level < BACKLIGHT_LEVEL_MAX:
                current_level += 1
            current_enabled = True
            set_backlight_state(current_enabled, current_level, persist=False)
            _refresh_ui()
            continue

        if inp in ("AC", "backlight", "on"):
            current_enabled = not current_enabled
            set_backlight_state(current_enabled, current_level, persist=False)
            _refresh_ui()
            continue

        if inp in ("alpha", "beta"):
            keypad_state_manager(x=inp)
            menu.update_buffer("")
            _refresh_ui()
            continue

        menu.update_buffer(inp)
        menu_refresh.refresh(state=nav.current_state())
