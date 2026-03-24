import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

from process_modules.ui_context import set_active_view

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.


class Tbf:
    def __init__(self, disp_out, chrs, f_b, nav=None):
        self.disp_out = disp_out
        self.chrs = chrs
        self.f_b = f_b
        self.nav = nav
        self.disp_out.clear_display()
        self.last_state = ""

    def _clear_page(self, page_index):
        self.disp_out.set_page_address(page_index)
        self.disp_out.set_column_address(0)
        for _ in range(128):
            self.disp_out.write_data(0b00000000)

    def _draw_page(self, buf, page_index):
        self._clear_page(page_index)
        if page_index < 0 or page_index >= self.f_b.rows or page_index >= len(buf):
            return

        if "inp_" in buf[page_index]:
            row_text = (
                "=>"
                + self.f_b.inp_list()[self.f_b.buffer()[page_index]][
                    self.f_b.inp_display_position() : self.f_b.inp_display_position()
                    + self.f_b.inp_cols()
                ]
            )
        else:
            row_text = buf[page_index]
        max_cols = self.f_b.inp_cols() + 2
        row_text = row_text[:max_cols]
        if len(row_text) < max_cols:
            row_text += " " * (max_cols - len(row_text))

        self.disp_out.set_page_address(page_index)
        self.disp_out.set_column_address(0)
        for col_index, char in enumerate(row_text):
            if page_index == self.f_b.cursor() and "inp_" not in buf[page_index]:
                char_bytes = self.chrs.invert_letter(char)
                cursor_line = 0b11111111
            elif page_index == self.f_b.cursor() and "inp_" in buf[page_index]:
                if col_index + self.f_b.inp_display_position() == self.f_b.inp_cursor() + 2:
                    char_bytes = self.chrs.invert_letter(char)
                    cursor_line = 0b11111111
                else:
                    char_bytes = self.chrs.Chr2bytes(char)
                    cursor_line = 0b00000000
            else:
                char_bytes = self.chrs.Chr2bytes(char)
                cursor_line = 0b00000000
            for byte in char_bytes:
                self.disp_out.write_data(byte)
            self.disp_out.write_data(cursor_line)
        for _ in range(max(0, 128 - (len(row_text) * 6))):
            self.disp_out.write_data(0b00000000)

    def _draw_state(self, state):
        if self.nav is not None:
            self.nav.draw_state(state)
            return
        self._clear_page(7)
        state = str(state or "")
        if state == "":
            return
        self.disp_out.set_column_address(0)
        for char in state:
            char_bytes = self.chrs.invert_letter(char)
            for byte in char_bytes:
                self.disp_out.write_data(byte)
            self.disp_out.write_data(0b11111111)

    def restore_bottom_row(self):
        try:
            self._draw_page(self.f_b.buffer(), self.f_b.rows - 1)
        except Exception:
            self._clear_page(7)
        self.last_state = ""

    def refresh(self, state=None):
        set_active_view("form")

        if state is None:
            state = self.nav.current_state() if self.nav is not None else ""

        buf = self.f_b.buffer()
        ref_rows = self.f_b.ref_ar()
        for page_index in range(ref_rows[0], min(ref_rows[1], self.f_b.rows)):
            self._draw_page(buf, page_index)

        if self.nav is not None:
            nav_overlay_visible = (
                str(state or "") != ""
                and str(state or "") == self.nav.current_state()
                and self.nav.is_visible()
            )
            self.nav.set_restore_callback(
                self.restore_bottom_row if nav_overlay_visible else None
            )

        state = str(state or "")
        if state != "":
            self._draw_state(state)
        elif self.last_state != "":
            self.restore_bottom_row()

        self.last_state = state
