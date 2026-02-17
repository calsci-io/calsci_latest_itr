# Triple Firmware Build and Flash Report (ESP32-S3)

## Scope
- Target board: ESP32-S3-N16R8 (16MB flash, 8MB PSRAM)
- USB port used: `/dev/ttyACM0`
- Firmware set:
- `ota_0` -> MicroPython (`mpy_driver_intergration_firmware`)
- `ota_1` -> C++ (`cpp_driver_intergration_firmware`)
- `ota_2` -> Rust (`rust_driver_intergration_firmware`)

## Requirements
- ESP-IDF v5.4 available at `~/calsci/triple_boot/esp-idf`
- Python 3 and `esptool.py` (project venv path used below)
- Rust ESP toolchain (`RUSTUP_TOOLCHAIN=esp`)
- Build tools: `make`, `cargo`, `idf.py`
- Serial access permission to `/dev/ttyACM0` (Linux: user in `dialout`)

## Environment Setup Used
- ESP-IDF shell: `source ~/calsci/triple_boot/esp-idf/export.sh`
- Rust + ESP shell: `source ~/.cargo/env && source ~/export-esp.sh && source ~/calsci/triple_boot/esp-idf/export.sh`

## Partition Map Used
- `ota_0` at `0x20000` (MicroPython)
- `ota_1` at `0x420000` (C++)
- `ota_2` at `0x820000` (Rust)

## Build Commands Used
- MicroPython build:
- `make -C ~/calsci/mpy_driver_intergration_firmware/ports/esp32 BOARD=ESP32_GENERIC_S3 BOARD_VARIANT=SPIRAM_OCT BUILD=build-ESP32_GENERIC_S3-SPIRAM_OCT-st7565-integration USER_C_MODULES=~/calsci/mpy_driver_intergration_firmware/c_modules/micropython.cmake -j$(nproc)`
- Output: `~/calsci/mpy_driver_intergration_firmware/ports/esp32/build-ESP32_GENERIC_S3-SPIRAM_OCT-st7565-integration/micropython.bin`

- C++ build:
- `cd ~/calsci/cpp_driver_intergration_firmware && idf.py build`
- Output: `~/calsci/cpp_driver_intergration_firmware/build/cpp_app.bin`

- Rust build:
- `cd ~/calsci/rust_driver_intergration_firmware && RUSTUP_TOOLCHAIN=esp ESP_IDF_TOOLS_INSTALL_DIR=fromenv IDF_PYTHON_CHECK_CONSTRAINTS=no cargo build --release`
- ELF output: `~/calsci/rust_driver_intergration_firmware/target/xtensa-esp32s3-espidf/release/rust_app`

## Flash Commands Used
- MicroPython (`ota_0`):
- `~/calsci/triple_boot/tripleboot/bin/esptool.py --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash 0x20000 ~/calsci/mpy_driver_intergration_firmware/ports/esp32/build-ESP32_GENERIC_S3-SPIRAM_OCT-st7565-integration/micropython.bin`

- C++ (`ota_1`):
- `~/calsci/triple_boot/tripleboot/bin/esptool.py --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash 0x420000 ~/calsci/cpp_driver_intergration_firmware/build/cpp_app.bin`

- Rust image generation (required before flashing Rust slot):
- `~/calsci/triple_boot/tripleboot/bin/esptool.py --chip esp32s3 elf2image --flash_size 16MB --flash_mode dio ~/calsci/rust_driver_intergration_firmware/target/xtensa-esp32s3-espidf/release/rust_app -o ~/calsci/rust_driver_intergration_firmware/rust_app.bin`

- Rust (`ota_2`):
- `~/calsci/triple_boot/tripleboot/bin/esptool.py --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash 0x820000 ~/calsci/rust_driver_intergration_firmware/rust_app.bin`

## Runtime File Sync Used (MicroPython app behavior)
- When `mpremote` was unstable, raw-REPL `pyserial` upload was used to update `/boot.py` and `/process_modules/typer.py` directly on device.

## Issues Faced and Resolutions
- MicroPython build failed with `PermissionError` in `makeqstrdefs.py` (`SemLock`).
- Cause: sandboxed build context blocked multiprocessing semaphore creation.
- Fix: rerun build with elevated permission context.

- C++/OTA switch gave `ESP_ERR_OTA_VALIDATE_FAILED` and `invalid segment length 0xffffffff`.
- Cause: invalid or wrong image in target slot (`ota_0`).
- Fix: reflash valid MicroPython image to `0x20000` and keep slot map consistent.

- Serial port intermittently failed with `could not open port /dev/ttyACM0`.
- Cause: USB re-enumeration race or another process holding port.
- Fix: wait and retry, ensure no parallel serial monitor is active.

- Rust build hit `unknown target triple 'xtensa'` in bindgen.
- Cause: incomplete/incorrect Rust ESP env or incompatible bindgen clang path.
- Fix: build in full Rust+ESP env (`source ~/.cargo/env && source ~/export-esp.sh && source ~/calsci/triple_boot/esp-idf/export.sh`).

- Rust slot boot behavior wrong after flash.
- Cause: wrong artifact flashed (`libespidf.bin` instead of app image).
- Fix: generate `rust_app.bin` from ELF using `esptool.py elf2image`, then flash that bin to `0x820000`.

- `ALPHA +/-` switching unreliable.
- Cause: combo edge detection was too strict and matrix scan order could miss the chord.
- Fix: detect `+/-` newly-pressed while `ALPHA` is physically held in all firmware layers.

## Validated Switching Behavior
- Hold `ALPHA` + press `+` -> next slot (`0 -> 1 -> 2 -> 0`)
- Hold `ALPHA` + press `-` -> previous slot (`0 <- 1 <- 2 <- 0`)

## Notes for Sharing
- This report reflects the exact command patterns and fixes used during integration and testing on `ESP32-S3-N16R8` with `/dev/ttyACM0`.
