# Phase 08: Hardening, Cutover, And Debug Docs

## Goal
- Add automated validation, preserve debug context, and leave `calsci_new` ready for device-side bring-up.

## Modules Added Or Changed
- `core/bootstrap.py`
- `core/fscompat.py`
- `core/legacy_import.py`
- `adapters/device/display.py`
- `adapters/device/hardware_config.py`
- `adapters/device/input.py`
- `adapters/device/network.py`
- `adapters/device/storage.py`
- `services/render_service.py`
- `services/update_service.py`
- `../CalSci_firmware/ports/esp32/main.c`
- `../CalSci_firmware/ports/esp32/boards/manifest.py`
- `../sim_new/main.py`
- `../sim_new/pygame_shell.py`
- `../sim_new/README.md`
- `../test.py`
- `tests/_helpers.py`
- `tests/test_fscompat.py`
- `tests/test_display_adapter.py`
- `tests/test_input_adapter.py`
- `tests/test_legacy_shell.py`
- `tests/test_sim_new.py`
- `tests/test_update_service.py`
- `docs/migration/phase-08-hardening-cutover.md`
- `tools/update_manifest_example.json`
- `apps/builtins/software_update.py`
- `config/system.json`
- `config/apps/settings_apps.json`
- `core/update_boot.py`
- `core/update_common.py`
- `ui/canvas.py`
- `ui/legacy_shell.py`

## Key Design Decisions
- Host tests use fake device modules so the new runtime can be validated without editing firmware.
- Import-guard tests enforce the architectural rule that non-adapter code cannot import device or legacy modules directly.
- `calsci_latest_itr` remains untouched and the migration summary points future debugging back to the exact replacements in `calsci_new`.

## Legacy Mapping
- Device bootstrap behavior is exercised through fake `st7565`, `network`, `machine`, and `calsci_keypad` modules.
- The summary doc maps old subsystem names to new runtime boundaries.

## Verification Run
- `python3 -m compileall calsci_new sim_new`
- `python3 -m unittest discover -s calsci_new/tests -p 'test_*.py'`
- `timeout 2s env SDL_VIDEODRIVER=dummy python3 sim_new/main.py`
- Real hardware serial capture on `/dev/ttyACM0`
- Real hardware `machine.reset()` restart check on `/dev/ttyACM0`
- Real hardware framebuffer validation via `hybrid_sim.status()` + `hybrid_sim.read_fb()`

## Failures Seen
- Host tests initially failed because `core/__init__.py` imported bootstrap and forced device modules into pure-host test imports.
- Real hardware boot failed in `boot.py` because `core/bootstrap.py`, `core/legacy_import.py`, and `adapters/device/storage.py` assumed CPython-style `os.path` and `os.makedirs`, which are not available on the target MicroPython build.
- Real hardware menu rendering failed in `adapters/device/display.py` because the target MicroPython build does not provide `str.ljust()`.
- Real hardware WiFi disconnect state stayed briefly stale after `disconnect()`, so an immediate status refresh could still report `connected=True`.
- REPL `Ctrl-D` soft reboot reported the legacy `calsci_latest_itr` boot failure (`ImportError: no module named 'data_modules'`) even though the device filesystem root already contained the deployed `calsci_new` `boot.py` and `main.py`.
- The standalone display smoke script in `../test.py` failed after the migration with `NameError: name 'display' isn't defined`, but that turned out to be a script bug: the local `import st7565 as display` line had been commented out.
- After the reboot path was fixed, the UI was still blank on-device because `adapters/device/display.py` still pushed an empty placeholder framebuffer for menu/text screens and `set_invert()` was a no-op.
- Cold boot still left the framebuffer blank even after the display renderer fix because `adapters/device/input.py` still depended on the blocking native keypad loop behind a worker-thread wrapper. That path was unreliable during boot and could still stop the runtime before the first launcher render.
- Even after framebuffer/render recovery, the physical LCD could still stay blank because `adapters/device/hardware_config.py` did not match the known-good working display wiring from `../test.py` and `test/board_config.py`. `calsci_new` was driving swapped `RS/RST` and `SDA/SCK` pins, so the hybrid capture path could look healthy while the real panel showed nothing.
- Non-canvas UI ownership was still in the wrong place. `services/render_service.py` delegated menu/text/form layout back into the device adapter through `draw_lines()`, so the legacy UI-shell parity work could not be shared cleanly between hardware and a future simulator.
- Simulator bring-up was still missing entirely. The codebase had simulator-ready runtime boundaries, but there was no `sim_new` host harness that could boot `calsci_new` on desktop without touching the working hardware bootstrap path.
- The first `sim_new` pass still did not match the existing `calsci_simulator` shell closely enough, and clickable keypad hotspots were not yet routed through mode-aware `calsci_new` tokens. Keyboard input worked, but the on-screen calculator faceplate was not a reliable manual test harness.
- There was no software-update path for WiFi-connected devices. The runtime could reach GitHub-backed APIs through the network adapter, but there was no manifest format, no staged download path, no boot-time file apply step, and no settings-screen entrypoint for updates.

