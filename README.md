# CalSci New

`calsci_new` is the new modular CalSci runtime.

Goals:
- device-first architecture
- manifest-driven app loading
- no app-level hardware imports
- services and adapters isolate platform dependencies
- background work goes through `TaskManager` and `EventBus`

Execution rule for this migration:
- all migration phases are executed in one uninterrupted run
- phase progress is recorded in `docs/migration/`
- `calsci_latest_itr` remains a read-only reference during migration

