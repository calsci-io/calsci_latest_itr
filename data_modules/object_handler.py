import st7565 as display

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
from process_modules.text_buffer import Textbuffer
from process_modules.text_buffer_uploader import Tbf as text_tbf

from process_modules.menu_buffer import Menu
from process_modules.menu_buffer_uploader import Tbf as menu_tbf

from process_modules.form_buffer import Form
from process_modules.form_buffer_uploader import Tbf as form_tbf

from process_modules.typer import Typer
from input_modules.keypad import Keypad
from data_modules.keypad_map import Keypad_5X8
from process_modules.keypad_modes import handle_mode_key, reset_mode

# from output_modules.st7565_spi import Display
# import st7565 as display
from data_modules.characters import Characters

from process_modules.navbar import Nav

from process_modules.app import App

# import esp32
# import time
import network
# import espnow


def _configure_wlan(iface, iface_type):
    try:
        if iface_type == network.STA_IF:
            iface.config(hostname="CalSci")
        elif iface_type == network.AP_IF:
            iface.config(ssid="CalSci")
    except Exception:
        pass


class LazyWLAN:
    def __init__(self, iface_type):
        self._iface_type = iface_type
        self._iface = None

    def _get(self):
        if self._iface is None:
            iface = network.WLAN(self._iface_type)
            _configure_wlan(iface, self._iface_type)
            self._iface = iface
        return self._iface

    def __getattr__(self, name):
        return getattr(self._get(), name)


class LazyAppsInstaller:
    def __init__(self):
        self._apps = None

    def _get(self):
        if self._apps is None:
            from process_modules.app_downloader import Apps

            self._apps = Apps()
        return self._apps

    def __getattr__(self, name):
        return getattr(self._get(), name)


sta_if = LazyWLAN(network.STA_IF)
ap_if = LazyWLAN(network.AP_IF)
# e = espnow.ESPNow()
current_app=["home", ""]
data_bucket={"ssid_g" : "", "connection_status_g" : False}
# keypad_rows=[26, 25, 33, 32, 35, 34, 39, 36] #3.0
# keypad_cols=[15, 13, 12, 14, 27] #3.0
keypad_rows=[14, 21, 47, 48, 38, 39, 40, 41, 42, 1] #2.9
keypad_cols=[8, 18, 17, 15, 7] #2.9                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
# st7565_display_pins={"cs1":2, "rs":16, "rst":4, "sda":5, "sck":17}  #3.0
st7565_display_pins={"cs1":9, "rs":10, "rst":11, "sda":12, "sck":13} #2.9
# display.init(st7565_display_pins["cs1"], st7565_display_pins["rs"], st7565_display_pins["rst"], st7565_display_pins["sda"], st7565_display_pins["sck"])
# display.init(9, 11, 10, 13, 12)
display=display
# display.write_instruction(0x81) #for only 3.0
# display.write_instruction(9)
# import display
keymap = Keypad_5X8()
keyin = Keypad(rows=keypad_rows, cols=keypad_cols)

chrs=Characters()
builtins.chrs=chrs

nav = Nav(disp_out=display, chrs=chrs)
builtins.nav=nav

typer = Typer(keypad=keyin, keypad_map=keymap, nav=nav)

text=Textbuffer()
menu=Menu()
form=Form()
builtins.text=text
builtins.menu=menu
builtins.form=form

builtins.typer=typer

text_refresh=text_tbf(disp_out=display, chrs=chrs, t_b=text, nav=nav)
menu_refresh=menu_tbf(disp_out=display, chrs=chrs, m_b=menu, nav=nav)
form_refresh=form_tbf(disp_out=display, chrs=chrs, f_b=form, nav=nav)
builtins.text_refresh=text_refresh
builtins.menu_refresh=menu_refresh
builtins.form_refresh=form_refresh

app=App()
builtins.app=app

mac_str = ''.join('{:02X}'.format(b) for b in machine.unique_id())
builtins.mac_str=mac_str

apps_installer=LazyAppsInstaller()
builtins.apps_installer=apps_installer

def keypad_state_manager(x):
    handle_mode_key(keymap=keymap, nav=nav, key_name=x)

def keypad_state_manager_reset():
    reset_mode(keymap=keymap, nav=nav)


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
