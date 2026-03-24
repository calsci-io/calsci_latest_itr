from machine import Pin  # type: ignore

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.


def _settings_db():
    from tinydb import Query, TinyDB

    return TinyDB("db/settings.json"), Query()


# Assuming the backlight is connected to a specific pin (e.g., Pin 15)
# backlight_pin = Pin(19, Pin.OUT) #3.0
backlight_pin = Pin(5, Pin.OUT)  # 2.9
backlight_label = ""
if backlight_pin.value() == 1:
    backlight_label = "backlight off"
else:
    backlight_label = "backlight on"


def backlight():
    db, q = _settings_db()
    current_state = backlight_pin.value()
    if current_state == 1:
        backlight_pin.off()
        db.update({"value": True}, q.feature == "backlight")
    else:
        backlight_pin.on()
        db.update({"value": False}, q.feature == "backlight")
