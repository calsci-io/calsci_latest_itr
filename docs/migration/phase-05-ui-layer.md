# Phase 05: UI Layer Migration

## Goal
- Replace direct buffer-writing app code with declarative screen models and reusable UI helpers.

## Modules Added Or Changed
- `ui/models.py`
- `ui/theme.py`
- `ui/components.py`
- `ui/canvas.py`
- `ui/font5x8.py`
- `services/render_service.py`

## Key Design Decisions
- The first UI contract is intentionally small: `MenuScreen`, `TextScreen`, `FormScreen`, and `CanvasScreen`.
- Shared UI behavior such as text editing, wrapping, menu movement, and screen sizing lives in `ui/` instead of inside apps.
- Canvas rendering remains adapter-backed so a simulator renderer can be added later without changing app logic.

## Legacy Mapping
- Old menu/text/form uploaders were collapsed into one `RenderService`.
- Apps now describe screen state rather than writing raw display bytes.

## Verification Run
- All UI modules compiled cleanly.
- App contract tests render screens through the new models.

## Failures Seen
- None in this phase.

## Fixes Applied
- Not applicable.

## Remaining Risks
- `CanvasScreen` currently prioritizes raw graph output and does not yet overlay title/footer text onto the bitmap.
