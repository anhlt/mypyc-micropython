"""
LVGL bindings for MicroPython.

This stub file serves two purposes:
1. Source of truth for C code generation (mpy-compile-c reads this)
2. IDE support (PyCharm/VSCode read this for autocomplete)

Usage:
    # Generate C bindings
    mpy-compile-c lvgl.pyi -o output/

    # In your code (IDE will autocomplete)
    import lvgl as lv
    btn = lv.lv_btn_create(screen)
"""

__c_header__ = "lvgl.h"
__c_include_dirs__ = ["lib/lvgl/src"]

from typing import TypeVar, Generic, Callable

T = TypeVar("T")

class c_ptr(Generic[T]):
    """C pointer type. c_ptr[LvObj] represents lv_obj_t*"""

    pass

class c_int:
    """C int type (typically int32_t)"""

    pass

class c_uint:
    """C unsigned int type (typically uint32_t)"""

    pass

def c_struct(c_name: str, opaque: bool = True):
    """Decorator marking a class as a C struct wrapper."""
    def decorator(cls: type) -> type:
        return cls
    return decorator

def c_enum(c_name: str):
    """Decorator marking a class as a C enum wrapper."""
    def decorator(cls: type) -> type:
        return cls
    return decorator

@c_struct("lv_obj_t")
class LvObj:
    """
    Base LVGL object. All widgets inherit from this.

    In C: lv_obj_t*

    This is an opaque type - you cannot access its fields directly.
    Use the lv_obj_* functions to manipulate objects.
    """

    pass

@c_struct("lv_display_t")
class LvDisplay:
    """
    LVGL display driver.

    In C: lv_display_t*
    """

    pass

@c_struct("lv_event_t")
class LvEvent:
    """
    LVGL event object passed to event callbacks.

    In C: lv_event_t*
    """

    pass

@c_struct("lv_style_t")
class LvStyle:
    """
    LVGL style object for customizing widget appearance.

    In C: lv_style_t*
    """

    pass

@c_enum("lv_obj_flag_t")
class LvObjFlag:
    """Object behavior flags."""

    HIDDEN: int = 1 << 0
    CLICKABLE: int = 1 << 1
    CLICK_FOCUSABLE: int = 1 << 2
    CHECKABLE: int = 1 << 3
    SCROLLABLE: int = 1 << 4
    SCROLL_ELASTIC: int = 1 << 5
    SCROLL_MOMENTUM: int = 1 << 6
    SCROLL_ONE: int = 1 << 7
    SNAPPABLE: int = 1 << 14
    PRESS_LOCK: int = 1 << 15
    EVENT_BUBBLE: int = 1 << 16
    GESTURE_BUBBLE: int = 1 << 17
    ADV_HITTEST: int = 1 << 18
    IGNORE_LAYOUT: int = 1 << 19
    FLOATING: int = 1 << 20
    SEND_DRAW_TASK_EVENTS: int = 1 << 21
    OVERFLOW_VISIBLE: int = 1 << 22
    FLEX_IN_NEW_TRACK: int = 1 << 23
    LAYOUT_1: int = 1 << 24
    LAYOUT_2: int = 1 << 25
    WIDGET_1: int = 1 << 26
    WIDGET_2: int = 1 << 27
    USER_1: int = 1 << 28
    USER_2: int = 1 << 29
    USER_3: int = 1 << 30
    USER_4: int = 1 << 31

@c_enum("lv_event_code_t")
class LvEventCode:
    """Event types."""

    ALL: int = 0
    PRESSED: int = 1
    PRESSING: int = 2
    PRESS_LOST: int = 3
    SHORT_CLICKED: int = 4
    LONG_PRESSED: int = 5
    LONG_PRESSED_REPEAT: int = 6
    CLICKED: int = 7
    RELEASED: int = 8
    SCROLL_BEGIN: int = 9
    SCROLL_THROW_BEGIN: int = 10
    SCROLL_END: int = 11
    SCROLL: int = 12
    GESTURE: int = 13
    KEY: int = 14
    ROTARY: int = 15
    FOCUSED: int = 16
    DEFOCUSED: int = 17
    LEAVE: int = 18
    HIT_TEST: int = 19
    INDEV_RESET: int = 20
    HOVER_OVER: int = 21
    HOVER_LEAVE: int = 22
    COVER_CHECK: int = 23
    REFR_EXT_DRAW_SIZE: int = 24
    DRAW_MAIN_BEGIN: int = 25
    DRAW_MAIN: int = 26
    DRAW_MAIN_END: int = 27
    DRAW_POST_BEGIN: int = 28
    DRAW_POST: int = 29
    DRAW_POST_END: int = 30
    DRAW_TASK_ADDED: int = 31
    VALUE_CHANGED: int = 32
    INSERT: int = 33
    REFRESH: int = 34
    READY: int = 35
    CANCEL: int = 36
    CREATE: int = 37
    DELETE: int = 38
    CHILD_CHANGED: int = 39
    CHILD_CREATED: int = 40
    CHILD_DELETED: int = 41
    SCREEN_UNLOAD_START: int = 42
    SCREEN_LOAD_START: int = 43
    SCREEN_LOADED: int = 44
    SCREEN_UNLOADED: int = 45
    SIZE_CHANGED: int = 46
    STYLE_CHANGED: int = 47
    LAYOUT_CHANGED: int = 48
    GET_SELF_SIZE: int = 49

EventCallback = Callable[[c_ptr[LvEvent]], None]

def lv_screen_active() -> c_ptr[LvObj]:
    """
    Get the currently active screen.

    Returns:
        Pointer to the active screen object
    """
    ...

def lv_screen_load(scr: c_ptr[LvObj]) -> None:
    """
    Load a screen (make it active).

    Args:
        scr: Screen object to load
    """
    ...

