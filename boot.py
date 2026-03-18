import gc
import machine
import esp32
import st7565 as display
from sleeping_features import keypad_normal

# ----------------------------
# Hardware bootstrap
# ----------------------------
DISPLAY_PINS = (9, 11, 10, 13, 12)
DEEPSLEEP_KEY_PIN = 14

keypad_normal()
machine.Pin(DEEPSLEEP_KEY_PIN, machine.Pin.OUT, value=1, hold=False)
display.init(*DISPLAY_PINS)

try:
    display.clear_display()
except Exception:
    pass

gc.enable()
print("free ram initially=", gc.mem_free())
print("ram allocated initially=", gc.mem_alloc())

# ----------------------------
# Triple boot helpers
# ----------------------------
print("=================================")
print("  CalSci - Triple Boot System")
print("=================================")
print("  boot.switch_to_cpp()   - Reboot into C++")
print("  boot.switch_to_rust()  - Reboot into Rust")
print("  boot.boot_info()       - Show current partition")
print("=================================")


def boot_info():
    cur = esp32.Partition(esp32.Partition.RUNNING)
    print("Running from:", cur.info())
    print()
    print("All app partitions:")
    for part in esp32.Partition.find(esp32.Partition.TYPE_APP):
        print(" ", part.info())


def switch_to_cpp():
    _switch_to("ota_1", "C++")


def switch_to_rust():
    _switch_to("ota_2", "Rust")


def switch_to_micropython():
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
    try:
        return esp32.Partition(label)
    except Exception:
        pass

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
    except Exception as exc:
        print("Error switching to", label, ":", exc)


# ----------------------------
# Runtime globals
# ----------------------------
from apps.settings.backlight import backlight_pin
import builtins
import calsci_runtime
from data_modules.object_handler import data_bucket, menu, menu_refresh, typer

backlight_pin.on()
builtins.display = display
builtins.typer = typer
builtins.set_calsci_keypad_blocked = calsci_runtime.set_calsci_keypad_blocked
builtins.block_calsci_keypad = calsci_runtime.block_calsci_keypad
builtins.unblock_calsci_keypad = calsci_runtime.unblock_calsci_keypad
builtins.calsci_keypad_blocked = calsci_runtime.calsci_keypad_blocked

# WiFi startup stays disabled for fast boot.
builtins.sta_if = None
data_bucket["connection_status_g"] = False
data_bucket["ssid_g"] = ""


