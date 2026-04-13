# Phase 02: Core Runtime And Contracts

## Goal
- Build the modular runtime core and define one app contract used across the new tree.

## Modules Added Or Changed
- `core/contracts.py`
- `core/context.py`
- `core/events.py`
- `core/state_store.py`
- `core/router.py`
- `core/tasks.py`
- `core/registry.py`
- `core/runtime.py`
- `core/bootstrap.py`

## Key Design Decisions
- `AppContext` is the only dependency surface exposed to apps.
- `TaskManager` owns background work and publishes results through `EventBus`.
- `Router` owns navigation history and pending transitions.
- `RuntimeKernel` keeps UI/render/input on the main loop and handles global `home`, `wifi`, and `off` tokens centrally.

## Legacy Mapping
- `data_modules/object_handler.py` responsibilities were split into `AppContext`, `StateStore`, `Router`, and services.
- Old app switching and hidden globals were replaced with `AppRegistry` plus manifest-driven creation.

## Verification Run
- Runtime modules compiled cleanly in `python3 -m compileall calsci_new`.
- `tests/test_router.py` and `tests/test_tasks.py` validate routing history and task completion.

## Failures Seen
- `core/__init__.py` initially imported full bootstrap and leaked device imports into host tests.

## Fixes Applied
- Removed bootstrap side effects from `core/__init__.py` and kept it as a package marker only.

## Remaining Risks
- Device-only scheduling behavior still depends on actual keypad/display timing.
