# AGENTS.md — mypyc-micropython

Typed Python → MicroPython C module compiler.

## Build / Test / Lint Commands

```bash
pip install -e ".[dev]"                          # Install deps (one-time)
pytest                                           # All tests (<20s)
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
make run-device-base-tests PORT=/dev/cu.usbmodem2101  # Run base language feature tests only
make run-device-lvgl-tests PORT=/dev/cu.usbmodem2101  # Run LVGL test suite on device
make benchmark PORT=/dev/cu.usbmodem2101         # Benchmark native vs vanilla MicroPython
```

**IMPORTANT**: Always use `make` commands for compiling and testing. Never call `mpy-compile` directly.

## Incremental Firmware Build

The firmware build process supports incremental compilation to speed up the edit-compile-test cycle:

- **ccache**: Automatically enabled if installed (`brew install ccache` on macOS)
- **Ninja incremental**: ESP-IDF's build system only recompiles changed .c files
- **FORCE flag**: Use `FORCE=1` with make commands to force full recompilation

```bash
# Incremental build (default): only recompiles changed .c files
make compile-all BOARD=ESP32_GENERIC_C6
make build BOARD=ESP32_GENERIC_C6

# Force full recompilation
make compile-all BOARD=ESP32_GENERIC_C6 FORCE=1
```


## Project Layout

```
src/mypyc_micropython/
├── __init__.py          # Public API: compile_source, compile_to_micropython
├── cli.py               # CLI entry point (mpy-compile command, --dump-ir)
├── compiler.py          # Top-level compilation orchestration
├── ir.py                # IR definitions: FuncIR, ClassIR, StmtIR, ValueIR, etc.
├── ir_builder.py        # AST → IR translation (builds FuncIR, ClassIR from AST)
├── ir_visualizer.py     # IR debugging: dump IR as text/tree/JSON
├── type_checker.py      # mypy integration for type checking
├── base_emitter.py      # Base emitter class, sanitize_name, C_RESERVED_WORDS
├── function_emitter.py  # FuncIR → C code emission
├── method_emitter.py    # MethodIR → C code emission for class methods
├── module_emitter.py    # ModuleIR → complete C module assembly
├── class_emitter.py     # ClassIR → C structs, vtables, methods
├── container_emitter.py # IR emission helpers for list/dict operations
└── c_bindings/          # C binding utilities for MicroPython integration

tests/
├── conftest.py          # compile_and_run fixture (gcc compile + execute)
├── test_compiler.py     # Unit tests - full compilation (568 tests)
├── test_ir_builder.py   # Unit tests - IR building (119 tests)
├── test_ir_visualizer.py # Unit tests - IR visualization (18 tests)
├── test_c_runtime.py    # Integration - compile generated C & run binary (117 tests)
├── test_emitters.py     # Unit tests - emitter code generation (85 tests)
├── test_type_checker.py # Unit tests - mypy type checker integration (20 tests)
├── mock_mp/             # Minimal C stubs for MicroPython API
└── device/              # Device test runners (run on MicroPython via mpremote)
    ├── run_device_tests.py          # Base language feature tests (no LVGL required)
    ├── run_benchmarks.py            # Benchmark runner (native C vs vanilla)
    ├── run_lvgl_tests.py            # LVGL tests: screens, MVU (diff/viewnode/reconciler/program/app)
    ├── run_nav_tests.py             # LVGL navigation tests (requires display)
    ├── run_lvgl_mvu_tests.py        # LVGL MVU architecture tests
    └── run_screen_navigation_tests.py  # Screen navigation tree tests (requires display)

examples/                # Sample Python input files (37 modules + 1 package)
modules/                 # Generated C output (gitignored except committed examples)
docs/                    # Documentation and ESP-IDF setup guides
blogs/                   # Technical blog posts (see Blog Writing Guidelines below)
configs/                 # ESP-IDF configuration files
├── partitions-default.csv  # Default partition table
├── partitions-lvgl.csv     # LVGL partition table (larger app)
└── sdkconfig.lvgl          # LVGL-specific sdkconfig
scripts/                 # Build and setup scripts
Makefile                 # Build commands for firmware compilation and flashing
```

## LVGL MVU Framework (Proof of Concept)

The `extmod/lvgl_mvu/` package is a **proof of concept** that demonstrates the compiler can handle complex, real-world application patterns. It implements a Model-View-Update architecture for LVGL UI development.

