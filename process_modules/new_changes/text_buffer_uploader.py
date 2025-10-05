from process_modules.new_changes.uploader import BaseUploader
class TextUploader(BaseUploader):
    def __init__(self, disp_out, chrs, t_b):
        super().__init__(disp_out=disp_out, chrs=chrs)
        self.buffer_klass = t_b


    def update(self, t_b_new):
        self.buffer_klass=t_b_new
    

    def refresh(self, state="default"):
        buf = self.buffer_klass.buffer()
        ref_ar = self.buffer_klass.ref_ar()
        start_row = ref_ar[0]//self.buffer_klass.cols
        end_row = ref_ar[1]//self.buffer_klass.cols
        for i in range(start_row, end_row):
            self._clear_row_display(i)
            if buf[i].strip()!="" or self.buffer_klass.cursor()//self.buffer_klass.cols==i:
                j_counter=0
                for j in buf[i]:
                    if j_counter+i*self.buffer_klass.cols==self.buffer_klass.cursor():
                        self._print_character(j, invert=True)
                    else:
                        self._print_character(j, invert=False)
                    j_counter+=1
            else:
                self._print_character(" ", invert=False)

        self._display_bar(state)
