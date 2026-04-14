import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

try:
    import json
except Exception:
    json = None

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


from apps.installed_apps._mono_ui import CHAR_ADVANCE, CHAR_HEIGHT, DISPLAY_HEIGHT, DISPLAY_WIDTH, MonoCanvas, clip_text_px
from apps.root import calculate as calculate_app
from apps.root.function_store import ensure_default_functions, get_function, list_default_functions, list_user_functions
from data_modules.math_symbols import normalize_expression, normalize_pi_token
from data_modules.object_handler import form, form_refresh, keyin, keymap, keypad_state_manager, keypad_state_manager_reset, nav, typer
from process_modules.keypad_modes import reset_mode, should_auto_reset_after_input, toggle_mode_lock
from process_modules.navigation import request_navigation_from_key
from process_modules.ui_context import set_active_view


VIEW_SHEET = "sheet"
VIEW_TOOLBOX = "toolbox"
VIEW_FUNCTION_LIST = "function_list"
VIEW_ARG_MAP = "arg_map"
VIEW_EXPR = "expr"
VIEW_INSERT = "insert"
VIEW_MESSAGE = "message"

TOOLBOX_CUSTOM = "Custom Formula"
TOOLBOX_USER = "User Functions"
TOOLBOX_DEFAULT = "Default Functions"
TOOLBOX_VIEW = "View Formula"
TOOLBOX_CLEAR = "Clear Formula"

