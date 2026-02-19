# Concept: .pyi Stub Files for C Bindings

## The Problem

You want to use a C library (like LVGL) from MicroPython. Today's options:

1. **Manual C wrappers** - Write C code by hand (tedious, error-prone)
2. **Existing binding generators** - Parse C headers (complex, requires C knowledge)
3. **CFFI** - Write C declarations in Python strings (not Pythonic)

## The Solution

Write a `.pyi` stub file in **pure Python syntax** that describes the C API:

```python
# lvgl.pyi - describes the LVGL C API

@c_struct("lv_obj_t")
class LvObj:
    """Base LVGL widget object."""
    pass

def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """Create a new button widget."""
    ...
```

Then compile it to C:

```bash
mpy-compile-c my_app.py --stub lvgl.pyi
```

## Architecture

```
                    ┌─────────────────┐
                    │   lvgl.pyi      │
                    │  (you write)    │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ mpy-compile-c│  │   PyCharm    │  │    mypy      │
    │ (our tool)   │  │   VSCode     │  │   pyright    │
    └──────┬───────┘  └──────────────┘  └──────────────┘
           │                 │                 │
           ▼                 │                 │
    ┌──────────────┐         │                 │
    │  lvgl.c      │    IDE uses .pyi     Type checker
    │ (generated)  │    for autocomplete   validates code
    └──────────────┘
```

## How IDEs Use .pyi Files

IDEs (PyCharm, VSCode) **automatically** read `.pyi` files for:

1. **Autocomplete** - Shows available functions/classes
2. **Hover documentation** - Shows docstrings and signatures
3. **Type checking** - Red squiggles for type errors
4. **Go to definition** - Jumps to the stub

The IDE doesn't know or care that we also use the `.pyi` to generate C code.

```python
# my_app.py - user gets full IDE support!

import lvgl as lv

screen = lv.lv_screen_active()
btn = lv.lv_btn_create(screen)  # ← IDE autocompletes this!
lv.lv_obj_set_size(btn, 100, 50)  # ← IDE shows parameter hints!
```

## Why This Is Novel

We researched existing tools (Feb 2026). **Nobody does this.**

| Tool | Direction | Input | Output |
|------|-----------|-------|--------|
| pybind11-stubgen | C++ → Python | .so file | .pyi |
| pyo3-stub-gen | Rust → Python | Rust code | .pyi |
| mypyc | Python → C | .py file | .so |
| CFFI | C → Python | C strings | .so |
| **Our approach** | **.pyi → C** | **.pyi file** | **C code** |

We're going the **opposite direction** from everyone else.

## Benefits

| Benefit | Description |
|---------|-------------|
| **Pythonic** | Write Python syntax, not C declarations |
| **IDE support** | Free autocomplete, hover docs, type checking |
| **Single source** | One file defines API, docs, and types |
| **Familiar** | Python developers already know .pyi format |
| **Validated** | mypy/pyright can check your code before runtime |

## Comparison with CFFI

**CFFI approach** (C syntax in Python strings):
```python
from cffi import FFI
ffi = FFI()
ffi.cdef("""
    typedef struct lv_obj_t lv_obj_t;
    lv_obj_t* lv_btn_create(lv_obj_t* parent);
    void lv_obj_set_size(lv_obj_t* obj, int w, int h);
""")
```

**Our approach** (pure Python syntax):
```python
@c_struct("lv_obj_t")
class LvObj: ...

def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None: ...
```

Our approach:
- Uses Python syntax (not C)
- Works with IDEs out of the box
- Can add docstrings
- Type checker understands it

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                        lvgl.pyi                             │
│                   (single source of truth)                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│  ast.parse()  │     │     IDE       │     │  Type Checker │
│               │     │               │     │               │
│ Parse stub    │     │ Autocomplete  │     │ Validate      │
│ Extract types │     │ Hover docs    │     │ user code     │
└───────┬───────┘     └───────────────┘     └───────────────┘
        │
        ▼
┌───────────────┐
│ CLibraryDef   │
│               │
│ - structs     │
│ - functions   │
│ - callbacks   │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│ C Code Gen    │
│               │
│ - wrappers    │
│ - conversions │
│ - module reg  │
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  lvgl.c       │
│               │
│ MicroPython   │
│ C module      │
└───────────────┘
```

## Next Steps

1. Read [02-proof-of-concept.md](02-proof-of-concept.md) for working code
2. Read [03-stub-format.md](03-stub-format.md) for stub file specification
3. Read [04-implementation-plan.md](04-implementation-plan.md) for roadmap
