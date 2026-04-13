from ui.models import FormField
from ui.theme import TEXT_COLS


COMMAND_TOKENS = (
    "nav_u",
    "nav_d",
    "nav_l",
    "nav_r",
    "nav_b",
    "ok",
    "exe",
    "back",
    "home",
    "wifi",
    "on",
    "toolbox",
    "alpha",
    "beta",
    "caps",
    "AC",
    "settings",
    "lock",
    "rst",
    "bt",
)


TEXT_INSERTS = {
    "sin()": "sin(",
    "cos()": "cos(",
    "tan()": "tan(",
    "asin(": "asin(",
    "acos(": "acos(",
    "atan(": "atan(",
    "diff()": "diff(",
    "ln()": "log(",
    "pow(,)": "pow(",
    "pow( ,0.5)": "**0.5",
    "pow( ,2)": "**2",
    "pi": "pi",
    "e": "e",
    "ans": "ans",
    "log": "log10(",
    "fraction": "/",
    "summation": "sum(",
    "tab": "    ",
    "S_D": "sqrt(",
    "igtn()": "int(",
    "module": "%",
    "backlight": "",
    "bluetooth": "",
    "shot": "",
    "copy": "",
    "paste": "",
    "undo": "",
    "off": "off",
}


def wrap_lines(lines, width=TEXT_COLS):
    wrapped = []
    for raw in lines:
        text = str(raw)
        if not text:
            wrapped.append("")
            continue
        while len(text) > width:
            wrapped.append(text[:width])
            text = text[width:]
        wrapped.append(text)
    return wrapped


def menu_move(token, index, count):
    if count <= 0:
        return 0
    if token == "nav_d":
        return (index + 1) % count
    if token == "nav_u":
        return (index - 1) % count
    return index


def normalize_insert(token):
    if token in TEXT_INSERTS:
        return TEXT_INSERTS[token]
    if token in COMMAND_TOKENS:
        return None
    return token


def apply_text_edit(current, token):
    if token == "AC":
        return ""
    if token in ("nav_b",):
        return current[:-1]
    text = normalize_insert(token)
    if text is None:
        return current
    if text == "off":
        return current
    return current + text


def fields_from_pairs(pairs):
    fields = []
    for key, label, value in pairs:
        fields.append(FormField(key, label, value))
    return fields
