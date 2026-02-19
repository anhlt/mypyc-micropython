"""
Example MicroPython application using LVGL bindings.

This file demonstrates:
1. How user code looks when using LVGL via .pyi stubs
2. IDE autocomplete and type checking work
3. The code that mypyc-micropython would compile

Run with:
    # On device with LVGL bindings
    import my_app
    my_app.main()
"""

import lvgl as lv


def create_button(parent: lv.c_ptr[lv.LvObj], text: str) -> lv.c_ptr[lv.LvObj]:
    """
    Create a button with a centered label.

    Args:
        parent: Parent object to attach button to
        text: Button label text

    Returns:
        The created button object
    """
    btn = lv.lv_btn_create(parent)
    lv.lv_obj_set_size(btn, 120, 50)
    lv.lv_obj_center(btn)

    label = lv.lv_label_create(btn)
    lv.lv_label_set_text(label, text)
    lv.lv_obj_center(label)

    return btn


def on_button_click(event: lv.c_ptr[lv.LvEvent]) -> None:
    """Handle button click event."""
    code = lv.lv_event_get_code(event)
    if code == lv.LvEventCode.CLICKED:
        target = lv.lv_event_get_target(event)
        print("Button clicked!")


def create_slider(parent: lv.c_ptr[lv.LvObj]) -> lv.c_ptr[lv.LvObj]:
    """Create a slider with default range 0-100."""
    slider = lv.lv_slider_create(parent)
    lv.lv_slider_set_range(slider, 0, 100)
    lv.lv_slider_set_value(slider, 50, 0)
    lv.lv_obj_set_size(slider, 200, 20)
    return slider


def on_slider_change(event: lv.c_ptr[lv.LvEvent]) -> None:
    """Handle slider value change."""
    code = lv.lv_event_get_code(event)
    if code == lv.LvEventCode.VALUE_CHANGED:
        target = lv.lv_event_get_target(event)
        value = lv.lv_slider_get_value(target)
        print(f"Slider value: {value}")


def main() -> None:
    """
    Main application entry point.

    Creates a simple UI with:
    - A centered button
    - A slider below it
    - Event handlers for both
    """
    screen = lv.lv_screen_active()

    btn = create_button(screen, "Click Me!")
    lv.lv_obj_set_pos(btn, 0, -40)
    lv.lv_obj_add_event_cb(btn, on_button_click, lv.LvEventCode.CLICKED, None)

    slider = create_slider(screen)
    lv.lv_obj_set_pos(slider, 0, 40)
    lv.lv_obj_center(slider)
    lv.lv_obj_add_event_cb(slider, on_slider_change, lv.LvEventCode.VALUE_CHANGED, None)

    print("UI created successfully!")


if __name__ == "__main__":
    main()
