import builtins


_ACTIVE_VIEW_ATTR = "_calsci_active_view"
_EDITABLE_VIEWS = {"text", "form"}


def set_active_view(view_name):
    setattr(builtins, _ACTIVE_VIEW_ATTR, str(view_name or ""))


def get_active_view():
    return str(getattr(builtins, _ACTIVE_VIEW_ATTR, "") or "")


def is_menu_view():
    return get_active_view() == "menu"


def allows_mode_switching():
    return get_active_view() in _EDITABLE_VIEWS