## Fixes Applied
- Removed bootstrap imports from `core/__init__.py`.
- Added `core/fscompat.py` and switched runtime/storage manifest bootstrap code to use MicroPython-safe path and directory helpers instead of `os.path`/`os.makedirs`.
- Added `tests/test_fscompat.py` to keep the compatibility helpers covered on the host test path.
- Replaced `str.ljust()` usage in `adapters/device/display.py` with explicit padding logic and added `tests/test_display_adapter.py` to keep the render path covered.
- Updated `adapters/device/network.py` so `disconnect()` waits for the STA interface to settle and falls back to an interface reset before reporting failure.
- Updated `CalSci_firmware/ports/esp32/main.c` so ESP32 startup now executes filesystem `boot.py` first and only falls back to a frozen copy if the file is absent. That makes reboot and reset honor the deployed `calsci_new` root files instead of an older frozen boot script.
- Removed the project-specific frozen `boot.py` entry from `CalSci_firmware/ports/esp32/boards/manifest.py` so clean firmware builds no longer embed the stale legacy `calsci_latest_itr/boot.py`.
- Restored `../test.py` to a valid standalone smoke script by uncommenting the firmware `st7565` import.
- Replaced the placeholder menu/text renderer in `adapters/device/display.py` with a real 5x8 glyph writer backed by `ui/font5x8.py`, and wired `set_invert()` through to the firmware driver so dark-mode changes actually reach the panel.
- Corrected `adapters/device/hardware_config.py` to use the same working LCD pin order as the proven standalone hardware test: `init(9, 11, 10, 13, 12)` for `(cs, rs, rst, sda, sck)`.
- Updated `adapters/device/input.py` so the device path uses a direct non-blocking GPIO matrix scan instead of a threaded wrapper around the blocking native keypad loop. The native threaded fallback remains only for non-device environments that do not expose `machine.Pin`.
- Upgraded `ui/canvas.py` using the framebuffer model already proven in `calsci_simulator` / `calsci_latest_itr`: it now exposes `draw_text`, `draw_text_in_rect`, `draw_text_center`, `draw_text_right`, `rect`, `fill_rect`, `hline`, and `vline` on a 1024-byte mono framebuffer.
- Refactored `adapters/device/display.py` to stop doing byte-at-a-time text uploads for menu/text/form screens. Line-based screens now render into a framebuffer and flush once through the firmware `st7565.graphics(...)` API, which matches the optimized C-module path.
- Removed the extra Python-side display tuning from `adapters/device/display.py` so panel startup uses the firmware ST7565 init profile instead of a new hardcoded Python contrast/profile override.
- Added/updated `tests/test_display_adapter.py`, `tests/test_input_adapter.py`, and `tests/_helpers.py` so the host path now covers graphics-based text rendering, the verified LCD init pin order, non-blocking matrix scanning, and the non-device keypad fallback.
- Added `ui/legacy_shell.py` and moved menu/text/form shell composition out of `adapters/device/display.py`. `services/render_service.py` now builds the full 128x64 framebuffer for non-canvas screens in shared UI code and flushes it through `draw_canvas(...)`, so hardware and simulator share the same renderer.
- Ported the updated legacy shell behavior for current `calsci_new` menu/text/form screens: centered normalized titles, boxed panels, legacy-style menu windowing and scrollbar, compact form rows, footer bar handling, active-field caret, and horizontal overflow handling.
- Added `sim_new/main.py` plus `sim_new/pygame_shell.py` as a host-only harness. `sim_new` now owns its own container, sim adapters, pygame boot path, and isolated `sim_new/data` storage while reusing `calsci_new` runtime, apps, services, and shared UI rendering.
- Added `tests/test_legacy_shell.py` and `tests/test_sim_new.py` so the host suite now covers shared framebuffer shell output and the headless simulator container/key-mapping path.
- Updated `sim_new/pygame_shell.py` to use the same outer calculator shell as `calsci_simulator`: it now loads the old reference background image and uses the old hotspot geometry for clickable buttons, falling back to a generated shell only if the image is absent.
- Added explicit simulator mode layouts in `sim_new` so a clicked hotspot resolves to the correct `calsci_new` token per mode (`default`, `alpha`, `beta`, `caps`) without importing legacy runtime code. This keeps the old simulator faceplate while making the keypad useful inside the new architecture.
- Extended the sim harness keyboard path so desktop `F1`..`F6` map to the current scientific tokens used by `calsci_new`, and added headless tests for clickable matrix events plus mode-sensitive token resolution.
- Added a GitHub-manifest updater flow for Python-side software updates. `services/update_service.py` now checks a remote manifest, validates product/version/file entries, downloads staged text files over WiFi, verifies optional SHA-256 hashes, and writes `pending_update.json` for the next reboot.
- Added `core/update_boot.py` plus `core/update_common.py`, and updated `boot.py` so pending staged files are applied before importing `core.bootstrap`. This keeps live modules from being overwritten while they are already imported in RAM.
- Extended storage and network boundaries for updater needs: `adapters/device/storage.py` now supports generic text/json path helpers plus staged tree cleanup, `adapters/device/network.py` / `services/network_service.py` now expose `http_get_text(...)`, and `adapters/device/power.py` / `services/power_service.py` now expose restart support for “download then reboot to apply”.
- Added the `Software Update` settings app in `apps/builtins/software_update.py` and registered it in `config/apps/settings_apps.json`. The settings flow is: `OK` checks GitHub, `OK` again downloads if a newer version is available, and `OK` once more reboots to apply the staged update.
- Added `tools/update_manifest_example.json` as the publishable manifest shape for the configured GitHub raw URL.

