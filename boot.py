import gc
import esp32
from sleeping_features import keypad_normal
keypad_normal()
import machine
opin = machine.Pin(14, machine.Pin.OUT, value=1, hold=False)  # Reinitialize the pin for deepsleep keypad
# from test_thread import run_thread
# opin.hold(False)
# from data_modules.object_handler import display
import st7565 as display
st7565_display_pins={"cs1":9, "rs":11, "rst":10, "sda":13, "sck":12} #2.9
# display.init(st7565_display_pins["cs1"], st7565_display_pins["rs"], st7565_display_pins["rst"], st7565_display_pins["sda"], st7565_display_pins["sck"])
# display.init(st7565_display_pins["cs1"], st7565_display_pins["rs"], st7565_display_pins["rst"], st7565_display_pins["sda"], st7565_display_pins["sck"]) #2.9
display.init(9, 11, 10, 13, 12)
cal_sci_buffer=bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xe0   \xa0\xa0\xa0\xa0            \xa0\xa0\xa0     \xa0\xa0\xa0\xa0             \xa0\xa0    \xe0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\x00\x00\x1f?  1\x11\x00\x00\x10:**><\x00\x00\x00 ?? \x00\x00\x00\x137$$=\x19\x00\x00\x1c>""6\x14\x00\x00\x00\x00>>\x00\x00\x00\x00\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\xc1\x01\x01\xc1\xc1\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01A\xc1\xc1\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xc1\xc1\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0f\x1f\x10\x10\x1f\x0f\x00\x00\x1f\x1f\x01\x01\x1f\x1e\x00\x00\x00\x10\x1f\x1f\x10\x00\x00\x00\x0e\x1f\x15\x15\x17\x16\x00\x00\x08\x1d\x15\x15\x1f\x1e\x00\x00\x12\x17\x15\x15\x1d\x08\x00\x00\x1f\x1f\x01\x01\x1f\x1e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x07\x0fxx\x0f\x07\x00\x008|DD|8\x00\x00<|@@|<\x00\x00||\x04\x04\x0c\x08\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00A\x7f\x7fA\x00\x00\x00||\x180\x18||\x00 tTT|x\x00\x00\x98\xbc\xa4\xa4\xfc|\x00\x00\x00\x00}}\x00\x00\x00\x00||\x04\x04|x\x00\x00 tTT|x\x00\x04\x04?\x7fDd \x00\x00\x00\x00}}\x00\x00\x00\x008|DD|8\x00\x00||\x04\x04|x\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
display.graphics(cal_sci_buffer)
# display.write_instruction(0x81) #for only 3.0
# display.write_instruction(0x06)
gc.enable()
print("free ram initially=", gc.mem_free())
print("ram allocated initially=", gc.mem_alloc())

# --- Triple Boot System ---
print("=================================")
print("  CalSci - Triple Boot System")
print("=================================")
print("  boot.switch_to_cpp()   - Reboot into C++")
print("  boot.switch_to_rust()  - Reboot into Rust")
print("  boot.boot_info()       - Show current partition")
print("=================================")


def boot_info():
    """Show current running partition info."""
    cur = esp32.Partition(esp32.Partition.RUNNING)
    print("Running from:", cur.info())
    print()
    print("All app partitions:")
    for p in esp32.Partition.find(esp32.Partition.TYPE_APP):
        print(" ", p.info())


def switch_to_cpp():
    """Switch to C++ (ota_1) and reboot."""
    _switch_to("ota_1", "C++")


def switch_to_rust():
    """Switch to Rust (ota_2) and reboot."""
    _switch_to("ota_2", "Rust")


def switch_to_micropython():
    """Switch back to MicroPython (ota_0) and reboot."""
    _switch_to("ota_0", "MicroPython")


def _decode_partition_field(value):
    if isinstance(value, bytes):
        try:
            return value.decode()
        except Exception:
            return None
    if isinstance(value, str):
        return value
    return None


def _partition_by_label(label):
    # Fast path for firmwares where Partition(label) is supported.
    try:
        return esp32.Partition(label)
    except Exception:
        pass

    # Fallback: scan app partitions and match label from info().
    try:
        parts = esp32.Partition.find(esp32.Partition.TYPE_APP)
    except Exception:
        return None

    for part in parts:
        try:
            info = part.info()
        except Exception:
            continue

        fields = info if isinstance(info, (tuple, list)) else (info,)
        for field in fields:
            if _decode_partition_field(field) == label:
                return part
    return None


