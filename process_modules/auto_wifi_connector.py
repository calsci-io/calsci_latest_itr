import st7565 as display

try:
    import tools
    if hasattr(display, "graphics") and not hasattr(display.graphics, "pixels_changed"):
        display.graphics = tools.refresh(display.graphics, pixels_changed=200)
except Exception:
    pass

# Copyright (c) 2025 CalSci
# Licensed under the MIT License.

import time
import json
from data_modules.object_handler import data_bucket, sta_if

WIFI_CREDENTIAL_FILES = ("/db/wifi.json", "db/wifi.json")
SETTINGS_FILES = ("/db/settings.json", "db/settings.json")


def _load_json_from_candidates(paths):
    for path in paths:
        try:
            with open(path, "r") as fp:
                return json.load(fp)
        except Exception:
            continue
    return None


def _auto_wifi_enabled():
    settings = _load_json_from_candidates(SETTINGS_FILES)
    if not isinstance(settings, dict):
        return False

    defaults = settings.get("_default", {})
    if not isinstance(defaults, dict):
        return False

    for entry in defaults.values():
        if isinstance(entry, dict) and entry.get("feature") == "auto_wifi_connect":
            return bool(entry.get("value"))
    return False


def _get_saved_credentials():
    creds = _load_json_from_candidates(WIFI_CREDENTIAL_FILES)
    if isinstance(creds, list):
        valid = []
        for item in creds:
            if not isinstance(item, dict):
                continue
            ssid = item.get("ssid", "")
            if not ssid:
                continue
            valid.append(
                {
                    "ssid": str(ssid),
                    "password": str(item.get("password", "")),
                }
            )
        return valid
    return []


def _extract_ssids(scanned_networks):
    ssids = []
    for net in scanned_networks:
        try:
            raw = net[0]
            if isinstance(raw, bytes):
                ssid = raw.decode()
            else:
                ssid = str(raw)
            if ssid:
                ssids.append(ssid)
        except Exception:
            continue
    return ssids


def _set_status_from_sta():
    connected = bool(sta_if.isconnected())
    data_bucket["connection_status_g"] = connected
    if connected:
        try:
            ssid = sta_if.config("essid")
            data_bucket["ssid_g"] = ssid if isinstance(ssid, str) else ""
        except Exception:
            if not data_bucket.get("ssid_g"):
                data_bucket["ssid_g"] = ""
    else:
        data_bucket["ssid_g"] = ""
    return connected


def scan_networks():
    sta_if.active(True)
    try:
        return _extract_ssids(sta_if.scan())
    except Exception as err:
        print("WiFi scan failed:", err)
        return []


def do_connect(ssid, password, timeout_s=6):
    sta_if.active(True)

    if sta_if.isconnected():
        try:
            current = sta_if.config("essid")
        except Exception:
            current = ""
        if current == ssid:
            return True
        try:
            sta_if.disconnect()
            time.sleep(0.2)
        except Exception:
            pass

    print("Trying to connect to %s..." % ssid)
    try:
        sta_if.connect(ssid, password)
    except Exception as err:
        print("Connect start failed:", err)
        return False

    retries = int(timeout_s * 10)
    for _ in range(retries):
        if sta_if.isconnected():
            break
        time.sleep(0.1)

    connected = bool(sta_if.isconnected())
    if connected:
        print("Connected. Network config:", sta_if.ifconfig())
    else:
        print("Failed. Not Connected to:", ssid)
    return connected


def auto_wifi_connector():
    if not _auto_wifi_enabled():
        print("Auto WiFi connect is off")
        return False

    if _set_status_from_sta():
        return True

    credentials = _get_saved_credentials()
    if not credentials:
        print("No saved WiFi credentials found")
        data_bucket["connection_status_g"] = False
        data_bucket["ssid_g"] = ""
        return False

    available_ssids = scan_networks()
    if not available_ssids:
        data_bucket["connection_status_g"] = False
        data_bucket["ssid_g"] = ""
        return False

    available_set = set(available_ssids)
    for cred in credentials:
        ssid = cred["ssid"]
        if ssid not in available_set:
            continue
        if do_connect(ssid=ssid, password=cred["password"]):
            data_bucket["connection_status_g"] = True
            data_bucket["ssid_g"] = ssid
            return True

    data_bucket["connection_status_g"] = False
    data_bucket["ssid_g"] = ""
    return False
