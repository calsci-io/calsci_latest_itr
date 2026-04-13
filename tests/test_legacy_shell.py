import unittest

from ui.legacy_shell import (
    CONTENT_W,
    CONTENT_X,
    CONTENT_Y,
    FOOTER_Y,
    FORM_INPUT_GAP,
    FORM_LABEL_W,
    FORM_MESSAGE_H,
    FORM_ROW_GAP,
    FORM_ROW_H,
    LegacyShellRenderer,
    MENU_ROW_GAP,
    MENU_ROW_H,
    PANEL_H,
    PANEL_Y,
)
from ui.models import FormField, FormScreen, MenuScreen, TextScreen
from ui.theme import DISPLAY_WIDTH


def _pixel(buffer_bytes, x, y):
    index = (y // 8) * DISPLAY_WIDTH + x
    mask = 1 << (y % 8)
    return 1 if (buffer_bytes[index] & mask) else 0


def _area_has_pixel(buffer_bytes, x, y, width, height):
    for row in range(y, y + height):
        for col in range(x, x + width):
            if _pixel(buffer_bytes, col, row):
                return True
    return False


class _FakeStorage:
    def __init__(self, dark_mode=False):
        self._dark_mode = dark_mode

    def get_setting(self, key, default=None):
        if key == "dark_mode":
            return self._dark_mode
        return default


class _FakeDisplay:
    def __init__(self):
        self.inverted = None
        self.frames = []

    def set_invert(self, enabled):
        self.inverted = bool(enabled)

    def draw_canvas(self, buffer_bytes):
        self.frames.append(bytes(buffer_bytes))


class LegacyShellRendererTests(unittest.TestCase):
    def test_render_service_menu_uses_full_framebuffer_shell(self):
        from services.render_service import RenderService

        display = _FakeDisplay()
        service = RenderService(display, _FakeStorage(dark_mode=True))
        service.render(MenuScreen("calsci", ["One", "Two", "Three", "Four"], selected=1, footer="default"))

        self.assertTrue(display.inverted)
        self.assertEqual(len(display.frames), 1)
        frame = display.frames[0]
        self.assertEqual(len(frame), 1024)
        selected_y = CONTENT_Y + (MENU_ROW_H + MENU_ROW_GAP) + 5
        idle_y = CONTENT_Y + 5
        sample_x = CONTENT_X + CONTENT_W - 8
        self.assertEqual(_pixel(frame, sample_x, selected_y), 1)
        self.assertEqual(_pixel(frame, sample_x, idle_y), 0)
        self.assertTrue(_area_has_pixel(frame, 0, FOOTER_Y - 1, DISPLAY_WIDTH, 9))

    def test_text_shell_wraps_into_second_line(self):
        renderer = LegacyShellRenderer()
        frame = renderer.render_text(
            TextScreen("Status", ["abcdefghijklmnopqrstuvwxyz"], footer="ok")
        )

        first_line_y = CONTENT_Y + 1
        second_line_y = CONTENT_Y + 1 + 10
        self.assertTrue(_area_has_pixel(frame, CONTENT_X, first_line_y, CONTENT_W, 8))
        self.assertTrue(_area_has_pixel(frame, CONTENT_X, second_line_y, CONTENT_W, 8))

    def test_form_shell_draws_selected_field_caret_and_message(self):
        renderer = LegacyShellRenderer()
        frame = renderer.render_form(
            FormScreen(
                "WiFi",
                [
                    FormField("ssid", "SSID", "MyNet"),
                    FormField("password", "Pass", ""),
                ],
                selected=1,
                footer="alpha",
                message="Enter password",
            )
        )

        row_y = CONTENT_Y + (FORM_ROW_H + FORM_ROW_GAP)
        input_x = CONTENT_X + FORM_LABEL_W + FORM_INPUT_GAP
        self.assertEqual(_pixel(frame, input_x + 3, row_y + 4), 0)
        self.assertEqual(_pixel(frame, input_x + 14, row_y + 4), 1)
        message_y = PANEL_Y + PANEL_H - FORM_MESSAGE_H - 2
        self.assertTrue(_area_has_pixel(frame, CONTENT_X, message_y, CONTENT_W, FORM_MESSAGE_H))

    def test_form_shell_draws_overflow_scrollbar_for_active_value(self):
        renderer = LegacyShellRenderer()
        frame = renderer.render_form(
            FormScreen(
                "Matrix",
                [FormField("a", "A", "123456789012345678901234567890")],
                selected=0,
                footer="default",
            )
        )

        row_y = CONTENT_Y
        input_x = CONTENT_X + FORM_LABEL_W + FORM_INPUT_GAP
        scrollbar_y = row_y + FORM_ROW_H - 2
        self.assertTrue(_area_has_pixel(frame, input_x + 2, scrollbar_y - 1, CONTENT_W - FORM_LABEL_W, 3))


if __name__ == "__main__":
    unittest.main()
