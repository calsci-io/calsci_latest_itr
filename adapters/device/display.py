import st7565

from adapters.device.hardware_config import (
    DISPLAY_CS1_PIN,
    DISPLAY_RS_PIN,
    DISPLAY_RST_PIN,
    DISPLAY_SCK_PIN,
    DISPLAY_SDA_PIN,
)
from ui.canvas import MonoCanvas
from ui.theme import CHAR_HEIGHT, DISPLAY_HEIGHT, DISPLAY_PAGES, DISPLAY_WIDTH, TEXT_COLS


class DeviceDisplayAdapter:
    """Display adapter backed by the firmware ST7565 bulk framebuffer API."""

    def __init__(self):
        self.display = st7565
        self._initialized = False

    def init(self):
        """Initialize display hardware"""
        if self._initialized:
            return
        self.display.init(
            DISPLAY_CS1_PIN,
            DISPLAY_RS_PIN,
            DISPLAY_RST_PIN,
            DISPLAY_SDA_PIN,
            DISPLAY_SCK_PIN,
        )
        if hasattr(self.display, "on"):
            self.display.on()
        if hasattr(self.display, "all_points_on"):
            self.display.all_points_on(False)
        self.display.invert(False)
        self.display.clear_display()
        self._initialized = True

    def set_invert(self, enabled):
        """Toggle inversion (dark mode) - handled in render service"""
        self.init()
        self.display.invert(bool(enabled))

    def clear(self):
        """Clear display"""
        self.init()
        self.display.clear_display()

    def _new_canvas(self):
        return MonoCanvas(DISPLAY_WIDTH, DISPLAY_HEIGHT)

    def _flush(self, buffer_bytes, page=0, column=0, width=DISPLAY_WIDTH, pages=DISPLAY_PAGES):
        self.init()
        self.display.graphics(buffer_bytes, page=page, column=column, width=width, pages=pages)

    def draw_lines(self, lines, selected_line=None, footer=""):
        """Render text screens to a framebuffer, then flush through graphics()."""
        canvas = self._new_canvas()
        canvas.clear()
        content_rows = DISPLAY_PAGES - (1 if footer else 0)
        visible_lines = list(lines[:content_rows])
        for page, text in enumerate(visible_lines):
            y = page * CHAR_HEIGHT
            highlighted = page == selected_line
            if highlighted:
                canvas.fill_rect(0, y, DISPLAY_WIDTH, CHAR_HEIGHT, 1)
            canvas.draw_text(str(text or "")[:TEXT_COLS], 0, y, color=0 if highlighted else 1, max_width=DISPLAY_WIDTH)
        if footer:
            footer_y = (DISPLAY_PAGES - 1) * CHAR_HEIGHT
            canvas.fill_rect(0, footer_y, DISPLAY_WIDTH, CHAR_HEIGHT, 1)
            canvas.draw_text(str(footer)[:TEXT_COLS], 0, footer_y, color=0, max_width=DISPLAY_WIDTH)
        self._flush(canvas.buffer)

    def draw_canvas(self, buffer_bytes):
        """Draw a full 128x64 framebuffer."""
        if len(buffer_bytes) != DISPLAY_WIDTH * DISPLAY_PAGES:
            raise ValueError("canvas buffer must be %d bytes" % (DISPLAY_WIDTH * DISPLAY_PAGES))
        self._flush(buffer_bytes)
