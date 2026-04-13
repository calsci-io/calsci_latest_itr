try:
    import _thread as _thread_mod
except ImportError:
    _thread_mod = None

try:
    import threading as _threading_mod
except ImportError:
    _threading_mod = None


def _alloc_lock():
    if _thread_mod is not None:
        return _thread_mod.allocate_lock()
    if _threading_mod is not None:
        return _threading_mod.Lock()
    return None


class EventBus:
    def __init__(self):
        self._queue = []
        self._lock = _alloc_lock()

    def publish(self, event):
        if event is None:
            return
        if self._lock is None:
            self._queue.append(event)
            return
        self._lock.acquire()
        try:
            self._queue.append(event)
        finally:
            self._lock.release()

    def drain(self):
        if self._lock is None:
            queued = self._queue
            self._queue = []
            return queued
        self._lock.acquire()
        try:
            queued = self._queue
            self._queue = []
            return queued
        finally:
            self._lock.release()


def input_event(token, mode_label):
    return {
        "type": "input",
        "token": token,
        "mode_label": mode_label,
    }


def task_event(name, status, payload=None, error=None):
    return {
        "type": "task",
        "name": name,
        "status": status,
        "payload": payload,
        "error": error,
    }


def tick_event(now_ms):
    return {
        "type": "tick",
        "now_ms": now_ms,
    }

