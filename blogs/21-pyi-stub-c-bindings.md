# .pyi Stub-Based C Bindings: Calling Native Libraries from MicroPython

*Using Python type stubs to auto-generate MicroPython C modules -- bridging LVGL, ESP-IDF, and any C library without writing a single line of wrapper code by hand.*

---

Until now, this compiler translated typed Python functions into C. But what about the other direction -- calling *existing* C libraries from Python? LVGL alone has over 2,000 functions. Writing MicroPython wrappers by hand for even 55 of them would be tedious and error-prone. This post shows how we built a system that reads a `.pyi` type stub and emits a complete, compilable MicroPython C module automatically.

## Table of Contents

1. [The FFI Problem](#part-1-the-ffi-problem) -- Why calling C from Python is hard, and how stubs solve it
2. [C Background](#part-2-c-background-for-python-developers) -- Void pointers, boxing, module registration
3. [Implementation](#part-3-implementation) -- From `.pyi` to generated C, step by step

---

# Part 1: The FFI Problem

## What Is an FFI?

A Foreign Function Interface (FFI) lets code written in one language call code written in another. When you use `ctypes` in CPython to call a shared library, that is an FFI:

```python
import ctypes
libc = ctypes.CDLL("libc.so.6")
libc.printf(b"hello from C\n")
```

The problem is that Python and C represent values differently. Python integers are arbitrary-precision heap objects. C integers are fixed-width machine words. An FFI must convert ("marshal") values between the two representations on every call.

## Runtime FFI vs Compile-Time Code Generation

There are two broad approaches:

**Runtime FFI** (ctypes, cffi): The conversion happens at runtime. You describe the C function signature in Python, and a generic marshalling layer converts arguments on each call. This is flexible -- you can call any C function without recompiling -- but slow, because every call goes through a generic dispatch.

**Compile-time code generation**: You describe the C interface once, and a tool generates purpose-built C wrapper functions *before* compilation. Each wrapper knows exactly what types to convert, so there is no runtime dispatch overhead. The downside: you need a build step.

For a microcontroller with 320KB of RAM and a 160MHz single-core CPU, runtime overhead matters. We chose compile-time code generation.

## Why .pyi Stubs?

We need a way to describe C function signatures. Common options:

| Approach | Pros | Cons |
|-|-|-|
| Hand-written C wrappers | Full control | Tedious, error-prone, no IDE support |
| JSON/YAML schema | Easy to parse | No IDE support, no type checking |
| C header parsing | Reads the real API | Complex parser (preprocessor, macros) |
| **.pyi type stubs** | **IDE autocomplete, type-checker validation, already Python** | Need custom type markers |

`.pyi` files are Python's standard for type annotations. IDEs already understand them. Pyright and mypy validate them. And they look like this:

```python
"""LVGL v9 bindings for MicroPython."""
__c_header__ = "lvgl.h"

from mypyc_micropython.c_bindings.c_types import c_ptr, c_struct, c_str

@c_struct("lv_obj_t")
class LvObj: ...

def lv_screen_active() -> c_ptr[LvObj]: ...
def lv_label_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_label_set_text(label: c_ptr[LvObj], text: str) -> None: ...
def lv_obj_center(obj: c_ptr[LvObj]) -> None: ...
```

That is a complete interface description. The `c_ptr[LvObj]` annotation tells our compiler: "this is a pointer to a C struct called `lv_obj_t`." The `str` annotation says: "this is a `const char *`." The `-> None` says: "this function returns void."

A developer writing this stub gets autocomplete, hover documentation, and type checking -- all for free, because `.pyi` files are standard Python.

## The Pipeline

```
lvgl.pyi
   |
   v
StubParser  (ast.parse -> walk AST -> extract types)
   |
   v
CLibraryDef  (IR: functions, structs, enums, callbacks)
   |
   +---> CEmitter -------> lvgl.c       (MicroPython C module)
   |
   +---> CMakeEmitter ---> micropython.cmake  (build integration)
```

The `StubParser` reads the `.pyi` file using Python's built-in `ast` module -- the same parser Python itself uses. It walks the AST looking for:

- **Module-level assignments**: `__c_header__`, `__c_include_dirs__`, `__c_libraries__`
- **Decorated classes**: `@c_struct("lv_obj_t")` and `@c_enum("lv_event_code_t")`
- **Function definitions**: Each becomes a C wrapper function
- **Type annotations**: `c_ptr[LvObj]`, `c_int`, `str`, `bool` -- mapped to C types

The parsed output is a `CLibraryDef` -- an intermediate representation holding all the information needed to emit C code.

---

# Part 2: C Background for Python Developers

## Void Pointers: The Universal Handle

In C, a `void *` ("void pointer") is a pointer that can point to any type of data. It is C's way of saying "I have an address, but I am not telling you what lives there."

```c
void *ptr = malloc(100);  // ptr holds an address; we don't know the type
int *ip = (int *)ptr;     // cast tells the compiler: "treat this as int*"
```

We use `void *` to pass C library objects (like LVGL widgets) through MicroPython. Python code sees an opaque integer handle; C code casts it back to the real type.

## Boxing and Unboxing

MicroPython represents every Python value as `mp_obj_t` -- a pointer-sized integer with tagged low bits. To pass a C `int` to Python, you must "box" it:

```c
mp_int_t n = 42;
mp_obj_t boxed = mp_obj_new_int(n);  // box: C int -> Python int
```

To get a C value back from Python, you "unbox" it:

```c
mp_obj_t obj = /* from Python */;
mp_int_t n = mp_obj_get_int(obj);    // unbox: Python int -> C int
```

Every type needs its own box/unbox pair:

| Python stub type | C type | Boxing (C -> Python) | Unboxing (Python -> C) |
|-|-|-|-|
| `c_int` | `mp_int_t` | `mp_obj_new_int(v)` | `mp_obj_get_int(obj)` |
| `c_uint` | `mp_uint_t` | `mp_obj_new_int_from_uint(v)` | `(uint32_t)mp_obj_get_int(obj)` |
| `c_str` / `str` | `const char *` | `mp_obj_new_str(v, strlen(v))` | `mp_obj_str_get_str(obj)` |
| `c_ptr[T]` | `T *` | `ptr_to_mp(v)` | `mp_to_ptr(obj)` |
| `c_bool` / `bool` | `bool` | `mp_obj_new_bool(v)` | `mp_obj_is_true(obj)` |
| `c_float` | `float` | `mp_obj_new_float(v)` | `(float)mp_obj_get_float(obj)` |
| `c_double` / `float` | `mp_float_t` | `mp_obj_new_float(v)` | `mp_obj_get_float(obj)` |
| `None` | `void` | `mp_const_none` | -- |

## Pointer Wrapping: Why Not MP_OBJ_FROM_PTR?

MicroPython provides `MP_OBJ_FROM_PTR(ptr)` to convert a C pointer to `mp_obj_t`. But this only works for pointers to MicroPython's own heap objects, because MicroPython uses tagged pointers:

```
mp_obj_t bit layout (REPR_A):

  xxxx...xxx1  -> small int (value = bits >> 1)
  xxxx...x010  -> interned string (qstr)
  xxxx...x110  -> immediate (None, True, False)
  xxxx...xx00  -> pointer to MicroPython heap object
```

A pointer to a MicroPython heap object always has its low two bits as `00` (because heap allocations are word-aligned). `MP_OBJ_FROM_PTR` relies on this.

But LVGL allocates objects from its own memory pool. Those addresses have no guaranteed alignment relative to MicroPython's tagging scheme. If an LVGL pointer happens to have bit 0 set, MicroPython interprets it as a small integer. If bits 0-2 are `010`, it looks like a qstr. The result: crashes, corrupted data, or silent wrong answers.

The fix is simple: wrap pointers as integers:

```c
static inline mp_obj_t ptr_to_mp(void *ptr) {
    if (ptr == NULL) return mp_const_none;
    return mp_obj_new_int_from_uint((uintptr_t)ptr);  // always safe

static inline void *mp_to_ptr(mp_obj_t obj) {
    if (obj == mp_const_none) return NULL;
    return (void *)(uintptr_t)mp_obj_get_int(obj);   // always safe
}
```

`mp_obj_new_int_from_uint` creates a proper Python integer object. The pointer value is preserved exactly. On the way back, `mp_obj_get_int` extracts it.

## Module Registration

MicroPython modules follow a fixed pattern. Every module needs:

1. **Wrapper functions**: One C function per Python-visible function
2. **Function objects**: `MP_DEFINE_CONST_FUN_OBJ_N` macros register each wrapper
3. **Globals table**: An array of `(name, object)` pairs
4. **Module object**: The `mp_obj_module_t` struct
5. **Registration**: `MP_REGISTER_MODULE` makes it importable

```c
// 1. Wrapper function
static mp_obj_t lv_obj_center_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    lv_obj_center(c_obj);
    return mp_const_none;
}

// 2. Function object
static MP_DEFINE_CONST_FUN_OBJ_1(lv_obj_center_obj, lv_obj_center_wrapper);

// 3. Globals table
static const mp_rom_map_elem_t lvgl_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lvgl) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_center), MP_ROM_PTR(&lv_obj_center_obj) },
    // ... all other functions ...
};
static MP_DEFINE_CONST_DICT(lvgl_module_globals, lvgl_module_globals_table);

// 4 + 5. Module object and registration
const mp_obj_module_t lvgl_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_lvgl, lvgl_user_cmodule);
```

The `MP_DEFINE_CONST_FUN_OBJ_N` macros vary by argument count:
- `OBJ_0` for zero arguments
- `OBJ_1` for one argument
- `OBJ_2` for two arguments
- `OBJ_3` for three arguments
- `OBJ_VAR_BETWEEN(min, max)` for four or more

## The Data Flow

```
Python REPL                   MicroPython Runtime              C Library

  lvgl.lv_label_create(scr)
      |
      v
  globals table lookup
  -> &lv_label_create_obj
      |
      v
  lv_label_create_wrapper(arg0)
      |   mp_to_ptr(arg0)        // unbox: Python int -> void*
      |   (lv_obj_t *)ptr        // cast to real type
      v
                                  lv_label_create(parent)
                                      |
                                      v
                                  lv_obj_t *result
      |   ptr_to_mp(result)      // box: void* -> Python int
      v
  return mp_obj_t  ----------->  Python sees: 1082247756
```

---

# Part 3: Implementation

## Step 1: Define the Stub

Here is a minimal LVGL stub with four functions:

```python
"""LVGL v9 bindings for MicroPython."""
__c_header__ = "lvgl.h"

from mypyc_micropython.c_bindings.c_types import c_ptr, c_struct

@c_struct("lv_obj_t")
class LvObj: ...

def lv_screen_active() -> c_ptr[LvObj]: ...
def lv_label_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_label_set_text(label: c_ptr[LvObj], text: str) -> None: ...
def lv_obj_center(obj: c_ptr[LvObj]) -> None: ...
```

The `@c_struct("lv_obj_t")` decorator tells the parser that `LvObj` maps to the C type `lv_obj_t`. The `c_ptr[LvObj]` generic means "pointer to `lv_obj_t`". The `...` body (Ellipsis) is standard `.pyi` syntax meaning "signature only, no implementation."

## Step 2: Parse into IR

The `StubParser` walks the AST and builds a `CLibraryDef`:

```python
from mypyc_micropython.c_bindings.stub_parser import StubParser
from pathlib import Path

parser = StubParser()
library = parser.parse_file(Path("lvgl.pyi"))
```

The resulting IR looks like this (simplified):

```
CLibraryDef(
    name="lvgl",
    header="lvgl.h",
    structs={
        "LvObj": CStructDef(py_name="LvObj", c_name="lv_obj_t", is_opaque=True)
    },
    functions={
        "lv_screen_active": CFuncDef(
            py_name="lv_screen_active",
            c_name="lv_screen_active",
            params=[],
            return_type=CTypeDef(base_type=CType.STRUCT_PTR, struct_name="LvObj")
        ),
        "lv_label_create": CFuncDef(
            py_name="lv_label_create",
            c_name="lv_label_create",
            params=[
                CParamDef(name="parent", type_def=CTypeDef(
                    base_type=CType.STRUCT_PTR, struct_name="LvObj"))
            ],
            return_type=CTypeDef(base_type=CType.STRUCT_PTR, struct_name="LvObj")
        ),
        "lv_label_set_text": CFuncDef(
            py_name="lv_label_set_text",
            c_name="lv_label_set_text",
            params=[
                CParamDef(name="label", type_def=CTypeDef(
                    base_type=CType.STRUCT_PTR, struct_name="LvObj")),
                CParamDef(name="text", type_def=CTypeDef(
                    base_type=CType.STR))
            ],
            return_type=CTypeDef(base_type=CType.VOID)
        ),
        "lv_obj_center": CFuncDef(
            py_name="lv_obj_center",
            c_name="lv_obj_center",
            params=[
                CParamDef(name="obj", type_def=CTypeDef(
                    base_type=CType.STRUCT_PTR, struct_name="LvObj"))
            ],
            return_type=CTypeDef(base_type=CType.VOID)
        ),
    }
)
```

Key observations:

- `c_ptr[LvObj]` became `CTypeDef(base_type=CType.STRUCT_PTR, struct_name="LvObj")`
- `str` became `CTypeDef(base_type=CType.STR)`
- `None` became `CTypeDef(base_type=CType.VOID)`
- Function names are preserved as both `py_name` (for the Python-side QSTR) and `c_name` (for the C call)

## Step 3: Emit C Code

The `CEmitter` walks the `CLibraryDef` and generates a complete C module:

```python
from mypyc_micropython.c_bindings.c_emitter import CEmitter

emitter = CEmitter(library)
c_code = emitter.emit()
```

For our four-function stub, the output is:

```c
/* LVGL v9 bindings for MicroPython. */
/* Auto-generated from .pyi stub - do not edit */

#include "py/runtime.h"
#include "py/obj.h"
#include "lvgl.h"

static inline void *mp_to_ptr(mp_obj_t obj) {
    if (obj == mp_const_none) return NULL;
    return (void *)(uintptr_t)mp_obj_get_int(obj);
}
static inline mp_obj_t ptr_to_mp(void *ptr) {
    if (ptr == NULL) return mp_const_none;
    return mp_obj_new_int_from_uint((uintptr_t)ptr);
}

static mp_obj_t lv_screen_active_wrapper(void) {
    lv_obj_t *result = lv_screen_active();
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_0(lv_screen_active_obj, lv_screen_active_wrapper);

static mp_obj_t lv_label_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = mp_to_ptr(arg0);
    lv_obj_t *result = lv_label_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_label_create_obj, lv_label_create_wrapper);

static mp_obj_t lv_label_set_text_wrapper(mp_obj_t arg0, mp_obj_t arg1) {
    lv_obj_t *c_label = mp_to_ptr(arg0);
    const char *c_text = mp_obj_str_get_str(arg1);
    lv_label_set_text(c_label, c_text);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(lv_label_set_text_obj, lv_label_set_text_wrapper);

static mp_obj_t lv_obj_center_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    lv_obj_center(c_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_obj_center_obj, lv_obj_center_wrapper);

static const mp_rom_map_elem_t lvgl_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lvgl) },
    { MP_ROM_QSTR(MP_QSTR_lv_screen_active), MP_ROM_PTR(&lv_screen_active_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_label_create), MP_ROM_PTR(&lv_label_create_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_label_set_text), MP_ROM_PTR(&lv_label_set_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_center), MP_ROM_PTR(&lv_obj_center_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_module_globals, lvgl_module_globals_table);

const mp_obj_module_t lvgl_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_lvgl, lvgl_user_cmodule);
```

Every function follows the same pattern:

1. **Unbox** each argument from `mp_obj_t` to its C type
2. **Call** the real C function
3. **Box** the return value back to `mp_obj_t`

The emitter dispatches boxing/unboxing through `CType.to_mp_box()` and `CType.to_mp_unbox()`:

```python
class CType(Enum):
    INT = auto()
    STR = auto()
    STRUCT_PTR = auto()
    # ...

    def to_mp_unbox(self, arg_expr: str) -> str:
        mapping = {
            CType.INT: f"mp_obj_get_int({arg_expr})",
            CType.STR: f"mp_obj_str_get_str({arg_expr})",
            CType.STRUCT_PTR: f"mp_to_ptr({arg_expr})",
            # ...
        }
        return mapping.get(self, f"mp_to_ptr({arg_expr})")

    def to_mp_box(self, val_expr: str) -> str:
        mapping = {
            CType.INT: f"mp_obj_new_int({val_expr})",
            CType.VOID: "mp_const_none",
            CType.STRUCT_PTR: f"ptr_to_mp((void *){val_expr})",
            # ...
        }
        return mapping.get(self, f"ptr_to_mp({val_expr})")
```

## Enums as Integer Constants

C enums become constant integers in the Python module. A stub like:

```python
@c_enum("lv_event_code_t")
class LvEventCode:
    CLICKED: int = 7
    VALUE_CHANGED: int = 8
    PRESSED: int = 1
```

generates entries in the globals table:

```c
{ MP_ROM_QSTR(MP_QSTR_LV_EVENT_CODE_CLICKED), MP_ROM_INT(7) },
{ MP_ROM_QSTR(MP_QSTR_LV_EVENT_CODE_VALUE_CHANGED), MP_ROM_INT(8) },
{ MP_ROM_QSTR(MP_QSTR_LV_EVENT_CODE_PRESSED), MP_ROM_INT(1) },
```

No wrapper functions needed -- enums are compile-time constants baked into the module.

## Callbacks with Trampoline Functions

Callbacks are the trickiest part. When LVGL fires an event, it calls a C function pointer. But the user's handler is a Python function. We need a "trampoline" -- a C function that LVGL can call, which in turn calls the Python callback.

Given a stub with a callback:

```python
EventCallback = Callable[[c_ptr[LvEvent]], None]

def lv_obj_add_event_cb(
    obj: c_ptr[LvObj],
    cb: EventCallback,
    filter: c_uint,
    user_data: c_ptr[c_void]
) -> None: ...
```

The emitter generates:

```c
#define MAX_EVENT_CALLBACKS 32
static mp_obj_t event_callbacks[MAX_EVENT_CALLBACKS];
static int event_callback_count = 0;

static void lv_obj_add_event_cb_cb_trampoline(lv_event_t *e) {
    int idx = (int)(intptr_t)lv_event_get_user_data(e);
    if (idx >= 0 && idx < event_callback_count) {
        mp_obj_t cb = event_callbacks[idx];
        mp_obj_t event_obj = ptr_to_mp((void *)e);
        mp_call_function_1(cb, event_obj);
    }
}

static mp_obj_t lv_obj_add_event_cb_wrapper(size_t n_args, const mp_obj_t *args) {
    lv_obj_t *c_obj = mp_to_ptr(args[0]);
    mp_obj_t callback = args[1];
    uint32_t c_filter = (uint32_t)mp_obj_get_int(args[2]);
    // Store callback, get index
    int idx = event_callback_count++;
    event_callbacks[idx] = callback;
    // Pass trampoline + index as user_data
    lv_obj_add_event_cb(c_obj, lv_obj_add_event_cb_cb_trampoline,
                        c_filter, (void *)(intptr_t)idx);
    return mp_const_none;
}
```

The trick: the `user_data` pointer carries the callback's index in our array. When LVGL fires the event, the trampoline retrieves the index, looks up the Python function, and calls it.

## Scaling Up

The real LVGL stub has 55 functions, 7 structs, 2 enums, and a callback type. The generated `lvgl.c` is 744 lines. The module exposes 161 symbols (functions + enum constants + 3 display driver functions added manually).

The entire generation takes under 50 milliseconds on a laptop. The generated C compiles into the MicroPython firmware alongside the LVGL library and runs on an ESP32-C6 with 320KB of RAM.

## On Device

```python
>>> import lvgl
>>> dir(lvgl)
['__name__', 'lv_screen_active', 'lv_label_create', 'lv_label_set_text',
' lv_obj_center', 'init_display', 'timer_handler', 'backlight', ...]
>>> lvgl.init_display()
>>> scr = lvgl.lv_screen_active()
>>> scr
1082247348
>>> label = lvgl.lv_label_create(scr)
>>> lvgl.lv_label_set_text(label, "Good morning")
>>> lvgl.lv_obj_center(label)
>>> for i in range(100):
...     lvgl.timer_handler()
...     time.sleep_ms(10)
```

The screen pointer `1082247348` is the LVGL object's address, safely wrapped as a Python integer. Pass it to any function that expects `c_ptr[LvObj]`, and the wrapper casts it back to `lv_obj_t *` on the C side.

## What We Built

| Component | Lines | Role |
|-|-|-|
| `c_types.py` | 137 | Type markers for `.pyi` stubs |
| `c_ir.py` | 152 | Intermediate representation |
| `stub_parser.py` | 265 | `.pyi` -> `CLibraryDef` |
| `c_emitter.py` | 312 | `CLibraryDef` -> C module |
| `cmake_emitter.py` | ~60 | `CLibraryDef` -> `micropython.cmake` |
| `compiler.py` | 101 | Pipeline orchestration |
| **Total** | **~1,027** | |

From those 1,027 lines of Python, we generate 744 lines of C that wrap 55 LVGL functions, 40+ enum constants, and a callback mechanism -- all type-safe, all IDE-friendly, all from a `.pyi` file that any Python developer can read and edit.