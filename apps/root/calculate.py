import st7565 as _display_driver
try:
    import json
except Exception:
    json = None

try:
    import os
except Exception:
    os = None

try:
    import time as _time
except Exception:
    _time = None

try:
    import tools

    if hasattr(_display_driver, "graphics") and not hasattr(
        _display_driver.graphics, "pixels_changed"
    ):
        _display_driver.graphics = tools.refresh(
            _display_driver.graphics,
            pixels_changed=200,
        )
except Exception:
    pass

from math import *

from apps.installed_apps._mono_ui import (
    CHAR_ADVANCE,
    CHAR_HEIGHT,
    DISPLAY_HEIGHT,
    DISPLAY_WIDTH,
    MonoCanvas,
    clip_text_px,
)
from data_modules.characters import Characters
from data_modules.db_instance import fun_db
from data_modules.math_symbols import PI_CHAR, normalize_expression, normalize_pi_token
from data_modules.object_handler import (
    app,
    data_bucket,
    display,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)
from process_modules.ui_context import set_active_view


_BASELINE = 6
_PLACEHOLDER_SCALE_PAD = 1
_FRACTION_PAD = 1
_FRACTION_GAP = 1
_FRACTION_OUTER_GAP = 1
_FRACTION_LINE_THICKNESS = 1
_MAIN_SCALE = 1
_SUB_SCALE = 1
_BORDER_PAD = 3
_WORK_LEFT = 8
_WORK_RIGHT_PAD = 8
_MESSAGE_TOP = 6
_MESSAGE_HEIGHT = 11
_ROOT_MIN_GAP = 1
_ROOT_BAR_GAP = 1
_ROOT_BAR_THICKNESS = 1
_ROOT_LEG_THICKNESS = 1
_ROOT_HOOK_THICKNESS = 2
_ROOT_INNER_GAP = 1
_EXPONENT_GAP = 1
_LOG_GAP = 1
_CURSOR_THICKNESS = 2
_CURSOR_BLINK_MS = 450
_EDITOR_BUCKET_KEY = "_calculate_editor"
_PENDING_BUCKET_KEY = "_calculate_pending_action"
_CALCULATE_STATE_PATHS = ("/db/calculate_state.json", "db/calculate_state.json")
_MODE_STATE_UPDATE = object()
_AUTO_CALL_TOKENS = {
    "sin": 1,
    "cos": 1,
    "tan": 1,
    "asin": 1,
    "acos": 1,
    "atan": 1,
}
_calculate_state_cache = None


def _ticks_ms():
    if _time is None:
        return 0
    try:
        return int(_time.ticks_ms())
    except AttributeError:
        pass
    try:
        return int(_time.monotonic() * 1000)
    except Exception:
        pass
    try:
        return int(_time.time() * 1000)
    except Exception:
        return 0


def build_function(func_def, safe_globals):
    vars_ = func_def["variables"]
    expr = normalize_expression(func_def["expression"])

    def generated_function(*args):
        if len(args) != len(vars_):
            raise ValueError("Wrong number of arguments")

        local_scope = {}
        for index, name in enumerate(vars_):
            local_scope[name] = args[index]

        return eval(expr, safe_globals, local_scope)

    return generated_function


FUNCTIONS = {}
ans = [0, 0]

_BASE_SAFE_GLOBALS = {
    "__builtins__": {},
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "asin": asin,
    "acos": acos,
    "atan": atan,
    "atan2": atan2,
    "sinh": sinh,
    "cosh": cosh,
    "tanh": tanh,
    "asinh": asinh,
    "acosh": acosh,
    "atanh": atanh,
    "exp": exp,
    "expm1": expm1,
    "log": log,
    "log10": log10,
    "log2": log2,
    "pow": pow,
    "sqrt": sqrt,
    "ceil": ceil,
    "floor": floor,
    "trunc": trunc,
    "modf": modf,
    "frexp": frexp,
    "ldexp": ldexp,
    "fmod": fmod,
    "fabs": fabs,
    "copysign": copysign,
    "degrees": degrees,
    "radians": radians,
    "erf": erf,
    "erfc": erfc,
    "gamma": gamma,
    "lgamma": lgamma,
    "isfinite": isfinite,
    "isinf": isinf,
    "isnan": isnan,
    "e": e,
    "pi": pi,
    PI_CHAR: pi,
}

SAFE_GLOBALS = {}


def load_all_functions():
    FUNCTIONS.clear()
    SAFE_GLOBALS.clear()
    SAFE_GLOBALS.update(_BASE_SAFE_GLOBALS)
    SAFE_GLOBALS["ans"] = ans[0]

    for row in fun_db.all():
        name = row.get("name")
        variables = row.get("variables")
        expression = row.get("expression")

        if not name or not variables or not expression:
            continue

        func_def = {
            "variables": variables,
            "expression": expression,
        }
        FUNCTIONS[name] = build_function(func_def, SAFE_GLOBALS)
        SAFE_GLOBALS[name] = FUNCTIONS[name]


class Slot:
    def __init__(self, owner=None, name=""):
        self.owner = owner
        self.name = name
        self.items = []
        self.width = 0
        self.height = 0
        self.baseline = 0
        self.x = 0
        self.y = 0
        self.positions = [0]


class TokenNode:
    def __init__(self, text):
        self.text = str(text)
        self.parent_slot = None
        self.width = 0
        self.height = 0
        self.baseline = 0
        self.x = 0
        self.y = 0


class FractionNode:
    def __init__(self):
        self.parent_slot = None
        self.numerator = Slot(self, "numerator")
        self.denominator = Slot(self, "denominator")
        self.width = 0
        self.height = 0
        self.baseline = 0
        self.x = 0
        self.y = 0


class PowerNode:
    def __init__(self):
        self.parent_slot = None
        self.base = Slot(self, "base")
        self.exponent = Slot(self, "exponent")
        self.width = 0
        self.height = 0
        self.baseline = 0
        self.x = 0
        self.y = 0
        self._base_top = 0
        self._exp_top = 0
        self._exp_x = 0


class RootNode:
    def __init__(self):
        self.parent_slot = None
        self.degree = Slot(self, "degree")
        self.radicand = Slot(self, "radicand")
        self.width = 0
        self.height = 0
        self.baseline = 0
        self.x = 0
        self.y = 0
        self._degree_top = 0
        self._degree_x = 0
        self._hook_start_x = 0
        self._hook_start_y = 0
        self._vertex_x = 0
        self._vertex_y = 0
        self._bar_start_x = 0
        self._bar_y = 0
        self._content_x = 0
        self._content_y = 0


class LogNode:
    def __init__(self):
        self.parent_slot = None
        self.base = Slot(self, "base")
        self.argument = Slot(self, "argument")
        self.width = 0
        self.height = 0
        self.baseline = 0
        self.x = 0
        self.y = 0
        self._label_scale = _MAIN_SCALE
        self._label_top = 0
        self._label_width = 0
        self._base_top = 0
        self._base_x = 0
        self._arg_top = 0
        self._arg_x = 0
        self._open_x = 0
        self._close_x = 0


