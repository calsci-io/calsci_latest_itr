import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

_menu_state_cache = {}


def _current_menu_target():
    try:
        from data_modules.object_handler import current_app

        app_name = str(current_app[0] or "")
        group_name = str(current_app[1] or "")
        if not app_name or not group_name:
            return None
        return (app_name, group_name)
    except Exception:
        return None


def _should_restore_current_menu():
    target = _current_menu_target()
    if target is None:
        return False
    try:
        from process_modules.navigation import consume_menu_restore_target

        return bool(consume_menu_restore_target(target[0], target[1]))
    except Exception:
        return False


def _menu_signature(menu_list):
    signature = []
    for item in menu_list or []:
        signature.append(str(item))
    return tuple(signature)


class Menu:
    def __init__(
        self,
        rows=3,
        cols=21,
        menu_list=None,
        menu_cursor=0,
        menu_display_position=0,
    ):
        self.rows = rows
        self.cols = cols
        self.menu_list = menu_list or ["label_0", "label_1", "label_2"]
        self.menu_cursor = menu_cursor
        self.menu_display_position = menu_display_position
        self.menu_display_size = min(self.rows, len(self.menu_list))
        self.display_buffer = self.menu_list[
            self.menu_display_position : self.menu_display_position
            + self.menu_display_size
        ]
        self.display_cursor = self.menu_cursor - self.menu_display_position
        self.refresh_rows = (0, self.menu_display_size)

    def _save_state(self):
        target = _current_menu_target()
        if target is None:
            return

        items = list(self.menu_list or [])
        selected_item = None
        if items and 0 <= self.menu_cursor < len(items):
            selected_item = str(items[self.menu_cursor])

        _menu_state_cache[target] = {
            "signature": _menu_signature(items),
            "cursor": int(self.menu_cursor),
            "display_position": int(self.menu_display_position),
            "selected_item": selected_item,
        }

    def _restore_state(self):
        target = _current_menu_target()
        if target is None:
            return False

        saved = _menu_state_cache.get(target)
        if not isinstance(saved, dict):
            return False

        items = list(self.menu_list or [])
        item_count = len(items)
        if item_count <= 0:
            self.menu_cursor = 0
            self.menu_display_position = 0
            return True

        current_signature = _menu_signature(items)
        saved_signature = saved.get("signature")
        saved_cursor = int(saved.get("cursor", 0) or 0)
        saved_display_position = int(saved.get("display_position", 0) or 0)
        selected_item = saved.get("selected_item")

        if saved_signature == current_signature:
            self.menu_cursor = saved_cursor
            max_display = max(0, item_count - self.menu_display_size)
            self.menu_display_position = min(max(0, saved_display_position), max_display)
        elif selected_item is not None and str(selected_item) in current_signature:
            self.menu_cursor = current_signature.index(str(selected_item))
            max_display = max(0, item_count - self.menu_display_size)
            min_display = max(0, self.menu_cursor - self.menu_display_size + 1)
            max_keep = min(self.menu_cursor, max_display)
            self.menu_display_position = min(max(0, saved_display_position), max_display)
            if self.menu_display_position < min_display:
                self.menu_display_position = min_display
            elif self.menu_display_position > max_keep:
                self.menu_display_position = max_keep
        else:
            return False

        self.menu_cursor = min(max(0, self.menu_cursor), item_count - 1)
        if self.menu_cursor < self.menu_display_position:
            self.menu_display_position = self.menu_cursor
        elif self.menu_cursor >= self.menu_display_position + self.menu_display_size:
            self.menu_display_position = self.menu_cursor - self.menu_display_size + 1
        return True

    def update_buffer(self, text):
        if text == "nav_d":
            self.menu_cursor += 1
            if self.menu_cursor == len(self.menu_list):  # Wrap to top if at the bottom
                self.menu_cursor = 0
                self.menu_display_position = 0
                self.refresh_rows = (0, self.menu_display_size)
            elif self.menu_cursor - self.menu_display_position == self.menu_display_size:
                self.menu_display_position += 1
                self.refresh_rows = (0, self.menu_display_size)
            else:
                self.refresh_rows = (
                    self.menu_cursor - 1 - self.menu_display_position,
                    self.menu_cursor - self.menu_display_position + 1,
                )
        elif text == "nav_u":
            self.menu_cursor -= 1
            if self.menu_cursor < 0:  # Wrap to bottom if at the top
                self.menu_cursor = len(self.menu_list) - 1
                self.menu_display_position = max(0, len(self.menu_list) - self.menu_display_size)
                self.refresh_rows = (0, self.menu_display_size)
            elif self.menu_cursor < self.menu_display_position:
                self.menu_display_position -= 1
                self.refresh_rows = (0, self.menu_display_size)
            else:
                self.refresh_rows = (
                    self.menu_cursor - self.menu_display_position,
                    self.menu_cursor - self.menu_display_position + 2,
                )

        self.display_buffer = self.menu_list[
            self.menu_display_position : self.menu_display_position
            + self.menu_display_size
        ]
        self.display_cursor = self.menu_cursor - self.menu_display_position
        self._save_state()
    
    def buffer(self):
        return self.display_buffer
    
    def cursor(self):
        return self.display_cursor
    
    def ref_ar(self):
        return self.refresh_rows
    
    def update(self, restore=None):
        self.menu_display_size = min(self.rows, len(self.menu_list))
        restored = False

        if restore is None:
            restore = _should_restore_current_menu()

        if restore:
            restored = self._restore_state()

        if not restored:
            self.menu_cursor = 0
            self.menu_display_position = 0

        self.display_buffer = self.menu_list[
            self.menu_display_position : self.menu_display_position
            + self.menu_display_size
        ]
        self.display_cursor = self.menu_cursor - self.menu_display_position
        self.refresh_rows = (0, self.menu_display_size)
        self._save_state()
