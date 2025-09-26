# class Keypad_5X8:
#     def __init__(self, state="d"):
#         # keypad_5X8_layout_default=[
#         #     ["alpha", "beta", "nav_u", "home", "on"],
#         #     ["back", "nav_l", "ok", "nav_r", "tab"],
#         #     ["\"", "'", "nav_d", "(", ")"],
#         #     ["pow(", "sin(", "cos(", "tan(", "log("],
#         #     ["7", "8", "9", "nav_b", "AC"],
#         #     ["4", "5", "6", "*", "/"],
#         #     ["1", "2", "3", "+", "-"],
#         #     [".", "0", "*pow(10,", "ans", "exe"],
#         # ]
#         # keypad_5X8_layout_alpha=[
#         #     ["alpha", "beta", "nav_u", "opt", "on"],
#         #     ["alpha_on", "nav_l", "ok", "nav_r", "<"],
#         #     ["y", "z", "nav_d", "[", "]"],
#         #     ["t", "u", "v", "w", "x"],
#         #     ["o", "p", "q", "r", "s"],
#         #     ["j", "k", "l", "m", "n"],
#         #     ["e", "f", "g", "h", "i"],
#         #     ["a", "b", "c", "d", " "],
#         # ]
#         # keypad_5X8_layout_beta=[
#         #     ["alpha", "beta", "nav_u", "backlight", "on"],
#         #     ["beta_on", "nav_l", "ok", "nav_r", ">"],
#         #     ["off", "caps", "nav_d", "{", "}"],
#         #     ["pi", "asin(", "acos(", "atan(", ""],
#         #     ["&", "~", "\\", "", ""],
#         #     ["$", "%", "^", "|", ""],
#         #     ["!", "@", "#", "=", "_"],
#         #     [",", "?", ":", ";", ""],
#         # ]
#         keypad_5X8_layout_default=[
#             ["on", "alpha", "beta", "home", "wifi"],
#             ["backlight", "back", "toolbox", "diff(", "ln"],
#             ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
#             ["module", "bluetooth", "sin(", "cos", "tan"],
#             ["ingn(", "pi", "e", "summation", "fraction"],
#             ["log", "pow(", "pow( ,0.5)", "pow( ,2)", "S_D"],
#             ["7", "8", "9", "nav_b", "AC"],
#             ["4", "5", "6", "*", "/"],
#             ["1", "2", "3", "+", "-"],
#             [".", "0", ",", "ans", "exe"]
#         ]
#         keypad_5X8_layout_alpha=[
#             ["on", "alpha", "beta", "home", "wifi"],
#             ["backlight", "back", "caps", "f", "l"],
#             ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
#             ["a", "b", "c", "d", "e"],
#             ["g", "h", "i", "j", "k"],
#             ["m", "n", "o", "p", "q"],
#             ["r", "s", "t", "nav_b", "AC"],
#             ["u", "v", "w", "*", "/"],
#             ["x", "y", "z", "+", "-"],
#             [" ", "off", "tab", "ans", "exe"]
#         ]
#         keypad_5X8_layout_beta=[
#             ["on", "alpha", "beta", "home", "wifi"],
#             ["backlight", "back", "undo", "=", "$"],
#             ["nav_l", "nav_d", "nav_r", "ok", "nav_u"],
#             ["copy", "paste", "asin(", "acos(", "atan("],
#             ["&", "`", '"', "'", "shot"],
#             ["^", "~", "!", "<", ">"],
#             ["[", "]", "%", "nav_b", "AC"],
#             ["{", "}", ":", "*", "/"],
#             ["(", ")", ";", "+", "-"],
#             ["@", "?", "\"", "ans", "exe"]
#         ]
        
#         self.state=state
#         self.states={"d":keypad_5X8_layout_default, "a":keypad_5X8_layout_alpha, "b": keypad_5X8_layout_beta}
#     def key_out(self, col, row):
#         return self.states[self.state][row][col]
#     def key_change(self, state):
#         self.state=state

from constants import KeyButtons as KB, KeypadMode as KM