HEADER_H = 11
FOOTER_H = 8
ROW_H = 10
LIST_TOP = HEADER_H + 2
LIST_BOTTOM = DISPLAY_HEIGHT - FOOTER_H - 2
VISIBLE_LIST_ROWS = max(1, (LIST_BOTTOM - LIST_TOP + 1) // ROW_H)
FIELD_LABEL_W = 42
FIELD_X = FIELD_LABEL_W + 4
FIELD_W = DISPLAY_WIDTH - FIELD_X - 5
CURSOR_BLINK_MS = 450

ROW_COUNT = 100
COLUMN_COUNT = 8
VISIBLE_ROWS = 4
VISIBLE_COLS = 4
INPUT_COLS = 10
ROW_HEADER_W = 30
STATE_PATHS = ("/db/spreadsheet_state.json", "db/spreadsheet_state.json")
STATE_IDLE_FLUSH_MS = 600
INPUT_POLL_SEC = 0.01

_BASE_COLUMN_LABELS = tuple(chr(ord("A") + index) for index in range(COLUMN_COUNT))


def _ticks_ms():
    if hasattr(time, "ticks_ms"):
        try:
            return int(time.ticks_ms())
        except Exception:
            pass
    try:
        return int(time.monotonic() * 1000)
    except Exception:
        return int(time.time() * 1000)


def _sleep_s(seconds):
    try:
        time.sleep(float(seconds))
    except Exception:
        pass


def _load_json_from_paths(paths):
    if json is None:
        return None
    for path in paths:
        try:
            with open(path, "r") as handle:
                return json.load(handle)
        except Exception:
            pass
    return None


def _save_json_to_paths(paths, payload):
    if json is None:
        return False
    for path in paths:
        try:
            with open(path, "w") as handle:
                json.dump(payload, handle)
            return True
        except Exception:
            pass
    return False


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


def _copy_table_keys():
    copied = []
    for row in getattr(form, "table_keys", []) or []:
        if isinstance(row, (list, tuple)):
            copied.append(list(row))
    return copied


def _capture_form_state():
    return {
        "ui_style": getattr(form, "ui_style", "classic"),
        "focus_inputs_only": getattr(form, "focus_inputs_only", False),
        "blink_cursor": getattr(form, "blink_cursor", False),
        "title": getattr(form, "title", ""),
        "input_cols": getattr(form, "input_cols", 19),
        "form_list": list(getattr(form, "form_list", [])),
        "input_list": dict(getattr(form, "input_list", {})),
        "menu_cursor": getattr(form, "menu_cursor", 0),
        "table_headers": list(getattr(form, "table_headers", [])),
        "table_keys": _copy_table_keys(),
        "table_row_count": getattr(form, "table_row_count", 0),
        "table_visible_rows": getattr(form, "table_visible_rows", 4),
        "table_visible_cols": getattr(form, "table_visible_cols", 5),
        "table_input_cols": getattr(form, "table_input_cols", 10),
        "table_row_labels": list(getattr(form, "table_row_labels", [])),
        "table_row_header_w": getattr(form, "table_row_header_w", 0),
        "table_show_scrollbars": getattr(form, "table_show_scrollbars", False),
        "table_row_label_provider": getattr(form, "table_row_label_provider", None),
        "table_active_label": getattr(form, "table_active_label", ""),
        "table_row_header_title": getattr(form, "table_row_header_title", ""),
        "table_cursor_row": getattr(form, "table_cursor_row", 0),
        "table_cursor_col": getattr(form, "table_cursor_col", 0),
        "table_row_offset": getattr(form, "table_row_offset", 0),
        "table_col_offset": getattr(form, "table_col_offset", 0),
        "table_show_button": getattr(form, "table_show_button", True),
        "table_button_text": getattr(form, "table_button_text", "Ok"),
        "has_table_editor_text": hasattr(form, "table_editor_text"),
        "table_editor_text": getattr(form, "table_editor_text", ""),
        "table_editor_cursor": getattr(form, "table_editor_cursor", 0),
        "table_editor_display_position": getattr(form, "table_editor_display_position", 0),
    }


def _restore_form_state(previous):
    form.ui_style = previous["ui_style"]
    form.focus_inputs_only = previous["focus_inputs_only"]
    form.blink_cursor = previous["blink_cursor"]
    form.title = previous["title"]
    form.input_cols = previous["input_cols"]
    form.form_list = previous["form_list"]
    form.input_list = previous["input_list"]
    form.menu_cursor = previous["menu_cursor"]
    form.table_headers = previous["table_headers"]
    form.table_keys = previous["table_keys"]
    form.table_row_count = previous["table_row_count"]
    form.table_visible_rows = previous["table_visible_rows"]
    form.table_visible_cols = previous["table_visible_cols"]
    form.table_input_cols = previous["table_input_cols"]
    form.table_row_labels = previous["table_row_labels"]
    form.table_row_header_w = previous["table_row_header_w"]
    form.table_show_scrollbars = previous["table_show_scrollbars"]
    form.table_row_label_provider = previous["table_row_label_provider"]
    form.table_active_label = previous["table_active_label"]
    form.table_row_header_title = previous["table_row_header_title"]
    form.table_cursor_row = previous["table_cursor_row"]
    form.table_cursor_col = previous["table_cursor_col"]
    form.table_row_offset = previous["table_row_offset"]
    form.table_col_offset = previous["table_col_offset"]
    form.table_show_button = previous["table_show_button"]
    form.table_button_text = previous["table_button_text"]
    if previous["has_table_editor_text"]:
        form.table_editor_text = previous["table_editor_text"]
        form.table_editor_cursor = previous["table_editor_cursor"]
        form.table_editor_display_position = previous["table_editor_display_position"]
    else:
        for attr_name in ("table_editor_text", "table_editor_cursor", "table_editor_display_position"):
            if hasattr(form, attr_name):
                delattr(form, attr_name)
    form.update()
    form_refresh.refresh(state=nav.current_state())


def _read_key(idle_callback=None):
    _sleep_s(max(0.02, float(getattr(typer, "debounce_delay_time", 0.02) or 0.02)))
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


class _SpreadsheetApp:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.previous_form = _capture_form_state()
        self.view = VIEW_SHEET
        self.rows = [["" for _col in range(COLUMN_COUNT)] for _row in range(ROW_COUNT)]
        self.column_formulas = [None for _col in range(COLUMN_COUNT)]
        self.cursor_row = 0
        self.cursor_col = 0

        self.toolbox_index = 0
        self.function_scope = "user"
        self.function_index = 0
        self.arg_map_index = 0
        self.selected_function_name = ""
        self.selected_function_row = None
        self.arg_sources = []

        self.editor = None
        self.editor_target_col = 0
        self._calculate_save_restore = None

        self.message_title = ""
        self.message_lines = []
        self.message_return_view = VIEW_SHEET

        self._state_cache = None
        self._state_pending = False
        self._state_pending_since = 0
        self._eval_safe_globals = None
        self.sheet_edit_mode = False
        self.table_editor_text = ""
        self.table_editor_cursor = 0
        self.table_editor_display_position = 0

    def _column_label(self, col_index):
        if 0 <= int(col_index) < len(_BASE_COLUMN_LABELS):
            return _BASE_COLUMN_LABELS[int(col_index)]
        return "C{}".format(int(col_index) + 1)

    def _cell_ref(self, row_index, col_index):
        return "{}{}".format(self._column_label(col_index), int(row_index) + 1)

    def _row_header_label(self, row_index, selected_col):
        return self._cell_ref(row_index, selected_col)

    def _toolbox_items(self):
        items = [TOOLBOX_CUSTOM, TOOLBOX_USER, TOOLBOX_DEFAULT]
        if self._active_formula() is not None:
            items.extend([TOOLBOX_VIEW, TOOLBOX_CLEAR])
        return items

    def _serialize_state(self):
        rows = []
        for row_index in range(ROW_COUNT):
            source = self.rows[row_index] if row_index < len(self.rows) else []
            row = []
            for col_index in range(COLUMN_COUNT):
                value = source[col_index] if col_index < len(source) else ""
                row.append(str(value or ""))
            rows.append(row)

        formulas = []
        for col_index in range(COLUMN_COUNT):
            formulas.append(self._serialize_formula(self.column_formulas[col_index]))

        return {
            "rows": rows,
            "column_formulas": formulas,
            "cursor_row": int(self.cursor_row or 0),
            "cursor_col": int(self.cursor_col or 0),
        }

    def _serialize_formula(self, spec):
        if not isinstance(spec, dict):
            return None

        spec_type = str(spec.get("type") or "")
        if spec_type == "expression":
            payload = {
                "type": "expression",
                "expression": str(spec.get("expression") or ""),
            }
            state = spec.get("expression_state")
            if isinstance(state, dict):
                payload["expression_state"] = state
            return payload

        if spec_type == "function":
            return {
                "type": "function",
                "scope": "default" if str(spec.get("scope") or "") == "default" else "user",
                "name": str(spec.get("name") or ""),
                "arg_columns": [int(value) for value in (spec.get("arg_columns") or [])],
            }

        return None

    def _normalize_formula(self, spec):
        if not isinstance(spec, dict):
            return None

        spec_type = str(spec.get("type") or "")
        if spec_type == "expression":
            payload = {
                "type": "expression",
                "expression": str(spec.get("expression") or "").strip(),
            }
            state = spec.get("expression_state")
            if isinstance(state, dict):
                payload["expression_state"] = state
            if payload["expression"] == "" and "expression_state" not in payload:
                return None
            return payload

        if spec_type == "function":
            name = str(spec.get("name") or "").strip()
            if name == "":
                return None
            arg_columns = []
            for value in spec.get("arg_columns") or []:
                try:
                    index = int(value)
                except Exception:
                    continue
                if 0 <= index < COLUMN_COUNT:
                    arg_columns.append(index)
            return {
                "type": "function",
                "scope": "default" if str(spec.get("scope") or "") == "default" else "user",
                "name": name,
                "arg_columns": arg_columns,
            }

        return None

    def _load_state(self):
        payload = _load_json_from_paths(STATE_PATHS)
        if isinstance(payload, dict):
            raw_rows = payload.get("rows")
            if isinstance(raw_rows, list):
                self.rows = []
                for row_index in range(ROW_COUNT):
                    source = raw_rows[row_index] if row_index < len(raw_rows) and isinstance(raw_rows[row_index], list) else []
                    row = []
                    for col_index in range(COLUMN_COUNT):
                        value = source[col_index] if col_index < len(source) else ""
                        row.append(str(value or ""))
                    self.rows.append(row)

            raw_formulas = payload.get("column_formulas")
            formulas = []
            for col_index in range(COLUMN_COUNT):
                raw_spec = raw_formulas[col_index] if isinstance(raw_formulas, list) and col_index < len(raw_formulas) else None
                formulas.append(self._normalize_formula(raw_spec))
            self.column_formulas = formulas

            try:
                self.cursor_row = max(0, min(int(payload.get("cursor_row", 0) or 0), ROW_COUNT - 1))
            except Exception:
                self.cursor_row = 0
            try:
                self.cursor_col = max(0, min(int(payload.get("cursor_col", 0) or 0), COLUMN_COUNT - 1))
            except Exception:
                self.cursor_col = 0

        self._state_cache = self._serialize_state()
        self._state_pending = False
        self._state_pending_since = 0

    def _write_state(self):
        payload = self._serialize_state()
        if payload == self._state_cache:
            return True
        if _save_json_to_paths(STATE_PATHS, payload):
            self._state_cache = payload
            return True
        return False

    def _mark_state_dirty(self):
        self._state_pending = True
        self._state_pending_since = _ticks_ms()

    def _flush_pending_state(self, force=False):
        if not self._state_pending:
            return False
        if not force and (_ticks_ms() - int(self._state_pending_since or 0)) < STATE_IDLE_FLUSH_MS:
            return False
        saved = self._write_state()
        if saved:
            self._state_pending = False
            self._state_pending_since = 0
        return saved

    def _header_labels(self):
        labels = []
        for col_index in range(COLUMN_COUNT):
            label = self._column_label(col_index)
            if self.column_formulas[col_index] is not None:
                label += "*"
            labels.append(label)
        return labels

    def _active_cell(self):
        row = max(0, min(int(getattr(form, "table_cursor_row", self.cursor_row) or 0), ROW_COUNT - 1))
        col = max(0, min(int(getattr(form, "table_cursor_col", self.cursor_col) or 0), COLUMN_COUNT - 1))
        return row, col

    def _active_formula(self):
        _row, col = self._active_cell()
        return self.column_formulas[col]

    def _active_formula_name(self):
        spec = self._active_formula()
        if not isinstance(spec, dict):
            return "Manual Column"
        if str(spec.get("type") or "") == "function":
            return str(spec.get("name") or "Formula")
        return "Custom Formula"

    def _formula_summary(self, col_index):
        spec = self.column_formulas[col_index]
        if not isinstance(spec, dict):
            return self._column_label(col_index) + " is manual"

        spec_type = str(spec.get("type") or "")
        if spec_type == "function":
            function_row = get_function(spec.get("name"), scope=spec.get("scope"))
            variables = list(function_row.get("variables") or []) if function_row is not None else []
            if variables:
                parts = []
                for arg_index, name in enumerate(variables):
                    source_col = spec.get("arg_columns", [])
                    source_index = source_col[arg_index] if arg_index < len(source_col) else 0
                    parts.append("{}={}".format(name, self._column_label(source_index)))
                return "{} -> {}({})".format(
                    self._column_label(col_index),
                    spec.get("name"),
                    ", ".join(parts),
                )
            return "{} -> {}".format(self._column_label(col_index), spec.get("name"))

        expression = str(spec.get("expression") or "").strip()
        if expression == "":
            expression = "<empty>"
        return "{} = {}".format(self._column_label(col_index), expression)

    def _column_index_from_label(self, label):
        label = str(label or "").strip().upper()
        for col_index in range(COLUMN_COUNT):
            if self._column_label(col_index).upper() == label:
                return col_index
        return None

    def _function_formula_text(self, spec):
        name = str(spec.get("name") or "").strip()
        if name == "":
            return ""

        function_row = get_function(name, scope=spec.get("scope"))
        arg_columns = list(spec.get("arg_columns") or [])
        arg_count = len(function_row.get("variables") or []) if function_row is not None else len(arg_columns)
        args = []
        for arg_index in range(arg_count):
            source_col = arg_columns[arg_index] if arg_index < len(arg_columns) else 0
            try:
                source_col = int(source_col)
            except Exception:
                source_col = 0
            if 0 <= source_col < COLUMN_COUNT:
                args.append(self._column_label(source_col))
        return "{}({})".format(name, ", ".join(args))

    def _formula_input_text(self, col_index):
        spec = self.column_formulas[col_index]
        if not isinstance(spec, dict):
            return ""
        if str(spec.get("type") or "") == "function":
            return self._function_formula_text(spec)
        return str(spec.get("expression") or "").strip()

    def _formula_edit_text(self, col_index):
        formula_text = self._formula_input_text(col_index)
        if formula_text == "":
            return ""
        return "=" + formula_text

    def _cell_preview_text(self, row_index, col_index):
        if self.column_formulas[col_index] is not None:
            return self._cell_display(row_index, col_index, {})
        return str(self.rows[row_index][col_index] or "")

    def _cell_edit_text(self, row_index, col_index):
        if self.column_formulas[col_index] is not None:
            return self._formula_edit_text(col_index)
        return str(self.rows[row_index][col_index] or "")

    def _sync_table_editor_view(self, prefer_end=False):
        text_value = str(self.table_editor_text or "")
        max_cursor = len(text_value)
        if prefer_end:
            self.table_editor_cursor = max_cursor
        else:
            self.table_editor_cursor = min(max(0, int(self.table_editor_cursor or 0)), max_cursor)

        visible_chars = max(1, INPUT_COLS)
        max_display = max(0, len(text_value) - visible_chars)
        self.table_editor_display_position = min(
            max(0, int(self.table_editor_display_position or 0)),
            max_display,
        )
        if self.table_editor_cursor < self.table_editor_display_position:
            self.table_editor_display_position = self.table_editor_cursor
        elif self.table_editor_cursor > self.table_editor_display_position + visible_chars:
            self.table_editor_display_position = self.table_editor_cursor - visible_chars

    def _refresh_table_editor_preview(self):
        row, col = self.cursor_row, self.cursor_col
        self.table_editor_text = self._cell_preview_text(row, col)
        self.table_editor_cursor = 0
        self.table_editor_display_position = 0
        self._sync_table_editor_view(prefer_end=False)

    def _enter_sheet_edit(self):
        self.sheet_edit_mode = True
        self.table_editor_text = self._cell_edit_text(self.cursor_row, self.cursor_col)
        self.table_editor_display_position = 0
        self._sync_table_editor_view(prefer_end=True)

    def _prepare_eval_globals(self):
        calculate_app._ensure_functions_loaded()
        self._eval_safe_globals = dict(calculate_app.SAFE_GLOBALS)

    def _parse_manual_number(self, text_value):
        text_value = str(text_value or "").strip()
        if text_value == "":
            return 0.0
        expression = normalize_expression(text_value)
        value = eval(expression, self._eval_safe_globals, {})
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        raise ValueError("Non numeric")

    def _row_has_manual_data(self, row_index, exclude_col=None):
        row = self.rows[row_index] if 0 <= row_index < len(self.rows) else []
        for col_index in range(COLUMN_COUNT):
            if exclude_col is not None and col_index == exclude_col:
                continue
            value = row[col_index] if col_index < len(row) else ""
            if str(value or "").strip() != "":
                return True
        return False

    def _function_callable(self, spec):
        function_row = get_function(spec.get("name"), scope=spec.get("scope"))
        if function_row is None:
            raise ValueError("Missing function")
        return calculate_app.build_function(
            {
                "variables": list(function_row.get("variables") or []),
                "expression": str(function_row.get("expression") or ""),
            },
            self._eval_safe_globals,
        )

    def _expression_code(self, spec):
        return compile(str(spec.get("expression") or ""), "<sheet_formula>", "eval")

    def _reference_target(self, name, current_row):
        token = str(name or "").strip()
        if token == "":
            return None

        upper = token.upper()
        source_col = self._column_index_from_label(upper)
        if source_col is not None:
            return {
                "name": token,
                "kind": "column",
                "row": int(current_row),
                "col": source_col,
            }

        split_index = 0
        while split_index < len(upper) and upper[split_index].isalpha():
            split_index += 1
        if split_index <= 0 or split_index >= len(upper):
            return None

        row_text = upper[split_index:]
        if not row_text.isdigit():
            return None

        source_col = self._column_index_from_label(upper[:split_index])
        if source_col is None:
            return None

        row_number = int(row_text)
        if row_number <= 0 or row_number > ROW_COUNT:
            return None

        return {
            "name": token,
            "kind": "cell",
            "row": row_number - 1,
            "col": source_col,
        }

    def _expression_dependencies(self, spec, current_row):
        try:
            names = tuple(self._expression_code(spec).co_names)
        except Exception:
            names = ()

        dependencies = []
        seen_names = []
        for name in names:
            if name in seen_names:
                continue
            target = self._reference_target(name, current_row)
            if target is None:
                continue
            dependencies.append(target)
            seen_names.append(name)
        return dependencies

    def _expression_uses_relative_refs(self, spec):
        for target in self._expression_dependencies(spec, 0):
            if target["kind"] == "column":
                return True
        return False

    def _formula_validation_scope(self, target_col, spec):
        locals_scope = {}
        for target in self._expression_dependencies(spec, 0):
            if target["col"] == target_col:
                raise ValueError("Formula cannot use its own column")
            if target["kind"] == "column":
                locals_scope[target["name"]] = float(target["col"] + 2)
            else:
                locals_scope[target["name"]] = float(((target["row"] + 1) * 100) + target["col"] + 2)
        return locals_scope

    def _validate_formula_spec(self, target_col, spec):
        self._prepare_eval_globals()
        spec = self._normalize_formula(spec)
        if spec is None:
            raise ValueError("Formula is empty")

        spec_type = str(spec.get("type") or "")
        if spec_type == "function":
            arg_columns = [int(value) for value in (spec.get("arg_columns") or [])]
            if target_col in arg_columns:
                raise ValueError("Formula cannot use its own column")
            fn = self._function_callable(spec)
            value = fn(*[float(index + 2) for index in range(len(arg_columns))])
        else:
            value = eval(
                self._expression_code(spec),
                self._eval_safe_globals,
                self._formula_validation_scope(target_col, spec),
            )

        if isinstance(value, bool):
            value = float(value)
        if not isinstance(value, (int, float)):
            raise ValueError("Formula must return a number")
        return spec

    def _parse_function_formula(self, target_col, text_value):
        text_value = str(text_value or "").strip()
        if text_value == "" or not text_value.endswith(")"):
            return None

        open_paren = text_value.find("(")
        if open_paren <= 0:
            return None

        name = text_value[:open_paren].strip()
        function_row = get_function(name)
        if function_row is None:
            return None

        inner_text = text_value[open_paren + 1 : -1].strip()
        args = [] if inner_text == "" else [part.strip() for part in inner_text.split(",")]
        variables = list(function_row.get("variables") or [])
        if len(args) != len(variables):
            return None

        arg_columns = []
        for arg in args:
            source_col = self._column_index_from_label(arg)
            if source_col is None:
                return None
            arg_columns.append(source_col)

        return {
            "type": "function",
            "scope": "default" if str(function_row.get("scope") or "") == "default" else "user",
            "name": str(function_row.get("name") or name),
            "arg_columns": arg_columns,
        }

    def _parse_formula_input(self, col_index, text_value):
        formula_text = str(text_value or "").strip()
        if formula_text.startswith("="):
            formula_text = formula_text[1:].strip()
        if formula_text == "":
            raise ValueError("Formula is empty")

        function_spec = self._parse_function_formula(col_index, formula_text)
        if function_spec is not None:
            return self._validate_formula_spec(col_index, function_spec)

        return self._validate_formula_spec(
            col_index,
            {
                "type": "expression",
                "expression": normalize_expression(formula_text),
            },
        )

    def _clear_formula_column(self, col_index):
        if col_index < 0 or col_index >= COLUMN_COUNT:
            return
        self.column_formulas[col_index] = None
        for row_index in range(ROW_COUNT):
            self.rows[row_index][col_index] = ""

    def _save_sheet_input(self):
        row, col = self._active_cell()
        text_value = str(self.table_editor_text or "")
        saving_formula = self.column_formulas[col] is not None or text_value.strip().startswith("=")

        if saving_formula:
            stripped = text_value.strip()
            if self.column_formulas[col] is not None and stripped in ("", "="):
                self._clear_formula_column(col)
            else:
                try:
                    self.column_formulas[col] = self._parse_formula_input(col, text_value)
                except Exception as exc:
                    self._set_message("Invalid Formula", str(exc), return_view=VIEW_SHEET)
                    return False
        else:
            self.rows[row][col] = text_value.rstrip()

        self.sheet_edit_mode = False
        self.cursor_row = row
        self.cursor_col = col
        self._refresh_table_editor_preview()
        self._mark_state_dirty()
        return True

    def _handle_sheet_edit_input(self, token):
        token = normalize_pi_token(token)
        text_value = str(self.table_editor_text or "")

        if token == "nav_l":
            self.table_editor_cursor = max(0, self.table_editor_cursor - 1)
        elif token == "nav_r":
            self.table_editor_cursor = min(len(text_value), self.table_editor_cursor + 1)
        elif token == "nav_u":
            self.table_editor_cursor = 0
        elif token == "nav_d":
            self.table_editor_cursor = len(text_value)
        elif token == "nav_b":
            if self.table_editor_cursor > 0:
                self.table_editor_text = (
                    text_value[: self.table_editor_cursor - 1] + text_value[self.table_editor_cursor :]
                )
                self.table_editor_cursor -= 1
        elif token == "AC":
            self.table_editor_text = ""
            self.table_editor_cursor = 0
            self.table_editor_display_position = 0
        elif token not in ("", "toolbox"):
            insert_text = str(token or "")
            self.table_editor_text = (
                text_value[: self.table_editor_cursor] + insert_text + text_value[self.table_editor_cursor :]
            )
            self.table_editor_cursor += len(insert_text)

        self._sync_table_editor_view(prefer_end=False)

    def _numeric_cell_value(self, row_index, col_index, cache, active):
        cache_key = (row_index, col_index)
        if cache_key in cache:
            return cache[cache_key]
        if cache_key in active:
            raise ValueError("Circular formula")

        spec = self.column_formulas[col_index]
        if not isinstance(spec, dict):
            value = self._parse_manual_number(self.rows[row_index][col_index])
            cache[cache_key] = value
            return value

        active.add(cache_key)
        try:
            spec_type = str(spec.get("type") or "")
            if spec_type == "function":
                if not self._row_has_manual_data(row_index, exclude_col=col_index):
                    raise ValueError("Blank row")
                fn = self._function_callable(spec)
                args = []
                for source_col in spec.get("arg_columns") or []:
                    args.append(self._numeric_cell_value(row_index, int(source_col), cache, active))
                value = fn(*args)
            else:
                if self._expression_uses_relative_refs(spec) and not self._row_has_manual_data(
                    row_index,
                    exclude_col=col_index,
                ):
                    raise ValueError("Blank row")
                locals_scope = {}
                for target in self._expression_dependencies(spec, row_index):
                    locals_scope[target["name"]] = self._numeric_cell_value(
                        target["row"],
                        target["col"],
                        cache,
                        active,
                    )
                value = eval(self._expression_code(spec), self._eval_safe_globals, locals_scope)
            if isinstance(value, bool):
                value = float(value)
            elif not isinstance(value, (int, float)):
                raise ValueError("Non numeric")
            value = float(value)
        finally:
            active.discard(cache_key)

        cache[cache_key] = value
        return value

    def _format_value(self, value):
        text = calculate_app._format_result(value)
        if text.startswith("= "):
            return text[2:]
        return text

    def _cell_display(self, row_index, col_index, cache):
        spec = self.column_formulas[col_index]
        if not isinstance(spec, dict):
            return str(self.rows[row_index][col_index] or "")

        spec_type = str(spec.get("type") or "")
        if spec_type == "function" and not self._row_has_manual_data(row_index, exclude_col=col_index):
            return ""
        if spec_type != "function" and self._expression_uses_relative_refs(spec) and not self._row_has_manual_data(
            row_index,
            exclude_col=col_index,
        ):
            return ""

        try:
            value = self._numeric_cell_value(row_index, col_index, cache, set())
            return self._format_value(value)
        except Exception:
            return "ERR"

    def _sync_active_manual_cell(self):
        row, col = self._active_cell()
        self.cursor_row = row
        self.cursor_col = col
        if self.column_formulas[col] is not None:
            return False
        cell_key = form.active_input_key()
        if cell_key is None:
            return False
        self.rows[row][col] = str(form.input_list.get(cell_key, " ") or " ").rstrip()
        self._mark_state_dirty()
        return True

    def _configure_sheet_form(self):
        form.ui_style = "table"
        form.focus_inputs_only = False
        form.blink_cursor = False
        form.title = ""
        form.configure_table(
            headers=self._header_labels(),
            row_count=ROW_COUNT,
            values=self.rows,
            visible_rows=VISIBLE_ROWS,
            visible_cols=VISIBLE_COLS,
            input_cols=INPUT_COLS,
            row_header_w=ROW_HEADER_W,
            show_scrollbars=True,
            button_text="OK",
            show_button=True,
        )
        form.table_row_labels = []
        form.table_row_label_provider = self._row_header_label
        form.table_active_label = self._cell_ref(self.cursor_row, self.cursor_col)
        form.table_row_header_title = "#"
        form.table_cursor_row = self.cursor_row
        form.table_cursor_col = self.cursor_col
        if hasattr(form, "_sync_table_view"):
            form._sync_table_view()
        self._refresh_table_editor_preview()

    def _render_sheet(self, force=False):
        set_active_view("form")
        self._prepare_eval_globals()
        headers = self._header_labels()
        display_cache = {}

        if form._ui_style() not in ("table", "sheet", "grid") or not getattr(form, "table_keys", None):
            self._configure_sheet_form()
        else:
            form.table_headers = headers
            form.table_row_count = ROW_COUNT
            form.table_visible_rows = VISIBLE_ROWS
            form.table_visible_cols = VISIBLE_COLS
            form.table_input_cols = INPUT_COLS
            form.table_row_header_w = ROW_HEADER_W
            form.table_show_scrollbars = True
            form.table_row_labels = []
            form.table_row_label_provider = self._row_header_label
            form.table_row_header_title = "#"
            form.table_show_button = True
            form.table_button_text = "OK"

        if hasattr(form, "_sync_table_view"):
            form._sync_table_view()

        row_offset = max(0, int(getattr(form, "table_row_offset", 0) or 0))
        col_offset = max(0, int(getattr(form, "table_col_offset", 0) or 0))
        visible_rows = min(ROW_COUNT, max(1, int(getattr(form, "table_visible_rows", VISIBLE_ROWS) or VISIBLE_ROWS)))
        visible_cols = min(COLUMN_COUNT, max(1, int(getattr(form, "table_visible_cols", VISIBLE_COLS) or VISIBLE_COLS)))
        row_end = min(ROW_COUNT, row_offset + visible_rows)
        col_end = min(COLUMN_COUNT, col_offset + visible_cols)

        for row_index in range(row_offset, row_end):
            for col_index in range(col_offset, col_end):
                cell_key = form._table_cell_key(row_index, col_index) if hasattr(form, "_table_cell_key") else None
                if cell_key is None:
                    continue
                form.input_list[cell_key] = self._cell_display(row_index, col_index, display_cache).rstrip() + " "

        self.cursor_row = max(0, min(int(getattr(form, "table_cursor_row", self.cursor_row) or 0), ROW_COUNT - 1))
        self.cursor_col = max(0, min(int(getattr(form, "table_cursor_col", self.cursor_col) or 0), COLUMN_COUNT - 1))
        if not self.sheet_edit_mode:
            self._refresh_table_editor_preview()
        form.table_active_label = self._cell_ref(self.cursor_row, self.cursor_col)
        form.blink_cursor = self.sheet_edit_mode
        form.table_editor_text = self.table_editor_text
        form.table_editor_cursor = self.table_editor_cursor
        form.table_editor_display_position = self.table_editor_display_position
        form_refresh.refresh(state=nav.current_state(), force=force)

    def _idle_sheet(self):
        try:
            nav.maybe_hide()
        except Exception:
            pass
        try:
            self._flush_pending_state(force=False)
        except Exception:
            pass
        try:
            if hasattr(form_refresh, "idle"):
                form_refresh.idle()
        except Exception:
            pass

    def _idle_custom_view(self):
        try:
            nav.maybe_hide()
        except Exception:
            pass
        try:
            self._flush_pending_state(force=False)
        except Exception:
            pass
        if self.view == VIEW_EXPR and self.editor is not None:
            try:
                self.editor.idle()
            except Exception:
                pass

    def _draw_nav_overlay(self):
        state = str(nav.current_state() or "")
        visible = state != "" and nav.is_visible()
        nav.set_restore_callback(self._flush_bottom_page if visible else None)
        if visible:
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
        y = LIST_TOP
        for row_index in range(top_index, min(len(rows), top_index + VISIBLE_LIST_ROWS)):
            selected = row_index == selected_index
            if selected:
                self.canvas.fill_rect(1, y - 1, DISPLAY_WIDTH - 5, ROW_H, 1)
            self.canvas.draw_text(
                clip_text_px(str(rows[row_index] or ""), DISPLAY_WIDTH - 10),
                3,
                y,
                0 if selected else 1,
            )
            y += ROW_H
        self._draw_scrollbar(top_index, len(rows))
        self._draw_footer(footer_text)
        self._flush_screen()

    def _field_slice(self, value, cursor):
        value = str(value or "")
        visible_chars = max(1, (FIELD_W - 8) // CHAR_ADVANCE)
        cursor = max(0, min(int(cursor), len(value)))
        start = 0
        if cursor > visible_chars:
            start = cursor - visible_chars
        max_start = max(0, len(value) - visible_chars)
        start = min(start, max_start)
        return start, value[start : start + visible_chars], visible_chars

    def _render_arg_map(self):
        function_row = self.selected_function_row or {}
        variables = list(function_row.get("variables") or [])
        self.arg_map_index = max(0, min(self.arg_map_index, max(0, len(variables) - 1)))
        self.canvas.clear(0)
        self._draw_header("Map {}".format(self._column_label(self.editor_target_col)))
        y = LIST_TOP
        for index, name in enumerate(variables):
            selected = index == self.arg_map_index
            self.canvas.draw_text(clip_text_px(name, FIELD_LABEL_W - 4), 2, y + 1, 1)
            self.canvas.rect(FIELD_X, y, FIELD_W, CHAR_HEIGHT + 2, 1)
            value = "<{}>".format(self._column_label(self.arg_sources[index]))
            self.canvas.draw_text(clip_text_px(value, FIELD_W - 4), FIELD_X + 2, y + 1, 1)
            if selected:
                self.canvas.fill_rect(0, y - 1, 1, CHAR_HEIGHT + 4, 1)
            y += ROW_H
        self._draw_footer("OK apply")
        self._flush_screen()

    def _draw_editor_footer(self):
        if self.view != VIEW_EXPR:
            return
        if str(nav.current_state() or "") != "" and nav.is_visible():
            return
        footer_buf = bytearray(DISPLAY_WIDTH)
        text_value = clip_text_px("Formula {}".format(self._column_label(self.editor_target_col)), DISPLAY_WIDTH - 2)
        if text_value:
            for index, char in enumerate(text_value):
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

    def _render_message(self):
        set_active_view("form")
        self.canvas.clear(0)
        self._draw_header(self.message_title)
        for index, line in enumerate(self.message_lines[:4]):
            self.canvas.draw_text(clip_text_px(line, DISPLAY_WIDTH - 6), 3, 17 + index * 10, 1)
        self._draw_footer("OK continue")
        self._flush_screen()

    def _render_insert_picker(self):
        labels, _selected = self._insert_entries()
        self._draw_list("Insert", labels, self.function_index, "OK insert")

    def _render_formula_view(self):
        title = self._active_formula_name()
        self._set_message(title, self._formula_summary(self.editor_target_col), return_view=VIEW_TOOLBOX)
        self._render_message()

    def render(self, force=False):
        if self.view == VIEW_SHEET:
            self._render_sheet(force=force)
            return
        if self.view == VIEW_TOOLBOX:
            self._draw_list("Spreadsheet", self._toolbox_items(), self.toolbox_index, "OK open")
            return
        if self.view == VIEW_FUNCTION_LIST:
            rows = list_user_functions() if self.function_scope == "user" else list_default_functions()
            self._draw_list(
                "User Functions" if self.function_scope == "user" else "Default Functions",
                [row["name"] for row in rows] or ["No functions"],
                self.function_index,
                "OK choose",
            )
            return
        if self.view == VIEW_ARG_MAP:
            self._render_arg_map()
            return
        if self.view == VIEW_EXPR and self.editor is not None:
            self.editor.render()
            return
        if self.view == VIEW_INSERT:
            self._render_insert_picker()
            return
        if self.view == VIEW_MESSAGE:
            self._render_message()

    def _set_message(self, title, text_value, return_view=None):
        max_chars = max(1, (DISPLAY_WIDTH - 6) // CHAR_ADVANCE)
        self.message_title = str(title or "")
        self.message_lines = _wrap_text(text_value, max_chars)
        self.message_return_view = return_view or self.view
        self.view = VIEW_MESSAGE

    def _open_expression_editor(self):
        self.editor_target_col = self._active_cell()[1]
        spec = self.column_formulas[self.editor_target_col]
        if self._calculate_save_restore is None:
            self._calculate_save_restore = calculate_app._save_calculate_state
            calculate_app._save_calculate_state = lambda *_args, **_kwargs: None

        editor = calculate_app._MathEditor()
        if isinstance(spec, dict) and str(spec.get("type") or "") == "expression":
            expression_state = spec.get("expression_state")
            if isinstance(expression_state, dict):
                calculate_app._load_slot_from_state(editor.root, expression_state)
            else:
                expression_text = str(spec.get("expression") or "")
                if expression_text != "":
                    editor._insert_sequence([calculate_app.TokenNode(expression_text)])
        editor._set_cursor(editor.root, len(editor.root.items))
        editor._flush_bottom_page = self._draw_editor_footer
        self.editor = editor
        self.view = VIEW_EXPR

    def _available_source_columns(self, target_col):
        return [index for index in range(COLUMN_COUNT) if index != target_col] or [target_col]

    def _open_function_map(self, function_row, scope):
        self.editor_target_col = self._active_cell()[1]
        self.function_scope = scope
        self.selected_function_row = function_row
        self.selected_function_name = str(function_row.get("name") or "")
        variables = list(function_row.get("variables") or [])
        available = self._available_source_columns(self.editor_target_col)
        existing = self.column_formulas[self.editor_target_col]
        self.arg_sources = []
        for index, _name in enumerate(variables):
            default_source = available[min(index, len(available) - 1)]
            if (
                isinstance(existing, dict)
                and str(existing.get("type") or "") == "function"
                and str(existing.get("name") or "") == self.selected_function_name
                and str(existing.get("scope") or "") == scope
                and index < len(existing.get("arg_columns") or [])
            ):
                candidate = int(existing["arg_columns"][index])
                if candidate in available:
                    default_source = candidate
            self.arg_sources.append(default_source)
        self.arg_map_index = 0
        self.view = VIEW_ARG_MAP

    def _save_function_formula(self):
        if self.selected_function_row is None:
            return
        self.column_formulas[self.editor_target_col] = {
            "type": "function",
            "scope": self.function_scope,
            "name": self.selected_function_name,
            "arg_columns": list(self.arg_sources),
        }
        self.sheet_edit_mode = False
        self._refresh_table_editor_preview()
        self._mark_state_dirty()
        self.view = VIEW_SHEET
        self.render(force=True)

    def _save_expression_formula(self):
        expression, ok = self.editor._slot_to_expression(self.editor.root)
        if not ok:
            self._set_message("Invalid Formula", "Expression is incomplete", return_view=VIEW_EXPR)
            return

        try:
            spec = self._validate_formula_spec(
                self.editor_target_col,
                {
                    "type": "expression",
                    "expression": normalize_expression(expression),
                },
            )
        except Exception as exc:
            self._set_message("Invalid Formula", str(exc), return_view=VIEW_EXPR)
            return

        spec["expression_state"] = calculate_app._serialize_slot(self.editor.root)
        self.column_formulas[self.editor_target_col] = spec
        self.sheet_edit_mode = False
        self._refresh_table_editor_preview()
        self._mark_state_dirty()
        self.editor = None
        self.view = VIEW_SHEET
        self.render(force=True)

    def _clear_active_formula(self):
        _row, col = self._active_cell()
        self._clear_formula_column(col)
        self.sheet_edit_mode = False
        self._refresh_table_editor_preview()
        self._mark_state_dirty()
        self.view = VIEW_SHEET
        self.render(force=True)

    def _insert_entries(self):
        labels = ["[Columns]"]
        selected_rows = {}
        target_col = self.editor_target_col

        for source_col in range(COLUMN_COUNT):
            if source_col == target_col:
                continue
            selected_rows[len(labels)] = {
                "type": "text",
                "text": self._column_label(source_col),
            }
            labels.append(self._column_label(source_col))

        labels.append("[User Functions]")
        user_rows = list_user_functions()
        if user_rows:
            for row in user_rows:
                name = str(row.get("name") or "").strip()
                if name == "":
                    continue
                selected_rows[len(labels)] = {
                    "type": "function",
                    "name": name,
                    "arg_count": len(row.get("variables") or []),
                }
                labels.append(name)
        else:
            labels.append("No user functions")

        labels.append("[Default Functions]")
        default_rows = list_default_functions()
        if default_rows:
            for row in default_rows:
                name = str(row.get("name") or "").strip()
                if name == "":
                    continue
                selected_rows[len(labels)] = {
                    "type": "function",
                    "name": name,
                    "arg_count": len(row.get("variables") or []),
                }
                labels.append(name)
        else:
            labels.append("No default functions")

        return labels, selected_rows

    def _handle_sheet_token(self, token):
        if token == "back":
            nav.set_restore_callback(None)
            self._flush_pending_state(force=True)
            _restore_form_state(self.previous_form)
            request_navigation_from_key("back")

        if token == "home":
            nav.set_restore_callback(None)
            self._flush_pending_state(force=True)
            _restore_form_state(self.previous_form)
            request_navigation_from_key("home")

        if token == "settings":
            nav.set_restore_callback(None)
            self._flush_pending_state(force=True)
            _restore_form_state(self.previous_form)
            request_navigation_from_key("settings")

        if token == "off":
            self._flush_pending_state(force=True)
            return False

        if token in ("alpha", "beta"):
            keypad_state_manager(x=token)
            self.render(force=True)
            return True

        if token == "caps":
            keypad_state_manager(x="A")
            self.render(force=True)
            return True

        if token == "toolbox":
            if self.sheet_edit_mode:
                self.render(force=True)
                return True
            _row, col = self._active_cell()
            self.editor_target_col = col
            self.toolbox_index = 0
            self.view = VIEW_TOOLBOX
            self.render()
            return True

        if token in ("ok", "exe"):
            if self.sheet_edit_mode:
                self._save_sheet_input()
            else:
                self._enter_sheet_edit()
            self.render(force=True)
            return True

        if self.sheet_edit_mode:
            self._handle_sheet_edit_input(token)
            self.render(force=True)
            return True

        if token in ("nav_u", "nav_d", "nav_l", "nav_r"):
            form.update_buffer(token)
            self.cursor_row, self.cursor_col = self._active_cell()
            self._refresh_table_editor_preview()
            self.render(force=True)
            return True

        self.render(force=True)
        return True

    def _handle_toolbox_token(self, token):
        items = self._toolbox_items()
        if token == "back":
            self.view = VIEW_SHEET
            return
        if token == "nav_u":
            self.toolbox_index = (self.toolbox_index - 1) % len(items)
            return
        if token == "nav_d":
            self.toolbox_index = (self.toolbox_index + 1) % len(items)
            return
        if token not in ("ok", "exe"):
            return

        selected = items[self.toolbox_index]
        if selected == TOOLBOX_CUSTOM:
            self._open_expression_editor()
        elif selected == TOOLBOX_USER:
            self.function_scope = "user"
            self.function_index = 0
            self.view = VIEW_FUNCTION_LIST
        elif selected == TOOLBOX_DEFAULT:
            self.function_scope = "default"
            self.function_index = 0
            self.view = VIEW_FUNCTION_LIST
        elif selected == TOOLBOX_VIEW:
            self._set_message("Formula", self._formula_summary(self.editor_target_col), return_view=VIEW_TOOLBOX)
        elif selected == TOOLBOX_CLEAR:
            self._clear_active_formula()

    def _handle_function_list_token(self, token):
        rows = list_user_functions() if self.function_scope == "user" else list_default_functions()
        if token == "back":
            self.view = VIEW_TOOLBOX
            return
        if token == "nav_u" and rows:
            self.function_index = (self.function_index - 1) % len(rows)
            return
        if token == "nav_d" and rows:
            self.function_index = (self.function_index + 1) % len(rows)
            return
        if token not in ("ok", "exe") or not rows:
            return
        self.function_index = max(0, min(self.function_index, len(rows) - 1))
        self._open_function_map(rows[self.function_index], self.function_scope)

    def _handle_arg_map_token(self, token):
        variables = list((self.selected_function_row or {}).get("variables") or [])
        if token == "back":
            self.view = VIEW_FUNCTION_LIST
            return
        if token == "nav_u" and variables:
            self.arg_map_index = (self.arg_map_index - 1) % len(variables)
            return
        if token == "nav_d" and variables:
            self.arg_map_index = (self.arg_map_index + 1) % len(variables)
            return
        if token in ("nav_l", "nav_r") and variables:
            choices = self._available_source_columns(self.editor_target_col)
            current = self.arg_sources[self.arg_map_index]
            current_index = choices.index(current) if current in choices else 0
            delta = -1 if token == "nav_l" else 1
            self.arg_sources[self.arg_map_index] = choices[(current_index + delta) % len(choices)]
            return
        if token in ("ok", "exe"):
            self._save_function_formula()

    def _handle_expr_token(self, token):
        if token == "back":
            self.editor = None
            self.view = VIEW_TOOLBOX
            return
        if token == "toolbox":
            self.function_index = 0
            self.view = VIEW_INSERT
            return
        if token in ("ok", "exe"):
            self._save_expression_formula()
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

    def _handle_insert_token(self, token):
        labels, selected_rows = self._insert_entries()
        if token == "back":
            self.view = VIEW_EXPR
            return
        if token == "nav_u":
            self.function_index = (self.function_index - 1) % len(labels)
            return
        if token == "nav_d":
            self.function_index = (self.function_index + 1) % len(labels)
            return
        if token not in ("ok", "exe"):
            return
        selected = selected_rows.get(self.function_index)
        if selected is None:
            return
        self.view = VIEW_EXPR
        if selected["type"] == "text":
            self.editor.apply_pending_action({"type": "insert_text", "text": selected["text"]})
        else:
            self.editor.apply_pending_action(
                {
                    "type": "insert_function",
                    "name": selected["name"],
                    "arg_count": selected["arg_count"],
                }
            )

    def _handle_message_token(self, token):
        if token in ("back", "ok", "exe"):
            self.view = self.message_return_view

    def _handle_token(self, token):
        if self.view == VIEW_SHEET:
            return self._handle_sheet_token(token)
        if token == "off":
            self._flush_pending_state(force=True)
            return False
        if token == "settings":
            nav.set_restore_callback(None)
            self._flush_pending_state(force=True)
            _restore_form_state(self.previous_form)
            request_navigation_from_key("settings")
        if token == "home":
            nav.set_restore_callback(None)
            self._flush_pending_state(force=True)
            _restore_form_state(self.previous_form)
            request_navigation_from_key("home")
        if token in ("alpha", "beta") and self.view != VIEW_EXPR:
            keypad_state_manager(x=token)
            return True
        if token == "caps" and self.view != VIEW_EXPR:
            keypad_state_manager(x="A")
            return True
        if token == "":
            return True

        if self.view == VIEW_TOOLBOX:
            self._handle_toolbox_token(token)
        elif self.view == VIEW_FUNCTION_LIST:
            self._handle_function_list_token(token)
        elif self.view == VIEW_ARG_MAP:
            self._handle_arg_map_token(token)
        elif self.view == VIEW_EXPR and self.editor is not None:
            self._handle_expr_token(token)
        elif self.view == VIEW_INSERT:
            self._handle_insert_token(token)
        elif self.view == VIEW_MESSAGE:
            self._handle_message_token(token)
        return True

    def run(self):
        ensure_default_functions()
        keypad_state_manager_reset()
        self._load_state()
        self._configure_sheet_form()
        display.clear_display()
        previous_delay = getattr(typer, "debounce_delay_time", None)
        if previous_delay is not None:
            typer.debounce_delay_time = INPUT_POLL_SEC
        self.render(force=True)

        try:
            while True:
                idle_callback = self._idle_sheet if self.view == VIEW_SHEET else self._idle_custom_view
                token = _read_key(idle_callback=idle_callback)
                if self._handle_token(token) is False:
                    return
                self.render()
        finally:
            nav.set_restore_callback(None)
            self._flush_pending_state(force=True)
            if self._calculate_save_restore is not None:
                calculate_app._save_calculate_state = self._calculate_save_restore
                self._calculate_save_restore = None
            if previous_delay is not None:
                typer.debounce_delay_time = previous_delay
            _restore_form_state(self.previous_form)


def spreadsheet():
    _SpreadsheetApp().run()