# ----------------------------
# Hybrid bridge (controller-facing)
# ----------------------------
try:
    import sys
    import _thread
    import time as _pytime

    try:
        import ujson as _json
    except Exception:
        import json as _json

    try:
        import ubinascii as _binascii
    except Exception:
        import binascii as _binascii

    try:
        import utime as _utime
    except Exception:
        _utime = None

    try:
        import uselect as _uselect
    except Exception:
        _uselect = None

    try:
        import hybrid_sim as _hyb_mod
    except Exception:
        _hyb_mod = None

    HYBRID_BAUDRATE = 115200
    _HYB_GLOBAL_DEBOUNCE_SEC = 0.150
    _HYB_GRAPH_DEBOUNCE_SEC = 0.001
    _HYB_EMIT_DIRTY_MS = 1
    _HYB_EMIT_PERIODIC_MS = 1000
    _HYB_FRAME_PREFIX = "{{CALSCI_HYB:"
    _HYB_FRAME_SUFFIX = "}}"

    _hyb_tx_lock = _thread.allocate_lock()
    _hyb_key_queue = []
    _hyb_local_keypad_loop = getattr(typer.keypad, "keypad_loop", None)

    _hyb_state = {
        "mode": "local",
        "hybrid_requested": False,
        "stream_enabled": False,
        "force_emit": False,
        "last_emit_ms": 0,
        "last_probe_ms": 0,
        "last_frame_id": -1,
        "protocol_enabled": True,
        "accept_protocol_stdin": False,
    }
    data_bucket["hyb_stream_enabled"] = False
    data_bucket["hyb_protocol_enabled"] = True
    data_bucket["hyb_accept_protocol_stdin"] = False
    data_bucket["hyb_mode"] = "local"
    data_bucket["hyb_requested"] = False

    def _hyb_norm_delay(value, fallback):
        try:
            parsed = float(value)
            if parsed > 0:
                return parsed
        except Exception:
            pass
        return float(fallback)

    if not isinstance(data_bucket.get("hyb_delay_local_map"), dict):
        data_bucket["hyb_delay_local_map"] = {}

    data_bucket["hyb_delay_global_sec"] = _hyb_norm_delay(
        data_bucket.get("hyb_delay_global_sec", _HYB_GLOBAL_DEBOUNCE_SEC),
        _HYB_GLOBAL_DEBOUNCE_SEC,
    )
    data_bucket["hyb_delay_local_map"]["graph"] = _hyb_norm_delay(
        data_bucket["hyb_delay_local_map"].get("graph", _HYB_GRAPH_DEBOUNCE_SEC),
        _HYB_GRAPH_DEBOUNCE_SEC,
    )

    # Backward-compatible names used by host apps.
    data_bucket["hyb_global_debounce_sec"] = data_bucket["hyb_delay_global_sec"]
    data_bucket["hyb_graph_fast_debounce_sec"] = data_bucket["hyb_delay_local_map"]["graph"]

    def hyb_delay_set_global(sec):
        sec = _hyb_norm_delay(sec, data_bucket.get("hyb_delay_global_sec", _HYB_GLOBAL_DEBOUNCE_SEC))
        data_bucket["hyb_delay_global_sec"] = sec
        data_bucket["hyb_global_debounce_sec"] = sec
        return sec

    def hyb_delay_set_local(name, sec):
        key = str(name).strip().lower()
        if not key:
            return None

        if not isinstance(data_bucket.get("hyb_delay_local_map"), dict):
            data_bucket["hyb_delay_local_map"] = {}

        sec = _hyb_norm_delay(sec, data_bucket.get("hyb_delay_global_sec", _HYB_GLOBAL_DEBOUNCE_SEC))
        data_bucket["hyb_delay_local_map"][key] = sec
        if key == "graph":
            data_bucket["hyb_graph_fast_debounce_sec"] = sec
        return sec

    def hyb_delay_use_global():
        sec = _hyb_norm_delay(
            data_bucket.get("hyb_delay_global_sec", _HYB_GLOBAL_DEBOUNCE_SEC),
            _HYB_GLOBAL_DEBOUNCE_SEC,
        )
        typer.debounce_delay_time = sec
        data_bucket["hyb_delay_active"] = "global"
        data_bucket["hyb_delay_active_sec"] = sec
        return sec

    def hyb_delay_use_local(name):
        key = str(name).strip().lower()
        if not key:
            return hyb_delay_use_global()

        local_map = data_bucket.get("hyb_delay_local_map")
        if not isinstance(local_map, dict):
            return hyb_delay_use_global()

        sec = _hyb_norm_delay(
            local_map.get(key, data_bucket.get("hyb_delay_global_sec", _HYB_GLOBAL_DEBOUNCE_SEC)),
            data_bucket.get("hyb_delay_global_sec", _HYB_GLOBAL_DEBOUNCE_SEC),
        )
        typer.debounce_delay_time = sec
        data_bucket["hyb_delay_active"] = key
        data_bucket["hyb_delay_active_sec"] = sec
        return sec

    builtins.hyb_delay_set_global = hyb_delay_set_global
    builtins.hyb_delay_set_local = hyb_delay_set_local
    builtins.hyb_delay_use_global = hyb_delay_use_global
    builtins.hyb_delay_use_local = hyb_delay_use_local

    # Boot default profile.
    hyb_delay_use_global()

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

    def _hyb_frame_text(text):
        return _HYB_FRAME_PREFIX + str(text) + _HYB_FRAME_SUFFIX

    def _hyb_write_line(text):
        try:
            _hyb_tx_lock.acquire()
            sys.stdout.write(_hyb_frame_text(text) + "\n")
            sys.stdout.flush()
        except Exception:
            pass
        finally:
            try:
                _hyb_tx_lock.release()
            except Exception:
                pass

    def _hyb_queue_key(col, row):
        try:
            col = int(col)
            row = int(row)
            if not (0 <= col <= 4 and 0 <= row <= 9):
                return False

            _hyb_key_queue.append((col, row))
            if len(_hyb_key_queue) > 1:
                del _hyb_key_queue[:-1]
            _hyb_state["force_emit"] = True
            return True
        except Exception:
            return False

    def hyb_stream_set_enabled(enabled):
        enabled = bool(enabled)
        _hyb_state["stream_enabled"] = enabled
        data_bucket["hyb_stream_enabled"] = enabled
        if enabled:
            _hyb_state["force_emit"] = True
        return enabled

    def hyb_stream_is_enabled():
        return bool(_hyb_state["stream_enabled"])

    def _hyb_use_local_keypad():
        if _hyb_local_keypad_loop is not None:
            typer.keypad.keypad_loop = _hyb_local_keypad_loop
        data_bucket["hyb_keypad_mode"] = "local"

    def _hyb_use_hybrid_keypad():
        typer.keypad.keypad_loop = hyb_keypad_input
        data_bucket["hyb_keypad_mode"] = "hybrid"

    def hyb_bridge_status():
        return {
            "mode": _hyb_state["mode"],
            "hybrid_requested": bool(_hyb_state["hybrid_requested"]),
            "stream_enabled": bool(_hyb_state["stream_enabled"]),
            "protocol_enabled": bool(_hyb_state["protocol_enabled"]),
            "accept_protocol_stdin": bool(_hyb_state["accept_protocol_stdin"]),
            "delay_active": data_bucket.get("hyb_delay_active", "global"),
            "delay_active_sec": data_bucket.get("hyb_delay_active_sec", data_bucket.get("hyb_delay_global_sec")),
        }

    def _hyb_apply_local_mode(hybrid_requested):
        _hyb_state["mode"] = "local"
        _hyb_state["hybrid_requested"] = bool(hybrid_requested)
        _hyb_state["stream_enabled"] = False
        _hyb_state["force_emit"] = False
        _hyb_state["protocol_enabled"] = True
        _hyb_state["accept_protocol_stdin"] = False
        data_bucket["hyb_mode"] = "local"
        data_bucket["hyb_requested"] = bool(hybrid_requested)
        data_bucket["hyb_stream_enabled"] = False
        data_bucket["hyb_protocol_enabled"] = True
        data_bucket["hyb_accept_protocol_stdin"] = False
        _hyb_use_local_keypad()
        return True

    def hyb_enter_local_mode():
        _hyb_apply_local_mode(False)
        _hyb_write_line("CTRL:HYBRID_DISABLED:OK")
        return True

    def _hyb_apply_command_mode():
        _hyb_apply_local_mode(_hyb_state["hybrid_requested"])
        _hyb_state["mode"] = "command"
        _hyb_state["protocol_enabled"] = False
        data_bucket["hyb_mode"] = "command"
        data_bucket["hyb_protocol_enabled"] = False
        return True

    def hyb_enter_command_mode():
        _hyb_apply_command_mode()
        _hyb_write_line("CTRL:COMMAND:OK")
        return True

    def hyb_enter_exec_mode():
        _hyb_apply_command_mode()
        _hyb_state["mode"] = "exec"
        data_bucket["hyb_mode"] = "exec"
        _hyb_write_line("CTRL:HYBRID_OFF:OK")
        return True

    def hyb_enter_hybrid_mode(stream_enabled=False):
        _hyb_state["mode"] = "hybrid"
        _hyb_state["hybrid_requested"] = True
        _hyb_state["protocol_enabled"] = True
        _hyb_state["accept_protocol_stdin"] = True
        _hyb_state["stream_enabled"] = bool(stream_enabled)
        _hyb_state["force_emit"] = _hyb_state["stream_enabled"]
        data_bucket["hyb_mode"] = "hybrid"
        data_bucket["hyb_requested"] = True
        data_bucket["hyb_protocol_enabled"] = True
        data_bucket["hyb_accept_protocol_stdin"] = True
        data_bucket["hyb_stream_enabled"] = _hyb_state["stream_enabled"]
        hyb_delay_use_global()
        _hyb_use_hybrid_keypad()
        _hyb_write_line("CTRL:HYBRID_ON:OK")
        if _hyb_state["stream_enabled"]:
            _hyb_emit_state_text()
        return True

    def _hyb_ping(token):
        _hyb_write_line("ECHO:" + str(token).strip())

    builtins.hyb_stream_set_enabled = hyb_stream_set_enabled
    builtins.hyb_stream_is_enabled = hyb_stream_is_enabled
    builtins.hyb_bridge_status = hyb_bridge_status
    builtins.hyb_enter_local_mode = hyb_enter_local_mode
    builtins.hyb_enter_command_mode = hyb_enter_command_mode
    builtins.hyb_enter_exec_mode = hyb_enter_exec_mode
    builtins.hyb_enter_hybrid_mode = hyb_enter_hybrid_mode
    builtins.hyb_keypad_input = None
    builtins.hyb_stream_updated_buffer = None

    def _hyb_clean_protocol_line(line):
        if line is None:
            return ""
        try:
            text = str(line)
        except Exception:
            return ""

        # Keep protocol parser stable even if control bytes leak into the line buffer.
        cleaned = ""
        for ch in text:
            code = ord(ch)
            if 32 <= code <= 126:
                cleaned += ch
        return cleaned.strip()

    def _hyb_release_rows(rows):
        for row_pin in rows:
            try:
                machine.Pin(row_pin, machine.Pin.OUT).value(1)
            except Exception:
                pass

    def _hyb_wait_while_keypad_blocked(rows):
        if not calsci_runtime.calsci_keypad_blocked():
            return False
        if _hyb_key_queue:
            del _hyb_key_queue[:]
        calsci_runtime.wait_if_repl_busy(lambda: _hyb_release_rows(rows))
        return True

    def hyb_keypad_input():
        rows = getattr(typer.keypad, "rows", [])
        cols = getattr(typer.keypad, "cols", [])

        while True:
            if _hyb_wait_while_keypad_blocked(rows):
                continue
            if _hyb_key_queue:
                return _hyb_key_queue.pop(0)

            for row in range(len(rows)):
                if _hyb_wait_while_keypad_blocked(rows):
                    break
                machine.Pin(rows[row], machine.Pin.OUT).value(0)
                hit = None

                for col in range(len(cols)):
                    if _hyb_wait_while_keypad_blocked(rows):
                        hit = None
                        break
                    if machine.Pin(cols[col], machine.Pin.IN, machine.Pin.PULL_UP).value() == 0:
                        hit = (col, row)
                        break

                machine.Pin(rows[row], machine.Pin.OUT).value(1)
                if calsci_runtime.calsci_keypad_blocked():
                    break
                if hit is not None:
                    return hit

            _hyb_sleep_ms(5)

    builtins.hyb_keypad_input = hyb_keypad_input

    def _hyb_fb_changed():
        if _hyb_mod is None:
            return False
        try:
            return bool(_hyb_mod.changed_since(_hyb_state["last_frame_id"]))
        except Exception:
            return False

    def _hyb_emit_state_text():
        try:
            fb = b""
            frame_id = _hyb_state["last_frame_id"]
            fb_seen = False

            if _hyb_mod is not None:
                frame = _hyb_mod.pop_frame()
                if isinstance(frame, dict):
                    frame_id = int(frame.get("frame_id", frame_id))
                    fb = frame.get("fb", b"")
                else:
                    fb = _hyb_mod.read_fb()
                    frame_id = int(_hyb_mod.frame_id())

                if fb is None:
                    fb = b""
                if isinstance(fb, memoryview):
                    fb = fb.tobytes()
                elif not isinstance(fb, (bytes, bytearray)):
                    fb = bytes(fb)

                _hyb_state["last_frame_id"] = frame_id
                fb_seen = True

            has_pixels = False
            for value in fb:
                if value:
                    has_pixels = True
                    break

            if has_pixels:
                raw = _binascii.b2a_base64(fb)
                if isinstance(raw, bytes):
                    raw = raw.decode().strip()
            else:
                raw = ""

            payload = {
                "fb": raw,
                "fb_seen": fb_seen,
            }
            _hyb_write_line("STATE:" + _json.dumps(payload))
            _hyb_state["last_emit_ms"] = _hyb_ticks_ms()
            _hyb_state["force_emit"] = False
            return True
        except Exception:
            return False

    def hyb_stream_updated_buffer():
        while True:
            if not _hyb_state["stream_enabled"]:
                _hyb_sleep_ms(5)
                continue

            now = _hyb_ticks_ms()
            emit_due = bool(_hyb_state["force_emit"])
            if not emit_due and _hyb_ticks_diff(now, _hyb_state["last_probe_ms"]) >= 8:
                _hyb_state["last_probe_ms"] = now
                emit_due = _hyb_fb_changed()

            periodic_due = _hyb_ticks_diff(now, _hyb_state["last_emit_ms"]) >= _HYB_EMIT_PERIODIC_MS

            if emit_due or periodic_due:
                if (not emit_due) or _hyb_ticks_diff(now, _hyb_state["last_emit_ms"]) >= _HYB_EMIT_DIRTY_MS:
                    _hyb_emit_state_text()
                _hyb_sleep_ms(1)
            else:
                _hyb_sleep_ms(4)

    builtins.hyb_stream_updated_buffer = hyb_stream_updated_buffer

    def _hyb_handle_line(line):
        line = _hyb_clean_protocol_line(line)
        if not line:
            return

        if line == "CTRL:HYBRID_OFF":
            hyb_enter_exec_mode()
            return

        if line == "CTRL:COMMAND":
            hyb_enter_command_mode()
            return

        if line == "CTRL:HYBRID_DISABLE":
            hyb_enter_local_mode()
            return

        if line == "CTRL:HYBRID_ON":
            hyb_enter_hybrid_mode(False)
            return

        if line == "CTRL:STATUS":
            try:
                _hyb_write_line("CTRL:STATUS:" + _json.dumps(hyb_bridge_status()))
            except Exception:
                _hyb_write_line("CTRL:STATUS:{}")
            return

        if line.startswith("PING:"):
            _hyb_ping(line[5:])
            return

        if line == "SYNC:FULL":
            if not _hyb_state["accept_protocol_stdin"]:
                return
            hyb_stream_set_enabled(True)
            _hyb_emit_state_text()
            _hyb_write_line("ECHO:SYNCFULL")
            return

        if line.startswith("KEY:"):
            if not _hyb_state["accept_protocol_stdin"]:
                return
            args = line[4:].strip()
            parts = args.split(",")
            if len(parts) == 2:
                if not _hyb_state["stream_enabled"]:
                    hyb_stream_set_enabled(True)
                _hyb_queue_key(parts[0], parts[1])
            return

        # OFF/disabled or unknown protocol: no action.
        return

    def _hyb_stdin_worker():
        poller = None
        if _uselect is not None:
            try:
                poller = _uselect.poll()
                poller.register(sys.stdin, _uselect.POLLIN)
            except Exception:
                poller = None

        line_buf = ""
        while True:
            try:
                if not _hyb_state["protocol_enabled"]:
                    if line_buf:
                        line_buf = ""
                    _hyb_sleep_ms(5)
                    continue

                if poller is not None:
                    try:
                        events = poller.poll(20)
                    except Exception:
                        events = ()
                    if not events:
                        _hyb_sleep_ms(1)
                        continue

                ch = sys.stdin.read(1)
                if ch is None or ch == "":
                    _hyb_sleep_ms(2)
                    continue

                if isinstance(ch, bytes):
                    ch = ch.decode("utf-8", "ignore")
                    if not ch:
                        continue

                # Drop non-text control bytes so protocol lines don't get poisoned.
                if len(ch) == 1:
                    code = ord(ch)
                    if code < 32 and ch not in ("\r", "\n", "\t"):
                        continue

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

    _hyb_write_line("HYBRID_PROTO:TXT")

    try:
        deb_ms = int(float(getattr(typer, "debounce_delay_time", 0.100)) * 1000)
        if deb_ms > 0:
            _hyb_write_line("HYB_KEY_DEB_MS:%d" % deb_ms)
    except Exception:
        pass

    try:
        graph_sec = data_bucket.get("hyb_graph_fast_debounce_sec", None)
        if graph_sec is not None:
            graph_ms = int(float(graph_sec) * 1000)
            if graph_ms > 0:
                _hyb_write_line("HYB_GRAPH_FAST_MS:%d" % graph_ms)
    except Exception:
        pass

    _hyb_write_line("HYBRID_READY")
    _hyb_write_line("HYBRID_BAUD:%d" % HYBRID_BAUDRATE)
    _hyb_write_line("HYBRID_MODE:LOCAL")

    _thread.start_new_thread(_hyb_stdin_worker, ())
    _thread.start_new_thread(hyb_stream_updated_buffer, ())
    _hyb_use_local_keypad()

except Exception as _hyb_exc:
    try:
        _hyb_write_line("HYBRID_BRIDGE_ERR:%s" % _hyb_exc)
    except Exception:
        print("HYBRID_BRIDGE_ERR:", _hyb_exc)
    try:
        import sys as _sys

        _sys.print_exception(_hyb_exc)
    except Exception:
        pass