class Keypad_5X8:
    def __init__(self, state=KM.DEFAULT):
        keypad_5X8_layout_default = [
            [KB.ON, KB.ALPHA, KB.BETA, KB.HOME, KB.WIFI],
            [KB.BACKLIGHT, KB.BACK, KB.TOOLBOX, KB.DIFF, KB.LN],
            [KB.NAV_L, KB.NAV_D, KB.NAV_R, KB.OK, KB.NAV_U],
            [KB.MODULE, KB.BLUETOOTH, KB.SIN, KB.COS, KB.TAN],
            [KB.INGN, KB.PI, KB.EULER_CONSTANT, KB.SUMMATION, KB.FRACTION],
            [KB.LOG, KB.POW, KB.SQRT, KB.POW_2, KB.S_D],
            [KB.SEVEN, KB.EIGHT, KB.NINE, KB.BACKSPACE, KB.ALL_CLEAR],
            [KB.FOUR, KB.FIVE, KB.SIX, KB.MULTIPLY, KB.DIVIDE],
            [KB.ONE, KB.TWO, KB.THREE, KB.PLUS, KB.MINUS],
            [KB.DECIMAL, KB.ZERO, KB.COMMA, KB.ANSWER, KB.EXE],
        ]

        keypad_5X8_layout_alpha = [
            [KB.ON, KB.ALPHA, KB.BETA, KB.HOME, KB.WIFI],
            [KB.BACKLIGHT, KB.BACK, KB.CAPS, KB.F, KB.L],
            [KB.NAV_L, KB.NAV_D, KB.NAV_R, KB.OK, KB.NAV_U],
            [KB.A, KB.B, KB.C, KB.D, KB.E],
            [KB.G, KB.H, KB.I, KB.J, KB.K],
            [KB.M, KB.N, KB.O, KB.P, KB.Q],
            [KB.R, KB.S, KB.T, KB.BACKSPACE, KB.ALL_CLEAR],
            [KB.U, KB.V, KB.W, KB.MULTIPLY, KB.DIVIDE],
            [KB.X, KB.Y, KB.Z, KB.PLUS, KB.MINUS],
            [KB.SPACE, KB.OFF, KB.TAB, KB.ANSWER, KB.EXE],  # Add SPACE to KeyButtons enum
        ]

        keypad_5X8_layout_beta = [
            [KB.ON, KB.ALPHA, KB.BETA, KB.HOME, KB.WIFI],
            [KB.BACKLIGHT, KB.BACK, KB.UNDO, KB.EQUAL, KB.DOLLAR],
            [KB.NAV_L, KB.NAV_D, KB.NAV_R, KB.OK, KB.NAV_U],
            [KB.COPY, KB.PASTE, KB.ASIN, KB.ACOS, KB.ATAN],
            [KB.AND, KB.BACKTICK, KB.ESCAPED_QUOTE, KB.SINGLE_QUOTE, KB.SHOT],
            [KB.CARET, KB.TILDE, KB.EXCLAMATION, KB.LESS_THAN, KB.GREATER_THAN],
            [KB.LEFT_BRACKET, KB.RIGHT_BRACKET, KB.PERCENT, KB.BACKSPACE, KB.ALL_CLEAR],
            [KB.LEFT_BRACE, KB.RIGHT_BRACE, KB.COLON, KB.ASTERISK, KB.SLASH],
            [KB.LEFT_PAREN, KB.RIGHT_PAREN, KB.SEMICOLON, KB.PLUS, KB.MINUS],
            [KB.AT, KB.QUESTION, KB.ESCAPED_QUOTE, KB.ANSWER, KB.EXE],
        ]

        self.state = state
        self.states = {
            KM.DEFAULT: keypad_5X8_layout_default,
            KM.ALPHA: keypad_5X8_layout_alpha,
            KM.BETA: keypad_5X8_layout_beta,
        }

    def key_out(self, col, row):
        return self.states[self.state][row][col]

    def key_change(self, state):
        self.state = state

