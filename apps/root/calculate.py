import st7565 as _display_driver

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
    DISPLAY_WIDTH,
    MonoCanvas,
    clip_text_px,
)
from data_modules.db_instance import fun_db
from data_modules.object_handler import (
    app,
    display,
    keypad_state_manager,
    keypad_state_manager_reset,
    nav,
    typer,
)
from process_modules.ui_context import set_active_view


_BASELINE = 6
_PLACEHOLDER_W = 8
_PLACEHOLDER_H = 8
_FRACTION_PAD = 2
_FRACTION_GAP = 1
_EXP_RAISE = 4
_ROOT_SYMBOL_W = 8
_EXPR_HEIGHT = 46
_DIVIDER_Y = 46
_STATUS_Y = 48
_MESSAGE_Y = 56


def build_function(func_def, safe_globals):
    vars_ = func_def["variables"]
    expr = func_def["expression"]

    def generated_function(*args):
        if len(args) != len(vars_):
            raise ValueError("Wrong number of arguments")

        local_scope = {}
        for i in range(len(vars_)):
            local_scope[vars_[i]] = args[i]

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
        self.width = _PLACEHOLDER_W
        self.height = _PLACEHOLDER_H
        self.baseline = _BASELINE
        self.x = 0
        self.y = 0
        self.positions = [0]


class TokenNode:
    def __init__(self, text):
        self.text = str(text)
        self.parent_slot = None
        self.width = CHAR_ADVANCE
        self.height = CHAR_HEIGHT
        self.baseline = _BASELINE
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
        self.radicand = Slot(self, "radicand")
        self.width = 0
        self.height = 0
        self.baseline = 0
        self.x = 0
        self.y = 0
        self._content_x = _ROOT_SYMBOL_W
        self._content_y = 2


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
        if not (char.isalnum() or char in "._"):
            return False
    return True


def _format_result(value):
    try:
        return "= {:.12g}".format(value)
    except Exception:
        return "= {}".format(value)


