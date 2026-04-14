import st7565 as display_driver

try:
    import tools

    if hasattr(display_driver, "graphics") and not hasattr(display_driver.graphics, "pixels_changed"):
        display_driver.graphics = tools.refresh(display_driver.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

try:
    import machine  # type: ignore
except ImportError:
    from mocking import machine  # type: ignore

from apps.installed_apps._mono_ui import MonoCanvas, clip_text_px
from data_modules.object_handler import (
    app,
    display,
    keypad_state_manager,
    keypad_state_manager_reset,
    typer,
)
from process_modules import boot_up_data_update


_MAX_SIGNAL = 4
_SCROLL_W = 4

_STATUS_BOX = (2, 11, 124, 18)
_HOME_ACTION_BOX = (2, 33, 124, 26)
_FULL_LIST_BOX = (2, 11, 124, 44)

_HOME_VISIBLE_ROWS = 2
_FULL_VISIBLE_ROWS = 3
_HOME_ROW_H = 10
_FULL_ROW_H = 13
_ROW_GAP = 1

_DUMMY_SCAN_NETWORKS = [
    {"ssid": "CalSci Lab", "signal": 4},
    {"ssid": "Home WiFi", "signal": 3},
    {"ssid": "Cafe Corner", "signal": 2},
    {"ssid": "Office Net", "signal": 4},
    {"ssid": "Guest Zone", "signal": 1},
    {"ssid": "Workshop AP", "signal": 2},
]

_DUMMY_SAVED_NETWORKS = [
    {"ssid": "CalSci Lab", "signal": 4},
    {"ssid": "Home WiFi", "signal": 3},
    {"ssid": "Office Net", "signal": 2},
]


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


class _WifiCenterDemo:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.view = "home"
        self.home_cursor = 0
        self.scan_cursor = 0
        self.saved_cursor = 0
        self.home_scroll = 0
        self.scan_scroll = 0
        self.saved_scroll = 0
        self._swallow_back_once = False

        self.wifi_on = True
        self.auto_connect = True
        self.connected_ssid = "CalSci Lab"
        self.connected_signal = 4
        self.scan_networks = [dict(item) for item in _DUMMY_SCAN_NETWORKS]
        self.saved_networks = [dict(item) for item in _DUMMY_SAVED_NETWORKS]

    def _is_connected(self):
        return bool(self.wifi_on and str(self.connected_ssid).strip())

    def _status_label(self):
        return "Connected" if self._is_connected() else "Disconnected"

    def _title_for_view(self):
        if self.view == "scan":
            return "Scan"
        if self.view == "saved":
            return "Saved Networks"
        return "Wi-Fi"

    def _draw_title(self, title):
        self.canvas.draw_text_center(title, 1, color=1)

    def _draw_box(self, x, y, width, height):
        self.canvas.rect(x, y, width, height, 1)

    def _draw_scrollbar(self, x, y, width, height, item_count, top_index, visible_rows):
        track_x = int(x) + int(width) - _SCROLL_W - 1
        track_y = int(y) + 2
        track_h = int(height) - 4

        self.canvas.rect(track_x, track_y, _SCROLL_W, track_h, 1)

        if item_count <= visible_rows:
            thumb_h = max(1, track_h - 2)
            thumb_y = track_y + 1
        else:
            thumb_h = max(6, ((track_h - 2) * visible_rows) // item_count)
            max_top = max(1, item_count - visible_rows)
            thumb_range = max(0, (track_h - 2) - thumb_h)
            thumb_y = track_y + 1 + (top_index * thumb_range // max_top)

        self.canvas.fill_rect(track_x + 1, thumb_y, max(1, _SCROLL_W - 2), thumb_h, 1)

    def _draw_signal_bars(self, right_x, top_y, strength, color=1):
        strength = int(_clamp(int(strength), 0, _MAX_SIGNAL))
        bar_widths = [4, 7, 10, 13]  # bottom -> top
        bar_step = 2
        bar_height = 1
        top_offset = 1
        for level_index, width in enumerate(bar_widths):
            y = int(top_y) + top_offset + ((_MAX_SIGNAL - 1 - level_index) * bar_step)
            x = int(right_x) - int(width)
            if level_index < strength:
                self.canvas.fill_rect(x, y, width, bar_height, color)
            else:
                self.canvas.hline(x, y, width, color)

    def _draw_toggle(self, x, y, enabled, fg=1, bg=0):
        x = int(x)
        y = int(y)
        width = 24
        height = 8
        knob_w = 9
        knob_x = x + width - knob_w - 1 if enabled else x + 1

        self.canvas.rect(x, y, width, height, fg)
        self.canvas.pixel(x + 1, y + 1, bg)
        self.canvas.pixel(x + width - 2, y + 1, bg)
        self.canvas.pixel(x + 1, y + height - 2, bg)
        self.canvas.pixel(x + width - 2, y + height - 2, bg)

        self.canvas.fill_rect(knob_x, y + 1, knob_w, height - 2, fg)
        self.canvas.pixel(knob_x, y + 1, bg)
        self.canvas.pixel(knob_x + knob_w - 1, y + 1, bg)
        self.canvas.pixel(knob_x, y + height - 2, bg)
        self.canvas.pixel(knob_x + knob_w - 1, y + height - 2, bg)

    def _action_items(self):
        return [
            {"kind": "toggle", "key": "wifi", "label": "Wi-Fi", "value": self.wifi_on},
            {"kind": "action", "key": "scan", "label": "Scan"},
            {"kind": "action", "key": "saved", "label": "Saved Networks"},
            {"kind": "toggle", "key": "auto_connect", "label": "Auto-connect", "value": self.auto_connect},
        ]

    def _network_items(self, source):
        items = []
        for row in source:
            ssid = str(row.get("ssid", "")).strip()
            if not ssid:
                continue
            prefix = "* " if self._is_connected() and ssid == self.connected_ssid else ""
            items.append(
                {
                    "kind": "network",
                    "label": prefix + ssid,
                    "ssid": ssid,
                    "signal": int(_clamp(int(row.get("signal", 0)), 0, _MAX_SIGNAL)),
                }
            )
        return items

    def _visible_window(self, item_count, cursor, scroll, visible_rows):
        if item_count <= visible_rows:
            return 0
        max_top = item_count - visible_rows
        scroll = int(_clamp(scroll, 0, max_top))
        if cursor < scroll:
            scroll = cursor
        elif cursor >= scroll + visible_rows:
            scroll = cursor - visible_rows + 1
        return int(_clamp(scroll, 0, max_top))

    def _move_cursor(self, current, total, delta):
        if total <= 0:
            return 0
        return (int(current) + int(delta)) % int(total)

    def _draw_status_box(self):
        x, y, width, height = _STATUS_BOX
        self._draw_box(x, y, width, height)

        self.canvas.draw_text("Status:", x + 4, y + 3, color=1)
        self.canvas.draw_text(self._status_label(), x + 46, y + 3, color=1)

        if self._is_connected():
            self.canvas.draw_text(clip_text_px(self.connected_ssid, 95), x + 4, y + 11, color=1)
            self._draw_signal_bars(x + width - 6, y + 9, self.connected_signal, color=1)
        else:
            self.canvas.draw_text("SSID: -", x + 4, y + 11, color=1)

    def _draw_row_item(self, item, row_x, row_y, row_w, row_h, text_color, row_fill):
        kind = str(item.get("kind", "action"))
        label = str(item.get("label", ""))

        if kind == "toggle":
            reserved = 49
            self.canvas.draw_text_in_rect(
                label,
                row_x + 2,
                row_y + 1,
                row_w - reserved,
                row_h - 2,
                color=text_color,
                align="left",
            )
            toggle_state = bool(item.get("value"))
            self.canvas.draw_text("ON" if toggle_state else "OFF", row_x + row_w - 42, row_y + 2, color=text_color)
            self._draw_toggle(row_x + row_w - 25, row_y + 1, toggle_state, fg=text_color, bg=row_fill)
            return

        if kind == "network":
            reserved = 18
            self.canvas.draw_text_in_rect(
                clip_text_px(label, row_w - reserved - 4),
                row_x + 2,
                row_y + 1,
                row_w - reserved - 4,
                row_h - 2,
                color=text_color,
                align="left",
            )
            signal_top = row_y + max(0, (row_h - 8) // 2)
            self._draw_signal_bars(row_x + row_w - 4, signal_top, item.get("signal", 0), color=text_color)
            return

        self.canvas.draw_text_in_rect(
            label,
            row_x + 2,
            row_y + 1,
            row_w - 4,
            row_h - 2,
            color=text_color,
            align="left",
        )

    def _draw_list(self, items, cursor, scroll, box, visible_rows, row_h):
        box_x, box_y, box_w, box_h = box
        self._draw_box(box_x, box_y, box_w, box_h)

        total = len(items)
        if total <= 0:
            self.canvas.draw_text_center("No Networks", box_y + max(0, (box_h - 8) // 2), color=1)
            return 0

        top_index = self._visible_window(total, cursor, scroll, visible_rows)
        row_x = box_x + 2
        row_y = box_y + 2
        row_w = box_w - _SCROLL_W - 5

        for slot in range(visible_rows):
            item_index = top_index + slot
            if item_index >= total:
                break

            y = row_y + slot * (row_h + _ROW_GAP)
            selected = item_index == cursor
            row_fill = 1 if selected else 0
            text_color = 0 if selected else 1

            self.canvas.fill_rect(row_x, y, row_w, row_h, row_fill)
            self.canvas.rect(row_x, y, row_w, row_h, 1)
            self._draw_row_item(items[item_index], row_x, y, row_w, row_h, text_color, row_fill)

        self._draw_scrollbar(box_x, box_y, box_w, box_h, total, top_index, visible_rows)
        return top_index

    def _draw_home(self):
        self._draw_title("Wi-Fi")
        self._draw_status_box()
        action_items = self._action_items()
        self.home_scroll = self._draw_list(
            action_items,
            self.home_cursor,
            self.home_scroll,
            _HOME_ACTION_BOX,
            _HOME_VISIBLE_ROWS,
            _HOME_ROW_H,
        )

    def _draw_network_view(self, title, items, cursor, scroll):
        self._draw_title(title)
        return self._draw_list(
            items,
            cursor,
            scroll,
            _FULL_LIST_BOX,
            _FULL_VISIBLE_ROWS,
            _FULL_ROW_H,
        )

    def render(self):
        self.canvas.clear()
        if self.view == "home":
            self._draw_home()
        elif self.view == "scan":
            self.scan_scroll = self._draw_network_view("Scan", self._network_items(self.scan_networks), self.scan_cursor, self.scan_scroll)
        else:
            self.saved_scroll = self._draw_network_view(
                "Saved Networks",
                self._network_items(self.saved_networks),
                self.saved_cursor,
                self.saved_scroll,
            )
        self.canvas.flush()

    def _connect_to(self, item):
        self.wifi_on = True
        self.connected_ssid = str(item.get("ssid", "")).strip()
        self.connected_signal = int(_clamp(int(item.get("signal", 0)), 0, _MAX_SIGNAL))
        self.view = "home"

    def _toggle_focused_setting(self, enabled=None):
        action_items = self._action_items()
        if not action_items:
            return
        current = action_items[self.home_cursor]
        key = current.get("key")
        if key == "wifi":
            new_state = (not self.wifi_on) if enabled is None else bool(enabled)
            self.wifi_on = new_state
            return
        if key == "auto_connect":
            new_state = (not self.auto_connect) if enabled is None else bool(enabled)
            self.auto_connect = new_state

    def _open_focused_home_item(self):
        action_items = self._action_items()
        if not action_items:
            return
        key = str(action_items[self.home_cursor].get("key", ""))
        if key in ("wifi", "auto_connect"):
            self._toggle_focused_setting()
        elif key == "scan":
            self.view = "scan"
        elif key == "saved":
            self.view = "saved"

    def _swallow_repeated_back_if_needed(self, inp):
        if inp == "back" and self._swallow_back_once:
            self._swallow_back_once = False
            return True
        if inp != "back":
            self._swallow_back_once = False
        return False

    def handle_input(self, inp):
        if inp in ("alpha", "beta"):
            keypad_state_manager(x=inp)
            return True
        if inp == "caps":
            keypad_state_manager(x="A")
            return True

        if inp == "off":
            boot_up_data_update.main()
            machine.deepsleep()
            return True

        if self._swallow_repeated_back_if_needed(inp):
            return True

        if inp == "back":
            if self.view == "home":
                app.set_app_name("settings")
                app.set_group_name("root")
                return False
            self.view = "home"
            self._swallow_back_once = True
            return True

        if self.view == "home":
            action_items = self._action_items()
            if inp == "nav_u":
                self.home_cursor = self._move_cursor(self.home_cursor, len(action_items), -1)
                return True
            if inp == "nav_d":
                self.home_cursor = self._move_cursor(self.home_cursor, len(action_items), 1)
                return True
            if inp == "nav_l":
                self._toggle_focused_setting(False)
                return True
            if inp == "nav_r":
                self._toggle_focused_setting(True)
                return True
            if inp in ("ok", "exe"):
                self._open_focused_home_item()
                return True
            return True

        if self.view == "scan":
            network_items = self._network_items(self.scan_networks)
            if inp == "nav_u":
                self.scan_cursor = self._move_cursor(self.scan_cursor, len(network_items), -1)
                return True
            if inp == "nav_d":
                self.scan_cursor = self._move_cursor(self.scan_cursor, len(network_items), 1)
                return True
            if inp in ("ok", "exe") and network_items:
                self._connect_to(network_items[self.scan_cursor])
                return True
            return True

        network_items = self._network_items(self.saved_networks)
        if inp == "nav_u":
            self.saved_cursor = self._move_cursor(self.saved_cursor, len(network_items), -1)
            return True
        if inp == "nav_d":
            self.saved_cursor = self._move_cursor(self.saved_cursor, len(network_items), 1)
            return True
        if inp in ("ok", "exe") and network_items:
            self._connect_to(network_items[self.saved_cursor])
            return True
        return True


def wifi_center(db={}):
    del db
    display.clear_display()
    keypad_state_manager_reset()

    dashboard = _WifiCenterDemo()
    dashboard.render()

    try:
        while True:
            inp = typer.start_typing()
            keep_running = dashboard.handle_input(inp)
            if not keep_running:
                break
            dashboard.render()
    finally:
        keypad_state_manager_reset()
