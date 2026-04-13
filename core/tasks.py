from .events import task_event

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


class TaskManager:
    def __init__(self, bus, max_workers=2):
        self.bus = bus
        self.max_workers = int(max_workers)
        self._active = 0
        self._lock = _alloc_lock()

    def _acquire_slot(self):
        if self._lock is None:
            if self._active >= self.max_workers:
                return False
            self._active += 1
            return True
        self._lock.acquire()
        try:
            if self._active >= self.max_workers:
                return False
            self._active += 1
            return True
        finally:
            self._lock.release()

    def _release_slot(self):
        if self._lock is None:
            self._active = max(0, self._active - 1)
            return
        self._lock.acquire()
        try:
            self._active = max(0, self._active - 1)
        finally:
            self._lock.release()

    def submit(self, name, target, args=None, kwargs=None):
        args = args or ()
        kwargs = kwargs or {}
        if not self._acquire_slot():
            self.bus.publish(task_event(name, "rejected", error="task pool full"))
            return False

        def runner():
            try:
                payload = target(*args, **kwargs)
                self.bus.publish(task_event(name, "completed", payload=payload))
            except Exception as exc:
                self.bus.publish(task_event(name, "failed", error=str(exc)))
            finally:
                self._release_slot()

        if _threading_mod is not None:
            thread = _threading_mod.Thread(target=runner)
            thread.daemon = True
            thread.start()
            return True
        if _thread_mod is not None:
            _thread_mod.start_new_thread(runner, ())
            return True

        try:
            payload = target(*args, **kwargs)
            self.bus.publish(task_event(name, "completed", payload=payload))
        except Exception as exc:
            self.bus.publish(task_event(name, "failed", error=str(exc)))
        finally:
            self._release_slot()
        return True

