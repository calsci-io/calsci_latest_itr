#
# Central hardware pin configuration for CalSci.
#
# Leave a value as None or an empty tuple/list to disable that hardware path.
# This lets the same firmware boot on boards with different pinouts, or with
# no local display/keypad at all.
#

DISPLAY_CS1_PIN = 9
DISPLAY_RST_PIN = 11
DISPLAY_RS_PIN = 10
DISPLAY_SCK_PIN = 13
DISPLAY_SDA_PIN = 12

KEYPAD_ROWS = (14, 21, 47, 48, 38, 39, 40, 41, 42, 1)
KEYPAD_COLS = (8, 18, 17, 15, 7)

BACKLIGHT_GPIO = 5

# Deep-sleep defaults follow the keypad matrix when not explicitly assigned.
DEEPSLEEP_HOLD_PIN = None
DEEPSLEEP_WAKE_PIN = None

# Set this True if you want to run the UI app thread through hybrid/remote
# control even when no local display/keypad pins are assigned.
REMOTE_UI_ENABLED = False


def _norm_pin(pin):
    try:
        if pin is None:
            return None
        return int(pin)
    except Exception:
        return None


def _norm_pin_list(pins):
    if pins is None:
        return ()
    out = []
    try:
        items = tuple(pins)
    except Exception:
        items = ()
    for pin in items:
        pin = _norm_pin(pin)
        if pin is not None:
            out.append(pin)
    return tuple(out)


DISPLAY_CS1_PIN = _norm_pin(DISPLAY_CS1_PIN)
DISPLAY_RST_PIN = _norm_pin(DISPLAY_RST_PIN)
DISPLAY_RS_PIN = _norm_pin(DISPLAY_RS_PIN)
DISPLAY_SCK_PIN = _norm_pin(DISPLAY_SCK_PIN)
DISPLAY_SDA_PIN = _norm_pin(DISPLAY_SDA_PIN)

KEYPAD_ROWS = _norm_pin_list(KEYPAD_ROWS)
KEYPAD_COLS = _norm_pin_list(KEYPAD_COLS)
BACKLIGHT_GPIO = _norm_pin(BACKLIGHT_GPIO)

if DEEPSLEEP_HOLD_PIN is None and KEYPAD_ROWS:
    DEEPSLEEP_HOLD_PIN = KEYPAD_ROWS[0]
else:
    DEEPSLEEP_HOLD_PIN = _norm_pin(DEEPSLEEP_HOLD_PIN)

if DEEPSLEEP_WAKE_PIN is None and KEYPAD_COLS:
    DEEPSLEEP_WAKE_PIN = KEYPAD_COLS[0]
else:
    DEEPSLEEP_WAKE_PIN = _norm_pin(DEEPSLEEP_WAKE_PIN)

DISPLAY_ENABLED = None not in (
    DISPLAY_CS1_PIN,
    DISPLAY_RST_PIN,
    DISPLAY_RS_PIN,
    DISPLAY_SCK_PIN,
    DISPLAY_SDA_PIN,
)
KEYPAD_ENABLED = bool(KEYPAD_ROWS and KEYPAD_COLS)
LOCAL_UI_ENABLED = DISPLAY_ENABLED and KEYPAD_ENABLED
APP_THREAD_ENABLED = bool(LOCAL_UI_ENABLED or REMOTE_UI_ENABLED)
BACKLIGHT_ENABLED = BACKLIGHT_GPIO is not None
DEEPSLEEP_ENABLED = DEEPSLEEP_HOLD_PIN is not None and DEEPSLEEP_WAKE_PIN is not None

DISPLAY_PINS = (
    DISPLAY_CS1_PIN,
    DISPLAY_RST_PIN,
    DISPLAY_RS_PIN,
    DISPLAY_SCK_PIN,
    DISPLAY_SDA_PIN,
) if DISPLAY_ENABLED else ()

st7565_display_pins = {
    "cs1": DISPLAY_CS1_PIN,
    "rst": DISPLAY_RST_PIN,
    "rs": DISPLAY_RS_PIN,
    "sck": DISPLAY_SCK_PIN,
    "sda": DISPLAY_SDA_PIN,
}


def display_pins():
    return DISPLAY_PINS


def display_is_enabled():
    return DISPLAY_ENABLED


def keypad_rows():
    return KEYPAD_ROWS


def keypad_cols():
    return KEYPAD_COLS


def keypad_is_enabled():
    return KEYPAD_ENABLED


def local_ui_is_enabled():
    return LOCAL_UI_ENABLED


def remote_ui_is_enabled():
    return bool(REMOTE_UI_ENABLED)


def app_thread_is_enabled():
    return APP_THREAD_ENABLED


def backlight_is_enabled():
    return BACKLIGHT_ENABLED


def deepsleep_hold_pin():
    return DEEPSLEEP_HOLD_PIN


def deepsleep_wake_pin():
    return DEEPSLEEP_WAKE_PIN
