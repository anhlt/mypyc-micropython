# 47. Static Symbols and C Linking

When compiling Python to C for MicroPython, symbol naming and linkage become critical concerns. A function named `get()` in your module could collide with `get` from `urequest` or other MicroPython libraries. This post explains how C linking works and how we use static linkage to prevent symbol collisions in compiled MicroPython modules.

## Table of Contents

- [Part 1: The Problem](#part-1-the-problem)
- [Part 2: How C Linking Works](#part-2-how-c-linking-works)
- [Part 3: Implementation](#part-3-implementation)
- [Closing](#closing)

## Part 1: The Problem

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

### Why This Matters

Symbol collisions manifest as build failures:

```
error: multiple definition of 'get_obj'
```

This is rare but catastrophic when it occurs. Your firmware build fails, and you have to hunt down which modules are colliding.

## Part 2: How C Linking Works

### The C Build Pipeline

To understand why symbol collisions happen, we need to understand how C code becomes firmware. The process has distinct phases:

```
Source Files (.c)
      |
      v  [Phase 1: Preprocessing]
      |  - Expands #include directives
      |  - Expands #define macros
      |  - Processes #ifdef conditionals
      |
Preprocessed Source (.i)
      |
      v  [Phase 2: Compilation]
      |  - Parses C syntax
      |  - Generates machine code
      |  - Creates symbol table
      |
Object Files (.o)
      |
      v  [Phase 3: Linking]
      |  - Combines all object files
      |  - Resolves symbol references
      |  - Produces final executable
      |
Executable / Firmware (.elf, .bin)
```

### Phase 1: Preprocessing

The preprocessor runs before actual compilation. It's essentially a text substitution engine:

```c
// Before preprocessing
#include "py/obj.h"
#define MAX_SIZE 100

int buffer[MAX_SIZE];
MP_DEFINE_CONST_FUN_OBJ_1(my_func_obj, my_func);

// After preprocessing
// ... thousands of lines from obj.h ...
int buffer[100];
const mp_obj_fun_builtin_fixed_t my_func_obj = {
    .base = {&mp_type_fun_builtin_1},
    .fun._1 = my_func,
};
```

The `MP_DEFINE_CONST_FUN_OBJ_1` macro expands to a struct definition. This is important: at this stage, we can add `static` before the macro and it becomes part of the struct definition.

### Phase 2: Compilation

Each `.c` file is compiled **independently** into an object file (`.o`). The compiler:

1. Parses the C code
2. Generates machine code for each function
3. Creates a **symbol table** listing what this file provides and needs

**Critical insight**: The compiler doesn't see other `.c` files. When it encounters a function call like `printf()`, it just records "this code needs a symbol called `printf`" without knowing where it is.

```c
// my_utils.c
#include <stdio.h>

static mp_obj_t my_utils_get(mp_obj_t key_obj) {
    printf("Getting key\n");  // Compiler: "I need 'printf' from somewhere"
    return key_obj;
}
```

The compiler produces `my_utils.o` containing:
- Machine code for `my_utils_get`
- A note: "I need `printf` - please find it later"

### Phase 3: Linking

The linker's job is to combine all object files and resolve all the "I need X" references:

```
       my_utils.o              urequest.o              libc.a
    +---------------+       +---------------+       +---------------+
    | my_utils_get  |       | urequest_get  |       | printf        |
    | needs: printf |       | needs: printf |       | malloc        |
    +---------------+       +---------------+       | free          |
           |                       |                +---------------+
           |                       |                       |
           +----------+------------+-----------------------+
                      |
                      v
              [Linker combines everything]
                      |
                      v
                 firmware.elf
```

### The Symbol Table

Each object file contains a **symbol table** - a list of symbols it defines and needs:

```bash
$ nm my_utils.o
00000000 t my_utils_get        # t = local (static) text symbol
00000040 D my_utils_get_obj    # D = global data symbol
         U printf              # U = undefined, needed from elsewhere
```

Symbol types:
- `T` / `t` = text (code) section, uppercase = global, lowercase = local
- `D` / `d` = data section, uppercase = global, lowercase = local
- `U` = undefined (needs to be found elsewhere)

### How the Linker Resolves Symbols

The linker builds a global symbol table from all object files:

```
Global Symbol Table (built by linker)
+---------------------+------------------+--------------------+
| Symbol              | Defined In       | Referenced By      |
+---------------------+------------------+--------------------+
| my_utils_get        | my_utils.o       | (internal only)    |
| my_utils_get_obj    | my_utils.o       | my_utils.o, main.o |
| urequest_get        | urequest.o       | (internal only)    |
| urequest_get_obj    | urequest.o       | urequest.o         |
| printf              | libc.a           | my_utils.o         |
+---------------------+------------------+--------------------+
```

The linker then:
1. For each undefined symbol (U), find a matching definition
2. Update the machine code with the actual addresses
3. Combine everything into one executable

### What Happens With Duplicate Symbols

If two object files define the same global symbol:

```
Global Symbol Table
+---------------------+------------------+
| Symbol              | Defined In       |
+---------------------+------------------+
| get_obj             | my_utils.o       | <- CONFLICT!
| get_obj             | urequest.o       | <- CONFLICT!
+---------------------+------------------+
```

The linker fails:

```
ld: error: duplicate symbol: get_obj
>>> defined in my_utils.o
>>> defined in urequest.o
```

This is the **symbol collision** we're trying to prevent.

### Static vs External Linkage

C provides two types of linkage:

**External linkage** (default): Symbol is exported to the linker's global table. Visible across all compilation units.

```c
// file1.c
int counter = 0;  // External linkage - appears in global symbol table

// file2.c
extern int counter;  // "Find 'counter' in some other object file"
counter++;           // Uses the same counter from file1.c
```

**Internal linkage** (`static`): Symbol is NOT exported. Only visible within its compilation unit. The linker never sees it.

```c
// file1.c
static int counter = 0;  // Internal linkage - hidden from linker

// file2.c
static int counter = 0;  // DIFFERENT variable! Also hidden from linker
```

With `static`, each file gets its own private copy. The linker doesn't know they exist, so no conflicts are possible.

### Visualizing Linkage with nm

Let's see the difference in symbol tables:

**Without static:**
```c
// my_utils.c
const mp_obj_fun_builtin_fixed_t my_utils_get_obj = { ... };
```

```bash
$ nm my_utils.o
00000040 D my_utils_get_obj    # D = global data, visible to linker
```

**With static:**
```c
// my_utils.c
static const mp_obj_fun_builtin_fixed_t my_utils_get_obj = { ... };
```

```bash
$ nm my_utils.o
00000040 d my_utils_get_obj    # d = local data, hidden from linker
```

The only difference is uppercase `D` vs lowercase `d`, but it completely changes visibility.

### Why Module Prefix Isn't Enough

You might think `my_utils_get_obj` is safe because of the `my_utils_` prefix. But consider:

1. **Accidental collisions**: Two developers might create `utils.py` in different projects
2. **MicroPython internals**: Some internal symbols might match your naming
3. **Future-proofing**: A new MicroPython version might add a module with your name
4. **Package flattening**: A package `myapp/utils.py` might have the same prefix as `myapp_utils.py`

`static` eliminates the entire class of problems.

### Benefits of Static Linkage

Beyond preventing collisions, `static` enables compiler optimizations:

1. **Inlining**: The compiler knows the function isn't called from other files, so it can inline it
2. **Dead code elimination**: If a static function isn't used, it can be removed entirely
3. **Smaller binary**: Local symbols don't need entries in the dynamic symbol table

```c
// With static, compiler can optimize more aggressively
static mp_obj_t helper(mp_obj_t x) {
    return x;  // Might be inlined at call sites
}

// Without static, compiler must preserve the function
// in case another file references it
mp_obj_t helper(mp_obj_t x) {
    return x;  // Must remain as separate function
}
```

### Forward Declarations and Static

When a symbol is used before it's defined, C requires a forward declaration:

```c
// Forward declaration - "this symbol exists somewhere"
extern const mp_obj_fun_builtin_fixed_t my_func_obj;

// Use - compiler trusts the forward declaration
mp_obj_t fn = MP_OBJ_FROM_PTR(&my_func_obj);

// Definition (later in file)
MP_DEFINE_CONST_FUN_OBJ_0(my_func_obj, my_func);
```

But here's the catch: **you cannot forward-declare a static symbol with `extern`**. They're fundamentally incompatible:

```c
extern const int x;        // Says: "x has external linkage, find it elsewhere"
static const int x = 5;    // Says: "x has internal linkage, it's private"
// error: static declaration of 'x' follows non-static declaration
```

The `extern` keyword explicitly requests external linkage, while `static` explicitly requests internal linkage. The compiler cannot reconcile these conflicting instructions.

This forces an architectural decision: **either keep symbols non-static with forward declarations, or make them static and ensure definition-before-use order.**

For our compiler, this meant:
- **Lambdas**: Reorder emission so lambdas are defined before functions that use them
- **Methods**: Keep non-static with `extern` forward declarations (methods reference each other)

### How Lambdas Get Compiled

To understand why lambda ordering matters, let's trace how a Python lambda becomes C code.

**Python source:**
```python
def make_adder(n: int) -> Callable[[int], int]:
    return lambda x: x + n
```

**What the compiler generates:**

Lambdas are "lifted" out of their containing function and compiled as separate top-level functions:

```c
// Lambda lifted to module level
static mp_obj_t mymodule__lambda_0(mp_obj_t x_obj) {
    mp_int_t x = mp_obj_get_int(x_obj);
    // Note: 'n' captured via closure mechanism (separate topic)
    mp_int_t n = /* get from closure */;
    return mp_obj_new_int(x + n);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mymodule__lambda_0_obj, mymodule__lambda_0);

// The containing function references the lambda
static mp_obj_t mymodule_make_adder(mp_obj_t n_obj) {
    // Get reference to lambda function object
    mp_obj_t lambda_fn = MP_OBJ_FROM_PTR(&mymodule__lambda_0_obj);
    // ... create closure with captured 'n' ...
    return closure;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mymodule_make_adder_obj, mymodule_make_adder);
```

**The ordering problem:**

Originally, our compiler emitted code in Python source order:

```c
// WRONG ORDER - main function first
static mp_obj_t mymodule_make_adder(mp_obj_t n_obj) {
    mp_obj_t lambda_fn = MP_OBJ_FROM_PTR(&mymodule__lambda_0_obj);  // ERROR!
    // ^^^^ mymodule__lambda_0_obj not yet defined!
    ...
}

// Lambda emitted after
static mp_obj_t mymodule__lambda_0(mp_obj_t x_obj) { ... }
static MP_DEFINE_CONST_FUN_OBJ_1(mymodule__lambda_0_obj, mymodule__lambda_0);
```

With external linkage, we could add a forward declaration:
```c
extern const mp_obj_fun_builtin_fixed_t mymodule__lambda_0_obj;  // Forward declare
```

But with static linkage, forward declarations don't work. The solution: **emit lambdas first**.

```c
// CORRECT ORDER - lambdas first
static mp_obj_t mymodule__lambda_0(mp_obj_t x_obj) { ... }
static MP_DEFINE_CONST_FUN_OBJ_1(mymodule__lambda_0_obj, mymodule__lambda_0);

// Now main function can reference it
static mp_obj_t mymodule_make_adder(mp_obj_t n_obj) {
    mp_obj_t lambda_fn = MP_OBJ_FROM_PTR(&mymodule__lambda_0_obj);  // OK!
    ...
}
```

This is a general pattern in C: **definition must precede use** for static symbols.

### The MicroPython Build System

MicroPython firmware builds involve hundreds of `.c` files:

```
micropython/
├── py/              # Core Python runtime (50+ files)
├── extmod/          # Extended modules (30+ files)
├── ports/esp32/     # ESP32-specific code (20+ files)
└── modules/         # User modules (your code!)
    ├── my_utils.c
    ├── urequest.c
    └── ...
```

All these compile to `.o` files and link into one firmware. With hundreds of symbols, collisions become increasingly likely without proper isolation.

### ESP-IDF Component System

For ESP32, MicroPython uses ESP-IDF's component system:

```
build/
├── esp-idf/
│   ├── freertos/libfreertos.a      # FreeRTOS library
│   ├── driver/libdriver.a          # Hardware drivers
│   └── ...
├── micropython/libmicropython.a    # MicroPython + user modules
└── firmware.elf                    # Final linked firmware
```

Each component compiles to a static library (`.a` = archive of `.o` files). The final link combines all libraries. Any global symbol collision across ANY component causes a build failure.

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

Adding `static` before the macro:

```c
static MP_DEFINE_CONST_FUN_OBJ_1(my_utils_get_obj, my_utils_get);
```

Expands to:

```c
static const mp_obj_fun_builtin_fixed_t my_utils_get_obj = { ... };
```

Now `my_utils_get_obj` has internal linkage and can't collide with other modules.

### Change 2: Lambda Emission Order

Making lambdas static introduced a new challenge. Lambdas are referenced inside functions but were originally defined after them:

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

With external linkage, we could use forward declarations. But `static` and `extern` are incompatible:

```c
extern const mp_obj_fun_builtin_fixed_t x;  // External linkage
static const mp_obj_fun_builtin_fixed_t x = { ... };  // Error!
// error: static declaration follows non-static declaration
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

### Verifying the Change

You can verify static linkage with `nm`:

```bash
# Compile a module
$ xtensa-esp32-elf-gcc -c my_utils.c -o my_utils.o

# Check symbol visibility
$ nm my_utils.o | grep get_obj
00000040 d my_utils_get_obj    # lowercase 'd' = local (static)

# Before the change, it would show:
00000040 D my_utils_get_obj    # uppercase 'D' = global (external)
```

## Closing

### Summary of Changes

| Component | Change | Reason |
|-----------|--------|--------|
| Module functions | Added `static` to `_obj` symbols | Prevent linker collisions |
| Generators | Added `static` to `_obj` symbols | Same as functions |
| Lambdas | Emit before containing functions | Definition-before-use for static |
| Methods | Keep non-static with `extern` forward decls | Methods reference each other |

### Trade-offs

**Static function objects:**
- Pro: Eliminates symbol collision risk with MicroPython libs
- Pro: Enables compiler optimizations (inlining, dead code elimination)
- Pro: Slightly smaller binary
- Con: More complex emission order for lambdas

**Non-static method objects:**
- Pro: Methods can reference each other freely
- Con: Potential collision with identically-named methods in other modules
- Mitigation: Method names include class prefix (`App_dispatch_obj`)

### Key Insight

The fundamental tension is between **flexibility** (reference anything from anywhere) and **safety** (prevent linker collisions). Our solution:

1. **Module functions/lambdas**: Prioritize safety with `static`, enforce ordering
2. **Class methods**: Prioritize flexibility with forward declarations

This matches how the code is actually used: module functions rarely reference each other by object, while methods frequently do.

### What's Next

Future improvements could include:
- Static method objects with topological sort of method dependencies
- Namespace prefixes for method objects to prevent cross-module collisions

For now, the current solution handles the common cases and follows MicroPython's convention of using `static` for module-local symbols.
