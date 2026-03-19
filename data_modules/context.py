import machine
import network

from data_modules.characters import Characters
from data_modules.keypad_map import Keypad_5X8
from input_modules.keypad import Keypad
from process_modules.app import App
from process_modules.app_downloader import Apps
from process_modules.form_buffer import Form
from process_modules.form_buffer_uploader import Tbf as form_tbf
from process_modules.menu_buffer import Menu
from process_modules.menu_buffer_uploader import Tbf as menu_tbf
from process_modules.navbar import Nav
from process_modules.text_buffer import Textbuffer
from process_modules.text_buffer_uploader import Tbf as text_tbf
from process_modules.typer import Typer


class RuntimeContext:
    def __init__(self, display_module):
        self.display = display_module
        self.data_bucket = {"ssid_g": "", "connection_status_g": False}
        self.current_app = ["home", "root"]
        self.app_state = {}

        self.keypad_rows = [14, 21, 47, 48, 38, 39, 40, 41, 42, 1]
        self.keypad_cols = [8, 18, 17, 15, 7]
        self.st7565_display_pins = {"cs1": 9, "rs": 10, "rst": 11, "sda": 12, "sck": 13}

        self.keymap = Keypad_5X8()
        self.keypad = Keypad(rows=self.keypad_rows, cols=self.keypad_cols)
        self.typer = Typer(keypad=self.keypad, keypad_map=self.keymap)

        self.chrs = Characters()
        self.text = Textbuffer()
        self.menu = Menu()
        self.form = Form()

        self.nav = Nav(disp_out=self.display, chrs=self.chrs)
        self.text_refresh = text_tbf(disp_out=self.display, chrs=self.chrs, t_b=self.text)
        self.menu_refresh = menu_tbf(disp_out=self.display, chrs=self.chrs, m_b=self.menu)
        self.form_refresh = form_tbf(disp_out=self.display, chrs=self.chrs, f_b=self.form)

        self.app = App(current_app=self.current_app)

        self.sta_if = network.WLAN(network.STA_IF)
        self.ap_if = network.WLAN(network.AP_IF)
        self._init_network()

        self.mac_str = "".join("{:02X}".format(b) for b in machine.unique_id())
        self.apps_installer = Apps()

    def _init_network(self):
        self.sta_if.active(True)
        self.ap_if.active(True)
        self.sta_if.config(hostname="CalSci")
        self.ap_if.config(ssid="CalSci")
        self.sta_if.active(False)
        self.ap_if.active(False)
