from ui.font5x8 import glyph_bytes
from ui.theme import CHAR_HEIGHT, CHAR_WIDTH, DISPLAY_HEIGHT, DISPLAY_WIDTH

CHAR_ADVANCE = CHAR_WIDTH + 1


def text_width(text_value):
    text_value = str(text_value)
    if not text_value:
        return 0
    return len(text_value) * CHAR_ADVANCE - 1


def clip_text(text_value, max_chars):
    text_value = str(text_value)
    if max_chars <= 0:
        return ""
    if len(text_value) <= max_chars:
        return text_value
    if max_chars <= 3:
        return text_value[:max_chars]
    return text_value[: max_chars - 3] + "..."


def clip_text_px(text_value, max_width):
    if max_width <= 0:
        return ""
    max_chars = max(1, (int(max_width) + 1) // CHAR_ADVANCE)
    return clip_text(text_value, max_chars)


class MonoCanvas:
    def __init__(self, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT):
        self.width = width
        self.height = height
        self.buffer = bytearray(width * height // 8)

    def clear(self, color=0):
        fill = 0xFF if color else 0x00
        for idx in range(len(self.buffer)):
            self.buffer[idx] = fill

    def pixel(self, x, y, color=1):
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        index = (y // 8) * self.width + x
        mask = 1 << (y % 8)
        if color:
            self.buffer[index] |= mask
        else:
            self.buffer[index] &= ~mask

    def hline(self, x, y, width, color=1):
        x = int(x)
        y = int(y)
        width = int(width)
        if width <= 0:
            return
        for offset in range(width):
            self.pixel(x + offset, y, color)

    def vline(self, x, y, height, color=1):
        x = int(x)
        y = int(y)
        height = int(height)
        if height <= 0:
            return
        for offset in range(height):
            self.pixel(x, y + offset, color)

    def rect(self, x, y, width, height, color=1):
        x = int(x)
        y = int(y)
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            return
        self.hline(x, y, width, color)
        self.hline(x, y + height - 1, width, color)
        self.vline(x, y, height, color)
        self.vline(x + width - 1, y, height, color)

    def fill_rect(self, x, y, width, height, color=1):
        x = int(x)
        y = int(y)
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            return
        for row in range(height):
            self.hline(x, y + row, width, color)

    def line(self, x0, y0, x1, y1, color=1):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = err * 2
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def draw_text(self, text_value, x, y, color=1, max_width=None):
        text_value = str(text_value)
        if max_width is not None:
            text_value = clip_text_px(text_value, max_width)

        cursor_x = int(x)
        y = int(y)
        color = 1 if color else 0
        for char in text_value:
            glyph = glyph_bytes(char)
            for col_idx, col_bits in enumerate(glyph):
                px = cursor_x + col_idx
                if px < 0 or px >= self.width:
                    continue
                for bit_idx in range(CHAR_HEIGHT):
                    py = y + bit_idx
                    if py < 0 or py >= self.height:
                        continue
                    if col_bits & (1 << bit_idx):
                        self.pixel(px, py, color)
            cursor_x += CHAR_ADVANCE
        return text_value

    def draw_text_in_rect(self, text_value, x, y, width, height, color=1, align="left"):
        text_value = clip_text_px(text_value, width)
        width = int(width)
        height = int(height)
        if align == "center":
            text_x = int(x) + max(0, (width - text_width(text_value)) // 2)
        elif align == "right":
            text_x = int(x) + max(0, width - text_width(text_value))
        else:
            text_x = int(x)
        text_y = int(y) + max(0, (height - CHAR_HEIGHT) // 2)
        return self.draw_text(text_value, text_x, text_y, color=color)

    def draw_text_center(self, text_value, y, color=1):
        text_value = clip_text_px(text_value, self.width - 2)
        text_x = max(0, (self.width - text_width(text_value)) // 2)
        return self.draw_text(text_value, text_x, int(y), color=color)

    def draw_text_right(self, text_value, right_x, y, color=1):
        text_value = clip_text_px(text_value, max(0, int(right_x)))
        text_x = max(0, int(right_x) - text_width(text_value))
        return self.draw_text(text_value, text_x, int(y), color=color)
