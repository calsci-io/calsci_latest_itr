import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

class Nav:
    def __init__(self, disp_out, chrs):
        self.state = "d"
        self.locked = False
        self.states = {"d": "default", "a": "alpha  ", "b": "beta   ", "A": "ALPHA  "}
        self.disp_out = disp_out
        self.chrs = chrs

    def state_change(self, state, locked=None):
        self.state = state
        if locked is not None:
            self.locked = bool(locked) and state in ("a", "A", "b")
        elif state == "d":
            self.locked = False

    def set_locked(self, locked):
        self.locked = bool(locked) and self.state in ("a", "A", "b")

    def is_mode_locked(self):
        return self.locked and self.state in ("a", "A", "b")

    def current_state(self):
        state = self.states[self.state]
        if self.is_mode_locked():
            return "{} locked".format(state.strip())
        return state
