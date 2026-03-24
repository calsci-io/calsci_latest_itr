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
    from machine import ADC, Pin  # type: ignore
except ImportError:
    from mocking import machine  # type: ignore
    from mocking.machine import ADC, Pin  # type: ignore

try:
    import _thread  # type: ignore
except Exception:
    _thread = None

from apps.installed_apps._mono_ui import MonoCanvas, clip_text_px, text_width
from data_modules.object_handler import nav, keypad_state_manager, keypad_state_manager_reset, typer
from process_modules import boot_up_data_update


_BATTERY_MIN_V = 3.5
_BATTERY_MAX_V = 4.2
_REFRESH_MS = 800
_SLEEP_SLICE_MS = 120

adc_pin = Pin(6)
adc = ADC(adc_pin)
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

charge_pin = Pin(4, Pin.IN, Pin.PULL_DOWN)


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


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _read_battery_voltage(samples=10):
    total = 0
    sample_count = max(1, int(samples))
    for _ in range(sample_count):
        total += adc.read()
    raw_value = total / sample_count
    cell_voltage = (raw_value / 4095.0) * 3.3
    return round((2 * cell_voltage) + 0.220, 3)


def _battery_percent(voltage):
    span = _BATTERY_MAX_V - _BATTERY_MIN_V
    if span <= 0:
        return 0
    level = int(round(((float(voltage) - _BATTERY_MIN_V) * 100) / span))
    return int(_clamp(level, 0, 100))


def _battery_label(percent):
    if percent <= 10:
        return "EMPTY"
    if percent <= 25:
        return "LOW"
    if percent <= 55:
        return "MID"
    if percent <= 85:
        return "GOOD"
    return "FULL"


def _power_label(charging):
    return "BAT" if charging else "CHG"


