# Migration Summary

## Old To New Subsystem Map
- `boot.py` + `main.py` legacy startup -> new `boot.py`, `main.py`, and `core/bootstrap.py`
- `data_modules/object_handler.py` -> `core/context.py`, `core/router.py`, `core/state_store.py`, `services/*`
- hardcoded JSON app lists -> `config/apps/*.json` + `core/registry.py`
- ad hoc thread/background work -> `core/tasks.py` + `core/events.py`
- direct ST7565/menu/form/text buffer flows -> `ui/models.py` + `services/render_service.py`
- app-level JSON/TinyDB/state mutations -> `services/storage_service.py`
- app-level WiFi/NTP/power calls -> `services/network_service.py`, `services/time_service.py`, `services/power_service.py`
- app-level math/graph/matrix helpers -> `services/calc_service.py`, `services/graph_service.py`, `services/matrix_service.py`, `services/latex_service.py`

## Main Behavior Differences
- The new graph flow is intentionally simpler than the legacy graph screen and focuses on clean service boundaries.
- Legacy “ChatGPT” behavior remains a web-search app because that is what the old code actually implemented.
- Unsupported optional/scientific apps are excluded instead of partially ported.
- Background work now returns through `EventBus`; apps do not own threads directly.

## Data Migration Notes
- First boot seeds `data/settings.json`, `data/wifi_credentials.json`, `data/functions.json`, and `data/installed_apps.json` from `calsci_latest_itr`.
- Legacy default app names are mapped to new route ids during import.
- Optional-app installation is now a runtime registry concern instead of direct folder dispatch.

## Next Debug Steps
- Boot `calsci_new` on real hardware and verify keypad mappings, display inversion, WiFi scan/connect, backlight PWM, and sleep behavior.
- Keep `sim_new` as the host-only harness while both hardware and simulator share the same non-canvas UI shell from `calsci_new`.
- Port excluded legacy apps only after their service boundaries are defined, not by reintroducing direct hardware calls into apps.
