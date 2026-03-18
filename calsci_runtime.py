try:
    import utime as _time
except ImportError:
    import time as _time


_CALSCI_KEYPAD_BLOCKED = False
_WAIT_SLICE_MS = 5


def _sleep_ms(delay_ms):
    try:
        _time.sleep_ms(int(delay_ms))
    except AttributeError:
        _time.sleep(max(0, int(delay_ms)) / 1000)


def set_calsci_keypad_blocked(blocked):
    global _CALSCI_KEYPAD_BLOCKED
    _CALSCI_KEYPAD_BLOCKED = bool(blocked)
    return _CALSCI_KEYPAD_BLOCKED


def block_calsci_keypad():
    return set_calsci_keypad_blocked(True)


def unblock_calsci_keypad():
    return set_calsci_keypad_blocked(False)


def calsci_keypad_blocked():
    return _CALSCI_KEYPAD_BLOCKED


def wait_if_repl_busy(release_callback=None):
    while _CALSCI_KEYPAD_BLOCKED:
        if release_callback is not None:
            try:
                release_callback()
            except Exception:
                pass
        _sleep_ms(_WAIT_SLICE_MS)
