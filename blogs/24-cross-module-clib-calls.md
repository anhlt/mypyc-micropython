# Cross-Module CLib Calls: Direct C Calls from .pyi Stubs

*Compiling `import lvgl as lv` calls into direct wrapper function calls, resolved at compile time.*

---

## Table of Contents

1. [Call Resolution Theory](#part-1-compiler-theory) -- Why `lv.xxx()` used to fall back to dynamic dispatch
2. [C Background](#part-2-c-background-for-python-developers) -- Linkage, headers, and why `static` broke everything
3. [Implementation](#part-3-implementation) -- New IR nodes, import tracking, extern declarations, and codegen

---

# Part 1: Compiler Theory

## The Problem: The Compiler Had No Meaningful Type for `lv`

From the compiler's point of view, a call like this is ambiguous:

```python
import lvgl as lv

def create_ui() -> int:
    screen = lv.lv_screen_active()
    label = lv.lv_label_create(screen)
    return 0
```

If the compiler does not know that `lv` is an external C library module, it has only one safe option: treat `lv` as a generic Python object and do MicroPython dynamic dispatch at runtime.

That old behavior is slow and indirect because it must:

1. Look up the attribute by name (qstr) on an object
2. Build a bound method object
3. Call it through the runtime call machinery

In this codebase, that dynamic path is emitted by the generic method call fallback:

```c
/* src/mypyc_micropython/container_emitter.py */
mp_obj_t __method[2 + n_args];
mp_load_method(receiver, MP_QSTR_method_name, __method);
/* fill args */
mp_call_method_n_kw(n_args, 0, __method);
```

That is correct for unknown objects, but it is wasted work for something like LVGL where the target function is known at compile time.

## The Goal: Resolve External Calls at Compile Time

We already have a description of the external API: the `.pyi` stub used to generate the MicroPython binding module (blog 21). The missing piece was teaching the typed-Python compiler to use that same stub metadata when compiling user code.

What we want instead is a direct C call to the binding wrapper function:

```c
/* Direct C call, resolved at compile time */
mp_obj_t label = lv_label_create_wrapper(screen);
```

This changes the runtime work from "find a method and call it" into "call a C function".

## Cross-Module Linking Is the Real Constraint

There are two generated artifacts in play:

1. `lvgl.c`: generated from `lvgl.pyi`, it defines `lv_label_create_wrapper`, `lv_obj_add_flag_wrapper`, and so on.
2. `ui.c`: generated from user Python code, it must call those wrapper functions.

These are separate C translation units.

ASCII view of the firmware build:

```
lvgl.pyi                 user code (ui.py)
   |                          |
   v                          v
generated lvgl.c          generated ui.c
   |                          |
   +-----------+  +-----------+
               v  v
              linker
               |
               v
         firmware image
```

If the wrapper functions in `lvgl.c` are `static`, they are invisible outside that file. The linker cannot resolve symbols from `ui.c`.

So the feature is not just "build a better call expression". It is: build a compile-time call resolution path that also produces linkable symbols across C files.

---

# Part 2: C Background for Python Developers

## `static` vs `extern`: What the Linker Can See

In C, `static` on a function at file scope means "this symbol is private to this `.c` file".

```c
static mp_obj_t lv_label_create_wrapper(mp_obj_t parent) {
    /* ... */
}
```

That compiles, but nothing outside `lvgl.c` can call it.

To make a function callable from another `.c` file, it must have external linkage:

```c
mp_obj_t lv_label_create_wrapper(mp_obj_t parent) {
    /* ... */
}
```

Then, in the other file, you need a declaration:

```c
extern mp_obj_t lv_label_create_wrapper(mp_obj_t);
```

The rule of thumb:

- Definition lives in exactly one `.c` file
- Declaration can appear in any number of other `.c` files
- Linker matches calls to the single definition

## Why This Project Uses Wrapper Functions That Take `mp_obj_t`

The binding generator emits wrapper functions using MicroPython's calling convention. Arguments and return values are `mp_obj_t`.

That matters because it makes the cross-module call easy:

- User code generator already works in `mp_obj_t` for object values
- Wrappers already accept `mp_obj_t`
- No new conversion layer is needed in the typed-Python compiler

Conceptually:

```
ui.c (compiled Python)                  lvgl.c (generated bindings)

  mp_obj_t screen  ------------------->  lv_screen_active_wrapper() -> mp_obj_t
  mp_obj_t label   ------------------->  lv_label_create_wrapper(screen) -> mp_obj_t
```

## Enums: Why We Emit Integers, Not Attribute Lookups

LVGL enums in the stub are already integers.

```python
class LvAlign:
    CENTER: int = 9
```

If we keep them as runtime attribute lookups, we pay for:

- `lv.LvAlign` lookup
- `CENTER` lookup on the class

If we resolve them at compile time, we can emit `9` directly. On a microcontroller, saving two attribute lookups per enum reference matters.

---

# Part 3: Implementation

This feature touched eight files. The change is easiest to understand by following the full pipeline from stub to IR to C.

## Step 0: Inputs

The binding stub lives at:

- `src/mypyc_micropython/c_bindings/stubs/lvgl/lvgl.pyi`

The user code we will compile in this post is small and stays within 0 to 3 arguments per wrapper call:

```python
import lvgl as lv

def create_ui() -> int:
    screen = lv.lv_screen_active()
    label = lv.lv_label_create(screen)
    lv.lv_label_set_text(label, "Hello")
    lv.lv_obj_add_flag(label, lv.LvObjFlag.CLICKABLE)
    return lv.LvAlign.CENTER
```

## Step 1: Parse the `.pyi` Stub into `CLibraryDef`

The stub parser produces a `CLibraryDef` describing:

- functions (name, params, return type)
- structs
- enums (class name, member names, integer values)

In code, this is the entry point:

```python
from pathlib import Path
from mypyc_micropython.c_bindings.stub_parser import StubParser

lib = StubParser().parse_file(
    Path("src/mypyc_micropython/c_bindings/stubs/lvgl/lvgl.pyi")
)
```

That `lib` object is passed into the typed-Python compiler via `external_libs`.

## Step 2: Two New IR Nodes

We added two expression IR nodes in `src/mypyc_micropython/ir.py`:

- `CLibCallIR`: a call to a wrapper function in an external library module
- `CLibEnumIR`: a resolved enum member value (an integer constant)

The definitions are real dataclasses with the data the emitter needs:

```python
@dataclass
class CLibCallIR(ExprIR):
    lib_name: str
    func_name: str
    c_wrapper_name: str
    args: list[ValueIR]
    arg_preludes: list[list[InstrIR]] = field(default_factory=list)
    is_void: bool = False

@dataclass
class CLibEnumIR(ExprIR):
    lib_name: str
    enum_class: str
    member_name: str
    c_enum_value: int
```

## Step 3: Track Imports and Build CLib IR in the IR Builder

The key idea is simple: if we see `import lvgl as lv`, remember that `lv` refers to the external library `lvgl`.

That happens in `src/mypyc_micropython/ir_builder.py`:

```python
self._external_libs: dict[str, CLibraryDef] = external_libs or {}
self._import_aliases: dict[str, str] = {}

def register_import(self, node: ast.Import | ast.ImportFrom) -> None:
    if isinstance(node, ast.Import):
        for alias in node.names:
            module_name = alias.name
            local_name = alias.asname or alias.name
            if module_name in self._external_libs:
                self._import_aliases[local_name] = module_name
```

Then `_build_method_call` intercepts the `lv.xxx(...)` pattern before it becomes a generic MicroPython method call:

```python
if isinstance(expr.func.value, ast.Name):
    var_name = expr.func.value.id
    if var_name in self._import_aliases:
        return self._build_clib_call(expr, var_name, locals_)
```

For enums, `_build_attribute` intercepts `lv.EnumClass.MEMBER` and resolves it to an integer using the stub's `enum_def.values`:

```python
enum_def = lib_def.enums.get(enum_class_name)
if enum_def and member_name in enum_def.values:
    c_value = enum_def.values[member_name]
    return CLibEnumIR(..., c_enum_value=c_value), []
```

## Step 4: IR Dump (Text Format)

With the example input, the IR dump for `create_ui` is:

```
def create_ui() -> MP_INT_T:
  c_name: ui_create_ui
  max_temp: 0
  locals: {screen: MP_OBJ_T, label: MP_OBJ_T}
  body:
    (new) screen = lvgl.lv_screen_active()
    (new) label = lvgl.lv_label_create(screen)
    lvgl.lv_label_set_text(label, "Hello")
    lvgl.lv_obj_add_flag(label, lvgl.LvObjFlag.CLICKABLE = 2)
    return lvgl.LvAlign.CENTER = 9
```

Those two lines are the important ones:

- `lvgl.lv_label_create(screen)` is a `CLibCallIR`
- `lvgl.LvAlign.CENTER = 9` is a `CLibEnumIR`

They show up like this because `src/mypyc_micropython/ir_visualizer.py` prints them explicitly:

```python
elif isinstance(value, CLibCallIR):
    return f"{value.lib_name}.{value.func_name}({args})"
elif isinstance(value, CLibEnumIR):
    return f"{value.lib_name}.{value.enum_class}.{value.member_name} = {value.c_enum_value}"
```

## Step 5: Emit Direct Wrapper Calls in the Function Emitter

`src/mypyc_micropython/function_emitter.py` adds two cases:

```python
elif isinstance(value, CLibCallIR):
    return self._emit_clib_call(value, native)
elif isinstance(value, CLibEnumIR):
    return str(value.c_enum_value), "mp_int_t"
```

The call emission is a direct C call to the wrapper name carried by the IR:

```python
def _emit_clib_call(self, call: CLibCallIR, native: bool = False) -> tuple[str, str]:
    # box args to mp_obj_t
    if call.is_void:
        return f"({call.c_wrapper_name}({args_str}), mp_const_none)", "mp_obj_t"
    return f"{call.c_wrapper_name}({args_str})", "mp_obj_t"
```

This is the main reason we needed a new IR node.

The existing `CallIR` path assumes a non-builtin call returns an integer:

```python
return f"mp_obj_get_int({call.c_func_name}({args_str}))", "mp_int_t"
```

That is wrong for wrapper calls, which return `mp_obj_t`.

## Step 6: Generate `extern` Declarations in the Module Emitter

The compiled user module needs prototypes for wrapper functions defined in another C file.

`src/mypyc_micropython/module_emitter.py` emits declarations near the top of the generated `.c`:

```c
/* External library: lvgl */
extern mp_obj_t lv_screen_active_wrapper(void);
extern mp_obj_t lv_screen_load_wrapper(mp_obj_t);
extern mp_obj_t lv_obj_create_wrapper(mp_obj_t);
extern mp_obj_t lv_obj_delete_wrapper(mp_obj_t);
extern mp_obj_t lv_obj_clean_wrapper(mp_obj_t);
extern mp_obj_t lv_obj_add_flag_wrapper(mp_obj_t, mp_obj_t);
/* ... */
```

This is self-contained. It avoids needing an `#include` path for a generated header during compilation of every user module.

## Step 7: Generated C Output (Relevant Excerpt)

With direct wrapper calls and compile-time enums, the generated function becomes:

```c
static mp_obj_t ui_create_ui(void) {
    mp_obj_t screen = lv_screen_active_wrapper();
    mp_obj_t label = lv_label_create_wrapper(screen);
    (void)(lv_label_set_text_wrapper(label, mp_obj_new_str("Hello", 5)), mp_const_none);
    (void)(lv_obj_add_flag_wrapper(label, mp_obj_new_int(2)), mp_const_none);
    return mp_obj_new_int(9);
}
```

No `mp_load_method`. No bound method objects. No attribute lookups. The call targets are compile-time constants.

## Before and After: What Changed in Generated C

Before, `lv.xxx(...)` ended up in the generic fallback method call path:

```c
mp_obj_t __method[2 + n_args];
mp_load_method(receiver, MP_QSTR_method_name, __method);
/* fill args */
mp_call_method_n_kw(n_args, 0, __method);
```

After, it is a direct call to the wrapper symbol:

```c
mp_obj_t label = lv_label_create_wrapper(screen);
```

The runtime difference is not subtle.

## Step 8: Make Wrapper Functions Linkable Across C Files

The binding generator lives in `src/mypyc_micropython/c_bindings/c_emitter.py`.

Originally, wrappers were emitted as `static`, which works when Python calls them through the module globals table, but fails when another C file wants to call them.

The emitter now takes `emit_public`:

```python
class CEmitter:
    def __init__(self, library: CLibraryDef, emit_public: bool = False) -> None:
        self.emit_public = emit_public

def _wrapper_linkage_prefix(self) -> str:
    return "" if self.emit_public else "static "
```

With `emit_public=True`, wrappers drop the `static` keyword.

### Header Generation

We also added a header generator:

```python
def emit_header_file(self) -> str:
    guard = self._header_guard_name()
    lines = [f"#ifndef {guard}", f"#define {guard}", '#include "py/obj.h"']
    for func in self.lib.functions.values():
        if func.has_var_args:
            continue
        lines.append(self._make_wrapper_extern_decl(func))
    lines.append("#endif")
    return "\n".join(lines)
```

The typed-Python module currently uses `extern` declarations directly (Step 6). The header is still useful for build systems that prefer an include-based integration.

## Wiring: Pass External Libraries Through the Compiler

The compiler entry points in `src/mypyc_micropython/compiler.py` now accept `external_libs`.

Two details matter:

1. Imports are processed before functions and classes so aliases are registered.
2. Only libraries that were actually imported are passed to `ModuleEmitter`.

The import pass is explicit:

```python
for node in ast.iter_child_nodes(tree):
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        ir_builder.register_import(node)
```

And we filter the library set by what the IR builder used:

```python
used_libs = {
    key: value
    for key, value in (external_libs or {}).items()
    if key in ir_builder.used_external_libs
}
```

## The Eight Files Changed, and Why

1. `src/mypyc_micropython/ir.py`
   Added `CLibCallIR` and `CLibEnumIR` so the backend can emit correct C for wrapper calls and compile-time enums.

2. `src/mypyc_micropython/c_bindings/c_emitter.py`
   Added `emit_public` so wrappers can be called from other C files, plus `emit_header_file()` for extern declarations.

3. `src/mypyc_micropython/ir_builder.py`
   Added `external_libs`, import alias tracking, and builders for `CLibCallIR` and `CLibEnumIR`.

4. `src/mypyc_micropython/function_emitter.py`
   Added emission logic for `CLibCallIR` (direct wrapper call) and `CLibEnumIR` (literal integer).

5. `src/mypyc_micropython/module_emitter.py`
   Emitted `extern` declarations for wrapper functions so user modules compile without needing generated headers.

6. `src/mypyc_micropython/compiler.py`
   Wired `external_libs` through `compile_source()` and `compile_to_micropython()`, registered imports early, and passed only used libraries to the module emitter.

7. `src/mypyc_micropython/ir_visualizer.py`
   Taught the IR dumper how to print `CLibCallIR` and `CLibEnumIR` so `--dump-ir text` stays useful.

8. `tests/test_compiler.py`
   Added `TestExternalLibCalls` with 13 tests covering direct calls, void calls, enum access, import aliases, extern declarations, and public wrapper visibility.

## Design Decisions (With Real Code)

### Why New IR Nodes Instead of Reusing `CallIR`?

`CallIR` assumes non-builtin calls return integers:

```python
return f"mp_obj_get_int({call.c_func_name}({args_str}))", "mp_int_t"
```

External wrapper functions return `mp_obj_t`, and void wrappers still need to produce a value in expression contexts. `CLibCallIR` carries `is_void` and the exact `c_wrapper_name`.

### Why Make Wrappers Non-Static?

Because `static` makes symbols file-local. A user module compiled into `ui.c` cannot call `static mp_obj_t lv_label_create_wrapper(...)` in `lvgl.c`.

### Why `extern` Declarations Instead of `#include`?

`extern` declarations are self-contained and avoid adding new include-path requirements for every generated user module. The header generator exists, but the default flow does not depend on it.

### Why Resolve Enums at Compile Time?

The stub already has the values, and `ir_builder.py` turns `lv.LvAlign.CENTER` into `c_enum_value=9`. The backend emits `9`, saving runtime work.

## Testing Coverage

The new tests are in `tests/test_compiler.py` under `class TestExternalLibCalls`. They build a minimal `CLibraryDef` in memory and then verify:

- direct wrapper names appear in generated C
- void wrappers are handled
- enum members become integer constants
- extern declarations are emitted only when the library is imported
- `emit_public=True` removes `static` from wrapper definitions

That is enough to protect the call resolution path and the linkability requirement.

## What This Enables Next

With CLib calls and enums in the typed-Python IR, the next optimizations are straightforward:

1. Filter wrapper `extern` declarations to only the functions referenced in the module
2. Support wrapper calling conventions for functions with more than three parameters
3. Extend enum resolution to cover any additional constant patterns that show up in real stubs
