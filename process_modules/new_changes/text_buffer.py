from base_buffer import BaseBuffer

from data_modules.constants import KeyButtons as KB

NAV_VALUES = [
    KB.NAV_D, KB.NAV_L, KB.NAV_R, KB.NAV_U, KB.BACKSPACE, KB.ALL_CLEAR
]
class TextBuffer(BaseBuffer):
    def __init__(self, text_buffer="𖤓", rows=7, cols=21):
        super()
        if text_buffer != "𖤓": # flower character
            text_buffer += "𖤓"
        self.text_buffer = text_buffer
        self.refresh_area = (0, self.rows * self.cols)
        self.buffer_size = len(self.text_buffer)
        self.display_buffer_position = 0
        self.display_buffer = []
        self.set_display_buffer()

    def buffer(self):
        self.buffer_size = len(self.text_buffer)
        self.text_buffer_nospace = self.buffer_size-1
        remaining_spaces = (self.cols - (self.buffer_size%self.cols))%self.cols

        self.text_buffer += " "*remaining_spaces
        self.menu_buffer_size = self.buffer_size + remaining_spaces
        
        
        self.extra_spaces = max(0, self.total_buffer_size - self.menu_buffer_size)
        self.text_buffer += " "*self.extra_spaces
        self.menu_buffer_size = len(self.text_buffer)

        self.set_display_buffer() 

        rows = []

        for i in range(self.rows):
            start = self.display_buffer[self.cols*i]
            end = self.display_buffer[self.cols*(i+1)-1]+1
            row = self.text_buffer[start:end]

            rows.append(row)

        return rows


    def navigate_buffer(self, inp):
        if inp == KB.ALL_CLEAR:
            self.all_clear()
            return
        
        past_buffer_cursor = self.buffer_cursor
        self.refresh_area = (0, self.total_buffer_size) 
        if inp == KB.NAV_D:
            self.buffer_length +=self.cols
        
        if inp == KB.NAV_R:
            self.buffer_length += 1

        if inp == KB.NAV_U:
            self.buffer_length -=self.cols

        if inp == KB.NAV_L or inp==KB.BACKSPACE:
            self.buffer_length -= 1


        if inp == KB.NAV_D or inp == KB.NAV_R:
            past_coords = (past_buffer_cursor - self.display_buffer_position)
            coords = (self.buffer_length - self.display_buffer_position)
            past_buffer_cal = (past_coords // self.cols) * self.cols
            current_buffer_cal = (coords // self.cols) * self.cols

            self.refresh_area = (
                past_coords % self.cols + past_buffer_cal,
                current_buffer_cal + self.cols
            )

            if self.buffer_cursor >= self.buffer_length:
                self.buffer_cursor = 0
                self.display_buffer_position = 0
            elif self.buffer_cursor > self.display_buffer[-1]:
                self.display_buffer_position += self.cols
            
            self.refresh_area = (0, self.total_buffer_size)
        
        elif inp == KB.NAV_U or inp == KB.NAV_L or inp == KB.BACKSPACE:
            going_bottom = False
            if self.buffer_cursor <0:
                self.refresh_area = (0, self.total_buffer_size)
                going_bottom = True

                if self.buffer_size < self.total_buffer_size:
                    self.buffer_cursor = self.buffer_size-1
                else:
                    self.buffer_cursor = self.total_buffer_size-1
                    remaining_spaces = (self.cols - (self.buffer_size%self.cols))%self.cols-1
                    self.buffer_cursor -= remaining_spaces
                    self.buffer_cursor -= self.buffer_size
                self.display_buffer_position = self.buffer_size - self.total_buffer_size
            
            elif self.buffer_cursor < self.display_buffer[0]:
                self.refresh_area = (0, self.total_buffer_size)
                self.display_buffer_position -= self.cols
            

            if inp == KB.BACKSPACE:
                remaining_spaces = (self.cols - (self.buffer_size%self.cols))%self.cols-1
                val =(self.buffer_size - remaining_spaces - self.extra_spaces-1) 
                if val == self.display_buffer[-self.cols] and val >=self.total_buffer_size:
                    self.display_buffer_position -= self.cols
                    self.refresh_area = (0, self.total_buffer_size)

                self.text_buffer = f"{self.text_buffer[:self.buffer_cursor]}{self.text_buffer[self.buffer_cursor+1:]}"

                if going_bottom == False:
                    self.text_buffer_nospace = max(0, self.text_buffer_nospace-1)


            else:
                coords = (self.buffer_cursor - self.display_buffer_position)
                current_buffer_cal = (
                    coords // self.cols
                ) * self.cols

                past_buffer_cal = ((past_buffer_cursor - self.display_buffer_position) // self.cols) * self.cols

                self.refresh_area = (
                    coords % self.cols + current_buffer_cal,
                    past_buffer_cal + self.cols
                )

    def update_buffer(self, inp):
        if inp in NAV_VALUES:
            self.navigate_buffer(inp)
            return;

        self.refresh_area = (0, self.total_buffer_size)
        past_buffer_cursor = self.buffer_cursor

        self.text_buffer = f"{self.text_buffer[:past_buffer_cursor]}{inp}{self.text_buffer[past_buffer_cursor+1:]}"
        self.text_buffer_nospace += len(inp)
        self.buffer_size += len(inp) # text_buffer_size
        self.buffer_cursor += len(inp) # position of the cursor

        past_display = past_buffer_cursor - self.display_buffer_position
        self.refresh_area = (
            past_display % self.cols + (past_display // self.cols) * self.cols,
            self.total_buffer_size
        )

        if self.buffer_cursor > self.total_buffer_size-1:
            self.display_buffer_position = (
                self.buffer_cursor - self.buffer_cursor % self.cols - ((self.rows-1)*self.cols)
            )

            self.refresh_area = (
                0,
                self.total_buffer_size
            )

        
        self.text_buffer = f"{self.text_buffer[0:self.text_buffer_nospace]}𖤓"

    def set_display_buffer(self):
        self.display_buffer = []
        for i in range(self.display_buffer_position, min(self.display_buffer_position + self.total_buffer_size, self.buffer_size)): 
            self.display_buffer.append(i)


    def all_clear(self):
        self.refresh_area = (0, self.total_buffer_size)
        self.display_buffer_position = 0
        self.buffer_size = 1
        self.text_buffer = "𖤓"
        self.buffer_cursor = 0
        self.text_buffer_nospace = 0
        self.no_last_spaces = 0


    def cursor(self):
        return self.buffer_cursor - self.display_buffer_position