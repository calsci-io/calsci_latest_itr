import st7565 as display

try:
    import tools

    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import utime as time  # type: ignore

try:
    import ujson as json  # type: ignore
except Exception:
    import json  # type: ignore

try:
    import usocket as socket  # type: ignore
except Exception:
    import socket  # type: ignore

try:
    import network  # type: ignore
except Exception:
    network = None

from data_modules.object_handler import (
    app,
    data_bucket,
    form,
    form_refresh,
    keyin,
    keymap,
    keypad_state_manager,
    menu,
    menu_refresh,
    nav,
    text,
    text_refresh,
    typer,
)

STREAM_CONFIG_PATHS = ("/db/stream_deck.json", "db/stream_deck.json")
DEFAULT_CONFIG = {
    "server_ip": "",
    "server_port": 4545,
    "timeout_ms": 700,
    "secret": "",
    "ble_name": "CalSci Nav",
}
TEXT_COLS = 21
TEXT_ROWS = int(getattr(text, "rows", 8))

HID_KEY_ENTER = 0x28
HID_KEY_BACKSPACE = 0x2A
HID_KEY_ESCAPE = 0x29
HID_KEY_RIGHT = 0x4F
HID_KEY_LEFT = 0x50
HID_KEY_DOWN = 0x51
HID_KEY_UP = 0x52

BLE_NAV_KEYMAP = {
    "nav_u": (HID_KEY_UP, "UP"),
    "nav_d": (HID_KEY_DOWN, "DOWN"),
    "nav_l": (HID_KEY_LEFT, "LEFT"),
    "nav_r": (HID_KEY_RIGHT, "RIGHT"),
    "ok": (HID_KEY_ENTER, "ENTER"),
    "nav_b": (HID_KEY_BACKSPACE, "BACK"),
    "back": (HID_KEY_ESCAPE, "ESC"),
}


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def _ble_imports():
    try:
        from hid_services import Keyboard  # type: ignore
    except Exception as err:
        return None, None, None, "hid_services import failed: " + str(err)

    try:
        from hid_keystores import NVSKeyStore, JSONKeyStore  # type: ignore
    except Exception:
        NVSKeyStore = None
        JSONKeyStore = None

    return Keyboard, NVSKeyStore, JSONKeyStore, ""


def _ble_keyboard_name(cfg):
    name = str(cfg.get("ble_name", "")).strip()
    return name if name else DEFAULT_CONFIG["ble_name"]


def _ble_state_label(keyboard):
    try:
        state = keyboard.get_state()
    except Exception:
        return "unknown"

    try:
        if state is keyboard.DEVICE_CONNECTED:
            return "connected"
        if state is keyboard.DEVICE_ADVERTISING:
            return "advertising"
        if state is keyboard.DEVICE_IDLE:
            return "idle"
    except Exception:
        pass
    return "unknown"


def _ble_start_keyboard(cfg):
    Keyboard, NVSKeyStore, JSONKeyStore, err = _ble_imports()
    if Keyboard is None:
        return None, err

    try:
        keyboard = Keyboard(_ble_keyboard_name(cfg))
    except Exception as err:
        return None, "Keyboard init failed: " + str(err)

    try:
        if NVSKeyStore is not None:
            keyboard.set_keystore(NVSKeyStore())
        elif JSONKeyStore is not None:
            keyboard.set_keystore(JSONKeyStore())
    except Exception:
        pass

    try:
        keyboard.start()
    except Exception as err:
        return None, "BLE start failed: " + str(err)

    try:
        keyboard.start_advertising()
    except Exception:
        pass

    return keyboard, ""


def _ble_send_keypress(keyboard, keycode, hold_ms=12):
    try:
        keyboard.set_keys(keycode)
        keyboard.notify_hid_report()
        _sleep_ms(hold_ms)
        keyboard.set_keys()
        keyboard.set_modifiers()
        keyboard.notify_hid_report()
        return True
    except Exception:
        return False


def _line_fit(text_value):
    line = str(text_value)
    if len(line) > TEXT_COLS:
        line = line[: TEXT_COLS - 1] + "~"
    if len(line) < TEXT_COLS:
        line += " " * (TEXT_COLS - len(line))
    return line


