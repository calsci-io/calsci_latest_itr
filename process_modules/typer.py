# from data_modules.object_handler import test_deep_sleep_awake
from sleeping_features import test_deep_sleep_awake, swdt
import time
class Typer:
    def __init__(self, keypad, keypad_map):
        self.keypad=keypad
        self.keypad_map=keypad_map
        self.debounce_delay_time=0.15
        self.min_debounce_delay_time=0.1
    def start_typing(self):
        time.sleep(self.debounce_delay_time)
        try:
            key_inp=self.keypad.keypad_loop()
            text=self.keypad_map.key_out(col=int(key_inp[0]), row=int(key_inp[1]))
            swdt.feed()
            if text == "off" or text == "on":
                # time.sleep(0.2)
                # display.clear_display()
                # display.off()
                test_deep_sleep_awake()
            return text
        except KeyboardInterrupt:
            swdt.stop()
            print("soft watchdog timer stopped")
            raise  # Let REPL get it!
        # except Exception as e:
        #     swdt.stop()
        #     print("soft watchdog timer stopped", e)
        #     return 0
    def debounce_delay(self,t=None):
        if t==None:
            return self.debounce_delay_time
        elif type(t) == int or type(t) == float:
            if t >= self.min_debounce_delay_time:
                self.debounce_delay_time=t
                return self.debounce_delay_time



