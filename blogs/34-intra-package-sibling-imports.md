# 34. Intra-Package Sibling Module Imports

This post documents the intra-package sibling module import feature in mypyc-micropython.

Goal: Enable Python packages to import sibling modules (e.g., `import screens` within the `lvui` package) and generate **direct C function calls** instead of runtime imports, achieving zero-overhead cross-module communication within a compiled package.

We'll walk from compiler theory through the C runtime, then into the IR and emitter changes that make this work.


## Part 1: Compiler Theory

### The package compilation problem

When compiling a Python package like:

```
lvui/
  __init__.py
  mvu.py
  nav.py
  screens.py
```

Each module can import its siblings:

```python
# In mvu.py
import screens as ls
import nav

def create_app():
    screen = ls.create_screen()  # Call sibling module function
    navigator = nav.Nav(10, builders, None)  # Instantiate sibling class
```

The question is: how should we compile `ls.create_screen()` and `nav.Nav(...)`?

### Two approaches to cross-module calls

**Approach 1: Runtime imports (slow)**

Generate the same runtime import code as for external modules:

```c
// Slow: runtime lookup every call
mp_obj_t _mod = mp_import_name(MP_QSTR_screens, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
mp_obj_t _func = mp_load_attr(_mod, MP_QSTR_create_screen);
mp_obj_t result = mp_call_function_0(_func);
```

This works but has overhead: module lookup, attribute lookup, indirect call.

**Approach 2: Direct C calls (fast)**

Since all modules in the package are compiled into the **same C file**, we can call sibling functions directly:

```c
// Fast: direct C call
mp_obj_t result = lvui_screens_create_screen();
```

No module lookup, no attribute lookup, just a direct function call.

### Why this is possible for packages

When we compile a package directory, all `.py` files become functions in a single `.c` file:

```
lvui/           -->  usermod_lvui/lvui.c
  __init__.py        Contains: lvui_* functions
  mvu.py             Contains: lvui_mvu_* functions
  nav.py             Contains: lvui_nav_* functions
  screens.py         Contains: lvui_screens_* functions
```

Since everything is in one compilation unit, we can:
1. Generate forward declarations for all functions
2. Call sibling module functions directly by their C names

### The sibling modules map

The key insight is building a map at compile time:

```python
# Built by compiler.py during package compilation
sibling_modules = {
    'mvu': 'lvui_mvu',       # import name -> C prefix
    'nav': 'lvui_nav',
    'screens': 'lvui_screens',
}
```

When the IRBuilder sees `import screens as ls`, it checks if `screens` is in `sibling_modules`. If yes, it generates `SiblingModuleRefIR` instead of `ModuleRefIR`.

### Where this fits in the pipeline

```
Python source
  |
  v
AST (ast.Import, ast.Attribute, ast.Call)
  |
  v
IRBuilder (with sibling_modules map)
  - Detects sibling module imports
  - Creates SiblingModuleRefIR, SiblingModuleCallIR, SiblingClassInstantiationIR
  |
  v
IR
  - SiblingModuleRefIR: reference to sibling module
  - SiblingModuleCallIR: call function on sibling
  - SiblingClassInstantiationIR: instantiate class from sibling
  |
  v
FunctionEmitter
  - _emit_sibling_module_call() -> direct C call
  - _emit_sibling_class_instantiation() -> direct make_new call
  |
  v
C code
  - lvui_screens_create_screen()
  - lvui_nav_Nav_make_new(&lvui_nav_Nav_type, n, 0, args)
```


## Part 2: C Background

This section explains the C patterns for direct calls vs runtime imports.

### Runtime import pattern (baseline)

When importing an external module, we generate:

```c
// 1. Import the module by name
mp_obj_t mod = mp_import_name(
    MP_QSTR_math,           // module name as qstr
    mp_const_none,          // fromlist (none for simple import)
    MP_OBJ_NEW_SMALL_INT(0) // level (0 = absolute import)
);

// 2. Load attribute from module
mp_obj_t sqrt_func = mp_load_attr(mod, MP_QSTR_sqrt);

// 3. Call the function
mp_obj_t result = mp_call_function_1(sqrt_func, arg);
```

