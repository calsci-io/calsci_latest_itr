class BaseUploader:
    def __init__(self, disp_out, chrs):
        self.disp_out=disp_out
        self.chrs=chrs
        self.disp_out.clear_display()
    def update(self, buffer):
        raise NotImplementedError("To be overridden!")
    def refresh(self, state="default"):
        raise NotImplementedError("To be overridden!")

    
    def _print_character(self, chtr, invert=False):
        chtr_byte_data = self.chrs.Chr2bytes(chtr)
        cursor_line = 0b00000000
        if invert:
            chtr_byte_data=self.chrs.invert_letter(chtr)
            cursor_line = 0b11111111
        for k in chtr_byte_data:
            self.disp_out.write_data(k)
        self.disp_out.write_data(cursor_line)
    
    def _display_bar(self, state):
        self.disp_out.set_page_address(7)
        self.disp_out.set_column_address(0)
        j_counter=0
        for j in state:
            chtr=j
            chtr_byte_data=self.chrs.invert_letter(chtr)
            cursor_line=0b11111111
            for k in chtr_byte_data:
                self.disp_out.write_data(k)
            self.disp_out.write_data(cursor_line)
            j_counter+=1
    
    def _clear_row_display(self, row):
        self.disp_out.set_page_address(row)
        self.disp_out.set_column_address(0)