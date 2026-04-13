from ui.components import wrap_lines


def go_back(ctx, fallback="launcher"):
    if not ctx.router.back():
        ctx.router.replace(fallback)


def clamp_scroll(lines, scroll, visible_rows=6):
    wrapped = wrap_lines(lines)
    limit = max(0, len(wrapped) - visible_rows)
    return max(0, min(int(scroll), limit))


def format_on_off(value):
    return "On" if value else "Off"


def level_bar(level, total=10):
    level = max(0, min(int(level), total))
    return "[" + ("#" * level) + ("." * (total - level)) + "]"


def get_saved_password(ctx, ssid):
    for item in ctx.storage.get_wifi_credentials():
        if item.get("ssid") == ssid:
            return item.get("password", "")
    return ""


def format_number(value):
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if int(value) == value:
            return str(int(value))
        return "%.6g" % value
    return str(value)


def format_minutes(milliseconds):
    return int(int(milliseconds) / 60000)
