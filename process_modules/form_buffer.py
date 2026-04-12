import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from data_modules.math_symbols import normalize_pi_token


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
        self.table_headers = []
        self.table_keys = []
        self.table_row_count = 0
        self.table_visible_rows = 4
        self.table_visible_cols = 5
        self.table_input_cols = 10
        self.table_row_labels = []
        self.table_row_header_w = 0
        self.table_show_scrollbars = False
        self.table_row_label_provider = None
        self.table_active_label = ""
        self.table_row_header_title = ""
        self.table_cursor_row = 0
        self.table_cursor_col = 0
        self.table_row_offset = 0
        self.table_col_offset = 0
        self.table_show_button = True
        self.table_button_text = "Ok"
        self.actual_rows = self.rows if len(self.form_list) >= self.rows else len(self.form_list)
        self.refresh_rows = (0, self.actual_rows)
        self.menu_display_size = self.actual_rows
        self.menu_display_position = menu_display_position
        self.display_buffer = self.form_list[
            self.menu_display_position : self.menu_display_position + self.menu_display_size
        ]
        self.menu_cursor = menu_cursor
        self.display_cursor = self.menu_cursor - self.menu_display_position

    def _ui_style(self):
        return str(getattr(self, "ui_style", "") or "").strip().lower()

    def _use_block_navigation(self):
        return self._ui_style() in ("buffer", "compact", "widgets")

    def _use_table_layout(self):
        return self._ui_style() in ("table", "sheet", "grid")

    def _active_input_cols(self):
        if self._use_table_layout():
            return max(1, int(getattr(self, "table_input_cols", self.input_cols) or 1))
        return max(1, int(self.input_cols or 1))

    def configure_table(
        self,
        headers=None,
        row_count=None,
        values=None,
        visible_rows=4,
        visible_cols=None,
        input_cols=10,
        row_labels=None,
        row_header_w=0,
        show_scrollbars=False,
        button_text="Ok",
        show_button=True,
    ):
        old_keys = set()
        for row in getattr(self, "table_keys", []) or []:
            if not isinstance(row, (list, tuple)):
                continue
            for key in row:
                if key not in (None, ""):
                    old_keys.add(str(key))
        for key in old_keys:
            self.input_list.pop(key, None)

        headers = list(headers or [])
        values = list(values or [])
        if row_count is None:
            row_count = len(values)
        row_count = max(int(row_count or 0), len(values), 1 if headers else 0)
        col_count = max(len(headers), max((len(row) for row in values), default=0))

        if col_count <= 0:
            self.table_headers = []
            self.table_keys = []
            self.table_row_count = 0
            self.table_cursor_row = 0
            self.table_cursor_col = 0
            self.table_row_offset = 0
            self.table_col_offset = 0
            self.update()
            return

        if visible_cols is None:
            visible_cols = min(5, col_count)
        if len(headers) < col_count:
            headers.extend([""] * (col_count - len(headers)))

        table_keys = []
        for row_index in range(row_count):
            row_values = list(values[row_index]) if row_index < len(values) else []
            row_keys = []
            for col_index in range(col_count):
                key = "tbl_{}_{}".format(row_index, col_index)
                row_keys.append(key)
                cell_value = row_values[col_index] if col_index < len(row_values) else ""
                self.input_list[key] = str(cell_value or "").rstrip() + " "
            table_keys.append(row_keys)

        self.table_headers = headers
        self.table_keys = table_keys
        self.table_row_count = row_count
        self.table_visible_rows = max(1, int(visible_rows or 1))
        self.table_visible_cols = max(1, int(visible_cols or 1))
        self.table_input_cols = max(1, int(input_cols or 1))
        self.table_row_labels = list(row_labels or [])
        self.table_row_header_w = max(0, int(row_header_w or 0))
        self.table_show_scrollbars = bool(show_scrollbars)
        self.table_row_label_provider = None
        self.table_active_label = ""
        self.table_row_header_title = ""
        self.table_cursor_row = 0
        self.table_cursor_col = 0
        self.table_row_offset = 0
        self.table_col_offset = 0
        self.table_show_button = bool(show_button)
        self.table_button_text = str(button_text or "Ok")
        self.update()

    def _table_col_count(self):
        max_cols = len(getattr(self, "table_headers", []) or [])
        for row in getattr(self, "table_keys", []) or []:
            if isinstance(row, (list, tuple)) and len(row) > max_cols:
                max_cols = len(row)
        return max_cols

    def _table_row_total(self):
        return max(
            int(getattr(self, "table_row_count", 0) or 0),
            len(getattr(self, "table_keys", []) or []),
        )

    def _table_cell_key(self, row_index, col_index):
        table_keys = getattr(self, "table_keys", []) or []
        if row_index < 0 or col_index < 0 or row_index >= len(table_keys):
            return None
        row_keys = table_keys[row_index]
        if not isinstance(row_keys, (list, tuple)) or col_index >= len(row_keys):
            return None
        cell_key = row_keys[col_index]
        if cell_key in (None, ""):
            return None
        return str(cell_key)

    def _ensure_table_grid(self):
        if not self._use_table_layout():
            return

        headers = list(getattr(self, "table_headers", []) or [])
        rows = []
        for row in getattr(self, "table_keys", []) or []:
            if isinstance(row, (list, tuple)):
                rows.append([str(cell or "") for cell in row])

        col_count = max(len(headers), max((len(row) for row in rows), default=0))
        desired_rows = max(self._table_row_total(), len(rows))

        if col_count <= 0:
            self.table_headers = headers
            self.table_keys = []
            self.table_row_count = 0
            self.table_cursor_row = 0
            self.table_cursor_col = 0
            self.table_row_offset = 0
            self.table_col_offset = 0
            return

        if len(headers) < col_count:
            headers.extend([""] * (col_count - len(headers)))
        while len(rows) < desired_rows:
            rows.append([])

        for row_index, row in enumerate(rows):
            while len(row) < col_count:
                row.append("")
            for col_index, key in enumerate(row):
                if key == "":
                    key = "tbl_{}_{}".format(row_index, col_index)
                    row[col_index] = key
                if key not in self.input_list:
                    self.input_list[key] = " "

        self.table_headers = headers
        self.table_keys = rows
        self.table_row_count = len(rows)
        self.table_visible_rows = max(1, int(getattr(self, "table_visible_rows", 4) or 1))
        self.table_visible_cols = max(1, int(getattr(self, "table_visible_cols", 5) or 1))
        self.table_input_cols = max(1, int(getattr(self, "table_input_cols", self.input_cols) or 1))

    def _sync_table_view(self):
        self._ensure_table_grid()
        row_count = len(getattr(self, "table_keys", []) or [])
        col_count = self._table_col_count()
        if row_count <= 0 or col_count <= 0:
            self.table_cursor_row = 0
            self.table_cursor_col = 0
            self.table_row_offset = 0
            self.table_col_offset = 0
            self.input_cursor = 0
            self.input_display_position = 0
            return

        self.table_cursor_row = min(max(0, int(getattr(self, "table_cursor_row", 0) or 0)), row_count - 1)
        self.table_cursor_col = min(max(0, int(getattr(self, "table_cursor_col", 0) or 0)), col_count - 1)
        visible_rows = min(max(1, int(getattr(self, "table_visible_rows", 4) or 1)), row_count)
        visible_cols = min(max(1, int(getattr(self, "table_visible_cols", 5) or 1)), col_count)
        self.table_visible_rows = visible_rows
        self.table_visible_cols = visible_cols

        max_row_offset = max(0, row_count - visible_rows)
        max_col_offset = max(0, col_count - visible_cols)
        self.table_row_offset = min(max(0, int(getattr(self, "table_row_offset", 0) or 0)), max_row_offset)
        self.table_col_offset = min(max(0, int(getattr(self, "table_col_offset", 0) or 0)), max_col_offset)

        if self.table_cursor_row < self.table_row_offset:
            self.table_row_offset = self.table_cursor_row
        elif self.table_cursor_row >= self.table_row_offset + visible_rows:
            self.table_row_offset = self.table_cursor_row - visible_rows + 1

        if self.table_cursor_col < self.table_col_offset:
            self.table_col_offset = self.table_cursor_col
        elif self.table_cursor_col >= self.table_col_offset + visible_cols:
            self.table_col_offset = self.table_cursor_col - visible_cols + 1

        self._sync_input_view(prefer_end=True)

    def _move_table_cursor(self, row_step=0, col_step=0):
        self._ensure_table_grid()
        row_count = len(getattr(self, "table_keys", []) or [])
        col_count = self._table_col_count()
        if row_count <= 0 or col_count <= 0:
            return

        self.table_cursor_row = (self.table_cursor_row + int(row_step or 0)) % row_count
        self.table_cursor_col = (self.table_cursor_col + int(col_step or 0)) % col_count
        self._sync_table_view()
        self.refresh_rows = (0, 0)

    def _is_input_row(self, index):
        if index < 0 or index >= len(self.form_list):
            return False
        return "inp_" in str(self.form_list[index])

    def _input_indices(self):
        return [index for index, item in enumerate(self.form_list) if "inp_" in str(item)]

    def _selectable_indices(self):
        indices = []
        index = 0
        while index < len(self.form_list):
            if (
                index + 1 < len(self.form_list)
                and not self._is_input_row(index)
                and self._is_input_row(index + 1)
            ):
                indices.append(index + 1)
                index += 2
                continue
            indices.append(index)
            index += 1
        return indices

    def _normalized_selectable_cursor(self, indices):
        if not indices:
            return 0
        if self.menu_cursor in indices:
            return self.menu_cursor
        if (
            self.menu_cursor + 1 in indices
            and self.menu_cursor + 1 < len(self.form_list)
            and self._is_input_row(self.menu_cursor + 1)
        ):
            return self.menu_cursor + 1

        for index in indices:
            if index >= self.menu_cursor:
                return index
        return indices[0]

    def active_input_key(self):
        if self._use_table_layout():
            self._ensure_table_grid()
            return self._table_cell_key(
                int(getattr(self, "table_cursor_row", 0) or 0),
                int(getattr(self, "table_cursor_col", 0) or 0),
            )
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

        visible_cols = self._active_input_cols()
        max_display = max(0, len(current_value) - visible_cols)
        self.input_display_position = min(
            max(0, self.input_display_position),
            max_display,
        )

        if self.input_cursor < self.input_display_position:
            self.input_display_position = self.input_cursor
        elif self.input_cursor >= self.input_display_position + visible_cols:
            self.input_display_position = self.input_cursor - visible_cols + 1

    def _edit_active_input(self, active_key, inp):
        if active_key is None:
            return

        inp = normalize_pi_token(inp)

        visible_cols = self._active_input_cols()
        current_value = str(self.input_list.get(active_key, " ") or " ")
        if current_value == "":
            current_value = " "
            self.input_list[active_key] = current_value

        if inp == "nav_r":
            self.input_cursor += 1

            if self.input_cursor == len(self.input_list[active_key]):
                self.input_cursor = 0
                self.input_display_position = 0
            elif self.input_cursor == self.input_display_position + visible_cols:
                self.input_display_position += 1

        elif inp == "nav_l" or inp == "nav_b":
            self.input_cursor -= 1

            if self.input_cursor < 0:
                self.input_cursor = len(self.input_list[active_key]) - 1
                self.input_display_position = len(self.input_list[active_key]) - visible_cols
                if self.input_display_position < 0:
                    self.input_display_position = 0

            elif self.input_cursor < self.input_display_position:
                self.input_display_position -= 1

            if inp == "nav_b" and self.input_cursor != len(self.input_list[active_key]) - 1:
                current_value = self.input_list[active_key]
                self.input_list[active_key] = (
                    current_value[: self.input_cursor] + current_value[self.input_cursor + 1 :]
                )
                if (
                    len(self.input_list[active_key]) > visible_cols
                    and len(self.input_list[active_key][self.input_display_position :]) < visible_cols
                ):
                    self.input_display_position = len(self.input_list[active_key]) - visible_cols
                elif len(self.input_list[active_key]) <= visible_cols:
                    self.input_display_position = 0
        elif inp == "AC":
            self.input_list[active_key] = " "
            self.input_cursor = 0
            self.input_display_position = 0

        else:
            if len(inp) > 1:
                for chr in inp:
                    current_value = self.input_list[active_key]
                    self.input_list[active_key] = (
                        current_value[: self.input_cursor] + chr + current_value[self.input_cursor :]
                    )
                    self.input_cursor += len(chr)

                    if self.input_cursor == self.input_display_position + visible_cols:
                        self.input_display_position += 1
            else:
                current_value = self.input_list[active_key]
                self.input_list[active_key] = (
                    current_value[: self.input_cursor] + inp + current_value[self.input_cursor :]
                )
                self.input_cursor += len(inp)

                if self.input_cursor == self.input_display_position + visible_cols:
                    self.input_display_position += 1

        self.input_list[active_key] = self.input_list[active_key].rstrip() + " "
        self._sync_input_view()

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

    def _move_block_cursor(self, step):
        indices = self._selectable_indices()
        if not indices:
            self.menu_cursor = 0
            self.menu_display_position = 0
            self.refresh_rows = (0, self.actual_rows)
            return

        current = self._normalized_selectable_cursor(indices)
        if current in indices:
            current_pos = indices.index(current)
        else:
            current_pos = 0
        self.menu_cursor = indices[(current_pos + step) % len(indices)]
        self.menu_display_position = 0
        self.refresh_rows = (0, self.actual_rows)
        self._sync_input_view(prefer_end=self._is_input_row(self.menu_cursor))

    def update_buffer(self, inp):
        if self._use_table_layout():
            if inp == "nav_d":
                self._move_table_cursor(row_step=1)
            elif inp == "nav_u":
                self._move_table_cursor(row_step=-1)
            elif inp == "nav_r":
                self._move_table_cursor(col_step=1)
            elif inp == "nav_l":
                self._move_table_cursor(col_step=-1)
            else:
                self._edit_active_input(self.active_input_key(), inp)
                self.refresh_rows = (0, 0)
            return

        if inp == "nav_d":
            if self.focus_inputs_only:
                self._focus_input(1)
                self.display_buffer = self.form_list[
                    self.menu_display_position : self.menu_display_position + self.menu_display_size
                ]
                self.display_cursor = self.menu_cursor - self.menu_display_position
                return
            if self._use_block_navigation():
                self._move_block_cursor(1)
            else:
                self.menu_cursor += 1

                if self.menu_cursor == len(self.form_list):
                    self.menu_cursor = 0
                    self.menu_display_position = 0
                    self.refresh_rows = (0, self.actual_rows)
                elif self.menu_cursor - self.menu_display_position == self.actual_rows:
                    self.menu_display_position += 1
                    self.refresh_rows = (0, self.actual_rows)
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
                    self.menu_display_position : self.menu_display_position + self.menu_display_size
                ]
                self.display_cursor = self.menu_cursor - self.menu_display_position
                return
            if self._use_block_navigation():
                self._move_block_cursor(-1)
            else:
                self.menu_cursor -= 1

                if self.menu_cursor < 0:
                    self.menu_cursor = len(self.form_list) - 1
                    self.menu_display_position = len(self.form_list) - self.actual_rows
                    self.refresh_rows = (0, self.actual_rows)
                elif self.menu_cursor < self.menu_display_position:
                    self.menu_display_position -= 1
                    self.refresh_rows = (0, self.actual_rows)
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
                self._edit_active_input(self.form_list[self.menu_cursor], inp)

        self.display_buffer = self.form_list[
            self.menu_display_position : self.menu_display_position + self.menu_display_size
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
        return self._active_input_cols()

    def update(self):
        if self._use_table_layout():
            self._ensure_table_grid()
            self.actual_rows = min(
                max(1, int(getattr(self, "table_visible_rows", 4) or 1)),
                max(1, len(getattr(self, "table_keys", []) or []) or 1),
            )
            self.refresh_rows = (0, 0)
            self.menu_display_size = 0
            self.menu_display_position = 0
            self.display_buffer = []
            self.menu_cursor = 0
            self.display_cursor = 0
            self._sync_table_view()
            return

        self.actual_rows = self.rows if len(self.form_list) >= self.rows else len(self.form_list)
        self.refresh_rows = (0, self.actual_rows)
        self.menu_display_size = self.actual_rows
        self.menu_display_position = 0
        self.display_buffer = self.form_list[
            self.menu_display_position : self.menu_display_position + self.menu_display_size
        ]
        self.menu_cursor = 0
        if self.focus_inputs_only:
            input_indices = self._input_indices()
            if input_indices:
                self.menu_cursor = input_indices[0]
        elif self._use_block_navigation():
            selectable = self._selectable_indices()
            if selectable:
                self.menu_cursor = selectable[0]
        self.display_cursor = self.menu_cursor - self.menu_display_position
        self._sync_input_view(prefer_end=self.focus_inputs_only or self._is_input_row(self.menu_cursor))

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
