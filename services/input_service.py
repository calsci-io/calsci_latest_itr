from core.events import input_event

try:
    import utime as _time_mod
except ImportError:
    import time as _time_mod


def _ticks_ms():
    if hasattr(_time_mod, "ticks_ms"):
        return _time_mod.ticks_ms()
    return int(_time_mod.time() * 1000)


class InputService:
    def __init__(self, adapter, storage):
        self.adapter = adapter
        self.storage = storage
        self._mode = "d"
        self._last_input_ms = None

    def mode_label(self):
        return {
            "d": "default",
            "a": "alpha",
            "b": "beta",
            "A": "ALPHA",
        }.get(self._mode, "default")

    def last_input_ms(self):
        return self._last_input_ms

    def poll(self):
        token = self.adapter.poll_token(self._mode)
        if token is None:
            return None
        self._last_input_ms = _ticks_ms()
        if token == "alpha":
            self._mode = "d" if self._mode == "a" else "a"
            return {"type": "mode", "mode_label": self.mode_label()}
        if token == "beta":
            self._mode = "d" if self._mode == "b" else "b"
            return {"type": "mode", "mode_label": self.mode_label()}
        if token == "caps":
            self._mode = "d" if self._mode == "A" else "A"
            return {"type": "mode", "mode_label": self.mode_label()}

        current_label = self.mode_label()
        event = input_event(token, current_label)
        if self._mode in ("a", "b"):
            self._mode = "d"
        return event

