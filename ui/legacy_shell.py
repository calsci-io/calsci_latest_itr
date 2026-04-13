from ui.canvas import CHAR_ADVANCE, MonoCanvas, clip_text_px, text_width
from ui.components import wrap_lines
from ui.models import TextScreen
from ui.theme import CHAR_HEIGHT, DISPLAY_WIDTH, TEXT_COLS

PANEL_X = 2
PANEL_Y = 11
PANEL_W = 124
PANEL_H = 44
SCROLL_W = 4
CONTENT_X = PANEL_X + 2
CONTENT_Y = PANEL_Y + 2
CONTENT_W = PANEL_W - SCROLL_W - 5
FOOTER_Y = 56

MENU_VISIBLE_ROWS = 3
MENU_ROW_H = 13
MENU_ROW_GAP = 1

TEXT_VISIBLE_ROWS = 4
TEXT_LINE_H = 10

FORM_VISIBLE_FIELDS = 3
FORM_VISIBLE_FIELDS_WITH_MESSAGE = 2
FORM_ROW_H = 12
FORM_ROW_GAP = 2
FORM_LABEL_W = 30
FORM_INPUT_GAP = 2
FORM_MESSAGE_H = 10
FORM_VALUE_PAD_X = 3
FORM_VALUE_PAD_RIGHT = 4


def _display_text(text_value):
    return str(text_value or "").replace("_", " ")


def _title_text(text_value):
    raw = str(text_value or "").strip()
    display_text = _display_text(raw)
    if "_" in raw or raw.islower():
        titled = []
        for part in display_text.split(" "):
            if not part:
                continue
            titled.append(part[:1].upper() + part[1:].lower())
        return " ".join(titled) or display_text
    return display_text


def _normalize_selected(index, item_count):
    if item_count <= 0:
        return 0
    index = int(index or 0)
    if index < 0:
        return 0
    if index >= item_count:
        return item_count - 1
    return index


def _top_index(item_count, selected_index, visible_rows):
    if item_count <= visible_rows:
        return 0
    top_index = selected_index - visible_rows + 1
    if top_index < 0:
        return 0
    max_top = item_count - visible_rows
    if top_index > max_top:
        return max_top
    return top_index


