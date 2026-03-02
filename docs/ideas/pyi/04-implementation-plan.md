# Implementation Plan (Phases 1-6)

> **Status**: All phases complete  
> **Completed**: Feb 2026  
> **Result**: LVGL bindings with 55 functions, running on ESP32 hardware  
> **Next phases**: See [05-roadmap.md](05-roadmap.md) for Phases 7-9

## Architecture Overview

```
addons/c_bindings/                    # Separate from core compiler
├── __init__.py                       # Public API
├── c_types.py                        # Type markers (c_ptr, @c_struct)
├── c_ir.py                           # IR definitions
├── stub_parser.py                    # .pyi → CLibraryDef
├── c_emitter.py                      # CLibraryDef → C code
├── cmake_emitter.py                  # Generate micropython.cmake
├── compiler.py                       # High-level orchestration
├── cli.py                            # mpy-compile-c command
└── stubs/                            # Pre-built stubs
    └── lvgl/
        └── lvgl.pyi
```

## Phase 1: Foundation (Days 1-2) -- COMPLETED

### 1.1 C Type System (`c_types.py`)

```python
"""C type markers for stub files."""

from typing import TypeVar, Generic

T = TypeVar("T")

class c_ptr(Generic[T]):
    """C pointer type: c_ptr[LvObj] -> lv_obj_t*"""
    pass

# Primitive types
class c_void: pass
class c_int: pass
class c_uint: pass
class c_int8: pass
class c_uint8: pass
class c_int16: pass
class c_uint16: pass
class c_int32: pass
class c_uint32: pass
class c_float: pass
class c_double: pass
class c_bool: pass
class c_str: pass

def c_struct(c_name: str, opaque: bool = True):
    """Decorator to mark a class as a C struct."""
    def decorator(cls):
        cls.__c_struct_name__ = c_name
        cls.__c_opaque__ = opaque
        return cls
    return decorator

def c_enum(c_name: str):
    """Decorator to mark a class as a C enum."""
    def decorator(cls):
        cls.__c_enum_name__ = c_name
        return cls
    return decorator
```

### 1.2 IR Definitions (`c_ir.py`)

```python
"""C-specific IR definitions."""

from dataclasses import dataclass, field
from enum import Enum, auto

class CType(Enum):
    VOID = auto()
    INT = auto()
    UINT = auto()
    # ... all primitive types
    STRUCT_PTR = auto()
    CALLBACK = auto()

@dataclass
class CStructDef:
    py_name: str
    c_name: str
    is_opaque: bool = True
    fields: dict[str, CType] = field(default_factory=dict)

@dataclass
class CEnumDef:
    py_name: str
    c_name: str
    values: dict[str, int] = field(default_factory=dict)

@dataclass
class CParamDef:
    name: str
    c_type: CType
    struct_name: str | None = None
    is_optional: bool = False

@dataclass
class CFuncDef:
    py_name: str
    c_name: str
    params: list[CParamDef] = field(default_factory=list)
    return_type: CType = CType.VOID
    return_struct: str | None = None
    docstring: str | None = None

@dataclass
class CCallbackDef:
    py_name: str
    params: list[CParamDef] = field(default_factory=list)
    return_type: CType = CType.VOID

@dataclass
class CLibraryDef:
    name: str
    header: str
    include_dirs: list[str] = field(default_factory=list)
    structs: dict[str, CStructDef] = field(default_factory=dict)
    enums: dict[str, CEnumDef] = field(default_factory=dict)
    functions: dict[str, CFuncDef] = field(default_factory=dict)
    callbacks: dict[str, CCallbackDef] = field(default_factory=dict)
```

### Deliverables
 [x] `c_types.py` with all type markers
 [x] `c_ir.py` with all IR definitions
 [x] Unit tests for IR structures

---

## Phase 2: Stub Parser (Days 3-4) -- COMPLETED

### 2.1 Parser Implementation (`stub_parser.py`)

```python
"""Parse .pyi stub files into CLibraryDef."""

import ast
from pathlib import Path
from .c_ir import *

class StubParser:
    PRIMITIVE_MAP = {
        "c_void": CType.VOID,
        "c_int": CType.INT,
        "int": CType.INT,
        "str": CType.STR,
        # ... complete mapping
    }
    
    def parse_file(self, path: Path) -> CLibraryDef:
        source = path.read_text()
        return self.parse_source(source, path.stem)
    
    def parse_source(self, source: str, name: str) -> CLibraryDef:
        tree = ast.parse(source)
        library = CLibraryDef(name=name, header="")
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                self._parse_module_var(node, library)
            elif isinstance(node, ast.ClassDef):
                self._parse_class(node, library)
            elif isinstance(node, ast.FunctionDef):
                self._parse_function(node, library)
        
        return library
    
    def _parse_module_var(self, node: ast.Assign, lib: CLibraryDef):
        # Handle __c_header__, __c_include_dirs__, etc.
        ...
    
    def _parse_class(self, node: ast.ClassDef, lib: CLibraryDef):
        # Handle @c_struct, @c_enum decorators
        ...
    
    def _parse_function(self, node: ast.FunctionDef, lib: CLibraryDef):
        # Extract function signature
        ...
    
    def _parse_annotation(self, ann: ast.expr) -> tuple[CType, str | None]:
        # Convert type annotation to CType
        ...
```

