# Migration Status

Date: 2026-04-13

This migration was executed in one uninterrupted run inside `calsci_new`.

## Phase Status
- `01 Foundation And Reporting`: completed
- `02 Core Runtime And Contracts`: completed
- `03 Device Adapters And Services`: completed
- `04 Config, Registry, And Manifest Migration`: completed
- `05 UI Layer Migration`: completed
- `06 Core App Migration`: completed
- `07 Remaining Feature Migration`: completed with explicit exclusions
- `08 Hardening, Cutover, And Debug Docs`: completed

## Final Verification
- `python3 -m compileall calsci_new sim_new`: passed
- `python3 -m unittest discover -s calsci_new/tests -p 'test_*.py'`: passed
- Host-side fake-device bootstrap, shared renderer, and sim harness validation: passed through the unit suite

## Explicit Exclusions In This Cut
- Legacy optional apps excluded from the new registry: `rgb`, `dino`, `lvgl_icon_demo`, `upi_pay_qr`, `stress`
- Legacy scientific entries excluded from the new registry: `simultanious_eqn_sol`, `quad_eqn_sol`, `constants`, `mymolecule`
- Legacy table/grid form parity and canvas-heavy parity are still deferred

## Primary Debug References
- [phase-01-foundation.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-01-foundation.md)
- [phase-02-core-runtime.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-02-core-runtime.md)
- [phase-03-adapters-services.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-03-adapters-services.md)
- [phase-04-config-registry.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-04-config-registry.md)
- [phase-05-ui-layer.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-05-ui-layer.md)
- [phase-06-core-apps.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-06-core-apps.md)
- [phase-07-remaining-features.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-07-remaining-features.md)
- [phase-08-hardening-cutover.md](/home/rupesh/calsci/calsci_new/docs/migration/phase-08-hardening-cutover.md)
- [migration-summary.md](/home/rupesh/calsci/calsci_new/docs/migration/migration-summary.md)
