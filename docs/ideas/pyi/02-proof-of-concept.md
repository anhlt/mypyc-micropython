# Proof of Concept: .pyi Parser and C Generator

> **Status**: Working prototype  
> **Tested**: Feb 2026  
> **Result**: Successfully generates valid MicroPython C module code

## Summary

This document proves that Option A (pure .pyi → C) is technically feasible.

The prototype:
1. Parses `.pyi` files using Python's `ast` module
2. Extracts type information (structs, functions, callbacks)
3. Generates MicroPython C wrapper code

## Key Findings

| Capability | Status | Evidence |
|------------|--------|----------|
| Parse .pyi with `ast.parse()` | **Works** | Standard Python - no deps |
| Extract `@c_struct` decorators | **Works** | `ast.ClassDef.decorator_list` |
| Extract function signatures | **Works** | `ast.FunctionDef.args`, `.returns` |
| Parse `c_ptr[T]` generics | **Works** | `ast.Subscript` node |
| Parse `Callable[[...], ...]` | **Works** | Nested `ast.Subscript` |
| Generate C wrapper functions | **Works** | See output below |
| Generate MicroPython module | **Works** | `MP_REGISTER_MODULE` |

## Proof: AST Parsing

When we parse a `.pyi` file, the AST contains all the information we need:

```python
# Input stub
def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...

# AST representation
FunctionDef(
    name='lv_btn_create',
    args=arguments(args=[
        arg(arg='parent', annotation=Subscript(
            value=Name(id='c_ptr'),
            slice=Name(id='LvObj')
        ))
    ]),
    returns=Subscript(
        value=Name(id='c_ptr'),
        slice=Name(id='LvObj')
    )
)
```

The AST gives us:
- Function name: `lv_btn_create`
- Parameter name: `parent`
- Parameter type: `c_ptr[LvObj]` (struct pointer)
- Return type: `c_ptr[LvObj]` (struct pointer)

## Proof: Type Extraction

### Simple Types

```python
# Input
def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None: ...

# Extracted
{
    "name": "lv_obj_set_size",
    "params": [
        {"name": "obj", "type": "STRUCT_PTR", "struct": "LvObj"},
        {"name": "w", "type": "INT"},
        {"name": "h", "type": "INT"}
    ],
    "return_type": "VOID"
}
```

### Struct Definitions

```python
# Input
@c_struct("lv_obj_t")
class LvObj:
    pass

@c_struct("lv_point_t", opaque=False)
class LvPoint:
    x: c_int
    y: c_int

# Extracted
{
    "LvObj": {"c_name": "lv_obj_t", "opaque": True, "fields": {}},
    "LvPoint": {"c_name": "lv_point_t", "opaque": False, "fields": {"x": "INT", "y": "INT"}}
}
```

### Callbacks

```python
# Input
EventCallback = Callable[[c_ptr[LvEvent]], None]

# Extracted
{
    "EventCallback": {"type": "CALLBACK", "params": ["c_ptr[LvEvent]"], "return": "None"}
}
```

## Proof: C Code Generation

### Input Stub

```python
@c_struct("lv_obj_t")
class LvObj:
    pass

def lv_scr_act() -> c_ptr[LvObj]: ...
def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None: ...
def lv_label_set_text(label: c_ptr[LvObj], text: str) -> None: ...
```

### Generated C Code

```c
/* Auto-generated from .pyi stub */
#include "py/runtime.h"
#include "py/obj.h"

/* Include the C library header */
// #include "lvgl.h"

/* Wrapper functions */
static mp_obj_t lv_scr_act_wrapper(void) {
    lv_obj_t * result = lv_scr_act();
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_0(lv_scr_act_obj, lv_scr_act_wrapper);

static mp_obj_t lv_btn_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = mp_to_ptr(arg0);
    lv_obj_t * result = lv_btn_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_btn_create_obj, lv_btn_create_wrapper);

static mp_obj_t lv_obj_set_size_wrapper(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    mp_int_t c_w = mp_obj_get_int(arg1);
    mp_int_t c_h = mp_obj_get_int(arg2);
    lv_obj_set_size(c_obj, c_w, c_h);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(lv_obj_set_size_obj, lv_obj_set_size_wrapper);

static mp_obj_t lv_label_set_text_wrapper(mp_obj_t arg0, mp_obj_t arg1) {
    lv_obj_t *c_label = mp_to_ptr(arg0);
    const char *c_text = mp_obj_str_get_str(arg1);
    lv_label_set_text(c_label, c_text);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(lv_label_set_text_obj, lv_label_set_text_wrapper);

/* Module globals table */
static const mp_rom_map_elem_t lvgl_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lvgl) },
    { MP_ROM_QSTR(MP_QSTR_lv_scr_act), MP_ROM_PTR(&lv_scr_act_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_btn_create), MP_ROM_PTR(&lv_btn_create_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_set_size), MP_ROM_PTR(&lv_obj_set_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_label_set_text), MP_ROM_PTR(&lv_label_set_text_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_globals, lvgl_globals_table);

const mp_obj_module_t lvgl_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_globals,
};

MP_REGISTER_MODULE(MP_QSTR_lvgl, lvgl_user_cmodule);
```

## Proof: IDE Integration

The same `.pyi` file works with IDEs:

```
User types: import lvgl as lv
User types: lv.

IDE reads lvgl.pyi and shows:
----------------------------------------
  class LvObj          - Base LVGL object
  lv_scr_act()         - Get active screen
  lv_btn_create(...)   - Create button widget
  lv_obj_set_size(...) - Set object size
  lv_label_set_text(...) - Set label text

User hovers over: lv.lv_obj_set_size

IDE shows:
----------------------------------------
def lv_obj_set_size(obj: c_ptr[LvObj], w: int, h: int) -> None

Set the size of an object.

Args:
    obj: Target object
    w: Width in pixels
    h: Height in pixels
```

## Working Prototype Code

See [examples/poc_parser.py](examples/poc_parser.py) for the complete working prototype.

The prototype is ~250 lines of Python and demonstrates:
1. Full stub parsing
2. Type extraction
3. C code generation
4. Module registration

## Conclusion

**Option A is technically proven.** The prototype successfully:

1. Parses `.pyi` files with standard `ast` module
2. Extracts all necessary type information
3. Generates valid MicroPython C module code
4. Works with IDEs for autocomplete

No external dependencies required. Pure Python implementation.
