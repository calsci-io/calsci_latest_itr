# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

# ----------------------------
# config constants
# ----------------------------
try:
    from micropython import const
except ImportError:
    def const(value):
        return value

import _thread
import gc
import math
import struct
import sys
import time
try:
    import ujson as json
except ImportError:
    import json

import machine
import network
try:
    import bluetooth
except ImportError:
    import ubluetooth as bluetooth  # type: ignore
import urequests

try:
    import esp32
except ImportError:
    esp32 = None

from data_modules.object_handler import (
    chrs,
    data_bucket,
    display,
    form,
    form_refresh,
    keyin,
    keymap,
    keypad_state_manager,
    keypad_state_manager_reset,
    menu,
    menu_refresh,
    nav,
    st7565_display_pins,
    typer,
)
from sleeping_features import swdt, test_deep_sleep_awake


if hasattr(time, "ticks_ms"):
    _ticks_ms = time.ticks_ms
    _ticks_diff = time.ticks_diff
else:
    def _ticks_ms():
        return int(time.time() * 1000)

    def _ticks_diff(a, b):
        return a - b


if hasattr(time, "sleep_ms"):
    _sleep_ms = time.sleep_ms
else:
    def _sleep_ms(ms):
        time.sleep(ms / 1000)


DISPLAY_PINS = (
    st7565_display_pins["cs1"],
    st7565_display_pins["rst"],
    st7565_display_pins["rs"],
    st7565_display_pins["sck"],
    st7565_display_pins["sda"],
)

DISPLAY_ROWS = const(8)
DISPLAY_COLS = const(21)
CHAR_STRIDE = const(6)

POLL_MS = const(25)
STATUS_REFRESH_MS = const(250)
DASHBOARD_REFRESH_MS = const(500)

WIFI_CONNECT_TIMEOUT_MS = const(12000)
WIFI_RETRY_BACKOFF_MS = const(1200)
WIFI_FETCH_TIMEOUT_S = const(10)
WIFI_THREAD_STACK = const(16384)
CPU_THREAD_STACK = const(16384)

BLE_NAME = "CalSci-Stress"
BLE_NOTIFY_INTERVAL_MS = const(120)
BLE_RXBUF = const(256)

CPU_MATRIX_SIZE = const(5)
CPU_QR_ITERATIONS = const(10)
CPU_GC_EVERY = const(8)
RUN_SAVE_INTERVAL_MS = const(60000)
RUN_STORE_PATH = "db/stress_runs.json"

PUBCHEM_URL_TEMPLATE = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
    "%s/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
)

WIFI_MOLECULES = (
    "glucose",
    "fructose",
    "sucrose",
    "ribose",
    "deoxyribose",
    "adenine",
    "guanine",
    "cytosine",
    "thymine",
    "uracil",
)

CPU_BASE_MATRIX = (
    (5.0, 1.0, 0.5, 2.0, 1.5),
    (1.0, 4.5, 1.2, 0.8, 1.1),
    (0.5, 1.2, 4.0, 1.4, 0.9),
    (2.0, 0.8, 1.4, 5.5, 1.0),
    (1.5, 1.1, 0.9, 1.0, 4.8),
)


# ----------------------------
# shared status/state
# ----------------------------
_STATE_LOCK = _thread.allocate_lock()
_STATE = {}

_DISPLAY_READY = False
_WIFI_THREAD_STARTED = False
_CPU_THREAD_STARTED = False
_CPU_THREAD_REQUESTED = False
_CPU_INLINE_FALLBACK = False
_LAST_BLE_NOTIFY_MS = 0
_KEY_HELD = None
_LAST_KEY_MS = 0


def _state_mutate(mutator):
    _STATE_LOCK.acquire()
    try:
        return mutator(_STATE)
    finally:
        _STATE_LOCK.release()


def _state_update(**changes):
    def _mutator(state):
        state.update(changes)
    _state_mutate(_mutator)


def _state_snapshot():
    _STATE_LOCK.acquire()
    try:
        return dict(_STATE)
    finally:
        _STATE_LOCK.release()


def _stop_requested():
    _STATE_LOCK.acquire()
    try:
        return bool(_STATE.get("stop_requested"))
    finally:
        _STATE_LOCK.release()


def _request_stop():
    _state_update(stop_requested=True, phase="stop")


def _reset_state():
    global _CPU_THREAD_REQUESTED, _CPU_INLINE_FALLBACK
    global _LAST_BLE_NOTIFY_MS, _KEY_HELD, _LAST_KEY_MS

    now = _ticks_ms()
    _CPU_THREAD_REQUESTED = False
    _CPU_INLINE_FALLBACK = False
    _LAST_BLE_NOTIFY_MS = 0
    _KEY_HELD = None
    _LAST_KEY_MS = 0
    _STATE_LOCK.acquire()
    try:
        _STATE.clear()
        _STATE.update(
            {
                "start_ms": now,
                "phase": "wifi",
                "stop_requested": False,
                "wifi_ssid": "",
                "wifi_password": "",
                "wifi_state": "idle",
                "wifi_connected": False,
                "wifi_request_count": 0,
                "wifi_success_count": 0,
                "wifi_error_count": 0,
                "wifi_current_query": "-",
                "wifi_last_fetch_ms": 0,
                "wifi_last_success_ms": 0,
                "wifi_last_error": "",
                "wifi_first_success": False,
                "ble_state": "idle",
                "ble_connected": False,
                "ble_connection_count": 0,
                "ble_tx_bytes": 0,
                "ble_tx_packets": 0,
                "ble_rx_bytes": 0,
                "ble_rx_packets": 0,
                "ble_last_error": "",
                "ble_notify_seq": 0,
                "cpu_state": "idle",
                "cpu_mode": "thread",
                "cpu_batch_count": 0,
                "cpu_last_batch_ms": 0,
                "cpu_batches_per_sec": 0.0,
                "cpu_mem_free": gc.mem_free(),
                "cpu_mem_alloc": gc.mem_alloc(),
                "cpu_temp_c": None,
                "cpu_last_error": "",
                "cpu_total_base_ms": 0,
                "cpu_total_live_ms": 0,
                "cpu_last_run_ms": 0,
                "cpu_run_count": 0,
                "cpu_session_start_ms": 0,
                "cpu_last_save_ms": 0,
                "cpu_run_active": False,
            }
        )
    finally:
        _STATE_LOCK.release()


