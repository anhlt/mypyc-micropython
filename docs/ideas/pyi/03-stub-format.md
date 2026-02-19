# Stub Format Specification

> **Version**: 0.1 Draft  
> **Status**: Proposal

## Overview

This document defines the `.pyi` stub file format for C library bindings.

## File Structure

```python
"""
Module docstring - becomes C comment header.
"""

# Module-level metadata
__c_header__ = "lvgl.h"  # Required: C header to include
__c_include_dirs__ = ["src/"]  # Optional: include paths

# Type imports (for IDE support)
from typing import TypeVar, Generic, Callable

# C type markers
from mypyc_micropython.c_types import c_ptr, c_int, c_struct, c_enum

# Struct definitions
@c_struct("c_name")
class PythonName: ...

# Enum definitions  
@c_enum("c_name")
class EnumName:
    VALUE1: int = 0
    VALUE2: int = 1

# Function declarations
def function_name(param: type) -> return_type:
    """Docstring becomes C comment."""
    ...

# Callback type aliases
CallbackType = Callable[[param_types], return_type]
```

## C Type Markers

### Primitive Types

| Python Type | C Type | Conversion (Python→C) | Conversion (C→Python) |
|-------------|--------|----------------------|----------------------|
| `c_void` | `void` | N/A | `mp_const_none` |
| `c_int` | `int` | `mp_obj_get_int()` | `mp_obj_new_int()` |
| `c_uint` | `unsigned int` | `(unsigned)mp_obj_get_int()` | `mp_obj_new_int_from_uint()` |
| `c_int8` | `int8_t` | `(int8_t)mp_obj_get_int()` | `mp_obj_new_int()` |
| `c_uint8` | `uint8_t` | `(uint8_t)mp_obj_get_int()` | `mp_obj_new_int()` |
| `c_int16` | `int16_t` | `(int16_t)mp_obj_get_int()` | `mp_obj_new_int()` |
| `c_uint16` | `uint16_t` | `(uint16_t)mp_obj_get_int()` | `mp_obj_new_int()` |
| `c_int32` | `int32_t` | `(int32_t)mp_obj_get_int()` | `mp_obj_new_int()` |
| `c_uint32` | `uint32_t` | `(uint32_t)mp_obj_get_int()` | `mp_obj_new_int_from_uint()` |
| `c_float` | `float` | `(float)mp_obj_get_float()` | `mp_obj_new_float()` |
| `c_double` | `double` | `mp_obj_get_float()` | `mp_obj_new_float()` |
| `c_bool` | `bool` | `mp_obj_is_true()` | `mp_obj_new_bool()` |
| `c_str` | `const char*` | `mp_obj_str_get_str()` | `mp_obj_new_str()` |

### Python Builtins (Auto-mapped)

| Python Type | Maps To |
|-------------|---------|
| `int` | `c_int` |
| `float` | `c_double` |
| `bool` | `c_bool` |
| `str` | `c_str` |
| `None` | `c_void` |

### Pointer Types

```python
c_ptr[T]  # Pointer to struct T -> T*
```

Example:
```python
c_ptr[LvObj]  # -> lv_obj_t*
c_ptr[c_void]  # -> void*
```

## Struct Definitions

### Opaque Structs (Default)

Most C library structs are opaque - you only use pointers to them:

```python
@c_struct("lv_obj_t")
class LvObj:
    """Base LVGL object type."""
    pass
```

Generated C:
```c
// No struct definition needed - just use lv_obj_t* from header
```

### Non-Opaque Structs

For structs where you need field access:

```python
@c_struct("lv_point_t", opaque=False)
class LvPoint:
    """2D point with x,y coordinates."""
    x: c_int
    y: c_int
```

Generated C:
```c
// Field accessors generated
static mp_obj_t LvPoint_get_x(mp_obj_t self_in) {
    lv_point_t *self = mp_to_ptr(self_in);
    return mp_obj_new_int(self->x);
}
```

## Enum Definitions

```python
@c_enum("lv_align_t")
class LvAlign:
    """Alignment options for objects."""
    CENTER: int = 0
    TOP_LEFT: int = 1
    TOP_MID: int = 2
    TOP_RIGHT: int = 3
    # ...
```

Generated C:
```c
// Constants added to module
{ MP_ROM_QSTR(MP_QSTR_LV_ALIGN_CENTER), MP_ROM_INT(0) },
{ MP_ROM_QSTR(MP_QSTR_LV_ALIGN_TOP_LEFT), MP_ROM_INT(1) },
```

## Function Declarations

### Basic Functions

```python
def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None:
    """Set the size of an object in pixels."""
    ...
```

