# Phase 07: Remaining Feature Migration

## Goal
- Complete the first optional/settings feature set and explicitly exclude unsupported legacy apps from the new registry.

## Modules Added Or Changed
- `apps/builtins/toggle_setting.py`
- `apps/builtins/backlight_setting.py`
- `apps/builtins/auto_sleep_setting.py`
- `apps/builtins/status_page.py`
- `apps/builtins/wifi_manager.py`
- `apps/optional/add_2_nums.py`
- `apps/optional/utc_time.py`
- `config/apps/settings_apps.json`
- `config/apps/optional_apps.json`

## Key Design Decisions
- Settings were grouped into reusable controller types: toggle, status, WiFi manager, backlight, and auto-sleep.
- WiFi scan/connect and time refresh use background tasks so UI ownership stays single-threaded.
- Unsupported optional apps are excluded from manifests instead of being carried forward as broken stubs.

## Legacy Mapping
- `apps/settings/backlight.py` -> `apps/builtins/backlight_setting.py`
- `apps/settings/wifi_app.py` and related connector logic -> `apps/builtins/wifi_manager.py`
- `apps/settings/network_status.py`, `mac_address.py`, `battery_status.py` -> `apps/builtins/status_page.py`
- `apps/settings/Dark_Mode.py`, `wifi_autoconnect.py` -> `apps/builtins/toggle_setting.py`
- `apps/settings/auto_sleep.py` -> `apps/builtins/auto_sleep_setting.py`
- `apps/installed_apps/add_2_nums.py` -> `apps/optional/add_2_nums.py`
- `apps/installed_apps/utc_time.py` -> `apps/optional/utc_time.py`

## Verification Run
- Bootstrap and app contract tests exercise WiFi and time apps through fake-device services.

## Failures Seen
- None during this phase.

## Fixes Applied
- Not applicable.

## Remaining Risks
- Legacy optional apps `rgb`, `dino`, `lvgl_icon_demo`, `upi_pay_qr`, and `stress` are not ported in this cut.
- Legacy scientific entries `simultanious_eqn_sol`, `quad_eqn_sol`, `constants`, and `mymolecule` are excluded pending a later service design.
