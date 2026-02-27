# 22. Runtime imports

This post documents the runtime import feature in mypyc-micropython.

Goal: make `import X`, `X.attr`, and `X.func(...)` work reliably when compiling typed Python to MicroPython C modules, even when the target MicroPython module is implemented with `static` C symbols and has no public header to link against.

We'll walk from theory to the MicroPython C runtime, then into the IR and emitter changes that make this work.


## Part 1: Compiler Theory

### Python modules are runtime objects

In CPython (and MicroPython), a module is an object you can store in a variable, pass around, and query attributes on. At runtime, the interpreter:

- finds the module by name using the import system
- creates or reuses the module object
- executes its top-level code (first import only)
- returns the module object

That means `math.sqrt` is not a compile-time symbol, it's a runtime attribute lookup on a runtime object.

### Why imports need special handling in ahead-of-time compilers

mypyc-micropython is an ahead-of-time (AOT) compiler. It takes Python source and emits C code that runs inside MicroPython.

The import problem shows up as soon as you ask, "can we just call the C function that implements `math.sqrt`?"

Often, the answer is no:

- Some MicroPython modules expose no public headers.
- Many module functions are `static` inside their C file.
- Even when a function is not `static`, it may not be stable across ports.

So a "direct C call" strategy is fragile and incomplete.

### Compile-time vs runtime resolution

There are two ways to resolve `math.sqrt(x)`:

1. Compile-time resolution: treat `math.sqrt` as a known symbol and emit a direct C call.
2. Runtime resolution: ask MicroPython to import `math`, load `sqrt`, and call it.

Runtime resolution is slower than a direct call, but it is universal. It works for every module tier (we will define tiers in Part 3) and matches Python semantics.

### Where this fits in the pipeline

The core trick is to preserve "imported module" as a first-class concept in the IR so the emitter can generate the correct runtime calls.

ASCII view of the path from Python to C:

```
Python source
  |
  v
AST (ast.Import, ast.Attribute, ast.Call)
  |
  v
IRBuilder
  - register_import() tracks aliases
  - _build_attribute() recognizes module.attr
  - _build_module_call() recognizes module.func(...)
  |
  v
IR
  - ModuleImportIR / ModuleAttrIR / ModuleCallIR
  |
  v
FunctionEmitter
  - _emit_module_attr() / _emit_module_call()
  |
  v
C code
  - mp_import_name + mp_load_attr + mp_call_function_N
```

### Prelude pattern: why calls become instructions

In this compiler, expressions are represented as:

- a ValueIR for "the result"
- plus a list of InstrIR "prelude" steps that must run first

A runtime import and call has side effects and has to happen before the value exists, so it naturally becomes a prelude instruction.


## Part 2: C Background

This section is for Python developers. We'll map `import math`, `math.sqrt(x)`, and `math.pi` to the MicroPython C API.

### Modules and objects in MicroPython

MicroPython represents values as `mp_obj_t`. A module is just another `mp_obj_t`.

At runtime, importing a module means asking the runtime to return that module object.

### Runtime import: `mp_import_name`

MicroPython exposes a runtime import helper:

- `mp_import_name(...)` is implemented in MicroPython's runtime (see `py/runtime.c`).
- It takes a module name as a QSTR (interned string id) and returns the module object.

Conceptually:

```
mp_obj_t mod = mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
```

The key idea is that you do not need access to `math` internals. You just need the runtime to hand you the module object.

### Attribute lookup: `mp_load_attr` and QSTRs

MicroPython uses QSTRs for names like `"sqrt"` and `"pi"`. A QSTR is an interned identifier, written in C as `MP_QSTR_<name>`.

To get `math.sqrt`, you load the attribute `sqrt` from the module object:

```
mp_obj_t fn = mp_load_attr(mod, MP_QSTR_sqrt);
```

### Calling: `mp_call_function_*`

Once you have a callable object (like the function you just loaded), you call it through the generic call helpers:

```
mp_obj_t out = mp_call_function_1(fn, arg);
```

### How `import math` maps to C

Here is the C API pattern table we will use in the emitter:

| Python Code | C API Pattern |
|-------------|--------------|
| `import math` | `mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0))` |
| `math.sqrt(x)` | `mp_load_attr(mod, MP_QSTR_sqrt)` then `mp_call_function_1(fn, x)` |
| `math.pi` | `mp_load_attr(mod, MP_QSTR_pi)` |

Putting the pieces together:

```
mp_obj_t mod = mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
mp_obj_t fn = mp_load_attr(mod, MP_QSTR_sqrt);
mp_obj_t out = mp_call_function_1(fn, mp_obj_new_float(x));
```

This pattern works regardless of whether the MicroPython port compiled `math` as a built-in module, a frozen module, or something else. That's why it is the baseline strategy for runtime imports.


## Part 3: Implementation

### The problem

Before runtime imports, code like this is hard to compile correctly:

- `import math`
- `math.sqrt(...)`
- `math.pi`

If you try to lower these into direct C calls, you quickly run into MicroPython module implementation details. Some modules export clean C entry points, many do not.

Runtime imports side-step all of that. The compiler emits C that uses the MicroPython runtime to import and resolve names.

### Research: module tier classification

During implementation, modules were grouped into tiers based on how easy it is to call them directly from generated C:

- Tier 1 (Header-declared extern): builtins, time, machine, ready for direct `.pyi` based C calls.
- Tier 2 (Non-static, no header): gc, struct, sys, re, usable with `extern` declarations if you accept some portability risk.
- Tier 3 (All static): math, json, random, hashlib, must use runtime import because there is nothing to link against.

Why runtime import was chosen:

- Universal: works for all tiers.
- Simpler: one emission strategy covers calls and attributes.
- Correct semantics: matches Python's runtime module lookup and attribute access.

### The solution: new IR nodes

Runtime imports are represented explicitly in the IR so emitters can generate the MicroPython runtime calls.

Core nodes:

- `ModuleImportIR`: represents `import X`, holds `module_name` and a result `TempIR` for the imported module object.
- `ModuleCallIR`: represents `X.func(args)`, holds `module_name`, `func_name`, `args`, and `arg_preludes`.
- `ModuleAttrIR`: represents `X.attr`, holds `module_name` and `attr_name`.

These nodes capture intent. The emitter does not guess based on string matching. It sees "this is a module call" and emits the runtime pattern.

### IR builder changes

The IR builder learns to treat imported modules as special receivers.

1. `register_import()` processes `ast.Import` and `ast.ImportFrom`.
   - It tracks `alias -> module` mapping in `_import_aliases`.
   - Example: `import math as m` adds `_import_aliases["m"] = "math"`.

2. `_build_module_call()` intercepts method calls when the receiver is an imported module.
   - Example: `math.sqrt(x)` becomes a `ModuleCallIR` instead of a normal method call.
   - The call becomes a prelude instruction so the expression result can be a `TempIR`.

3. `_build_attribute()` intercepts attribute access when the value is an imported module.
   - Example: `math.pi` becomes a `ModuleAttrIR`.
   - This supports both direct reads and nesting inside larger expressions.

### Emitter changes

The function emitter adds two helpers that turn the new IR nodes into MicroPython runtime calls.

1. `_emit_module_call()` generates:
   - `mp_import_name(...)` to get the module object
   - `mp_load_attr(...)` to get the function attribute
   - `mp_call_function_N(...)` to call it

2. `_emit_module_attr()` generates:
   - `mp_import_name(...)` to get the module object
   - `mp_load_attr(...)` to load the attribute

### 3-stage view: Python input, IR output, C output

#### Stage 1: Python input

Use this exact source (`examples/math_ops.py`):

```python
import math
import time

def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance between two points."""
    dx: float = x2 - x1
    dy: float = y2 - y1
    return math.sqrt(dx * dx + dy * dy)

def circle_area(radius: float) -> float:
    """Area of a circle."""
    return math.pi * radius * radius

def trig_sum(angle: float) -> float:
    """Sum of sin and cos for an angle (in radians)."""
    return math.sin(angle) + math.cos(angle)
```

#### Stage 2: IR output

Full module IR dump (text format):