## Root Cause
- Legacy reboot path: `ports/esp32/main.c` called `pyexec_file_if_exists("boot.py")`, and `shared/runtime/pyexec.c` prefers frozen modules over the filesystem. Because the ESP32 board manifest had frozen `calsci_latest_itr/boot.py`, soft reboot and reset executed that legacy boot file first. The captured serial failure was:
  - `MPY: soft reboot`
  - `Traceback (most recent call last):`
  - `File "boot.py", line 4, in <module>`
  - `ImportError: no module named 'data_modules'`
- Standalone display smoke failure: `../test.py` was not failing because of `calsci_new`; it simply had the line `import st7565 as display` commented out, so the board traceback was `NameError: name 'display' isn't defined`.
- Blank UI after reboot: once startup was routed into `calsci_new`, the runtime could reach the launcher app but the visible menu/text path was still empty because `adapters/device/display.py` was writing a zeroed placeholder framebuffer for `draw_lines()`. Manual on-device launcher rendering proved the app screens were healthy and the framebuffer became non-zero (`FB_NONZERO 520`) as soon as the adapter rendered real glyphs.
- Blank UI after cold boot: even with the real text renderer in place, the runtime could still stop before first render on reset because the keypad path still relied on the blocking native `calsci_keypad.Keypad.keypad_loop()` call through a worker-thread wrapper. Replacing that with a direct non-blocking GPIO matrix scan on the device path removed the cold-boot stall.
- Physical LCD still blank while hybrid capture looked healthy: `calsci_new` was not using the same board wiring as the known-good display test. The real root cause on hardware was the bad pin map in `adapters/device/hardware_config.py`, not the panel. After restoring the working init order from the standalone test, the physical display came up correctly with contrast kept at `2`.
- Display adapter quality gap: even after the panel was working, the line-based UI path was still bring-up grade because it bypassed the firmware bulk-update API and pushed glyph bytes one-by-one with Python loops. The firmware C module already exposes the optimized `graphics(...)` region upload path, so the adapter was leaving performance and consistency on the table.
- Shared UI-shell gap: even after the adapter switched to `graphics(...)`, menu/text/form layout still lived inside the device adapter path. That meant desktop simulation would need a second renderer or more hardcoded adapter behavior. Moving the shell into shared UI code fixed the ownership problem and made the adapter a framebuffer sink again.
- Simulator gap: `calsci_new` had the correct runtime boundaries for a simulator, but there was no host harness to assemble a container with non-device adapters. The missing piece was a new `sim_new` entrypoint, not more changes to the working hardware bootstrap path.
- Simulator click gap: the old simulator faceplate is not the same logical key matrix as the new device adapter. The simulator needed its own explicit translation layer from old faceplate positions to `calsci_new` tokens; otherwise clickable buttons would either do nothing or emit stale legacy meanings.
- Software-update gap: safe self-update needed to happen at boot, not in the live runtime. The real missing pieces were a staged file area under `data/`, a pending-update marker, and a pre-bootstrap apply step in `boot.py`.

## Re-Tested
- Host validation still passes:
  - `python3 -m compileall calsci_new sim_new`
  - `python3 -m unittest discover -s calsci_new/tests -p 'test_*.py'`
- Soft reboot on hardware now returns cleanly with no legacy traceback:
  - `MPY: soft reboot`
  - `MicroPython 7431f4afa5-dirty on 2026-04-13; Generic ESP32S3 module with Octal-SPIRAM with ESP32S3`
  - `CalSci >>>`
