# Phase 01: Foundation And Reporting

## Goal
- Create `calsci_new` as a parallel codebase with a clean folder layout and a persistent migration log.

## Modules Added Or Changed
- `README.md`
- `boot.py`
- `main.py`
- `config/system.json`
- top-level folders for `core`, `apps`, `ui`, `services`, `adapters`, `config`, `data`, `tests`, and `docs/migration`

## Key Design Decisions
- The new runtime lives beside `calsci_latest_itr` and does not mutate the old tree.
- `boot.py` and `main.py` are composition-only entrypoints.
- Debug history is stored under `docs/migration/` instead of mixed into source folders.

## Legacy Mapping
- Old direct boot flow stays as reference only.
- New tree starts from `boot.py` and `main.py` with no direct dependency on `object_handler.py`.

## Verification Run
- Folder scaffold created and source entrypoints compiled in `python3 -m compileall calsci_new`.

## Failures Seen
- None in this phase.

## Fixes Applied
- Not applicable.

## Remaining Risks
- Boot was not device-validated yet at this phase.
