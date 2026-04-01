import st7565 as display
# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import machine
import time
import esp32
from tinydb import TinyDB, Query
from soft_watch_dog_timer import SoftWatchdog
from data_modules.hardware_config import (
    DEEPSLEEP_HOLD_PIN,
    DEEPSLEEP_WAKE_PIN,
    DISPLAY_ENABLED,
    KEYPAD_ROWS,
)
db = TinyDB('db/settings.json')

def get_sleep_time():
    global db
    # db = TinyDB('db/settings.json')
    f=Query()
    res=db.search(f.feature=="sleep_timer")
    return res[0]["value"]

def test_deep_sleep_awake():
    if DEEPSLEEP_HOLD_PIN is not None:
        machine.Pin(DEEPSLEEP_HOLD_PIN, machine.Pin.OUT, value=1, hold=True)
    if DEEPSLEEP_WAKE_PIN is not None:
        wakeup_pin = machine.Pin(DEEPSLEEP_WAKE_PIN, mode=machine.Pin.IN, pull=machine.Pin.PULL_DOWN)
        esp32.wake_on_ext0(pin=wakeup_pin, level=esp32.WAKEUP_ANY_HIGH)
        esp32.gpio_deep_sleep_hold(True)
    time.sleep(0.2)
    if DISPLAY_ENABLED:
        try:
            display.clear_display()
        except Exception:
            pass
        try:
            display.off()
        except Exception:
            pass
    machine.deepsleep()

swdt=SoftWatchdog(timeout_ms=get_sleep_time(), callback=test_deep_sleep_awake, timer_id=1)

def update_sleep_time(time):
    global swdt, db
    # db = TinyDB('db/settings.json')
    f=Query()
    db.update({'value': time}, f.feature == "sleep_timer")
    swdt.update_time(timeout_ms=time)

def keypad_normal():
    for pin in KEYPAD_ROWS:
        try:
            machine.Pin(pin, machine.Pin.OUT, value=1, hold=False)
        except Exception:
            pass
