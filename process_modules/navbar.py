import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

import utime as time  # type: ignore

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

class Nav:
    AUTO_HIDE_MS = 1000
    BOTTOM_PAGE = 7
    PAGE_WIDTH = 128

    def __init__(self, disp_out, chrs):
        self.state = "d"
        self.locked = False
        self.states = {"d": "default", "a": "alpha  ", "b": "beta   ", "A": "ALPHA  "}
        self.disp_out = disp_out
        self.chrs = chrs
        self._visible_until_ms = None
        self._restore_callback = None
        self._last_bottom_page = None
        self._wrap_display_calls()

    def _wrap_display_calls(self):
        graphics_callable = getattr(self.disp_out, "graphics", None)
        if callable(graphics_callable) and not getattr(graphics_callable, "_nav_cache_wrapper", False):
            original_graphics = graphics_callable

            def _graphics_wrapper(framebuffer, **kwargs):
                page = int(kwargs.get("page", 0) or 0)
                pages = int(kwargs.get("pages", 1) or 1)
                if page <= self.BOTTOM_PAGE < (page + max(0, pages)):
                    self._last_bottom_page = None
                return original_graphics(framebuffer, **kwargs)

            _graphics_wrapper.__wrapped__ = original_graphics
            if hasattr(original_graphics, "pixels_changed"):
                _graphics_wrapper.pixels_changed = getattr(original_graphics, "pixels_changed")
            _graphics_wrapper._nav_cache_wrapper = True
            self.disp_out.graphics = _graphics_wrapper

        clear_callable = getattr(self.disp_out, "clear_display", None)
        if callable(clear_callable) and not getattr(clear_callable, "_nav_cache_wrapper", False):
            original_clear = clear_callable

            def _clear_wrapper(*args, **kwargs):
                self._last_bottom_page = None
                return original_clear(*args, **kwargs)

            _clear_wrapper.__wrapped__ = original_clear
            _clear_wrapper._nav_cache_wrapper = True
            self.disp_out.clear_display = _clear_wrapper

    def _ticks_ms(self):
        if hasattr(time, "ticks_ms"):
            return time.ticks_ms()
        return int(time.time() * 1000)

    def _ticks_add(self, base_ms, delta_ms):
        if hasattr(time, "ticks_add"):
            return time.ticks_add(base_ms, delta_ms)
        return base_ms + delta_ms

    def _ticks_diff(self, now_ms, target_ms):
        if hasattr(time, "ticks_diff"):
            return time.ticks_diff(now_ms, target_ms)
        return now_ms - target_ms

    def _label(self):
        state = self.states[self.state]
        if self.is_mode_locked():
            return "{} locked".format(state.strip())
        return state

    def state_change(self, state, locked=None, show=True):
        self.state = state
        if locked is not None:
            self.locked = bool(locked) and state in ("a", "A", "b")
        elif state == "d":
            self.locked = False
        if show:
            self.show()
        else:
            self._visible_until_ms = None

    def set_locked(self, locked, show=True):
        self.locked = bool(locked) and self.state in ("a", "A", "b")
        if show:
            self.show()
        else:
            self._visible_until_ms = None

    def is_mode_locked(self):
        return self.locked and self.state in ("a", "A", "b")

    def show(self, duration_ms=None):
        duration_ms = self.AUTO_HIDE_MS if duration_ms is None else int(duration_ms)
        self._visible_until_ms = self._ticks_add(self._ticks_ms(), duration_ms)

    def is_visible(self):
        if self._visible_until_ms is None:
            return False
        return self._ticks_diff(self._visible_until_ms, self._ticks_ms()) > 0

    def set_restore_callback(self, callback=None):
        self._restore_callback = callback

    def maybe_hide(self):
        if self._visible_until_ms is None:
            return False
        if self._ticks_diff(self._ticks_ms(), self._visible_until_ms) < 0:
            return False
        self._visible_until_ms = None
        if self._restore_callback is not None:
            try:
                self._restore_callback()
            except Exception:
                pass
        return True

    def _normalize_bottom_page(self, page_buf):
        page_bytes = bytes(page_buf or b"")
        if len(page_bytes) < self.PAGE_WIDTH:
            page_bytes += b"\x00" * (self.PAGE_WIDTH - len(page_bytes))
        elif len(page_bytes) > self.PAGE_WIDTH:
            page_bytes = page_bytes[: self.PAGE_WIDTH]
        return page_bytes

    def draw_bottom_page(self, page_buf, force=False):
        page_bytes = self._normalize_bottom_page(page_buf)
        if not force and page_bytes == self._last_bottom_page:
            return False

        if hasattr(self.disp_out, "graphics"):
            self.disp_out.graphics(
                page_bytes,
                page=self.BOTTOM_PAGE,
                column=0,
                width=self.PAGE_WIDTH,
                pages=1,
            )
            self._last_bottom_page = page_bytes
            return True

        self.disp_out.set_page_address(self.BOTTOM_PAGE)
        self.disp_out.set_column_address(0)
        for value in page_bytes:
            self.disp_out.write_data(value)
        self._last_bottom_page = page_bytes
        return True

    def clear_bottom_page(self, force=False):
        return self.draw_bottom_page(bytearray(self.PAGE_WIDTH), force=force)

    def draw_state(self, state, force=False):
        state = str(state or "")
        if state == "":
            self.clear_bottom_page(force=force)
            return

        page_buf = bytearray(self.PAGE_WIDTH)
        buf_x = 0
        invert = (
            "default" in state
            or "alpha" in state
            or "beta" in state
            or "ALPHA" in state
        )
        for char in state:
            if invert:
                char_bytes = self.chrs.invert_letter(char)
                cursor_line = 0b11111111
            else:
                char_bytes = self.chrs.Chr2bytes(char)
                cursor_line = 0b00000000
            for byte in char_bytes:
                if buf_x >= self.PAGE_WIDTH:
                    break
                page_buf[buf_x] = byte
                buf_x += 1
            if buf_x >= self.PAGE_WIDTH:
                break
            page_buf[buf_x] = cursor_line
            buf_x += 1

        self.draw_bottom_page(page_buf, force=force)

    def current_state(self):
        if self.state in ("a", "A", "b") or self.is_visible():
            return self._label()
        return ""
