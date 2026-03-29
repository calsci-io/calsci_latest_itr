_EDITABLE_VIEWS = {"text", "form"}
_active_view = ""


def set_active_view(view_name):
    global _active_view
    _active_view = str(view_name or "")


def get_active_view():
    return str(_active_view or "")


def is_menu_view():
    return get_active_view() == "menu"


def allows_mode_switching():
    return get_active_view() in _EDITABLE_VIEWS