def _ensure_display_ready():
    global _DISPLAY_READY
    if _DISPLAY_READY:
        return
    try:
        display.init(*DISPLAY_PINS)
    except Exception:
        pass
    try:
        display.clear_display()
    except Exception:
        pass
    _DISPLAY_READY = True


def _feed_sleep_watchdog():
    try:
        swdt.feed()
    except Exception:
        pass


def _default_run_store():
    return {
        "version": 1,
        "run_count": 0,
        "total_run_ms": 0,
        "last_run_ms": 0,
        "current_run_open": False,
        "current_run_ms": 0,
    }


def _load_run_store():
    store = _default_run_store()
    try:
        with open(RUN_STORE_PATH, "r") as handle:
            loaded = json.loads(handle.read())
        if isinstance(loaded, dict):
            store.update(loaded)
    except Exception:
        pass

    try:
        store["run_count"] = int(store.get("run_count", 0) or 0)
    except Exception:
        store["run_count"] = 0
    try:
        store["total_run_ms"] = int(store.get("total_run_ms", 0) or 0)
    except Exception:
        store["total_run_ms"] = 0
    try:
        store["last_run_ms"] = int(store.get("last_run_ms", 0) or 0)
    except Exception:
        store["last_run_ms"] = 0
    try:
        store["current_run_ms"] = int(store.get("current_run_ms", 0) or 0)
    except Exception:
        store["current_run_ms"] = 0
    store["current_run_open"] = bool(store.get("current_run_open"))
    if store["current_run_open"] and store["current_run_ms"] > store["last_run_ms"]:
        store["last_run_ms"] = store["current_run_ms"]
    return store


def _write_run_store(store):
    try:
        with open(RUN_STORE_PATH, "w") as handle:
            handle.write(json.dumps(store))
        return True
    except Exception as exc:
        _state_update(cpu_last_error=str(exc)[:DISPLAY_COLS])
        return False


def _apply_loaded_run_store():
    store = _load_run_store()
    _state_update(
        cpu_total_base_ms=store["total_run_ms"],
        cpu_total_live_ms=store["total_run_ms"],
        cpu_last_run_ms=store["last_run_ms"],
        cpu_run_count=store["run_count"],
        cpu_run_active=False,
        cpu_session_start_ms=0,
        cpu_last_save_ms=0,
    )
    return store


# ----------------------------
# plain dashboard renderer
# ----------------------------
def _fit_text(text, width=DISPLAY_COLS):
    text = str(text)
    if len(text) > width:
        return text[:width]
    return text + (" " * (width - len(text)))