**CRITICAL: Never work around compiler limitations for MVU code. Fix the compiler instead.**

The MVU framework tests the compiler's ability to handle:
- Module-level imports (`import lvgl as lv`)
- Function references as first-class values (`reconciler.register_factory(WidgetKey.LABEL, create_label)`)
- Complex class hierarchies and method dispatch
- Callback registration patterns
- Cross-module dependencies within a package

When MVU compilation fails, it indicates a compiler bug that must be fixed in:
- `ir_builder.py` - IR generation for the problematic pattern
- `function_emitter.py` - C code emission for function-level IR
- `container_emitter.py` - C code emission for container/expression IR
- `class_emitter.py` - C code emission for class-level IR

**Example of what NOT to do:**
```python
# WRONG: Working around by excluding from compilation
# Instead, fix the compiler to handle the pattern
```

**Example of what TO do:**
```python
# RIGHT: Add FuncRefIR handling to container_emitter.py
elif isinstance(value, FuncRefIR):
    return f"MP_OBJ_FROM_PTR(&{value.c_name}_obj)"
```

## Architecture

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

**IMPORTANT**: When adding new IR classes to `ir.py`, you MUST also update `ir_visualizer.py` to handle the new type. Otherwise, IR dumps will show `/* unknown instr: YourNewIR */` instead of useful debugging output.

### The Prelude Pattern

Every expression returns `tuple[ValueIR, list[InstrIR]]`:
- **ValueIR**: The result value (const, name, temp, or compound expression)
- **list[InstrIR]**: Instructions that must execute BEFORE the value is valid

This separates "what value" from "what side effects" — critical for correct C code generation.

### Key Functions

- **`compile_source(source, module_name, *, type_check=True, strict=True) -> str`** — Core: source -> C string
- **`compile_to_micropython(path, output_dir) -> CompilationResult`** — File-level wrapper
- **`IRBuilder.build_function(node) -> FuncIR`** — AST function -> IR
- **`FunctionEmitter(func_ir).emit() -> tuple[str, str]`** — IR -> C code (native + wrapper)

### Type System

The compiler follows mypyc's type erasure strategy:

**CType enum** (`ir.py`): Maps Python types to C types
- `MP_OBJ_T` — boxed `mp_obj_t` for known container/string types (`str`, `list`, `dict`, `tuple`, `set`)
- `MP_INT_T` — unboxed `mp_int_t` for `int`
- `MP_FLOAT_T` — unboxed `mp_float_t` for `float`
- `BOOL` — native `bool`
- `VOID` — `void` (for `None` returns)
- `GENERAL` — truly unknown/dynamic types (`object`, `Any`, unannotated). Maps to `mp_obj_t` in C but semantically distinct from `MP_OBJ_T`

**Literal type erasure** (`ir_builder.py`): `Literal[3]` erases to `int`, `Literal["hello"]` to `str`, `Literal[True]` to `bool`. Same strategy as mypyc.

**TypeVar erasure** (`ir_builder.py`, `compiler.py`): TypeVar erases to its upper bound.
- Unbounded `T = TypeVar("T")` erases to `object` (CType.GENERAL)
- Bounded `N = TypeVar("N", bound=int)` erases to `int` (CType.MP_INT_T)
- PEP 695 syntax (`def f[T](...)`) supported in IR builder but requires `--no-type-check` (mypy does not yet support PEP 695)
- Classic syntax (`T = TypeVar("T")`) works with mypy strict mode

**Key methods**:
- `CType.from_python_type(type_str)` — maps Python type strings to CType
- `CType.from_c_type_str(c_type)` — maps C type strings directly to CType (avoids roundtrip through Python types)
- `IRBuilder._erase_literal_type(node)` — unwraps Literal AST to underlying type
- `IRBuilder._resolve_typevar(name)` — resolves TypeVar name to bound type
- `IRBuilder._scan_typevars()` — scans PEP 695 function type params
- `IRBuilder.register_typevar(node)` — registers classic TypeVar assignments

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
- **Python target**: 3.12+
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

### Type Checking in Tests (IMPORTANT)

**Always use strict type checking by default in tests.** This ensures test sources are valid typed Python that would pass mypy strict mode.

