# from data_modules.object_handler import test_deep_sleep_awake
from sleeping_features import test_deep_sleep_awake, swdt
import time


class Typer:
    def __init__(self, keypad, keypad_map):
        self.keypad = keypad
        self.keypad_map = keypad_map
        self.debounce_delay_time = 0.2
        self.min_debounce_delay_time = 0.12

    def start_typing(self):
        time.sleep(self.debounce_delay_time)
        try:
            key_inp = self.keypad.keypad_loop()
            col = int(key_inp[0])
            row = int(key_inp[1])
            text = self.keypad_map.key_out(col=col, row=row)
            swdt.feed()
            if text == "off":
                test_deep_sleep_awake()
            return text
        except Exception:
            swdt.stop()
            print("soft watchdog timer stopped")

    def debounce_delay(self, t=None):
        if t is None:
            return self.debounce_delay_time
        if isinstance(t, (int, float)) and t >= self.min_debounce_delay_time:
            self.debounce_delay_time = t
        return self.debounce_delay_time