def _switch_to(label, name):
    """Set boot partition and restart."""
    import time as _time
    try:
        part = _partition_by_label(label)
        if part is None:
            print("Error switching to", label, ": partition not found")
            return
        part.set_boot()
        print("Next boot:", name, "(" + label + ")")
        display.clear_display()
        menu.menu_list = ["Switching to:", name, "Rebooting..."]
        menu.update()
        menu_refresh.refresh()
        print("Restarting in 1 second...")
        _time.sleep(1)
        machine.reset()
    except Exception as e:
        print("Error switching to", label, ":", e)
# --- End Triple Boot System ---
from apps.settings.backlight import backlight_pin
# backlight_pin.off() #3.0
backlight_pin.on() #2.9
# from test_thread import run_thread
# run_thread()
# import uasyncio as asyncio
# from test_async import main
# asyncio.run(main())
import builtins
import sys as _boot_sys

_hyb_graphics_hook = None
_hyb_set_page_hook = None
_hyb_set_col_hook = None
_hyb_write_data_hook = None
_hyb_clear_hook = None


class _HybridDisplayProxy:
    def __init__(self, real_mod):
        self._real_mod = real_mod
        self.__name__ = "st7565"

    def __setattr__(self, name, value):
        if name in ("_real_mod", "__name__"):
            object.__setattr__(self, name, value)
            return

        # Keep bridge interception active even if app code tries to monkey-patch.
        if name in (
            "graphics",
            "set_page_address",
            "set_column_address",
            "write_data",
            "clear_display",
        ):
            return

        try:
            setattr(self._real_mod, name, value)
        except Exception:
            object.__setattr__(self, name, value)

    def __getattr__(self, name):
        return getattr(self._real_mod, name)

    def init(self, *args, **kwargs):
        return self._real_mod.init(*args, **kwargs)

    def set_page_address(self, page):
        hook = _hyb_set_page_hook
        if hook is not None:
            try:
                hook(page)
            except Exception:
                pass
        return self._real_mod.set_page_address(page)

    def set_column_address(self, col):
        hook = _hyb_set_col_hook
        if hook is not None:
            try:
                hook(col)
            except Exception:
                pass
        return self._real_mod.set_column_address(col)

    def write_data(self, value):
        hook = _hyb_write_data_hook
        if hook is not None:
            try:
                hook(value)
            except Exception:
                pass
        return self._real_mod.write_data(value)

    def graphics(self, buf, *args, **kwargs):
        hook = _hyb_graphics_hook
        if hook is not None:
            try:
                hook(buf, args, kwargs)
            except Exception:
                pass
        return self._real_mod.graphics(buf, *args, **kwargs)

    def clear_display(self):
        hook = _hyb_clear_hook
        if hook is not None:
            try:
                hook()
            except Exception:
                pass
        return self._real_mod.clear_display()

try:
    _hyb_display_proxy = _HybridDisplayProxy(display)
    _boot_sys.modules["st7565"] = _hyb_display_proxy
    display = _hyb_display_proxy
except Exception:
    pass

from data_modules.object_handler import text, menu, form, nav, text_refresh, menu_refresh, form_refresh, typer, data_bucket
builtins.display=display
builtins.text=text
builtins.menu=menu
builtins.form=form
builtins.text_refresh=text_refresh
builtins.text_refresh=menu_refresh
builtins.text_refresh=form_refresh
builtins.typer=typer



# WiFi startup disabled for fast boot.
builtins.sta_if = None
data_bucket["connection_status_g"] = False
data_bucket["ssid_g"] = ""

# Hybrid keypad debounce profile:
# - global stable delay for menus/general typing
# - graph app can temporarily switch to fast poll while cursor/tools are inactive
try:
    _HYB_GLOBAL_DEBOUNCE_SEC = 0.035
    typer.debounce_delay_time = _HYB_GLOBAL_DEBOUNCE_SEC
    data_bucket["hyb_global_debounce_sec"] = _HYB_GLOBAL_DEBOUNCE_SEC
except Exception:
    data_bucket["hyb_global_debounce_sec"] = None
data_bucket["hyb_graph_fast_debounce_sec"] = 0.001