def _render_stream_screen(lines, state="Deck"):
    payload = ""
    rows = lines[:TEXT_ROWS]
    for row in rows:
        payload += _line_fit(row)
    if len(rows) < TEXT_ROWS:
        payload += " " * ((TEXT_ROWS - len(rows)) * TEXT_COLS)

    text.all_clear()
    text.update_buffer(payload)
    try:
        text.menu_buffer_cursor = max(0, (TEXT_ROWS * TEXT_COLS) - 1)
        text.display_buffer_position = 0
        text.refresh_area = (0, TEXT_ROWS * TEXT_COLS)
    except Exception:
        pass
    text_refresh.new = True
    text_refresh.refresh(state=state)


def _show_menu(lines, state=None):
    display.clear_display()
    cols = int(getattr(menu, "cols", 21))
    if cols < 1:
        cols = 1
    safe_lines = []
    for row in lines:
        row_s = str(row)
        if len(row_s) > cols:
            row_s = row_s[: cols - 1] + "~" if cols > 1 else row_s[:1]
        safe_lines.append(row_s)
    menu.menu_list = safe_lines
    menu.update()
    menu_refresh.refresh(state=state if state is not None else nav.current_state())


def _show_form(state=None):
    display.clear_display()
    form_refresh.refresh(state=state if state is not None else nav.current_state())


def _toast(lines, hold_ms=900):
    _show_menu(lines)
    _sleep_ms(hold_ms)


def _load_stream_config():
    cfg = dict(DEFAULT_CONFIG)
    loaded = None

    for path in STREAM_CONFIG_PATHS:
        try:
            with open(path, "r") as file:
                loaded = json.load(file)
                break
        except Exception:
            continue

    if isinstance(loaded, dict):
        for key, value in loaded.items():
            cfg[key] = value

    cfg["server_ip"] = str(cfg.get("server_ip", "")).strip()

    try:
        cfg["server_port"] = int(cfg.get("server_port", DEFAULT_CONFIG["server_port"]))
    except Exception:
        cfg["server_port"] = DEFAULT_CONFIG["server_port"]
    if cfg["server_port"] < 1 or cfg["server_port"] > 65535:
        cfg["server_port"] = DEFAULT_CONFIG["server_port"]

    try:
        cfg["timeout_ms"] = int(cfg.get("timeout_ms", DEFAULT_CONFIG["timeout_ms"]))
    except Exception:
        cfg["timeout_ms"] = DEFAULT_CONFIG["timeout_ms"]
    if cfg["timeout_ms"] < 100:
        cfg["timeout_ms"] = 100
    if cfg["timeout_ms"] > 5000:
        cfg["timeout_ms"] = 5000

    cfg["secret"] = str(cfg.get("secret", ""))
    return cfg


def _save_stream_config(cfg):
    payload = json.dumps(cfg)
    for path in STREAM_CONFIG_PATHS:
        try:
            with open(path, "w") as file:
                file.write(payload)
            return True
        except Exception:
            continue
    return False


def _is_wifi_connected():
    if network is None:
        return bool(data_bucket.get("connection_status_g", False))

    try:
        sta_if = network.WLAN(network.STA_IF)
        return bool(sta_if.isconnected())
    except Exception:
        return bool(data_bucket.get("connection_status_g", False))


def _prompt_value(label, default_value="", save_label="Save"):
    value = str(default_value)
    if not value:
        value = " "

    form.input_list = {"inp_0": value}
    form.form_list = [label, "inp_0", save_label, "Cancel"]
    form.update()
    form.menu_cursor = 1
    form.display_cursor = 1
    form.input_cursor = len(value) if value != " " else 0
    form.input_display_position = 0
    _show_form(state=nav.current_state())

    while True:
        inp = typer.start_typing()
        if inp == "ok":
            current_line = form.form_list[form.menu_cursor]
            if current_line == "Cancel":
                return None
            if current_line == save_label:
                raw_value = str(form.inp_list().get("inp_0", " "))
                return raw_value[:-1] if raw_value.endswith(" ") else raw_value
        elif inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            form.update_buffer("")
        elif inp == "caps":
            keypad_state_manager(x="A")
            form.update_buffer("")
        else:
            form.update_buffer(inp)

        form_refresh.refresh(state=nav.current_state())


