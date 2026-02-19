# AGENTS.md — mypyc-micropython

Typed Python → MicroPython C module compiler.

## Build / Test / Lint Commands

```bash
pip install -e ".[dev]"                          # Install deps (one-time)
pytest                                           # All tests (357 tests, <20s)
pytest -xvs -k "test_simple_function"            # Single test by name
pytest -xvs tests/test_compiler.py::TestDictOperations  # Single test class
pytest -xvs tests/test_compiler.py               # Single test file
pytest -xvs -m c_runtime                         # C runtime tests only (compile+exec C via gcc)
pytest -xvs -m "not c_runtime"                   # Skip C runtime tests
ruff check src/ tests/                           # Lint
ruff check src/ tests/ --fix                     # Lint with auto-fix
make compile SRC=examples/factorial.py           # Compile one Python file → C module
make compile-all                                 # Compile all examples
make build BOARD=ESP32_GENERIC_C6                # Build firmware for ESP32-C6
make flash BOARD=ESP32_GENERIC_C6                # Flash to device
make test-device BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101  # Full device test
make run-device-tests PORT=/dev/cu.usbmodem2101  # Run device tests only
make benchmark PORT=/dev/cu.usbmodem2101         # Benchmark native vs vanilla MicroPython
```

**IMPORTANT**: Always use `make` commands for compiling and testing. Never call `mpy-compile` directly.

## Project Layout

```
src/mypyc_micropython/
├── __init__.py          # Public API: compile_source, compile_to_micropython
├── cli.py               # CLI entry point (mpy-compile command, --dump-ir)
├── compiler.py          # Top-level compilation orchestration
├── ir.py                # IR definitions: FuncIR, ClassIR, StmtIR, ValueIR, etc.
├── ir_builder.py        # AST → IR translation (builds FuncIR, ClassIR from AST)
├── ir_visualizer.py     # IR debugging: dump IR as text/tree/JSON
├── function_emitter.py  # FuncIR → C code emission
├── module_emitter.py    # ModuleIR → complete C module assembly
├── class_emitter.py     # ClassIR → C structs, vtables, methods
└── container_emitter.py # IR emission helpers for list/dict operations

tests/
├── conftest.py          # compile_and_run fixture (gcc compile + execute)
├── test_compiler.py     # Unit tests — full compilation (347 tests)
├── test_ir_builder.py   # Unit tests — IR building (53 tests)
├── test_ir_visualizer.py # Unit tests — IR visualization (18 tests)
├── test_c_runtime.py    # Integration — compile generated C & run binary (37 tests)
└── mock_mp/             # Minimal C stubs for MicroPython API

examples/                # Sample Python input files
modules/                 # Generated C output (gitignored except committed examples)
docs/                    # Documentation and ESP-IDF setup guides
blogs/                   # Technical blog posts (see Blog Writing Guidelines below)
Makefile                 # Build commands for firmware compilation and flashing
```

## Architecture

Pipeline: `Python source → ast.parse() → IRBuilder → FuncIR/ClassIR → Emitters → C code`

### Two-Phase IR Pipeline

**Phase 1: IR Building** (`ir_builder.py`)
- Parses Python AST into typed IR structures
- Handles prelude pattern: expressions return `(ValueIR, list[InstrIR])`
- Tracks temp variables, RTuple optimizations, type information

**Phase 2: Code Emission** (`function_emitter.py`, `class_emitter.py`, `module_emitter.py`)
- Converts IR to MicroPython C API calls
- Handles boxing/unboxing, type conversions
- Generates module registration boilerplate

### Key IR Types (`ir.py`)

| Category | Types | Purpose |
|----------|-------|---------|
| **Function-level** | `FuncIR`, `MethodIR` | Function/method signatures, bodies |
| **Class-level** | `ClassIR`, `FieldIR` | Class structure, fields, inheritance |
| **Statement** | `ReturnIR`, `IfIR`, `WhileIR`, `ForRangeIR`, `ForIterIR`, `AssignIR`, ... | Control flow, assignments |
| **Expression** | `BinOpIR`, `CallIR`, `SubscriptIR`, `CompareIR`, ... | Computations |
| **Value** | `ConstIR`, `NameIR`, `TempIR` | Leaf values |
| **Instruction** | `ListNewIR`, `DictNewIR`, `MethodCallIR`, ... | Prelude instructions (side effects) |