Generated C:
```c
static mp_obj_t lv_obj_set_size_wrapper(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    mp_int_t c_w = mp_obj_get_int(arg1);
    mp_int_t c_h = mp_obj_get_int(arg2);
    lv_obj_set_size(c_obj, c_w, c_h);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(lv_obj_set_size_obj, lv_obj_set_size_wrapper);
```

### Functions with Return Values

```python
def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """Create a new button widget."""
    ...
```

Generated C:
```c
static mp_obj_t lv_btn_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = mp_to_ptr(arg0);
    lv_obj_t *result = lv_btn_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_btn_create_obj, lv_btn_create_wrapper);
```

### Functions with Optional Parameters

```python
def lv_obj_create(parent: c_ptr[LvObj] | None = None) -> c_ptr[LvObj]:
    """Create a base object. Pass None for screen-level object."""
    ...
```

Generated C:
```c
static mp_obj_t lv_obj_create_wrapper(size_t n_args, const mp_obj_t *args) {
    lv_obj_t *c_parent = (n_args > 0 && args[0] != mp_const_none) 
        ? mp_to_ptr(args[0]) : NULL;
    lv_obj_t *result = lv_obj_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lv_obj_create_obj, 0, 1, lv_obj_create_wrapper);
```

## Callback Types

### Definition

```python
# Type alias for callback signature
EventCallback = Callable[[c_ptr[LvEvent]], None]

def lv_obj_add_event_cb(
    obj: c_ptr[LvObj],
    event_cb: EventCallback,
    filter: c_int,
    user_data: c_ptr[c_void] | None = None
) -> None:
    """Add an event handler to an object."""
    ...
```

### Generated C (Callback Trampoline)

```c
// Store Python callback
static mp_obj_t stored_callback;

// C trampoline that calls Python
static void event_cb_trampoline(lv_event_t *e) {
    mp_obj_t arg = ptr_to_mp((void *)e);
    mp_call_function_1(stored_callback, arg);
}

static mp_obj_t lv_obj_add_event_cb_wrapper(size_t n_args, const mp_obj_t *args) {
    lv_obj_t *c_obj = mp_to_ptr(args[0]);
    stored_callback = args[1];  // Store Python callable
    lv_event_code_t c_filter = mp_obj_get_int(args[2]);
    void *c_user_data = (n_args > 3) ? mp_to_ptr(args[3]) : NULL;
    
    lv_obj_add_event_cb(c_obj, event_cb_trampoline, c_filter, c_user_data);
    return mp_const_none;
}
```

## Module Metadata

### Required

```python
__c_header__ = "lvgl.h"  # C header file to include
```

Generated:
```c
#include "lvgl.h"
```

### Optional

```python
__c_include_dirs__ = ["src/", "lib/lvgl/"]  # Additional include paths
__c_libraries__ = ["lvgl"]  # Libraries to link
__c_defines__ = ["LV_CONF_INCLUDE_SIMPLE"]  # Preprocessor defines
```

Generated in `micropython.cmake`:
```cmake
target_include_directories(usermod_lvgl INTERFACE src/ lib/lvgl/)
target_link_libraries(usermod_lvgl INTERFACE lvgl)
target_compile_definitions(usermod_lvgl INTERFACE LV_CONF_INCLUDE_SIMPLE)
```

## Complete Example

```python
"""
LVGL bindings for MicroPython.

Provides access to LVGL graphics library functions.
"""

__c_header__ = "lvgl.h"

from typing import Callable
from mypyc_micropython.c_types import c_ptr, c_int, c_uint, c_struct, c_enum

# Structs
@c_struct("lv_obj_t")
class LvObj:
    """Base LVGL object - all widgets inherit from this."""
    pass

@c_struct("lv_event_t")
class LvEvent:
    """Event object passed to callbacks."""
    pass

# Enums
@c_enum("lv_event_code_t")
class LvEventCode:
    CLICKED: int = 7
    VALUE_CHANGED: int = 28
    READY: int = 31

# Callbacks
EventCallback = Callable[[c_ptr[LvEvent]], None]

# Functions
def lv_screen_active() -> c_ptr[LvObj]:
    """Get the currently active screen."""
    ...

def lv_obj_create(parent: c_ptr[LvObj] | None) -> c_ptr[LvObj]:
    """Create a new base object."""
    ...

def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """Create a button widget."""
    ...

def lv_label_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """Create a label widget."""
    ...

def lv_label_set_text(label: c_ptr[LvObj], text: str) -> None:
    """Set the text content of a label."""
    ...

def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None:
    """Set the size of an object in pixels."""
    ...

def lv_obj_center(obj: c_ptr[LvObj]) -> None:
    """Center an object within its parent."""
    ...

def lv_obj_add_event_cb(
    obj: c_ptr[LvObj],
    event_cb: EventCallback,
    filter: c_int,
    user_data: c_ptr[c_void] | None = None
) -> None:
    """Register an event callback for an object."""
    ...
```