### Deliverables
 [x] `stub_parser.py` with full parsing logic
 [x] Handle all type annotations (primitives, `c_ptr[T]`, `Callable`)
 [x] Handle module metadata (`__c_header__`, etc.)
 [x] Unit tests for parser

---

## Phase 3: C Code Generator (Days 5-6) -- COMPLETED

### 3.1 Emitter Implementation (`c_emitter.py`)

```python
"""Generate C code from CLibraryDef."""

from .c_ir import *

class CEmitter:
    def __init__(self, library: CLibraryDef):
        self.lib = library
        self.lines: list[str] = []
    
    def emit(self) -> str:
        self._emit_header()
        self._emit_helpers()
        self._emit_wrappers()
        self._emit_module_def()
        return "\n".join(self.lines)
    
    def _emit_header(self):
        self.lines.append("/* Auto-generated from .pyi stub */")
        self.lines.append('#include "py/runtime.h"')
        self.lines.append('#include "py/obj.h"')
        self.lines.append(f'#include "{self.lib.header}"')
        self.lines.append("")
    
    def _emit_helpers(self):
        # mp_to_ptr, ptr_to_mp helpers
        ...
    
    def _emit_wrappers(self):
        for func in self.lib.functions.values():
            self._emit_function_wrapper(func)
    
    def _emit_function_wrapper(self, func: CFuncDef):
        # Generate wrapper function
        ...
    
    def _emit_module_def(self):
        # Generate module globals table and registration
        ...
```

### 3.2 Type Conversion Table

```python
class TypeConverter:
    """Generate type conversion code."""
    
    # Python → C
    TO_C = {
        CType.INT: "mp_obj_get_int({arg})",
        CType.UINT: "(uint32_t)mp_obj_get_int({arg})",
        CType.FLOAT: "(float)mp_obj_get_float({arg})",
        CType.DOUBLE: "mp_obj_get_float({arg})",
        CType.BOOL: "mp_obj_is_true({arg})",
        CType.STR: "mp_obj_str_get_str({arg})",
        CType.STRUCT_PTR: "mp_to_ptr({arg})",
    }
    
    # C → Python
    TO_PY = {
        CType.INT: "mp_obj_new_int({val})",
        CType.UINT: "mp_obj_new_int_from_uint({val})",
        CType.FLOAT: "mp_obj_new_float({val})",
        CType.DOUBLE: "mp_obj_new_float({val})",
        CType.BOOL: "mp_obj_new_bool({val})",
        CType.STR: "mp_obj_new_str({val}, strlen({val}))",
        CType.STRUCT_PTR: "ptr_to_mp((void *){val})",
        CType.VOID: "mp_const_none",
    }
```

### Deliverables
 [x] `c_emitter.py` with full code generation
 [x] `cmake_emitter.py` for build files
 [x] Correct MP_DEFINE_CONST_FUN_OBJ macros (0-3 args, VAR)
 [x] Unit tests comparing output to expected C

---

## Phase 4: CLI & Integration (Days 7-8) -- COMPLETED

### 4.1 Compiler Orchestration (`compiler.py`)

```python
"""High-level compiler API."""

from pathlib import Path
from dataclasses import dataclass
from .stub_parser import StubParser
from .c_emitter import CEmitter
from .cmake_emitter import CMakeEmitter

@dataclass
class CompilationResult:
    success: bool
    c_code: str
    cmake_code: str
    module_name: str
    errors: list[str]

class CBindingCompiler:
    def __init__(self):
        self.parser = StubParser()
    
    def compile_stub(
        self, 
        stub_path: Path,
        output_dir: Path | None = None
    ) -> CompilationResult:
        # Parse stub
        library = self.parser.parse_file(stub_path)
        
        # Generate C code
        emitter = CEmitter(library)
        c_code = emitter.emit()
        
        # Generate CMake
        cmake = CMakeEmitter(library)
        cmake_code = cmake.emit()
        
        # Write files if output_dir specified
        if output_dir:
            self._write_output(output_dir, library.name, c_code, cmake_code)
        
        return CompilationResult(
            success=True,
            c_code=c_code,
            cmake_code=cmake_code,
            module_name=library.name,
            errors=[],
        )
```

### 4.2 CLI (`cli.py`)

```python
"""Command-line interface: mpy-compile-c"""

import argparse
from pathlib import Path
from .compiler import CBindingCompiler

def main():
    parser = argparse.ArgumentParser(
        prog="mpy-compile-c",
        description="Generate MicroPython C bindings from .pyi stubs"
    )
    parser.add_argument("stub", help="Path to .pyi stub file")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("-v", "--verbose", action="store_true")
    
    args = parser.parse_args()
    
    compiler = CBindingCompiler()
    result = compiler.compile_stub(
        Path(args.stub),
        Path(args.output) if args.output else None
    )
    
    if result.success:
        if not args.output:
            print(result.c_code)
        else:
            print(f"Generated: {args.output}/{result.module_name}.c")
    else:
        for error in result.errors:
            print(f"Error: {error}")
        return 1

if __name__ == "__main__":
    main()
```

