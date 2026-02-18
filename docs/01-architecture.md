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
│  │    IR Builder       │  AST to IR translation (ir_builder.py)         │
│  │                     │  - Extracts type annotations                   │
│  │                     │  - Builds FuncIR, ClassIR, StmtIR, ExprIR      │
│  │                     │  - Tracks variable types and RTuple structs    │
│  └──────┬──────────────┘                                                │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────────┐                                                │
│  │    Emitters         │  IR to C code generation                       │
│  │                     │  - FunctionEmitter (function_emitter.py)       │
│  │                     │  - ClassEmitter (class_emitter.py)             │
│  │                     │  - ModuleEmitter (module_emitter.py)           │
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

### 1. Entry Point (`src/mypyc_micropython/compiler.py`)

The main `compile_source` function orchestrates the pipeline:

```python
def compile_source(source: str, module_name: str) -> str:
    """Compile typed Python source to MicroPython C code."""
    tree = ast.parse(source)
    ir_builder = IRBuilder(module_name)
    module_ir = ir_builder.build(tree)
    emitter = ModuleEmitter(module_ir)
    return emitter.emit()
```

### 2. IR Definitions (`src/mypyc_micropython/ir.py`)

The intermediate representation layer:

```python
# Value IR - expression results
@dataclass
class ValueIR:
    ir_type: IRType  # OBJ, INT, FLOAT, BOOL

@dataclass
class BinOpIR(ValueIR):
    left: ValueIR
    op: str
    right: ValueIR

# Statement IR - control flow
@dataclass
class IfIR(StmtIR):
    test: ValueIR
    body: list[StmtIR]
    orelse: list[StmtIR]

# Function/Class IR
@dataclass
class FuncIR:
    name: str
    params: list[tuple[str, CType]]
    return_type: CType
    body: list[StmtIR]
```

### 3. IR Builder (`src/mypyc_micropython/ir_builder.py`)

Transforms AST to IR:

```python
class IRBuilder:
    def build(self, tree: ast.Module) -> ModuleIR:
        """Build IR from AST module."""
        
    def _build_func(self, node: ast.FunctionDef) -> FuncIR:
        """Build function IR from AST function definition."""
        
    def _build_expr(self, expr: ast.expr) -> tuple[ValueIR, list[InstrIR]]:
        """Build expression IR, returning value and prelude instructions."""
```

### 4. Emitters (`src/mypyc_micropython/`)

Generate C code from IR:

| File | Responsibility |
|------|----------------|
| `function_emitter.py` | FuncIR/MethodIR to C function code |
| `class_emitter.py` | ClassIR to C structs and vtables |
| `module_emitter.py` | ModuleIR to complete C module file |
| `container_emitter.py` | Container operation IR to C code |

### 5. CLI (`src/mypyc_micropython/cli.py`)

Command-line interface:

```bash
mpy-compile source.py              # Compile to usermod_source/
mpy-compile source.py -o outdir/   # Custom output directory
mpy-compile source.py -v           # Verbose output
```

### 6. Generated Output Structure

```
usermod_<module>/
├── <module>.c          # Generated C code
├── micropython.mk      # Make build system integration
└── micropython.cmake   # CMake build system integration
```

## Design Decisions

### Two-Phase IR Architecture

The compiler uses a clean two-phase pipeline:

```
Python AST  -->  IR Builder  -->  IR  -->  Emitters  -->  C Code
```

**Phase 1: AST to IR (ir_builder.py)**
- Extracts type annotations
- Builds typed IR nodes
- Tracks variable types and RTuple optimizations
- Separates "what value" from "what must happen first" (prelude pattern)

**Phase 2: IR to C (emitters)**
- Generates optimized C code from IR
- Handles boxing/unboxing based on IR types
- Emits MicroPython API calls

**Advantages:**
- Clean separation of concerns
- Type information flows through IR
- Enables optimizations (RTuple structs, native int operations)
- Easier to test and maintain

### The Prelude Pattern

Expressions return `tuple[ValueIR, list[InstrIR]]` - the value and any instructions that must execute first:

```python
# result.append(i * i) produces:
# - ValueIR: TempIR("_tmp1")
# - Prelude: [MethodCallIR(result="_tmp1", receiver=result, method="append", args=[BinOpIR(...)])]
```

This cleanly separates side effects from values.

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
| **IR** | Full IR with transforms | Custom IR (FuncIR, StmtIR, ExprIR) |
| **Type System** | Full mypy integration | Annotation-based |
| **Memory** | Reference counting | MicroPython GC |
| **Object Model** | PyObject* | mp_obj_t |

## See Also

- [02-mypyc-reference.md](02-mypyc-reference.md) - How mypyc works
- [03-micropython-c-api.md](03-micropython-c-api.md) - MicroPython C API reference
- [04-feature-scope.md](04-feature-scope.md) - Supported features
- [08-ir-design.md](08-ir-design.md) - Detailed IR design documentation
- [Blog: IR Pipeline Refactoring](/blogs/06-ir-pipeline-refactoring.md) - Technical deep-dive into the IR architecture