# ------------------------------------------------------------
# Hybrid serial bridge (test-only, no firmware rebuild needed)
# Input protocol (text):
#   PING:<msg>      -> ECHO:<msg>
#   KEY:<col>,<row> -> inject key into keypad loop
# Output protocol (binary framed + CRC16):
#   magic(2) + type(1) + flags(1) + len(2) + payload + crc16(2)
# ------------------------------------------------------------
try:
    import sys
    import time as _pytime
    import _thread

    try:
        import uselect as _uselect
    except Exception:
        _uselect = None

    try:
        import ubinascii as _binascii
    except Exception:
        import binascii as _binascii

    try:
        import ujson as _json
    except Exception:
        import json as _json

    try:
        import utime as _utime
    except Exception:
        _utime = None

    _hyb_key_queue = []
    _hyb_fb = bytearray(1024)
    _hyb_prev_fb = bytearray(1024)
    _hyb_cur_page = 0
    _hyb_cur_col = 0
    _hyb_dirty = True
    _hyb_force_full = True
    _hyb_fb_seen = False
    _hyb_last_emit = 0
    _hyb_last_full_emit = 0
    _hyb_frame_seq = 0
    _hyb_last_heartbeat = 0
    _hyb_emit_dirty_ms = 1
    _hyb_emit_ui_ms = 1
    _hyb_idle_emit_ms = 1
    _hyb_heartbeat_ms = 1
    _hyb_full_keyframe_ms = 1
    _hyb_periodic_full_ms = 1
    _hyb_full_only = False
    _hyb_last_nav_sent = ""
    _hyb_last_lines_sent = []
    _hyb_tx_lock = _thread.allocate_lock()

    _HYB_MAGIC0 = 0xCA
    _HYB_MAGIC1 = 0x1C
    _HYB_PKT_FULL = 1
    _HYB_PKT_PATCH = 2
    _HYB_PKT_NAV = 3
    _HYB_PKT_LINES = 4
    _HYB_PKT_HEARTBEAT = 5

    _hyb_out = None
    _hyb_binary_ok = False

    def _hyb_global(name):
        try:
            return globals().get(name, None)
        except Exception:
            return None

    def _hyb_ticks_ms():
        if _utime is not None and hasattr(_utime, "ticks_ms"):
            return _utime.ticks_ms()
        return int(_pytime.time() * 1000)

    def _hyb_ticks_diff(a, b):
        if _utime is not None and hasattr(_utime, "ticks_diff"):
            return _utime.ticks_diff(a, b)
        return a - b

    def _hyb_sleep_ms(ms):
        if _utime is not None and hasattr(_utime, "sleep_ms"):
            _utime.sleep_ms(ms)
        else:
            _pytime.sleep(ms / 1000.0)

    def _hyb_nav_state():
        try:
            nav_obj = _hyb_global("nav")
            if nav_obj is not None and hasattr(nav_obj, "current_state"):
                return str(nav_obj.current_state())
        except Exception:
            pass
        return ""

    def _hyb_clean_line(text):
        try:
            s = str(text)
            s = s.replace("𖤓", "_")
            return s
        except Exception:
            return ""

    def _hyb_menu_lines():
        try:
            menu_obj = _hyb_global("menu")
            if menu_obj is None or not hasattr(menu_obj, "buffer"):
                return []
            buf = menu_obj.buffer()
            if not isinstance(buf, (list, tuple)) or not buf:
                return []
            if all(_hyb_clean_line(x).startswith("label_") for x in buf):
                return []
            cur = -1
            if hasattr(menu_obj, "cursor"):
                try:
                    cur = int(menu_obj.cursor())
                except Exception:
                    cur = -1
            lines = []
            for i, row in enumerate(buf):
                prefix = ">" if i == cur else " "
                lines.append(prefix + _hyb_clean_line(row))
            return lines[:7]
        except Exception:
            return []

    def _hyb_form_lines():
        try:
            form_obj = _hyb_global("form")
            if form_obj is None or not hasattr(form_obj, "buffer"):
                return []
            buf = form_obj.buffer()
            if not isinstance(buf, (list, tuple)) or not buf:
                return []
            if all(_hyb_clean_line(x).startswith("label_") for x in buf):
                return []
            lines = []
            cur = -1
            if hasattr(form_obj, "cursor"):
                try:
                    cur = int(form_obj.cursor())
                except Exception:
                    cur = -1
            inp_list = {}
            if hasattr(form_obj, "inp_list"):
                try:
                    inp_list = form_obj.inp_list() or {}
                except Exception:
                    inp_list = {}
            inp_start = 0
            if hasattr(form_obj, "inp_display_position"):
                try:
                    inp_start = int(form_obj.inp_display_position())
                except Exception:
                    inp_start = 0
            inp_cols = 19
            if hasattr(form_obj, "inp_cols"):
                try:
                    inp_cols = int(form_obj.inp_cols())
                except Exception:
                    inp_cols = 19

            for i, row in enumerate(buf):
                name = _hyb_clean_line(row)
                if name.startswith("inp_"):
                    value = _hyb_clean_line(inp_list.get(name, ""))
                    line = "=>" + value[inp_start : inp_start + inp_cols]
                else:
                    line = name
                prefix = ">" if i == cur and not name.startswith("inp_") else " "
                lines.append(prefix + line)
            return lines[:7]
        except Exception:
            return []

    def _hyb_text_lines():
        try:
            text_obj = _hyb_global("text")
            if text_obj is None or not hasattr(text_obj, "buffer"):
                return []
            buf = text_obj.buffer()
            if not isinstance(buf, (list, tuple)) or not buf:
                return []
            lines = []
            for row in buf:
                lines.append(_hyb_clean_line(row))
            return lines[:7]
        except Exception:
            return []

    def _hyb_lines_snapshot():
        for producer in (_hyb_text_lines, _hyb_form_lines, _hyb_menu_lines):
            lines = producer()
            if lines:
                return lines
        return []

    def _hyb_write_line(text):
        try:
            _hyb_tx_lock.acquire()
            sys.stdout.write(text + "\n")
            sys.stdout.flush()
        except Exception:
            pass
        finally:
            try:
                _hyb_tx_lock.release()
            except Exception:
                pass

    def _hyb_init_output_stream():
        global _hyb_out, _hyb_binary_ok
        _hyb_out = None
        _hyb_binary_ok = False
        # Keep bridge in text/JSON mode for stable compatibility.
        _hyb_out = sys.stdout

    def _hyb_crc16(raw):
        crc = 0xFFFF
        for b in raw:
            if not isinstance(b, int):
                b = ord(b)
            crc ^= (b << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ 0x1021) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc

    def _hyb_write_raw(data):
        global _hyb_binary_ok
        if not _hyb_binary_ok:
            return False
        try:
            _hyb_tx_lock.acquire()
            _hyb_out.write(data)
            return True
        except Exception:
            _hyb_binary_ok = False
            return False
        finally:
            try:
                _hyb_tx_lock.release()
            except Exception:
                pass

    def _hyb_send_packet(pkt_type, flags, payload):
        if payload is None:
            payload = b""
        try:
            plen = len(payload)
        except Exception:
            plen = 0
            payload = b""
        if plen > 2048:
            return False

        frame = bytearray(6 + plen + 2)
        frame[0] = _HYB_MAGIC0
        frame[1] = _HYB_MAGIC1
        frame[2] = pkt_type & 0xFF
        frame[3] = flags & 0xFF
        frame[4] = plen & 0xFF
        frame[5] = (plen >> 8) & 0xFF
        if plen > 0:
            frame[6 : 6 + plen] = payload
        crc = _hyb_crc16(frame[2 : 6 + plen])
        frame[6 + plen] = crc & 0xFF
        frame[7 + plen] = (crc >> 8) & 0xFF
        return _hyb_write_raw(frame)

    def _hyb_send_nav(nav_txt):
        if nav_txt is None:
            nav_txt = ""
        try:
            raw = str(nav_txt).encode("utf-8")
        except Exception:
            raw = b""
        if len(raw) > 120:
            raw = raw[:120]
        _hyb_send_packet(_HYB_PKT_NAV, 0, raw)

    def _hyb_send_lines(lines):
        try:
            rows = list(lines or [])
        except Exception:
            rows = []
        if len(rows) > 7:
            rows = rows[:7]
        payload = bytearray(b"\x00")
        count = 0
        for row in rows:
            try:
                raw = _hyb_clean_line(row).encode("utf-8")
            except Exception:
                raw = b""
            if len(raw) > 31:
                raw = raw[:31]
            if len(payload) + 1 + len(raw) > 250:
                break
            payload.append(len(raw))
            payload.extend(raw)
            count += 1
        payload[0] = count & 0xFF
        _hyb_send_packet(_HYB_PKT_LINES, 0, payload)

    def _hyb_fb_flags(seq):
        flags = (int(seq) & 0x7F) << 1
        if _hyb_fb_seen:
            flags |= 0x01
        return flags

    def _hyb_send_full_frame(seq):
        global _hyb_last_full_emit
        flags = _hyb_fb_flags(seq)
        if not _hyb_send_packet(_HYB_PKT_FULL, flags, bytes(_hyb_fb)):
            return False
        _hyb_prev_fb[:] = _hyb_fb
        _hyb_last_full_emit = _hyb_ticks_ms()
        return True

    def _hyb_build_patches(max_patches=32, max_run=80):
        patches = []
        changed = 0
        for page in range(8):
            base = page * 128
            col = 0
            while col < 128:
                if _hyb_fb[base + col] != _hyb_prev_fb[base + col]:
                    start = col
                    while (
                        col < 128
                        and _hyb_fb[base + col] != _hyb_prev_fb[base + col]
                        and (col - start) < max_run
                    ):
                        col += 1
                        changed += 1
                    width = col - start
                    raw = bytes(_hyb_fb[base + start : base + start + width])
                    patches.append((page, start, width, 1, raw))
                    if len(patches) >= max_patches:
                        return changed + 1, patches
                else:
                    col += 1
        return changed, patches

    def _hyb_emit_state_text(nav_state, lines_state):
        try:
            has_pixels = False
            for _b in _hyb_fb:
                if _b:
                    has_pixels = True
                    break
            if has_pixels:
                raw = _binascii.b2a_base64(_hyb_fb)
                if isinstance(raw, bytes):
                    raw = raw.decode().strip()
            else:
                raw = ""
            payload = {
                "fb": raw,
                "fb_seen": _hyb_fb_seen,
                "nav": nav_state,
                "lines": lines_state,
            }
            _hyb_write_line("STATE:" + _json.dumps(payload))
            _hyb_prev_fb[:] = _hyb_fb
            return True
        except Exception:
            return False

    def _hyb_emit_state(force=False):
        global _hyb_dirty, _hyb_force_full, _hyb_last_emit, _hyb_last_heartbeat
        global _hyb_last_full_emit, _hyb_frame_seq
        global _hyb_last_nav_sent, _hyb_last_lines_sent

        now = _hyb_ticks_ms()
        nav_state = _hyb_nav_state()
        lines_state = _hyb_lines_snapshot()
        nav_changed = nav_state != _hyb_last_nav_sent
        lines_changed = lines_state != _hyb_last_lines_sent
        periodic_full_due = _hyb_ticks_diff(now, _hyb_last_full_emit) >= _hyb_periodic_full_ms
        display_changed = _hyb_dirty or _hyb_force_full or force or periodic_full_due
        heartbeat_due = _hyb_ticks_diff(now, _hyb_last_heartbeat) >= _hyb_heartbeat_ms

        if not force:
            diff = _hyb_ticks_diff(now, _hyb_last_emit)
            if display_changed:
                if diff < _hyb_emit_dirty_ms:
                    return
            elif nav_changed or lines_changed:
                if diff < _hyb_emit_ui_ms:
                    return
            elif not heartbeat_due:
                return

        sent_ok = False
        if _hyb_binary_ok:
            if display_changed:
                next_frame_seq = (_hyb_frame_seq + 1) & 0x7F
                display_sent_ok = _hyb_send_full_frame(next_frame_seq)

                if display_sent_ok:
                    _hyb_dirty = False
                    _hyb_force_full = False
                    _hyb_frame_seq = next_frame_seq
                    sent_ok = True
                else:
                    _hyb_force_full = True

            if nav_changed or force:
                _hyb_send_nav(nav_state)
                _hyb_last_nav_sent = nav_state
                sent_ok = True
            if lines_changed or force:
                _hyb_send_lines(lines_state)
                _hyb_last_lines_sent = lines_state
                sent_ok = True
            if heartbeat_due:
                hb_flags = _hyb_fb_flags(_hyb_frame_seq)
                _hyb_send_packet(_HYB_PKT_HEARTBEAT, hb_flags, b"")
                _hyb_last_heartbeat = now
                sent_ok = True
        else:
            sent_ok = _hyb_emit_state_text(nav_state, lines_state)
            _hyb_last_nav_sent = nav_state
            _hyb_last_lines_sent = lines_state
            _hyb_dirty = False
            _hyb_force_full = False
            _hyb_last_heartbeat = now

        if sent_ok:
            _hyb_last_emit = now

    def _hyb_queue_key(col, row):
        global _hyb_force_full
        try:
            col = int(col)
            row = int(row)
            if not (0 <= col <= 4 and 0 <= row <= 9):
                return False
            _hyb_key_queue.append((col, row))
            # Do not force full-frame on every key; patch mode is much faster.
            if not _hyb_fb_seen:
                _hyb_force_full = True
            if len(_hyb_key_queue) > 1:
                del _hyb_key_queue[:-1]
            return True
        except Exception:
            return False

    # REPL-safe helper: PC can call this over normal serial without raw-repl toggling.
    def _hyb_key_enqueue(col, row):
        return _hyb_queue_key(col, row)

    # REPL-safe helper for link checks from PC.
    def _hyb_ping(msg=""):
        _hyb_write_line("ECHO:" + str(msg))
        return True

    def _hyb_set_page(page):
        global _hyb_cur_page
        try:
            _hyb_cur_page = int(page) & 0x07
        except Exception:
            _hyb_cur_page = 0

    def _hyb_set_col(col):
        global _hyb_cur_col
        try:
            _hyb_cur_col = int(col) & 0x7F
        except Exception:
            _hyb_cur_col = 0

    def _hyb_write_data(value):
        global _hyb_cur_col, _hyb_dirty, _hyb_fb_seen
        try:
            b = int(value) & 0xFF
            idx = (_hyb_cur_page * 128) + _hyb_cur_col
            if 0 <= idx < 1024 and _hyb_fb[idx] != b:
                _hyb_fb[idx] = b
                _hyb_dirty = True
            _hyb_fb_seen = True
            _hyb_cur_col = (_hyb_cur_col + 1) & 0x7F
        except Exception:
            pass

    def _hyb_graphics(buf, pos_args=(), kw_args=None):
        global _hyb_dirty, _hyb_fb_seen
        try:
            data = None
            if isinstance(buf, memoryview):
                data = buf
            elif isinstance(buf, (bytes, bytearray)):
                data = memoryview(buf)
            elif hasattr(buf, "buf"):
                data = memoryview(buf.buf)
            elif hasattr(buf, "buffer"):
                data = memoryview(buf.buffer)
            if data is None:
                return

            page = 0
            col = 0
            width = 128
            pages = 8

            if isinstance(pos_args, (tuple, list)):
                if len(pos_args) > 0:
                    page = int(pos_args[0])
                if len(pos_args) > 1:
                    col = int(pos_args[1])
                if len(pos_args) > 2:
                    width = int(pos_args[2])
                if len(pos_args) > 3:
                    pages = int(pos_args[3])

            if isinstance(kw_args, dict):
                if "page" in kw_args:
                    page = int(kw_args["page"])
                if "column" in kw_args:
                    col = int(kw_args["column"])
                if "width" in kw_args:
                    width = int(kw_args["width"])
                if "pages" in kw_args:
                    pages = int(kw_args["pages"])

            if page < 0:
                page = 0
            if page > 7:
                page = 7
            if col < 0:
                col = 0
            if col > 127:
                col = 127
            if width < 0:
                width = 0
            if pages < 0:
                pages = 0
            if col + width > 128:
                width = 128 - col
            if page + pages > 8:
                pages = 8 - page
            if width <= 0 or pages <= 0:
                return

            expected = width * pages
            available = len(data)
            if available <= 0:
                return
            if available > expected:
                available = expected

            changed = False
            src = 0
            for p in range(pages):
                if src >= available:
                    break
                dst_base = (page + p) * 128 + col
                span = width
                if src + span > available:
                    span = available - src
                for x in range(span):
                    b = data[src + x]
                    idx = dst_base + x
                    if _hyb_fb[idx] != b:
                        _hyb_fb[idx] = b
                        changed = True
                src += width

            if changed:
                _hyb_dirty = True
            _hyb_fb_seen = True
        except Exception:
            pass

    def _hyb_clear():
        global _hyb_dirty, _hyb_fb_seen
        try:
            for i in range(1024):
                _hyb_fb[i] = 0
            _hyb_dirty = True
            _hyb_fb_seen = True
        except Exception:
            pass

    _hyb_set_page_hook = _hyb_set_page
    _hyb_set_col_hook = _hyb_set_col
    _hyb_write_data_hook = _hyb_write_data
    _hyb_graphics_hook = _hyb_graphics
    _hyb_clear_hook = _hyb_clear

    try:
        if isinstance(cal_sci_buffer, (bytes, bytearray, memoryview)) and len(cal_sci_buffer) >= 1024:
            _hyb_graphics(cal_sci_buffer)
    except Exception:
        pass

    # Replace keypad loop so host key queue and physical keypad both work.
    def _hyb_keypad_loop():
        rows = getattr(typer.keypad, "rows", [])
        cols = getattr(typer.keypad, "cols", [])
        while True:
            if _hyb_key_queue:
                return _hyb_key_queue.pop(0)
            for row in range(len(rows)):
                machine.Pin(rows[row], machine.Pin.OUT).value(0)
                hit = None
                for col in range(len(cols)):
                    if machine.Pin(cols[col], machine.Pin.IN, machine.Pin.PULL_UP).value() == 0:
                        hit = (col, row)
                        break
                machine.Pin(rows[row], machine.Pin.OUT).value(1)
                if hit is not None:
                    return hit
            _hyb_sleep_ms(5)

    typer.keypad.keypad_loop = _hyb_keypad_loop

    def _hyb_handle_line(line):
        if not line:
            return
        if line.startswith("PING:"):
            msg = line[5:].strip()
            _hyb_write_line("ECHO:" + msg)
            return
        if line == "SYNC:FULL":
            try:
                global _hyb_force_full
                _hyb_force_full = True
                _hyb_emit_state(True)
            except Exception:
                pass
            _hyb_write_line("ECHO:SYNCFULL")
            return
        if line.startswith("KEY:"):
            raw = line[4:].strip()
            parts = raw.split(",")
            if len(parts) == 2:
                _hyb_queue_key(parts[0], parts[1])
            return
        _hyb_write_line("ECHO:" + line)

    def _hyb_stdin_worker():
        line_buf = ""
        while True:
            try:
                ch = sys.stdin.read(1)
                if ch is None or ch == "":
                    _hyb_sleep_ms(2)
                    continue
                if isinstance(ch, bytes):
                    ch = ch.decode()
                if ch == "\r" or ch == "\n":
                    if line_buf:
                        _hyb_handle_line(line_buf)
                        line_buf = ""
                elif len(line_buf) < 128:
                    line_buf += ch
                else:
                    line_buf = ""
            except Exception:
                _hyb_sleep_ms(10)

    def _hyb_state_worker():
        while True:
            _hyb_emit_state(False)
            _hyb_sleep_ms(1)

    _hyb_init_output_stream()
    if _hyb_binary_ok:
        _hyb_write_line("HYBRID_PROTO:BIN1")
    else:
        _hyb_write_line("HYBRID_PROTO:TXT")
    try:
        _deb_ms = int(float(getattr(typer, "debounce_delay_time", 0.035)) * 1000)
        if _deb_ms > 0:
            _hyb_write_line("HYB_KEY_DEB_MS:%d" % _deb_ms)
    except Exception:
        pass
    try:
        _fast_sec = data_bucket.get("hyb_graph_fast_debounce_sec", None)
        if _fast_sec is not None:
            _fast_ms = int(float(_fast_sec) * 1000)
            if _fast_ms > 0:
                _hyb_write_line("HYB_GRAPH_FAST_MS:%d" % _fast_ms)
    except Exception:
        pass
    _hyb_write_line("HYBRID_READY")
    _hyb_write_line("HYBRID_BAUD:115200")
    _thread.start_new_thread(_hyb_stdin_worker, ())
    _thread.start_new_thread(_hyb_state_worker, ())
    _hyb_emit_state(True)

except Exception as _hyb_exc:
    print("HYBRID_BRIDGE_ERR:", _hyb_exc)
    try:
        import sys as _sys
        _sys.print_exception(_hyb_exc)
    except Exception:
        pass