### 4.3 Package Setup

```toml
# pyproject.toml additions
[project.optional-dependencies]
c-bindings = []

[project.scripts]
mpy-compile-c = "mypyc_micropython_c_bindings.cli:main"
```

### Deliverables
 [x] `compiler.py` orchestration
 [x] `cli.py` command line tool
 [x] `pyproject.toml` updates
 [x] Integration tests (stub -> C -> compile)

---

## Phase 5: LVGL MVP Stub (Days 9-10) -- COMPLETED

### 5.1 Core LVGL Stub

Create `stubs/lvgl/lvgl.pyi` with:

| Category | Functions | Count |
|----------|-----------|-------|
| Core object | `lv_obj_create`, `lv_obj_delete`, `lv_obj_set_*` | ~15 |
| Screen | `lv_screen_active`, `lv_screen_load` | ~5 |
| Label | `lv_label_create`, `lv_label_set_text` | ~5 |
| Button | `lv_btn_create` | ~3 |
| Events | `lv_obj_add_event_cb`, `lv_event_get_*` | ~10 |
| Style basics | `lv_style_init`, `lv_style_set_*` | ~12 |
| **Total** | | **~50** |

### 5.2 Test with Real LVGL

```bash
# Generate bindings
mpy-compile-c stubs/lvgl/lvgl.pyi -o modules/lvgl

# Build with MicroPython
cd micropython/ports/esp32
make USER_C_MODULES=../../../modules/lvgl/micropython.cmake

# Test on device
>>> import lvgl as lv
>>> screen = lv.lv_screen_active()
>>> btn = lv.lv_btn_create(screen)
```

### Deliverables
 [x] `lvgl.pyi` with ~55 functions (exceeded target of ~50)
 [x] Test build with MicroPython
 [x] Example app using bindings -- see [Blog 22](../../../blogs/22-lvgl-display-driver-esp32.md)

---

## Phase 6: Callbacks & Events (Days 11-12) -- COMPLETED

### 6.1 Callback Support

```python
# In stub
EventCallback = Callable[[c_ptr[LvEvent]], None]

def lv_obj_add_event_cb(
    obj: c_ptr[LvObj],
    cb: EventCallback,
    filter: c_int
) -> None: ...
```

Generated C:
```c
// Callback storage (simplified - real impl needs proper management)
static mp_obj_t event_callback_storage[16];
static int event_callback_count = 0;

static void event_trampoline(lv_event_t *e) {
    int idx = (int)(intptr_t)lv_event_get_user_data(e);
    mp_obj_t cb = event_callback_storage[idx];
    mp_obj_t arg = ptr_to_mp((void *)e);
    mp_call_function_1(cb, arg);
}

static mp_obj_t lv_obj_add_event_cb_wrapper(mp_obj_t obj, mp_obj_t cb, mp_obj_t filter) {
    lv_obj_t *c_obj = mp_to_ptr(obj);
    int idx = event_callback_count++;
    event_callback_storage[idx] = cb;
    lv_obj_add_event_cb(c_obj, event_trampoline, mp_obj_get_int(filter), (void *)(intptr_t)idx);
    return mp_const_none;
}
```

### Deliverables
 [x] Callback trampoline generation
 [x] Event callback storage
 [x] Test event handling works -- verified on ESP32 hardware

---

## Timeline Summary
| Phase | Days | Deliverables | Status |
|-------|------|--------------|--------|
| 1. Foundation | 1-2 | `c_types.py`, `c_ir.py` | Done |
| 2. Parser | 3-4 | `stub_parser.py` | Done |
| 3. Emitter | 5-6 | `c_emitter.py`, `cmake_emitter.py` | Done |
| 4. CLI | 7-8 | `cli.py`, `compiler.py` | Done |
| 5. LVGL MVP | 9-10 | `lvgl.pyi` (55 functions), integration test | Done |
| 6. Callbacks | 11-12 | Callback support | Done |

**All 6 phases completed.** See [Blog 21](../../../blogs/21-pyi-stub-c-bindings.md) and [Blog 22](../../../blogs/22-lvgl-display-driver-esp32.md) for implementation details.

---

## Success Criteria -- ALL MET

1. **Parse** any well-formed `.pyi` stub file -- done
2. **Generate** valid MicroPython C module code -- done (55 wrapper functions)
3. **Compile** generated code with real LVGL headers -- done
4. **Run** on ESP32 with MicroPython -- done (ESP32-C6 hardware verified)
5. **IDE** autocomplete works with the same `.pyi` file -- done

## What's Next

The next evolution takes this system from LVGL-specific to **general-purpose C bindings**.
See [05-roadmap.md](05-roadmap.md) for Phases 7-9:

- **Phase 7**: Fix emitter bugs (pointer wrapping, GC-safe callbacks, generic trampolines)
- **Phase 8**: C header parser via `pycparser` (auto-generate bindings from `.h` files)
- **Phase 9**: Hybrid system with `bind.toml` config (headers + optional `.pyi` overrides)
