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
    import _thread  # type: ignore
except Exception:
    _thread = None

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
from apps.root.constant_store import list_default_constants, list_user_constants
from apps.root.function_store import list_default_functions, list_user_functions
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


_PENDING_BUCKET_KEY = "_calculate_pending_action"
_TOOLBOX_INPUT_POLL_SEC = 0.01

_SCOPE_ROOT = "root"
_SCOPE_CONSTANTS = "constants"
_SCOPE_FUNCTIONS = "functions"
_SCOPE_CONSTANTS_USER = "constants_user"
_SCOPE_CONSTANTS_DEFAULT = "constants_default"
_SCOPE_FUNCTIONS_USER = "functions_user"
_SCOPE_FUNCTIONS_DEFAULT = "functions_default"

_KIND_SECTION = "section"
_KIND_CONSTANT = "constant"
_KIND_FUNCTION = "function"

HEADER_H = 10
SEARCH_X = 2
SEARCH_Y = 11
SEARCH_W = DISPLAY_WIDTH - 4
SEARCH_H = 10
SEARCH_TEXT_X = SEARCH_X + 10
SEARCH_TEXT_W = SEARCH_W - 13
LIST_TOP = 22
FOOTER_H = 8
LIST_BOTTOM = DISPLAY_HEIGHT - FOOTER_H - 3
ROW_H = 8
VISIBLE_ROWS = max(1, (LIST_BOTTOM - LIST_TOP + 1) // ROW_H)
CURSOR_BLINK_MS = 450
SEARCH_WORKER_SLEEP_MS = 20


def _push_toolbox_poll_delay():
    previous_delay = getattr(typer, "debounce_delay_time", None)
    if previous_delay is not None:
        typer.debounce_delay_time = _TOOLBOX_INPUT_POLL_SEC
    return previous_delay


def _restore_toolbox_poll_delay(previous_delay):
    if previous_delay is not None:
        typer.debounce_delay_time = previous_delay


def _ticks_ms():
    try:
        return time.ticks_ms()
    except Exception:
        try:
            return int(time.monotonic() * 1000)
        except Exception:
            return int(time.time() * 1000)


def _sleep_ms(ms):
    ms = max(0, int(ms))
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000.0)


def _sleep_s(seconds):
    try:
        time.sleep(float(seconds))
    except Exception:
        pass


def _search_char_from_token(token):
    token = str(token or "")
    if token == "tab":
        return " "
    if len(token) != 1:
        return None
    code = ord(token)
    if 32 <= code <= 126:
        return token
    return None


def _normalize_query(text_value):
    text_value = str(text_value or "").strip().lower()
    folded = []
    for char in text_value:
        if ("a" <= char <= "z") or ("0" <= char <= "9"):
            folded.append(char)
    return text_value, "".join(folded)


def _signature(name, variables):
    args = []
    for value in variables or []:
        value = str(value or "").strip()
        if value != "":
            args.append(value)
    return "{}({})".format(str(name or "").strip(), ",".join(args))


def _scope_title(scope):
    if scope == _SCOPE_CONSTANTS:
        return "Constants"
    if scope == _SCOPE_FUNCTIONS:
        return "Functions"
    if scope == _SCOPE_CONSTANTS_USER:
        return "User Constants"
    if scope == _SCOPE_CONSTANTS_DEFAULT:
        return "Default Constants"
    if scope == _SCOPE_FUNCTIONS_USER:
        return "User Functions"
    if scope == _SCOPE_FUNCTIONS_DEFAULT:
        return "Default Functions"
    return "Toolbox"


def _parent_scope(scope):
    if scope in (_SCOPE_CONSTANTS, _SCOPE_FUNCTIONS):
        return _SCOPE_ROOT
    if scope in (_SCOPE_CONSTANTS_USER, _SCOPE_CONSTANTS_DEFAULT):
        return _SCOPE_CONSTANTS
    if scope in (_SCOPE_FUNCTIONS_USER, _SCOPE_FUNCTIONS_DEFAULT):
        return _SCOPE_FUNCTIONS
    return None


def _section_row(label, next_scope):
    return {
        "kind": _KIND_SECTION,
        "label": str(label or ""),
        "next_scope": str(next_scope or ""),
        "selectable": True,
        "key": "section:" + str(next_scope or ""),
        "search_raw": "",
        "search_folded": "",
    }


