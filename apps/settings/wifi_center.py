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
import network  # type: ignore
import json
from tinydb import TinyDB, Query
from data_modules.object_handler import (
    app,
    data_bucket,
    display,
    form,
    form_refresh,
    keypad_state_manager,
    menu,
    menu_refresh,
    nav,
    typer,
)

WIFI_PASSWORD_DATA = "/db/wifi.json"
SETTINGS_DB_PATH = "db/settings.json"

sta_if = network.WLAN(network.STA_IF)
settings_db = TinyDB(SETTINGS_DB_PATH)
settings_q = Query()


def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except Exception:
        time.sleep(ms / 1000)


def _read_saved_wifi():
    try:
        with open(WIFI_PASSWORD_DATA, "r") as file:
            data = json.load(file)
            if isinstance(data, list):
                out = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    ssid = str(item.get("ssid", "")).strip()
                    if not ssid:
                        continue
                    out.append(
                        {
                            "ssid": ssid,
                            "password": str(item.get("password", "")),
                        }
                    )
                return out
    except Exception:
        pass
    return []


def _write_saved_wifi(data):
    with open(WIFI_PASSWORD_DATA, "w") as file:
        json.dump(data, file)


def _get_saved_password(ssid):
    for item in _read_saved_wifi():
        if item["ssid"] == ssid:
            return item["password"]
    return ""


def _upsert_saved_wifi(ssid, password):
    ssid = str(ssid).strip()
    password = str(password)
    data = _read_saved_wifi()

    for item in data:
        if item["ssid"] == ssid:
            item["password"] = password
            _write_saved_wifi(data)
            return

    data.append({"ssid": ssid, "password": password})
    _write_saved_wifi(data)


def _clear_saved_wifi():
    _write_saved_wifi([])


def _forget_saved_ssid(ssid):
    ssid = str(ssid).strip()
    data = _read_saved_wifi()
    filtered = [item for item in data if item["ssid"] != ssid]
    _write_saved_wifi(filtered)
    return len(filtered) != len(data)


def _auto_connect_enabled():
    row = settings_db.search(settings_q.feature == "auto_wifi_connect")
    if row:
        return bool(row[0].get("value"))
    return False


def _set_auto_connect(enabled):
    settings_db.update({"value": bool(enabled)}, settings_q.feature == "auto_wifi_connect")
    return bool(enabled)


def _current_ssid():
    if not sta_if.isconnected():
        return ""
    try:
        ssid = sta_if.config("essid")
        if isinstance(ssid, str):
            return ssid
    except Exception:
        pass
    return str(data_bucket.get("ssid_g", "")).strip()


def _sync_connection_state():
    connected = bool(sta_if.isconnected())
    data_bucket["connection_status_g"] = connected
    if connected:
        data_bucket["ssid_g"] = _current_ssid()
    else:
        data_bucket["ssid_g"] = ""
    return connected, data_bucket["ssid_g"]


def _scan_networks():
    sta_if.active(True)
    try:
        scanned = sta_if.scan()
    except Exception:
        return []

    seen = set()
    results = []
    for net in scanned:
        try:
            raw_ssid = net[0]
            ssid = raw_ssid.decode() if isinstance(raw_ssid, bytes) else str(raw_ssid)
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            rssi = net[3] if len(net) > 3 else None
            results.append((ssid, rssi))
        except Exception:
            continue

    results.sort(key=lambda item: item[1] if isinstance(item[1], int) else -999, reverse=True)
    return results


def _show_menu(lines, state="Wi-Fi"):
    display.clear_display()
    cols = int(getattr(menu, "cols", 21))
    if cols < 1:
        cols = 1
    safe_lines = []
    for line in lines:
        line_s = str(line)
        if len(line_s) > cols:
            line_s = line_s[: cols - 1] + "~" if cols > 1 else line_s[:1]
        safe_lines.append(line_s)
    menu.menu_list = safe_lines
    menu.update()
    menu_refresh.refresh(state=state)


def _show_form(state="Wi-Fi"):
    display.clear_display()
    form_refresh.refresh(state=state)


def _toast(lines, hold_ms=900):
    _show_menu(lines)
    _sleep_ms(hold_ms)