### The Prelude Pattern

Every expression returns `tuple[ValueIR, list[InstrIR]]`:
- **ValueIR**: The result value (const, name, temp, or compound expression)
- **list[InstrIR]**: Instructions that must execute BEFORE the value is valid

This separates "what value" from "what side effects" — critical for correct C code generation.

### Key Functions

- **`compile_source(source: str, module_name: str) -> str`** — Core: source → C string
- **`compile_to_micropython(path, output_dir) -> CompilationResult`** — File-level wrapper
- **`IRBuilder.build_function(node) -> FuncIR`** — AST function → IR
- **`FunctionEmitter(func_ir).emit() -> str`** — IR → C code

## IR Debugging

When debugging compilation issues, use the `--dump-ir` flag to inspect intermediate representation:

```bash
# Dump full module IR as human-readable text
mpy-compile examples/factorial.py --dump-ir text

# Dump as ASCII tree (shows full IR structure)
mpy-compile examples/factorial.py --dump-ir tree

# Dump as JSON (for external tools)
mpy-compile examples/factorial.py --dump-ir json

# Dump specific function only
mpy-compile examples/factorial.py --dump-ir text --ir-function factorial
mpy-compile examples/dict_operations.py --dump-ir tree --ir-function merge_dicts
```

### Output Formats

**text** — Python-like readable format:
```
def merge_dicts(d1: MP_OBJ_T, d2: MP_OBJ_T) -> MP_OBJ_T:
  c_name: dict_operations_merge_dicts
  max_temp: 2
  locals: {d1: MP_OBJ_T, d2: MP_OBJ_T, result: MP_OBJ_T, key: MP_OBJ_T}
  body:
    result: mp_obj_t = {}
    # iter prelude:
      _tmp1 = d1.keys()
    for key in _tmp1:
      result[key] = d1[key]
    ...
```

**tree** — ASCII tree showing IR node hierarchy:
```
`-- root: FuncIR
    |-- name: "factorial"
    |-- c_name: "factorial_factorial"
    |-- params: list[1]
    |-- body: list[2]
    |   |-- [0]: IfIR
    |   |   |-- test: CompareIR
    |   |   |   |-- left: NameIR
    |   |   |   |-- ops: list[1]
    ...
```

**json** — Machine-readable for external tools:
```json
{
  "_type": "FuncIR",
  "name": "add",
  "c_name": "factorial_add",
  "params": [["a", "CType.MP_INT_T"], ["b", "CType.MP_INT_T"]],
  "body": [{"_type": "ReturnIR", "value": {"_type": "BinOpIR", ...}}]
}
```

### Debugging Workflow

1. **Compilation fails or wrong output?** Dump IR to see what was built:
   ```bash
   mpy-compile myfile.py --dump-ir text --ir-function problematic_func
   ```

2. **Check prelude instructions** — Look for `# prelude:` or `# iter prelude:` in text output

3. **Verify temp variable allocation** — Check `max_temp` field matches usage

4. **Compare with expected** — Use tree format to see exact IR structure

### Programmatic IR Inspection

```python
import ast
from mypyc_micropython.ir_builder import IRBuilder
from mypyc_micropython.ir_visualizer import dump_ir

source = '''
def add(a: int, b: int) -> int:
    return a + b
'''

tree = ast.parse(source)
builder = IRBuilder("test")

for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.FunctionDef):
        func_ir = builder.build_function(node)
        print(dump_ir(func_ir, "text"))   # or "tree" or "json"
```

## Code Style

### General Rules
- **Never use emoji** in code, comments, commit messages, or documentation - strictly text-only

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
        result = compile_source(source, "test")
        assert "mp_obj_new_dict" in result
