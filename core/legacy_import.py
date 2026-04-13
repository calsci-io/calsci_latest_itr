import json

from .fscompat import ensure_dir, exists, is_dir


def _read_json(path, default):
    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except Exception:
        return default


def _write_json(path, payload):
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def _legacy_orders(legacy_root):
    home = _read_json(legacy_root + "/db/application_modules_app_list.json", [])
    settings = _read_json(legacy_root + "/db/settings_app_list.json", [])
    scientific = _read_json(legacy_root + "/db/scientific_calculator_app_list.json", [])
    return {
        "launcher": [item.get("name") for item in home if item.get("visibility")],
        "settings": [item.get("name") for item in settings if item.get("visibility")],
        "scientific": [item.get("name") for item in scientific if item.get("visibility")],
    }


def _manifest_payloads(legacy_root, storage_service):
    legacy_orders = _legacy_orders(legacy_root)
    launcher_order = {
        "calculate": 10,
        "settings_hub": 20,
        "chatgpt": 30,
        "installed_hub": 40,
        "scientific_hub": 50,
        "function_locker": 60,
        "latex_calc": 70,
    }
    for index, legacy_name in enumerate(legacy_orders["launcher"], 1):
        mapping = {
            "calculate": "calculate",
            "settings": "settings_hub",
            "ChatGPT": "chatgpt",
            "installed_apps": "installed_hub",
            "scientific_calculator": "scientific_hub",
            "function_locker": "function_locker",
            "latex_calc": "latex_calc",
        }.get(legacy_name)
        if mapping is not None:
            launcher_order[mapping] = index * 10

    settings_order = {
        "backlight_setting": 10,
        "wifi_manager": 20,
        "network_status": 30,
        "dark_mode_setting": 40,
        "device_info": 50,
        "auto_wifi_setting": 60,
        "auto_sleep_setting": 70,
        "battery_status": 80,
    }
    for index, legacy_name in enumerate(legacy_orders["settings"], 1):
        mapping = {
            "backlight": "backlight_setting",
            "wifi_app": "wifi_manager",
            "network_status": "network_status",
            "Dark_Mode": "dark_mode_setting",
            "mac_address": "device_info",
            "wifi_autoconnect": "auto_wifi_setting",
            "auto_sleep": "auto_sleep_setting",
            "battery_status": "battery_status",
        }.get(legacy_name)
        if mapping is not None:
            settings_order[mapping] = index * 10

    scientific_order = {
        "graph_plotter": 10,
        "matrix_tools": 20,
    }
    for index, legacy_name in enumerate(legacy_orders["scientific"], 1):
        mapping = {
            "graph": "graph_plotter",
            "matrix_operations": "matrix_tools",
        }.get(legacy_name)
        if mapping is not None:
            scientific_order[mapping] = index * 10

    installed_apps = storage_service.get_installed_apps()
    optional_installed = {
        "add_2_nums": "add_2_nums" in installed_apps,
        "utc_time": "utc_time" in installed_apps,
    }

    return {
        "system_apps.json": [
            {
                "app_id": "launcher",
                "title": "CalSci",
                "module": "apps.builtins.launcher",
                "group": "system",
                "order": 0,
                "metadata": {
                    "child_group": "launcher",
                    "subtitle": "Modular Runtime",
                    "empty_message": "No launcher apps",
                },
            }
        ],
        "launcher_apps.json": [
            {
                "app_id": "calculate",
                "title": "Calculate",
                "module": "apps.builtins.calculate",
                "group": "launcher",
                "order": launcher_order["calculate"],
            },
            {
                "app_id": "settings_hub",
                "title": "Settings",
                "module": "apps.builtins.settings_hub",
                "group": "launcher",
                "order": launcher_order["settings_hub"],
                "metadata": {
                    "child_group": "settings",
                    "back_route": "launcher",
                    "subtitle": "Device + runtime",
                },
            },
            {
                "app_id": "chatgpt",
                "title": "ChatGPT",
                "module": "apps.builtins.chatgpt",
                "group": "launcher",
                "order": launcher_order["chatgpt"],
            },
            {
                "app_id": "installed_hub",
                "title": "Installed Apps",
                "module": "apps.builtins.installed_hub",
                "group": "launcher",
                "order": launcher_order["installed_hub"],
                "metadata": {
                    "child_group": "installed",
                    "back_route": "launcher",
                    "subtitle": "Optional modules",
                    "empty_message": "No installed apps",
                },
            },
            {
                "app_id": "scientific_hub",
                "title": "Scientific",
                "module": "apps.builtins.scientific_hub",
                "group": "launcher",
                "order": launcher_order["scientific_hub"],
                "metadata": {
                    "child_group": "scientific",
                    "back_route": "launcher",
                    "subtitle": "Graph + matrix",
                },
            },
            {
                "app_id": "function_locker",
                "title": "Function Locker",
                "module": "apps.builtins.function_locker",
                "group": "launcher",
                "order": launcher_order["function_locker"],
            },
            {
                "app_id": "latex_calc",
                "title": "LaTeX Calc",
                "module": "apps.builtins.latex_calc",
                "group": "launcher",
                "order": launcher_order["latex_calc"],
            },
        ],
        "scientific_apps.json": [
            {
                "app_id": "graph_plotter",
                "title": "Graph",
                "module": "apps.builtins.graph_plotter",
                "group": "scientific",
                "order": scientific_order["graph_plotter"],
            },
            {
                "app_id": "matrix_tools",
                "title": "Matrix Tools",
                "module": "apps.builtins.matrix_tools",
                "group": "scientific",
                "order": scientific_order["matrix_tools"],
            },
        ],
        "settings_apps.json": [
            {
                "app_id": "backlight_setting",
                "title": "Backlight",
                "module": "apps.builtins.backlight_setting",
                "group": "settings",
                "order": settings_order["backlight_setting"],
            },
            {
                "app_id": "wifi_manager",
                "title": "WiFi",
                "module": "apps.builtins.wifi_manager",
                "group": "settings",
                "order": settings_order["wifi_manager"],
            },
            {
                "app_id": "network_status",
                "title": "Network Status",
                "module": "apps.builtins.status_page",
                "group": "settings",
                "order": settings_order["network_status"],
                "metadata": {"status_kind": "network"},
            },
            {
                "app_id": "dark_mode_setting",
                "title": "Dark Mode",
                "module": "apps.builtins.toggle_setting",
                "group": "settings",
                "order": settings_order["dark_mode_setting"],
                "metadata": {
                    "setting_key": "dark_mode",
                    "description": "Invert the display theme.",
                },
            },
            {
                "app_id": "device_info",
                "title": "Device Info",
                "module": "apps.builtins.status_page",
                "group": "settings",
                "order": settings_order["device_info"],
                "metadata": {"status_kind": "device"},
            },
            {
                "app_id": "auto_wifi_setting",
                "title": "Auto WiFi",
                "module": "apps.builtins.toggle_setting",
                "group": "settings",
                "order": settings_order["auto_wifi_setting"],
                "metadata": {
                    "setting_key": "auto_wifi_connect",
                    "description": "Reconnect using saved credentials.",
                },
            },
            {
                "app_id": "auto_sleep_setting",
                "title": "Auto Sleep",
                "module": "apps.builtins.auto_sleep_setting",
                "group": "settings",
                "order": settings_order["auto_sleep_setting"],
            },
            {
                "app_id": "battery_status",
                "title": "Battery",
                "module": "apps.builtins.status_page",
                "group": "settings",
                "order": settings_order["battery_status"],
                "metadata": {"status_kind": "battery"},
            },
        ],
        "optional_apps.json": [
            {
                "app_id": "add_2_nums",
                "title": "Add 2 Nums",
                "module": "apps.optional.add_2_nums",
                "group": "installed",
                "order": 10,
                "kind": "optional",
                "installed": optional_installed["add_2_nums"],
            },
            {
                "app_id": "utc_time",
                "title": "Indian Time",
                "module": "apps.optional.utc_time",
                "group": "installed",
                "order": 20,
                "kind": "optional",
                "installed": optional_installed["utc_time"],
            },
        ],
    }


def ensure_manifest_layout(root_dir, legacy_root, storage_service):
    manifest_dir = root_dir + "/config/apps"
    if not is_dir(manifest_dir):
        ensure_dir(manifest_dir)
    payloads = _manifest_payloads(legacy_root, storage_service)
    for filename, items in payloads.items():
        path = manifest_dir + "/" + filename
        if not exists(path):
            _write_json(path, items)