def _max_chars_for_width(width):
    if width <= 0:
        return 1
    return max(1, (int(width) + 1) // CHAR_ADVANCE)


class LegacyShellRenderer:
    """Shared legacy-style shells for menu, text, and form screens."""

    def __init__(self):
        self.width = DISPLAY_WIDTH

    def render(self, screen):
        screen_type = getattr(screen, "screen_type", "")
        if screen_type == "menu":
            return self.render_menu(screen)
        if screen_type == "text":
            return self.render_text(screen)
        if screen_type == "form":
            return self.render_form(screen)
        raise ValueError("unsupported screen type: %s" % screen_type)

    def render_exception(self, exc):
        return self.render_text(
            TextScreen(
                "System Error",
                [str(exc)[:TEXT_COLS], "Press back/home"],
                footer="error",
            )
        )

    def render_menu(self, screen):
        canvas = MonoCanvas()
        canvas.clear()
        self._draw_title(canvas, screen.title)
        canvas.rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, 1)

        subtitle = _display_text(getattr(screen, "subtitle", ""))
        items = [_display_text(item) for item in getattr(screen, "items", [])]
        if not items:
            items = ["No items available"]
        selected_index = _normalize_selected(getattr(screen, "selected", 0), len(items))

        subtitle_rows = 1 if subtitle else 0
        visible_items = max(1, MENU_VISIBLE_ROWS - subtitle_rows)
        top_index = _top_index(len(items), selected_index, visible_items)

        if subtitle:
            subtitle_y = CONTENT_Y
            canvas.draw_text_in_rect(
                subtitle,
                CONTENT_X,
                subtitle_y,
                CONTENT_W,
                MENU_ROW_H - 1,
                color=1,
                align="center",
            )

        for slot in range(visible_items):
            item_index = top_index + slot
            if item_index >= len(items):
                break
            row_y = CONTENT_Y + (slot + subtitle_rows) * (MENU_ROW_H + MENU_ROW_GAP)
            self._draw_menu_row(
                canvas,
                row_y,
                items[item_index],
                selected=item_index == selected_index,
            )

        self._draw_scrollbar(canvas, len(items), top_index, visible_items)
        self._draw_footer(canvas, getattr(screen, "footer", ""))
        return canvas.buffer

    def render_text(self, screen):
        canvas = MonoCanvas()
        canvas.clear()
        self._draw_title(canvas, screen.title)
        canvas.rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, 1)

        raw_lines = []
        for item in getattr(screen, "lines", []):
            raw_lines.append(_display_text(item))
        wrapped = wrap_lines(raw_lines, width=TEXT_COLS)
        scroll = max(0, int(getattr(screen, "scroll", 0) or 0))
        visible = wrapped[scroll : scroll + TEXT_VISIBLE_ROWS]
        while len(visible) < TEXT_VISIBLE_ROWS:
            visible.append("")

        for index, line in enumerate(visible):
            y = CONTENT_Y + 1 + index * TEXT_LINE_H
            canvas.draw_text(str(line), CONTENT_X, y, color=1, max_width=CONTENT_W)

        self._draw_footer(canvas, getattr(screen, "footer", ""))
        return canvas.buffer

    def render_form(self, screen):
        canvas = MonoCanvas()
        canvas.clear()
        self._draw_title(canvas, screen.title)
        canvas.rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, 1)

        fields = list(getattr(screen, "fields", []))
        message = _display_text(getattr(screen, "message", ""))
        selected_index = _normalize_selected(getattr(screen, "selected", 0), max(1, len(fields)))

        visible_fields = FORM_VISIBLE_FIELDS_WITH_MESSAGE if message else FORM_VISIBLE_FIELDS
        if not fields:
            fields = []
            visible_fields = 0
            selected_index = 0

        top_index = _top_index(len(fields), selected_index, max(1, visible_fields)) if fields else 0

        for slot in range(visible_fields):
            field_index = top_index + slot
            if field_index >= len(fields):
                break
            row_y = CONTENT_Y + slot * (FORM_ROW_H + FORM_ROW_GAP)
            self._draw_form_field(
                canvas,
                row_y,
                fields[field_index],
                selected=field_index == selected_index,
            )

        if message:
            message_y = PANEL_Y + PANEL_H - FORM_MESSAGE_H - 2
            canvas.draw_text_in_rect(
                message,
                CONTENT_X,
                message_y,
                CONTENT_W,
                FORM_MESSAGE_H,
                color=1,
                align="center",
            )

        self._draw_footer(canvas, getattr(screen, "footer", ""))
        return canvas.buffer

    def _draw_title(self, canvas, title):
        canvas.draw_text_center(_title_text(title), 1, color=1)

    def _draw_menu_row(self, canvas, row_y, text_value, selected=False):
        row_color = 1 if selected else 0
        text_color = 0 if selected else 1
        canvas.fill_rect(CONTENT_X, row_y, CONTENT_W, MENU_ROW_H, row_color)
        canvas.rect(CONTENT_X, row_y, CONTENT_W, MENU_ROW_H, 1)
        canvas.draw_text_in_rect(
            text_value,
            CONTENT_X + 2,
            row_y + 1,
            CONTENT_W - 4,
            MENU_ROW_H - 2,
            color=text_color,
            align="left",
        )

    def _draw_form_field(self, canvas, row_y, field, selected=False):
        label_text = _display_text(getattr(field, "label", ""))
        value_text = str(getattr(field, "value", "") or "")
        label_w = min(max(FORM_LABEL_W, text_width(label_text) + 8), CONTENT_W - 28)
        input_x = CONTENT_X + label_w + FORM_INPUT_GAP
        input_w = CONTENT_W - label_w - FORM_INPUT_GAP
        input_text_w = max(8, input_w - (FORM_VALUE_PAD_X + FORM_VALUE_PAD_RIGHT))
        input_y = row_y

        canvas.fill_rect(CONTENT_X, row_y, label_w, FORM_ROW_H, 1)
        canvas.rect(CONTENT_X, row_y, label_w, FORM_ROW_H, 1)
        canvas.draw_text_in_rect(
            label_text,
            CONTENT_X + 2,
            row_y,
            label_w - 4,
            FORM_ROW_H,
            color=0,
            align="center",
        )

        view = self._field_view(value_text, input_text_w, selected)
        if selected:
            canvas.fill_rect(input_x, input_y, input_w, FORM_ROW_H, 1)
            text_color = 0
        else:
            text_color = 1
        canvas.rect(input_x, input_y, input_w, FORM_ROW_H, 1)
        text_y = input_y + max(0, (FORM_ROW_H - CHAR_HEIGHT) // 2)
        canvas.draw_text(
            view["visible_text"],
            input_x + FORM_VALUE_PAD_X,
            text_y,
            color=text_color,
            max_width=input_text_w,
        )

        if selected:
            caret_x = input_x + FORM_VALUE_PAD_X + view["caret_col"] * CHAR_ADVANCE
            max_x = input_x + input_w - FORM_VALUE_PAD_RIGHT
            if caret_x > max_x:
                caret_x = max_x
            canvas.fill_rect(caret_x, input_y + 2, 2, max(1, FORM_ROW_H - 4), text_color)
            if view["has_overflow"]:
                self._draw_horizontal_scrollbar(
                    canvas,
                    input_x + 2,
                    input_y + FORM_ROW_H - 2,
                    max(8, input_w - 4),
                    max(view["visible_chars"], len(view["value_text"])),
                    view["visible_chars"],
                    view["display_pos"],
                    color=text_color,
                )

    def _field_view(self, value_text, max_width, selected):
        value_text = str(value_text or "")
        visible_chars = _max_chars_for_width(max_width)
        if not selected:
            return {
                "value_text": value_text,
                "visible_text": clip_text_px(value_text, max_width),
                "visible_chars": visible_chars,
                "display_pos": 0,
                "caret_col": min(len(value_text), visible_chars),
                "has_overflow": len(value_text) > visible_chars,
            }

        display_pos = max(0, len(value_text) - visible_chars)
        visible_text = value_text[display_pos : display_pos + visible_chars]
        caret_col = len(value_text) - display_pos
        if caret_col < 0:
            caret_col = 0
        if caret_col > visible_chars:
            caret_col = visible_chars
        return {
            "value_text": value_text,
            "visible_text": visible_text,
            "visible_chars": visible_chars,
            "display_pos": display_pos,
            "caret_col": caret_col,
            "has_overflow": len(value_text) > visible_chars,
        }

    def _draw_scrollbar(self, canvas, item_count, top_index, visible_rows):
        track_x = PANEL_X + PANEL_W - SCROLL_W - 1
        track_y = PANEL_Y + 2
        track_h = PANEL_H - 4
        canvas.rect(track_x, track_y, SCROLL_W, track_h, 1)

        if item_count <= visible_rows:
            thumb_h = track_h - 2
            thumb_y = track_y + 1
        else:
            thumb_h = max(8, ((track_h - 2) * visible_rows) // item_count)
            max_top = max(1, item_count - visible_rows)
            thumb_range = max(0, (track_h - 2) - thumb_h)
            thumb_y = track_y + 1 + (top_index * thumb_range // max_top)

        canvas.fill_rect(track_x + 1, thumb_y, max(1, SCROLL_W - 2), thumb_h, 1)

    def _draw_horizontal_scrollbar(self, canvas, x, y, width, total_cols, visible_cols, start_col, color=1):
        if total_cols <= visible_cols:
            return
        width = max(8, int(width))
        canvas.hline(x, y, width, color)
        thumb_w = max(6, (width * visible_cols) // max(total_cols, 1))
        thumb_range = max(0, width - thumb_w)
        max_start = max(1, total_cols - visible_cols)
        thumb_x = x + (start_col * thumb_range // max_start)
        canvas.fill_rect(thumb_x, y - 1, thumb_w, 2, color)

    def _draw_footer(self, canvas, footer_text):
        footer_text = str(footer_text or "")
        if footer_text == "":
            return
        canvas.fill_rect(0, FOOTER_Y - 1, DISPLAY_WIDTH, 9, 1)
        canvas.draw_text_center(footer_text, FOOTER_Y, color=0)