def _short_count(value):
    value = int(value or 0)
    if value >= 1000000:
        return "%dm" % (value // 1000000)
    if value >= 1000:
        return "%dk" % (value // 1000)
    return str(value)


def _format_rate(value):
    value = float(value or 0.0)
    if value >= 10:
        return str(int(round(value)))
    return "%.1f" % value


def _format_duration_ms(value):
    value = int(value or 0)
    if value >= 10000:
        return "%ds" % (value // 1000)
    if value >= 1000:
        return "%.1fs" % (value / 1000)
    return "%dms" % value


def _format_uptime(value_ms, short=False):
    total = max(0, int(value_ms // 1000))
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    if short:
        if hours:
            return "%d:%02d" % (hours, minutes)
        return "%02d:%02d" % (minutes, seconds)
    return "%02d:%02d:%02d" % (hours, minutes, seconds)


def _phase_label(phase):
    labels = {
        "wifi": "WIFI",
        "ble": "BLE",
        "run": "RUN",
        "stop": "STOP",
        "error": "ERR",
    }
    return labels.get(phase, "INIT")


def _wifi_state_label(value):
    labels = {
        "idle": "idle",
        "scan": "scan",
        "connect": "conn",
        "reconnect": "rcon",
        "stress": "load",
        "fetch": "http",
        "ok": "ok",
        "error": "err",
    }
    return labels.get(value, str(value)[:4])


def _ble_state_label(value):
    labels = {
        "idle": "idle",
        "init": "init",
        "adv": "adv",
        "conn": "conn",
        "disc": "disc",
        "error": "err",
    }
    return labels.get(value, str(value)[:4])


def _cpu_state_label(value):
    labels = {
        "idle": "IDLE",
        "run": "ON",
        "error": "ERR",
    }
    return labels.get(value, str(value)[:4].upper())


def _cpu_mode_label(value):
    return "co-op" if value == "inline" else "thread"


def _write_text_row(page, text):
    display.set_page_address(page)
    display.set_column_address(0)
    for char in _fit_text(text):
        for byte in chrs.Chr2bytes(char):
            display.write_data(byte)
        display.write_data(0x00)
    display.write_data(0x00)
    display.write_data(0x00)


def _render_lines(lines):
    padded = list(lines[:DISPLAY_ROWS])
    while len(padded) < DISPLAY_ROWS:
        padded.append("")
    for row_index in range(DISPLAY_ROWS):
        _write_text_row(row_index, padded[row_index])


def _dashboard_lines():
    snapshot = _state_snapshot()
    uptime_ms = int(snapshot.get("cpu_total_live_ms", 0) or 0)
    if uptime_ms <= 0:
        uptime_ms = _ticks_diff(_ticks_ms(), snapshot["start_ms"])
    temp_c = snapshot.get("cpu_temp_c")

    title = "Stress %s %s" % (
        _phase_label(snapshot["phase"]),
        _format_uptime(uptime_ms, short=bool(temp_c is not None)),
    )
    if temp_c is not None:
        title = "%s T%d" % (title, int(temp_c))

    wifi_line = "WF %s s%s e%s" % (
        _wifi_state_label(snapshot["wifi_state"]),
        _short_count(snapshot["wifi_success_count"]),
        _short_count(snapshot["wifi_error_count"]),
    )
    wifi_query = "Q %s %s" % (
        str(snapshot["wifi_current_query"])[:11],
        _format_duration_ms(snapshot["wifi_last_fetch_ms"]),
    )
    ble_line = "BLE %s c%s" % (
        _ble_state_label(snapshot["ble_state"]),
        _short_count(snapshot["ble_connection_count"]),
    )
    ble_tx = "TX %sB %sp" % (
        _short_count(snapshot["ble_tx_bytes"]),
        _short_count(snapshot["ble_tx_packets"]),
    )
    ble_rx = "RX %sB %sp" % (
        _short_count(snapshot["ble_rx_bytes"]),
        _short_count(snapshot["ble_rx_packets"]),
    )
    mem_free_k = int(snapshot["cpu_mem_free"] // 1024)
    mem_alloc_k = int(snapshot["cpu_mem_alloc"] // 1024)
    cpu_line = "CPU %s %s/s %d/%dk" % (
        _cpu_state_label(snapshot["cpu_state"]),
        _format_rate(snapshot["cpu_batches_per_sec"]),
        mem_free_k,
        mem_alloc_k,
    )
    cpu_line = "%s %s" % (
        cpu_line[:14],
        _cpu_mode_label(snapshot.get("cpu_mode", "thread"))[:6],
    )

    return [
        title,
        wifi_line,
        wifi_query,
        ble_line,
        ble_tx,
        ble_rx,
        cpu_line,
        "Back=stop",
    ]


def _render_dashboard():
    _render_lines(_dashboard_lines())


def _history_screen_lines():
    snapshot = _state_snapshot()
    return [
        "Saved stress time",
        "Runs:%s" % _short_count(snapshot.get("cpu_run_count", 0)),
        "Total:%s" % _format_uptime(snapshot.get("cpu_total_live_ms", 0)),
        "Last:%s" % _format_uptime(snapshot.get("cpu_last_run_ms", 0)),
        "",
        "OK=add run",
        "AC=reset",
        "Back=stop",
    ]


def _reset_run_history():
    store = _default_run_store()
    _write_run_store(store)
    _state_update(
        cpu_total_base_ms=0,
        cpu_total_live_ms=0,
        cpu_last_run_ms=0,
        cpu_run_count=0,
        cpu_run_active=False,
        cpu_session_start_ms=0,
        cpu_last_save_ms=0,
    )


def _history_gate():
    keypad_state_manager_reset()
    next_refresh = 0
    while not _stop_requested():
        now = _ticks_ms()
        if _ticks_diff(now, next_refresh) >= 0:
            _render_lines(_history_screen_lines())
            next_refresh = now + STATUS_REFRESH_MS

        inp = _poll_input()
        if inp == "ok":
            return True
        if inp == "back":
            return False
        if inp == "AC":
            _reset_run_history()
            next_refresh = 0

        _feed_sleep_watchdog()
        _sleep_ms(POLL_MS)
    return False


def _begin_cpu_run_session():
    snapshot = _state_snapshot()
    session_start = _ticks_ms()
    store = {
        "version": 1,
        "run_count": int(snapshot.get("cpu_run_count", 0) or 0) + 1,
        "total_run_ms": int(snapshot.get("cpu_total_base_ms", 0) or 0),
        "last_run_ms": int(snapshot.get("cpu_last_run_ms", 0) or 0),
        "current_run_open": True,
        "current_run_ms": 0,
    }
    _write_run_store(store)
    _state_update(
        cpu_run_count=store["run_count"],
        cpu_run_active=True,
        cpu_session_start_ms=session_start,
        cpu_last_save_ms=session_start,
        cpu_total_live_ms=store["total_run_ms"],
    )


def _persist_cpu_run(force=False, closing=False):
    snapshot = _state_snapshot()
    if not snapshot.get("cpu_run_active"):
        return

    now = _ticks_ms()
    session_start = int(snapshot.get("cpu_session_start_ms", 0) or 0)
    if session_start <= 0:
        return

    session_ms = max(0, _ticks_diff(now, session_start))
    total_ms = int(snapshot.get("cpu_total_base_ms", 0) or 0) + session_ms
    run_count = int(snapshot.get("cpu_run_count", 0) or 0)
    last_run_ms = session_ms

    _state_update(
        cpu_total_live_ms=total_ms,
        cpu_last_run_ms=last_run_ms,
    )

    if not force:
        last_save = int(snapshot.get("cpu_last_save_ms", 0) or 0)
        if _ticks_diff(now, last_save) < RUN_SAVE_INTERVAL_MS:
            return

    store = {
        "version": 1,
        "run_count": run_count,
        "total_run_ms": total_ms,
        "last_run_ms": last_run_ms,
        "current_run_open": not closing,
        "current_run_ms": 0 if closing else session_ms,
    }
    if _write_run_store(store):
        _state_update(cpu_last_save_ms=now)
        if closing:
            _state_update(
                cpu_run_active=False,
                cpu_total_base_ms=total_ms,
                cpu_total_live_ms=total_ms,
                cpu_last_run_ms=last_run_ms,
            )


# ----------------------------
# Wi-Fi selection/connect UI
# ----------------------------
def _scan_keypad_once():
    try:
        for row_index in range(len(keyin.rows)):
            machine.Pin(keyin.rows[row_index], machine.Pin.OUT).value(0)
            for col_index in range(len(keyin.cols)):
                if machine.Pin(
                    keyin.cols[col_index],
                    machine.Pin.IN,
                    machine.Pin.PULL_UP,
                ).value() == 0:
                    machine.Pin(keyin.rows[row_index], machine.Pin.OUT).value(1)
                    return col_index, row_index
            machine.Pin(keyin.rows[row_index], machine.Pin.OUT).value(1)
    except Exception:
        return None
    return None


def _poll_input():
    global _KEY_HELD, _LAST_KEY_MS

    raw = _scan_keypad_once()
    if raw is None:
        _KEY_HELD = None
        return None
    if raw == _KEY_HELD:
        return None

    now = _ticks_ms()
    debounce_ms = max(120, int(typer.debounce_delay() * 1000))
    if _ticks_diff(now, _LAST_KEY_MS) < debounce_ms:
        _KEY_HELD = raw
        return None

    _KEY_HELD = raw
    _LAST_KEY_MS = now

    text = keymap.key_out(raw[0], raw[1])
    _feed_sleep_watchdog()
    if text == "off":
        test_deep_sleep_awake()
    return text


def _show_menu(lines):
    menu.menu_list = [str(line)[:DISPLAY_COLS] for line in lines]
    menu.update()
    display.clear_display()
    menu_refresh.refresh(state=nav.current_state())


def _show_form(lines, input_value=" "):
    form.input_list = {"inp_0": input_value if input_value else " "}
    form.form_list = lines
    form.update()
    display.clear_display()
    form_refresh.refresh(state=nav.current_state())


def _wait_plain_screen(lines, ble_uart=None):
    keypad_state_manager_reset()
    next_refresh = 0
    while not _stop_requested():
        now = _ticks_ms()
        if _ticks_diff(now, next_refresh) >= 0:
            current_lines = lines() if callable(lines) else lines
            _render_lines(current_lines)
            next_refresh = now + STATUS_REFRESH_MS
        _service_ble_notify(ble_uart, now)
        inp = _poll_input()
        if inp == "ok":
            return True
        if inp == "back":
            return False
        _feed_sleep_watchdog()
        _sleep_ms(POLL_MS)
    return False


def _scan_networks(sta_if):
    _state_update(wifi_state="scan")
    sta_if.active(True)
    networks = sta_if.scan()

    dedup = {}
    hidden_count = 0
    for info in networks:
        try:
            ssid = info[0].decode().strip()
        except Exception:
            ssid = ""
        if not ssid:
            hidden_count += 1
            ssid = "<hidden-%d>" % hidden_count
        rssi = info[3]
        previous = dedup.get(ssid)
        if previous is None or rssi > previous[3]:
            dedup[ssid] = info

    entries = []
    ordered = sorted(dedup.items(), key=lambda item: item[1][3], reverse=True)
    index = 1
    for ssid, info in ordered:
        label = "%d. %s" % (index, ssid)
        entries.append({"ssid": ssid, "label": _fit_text(label)})
        index += 1
    return entries


def _select_wifi_ssid(sta_if):
    keypad_state_manager_reset()
    while not _stop_requested():
        _render_lines(
            [
                "WiFi scan",
                "",
                "Scanning...",
                "",
                "",
                "",
                "",
                "Back=stop",
            ]
        )
        _feed_sleep_watchdog()
        try:
            entries = _scan_networks(sta_if)
        except Exception as exc:
            message = str(exc)[:DISPLAY_COLS]
            if _wait_plain_screen(
                [
                    "WiFi scan failed",
                    message,
                    "",
                    "OK=rescan",
                    "",
                    "",
                    "",
                    "Back=stop",
                ]
            ):
                continue
            return None

        if not entries:
            if _wait_plain_screen(
                [
                    "No WiFi found",
                    "",
                    "OK=rescan",
                    "",
                    "",
                    "",
                    "",
                    "Back=stop",
                ]
            ):
                continue
            return None

        labels = [entry["label"] for entry in entries]
        labels.append("Rescan")
        _show_menu(labels)

        while not _stop_requested():
            inp = _poll_input()
            if inp == "back":
                return None
            if inp == "ok":
                choice = menu.menu_list[menu.menu_cursor]
                if choice.strip() == "Rescan":
                    break
                return entries[menu.menu_cursor]["ssid"]
            if inp in ("alpha", "beta"):
                keypad_state_manager(inp)
                menu.update_buffer("")
                menu_refresh.refresh(state=nav.current_state())
            elif inp is not None:
                menu.update_buffer(inp)
                menu_refresh.refresh(state=nav.current_state())
            _feed_sleep_watchdog()
            _sleep_ms(POLL_MS)
    return None


def _password_field_value(seed_text):
    seed_text = str(seed_text or "").strip()
    return (seed_text + " ") if seed_text else " "


def _prompt_wifi_password(ssid, seed_text=""):
    _show_form(
        [
            "Password:",
            "inp_0",
            "Wi-Fi Name:",
            _fit_text(ssid),
        ],
        input_value=_password_field_value(seed_text),
    )

    while not _stop_requested():
        inp = _poll_input()
        if inp == "back":
            keypad_state_manager_reset()
            return None
        if inp == "ok":
            password = form.inp_list()["inp_0"].strip()
            keypad_state_manager_reset()
            return password
        if inp in ("alpha", "beta"):
            keypad_state_manager(inp)
            form.update_buffer("")
        elif inp == "caps":
            keypad_state_manager("A")
            form.update_buffer("")
        elif inp is not None and inp != "ok":
            form.update_buffer(inp)
        form_refresh.refresh(state=nav.current_state())
        _feed_sleep_watchdog()
        _sleep_ms(POLL_MS)
    return None


def _connect_wifi(sta_if, ssid, password):
    _state_update(
        wifi_state="connect",
        wifi_ssid=ssid,
        wifi_password=password,
        wifi_connected=False,
        wifi_last_error="",
    )
    data_bucket["ssid_g"] = ssid
    data_bucket["connection_status_g"] = False

    try:
        sta_if.active(True)
    except Exception:
        pass

    try:
        if sta_if.isconnected():
            sta_if.disconnect()
            _sleep_ms(200)
    except Exception:
        pass

    try:
        if password:
            sta_if.connect(ssid, password)
        else:
            sta_if.connect(ssid)
    except Exception as exc:
        _state_update(wifi_state="error", wifi_last_error=str(exc)[:DISPLAY_COLS])
        return "fail"

    deadline = _ticks_ms() + WIFI_CONNECT_TIMEOUT_MS
    dots = 0
    next_refresh = 0

    while _ticks_diff(deadline, _ticks_ms()) > 0 and not _stop_requested():
        if sta_if.isconnected():
            _state_update(wifi_state="stress", wifi_connected=True)
            data_bucket["connection_status_g"] = True
            return "connected"

        now = _ticks_ms()
        if _ticks_diff(now, next_refresh) >= 0:
            _render_lines(
                [
                    "Connect WiFi",
                    _fit_text(ssid),
                    "Please wait" + ("." * dots),
                    "",
                    "",
                    "",
                    "",
                    "Back=cancel",
                ]
            )
            dots = (dots + 1) % 4
            next_refresh = now + STATUS_REFRESH_MS

        inp = _poll_input()
        if inp == "back":
            try:
                sta_if.disconnect()
            except Exception:
                pass
            _state_update(wifi_state="idle")
            return "back"
        _feed_sleep_watchdog()
        _sleep_ms(POLL_MS)

    try:
        sta_if.disconnect()
    except Exception:
        pass
    data_bucket["connection_status_g"] = False
    _state_update(wifi_state="error", wifi_connected=False, wifi_last_error="connect timeout")
    return "fail"


def _wifi_failure_prompt(ssid):
    lines = [
        "WiFi connect fail",
        _fit_text(ssid),
        "",
        "OK=retry pass",
        "",
        "",
        "",
        "Back=scan list",
    ]
    return "retry" if _wait_plain_screen(lines) else "scan"


def _wifi_stage_status_lines():
    snapshot = _state_snapshot()
    return [
        "WiFi stress start",
        _fit_text(snapshot["wifi_ssid"]),
        "State %s" % _wifi_state_label(snapshot["wifi_state"]),
        "s%s e%s" % (
            _short_count(snapshot["wifi_success_count"]),
            _short_count(snapshot["wifi_error_count"]),
        ),
        "Q %s" % str(snapshot["wifi_current_query"])[:16],
        "Last %s" % _format_duration_ms(snapshot["wifi_last_fetch_ms"]),
        "Wait first HTTPS OK",
        "Back=stop",
    ]


def _wait_for_wifi_stage_success():
    keypad_state_manager_reset()
    next_refresh = 0
    while not _stop_requested():
        snapshot = _state_snapshot()
        if snapshot["wifi_first_success"]:
            return True

        now = _ticks_ms()
        if _ticks_diff(now, next_refresh) >= 0:
            _render_lines(_wifi_stage_status_lines())
            next_refresh = now + STATUS_REFRESH_MS

        inp = _poll_input()
        if inp == "back":
            return False
        _feed_sleep_watchdog()
        _sleep_ms(POLL_MS)
    return False


def _wifi_stage(sta_if):
    _state_update(phase="wifi")

    while not _stop_requested():
        ssid = _select_wifi_ssid(sta_if)
        if ssid is None:
            return False

        password_seed = ""
        while not _stop_requested():
            password = _prompt_wifi_password(ssid, password_seed)
            if password is None:
                break

            result = _connect_wifi(sta_if, ssid, password)
            if result == "back":
                break
            if result == "connected":
                _start_wifi_worker()
                if not _wait_for_wifi_stage_success():
                    return False
                return _wait_plain_screen(
                    [
                        "WiFi Test OK",
                        _fit_text(ssid),
                        "HTTPS load active",
                        "OK=BLE setup",
                        "",
                        "",
                        "",
                        "Back=stop",
                    ]
                )

            password_seed = password
            if _wifi_failure_prompt(ssid) == "retry":
                continue
            break

    return False


# ----------------------------
# Wi-Fi stress worker
# ----------------------------
def _wifi_stress_worker():
    sta_if = network.WLAN(network.STA_IF)
    query_index = 0

    while not _stop_requested():
        snapshot = _state_snapshot()
        ssid = snapshot["wifi_ssid"]
        password = snapshot["wifi_password"]
        if not ssid:
            _sleep_ms(100)
            continue

        try:
            if not sta_if.active():
                sta_if.active(True)
        except Exception:
            pass

        try:
            connected = sta_if.isconnected()
        except Exception:
            connected = False

        if not connected:
            _state_update(wifi_state="reconnect", wifi_connected=False)
            try:
                if password:
                    sta_if.connect(ssid, password)
                else:
                    sta_if.connect(ssid)
            except Exception as exc:
                _state_update(wifi_state="error", wifi_last_error=str(exc)[:DISPLAY_COLS])
                _sleep_ms(WIFI_RETRY_BACKOFF_MS)
                continue

            retry_deadline = _ticks_ms() + WIFI_CONNECT_TIMEOUT_MS
            while _ticks_diff(retry_deadline, _ticks_ms()) > 0 and not _stop_requested():
                try:
                    if sta_if.isconnected():
                        connected = True
                        break
                except Exception:
                    connected = False
                _sleep_ms(100)

            if not connected:
                def _mutator(state):
                    state["wifi_error_count"] += 1
                    state["wifi_connected"] = False
                    state["wifi_state"] = "error"
                    state["wifi_last_error"] = "reconnect"
                _state_mutate(_mutator)
                _sleep_ms(WIFI_RETRY_BACKOFF_MS)
                continue

            _state_update(wifi_state="stress", wifi_connected=True, wifi_last_error="")

        molecule = WIFI_MOLECULES[query_index]
        query_index = (query_index + 1) % len(WIFI_MOLECULES)

        def _before_fetch(state):
            state["wifi_request_count"] += 1
            state["wifi_current_query"] = molecule
            state["wifi_state"] = "fetch"
        _state_mutate(_before_fetch)

        started = _ticks_ms()
        response = None
        try:
            response = urequests.get(PUBCHEM_URL_TEMPLATE % molecule, timeout=WIFI_FETCH_TIMEOUT_S)
            if response.status_code != 200:
                raise ValueError("HTTP %d" % response.status_code)
            data = response.json()
            props = data["PropertyTable"]["Properties"][0]
            if not props.get("MolecularFormula"):
                raise ValueError("missing formula")
            elapsed = _ticks_diff(_ticks_ms(), started)
            now = _ticks_ms()

            def _on_success(state):
                state["wifi_success_count"] += 1
                state["wifi_connected"] = True
                state["wifi_state"] = "ok"
                state["wifi_last_fetch_ms"] = int(elapsed)
                state["wifi_last_success_ms"] = now
                state["wifi_last_error"] = ""
                state["wifi_first_success"] = True
            _state_mutate(_on_success)
        except Exception as exc:
            def _on_error(state):
                state["wifi_error_count"] += 1
                state["wifi_connected"] = False
                state["wifi_state"] = "error"
                state["wifi_last_error"] = str(exc)[:DISPLAY_COLS]
            _state_mutate(_on_error)
            _sleep_ms(WIFI_RETRY_BACKOFF_MS)
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
            gc.collect()


def _start_wifi_worker():
    global _WIFI_THREAD_STARTED
    if _WIFI_THREAD_STARTED:
        return
    try:
        _thread.stack_size(WIFI_THREAD_STACK)
    except Exception:
        pass
    _thread.start_new_thread(_wifi_stress_worker, ())
    _WIFI_THREAD_STARTED = True


# ----------------------------
# BLE UART helper/service
# ----------------------------
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_APPEARANCE = const(0x19)
_ADV_APPEARANCE_GENERIC_COMPUTER = const(128)

_UART_UUID = bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_UART_TX = (
    bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"),
    _FLAG_READ | _FLAG_NOTIFY,
)
_UART_RX = (
    bluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E"),
    _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
)
_UART_SERVICE = (_UART_UUID, (_UART_TX, _UART_RX))


def _advertising_payload(name=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type))
        payload.extend(value)

    _append(_ADV_TYPE_FLAGS, struct.pack("B", 0x06))
    if name:
        if isinstance(name, str):
            name = name.encode()
        _append(_ADV_TYPE_NAME, name)
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))
    return payload


class BLEUARTStress:
    def __init__(self, ble, name=BLE_NAME):
        self._ble = ble
        self._connections = set()
        self._closed = False

        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._tx_handle, self._rx_handle),) = self._ble.gatts_register_services((_UART_SERVICE,))
        self._ble.gatts_set_buffer(self._rx_handle, BLE_RXBUF, True)
        self._payload = _advertising_payload(
            name=name,
            appearance=_ADV_APPEARANCE_GENERIC_COMPUTER,
        )
        self._advertise()

    def _advertise(self):
        if self._closed:
            return
        self._ble.gap_advertise(500000, adv_data=self._payload)
        _state_update(ble_state="adv", ble_last_error="")

    def _irq(self, event, data):
        if self._closed:
            return

        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)

            def _on_connect(state):
                state["ble_connected"] = True
                state["ble_state"] = "conn"
                state["ble_connection_count"] += 1
                state["ble_last_error"] = ""
            _state_mutate(_on_connect)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            if conn_handle in self._connections:
                self._connections.remove(conn_handle)

            def _on_disconnect(state):
                state["ble_connected"] = bool(self._connections)
                state["ble_state"] = "disc"
            _state_mutate(_on_disconnect)

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle != self._rx_handle or conn_handle not in self._connections:
                return
            payload = self._ble.gatts_read(self._rx_handle)
            packet_len = len(payload)

            def _on_rx(state):
                state["ble_rx_packets"] += 1
                state["ble_rx_bytes"] += packet_len
            _state_mutate(_on_rx)

    def is_connected(self):
        return bool(self._connections)

    def notify(self, payload):
        sent = 0
        for conn_handle in tuple(self._connections):
            try:
                self._ble.gatts_notify(conn_handle, self._tx_handle, payload)
                sent += 1
            except Exception:
                pass
        return sent

    def close(self):
        self._closed = True
        try:
            self._ble.gap_advertise(None)
        except Exception:
            pass
        for conn_handle in tuple(self._connections):
            try:
                self._ble.gap_disconnect(conn_handle)
            except Exception:
                pass
        self._connections.clear()
        try:
            self._ble.active(False)
        except Exception:
            pass


def _service_ble_notify(ble_uart, now_ms=None):
    global _LAST_BLE_NOTIFY_MS

    if ble_uart is None or not ble_uart.is_connected():
        return

    if now_ms is None:
        now_ms = _ticks_ms()
    if _ticks_diff(now_ms, _LAST_BLE_NOTIFY_MS) < BLE_NOTIFY_INTERVAL_MS:
        return

    def _next_seq(state):
        state["ble_notify_seq"] += 1
        return state["ble_notify_seq"]
    sequence = _state_mutate(_next_seq)
    payload = ("S%06d" % sequence).encode()
    sent = ble_uart.notify(payload)
    if sent:
        _LAST_BLE_NOTIFY_MS = now_ms

        def _on_tx(state):
            state["ble_tx_packets"] += sent
            state["ble_tx_bytes"] += len(payload) * sent
        _state_mutate(_on_tx)


def _start_ble_service():
    _state_update(phase="ble", ble_state="init")
    try:
        return BLEUARTStress(bluetooth.BLE(), name=BLE_NAME)
    except Exception as exc:
        _state_update(ble_state="error", ble_last_error=str(exc)[:DISPLAY_COLS])
        return None


def _ble_stage_lines():
    snapshot = _state_snapshot()
    return [
        "BLE advertise",
        BLE_NAME,
        "State %s" % _ble_state_label(snapshot["ble_state"]),
        "Conn %s" % _short_count(snapshot["ble_connection_count"]),
        "TX %sB/%sp" % (
            _short_count(snapshot["ble_tx_bytes"]),
            _short_count(snapshot["ble_tx_packets"]),
        ),
        "RX %sB/%sp" % (
            _short_count(snapshot["ble_rx_bytes"]),
            _short_count(snapshot["ble_rx_packets"]),
        ),
        "Phone/PC connect",
        "Back=stop",
    ]


def _ble_stage(ble_uart):
    if ble_uart is None:
        return False

    keypad_state_manager_reset()
    next_refresh = 0
    while not _stop_requested():
        snapshot = _state_snapshot()
        if snapshot["ble_connection_count"] > 0:
            break

        now = _ticks_ms()
        if _ticks_diff(now, next_refresh) >= 0:
            _render_lines(_ble_stage_lines())
            next_refresh = now + STATUS_REFRESH_MS
        _service_ble_notify(ble_uart, now)

        inp = _poll_input()
        if inp == "back":
            return False
        _feed_sleep_watchdog()
        _sleep_ms(POLL_MS)

    return _wait_plain_screen(
        [
            "BLE Test OK",
            BLE_NAME,
            "Link confirmed",
            "OK=CPU stress",
            "",
            "",
            "",
            "Back=stop",
        ],
        ble_uart=ble_uart,
    )


# ----------------------------
# CPU stress worker
# ----------------------------
def _build_cpu_matrix(seed):
    diagonal_nudge = (seed % 11) * 0.03125
    ripple = ((seed % 7) - 3) * 0.015625

    matrix = []
    for row_index in range(CPU_MATRIX_SIZE):
        row = []
        for col_index in range(CPU_MATRIX_SIZE):
            value = CPU_BASE_MATRIX[row_index][col_index]
            if row_index == col_index:
                value += diagonal_nudge
            elif ((row_index + col_index + seed) % 3) == 0:
                value += ripple
            row.append(value)
        matrix.append(row)
    return matrix


def _qr_decomposition(matrix, n):
    q = [[0.0 for _ in range(n)] for _ in range(n)]
    r = [[0.0 for _ in range(n)] for _ in range(n)]
    a = [[float(value) for value in row] for row in matrix]

    for column in range(n):
        norm = 0.0
        for row in range(n):
            norm += a[row][column] * a[row][column]
        norm = math.sqrt(norm)

        if abs(norm) < 1e-10:
            continue

        r[column][column] = norm
        for row in range(n):
            q[row][column] = a[row][column] / norm

        for next_col in range(column + 1, n):
            dot = 0.0
            for row in range(n):
                dot += a[row][next_col] * q[row][column]
            r[column][next_col] = dot
            for row in range(n):
                a[row][next_col] -= dot * q[row][column]

    return q, r


def _matrix_multiply(left, right, n):
    result = [[0.0 for _ in range(n)] for _ in range(n)]
    for row in range(n):
        for col in range(n):
            total = 0.0
            for mid in range(n):
                total += left[row][mid] * right[mid][col]
            result[row][col] = total
    return result


def _cpu_batch(seed):
    matrix = _build_cpu_matrix(seed)
    trace = 0.0
    for _ in range(CPU_QR_ITERATIONS):
        q, r = _qr_decomposition(matrix, CPU_MATRIX_SIZE)
        matrix = _matrix_multiply(r, q, CPU_MATRIX_SIZE)
        for index in range(CPU_MATRIX_SIZE):
            trace += matrix[index][index]
    return trace


def _sample_cpu_metrics():
    mem_free = gc.mem_free()
    mem_alloc = gc.mem_alloc()
    temp_c = None
    if esp32 is not None and hasattr(esp32, "mcu_temperature"):
        try:
            temp_c = int(esp32.mcu_temperature())
        except Exception:
            temp_c = None
    return mem_free, mem_alloc, temp_c


def _cpu_run_single_batch(seed, mode):
    started = _ticks_ms()
    _cpu_batch(seed)
    elapsed = max(1, _ticks_diff(_ticks_ms(), started))

    if (seed % CPU_GC_EVERY) == 0:
        gc.collect()

    mem_free, mem_alloc, temp_c = _sample_cpu_metrics()

    def _on_batch(state):
        state["cpu_state"] = "run"
        state["cpu_mode"] = mode
        state["cpu_batch_count"] += 1
        state["cpu_last_batch_ms"] = elapsed
        state["cpu_batches_per_sec"] = 1000.0 / elapsed
        state["cpu_mem_free"] = mem_free
        state["cpu_mem_alloc"] = mem_alloc
        state["cpu_temp_c"] = temp_c
        state["cpu_last_error"] = ""
    _state_mutate(_on_batch)

    return (seed + 1) % 97


def _cpu_stress_worker():
    seed = 0
    while not _stop_requested():
        try:
            seed = _cpu_run_single_batch(seed, "thread")
        except Exception as exc:
            _state_update(cpu_state="error", cpu_last_error=str(exc)[:DISPLAY_COLS])
            _sleep_ms(100)


def _start_cpu_worker():
    global _CPU_THREAD_REQUESTED, _CPU_THREAD_STARTED, _CPU_INLINE_FALLBACK

    if _CPU_THREAD_REQUESTED:
        return _CPU_THREAD_STARTED
    _CPU_THREAD_REQUESTED = True

    try:
        _thread.stack_size(CPU_THREAD_STACK)
    except Exception:
        pass
    try:
        _thread.start_new_thread(_cpu_stress_worker, ())
        _CPU_THREAD_STARTED = True
        _CPU_INLINE_FALLBACK = False
        _state_update(cpu_state="run", cpu_mode="thread", cpu_last_error="")
        return True
    except Exception as exc:
        _CPU_THREAD_STARTED = False
        _CPU_INLINE_FALLBACK = True
        _state_update(
            cpu_state="run",
            cpu_mode="inline",
            cpu_last_error=str(exc)[:DISPLAY_COLS],
        )
        return False


# ----------------------------
# staged controller / main loop
# ----------------------------
def _cleanup(ble_uart, sta_if):
    global _WIFI_THREAD_STARTED, _CPU_THREAD_STARTED
    global _CPU_THREAD_REQUESTED, _CPU_INLINE_FALLBACK
    global _LAST_BLE_NOTIFY_MS, _KEY_HELD, _LAST_KEY_MS

    _request_stop()
    _sleep_ms(150)

    if ble_uart is not None:
        try:
            ble_uart.close()
        except Exception:
            pass

    if sta_if is not None:
        try:
            if sta_if.isconnected():
                sta_if.disconnect()
        except Exception:
            pass
        try:
            sta_if.active(False)
        except Exception:
            pass

    data_bucket["connection_status_g"] = False
    data_bucket["ssid_g"] = ""
    _WIFI_THREAD_STARTED = False
    _CPU_THREAD_STARTED = False
    _CPU_THREAD_REQUESTED = False
    _CPU_INLINE_FALLBACK = False
    _LAST_BLE_NOTIFY_MS = 0
    _KEY_HELD = None
    _LAST_KEY_MS = 0
    _state_update(
        wifi_connected=False,
        wifi_ssid="",
        wifi_password="",
        ble_connected=False,
        ble_state="idle",
        cpu_state="idle",
        cpu_mode="thread",
    )
    keypad_state_manager_reset()
    _feed_sleep_watchdog()
    try:
        display.clear_display()
    except Exception:
        pass


def _run_dashboard_loop(ble_uart):
    _state_update(phase="run")
    next_refresh = 0
    inline_seed = 0

    while not _stop_requested():
        now = _ticks_ms()
        _persist_cpu_run()
        if _ticks_diff(now, next_refresh) >= 0:
            _render_dashboard()
            next_refresh = now + DASHBOARD_REFRESH_MS

        _service_ble_notify(ble_uart, now)

        if _CPU_INLINE_FALLBACK:
            try:
                inline_seed = _cpu_run_single_batch(inline_seed, "inline")
            except Exception as exc:
                _state_update(cpu_state="error", cpu_last_error=str(exc)[:DISPLAY_COLS])
                _sleep_ms(50)

        inp = _poll_input()
        if inp == "back":
            return

        _feed_sleep_watchdog()
        _sleep_ms(POLL_MS)


def stress(db={}):
    ble_uart = None
    sta_if = None

    try:
        _ensure_display_ready()
        keypad_state_manager_reset()
        _reset_state()
        _apply_loaded_run_store()
        _feed_sleep_watchdog()

        if not _history_gate():
            return

        sta_if = network.WLAN(network.STA_IF)

        if not _wifi_stage(sta_if):
            return

        ble_uart = _start_ble_service()
        if ble_uart is None:
            _wait_plain_screen(
                [
                    "BLE init failed",
                    _fit_text(_state_snapshot().get("ble_last_error", "")),
                    "",
                    "OK=return",
                    "",
                    "",
                    "",
                    "Back=return",
                ]
            )
            return

        if not _ble_stage(ble_uart):
            return

        _begin_cpu_run_session()
        _start_cpu_worker()
        _run_dashboard_loop(ble_uart)

    except Exception as exc:
        try:
            sys.print_exception(exc)
        except Exception:
            pass
        _state_update(phase="error")
        _wait_plain_screen(
            [
                "Stress error",
                _fit_text(str(exc)),
                "",
                "OK=return",
                "",
                "",
                "",
                "Back=return",
            ],
            ble_uart=ble_uart,
        )
    finally:
        _persist_cpu_run(force=True, closing=True)
        _cleanup(ble_uart, sta_if)


if __name__ == "__main__":
    stress()
