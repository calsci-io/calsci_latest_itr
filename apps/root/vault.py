import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

from apps.installed_apps._mono_ui import DISPLAY_HEIGHT, DISPLAY_WIDTH, MonoCanvas, clip_text_px
from apps.root.constant_vault import _read_key_with_local_back, run_constant_section
from apps.root.function_vault import run_function_section
from data_modules.object_handler import keypad_state_manager, keypad_state_manager_reset, nav
from process_modules.navigation import request_navigation_from_key
from process_modules.ui_context import set_active_view


HEADER_H = 11
FOOTER_H = 8
ROW_H = 10
LIST_TOP = HEADER_H + 2
LIST_BOTTOM = DISPLAY_HEIGHT - FOOTER_H - 2
VISIBLE_LIST_ROWS = max(1, (LIST_BOTTOM - LIST_TOP + 1) // ROW_H)
MENU_ITEMS = ("Constants", "Functions")


class _VaultApp:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.menu_index = 0
        self.status_message = "OK open"

    def _draw_nav_overlay(self):
        state = str(nav.current_state() or "")
        nav_overlay_visible = state != "" and nav.is_visible()
        nav.set_restore_callback(self._flush_bottom_page if nav_overlay_visible else None)
        if nav_overlay_visible:
            nav.draw_state(state)
        else:
            self._flush_bottom_page()

    def _flush_bottom_page(self):
        bottom_page = (DISPLAY_HEIGHT // 8) - 1
        start = bottom_page * DISPLAY_WIDTH
        end = start + DISPLAY_WIDTH
        nav.draw_bottom_page(memoryview(self.canvas.buf)[start:end])

    def _flush_screen(self):
        self.canvas.flush(page=0, pages=(DISPLAY_HEIGHT // 8) - 1)
        self._draw_nav_overlay()

    def _draw_header(self, title):
        self.canvas.draw_text(clip_text_px(title, DISPLAY_WIDTH - 4), 2, 1, 1)
        self.canvas.hline(0, HEADER_H - 1, DISPLAY_WIDTH, 1)

    def _draw_footer(self, text_value):
        self.canvas.hline(0, DISPLAY_HEIGHT - FOOTER_H - 1, DISPLAY_WIDTH, 1)
        self.canvas.draw_text(clip_text_px(text_value, DISPLAY_WIDTH - 2), 1, DISPLAY_HEIGHT - FOOTER_H + 1, 1)

    def _list_window(self, selected_index, item_count):
        if item_count <= VISIBLE_LIST_ROWS:
            return 0
        top_index = max(0, int(selected_index) - VISIBLE_LIST_ROWS + 1)
        max_top = max(0, item_count - VISIBLE_LIST_ROWS)
        return min(top_index, max_top)

    def _draw_scrollbar(self, top_index, item_count):
        if item_count <= VISIBLE_LIST_ROWS:
            return
        track_x = DISPLAY_WIDTH - 2
        track_y = LIST_TOP
        track_h = max(8, LIST_BOTTOM - LIST_TOP + 1)
        self.canvas.vline(track_x, track_y, track_h, 1)
        thumb_h = max(8, (track_h * VISIBLE_LIST_ROWS) // max(1, item_count))
        max_top = max(1, item_count - VISIBLE_LIST_ROWS)
        thumb_range = max(0, track_h - thumb_h)
        thumb_y = track_y + (top_index * thumb_range // max_top)
        self.canvas.fill_rect(track_x - 1, thumb_y, 3, thumb_h, 1)

    def render(self):
        set_active_view("menu")
        self.canvas.clear(0)
        self._draw_header("Vault")

        top_index = self._list_window(self.menu_index, len(MENU_ITEMS))
        bottom_index = min(len(MENU_ITEMS), top_index + VISIBLE_LIST_ROWS)
        y = LIST_TOP

        for row_index in range(top_index, bottom_index):
            selected = row_index == self.menu_index
            label = MENU_ITEMS[row_index]
            if selected:
                self.canvas.fill_rect(1, y - 1, DISPLAY_WIDTH - 5, ROW_H, 1)
            self.canvas.draw_text(
                clip_text_px(label, DISPLAY_WIDTH - 10),
                3,
                y,
                0 if selected else 1,
            )
            y += ROW_H

        self._draw_scrollbar(top_index, len(MENU_ITEMS))
        self._draw_footer(self.status_message or "OK open")
        self._flush_screen()

    def handle_token(self, token):
        if token == "back":
            request_navigation_from_key("back")
        if token == "nav_u":
            self.menu_index = (self.menu_index - 1) % len(MENU_ITEMS)
            self.status_message = "OK open"
            return
        if token == "nav_d":
            self.menu_index = (self.menu_index + 1) % len(MENU_ITEMS)
            self.status_message = "OK open"
            return
        if token in ("alpha", "beta"):
            keypad_state_manager(x=token)
            return
        if token == "caps":
            keypad_state_manager(x="A")
            return
        if token != "" and token not in ("ok", "exe"):
            return
        if token == "":
            return

        if self.menu_index == 0:
            run_constant_section(menu_title="Constants", return_to_parent=True)
        else:
            run_function_section(menu_title="Functions", return_to_parent=True)

        keypad_state_manager_reset()
        display.clear_display()
        self.status_message = "OK open"

    def run(self):
        keypad_state_manager_reset()
        display.clear_display()
        self.render()
        try:
            while True:
                token = _read_key_with_local_back()

                if token == "home":
                    nav.set_restore_callback(None)
                    request_navigation_from_key("home")
                if token == "settings":
                    nav.set_restore_callback(None)
                    request_navigation_from_key("settings")
                if token == "off":
                    nav.set_restore_callback(None)
                    return

                self.handle_token(token)
                self.render()
        finally:
            nav.set_restore_callback(None)


def vault():
    _VaultApp().run()
