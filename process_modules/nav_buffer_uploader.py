# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

class Tbf:
    def __init__(self, disp_out, chrs, m_b):
        self.disp_out = disp_out
        self.chrs = chrs
        self.m_b = m_b
        self.disp_out.graphics(bytearray(128), page=7, column=0, width=128, pages=1)
        
    def refresh(self, state="default"):
        self.disp_out.set_page_address(7)
        self.disp_out.set_column_address(0)
        for j in state:
            chtr_byte_data = self.chrs.invert_letter(j)
            cursor_line = 0b11111111
            for k in chtr_byte_data:
                self.disp_out.write_data(k)
            self.disp_out.write_data(cursor_line)
