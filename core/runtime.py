from .events import tick_event

try:
    import utime as _time_mod
except ImportError:
    import time as _time_mod


def _ticks_ms():
    if hasattr(_time_mod, "ticks_ms"):
        return _time_mod.ticks_ms()
    return int(_time_mod.time() * 1000)


def _ticks_diff(now_ms, prev_ms):
    if hasattr(_time_mod, "ticks_diff"):
        return _time_mod.ticks_diff(now_ms, prev_ms)
    return now_ms - prev_ms


def _sleep_ms(value):
    if hasattr(_time_mod, "sleep_ms"):
        _time_mod.sleep_ms(value)
    else:
        _time_mod.sleep(value / 1000.0)


class RuntimeKernel:
    def __init__(self, ctx, initial_route="launcher", tick_ms=100):
        self.ctx = ctx
        self.initial_route = initial_route
        self.tick_ms = tick_ms
        self._app = None
        self._force_render = True

    def _activate(self, route, params):
        if self._app is not None:
            try:
                self._app.exit(self.ctx)
            except Exception:
                pass
        self._app = self.ctx.registry.create(route)
        self.ctx.router.set_current(route, params)
        self._app.enter(self.ctx, params)
        self._force_render = True

    def _handle_event(self, event):
        if self._app is None:
            return
        if event.get("type") == "mode":
            self._force_render = True
            return
        if event.get("type") == "input":
            token = event.get("token")
            if token == "home":
                self.ctx.router.replace("launcher")
                return
            if token == "settings":
                self.ctx.router.replace("settings_hub")
                return
            if token == "wifi":
                self.ctx.router.replace("wifi_manager")
                return
            if token == "lock":
                self.ctx.router.replace("wifi_manager")
                return
            if token == "off":
                self.ctx.power.deep_sleep()
                return
        try:
            self._app.handle_event(self.ctx, event)
        except Exception as exc:
            self.ctx.render.render_exception(exc)

    def run(self):
        self._activate(self.initial_route, {})
        last_tick = _ticks_ms()
        while True:
            pending = self.ctx.router.consume_pending()
            if pending is not None:
                self._activate(pending[0], pending[1])

            now_ms = _ticks_ms()
            if _ticks_diff(now_ms, last_tick) >= self.tick_ms:
                self.ctx.bus.publish(tick_event(now_ms))
                last_tick = now_ms

            event = self.ctx.input.poll()
            if event is not None:
                self.ctx.bus.publish(event)

            for item in self.ctx.bus.drain():
                self._handle_event(item)

            pending = self.ctx.router.consume_pending()
            if pending is not None:
                self._activate(pending[0], pending[1])

            self._handle_idle_timeout(now_ms)
            if self._app is not None and (self._force_render or self._app.consume_dirty()):
                screen = self._app.render(self.ctx)
                self.ctx.render.render(screen)
                self._force_render = False

            _sleep_ms(20)

    def _handle_idle_timeout(self, now_ms):
        settings = self.ctx.storage.get_settings()
        if not settings.get("auto_sleep", False):
            return
        timeout_ms = int(settings.get("sleep_timer_ms", 0) or 0)
        if timeout_ms <= 0:
            return
        last_input_ms = self.ctx.input.last_input_ms()
        if last_input_ms is None:
            return
        if _ticks_diff(now_ms, last_input_ms) >= timeout_ms:
            self.ctx.power.deep_sleep()