def lv_obj_create(parent: c_ptr[LvObj] | None) -> c_ptr[LvObj]:
    """
    Create a new base object.

    Args:
        parent: Parent object, or None for screen-level object

    Returns:
        Pointer to the new object
    """
    ...

def lv_obj_delete(obj: c_ptr[LvObj]) -> None:
    """
    Delete an object and all its children.

    Args:
        obj: Object to delete
    """
    ...

def lv_obj_clean(obj: c_ptr[LvObj]) -> None:
    """
    Delete all children of an object.

    Args:
        obj: Object whose children to delete
    """
    ...

def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None:
    """
    Set the size of an object.

    Args:
        obj: Target object
        w: Width in pixels
        h: Height in pixels
    """
    ...

def lv_obj_set_width(obj: c_ptr[LvObj], w: c_int) -> None:
    """
    Set the width of an object.

    Args:
        obj: Target object
        w: Width in pixels
    """
    ...

def lv_obj_set_height(obj: c_ptr[LvObj], h: c_int) -> None:
    """
    Set the height of an object.

    Args:
        obj: Target object
        h: Height in pixels
    """
    ...

def lv_obj_set_pos(obj: c_ptr[LvObj], x: c_int, y: c_int) -> None:
    """
    Set the position of an object relative to its parent.

    Args:
        obj: Target object
        x: X coordinate in pixels
        y: Y coordinate in pixels
    """
    ...

def lv_obj_set_x(obj: c_ptr[LvObj], x: c_int) -> None:
    """
    Set the X position of an object.

    Args:
        obj: Target object
        x: X coordinate in pixels
    """
    ...

def lv_obj_set_y(obj: c_ptr[LvObj], y: c_int) -> None:
    """
    Set the Y position of an object.

    Args:
        obj: Target object
        y: Y coordinate in pixels
    """
    ...

def lv_obj_center(obj: c_ptr[LvObj]) -> None:
    """
    Center an object within its parent.

    Args:
        obj: Object to center
    """
    ...

def lv_obj_add_flag(obj: c_ptr[LvObj], flag: c_uint) -> None:
    """
    Add one or more flags to an object.

    Args:
        obj: Target object
        flag: Flag(s) to add (use LV_OBJ_FLAG_* constants)
    """
    ...

def lv_obj_remove_flag(obj: c_ptr[LvObj], flag: c_uint) -> None:
    """
    Remove one or more flags from an object.

    Args:
        obj: Target object
        flag: Flag(s) to remove
    """
    ...

def lv_obj_add_event_cb(
    obj: c_ptr[LvObj],
    event_cb: EventCallback,
    filter: c_int,
    user_data: c_ptr[object] | None = None,
) -> None:
    """
    Add an event handler to an object.

    Args:
        obj: Target object
        event_cb: Callback function
        filter: Event type to listen for (use LV_EVENT_* constants)
        user_data: Optional user data passed to callback
    """
    ...

def lv_event_get_code(e: c_ptr[LvEvent]) -> c_int:
    """
    Get the event code from an event object.

    Args:
        e: Event object

    Returns:
        Event code (LV_EVENT_* constant)
    """
    ...

def lv_event_get_target(e: c_ptr[LvEvent]) -> c_ptr[LvObj]:
    """
    Get the object that triggered the event.

    Args:
        e: Event object

    Returns:
        Object that triggered the event
    """
    ...

def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """
    Create a new button widget.

    Args:
        parent: Parent object

    Returns:
        Pointer to the new button
    """
    ...

def lv_label_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """
    Create a new label widget.

    Args:
        parent: Parent object

    Returns:
        Pointer to the new label
    """
    ...

def lv_label_set_text(label: c_ptr[LvObj], text: str) -> None:
    """
    Set the text of a label.

    Args:
        label: Label object
        text: Text to display
    """
    ...

def lv_label_set_text_fmt(label: c_ptr[LvObj], fmt: str, *args: object) -> None:
    """
    Set the text of a label using printf-style formatting.

    Args:
        label: Label object
        fmt: Format string
        args: Format arguments
    """
    ...

def lv_slider_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """
    Create a new slider widget.

    Args:
        parent: Parent object

    Returns:
        Pointer to the new slider
    """
    ...

def lv_slider_set_value(slider: c_ptr[LvObj], value: c_int, anim: c_int) -> None:
    """
    Set the value of a slider.

    Args:
        slider: Slider object
        value: New value
        anim: Animation enable (LV_ANIM_ON/OFF)
    """
    ...

def lv_slider_get_value(slider: c_ptr[LvObj]) -> c_int:
    """
    Get the current value of a slider.

    Args:
        slider: Slider object

    Returns:
        Current slider value
    """
    ...

def lv_slider_set_range(slider: c_ptr[LvObj], min_val: c_int, max_val: c_int) -> None:
    """
    Set the range of a slider.

    Args:
        slider: Slider object
        min_val: Minimum value
        max_val: Maximum value
    """
    ...

def lv_style_init(style: c_ptr[LvStyle]) -> None:
    """
    Initialize a style object.

    Args:
        style: Style object to initialize
    """
    ...

def lv_style_reset(style: c_ptr[LvStyle]) -> None:
    """
    Reset a style to default values.

    Args:
        style: Style object to reset
    """
    ...

def lv_obj_add_style(obj: c_ptr[LvObj], style: c_ptr[LvStyle], selector: c_uint) -> None:
    """
    Add a style to an object.

    Args:
        obj: Target object
        style: Style to add
        selector: Part and state selector
    """
    ...

def lv_obj_remove_style_all(obj: c_ptr[LvObj]) -> None:
    """
    Remove all styles from an object.

    Args:
        obj: Target object
    """
    ...