```python
# CORRECT: Use type_check=True (default) for strict checking
result = compile_source(source, "test")  # type_check=True, strict=True by default
result = compile_source(source, "test", type_check=True)  # explicit

# ONLY use type_check=False when testing specific edge cases that intentionally
# bypass type checking (e.g., testing error handling for untyped code)
result = compile_source(source, "test", type_check=False)  # document why!
```

**Why strict by default?**
- Catches type errors early in test sources
- Ensures generated C code handles properly typed inputs
- Matches production behavior (CLI uses strict by default)
- Prevents tests from passing with invalid Python that would fail in real use

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
        result = compile_source(source, "test")  # strict type checking enabled
        assert "mp_obj_new_dict" in result
```
1. Define Python source as triple-quoted string
2. Call `compile_source(source, "test")` (strict type check by default)
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

### Device tests (tests/device/run_device_tests.py)

**IMPORTANT**: When adding or updating features, ALWAYS update `tests/device/run_device_tests.py` with corresponding device tests.

```bash
# Full cycle: compile all examples + build firmware + flash + run tests
make test-device BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101

# Run base language feature tests only (skip compile/build/flash if already done)
make run-device-base-tests PORT=/dev/cu.usbmodem2101
```

**WARNING**: When running `make run-device-base-tests`, NEVER pipe the output through `grep`, `tail`, or other filters. The device test output is streaming and can cause the connection to hang or miss critical output. Always capture the full output:
```bash
# CORRECT: Full output, no filtering
make run-device-base-tests PORT=/dev/cu.usbmodem2101

# WRONG: Can cause hangs or missed output
make run-device-base-tests PORT=/dev/cu.usbmodem2101 | tail -50    # DON'T DO THIS
make run-device-base-tests PORT=/dev/cu.usbmodem2101 | grep async  # DON'T DO THIS
```


Test pattern in `tests/device/run_device_tests.py` (uses `t(name, got, expected)` helper and `suite(name)` for grouping):
```python
suite("special_methods")
import special_methods as sm

n3 = sm.Number(3)
n5 = sm.Number(5)
t("Number eq T", n3 == sm.Number(3), "True")
t("Number lt T", n3 < n5, "True")
t("Number hash", hash(sm.Number(42)), "42")
```

Each module should have a corresponding `suite("module_name")` block added before the summary section.

### Benchmarks (tests/device/run_benchmarks.py)

Compare native compiled modules vs vanilla MicroPython interpreter performance.

```bash
# Run all benchmarks on device
make benchmark PORT=/dev/cu.usbmodem2101
```

#### Adding New Benchmarks

Add a `bench_<name>()` function in `tests/device/run_benchmarks.py` and call it from `run_all_benchmarks()`:

```python
def bench_my_module():
    import my_module

    def native_fn():
        my_module.my_func(1000)

    def python_fn():
        total = 0
        for i in range(1000):
            total += i
        return total

    b("my_func(1000) x100", native_fn, python_fn, 100)
    gc.collect()
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

### Bug Fix Testing Requirements

**CRITICAL: Every bug fix MUST include tests.** When fixing a compiler bug:

1. **Add IR builder test** (`tests/test_ir_builder.py`) - Verify the IR is generated correctly
2. **Add emitter test** (`tests/test_emitters.py`) - Verify the C code is emitted correctly
3. **Add compiler test** (`tests/test_compiler.py`) - End-to-end test of the full compilation
4. **Add C runtime test** (`tests/test_c_runtime.py`) - Only if the bug can be tested with mock runtime

**Example: Custom class method dispatch bug**

Bug: `Registry.add()` method was incorrectly using `set.add` dispatch (emitting `mp_obj_set_store`).

Tests added:
- `test_emitters.py::TestEmitMethodCall::test_custom_class_method_with_builtin_name`
- `test_compiler.py::TestCustomClassMethodDispatch::test_custom_class_add_method`

**Why all test levels?**
- **IR builder tests**: Catch bugs in AST to IR translation
- **Emitter tests**: Catch bugs in IR to C code generation (isolated, fast)
- **Compiler tests**: Catch integration issues between IR builder and emitters
- **C runtime tests**: Verify generated code actually executes correctly

**Test naming convention for bug fixes:**
- Class: `TestFeatureNameBugFix` or existing feature test class
- Method: `test_<specific_scenario_that_was_broken>`
- Include a docstring explaining: the bug, the fix, and why this test catches it

## ESP-IDF / Firmware

