import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

try:
    import utime as time  # type: ignore
except Exception:
    import time  # type: ignore

try:
    from sleeping_features import swdt, test_deep_sleep_awake
except Exception:
    class _DummySwdt:
        def feed(self):
            return None

    swdt = _DummySwdt()

    def test_deep_sleep_awake():
        return None


from apps.installed_apps._mono_ui import (
    CHAR_ADVANCE,
    CHAR_HEIGHT,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    MonoCanvas,
    clip_text_px,
)
from apps.root import calculate as calculate_app
from apps.root.constant_store import (
    default_constant_exists,
    delete_user_constant,
    ensure_default_constants,
    get_constant,
    list_default_constants,
    list_user_constants,
    upsert_user_constant,
    user_constant_exists,
)
from apps.root.function_store import default_function_exists, user_function_exists
from data_modules.object_handler import (
    data_bucket,
    keyin,
    keymap,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)
from process_modules.keypad_modes import reset_mode, should_auto_reset_after_input, toggle_mode_lock
from process_modules.navigation import request_navigation_from_key
from process_modules.ui_context import set_active_view


VIEW_MENU = "menu"
VIEW_META = "meta"
VIEW_USER_LIST = "user_list"
VIEW_USER_ACTIONS = "user_actions"
VIEW_DEFAULT_LIST = "default_list"
VIEW_DEFAULT_DETAIL = "default_detail"
VIEW_EXPR = "expr"
VIEW_MESSAGE = "message"

MENU_ITEMS = ("Create New", "User Defined", "Default Constants")
ACTION_ITEMS = ("Edit", "Delete")

