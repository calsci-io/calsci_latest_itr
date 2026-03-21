import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

import utime as time  # type: ignore

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

class Nav:
    AUTO_HIDE_MS = 1000

    def __init__(self, disp_out, chrs):
        self.state = "d"
        self.locked = False
        self.states = {"d": "default", "a": "alpha  ", "b": "beta   ", "A": "ALPHA  "}
        self.disp_out = disp_out
        self.chrs = chrs
        self._visible_until_ms = None
        self._restore_callback = None

    def _ticks_ms(self):
        if hasattr(time, "ticks_ms"):
            return time.ticks_ms()
        return int(time.time() * 1000)

    def _ticks_add(self, base_ms, delta_ms):
        if hasattr(time, "ticks_add"):
            return time.ticks_add(base_ms, delta_ms)
        return base_ms + delta_ms

    def _ticks_diff(self, now_ms, target_ms):
        if hasattr(time, "ticks_diff"):
            return time.ticks_diff(now_ms, target_ms)
        return now_ms - target_ms

    def _label(self):
        state = self.states[self.state]
        if self.is_mode_locked():
            return "{} locked".format(state.strip())
        return state

    def state_change(self, state, locked=None, show=True):
        self.state = state
        if locked is not None:
            self.locked = bool(locked) and state in ("a", "A", "b")
        elif state == "d":
            self.locked = False
        if show:
            self.show()
        else:
            self._visible_until_ms = None

    def set_locked(self, locked, show=True):
        self.locked = bool(locked) and self.state in ("a", "A", "b")
        if show:
            self.show()
        else:
            self._visible_until_ms = None

    def is_mode_locked(self):
        return self.locked and self.state in ("a", "A", "b")

    def show(self, duration_ms=None):
        duration_ms = self.AUTO_HIDE_MS if duration_ms is None else int(duration_ms)
        self._visible_until_ms = self._ticks_add(self._ticks_ms(), duration_ms)

    def is_visible(self):
        if self._visible_until_ms is None:
            return False
        return self._ticks_diff(self._visible_until_ms, self._ticks_ms()) > 0

    def set_restore_callback(self, callback=None):
        self._restore_callback = callback

    def maybe_hide(self):
        if self._visible_until_ms is None:
            return False
        if self._ticks_diff(self._ticks_ms(), self._visible_until_ms) < 0:
            return False
        self._visible_until_ms = None
        if self._restore_callback is not None:
            try:
                self._restore_callback()
            except Exception:
                pass
        return True

    def draw_state(self, state):
        state = str(state or "")
        self.disp_out.set_page_address(7)
        self.disp_out.set_column_address(0)
        for _ in range(128):
            self.disp_out.write_data(0b00000000)
        if state == "":
            return
        self.disp_out.set_column_address(0)
        invert = (
            "default" in state
            or "alpha" in state
            or "beta" in state
            or "ALPHA" in state
        )
        for char in state:
            if invert:
                char_bytes = self.chrs.invert_letter(char)
                cursor_line = 0b11111111
            else:
                char_bytes = self.chrs.Chr2bytes(char)
                cursor_line = 0b00000000
            for byte in char_bytes:
                self.disp_out.write_data(byte)
            self.disp_out.write_data(cursor_line)

    def current_state(self):
        if self.is_visible():
            return self._label()
        return ""
