# AGENTS.md - C Bindings Generator

Generates MicroPython C wrappers from Python `.pyi` type stub files for external C libraries.

## Quick Reference

```bash
# Compile C library stubs
mpy-compile-c src/mypyc_micropython/c_bindings/libraries/lvgl/stubs/lvgl.pyi -o modules/usermod_lvgl

# With verbose output
mpy-compile-c lvgl.pyi -o output/ -v
```

## Purpose

This is a **separate compilation pipeline** from the main compiler:
- **Main compiler**: Python source to C modules
- **C bindings**: C library stubs to C wrappers

```
.pyi stub file --> StubParser --> CLibraryDef (IR) --> CEmitter --> C wrapper code
                                                   --> CMakeEmitter --> micropython.cmake
```

## File Overview

| File | LOC | Purpose |
|------|-----|---------|
| `core/c_ir.py` | 153 | IR definitions (CType, CStructDef, CFuncDef, etc.) |
| `core/stub_parser.py` | 307 | Parse .pyi stubs to CLibraryDef |
| `core/c_emitter.py` | 524 | Generate C wrapper code |
| `core/cmake_emitter.py` | 49 | Generate micropython.cmake |
| `core/compiler.py` | 103 | Orchestration |
| `core/c_types.py` | ~100 | Type markers for .pyi files |
| `cli.py` | ~80 | CLI entry point |
| `libraries/lvgl/` | - | LVGL v9 bindings |

## Writing .pyi Stub Files

### Module Metadata

```python
__c_header__ = "lvgl.h"                    # C header to include
__c_include_dirs__ = ["deps/lvgl/src"]     # Include directories
__c_libraries__ = ["lvgl"]                 # Libraries to link
__c_defines__ = ["LV_CONF_INCLUDE_SIMPLE"] # Compiler defines
```

### Struct Definitions

```python
from mypyc_micropython.c_bindings import c_struct, c_ptr

@c_struct("lv_obj_t")  # Opaque by default (pointer-based)
class LvObj: pass

@c_struct("lv_point_t", opaque=False)  # Value struct (copy-based)
class LvPoint:
    x: c_int
    y: c_int
```

### Enum Definitions

```python
from mypyc_micropython.c_bindings import c_enum

@c_enum("lv_event_code_t")
class LvEventCode:
    PRESSED: int = 1
    CLICKED: int = 4
    RELEASED: int = 11

@c_enum("lv_obj_flag_t")
class LvObjFlag:
    HIDDEN: int = 1 << 0      # Bitwise expressions supported
    CLICKABLE: int = 1 << 1
    SCROLLABLE: int = 1 << 4
```

### Function Signatures

```python
from mypyc_micropython.c_bindings import c_ptr, c_int, c_void

def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_obj_set_pos(obj: c_ptr[LvObj], x: c_int, y: c_int) -> None: ...
def lv_obj_get_user_data(obj: c_ptr[LvObj]) -> c_ptr[c_void]: ...
```

### Callback Types

```python
from typing import Callable

EventCallback = Callable[[c_ptr[LvEvent]], None]

def lv_obj_add_event_cb(
    obj: c_ptr[LvObj],
    event_cb: EventCallback,
    event_code: c_int,
    user_data: c_ptr[c_void]
) -> None: ...
```

## Generated Code Patterns

### Opaque Struct Wrapper

```c
typedef struct {
    mp_obj_base_t base;
    void *ptr;
} mp_c_ptr_t;

static mp_obj_t wrap_LvObj(lv_obj_t *ptr) {
    if (ptr == NULL) return mp_const_none;
    mp_c_ptr_t *o = mp_obj_malloc(mp_c_ptr_t, &mp_type_LvObj);
    o->ptr = ptr;
    return MP_OBJ_FROM_PTR(o);
}
```

### Function Wrapper

```c
static mp_obj_t lv_btn_create_wrapper(mp_obj_t parent_obj) {
    lv_obj_t *c_parent = unwrap_LvObj(parent_obj);  // Unbox
    lv_obj_t *result = lv_btn_create(c_parent);      // Call C
    return wrap_LvObj(result);                        // Box
}
MP_DEFINE_CONST_FUN_OBJ_1(lv_btn_create_obj, lv_btn_create_wrapper);
```

### Callback Trampoline

```c
static mp_obj_t lvgl_cb_registry[32];  // Callback storage
static int lvgl_cb_count = 0;

static void event_cb_trampoline(lv_event_t *event) {
    int idx = (int)(intptr_t)lv_event_get_user_data(event);
    if (idx >= 0 && idx < lvgl_cb_count) {
        mp_obj_t cb = lvgl_cb_registry[idx];
        mp_obj_t args[1] = { wrap_LvEvent(event) };
        mp_call_function_n_kw(cb, 1, 0, args);
    }
}
```

## Available C Types

| Python Type | C Type | Notes |
|-------------|--------|-------|
| `c_int` | `mp_int_t` | Signed integer |
| `c_uint` | `mp_uint_t` | Unsigned integer |
| `c_int8`..`c_uint32` | `int8_t`..`uint32_t` | Fixed-width |
| `c_float` | `float` | Single precision |
| `c_double` | `double` | Double precision |
| `c_bool` | `bool` | Boolean |
| `c_str` | `const char*` | String |
| `c_void` | `void` | Void type |
| `c_ptr[T]` | `T*` | Pointer to T |

## LVGL Bindings

Pre-built bindings for LVGL v9 graphics library:

```
libraries/lvgl/
├── stubs/
│   └── lvgl.pyi           # 772 lines of type stubs
└── config/
    ├── lv_conf.h          # LVGL configuration
    └── micropython.cmake  # Build integration
```

### Supported LVGL Features

- **Structs**: LvObj, LvDisplay, LvEvent, LvPoint, LvArea
- **Enums**: LvEventCode, LvObjFlag, LvAlign, LvDir (with bitwise flags)
- **Functions**: Object creation, styling, event handling
- **Callbacks**: Event callbacks with user_data

## Adding New Library Bindings

1. Create directory: `libraries/<name>/`
2. Create stub file: `libraries/<name>/stubs/<name>.pyi`
3. Add metadata and type definitions
4. Compile: `mpy-compile-c libraries/<name>/stubs/<name>.pyi -o modules/usermod_<name>`

## Relationship to Main Compiler

This is **independent** of the main Python-to-C compiler:
- Does NOT use `ir.py`, `ir_builder.py`, or the main emitters
- Has its own IR (`c_ir.py`) and emitter (`c_emitter.py`)
- Shares only the `CompilationResult` dataclass pattern

Use this when binding existing C libraries. Use the main compiler when compiling Python code.
