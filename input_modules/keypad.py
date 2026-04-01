from calsci_keypad import Keypad as _NativeKeypad
from calsci_keypad import keypad_press_printing, set_keypad_press_printing


class Keypad:
    def __init__(self, *args, **kwargs):
        native = _NativeKeypad(*args, **kwargs)
        object.__setattr__(self, "_native", native)
        object.__setattr__(self, "keypad_loop", native.keypad_loop)

    def __getattr__(self, name):
        return getattr(self._native, name)

    def __setattr__(self, name, value):
        if name in ("_native", "keypad_loop"):
            object.__setattr__(self, name, value)
            return
        try:
            setattr(self._native, name, value)
        except Exception:
            object.__setattr__(self, name, value)

    def keypad_start(self):
        return self._native.keypad_start()

    def keypad_stop(self):
        return self._native.keypad_stop()


__all__ = ("Keypad", "keypad_press_printing", "set_keypad_press_printing")
