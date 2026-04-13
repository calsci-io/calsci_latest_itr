import contextlib
import os
import sys
import types


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(ROOT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _purge(prefixes):
    for name in list(sys.modules):
        for prefix in prefixes:
            if name == prefix or name.startswith(prefix + "."):
                sys.modules.pop(name, None)
                break


@contextlib.contextmanager
def fake_device_modules():
    saved = {}
    module_names = ("st7565", "calsci_keypad", "network", "machine", "ntptime")
    for name in module_names:
        if name in sys.modules:
            saved[name] = sys.modules[name]

    _purge(("core.bootstrap", "adapters.device"))

    st7565 = types.ModuleType("st7565")
    st7565._buffer = []
    st7565._graphics = None
    st7565._inverted = False
    st7565._contrast = None
    st7565._init_args = None
    st7565._init_kwargs = None

    def _noop(*args, **kwargs):
        return None

    def _init(*args, **kwargs):
        st7565._init_args = args
        st7565._init_kwargs = kwargs
        return None

    def _graphics_writer(buf, **kwargs):
        st7565._graphics = bytes(buf)

    st7565.init = _init
    st7565.clear_display = _noop
    st7565.set_page_address = _noop
    st7565.set_column_address = _noop
    st7565.write_data = lambda value: st7565._buffer.append(value)
    st7565.graphics = _graphics_writer
    st7565.invert = lambda enabled: setattr(st7565, "_inverted", bool(enabled))
    st7565.set_contrast = lambda value: setattr(st7565, "_contrast", int(value))

    keypad_mod = types.ModuleType("calsci_keypad")

    class Keypad:
        def __init__(self, rows=None, cols=None):
            self.rows = rows or []
            self.cols = cols or []

        def keypad_loop(self):
            return None

    keypad_mod.Keypad = Keypad

    network_mod = types.ModuleType("network")
    network_mod.STA_IF = 0

    class WLAN:
        def __init__(self, iface):
            self.iface = iface
            self._active = False
            self._connected = False
            self._ssid = ""

        def active(self, value=None):
            if value is None:
                return self._active
            self._active = bool(value)
            return self._active

        def scan(self):
            return [(b"TestWiFi",), (b"Guest",)]

        def connect(self, ssid, password):
            self._ssid = ssid
            self._connected = bool(ssid)

        def disconnect(self):
            self._connected = False
            self._ssid = ""

        def isconnected(self):
            return self._connected

        def ifconfig(self):
            return ("192.168.1.10", "255.255.255.0", "192.168.1.1", "8.8.8.8")

        def config(self, key=None):
            if key == "essid":
                return self._ssid
            return None

    network_mod.WLAN = WLAN

    machine_mod = types.ModuleType("machine")

    class Pin:
        OUT = 1
        IN = 0
        PULL_UP = 1
        PULL_DOWN = 0

        def __init__(self, pin, mode=None, pull=None):
            self.pin = pin
            self.mode = mode
            self.pull = pull
            self._value = 0

        def value(self, new=None):
            if new is None:
                return self._value
            self._value = new
            return self._value

    class PWM:
        def __init__(self, pin):
            self.pin = pin
            self._freq = 0
            self._duty = 0

        def freq(self, value):
            self._freq = value

        def duty(self, value):
            self._duty = value

    class ADC:
        ATTN_11DB = 0
        WIDTH_12BIT = 0

        def __init__(self, pin):
            self.pin = pin

        def atten(self, value):
            return value

        def width(self, value):
            return value

        def read(self):
            return 3200

    machine_mod.Pin = Pin
    machine_mod.PWM = PWM
    machine_mod.ADC = ADC
    machine_mod.deepsleep = _noop
    machine_mod.reset = _noop
    machine_mod.unique_id = lambda: b"\xAA\xBB\xCC\xDD"

    ntptime_mod = types.ModuleType("ntptime")
    ntptime_mod.settime = _noop

    sys.modules["st7565"] = st7565
    sys.modules["calsci_keypad"] = keypad_mod
    sys.modules["network"] = network_mod
    sys.modules["machine"] = machine_mod
    sys.modules["ntptime"] = ntptime_mod

    try:
        yield
    finally:
        _purge(("core.bootstrap", "adapters.device"))
        for name in module_names:
            sys.modules.pop(name, None)
        for name, module in saved.items():
            sys.modules[name] = module