def _disconnect_wifi():
    try:
        if sta_if.isconnected():
            sta_if.disconnect()
    except Exception:
        pass
    _sync_connection_state()


def _connect_to_wifi(ssid, password, timeout_s=8):
    ssid = str(ssid).strip()
    password = str(password)
    sta_if.active(True)

    if sta_if.isconnected():
        if _current_ssid() == ssid:
            _sync_connection_state()
            return True
        try:
            sta_if.disconnect()
            _sleep_ms(250)
        except Exception:
            pass

    try:
        sta_if.connect(ssid, password)
    except Exception:
        _sync_connection_state()
        return False

    retries = int(timeout_s * 10)
    for _ in range(retries):
        if sta_if.isconnected():
            break
        _sleep_ms(100)

    connected, connected_ssid = _sync_connection_state()
    if connected and connected_ssid and connected_ssid != ssid:
        return False
    return connected


def _select_network():
    while True:
        _show_menu(["Scanning Wi-Fi...", "Please wait"])
        scanned = _scan_networks()

        options = [("rescan", "Rescan Networks"), ("cancel", "Cancel")]
        if scanned:
            for ssid, rssi in scanned:
                label = ssid if rssi is None else "%s (%sdBm)" % (ssid, rssi)
                options.append(("ssid", label, ssid))
        else:
            options.append(("empty", "No networks found"))

        _show_menu([row[1] for row in options], state=nav.current_state())

        while True:
            inp = typer.start_typing()
            if inp == "ok":
                chosen = options[menu.menu_cursor]
                action = chosen[0]
                if action == "rescan":
                    break
                if action == "cancel":
                    return None
                if action == "ssid":
                    return chosen[2]
                if action == "empty":
                    break
            elif inp == "alpha" or inp == "beta":
                keypad_state_manager(x=inp)
                menu.update_buffer("")
            else:
                menu.update_buffer(inp)
            menu_refresh.refresh(state=nav.current_state())


def _prompt_password(ssid, default_password="", action_label="Connect"):
    pwd = str(default_password)
    if not pwd:
        pwd = " "

    form.input_list = {"inp_0": pwd}
    form.form_list = ["SSID:", ssid, "Password:", "inp_0", action_label, "Cancel"]
    form.update()
    form.menu_cursor = 3
    form.display_cursor = 3
    form.input_cursor = len(pwd) if pwd != " " else 0
    form.input_display_position = 0
    _show_form(state=nav.current_state())

    while True:
        inp = typer.start_typing()
        if inp == "ok":
            current_line = form.form_list[form.menu_cursor]
            if current_line == "Cancel":
                return None

            raw_pwd = str(form.inp_list().get("inp_0", " "))
            password = raw_pwd[:-1] if raw_pwd.endswith(" ") else raw_pwd
            return password

        if inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            form.update_buffer("")
        elif inp == "caps":
            keypad_state_manager(x="A")
            form.update_buffer("")
        else:
            form.update_buffer(inp)

        form_refresh.refresh(state=nav.current_state())


def _saved_network_detail_flow(ssid):
    while True:
        password = _get_saved_password(ssid)
        password_view = password if password else "<empty>"

        options = [
            ("ssid", "SSID: " + ssid),
            ("pwd", "Password: " + password_view),
            ("connect", "Connect"),
            ("edit", "Edit Password"),
            ("forget", "Forget Network"),
            ("back", "Back"),
        ]
        _show_menu([row[1] for row in options], state=nav.current_state())

        while True:
            inp = typer.start_typing()
            if inp == "ok":
                detail_action = options[menu.menu_cursor][0]

                if detail_action == "ssid":
                    _toast(["SSID", ssid], hold_ms=900)
                    break
                if detail_action == "pwd":
                    _toast(["Password", password_view], hold_ms=1000)
                    break
                if detail_action == "connect":
                    _show_menu(["Connecting to:", ssid])
                    if _connect_to_wifi(ssid, password):
                        _toast(["Connected:", ssid], hold_ms=900)
                    else:
                        _toast(["Failed to connect", ssid], hold_ms=900)
                    break
                if detail_action == "edit":
                    new_password = _prompt_password(ssid, password, action_label="Save")
                    if new_password is not None:
                        _upsert_saved_wifi(ssid, new_password)
                        _toast(["Password saved", ssid], hold_ms=700)
                    break
                if detail_action == "forget":
                    _forget_saved_ssid(ssid)
                    _toast(["Network removed", ssid], hold_ms=700)
                    return
                if detail_action == "back":
                    return

            elif inp == "alpha" or inp == "beta":
                keypad_state_manager(x=inp)
                menu.update_buffer("")
            else:
                menu.update_buffer(inp)
            menu_refresh.refresh(state=nav.current_state())


