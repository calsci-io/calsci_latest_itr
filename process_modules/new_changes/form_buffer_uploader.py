from process_modules.new_changes.uploader import BaseUploader
class FormUploader(BaseUploader):
    def __init__(self, disp_out, chrs, buffer_klass):
        super().__init__(disp_out=disp_out, chrs=chrs)
        self.buffer_klass = buffer_klass

    def refresh(self, state="default"):
        buf=self.buffer_klass.buffer()
        ref_rows=self.buffer_klass.ref_ar()
        for i in range(ref_rows[0], ref_rows[1]):
            self._clear_row_display(i)
            if "inp_" in buf[i]:
                buf_current="=>"+self.buffer_klass.inp_list()[self.f_b.buffer()[i]][self.f_b.inp_display_position():self.f_b.inp_display_position()+self.f_b.inp_cols()]
            else:
                buf_current = buf[i]
            if len(buf_current)<self.buffer_klass.inp_cols():
                    buf_current+=" "*(self.buffer_klass.inp_cols()-len(buf_current)+2)
            j_counter=0
            for j in buf_current:
                if i==self.buffer_klass.cursor():
                    if "inp_" not in buf[i]:
                        self._print_character(j, invert=True)
                    elif "inp_" in buf[i]:
                        if j_counter+self.buffer_klass.inp_display_position()==self.f_b.inp_cursor()+2:
                            self._print_character(j, invert=True)
                        else:
                            self._print_character(j, invert=False)
                else:
                    self._print_character(j, invert=False)
                j_counter+=1
        self._display_bar(state)     
    