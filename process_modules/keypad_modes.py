LOCKABLE_KEYPAD_STATES = ("a", "A", "b")
ALPHA_KEYPAD_STATES = ("a", "A")

from process_modules.ui_context import allows_mode_switching, is_menu_view


def is_lockable_state(state):
    return state in LOCKABLE_KEYPAD_STATES


def _apply_state(keymap, nav, state, locked=False, show_overlay=True):
    keymap.key_change(state=state)
    nav.state_change(state=state, locked=locked, show=show_overlay)


def reset_mode(keymap, nav, show_overlay=False):
    _apply_state(
        keymap=keymap,
        nav=nav,
        state="d",
        locked=False,
        show_overlay=show_overlay,
    )


def _menu_force_default(keymap, nav):
    reset_mode(keymap=keymap, nav=nav, show_overlay=False)


def handle_mode_key(keymap, nav, key_name):
    current_state = getattr(keymap, "state", "d")
    key_name = str(key_name)

    if is_menu_view() or not allows_mode_switching():
        if key_name in ("alpha", "a", "beta", "b", "caps", "A"):
            if current_state != "d" or nav.is_mode_locked():
                _menu_force_default(keymap=keymap, nav=nav)
            return True

    if key_name in ("alpha", "a"):
        if current_state in ALPHA_KEYPAD_STATES:
            reset_mode(keymap=keymap, nav=nav, show_overlay=True)
        else:
            _apply_state(
                keymap=keymap,
                nav=nav,
                state="a",
                locked=False,
                show_overlay=True,
            )
        return True

    if key_name in ("beta", "b"):
        if current_state == "b":
            reset_mode(keymap=keymap, nav=nav, show_overlay=True)
        else:
            _apply_state(
                keymap=keymap,
                nav=nav,
                state="b",
                locked=False,
                show_overlay=True,
            )
        return True

    if key_name in ("caps", "A"):
        if current_state == "a":
            _apply_state(
                keymap=keymap,
                nav=nav,
                state="A",
                locked=nav.is_mode_locked(),
                show_overlay=True,
            )
        elif current_state == "A":
            _apply_state(
                keymap=keymap,
                nav=nav,
                state="a",
                locked=nav.is_mode_locked(),
                show_overlay=True,
            )
        else:
            _apply_state(
                keymap=keymap,
                nav=nav,
                state="A",
                locked=False,
                show_overlay=True,
            )
        return True

    return False


def toggle_mode_lock(keymap, nav):
    current_state = getattr(keymap, "state", "d")

    if is_menu_view() or not allows_mode_switching():
        if current_state != "d" or nav.is_mode_locked():
            _menu_force_default(keymap=keymap, nav=nav)
        else:
            nav.set_locked(False, show=False)
        return False

    if not is_lockable_state(current_state):
        nav.set_locked(False, show=False)
        return False

    if nav.is_mode_locked():
        reset_mode(keymap=keymap, nav=nav, show_overlay=True)
    else:
        nav.set_locked(True, show=True)
    return True


def should_auto_reset_after_input(keymap, nav, key_name):
    if is_menu_view() or not allows_mode_switching():
        return False

    current_state = getattr(keymap, "state", "d")
    if not is_lockable_state(current_state) or nav.is_mode_locked():
        return False

    key_name = str(key_name)
    if key_name in ("", "alpha", "beta", "caps", "lock"):
        return False

    return True
