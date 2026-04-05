import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import network # type: ignore
from data_modules.object_handler import nav, keypad_state_manager, menu, menu_refresh, form, form_refresh, typer, display
import time
from data_modules.object_handler import current_app, data_bucket, app
import json
import machine

wifi_password_data = "/db/wifi.json"

connection_status = False
sta_if = network.WLAN(network.STA_IF)



if not sta_if.active():
    sta_if.active(True)
    time.sleep(1)
try:
    sta_if.config(pm=0)
except Exception:
    pass

def display_error_message(ssid):
    display.clear_display()
    menu.menu_list=["Failed to connect to:", ssid]
    menu.update()
    menu_refresh.refresh()


    while True:
        error_inp = typer.start_typing()
        # if error_inp:
        current_app[0]="settings"
        current_app[1]="application_modules"
        break

def display_ip_addresses(ssid):
    ssid=data_bucket["ssid_g"]
    ip_addresses = list(sta_if.ifconfig())
    ip_addresses.insert(0, "Connected to:")
    ip_addresses.insert(1, ssid)
    ip_addresses.insert(2, "IP Addresses:")
    ip_addresses.append("Press OK to continue")
    menu.menu_list=ip_addresses
    menu.update()
    display.clear_display()
    menu_refresh.refresh()

    while True:
        inp_menu = typer.start_typing()

        if inp_menu == "ok" or inp_menu == "back":
            current_app[0]="settings"
            current_app[1]="application_modules"
            break
        menu.update_buffer(inp_menu)
        menu_refresh.refresh()
        time.sleep(0.1)

def update_wifi_credentials(ssid, password):
    ssid = str(ssid).strip()
    password = str(password)

    data = []
    try:
        with open(wifi_password_data, "r") as file:
            loaded = json.load(file)
            if isinstance(loaded, list):
                data = loaded
    except Exception:
        data = []

    for cred in data:
        if isinstance(cred, dict) and cred.get("ssid") == ssid:
            cred["password"] = password
            print(f"Updated password for Wi-Fi {ssid}")
            break
    else:
        data.append({"ssid": ssid, "password": password})
        print(f"Added Wi-Fi {ssid} to JSON")
    
    with open(wifi_password_data, "w") as file:
        json.dump(data, file)

def wifi_connector():
    ssid = str(data_bucket.get("ssid_g", "")).strip()
    form.input_list={"inp_0": " "}
    form.form_list=["Password:", "inp_0", "Wi-Fi Name:", ssid]
    form.update()
    display.clear_display()
    form_refresh.refresh()

    while True:
        inp = typer.start_typing()
        if inp == "back":
            current_app[0]="settings"
            current_app[1]="application_modules"
            app.set_app_name("settings")
            app.set_group_name("root")
            break

        if inp == "ok":
            password = form.input_list["inp_0"]
            password = password[:-1]
            print(ssid, password, len(password))

            display.clear_display()
            menu.menu_list=["Trying to connect to:", ssid]
            menu.update()
            menu_refresh.refresh()

            connection_status = bool(do_connect(ssid, password) and sta_if.isconnected())

            connected_ssid = ""
            if connection_status:
                try:
                    connected_ssid = sta_if.config("essid")
                except Exception:
                    connected_ssid = ""
                if connected_ssid and connected_ssid != ssid:
                    connection_status = False

            data_bucket["connection_status_g"] = connection_status
            if connection_status:
                data_bucket["ssid_g"] = ssid
                update_wifi_credentials(ssid=ssid, password=password)
                try:
                    from process_modules.wireless_transfer import ensure_service

                    ensure_service(force_restart=True)
                except Exception as err:
                    print("Wireless REPL start failed:", err)
                display_ip_addresses(ssid)
            else:
                display_error_message(ssid)
            display.clear_display()
            app.set_app_name("settings")
            app.set_group_name("root")
            break
        if inp == "alpha" or inp == "beta":
            keypad_state_manager(x=inp)
            form.update_buffer("")
        if inp == "caps":
            keypad_state_manager(x="A")
            form.update_buffer("")

        # if inp == "off":
        #     machine.deepsleep()
        if inp not in ["alpha", "beta", "ok"]:
            form.update_buffer(inp)
        form_refresh.refresh(state=nav.current_state())
        # time.sleep(0.15)
        

def do_connect(ssid, password):
    ssid = str(ssid).strip()
    sta_if.active(True)
    try:
        sta_if.config(pm=0)
    except Exception:
        pass

    if sta_if.isconnected():
        try:
            current_ssid = sta_if.config("essid")
        except Exception:
            current_ssid = ""

        if current_ssid == ssid:
            return True

        try:
            sta_if.disconnect()
            time.sleep(0.2)
        except Exception:
            pass

    print('Trying to connect to %s...' % ssid)

    try:
        sta_if.connect(ssid, password)
    except Exception as err:
        print("Failed to start connection:", err)
        return False

    connected = False
    for retry in range(100):
        connected = sta_if.isconnected()
        if connected:
            break
        time.sleep(0.1)
    if connected:
        try:
            sta_if.config(pm=0)
        except Exception:
            pass
        print('\nConnected. Network config: ', sta_if.ifconfig())
        
    else:
        print('\nFailed. Not Connected to: ' + ssid)
    return connected
