import st7565 as _st7565

# try:
#     import tools
#     if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
#         display.graphics = tools.refresh(display.graphics, pixels_changed=8)
# except Exception:
#     pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import machine
import builtins
from data_modules.hardware_config import (
    APP_THREAD_ENABLED,
    DISPLAY_ENABLED,
    KEYPAD_COLS,
    KEYPAD_ENABLED,
    KEYPAD_ROWS,
    LOCAL_UI_ENABLED,
    st7565_display_pins,
)
from process_modules.text_buffer import Textbuffer
from process_modules.text_buffer_uploader import Tbf as text_tbf

from process_modules.menu_buffer import Menu
from process_modules.menu_buffer_uploader import Tbf as menu_tbf

from process_modules.form_buffer import Form
from process_modules.form_buffer_uploader import Tbf as form_tbf

from process_modules.typer import Typer
from input_modules.keypad import Keypad
from data_modules.keypad_map import Keypad_5X8

# from output_modules.st7565_spi import Display
# import st7565 as display
from data_modules.characters import Characters

from process_modules.navbar import Nav

from process_modules.app import App

from process_modules.app_downloader import Apps

# import esp32
# import time
import network
# import espnow
sta_if=network.WLAN(network.STA_IF)
ap_if=network.WLAN(network.AP_IF)
sta_if.active(True)
ap_if.active(True)
sta_if.config(hostname="CalSci")
ap_if.config(ssid="CalSci")
sta_if.active(False)
ap_if.active(False)
# e = espnow.ESPNow()
current_app=["home", ""]
data_bucket={"ssid_g" : "", "connection_status_g" : False}
keypad_rows=list(KEYPAD_ROWS)
keypad_cols=list(KEYPAD_COLS)
# display.init(st7565_display_pins["cs1"], st7565_display_pins["rs"], st7565_display_pins["rst"], st7565_display_pins["sda"], st7565_display_pins["sck"])
# display.init(9, 11, 10, 13, 12)
class _NullDisplay:
    WIDTH = getattr(_st7565, "WIDTH", 128)
    HEIGHT = getattr(_st7565, "HEIGHT", 64)
    PAGES = getattr(_st7565, "PAGES", 8)

    def init(self, *args, **kwargs):
        return False

    def deinit(self, *args, **kwargs):
        return None

    def clear_display(self, *args, **kwargs):
        return None

    def set_page_address(self, *args, **kwargs):
        return None

    def set_column_address(self, *args, **kwargs):
        return None

    def write_data(self, *args, **kwargs):
        return None

    def write_instruction(self, *args, **kwargs):
        return None

    def graphics(self, *args, **kwargs):
        return None

    def on(self, *args, **kwargs):
        return None

    def off(self, *args, **kwargs):
        return None

    def invert(self, *args, **kwargs):
        return None

    def all_points_on(self, *args, **kwargs):
        return None


class _NullKeypad:
    def __init__(self, rows=(), cols=()):
        self.rows = list(rows)
        self.cols = list(cols)
        self.keypad_loop = self._disabled_loop

    def _disabled_loop(self):
        raise RuntimeError("Keypad disabled")

    def keypad_start(self):
        return None

    def keypad_stop(self):
        return None


display = _st7565 if DISPLAY_ENABLED else _NullDisplay()
# display.write_instruction(0x81) #for only 3.0
# display.write_instruction(9)
# import display
keymap = Keypad_5X8()
keyin = Keypad(rows=keypad_rows, cols=keypad_cols) if KEYPAD_ENABLED else _NullKeypad(rows=keypad_rows, cols=keypad_cols)
typer = Typer(keypad=keyin, keypad_map=keymap)

chrs=Characters()
builtins.chrs=chrs

text=Textbuffer()
menu=Menu()
form=Form()
builtins.text=text
builtins.menu=menu
builtins.form=form

builtins.typer=typer

nav = Nav(disp_out=display, chrs=chrs)
builtins.nav=nav

text_refresh=text_tbf(disp_out=display, chrs=chrs, t_b=text)
menu_refresh=menu_tbf(disp_out=display, chrs=chrs, m_b=menu)
form_refresh=form_tbf(disp_out=display, chrs=chrs, f_b=form)
builtins.text_refresh=text_refresh
builtins.menu_refresh=menu_refresh
builtins.form_refresh=form_refresh

app=App()
builtins.app=App()

mac_str = ''.join('{:02X}'.format(b) for b in machine.unique_id())
builtins.mac_str=mac_str

apps_installer=Apps()
builtins.apps_installer=apps_installer
builtins.hardware_local_ui_enabled = LOCAL_UI_ENABLED
builtins.hardware_app_thread_enabled = APP_THREAD_ENABLED

def keypad_state_manager(x):
    if keymap.state == "a" and x[0] == "a":
        keymap.key_change(state="d")
        nav.state_change(state="d")
    elif keymap.state == "b" and x[0] == "b":
        keymap.key_change(state="d")
        nav.state_change(state="d")
    elif keymap.state == "A" and x[0] == "A":
        keymap.key_change(state="d")
        nav.state_change(state="d")
    else:
        keymap.key_change(state=x[0])
        nav.state_change(state=x[0])

def keypad_state_manager_reset():
    keymap.key_change(state="d")
    nav.state_change(state="d")


# def test_deep_sleep_awake():
#     # -------- Hold GPIO32 HIGH --------
#     hold_pin = machine.Pin(32, machine.Pin.OUT)
#     hold_pin.value(1)  # Keep high

#     # -------- Configure Wakeup Pin (GPIO33) --------
#     wakeup_pin = machine.Pin(33, mode=machine.Pin.IN)

#     # Enable wakeup on high level (1)
#     esp32.wake_on_ext0(pin=wakeup_pin, level=esp32.WAKEUP_ANY_HIGH)

#     print("Going to deep sleep now...")
#     time.sleep(1)  # Give time for message to print
#     machine.deepsleep()
