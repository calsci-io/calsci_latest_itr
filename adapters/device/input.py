try:
    import _thread as _thread_mod
except ImportError:
    _thread_mod = None

try:
    import threading as _threading_mod
except ImportError:
    _threading_mod = None

try:
    import utime as _time_mod
except ImportError:
    import time as _time_mod

try:
    import machine  # type: ignore
except ImportError:
    machine = None

from adapters.device.hardware_config import KEYPAD_COLS, KEYPAD_ENABLED, KEYPAD_ROWS

try:
    from calsci_keypad import Keypad as NativeKeypad  # type: ignore
except ImportError:
    NativeKeypad = None


def _sleep_ms(value):
    if hasattr(_time_mod, "sleep_ms"):
        _time_mod.sleep_ms(value)
    else:
        _time_mod.sleep(value / 1000.0)


def _allocate_lock():
    if _threading_mod is not None and hasattr(_threading_mod, "Lock"):
        return _threading_mod.Lock()
    if _thread_mod is not None:
        return _thread_mod.allocate_lock()
    return None


def _start_worker(target):
    if _threading_mod is not None and hasattr(_threading_mod, "Thread"):
        worker = _threading_mod.Thread(target=target, daemon=True)
        worker.start()
        return worker
    if _thread_mod is not None:
        _thread_mod.start_new_thread(target, ())
        return True
    return None


class _NullKeypad:
    def keypad_loop(self):
        return None


class _MatrixKeypad:
    def __init__(self, rows, cols):
        self._held_key = None
        pin_cls = machine.Pin
        pull_up = getattr(pin_cls, "PULL_UP", None)
        self._row_pins = []
        self._col_pins = []
        for pin in rows:
            row_pin = pin_cls(pin, pin_cls.OUT)
            row_pin.value(1)
            self._row_pins.append(row_pin)
        for pin in cols:
            if pull_up is None:
                col_pin = pin_cls(pin, pin_cls.IN)
            else:
                col_pin = pin_cls(pin, pin_cls.IN, pull=pull_up)
            self._col_pins.append(col_pin)

    def poll_key(self):
        detected = None
        for row_index, row_pin in enumerate(self._row_pins):
            row_pin.value(0)
            for col_index, col_pin in enumerate(self._col_pins):
                if int(col_pin.value()) == 0:
                    detected = (col_index, row_index)
                    break
            row_pin.value(1)
            if detected is not None:
                break
        if detected is None:
            self._held_key = None
            return None
        if detected == self._held_key:
            return None
        self._held_key = detected
        return detected


class DeviceInputAdapter:
    def __init__(self):
        self._layouts = {
            "d": [
                ["on", "alpha", "beta", "home", "wifi"],
                ["backlight", "back", "toolbox", "diff()", "ln()"],
                ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
                ["module", "bluetooth", "sin()", "cos()", "tan()"],
                ["igtn()", "pi", "e", "summation", "fraction"],
                ["log", "pow(,)", "pow( ,0.5)", "pow( ,2)", "S_D"],
                ["7", "8", "9", "nav_b", "AC"],
                ["4", "5", "6", "*", "/"],
                ["1", "2", "3", "+", "-"],
                [".", "0", ",", "ans", "exe"],
            ],
            "a": [
                ["on", "alpha", "beta", "home", "wifi"],
                ["backlight", "back", "caps", "f", "l"],
                ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
                ["a", "b", "c", "d", "e"],
                ["g", "h", "i", "j", "k"],
                ["m", "n", "o", "p", "q"],
                ["r", "s", "t", "nav_b", "AC"],
                ["u", "v", "w", "*", "/"],
                ["x", "y", "z", "+", "-"],
                [" ", "off", "tab", "ans", "exe"],
            ],
            "b": [
                ["on", "alpha", "beta", "home", "wifi"],
                ["backlight", "back", "undo", "=", "$"],
                ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
                ["copy", "paste", "asin(", "acos(", "atan("],
                ["&", "`", '"', "'", "shot"],
                ["^", "~", "!", "<", ">"],
                ["[", "]", "%", "nav_b", "AC"],
                ["{", "}", ":", "*", "/"],
                ["(", ")", ";", "+", "-"],
                ["@", "?", "\"", "ans", "exe"],
            ],
            "A": [
                ["on", "alpha", "beta", "home", "wifi"],
                ["backlight", "back", "caps", "F", "L"],
                ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
                ["A", "B", "C", "D", "E"],
                ["G", "H", "I", "J", "K"],
                ["M", "N", "O", "P", "Q"],
                ["R", "S", "T", "nav_b", "AC"],
                ["U", "V", "W", "*", "/"],
                ["X", "Y", "Z", "+", "-"],
                [" ", "off", "tab", "ans", "exe"],
            ],
        }
        self._matrix_keypad = None
        self._pending_key = None
        self._pending_lock = None
        self._keypad = _NullKeypad()
        if not KEYPAD_ENABLED:
            return
        if machine is not None and hasattr(machine, "Pin"):
            try:
                self._matrix_keypad = _MatrixKeypad(KEYPAD_ROWS, KEYPAD_COLS)
                return
            except Exception:
                self._matrix_keypad = None
        if NativeKeypad is not None:
            self._keypad = NativeKeypad(rows=list(KEYPAD_ROWS), cols=list(KEYPAD_COLS))
            self._pending_lock = _allocate_lock()
            if self._pending_lock is not None:
                _start_worker(self._keypad_worker)

    def _store_pending_key(self, key):
        if self._pending_lock is None:
            self._pending_key = key
            return
        self._pending_lock.acquire()
        try:
            self._pending_key = key
        finally:
            self._pending_lock.release()

    def _take_pending_key(self):
        if self._pending_lock is None:
            key = self._pending_key
            self._pending_key = None
            return key
        self._pending_lock.acquire()
        try:
            key = self._pending_key
            self._pending_key = None
            return key
        finally:
            self._pending_lock.release()

    def _keypad_worker(self):
        while True:
            try:
                key = self._keypad.keypad_loop()
            except Exception:
                _sleep_ms(20)
                continue
            if key is None:
                _sleep_ms(10)
                continue
            self._store_pending_key((int(key[0]), int(key[1])))

    def poll_token(self, mode_key):
        if self._matrix_keypad is not None:
            key = self._matrix_keypad.poll_key()
        else:
            key = self._take_pending_key()
            if key is None and self._pending_lock is None:
                key = self._keypad.keypad_loop()
        if key is None:
            return None
        col = int(key[0])
        row = int(key[1])
        layout = self._layouts.get(mode_key, self._layouts["d"])
        if row < 0 or row >= len(layout):
            return None
        if col < 0 or col >= len(layout[row]):
            return None
        return layout[row][col]
