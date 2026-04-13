import threading
import time
import unittest

from _helpers import fake_device_modules


class BlockingKeypad:
    def __init__(self, rows=None, cols=None):
        self.rows = rows or []
        self.cols = cols or []
        self.queue = []
        self.ready = threading.Event()

    def keypad_loop(self):
        self.ready.set()
        while not self.queue:
            time.sleep(0.01)
        return self.queue.pop(0)


class MatrixMachine:
    pressed_key = None
    row_values = {}
    row_pins = ()
    col_pins = ()

    class Pin:
        OUT = 1
        IN = 0
        PULL_UP = 1

        def __init__(self, pin, mode=None, pull=None):
            self.pin = pin
            self.mode = mode
            self.pull = pull
            if mode == self.OUT:
                MatrixMachine.row_values[pin] = 1

        def value(self, new=None):
            if new is not None:
                MatrixMachine.row_values[self.pin] = int(new)
                return MatrixMachine.row_values[self.pin]
            if self.mode == self.OUT:
                return MatrixMachine.row_values.get(self.pin, 1)
            key = MatrixMachine.pressed_key
            if key is None:
                return 1
            col_index, row_index = key
            active_row_pin = MatrixMachine.row_pins[row_index]
            active_col_pin = MatrixMachine.col_pins[col_index]
            if self.pin == active_col_pin and MatrixMachine.row_values.get(active_row_pin, 1) == 0:
                return 0
            return 1


class InputAdapterTests(unittest.TestCase):
    def test_poll_token_uses_non_blocking_matrix_scan_on_device_path(self):
        with fake_device_modules():
            from adapters.device import input as input_mod

            MatrixMachine.row_values = {}
            MatrixMachine.row_pins = tuple(input_mod.KEYPAD_ROWS)
            MatrixMachine.col_pins = tuple(input_mod.KEYPAD_COLS)
            MatrixMachine.pressed_key = None

            input_mod.machine = MatrixMachine
            input_mod.NativeKeypad = None
            input_mod.KEYPAD_ENABLED = True

            adapter = input_mod.DeviceInputAdapter()

            started = time.time()
            self.assertIsNone(adapter.poll_token("d"))
            self.assertLess(time.time() - started, 0.2)

            MatrixMachine.pressed_key = (3, 2)
            self.assertEqual(adapter.poll_token("d"), "ok")
            self.assertIsNone(adapter.poll_token("d"))

            MatrixMachine.pressed_key = None
            self.assertIsNone(adapter.poll_token("d"))

    def test_poll_token_stays_non_blocking_with_native_keypad_fallback(self):
        with fake_device_modules():
            from adapters.device import input as input_mod

            input_mod.machine = None
            input_mod.NativeKeypad = BlockingKeypad
            input_mod.KEYPAD_ENABLED = True

            adapter = input_mod.DeviceInputAdapter()
            keypad = adapter._keypad

            self.assertTrue(keypad.ready.wait(0.5))

            started = time.time()
            self.assertIsNone(adapter.poll_token("d"))
            self.assertLess(time.time() - started, 0.2)

            keypad.queue.append((3, 2))

            token = None
            deadline = time.time() + 0.5
            while time.time() < deadline and token is None:
                token = adapter.poll_token("d")
                if token is None:
                    time.sleep(0.01)

            self.assertEqual(token, "ok")


if __name__ == "__main__":
    unittest.main()
