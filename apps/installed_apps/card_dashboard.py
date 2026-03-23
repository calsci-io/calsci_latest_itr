import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

try:
    import urandom as _rand
except ImportError:
    import random as _rand

import machine
import utime as time  # type: ignore

from apps.installed_apps._mono_ui import MonoCanvas, clip_text, clip_text_px
from data_modules.object_handler import keyin, keymap, keypad_state_manager_reset
from process_modules import boot_up_data_update
from process_modules.navigation import request_navigation_from_key


_WIDTH = 128
_HEIGHT = 64
_LOCKABLE_STATES = ("a", "A", "b")
_PROFILES = ("Field", "Desk", "Night")
_CARD_POSITIONS = (
    (4, 9),
    (66, 9),
    (4, 32),
    (66, 32),
)
_CARD_W = 58
_CARD_H = 20
_POPUP_X = 8
_POPUP_Y = 10
_POPUP_W = 112
_POPUP_H = 44


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


def _randbelow(limit):
    if limit <= 1:
        return 0

    if hasattr(_rand, "randrange"):
        try:
            return _rand.randrange(limit)
        except Exception:
            pass

    bits = 1
    while (1 << bits) < limit:
        bits += 1

    while True:
        value = _rand.getrandbits(bits)
        if value < limit:
            return value


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, int(value)))


