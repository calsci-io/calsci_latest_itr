# Phase 06: Core App Migration

## Goal
- Port the main first-party workflows into the new app contract.

## Modules Added Or Changed
- `apps/builtins/hub.py`
- `apps/builtins/launcher.py`
- `apps/builtins/settings_hub.py`
- `apps/builtins/scientific_hub.py`
- `apps/builtins/installed_hub.py`
- `apps/builtins/calculate.py`
- `apps/builtins/chatgpt.py`
- `apps/builtins/function_locker.py`
- `apps/builtins/latex_calc.py`
- `apps/builtins/graph_plotter.py`
- `apps/builtins/matrix_tools.py`
- `apps/builtins/common.py`

## Key Design Decisions
- Navigation hubs are generic group-driven controllers instead of hardcoded folder routers.
- Calculator, search, function vault, LaTeX, graph, and matrix logic are app-local controllers over shared services.
- Background search runs through `TaskManager` rather than app-owned threads.

## Legacy Mapping
- `apps/root/home.py` -> `apps/builtins/launcher.py`
- `apps/root/calculate.py` -> `apps/builtins/calculate.py` + `services/calc_service.py`
- `apps/root/ChatGPT.py` -> `apps/builtins/chatgpt.py` + `services/search_service.py`
- `apps/root/function_locker.py` and nested helper flows -> `apps/builtins/function_locker.py`
- `apps/root/latex_calc.py` -> `apps/builtins/latex_calc.py`
- `apps/scientific_calculator/graph.py` -> `apps/builtins/graph_plotter.py` + `services/graph_service.py`
- legacy matrix operation files -> `apps/builtins/matrix_tools.py` + `services/matrix_service.py`

## Verification Run
- `tests/test_app_contracts.py` instantiates and renders all enabled/installed apps through the new registry.
- Host bootstrap test confirms these apps register under the new launcher/scientific groups.

## Failures Seen
- None beyond the earlier package bootstrap issue.

## Fixes Applied
- Not applicable.

## Remaining Risks
- Graph UX is intentionally simpler than the old highly tuned graph screen.