Three operations: import, attr lookup, call.

### Direct call pattern (sibling modules)

For sibling modules in the same package:

```c
// Direct call - no import, no lookup
mp_obj_t result = lvui_screens_create_screen();
```

One operation: direct function call.

### Forward declarations

Since C requires functions to be declared before use, we generate forward declarations at the top of the compiled package:

```c
// Forward declarations for all module-level functions
static mp_obj_t lvui_screens_create_screen(void);
static mp_obj_t lvui_nav_Nav_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
// ... more declarations
```

This allows any function in the file to call any other function, regardless of definition order.

### Class instantiation pattern

For instantiating a class from a sibling module:

**Runtime pattern (slow):**
```c
mp_obj_t mod = mp_import_name(MP_QSTR_nav, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
mp_obj_t Nav_class = mp_load_attr(mod, MP_QSTR_Nav);
mp_obj_t instance = mp_call_function_n_kw(Nav_class, 3, 0, args);
```

**Direct pattern (fast):**
```c
mp_obj_t instance = lvui_nav_Nav_make_new(
    &lvui_nav_Nav_type,  // type object pointer
    3,                    // n_args
    0,                    // n_kw
    (const mp_obj_t[]){arg1, arg2, arg3}  // args array
);
```

The direct pattern calls `make_new` directly, bypassing the type object's `call` slot.


## Part 3: Implementation

### New IR types

We added three new IR types to represent sibling module operations:

```python
@dataclass
class SiblingModuleRefIR(ExprIR):
    """Reference to a sibling module within the same package."""
    c_prefix: str  # C name prefix (e.g., 'lvui_screens')


@dataclass
class SiblingModuleCallIR(ExprIR):
    """Call a function on a sibling module.
    
    Generated C: {c_prefix}_{func_name}(args...)
    """
    c_prefix: str      # C name prefix (e.g., 'lvui_screens')
    func_name: str     # Function name (e.g., 'create_screen')
    args: list[ValueIR]
    arg_preludes: list[list[InstrIR]]


@dataclass
class SiblingClassInstantiationIR(ExprIR):
    """Instantiate a class from a sibling module.
    
    Generated C: {c_prefix}_{class_name}_make_new(&type, n_args, 0, args_array)
    """
    c_prefix: str    # C name prefix (e.g., 'lvui_nav')
    class_name: str  # Class name (e.g., 'Nav')
    args: list[ValueIR]
    arg_preludes: list[list[InstrIR]]
```

### IRBuilder changes

The IRBuilder receives a `sibling_modules` map and checks it when processing imports and calls:

```python
class IRBuilder:
    def __init__(
        self,
        module_name: str,
        sibling_modules: dict[str, str] | None = None,  # import name -> C prefix
    ):
        self._sibling_modules = sibling_modules or {}
```

**Name lookup** (`_build_name`):

```python
def _build_name(self, node: ast.Name, locals_: list[str]) -> ValueIR:
    name = node.id
    
    # Check import aliases
    if name in self._import_aliases:
        module_name = self._import_aliases[name]
        
        # Is this a sibling module?
        if module_name in self._sibling_modules:
            c_prefix = self._sibling_modules[module_name]
            return SiblingModuleRefIR(ir_type=IRType.OBJ, c_prefix=c_prefix)
        
        # Fall back to runtime import
        return ModuleRefIR(ir_type=IRType.OBJ, module_name=module_name)
```

**Module call** (`_build_module_call`):