class _MathEditor:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.root = Slot(name="expression")
        self.cursor_slot = self.root
        self.cursor_index = 0
        self.scroll_x = 0
        self.message = ""

    def _set_cursor(self, slot, index):
        self.cursor_slot = slot
        self.cursor_index = max(0, min(int(index), len(slot.items)))

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

        extracted = items[start:index]
        del items[start:index]
        for item in extracted:
            item.parent_slot = None
        return extracted

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
            self._collect_positions(node.radicand, positions)

    def _move_linear(self, step):
        positions = []
        self._collect_positions(self.root, positions)

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

        target = current + int(step)
        if target < 0:
            target = 0
        if target >= len(positions):
            target = len(positions) - 1

        self._set_cursor(positions[target][0], positions[target][1])

    def _move_vertical(self, direction):
        slot = self.cursor_slot
        owner = slot.owner
        target = None

        if isinstance(owner, FractionNode):
            if direction > 0 and slot is owner.numerator:
                target = owner.denominator
            elif direction < 0 and slot is owner.denominator:
                target = owner.numerator
        elif isinstance(owner, PowerNode):
            if direction > 0 and slot is owner.base:
                target = owner.exponent
            elif direction < 0 and slot is owner.exponent:
                target = owner.base

        if target is None:
            return

        source_len = len(slot.items)
        target_len = len(target.items)
        if source_len <= 0:
            target_index = 0
        else:
            ratio = self.cursor_index / float(source_len)
            target_index = int(round(ratio * target_len))

        self._set_cursor(target, target_index)

    def _insert_token(self, token):
        token = str(token or "")
        if token == "":
            return
        if token == "tab":
            token = " "

        _insert_item(self.cursor_slot, self.cursor_index, TokenNode(token))
        self._set_cursor(self.cursor_slot, self.cursor_index + 1)
        self.message = ""

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
        node = RootNode()
        _insert_item(slot, index, node)
        self._set_cursor(node.radicand, 0)
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
        self.message = ""

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
            return item.text, True

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
            radicand, ok_r = self._slot_to_expression(item.radicand)
            if not ok_r:
                return "", False
            return "(sqrt({}))".format(radicand), True

        return "", False

    def evaluate(self):
        expression, ok = self._slot_to_expression(self.root)
        if not ok:
            self.message = "ERR: incomplete"
            return

        try:
            raw_res = eval(expression, SAFE_GLOBALS)
            ans[0] = raw_res
            SAFE_GLOBALS["ans"] = ans[0]
            self.message = _format_result(raw_res)
        except Exception as exc:
            self.message = "ERR: {}".format(exc)

    def _measure_slot(self, slot):
        if not slot.items:
            slot.width = _PLACEHOLDER_W
            slot.height = _PLACEHOLDER_H
            slot.baseline = _BASELINE
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
        slot.height = height
        slot.baseline = max_baseline

    def _measure_item(self, item):
        if isinstance(item, TokenNode):
            item.width = max(CHAR_ADVANCE, len(item.text) * CHAR_ADVANCE)
            item.height = CHAR_HEIGHT
            item.baseline = _BASELINE
            return

        if isinstance(item, FractionNode):
            self._measure_slot(item.numerator)
            self._measure_slot(item.denominator)
            inner_w = max(item.numerator.width, item.denominator.width)
            item.width = inner_w + (_FRACTION_PAD * 2)
            item.baseline = item.numerator.height + _FRACTION_GAP
            item.height = (
                item.numerator.height
                + (_FRACTION_GAP * 2)
                + 1
                + item.denominator.height
            )
            return

        if isinstance(item, PowerNode):
            self._measure_slot(item.base)
            self._measure_slot(item.exponent)

            exp_top = item.base.baseline - _EXP_RAISE - item.exponent.baseline
            top_shift = -exp_top if exp_top < 0 else 0

            item._base_top = top_shift
            item._exp_top = exp_top + top_shift
            item._exp_x = item.base.width
            item.width = item.base.width + item.exponent.width
            item.baseline = item._base_top + item.base.baseline
            item.height = max(
                item._base_top + item.base.height,
                item._exp_top + item.exponent.height,
            )
            return

        if isinstance(item, RootNode):
            self._measure_slot(item.radicand)
            item._content_x = _ROOT_SYMBOL_W
            item._content_y = 2
            item.width = item._content_x + item.radicand.width
            item.baseline = item._content_y + item.radicand.baseline
            item.height = item._content_y + item.radicand.height

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

    def _layout_item(self, item, x, y, baseline):
        item.x = int(x)
        item.y = int(y + baseline - item.baseline)

        if isinstance(item, FractionNode):
            inner_w = item.width - (_FRACTION_PAD * 2)
            num_x = item.x + _FRACTION_PAD + max(
                0, (inner_w - item.numerator.width) // 2
            )
            den_x = item.x + _FRACTION_PAD + max(
                0, (inner_w - item.denominator.width) // 2
            )
            self._layout_slot(item.numerator, num_x, item.y, item.numerator.baseline)
            den_y = item.y + item.baseline + _FRACTION_GAP + 1
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
                item.radicand,
                item.x + item._content_x,
                item.y + item._content_y,
                item.radicand.baseline,
            )

    def _pixel(self, x, y):
        if 0 <= int(x) < DISPLAY_WIDTH and 0 <= int(y) < 64:
            self.canvas.pixel(int(x), int(y), 1)

    def _hline(self, x, y, width):
        x = int(x)
        y = int(y)
        width = int(width)
        if width <= 0 or y < 0 or y >= 64:
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
        end = min(64, y + height)
        if end > start:
            self.canvas.vline(x, start, end - start, 1)

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

    def _rect(self, x, y, width, height):
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            return
        self._hline(x, y, width)
        self._hline(x, y + height - 1, width)
        self._vline(x, y, height)
        self._vline(x + width - 1, y, height)

    def _draw_placeholder(self, slot, scroll_x):
        box_x = slot.x - scroll_x
        box_y = slot.y + max(0, slot.baseline - 5)
        box_w = max(5, slot.width - 1)
        self._rect(box_x, box_y, box_w, 6)

    def _render_slot(self, slot, scroll_x):
        if not slot.items:
            self._draw_placeholder(slot, scroll_x)
            return

        for item in slot.items:
            self._render_item(item, scroll_x)

    def _render_item(self, item, scroll_x):
        if isinstance(item, TokenNode):
            self.canvas.draw_text(item.text, item.x - scroll_x, item.y, color=1)
            return

        if isinstance(item, FractionNode):
            self._render_slot(item.numerator, scroll_x)
            self._render_slot(item.denominator, scroll_x)
            self._hline(
                item.x + _FRACTION_PAD - scroll_x,
                item.y + item.baseline,
                item.width - (_FRACTION_PAD * 2),
            )
            return

        if isinstance(item, PowerNode):
            self._render_slot(item.base, scroll_x)
            self._render_slot(item.exponent, scroll_x)
            return

        if isinstance(item, RootNode):
            self._render_slot(item.radicand, scroll_x)
            root_x = item.x - scroll_x
            bar_y = item.radicand.y - 1
            bottom_y = item.radicand.y + item.radicand.height - 1
            self._line(root_x, bottom_y - 2, root_x + 2, bottom_y)
            self._line(root_x + 2, bottom_y, root_x + 4, bar_y)
            self._hline(root_x + 4, bar_y, item.width - 4)

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
            top = slot.y + max(0, slot.baseline - 6)
            height = 7

        return x, top, height

    def _status_text(self):
        state = str(nav.current_state() or "").strip()
        if state != "":
            return state

        slot = self.cursor_slot
        owner = slot.owner
        if owner is None:
            return "expression"
        if isinstance(owner, FractionNode):
            if slot is owner.numerator:
                return "numerator"
            return "denominator"
        if isinstance(owner, PowerNode):
            if slot is owner.base:
                return "power base"
            return "exponent"
        if isinstance(owner, RootNode):
            return "square root"
        return "expression"

    def render(self):
        set_active_view("text")
        self.canvas.clear()

        self._measure_slot(self.root)
        top = max(1, (_EXPR_HEIGHT - self.root.height) // 2)
        self._layout_slot(self.root, 4, top, self.root.baseline)

        cursor_x, cursor_y, cursor_h = self._cursor_geometry()
        max_scroll = max(0, (self.root.x + self.root.width) - (DISPLAY_WIDTH - 3))
        scroll_x = min(max(0, self.scroll_x), max_scroll)

        view_left = 4
        view_right = DISPLAY_WIDTH - 5
        cursor_view_x = cursor_x - scroll_x
        if cursor_view_x < view_left:
            scroll_x = max(0, cursor_x - view_left)
        elif cursor_view_x > view_right:
            scroll_x = min(max_scroll, cursor_x - view_right)

        self.scroll_x = min(max(0, scroll_x), max_scroll)

        self._render_slot(self.root, self.scroll_x)

        cursor_view_x = cursor_x - self.scroll_x
        self._vline(cursor_view_x, cursor_y, cursor_h)
        self._pixel(cursor_view_x - 1, cursor_y)
        self._pixel(cursor_view_x + 1, cursor_y + cursor_h - 1)

        self._hline(0, _DIVIDER_Y, DISPLAY_WIDTH)
        self.canvas.draw_text(
            clip_text_px(self._status_text(), DISPLAY_WIDTH - 2),
            1,
            _STATUS_Y,
            color=1,
        )
        self.canvas.draw_text(
            clip_text_px(
                self.message if self.message else "OK=EVAL U/D=SLOT",
                DISPLAY_WIDTH - 2,
            ),
            1,
            _MESSAGE_Y,
            color=1,
        )
        self.canvas.flush()

    def handle_key(self, token):
        token = str(token or "")
        if token == "":
            self.render()
            return

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
        elif token == "*pow(10, )":
            self._insert_pow10()
        elif token == "copy":
            self.message = "COPY N/A"
        elif token == "paste":
            self.message = "PASTE N/A"
        else:
            self._insert_token(token)

        self.render()


def calculate():
    load_all_functions()
    keypad_state_manager_reset()
    set_active_view("text")
    display.clear_display()

    editor = _MathEditor()
    editor.render()

    while True:
        token = typer.start_typing()

        if token is None:
            editor.render()
            continue

        if token == "":
            editor.render()
            continue

        if token in ("alpha", "beta"):
            keypad_state_manager(x=token)
            editor.render()
            continue

        if token == "caps":
            keypad_state_manager(x="A")
            editor.render()
            continue

        if token == "toolbox":
            app.set_app_name("toolbox")
            app.set_group_name("root")
            break

        if token in ("ok", "exe"):
            editor.evaluate()
            editor.render()
            continue

        editor.handle_key(token)