def _constant_row(row, prefix=""):
    name = str((row or {}).get("name") or "").strip()
    if name == "":
        return None

    value = str((row or {}).get("value") or "").strip()
    description = str((row or {}).get("description") or "").strip()
    label = "{}{}".format(prefix, name)
    if value != "":
        label = "{} = {}".format(label, value)

    search_raw, search_folded = _normalize_query(
        "{} {} {}".format(name, value, description)
    )
    return {
        "kind": _KIND_CONSTANT,
        "label": label,
        "name": name,
        "selectable": True,
        "key": "constant:" + name,
        "search_raw": search_raw,
        "search_folded": search_folded,
    }


def _function_row(row, prefix=""):
    name = str((row or {}).get("name") or "").strip()
    if name == "":
        return None

    variables = list((row or {}).get("variables") or [])
    label = "{}{}".format(prefix, _signature(name, variables))
    search_raw, search_folded = _normalize_query(
        "{} {}".format(name, " ".join(str(value or "").strip() for value in variables))
    )
    return {
        "kind": _KIND_FUNCTION,
        "label": label,
        "name": name,
        "arg_count": len(variables),
        "selectable": True,
        "key": "function:" + name,
        "search_raw": search_raw,
        "search_folded": search_folded,
    }


def _empty_row(label):
    return {
        "kind": "info",
        "label": str(label or ""),
        "selectable": False,
        "key": "info:" + str(label or ""),
        "search_raw": "",
        "search_folded": "",
    }


def _searching_row():
    return _empty_row("Searching...")


def _matches_query(row, query):
    query_raw, query_folded = _normalize_query(query)
    if query_raw == "":
        return True

    row_raw = str(row.get("search_raw") or "")
    row_folded = str(row.get("search_folded") or "")

    if query_raw in row_raw:
        return True
    if query_folded != "" and query_folded in row_folded:
        return True
    return False


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