def _insert_item(slot, index, item):
    index = max(0, min(int(index), len(slot.items)))
    item.parent_slot = slot
    slot.items.insert(index, item)


def _extend_slot(slot, items):
    for item in items:
        item.parent_slot = slot
        slot.items.append(item)


def _is_wordlike_token(text):
    text = str(text or "")
    if text == "":
        return False
    for char in text:
        if char == PI_CHAR:
            continue
        code = ord(char)
        is_digit = 48 <= code <= 57
        is_upper = 65 <= code <= 90
        is_lower = 97 <= code <= 122
        if not (is_digit or is_upper or is_lower or char in "._"):
            return False
    return True


def _format_result(value):
    try:
        return "= {:.12g}".format(value)
    except Exception:
        return "= {}".format(value)


def _load_json_from_paths(paths):
    if json is None:
        return None
    for path in paths:
        for candidate in (path, path + ".bak"):
            try:
                with open(candidate, "r") as fh:
                    return json.load(fh)
            except Exception:
                pass
    return None


def _remove_file(path):
    if os is None:
        return False
    try:
        os.remove(path)
        return True
    except Exception:
        return False


def _replace_file(src, dst):
    if os is None:
        return False
    try:
        os.rename(src, dst)
        return True
    except Exception:
        try:
            os.remove(dst)
        except Exception:
            pass
        try:
            os.rename(src, dst)
            return True
        except Exception:
            return False


def _save_json_to_paths(paths, payload):
    if json is None:
        return False
    for path in paths:
        temp_path = path + ".tmp"
        backup_path = path + ".bak"
        try:
            with open(temp_path, "w") as fh:
                json.dump(payload, fh)
        except Exception:
            _remove_file(temp_path)
            pass
            continue

        _replace_file(path, backup_path)
        if _replace_file(temp_path, path):
            return True
        _remove_file(temp_path)
    return False


def _child_slot_names(item):
    if isinstance(item, FractionNode):
        return ("numerator", "denominator")
    if isinstance(item, PowerNode):
        return ("base", "exponent")
    if isinstance(item, RootNode):
        return ("degree", "radicand")
    if isinstance(item, LogNode):
        return ("base", "argument")
    return ()


def _serialize_slot(slot):
    items = []
    for item in getattr(slot, "items", []):
        serialized = _serialize_item(item)
        if serialized is not None:
            items.append(serialized)
    return {"items": items}


def _serialize_item(item):
    if isinstance(item, TokenNode):
        return {"kind": "token", "text": str(item.text or "")}

    if isinstance(item, FractionNode):
        return {
            "kind": "fraction",
            "numerator": _serialize_slot(item.numerator),
            "denominator": _serialize_slot(item.denominator),
        }

    if isinstance(item, PowerNode):
        return {
            "kind": "power",
            "base": _serialize_slot(item.base),
            "exponent": _serialize_slot(item.exponent),
        }

    if isinstance(item, RootNode):
        return {
            "kind": "root",
            "degree": _serialize_slot(item.degree),
            "radicand": _serialize_slot(item.radicand),
        }

    if isinstance(item, LogNode):
        return {
            "kind": "log",
            "base": _serialize_slot(item.base),
            "argument": _serialize_slot(item.argument),
        }

    return None


def _load_slot_from_state(slot, state):
    slot.items = []
    if not isinstance(state, dict):
        return
    items = state.get("items")
    if not isinstance(items, list):
        return
    for item_state in items:
        item = _deserialize_item(item_state)
        if item is None:
            continue
        item.parent_slot = slot
        slot.items.append(item)


def _deserialize_item(state):
    if not isinstance(state, dict):
        return None

    kind = str(state.get("kind") or "")
    if kind == "token":
        return TokenNode(str(state.get("text") or ""))

    if kind == "fraction":
        item = FractionNode()
        _load_slot_from_state(item.numerator, state.get("numerator"))
        _load_slot_from_state(item.denominator, state.get("denominator"))
        return item

    if kind == "power":
        item = PowerNode()
        _load_slot_from_state(item.base, state.get("base"))
        _load_slot_from_state(item.exponent, state.get("exponent"))
        return item

    if kind == "root":
        item = RootNode()
        _load_slot_from_state(item.degree, state.get("degree"))
        _load_slot_from_state(item.radicand, state.get("radicand"))
        return item

    if kind == "log":
        item = LogNode()
        _load_slot_from_state(item.base, state.get("base"))
        _load_slot_from_state(item.argument, state.get("argument"))
        return item

    return None


def _find_slot_path(slot, target_slot):
    if slot is target_slot:
        return []

    for index, item in enumerate(getattr(slot, "items", [])):
        for child_name in _child_slot_names(item):
            child_slot = getattr(item, child_name, None)
            if child_slot is None:
                continue
            child_path = _find_slot_path(child_slot, target_slot)
            if child_path is not None:
                return [{"item": index, "slot": child_name}] + child_path
    return None


def _resolve_slot_path(root_slot, path):
    slot = root_slot
    if not isinstance(path, list):
        return slot

    for step in path:
        if not isinstance(step, dict):
            return root_slot
        try:
            item_index = int(step.get("item", -1))
        except Exception:
            return root_slot
        child_name = str(step.get("slot") or "")
        if item_index < 0 or item_index >= len(slot.items):
            return root_slot
        item = slot.items[item_index]
        child_slot = getattr(item, child_name, None)
        if child_slot is None:
            return root_slot
        slot = child_slot
    return slot


def _serialize_editor_state(editor):
    cursor_path = _find_slot_path(editor.root, editor.cursor_slot)
    if cursor_path is None:
        cursor_path = []
    return {
        "root": _serialize_slot(editor.root),
        "cursor_path": cursor_path,
        "cursor_index": int(getattr(editor, "cursor_index", 0) or 0),
        "scroll_x": int(getattr(editor, "scroll_x", 0) or 0),
        "scroll_y": int(getattr(editor, "scroll_y", 0) or 0),
        "message": str(getattr(editor, "message", "") or ""),
    }


def _restore_editor_from_state(state):
    if not isinstance(state, dict):
        return None

    editor = _MathEditor()
    _load_slot_from_state(editor.root, state.get("root"))
    editor.cursor_slot = _resolve_slot_path(editor.root, state.get("cursor_path") or [])
    try:
        cursor_index = int(state.get("cursor_index", 0) or 0)
    except Exception:
        cursor_index = 0
    editor.cursor_index = max(0, min(cursor_index, len(editor.cursor_slot.items)))
    try:
        editor.scroll_x = max(0, int(state.get("scroll_x", 0) or 0))
    except Exception:
        editor.scroll_x = 0
    try:
        editor.scroll_y = max(0, int(state.get("scroll_y", 0) or 0))
    except Exception:
        editor.scroll_y = 0
    editor.message = str(state.get("message", "") or "")
    editor._cursor_visible = True
    editor._cursor_last_toggle = _ticks_ms()
    return editor


