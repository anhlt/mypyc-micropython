"""LVGL v9 Screen Operations Compatibility Shim

Provides minimal runtime compatibility for LVGL screen operations.
Pinned to LVGL v9 API names.
"""

import lvgl


def screen_active():
    """Get the currently active screen."""
    return lvgl.lv_screen_active()


def screen_load(scr):
    """Load a new screen."""
    return lvgl.lv_screen_load(scr)


def obj_delete(obj):
    """Delete a LVGL object."""
    return lvgl.lv_obj_delete(obj)