```
Module: math_ops (c_name: math_ops)

Functions:
  def distance(x1: MP_FLOAT_T, y1: MP_FLOAT_T, x2: MP_FLOAT_T, y2: MP_FLOAT_T) -> MP_FLOAT_T:
    c_name: math_ops_distance
    max_temp: 1
    locals: {x1: MP_FLOAT_T, y1: MP_FLOAT_T, x2: MP_FLOAT_T, y2: MP_FLOAT_T, dx: MP_FLOAT_T, dy: MP_FLOAT_T}
    body:
      dx: mp_float_t = (x2 - x1)
      dy: mp_float_t = (y2 - y1)
      # prelude:
        _tmp1 = math.sqrt(((dx * dx) + (dy * dy)))
      return _tmp1

  def circle_area(radius: MP_FLOAT_T) -> MP_FLOAT_T:
    c_name: math_ops_circle_area
    max_temp: 0
    locals: {radius: MP_FLOAT_T}
    body:
      return ((None * radius) * radius)

  def trig_sum(angle: MP_FLOAT_T) -> MP_FLOAT_T:
    c_name: math_ops_trig_sum
    max_temp: 2
    locals: {angle: MP_FLOAT_T}
    body:
      # prelude:
        _tmp1 = math.sin(angle)
        _tmp2 = math.cos(angle)
      return (_tmp1 + _tmp2)
```

Tree format for `distance`:

```
`-- root: FuncIR
    |-- name: "distance"
    |-- c_name: "math_ops_distance"
    |-- params: list[4]
    |-- return_type: CType.MP_FLOAT_T
    |-- body: list[3]
    |   |-- [0]: AnnAssignIR (dx = x2 - x1)
    |   |-- [1]: AnnAssignIR (dy = y2 - y1)
    |   `-- [2]: ReturnIR
    |       |-- value: TempIR (_tmp1)
    |       `-- prelude: list[1]
    |           `-- [0]: MethodCallIR
    |               |-- receiver: NameIR ("math")
    |               |-- method: "sqrt"
    |               `-- args: [BinOpIR ((dx*dx) + (dy*dy))]
    |-- uses_imports: False
    `-- max_temp: 1
```

Two details to notice:

- The `sqrt` call lives in the return's prelude, not inline in the `ReturnIR` value. That is the prelude pattern at work.
- The tree includes `uses_imports: False`. The runtime import emission is driven by the import-aware nodes and patterns, not this flag.

#### Stage 3: C output

Exact generated C for `distance` (`modules/usermod_math_ops/math_ops.c`):

```c
static mp_obj_t math_ops_distance(size_t n_args, const mp_obj_t *args) {
    mp_float_t x1 = mp_get_float_checked(args[0]);
    mp_float_t y1 = mp_get_float_checked(args[1]);
    mp_float_t x2 = mp_get_float_checked(args[2]);
    mp_float_t y2 = mp_get_float_checked(args[3]);

    mp_float_t dx = (x2 - x1);
    mp_float_t dy = (y2 - y1);
    return mp_call_function_1(
        mp_load_attr(
            mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
            MP_QSTR_sqrt),
        mp_obj_new_float(((dx * dx) + (dy * dy))));
}
```

What to look for:

- `mp_import_name(MP_QSTR_math, ...)` fetches the module object.
- `mp_load_attr(..., MP_QSTR_sqrt)` loads the function.
- `mp_call_function_1(...)` calls it with one argument.

Exact generated C for `circle_area` (attribute access pattern for `math.pi`):

```c
static mp_obj_t math_ops_circle_area(mp_obj_t radius_obj) {
    mp_float_t radius = mp_get_float_checked(radius_obj);

    return mp_binary_op(MP_BINARY_OP_MULTIPLY,
        mp_binary_op(MP_BINARY_OP_MULTIPLY,
            mp_load_attr(
                mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                MP_QSTR_pi),
            mp_obj_new_float(radius)),
        mp_obj_new_float(radius));
}
```

This is the same runtime import idea, but for attributes:

- import module
- load attribute
- feed it into normal expression emission (`mp_binary_op` here)

### How the pieces work together (end-to-end)

Here is the high-level translation of `return math.sqrt(dx * dx + dy * dy)`:

```
Python
  return math.sqrt(expr)

IR
  _tmp1 = ModuleCallIR(module_name="math", func_name="sqrt", args=[expr])
  return _tmp1

C
  mod = mp_import_name(MP_QSTR_math, ...)
  fn = mp_load_attr(mod, MP_QSTR_sqrt)
  return mp_call_function_1(fn, boxed_expr)
```

The important property is that nothing assumes `math` has linkable symbols. Everything flows through MicroPython's runtime.

### Testing

- Device testing results: 300/300 tests pass on ESP32-C6.

This matters because the generated C runs in a constrained runtime on a 32-bit MCU. Desktop compilation is not enough for confidence.

### Future work

- Cached module references: import once per function and reuse the module object.
- `.pyi` direct C calls for Tier 1 modules: skip runtime import when a stable C API exists.
- `from X import Y` optimized emission: import module once, then load and reuse `Y`.