class _CardDashboard:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.mode_state = "d"
        self.mode_locked = False
        self.profile_index = 0
        self.dashboard_frozen = False
        self.compact_mode = False
        self.selected_index = 0
        self.popup_kind = None
        self.popup_page = 0
        self.last_action = "OK details  Tool help"
        self.clipboard = ""
        self.last_auto_ms = _ticks_ms()
        self.cards = [
            {
                "title": "Power",
                "value": 84,
                "unit": "%",
                "aux": 18,
                "aux_unit": "w",
                "tag": "Eco",
                "state": "steady",
                "note": "",
                "favorite": False,
                "min": 0,
                "max": 100,
            },
            {
                "title": "Link",
                "value": 67,
                "unit": "%",
                "aux": 24,
                "aux_unit": "ms",
                "tag": "Mesh",
                "state": "clean",
                "note": "",
                "favorite": True,
                "min": 0,
                "max": 100,
            },
            {
                "title": "Store",
                "value": 58,
                "unit": "%",
                "aux": 3,
                "aux_unit": "q",
                "tag": "Sync",
                "state": "ready",
                "note": "",
                "favorite": False,
                "min": 0,
                "max": 100,
            },
            {
                "title": "Climate",
                "value": 24,
                "unit": "C",
                "aux": 41,
                "aux_unit": "%",
                "tag": "Auto",
                "state": "calm",
                "note": "",
                "favorite": False,
                "min": 10,
                "max": 40,
            },
        ]

    def build(self):
        self.refresh(full=True)

    def _set_mode(self, state, locked=None):
        self.mode_state = str(state)
        if self.mode_state not in ("d", "a", "A", "b"):
            self.mode_state = "d"
        if locked is None:
            if self.mode_state == "d":
                self.mode_locked = False
        else:
            self.mode_locked = bool(locked) and self.mode_state in _LOCKABLE_STATES
        keymap.key_change(self.mode_state)

    def _mode_label(self):
        labels = {
            "d": "DEF",
            "a": "ALP",
            "A": "CAP",
            "b": "BET",
        }
        label = labels.get(self.mode_state, "DEF")
        if self.mode_locked and self.mode_state in _LOCKABLE_STATES:
            label += "!"
        return label

    def _handle_mode_key(self, token):
        if token == "alpha":
            if self.mode_state in ("a", "A"):
                self._set_mode("d", locked=False)
                self.last_action = "Alpha mode off"
            else:
                self._set_mode("a", locked=False)
                self.last_action = "Alpha mode on"
            return True

        if token == "beta":
            if self.mode_state == "b":
                self._set_mode("d", locked=False)
                self.last_action = "Beta mode off"
            else:
                self._set_mode("b", locked=False)
                self.last_action = "Beta mode on"
            return True

        if token == "caps":
            if self.mode_state == "a":
                self._set_mode("A", locked=self.mode_locked)
                self.last_action = "Caps on"
            elif self.mode_state == "A":
                self._set_mode("a", locked=self.mode_locked)
                self.last_action = "Caps off"
            else:
                self._set_mode("A", locked=False)
                self.last_action = "Caps latch"
            return True

        return False

    def _auto_reset_mode(self, token):
        if self.mode_state not in _LOCKABLE_STATES or self.mode_locked:
            return
        if token in ("", "lock", "alpha", "beta", "caps"):
            return
        self._set_mode("d", locked=False)

    def _selected_card(self):
        return self.cards[self.selected_index]

    def _show_popup(self, kind, page=0):
        self.popup_kind = kind
        self.popup_page = int(page)

    def _hide_popup(self):
        self.popup_kind = None
        self.popup_page = 0

    def _move_card(self, dx=0, dy=0):
        row = self.selected_index // 2
        col = self.selected_index % 2
        row = (row + dy) % 2
        col = (col + dx) % 2
        self.selected_index = row * 2 + col
        self.last_action = "Focus {}".format(self._selected_card()["title"])

    def _select_card(self, idx):
        self.selected_index = int(idx) % len(self.cards)
        self.last_action = "Jump {}".format(self._selected_card()["title"])

    def _adjust_card(self, value_delta=0, aux_delta=0):
        card = self._selected_card()
        card["value"] = _clamp(card["value"] + value_delta, card["min"], card["max"])
        card["aux"] = _clamp(card["aux"] + aux_delta, 0, 99)

    def _set_digit_preset(self, token):
        card = self._selected_card()
        digit = int(token)
        if card["title"] == "Climate":
            card["value"] = _clamp(10 + digit * 3, card["min"], card["max"])
        elif digit == 0:
            card["value"] = card["max"]
        else:
            card["value"] = _clamp(digit * 10, card["min"], card["max"])
        self.last_action = "{} preset {}".format(card["title"], token)

    def _toggle_favorite(self):
        card = self._selected_card()
        card["favorite"] = not card["favorite"]
        state = "pinned" if card["favorite"] else "unpinned"
        self.last_action = "{} {}".format(card["title"], state)

    def _append_note(self, token):
        card = self._selected_card()
        if token == "tab":
            addition = "|"
        elif token == " ":
            addition = "_"
        else:
            addition = str(token)
        card["note"] = (card["note"] + addition)[-12:]
        self.last_action = "{} note {}".format(card["title"], addition)

    def _copy_note(self):
        self.clipboard = self._selected_card()["note"]
        self.last_action = "Copied note"

    def _paste_note(self):
        if not self.clipboard:
            self.last_action = "Clipboard empty"
            return
        card = self._selected_card()
        card["note"] = (card["note"] + self.clipboard)[-12:]
        self.last_action = "Pasted note"

    def _undo_note(self):
        card = self._selected_card()
        card["note"] = card["note"][:-1]
        self.last_action = "Undo note"

    def _clear_selected(self):
        card = self._selected_card()
        card["note"] = ""
        card["tag"] = "Clear"
        self.last_action = "{} cleared".format(card["title"])

    def _randomize_cards(self):
        tags = ("Eco", "Boost", "Mesh", "Sync", "Quiet", "Peak", "Flow", "Watch")
        states = ("steady", "ready", "clean", "fast", "cool", "warm", "prime", "live")
        for idx, card in enumerate(self.cards):
            delta = _randbelow(11) - 5
            if idx == 3:
                delta = _randbelow(5) - 2
            card["value"] = _clamp(card["value"] + delta, card["min"], card["max"])
            card["aux"] = _clamp(card["aux"] + (_randbelow(7) - 3), 0, 99)
            card["tag"] = tags[_randbelow(len(tags))]
            card["state"] = states[_randbelow(len(states))]
        self.last_action = "Dashboard refreshed"

    def _cycle_profile(self, step=1):
        self.profile_index = (self.profile_index + int(step)) % len(_PROFILES)
        self.last_action = "Profile {}".format(_PROFILES[self.profile_index])

    def _tag_selected(self, token):
        card = self._selected_card()
        card["tag"] = clip_text(str(token).upper(), 5)
        self.last_action = "{} tag {}".format(card["title"], card["tag"])

    def _primary_action(self):
        card = self._selected_card()
        card["state"] = "armed" if card["state"] != "armed" else "ready"
        card["aux"] = _clamp(card["aux"] + 1, 0, 99)
        self.last_action = "{} primary".format(card["title"])

    def _secondary_action(self):
        card = self._selected_card()
        card["state"] = "scan"
        self.last_action = "{} execute".format(card["title"])

    def _cycle_popup_page(self, step):
        if self.popup_kind is None:
            return
        max_pages = 3 if self.popup_kind == "detail" else 3
        self.popup_page = (self.popup_page + int(step)) % max_pages
        self.last_action = "Popup page {}".format(self.popup_page + 1)

    def _auto_tick(self):
        now_ms = _ticks_ms()
        if self.dashboard_frozen:
            self.last_auto_ms = now_ms
            return False

        if _ticks_diff(now_ms, self.last_auto_ms) < 850:
            return False

        self.last_auto_ms = now_ms
        for idx, card in enumerate(self.cards):
            wave = ((now_ms // 850) + idx + self.profile_index) % 3
            delta = wave - 1
            if card["title"] == "Climate":
                delta = 0 if wave == 1 else (1 if wave == 2 else -1)
            card["value"] = _clamp(card["value"] + delta, card["min"], card["max"])
            if idx != self.selected_index:
                card["aux"] = _clamp(card["aux"] + delta, 0, 99)
        return True

    def _idle_tasks(self):
        if self._auto_tick():
            self.refresh()

    def _read_key(self):
        _sleep_ms(120)
        col, row = keyin.keypad_loop(idle_callback=self._idle_tasks)
        return keymap.key_out(col=int(col), row=int(row))

    def _popup_page_data(self):
        if self.popup_kind == "help":
            pages = [
                (
                    "Key Map",
                    (
                        "Nav move  OK open",
                        "EXE run  ANS pin",
                        "F1-4 jump F6 rand",
                    ),
                    "UD pages  Back close",
                ),
                (
                    "Modes",
                    (
                        "ALPHA text input",
                        "BETA symbols/tools",
                        "LOCK hold mode/freeze",
                    ),
                    "TAB/space add notes",
                ),
                (
                    "Actions",
                    (
                        "+- tune  */ aux",
                        "Digits preset value",
                        "AC clear Toolbox help",
                    ),
                    "Home/Set/Back exit",
                ),
            ]
            return pages[self.popup_page % len(pages)]

        card = self._selected_card()
        pages = [
            (
                "{} Detail".format(card["title"]),
                (
                    "Value {}{}".format(card["value"], card["unit"]),
                    "Aux {}{}".format(card["aux"], card["aux_unit"]),
                    "Tag {} {}".format(card["tag"], "PIN" if card["favorite"] else "LIVE"),
                ),
                "OK arm  EXE run",
            ),
            (
                "{} Status".format(card["title"]),
                (
                    "State {}".format(card["state"]),
                    "Profile {}".format(_PROFILES[self.profile_index]),
                    "Freeze {}".format("on" if self.dashboard_frozen else "off"),
                ),
                "LR card  UD page",
            ),
            (
                "{} Notes".format(card["title"]),
                (
                    "Note {}".format(clip_text(card["note"] or "-", 14)),
                    "Clip {}".format(clip_text(self.clipboard or "-", 14)),
                    "Last {}".format(clip_text(self.last_action, 13)),
                ),
                "Copy paste undo AC",
            ),
        ]
        return pages[self.popup_page % len(pages)]

    def _draw_card(self, idx, x, y):
        card = self.cards[idx]
        selected = idx == self.selected_index
        fill_color = 1 if selected else 0
        text_color = 0 if selected else 1

        self.canvas.fill_rect(x, y, _CARD_W, _CARD_H, fill_color)
        self.canvas.rect(x, y, _CARD_W, _CARD_H, 1)

        title_text = "{}{}".format(card["title"][:5], "*" if card["favorite"] else "")
        value_text = "{}{}".format(card["value"], card["unit"])
        if self.compact_mode:
            meta_text = clip_text(card["tag"], 5)
        else:
            note_mark = "+" if card["note"] else "."
            meta_text = clip_text("{} {}{}".format(card["tag"], card["aux"], note_mark), 10)

        self.canvas.draw_text(title_text, x + 2, y + 1, color=text_color)
        self.canvas.draw_text_in_rect(value_text, x + 1, y + 6, _CARD_W - 2, 8, color=text_color, align="center")
        self.canvas.draw_text_in_rect(meta_text, x + 1, y + 12, _CARD_W - 2, 8, color=text_color, align="center")

    def _draw_popup(self):
        if self.popup_kind is None:
            return

        title, lines, hint = self._popup_page_data()
        self.canvas.fill_rect(_POPUP_X, _POPUP_Y, _POPUP_W, _POPUP_H, 0)
        self.canvas.rect(_POPUP_X, _POPUP_Y, _POPUP_W, _POPUP_H, 1)
        self.canvas.hline(_POPUP_X + 1, _POPUP_Y + 10, _POPUP_W - 2, 1)
        self.canvas.hline(_POPUP_X + 1, _POPUP_Y + _POPUP_H - 10, _POPUP_W - 2, 1)
        self.canvas.draw_text_in_rect(title, _POPUP_X + 2, _POPUP_Y + 1, _POPUP_W - 4, 8, color=1, align="center")
        self.canvas.draw_text_in_rect(lines[0], _POPUP_X + 3, _POPUP_Y + 12, _POPUP_W - 6, 8, color=1, align="center")
        self.canvas.draw_text_in_rect(lines[1], _POPUP_X + 3, _POPUP_Y + 20, _POPUP_W - 6, 8, color=1, align="center")
        self.canvas.draw_text_in_rect(lines[2], _POPUP_X + 3, _POPUP_Y + 28, _POPUP_W - 6, 8, color=1, align="center")
        self.canvas.draw_text_in_rect(hint, _POPUP_X + 2, _POPUP_Y + _POPUP_H - 9, _POPUP_W - 4, 8, color=1, align="center")

    def refresh(self, full=False):
        _ = full
        self.canvas.clear()
        self.canvas.draw_text("Dash {}".format("L" if self.dashboard_frozen else " "), 4, 1, color=1)
        self.canvas.draw_text_right(
            "{} {}".format(_PROFILES[self.profile_index][:2], self._mode_label()),
            _WIDTH - 4,
            1,
            color=1,
        )

        for idx, (x, y) in enumerate(_CARD_POSITIONS):
            self._draw_card(idx, x, y)

        self.canvas.draw_text_center(clip_text(self.last_action, 24), 56, color=1)
        self._draw_popup()
        self.canvas.flush()

    def _handle_token(self, token):
        if token == "":
            self._cycle_profile(1)
            return

        if self._handle_mode_key(token):
            return

        if token == "on":
            boot_up_data_update.main()
            machine.deepsleep()
            return

        if token in ("home", "settings"):
            request_navigation_from_key(token)

        if token == "back":
            if self.popup_kind is not None:
                self._hide_popup()
                self.last_action = "Popup closed"
            else:
                request_navigation_from_key("back")
            return

        if token == "lock":
            if self.mode_state in _LOCKABLE_STATES:
                self.mode_locked = not self.mode_locked
                self.last_action = "Mode lock {}".format("on" if self.mode_locked else "off")
            else:
                self.dashboard_frozen = not self.dashboard_frozen
                self.last_action = "Freeze {}".format("on" if self.dashboard_frozen else "off")
            return

        if token == "toolbox":
            self._show_popup("help", page=0)
            self.last_action = "Help open"
            return

        if token == "fraction":
            self.compact_mode = not self.compact_mode
            self.last_action = "Compact {}".format("on" if self.compact_mode else "off")
            return

        if token == "nav_l":
            if self.popup_kind == "detail":
                self._move_card(dx=-1, dy=0)
            elif self.popup_kind == "help":
                self._cycle_popup_page(-1)
            else:
                self._move_card(dx=-1, dy=0)
            return

        if token == "nav_r":
            if self.popup_kind == "detail":
                self._move_card(dx=1, dy=0)
            elif self.popup_kind == "help":
                self._cycle_popup_page(1)
            else:
                self._move_card(dx=1, dy=0)
            return

        if token == "nav_u":
            if self.popup_kind is not None:
                self._cycle_popup_page(-1)
            else:
                self._move_card(dx=0, dy=-1)
            return

        if token == "nav_d":
            if self.popup_kind is not None:
                self._cycle_popup_page(1)
            else:
                self._move_card(dx=0, dy=1)
            return

        if token == "nav_b":
            if self.popup_kind is not None:
                self._hide_popup()
                self.last_action = "Popup dismissed"
            else:
                self._move_card(dx=-1, dy=0)
            return

        if token == "ok":
            if self.popup_kind == "detail":
                self._primary_action()
            else:
                self._show_popup("detail", page=0)
                self.last_action = "Detail open"
            return

        if token == "exe":
            if self.popup_kind != "detail":
                self._show_popup("detail", page=0)
            self._secondary_action()
            return

        if token == "ans":
            self._toggle_favorite()
            return

        if token == "AC":
            self._clear_selected()
            return

        if token == "copy":
            self._copy_note()
            return

        if token == "paste":
            self._paste_note()
            return

        if token == "undo":
            self._undo_note()
            return

        if token == "tab":
            self._append_note(token)
            return

        if token == " ":
            self._append_note(token)
            return

        if token in ("F1", "F2", "F3", "F4"):
            self._select_card(int(token[1]) - 1)
            return

        if token == "F5":
            if self.popup_kind is None:
                self._show_popup("detail", page=1)
                self.last_action = "Quick detail"
            else:
                self._hide_popup()
                self.last_action = "Quick close"
            return

        if token == "F6":
            self._randomize_cards()
            return

        if token.isdigit():
            self._set_digit_preset(token)
            return

        if token == "+":
            self._adjust_card(value_delta=1)
            self.last_action = "Value +1"
            return

        if token == "-":
            self._adjust_card(value_delta=-1)
            self.last_action = "Value -1"
            return

        if token == "*":
            self._adjust_card(aux_delta=1)
            self.last_action = "Aux +1"
            return

        if token == "/":
            self._adjust_card(aux_delta=-1)
            self.last_action = "Aux -1"
            return

        if token == "pow":
            self._adjust_card(value_delta=10)
            self.last_action = "Boost +10"
            return

        if token == "root":
            self._adjust_card(value_delta=-10)
            self.last_action = "Trim -10"
            return

        if token in (
            "pi",
            "log",
            "sin",
            "cos",
            "tan",
            "asin",
            "acos",
            "atan",
            ",",
            "(",
            ")",
            "=",
            "$",
            "&",
            "`",
            '"',
            "'",
            "\\",
            "^",
            "~",
            "!",
            "<",
            ">",
            "[",
            "]",
            "%",
            "{",
            "}",
            ":",
            "#",
            "|",
            ";",
            "@",
            "?",
            "_",
            "copy",
            "paste",
        ):
            self._tag_selected(token)
            return

        self._append_note(token)

    def run(self):
        self._set_mode("d", locked=False)
        self.build()
        try:
            while True:
                token = self._read_key()
                self._handle_token(token)
                self._auto_reset_mode(token)
                self.refresh()
        finally:
            self._hide_popup()
            self._set_mode("d", locked=False)


def card_dashboard(db={}):
    _ = db
    keypad_state_manager_reset()

    display.clear_display()
    dashboard = _CardDashboard()
    dashboard.run()