HEADER_H = 11
FOOTER_H = 8
ROW_H = 10
LIST_TOP = HEADER_H + 2
LIST_BOTTOM = DISPLAY_HEIGHT - FOOTER_H - 2
VISIBLE_LIST_ROWS = max(1, (LIST_BOTTOM - LIST_TOP + 1) // ROW_H)

FIELD_LABEL_W = 34
FIELD_X = FIELD_LABEL_W + 4
FIELD_W = DISPLAY_WIDTH - FIELD_X - 5
FIELD_INNER_W = FIELD_W - 4
FIELD_VISIBLE_CHARS = max(1, (FIELD_INNER_W + 1) // CHAR_ADVANCE)

POPUP_W = 98
POPUP_H = 36
POPUP_X = (DISPLAY_WIDTH - POPUP_W) // 2
POPUP_Y = (DISPLAY_HEIGHT - POPUP_H) // 2

CURSOR_BLINK_MS = 450
FUNCTIONS_RELOAD_BUCKET_KEY = "_calculate_functions_dirty"


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        return time.ticks_ms()
    try:
        return int(time.monotonic() * 1000)
    except Exception:
        return int(time.time() * 1000)


def _sleep_s(seconds):
    try:
        time.sleep(float(seconds))
    except Exception:
        pass


def _wrap_text(text_value, max_chars):
    text_value = str(text_value or "")
    max_chars = max(1, int(max_chars or 1))
    words = text_value.split()
    if not words:
        return [""]

    lines = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            if current:
                lines.append(current)
                current = ""
            start = 0
            while start < len(word):
                lines.append(word[start : start + max_chars])
                start += max_chars
            continue

        candidate = word if current == "" else current + " " + word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines or [""]


def _is_identifier(name):
    name = str(name or "").strip()
    if name == "":
        return False

    first = name[0]
    if not (("a" <= first <= "z") or ("A" <= first <= "Z") or first == "_"):
        return False

    for char in name[1:]:
        if not (
            ("a" <= char <= "z")
            or ("A" <= char <= "Z")
            or ("0" <= char <= "9")
            or char == "_"
        ):
            return False
    return True


def _identifier_token(token):
    token = str(token or "")
    if len(token) != 1:
        return None
    char = token[0]
    if (
        ("a" <= char <= "z")
        or ("A" <= char <= "Z")
        or ("0" <= char <= "9")
        or char == "_"
    ):
        return char
    return None


def _read_key_with_local_back(idle_callback=None):
    _sleep_s(max(0.2, float(typer.debounce_delay())))
    col, row = keyin.keypad_loop(idle_callback=idle_callback)
    token = keymap.key_out(col=int(col), row=int(row))
    swdt.feed()

    if token in ("off", "on"):
        test_deep_sleep_awake()
        return "off"

    if token == "lock":
        toggle_mode_lock(keymap=keymap, nav=nav)
        return ""

    if should_auto_reset_after_input(keymap=keymap, nav=nav, key_name=token):
        reset_mode(keymap=keymap, nav=nav)

    return token


class _ConstantVaultApp:
    def __init__(self, menu_title="Constants", return_to_parent=False):
        self.canvas = MonoCanvas()
        self._inline_canvas = MonoCanvas()
        self.menu_title = str(menu_title or "Constants")
        self.return_to_parent = bool(return_to_parent)
        self._should_exit = False
        self.view = VIEW_MENU
        self.menu_index = 0
        self.user_index = 0
        self.default_index = 0
        self.action_index = 0
        self.selected_user_name = ""
        self.selected_default_name = ""
        self.status_message = "OK open"

        self.meta_title = "Create New"
        self.meta_return_view = VIEW_MENU
        self.editing_original_name = ""
        self.meta_name = ""
        self.meta_name_cursor = 0
        self.meta_value = ""
        self.meta_value_state = None
        self.meta_field_index = 0
        self.meta_value_editing = False

        self.popup = None
        self.message_title = ""
        self.message_lines = []
        self.message_return_view = VIEW_MENU

        self.editor = None
        self.editor_name = ""
        self._calculate_save_restore = None

        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()

    def _reset_cursor_blink(self):
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()

    def _update_cursor_blink(self):
        now = _ticks_ms()
        elapsed = now - self._cursor_last_toggle
        if elapsed < CURSOR_BLINK_MS:
            return False
        toggles = max(1, elapsed // CURSOR_BLINK_MS)
        if toggles % 2:
            self._cursor_visible = not self._cursor_visible
        self._cursor_last_toggle += toggles * CURSOR_BLINK_MS
        return True

    def _idle_callback(self):
        if self.view == VIEW_META and self.meta_value_editing and self.editor is not None:
            return self.editor.idle

        if self.view == VIEW_EXPR and self.editor is not None:
            return self.editor.idle

        if self.view == VIEW_META:
            def _idle():
                if self._update_cursor_blink():
                    self.render()

            return _idle

        return None

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

    def _footer_text(self, default_text):
        if self.status_message:
            return clip_text_px(self.status_message, DISPLAY_WIDTH - 2)
        return clip_text_px(default_text, DISPLAY_WIDTH - 2)

    def _draw_header(self, title, subtitle=""):
        title = clip_text_px(title, DISPLAY_WIDTH - 4)
        self.canvas.draw_text(title, 2, 1, 1)
        self.canvas.hline(0, HEADER_H - 1, DISPLAY_WIDTH, 1)
        if subtitle:
            self.canvas.draw_text(clip_text_px(subtitle, DISPLAY_WIDTH - 4), 2, HEADER_H + 1, 1)

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

    def _draw_list(self, title, items, selected_index, footer_text):
        set_active_view("menu")
        self.canvas.clear(0)
        self._draw_header(title)

        rows = list(items or [])
        if not rows:
            rows = ["No items"]
            selected_index = 0

        selected_index = max(0, min(int(selected_index), len(rows) - 1))
        top_index = self._list_window(selected_index, len(rows))
        bottom_index = min(len(rows), top_index + VISIBLE_LIST_ROWS)

        y = LIST_TOP
        for row_index in range(top_index, bottom_index):
            label = str(rows[row_index] or "")
            selected = row_index == selected_index
            if selected:
                self.canvas.fill_rect(1, y - 1, DISPLAY_WIDTH - 5, ROW_H, 1)
            self.canvas.draw_text(
                clip_text_px(label, DISPLAY_WIDTH - 10),
                3,
                y,
                0 if selected else 1,
            )
            y += ROW_H

        self._draw_scrollbar(top_index, len(rows))
        self._draw_footer(footer_text)
        self._flush_screen()

    def _visible_field_slice(self, value, cursor):
        value = str(value or "")
        cursor = max(0, min(int(cursor), len(value)))
        start = 0
        if cursor > FIELD_VISIBLE_CHARS:
            start = cursor - FIELD_VISIBLE_CHARS
        max_start = max(0, len(value) - FIELD_VISIBLE_CHARS)
        start = min(start, max_start)
        if cursor < start:
            start = cursor
        visible = value[start : start + FIELD_VISIBLE_CHARS]
        return start, visible

    def _meta_rows(self):
        return (
            ("Name", self.meta_name),
            ("Value", self.meta_value),
        )

    def _meta_preview(self):
        name = self.meta_name.strip() or "const"
        value = self._current_meta_value().strip()
        if value == "":
            return "{} =".format(name)
        return "{} = {}".format(name, value)

    def _current_meta_value(self):
        if self.meta_value_editing and self.editor is not None:
            try:
                expression, ok = self.editor._slot_to_expression(self.editor.root)
                if ok:
                    return str(expression or "")
            except Exception:
                pass
        return str(self.meta_value or "")

    def _start_value_editing(self):
        if self.meta_value_editing:
            return
        self.meta_field_index = 1
        self._open_expression_editor()

    def _try_save_constant(self):
        valid, message = self._validate_meta()
        if not valid:
            self._set_message("Invalid Constant", message, return_view=VIEW_META)
            return

        proposed_name = self.meta_name.strip()
        if user_constant_exists(proposed_name, exclude_name=self.editing_original_name):
            self._activate_popup(
                "Name Exists",
                [
                    "User constant exists",
                    clip_text_px(proposed_name, POPUP_W - 6),
                ],
                "Cancel",
                "Replace",
                "replace_save",
            )
            return

        success, message = self._validate_expression_and_save()
        if success:
            self.editor = None
            return
        self._set_message("Invalid Constant", message, return_view=VIEW_META)

    def _inline_editor_bounds(self):
        frame_left = 2
        frame_top = LIST_TOP + (2 * ROW_H) + 1
        frame_right = DISPLAY_WIDTH - 4
        frame_bottom = DISPLAY_HEIGHT - FOOTER_H - 2
        return frame_left, frame_top, frame_right, frame_bottom

    def _draw_inline_editor_scrollbars(
        self,
        editor,
        frame_left,
        frame_top,
        frame_right,
        frame_bottom,
        view_left,
        view_right,
        content_top,
        content_bottom,
        max_scroll_x,
        max_scroll_y,
    ):
        visible_width = max(1, view_right - view_left + 1)
        visible_height = max(1, content_bottom - content_top + 1)

        if max_scroll_x > 0:
            h_track_x = frame_left + 1
            h_track_y = frame_bottom - 1
            h_track_w = max(1, frame_right - frame_left - 1)
            content_width = visible_width + max_scroll_x
            h_thumb_w = max(8, (h_track_w * visible_width) // max(1, content_width))
            h_thumb_w = min(h_track_w, h_thumb_w)
            h_thumb_range = max(0, h_track_w - h_thumb_w)
            h_thumb_x = h_track_x + (
                editor.scroll_x * h_thumb_range // max(1, max_scroll_x)
            )
            editor._fill_rect(h_thumb_x, h_track_y, h_thumb_w, 1)

        if max_scroll_y > 0:
            v_track_x = frame_right - 1
            v_track_y = frame_top + 1
            v_track_h = max(1, frame_bottom - frame_top - 1)
            content_height = visible_height + max_scroll_y
            v_thumb_h = max(8, (v_track_h * visible_height) // max(1, content_height))
            v_thumb_h = min(v_track_h, v_thumb_h)
            v_thumb_range = max(0, v_track_h - v_thumb_h)
            v_thumb_y = v_track_y + (
                editor.scroll_y * v_thumb_range // max(1, max_scroll_y)
            )
            editor._fill_rect(v_track_x, v_thumb_y, 1, v_thumb_h)

    def _blit_inline_region(self, src_canvas, left, top, right, bottom):
        left = max(0, int(left))
        top = max(0, int(top))
        right = min(DISPLAY_WIDTH - 1, int(right))
        bottom = min(DISPLAY_HEIGHT - 1, int(bottom))
        if right < left or bottom < top:
            return

        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                try:
                    color = 1 if src_canvas.fb.pixel(x, y) else 0
                except Exception:
                    color = 0
                self.canvas.pixel(x, y, color)

    def _draw_inline_editor(self):
        frame_left, frame_top, frame_right, frame_bottom = self._inline_editor_bounds()
        frame_w = max(1, frame_right - frame_left + 1)
        frame_h = max(1, frame_bottom - frame_top + 1)
        self.canvas.rect(frame_left, frame_top, frame_w, frame_h, 1)
        self.canvas.fill_rect(frame_left + 1, frame_top + 1, max(1, frame_w - 2), max(1, frame_h - 2), 0)

        if self.editor is None:
            return

        editor = self.editor
        temp_canvas = self._inline_canvas
        temp_canvas.clear(0)
        original_canvas = editor.canvas
        editor.canvas = temp_canvas
        try:
            editor._measure_slot(editor.root)
            view_left = frame_left + 1
            view_right = max(view_left, frame_right - 2)
            content_top = frame_top + 1
            content_bottom = max(content_top, frame_bottom - 2)
            content_height = max(1, content_bottom - content_top + 1)
            top = content_top + max(0, (content_height - editor.root.height) // 2)
            editor._layout_slot(editor.root, max(view_left, calculate_app._WORK_LEFT), top, editor.root.baseline)

            cursor_x, cursor_y, cursor_h = editor._cursor_geometry()
            max_scroll_x = max(0, (editor.root.x + editor.root.width) - view_right)
            max_scroll_y = max(0, (editor.root.y + editor.root.height) - content_bottom)
            scroll_x = min(max(0, editor.scroll_x), max_scroll_x)
            scroll_y = min(max(0, editor.scroll_y), max_scroll_y)

            cursor_view_x = cursor_x - scroll_x
            if cursor_view_x < view_left:
                scroll_x = max(0, cursor_x - view_left)
            elif cursor_view_x > view_right:
                scroll_x = min(max_scroll_x, cursor_x - view_right)

            cursor_view_y = cursor_y - scroll_y
            if cursor_view_y < content_top:
                scroll_y = max(0, cursor_y - content_top)
            elif cursor_view_y + cursor_h > content_bottom:
                scroll_y = min(max_scroll_y, cursor_y + cursor_h - content_bottom)

            editor.scroll_x = min(max(0, scroll_x), max_scroll_x)
            editor.scroll_y = min(max(0, scroll_y), max_scroll_y)
            editor._render_slot(editor.root, editor.scroll_x, editor.scroll_y)

            cursor_view_x = cursor_x - editor.scroll_x
            cursor_view_y = cursor_y - editor.scroll_y
            if editor._cursor_visible:
                editor._draw_cursor(cursor_view_x, cursor_view_y, cursor_h)

            self._draw_inline_editor_scrollbars(
                editor,
                frame_left,
                frame_top,
                frame_right,
                frame_bottom,
                view_left,
                view_right,
                content_top,
                content_bottom,
                max_scroll_x,
                max_scroll_y,
            )
        finally:
            editor.canvas = original_canvas

        self._blit_inline_region(
            temp_canvas,
            frame_left + 1,
            frame_top + 1,
            frame_right - 1,
            frame_bottom - 1,
        )

    def _render_meta(self):
        set_active_view("form")
        self.canvas.clear(0)
        self._draw_header(self.meta_title)

        rows = self._meta_rows()
        self.meta_field_index = max(0, min(int(self.meta_field_index), len(rows) - 1))
        y = LIST_TOP

        for row_index in range(len(rows)):
            label, value = rows[row_index]
            selected = row_index == self.meta_field_index
            self.canvas.draw_text(label, 2, y + 1, 1)
            self.canvas.rect(FIELD_X, y, FIELD_W, CHAR_HEIGHT + 2, 1)

            if row_index == 0:
                cursor = self.meta_name_cursor
            else:
                value = self._current_meta_value()
                cursor = len(value)

            start, visible_value = self._visible_field_slice(value, cursor)
            self.canvas.draw_text(visible_value, FIELD_X + 2, y + 1, 1)

            if row_index == 0 and selected and self._cursor_visible and self.popup is None and not self.meta_value_editing:
                cursor_offset = max(0, min(cursor - start, len(visible_value)))
                cursor_x = FIELD_X + 2 + cursor_offset * CHAR_ADVANCE
                cursor_x = min(cursor_x, FIELD_X + FIELD_W - 3)
                self.canvas.vline(cursor_x, y + 1, CHAR_HEIGHT, 1)

            if selected:
                self.canvas.fill_rect(0, y - 1, 1, CHAR_HEIGHT + 4, 1)

            y += ROW_H

        if self.meta_value_editing:
            self._draw_inline_editor()

        footer_text = self._meta_preview()
        if self.meta_value_editing:
            footer_text = "OK save BACK done"
        elif self.meta_field_index == 1:
            footer_text = "OK edit value"
        else:
            footer_text = "OK value field"
        self._draw_footer(self._footer_text(footer_text))

        if self.popup is not None:
            self._draw_popup()

        self._flush_screen()

    def _draw_popup(self):
        popup = self.popup or {}
        title = clip_text_px(popup.get("title", ""), POPUP_W - 6)
        lines = popup.get("lines") or []
        left_label = clip_text_px(popup.get("left", "Cancel"), 34)
        right_label = clip_text_px(popup.get("right", "Ok"), 34)
        selected = str(popup.get("selected") or "left")

        self.canvas.fill_rect(POPUP_X, POPUP_Y, POPUP_W, POPUP_H, 0)
        self.canvas.rect(POPUP_X, POPUP_Y, POPUP_W, POPUP_H, 1)
        self.canvas.hline(POPUP_X + 1, POPUP_Y + 10, POPUP_W - 2, 1)
        self.canvas.draw_text(title, POPUP_X + 3, POPUP_Y + 1, 1)

        for index in range(min(2, len(lines))):
            self.canvas.draw_text(
                clip_text_px(lines[index], POPUP_W - 6),
                POPUP_X + 3,
                POPUP_Y + 13 + index * 8,
                1,
            )

        left_x = POPUP_X + 6
        right_x = POPUP_X + POPUP_W - 42
        option_y = POPUP_Y + POPUP_H - 11

        if selected == "left":
            self.canvas.fill_rect(left_x - 2, option_y - 1, 38, 10, 1)
            self.canvas.draw_text(left_label, left_x, option_y, 0)
            self.canvas.draw_text(right_label, right_x, option_y, 1)
        else:
            self.canvas.draw_text(left_label, left_x, option_y, 1)
            self.canvas.fill_rect(right_x - 2, option_y - 1, 38, 10, 1)
            self.canvas.draw_text(right_label, right_x, option_y, 0)

    def _render_user_actions(self):
        row = get_constant(self.selected_user_name, scope="user")
        if row is None:
            self.view = VIEW_USER_LIST
            self.status_message = "Constant missing"
            self.render()
            return

        set_active_view("menu")
        self.canvas.clear(0)
        self._draw_header("User Defined")
        self.canvas.draw_text(clip_text_px(row["name"], DISPLAY_WIDTH - 6), 2, 14, 1)
        self.canvas.draw_text(clip_text_px(str(row.get("value", "")), DISPLAY_WIDTH - 6), 2, 23, 1)

        option_row_h = 8
        start_y = 39
        for index, label in enumerate(ACTION_ITEMS):
            selected = index == self.action_index
            y = start_y + index * option_row_h
            if selected:
                self.canvas.fill_rect(1, y - 1, DISPLAY_WIDTH - 4, option_row_h + 1, 1)
            self.canvas.draw_text(label, 4, y, 0 if selected else 1)

        if self.popup is not None:
            self._draw_popup()

        self._draw_footer(self._footer_text("BACK user list"))
        self._flush_screen()

    def _render_default_detail(self):
        row = get_constant(self.selected_default_name, scope="default")
        if row is None:
            self.view = VIEW_DEFAULT_LIST
            self.status_message = "Constant missing"
            self.render()
            return

        set_active_view("menu")
        self.canvas.clear(0)
        self._draw_header("Default Constant")
        self.canvas.draw_text(clip_text_px(row["name"], DISPLAY_WIDTH - 6), 2, 14, 1)
        self.canvas.draw_text(clip_text_px(str(row.get("value", "")), DISPLAY_WIDTH - 6), 2, 23, 1)

        lines = _wrap_text(row.get("description", ""), 20)
        for index, line in enumerate(lines[:3]):
            self.canvas.draw_text(clip_text_px(line, DISPLAY_WIDTH - 6), 2, 33 + index * 8, 1)

        self._draw_footer(self._footer_text("Read only"))
        self._flush_screen()

    def _render_message(self):
        set_active_view("form")
        self.canvas.clear(0)
        self._draw_header(self.message_title)
        for index, line in enumerate(self.message_lines[:4]):
            self.canvas.draw_text(
                clip_text_px(line, DISPLAY_WIDTH - 6),
                3,
                17 + index * 10,
                1,
            )
        self._draw_footer("OK continue")
        self._flush_screen()

    def _draw_expression_footer(self):
        if self.view != VIEW_EXPR or self.editor is None:
            return
        if str(nav.current_state() or "") != "" and nav.is_visible():
            return

        footer_buf = bytearray(DISPLAY_WIDTH)
        expression = ""
        try:
            expression, _ = self.editor._slot_to_expression(self.editor.root)
        except Exception:
            expression = ""

        page_text = clip_text_px(
            "{} = {}".format(self.editor_name or "const", expression).strip(),
            DISPLAY_WIDTH - 2,
        )
        if page_text:
            for index, char in enumerate(page_text):
                glyph = calculate_app.Characters.Chr2bytes(calculate_app.Characters, char)
                x = index * CHAR_ADVANCE
                if x >= DISPLAY_WIDTH:
                    break
                for col_index, col_bits in enumerate(glyph):
                    target = x + col_index
                    if target >= DISPLAY_WIDTH:
                        break
                    footer_buf[target] = col_bits
        nav.draw_bottom_page(footer_buf)

    def render(self):
        if self.view == VIEW_MENU:
            self._draw_list(self.menu_title, MENU_ITEMS, self.menu_index, self._footer_text("OK open"))
            return
        if self.view == VIEW_USER_LIST:
            rows = [row["name"] for row in list_user_constants()]
            self._draw_list("User Defined", rows, self.user_index, self._footer_text("OK actions"))
            return
        if self.view == VIEW_DEFAULT_LIST:
            rows = [row["name"] for row in list_default_constants()]
            self._draw_list("Default Constants", rows, self.default_index, self._footer_text("OK details"))
            return
        if self.view == VIEW_META:
            self._render_meta()
            return
        if self.view == VIEW_USER_ACTIONS:
            self._render_user_actions()
            return
        if self.view == VIEW_DEFAULT_DETAIL:
            self._render_default_detail()
            return
        if self.view == VIEW_MESSAGE:
            self._render_message()
            return
        if self.view == VIEW_EXPR and self.editor is not None:
            self.editor.render()

    def _set_message(self, title, text_value, return_view=None):
        max_chars = max(1, (DISPLAY_WIDTH - 6) // CHAR_ADVANCE)
        self.message_title = str(title or "")
        self.message_lines = _wrap_text(text_value, max_chars)
        self.message_return_view = return_view or self.view
        self.view = VIEW_MESSAGE

    def _activate_popup(self, title, lines, left_label, right_label, kind):
        self.popup = {
            "title": str(title or ""),
            "lines": list(lines or []),
            "left": str(left_label or "Cancel"),
            "right": str(right_label or "Ok"),
            "selected": "left",
            "kind": str(kind or ""),
        }

    def _clear_popup(self):
        self.popup = None

    def _open_create_form(self, row=None, return_view=VIEW_MENU):
        row = row or {}
        self.meta_title = "Edit Constant" if row else "Create New"
        self.meta_return_view = return_view
        self.editing_original_name = str(row.get("name") or "")
        self.meta_name = str(row.get("name") or "")
        self.meta_name_cursor = len(self.meta_name)
        self.meta_value = str(row.get("value") or "")
        self.meta_value_state = row.get("expression_state")
        self.meta_field_index = 0
        self.meta_value_editing = False
        self.editor = None
        self._reset_cursor_blink()
        self.status_message = "OK edit value"
        self.view = VIEW_META

    def _validate_meta(self):
        name = self.meta_name.strip()
        if not _is_identifier(name):
            return False, "Constant name must be a valid identifier"

        if default_constant_exists(name) and name != self.editing_original_name:
            return False, "Default constant '{}' already exists".format(name)

        if default_function_exists(name) or user_function_exists(name):
            return False, "Function '{}' already exists".format(name)

        if name in calculate_app._BASE_SAFE_GLOBALS or name == "ans":
            return False, "Constant name '{}' is reserved".format(name)

        return True, ""

    def _open_expression_editor(self):
        if self._calculate_save_restore is None:
            self._calculate_save_restore = calculate_app._save_calculate_state
            calculate_app._save_calculate_state = lambda _editor: None

        editor = calculate_app._MathEditor()
        if isinstance(self.meta_value_state, dict):
            calculate_app._load_slot_from_state(editor.root, self.meta_value_state)
        elif self.meta_value != "":
            editor._insert_sequence([calculate_app.TokenNode(self.meta_value)])

        editor._set_cursor(editor.root, len(editor.root.items))
        editor._flush_bottom_page = self._draw_expression_footer
        editor.render = lambda: self.render()

        self.editor = editor
        self.editor_name = self.meta_name.strip()
        self.meta_field_index = 1
        self.meta_value_editing = True
        self.view = VIEW_META
        self.status_message = ""
        self.render()

    def _restore_expression_state(self):
        if self.editor is None:
            return
        self.meta_value_state = calculate_app._serialize_slot(self.editor.root)
        try:
            expression, _ = self.editor._slot_to_expression(self.editor.root)
        except Exception:
            expression = self.meta_value
        self.meta_value = str(expression or "")
        self.meta_value_editing = False
        self.meta_field_index = 0
        self.editor = None

    def _validate_numeric_value(self, value):
        if isinstance(value, bool):
            return True
        return isinstance(value, (int, float))

    def _validate_expression_and_save(self):
        expression, ok = self.editor._slot_to_expression(self.editor.root)
        if not ok:
            return False, "Value is incomplete"

        safe_globals = calculate_app.build_runtime_safe_globals(
            exclude_constant_name=self.editor_name
        )

        try:
            value = eval(expression, safe_globals, {})
        except Exception as exc:
            return False, str(exc)

        if not self._validate_numeric_value(value):
            return False, "Value must be numeric"

        expression_state = calculate_app._serialize_slot(self.editor.root)
        upsert_user_constant(
            self.editor_name,
            expression,
            original_name=self.editing_original_name,
            expression_state=expression_state,
        )
        data_bucket[FUNCTIONS_RELOAD_BUCKET_KEY] = True

        self.meta_value = expression
        self.meta_value_state = expression_state
        self.meta_value_editing = False
        self.selected_user_name = self.editor_name
        rows = [row["name"] for row in list_user_constants()]
        if self.selected_user_name in rows:
            self.user_index = rows.index(self.selected_user_name)
        self.view = VIEW_USER_LIST
        self.status_message = "Saved {}".format(self.editor_name)
        return True, ""

    def _handle_popup_token(self, token):
        if token in ("nav_l", "nav_r"):
            if self.popup is not None:
                self.popup["selected"] = "right" if self.popup.get("selected") == "left" else "left"
            return

        if token == "back":
            self._clear_popup()
            self.status_message = "Cancelled"
            return

        if token not in ("ok", "exe"):
            return

        selected = "left"
        kind = ""
        if self.popup is not None:
            selected = str(self.popup.get("selected") or "left")
            kind = str(self.popup.get("kind") or "")

        self._clear_popup()
        if selected == "left":
            self.status_message = "Cancelled"
            return

        if kind == "replace":
            self.meta_field_index = 1
            self._open_expression_editor()
        elif kind == "replace_save":
            success, message = self._validate_expression_and_save()
            if success:
                self.editor = None
            else:
                self._set_message("Invalid Constant", message, return_view=VIEW_META)
        elif kind == "delete":
            if delete_user_constant(self.selected_user_name):
                data_bucket[FUNCTIONS_RELOAD_BUCKET_KEY] = True
                rows = [row["name"] for row in list_user_constants()]
                if rows:
                    self.user_index = min(self.user_index, len(rows) - 1)
                else:
                    self.user_index = 0
                self.view = VIEW_USER_LIST
                self.status_message = "Deleted {}".format(self.selected_user_name)
            else:
                self.status_message = "Delete failed"

    def _handle_menu_token(self, token):
        if token == "back":
            if self.return_to_parent:
                self._should_exit = True
            else:
                request_navigation_from_key("back")
            return
        if token == "nav_u":
            self.menu_index = (self.menu_index - 1) % len(MENU_ITEMS)
            self.status_message = "OK open"
            return
        if token == "nav_d":
            self.menu_index = (self.menu_index + 1) % len(MENU_ITEMS)
            self.status_message = "OK open"
            return
        if token not in ("ok", "exe"):
            return

        if self.menu_index == 0:
            self._open_create_form()
        elif self.menu_index == 1:
            self.view = VIEW_USER_LIST
            self.status_message = "OK actions"
        else:
            self.view = VIEW_DEFAULT_LIST
            self.status_message = "OK details"

    def _handle_user_list_token(self, token):
        rows = list_user_constants()
        if token == "back":
            self.view = VIEW_MENU
            self.status_message = "OK open"
            return
        if token == "nav_u" and rows:
            self.user_index = (self.user_index - 1) % len(rows)
            self.status_message = "OK actions"
            return
        if token == "nav_d" and rows:
            self.user_index = (self.user_index + 1) % len(rows)
            self.status_message = "OK actions"
            return
        if token not in ("ok", "exe") or not rows:
            return

        self.user_index = max(0, min(self.user_index, len(rows) - 1))
        self.selected_user_name = rows[self.user_index]["name"]
        self.action_index = 0
        self.view = VIEW_USER_ACTIONS
        self.status_message = ""

    def _handle_default_list_token(self, token):
        rows = list_default_constants()
        if token == "back":
            self.view = VIEW_MENU
            self.status_message = "OK open"
            return
        if token == "nav_u" and rows:
            self.default_index = (self.default_index - 1) % len(rows)
            self.status_message = "OK details"
            return
        if token == "nav_d" and rows:
            self.default_index = (self.default_index + 1) % len(rows)
            self.status_message = "OK details"
            return
        if token not in ("ok", "exe") or not rows:
            return

        self.default_index = max(0, min(self.default_index, len(rows) - 1))
        self.selected_default_name = rows[self.default_index]["name"]
        self.view = VIEW_DEFAULT_DETAIL
        self.status_message = "Read only"

    def _handle_user_actions_token(self, token):
        if self.popup is not None:
            self._handle_popup_token(token)
            return

        if token == "back":
            self.view = VIEW_USER_LIST
            self.status_message = "OK actions"
            return
        if token == "nav_u":
            self.action_index = (self.action_index - 1) % len(ACTION_ITEMS)
            return
        if token == "nav_d":
            self.action_index = (self.action_index + 1) % len(ACTION_ITEMS)
            return
        if token not in ("ok", "exe"):
            return

        row = get_constant(self.selected_user_name, scope="user")
        if row is None:
            self.view = VIEW_USER_LIST
            self.status_message = "Constant missing"
            return

        if self.action_index == 0:
            self._open_create_form(row=row, return_view=VIEW_USER_ACTIONS)
            return

        self._activate_popup(
            "Delete Constant",
            [
                clip_text_px(self.selected_user_name, POPUP_W - 6),
                "Delete this constant?",
            ],
            "Cancel",
            "Delete",
            "delete",
        )

    def _handle_default_detail_token(self, token):
        if token == "back":
            self.view = VIEW_DEFAULT_LIST
            self.status_message = "OK details"

    def _meta_insert_token(self, token):
        if self.meta_field_index != 0:
            return

        insert_text = _identifier_token(token)
        if insert_text is None:
            return

        field_cursor = self.meta_name_cursor
        self.meta_name = (
            self.meta_name[:field_cursor]
            + insert_text
            + self.meta_name[field_cursor:]
        )
        self.meta_name_cursor = min(len(self.meta_name), field_cursor + len(insert_text))
        self._reset_cursor_blink()

    def _handle_meta_token(self, token):
        if self.popup is not None:
            self._handle_popup_token(token)
            return

        if self.meta_value_editing:
            self._handle_expression_token(token)
            return

        if token == "back":
            self.view = self.meta_return_view
            self.status_message = "OK open" if self.view == VIEW_MENU else "OK actions"
            return

        if token == "nav_u":
            self.meta_field_index = max(0, self.meta_field_index - 1)
            self._reset_cursor_blink()
            return

        if token == "nav_d":
            self.meta_field_index = min(len(self._meta_rows()) - 1, self.meta_field_index + 1)
            self._reset_cursor_blink()
            if self.meta_field_index == 1:
                self._start_value_editing()
            return

        if token == "nav_l" and self.meta_field_index == 0:
            self.meta_name_cursor = max(0, self.meta_name_cursor - 1)
            self._reset_cursor_blink()
            return

        if token == "nav_r" and self.meta_field_index == 0:
            self.meta_name_cursor = min(len(self.meta_name), self.meta_name_cursor + 1)
            self._reset_cursor_blink()
            return

        if token in ("nav_b", "undo") and self.meta_field_index == 0:
            if self.meta_name_cursor > 0:
                self.meta_name = (
                    self.meta_name[: self.meta_name_cursor - 1]
                    + self.meta_name[self.meta_name_cursor:]
                )
                self.meta_name_cursor -= 1
            self._reset_cursor_blink()
            return

        if token == "AC":
            if self.meta_field_index == 0:
                self.meta_name = ""
                self.meta_name_cursor = 0
            else:
                self.meta_value = ""
                self.meta_value_state = None
            self._reset_cursor_blink()
            return

        if token in ("ok", "exe"):
            if self.meta_field_index == 0:
                self._start_value_editing()
                return

            self._start_value_editing()
            return

        self._meta_insert_token(token)

    def _handle_expression_token(self, token):
        if token == "back":
            self._restore_expression_state()
            self.status_message = "DOWN value field"
            return

        if token in ("ok", "exe"):
            self._try_save_constant()
            return

        if token in ("alpha", "beta"):
            keypad_state_manager(x=token)
            self.editor._reset_cursor_blink()
            return

        if token == "caps":
            keypad_state_manager(x="A")
            self.editor._reset_cursor_blink()
            return

        if token == "":
            self.editor._reset_cursor_blink()
            return

        self.editor.handle_key(token)

    def _handle_message_token(self, token):
        if token in ("back", "ok", "exe"):
            self.view = self.message_return_view
            self.status_message = ""

    def handle_token(self, token):
        if self.view == VIEW_MENU:
            self._handle_menu_token(token)
            return
        if self.view == VIEW_USER_LIST:
            self._handle_user_list_token(token)
            return
        if self.view == VIEW_DEFAULT_LIST:
            self._handle_default_list_token(token)
            return
        if self.view == VIEW_USER_ACTIONS:
            self._handle_user_actions_token(token)
            return
        if self.view == VIEW_DEFAULT_DETAIL:
            self._handle_default_detail_token(token)
            return
        if self.view == VIEW_META:
            self._handle_meta_token(token)
            return
        if self.view == VIEW_EXPR:
            self._handle_expression_token(token)
            return
        if self.view == VIEW_MESSAGE:
            self._handle_message_token(token)

    def _handle_mode_tokens(self, token):
        if self.view != VIEW_EXPR and not (self.view == VIEW_META and self.meta_value_editing) and token in ("alpha", "beta"):
            keypad_state_manager(x=token)
            self.render()
            return True
        if self.view != VIEW_EXPR and not (self.view == VIEW_META and self.meta_value_editing) and token == "caps":
            keypad_state_manager(x="A")
            self.render()
            return True
        if self.view != VIEW_EXPR and not (self.view == VIEW_META and self.meta_value_editing) and token == "":
            self.render()
            return True
        return False

    def run(self):
        ensure_default_constants()
        keypad_state_manager_reset()
        display.clear_display()
        self.render()

        try:
            while True:
                token = _read_key_with_local_back(idle_callback=self._idle_callback())

                if token == "home":
                    nav.set_restore_callback(None)
                    request_navigation_from_key("home")
                if token == "settings":
                    nav.set_restore_callback(None)
                    request_navigation_from_key("settings")
                if token == "off":
                    nav.set_restore_callback(None)
                    return

                if self._handle_mode_tokens(token):
                    continue

                self.handle_token(token)
                if self._should_exit:
                    return
                self.render()
        finally:
            nav.set_restore_callback(None)
            if self._calculate_save_restore is not None:
                calculate_app._save_calculate_state = self._calculate_save_restore
                self._calculate_save_restore = None


def run_constant_section(menu_title="Constants", return_to_parent=False):
    _ConstantVaultApp(menu_title=menu_title, return_to_parent=return_to_parent).run()
