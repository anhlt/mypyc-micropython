# LVGL Build Guide

This guide documents the automated LVGL firmware pipeline in this repository.

With the Makefile targets in this guide, a single command compiles user modules, generates LVGL bindings from the `.pyi` stub, builds firmware with the LVGL partition table, and flashes to device.

## Overview

The LVGL integration provides:

- Generated LVGL bindings from `src/mypyc_micropython/c_bindings/stubs/lvgl/lvgl.pyi`
- 55+ wrapped LVGL APIs (current stub exports 70+ functions)
- ST7789 display driver integration for Waveshare ESP32-C6-LCD-1.47
- `lv_conf.h` configuration integrated into firmware builds
- One-command deployment via `make deploy-lvgl`

## Prerequisites

Before using LVGL targets:

1. ESP-IDF is installed and exported (see `docs/esp-idf-setup-macos.md` or `docs/esp-idf-setup-linux.md`)
2. Project dependencies are installed
3. `mpy-compile-c` is available in `PATH`
4. Device is connected and port is known (`ls /dev/cu.usb*` on macOS)

If you cloned this repository without submodules initialized:

```bash
git submodule update --init --recursive
```

Recommended environment setup:

```bash
pip install -e ".[dev]"
source ~/esp/esp-idf/export.sh
```

## Quick Start

Use one command to compile, build, and flash LVGL firmware:

```bash
make deploy-lvgl BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem101
```

After flashing, run a quick display smoke test:

```bash
make test-lvgl PORT=/dev/cu.usbmodem101
```

Run the UI navigation memory test:

```bash
make test-lvgl-ui PORT=/dev/cu.usbmodem101
```

This copies `examples/lvgl/ui_*.py` to the device root and runs `ui_device_nav_test.run()`.

## What `deploy-lvgl` Does

`deploy-lvgl` runs `build-lvgl` and `flash-lvgl`.

`build-lvgl` runs this pipeline:

1. `compile-all`
   - Cleans and recompiles all Python examples to `modules/usermod_*`
   - Regenerates `modules/micropython.cmake`
2. `compile-lvgl`
   - Generates `modules/usermod_lvgl/lvgl.c` from `lvgl.pyi`
   - Copies `st7789_driver.c`, `st7789_driver.h`, `lv_conf.h`, and `micropython.cmake` from `src/.../stubs/lvgl/`
   - Patches generated `lvgl.c` via `scripts/patch_lvgl_c.py` to inject display-driver include and globals entries
3. `build-lvgl`
   - Ensures LVGL include is present in `modules/micropython.cmake`
   - Swaps in `partitions-lvgl.csv` as `deps/micropython/ports/esp32/partitions-4MiB.csv`
   - Builds MicroPython firmware with `USER_C_MODULES=$(MODULES_DIR)/micropython.cmake`
   - Restores the original `partitions-4MiB.csv`

`flash-lvgl` then:

1. Swaps in `partitions-lvgl.csv`
2. Runs MicroPython `deploy` for selected `BOARD` and `PORT`
3. Restores the original partition file

## Individual Steps

Use these targets for debugging or customization:

```bash
# Generate LVGL module only
make compile-lvgl

# Build firmware with LVGL, but do not flash
make build-lvgl BOARD=ESP32_GENERIC_C6

# Flash previously built LVGL firmware
make flash-lvgl BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem101
```

## Testing on Device

### Automated Smoke Test

```bash
make test-lvgl PORT=/dev/cu.usbmodem101
```

### Manual REPL Test

```python
import lvgl, time

lvgl.init_display()
scr = lvgl.lv_screen_active()
label = lvgl.lv_label_create(scr)
lvgl.lv_obj_center(label)
lvgl.lv_label_set_text(label, "Hello World")

for _ in range(200):
    lvgl.timer_handler()
    time.sleep_ms(10)
```

If display output appears stale after soft reset, use `machine.reset()` to perform a hard reset.

## Available Functions

The generated `lvgl` module exports LVGL APIs by category plus display-driver helpers.

