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
_ITEM_COUNT = 24
_PAGE_STEP = 5
_VISIBLE_ROWS = 3

_LIST_X = 2
_LIST_Y = 11
_LIST_W = 124
_LIST_H = 44
_ROW_HEIGHT = 13
_ROW_GAP = 1
_SCROLL_W = 4
_CONTENT_X = _LIST_X + 2
_CONTENT_Y = _LIST_Y + 2
_CONTENT_W = _LIST_W - _SCROLL_W - 5
_STATUS_Y = 56

_PREFIXES = (
    "Amber",
    "Brisk",
    "Cinder",
    "Dusty",
    "Echo",
    "Fable",
    "Glimmer",
    "Harbor",
    "Ivory",
    "Jade",
    "Kindle",
    "Lunar",
    "Mellow",
    "Nimbus",
    "Orbit",
    "Prairie",
    "Quartz",
    "Rusty",
    "Solar",
    "Tidy",
    "Umber",
    "Velvet",
    "Wisp",
    "Yonder",
)

_ITEMS = (
    "Beacon",
    "Bottle",
    "Cable",
    "Compass",
    "Crate",
    "Drum",
    "Flask",
    "Gizmo",
    "Kettle",
    "Lantern",
    "Ledger",
    "Magnet",
    "Mirror",
    "Mug",
    "Parcel",
    "Pebble",
    "Pouch",
    "Radio",
    "Ribbon",
    "Satchel",
    "Spool",
    "Ticket",
    "Token",
    "Whistle",
)

_TRAITS = (
    "Mk2",
    "Nova",
    "Prime",
    "Mini",
    "Lite",
    "Flex",
    "Bolt",
    "Wave",
)


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


def _shuffle(values):
    values = list(values)
    for idx in range(len(values) - 1, 0, -1):
        swap_idx = _randbelow(idx + 1)
        values[idx], values[swap_idx] = values[swap_idx], values[idx]
    return values


def _make_item_names(count=_ITEM_COUNT):
    names = []
    seen = {}
    attempts = 0
    max_attempts = count * 12

    while len(names) < count and attempts < max_attempts:
        attempts += 1
        candidate = "{} {} {}".format(
            _PREFIXES[_randbelow(len(_PREFIXES))],
            _ITEMS[_randbelow(len(_ITEMS))],
            _TRAITS[_randbelow(len(_TRAITS))],
        )
        if candidate in seen:
            continue
        seen[candidate] = True
        names.append(candidate)

    fallback_index = 1
    while len(names) < count:
        candidate = "Random Item {:02d}".format(fallback_index)
        fallback_index += 1
        if candidate in seen:
            continue
        seen[candidate] = True
        names.append(candidate)

    return _shuffle(names)


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def _read_key():
    _sleep_ms(120)
    col, row = keyin.keypad_loop()
    return keymap.key_out(col=int(col), row=int(row))


class _RandomItemsApp:
    def __init__(self):
        self.canvas = MonoCanvas()
        self.items = []
        self.selected_index = 0
        self.top_index = 0
        self.status_prefix = "Selected"

    def build(self):
        self.shuffle()

    def shuffle(self):
        self.items = _make_item_names()
        self.selected_index = 0
        self.top_index = 0
        self.status_prefix = "Selected"
        self.render()

    def move(self, step):
        if not self.items:
            return
        self.selected_index = (self.selected_index + step) % len(self.items)
        self.status_prefix = "Selected"
        self._ensure_visible()
        self.render()

    def pick(self):
        self.status_prefix = "Picked"
        self.render()

    def _ensure_visible(self):
        if self.selected_index < self.top_index:
            self.top_index = self.selected_index
        elif self.selected_index >= self.top_index + _VISIBLE_ROWS:
            self.top_index = self.selected_index - _VISIBLE_ROWS + 1

    def _status_text(self):
        if not self.items:
            return "No items"
        selected_name = clip_text(self.items[self.selected_index], 18)
        return "{}: {}".format(self.status_prefix, selected_name)

    def _render_scrollbar(self):
        track_x = _LIST_X + _LIST_W - _SCROLL_W - 1
        track_y = _LIST_Y + 2
        track_h = _LIST_H - 4

        self.canvas.rect(track_x, track_y, _SCROLL_W, track_h, 1)

        if len(self.items) <= _VISIBLE_ROWS:
            thumb_h = track_h - 2
            thumb_y = track_y + 1
        else:
            thumb_h = max(8, ((track_h - 2) * _VISIBLE_ROWS) // len(self.items))
            max_top = len(self.items) - _VISIBLE_ROWS
            thumb_range = max(0, (track_h - 2) - thumb_h)
            thumb_y = track_y + 1 + (self.top_index * thumb_range // max_top)

        self.canvas.fill_rect(track_x + 1, thumb_y, max(1, _SCROLL_W - 2), thumb_h, 1)

    def render(self):
        self.canvas.clear()
        self.canvas.draw_text_center("Random Items", 1, color=1)
        self.canvas.rect(_LIST_X, _LIST_Y, _LIST_W, _LIST_H, 1)

        for slot in range(_VISIBLE_ROWS):
            item_index = self.top_index + slot
            if item_index >= len(self.items):
                break

            row_y = _CONTENT_Y + slot * (_ROW_HEIGHT + _ROW_GAP)
            selected = item_index == self.selected_index
            row_color = 1 if selected else 0
            text_color = 0 if selected else 1

            self.canvas.fill_rect(_CONTENT_X, row_y, _CONTENT_W, _ROW_HEIGHT, row_color)
            self.canvas.rect(_CONTENT_X, row_y, _CONTENT_W, _ROW_HEIGHT, 1)
            item_text = clip_text_px(self.items[item_index], _CONTENT_W - 4)
            self.canvas.draw_text_in_rect(
                item_text,
                _CONTENT_X + 2,
                row_y + 1,
                _CONTENT_W - 4,
                _ROW_HEIGHT - 2,
                color=text_color,
                align="left",
            )

        self._render_scrollbar()
        self.canvas.draw_text_center(self._status_text(), _STATUS_Y, color=1)
        self.canvas.flush()


def random_items(db={}):
    _ = db
    keypad_state_manager_reset()

    display.clear_display()
    app = _RandomItemsApp()
    app.build()

    while True:
        key_name = _read_key()

        if key_name in ("back", "home", "settings"):
            request_navigation_from_key(key_name)

        if key_name in ("on", "off"):
            boot_up_data_update.main()
            machine.deepsleep()

        if key_name in ("nav_u", "nav_l"):
            step = -1 if key_name == "nav_u" else -_PAGE_STEP
            app.move(step)
            continue

        if key_name in ("nav_d", "nav_r"):
            step = 1 if key_name == "nav_d" else _PAGE_STEP
            app.move(step)
            continue

        if key_name == "ok":
            app.pick()
            continue

        if key_name in ("alpha", "beta"):
            app.shuffle()
