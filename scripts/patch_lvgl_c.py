#!/usr/bin/env python3
"""Patch generated lvgl.c with display-driver integration entries."""

from __future__ import annotations

import sys
from pathlib import Path

INCLUDE_LINE = '#include "st7789_driver.h"'
HEADER_MARKER = '#include "lvgl.h"'
GLOBALS_DICT_MARKER = "static MP_DEFINE_CONST_DICT(lvgl_module_globals, lvgl_module_globals_table);"
DRIVER_ENTRIES = (
    "    { MP_ROM_QSTR(MP_QSTR_init_display), MP_ROM_PTR(&lvgl_init_display_obj) },\n"
    "    { MP_ROM_QSTR(MP_QSTR_timer_handler), MP_ROM_PTR(&lvgl_timer_handler_obj) },\n"
    "    { MP_ROM_QSTR(MP_QSTR_backlight), MP_ROM_PTR(&lvgl_backlight_obj) },\n"
)


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")

    if INCLUDE_LINE not in text:
        if HEADER_MARKER not in text:
            raise RuntimeError(f"Expected marker not found: {HEADER_MARKER}")
        text = text.replace(HEADER_MARKER, f"{HEADER_MARKER}\n{INCLUDE_LINE}", 1)

    if "MP_QSTR_init_display" not in text:
        marker = f"}};\n{GLOBALS_DICT_MARKER}"
        if marker not in text:
            raise RuntimeError("Expected lvgl globals table marker not found")
        text = text.replace(marker, DRIVER_ENTRIES + marker, 1)

    path.write_text(text, encoding="utf-8")
    print(f"Patched {path}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: patch_lvgl_c.py <path-to-lvgl.c>", file=sys.stderr)
        return 1
    patch(Path(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