For building firmware and flashing to ESP32, see platform-specific guides:
- **Linux**: [docs/esp-idf-setup-linux.md](docs/esp-idf-setup-linux.md)
- **macOS**: [docs/esp-idf-setup-macos.md](docs/esp-idf-setup-macos.md)

### Device Testing Workflow

**CRITICAL**: ALWAYS detect the connected board type BEFORE building firmware. Building for the wrong chip wastes time and will fail to flash.

```bash
# 1. Check connected device
ls /dev/cu.usb*                                  # macOS - find USB serial port

# 2. Detect board type via esptool (MANDATORY before building)
source ~/esp/esp-idf/export.sh
esptool.py --port /dev/cu.usbmodem2101 chip_id  # Shows chip type (ESP32-P4, C6, C3, S3, etc.)

# 3. Build with CORRECT board type (must match detected chip!)
make build BOARD=ESP32_GENERIC_P4               # For ESP32-P4
make build BOARD=ESP32_GENERIC_C6               # For ESP32-C6
make flash BOARD=ESP32_GENERIC_P4 PORT=/dev/cu.usbmodem2101
```

### Board Type Detection Quick Reference

| esptool Output | BOARD Variable |
|----------------|----------------|
| `ESP32-P4` | `ESP32_GENERIC_P4` |
| `ESP32-C6` | `ESP32_GENERIC_C6` |
| `ESP32-C3` | `ESP32_GENERIC_C3` |
| `ESP32-S3` | `ESP32_GENERIC_S3` |

### Build Commands

Key commands: `make build BOARD=<board>`, `make flash`, `make deploy`.
Always run `source ~/esp/esp-idf/export.sh` before firmware builds.

| Variable | Default | Description |
|----------|---------|-------------|
| `BOARD` | (required) | Target board - MUST match detected chip type |
| `PORT` | `/dev/ttyACM0` | Serial port (macOS: `/dev/cu.usbmodem2101`) |
| `ESP_IDF_DIR` | `~/esp/esp-idf` | ESP-IDF installation path |
| `BAUD` | `460800` | Serial baud rate for flashing |

### Build Output Best Practice

**NEVER** use `tail`, `head`, or pipe build output through truncation commands. Firmware builds produce thousands of lines — errors can appear anywhere.

**ALWAYS** grep for errors to catch build failures:

```bash
# CORRECT: Grep for errors and undefined references
make build BOARD=ESP32_GENERIC_P4 2>&1 | grep -E '(error:|undefined refer)'

# CORRECT: Full output (when you need all details)
make build BOARD=ESP32_GENERIC_P4

# WRONG: Tail misses errors in the middle of output
make build BOARD=ESP32_GENERIC_P4 2>&1 | tail -50    # DON'T DO THIS
make build BOARD=ESP32_GENERIC_P4 2>&1 | tail -100   # DON'T DO THIS
```

**Why this matters**: Linker errors (`undefined reference`) and compilation errors can appear hundreds of lines before the end of build output. Using `tail` will show "build succeeded" boilerplate while hiding critical errors.

## MicroPython C API Internals

See [docs/03-micropython-c-api.md](docs/03-micropython-c-api.md) for the full C API reference.

**IMPORTANT**: Always check that file before implementing new features or modifying code generation.
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

### Content Rules

- **Do NOT include test results** (unit tests, device tests, or benchmark output) in blog posts
- Blog posts are educational documentation, not test reports
- Focus on explaining concepts, not proving they work

## Version Matrix

| Component | Version |
|-----------|---------|
| Python | >=3.12 |
| MicroPython submodule | v1.28.0-preview |
| ESP-IDF (for firmware) | v5.4.2 |
| mypy | ≥1.0.0 |

## Device Testing (REQUIRED)

> **CRITICAL: Unit tests passing is NOT sufficient. Real device testing is MANDATORY.**
>
> This is a MicroPython compiler. The generated C code runs on microcontrollers, NOT on your
> development machine. Unit tests only verify C code generation - they DO NOT verify that
> the code actually works on real hardware. Many bugs only appear on device:
> - Memory alignment issues
> - Missing MicroPython runtime symbols
> - Integer overflow on 32-bit systems
> - Stack size limitations
> - Hardware-specific API differences
>
> **NEVER skip device testing. NEVER assume "tests pass" means "it works".**

**Device testing is required at TWO stages:**
1. **After implementing a feature** — Verify it works on real hardware before considering the feature complete
2. **Before creating a PR** — Final validation that everything works together

