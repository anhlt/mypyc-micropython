# Architecture Overview

## Introduction

mypyc-micropython is a compiler that transforms typed Python code into MicroPython-compatible C extension modules. This document describes the overall architecture and design decisions.

## Compilation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    MYPYC-MICROPYTHON PIPELINE                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐                                                        │
│  │   Python    │  Input: Typed Python source file (.py)                 │
│  │   Source    │  Example: def add(a: int, b: int) -> int: return a + b │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────┐                                                        │
│  │  ast.parse  │  Python's built-in AST parser                          │
│  │             │  Produces: ast.Module with typed function definitions  │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────┐                                                │
│  │ TypedPythonTransla- │  Core translator class                         │
│  │ tor                 │  - Extracts type annotations                   │
│  │                     │  - Translates statements to C                  │
│  │                     │  - Generates MicroPython API calls             │
│  └──────┬──────────────┘                                                │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────────────────────────────────────────┐            │
│  │                   Output Files                          │            │
│  │  ┌─────────────┐  ┌───────────────┐  ┌────────────────┐ │            │
│  │  │ <module>.c  │  │ micropython.mk│  │micropython.cmake│ │            │
│  │  │             │  │               │  │                │ │            │
│  │  │ C code with │  │ Make build    │  │ CMake build    │ │            │
│  │  │ MP C-API    │  │ integration   │  │ integration    │ │            │
│  │  └─────────────┘  └───────────────┘  └────────────────┘ │            │
│  └─────────────────────────────────────────────────────────┘            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Compiler (`src/mypyc_micropython/compiler.py`)

The main compilation logic:

```python
class TypedPythonTranslator:
    """Translates typed Python AST to MicroPython C code."""
    
    def translate_source(self, source: str) -> str:
        """Main entry point - parse and translate Python source."""
        
    def _translate_function(self, node: ast.FunctionDef) -> None:
        """Translate a single function definition."""
        
    def _translate_expr(self, expr, locals_: list[str]) -> tuple[str, str]:
        """Translate an expression, returning (C code, C type)."""
```

### 2. CLI (`src/mypyc_micropython/cli.py`)

Command-line interface:

```bash
mpy-compile source.py              # Compile to usermod_source/
mpy-compile source.py -o outdir/   # Custom output directory
mpy-compile source.py -v           # Verbose output
```

### 3. Generated Output Structure

```
usermod_<module>/
├── <module>.c          # Generated C code
├── micropython.mk      # Make build system integration
└── micropython.cmake   # CMake build system integration
```

## Design Decisions

### Current Approach: Direct AST-to-C Translation

The current implementation directly translates Python AST to C code without an intermediate representation (IR).

**Advantages:**
- Simple to understand and implement
- Fast compilation
- No external dependencies at compile time
- Direct mapping from Python constructs to C

**Limitations:**
- Limited optimization opportunities
- Type inference relies solely on annotations
- Harder to implement advanced features (closures, generators)

### Future Direction: mypyc IR Integration

For advanced features, we plan to integrate with mypyc's IR:

```
Python Source → [mypy type check] → [mypyc IR] → [MP Code Generator] → C
```

This would provide:
- Sophisticated type inference from mypy
- IR-level optimizations
- Proven transforms for complex features

## Type Mapping

| Python Type | C Type | MicroPython Conversion |
|-------------|--------|------------------------|
| `int` | `mp_int_t` | `mp_obj_get_int()` / `mp_obj_new_int()` |
| `float` | `mp_float_t` | `mp_obj_get_float()` / `mp_obj_new_float()` |
| `bool` | `bool` | `mp_obj_is_true()` / `mp_const_true/false` |
| `str` | `const char*` | `mp_obj_str_get_str()` / `mp_obj_new_str()` |
| `None` | - | `mp_const_none` |
| `object` | `mp_obj_t` | No conversion (boxed) |

## Function Signature Translation

MicroPython uses different function object macros based on argument count:

| Args | Macro | C Signature |
|------|-------|-------------|
| 0 | `MP_DEFINE_CONST_FUN_OBJ_0` | `mp_obj_t func(void)` |
| 1 | `MP_DEFINE_CONST_FUN_OBJ_1` | `mp_obj_t func(mp_obj_t arg0)` |
| 2 | `MP_DEFINE_CONST_FUN_OBJ_2` | `mp_obj_t func(mp_obj_t arg0, mp_obj_t arg1)` |
| 3 | `MP_DEFINE_CONST_FUN_OBJ_3` | `mp_obj_t func(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2)` |
| 4+ | `MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN` | `mp_obj_t func(size_t n_args, const mp_obj_t *args)` |

## Module Registration

Generated modules are registered with MicroPython using:

```c
// Module globals table
static const mp_rom_map_elem_t module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_module_name) },
    { MP_ROM_QSTR(MP_QSTR_func1), MP_ROM_PTR(&func1_obj) },
    { MP_ROM_QSTR(MP_QSTR_func2), MP_ROM_PTR(&func2_obj) },
};
MP_DEFINE_CONST_DICT(module_globals, module_globals_table);

// Module object
const mp_obj_module_t module_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&module_globals,
};

// Register module
MP_REGISTER_MODULE(MP_QSTR_module_name, module_user_cmodule);
```

## Comparison with mypyc

| Aspect | mypyc | mypyc-micropython |
|--------|-------|-------------------|
| **Target** | CPython C extensions | MicroPython user modules |
| **Runtime** | CPython + mypyc runtime | MicroPython only |
| **IR** | Full IR with transforms | Direct AST translation |
| **Type System** | Full mypy integration | Annotation-based |
| **Memory** | Reference counting | MicroPython GC |
| **Object Model** | PyObject* | mp_obj_t |

## See Also

- [02-mypyc-reference.md](02-mypyc-reference.md) - How mypyc works
- [03-micropython-c-api.md](03-micropython-c-api.md) - MicroPython C API reference
- [04-feature-scope.md](04-feature-scope.md) - Supported features
