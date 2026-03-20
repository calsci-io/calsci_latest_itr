LOCKABLE_KEYPAD_STATES = ("a", "A", "b")
ALPHA_KEYPAD_STATES = ("a", "A")


def is_lockable_state(state):
    return state in LOCKABLE_KEYPAD_STATES


def _apply_state(keymap, nav, state, locked=False):
    keymap.key_change(state=state)
    nav.state_change(state=state, locked=locked)


def reset_mode(keymap, nav):
    _apply_state(keymap=keymap, nav=nav, state="d", locked=False)


def handle_mode_key(keymap, nav, key_name):
    current_state = getattr(keymap, "state", "d")
    key_name = str(key_name)

    if key_name in ("alpha", "a"):
        if current_state in ALPHA_KEYPAD_STATES:
            reset_mode(keymap=keymap, nav=nav)
        else:
            _apply_state(keymap=keymap, nav=nav, state="a", locked=False)
        return True

    if key_name in ("beta", "b"):
        if current_state == "b":
            reset_mode(keymap=keymap, nav=nav)
        else:
            _apply_state(keymap=keymap, nav=nav, state="b", locked=False)
        return True

    if key_name in ("caps", "A"):
        if current_state == "a":
            _apply_state(
                keymap=keymap,
                nav=nav,
                state="A",
                locked=nav.is_mode_locked(),
            )
        elif current_state == "A":
            _apply_state(
                keymap=keymap,
                nav=nav,
                state="a",
                locked=nav.is_mode_locked(),
            )
        else:
            _apply_state(keymap=keymap, nav=nav, state="A", locked=False)
        return True

    return False


def toggle_mode_lock(keymap, nav):
    current_state = getattr(keymap, "state", "d")
    if not is_lockable_state(current_state):
        nav.set_locked(False)
        return False

    if nav.is_mode_locked():
        reset_mode(keymap=keymap, nav=nav)
    else:
        nav.set_locked(True)
    return True


def should_auto_reset_after_input(keymap, nav, key_name):
    current_state = getattr(keymap, "state", "d")
    if not is_lockable_state(current_state) or nav.is_mode_locked():
        return False

    key_name = str(key_name)
    if key_name in ("", "alpha", "beta", "caps", "lock"):
        return False

    return True
