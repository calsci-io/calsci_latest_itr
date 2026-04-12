try:
    import framebuf  # type: ignore
except ImportError:
    from mocking import framebuf  # type: ignore

from data_modules.characters import Characters
from data_modules.object_handler import display


DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64
DISPLAY_PAGES = DISPLAY_HEIGHT // 8
CHAR_WIDTH = 5
CHAR_HEIGHT = 8
CHAR_ADVANCE = 6


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
    def __init__(self):
        self.buf = bytearray((DISPLAY_WIDTH * DISPLAY_HEIGHT) // 8)
        self.fb = framebuf.FrameBuffer(self.buf, DISPLAY_WIDTH, DISPLAY_HEIGHT, framebuf.MONO_VLSB)

    def clear(self, color=0):
        self.fb.fill(1 if color else 0)

    def flush(self, page=0, pages=None):
        page = max(0, int(page))
        if pages is None:
            pages = DISPLAY_PAGES - page
        pages = max(0, int(pages))
        if pages <= 0 or page >= DISPLAY_PAGES:
            return
        if page + pages > DISPLAY_PAGES:
            pages = DISPLAY_PAGES - page

        start = page * DISPLAY_WIDTH
        end = start + (pages * DISPLAY_WIDTH)
        display.graphics(
            memoryview(self.buf)[start:end],
            page=page,
            column=0,
            width=DISPLAY_WIDTH,
            pages=pages,
        )

    def rect(self, x, y, width, height, color=1):
        self.fb.rect(int(x), int(y), int(width), int(height), 1 if color else 0)

    def fill_rect(self, x, y, width, height, color=1):
        self.fb.fill_rect(int(x), int(y), int(width), int(height), 1 if color else 0)

    def hline(self, x, y, width, color=1):
        self.fb.hline(int(x), int(y), int(width), 1 if color else 0)

    def vline(self, x, y, height, color=1):
        self.fb.vline(int(x), int(y), int(height), 1 if color else 0)

    def pixel(self, x, y, color=1):
        self.fb.pixel(int(x), int(y), 1 if color else 0)

    def draw_text(self, text_value, x, y, color=1, max_width=None):
        text_value = str(text_value)
        if max_width is not None:
            text_value = clip_text_px(text_value, max_width)

        color = 1 if color else 0
        cursor_x = int(x)
        y = int(y)
        for char in text_value:
            glyph = Characters.Chr2bytes(Characters, char)
            for col_idx, col_bits in enumerate(glyph):
                px = cursor_x + col_idx
                if px < 0 or px >= DISPLAY_WIDTH:
                    continue
                for bit_idx in range(CHAR_HEIGHT):
                    py = y + bit_idx
                    if py < 0 or py >= DISPLAY_HEIGHT:
                        continue
                    if col_bits & (1 << bit_idx):
                        self.fb.pixel(px, py, color)
            cursor_x += CHAR_ADVANCE
        return text_value

    def draw_text_in_rect(self, text_value, x, y, width, height, color=1, align="left"):
        text_value = clip_text_px(text_value, width)
        tw = text_width(text_value)

        if align == "center":
            text_x = int(x) + max(0, (int(width) - tw) // 2)
        elif align == "right":
            text_x = int(x) + max(0, int(width) - tw)
        else:
            text_x = int(x)

        text_y = int(y) + max(0, (int(height) - CHAR_HEIGHT) // 2)
        self.draw_text(text_value, text_x, text_y, color=color)
        return text_value

    def draw_text_center(self, text_value, y, color=1):
        text_value = clip_text_px(text_value, DISPLAY_WIDTH - 2)
        tw = text_width(text_value)
        text_x = max(0, (DISPLAY_WIDTH - tw) // 2)
        self.draw_text(text_value, text_x, int(y), color=color)
        return text_value

    def draw_text_right(self, text_value, right_x, y, color=1):
        text_value = clip_text_px(text_value, max(0, int(right_x)))
        tw = text_width(text_value)
        text_x = max(0, int(right_x) - tw)
        self.draw_text(text_value, text_x, int(y), color=color)
        return text_value
