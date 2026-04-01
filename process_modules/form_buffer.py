import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

class Form:
    def __init__(
        self,
        rows=8,
        menu_cursor=0,
        menu_display_position=0,
        input_list=None,
        form_list=None,
        input_cursor=0,
        input_display_position=0,
        input_cols=19,
    ):
        self.rows = rows
        self.input_list = input_list or {"inp_0": " ", "inp_1": " ", "inp_2": " "}
        self.form_list = form_list or [
            "label_0",
            "inp_0",
            "label_1",
            "inp_1",
            "label_2",
            "inp_2",
        ]
        self.input_cursor = input_cursor
        self.input_display_position = input_display_position
        self.input_cols = input_cols
        self.focus_inputs_only = False
        self.ui_style = "boxed"
        self.blink_cursor = True
        self.title = ""
        self.actual_rows = (
            self.rows if len(self.form_list) >= self.rows else len(self.form_list)
        )
        self.refresh_rows = (0, self.actual_rows)
        self.menu_display_size = self.actual_rows
        self.menu_display_position = menu_display_position
        self.display_buffer = self.form_list[
            self.menu_display_position : self.menu_display_position
            + self.menu_display_size
        ]
        self.menu_cursor = menu_cursor
        self.display_cursor = self.menu_cursor - self.menu_display_position

    def _is_input_row(self, index):
        if index < 0 or index >= len(self.form_list):
            return False
        return "inp_" in str(self.form_list[index])

    def _input_indices(self):
        return [index for index, item in enumerate(self.form_list) if "inp_" in str(item)]

    def active_input_key(self):
        if self._is_input_row(self.menu_cursor):
            return self.form_list[self.menu_cursor]
        return None

    def _sync_input_view(self, prefer_end=False):
        active_key = self.active_input_key()
        if active_key is None:
            self.input_cursor = 0
            self.input_display_position = 0
            return

        current_value = str(self.input_list.get(active_key, " ") or " ")
        if current_value == "":
            current_value = " "
            self.input_list[active_key] = current_value

        max_cursor = max(0, len(current_value) - 1)
        if prefer_end:
            self.input_cursor = max_cursor
        else:
            self.input_cursor = min(max(0, self.input_cursor), max_cursor)

        max_display = max(0, len(current_value) - self.input_cols)
        self.input_display_position = min(
            max(0, self.input_display_position),
            max_display,
        )

        if self.input_cursor < self.input_display_position:
            self.input_display_position = self.input_cursor
        elif self.input_cursor >= self.input_display_position + self.input_cols:
            self.input_display_position = self.input_cursor - self.input_cols + 1

    def _focus_input(self, step):
        input_indices = self._input_indices()
        if not input_indices:
            return False

        if self.menu_cursor in input_indices:
            current_pos = input_indices.index(self.menu_cursor)
            self.menu_cursor = input_indices[(current_pos + step) % len(input_indices)]
        elif step >= 0:
            next_inputs = [index for index in input_indices if index > self.menu_cursor]
            self.menu_cursor = next_inputs[0] if next_inputs else input_indices[0]
        else:
            prev_inputs = [index for index in input_indices if index < self.menu_cursor]
            self.menu_cursor = prev_inputs[-1] if prev_inputs else input_indices[-1]

        max_top = max(0, len(self.form_list) - self.actual_rows)
        self.menu_display_position = min(max(0, self.menu_cursor - 1), max_top)
        self._sync_input_view(prefer_end=True)
        self.refresh_rows = (0, self.actual_rows)
        return True

    def update_buffer(self, inp):

        if inp == "nav_d":
            if self.focus_inputs_only:
                self._focus_input(1)
                self.display_buffer = self.form_list[
                    self.menu_display_position : self.menu_display_position
                    + self.menu_display_size
                ]
                self.display_cursor = self.menu_cursor - self.menu_display_position
                return
            self.menu_cursor += 1

            if self.menu_cursor==len(self.form_list):
                self.menu_cursor=0
                self.menu_display_position=0
                self.refresh_rows=(0,self.actual_rows)

            elif self.menu_cursor-self.menu_display_position==self.actual_rows:
                self.menu_display_position+=1
                self.refresh_rows=(0,self.actual_rows)

            else:
                self.refresh_rows = (
                    self.menu_cursor - 1 - self.menu_display_position,
                    self.menu_cursor - self.menu_display_position + 1,
                )
            self.input_cursor = 0
            self.input_display_position = 0

        elif inp == "nav_u":
            if self.focus_inputs_only:
                self._focus_input(-1)
                self.display_buffer = self.form_list[
                    self.menu_display_position : self.menu_display_position
                    + self.menu_display_size
                ]
                self.display_cursor = self.menu_cursor - self.menu_display_position
                return
            self.menu_cursor -= 1

            if self.menu_cursor<0:
                self.menu_cursor=len(self.form_list)-1
                self.menu_display_position=len(self.form_list)-self.actual_rows
                self.refresh_rows=(0,self.actual_rows)

            elif self.menu_cursor<self.menu_display_position:
                self.menu_display_position-=1
                self.refresh_rows=(0,self.actual_rows)

            else:
                self.refresh_rows = (
                    self.menu_cursor - self.menu_display_position,
                    self.menu_cursor - self.menu_display_position + 2,
                )

            self.input_cursor = 0
            self.input_display_position = 0

        else:
            if "inp_" in self.form_list[self.menu_cursor]:
                self.refresh_rows = (
                    self.menu_cursor - self.menu_display_position,
                    self.menu_cursor - self.menu_display_position + 1,
                )
                if inp == "nav_r":
                    self.input_cursor += 1

                    if self.input_cursor == len(
                        self.input_list[self.form_list[self.menu_cursor]]
                    ):
                        self.input_cursor = 0
                        self.input_display_position = 0

                    elif self.input_cursor == self.input_display_position + self.input_cols:
                        self.input_display_position += 1
                    
                elif inp == "nav_l" or inp == "nav_b":
                    self.input_cursor -= 1
                    
                    if self.input_cursor < 0:
                        self.input_cursor = (
                            len(self.input_list[self.form_list[self.menu_cursor]]) - 1
                        )
                        self.input_display_position = (
                            len(self.input_list[self.form_list[self.menu_cursor]])
                            - self.input_cols
                        )
                        if self.input_display_position < 0:
                            self.input_display_position = 0

                    elif self.input_cursor < self.input_display_position:
                        self.input_display_position -= 1

                    if (
                        inp == "nav_b"
                        and self.input_cursor
                        != len(self.input_list[self.form_list[self.menu_cursor]]) - 1
                    ):
                        current_value = self.input_list[self.form_list[self.menu_cursor]]
                        self.input_list[self.form_list[self.menu_cursor]] = (
                            current_value[: self.input_cursor]
                            + current_value[self.input_cursor + 1 :]
                        )
                        if (
                            len(self.input_list[self.form_list[self.menu_cursor]])
                            > self.input_cols
                            and len(
                                self.input_list[self.form_list[self.menu_cursor]][
                                    self.input_display_position :
                                ]
                            )
                            < self.input_cols
                        ):
                            self.input_display_position = (
                                len(self.input_list[self.form_list[self.menu_cursor]])
                                - self.input_cols
                            )
                        elif len(self.input_list[self.form_list[self.menu_cursor]]) <= self.input_cols:
                            self.input_display_position = 0
                elif inp == "AC":
                    self.input_list[self.form_list[self.menu_cursor]] = " "
                    self.input_cursor = 0
                    self.input_display_position = 0

                        
                else:
                    if len(inp) > 1:
                        for chr in inp:
                            current_value = self.input_list[
                                self.form_list[self.menu_cursor]
                            ]
                            self.input_list[self.form_list[self.menu_cursor]] = (
                                current_value[: self.input_cursor]
                                + chr
                                + current_value[self.input_cursor :]
                            )
                            self.input_cursor += len(chr)
                
                            if self.input_cursor == self.input_display_position + self.input_cols:
                                self.input_display_position += 1
                    else:
                        current_value = self.input_list[self.form_list[self.menu_cursor]]
                        self.input_list[self.form_list[self.menu_cursor]] = (
                            current_value[: self.input_cursor]
                            + inp
                            + current_value[self.input_cursor :]
                        )
                        self.input_cursor += len(inp)
                    
                        if self.input_cursor == self.input_display_position + self.input_cols:
                            self.input_display_position += 1
                self.input_list[self.form_list[self.menu_cursor]] = (
                    self.input_list[self.form_list[self.menu_cursor]].rstrip() + " "
                )
                self._sync_input_view()

        self.display_buffer = self.form_list[
            self.menu_display_position : self.menu_display_position
            + self.menu_display_size
        ]
        self.display_cursor = self.menu_cursor - self.menu_display_position
    
    def ref_ar(self):
        return self.refresh_rows
    
    def buffer(self):
        return self.display_buffer
    
    def cursor(self):
        return self.display_cursor
    
    def act_rows(self):
        return self.actual_rows
    
    def inp_cursor(self):
        return self.input_cursor
    
    def inp_list(self):
        return self.input_list
    
    def inp_display_position(self):
        return self.input_display_position
    
    def inp_cols(self):
        return self.input_cols
    
    def update(self):
        self.actual_rows = (
            self.rows if len(self.form_list) >= self.rows else len(self.form_list)
        )
        self.refresh_rows = (0, self.actual_rows)
        self.menu_display_size = self.actual_rows
        self.menu_display_position = 0
        self.display_buffer = self.form_list[
            self.menu_display_position : self.menu_display_position
            + self.menu_display_size
        ]
        self.menu_cursor = 0
        if self.focus_inputs_only:
            input_indices = self._input_indices()
            if input_indices:
                self.menu_cursor = input_indices[0]
        self.display_cursor = self.menu_cursor - self.menu_display_position
        self._sync_input_view(prefer_end=self.focus_inputs_only)
        
    def update_label(self, index_label, new_label):
        self.form_list[index_label] = new_label
    

def test2():
    form = Form()

    while True:
        print("Current form_list:", form.form_list)
        print("Current input_list:", form.inp_list())
        print("\n")

        for i in range(form.act_rows()):
            if "inp_" in form.buffer()[i]:
                print(
                    f"{i}: Input Field ({form.buffer()[i]}): "
                    f"{form.inp_list()[form.buffer()[i]][form.inp_display_position():form.inp_display_position() + form.inp_cols()]}"
                )
            else:
                print(f"{i}: Label: {form.buffer()[i]}")

        inp = input("Enter command (or text): ")
        form.update_buffer(inp)

        if inp == "ok":
            current_input_key = form.buffer()[form.cursor()]
            if "inp_" in current_input_key:
                input_text = form.inp_list()[current_input_key].strip()
                label_index = form.form_list.index(current_input_key) - 1
                form.update_label(label_index, input_text)
                form.input_list[current_input_key] = " "  
                print(f"Label updated: {form.form_list[label_index]}")
                print(f"Input field cleared: {current_input_key}")
