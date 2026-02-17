import st7565 as display
# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

from tinydb import TinyDB, Query
db = TinyDB('db/settings.json')
q=Query()
from machine import Pin
def backlight():
    backlight_status=db.search(q.feature=="backlight")
    if backlight_status[0]["value"] == False:
        from apps.settings.backlight import backlight_pin
        backlight_pin.on()
    elif backlight_status[0]["value"] == True:
        from apps.settings.backlight import backlight_pin
        backlight_pin.off()

def darkmode():
    dark_mode_status=db.search(q.feature=="dark_mode")
    if dark_mode_status[0]["value"] == False:
        # from apps.settings.dark_mode import dark_mode
        display.invert(False)
    elif dark_mode_status[0]["value"] == True:
        display.invert(True)

    # from apps.settings.dark_mode import dark_mode
    # dark_mode()

# import network
# import time
# import json
# import espnow
# import _thread

# sta_if = network.WLAN(network.STA_IF)
# builtins.sta_if=sta_if
# sta_if.active(False)
# time.sleep(0.5)
# gc.collect()
# sta_if.active(True)

# # Attempt WiFi connection using /database/wifi.json
# wifi_config_file = "/db/wifi.json"

# try:
#     with open(wifi_config_file, "r") as f:
#         wifi_data = json.load(f)
        
#     # with open("/db/boot_up.json") as f:
#     #     boot_data = json.load(f)
        
#     # if boot_data["states"].get("wifi_connected"):

#     scanned = sta_if.scan()
#     available_ssids = [net[0].decode() for net in scanned]
#     for entry in wifi_data:
#         ssid = entry.get("ssid")
#         password = entry.get("password")
#         if ssid in available_ssids:
#             print("Connecting to:", ssid)
#             display.clear_display()
#             menu.menu_list=["Connecting to:", str(ssid), "password:", password]
#             menu.update()
#             menu_refresh.refresh()
#             print("connected to ", str(ssid), "password:", password)
#             time.sleep(1)
#             sta_if.connect(ssid, password)
#             for _ in range(100):
#                 if sta_if.isconnected():
#                     display.clear_display()
#                     menu.menu_list=["Connected to:", str(ssid)]
#                     menu.update()
#                     menu_refresh.refresh()
#                     data_bucket["ssid_g"] =ssid
#                     time.sleep(1)
#                     break
#                 time.sleep(0.1)
#             break

#     print("WiFi connected:", sta_if.isconnected())
#     if sta_if.isconnected():
#         print("IP config:", sta_if.ifconfig())
#         data_bucket["connection_status_g"]=True
#     else:
#         display.clear_display()
#         menu.menu_list=["wifi not connected"]
#         menu.update()
#         menu_refresh.refresh()
#         time.sleep(2)
# except Exception as e:
#     print("WiFi setup skipped or failed:", e)

def wifi():
    auto=db.search(q.feature=="auto_wifi_connect")
    if auto[0]["value"]==True:
        from data_modules.object_handler import sta_if
        # import network
        import time
        import json
        from data_modules.object_handler import data_bucket
        # sta_if = network.WLAN(network.STA_IF)
        # builtins.sta_if=sta_if
        # sta_if.active(False)
        # time.sleep(0.5)
        # gc.collect()
        sta_if.active(True)

        # Attempt WiFi connection using /database/wifi.json
        wifi_config_file = "/db/wifi.json"

        try:
            with open(wifi_config_file, "r") as f:
                wifi_data = json.load(f)
                
            # with open("/db/boot_up.json") as f:
            #     boot_data = json.load(f)
                
            # if boot_data["states"].get("wifi_connected"):

            scanned = sta_if.scan()
            available_ssids = [net[0].decode() for net in scanned]
            for entry in wifi_data:
                ssid = entry.get("ssid")
                password = entry.get("password")
                if ssid in available_ssids:
                    print("Connecting to:", ssid)
                    # display.clear_display()
                    # menu.menu_list=["Connecting to:", str(ssid), "password:", password]
                    # menu.update()
                    # menu_refresh.refresh()
                    print("connected to ", str(ssid), "password:", password)
                    time.sleep(1)
                    sta_if.connect(ssid, password)
                    for _ in range(100):
                        if sta_if.isconnected():
                            # display.clear_display()
                            # menu.menu_list=["Connected to:", str(ssid)]
                            # menu.update()
                            # menu_refresh.refresh()
                            data_bucket["ssid_g"] =ssid
                            # time.sleep(1)
                            break
                        time.sleep(0.1)
                    break

            print("WiFi connected:", sta_if.isconnected())
            if sta_if.isconnected():
                print("IP config:", sta_if.ifconfig())
                data_bucket["connection_status_g"]=True
                
            else:
                # display.clear_display()
                # menu.menu_list=["wifi not connected"]
                # menu.update()
                # menu_refresh.refresh()
                # time.sleep(2)
                print("wifi not connected")
                data_bucket["connection_status_g"]=False
        except Exception as e:
            print("WiFi setup skipped or failed:", e)
    else:
        print("auto wifi connect is off")

def default_pins_state():
    i1=Pin(44, Pin.OUT, value=0)
    i2=Pin(43, Pin.OUT, value=0)
    i3=Pin(2, Pin.OUT, value=0)
    i4=Pin(16, Pin.OUT, value=0)
    # i1.off()
    # i2.off()
    # i3.off()
    # i4.off()


def bootup():
    default_pins_state()
    backlight()
    darkmode()
    wifi()