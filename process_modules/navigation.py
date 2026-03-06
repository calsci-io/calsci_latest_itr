import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.


class NavigationRequest(BaseException):
    def __init__(self, app_name, group_name):
        self.app_name = app_name
        self.group_name = group_name
        super().__init__(app_name, group_name)


_home_target = ("home", "root")
_stack = [_home_target]


def _target_tuple(app_name, group_name):
    return (str(app_name), str(group_name))


def register_app_entry(app_name, group_name):
    target = _target_tuple(app_name, group_name)
    if target == _home_target:
        reset_to_home()
        return
    if not _stack:
        _stack.append(_home_target)
    if _stack[-1] == target:
        return
    _stack.append(target)
    if len(_stack) > 50:
        del _stack[:-50]


def reset_to_home():
    _stack[:] = [_home_target]


def _back_target():
    if len(_stack) <= 1:
        return _home_target
    _stack.pop()
    return _stack[-1]


def request_navigation_from_key(key):
    if key == "home":
        reset_to_home()
        raise NavigationRequest(_home_target[0], _home_target[1])

    if key == "settings":
        raise NavigationRequest("settings", "root")

    if key == "back":
        target = _back_target()
        raise NavigationRequest(target[0], target[1])
