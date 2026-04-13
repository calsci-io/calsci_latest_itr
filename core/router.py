class Router:
    def __init__(self, initial_route="launcher"):
        self._current = None
        self._current_params = {}
        self._pending = (initial_route, {})
        self._history = []

    def current(self):
        return self._current

    def current_params(self):
        return self._current_params

    def navigate(self, route, params=None):
        params = params or {}
        if self._current is not None:
            self._history.append((self._current, self._current_params))
        self._pending = (route, params)

    def replace(self, route, params=None):
        self._pending = (route, params or {})

    def back(self):
        if self._history:
            self._pending = self._history.pop()
            return True
        return False

    def consume_pending(self):
        pending = self._pending
        self._pending = None
        return pending

    def set_current(self, route, params=None):
        self._current = route
        self._current_params = params or {}

