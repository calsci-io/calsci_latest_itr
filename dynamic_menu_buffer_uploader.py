import time

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from data_modules.object_handler import menu, menu_refresh, nav
from dynamic_stuff.dynamic_data import menu_items_data
from dynamic_stuff.dynamic_switches import new_upload


def refresh():
    for index in sorted(menu_items_data.keys()):
        if 0 <= index < len(menu.menu_list):
            menu.menu_list[index] = str(menu_items_data[index])
    menu_items_data.clear()
    menu_refresh.refresh(state=nav.current_state())


def uploader():
    while new_upload[0] is True:
        refresh()
        time.sleep(0.1)
