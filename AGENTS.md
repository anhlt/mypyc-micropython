# AGENTS.md — mypyc-micropython

Typed Python → MicroPython C module compiler.

## Build / Test / Lint Commands

```bash
pip install -e ".[dev]"                          # Install deps (one-time)
pytest                                           # All tests (195 tests, <1s)
pytest -xvs -k "test_simple_function"            # Single test by name
pytest -xvs tests/test_compiler.py::TestDictOperations  # Single test class
pytest -xvs tests/test_compiler.py               # Single test file
pytest -xvs -m c_runtime                         # C runtime tests only (compile+exec C via gcc)
pytest -xvs -m "not c_runtime"                   # Skip C runtime tests
ruff check src/ tests/                           # Lint
ruff check src/ tests/ --fix                     # Lint with auto-fix
make compile SRC=examples/factorial.py           # Compile one Python file → C module
make compile-all                                 # Compile all examples
make build BOARD=ESP32_GENERIC_C3                # Build firmware for ESP32-C3
make flash BOARD=ESP32_GENERIC_C3                # Flash to device
```

## Project Layout

```
src/mypyc_micropython/
├── __init__.py          # Public API: compile_source, compile_to_micropython
├── cli.py               # CLI entry point (mpy-compile command)
├── compiler.py          # AST translator and code generation (~1200 LOC)
├── ir.py                # IR definitions: ClassIR, MethodIR, FuncIR, etc.
├── class_emitter.py     # C code generation for classes (structs, vtables, methods)
└── container_emitter.py # IR emission for list/dict operations

tests/
├── conftest.py          # compile_and_run fixture (gcc compile + execute)
├── test_compiler.py     # Unit tests — AST→C translation (180 tests)
├── test_c_runtime.py    # Integration — compile generated C & run binary (15 tests, marker: c_runtime)
└── mock_mp/             # Minimal C stubs for MicroPython API

examples/                # Sample Python input files
modules/                 # Generated C output (gitignored except committed examples)
docs/                    # Documentation and ESP-IDF setup guides
blogs/                   # Technical blog posts
Makefile                 # Build commands for firmware compilation and flashing
```

## Architecture

Pipeline: `Python source → ast.parse() → TypedPythonTranslator → C code string`

Key types in `compiler.py`:
- **`TypedPythonTranslator`** — AST walker. `translate_source()` → `_translate_function()` → `_translate_statement()` → `_translate_expr()`
- **`CompilationResult`** — Dataclass: `c_code`, `mk_code`, `cmake_code`, `success`, `errors`

Key types in `ir.py`:
- **`ClassIR`** — Class intermediate representation (fields, methods, inheritance)
- **`MethodIR`** — Method IR with vtable support
- **`FuncIR`** — Function IR for module-level functions
- **`CType`** — Enum for C type mapping (MP_OBJ_T, MP_INT_T, MP_FLOAT_T, BOOL)

Key modules:
- **`class_emitter.py`** — `ClassEmitter`: generates C structs, vtables, constructors for classes
- **`container_emitter.py`** — `ContainerEmitter`: generates IR for list/dict operations

Key functions:
- **`compile_source(source: str, module_name: str) -> str`** — Core: source → C string
- **`compile_to_micropython(path, output_dir) -> CompilationResult`** — File-level wrapper
- **`sanitize_name(name: str) -> str`** — Python name → valid C identifier

## Code Style

### Tooling (pyproject.toml)
- **Linter**: ruff — rules `E`, `F`, `I`, `W`
- **Line length**: 100
- **Python target**: 3.10+
- **Build**: hatchling
- **Tests**: pytest (`testpaths = ["tests"]`)

### Imports
```python
from __future__ import annotations       # Always first in src/ files

import ast                               # stdlib alphabetical
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:                        # Type-only imports guarded
    from mypyc.ir.module_ir import ModuleIR
```
Order: `__future__` → stdlib → third-party → local. Blank line between groups.

### Type Annotations
- Use `str | None` (PEP 604), not `Optional[str]`
- Use lowercase generics: `list[str]`, `dict[str, str]`, `tuple[str, int]`
- Annotate all function signatures (params + return)
- Local variables: annotate only when needed for clarity

### Naming
| Kind | Convention | Examples |
|------|-----------|----------|
| Functions/methods | `snake_case` | `compile_source`, `_translate_expr` |
| Private methods | `_` prefix | `_fresh_temp`, `_unbox_if_needed` |
| Classes | `PascalCase` | `TypedPythonTranslator`, `CompilationResult` |
| Constants | `UPPER_SNAKE` | `C_RESERVED_WORDS` |
| Test classes | `TestFeatureName` | `TestSanitizeName`, `TestDictOperations` |
| Test methods | `test_descriptive_behavior` | `test_simple_function`, `test_pop_no_args` |

### Error Handling
- Compiler errors → `CompilationResult(success=False, errors=[...])`, never raise
- Unsupported AST nodes → emit C comment: `/* unsupported: <description> */`
- Broad `except Exception` only at top-level `compile_to_micropython`; inner code propagates

### Code Patterns
- `@dataclass` for data containers, not dicts or named tuples
- `Path` for file paths, never raw strings
- f-strings for string building (including C code generation)
- Generated C built as `list[str]` joined with `"\n"`, not concatenation

## Test Conventions

### Unit tests (test_compiler.py)
Grouped in pytest classes. Pattern:
```python
class TestDictOperations:
    def test_dict_literal(self):
        source = '''
def make_dict() -> dict:
    d: dict = {"key": 1}
    return d
'''
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        assert "mp_obj_new_dict" in result
```
1. Define Python source as triple-quoted string
2. Create `TypedPythonTranslator("test")`
3. Call `translator.translate_source(source)`
4. Assert on substrings in generated C

### C runtime tests (test_c_runtime.py)
Marked `@pytest.mark.c_runtime`. Requires gcc. Uses `compile_and_run` fixture:
```python
pytestmark = pytest.mark.c_runtime

def test_c_sum_range(compile_and_run):
    source = "..."
    test_main_c = "..."   # C main() calling generated function
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"
```

## ESP-IDF / Firmware

For building firmware and flashing to ESP32, see platform-specific guides:
- **Linux**: [docs/esp-idf-setup-linux.md](docs/esp-idf-setup-linux.md)
- **macOS**: [docs/esp-idf-setup-macos.md](docs/esp-idf-setup-macos.md)

Key commands: `make build BOARD=ESP32_GENERIC_C3`, `make flash`, `make deploy`.
Always run `source ~/esp/esp-idf/export.sh` before firmware builds.

| Variable | Default | Description |
|----------|---------|-------------|
| `BOARD` | `ESP32_GENERIC` | Target board (`ESP32_GENERIC_C3`, `ESP32_GENERIC_S3`) |
| `PORT` | `/dev/ttyACM0` | Serial port (macOS: `/dev/cu.usbmodem101`) |
| `ESP_IDF_DIR` | `~/esp/esp-idf` | ESP-IDF installation path |

## Version Matrix

| Component | Version |
|-----------|---------|
| Python | ≥3.10 |
| MicroPython submodule | v1.28.0-preview |
| ESP-IDF (for firmware) | v5.4.2 |
| mypy | ≥1.0.0 |