| Category | Exported functions |
|---|---|
| Screen | `lv_screen_active`, `lv_screen_load` |
| Object core | `lv_obj_create`, `lv_obj_delete`, `lv_obj_clean`, `lv_obj_add_flag`, `lv_obj_remove_flag`, `lv_obj_add_state`, `lv_obj_remove_state`, `lv_obj_has_flag`, `lv_obj_has_state`, `lv_obj_set_user_data`, `lv_obj_is_valid` |
| Object position and size | `lv_obj_set_pos`, `lv_obj_set_x`, `lv_obj_set_y`, `lv_obj_set_size`, `lv_obj_set_width`, `lv_obj_set_height`, `lv_obj_set_content_width`, `lv_obj_set_content_height`, `lv_obj_set_layout`, `lv_obj_center`, `lv_obj_align`, `lv_obj_set_ext_click_area`, `lv_obj_get_x`, `lv_obj_get_y`, `lv_obj_get_width`, `lv_obj_get_height`, `lv_obj_get_content_width`, `lv_obj_get_content_height`, `lv_obj_get_self_width`, `lv_obj_get_self_height` |
| Object tree | `lv_obj_get_screen`, `lv_obj_get_parent`, `lv_obj_get_child`, `lv_obj_get_child_count`, `lv_obj_get_index` |
| Events | `lv_obj_add_event_cb`, `lv_event_get_code`, `lv_event_get_target_obj`, `lv_event_get_current_target_obj` |
| Widgets | `lv_button_create`, `lv_label_create`, `lv_label_set_text`, `lv_label_set_text_static`, `lv_label_set_long_mode`, `lv_label_set_recolor`, `lv_slider_create`, `lv_slider_set_value`, `lv_slider_set_range`, `lv_slider_set_min_value`, `lv_slider_set_max_value`, `lv_slider_get_value`, `lv_slider_get_min_value`, `lv_slider_get_max_value`, `lv_switch_create`, `lv_checkbox_create`, `lv_checkbox_set_text`, `lv_checkbox_set_text_static`, `lv_bar_create`, `lv_bar_set_value`, `lv_bar_set_range`, `lv_bar_get_value`, `lv_bar_get_min_value`, `lv_bar_get_max_value`, `lv_arc_create`, `lv_arc_set_value`, `lv_arc_set_range`, `lv_arc_set_rotation`, `lv_arc_get_value`, `lv_arc_get_min_value`, `lv_arc_get_max_value` |
| Display driver helpers | `init_display`, `timer_handler`, `backlight` |

## Architecture

Build pipeline:

```text
lvgl.pyi (stub) --> mpy-compile-c --> lvgl.c (generated)
                                      + st7789_driver.c (copied)
                                      + st7789_driver.h (copied)
                                      + lv_conf.h (copied)
                                      + micropython.cmake (copied)
                                      --> patch_lvgl_c.py patches lvgl.c
                                      --> build-lvgl (ESP-IDF build with larger partition)
```

Source-of-truth files now live in:

- `src/mypyc_micropython/c_bindings/stubs/lvgl/lvgl.pyi`
- `src/mypyc_micropython/c_bindings/stubs/lvgl/st7789_driver.c`
- `src/mypyc_micropython/c_bindings/stubs/lvgl/st7789_driver.h`
- `src/mypyc_micropython/c_bindings/stubs/lvgl/lv_conf.h`
- `src/mypyc_micropython/c_bindings/stubs/lvgl/micropython.cmake`

Generated output remains in `modules/usermod_lvgl/`.

## Customization

### Add more LVGL functions

1. Edit `src/mypyc_micropython/c_bindings/stubs/lvgl/lvgl.pyi`
2. Regenerate bindings:

```bash
make compile-lvgl
```

### Change display settings

Edit:

- `src/mypyc_micropython/c_bindings/stubs/lvgl/lv_conf.h`

Then rebuild:

```bash
make build-lvgl BOARD=ESP32_GENERIC_C6
```

### Use a different display panel

1. Add a new driver source/header in `src/mypyc_micropython/c_bindings/stubs/lvgl/`
2. Update `src/mypyc_micropython/c_bindings/stubs/lvgl/micropython.cmake`
3. Update `scripts/patch_lvgl_c.py` if new helper exports are needed
4. Re-run `make deploy-lvgl ...`

### Change partition size

Edit `partitions-lvgl.csv` and then rebuild/flash with LVGL targets.

## Troubleshooting

### `app partition is too small`

Cause: LVGL partition table was not applied.

Fix:

```bash
make clean-all BOARD=ESP32_GENERIC_C6
make deploy-lvgl BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem101
```

### `undefined reference to lvgl_user_cmodule`

Cause: LVGL module not included from `modules/micropython.cmake`.

Fix:

```bash
make compile-lvgl
make build-lvgl BOARD=ESP32_GENERIC_C6
```

### Display shows nothing after soft reset

Cause: C static state and MicroPython soft-reset state are out of sync.

Fix: run `machine.reset()` (hard reset), then test again.

### Flash fails

Check serial device and retry with explicit port:

```bash
ls /dev/cu.usb*
make flash-lvgl BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem101
```

## Hardware Reference

Target board: Waveshare ESP32-C6-LCD-1.47

| Parameter | Value |
|---|---|
| MCU | ESP32-C6 |
| Display controller | ST7789V |
| Resolution | 172 x 320 |
| Color depth | RGB565 (16-bit) |
| Interface | SPI (40MHz) |
| LCD controller width | 240 pixels |
| X offset | 34 pixels |

Related background: `blogs/22-lvgl-display-driver-esp32.md`.