def _read_key_raw():
    delay_ms = int(typer.debounce_delay() * 1000)
    if delay_ms > 0:
        _sleep_ms(delay_ms)

    key_inp = keyin.keypad_loop(idle_callback=nav.maybe_hide)
    col = int(key_inp[0])
    row = int(key_inp[1])
    layer_before = str(getattr(keymap, "state", "d"))
    key_name = keymap.key_out(col=col, row=row)

    if key_name == "alpha" or key_name == "beta":
        keypad_state_manager(x=key_name)
    elif key_name == "caps":
        keypad_state_manager(x="A")

    layer_after = str(getattr(keymap, "state", "d"))
    return str(key_name), layer_before, layer_after


def _server_host_port(cfg):
    host = str(cfg.get("server_ip", "")).strip()
    try:
        port = int(cfg.get("server_port", DEFAULT_CONFIG["server_port"]))
    except Exception:
        port = int(DEFAULT_CONFIG["server_port"])
    return host, port


def _create_udp_socket(timeout_ms):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except Exception as err:
        return None, str(err)

    try:
        timeout_sec = int(timeout_ms) / 1000.0
        sock.settimeout(timeout_sec)
    except Exception:
        pass
    return sock, ""


def _probe_server(sock, cfg):
    host, port = _server_host_port(cfg)
    payload = {"type": "ping", "device": "calsci"}
    secret = str(cfg.get("secret", ""))
    if secret:
        payload["secret"] = secret

    try:
        sock.sendto(json.dumps(payload).encode(), (host, port))
    except Exception as err:
        return False, "Send failed", str(err)

    try:
        data, _ = sock.recvfrom(768)
    except Exception as err:
        return False, "No reply", str(err)

    try:
        response = json.loads(data.decode())
    except Exception as err:
        return False, "Bad reply", str(err)

    if isinstance(response, dict):
        action = str(response.get("action", "reply received"))
        detail = str(response.get("detail", ""))
        return True, action, detail
    return False, "Bad reply", "non-json-dict"


def _test_connection(cfg):
    if not _is_wifi_connected():
        _toast(["Wi-Fi not connected", "Use Wi-Fi Center"], hold_ms=1100)
        return

    host, port = _server_host_port(cfg)
    if not host:
        _toast(["Set server IP first"], hold_ms=1000)
        return

    _render_stream_screen(
        [
            "Testing connection",
            "Host: " + host,
            "Port: " + str(port),
            "",
            "Sending probe...",
            "",
            "",
        ],
        state="Deck",
    )

    sock, socket_err = _create_udp_socket(cfg.get("timeout_ms", 700))
    if sock is None:
        _render_stream_screen(
            [
                "Test failed",
                "Socket init error",
                socket_err,
                "",
                "",
                "",
                "",
            ],
            state="ERR",
        )
        _sleep_ms(1400)
        return

    try:
        ok, action, detail = _probe_server(sock, cfg)
    finally:
        try:
            sock.close()
        except Exception:
            pass

    status = "OK" if ok else "ERR"
    line_3 = "Reply received" if ok else "No server reply"
    line_4 = "Action: " + action
    line_5 = detail if detail else ("Connection looks good" if ok else "Check server/firewall")

    _render_stream_screen(
        [
            "Connection test",
            "Host: " + host,
            "Port: " + str(port),
            line_3,
            line_4,
            line_5,
            "",
        ],
        state=status,
    )
    _sleep_ms(1600)


def _send_key_event(sock, cfg, key_name, layer_before, layer_after):
    host, port = _server_host_port(cfg)

    payload = {
        "type": "key_event",
        "device": "calsci",
        "key": key_name,
        "layer": layer_before,
        "layer_after": layer_after,
    }
    secret = str(cfg.get("secret", ""))
    if secret:
        payload["secret"] = secret

    try:
        sock.sendto(json.dumps(payload).encode(), (host, port))
    except Exception as err:
        return False, "Send failed", str(err)

    try:
        data, _ = sock.recvfrom(768)
    except Exception as err:
        return False, "No reply", str(err)

    try:
        response = json.loads(data.decode())
    except Exception as err:
        return False, "Bad reply", str(err)

    action = str(response.get("action", "No action"))
    detail = str(response.get("detail", ""))
    ok = bool(response.get("ok", False))
    return ok, action, detail


