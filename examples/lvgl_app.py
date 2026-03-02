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
    lv.lv_obj_align(label, 9, 0, 0)  # LvAlign.CENTER = 9
    return 0


def counter_label(n: int) -> int:
    """Create a label showing a counter value."""
    screen = lv.lv_screen_active()
    label = lv.lv_label_create(screen)
    lv.lv_label_set_text(label, "Count:")
    lv.lv_obj_align(label, 2, 0, 20)  # LvAlign.TOP_MID = 2
    return n


def slider_demo() -> int:
    """Create a slider widget."""
    screen = lv.lv_screen_active()
    slider = lv.lv_slider_create(screen)
    lv.lv_slider_set_range(slider, 0, 100)
    lv.lv_slider_set_value(slider, 50, 0)
    lv.lv_obj_center(slider)
    return lv.lv_slider_get_value(slider)


def styled_button() -> int:
    """Create a styled button with custom colors using new Style API."""
    screen = lv.lv_screen_active()
    btn = lv.lv_button_create(screen)
    lv.lv_obj_set_size(btn, 120, 50)
    lv.lv_obj_center(btn)

    # Use new color API
    bg_color = lv.lv_color_hex(0x2196F3)  # Material Blue
    lv.lv_obj_set_style_bg_color(btn, bg_color, 0)
    lv.lv_obj_set_style_bg_opa(btn, lv.LV_OPA_COVER, 0)

    # Add label to button
    label = lv.lv_label_create(btn)
    lv.lv_label_set_text(label, "Styled")
    lv.lv_obj_center(label)

    # Style the label text
    text_color = lv.lv_color_white()
    lv.lv_obj_set_style_text_color(label, text_color, 0)

    return 0


def palette_demo() -> int:
    """Demonstrate palette colors."""
    screen = lv.lv_screen_active()

    # Create container with flex layout
    cont = lv.lv_obj_create(screen)
    lv.lv_obj_set_size(cont, 200, 150)
    lv.lv_obj_center(cont)
    # LvFlexFlow.COLUMN = 0x01, LvFlexAlign.CENTER = 2
    lv.lv_obj_set_flex_flow(cont, 0x01)
    lv.lv_obj_set_flex_align(cont, 2, 2, 2)

    # Create labels with different palette colors
    # LvPalette: RED=0, GREEN=9, BLUE=5
    label1 = lv.lv_label_create(cont)
    lv.lv_label_set_text(label1, "Red")
    red = lv.lv_palette_main(0)  # RED
    lv.lv_obj_set_style_text_color(label1, red, 0)

    label2 = lv.lv_label_create(cont)
    lv.lv_label_set_text(label2, "Green")
    green = lv.lv_palette_main(9)  # GREEN
    lv.lv_obj_set_style_text_color(label2, green, 0)

    label3 = lv.lv_label_create(cont)
    lv.lv_label_set_text(label3, "Blue")
    blue = lv.lv_palette_main(5)  # BLUE
    lv.lv_obj_set_style_text_color(label3, blue, 0)

    return 0


def flex_row_demo() -> int:
    """Demonstrate flex row layout."""
    screen = lv.lv_screen_active()

    cont = lv.lv_obj_create(screen)
    lv.lv_obj_set_size(cont, 280, 60)
    lv.lv_obj_center(cont)
    # LvFlexFlow.ROW = 0x00, LvFlexAlign.SPACE_EVENLY = 3, LvFlexAlign.CENTER = 2
    lv.lv_obj_set_flex_flow(cont, 0x00)
    lv.lv_obj_set_flex_align(cont, 3, 2, 2)

    # Add 3 buttons
    btn1 = lv.lv_button_create(cont)
    lv.lv_obj_set_size(btn1, 60, 40)
    label1 = lv.lv_label_create(btn1)
    lv.lv_label_set_text(label1, "A")
    lv.lv_obj_center(label1)

    btn2 = lv.lv_button_create(cont)
    lv.lv_obj_set_size(btn2, 60, 40)
    label2 = lv.lv_label_create(btn2)
    lv.lv_label_set_text(label2, "B")
    lv.lv_obj_center(label2)

    btn3 = lv.lv_button_create(cont)
    lv.lv_obj_set_size(btn3, 60, 40)
    label3 = lv.lv_label_create(btn3)
    lv.lv_label_set_text(label3, "C")
    lv.lv_obj_center(label3)

    return 0


def bar_with_style() -> int:
    """Create a progress bar with custom styling."""
    screen = lv.lv_screen_active()

    bar = lv.lv_bar_create(screen)
    lv.lv_obj_set_size(bar, 200, 20)
    lv.lv_obj_center(bar)
    lv.lv_bar_set_range(bar, 0, 100)
    lv.lv_bar_set_value(bar, 70, lv.LV_ANIM_OFF)

    # Style the background - LvPart.MAIN = 0x000000
    bg_color = lv.lv_palette_lighten(18, 2)  # GREY=18, lighten by 2
    lv.lv_obj_set_style_bg_color(bar, bg_color, 0x000000)
    lv.lv_obj_set_style_radius(bar, 5, 0x000000)

    # Style the indicator - LvPart.INDICATOR = 0x020000
    ind_color = lv.lv_palette_main(5)  # BLUE=5
    lv.lv_obj_set_style_bg_color(bar, ind_color, 0x020000)
    lv.lv_obj_set_style_radius(bar, 5, 0x020000)

    return lv.lv_bar_get_value(bar)


def arc_demo() -> int:
    """Create an arc with styling."""
    screen = lv.lv_screen_active()

    arc = lv.lv_arc_create(screen)
    lv.lv_obj_set_size(arc, 150, 150)
    lv.lv_obj_center(arc)
    lv.lv_arc_set_rotation(arc, 135)
    lv.lv_arc_set_range(arc, 0, 100)
    lv.lv_arc_set_value(arc, 75)

    # Style the arc - LvPart.KNOB = 0x030000, CYAN=7
    arc_color = lv.lv_palette_main(7)
    lv.lv_obj_set_style_bg_color(arc, arc_color, 0x030000)

    return lv.lv_arc_get_value(arc)


def dropdown_demo() -> int:
    """Create a dropdown widget."""
    screen = lv.lv_screen_active()

    dd = lv.lv_dropdown_create(screen)
    lv.lv_dropdown_set_options(dd, "A;B;C;D")
    lv.lv_dropdown_set_selected(dd, 1)
    lv.lv_obj_set_width(dd, 150)
    lv.lv_obj_center(dd)

    return lv.lv_dropdown_get_selected(dd)


def checkbox_switch_demo() -> int:
    """Create checkbox and switch widgets."""
    screen = lv.lv_screen_active()

    # Container with flex - LvFlexFlow.COLUMN=0x01, LvFlexAlign: CENTER=2, START=0
    cont = lv.lv_obj_create(screen)
    lv.lv_obj_set_size(cont, 200, 100)
    lv.lv_obj_center(cont)
    lv.lv_obj_set_flex_flow(cont, 0x01)
    lv.lv_obj_set_flex_align(cont, 2, 0, 2)
    lv.lv_obj_set_style_pad_row(cont, 10, 0)

    # Checkbox - LvState.CHECKED = 0x0001
    cb = lv.lv_checkbox_create(cont)
    lv.lv_checkbox_set_text(cb, "Enable feature")
    lv.lv_obj_add_state(cb, 0x0001)

    # Switch
    sw = lv.lv_switch_create(cont)
    lv.lv_obj_add_state(sw, 0x0001)

    return 0
