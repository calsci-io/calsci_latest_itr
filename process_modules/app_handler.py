# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import gc
from data_modules.object_handler import keypad_state_manager_reset
from process_modules.app_runner import app_runner

def app_handler():
    while True:
        keypad_state_manager_reset()

        app_runner()
        gc.collect()
        print(gc.mem_free(), gc.mem_alloc())