def _stream_mode(cfg):
    if not _is_wifi_connected():
        _toast(["Wi-Fi not connected", "Use Wi-Fi Center"], hold_ms=1000)
        return

    host, port = _server_host_port(cfg)
    if not host:
        _toast(["Set server IP first"], hold_ms=1000)
        return

    sock, socket_err = _create_udp_socket(cfg.get("timeout_ms", 700))
    if sock is None:
        _toast(["Socket error", socket_err], hold_ms=1200)
        return

    _render_stream_screen(
        [
            "Stream deck active",
            "Host: " + host,
            "Port: " + str(port),
            "Press keys to send",
            "lock = exit mode",
            "",
            "Waiting...",
        ],
        state="Deck",
    )

    try:
        while True:
            key_name, layer_before, layer_after = _read_key_raw()

            if key_name == "lock":
                _render_stream_screen(
                    [
                        "Stream deck closed",
                        "Returning to menu",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ],
                    state="Deck",
                )
                _sleep_ms(450)
                return

            ok, action, detail = _send_key_event(
                sock, cfg, key_name, layer_before, layer_after
            )
            key_label = layer_before + ":" + key_name
            status_label = "OK" if ok else "ERR"
            _render_stream_screen(
                [
                    "Stream deck active",
                    "Host: " + host,
                    "Port: " + str(port),
                    "Key: " + key_label,
                    "Action: " + action,
                    detail,
                    "lock = exit mode",
                ],
                state=status_label,
            )
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _ble_nav_mode(cfg):
    keyboard, err = _ble_start_keyboard(cfg)
    if keyboard is None:
        _render_stream_screen(
            ["Bluetooth HID error", err, "", "", "", "", ""], state="ERR"
        )
        _sleep_ms(1500)
        return

    ble_name = _ble_keyboard_name(cfg)
    _render_stream_screen(
        [
            "Bluetooth nav keys",
            "Name: " + ble_name,
            "Pair on your PC",
            "Status: " + _ble_state_label(keyboard),
            "Use nav/ok/back",
            "lock = exit mode",
            "",
        ],
        state="BLE",
    )

    try:
        while True:
            key_name, layer_before, layer_after = _read_key_raw()

            if key_name == "lock":
                _render_stream_screen(
                    [
                        "Bluetooth nav keys",
                        "Stream deck closed",
                        "Returning to menu",
                        "",
                        "",
                        "",
                        "",
                    ],
                    state="BLE",
                )
                _sleep_ms(450)
                return

            try:
                if keyboard.get_state() is keyboard.DEVICE_IDLE:
                    keyboard.start_advertising()
            except Exception:
                pass

            try:
                if keyboard.get_state() is not keyboard.DEVICE_CONNECTED:
                    _render_stream_screen(
                        [
                            "Bluetooth nav keys",
                            "Not connected",
                            "Status: " + _ble_state_label(keyboard),
                            "Pair on your PC",
                            "Press nav keys",
                            "lock = exit mode",
                            "",
                        ],
                        state="BLE",
                    )
                    continue
            except Exception:
                pass

            mapped = BLE_NAV_KEYMAP.get(key_name)
            if mapped is None:
                _render_stream_screen(
                    [
                        "Bluetooth nav keys",
                        "Unmapped key",
                        "Key: " + str(key_name),
                        "Use nav/ok/back",
                        "lock = exit mode",
                        "",
                        "",
                    ],
                    state="BLE",
                )
                continue

            keycode, label = mapped
            ok = _ble_send_keypress(keyboard, keycode)
            status_label = "OK" if ok else "ERR"
            detail = "Sent" if ok else "Send failed"
            _render_stream_screen(
                [
                    "Bluetooth nav keys",
                    "Key: " + str(key_name) + "->" + str(label),
                    "Status: " + _ble_state_label(keyboard),
                    detail,
                    "",
                    "lock = exit mode",
                    "",
                ],
                state=status_label,
            )
    finally:
        try:
            keyboard.stop_advertising()
        except Exception:
            pass
        try:
            keyboard.stop()
        except Exception:
            pass


