"""LVGL v9 bindings for MicroPython.

Generated from deps/lvgl/ headers (v9.5.0).
"""

__c_header__ = "lvgl.h"
__c_include_dirs__ = ["deps/lvgl/src"]

from typing import Callable, Generic, TypeVar

T = TypeVar("T")

class c_ptr(Generic[T]):
    pass

class c_int:
    pass

class c_uint:
    pass

class c_bool:
    pass

class c_str:
    pass

def c_struct(c_name: str, opaque: bool = True):
    def decorator(cls: type) -> type:
        return cls
    return decorator

def c_enum(c_name: str):
    def decorator(cls: type) -> type:
        return cls
    return decorator

@c_struct("lv_obj_t")
class LvObj:
    pass

@c_struct("lv_display_t")
class LvDisplay:
    pass

@c_struct("lv_event_t")
class LvEvent:
    pass

@c_struct("lv_style_t")
class LvStyle:
    pass

@c_struct("lv_event_dsc_t")
class LvEventDsc:
    pass

@c_enum("lv_event_code_t")
class LvEventCode:
    ALL: int = 0
    PRESSED: int = 1
    PRESSING: int = 2
    PRESS_LOST: int = 3
    SHORT_CLICKED: int = 4
    SINGLE_CLICKED: int = 5
    DOUBLE_CLICKED: int = 6
    TRIPLE_CLICKED: int = 7
    LONG_PRESSED: int = 8
    LONG_PRESSED_REPEAT: int = 9
    CLICKED: int = 10
    RELEASED: int = 11
    SCROLL_BEGIN: int = 12
    SCROLL_THROW_BEGIN: int = 13
    SCROLL_END: int = 14
    SCROLL: int = 15
    GESTURE: int = 16
    KEY: int = 17
    ROTARY: int = 18
    FOCUSED: int = 19
    DEFOCUSED: int = 20
    LEAVE: int = 21
    HIT_TEST: int = 22
    INDEV_RESET: int = 23
    HOVER_OVER: int = 24
    HOVER_LEAVE: int = 25
    COVER_CHECK: int = 26
    REFR_EXT_DRAW_SIZE: int = 27
    DRAW_MAIN_BEGIN: int = 28
    DRAW_MAIN: int = 29
    DRAW_MAIN_END: int = 30
    DRAW_POST_BEGIN: int = 31
    DRAW_POST: int = 32
    DRAW_POST_END: int = 33
    DRAW_TASK_ADDED: int = 34
    VALUE_CHANGED: int = 35
    INSERT: int = 36
    REFRESH: int = 37
    READY: int = 38
    CANCEL: int = 39
    STATE_CHANGED: int = 40
    CREATE: int = 41
    DELETE: int = 42
    CHILD_CHANGED: int = 43
    CHILD_CREATED: int = 44
    CHILD_DELETED: int = 45
    SCREEN_UNLOAD_START: int = 46
    SCREEN_LOAD_START: int = 47
    SCREEN_LOADED: int = 48
    SCREEN_UNLOADED: int = 49
    SIZE_CHANGED: int = 50
    STYLE_CHANGED: int = 51
    LAYOUT_CHANGED: int = 52
    GET_SELF_SIZE: int = 53

@c_enum("lv_obj_flag_t")
class LvObjFlag:
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

@c_enum("lv_align_t")
class LvAlign:
    DEFAULT: int = 0
    TOP_LEFT: int = 1
    TOP_MID: int = 2
    TOP_RIGHT: int = 3
    BOTTOM_LEFT: int = 4
    BOTTOM_MID: int = 5
    BOTTOM_RIGHT: int = 6
    LEFT_MID: int = 7
    RIGHT_MID: int = 8
    CENTER: int = 9

EventCallback = Callable[[c_ptr[LvEvent]], None]

# -- Screen --

def lv_screen_active() -> c_ptr[LvObj]: ...
def lv_screen_load(scr: c_ptr[LvObj]) -> None: ...

# -- Object core --

def lv_obj_create(parent: c_ptr[LvObj] | None) -> c_ptr[LvObj]: ...
def lv_obj_delete(obj: c_ptr[LvObj]) -> None: ...
def lv_obj_clean(obj: c_ptr[LvObj]) -> None: ...
def lv_obj_add_flag(obj: c_ptr[LvObj], flag: c_uint) -> None: ...
def lv_obj_remove_flag(obj: c_ptr[LvObj], flag: c_uint) -> None: ...
def lv_obj_add_state(obj: c_ptr[LvObj], state: c_uint) -> None: ...
def lv_obj_remove_state(obj: c_ptr[LvObj], state: c_uint) -> None: ...
def lv_obj_has_flag(obj: c_ptr[LvObj], flag: c_uint) -> c_bool: ...
def lv_obj_has_state(obj: c_ptr[LvObj], state: c_uint) -> c_bool: ...
def lv_obj_set_user_data(obj: c_ptr[LvObj], user_data: c_ptr[object] | None) -> None: ...
def lv_obj_is_valid(obj: c_ptr[LvObj]) -> c_bool: ...

# -- Object position and size --