```python
def _build_module_call(self, expr: ast.Call, alias: str, locals_: list[str]):
    module_name = self._import_aliases[alias]
    func_name = expr.func.attr
    
    # Build args...
    
    # Check if sibling module
    if module_name in self._sibling_modules:
        c_prefix = self._sibling_modules[module_name]
        
        # Class instantiation? (uppercase first letter)
        if func_name[0].isupper():
            return SiblingClassInstantiationIR(
                ir_type=IRType.OBJ,
                c_prefix=c_prefix,
                class_name=func_name,
                args=args,
                arg_preludes=arg_preludes,
            ), all_preludes
        
        # Function call
        return SiblingModuleCallIR(
            ir_type=IRType.OBJ,
            c_prefix=c_prefix,
            func_name=func_name,
            args=args,
            arg_preludes=arg_preludes,
        ), all_preludes
    
    # Fall back to runtime module call
    return ModuleCallIR(...), all_preludes
```

### FunctionEmitter changes

The emitter generates direct C calls for sibling modules:

```python
def _emit_sibling_module_call(self, call: SiblingModuleCallIR, native: bool = False):
    """Emit direct C call for sibling module function."""
    boxed_args = []
    for arg in call.args:
        arg_expr, arg_type = self._emit_expr(arg)
        boxed_args.append(self._box_value(arg_expr, arg_type))
    
    args_str = ", ".join(boxed_args)
    c_func_name = f"{call.c_prefix}_{call.func_name}"
    
    return f"{c_func_name}({args_str})", "mp_obj_t"


def _emit_sibling_class_instantiation(self, inst: SiblingClassInstantiationIR, native: bool = False):
    """Emit direct make_new call for sibling class."""
    boxed_args = []
    for arg in inst.args:
        arg_expr, arg_type = self._emit_expr(arg)
        boxed_args.append(self._box_value(arg_expr, arg_type))
    
    c_class_name = f"{inst.c_prefix}_{inst.class_name}"
    n_args = len(boxed_args)
    
    if n_args == 0:
        return f"{c_class_name}_make_new(&{c_class_name}_type, 0, 0, NULL)", "mp_obj_t"
    else:
        args_array = ", ".join(boxed_args)
        return (
            f"{c_class_name}_make_new(&{c_class_name}_type, {n_args}, 0, "
            f"(const mp_obj_t[]){{{args_array}}})",
            "mp_obj_t"
        )
```

### Compiler orchestration

The `compile_package` function builds the sibling modules map:

```python
def compile_package(package_path: Path, ...):
    module_name = package_path.name  # e.g., 'lvui'
    
    # Build sibling modules map
    sibling_modules: dict[str, str] = {}
    for py_file in package_path.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        submod_name = py_file.stem  # e.g., 'screens'
        c_prefix = sanitize_name(f"{module_name}_{submod_name}")  # e.g., 'lvui_screens'
        sibling_modules[submod_name] = c_prefix
    
    # Pass to recursive scanner
    submodules = _scan_package_recursive(
        package_path,
        module_name,
        sibling_modules=sibling_modules,  # Passed down
        ...
    )
```

Each submodule's IRBuilder receives this map:

```python
def _compile_module_parts(source: str, module_name: str, sibling_modules: dict[str, str] | None = None):
    ir_builder = IRBuilder(
        module_name,
        sibling_modules=sibling_modules,  # Enable sibling detection
    )
```


## Part 4: Complete Example

### Python source

**extmod/lvui/screens.py:**
```python
def create_screen() -> object:
    """Create a new LVGL screen."""
    return lv.obj()
```

**extmod/lvui/nav.py:**
```python
class Nav:
    def __init__(self, capacity: int, builders: object, default_screen: object) -> None:
        self.capacity = capacity
        self.builders = builders
        self.current = default_screen
```

**extmod/lvui/mvu.py:**
```python
import screens as ls
import nav

def create_app(builders: object) -> object:
    screen = ls.create_screen()
    navigator = nav.Nav(10, builders, None)
    return navigator
```

### IR dump

```bash
mpy-compile extmod/lvui --dump-ir text --ir-function create_app
```

