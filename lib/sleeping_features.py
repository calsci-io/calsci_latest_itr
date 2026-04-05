import st7565 as display
# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import machine
import time
import esp32
from tinydb import TinyDB, Query
from soft_watch_dog_timer import SoftWatchdog
db = TinyDB('db/settings.json')

def get_sleep_time():
    global db
    # db = TinyDB('db/settings.json')
    f=Query()
    res=db.search(f.feature=="sleep_timer")
    return res[0]["value"]

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


def _ticks_diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except Exception:
        return a - b


def test_deep_sleep_awake(screen_off_delay_ms=350, release_timeout_ms=1500):
    wakeup_pin = machine.Pin(8, mode=machine.Pin.IN, pull=machine.Pin.PULL_DOWN)
    display.clear_display()
    display.off()

    # Wait for key release (or timeout) so the same press doesn't wake immediately.
    start = _ticks_ms()
    while wakeup_pin.value() == 1 and _ticks_diff(_ticks_ms(), start) < release_timeout_ms:
        _sleep_ms(20)

    # Extra debounce after display is off.
    _sleep_ms(screen_off_delay_ms)

    opin = machine.Pin(14, machine.Pin.OUT, value=1, hold=True) # hold output level
    esp32.wake_on_ext0(pin=wakeup_pin, level=esp32.WAKEUP_ANY_HIGH)
    esp32.gpio_deep_sleep_hold(True)
    machine.deepsleep()

swdt=SoftWatchdog(timeout_ms=get_sleep_time(), callback=test_deep_sleep_awake, timer_id=1)

def update_sleep_time(time):
    global swdt, db
    # db = TinyDB('db/settings.json')
    f=Query()
    db.update({'value': time}, f.feature == "sleep_timer")
    swdt.update_time(timeout_ms=time)

def keypad_normal():
    opin = machine.Pin(21, machine.Pin.OUT, value=1, hold=False)