def _saved_networks_flow():
    while True:
        saved = _read_saved_wifi()
        if not saved:
            _toast(["Saved Networks", "No saved Wi-Fi"], hold_ms=800)
            return

        options = [("clear", "Forget All"), ("cancel", "Back")]
        for row in saved:
            options.append(("ssid", row["ssid"], row["ssid"]))

        _show_menu([row[1] for row in options], state=nav.current_state())

        while True:
            inp = typer.start_typing()
            if inp == "ok":
                chosen = options[menu.menu_cursor]
                action = chosen[0]
                if action == "clear":
                    _clear_saved_wifi()
                    _toast(["Saved Networks", "All removed"], hold_ms=700)
                    break
                if action == "cancel":
                    return
                if action == "ssid":
                    ssid = chosen[2]
                    _saved_network_detail_flow(ssid)
                    break
            elif inp == "alpha" or inp == "beta":
                keypad_state_manager(x=inp)
                menu.update_buffer("")
            else:
                menu.update_buffer(inp)
            menu_refresh.refresh(state=nav.current_state())


def wifi_center(db={}):
    sta_if.active(True)
    _sync_connection_state()

    while True:
        connected, ssid = _sync_connection_state()
        auto_label = "ON" if _auto_connect_enabled() else "OFF"
        saved_count = len(_read_saved_wifi())

        options = [
            ("status", "Status: " + ("Connected" if connected else "Offline")),
            ("ssid", "SSID: " + (ssid if ssid else "-")),
            ("connect", "Connect / Switch Wi-Fi"),
            ("disconnect", "Disconnect Wi-Fi" + ("" if connected else " (N/A)")),
            ("toggle_auto", "Auto-connect: " + auto_label),
            ("saved", "Saved Networks: " + str(saved_count)),
            ("back", "Back to Settings"),
        ]

        _show_menu([row[1] for row in options], state=nav.current_state())

        while True:
            inp = typer.start_typing()
            if inp == "ok":
                action = options[menu.menu_cursor][0]

                if action == "status":
                    _toast(["Wi-Fi", "Connected" if connected else "Offline"], hold_ms=700)
                    break
                elif action == "ssid":
                    _toast(["Current SSID", ssid if ssid else "-"], hold_ms=700)
                    break
                elif action == "connect":
                    selected_ssid = _select_network()
                    if selected_ssid:
                        preset = _get_saved_password(selected_ssid)
                        password = _prompt_password(selected_ssid, preset)
                        if password is not None:
                            _show_menu(["Connecting to:", selected_ssid])
                            ok = _connect_to_wifi(selected_ssid, password)
                            if ok:
                                _upsert_saved_wifi(selected_ssid, password)
                                _toast(["Connected:", selected_ssid], hold_ms=900)
                            else:
                                _toast(["Connection failed", selected_ssid], hold_ms=900)
                    break
                elif action == "disconnect":
                    if connected:
                        _disconnect_wifi()
                        _toast(["Wi-Fi disconnected"], hold_ms=700)
                    else:
                        _toast(["No active Wi-Fi"], hold_ms=700)
                    break
                elif action == "toggle_auto":
                    new_state = _set_auto_connect(not _auto_connect_enabled())
                    _toast(["Auto-connect", "ON" if new_state else "OFF"], hold_ms=700)
                    break
                elif action == "saved":
                    _saved_networks_flow()
                    break
                elif action == "back":
                    app.set_app_name("settings")
                    app.set_group_name("root")
                    return
            elif inp == "alpha" or inp == "beta":
                keypad_state_manager(x=inp)
                menu.update_buffer("")
            else:
                menu.update_buffer(inp)
            menu_refresh.refresh(state=nav.current_state())
