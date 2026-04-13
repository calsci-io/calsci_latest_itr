import json

from core.update_common import PENDING_UPDATE_FILE, UPDATE_STATE_FILE


LEGACY_ROUTE_MAP = {
    "home": "launcher",
    "calculate": "calculate",
    "settings": "settings_hub",
    "ChatGPT": "chatgpt",
    "installed_apps": "installed_hub",
    "scientific_calculator": "scientific_hub",
    "function_locker": "function_locker",
    "latex_calc": "latex_calc",
}


class StorageService:
    def __init__(self, adapter, config):
        self.adapter = adapter
        self.config = config
        self.adapter.ensure_data_dirs()

    def bootstrap_from_legacy(self):
        if self.adapter.exists("settings.json"):
            return

        legacy_root = self.config.get("legacy_root")
        settings = {
            "dark_mode": False,
            "default_route": "launcher",
            "sleep_timer_ms": 12000000,
            "auto_sleep": True,
            "backlight": True,
            "auto_wifi_connect": True,
            "backlight_level": 15,
            "supported_optional_apps": ["add_2_nums", "utc_time"],
        }
        wifi_credentials = []
        functions = []
        installed_apps = ["add_2_nums", "utc_time"]

        try:
            with open(legacy_root + "/db/settings.json", "r") as handle:
                legacy_settings = json.load(handle)
            for item in legacy_settings.get("_default", {}).values():
                feature = item.get("feature")
                value = item.get("value")
                if feature == "dark_mode":
                    settings["dark_mode"] = bool(value)
                elif feature == "default_app":
                    route_name = value.get("app_name", "home")
                    settings["default_route"] = LEGACY_ROUTE_MAP.get(route_name, "launcher")
                elif feature == "sleep_timer":
                    settings["sleep_timer_ms"] = int(value)
                elif feature == "auto_sleep":
                    settings["auto_sleep"] = bool(value)
                elif feature == "backlight":
                    settings["backlight"] = bool(value)
                elif feature == "auto_wifi_connect":
                    settings["auto_wifi_connect"] = bool(value)
                elif feature == "backlight_level":
                    settings["backlight_level"] = int(value)
        except Exception:
            pass

        try:
            with open(legacy_root + "/db/wifi.json", "r") as handle:
                wifi_credentials = json.load(handle)
        except Exception:
            wifi_credentials = []

        try:
            with open(legacy_root + "/db/functions_data.json", "r") as handle:
                legacy_functions = json.load(handle)
            functions = list(legacy_functions.get("_default", {}).values())
        except Exception:
            functions = []

        try:
            with open(legacy_root + "/db/installed_apps.json", "r") as handle:
                legacy_installed = json.load(handle)
            installed_apps = []
            for item in legacy_installed.get("_default", {}).values():
                app_name = item.get("app_name")
                if app_name in settings["supported_optional_apps"] and app_name not in installed_apps:
                    installed_apps.append(app_name)
        except Exception:
            installed_apps = list(settings["supported_optional_apps"])

        self.adapter.write_json("settings.json", settings)
        self.adapter.write_json("wifi_credentials.json", wifi_credentials)
        self.adapter.write_json("functions.json", functions)
        self.adapter.write_json("installed_apps.json", installed_apps)

    def ensure_runtime_ready(self):
        self.bootstrap_from_legacy()
        self.ensure_update_state()
        return True

    def _default_update_state(self):
        return {
            "current_version": self.config.get("software_version", "dev"),
            "available_version": "",
            "pending_version": "",
            "update_available": False,
            "status": "idle",
            "last_error": "",
            "last_checked_version": "",
        }

    def ensure_update_state(self):
        if self.adapter.exists(UPDATE_STATE_FILE):
            state = self.get_update_state()
            self.adapter.write_json(UPDATE_STATE_FILE, state)
            return state
        state = self._default_update_state()
        self.adapter.write_json(UPDATE_STATE_FILE, state)
        return state

    def get_settings(self):
        return self.adapter.read_json("settings.json", {}) or {}

    def save_settings(self, payload):
        return self.adapter.write_json("settings.json", payload)

    def get_setting(self, key, default=None):
        return self.get_settings().get(key, default)

    def set_setting(self, key, value):
        settings = self.get_settings()
        settings[key] = value
        self.save_settings(settings)
        return value

    def get_update_state(self):
        state = self.adapter.read_json(UPDATE_STATE_FILE, {}) or {}
        merged = self._default_update_state()
        merged.update(state)
        return merged

    def save_update_state(self, payload):
        state = self._default_update_state()
        state.update(payload or {})
        return self.adapter.write_json(UPDATE_STATE_FILE, state)

    def get_pending_update(self):
        return self.adapter.read_json(PENDING_UPDATE_FILE, None)

    def save_pending_update(self, payload):
        return self.adapter.write_json(PENDING_UPDATE_FILE, payload)

    def clear_pending_update(self):
        return self.adapter.remove_path(self.adapter.path(PENDING_UPDATE_FILE))

    def get_wifi_credentials(self):
        return self.adapter.read_json("wifi_credentials.json", []) or []

    def upsert_wifi_credential(self, ssid, password):
        credentials = self.get_wifi_credentials()
        found = False
        for item in credentials:
            if item.get("ssid") == ssid:
                item["password"] = password
                found = True
                break
        if not found:
            credentials.append({"ssid": ssid, "password": password})
        self.adapter.write_json("wifi_credentials.json", credentials)
        return credentials

    def get_functions(self):
        return self.adapter.read_json("functions.json", []) or []

    def save_function(self, name, variables, expression):
        functions = self.get_functions()
        functions = [item for item in functions if item.get("name") != name]
        functions.append({
            "name": name,
            "variables": list(variables),
            "expression": expression,
        })
        self.adapter.write_json("functions.json", functions)
        return functions

    def delete_function(self, name):
        functions = [item for item in self.get_functions() if item.get("name") != name]
        self.adapter.write_json("functions.json", functions)
        return functions

    def get_installed_apps(self):
        return self.adapter.read_json("installed_apps.json", []) or []

    def set_installed_apps(self, app_ids):
        unique = []
        for app_id in app_ids:
            if app_id not in unique:
                unique.append(app_id)
        self.adapter.write_json("installed_apps.json", unique)
        return unique
