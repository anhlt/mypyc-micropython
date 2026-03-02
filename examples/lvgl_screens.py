"""Compiled LVGL screen manager for native performance.

This is a simplified, type-annotated version designed for mypyc compilation.
"""

import lvgl as lv


def screen_load(scr: object) -> None:
    """Load a screen."""
    lv.lv_screen_load(scr)


def screen_active() -> object:
    """Get active screen."""
    return lv.lv_screen_active()


def obj_delete(obj: object) -> None:
    """Delete an LVGL object."""
    lv.lv_obj_delete(obj)


def obj_clean(obj: object) -> None:
    """Clean all children from an object."""
    lv.lv_obj_clean(obj)


def timer_handler() -> int:
    """Run LVGL timer handler."""
    return lv.timer_handler()


def create_label(parent: object, text: str) -> object:
    """Create a label widget."""
    label = lv.lv_label_create(parent)
    lv.lv_label_set_text(label, text)
    return label


def create_button(parent: object, text: str, width: int, height: int) -> object:
    """Create a styled button with label."""
    btn = lv.lv_button_create(parent)
    lv.lv_obj_set_size(btn, width, height)

    label = lv.lv_label_create(btn)
    lv.lv_label_set_text(label, text)
    lv.lv_obj_center(label)

    return btn


def create_slider(parent: object, min_val: int, max_val: int, value: int) -> object:
    """Create a slider widget."""
    slider = lv.lv_slider_create(parent)
    lv.lv_slider_set_range(slider, min_val, max_val)
    lv.lv_slider_set_value(slider, value, 0)
    lv.lv_obj_center(slider)
    return slider


def create_bar(parent: object, min_val: int, max_val: int, value: int) -> object:
    """Create a progress bar widget."""
    bar = lv.lv_bar_create(parent)
    lv.lv_obj_set_size(bar, 200, 20)
    lv.lv_bar_set_range(bar, min_val, max_val)
    lv.lv_bar_set_value(bar, value, 0)
    lv.lv_obj_center(bar)
    return bar


def create_arc(parent: object, min_val: int, max_val: int, value: int) -> object:
    """Create an arc widget."""
    arc = lv.lv_arc_create(parent)
    lv.lv_obj_set_size(arc, 150, 150)
    lv.lv_arc_set_range(arc, min_val, max_val)
    lv.lv_arc_set_value(arc, value)
    lv.lv_obj_center(arc)
    return arc


def create_switch(parent: object, checked: bool) -> object:
    """Create a switch widget."""
    sw = lv.lv_switch_create(parent)
    if checked:
        lv.lv_obj_add_state(sw, 0x0001)  # LV_STATE_CHECKED
    return sw


def create_checkbox(parent: object, text: str, checked: bool) -> object:
    """Create a checkbox widget."""
    cb = lv.lv_checkbox_create(parent)
    lv.lv_checkbox_set_text(cb, text)
    if checked:
        lv.lv_obj_add_state(cb, 0x0001)  # LV_STATE_CHECKED
    return cb


def set_flex_column(obj: object) -> None:
    """Set flex column layout on object."""
    lv.lv_obj_set_flex_flow(obj, 0x01)  # LV_FLEX_FLOW_COLUMN
    lv.lv_obj_set_flex_align(obj, 2, 2, 2)  # CENTER


def set_flex_row(obj: object) -> None:
    """Set flex row layout on object."""
    lv.lv_obj_set_flex_flow(obj, 0x00)  # LV_FLEX_FLOW_ROW
    lv.lv_obj_set_flex_align(obj, 3, 2, 2)  # SPACE_EVENLY, CENTER


def set_style_bg_color(obj: object, color_hex: int, part: int) -> None:
    """Set background color."""
    color = lv.lv_color_hex(color_hex)
    lv.lv_obj_set_style_bg_color(obj, color, part)
    lv.lv_obj_set_style_bg_opa(obj, 255, part)  # LV_OPA_COVER


def set_style_text_color(obj: object, color_hex: int) -> None:
    """Set text color."""
    color = lv.lv_color_hex(color_hex)
    lv.lv_obj_set_style_text_color(obj, color, 0)


def create_container(parent: object, width: int, height: int) -> object:
    """Create a container object."""
    cont = lv.lv_obj_create(parent)
    lv.lv_obj_set_size(cont, width, height)
    lv.lv_obj_center(cont)
    return cont


def create_screen() -> object:
    """Create a new screen."""
    return lv.lv_obj_create(None)


def get_slider_value(slider: object) -> int:
    """Get slider value."""
    return lv.lv_slider_get_value(slider)


def get_bar_value(bar: object) -> int:
    """Get bar value."""
    return lv.lv_bar_get_value(bar)


def get_arc_value(arc: object) -> int:
    """Get arc value."""
    return lv.lv_arc_get_value(arc)


def show_screen(screen: object, old: object) -> None:
    """Show a screen and optionally clean up a previous one."""
    screen_load(screen)
    if old is not None:
        obj_delete(old)


def build_home_screen() -> object:
    """Build home screen with navigation buttons."""
    scr = create_screen()

    cont = create_container(scr, 280, 200)
    set_flex_column(cont)

    create_label(cont, "Home Screen")
    create_button(cont, "Slider", 120, 40)
    create_button(cont, "Progress", 120, 40)
    create_button(cont, "Arc", 120, 40)

    return scr


def build_slider_screen() -> object:
    """Build slider demo screen."""
    scr = create_screen()

    create_label(scr, "Slider Demo")
    create_slider(scr, 0, 100, 50)

    return scr


def build_progress_screen() -> object:
    """Build progress bar demo screen."""
    scr = create_screen()

    create_label(scr, "Progress Demo")
    bar = create_bar(scr, 0, 100, 70)
    set_style_bg_color(bar, 0x2196F3, 0x020000)  # Blue indicator

    return scr


def build_arc_screen() -> object:
    """Build arc demo screen."""
    scr = create_screen()

    create_label(scr, "Arc Demo")
    create_arc(scr, 0, 100, 75)

    return scr


def build_controls_screen() -> object:
    """Build controls demo screen."""
    scr = create_screen()

    cont = create_container(scr, 200, 150)
    set_flex_column(cont)

    create_label(cont, "Controls")
    create_checkbox(cont, "Option 1", True)
    create_checkbox(cont, "Option 2", False)
    create_switch(cont, True)

    return scr