def _load_saved_editor_state():
    global _calculate_state_cache

    state = _load_json_from_paths(_CALCULATE_STATE_PATHS)
    editor = _restore_editor_from_state(state)
    if editor is None:
        return None
    _calculate_state_cache = _serialize_editor_state(editor)
    return editor


def _save_calculate_state(editor):
    global _calculate_state_cache

    payload = _serialize_editor_state(editor)
    if payload == _calculate_state_cache:
        return
    if _save_json_to_paths(_CALCULATE_STATE_PATHS, payload):
        _calculate_state_cache = payload


class _MathEditor:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.root = Slot(name="expression")
        self.cursor_slot = self.root
        self.cursor_index = 0
        self.scroll_x = 0
        self.scroll_y = 0
        self.message = ""
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()

    def _reset_cursor_blink(self):
        self._cursor_visible = True
        self._cursor_last_toggle = _ticks_ms()

    def _update_cursor_blink(self):
        now = _ticks_ms()
        elapsed = now - self._cursor_last_toggle
        if elapsed < _CURSOR_BLINK_MS:
            return False
        toggles = max(1, elapsed // _CURSOR_BLINK_MS)
        changed = False
        if toggles % 2:
            self._cursor_visible = not self._cursor_visible
            changed = True
        self._cursor_last_toggle += toggles * _CURSOR_BLINK_MS
        return changed

    def idle(self):
        if self._update_cursor_blink():
            self.render()

    def _set_cursor(self, slot, index):
        self.cursor_slot = slot
        self.cursor_index = max(0, min(int(index), len(slot.items)))
        self._reset_cursor_blink()

    def _slot_scale(self, slot):
        owner = getattr(slot, "owner", None)
        if owner is None:
            return _MAIN_SCALE
        if isinstance(owner, FractionNode):
            return self._slot_scale(owner.parent_slot)
        if isinstance(owner, PowerNode):
            return self._slot_scale(owner.parent_slot)
        if isinstance(owner, LogNode):
            return self._slot_scale(owner.parent_slot)
        if isinstance(owner, RootNode):
            return self._slot_scale(owner.parent_slot)
        return self._slot_scale(owner.parent_slot)

    def _text_spacing(self, scale):
        return 1 if int(scale) <= 1 else 2

    def _text_height(self, scale):
        return CHAR_HEIGHT * int(scale)

    def _text_baseline(self, scale):
        scale = int(scale)
        return (_BASELINE + 1) * scale - 1

    def _text_width(self, text, scale):
        text = str(text or "")
        scale = int(scale)
        if text == "":
            return 0
        advance = (CHAR_ADVANCE - 1) * scale + self._text_spacing(scale)
        return (len(text) * advance) - self._text_spacing(scale)

    def _text_pixel_span(self, text, scale):
        text = str(text or "")
        scale = max(1, int(scale))
        if text == "":
            return (0, 0)

        spacing = self._text_spacing(scale)
        cursor_x = 0
        left = None
        right = None

        for char in text:
            glyph = Characters.Chr2bytes(Characters, char)
            for col_idx, col_bits in enumerate(glyph):
                if not col_bits:
                    continue
                px = cursor_x + (col_idx * scale)
                if left is None or px < left:
                    left = px
                col_right = px + scale - 1
                if right is None or col_right > right:
                    right = col_right
            cursor_x += ((CHAR_ADVANCE - 1) * scale) + spacing

        if left is None or right is None:
            return (0, max(0, self._text_width(text, scale) - 1))
        return (left, right)

    def _slot_plain_text(self, slot):
        parts = []
        for item in getattr(slot, "items", []):
            if not isinstance(item, TokenNode):
                return None
            parts.append(item.text)
        return "".join(parts)

    def _placeholder_width(self, scale):
        scale = int(scale)
        return max(8, self._text_width(" ", scale) + _PLACEHOLDER_SCALE_PAD)

    def _placeholder_height(self, scale):
        scale = int(scale)
        return max(7, self._text_height(scale))

    def _take_previous_atom(self, slot, index):
        index = max(0, min(int(index), len(slot.items)))
        if index <= 0:
            return []

        items = slot.items
        start = index - 1
        last = items[start]

        if isinstance(last, TokenNode) and last.text == ")":
            depth = 0
            match = -1
            cursor = start
            while cursor >= 0:
                item = items[cursor]
                if isinstance(item, TokenNode):
                    if item.text == ")":
                        depth += 1
                    elif item.text == "(":
                        depth -= 1
                        if depth == 0:
                            match = cursor
                            break
                cursor -= 1

            if match >= 0:
                start = match
                while start > 0:
                    prev_item = items[start - 1]
                    if isinstance(prev_item, TokenNode) and _is_wordlike_token(
                        prev_item.text
                    ):
                        start -= 1
                        continue
                    break
        elif isinstance(last, TokenNode) and _is_wordlike_token(last.text):
            while start > 0:
                prev_item = items[start - 1]
                if isinstance(prev_item, TokenNode) and _is_wordlike_token(
                    prev_item.text
                ):
                    start -= 1
                    continue
                break
        elif isinstance(last, TokenNode):
            return []

        extracted = items[start:index]
        del items[start:index]
        for item in extracted:
            item.parent_slot = None
        return extracted

    def _needs_implicit_multiplication(self, slot=None, index=None):
        slot = self.cursor_slot if slot is None else slot
        index = self.cursor_index if index is None else int(index)
        if index <= 0 or index > len(slot.items):
            return False

        previous = slot.items[index - 1]
        if isinstance(previous, TokenNode):
            return previous.text not in ("+", "-", "*", "/", "(", ",")
        return True

    def _collect_positions(self, slot, positions):
        positions.append((slot, 0))
        for index, item in enumerate(slot.items):
            if not isinstance(item, TokenNode):
                self._collect_inside_node(item, positions)
            positions.append((slot, index + 1))

    def _collect_inside_node(self, node, positions):
        if isinstance(node, FractionNode):
            self._collect_positions(node.numerator, positions)
            self._collect_positions(node.denominator, positions)
        elif isinstance(node, PowerNode):
            self._collect_positions(node.base, positions)
            self._collect_positions(node.exponent, positions)
        elif isinstance(node, RootNode):
            self._collect_positions(node.degree, positions)
            self._collect_positions(node.radicand, positions)
        elif isinstance(node, LogNode):
            self._collect_positions(node.base, positions)
            self._collect_positions(node.argument, positions)

    def _move_linear(self, step):
        step = int(step)
        slot = self.cursor_slot
        owner = getattr(slot, "owner", None)

        if isinstance(owner, FractionNode):
            parent_slot = getattr(owner, "parent_slot", None)
            if parent_slot is not None:
                try:
                    owner_index = parent_slot.items.index(owner)
                except Exception:
                    owner_index = -1

                if owner_index >= 0:
                    if step > 0 and slot is owner.numerator and self.cursor_index >= len(slot.items):
                        self._set_cursor(parent_slot, owner_index + 1)
                        return
                    if step < 0 and slot is owner.denominator and self.cursor_index <= 0:
                        self._set_cursor(parent_slot, owner_index)
                        return

        positions = []
        self._collect_positions(self.root, positions)
        if not positions:
            self._set_cursor(self.root, 0)
            return

        current = 0
        found = False
        for index, entry in enumerate(positions):
            if entry[0] is self.cursor_slot and entry[1] == self.cursor_index:
                current = index
                found = True
                break

        if not found:
            self._set_cursor(self.root, 0)
            return

        target = (current + step) % len(positions)
        self._set_cursor(positions[target][0], positions[target][1])

    def _parent_slot(self, slot):
        owner = getattr(slot, "owner", None)
        return getattr(owner, "parent_slot", None)

    def _is_ancestor_slot(self, maybe_ancestor, slot):
        current = self._parent_slot(slot)
        while current is not None:
            if current is maybe_ancestor:
                return True
            current = self._parent_slot(current)
        return False

    def _slot_cursor_box(self, slot):
        top = int(getattr(slot, "y", 0) or 0)
        if getattr(slot, "items", None):
            height = max(7, int(getattr(slot, "height", 0) or 0))
        else:
            height = max(7, self._placeholder_height(self._slot_scale(slot)))
        return top, height

    def _cursor_x_for(self, slot, index):
        positions = getattr(slot, "positions", None) or [getattr(slot, "x", 0)]
        if index < len(positions):
            return int(positions[index])
        return int(positions[-1])

    def _collect_cursor_targets(self, slot, targets):
        top, height = self._slot_cursor_box(slot)
        center_y = top + (height / 2.0)
        positions = getattr(slot, "positions", None) or [getattr(slot, "x", 0)]
        for index, x in enumerate(positions):
            targets.append(
                {
                    "slot": slot,
                    "index": index,
                    "x": int(x),
                    "top": top,
                    "height": height,
                    "center_y": center_y,
                }
            )

        for item in getattr(slot, "items", []):
            if isinstance(item, FractionNode):
                self._collect_cursor_targets(item.numerator, targets)
                self._collect_cursor_targets(item.denominator, targets)
            elif isinstance(item, PowerNode):
                self._collect_cursor_targets(item.base, targets)
                self._collect_cursor_targets(item.exponent, targets)
            elif isinstance(item, RootNode):
                self._collect_cursor_targets(item.degree, targets)
                self._collect_cursor_targets(item.radicand, targets)
            elif isinstance(item, LogNode):
                self._collect_cursor_targets(item.base, targets)
                self._collect_cursor_targets(item.argument, targets)

    def _prepare_layout(self):
        self._measure_slot(self.root)
        content_top = 1
        content_bottom = DISPLAY_HEIGHT - CHAR_HEIGHT - 6
        content_height = max(1, content_bottom - content_top + 1)
        top = content_top + max(0, (content_height - self.root.height) // 2)
        self._layout_slot(self.root, _WORK_LEFT, top, self.root.baseline)
        return content_top, content_bottom

    def _move_vertical(self, direction):
        direction = -1 if int(direction) < 0 else 1
        self._prepare_layout()

        current_x = self._cursor_x_for(self.cursor_slot, self.cursor_index)
        current_top, current_height = self._slot_cursor_box(self.cursor_slot)
        current_center_y = current_top + (current_height / 2.0)

        targets = []
        self._collect_cursor_targets(self.root, targets)

        candidates = []
        for target in targets:
            target_slot = target["slot"]
            target_index = target["index"]

            if target_slot is self.cursor_slot and target_index == self.cursor_index:
                continue
            if self._is_ancestor_slot(target_slot, self.cursor_slot):
                continue

            delta_y = target["center_y"] - current_center_y
            if direction > 0 and delta_y <= 0:
                continue
            if direction < 0 and delta_y >= 0:
                continue

            candidates.append(target)

        if not candidates:
            return

        aligned = [
            target
            for target in candidates
            if abs(target["x"] - current_x) <= (CHAR_ADVANCE * 2)
        ]
        if aligned:
            candidates = aligned

        best = min(
            candidates,
            key=lambda target: (
                abs(target["center_y"] - current_center_y),
                abs(target["x"] - current_x),
                0 if self._parent_slot(target["slot"]) is self._parent_slot(self.cursor_slot) else 1,
                abs(target["height"] - current_height),
            ),
        )
        self._set_cursor(best["slot"], best["index"])

    def _insert_sequence(self, items, cursor_index=None):
        slot = self.cursor_slot
        insert_at = self.cursor_index
        for offset, item in enumerate(items):
            _insert_item(slot, insert_at + offset, item)
        if cursor_index is None:
            cursor_index = insert_at + len(items)
        self._set_cursor(slot, cursor_index)
        self.message = ""

    def _insert_token(self, token):
        token = normalize_pi_token(token)
        if token == "":
            return
        if token == "tab":
            token = " "
        self._insert_sequence([TokenNode(token)])

    def _insert_function_call(self, func_name, arg_count=1):
        func_name = str(func_name or "").strip()
        arg_count = max(0, int(arg_count))
        if func_name == "":
            return

        items = []
        if self._needs_implicit_multiplication():
            items.append(TokenNode("*"))

        items.extend([TokenNode(func_name), TokenNode("(")])
        if arg_count <= 0:
            items.append(TokenNode(")"))
        else:
            for _ in range(arg_count - 1):
                items.append(TokenNode(","))
            items.append(TokenNode(")"))
        cursor_offset = 2
        if items and isinstance(items[0], TokenNode) and items[0].text == "*":
            cursor_offset += 1
        self._insert_sequence(items, cursor_index=self.cursor_index + cursor_offset)

    def _insert_fraction(self):
        slot = self.cursor_slot
        index = self.cursor_index
        extracted = self._take_previous_atom(slot, index)
        if extracted:
            index -= len(extracted)

        node = FractionNode()
        _insert_item(slot, index, node)

        if extracted:
            _extend_slot(node.numerator, extracted)
            self._set_cursor(node.denominator, 0)
        else:
            self._set_cursor(node.numerator, 0)

        self.message = ""

    def _insert_power(self):
        slot = self.cursor_slot
        index = self.cursor_index
        extracted = self._take_previous_atom(slot, index)
        if extracted:
            index -= len(extracted)

        node = PowerNode()
        _insert_item(slot, index, node)

        if extracted:
            _extend_slot(node.base, extracted)
            self._set_cursor(node.exponent, 0)
        else:
            self._set_cursor(node.base, 0)

        self.message = ""

    def _insert_root(self):
        slot = self.cursor_slot
        index = self.cursor_index
        if self._needs_implicit_multiplication(slot, index):
            _insert_item(slot, index, TokenNode("*"))
            index += 1
            self.cursor_index += 1
        node = RootNode()
        _insert_item(slot, index, node)
        _extend_slot(node.degree, [TokenNode("2")])
        self._set_cursor(node.radicand, 0)
        self.message = ""

    def _insert_log(self):
        slot = self.cursor_slot
        index = self.cursor_index
        if self._needs_implicit_multiplication(slot, index):
            _insert_item(slot, index, TokenNode("*"))
            index += 1
            self.cursor_index += 1
        node = LogNode()
        _insert_item(slot, index, node)
        _extend_slot(node.base, [TokenNode("10")])
        self._set_cursor(node.argument, 0)
        self.message = ""

    def _insert_pow10(self):
        slot = self.cursor_slot
        index = self.cursor_index

        _insert_item(slot, index, TokenNode("*"))
        node = PowerNode()
        _insert_item(slot, index + 1, node)
        _extend_slot(node.base, [TokenNode("10")])
        self._set_cursor(node.exponent, 0)
        self.message = ""

    def _backspace(self):
        slot = self.cursor_slot
        if self.cursor_index > 0:
            removed = slot.items.pop(self.cursor_index - 1)
            removed.parent_slot = None
            self._set_cursor(slot, self.cursor_index - 1)
            self.message = ""
            return

        owner = slot.owner
        if owner is None:
            return

        if slot.items:
            if isinstance(owner, FractionNode) and slot is owner.denominator:
                self._set_cursor(owner.numerator, len(owner.numerator.items))
                return
            if isinstance(owner, PowerNode) and slot is owner.exponent:
                self._set_cursor(owner.base, len(owner.base.items))
                return
            if isinstance(owner, LogNode) and slot is owner.argument:
                self._set_cursor(owner.base, len(owner.base.items))
                return
            if isinstance(owner, RootNode) and slot is owner.radicand:
                self._set_cursor(owner.degree, len(owner.degree.items))
                return

            parent_slot = owner.parent_slot
            if parent_slot is not None:
                self._set_cursor(parent_slot, parent_slot.items.index(owner))
            return

        parent_slot = owner.parent_slot
        if parent_slot is None:
            return

        owner_index = parent_slot.items.index(owner)
        del parent_slot.items[owner_index]
        owner.parent_slot = None
        self._set_cursor(parent_slot, owner_index)
        self.message = ""

    def _clear(self):
        self.root.items[:] = []
        self._set_cursor(self.root, 0)
        self.scroll_x = 0
        self.scroll_y = 0
        self.message = ""
        self._reset_cursor_blink()

    def _slot_to_expression(self, slot):
        if not slot.items:
            return "", False

        parts = []
        has_content = False
        for item in slot.items:
            expr, ok = self._item_to_expression(item)
            if not ok:
                return "", False
            parts.append(expr)
            if str(expr).strip() != "":
                has_content = True

        if not has_content:
            return "", False

        return "".join(parts), True

    def _item_to_expression(self, item):
        if isinstance(item, TokenNode):
            return normalize_expression(item.text), True

        if isinstance(item, FractionNode):
            numerator, ok_n = self._slot_to_expression(item.numerator)
            denominator, ok_d = self._slot_to_expression(item.denominator)
            if not ok_n or not ok_d:
                return "", False
            return "(({})/({}))".format(numerator, denominator), True

        if isinstance(item, PowerNode):
            base, ok_b = self._slot_to_expression(item.base)
            exponent, ok_e = self._slot_to_expression(item.exponent)
            if not ok_b or not ok_e:
                return "", False
            return "(({})**({}))".format(base, exponent), True

        if isinstance(item, RootNode):
            degree, ok_d = self._slot_to_expression(item.degree)
            radicand, ok_r = self._slot_to_expression(item.radicand)
            if not ok_r:
                return "", False
            if ok_d and degree.strip() != "":
                return "(({})**(1/({})))".format(radicand, degree), True
            return "(sqrt({}))".format(radicand), True

        if isinstance(item, LogNode):
            argument, ok_arg = self._slot_to_expression(item.argument)
            if not ok_arg:
                return "", False
            if item.base.items:
                base, ok_base = self._slot_to_expression(item.base)
                if not ok_base:
                    return "", False
                return "(log(({}),({})))".format(argument, base), True
            return "(log10({}))".format(argument), True

        return "", False

    def evaluate(self):
        expression, ok = self._slot_to_expression(self.root)
        if not ok:
            self.message = "ERR: incomplete"
            self._reset_cursor_blink()
            _save_calculate_state(self)
            return

        try:
            raw_res = eval(expression, SAFE_GLOBALS)
            ans[0] = raw_res
            SAFE_GLOBALS["ans"] = ans[0]
            self.message = _format_result(raw_res)
        except Exception as exc:
            self.message = "ERR: {}".format(exc)
        self._reset_cursor_blink()
        _save_calculate_state(self)

    def _measure_slot(self, slot):
        scale = self._slot_scale(slot)
        if not slot.items:
            slot.width = self._placeholder_width(scale)
            slot.height = self._placeholder_height(scale)
            slot.baseline = self._text_baseline(scale)
            return

        max_baseline = 0
        for item in slot.items:
            self._measure_item(item)
            if item.baseline > max_baseline:
                max_baseline = item.baseline

        width = 0
        height = 0
        for item in slot.items:
            width += item.width
            item_bottom = (max_baseline - item.baseline) + item.height
            if item_bottom > height:
                height = item_bottom

        slot.width = width
        slot.height = max(height, self._placeholder_height(scale))
        slot.baseline = max(max_baseline, self._text_baseline(scale))

    def _measure_item(self, item):
        if isinstance(item, TokenNode):
            scale = self._slot_scale(item.parent_slot)
            item.width = max(
                1,
                self._text_width(item.text, scale) + self._text_spacing(scale),
            )
            item.height = self._text_height(scale)
            item.baseline = self._text_baseline(scale)
            return

        if isinstance(item, FractionNode):
            self._measure_slot(item.numerator)
            self._measure_slot(item.denominator)
            inner_w = max(item.numerator.width, item.denominator.width)
            line_thickness = _FRACTION_LINE_THICKNESS
            item.width = inner_w + (_FRACTION_PAD * 2)
            item.baseline = _FRACTION_OUTER_GAP + item.numerator.height + _FRACTION_GAP
            item.height = (
                _FRACTION_OUTER_GAP
                + item.numerator.height
                + (_FRACTION_GAP * 2)
                + line_thickness
                + item.denominator.height
                + _FRACTION_OUTER_GAP
            )
            return

        if isinstance(item, PowerNode):
            self._measure_slot(item.base)
            self._measure_slot(item.exponent)
            base_scale = self._slot_scale(item.base)
            raise_px = max(4, base_scale * 4)
            exponent_floor = (
                item.base.baseline
                - raise_px
                + (self._text_height(base_scale) - self._text_baseline(base_scale))
            )
            exp_top = exponent_floor - item.exponent.height
            top_shift = -exp_top if exp_top < 0 else 0

            item._base_top = top_shift
            item._exp_top = exp_top + top_shift
            item._exp_x = item.base.width + _EXPONENT_GAP
            item.width = item._exp_x + item.exponent.width
            item.baseline = item._base_top + item.base.baseline
            item.height = max(
                item._base_top + item.base.height,
                item._exp_top + item.exponent.height,
            )
            return

        if isinstance(item, RootNode):
            self._measure_slot(item.degree)
            self._measure_slot(item.radicand)
            scale = self._slot_scale(item.radicand)
            bar_thickness = _ROOT_BAR_THICKNESS
            bar_gap = _ROOT_BAR_GAP
            leg_thickness = _ROOT_LEG_THICKNESS
            hook_dx = max(2, (max(4, scale * 2) + 1) // 2)
            hook_dy = max(3, (max(5, scale * 3) + 1) // 2)
            raise_px = max(4, scale * 4)
            content_pad = leg_thickness + _ROOT_INNER_GAP
            item._degree_x = 0
            item._hook_start_x = max(1, item.degree.width + 1 - hook_dx)
            item._content_y = max(
                bar_thickness + bar_gap + 1,
                item.degree.height - max(4, scale * 3),
            )
            item._bar_y = item._content_y - bar_gap - bar_thickness
            item._vertex_x = item._hook_start_x + hook_dx
            item._vertex_y = item._content_y + item.radicand.height - 1
            item._hook_start_y = max(
                item._bar_y + bar_thickness + 1,
                item._vertex_y - hook_dy,
            )
            item._bar_start_x = item._vertex_x
            item._content_x = item._bar_start_x + content_pad
            degree_bottom = item._content_y + item.radicand.height - raise_px
            item._degree_top = max(0, degree_bottom - item.degree.height)
            item.width = item._content_x + max(
                item.radicand.width,
                self._placeholder_width(scale) + _ROOT_MIN_GAP,
            )
            item.baseline = item._content_y + item.radicand.baseline
            item.height = max(
                item._degree_top + item.degree.height,
                item._vertex_y + 1,
            )
            return

        if isinstance(item, LogNode):
            self._measure_slot(item.base)
            self._measure_slot(item.argument)
            parent_scale = self._slot_scale(item.parent_slot)
            item._label_scale = max(_SUB_SCALE, parent_scale)
            item._label_width = self._text_width("log", item._label_scale)
            label_height = self._text_height(item._label_scale)
            label_baseline = self._text_baseline(item._label_scale)
            paren_width = self._text_width("(", item._label_scale)
            base_text = self._slot_plain_text(item.base)
            base_left = 0
            if base_text:
                base_left, _ = self._text_pixel_span(base_text, item._label_scale)

            item.baseline = max(label_baseline, item.argument.baseline)
            item._label_top = item.baseline - label_baseline
            item._arg_top = item.baseline - item.argument.baseline
            item._base_top = item._label_top + max(1, label_height // 2)
            item._base_x = max(0, item._label_width + _LOG_GAP - base_left)
            item._open_x = item._base_x + item.base.width
            item._arg_x = item._open_x + paren_width + _LOG_GAP
            item._close_x = item._arg_x + item.argument.width
            item.width = max(
                item._base_x + item.base.width,
                item._close_x + paren_width,
            )
            item.height = max(
                item._label_top + label_height,
                item._arg_top + item.argument.height,
                item._base_top + item.base.height,
            )

    def _layout_slot(self, slot, x, y, baseline):
        slot.x = int(x)
        slot.y = int(y)
        slot.baseline = int(baseline)

        if not slot.items:
            slot.positions = [slot.x]
            return

        current_x = slot.x
        positions = [current_x]
        for item in slot.items:
            self._layout_item(item, current_x, slot.y, slot.baseline)
            current_x += item.width
            positions.append(current_x)
        slot.positions = positions

    def _fraction_adjacent_operator_offset(self, item):
        if not isinstance(item, TokenNode):
            return 0

        token_text = str(getattr(item, "text", "") or "")
        if token_text not in ("+", "-", "*", "/", "="):
            return 0

        parent_slot = getattr(item, "parent_slot", None)
        slot_items = getattr(parent_slot, "items", None)
        if not slot_items:
            return 0

        try:
            item_index = slot_items.index(item)
        except Exception:
            return 0

        if item_index <= 0 or not isinstance(slot_items[item_index - 1], FractionNode):
            return 0

        scale = max(1, int(self._slot_scale(parent_slot)))
        operator_line_row = 3 * scale
        return max(0, int(getattr(item, "baseline", 0) or 0) - operator_line_row)

    def _layout_item(self, item, x, y, baseline):
        item.x = int(x)
        item.y = int(y + baseline - item.baseline)

        if isinstance(item, TokenNode):
            item.y += self._fraction_adjacent_operator_offset(item)
            return

        if isinstance(item, FractionNode):
            inner_w = item.width - (_FRACTION_PAD * 2)
            num_x = item.x + _FRACTION_PAD + max(0, (inner_w - item.numerator.width) // 2)
            den_x = item.x + _FRACTION_PAD + max(0, (inner_w - item.denominator.width) // 2)
            self._layout_slot(
                item.numerator,
                num_x,
                item.y + _FRACTION_OUTER_GAP,
                item.numerator.baseline,
            )
            den_y = item.y + item.baseline + _FRACTION_GAP + _FRACTION_LINE_THICKNESS
            self._layout_slot(
                item.denominator,
                den_x,
                den_y,
                item.denominator.baseline,
            )
            return

        if isinstance(item, PowerNode):
            self._layout_slot(
                item.base,
                item.x,
                item.y + item._base_top,
                item.base.baseline,
            )
            self._layout_slot(
                item.exponent,
                item.x + item._exp_x,
                item.y + item._exp_top,
                item.exponent.baseline,
            )
            return

        if isinstance(item, RootNode):
            self._layout_slot(
                item.degree,
                item.x + item._degree_x,
                item.y + item._degree_top,
                item.degree.baseline,
            )
            self._layout_slot(
                item.radicand,
                item.x + item._content_x,
                item.y + item._content_y,
                item.radicand.baseline,
            )
            return

        if isinstance(item, LogNode):
            self._layout_slot(
                item.base,
                item.x + item._base_x,
                item.y + item._base_top,
                item.base.baseline,
            )
            self._layout_slot(
                item.argument,
                item.x + item._arg_x,
                item.y + item._arg_top,
                item.argument.baseline,
            )

    def _pixel(self, x, y):
        if 0 <= int(x) < DISPLAY_WIDTH and 0 <= int(y) < DISPLAY_HEIGHT:
            self.canvas.pixel(int(x), int(y), 1)

    def _hline(self, x, y, width):
        x = int(x)
        y = int(y)
        width = int(width)
        if width <= 0 or y < 0 or y >= DISPLAY_HEIGHT:
            return
        start = max(0, x)
        end = min(DISPLAY_WIDTH, x + width)
        if end > start:
            self.canvas.hline(start, y, end - start, 1)

    def _vline(self, x, y, height):
        x = int(x)
        y = int(y)
        height = int(height)
        if height <= 0 or x < 0 or x >= DISPLAY_WIDTH:
            return
        start = max(0, y)
        end = min(DISPLAY_HEIGHT, y + height)
        if end > start:
            self.canvas.vline(x, start, end - start, 1)

    def _hline_thick(self, x, y, width, thickness=2):
        for offset in range(max(1, int(thickness))):
            self._hline(x, int(y) + offset, width)

    def _vline_thick(self, x, y, height, thickness=2):
        for offset in range(max(1, int(thickness))):
            self._vline(int(x) + offset, y, height)

    def _line(self, x0, y0, x1, y1):
        x0 = int(x0)
        y0 = int(y0)
        x1 = int(x1)
        y1 = int(y1)

        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            self._pixel(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = err * 2
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def _line_thick(self, x0, y0, x1, y1, thickness=2):
        for offset in range(max(1, int(thickness))):
            self._line(x0, int(y0) + offset, x1, int(y1) + offset)

    def _rect(self, x, y, width, height):
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            return
        self.canvas.rect(int(x), int(y), width, height, 1)

    def _fill_rect(self, x, y, width, height):
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            return
        self.canvas.fill_rect(int(x), int(y), width, height, 1)

    def _draw_scaled_text(self, text, x, y, scale=1, color=1, bold=False):
        text = str(text or "")
        scale = max(1, int(scale))
        spacing = self._text_spacing(scale)
        cursor_x = int(x)
        y = int(y)
        color = 1 if color else 0
        stroke = 1 if bold or scale > 1 else 0

        for char in text:
            glyph = Characters.Chr2bytes(Characters, char)
            for col_idx, col_bits in enumerate(glyph):
                px = cursor_x + (col_idx * scale)
                for bit_idx in range(CHAR_HEIGHT):
                    if not (col_bits & (1 << bit_idx)):
                        continue
                    py = y + (bit_idx * scale)
                    self.canvas.fill_rect(px, py, scale + stroke, scale, color)
            cursor_x += ((CHAR_ADVANCE - 1) * scale) + spacing

    def _draw_placeholder(self, slot, scroll_x, scroll_y):
        scale = self._slot_scale(slot)
        box_x = slot.x - scroll_x
        box_y = slot.y - scroll_y
        box_w = max(6, slot.width - 1)
        box_h = max(7, self._placeholder_height(scale))
        self._rect(box_x, box_y, box_w, box_h)

    def _render_slot(self, slot, scroll_x, scroll_y):
        if not slot.items:
            self._draw_placeholder(slot, scroll_x, scroll_y)
            return
        for item in slot.items:
            self._render_item(item, scroll_x, scroll_y)

    def _render_item(self, item, scroll_x, scroll_y):
        if isinstance(item, TokenNode):
            scale = self._slot_scale(item.parent_slot)
            self._draw_scaled_text(
                item.text,
                item.x - scroll_x,
                item.y - scroll_y,
                scale=scale,
                color=1,
                bold=scale > 1,
            )
            return

        if isinstance(item, FractionNode):
            self._render_slot(item.numerator, scroll_x, scroll_y)
            self._render_slot(item.denominator, scroll_x, scroll_y)
            self._hline_thick(
                item.x + _FRACTION_PAD - scroll_x,
                item.y + item.baseline - scroll_y,
                item.width - (_FRACTION_PAD * 2),
                thickness=_FRACTION_LINE_THICKNESS,
            )
            return

        if isinstance(item, PowerNode):
            self._render_slot(item.base, scroll_x, scroll_y)
            self._render_slot(item.exponent, scroll_x, scroll_y)
            return

        if isinstance(item, RootNode):
            self._render_slot(item.degree, scroll_x, scroll_y)
            self._render_slot(item.radicand, scroll_x, scroll_y)
            hook_start_x = item.x + item._hook_start_x - scroll_x
            hook_start_y = item.y + item._hook_start_y - scroll_y
            vertex_x = item.x + item._vertex_x - scroll_x
            vertex_y = item.y + item._vertex_y - scroll_y
            bar_y = item.y + item._bar_y - scroll_y
            self._line_thick(
                hook_start_x,
                hook_start_y,
                vertex_x,
                vertex_y,
                thickness=_ROOT_HOOK_THICKNESS,
            )
            self._vline_thick(
                vertex_x,
                bar_y,
                vertex_y - bar_y + 1,
                thickness=_ROOT_LEG_THICKNESS,
            )
            self._hline_thick(
                item.x + item._bar_start_x - scroll_x,
                bar_y,
                item.width - item._bar_start_x,
                thickness=_ROOT_BAR_THICKNESS,
            )
            return

        if isinstance(item, LogNode):
            self._draw_scaled_text(
                "log",
                item.x - scroll_x,
                item.y + item._label_top - scroll_y,
                scale=item._label_scale,
                color=1,
                bold=item._label_scale > 1,
            )
            self._render_slot(item.base, scroll_x, scroll_y)
            self._render_slot(item.argument, scroll_x, scroll_y)
            self._draw_scaled_text(
                "(",
                item.x + item._open_x - scroll_x,
                item.y + item._arg_top - scroll_y,
                scale=item._label_scale,
                color=1,
                bold=item._label_scale > 1,
            )
            self._draw_scaled_text(
                ")",
                item.x + item._close_x - scroll_x,
                item.y + item._arg_top - scroll_y,
                scale=item._label_scale,
                color=1,
                bold=item._label_scale > 1,
            )

    def _cursor_geometry(self):
        slot = self.cursor_slot
        if slot.positions:
            if self.cursor_index < len(slot.positions):
                x = slot.positions[self.cursor_index]
            else:
                x = slot.positions[-1]
        else:
            x = slot.x

        if slot.items:
            top = slot.y
            height = max(7, slot.height)
        else:
            top = slot.y
            height = max(7, self._placeholder_height(self._slot_scale(slot)))

        return x, top, height

    def _draw_cursor(self, cursor_x, cursor_y, cursor_h):
        for offset in range(_CURSOR_THICKNESS):
            self._vline(cursor_x + offset, cursor_y, cursor_h)

    def _draw_scrollbars(
        self,
        content_top,
        content_bottom,
        view_left,
        view_right,
        max_scroll_x,
        max_scroll_y,
    ):
        visible_width = max(1, view_right - view_left + 1)
        visible_height = max(1, content_bottom - content_top + 1)

        if max_scroll_x <= 0:
            h_thumb_x = None
            h_thumb_w = 0
        else:
            h_track_x = 0
            h_track_y = DISPLAY_HEIGHT - 1
            h_track_w = DISPLAY_WIDTH
            content_width = visible_width + max_scroll_x
            h_thumb_w = max(8, (h_track_w * visible_width) // max(1, content_width))
            h_thumb_w = min(h_track_w, h_thumb_w)
            h_thumb_range = max(0, h_track_w - h_thumb_w)
            h_thumb_x = h_track_x + (
                self.scroll_x * h_thumb_range // max(1, max_scroll_x)
            )
            self._fill_rect(h_thumb_x, h_track_y, h_thumb_w, 1)

        if max_scroll_y <= 0:
            v_thumb_y = None
            v_thumb_h = 0
        else:
            v_track_x = DISPLAY_WIDTH - 1
            v_track_y = 0
            v_track_h = max(1, content_bottom + 1)
            content_height = visible_height + max_scroll_y
            v_thumb_h = max(8, (v_track_h * visible_height) // max(1, content_height))
            v_thumb_h = min(v_track_h, v_thumb_h)
            v_thumb_range = max(0, v_track_h - v_thumb_h)
            v_thumb_y = v_track_y + (
                self.scroll_y * v_thumb_range // max(1, max_scroll_y)
            )
            self._fill_rect(v_track_x, v_thumb_y, 1, v_thumb_h)

    def _draw_bottom_answer(self):
        if not self.message:
            return
        self.canvas.draw_text(
            clip_text_px(self.message, DISPLAY_WIDTH - 2),
            1,
            DISPLAY_HEIGHT - CHAR_HEIGHT - 1,
            color=1,
        )

    def _nav_overlay(self):
        state = str(nav.current_state() or "")
        nav_overlay_visible = state != "" and nav.is_visible()
        nav.set_restore_callback(self.render if nav_overlay_visible else None)
        if state != "":
            nav.draw_state(state)

    def render(self):
        set_active_view("text")
        self.canvas.clear()

        content_top, content_bottom = self._prepare_layout()

        cursor_x, cursor_y, cursor_h = self._cursor_geometry()
        view_left = _WORK_LEFT
        view_right = DISPLAY_WIDTH - _WORK_RIGHT_PAD
        max_scroll_x = max(0, (self.root.x + self.root.width) - view_right)
        max_scroll_y = max(0, (self.root.y + self.root.height) - content_bottom)
        scroll_x = min(max(0, self.scroll_x), max_scroll_x)
        scroll_y = min(max(0, self.scroll_y), max_scroll_y)

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

        self.scroll_x = min(max(0, scroll_x), max_scroll_x)
        self.scroll_y = min(max(0, scroll_y), max_scroll_y)
        self._render_slot(self.root, self.scroll_x, self.scroll_y)

        cursor_view_x = cursor_x - self.scroll_x
        cursor_view_y = cursor_y - self.scroll_y
        self._update_cursor_blink()
        if self._cursor_visible:
            self._draw_cursor(cursor_view_x, cursor_view_y, cursor_h)
        self._draw_scrollbars(
            content_top,
            content_bottom,
            view_left,
            view_right,
            max_scroll_x,
            max_scroll_y,
        )
        self._draw_bottom_answer()
        self.canvas.flush()
        self._nav_overlay()

    def apply_pending_action(self, action):
        if not isinstance(action, dict):
            return
        action_type = str(action.get("type") or "")
        if action_type == "insert_function":
            self._insert_function_call(
                action.get("name", ""),
                action.get("arg_count", 0),
            )
        elif action_type == "insert_text":
            self._insert_token(action.get("text", ""))

    def handle_key(self, token):
        token = str(token or "")
        if token == "":
            self.render()
            return

        self._reset_cursor_blink()

        if token == "nav_l":
            self._move_linear(-1)
        elif token == "nav_r":
            self._move_linear(1)
        elif token == "nav_u":
            self._move_vertical(-1)
        elif token == "nav_d":
            self._move_vertical(1)
        elif token in ("nav_b", "undo"):
            self._backspace()
        elif token == "AC":
            self._clear()
        elif token == "fraction":
            self._insert_fraction()
        elif token == "pow":
            self._insert_power()
        elif token == "root":
            self._insert_root()
        elif token == "log":
            self._insert_log()
        elif token == "*pow(10, )":
            self._insert_pow10()
        elif token in _AUTO_CALL_TOKENS:
            self._insert_function_call(token, _AUTO_CALL_TOKENS[token])
        elif token == "copy":
            self.message = "COPY N/A"
        elif token == "paste":
            self.message = "PASTE N/A"
        else:
            self._insert_token(token)

        self.render()
        _save_calculate_state(self)


def _load_editor():
    editor = data_bucket.get(_EDITOR_BUCKET_KEY)
    if getattr(editor, "root", None) is None or not hasattr(editor, "render"):
        editor = _load_saved_editor_state()
        if editor is None:
            editor = _MathEditor()
        data_bucket[_EDITOR_BUCKET_KEY] = editor
    if not hasattr(editor, "scroll_y"):
        editor.scroll_y = 0
    if not hasattr(editor, "_cursor_visible"):
        editor._cursor_visible = True
    if not hasattr(editor, "_cursor_last_toggle"):
        editor._cursor_last_toggle = _ticks_ms()
    _save_calculate_state(editor)
    return editor


def _start_typing_with_editor_idle(editor):
    original_idle_tasks = getattr(typer, "_idle_tasks", None)
    keymap = getattr(typer, "keypad_map", None)
    before_state = str(getattr(keymap, "state", "") or "")
    before_locked = bool(nav.is_mode_locked())

    def _combined_idle_tasks():
        if callable(original_idle_tasks):
            original_idle_tasks()
        editor.idle()

    typer._idle_tasks = _combined_idle_tasks
    try:
        token = typer.start_typing()
    finally:
        typer._idle_tasks = original_idle_tasks

    if token in ("alpha", "beta"):
        keypad_state_manager(x=token)
        editor._reset_cursor_blink()
        return _MODE_STATE_UPDATE

    if token == "caps":
        keypad_state_manager(x="A")
        editor._reset_cursor_blink()
        return _MODE_STATE_UPDATE

    after_state = str(getattr(keymap, "state", "") or "")
    after_locked = bool(nav.is_mode_locked())
    if token == "" and (after_state != before_state or after_locked != before_locked):
        editor._reset_cursor_blink()
        return _MODE_STATE_UPDATE

    return token


def calculate():
    load_all_functions()
    keypad_state_manager_reset()
    set_active_view("text")
    display.clear_display()

    editor = _load_editor()
    pending_action = data_bucket.pop(_PENDING_BUCKET_KEY, None)
    if pending_action:
        editor.apply_pending_action(pending_action)
        _save_calculate_state(editor)

    editor.render()
    try:
        while True:
            token = _start_typing_with_editor_idle(editor)

            if token is None:
                editor.render()
                continue

            if token is _MODE_STATE_UPDATE or token == "":
                editor.render()
                continue

            if token == "toolbox":
                data_bucket[_EDITOR_BUCKET_KEY] = editor
                _save_calculate_state(editor)
                app.set_app_name("toolbox")
                app.set_group_name("root")
                break

            if token in ("ok", "exe"):
                editor.evaluate()
                editor.render()
                continue

            editor.handle_key(token)
    finally:
        _save_calculate_state(editor)