### When Device Testing is Required

- Adding new language features (string methods, operators, builtins)
- Modifying code generation (emitters, IR builder)
- Adding new example modules
- Fixing bugs in compiled output
- ANY change to `ir.py`, `ir_builder.py`, `function_emitter.py`, `class_emitter.py`, `module_emitter.py`, or `container_emitter.py`

### Device Testing Workflow

**CRITICAL**: ALWAYS detect the connected board type BEFORE building firmware. Building for the wrong chip wastes time and will fail to flash.

```bash
# 1. Detect connected device
ls /dev/cu.usb*

# 2. Detect board type via esptool (MANDATORY before building)
source ~/esp/esp-idf/export.sh
esptool.py --port /dev/cu.usbmodem2101 chip_id  # Shows chip type (ESP32-P4, C6, C3, S3, etc.)

# 3. Compile all examples including new ones
make compile-all BOARD=ESP32_GENERIC_P4         # Use detected board type

# 4. Build firmware with new modules
make build BOARD=ESP32_GENERIC_P4               # Must match detected chip!

# 5. Flash to device
make flash BOARD=ESP32_GENERIC_P4 PORT=/dev/cu.usbmodem2101

# 6. Run base language feature tests (REQUIRED after implementing feature AND before PR)
make run-device-base-tests PORT=/dev/cu.usbmodem2101

# 7. Run LVGL tests (REQUIRED for boards with display - see board table below)
make run-device-lvgl-tests PORT=/dev/cu.usbmodem2101

# 8. Run benchmarks (optional but recommended)
make benchmark PORT=/dev/cu.usbmodem2101
```

### Board-Specific Testing Requirements

Not all boards have displays. LVGL tests require a monitor and will fail on boards without one.

| Board | Chip | Display | Required Tests |
|-------|------|---------|----------------|
| `ESP32_GENERIC_C3` | ESP32-C3 | None | `make run-device-base-tests` only |
| `ESP32_GENERIC_C6` | ESP32-C6 | ST7789 SPI (172x320) | `make run-device-base-tests` + `make run-device-lvgl-tests` |
| `ESP32_GENERIC_P4` | ESP32-P4 | ST7701 MIPI-DSI (480x800) | `make run-device-base-tests` + `make run-device-lvgl-tests` |

**For boards WITHOUT display (C3):**
```bash
make compile-all BOARD=ESP32_GENERIC_C3 LVGL=0
make build BOARD=ESP32_GENERIC_C3 LVGL=0
make flash BOARD=ESP32_GENERIC_C3 LVGL=0 PORT=/dev/ttyACM0
make run-device-base-tests PORT=/dev/ttyACM0
```

**For boards WITH display (C6, P4):**
```bash
make compile-all BOARD=ESP32_GENERIC_C6
make build BOARD=ESP32_GENERIC_C6
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101
make run-device-base-tests PORT=/dev/cu.usbmodem2101
make run-device-lvgl-tests PORT=/dev/cu.usbmodem2101    # MANDATORY for display boards
```

**LVGL test files** (in `tests/device/`):

| File | Description | Requires Display |
|------|-------------|-----------------|
| `run_device_tests.py` | Base language feature tests | No |
| `run_lvgl_tests.py` | LVGL screens + MVU logic tests (diff, viewnode, reconciler, program, app) | No (but needs LVGL modules) |
| `run_nav_tests.py` | LVGL navigation flow tests | Yes |
| `run_lvgl_mvu_tests.py` | LVGL MVU architecture tests | No (but needs LVGL modules) |
| `run_screen_navigation_tests.py` | Screen navigation tree tests | Yes |

### Feature Implementation Checklist

A feature is NOT complete until:
- [ ] Unit tests pass (`pytest`)
- [ ] C runtime tests pass (`pytest -m c_runtime`)
- [ ] Example file created in `examples/`
- [ ] Device tests added to `tests/device/run_device_tests.py`
- [ ] **Device tests pass on real hardware** (this is the final verification)

### Why Device Testing Cannot Be Skipped

1. **C compiler differences**: gcc on your machine vs xtensa/riscv cross-compiler for ESP32
2. **Runtime environment**: Full libc vs MicroPython's minimal runtime
3. **Memory model**: 64-bit development machine vs 32-bit microcontroller
4. **API availability**: Some MicroPython APIs behave differently on device
5. **Real-world validation**: The entire point of this project is running on devices

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
