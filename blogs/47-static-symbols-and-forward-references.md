# 47. Static Symbols and Forward Reference Detection

When compiling Python to C for MicroPython, symbol naming and linkage become critical concerns. A function named `get()` in your module could collide with `get` from `urequest` or other MicroPython libraries. This post explains how we solved two related problems: C symbol collisions through static linkage, and forward reference bugs through compile-time detection.

## Table of Contents

- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [Part 2: C Background](#part-2-c-background)
- [Part 3: Implementation](#part-3-implementation)
- [Device Testing](#device-testing)
- [Closing](#closing)

## Part 1: Compiler Theory

### The Symbol Collision Problem

When you compile multiple C files into a single firmware image, all global symbols share the same namespace. Consider two modules:

```python
# my_utils.py
def get(key: str) -> str:
    return key.upper()

# urequest.py (MicroPython built-in)
def get(url: str) -> Response:
    # HTTP GET request
    ...
```

Without proper namespacing, both would generate C functions that could collide at link time.

### MicroPython's Naming Convention

MicroPython user modules typically prefix symbols with the module name:

```c
// Generated from my_utils.py
static mp_obj_t my_utils_get(mp_obj_t key_obj) { ... }
MP_DEFINE_CONST_FUN_OBJ_1(my_utils_get_obj, my_utils_get);
```

The function is prefixed with `my_utils_`, but the real question is: **what about the `_obj` symbol?**

### Two Types of Symbols

Every Python function compiles to two C symbols:

1. **The function implementation**: `my_utils_get` - the actual C function
2. **The function object**: `my_utils_get_obj` - a struct that MicroPython uses to call the function

The function implementation is already `static` (internal linkage). But the function object was NOT static in our original implementation:

```c
// Original: _obj has external linkage
static mp_obj_t my_utils_get(mp_obj_t key_obj) { ... }
MP_DEFINE_CONST_FUN_OBJ_1(my_utils_get_obj, my_utils_get);  // NOT static!
```

This means `my_utils_get_obj` is visible to the linker and could collide with similarly-named symbols from other modules.

### The Forward Reference Problem

A separate but related issue occurs when module-level constants are defined after functions that use them:

```python
def use_constant() -> int:
    return MY_CONST  # Error: MY_CONST not yet registered!

MY_CONST: int = 42
```

The compiler processes the file top-to-bottom. When it encounters `MY_CONST` in `use_constant()`, the constant hasn't been registered yet. The compiler falls through to emitting a bare C identifier `MY_CONST`, which doesn't exist.

### Why This Matters

Both problems manifest as build failures:

1. **Symbol collision**: `error: multiple definition of 'xxx_obj'`
2. **Forward reference**: `error: 'MY_CONST' undeclared`

The first is rare but catastrophic when it occurs. The second wastes developer time - you compile, wait for the firmware build, and only then discover the ordering issue.

## Part 2: C Background

### Static vs External Linkage

In C, symbols have two types of linkage:

**External linkage** (default): Symbol is visible across all compilation units. The linker combines them.

```c
// file1.c
int counter = 0;  // External linkage

// file2.c
extern int counter;  // References the same counter
```

**Internal linkage** (`static`): Symbol is only visible within its compilation unit. Each file gets its own copy.

```c
// file1.c
static int counter = 0;  // Only visible in file1.c

// file2.c
static int counter = 0;  // Different variable, only visible in file2.c
```

### The MP_DEFINE_CONST_FUN_OBJ Macro

MicroPython defines function objects using macros:

```c
// From MicroPython's obj.h
#define MP_DEFINE_CONST_FUN_OBJ_1(obj_name, fun_name) \
    const mp_obj_fun_builtin_fixed_t obj_name = { \
        .base = {&mp_type_fun_builtin_1}, \
        .fun._1 = fun_name, \
    }
```

This creates a `const` struct. By default, `const` at file scope has external linkage in C (unlike C++ where it's internal by default).

### Making Function Objects Static

Adding `static` before the macro:

```c
static MP_DEFINE_CONST_FUN_OBJ_1(my_utils_get_obj, my_utils_get);
```

Expands to:

```c
static const mp_obj_fun_builtin_fixed_t my_utils_get_obj = { ... };
```

Now `my_utils_get_obj` has internal linkage and can't collide with other modules.

### Forward Declarations and Static

When a symbol is used before it's defined, C requires a forward declaration:

```c
// Forward declaration
extern const mp_obj_fun_builtin_fixed_t my_func_obj;

// Use
mp_obj_t fn = MP_OBJ_FROM_PTR(&my_func_obj);

// Definition (later in file)
MP_DEFINE_CONST_FUN_OBJ_0(my_func_obj, my_func);
```

But here's the catch: **you cannot forward-declare a static symbol with `extern`**. They're incompatible:

```c
extern const int x;  // External linkage
static const int x = 5;  // Error: static declaration follows non-static
```

This forces an architectural decision: either keep symbols non-static with forward declarations, or make them static and ensure definition-before-use order.

## Part 3: Implementation

### Change 1: Static Function Objects

For module-level functions, we added `static` to all `MP_DEFINE_CONST_FUN_OBJ_*` macros:

```python
# function_emitter.py - Before
f"MP_DEFINE_CONST_FUN_OBJ_1({self.func_ir.c_name}_obj, {self.func_ir.c_name});"

# function_emitter.py - After
f"static MP_DEFINE_CONST_FUN_OBJ_1({self.func_ir.c_name}_obj, {self.func_ir.c_name});"
```

This applies to all function variations:
- `MP_DEFINE_CONST_FUN_OBJ_0` through `MP_DEFINE_CONST_FUN_OBJ_3`
- `MP_DEFINE_CONST_FUN_OBJ_VAR`
- `MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN`
- `MP_DEFINE_CONST_FUN_OBJ_KW`

### Change 2: Lambda Emission Order

Lambdas are referenced inside functions but defined after them:

```c
// Problem: lambda_0_obj used before defined
static mp_obj_t my_func(void) {
    mp_obj_t fn = MP_OBJ_FROM_PTR(&my_module__lambda_0_obj);  // Error!
    return fn;
}

// Lambda defined later
static mp_obj_t my_module__lambda_0(mp_obj_t x_obj) { ... }
static MP_DEFINE_CONST_FUN_OBJ_1(my_module__lambda_0_obj, my_module__lambda_0);
```

The fix: emit lambda code BEFORE the functions that use them:

```python
# compiler.py - Before
for lambda_func_ir in ir_builder.lambda_funcs:
    lambda_code, _ = lambda_emitter.emit()
    function_code.append(lambda_code)  # Appended after main functions

# compiler.py - After
lambda_code_list: list[str] = []
for lambda_func_ir in ir_builder.lambda_funcs:
    lambda_code, _ = lambda_emitter.emit()
    lambda_code_list.append(lambda_code)
function_code = lambda_code_list + function_code  # Prepended before main functions
```

### Change 3: Method Objects Stay Non-Static

Class methods have a complication: they can reference other methods from the same class:

```python
class App:
    def tick(self) -> None:
        effect = Effect(data=self.dispatch)  # Reference to dispatch method
    
    def dispatch(self, msg: object) -> None:
        ...
```

The generated C needs `dispatch_obj` available when compiling `tick`:

```c
static mp_obj_t App_tick_mp(mp_obj_t self_in) {
    // Creates bound method from dispatch_obj
    mp_obj_t bound = mp_obj_new_bound_meth(
        MP_OBJ_FROM_PTR(&App_dispatch_obj),  // Must be defined!
        self_in
    );
    ...
}

// dispatch defined later
MP_DEFINE_CONST_FUN_OBJ_2(App_dispatch_obj, App_dispatch_mp);
```

Since methods can reference each other in any order, we keep method objects non-static with `extern` forward declarations:

```c
// Forward declaration at top of file
extern const mp_obj_fun_builtin_fixed_t App_dispatch_obj;

// Now App_tick can reference it
static mp_obj_t App_tick_mp(mp_obj_t self_in) { ... }

// Definition comes later
MP_DEFINE_CONST_FUN_OBJ_2(App_dispatch_obj, App_dispatch_mp);
```

### Change 4: Forward Reference Warning

To catch constant ordering issues at compile time (rather than during firmware build), we added a warning system:

```python
# ir_builder.py

def prescan_module_constants(self, tree: ast.Module) -> None:
    """Pre-scan module to collect ALL constant definitions."""
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value:
                if isinstance(node.value, ast.Constant):
                    self._all_module_constants[node.target.id] = node.value.value

def _build_name(self, name: str, ...) -> ValueIR:
    # ... existing resolution logic ...
    
    # Warn on forward references
    if name in self._all_module_constants and name not in self._module_constants:
        warnings.warn(
            f"Forward reference to module-level constant '{name}' - define before use"
        )
    
    # ... fallthrough ...
```

The pre-scan runs once at the start of compilation, collecting ALL constants. Then during IR building, if a name is in `_all_module_constants` but not yet in `_module_constants` (the incrementally-built dict), it's a forward reference.

### Generated Code Comparison

**Before (non-static):**
```c
static mp_obj_t my_utils_get(mp_obj_t key_obj) {
    ...
}
MP_DEFINE_CONST_FUN_OBJ_1(my_utils_get_obj, my_utils_get);

static const mp_rom_map_elem_t my_utils_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&my_utils_get_obj) },
};
```

**After (static):**
```c
static mp_obj_t my_utils_get(mp_obj_t key_obj) {
    ...
}
static MP_DEFINE_CONST_FUN_OBJ_1(my_utils_get_obj, my_utils_get);

static const mp_rom_map_elem_t my_utils_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&my_utils_get_obj) },
};
```

The only visible change is the `static` keyword, but it prevents an entire class of linker errors.

### IR Dump Example

Using `mpy-compile --dump-ir text` on a file with a forward reference:

```
$ mpy-compile examples/forward_ref.py --dump-ir text
forward_ref.py:2: UserWarning: Forward reference to module-level constant 'MY_CONST' - define before use

def use_constant() -> MP_INT_T:
  c_name: forward_ref_use_constant
  body:
    return MY_CONST  # Will emit bare identifier - build will fail!

MY_CONST: int = 42
```

The warning alerts the developer immediately, before waiting for the firmware build.

## Device Testing

After implementing these changes, all device tests pass:

```
@S:lambda_closures
  OK: simple_lambda
  OK: lambda_with_closure(0)
  OK: lambda_with_closure(5)
  OK: multiple_lambdas
  OK: lambda_multi_capture(10,20)
  OK: use_higher_order
@D:486|486|0
ALL 486 TESTS PASSED
```

The lambda tests specifically verify that static lambda objects work correctly when referenced from containing functions.

## Closing

### Summary of Changes

| Component | Change | Reason |
|-----------|--------|--------|
| Module functions | Added `static` to `_obj` symbols | Prevent linker collisions |
| Generators | Added `static` to `_obj` symbols | Same as functions |
| Lambdas | Emit before containing functions | Definition-before-use for static |
| Methods | Keep non-static with `extern` forward decls | Methods reference each other |
| IR Builder | Pre-scan for forward reference warning | Catch ordering bugs early |

### Trade-offs

**Static function objects:**
- Pro: Eliminates symbol collision risk with MicroPython libs
- Pro: Slightly smaller binary (static symbols can be optimized more aggressively)
- Con: More complex emission order for lambdas

**Non-static method objects:**
- Pro: Methods can reference each other freely
- Con: Potential collision with identically-named methods in other modules
- Mitigation: Method names include class prefix (`App_dispatch_obj`)

**Forward reference warning:**
- Pro: Immediate feedback at Python compile time
- Pro: No firmware build required to discover the bug
- Con: Additional pre-scan pass adds ~5% to compile time

### Key Insight

The fundamental tension is between **flexibility** (reference anything from anywhere) and **safety** (prevent collisions and undefined references). Our solution:

1. **Module functions/lambdas**: Prioritize safety with `static`, enforce ordering
2. **Class methods**: Prioritize flexibility with forward declarations
3. **Constants**: Warn at compile time, let developer fix ordering

This matches how the code is actually used: module functions rarely reference each other by object, methods frequently do, and constants should always be defined at the top of the file anyway.

### What's Next

Future improvements could include:
- Automatic constant hoisting (move constants to top during compilation)
- Static method objects with topological sort of method dependencies
- Namespace prefixes for method objects to prevent cross-module collisions

For now, the current solution handles the common cases while providing clear warnings for the edge cases.
