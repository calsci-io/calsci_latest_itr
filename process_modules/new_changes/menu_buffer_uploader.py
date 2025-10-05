from process_modules.new_changes.uploader import BaseUploader

class MenuUploader(BaseUploader):
    def __init__(self, disp_out, chrs, m_b):
        super().__init__(disp_out=disp_out, chrs=chrs)
        self.buffer_klass = m_b

    def refresh(self, state="default"):
        buf = self.buffer_klass.buffer()
        ref_rows = self.buffer_klass.ref_ar()

        for i in range(ref_rows[0], ref_rows[1]):
            self._clear_row_display(i)

            buf[i]+=" "*(self.buffer_klass.cols-len(buf[i]))

            for j in buf[i]:
                if i == self.buffer_klass.cursor():
                    self._print_character(j, invert=True)
                else:
                    self._print_character(j, invert=False)