```
1. Define Python source as triple-quoted string
2. Call `compile_source(source, "test")`
3. Assert on substrings in generated C

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

### Device tests (run_device_tests.py)

**IMPORTANT**: When adding or updating features, ALWAYS update `run_device_tests.py` with corresponding device tests.

```bash
# Run all device tests (compiles, builds, flashes, then tests)
make test-device BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101

# Run device tests only (skip compile/build/flash if already done)
make run-device-tests PORT=/dev/cu.usbmodem2101
```

Test pattern in `run_device_tests.py`:
```python
def test_tuple_operations():
    test(
        "make_point",
        "import tuple_operations as t; print(t.make_point())",
        "(10, 20)",
    )
```

Each module should have a `test_<module>()` function added to `run_all_tests()`.

### Benchmarks (run_benchmarks.py)

Compare native compiled modules vs vanilla MicroPython interpreter performance.

```bash
# Run all benchmarks on device
make benchmark PORT=/dev/cu.usbmodem2101
```

#### Adding New Benchmarks

Add entries to the `BENCHMARKS` list in `run_benchmarks.py`:

```python
BENCHMARKS = [
    # (name, native_code, python_code)
    (
        "my_func(1000) x100",           # Descriptive name with iterations
        """
import my_module
import time
start = time.ticks_us()
for _ in range(100):
    my_module.my_func(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def my_func(n):
    # Vanilla Python implementation
    pass
start = time.ticks_us()
for _ in range(100):
    my_func(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
]
```

**Benchmark naming convention**: `function_name(args) xN` where N is iteration count.

#### Example Output

```
Benchmark                            Native       Python    Speedup
----------------------------------------------------------------------
sum_range(1000) x100                 8929us     310206us     34.74x
chained_attr x10000                129663us     234032us      1.80x
container_attr x10000               99621us     190022us      1.91x
----------------------------------------------------------------------
TOTAL                             9060383us   33422565us      3.69x

Average speedup: 10.90x
```

## ESP-IDF / Firmware

For building firmware and flashing to ESP32, see platform-specific guides:
- **Linux**: [docs/esp-idf-setup-linux.md](docs/esp-idf-setup-linux.md)
- **macOS**: [docs/esp-idf-setup-macos.md](docs/esp-idf-setup-macos.md)

### Device Testing Workflow

**IMPORTANT**: Always detect the connected board type before building firmware.

```bash
# 1. Check connected device
ls /dev/cu.usb*                                  # macOS - find USB serial port

# 2. Detect board type via esptool (run BEFORE building)
source ~/esp/esp-idf/export.sh
esptool.py --port /dev/cu.usbmodem2101 chip_id  # Shows chip type (ESP32-C6, C3, S3, etc.)

# 3. Build with correct board type
make build BOARD=ESP32_GENERIC_C6               # Match detected chip!
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101
```

### Current Development Hardware

| Item | Value |
|------|-------|
| Board | ESP32-C6 DevKit |
| Port (macOS) | `/dev/cu.usbmodem2101` |
| Board variable | `ESP32_GENERIC_C6` |

### Build Commands

Key commands: `make build BOARD=ESP32_GENERIC_C6`, `make flash`, `make deploy`.
Always run `source ~/esp/esp-idf/export.sh` before firmware builds.

| Variable | Default | Description |
|----------|---------|-------------|
| `BOARD` | `ESP32_GENERIC` | Target board (`ESP32_GENERIC_C3`, `ESP32_GENERIC_C6`, `ESP32_GENERIC_S3`) |
| `PORT` | `/dev/ttyACM0` | Serial port (macOS: `/dev/cu.usbmodem2101`) |
| `ESP_IDF_DIR` | `~/esp/esp-idf` | ESP-IDF installation path |

## Blog Writing Guidelines

Technical blog posts in `blogs/` document compiler features with educational depth. Follow this structure:

### Required Structure (3 Parts)

1. **Part 1: Compiler Theory** — Explain relevant compiler concepts
   - What is a compiler and why we need one
   - The compilation pipeline (Python → AST → IR → C)
   - Why intermediate representation matters
   - IR node design and the prelude pattern

2. **Part 2: C Background** — Essential C for Python developers
   - Pointers and memory addresses
   - Structs and memory layout
   - Arrow operator (`->`) for pointer access
   - Type casting and macros
   - MicroPython-specific patterns (`MP_OBJ_TO_PTR`, boxing/unboxing)

3. **Part 3: Implementation** — The actual feature implementation
   - The problem being solved
   - The bug or missing case
   - The solution (new IR nodes, tracking, emission)
   - Complete step-by-step compilation example
   - Testing approach

### IR Visualization (REQUIRED)

**Always include IR dump output in blog posts.** This helps readers understand the intermediate representation before seeing generated C code.

Use the `--dump-ir` flag to generate IR output:

```bash
# Text format (most readable for blogs)
mpy-compile examples/myfile.py --dump-ir text

# For specific function
mpy-compile examples/myfile.py --dump-ir text --ir-function my_func
```

Example IR output to include in blogs:

```
def get_width(rect: MP_OBJ_T) -> MP_INT_T:
  c_name: module_get_width
  max_temp: 2
  locals: {rect: MP_OBJ_T}
  body:
    # prelude:
      _tmp1 = rect.bottom_right.x
      _tmp2 = rect.top_left.x
    return (_tmp1 - _tmp2)
```

The IR visualization shows:
- Function signature with C types
- Temp variable allocation (`max_temp`)
- Local variable types
- Prelude instructions (side effects)
- Expression structure

### Blog File Naming

Use sequential numbering: `NN-feature-name.md`

```
blogs/
├── 01-list-and-forloop-support.md
├── 02-dict-support.md
├── ...
├── 11-class-parameter-access.md
```

### Code Examples

- Show Python input, IR output, AND C output (three-stage view)
- Include IR representation to bridge Python and C understanding
- Use ASCII diagrams for memory layouts
- Add tables for comparisons (Python runtime vs compiled C)

### Target Audience

Write for Python developers unfamiliar with:
- C programming
- Compiler internals
- MicroPython's C API

Explain every C concept before using it.

## Version Matrix

| Component | Version |
|-----------|---------|
| Python | ≥3.10 |
| MicroPython submodule | v1.28.0-preview |
| ESP-IDF (for firmware) | v5.4.2 |
| mypy | ≥1.0.0 |

## Pre-PR Device Testing (REQUIRED)

**Before creating any PR that adds or modifies compiler features, ALWAYS run device tests on real hardware.**

### When Device Testing is Required

- Adding new language features (string methods, operators, builtins)
- Modifying code generation (emitters, IR builder)
- Adding new example modules
- Fixing bugs in compiled output

### Device Testing Workflow

```bash
# 1. Detect connected device
ls /dev/cu.usb*

# 2. Compile all examples including new ones
make compile-all

# 3. Build firmware with new modules
make build BOARD=ESP32_GENERIC_C6

# 4. Flash to device
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101

# 5. Run device tests (REQUIRED before PR)
make run-device-tests PORT=/dev/cu.usbmodem2101

# 6. Run benchmarks (optional but recommended)
make benchmark PORT=/dev/cu.usbmodem2101
```

### If No Device Available

If hardware is not connected, explicitly note in the PR:
- "Device tests pending - no hardware available"
- Request reviewer to run device tests before merge

**DO NOT create PRs for compiler features without either:**
1. Running device tests successfully, OR
2. Explicitly noting device tests are pending in PR description

## GitHub CLI Configuration

This repository uses the `anhlt` GitHub account. Before any `gh` commands, ensure the correct account is active:

```bash
gh auth switch --user anhlt
```

Always verify with `gh auth status` if PR creation fails with "must be a collaborator" error.

## Changelog

This project uses [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

**When creating or updating a PR, ALWAYS update CHANGELOG.md:**

1. Add entries under `## [Unreleased]` section
2. Use appropriate category: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`
3. Each entry should be a single line describing the change
4. Reference PR numbers when available

Example:
```markdown
## [Unreleased]

### Added
- `print()` builtin function support (#3)

### Changed
- Move generated usermod files from examples/ to modules/

### Fixed
- Void functions now return mp_const_none
```
