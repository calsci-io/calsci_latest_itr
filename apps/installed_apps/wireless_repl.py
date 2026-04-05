import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

try:
    import utime as time  # type: ignore
except ImportError:
    import time  # type: ignore

try:
    import machine  # type: ignore
except ImportError:
    from mocking import machine  # type: ignore

try:
    import _thread  # type: ignore
except Exception:
    _thread = None

from apps.installed_apps._mono_ui import MonoCanvas, clip_text_px
from data_modules.object_handler import keypad_state_manager, keypad_state_manager_reset, nav, typer
from process_modules import boot_up_data_update, wireless_transfer


_REFRESH_MS = 250
_SLEEP_SLICE_MS = 120


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def _ticks_ms():
    try:
        return time.ticks_ms()
    except Exception:
        return int(time.time() * 1000)


def _ticks_diff(now_ms, past_ms):
    try:
        return time.ticks_diff(now_ms, past_ms)
    except Exception:
        return now_ms - past_ms


class _WirelessDashboard:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.running = False
        self.last_snapshot = None
        self._render_at_ms = 0
        self._render_lock = None
        if _thread is not None:
            try:
                self._render_lock = _thread.allocate_lock()
            except Exception:
                self._render_lock = None

    def _lock(self):
        if self._render_lock is not None:
            try:
                self._render_lock.acquire()
            except Exception:
                pass

    def _unlock(self):
        if self._render_lock is not None:
            try:
                self._render_lock.release()
            except Exception:
                pass

    def start(self):
        self.running = True
        wireless_transfer.ensure_service(force_restart=False)
        self.refresh(force=True)
        if _thread is not None:
            try:
                _thread.start_new_thread(self._refresh_worker, ())
            except Exception:
                pass

    def stop(self):
        self.running = False
        _sleep_ms(_SLEEP_SLICE_MS)

    def refresh(self, force=False):
        now_ms = _ticks_ms()
        if (not force) and _ticks_diff(now_ms, self._render_at_ms) < _REFRESH_MS:
            return
        self._render_at_ms = now_ms
        self.last_snapshot = wireless_transfer.snapshot()
        self.render()

    def _refresh_worker(self):
        while self.running:
            self.refresh(force=False)
            _sleep_ms(_SLEEP_SLICE_MS)

    def _status_badge(self, snapshot):
        state = str(snapshot.get("state", "") or "").upper()
        if not state:
            state = "IDLE"
        if len(state) > 6:
            state = state[:6]
        return state

    def _draw_header(self, snapshot):
        self.canvas.fill_rect(0, 0, 128, 10, 1)
        self.canvas.draw_text("Wireless REPL", 2, 1, color=0)
        badge = self._status_badge(snapshot)
        badge_w = min(40, (len(badge) * 6) + 6)
        badge_x = 128 - badge_w - 2
        self.canvas.fill_rect(badge_x, 1, badge_w, 8, 0)
        self.canvas.rect(badge_x, 1, badge_w, 8, 0)
        self.canvas.draw_text_in_rect(badge, badge_x + 2, 1, badge_w - 4, 8, color=1, align="center")

    def _draw_idle_body(self, snapshot):
        wifi_ssid = str(snapshot.get("wifi_ssid", "") or "")
        ip = str(snapshot.get("ip", "") or "")
        password = str(snapshot.get("password", "") or "")
        webrepl_port = int(snapshot.get("webrepl_port", 8266) or 8266)
        status_port = int(snapshot.get("status_port", 8267) or 8267)
        message = str(snapshot.get("message", "") or "")

        line1 = "WiFi: " + (wifi_ssid if wifi_ssid else "not connected")
        line2 = "IP: " + (ip if ip else "-")
        line3 = "REPL:{}  UPD:{}".format(webrepl_port, status_port)
        line4 = "PWD: " + (password if password else "-")
        line5 = clip_text_px(message if message else "Use desktop WiFi mode", 124)

        self.canvas.draw_text(line1, 2, 14, color=1, max_width=124)
        self.canvas.draw_text(line2, 2, 23, color=1, max_width=124)
        self.canvas.draw_text(line3, 2, 32, color=1, max_width=124)
        self.canvas.draw_text(line4, 2, 41, color=1, max_width=124)
        self.canvas.draw_text(line5, 2, 48, color=1, max_width=124)

    def _draw_transfer_body(self, snapshot):
        current_file = str(snapshot.get("current_file_name", "") or snapshot.get("current_file", "") or "-")
        message = str(snapshot.get("message", "") or "")
        files_done = int(snapshot.get("files_done", 0) or 0)
        files_remaining = int(snapshot.get("files_remaining", 0) or 0)
        total_files = int(snapshot.get("total_files", 0) or 0)
        percent = float(snapshot.get("percent", 0.0) or 0.0)
        remaining_percent = float(snapshot.get("remaining_percent", 100.0) or 100.0)
        ip = str(snapshot.get("ip", "") or "")

        line1 = clip_text_px(message if message else "Transfer active", 124)
        line2 = "File: " + clip_text_px(current_file, 94)
        line3 = "Done {}  Left {}".format(files_done, files_remaining)
        if total_files > 0:
            line3 = "{}/{} files  Left {}".format(files_done, total_files, files_remaining)
        line4 = "Sent {:>3.0f}%  Left {:>3.0f}%".format(percent, remaining_percent)
        line5 = "IP: " + (ip if ip else "-")

        self.canvas.draw_text(line1, 2, 14, color=1, max_width=124)
        self.canvas.draw_text(line2, 2, 23, color=1, max_width=124)
        self.canvas.draw_text(line3, 2, 32, color=1, max_width=124)
        self.canvas.draw_text(line4, 2, 41, color=1, max_width=124)
        self.canvas.draw_text(line5, 2, 48, color=1, max_width=124)

        self._draw_progress_bar(percent)

    def _draw_complete_body(self, snapshot):
        self._draw_transfer_body(snapshot)
        wait_ms = int(snapshot.get("reset_wait_ms", 0) or 0)
        if wait_ms > 0:
            seconds = float(wait_ms) / 1000.0
            label = "Reset in {:.1f}s".format(seconds)
        elif snapshot.get("auto_reset"):
            label = "Reset requested"
        else:
            label = "Upload complete"
        self.canvas.fill_rect(0, 56, 128, 8, 1)
        self.canvas.draw_text_center(label, 56, color=0)

    def _draw_progress_bar(self, percent):
        bar_x = 12
        bar_y = 57
        bar_w = 104
        bar_h = 5
        self.canvas.rect(bar_x, bar_y, bar_w, bar_h, 1)
        fill_w = int((max(0.0, min(100.0, float(percent))) / 100.0) * (bar_w - 2))
        if fill_w > 0:
            self.canvas.fill_rect(bar_x + 1, bar_y + 1, max(1, fill_w), bar_h - 2, 1)

    def _draw_error_body(self, snapshot):
        line1 = clip_text_px(str(snapshot.get("message", "") or "Wireless setup error"), 124)
        line2 = clip_text_px(str(snapshot.get("webrepl_error", "") or ""), 124)
        line3 = "WiFi: " + ("ON" if snapshot.get("wifi_connected") else "OFF")
        line4 = "IP: " + str(snapshot.get("ip", "") or "-")
        line5 = "OK refresh  EXE clear"
        self.canvas.draw_text(line1, 2, 14, color=1, max_width=124)
        self.canvas.draw_text(line2, 2, 23, color=1, max_width=124)
        self.canvas.draw_text(line3, 2, 32, color=1, max_width=124)
        self.canvas.draw_text(line4, 2, 41, color=1, max_width=124)
        self.canvas.draw_text(line5, 2, 48, color=1, max_width=124)

    def _draw_footer(self):
        state_text = str(nav.current_state() or "").strip()
        if state_text:
            self.canvas.fill_rect(0, 56, 128, 8, 1)
            self.canvas.draw_text_center(state_text, 56, color=0)
        return

    def render(self):
        snapshot = self.last_snapshot or wireless_transfer.snapshot()
        self._lock()
        try:
            self.canvas.clear()
            self._draw_header(snapshot)

            state = str(snapshot.get("state", "") or "")
            if state == "error":
                self._draw_error_body(snapshot)
            elif state == "uploading":
                self._draw_transfer_body(snapshot)
            elif state == "complete":
                self._draw_complete_body(snapshot)
            else:
                self._draw_idle_body(snapshot)
                self._draw_progress_bar(float(snapshot.get("percent", 0.0) or 0.0))

            if state != "complete":
                self._draw_footer()
            self.canvas.flush()
        finally:
            self._unlock()


def wireless_repl():
    display.clear_display()
    keypad_state_manager_reset()

    dashboard = _WirelessDashboard()
    dashboard.start()

    try:
        while True:
            inp = typer.start_typing()

            if inp in ("alpha", "beta", "caps"):
                keypad_state_manager(x=inp)
                dashboard.render()
                continue

            if inp in ("ok", "exe", "nav_u", "nav_d", "nav_l", "nav_r"):
                if inp == "ok":
                    wireless_transfer.ensure_service(force_restart=True)
                elif inp == "exe":
                    wireless_transfer.clear_transfer_state()
                dashboard.refresh(force=True)
                continue

            if inp == "off":
                boot_up_data_update.main()
                machine.deepsleep()
    finally:
        dashboard.stop()
        keypad_state_manager_reset()
