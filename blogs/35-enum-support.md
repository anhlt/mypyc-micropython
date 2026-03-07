# 35. Enum Support: Compile-Time Integer Constants

Python's `enum.IntEnum` is a nice way to name integers without losing the ability to do integer math and bit operations. On MicroPython, though, building enum classes at import time and creating enum member objects costs RAM and startup time.

This post explains how `mypyc-micropython` adds `IntEnum` support by turning enum member access into compile time integer constants, and by exporting those constants as module globals.

## Table of Contents

- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [Part 2: C Background](#part-2-c-background)
- [Part 3: Implementation](#part-3-implementation)
- [Device Testing](#device-testing)
- [Closing](#closing)

## Part 1: Compiler Theory

### Enums are classes, but we want constants

In normal Python, an `IntEnum` is a class definition that runs at import time. It creates:

- A class object (for example `Color`)
- A set of member objects (for example `Color.RED`, `Color.GREEN`)
- Metadata like names and repr strings

That runtime behavior is great for Python, but a compiler can often do better.

When you write:

```python
return Color.GREEN
```

you usually want the integer `2`, not a rich object that remembers it was called `GREEN`.

### Compile time resolution

The key idea is compile time resolution: if the compiler can evaluate an enum member to a plain integer while building IR, it can erase the enum object completely.

That changes the work done at runtime:

- Python runtime approach: import code creates classes and member objects, then attribute access returns an object.
- Compiled approach: attribute access becomes an integer literal in IR, and the emitted C returns or compares plain integers.

### Constant folding and forward references

Enums often use expressions, not just literal integers. Bitmask enums are the common case:

```python
ALL = READ | WRITE | EXECUTE
```

This creates two requirements for the compiler:

1. It must fold simple integer expressions (`<<`, `|`, `&`, `^`, `+`, `-`, `*`, and so on) at compile time.
2. It must resolve forward references to earlier members inside the same enum class body.

In other words, `ALL` should be computed as soon as `READ`, `WRITE`, and `EXECUTE` are known.

### Memory layout intuition

At a high level, a runtime enum member is an object with fields, while a compiled enum member is just an integer.

Runtime (conceptual):

```
Color.GREEN
  |
  v
+---------------------------+
| enum member object        |
| - integer value: 2        |
| - name string: "GREEN"    |
| - backref to class Color  |
| - methods, repr, etc      |
+---------------------------+
```

Compiled (conceptual):

```
Color.GREEN
  |
  v
2
```

The compiler's job is to make that second diagram true without changing program meaning for the subset it supports.

### Python enum at runtime vs compiled enum

| Aspect | Python `IntEnum` at runtime | Compiled enum in `mypyc-micropython` |
| --- | --- | --- |
| Representation | Class plus member objects | Integers only |
| Import cost | Builds class and members at import time | No enum objects created |
| `Color.GREEN` | Attribute lookup returns enum member object | Replaced with integer constant during IR build |
| Comparisons (`==`) | Often compares like integers, but still objects exist | Plain integer comparison in IR/C |
| Bitmasks (`|`, `&`) | Operates on enum members or ints | Operates on ints, constant folded when possible |
| Exported names | `Color`, `Color.GREEN`, etc | Module globals entries like `Color_GREEN = 2` |

## Part 2: C Background

This feature leans on a few MicroPython C API patterns. You don't need to know MicroPython internals to follow the idea, but you do need a mental model for three things.

### `MP_ROM_INT` and ROMable objects

MicroPython distinguishes objects that can live in read only memory (ROM) versus heap allocated runtime objects.

`MP_ROM_INT(n)` is a macro that produces a ROMable integer object for small constants. In practice, it lets a module expose constants without allocating new objects during import.

### Module globals tables

User C modules typically define a globals table like this:

```c
static const mp_rom_map_elem_t module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_modname) },
    { MP_ROM_QSTR(MP_QSTR_fn), MP_ROM_PTR(&fn_obj) },
    { MP_ROM_QSTR(MP_QSTR_SOME_CONST), MP_ROM_INT(123) },
};
MP_DEFINE_CONST_DICT(module_globals, module_globals_table);
```

Each entry is a key value pair:

- Key: usually a QSTR, MicroPython's interned string id
- Value: a pointer to a function object, another QSTR, or a ROMable value like `MP_ROM_INT`

At import time, MicroPython uses this table to populate the module's global namespace.

### QSTR macros (`MP_QSTR_*`, `MP_ROM_QSTR`, `MP_ROM_PTR`)

MicroPython uses QSTRs ("qualified strings") to avoid storing duplicate strings at runtime. The important idea is simple:

- `MP_QSTR_name` is a compile time id for the string `"name"`
- `MP_ROM_QSTR(MP_QSTR_name)` puts that id in a ROMable form
- `MP_ROM_PTR(&obj)` stores a pointer to an object (like a function object)

For this enum feature, we piggyback on the globals table mechanism by emitting new QSTR keys and mapping them to `MP_ROM_INT` values.

## Part 3: Implementation

This compiler feature has three main pieces:

1. A small IR container to store enum definitions (`EnumIR`)
2. IRBuilder logic that recognizes `IntEnum` classes and evaluates member values at compile time
3. Module emission logic that exports enum members as `MP_ROM_INT` entries in the module globals table

### The design inspiration: `CEnumDef`

The project already had a pattern for "an enum is a name plus a set of integer values" on the C bindings side:

```python
@dataclass
class CEnumDef:
    py_name: str    # Python-side name (e.g., "LvAlign")
    c_name: str     # C-side enum type (e.g., "lv_align_t")
    values: dict[str, int] = field(default_factory=dict)
```

The `EnumIR` dataclass mirrors that idea, but it lives in the compiler IR and is tied to a specific module and sanitized C identifiers:

```python
@dataclass
class EnumIR:
    name: str       # Python enum class name (e.g., 'Color')
    c_name: str     # Sanitized C identifier (e.g., 'enum_demo_Color')
    module_name: str
    values: dict[str, int] = field(default_factory=dict)  # member_name -> int value
    docstring: str | None = None
```

It's intentionally boring. It stores only what the compiler needs to replace enum member access with integer constants.

### Step 1: Detect enum classes during module compilation

During compilation, class definitions (`ast.ClassDef`) are routed either to normal class lowering or to enum lowering:

```python
elif isinstance(node, ast.ClassDef):
    if ir_builder.is_enum_class(node):
        enum_ir = ir_builder.build_enum(node)
        module_ir.add_enum(enum_ir)
    else:
        class_ir = ir_builder.build_class(node)
        module_ir.add_class(class_ir)
```

This is where the compiler chooses the "erase the enum" strategy.

### Step 2: Build `EnumIR` and evaluate member values at compile time

`IRBuilder.build_enum()` walks the enum class body and collects assignments:

```python
def build_enum(self, node: ast.ClassDef) -> EnumIR:
    enum_ir = EnumIR(name=node.name, c_name=..., module_name=...)
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            val = self._eval_enum_value(stmt.value, enum_ir.values)
            if val is not None:
                enum_ir.values[target.id] = val
    self._known_enums[enum_name] = enum_ir
    return enum_ir
```

Two important things happen here:

- Values are computed while we still have the AST, before we emit any runtime code.
- The builder caches the enum in `_known_enums`, so later expressions can resolve `Color.GREEN` into a constant.

### Step 3: `_eval_enum_value()` and forward reference resolution

The method `_eval_enum_value()` is a tiny compile time evaluator for integer expressions:

```python
def _eval_enum_value(self, node, resolved=None) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.Name) and resolved and node.id in resolved:
        return resolved[node.id]  # Forward ref: ALL = READ | WRITE
    if isinstance(node, ast.BinOp):
        left = self._eval_enum_value(node.left, resolved)
        right = self._eval_enum_value(node.right, resolved)
        # Handle <<, >>, |, &, ^, +, -, *
```

That `ast.Name` branch is the forward reference hook.

For the bitmask enum:

```python
class Permission(IntEnum):
    READ = 1 << 0
    WRITE = 1 << 1
    EXECUTE = 1 << 2
    ALL = READ | WRITE | EXECUTE
```

`build_enum()` evaluates in order:

1. `READ` becomes `1 << 0`, which `_eval_enum_value()` reduces to `1`.
2. `WRITE` becomes `1 << 1`, reduced to `2`.
3. `EXECUTE` becomes `1 << 2`, reduced to `4`.
4. `ALL` becomes `READ | WRITE | EXECUTE`. Each name lookup hits the `resolved` dict, then the bitwise ORs are applied, producing `7`.

The important constraint is that this works only for references to already computed members in the same enum body. That is exactly the pattern used by `ALL = READ | WRITE | EXECUTE`.

### Step 4: Replace enum member access with `ConstIR` during IR building

Once `_known_enums` is populated, attribute access can fold enum members into IR constants:

```python
# In _build_attribute():
if enum_name in self._known_enums:
    enum_ir = self._known_enums[enum_name]
    if member_name in enum_ir.values:
        return ConstIR(ir_type=IRType.INT, value=enum_ir.values[member_name]), []
```

This is the moment where `Color.GREEN` stops being "attribute access" and becomes just `2` in the IR.

### Step 5: Export enum members as module globals (`MP_ROM_INT`)

Even though the compiler erases enum objects, it can still expose the values as module globals for debugging and interop.

The module emitter walks the enums and writes additional globals table entries:

```python
# In _emit_globals_table():
for enum_name in self.module_ir.enum_order:
    enum_ir = self.module_ir.enums[enum_name]
    for member_name, member_value in enum_ir.values.items():
        qstr_name = f"{enum_ir.name}_{member_name}"
        lines.append(
            f"    {{ MP_ROM_QSTR(MP_QSTR_{qstr_name}), MP_ROM_INT({member_value}) }},"
        )
```

This produces globals like `Color_GREEN = 2` and `Permission_ALL = 7`.

### The full three-stage view (Python -> IR -> C)

This section shows the exact flow on a concrete input.

#### Stage 1: Python input (`examples/enum_demo.py`)

```python
from enum import IntEnum


class Color(IntEnum):
    RED = 1
    GREEN = 2
    BLUE = 3


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10


class Permission(IntEnum):
    READ = 1 << 0
    WRITE = 1 << 1
    EXECUTE = 1 << 2
    ALL = READ | WRITE | EXECUTE


def get_color() -> int:
    return Color.GREEN


def check_color(c: int) -> bool:
    return c == Color.BLUE


def total_priority() -> int:
    return Priority.LOW + Priority.MEDIUM + Priority.HIGH


def is_high_priority(p: int) -> bool:
    return p == Priority.HIGH


def has_write(perm: int) -> bool:
    return (perm & Permission.WRITE) != 0


def default_permissions() -> int:
    return Permission.READ | Permission.WRITE
```

#### Stage 2: IR dump (text format)

Notice that every enum usage inside functions is already an integer literal, and even arithmetic is folded.

```text
Module: enum_demo (c_name: enum_demo)

Functions:
  def get_color() -> MP_INT_T:
    c_name: enum_demo_get_color
    max_temp: 0
    body:
      return 2

  def check_color(c: MP_INT_T) -> BOOL:
    c_name: enum_demo_check_color
    max_temp: 0
    locals: {c: MP_INT_T}
    body:
      return (c == 3)

  def total_priority() -> MP_INT_T:
    c_name: enum_demo_total_priority
    max_temp: 0
    body:
      return ((1 + 5) + 10)

  def is_high_priority(p: MP_INT_T) -> BOOL:
    c_name: enum_demo_is_high_priority
    max_temp: 0
    locals: {p: MP_INT_T}
    body:
      return (p == 10)

  def has_write(perm: MP_INT_T) -> BOOL:
    c_name: enum_demo_has_write
    max_temp: 0
    locals: {perm: MP_INT_T}
    body:
      return ((perm & 2) != 0)

  def default_permissions() -> MP_INT_T:
    c_name: enum_demo_default_permissions
    max_temp: 0
    body:
      return (1 | 2)

Enums:
  Enum: Color (c_name: enum_demo_Color)
    RED = 1
    GREEN = 2
    BLUE = 3

  Enum: Priority (c_name: enum_demo_Priority)
    LOW = 1
    MEDIUM = 5
    HIGH = 10

  Enum: Permission (c_name: enum_demo_Permission)
    READ = 1
    WRITE = 2
    EXECUTE = 4
    ALL = 7
```

#### Stage 3: Generated C output (`enum_demo.c`)

Two things to look for:

- Functions return or compare plain integers (`mp_obj_new_int(2)`, `c == 3`, `perm & 2`).
- Enum members are exported as `MP_ROM_INT` values in `enum_demo_module_globals_table`.

```c
#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

static mp_obj_t enum_demo_get_color(void);
static mp_obj_t enum_demo_check_color(mp_obj_t c_obj);
static mp_obj_t enum_demo_total_priority(void);
static mp_obj_t enum_demo_is_high_priority(mp_obj_t p_obj);
static mp_obj_t enum_demo_has_write(mp_obj_t perm_obj);
static mp_obj_t enum_demo_default_permissions(void);

static mp_obj_t enum_demo_get_color(void) {
    return mp_obj_new_int(2);
}
MP_DEFINE_CONST_FUN_OBJ_0(enum_demo_get_color_obj, enum_demo_get_color);

static mp_obj_t enum_demo_check_color(mp_obj_t c_obj) {
    mp_int_t c = mp_obj_get_int(c_obj);
    return (c == 3) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(enum_demo_check_color_obj, enum_demo_check_color);

static mp_obj_t enum_demo_total_priority(void) {
    return mp_obj_new_int(((1 + 5) + 10));
}
MP_DEFINE_CONST_FUN_OBJ_0(enum_demo_total_priority_obj, enum_demo_total_priority);

static mp_obj_t enum_demo_is_high_priority(mp_obj_t p_obj) {
    mp_int_t p = mp_obj_get_int(p_obj);
    return (p == 10) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(enum_demo_is_high_priority_obj, enum_demo_is_high_priority);

static mp_obj_t enum_demo_has_write(mp_obj_t perm_obj) {
    mp_int_t perm = mp_obj_get_int(perm_obj);
    return ((perm & 2) != 0) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(enum_demo_has_write_obj, enum_demo_has_write);

static mp_obj_t enum_demo_default_permissions(void) {
    return mp_obj_new_int((1 | 2));
}
MP_DEFINE_CONST_FUN_OBJ_0(enum_demo_default_permissions_obj, enum_demo_default_permissions);

static const mp_rom_map_elem_t enum_demo_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_enum_demo) },
    { MP_ROM_QSTR(MP_QSTR_get_color), MP_ROM_PTR(&enum_demo_get_color_obj) },
    { MP_ROM_QSTR(MP_QSTR_check_color), MP_ROM_PTR(&enum_demo_check_color_obj) },
    { MP_ROM_QSTR(MP_QSTR_total_priority), MP_ROM_PTR(&enum_demo_total_priority_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_high_priority), MP_ROM_PTR(&enum_demo_is_high_priority_obj) },
    { MP_ROM_QSTR(MP_QSTR_has_write), MP_ROM_PTR(&enum_demo_has_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_default_permissions), MP_ROM_PTR(&enum_demo_default_permissions_obj) },
    { MP_ROM_QSTR(MP_QSTR_Color_RED), MP_ROM_INT(1) },
    { MP_ROM_QSTR(MP_QSTR_Color_GREEN), MP_ROM_INT(2) },
    { MP_ROM_QSTR(MP_QSTR_Color_BLUE), MP_ROM_INT(3) },
    { MP_ROM_QSTR(MP_QSTR_Priority_LOW), MP_ROM_INT(1) },
    { MP_ROM_QSTR(MP_QSTR_Priority_MEDIUM), MP_ROM_INT(5) },
    { MP_ROM_QSTR(MP_QSTR_Priority_HIGH), MP_ROM_INT(10) },
    { MP_ROM_QSTR(MP_QSTR_Permission_READ), MP_ROM_INT(1) },
    { MP_ROM_QSTR(MP_QSTR_Permission_WRITE), MP_ROM_INT(2) },
    { MP_ROM_QSTR(MP_QSTR_Permission_EXECUTE), MP_ROM_INT(4) },
    { MP_ROM_QSTR(MP_QSTR_Permission_ALL), MP_ROM_INT(7) },
};
MP_DEFINE_CONST_DICT(enum_demo_module_globals, enum_demo_module_globals_table);

const mp_obj_module_t enum_demo_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&enum_demo_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_enum_demo, enum_demo_user_cmodule);
```

### One more memory diagram: what the module exports

Instead of exporting a `Color` class object and its member objects, the compiled module exports integer constants under QSTR names.

```
enum_demo module globals
  |
  +-- get_color -> function object
  +-- check_color -> function object
  +-- ...
  +-- Color_RED -> 1
  +-- Color_GREEN -> 2
  +-- Color_BLUE -> 3
  +-- Permission_ALL -> 7
```

That matches the generated C globals table entries.

## Device Testing

This feature needs device testing because the generated C module runs inside MicroPython firmware on a microcontroller. The important check is behavior, not text output: enum member reads, comparisons, and bitmask operations should behave like plain integers.

## Closing

`IntEnum` support in `mypyc-micropython` is a good example of a compiler tradeoff that fits embedded Python well. Enums are convenient for humans, but on device you often want the cheapest possible representation.

The core trick is simple: evaluate enum member values at compile time, replace enum member access with `ConstIR`, and export the values with `MP_ROM_INT` through the module globals table.