class _ToolboxApp:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.scope = _SCOPE_ROOT
        self.query = ""
        self.query_cursor = 0
        self.row_index = 0
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()

        self._user_constants = []
        self._default_constants = []
        self._user_functions = []
        self._default_functions = []

        self._search_rows = []
        self._searching = False
        self._search_generation = 0
        self._search_pending_local = False
        self._worker_request_generation = 0
        self._worker_request_scope = _SCOPE_ROOT
        self._worker_request_query = ""
        self._worker_result = None
        self._worker_result_ready = False
        self._worker_running = False
        self._worker_started = False
        self._worker_lock = None

        if _thread is not None:
            try:
                self._worker_lock = _thread.allocate_lock()
            except Exception:
                self._worker_lock = None

    def _refresh_catalog(self):
        self._user_constants = list_user_constants()
        self._default_constants = list_default_constants()
        self._user_functions = list_user_functions()
        self._default_functions = list_default_functions()

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

    def _worker_lock_acquire(self):
        if self._worker_lock is not None:
            try:
                self._worker_lock.acquire()
            except Exception:
                pass

    def _worker_lock_release(self):
        if self._worker_lock is not None:
            try:
                self._worker_lock.release()
            except Exception:
                pass

    def _ensure_worker_started(self):
        if self._worker_started or _thread is None or self._worker_lock is None:
            return
        self._worker_running = True
        try:
            _thread.start_new_thread(self._search_worker, ())
            self._worker_started = True
        except Exception:
            self._worker_running = False
            self._worker_started = False

    def _stop_worker(self):
        self._worker_running = False
        if self._worker_started:
            _sleep_ms(SEARCH_WORKER_SLEEP_MS)

    def _search_worker(self):
        last_generation = 0
        while self._worker_running:
            request = None
            self._worker_lock_acquire()
            try:
                generation = int(self._worker_request_generation or 0)
                if generation != 0 and generation != last_generation:
                    request = (
                        generation,
                        str(self._worker_request_scope or _SCOPE_ROOT),
                        str(self._worker_request_query or ""),
                    )
            finally:
                self._worker_lock_release()

            if request is None:
                _sleep_ms(SEARCH_WORKER_SLEEP_MS)
                continue

            generation, scope, query = request
            rows = self._compute_search_rows(scope, query)

            self._worker_lock_acquire()
            try:
                if generation == self._worker_request_generation:
                    self._worker_result = {
                        "generation": generation,
                        "scope": scope,
                        "query": query,
                        "rows": rows,
                    }
                    self._worker_result_ready = True
            finally:
                self._worker_lock_release()

            last_generation = generation
            _sleep_ms(0)

    def _consume_search_result(self):
        if not self._worker_started:
            return False

        result = None
        self._worker_lock_acquire()
        try:
            if self._worker_result_ready:
                result = self._worker_result
                self._worker_result = None
                self._worker_result_ready = False
        finally:
            self._worker_lock_release()

        if not isinstance(result, dict):
            return False

        if int(result.get("generation", -1)) != self._search_generation:
            return False
        if str(result.get("scope") or "") != self.scope:
            return False
        if str(result.get("query") or "") != self.query:
            return False

        self._search_rows = list(result.get("rows") or [])
        self._searching = False
        self._search_pending_local = False
        self.row_index = 0
        return True

    def _resolve_pending_search(self):
        if not self._searching or not self._search_pending_local:
            return False

        self._refresh_catalog()
        self._search_rows = self._compute_search_rows(self.scope, self.query)
        self._searching = False
        self._search_pending_local = False
        self.row_index = 0
        return True

    def _idle_callback(self):
        def _idle():
            changed = False
            if self._update_cursor_blink():
                changed = True
            if self._consume_search_result():
                changed = True
            elif self._resolve_pending_search():
                changed = True
            if changed:
                self.render()

        return _idle

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

    def _search_visible_slice(self):
        cursor = max(0, min(int(self.query_cursor), len(self.query)))
        max_chars = max(1, (SEARCH_TEXT_W + 1) // CHAR_ADVANCE)
        start = 0
        if cursor > max_chars:
            start = cursor - max_chars
        max_start = max(0, len(self.query) - max_chars)
        start = min(start, max_start)
        visible = self.query[start : start + max_chars]
        return start, visible

    def _browse_rows(self):
        if self.scope == _SCOPE_ROOT:
            return [
                _section_row("Constants", _SCOPE_CONSTANTS),
                _section_row("Functions", _SCOPE_FUNCTIONS),
            ]

        if self.scope == _SCOPE_CONSTANTS:
            return [
                _section_row("User Defined", _SCOPE_CONSTANTS_USER),
                _section_row("Default Constants", _SCOPE_CONSTANTS_DEFAULT),
            ]

        if self.scope == _SCOPE_FUNCTIONS:
            return [
                _section_row("User Defined", _SCOPE_FUNCTIONS_USER),
                _section_row("Default Functions", _SCOPE_FUNCTIONS_DEFAULT),
            ]

        if self.scope == _SCOPE_CONSTANTS_USER:
            rows = []
            for row in self._user_constants:
                entry = _constant_row(row)
                if entry is not None:
                    rows.append(entry)
            return rows or [_empty_row("No user constants")]

        if self.scope == _SCOPE_CONSTANTS_DEFAULT:
            rows = []
            for row in self._default_constants:
                entry = _constant_row(row)
                if entry is not None:
                    rows.append(entry)
            return rows or [_empty_row("No default constants")]

        if self.scope == _SCOPE_FUNCTIONS_USER:
            rows = []
            for row in self._user_functions:
                entry = _function_row(row)
                if entry is not None:
                    rows.append(entry)
            return rows or [_empty_row("No user functions")]

        rows = []
        for row in self._default_functions:
            entry = _function_row(row)
            if entry is not None:
                rows.append(entry)
        return rows or [_empty_row("No default functions")]

    def _compute_search_rows(self, scope, query):
        rows = []

        if scope == _SCOPE_ROOT:
            for row in self._user_constants:
                entry = _constant_row(row, prefix="CU ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            for row in self._default_constants:
                entry = _constant_row(row, prefix="CD ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            for row in self._user_functions:
                entry = _function_row(row, prefix="FU ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            for row in self._default_functions:
                entry = _function_row(row, prefix="FD ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            return rows

        if scope == _SCOPE_CONSTANTS:
            for row in self._user_constants:
                entry = _constant_row(row, prefix="U ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            for row in self._default_constants:
                entry = _constant_row(row, prefix="D ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            return rows

        if scope == _SCOPE_FUNCTIONS:
            for row in self._user_functions:
                entry = _function_row(row, prefix="U ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            for row in self._default_functions:
                entry = _function_row(row, prefix="D ")
                if entry is not None and _matches_query(entry, query):
                    rows.append(entry)
            return rows

        source_rows = []
        builder = None
        if scope == _SCOPE_CONSTANTS_USER:
            source_rows = self._user_constants
            builder = _constant_row
        elif scope == _SCOPE_CONSTANTS_DEFAULT:
            source_rows = self._default_constants
            builder = _constant_row
        elif scope == _SCOPE_FUNCTIONS_USER:
            source_rows = self._user_functions
            builder = _function_row
        else:
            source_rows = self._default_functions
            builder = _function_row

        for row in source_rows:
            entry = builder(row)
            if entry is not None and _matches_query(entry, query):
                rows.append(entry)
        return rows

    def _schedule_search(self):
        if self.query == "":
            self._search_generation += 1
            self._refresh_catalog()
            self._search_rows = []
            self._searching = False
            self._search_pending_local = False
            self.row_index = 0
            return

        self._search_generation += 1
        self._refresh_catalog()
        self._search_rows = []
        self._searching = True
        self._search_pending_local = True
        self.row_index = 0
        self._ensure_worker_started()

        if not self._worker_started:
            self._search_rows = self._compute_search_rows(self.scope, self.query)
            self._searching = False
            self._search_pending_local = False
            return

        self._worker_lock_acquire()
        try:
            self._worker_request_generation = self._search_generation
            self._worker_request_scope = self.scope
            self._worker_request_query = self.query
        finally:
            self._worker_lock_release()

    def _display_rows(self):
        if self.query != "":
            if self._searching:
                return [_searching_row()]
            if self._search_rows:
                return list(self._search_rows)
            return [_empty_row("No matches")]
        return self._browse_rows()

    def _normalized_row_index(self, rows):
        selectable = [index for index, row in enumerate(rows) if row.get("selectable")]
        if not selectable:
            self.row_index = 0
            return 0
        if self.row_index in selectable:
            return self.row_index
        self.row_index = selectable[0]
        return self.row_index

    def _move_selection(self, direction):
        rows = self._display_rows()
        selectable = [index for index, row in enumerate(rows) if row.get("selectable")]
        if not selectable:
            self.row_index = 0
            return

        current = self._normalized_row_index(rows)
        try:
            current_pos = selectable.index(current)
        except Exception:
            current_pos = 0

        next_pos = (current_pos + int(direction)) % len(selectable)
        self.row_index = selectable[next_pos]

    def _draw_header(self):
        self.canvas.draw_text(clip_text_px(_scope_title(self.scope), DISPLAY_WIDTH - 4), 2, 1, 1)
        self.canvas.hline(0, HEADER_H - 1, DISPLAY_WIDTH, 1)

    def _draw_search_box(self):
        self.canvas.rect(SEARCH_X, SEARCH_Y, SEARCH_W, SEARCH_H, 1)
        self.canvas.draw_text("?", SEARCH_X + 3, SEARCH_Y + 1, 1)

        start, visible = self._search_visible_slice()
        self.canvas.draw_text(visible, SEARCH_TEXT_X, SEARCH_Y + 1, 1)

        if self._cursor_visible:
            offset = max(0, min(self.query_cursor - start, len(visible)))
            cursor_x = SEARCH_TEXT_X + offset * CHAR_ADVANCE
            cursor_x = min(cursor_x, SEARCH_X + SEARCH_W - 3)
            self.canvas.vline(cursor_x, SEARCH_Y + 1, CHAR_HEIGHT, 1)

    def _list_window(self, selected_index, item_count):
        if item_count <= VISIBLE_ROWS:
            return 0
        top_index = max(0, int(selected_index) - VISIBLE_ROWS + 1)
        max_top = max(0, item_count - VISIBLE_ROWS)
        return min(top_index, max_top)

    def _draw_scrollbar(self, top_index, item_count):
        if item_count <= VISIBLE_ROWS:
            return
        track_x = DISPLAY_WIDTH - 2
        track_y = LIST_TOP
        track_h = max(8, LIST_BOTTOM - LIST_TOP + 1)
        self.canvas.vline(track_x, track_y, track_h, 1)
        thumb_h = max(8, (track_h * VISIBLE_ROWS) // max(1, item_count))
        max_top = max(1, item_count - VISIBLE_ROWS)
        thumb_range = max(0, track_h - thumb_h)
        thumb_y = track_y + (top_index * thumb_range // max_top)
        self.canvas.fill_rect(track_x - 1, thumb_y, 3, thumb_h, 1)

    def _footer_text(self, rows):
        if self.query != "" and self._searching:
            return "Searching..."

        selectable_rows = [row for row in rows if row.get("selectable")]
        if self.query != "":
            if not selectable_rows:
                return "AC clear"
            return "OK insert"

        selected_index = self._normalized_row_index(rows)
        if rows and rows[selected_index].get("kind") == _KIND_SECTION:
            return "OK open"
        if rows and rows[selected_index].get("selectable"):
            return "OK insert"

        parent_scope = _parent_scope(self.scope)
        if parent_scope is None:
            return "BACK calculate"
        return "BACK up"

    def _draw_footer(self, text_value):
        self.canvas.hline(0, DISPLAY_HEIGHT - FOOTER_H - 1, DISPLAY_WIDTH, 1)
        self.canvas.draw_text(clip_text_px(text_value, DISPLAY_WIDTH - 2), 1, DISPLAY_HEIGHT - FOOTER_H + 1, 1)

    def render(self):
        set_active_view("form")
        self.canvas.clear(0)
        self._draw_header()
        self._draw_search_box()

        rows = self._display_rows()
        selected_index = self._normalized_row_index(rows)
        top_index = self._list_window(selected_index, len(rows))
        bottom_index = min(len(rows), top_index + VISIBLE_ROWS)

        y = LIST_TOP
        for row_index in range(top_index, bottom_index):
            row = rows[row_index]
            selected = row_index == selected_index and row.get("selectable")
            if selected:
                self.canvas.fill_rect(1, y, DISPLAY_WIDTH - 5, ROW_H, 1)
            self.canvas.draw_text(
                clip_text_px(row.get("label", ""), DISPLAY_WIDTH - 10),
                3,
                y,
                0 if selected else 1,
            )
            y += ROW_H

        self._draw_scrollbar(top_index, len(rows))
        self._draw_footer(self._footer_text(rows))
        self._flush_screen()

    def _insert_query_text(self, text_value):
        text_value = str(text_value or "")
        if text_value == "":
            return
        cursor = max(0, min(self.query_cursor, len(self.query)))
        self.query = self.query[:cursor] + text_value + self.query[cursor:]
        self.query_cursor = cursor + len(text_value)
        self._schedule_search()
        self._reset_cursor_blink()

    def _delete_query_char(self):
        if self.query_cursor <= 0:
            return
        cursor = max(0, min(self.query_cursor, len(self.query)))
        self.query = self.query[: cursor - 1] + self.query[cursor:]
        self.query_cursor = cursor - 1
        self._schedule_search()
        self._reset_cursor_blink()

    def _clear_query(self):
        if self.query == "":
            return
        self.query = ""
        self.query_cursor = 0
        self._schedule_search()
        self._reset_cursor_blink()

    def _activate_row(self):
        rows = self._display_rows()
        if not rows:
            return False

        row = rows[self._normalized_row_index(rows)]
        if not row.get("selectable"):
            return False

        kind = row.get("kind")
        if kind == _KIND_SECTION:
            self.scope = str(row.get("next_scope") or _SCOPE_ROOT)
            self.row_index = 0
            if self.query != "":
                self._schedule_search()
            return False

        if kind == _KIND_CONSTANT:
            data_bucket[_PENDING_BUCKET_KEY] = {
                "type": "insert_text",
                "text": row.get("name", ""),
            }
            request_navigation_from_key("back")

        if kind == _KIND_FUNCTION:
            data_bucket[_PENDING_BUCKET_KEY] = {
                "type": "insert_function",
                "name": row.get("name", ""),
                "arg_count": row.get("arg_count", 0),
            }
            request_navigation_from_key("back")

        return False

    def _handle_token(self, token):
        if token == "back":
            parent_scope = _parent_scope(self.scope)
            if parent_scope is None:
                request_navigation_from_key("back")
            self.scope = parent_scope
            self.row_index = 0
            if self.query != "":
                self._schedule_search()
            return

        if token == "nav_u":
            self._move_selection(-1)
            return

        if token == "nav_d":
            self._move_selection(1)
            return

        if token == "nav_l":
            self.query_cursor = max(0, self.query_cursor - 1)
            self._reset_cursor_blink()
            return

        if token == "nav_r":
            self.query_cursor = min(len(self.query), self.query_cursor + 1)
            self._reset_cursor_blink()
            return

        if token in ("nav_b", "undo"):
            self._delete_query_char()
            return

        if token == "AC":
            self._clear_query()
            return

        if token in ("ok", "exe"):
            if self._searching:
                self._consume_search_result()
                self._resolve_pending_search()
            self._activate_row()
            return

        char = _search_char_from_token(token)
        if char is not None:
            self._insert_query_text(char)

    def run(self):
        previous_delay = _push_toolbox_poll_delay()
        keypad_state_manager_reset()
        self._refresh_catalog()
        self._ensure_worker_started()
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

                if token in ("alpha", "beta"):
                    keypad_state_manager(x=token)
                    self._reset_cursor_blink()
                    self.render()
                    continue

                if token == "caps":
                    keypad_state_manager(x="A")
                    self._reset_cursor_blink()
                    self.render()
                    continue

                if token == "":
                    self.render()
                    continue

                self._handle_token(token)
                self.render()
        finally:
            nav.set_restore_callback(None)
            self._stop_worker()
            _restore_toolbox_poll_delay(previous_delay)


def toolbox():
    _ToolboxApp().run()