def lv_obj_set_pos(obj: c_ptr[LvObj], x: c_int, y: c_int) -> None: ...
def lv_obj_set_x(obj: c_ptr[LvObj], x: c_int) -> None: ...
def lv_obj_set_y(obj: c_ptr[LvObj], y: c_int) -> None: ...
def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None: ...
def lv_obj_set_width(obj: c_ptr[LvObj], w: c_int) -> None: ...
def lv_obj_set_height(obj: c_ptr[LvObj], h: c_int) -> None: ...
def lv_obj_set_content_width(obj: c_ptr[LvObj], w: c_int) -> None: ...
def lv_obj_set_content_height(obj: c_ptr[LvObj], h: c_int) -> None: ...
def lv_obj_set_layout(obj: c_ptr[LvObj], layout: c_uint) -> None: ...
def lv_obj_center(obj: c_ptr[LvObj]) -> None: ...
def lv_obj_align(obj: c_ptr[LvObj], align: c_int, x_ofs: c_int, y_ofs: c_int) -> None: ...
def lv_obj_set_ext_click_area(obj: c_ptr[LvObj], size: c_int) -> None: ...
def lv_obj_get_x(obj: c_ptr[LvObj]) -> c_int: ...
def lv_obj_get_y(obj: c_ptr[LvObj]) -> c_int: ...
def lv_obj_get_width(obj: c_ptr[LvObj]) -> c_int: ...
def lv_obj_get_height(obj: c_ptr[LvObj]) -> c_int: ...
def lv_obj_get_content_width(obj: c_ptr[LvObj]) -> c_int: ...
def lv_obj_get_content_height(obj: c_ptr[LvObj]) -> c_int: ...
def lv_obj_get_self_width(obj: c_ptr[LvObj]) -> c_int: ...
def lv_obj_get_self_height(obj: c_ptr[LvObj]) -> c_int: ...

# -- Object tree --

def lv_obj_get_screen(obj: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_obj_get_parent(obj: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_obj_get_child(obj: c_ptr[LvObj], idx: c_int) -> c_ptr[LvObj]: ...
def lv_obj_get_child_count(obj: c_ptr[LvObj]) -> c_uint: ...
def lv_obj_get_index(obj: c_ptr[LvObj]) -> c_uint: ...

# -- Events --

def lv_obj_add_event_cb(
    obj: c_ptr[LvObj],
    event_cb: EventCallback,
    filter: c_int,
    user_data: c_ptr[object] | None = None,
) -> None: ...
def lv_event_get_code(e: c_ptr[LvEvent]) -> c_int: ...
def lv_event_get_target_obj(e: c_ptr[LvEvent]) -> c_ptr[LvObj]: ...
def lv_event_get_current_target_obj(e: c_ptr[LvEvent]) -> c_ptr[LvObj]: ...

# -- Button widget (lv_button in v9) --

def lv_button_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...

# -- Label widget --

def lv_label_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_label_set_text(obj: c_ptr[LvObj], text: str) -> None: ...
def lv_label_set_text_static(obj: c_ptr[LvObj], text: str) -> None: ...
def lv_label_set_long_mode(obj: c_ptr[LvObj], long_mode: c_int) -> None: ...
def lv_label_set_recolor(obj: c_ptr[LvObj], en: c_bool) -> None: ...

# -- Slider widget --

def lv_slider_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_slider_set_value(obj: c_ptr[LvObj], value: c_int, anim: c_int) -> None: ...
def lv_slider_set_range(obj: c_ptr[LvObj], min_val: c_int, max_val: c_int) -> None: ...
def lv_slider_set_min_value(obj: c_ptr[LvObj], min_val: c_int) -> None: ...
def lv_slider_set_max_value(obj: c_ptr[LvObj], max_val: c_int) -> None: ...
def lv_slider_get_value(obj: c_ptr[LvObj]) -> c_int: ...
def lv_slider_get_min_value(obj: c_ptr[LvObj]) -> c_int: ...
def lv_slider_get_max_value(obj: c_ptr[LvObj]) -> c_int: ...

# -- Switch widget --

def lv_switch_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...

# -- Checkbox widget --

def lv_checkbox_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_checkbox_set_text(obj: c_ptr[LvObj], txt: str) -> None: ...
def lv_checkbox_set_text_static(obj: c_ptr[LvObj], txt: str) -> None: ...

# -- Bar widget --

def lv_bar_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_bar_set_value(obj: c_ptr[LvObj], value: c_int, anim: c_int) -> None: ...
def lv_bar_set_range(obj: c_ptr[LvObj], min_val: c_int, max_val: c_int) -> None: ...
def lv_bar_get_value(obj: c_ptr[LvObj]) -> c_int: ...
def lv_bar_get_min_value(obj: c_ptr[LvObj]) -> c_int: ...
def lv_bar_get_max_value(obj: c_ptr[LvObj]) -> c_int: ...

# -- Arc widget --

def lv_arc_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_arc_set_value(obj: c_ptr[LvObj], value: c_int) -> None: ...
def lv_arc_set_range(obj: c_ptr[LvObj], min_val: c_int, max_val: c_int) -> None: ...
def lv_arc_set_rotation(obj: c_ptr[LvObj], rotation: c_int) -> None: ...
def lv_arc_get_value(obj: c_ptr[LvObj]) -> c_int: ...
def lv_arc_get_min_value(obj: c_ptr[LvObj]) -> c_int: ...
def lv_arc_get_max_value(obj: c_ptr[LvObj]) -> c_int: ...
