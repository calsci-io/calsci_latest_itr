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
try:
    from apps.settings.backlight import apply_saved_backlight
except ImportError:
    from apps.settings.backlight import backlight_pin
    backlight_pin.on()
else:
    apply_saved_backlight()
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
    _HYB_GLOBAL_DEBOUNCE_SEC = 0.200
    typer.debounce_delay_time = _HYB_GLOBAL_DEBOUNCE_SEC
    data_bucket["hyb_global_debounce_sec"] = _HYB_GLOBAL_DEBOUNCE_SEC
except Exception:
    data_bucket["hyb_global_debounce_sec"] = None
data_bucket["hyb_graph_fast_debounce_sec"] = 0.001

# ------------------------------------------------------------
# Hybrid REPL helpers
# Single CDC rule: no unsolicited bridge traffic while the REPL helpers are
# active. The host/extension must explicitly request state with helper calls.
# ------------------------------------------------------------
try:
    import sys
    import time as _pytime

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

    import hybrid_sim

    _hyb_key_queue = []

    def _hyb_global(name):
        try:
            return globals().get(name, None)
        except Exception:
            return None

    def _hyb_sleep_ms(ms):
        if _utime is not None and hasattr(_utime, "sleep_ms"):
            _utime.sleep_ms(ms)
        else:
            _pytime.sleep(ms / 1000.0)

    def _hyb_write_line(text):
        text = str(text)
        try:
            sys.stdout.write(text + "\n")
        except Exception:
            try:
                print(text)
            except Exception:
                pass

    def _hyb_clean_line(text):
        try:
            s = str(text)
            s = s.replace("𖤓", "_")
            return s
        except Exception:
            return ""

    def _hyb_nav_state():
        try:
            nav_obj = _hyb_global("nav")
            if nav_obj is not None and hasattr(nav_obj, "current_state"):
                return str(nav_obj.current_state())
        except Exception:
            pass
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

    def _hyb_fb_to_b64(raw_fb):
        if raw_fb is None:
            return ""
        try:
            if isinstance(raw_fb, memoryview):
                raw_fb = raw_fb.tobytes()
            elif not isinstance(raw_fb, (bytes, bytearray)):
                raw_fb = bytes(raw_fb)
            return _binascii.b2a_base64(raw_fb).decode().strip()
        except Exception:
            return ""

    def _hyb_state_payload(state, include_fb=False):
        payload = {}
        if isinstance(state, dict):
            try:
                payload.update(state)
            except Exception:
                payload = {}

        try:
            payload["frame_id"] = int(payload.get("frame_id", -1))
        except Exception:
            payload["frame_id"] = -1

        if payload["frame_id"] >= 0:
            payload["fb_seq"] = payload["frame_id"] & 0x7F
        else:
            payload["fb_seq"] = 0
        payload["mode"] = bool(payload.get("mode", hybrid_sim.mode()))
        payload["capture_enabled"] = bool(payload.get("capture_enabled", hybrid_sim.enabled()))
        payload["fb_seen"] = bool(payload.get("fb_seen", payload["capture_enabled"]))
        payload["nav"] = _hyb_nav_state()
        payload["lines"] = _hyb_lines_snapshot()

        raw_fb = payload.pop("fb", None)
        if include_fb or raw_fb is not None:
            if raw_fb is None:
                raw_fb = hybrid_sim.read_fb()
            fb_b64 = _hyb_fb_to_b64(raw_fb)
            if fb_b64:
                payload["fb"] = fb_b64
                payload["fb_full"] = True

        return payload

    def _hyb_emit_state(last_frame=-1, force_full=False):
        try:
            last_frame = int(last_frame)
        except Exception:
            last_frame = -1

        try:
            if force_full:
                state = hybrid_sim.status()
            else:
                state = hybrid_sim.poll_state(last_frame)
            payload = _hyb_state_payload(state, include_fb=force_full)
            _hyb_write_line("STATE:" + _json.dumps(payload))
        except Exception as exc:
            _hyb_write_line("HYBRID_SYNC_ERR:%s" % exc)

    def _hyb_ping(token=""):
        _hyb_write_line("ECHO:%s" % str(token).strip())

    def _hyb_mode(enabled=None):
        if enabled is None:
            return hybrid_sim.mode()
        hybrid_sim.mode(bool(enabled))

    def _hyb_status():
        try:
            payload = _hyb_state_payload(hybrid_sim.status(), include_fb=False)
            _hyb_write_line("STATE:" + _json.dumps(payload))
        except Exception as exc:
            _hyb_write_line("HYBRID_STATUS_ERR:%s" % exc)

    def _hyb_queue_key(col, row):
        try:
            col = int(col)
            row = int(row)
            if not (0 <= col <= 4 and 0 <= row <= 9):
                return False
            _hyb_key_queue.append((col, row))
            if len(_hyb_key_queue) > 1:
                del _hyb_key_queue[:-1]
            return True
        except Exception:
            return False

    def _hyb_key(col, row):
        if _hyb_queue_key(col, row):
            _hyb_write_line("HYBRID_KEY_OK:%d,%d" % (int(col), int(row)))
        else:
            _hyb_write_line("HYBRID_KEY_ERR:RANGE")

    def _hyb_key_enqueue(col, row):
        return _hyb_queue_key(col, row)

    def _hyb_poll_state(last_frame=-1):
        _hyb_emit_state(last_frame, False)

    def _hyb_sync_full():
        _hyb_emit_state(-1, True)

    def _hyb_emit_hybrid_config():
        try:
            debounce_ms = int(float(getattr(typer, "debounce_delay_time", 0.100)) * 1000)
            if debounce_ms > 0:
                _hyb_write_line("HYB_KEY_DEB_MS:%d" % debounce_ms)
        except Exception:
            pass

        try:
            graph_sec = data_bucket.get("hyb_graph_fast_debounce_sec", None)
            if graph_sec is None:
                graph_sec = 0.001
                data_bucket["hyb_graph_fast_debounce_sec"] = graph_sec
            graph_ms = int(float(graph_sec) * 1000)
            if graph_ms > 0:
                _hyb_write_line("HYB_GRAPH_FAST_MS:%d" % graph_ms)
        except Exception:
            pass

    # Keep injected keys and physical keypad available through one loop.
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

    hybrid_sim.enable(True)
    hybrid_sim.mode(False)
    _hyb_write_line("HYBRID_PROTO:POLL_V1")
    _hyb_emit_hybrid_config()
    _hyb_write_line("HYBRID_READY")
    _hyb_write_line("HYBRID_BAUD:115200")

except Exception as _hyb_exc:
    print("HYBRID_BRIDGE_ERR:", _hyb_exc)
    try:
        import sys as _sys
        _sys.print_exception(_hyb_exc)
    except Exception:
        pass