def stream_deck(db={}):
    while True:
        cfg = _load_stream_config()
        secret_label = "set" if str(cfg.get("secret", "")) else "none"
        ble_name = _ble_keyboard_name(cfg)
        options = [
            ("start", "Start Wi-Fi Stream Deck"),
            ("ble", "Start Bluetooth Nav Keys"),
            ("test", "Test Connection"),
            ("ip", "Server IP: " + (cfg["server_ip"] or "<unset>")),
            ("port", "Server Port: " + str(cfg["server_port"])),
            ("timeout", "Reply Timeout: " + str(cfg["timeout_ms"])),
            ("secret", "Shared Secret: " + secret_label),
            ("ble_name", "BLE Name: " + ble_name),
            ("back", "Back to Home"),
        ]

        _show_menu([row[1] for row in options], state=nav.current_state())

        while True:
            inp = typer.start_typing()
            if inp == "ok":
                action = options[menu.menu_cursor][0]

                if action == "start":
                    _stream_mode(cfg)
                    break

                if action == "ble":
                    _ble_nav_mode(cfg)
                    break

                if action == "test":
                    _test_connection(cfg)
                    break

                if action == "ip":
                    new_ip = _prompt_value("Server IP", cfg["server_ip"], save_label="Save")
                    if new_ip is not None:
                        cfg["server_ip"] = new_ip.strip()
                        if _save_stream_config(cfg):
                            _toast(["Server IP saved"], hold_ms=700)
                        else:
                            _toast(["Save failed"], hold_ms=700)
                    break

                if action == "port":
                    new_port = _prompt_value(
                        "Server Port", str(cfg["server_port"]), save_label="Save"
                    )
                    if new_port is not None:
                        try:
                            port = int(new_port.strip())
                            if port < 1 or port > 65535:
                                raise ValueError("port out of range")
                            cfg["server_port"] = port
                            if _save_stream_config(cfg):
                                _toast(["Port saved"], hold_ms=700)
                            else:
                                _toast(["Save failed"], hold_ms=700)
                        except Exception:
                            _toast(["Invalid port"], hold_ms=900)
                    break

                if action == "timeout":
                    new_timeout = _prompt_value(
                        "Timeout ms", str(cfg["timeout_ms"]), save_label="Save"
                    )
                    if new_timeout is not None:
                        try:
                            timeout_ms = int(new_timeout.strip())
                            if timeout_ms < 100 or timeout_ms > 5000:
                                raise ValueError("timeout out of range")
                            cfg["timeout_ms"] = timeout_ms
                            if _save_stream_config(cfg):
                                _toast(["Timeout saved"], hold_ms=700)
                            else:
                                _toast(["Save failed"], hold_ms=700)
                        except Exception:
                            _toast(["Use 100..5000"], hold_ms=900)
                    break

                if action == "secret":
                    new_secret = _prompt_value(
                        "Secret (optional)", cfg["secret"], save_label="Save"
                    )
                    if new_secret is not None:
                        cfg["secret"] = new_secret
                        if _save_stream_config(cfg):
                            _toast(["Secret saved"], hold_ms=700)
                        else:
                            _toast(["Save failed"], hold_ms=700)
                    break

                if action == "ble_name":
                    new_name = _prompt_value("BLE Name", ble_name, save_label="Save")
                    if new_name is not None:
                        cfg["ble_name"] = new_name.strip()
                        if _save_stream_config(cfg):
                            _toast(["BLE name saved"], hold_ms=700)
                        else:
                            _toast(["Save failed"], hold_ms=700)
                    break

                if action == "back":
                    app.set_app_name("home")
                    app.set_group_name("root")
                    return

            elif inp == "alpha" or inp == "beta":
                keypad_state_manager(x=inp)
                menu.update_buffer("")
            else:
                menu.update_buffer(inp)

            menu_refresh.refresh(state=nav.current_state())
