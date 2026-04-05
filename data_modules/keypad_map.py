import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from data_modules.math_symbols import PI_CHAR

class Keypad_5X8:
    def __init__(self, state="d"):
        keypad_5X8_layout_default=[
            ["on", "home", "settings", "back", "lock"],
            ["beta", "alpha", "toolbox", "fraction", "F1"],
            ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
            [PI_CHAR, "log", "sin", "cos", "tan"],
            ["pow", "root", ",", "(", ")"],
            ["F2", "F3", "F4", "F5", "F6"],
            ["7", "8", "9", "nav_b", "AC"],
            ["4", "5", "6", "*", "/"],
            ["1", "2", "3", "+", "-"],
            [".", "0", "*pow(10, )", "ans", "exe"]
        ]
        keypad_5X8_layout_alpha=[
            ["on", "home", "settings", "back", "lock"],
            ["beta", "alpha", "caps", "f", "l"],
            ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
            ["a", "b", "c", "d", "e"],
            ["g", "h", "i", "j", "k"],
            ["m", "n", "o", "p", "q"],
            ["r", "s", "t", "nav_b", "AC"],
            ["u", "v", "w", "*", "/"],
            ["x", "y", "z", "+", "-"],
            ["tab", " ", "", "ans", "exe"]
        ]
        keypad_5X8_layout_beta=[
            ["on", "home", "settings", "back", "lock"],
            ["beta", "alpha", "undo", "=", "$"],
            ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
            ["copy", "paste", "asin", "acos", "atan"],
            ["&", "`", '"', "'", "\\"],
            ["^", "~", "!", "<", ">"],
            ["[", "]", "%", "nav_b", "AC"],
            ["{", "}", ":", "*", "/"],
            ["#", "|", ";", "+", "-"],
            ["@", "?", "_", "ans", "exe"]
        ]
        keypad_5X8_layout_ALPHA=[
            ["on", "home", "settings", "back", "lock"],
            ["beta", "alpha", "caps", "F", "L"],
            ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
            ["A", "B", "C", "D", "E"],
            ["G", "H", "I", "J", "K"],
            ["M", "N", "O", "P", "Q"],
            ["R", "S", "T", "nav_b", "AC"],
            ["U", "V", "W", "*", "/"],
            ["X", "Y", "Z", "+", "-"],
            ["tab", " ", "", "ans", "exe"]
        ]

        self.state=state
        self.states={"d":keypad_5X8_layout_default, "a":keypad_5X8_layout_alpha, "b": keypad_5X8_layout_beta, "A": keypad_5X8_layout_ALPHA}
    def key_out(self, col, row):
        return self.states[self.state][row][col]
    def key_change(self, state):
        self.state=state