class _BatteryDashboard:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.running = False
        self.voltage = None
        self.percent = 0
        self.charging = False
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
        self.refresh(force=True)
        if _thread is not None:
            try:
                _thread.start_new_thread(self._refresh_worker, ())
            except Exception:
                self._refresh_worker_enabled = False

    def stop(self):
        self.running = False
        _sleep_ms(_SLEEP_SLICE_MS)

    def _measure(self):
        new_voltage = _read_battery_voltage()
        if self.voltage is None:
            self.voltage = new_voltage
        else:
            self.voltage = round((self.voltage * 3 + new_voltage) / 4, 3)
        self.charging = bool(charge_pin.value())
        self.percent = _battery_percent(self.voltage)

    def refresh(self, force=False):
        now_ms = _ticks_ms()
        if (not force) and _ticks_diff(now_ms, self._render_at_ms) < _REFRESH_MS:
            return
        self._measure()
        self._render_at_ms = now_ms
        self.render()

    def _refresh_worker(self):
        while self.running:
            self.refresh(force=False)
            _sleep_ms(_SLEEP_SLICE_MS)

    def _draw_title(self):
        self.canvas.fill_rect(0, 0, 128, 10, 1)
        self.canvas.draw_text_center("Battery Status", 1, color=0)

    def _draw_battery_frame(self, x, y, w, h, terminal_w, terminal_h):
        right = x + w - 1
        bottom = y + h - 1
        terminal_x = x + w
        terminal_y = y + ((h - terminal_h) // 2)

        self.canvas.rect(x, y, w, h, 1)
        self.canvas.rect(x + 1, y + 1, w - 2, h - 2, 1)

        # Trim a few inner-corner pixels so the outline looks softer on the mono LCD.
        self.canvas.pixel(x + 1, y + 1, 0)
        self.canvas.pixel(right - 1, y + 1, 0)
        self.canvas.pixel(x + 1, bottom - 1, 0)
        self.canvas.pixel(right - 1, bottom - 1, 0)

        self.canvas.rect(terminal_x, terminal_y, terminal_w, terminal_h, 1)
        self.canvas.fill_rect(terminal_x + 1, terminal_y + 2, max(1, terminal_w - 2), max(1, terminal_h - 4), 1)

    def _draw_battery_cells(self, x, y, w, h):
        cell_count = 4
        cell_gap = 2
        cell_inner_h = max(1, h - 2)
        usable_w = max(0, w - ((cell_count - 1) * cell_gap))
        cell_w = max(8, usable_w // cell_count)
        total_cells_w = cell_count * cell_w + (cell_count - 1) * cell_gap
        start_x = x + max(0, (w - total_cells_w) // 2)

        for idx in range(cell_count):
            cell_x = start_x + idx * (cell_w + cell_gap)
            self.canvas.rect(cell_x, y, cell_w, h, 1)

            inner_fill_w = max(1, cell_w - 2)
            fill_ratio = _clamp((self.percent / 25.0) - idx, 0.0, 1.0)
            fill_w = int(round(inner_fill_w * fill_ratio))
            if fill_w > 0:
                self.canvas.fill_rect(cell_x + 1, y + 1, fill_w, cell_inner_h, 1)

    def _draw_battery_body(self):
        x = 7
        y = 15
        w = 64
        h = 24
        terminal_w = 4
        terminal_h = 10
        cell_pad_x = 4
        cell_pad_y = 5

        self._draw_battery_frame(x, y, w, h, terminal_w, terminal_h)
        self._draw_battery_cells(
            x + cell_pad_x,
            y + cell_pad_y,
            w - (2 * cell_pad_x),
            h - (2 * cell_pad_y),
        )

        percent_text = "{}%".format(self.percent)
        self.canvas.draw_text_in_rect(percent_text, x, y + h + 3, w + terminal_w, 9, color=1, align="center")

    def _draw_info_panel(self):
        x = 79
        y = 15
        w = 44
        h = 29
        voltage_text = "{:.3f}V".format(self.voltage if self.voltage is not None else 0)
        status_text = _battery_label(self.percent)
        power_text = _power_label(self.charging)

        self.canvas.rect(x, y, w, h, 1)
        self.canvas.fill_rect(x + 1, y + 1, w - 2, 9, 1)
        self.canvas.draw_text_in_rect(status_text, x + 1, y + 1, w - 2, 9, color=0, align="center")

        self.canvas.draw_text_in_rect(voltage_text, x + 2, y + 11, w - 4, 9, color=1, align="center")
        self.canvas.fill_rect(x + 8, y + 19, w - 16, 9, 1)
        self.canvas.draw_text_in_rect(power_text, x + 8, y + 20, w - 16, 9, color=0, align="center")

    def _draw_range_bar(self):
        gauge_x = 18
        gauge_y = 49
        gauge_w = 92
        gauge_h = 5
        indicator_x = gauge_x + int((gauge_w - 1) * self.percent / 100)

        self.canvas.rect(gauge_x, gauge_y, gauge_w, gauge_h, 1)
        if self.percent > 0:
            self.canvas.fill_rect(gauge_x + 1, gauge_y + 1, max(1, int((gauge_w - 2) * self.percent / 100)), gauge_h - 2, 1)

        marker_x = int(_clamp(indicator_x, gauge_x + 1, gauge_x + gauge_w - 2))
        self.canvas.vline(marker_x, gauge_y - 1, gauge_h + 2, 1)

    def _draw_footer(self):
        state_text = str(nav.current_state() or "").strip()
        if state_text:
            self.canvas.fill_rect(0, 63 - 7, 128, 8, 1)
            self.canvas.draw_text_center(state_text, 56, color=0)
            return

        self.canvas.draw_text("3.5V", 4, 56, color=1)
        self.canvas.draw_text_right("4.2V", 124, 56, color=1)

    def render(self):
        self._lock()
        try:
            self.canvas.clear()
            self._draw_title()
            self._draw_battery_body()
            self._draw_info_panel()
            self._draw_range_bar()
            self._draw_footer()
            self.canvas.flush()
        finally:
            self._unlock()


def battery_status():
    display.clear_display()
    keypad_state_manager_reset()

    dashboard = _BatteryDashboard()
    dashboard.start()

    try:
        while True:
            inp = typer.start_typing()

            if inp in ("alpha", "beta", "caps"):
                keypad_state_manager(x=inp)
                dashboard.render()
                continue

            if inp in ("ok", "exe", "nav_u", "nav_d", "nav_l", "nav_r"):
                dashboard.refresh(force=True)
                continue

            if inp == "off":
                boot_up_data_update.main()
                machine.deepsleep()
    finally:
        dashboard.stop()
        keypad_state_manager_reset()
