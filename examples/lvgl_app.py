"""LVGL UI application - compiled with cross-module CLib calls.

This module demonstrates calling external C library (LVGL) functions
from typed Python compiled to C. The compiler resolves lv.func() calls
to direct wrapper function calls at compile time.
"""

import lvgl as lv


def hello_label() -> int:
    """Create a label with 'Hello from mypyc!' on the active screen."""
    screen = lv.lv_screen_active()
    label = lv.lv_label_create(screen)
    lv.lv_label_set_text(label, "Hello from mypyc!")
    lv.lv_obj_align(label, lv.LvAlign.CENTER, 0, 0)
    return 0


def counter_label(n: int) -> int:
    """Create a label showing a counter value."""
    screen = lv.lv_screen_active()
    label = lv.lv_label_create(screen)
    lv.lv_label_set_text(label, "Count:")
    lv.lv_obj_align(label, lv.LvAlign.TOP_MID, 0, 20)
    return n


def slider_demo() -> int:
    """Create a slider widget."""
    screen = lv.lv_screen_active()
    slider = lv.lv_slider_create(screen)
    lv.lv_slider_set_range(slider, 0, 100)
    lv.lv_slider_set_value(slider, 50, 0)
    lv.lv_obj_center(slider)
    return lv.lv_slider_get_value(slider)
