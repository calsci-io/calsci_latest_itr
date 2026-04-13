# Phase 03: Device Adapters And Services

## Goal
- Move hardware and platform concerns behind adapters and expose reusable services to apps.

## Modules Added Or Changed
- `adapters/device/display.py`
- `adapters/device/input.py`
- `adapters/device/network.py`
- `adapters/device/power.py`
- `adapters/device/storage.py`
- `adapters/device/hardware_config.py`
- `services/storage_service.py`
- `services/input_service.py`
- `services/render_service.py`
- `services/network_service.py`
- `services/power_service.py`
- `services/calc_service.py`
- `services/graph_service.py`
- `services/search_service.py`
- `services/matrix_service.py`
- `services/time_service.py`
- `services/latex_service.py`

## Key Design Decisions
- Only adapter modules import `machine`, `network`, `st7565`, or `calsci_keypad`.
- `StorageService` owns settings, WiFi credentials, installed apps, and custom functions.
- `RenderService` renders view models instead of allowing app-level display writes.
- `TimeService` now fails cleanly when WiFi/NTP is unavailable instead of silently using stale state.

## Legacy Mapping
- Direct ST7565, keypad, NTP, WiFi, power, and JSON access moved out of app files.
- Old calculator, graph, search, matrix, and time behaviors were preserved as services rather than embedded in screens.

## Verification Run
- `tests/test_storage.py` validates legacy-data import into the new storage layout.
- `tests/test_import_guards.py` enforces the adapter-only hardware rule.

## Failures Seen
- Time sync logic needed a cleaner failure path for disconnected WiFi.

## Fixes Applied
- `TimeService.indian_time()` now checks WiFi status first and raises explicit errors.

## Remaining Risks
- Actual device display contrast/inversion behavior still depends on the firmware display module.