```
def create_app(builders: MP_OBJ_T) -> MP_OBJ_T:
  c_name: lvui_mvu_create_app
  max_temp: 2
  locals: {builders: MP_OBJ_T, screen: MP_OBJ_T, navigator: MP_OBJ_T}
  body:
    screen: mp_obj_t = lvui_screens.create_screen()
    navigator: mp_obj_t = lvui_nav.Nav(10, builders, None)
    return navigator
```

Note: The IR shows `lvui_screens.create_screen()` and `lvui_nav.Nav(...)` - these are SiblingModuleCallIR and SiblingClassInstantiationIR respectively.

### Generated C code

**Before (runtime imports):**
```c
static mp_obj_t lvui_mvu_create_app(mp_obj_t builders) {
    // Runtime import screens module
    mp_obj_t _mod_screens = mp_import_name(MP_QSTR_screens, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t _func = mp_load_attr(_mod_screens, MP_QSTR_create_screen);
    mp_obj_t screen = mp_call_function_0(_func);
    
    // Runtime import nav module and instantiate class
    mp_obj_t _mod_nav = mp_import_name(MP_QSTR_nav, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t _Nav_class = mp_load_attr(_mod_nav, MP_QSTR_Nav);
    mp_obj_t navigator = mp_call_function_n_kw(_Nav_class, 3, 0, 
        (const mp_obj_t[]){mp_obj_new_int(10), builders, mp_const_none});
    
    return navigator;
}
```

**After (direct C calls):**
```c
// Forward declarations
static mp_obj_t lvui_screens_create_screen(void);
static mp_obj_t lvui_nav_Nav_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

static mp_obj_t lvui_mvu_create_app(mp_obj_t builders) {
    // Direct call to sibling module function
    mp_obj_t screen = lvui_screens_create_screen();
    
    // Direct class instantiation
    mp_obj_t navigator = lvui_nav_Nav_make_new(
        &lvui_nav_Nav_type, 3, 0,
        (const mp_obj_t[]){mp_obj_new_int(10), builders, mp_const_none}
    );
    
    return navigator;
}
```


## Part 5: Design Decisions

### Why not always use direct calls?

Direct calls only work for **sibling modules in the same package**. For external modules (like `math`, `json`, `asyncio`), we must use runtime imports because:

1. External modules are compiled separately
2. Their C symbols may be `static` (not linkable)
3. Their API may differ across MicroPython ports

### Class detection heuristic

We detect class instantiation by checking if the function name starts with an uppercase letter:

```python
if func_name[0].isupper():
    return SiblingClassInstantiationIR(...)
```

This follows Python naming conventions (PEP 8) where classes use `CamelCase`.

### Forward declaration generation

We generate forward declarations for ALL module-level functions in a package, not just those that are called. This:

1. Simplifies the implementation (no dependency analysis needed)
2. Allows any function to call any other function
3. Has zero runtime cost (forward declarations are compile-time only)

### Why not use header files?

Traditional C projects use `.h` files for cross-file visibility. We chose inline forward declarations because:

1. Packages compile to a single `.c` file anyway
2. No need to manage separate header files
3. Simpler build process for MicroPython usermod system


## Summary

Intra-package sibling imports enable efficient cross-module communication within compiled Python packages:

| Aspect | Runtime Import | Sibling Import |
|--------|---------------|----------------|
| Module lookup | `mp_import_name()` | None |
| Attribute lookup | `mp_load_attr()` | None |
| Function call | `mp_call_function_N()` | Direct C call |
| Class instantiation | `mp_call_function_n_kw()` | Direct `make_new()` |

The implementation required:
- 3 new IR types: `SiblingModuleRefIR`, `SiblingModuleCallIR`, `SiblingClassInstantiationIR`
- IRBuilder changes to detect sibling modules via the `sibling_modules` map
- FunctionEmitter changes to generate direct C calls
- Compiler changes to build the sibling modules map during package compilation
- Forward declaration generation for cross-function visibility

This makes Python packages work naturally in MicroPython with zero-overhead cross-module calls.
