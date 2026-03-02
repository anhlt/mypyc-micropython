# C Library Bindings via .pyi Stub Files

> **Status**: Implemented (Phases 1-6 complete) -- evolving toward general C binding system  
> **Author**: Research from Feb 2026  
> **Novel Approach**: First known use of .pyi as source for C code generation  
> **Next**: Phase 7 (emitter fixes) -- see [05-roadmap.md](05-roadmap.md)

## Overview

This system generates MicroPython C bindings for external C libraries (like LVGL) using Python `.pyi` stub files. It works end-to-end: LVGL runs on ESP32 hardware with 55 auto-generated wrapper functions. See [Blog 21](../../../blogs/21-pyi-stub-c-bindings.md) and [Blog 22](../../../blogs/22-lvgl-display-driver-esp32.md).

## The Innovation

**Traditional approach** (what everyone does):
```
C headers (.h) → Binding generator → Python wrapper + .pyi stubs
```

**Our approach** (novel):
```
.pyi stub file → Our tool → C wrapper code for MicroPython
```

The same `.pyi` file serves **three purposes**:
1. **Source of truth** for C code generation
2. **IDE support** (autocomplete, hover docs)
3. **Type checking** (mypy/pyright validation)

## Why This Matters

| Benefit | Description |
|---------|-------------|
| **Pythonic API** | Developers write familiar Python syntax, not C |
| **IDE support free** | PyCharm/VSCode understand .pyi natively |
| **Type safety** | mypy/pyright can validate your code |
| **Single source** | One file defines interface, docs, and types |
| **No C knowledge needed** | Write stubs in Python, get C bindings |

## Documentation

| Document | Description |
|----------|-------------|
| [01-concept.md](01-concept.md) | Core concept and architecture |
| [02-proof-of-concept.md](02-proof-of-concept.md) | Working prototype code |
| [03-stub-format.md](03-stub-format.md) | .pyi stub file format specification |
| [03a-pyi-plus-header.md](03a-pyi-plus-header.md) | How .pyi + .h files combine to generate C |
| [04-implementation-plan.md](04-implementation-plan.md) | Original phased implementation plan (Phases 1-6, all complete) |
| [05-roadmap.md](05-roadmap.md) | **Roadmap**: completed phases + next phases (7-9) toward general C bindings |
| [06-direct-c-calls.md](06-direct-c-calls.md) | Optimization: direct C calls from compiled Python |

## Example

**Input** (`lvgl.pyi`):
```python
@c_struct("lv_obj_t")
class LvObj:
    """Base LVGL object."""
    pass

def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """Create a button widget."""
    ...

def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None:
    """Set object size in pixels."""
    ...
```

**Output** (generated C):
```c
#include "py/runtime.h"
#include "lvgl.h"

static mp_obj_t lv_btn_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = mp_to_ptr(arg0);
    lv_obj_t *result = lv_btn_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_btn_create_obj, lv_btn_create_wrapper);
```

**User code** (with full IDE support):
```python
import lvgl as lv

btn = lv.lv_btn_create(screen)  # IDE autocompletes!
lv.lv_obj_set_size(btn, 100, 50)  # IDE shows parameter hints!
```

## Quick Links

- [Proof of Concept Code](examples/poc_parser.py)
- [Example LVGL Stub](examples/lvgl.pyi)
- [Example User App](examples/my_app.py)
- [Generated C Output](examples/generated_output.c)

## Research Findings

- **No existing tools** use .pyi as source for C generation (we checked)
- **All existing tools** go the opposite direction (C → .pyi)
- **Python's ast module** can parse .pyi files perfectly
- **Technical feasibility**: Proven with working prototype