- The fixed `../test.py` now runs cleanly on the board and completes the full firmware display smoke:
  - `ST7565 basic demo`
  - `WIDTH = 128`
  - `HEIGHT = 64`
  - `PAGES = 8`
  - `SPI2_HOST = 1`
  - `basic demo complete`
- Soft reboot now reaches the runtime display path quickly on hardware:
  - `hybrid_sim.status()["frame_id"] == 1043`
  - `hybrid_sim.read_fb()` shows `FB_NONZERO 520`
- Hard reset via `machine.reset()` now also reaches the runtime display path on the same 2026-04-13 firmware:
  - `BOOT_MODS == ['core.bootstrap', 'core.runtime', 'apps.builtins.launcher']`
  - `hybrid_sim.status()["frame_id"] == 1043`
  - `hybrid_sim.read_fb()` shows `FB_NONZERO 520`
- Physical display retest after correcting `adapters/device/hardware_config.py`:
  - Contrast was explicitly restored back to `2`
  - Updated files were pushed to the board
  - After reboot, the real LCD display is now visibly working on hardware
- Production-grade display adapter retest after the framebuffer refactor:
  - `adapters/device/display.py` and `ui/canvas.py` were pushed to the board
  - Soft reboot still returns cleanly into `calsci_new`
  - `BOOT_MODS == ['core.bootstrap', 'core.runtime', 'apps.builtins.launcher']`
  - `hybrid_sim.status()["contrast"] == 2` using the firmware default profile
  - `hybrid_sim.read_fb()` shows `FB_NONZERO 530`
- Shared renderer and simulator validation now pass on the host:
  - `python3 -m compileall calsci_new sim_new`
  - `python3 -m unittest discover -s calsci_new/tests -p 'test_*.py'`
  - `21` host tests pass, including shared renderer output checks and headless `sim_new` container/key-mapping checks
  - `timeout 2s env SDL_VIDEODRIVER=dummy python3 sim_new/main.py` starts cleanly and stays alive until the expected timeout, confirming the real desktop entrypoint boots without immediate errors
- `sim_new` now matches the existing `calsci_simulator` shell when the old background image is present, and the host test suite now exercises both direct keyboard tokens and clickable keypad matrix events through the new simulator translation layer.
- GitHub updater validation now passes on the host:
  - `python3 -m compileall /home/rupesh/calsci/calsci_v1`
  - `python3 -m unittest discover -s /home/rupesh/calsci/calsci_v1/tests -p 'test_*.py'`
  - `23` host tests pass, including new coverage for manifest checking, staged file download, pending-update creation, and boot-time update apply
  - `timeout 2s env SDL_VIDEODRIVER=dummy python3 /home/rupesh/calsci/sim_new/main.py` still starts cleanly after adding the updater and the `sim_new` root-path fallback
- Direct hardware adapter checks were re-driven on the board:
  - WiFi status before scan: `{'connected': False, 'ifconfig': (), 'ssid': ''}`
  - WiFi scan returned `25` SSIDs
  - WiFi disconnect/status cleanup still reports `connected=False`
  - Battery/backlight path still responds: `voltage=4.211`, `charging=False`, and backlight level changes `10 -> 7 -> 3 -> 0 -> 10` all round-trip correctly
- Built-in app initial renders were re-driven on the board by constructing each app and painting it through the real display adapter. All of the following rendered without exception and produced non-zero framebuffers:
  - `calculate`
  - `settings_hub`
  - `chatgpt`
  - `installed_hub`
  - `scientific_hub`
  - `function_locker`
  - `latex_calc`
  - `backlight_setting`
  - `wifi_manager`
  - `network_status`
  - `dark_mode_setting`
  - `device_info`
  - `auto_wifi_setting`
  - `auto_sleep_setting`
  - `battery_status`
- Device-side storage still reports `data/settings.json["default_route"] == "launcher"` after boot.

## Remaining Risks
- Physical keypad presses (`nav/ok/back/alpha/beta/caps`) were not manually re-driven in this pass. The device-side keypad scan path is now non-blocking and the app render path is live, but the real key matrix still needs a human press sweep on hardware.
- WiFi manager connect flow, backlight UI navigation, and full auto-sleep behavior were not manually re-driven through the live launcher/settings menus in this pass. Their adapters and initial app renders are healthy, but the end-to-end button-driven UI sweep is still pending.
- `sim_new` currently matches the shared menu/text/form shell only. Canvas-heavy screens still use the existing `CanvasScreen` path, and legacy table/grid form parity is still deferred.
- The updater is configured to look for `https://raw.githubusercontent.com/calsci-io/calsci_latest_itr/calsci_v1/update/manifest.json`, but that manifest and its referenced raw files must actually be published to the GitHub branch before the device can download anything. The code path is present; the hosted update bundle is still an operational step.
