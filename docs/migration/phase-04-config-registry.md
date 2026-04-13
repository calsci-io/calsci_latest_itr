# Phase 04: Config, Registry, And Manifest Migration

## Goal
- Replace legacy hardcoded routing and JSON app lists with manifest-driven registration.

## Modules Added Or Changed
- `core/legacy_import.py`
- `config/apps/system_apps.json`
- `config/apps/launcher_apps.json`
- `config/apps/scientific_apps.json`
- `config/apps/settings_apps.json`
- `config/apps/optional_apps.json`
- `core/bootstrap.py`
- `core/registry.py`
- `services/storage_service.py`

## Key Design Decisions
- Manifest files are committed into the repo and can also be regenerated if missing.
- Optional apps are filtered through `registry.sync_installed(...)`.
- Legacy default-app names are mapped onto new route ids during storage bootstrap.

## Legacy Mapping
- `db/application_modules_app_list.json` -> `config/apps/launcher_apps.json`
- `db/settings_app_list.json` -> `config/apps/settings_apps.json`
- `db/scientific_calculator_app_list.json` -> `config/apps/scientific_apps.json`
- `db/installed_apps.json` -> `data/installed_apps.json` plus optional manifest sync

## Verification Run
- `tests/test_registry.py` validates manifest loading and optional-app filtering.
- `tests/test_bootstrap_device_path.py` validates manifest loading through the real bootstrap path with fake device modules.

## Failures Seen
- None after the registry bootstrap cleanup.

## Fixes Applied
- Not applicable.

## Remaining Risks
- If new optional apps are added later, manifest and storage support lists must be extended together.
