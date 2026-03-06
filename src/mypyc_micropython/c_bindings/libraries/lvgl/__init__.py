"""LVGL library bindings.

Directory structure:
- stubs/  - .pyi type stub files for LVGL API
- drivers/ - Display and input drivers (C source)
- config/  - LVGL configuration files (lv_conf.h, micropython.cmake)
"""

from __future__ import annotations

from pathlib import Path

# Path helpers for accessing LVGL resources
LVGL_DIR = Path(__file__).parent
STUBS_DIR = LVGL_DIR / "stubs"
DRIVERS_DIR = LVGL_DIR / "drivers"
CONFIG_DIR = LVGL_DIR / "config"


def get_stub_path(name: str = "lvgl") -> Path:
    """Get path to an LVGL stub file."""
    return STUBS_DIR / f"{name}.pyi"


def get_config_path(name: str = "lv_conf.h") -> Path:
    """Get path to an LVGL config file."""
    return CONFIG_DIR / name


def get_driver_path(name: str) -> Path:
    """Get path to an LVGL driver file."""
    return DRIVERS_DIR / name
