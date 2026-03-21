import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

class Tbf:
    def __init__(self, disp_out, chrs, t_b, nav=None):
        self.disp_out = disp_out
        self.chrs = chrs
        self.t_b = t_b
        self.nav = nav
        self.disp_out.clear_display()
        self.last_state = ""
        self.new = False

    def update(self, t_b_new):
        self.t_b = t_b_new

    def _clear_page(self, page_index):
        self.disp_out.set_page_address(page_index)
        self.disp_out.set_column_address(0)
        for _ in range(128):
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
        invert = (
            "default" in state
            or "alpha" in state
            or "beta" in state
            or "ALPHA" in state
        )
        for char in state:
            if invert:
                char_bytes = self.chrs.invert_letter(char)
                cursor_line = 0b11111111
            else:
                char_bytes = self.chrs.Chr2bytes(char)
                cursor_line = 0b00000000
            for byte in char_bytes:
                self.disp_out.write_data(byte)
            self.disp_out.write_data(cursor_line)

    def _draw_page(self, buf, page_index):
        self._clear_page(page_index)
        if page_index < 0 or page_index >= self.t_b.rows or page_index >= len(buf):
            return

        should_draw = (
            buf[page_index].strip() != ""
            or self.t_b.cursor() // self.t_b.cols == page_index
        ) or self.t_b.ac
        if not should_draw:
            return

        self.disp_out.set_page_address(page_index)
        self.disp_out.set_column_address(0)
        row_text = buf[page_index][: self.t_b.cols]
        if len(row_text) < self.t_b.cols:
            row_text += " " * (self.t_b.cols - len(row_text))
        for col_index, char in enumerate(row_text):
            cursor_line = 0b00000000
            char_bytes = self.chrs.Chr2bytes(char)
            if col_index + page_index * self.t_b.cols == self.t_b.cursor():
                char_bytes = self.chrs.invert_letter(char)
                cursor_line = 0b11111111
            for byte in char_bytes:
                self.disp_out.write_data(byte)
            self.disp_out.write_data(cursor_line)
        for _ in range(max(0, 128 - (self.t_b.cols * 6))):
            self.disp_out.write_data(0b00000000)

    def restore_bottom_row(self):
        try:
            buf = self.t_b.buffer()
            self._draw_page(buf, self.t_b.rows - 1)
        except Exception:
            self._clear_page(7)
        self.last_state = ""

    def refresh(self, state=None):
        if state is None:
            state = self.nav.current_state() if self.nav is not None else ""

        buf = self.t_b.buffer()
        ref_ar = self.t_b.ref_ar()
        start_page = ref_ar[0] // self.t_b.cols
        end_page = (ref_ar[1] + self.t_b.cols - 1) // self.t_b.cols
        for page_index in range(start_page, min(end_page, self.t_b.rows)):
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

        if state != "":
            self._draw_state(state)
        elif self.last_state != "" or self.new:
            self.restore_bottom_row()

        self.last_state = str(state or "")
        self.new = False
