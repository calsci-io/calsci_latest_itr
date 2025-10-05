from .base_buffer import BaseBuffer

from data_modules.constants import KeyButtons as KB

NAV_VALUES = [
    KB.NAV_D, KB.NAV_L, KB.NAV_R, KB.NAV_U, KB.BACKSPACE, KB.ALL_CLEAR
]
class TextBuffer(BaseBuffer):
    def __init__(self):
        super().__init__()
        self.text_buffer = "𖤓" # -> the entire string.
        self.refresh_area = (0, self.rows * self.cols) #-> start and end point on the screen.
        self.buffer_size = len(self.text_buffer) #-> current size of the buffer 
        self.display_buffer_start = 0 #-> indicates the point on the string that which is the starting point on the screen
        self.display_buffer_end = min(self.buffer_size, self.display_buffer_start+self.total_buffer_size-1) 
        self.buffer_cursor = len(self.text_buffer) #-> points to the end of the string.
        self.content_length = len(self.text_buffer) 

    def buffer(self):
        self.buffer_size = len(self.text_buffer)
        remaining_spaces = (self.cols - (self.buffer_size%self.cols))%self.cols

        self.text_buffer += " "*remaining_spaces
        self.buffer_size += remaining_spaces
        
        self.extra_spaces = max(0, self.total_buffer_size - self.buffer_size)
        self.text_buffer += " "*self.extra_spaces
        self.buffer_size = len(self.text_buffer)

        self.display_buffer_end = min(self.buffer_size, self.display_buffer_start+self.total_buffer_size-1)

        rows = []

        for i in range(self.display_buffer_start, self.display_buffer_end,self.cols):
            row = self.text_buffer[i:i+self.cols]
            rows.append(row)

        return rows


    def navigate_buffer(self, inp):
        if inp == KB.ALL_CLEAR:
            self.all_clear()
            return
        
        past_buffer_cursor = self.buffer_cursor
        self.refresh_area = (0, self.total_buffer_size) 
        if inp == KB.NAV_D:
            self.buffer_cursor +=self.cols
        
        if inp == KB.NAV_R:
            self.buffer_cursor += 1

        if inp == KB.NAV_U:
            self.buffer_cursor -=self.cols

        if inp == KB.NAV_L or inp==KB.BACKSPACE:
            self.buffer_cursor -= 1


        if inp == KB.NAV_D or inp == KB.NAV_R:
            past_coords = (past_buffer_cursor - self.display_buffer_start)
            coords = (self.buffer_cursor - self.display_buffer_start)
            past_buffer_cal = (past_coords // self.cols) * self.cols
            current_buffer_cal = (coords // self.cols) * self.cols


            self.refresh_area = (
                past_coords % self.cols + past_buffer_cal,
                current_buffer_cal + self.cols
            )
            
            if self.buffer_cursor >= self.content_length:
                self.buffer_cursor = 0
                self.display_buffer_start = 0
                self.refresh_area = (0,min(self.content_length+self.cols, self.total_buffer_size))

            elif self.buffer_cursor > self.display_buffer_end:
                self.display_buffer_start += self.cols
                self.refresh_area = (0,self.total_buffer_size)
            
        elif inp == KB.NAV_U or inp == KB.NAV_L or inp == KB.BACKSPACE:
            going_bottom = False
            if inp == KB.BACKSPACE:                
                coords = (self.buffer_cursor - self.display_buffer_start)
                buffer_cal = (
                       coords // self.cols
                    ) * self.cols
                self.refresh_area = (
                    coords % self.cols
                    + buffer_cal,
                    self.rows * self.cols,
                )

            else:
                coords = (self.buffer_cursor - self.display_buffer_start)
                current_buffer_cal = (
                    coords // self.cols
                ) * self.cols

                past_buffer_cal = ((past_buffer_cursor - self.display_buffer_start) // self.cols) * self.cols

                self.refresh_area = (
                    coords % self.cols + current_buffer_cal,
                    past_buffer_cal + self.cols
                )
            
            if self.buffer_cursor <0:
                self.refresh_area = (0, self.total_buffer_size)
                going_bottom = True

                self.buffer_cursor = self.content_length-1 
                self.display_buffer_start = self.buffer_size - self.total_buffer_size
            
            elif self.buffer_cursor < self.display_buffer_start:
                self.refresh_area = (0, self.total_buffer_size)
                self.display_buffer_start -= self.cols



            if inp == KB.BACKSPACE:
                val = self.content_length-1 
                if val == self.display_buffer_end-self.cols-1 and val >=self.total_buffer_size:
                    self.display_buffer_start -= self.cols
                    self.display_buffer_start = max(self.display_buffer_start, 0)
                    self.refresh_area = (0, self.total_buffer_size)
                self.text_buffer = f"{self.text_buffer[:self.buffer_cursor]}{self.text_buffer[self.buffer_cursor+1:]}"
                if going_bottom == False:
                    self.content_length = max(1, self.content_length-1)


    def update_buffer(self, inp):
        if inp in NAV_VALUES:
            self.navigate_buffer(inp)
            self.text_buffer = f"{self.text_buffer[: self.content_length-1]}𖤓"
            return;
        self.refresh_area = (0, self.total_buffer_size)
        past_buffer_cursor = self.buffer_cursor
        self.text_buffer = f"{self.text_buffer[0:past_buffer_cursor]}{inp}{self.text_buffer[past_buffer_cursor:]}"
        self.content_length+=len(inp)
        self.buffer_size += len(inp) 
        self.buffer_cursor += len(inp) 

        past_display = past_buffer_cursor - self.display_buffer_start
        self.refresh_area = (
            past_display % self.cols + (past_display // self.cols) * self.cols,
            self.total_buffer_size
        )

        if self.buffer_cursor > self.total_buffer_size-1:
            self.display_buffer_start = (
                self.buffer_cursor - self.buffer_cursor % self.cols - ((self.rows-1)*self.cols)
            )

            self.refresh_area = (
                0,
                self.total_buffer_size
            )

        self.text_buffer = f"{self.text_buffer[:self.content_length-1]}𖤓"


    def all_clear(self):
        self.refresh_area = (0, self.total_buffer_size)
        self.display_buffer_start = 0
        self.buffer_size = 1
        self.text_buffer = "𖤓"
        self.buffer_cursor = 0
        self.content_length=1
        self.no_last_spaces = 0


    def cursor(self):
        return self.buffer_cursor - self.display_buffer_start
    
    def ref_ar(self):
        return self.refresh_area

