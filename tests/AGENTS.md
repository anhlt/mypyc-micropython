# AGENTS.md - Test Suite

Four-layer testing architecture: Unit, C Runtime, Emitter, and Device tests.

## Quick Reference

```bash
# All tests (parallel)
pytest

# By category
pytest -m "not c_runtime"                   # Unit tests only (~20s)
pytest -m c_runtime                         # C runtime tests only
pytest tests/test_compiler.py               # Single file
pytest tests/test_compiler.py::TestDictOperations  # Single class
pytest -xvs -k "test_dict_literal"          # Single test by name

# Device tests (requires hardware)
make run-device-base-tests PORT=/dev/cu.usbmodem2101
make run-device-lvgl-tests PORT=/dev/cu.usbmodem2101
make benchmark PORT=/dev/cu.usbmodem2101
```

## Test File Overview

| File | LOC | Tests | Purpose |
|------|-----|-------|---------|
| `test_compiler.py` | 7,729 | 600+ | End-to-end compilation |
| `test_c_runtime.py` | 3,533 | 117 | Compile and execute C |
| `test_ir_builder.py` | 2,708 | 119 | IR generation |
| `test_emitters.py` | 2,599 | 85 | C code emission |
| `test_ir_visualizer.py` | ~500 | 18 | IR visualization |
| `test_type_checker.py` | 444 | 20 | mypy integration |
| `conftest.py` | ~200 | - | Fixtures |

## Four Testing Layers

### 1. Unit Tests (`test_compiler.py`, `test_ir_builder.py`)

Test Python-to-C compilation without executing C code.

```python
class TestDictOperations:
    def test_dict_literal(self):
        source = '''
def make_dict() -> dict:
    d: dict = {"key": 1}
    return d
'''
        result = compile_source(source, "test")  # type_check=True by default
        assert "mp_obj_new_dict" in result
```

**Pattern**: Source string -> `compile_source()` -> Assert on C output substrings

### 2. Emitter Tests (`test_emitters.py`)

Test emitters in isolation using manually constructed IR.

```python
def make_func(name="f", params=None, return_type=CType.MP_INT_T, 
              body=None, locals_=None, max_temp=0) -> FuncIR:
    return FuncIR(name=name, c_name=f"test_{name}", ...)

def test_emit_simple_function():
    func = make_func("add", 
                     params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
                     body=[...])
    emitter = FunctionEmitter(func)
    c_code, wrapper = emitter.emit()
    assert "mp_obj_get_int" in c_code
```

**Pattern**: Manual IR construction -> Emitter -> Assert on C output

### 3. C Runtime Tests (`test_c_runtime.py`)

Compile generated C with gcc and execute the binary.

```python
pytestmark = pytest.mark.c_runtime

def test_c_sum_range(compile_and_run):
    source = '''
def sum_range(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i
    return total
'''
    test_main_c = '''
#include <stdio.h>
int main(void) {
    mp_obj_t result = test_sum_range(mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
'''
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"
```

**Pattern**: Source + C main -> `compile_and_run` fixture -> Assert on stdout

### 4. Device Tests (`tests/device/`)

Run on real MicroPython hardware via `mpremote`.

```python
# tests/device/run_device_tests.py
def t(name, got, expected):
    """Assert expected string is in str(got)"""
    global _total, _passed, _failed
    _total += 1
    if expected in str(got):
        _passed += 1
        print("  OK: " + name)
    else:
        _failed += 1
        print("FAIL: " + name)

def suite(name):
    """Mark test suite start"""
    gc.collect()
    print("@S:" + name)

# Usage
suite("factorial")
import factorial
t("factorial(5)", factorial.factorial(5), "120")
```

**Pattern**: `suite()` grouping -> `import module` -> `t()` assertions

## The compile_and_run Fixture

Located in `conftest.py`, this fixture:

1. Compiles Python source to C
2. Rewrites includes to use mock headers (`tests/mock_mp/`)
3. Compiles with gcc (`-Wall -Werror`)
4. Executes binary and captures stdout

```python
@pytest.fixture
def compile_and_run(tmp_path: Path):
    mock_include_dir = Path(__file__).parent / "mock_mp"
    
    def _run(python_source: str, module_name: str, test_main_c: str) -> str:
        generated_c = compile_source(python_source, module_name, type_check=False)
        generated_c = _rewrite_generated_includes(generated_c)
        
        test_c = f"{generated_c}\n\n{test_main_c}\n"
        test_c_path = tmp_path / f"{module_name}_runtime_test.c"
        test_c_path.write_text(test_c)
        
        compile_cmd = ["/usr/bin/gcc", "-std=c99", "-Wall", "-Werror",
                       "-I", str(mock_include_dir), str(test_c_path), ...]
        # ... compile and execute ...
        return stdout
    
    return _run
```

## Mock MicroPython Runtime

`tests/mock_mp/` provides minimal C stubs for testing:

- `runtime.h` - 54KB of MicroPython C API stubs
- `obj.h` - Object type definitions

This allows compiling generated C with host gcc instead of cross-compiler.

## Device Test Files

| File | Description | Requires Display |
|------|-------------|-----------------|
| `run_device_tests.py` | Base language features | No |
| `run_benchmarks.py` | Performance comparison | No |
| `run_lvgl_tests.py` | LVGL + MVU tests | No (needs LVGL modules) |
| `run_nav_tests.py` | Navigation flow | Yes |
| `run_lvgl_mvu_tests.py` | MVU architecture | No (needs LVGL modules) |

## Type Checking in Tests

**ALWAYS use strict type checking by default:**

```python
# CORRECT: Default strict checking
result = compile_source(source, "test")

# ONLY when testing edge cases
result = compile_source(source, "test", type_check=False)  # Document why!
```

## Adding Tests for Bug Fixes

Every bug fix needs tests at multiple levels:

1. **IR builder test** - Verify IR is generated correctly
2. **Emitter test** - Verify C code is emitted correctly
3. **Compiler test** - End-to-end test
4. **C runtime test** - If testable with mock runtime
5. **Device test** - Add to `run_device_tests.py`

```python
# Example test naming for bug fix
class TestCustomClassMethodDispatch:
    def test_custom_class_add_method(self):
        """
        Bug: Registry.add() was incorrectly using set.add dispatch.
        Fix: Check receiver type before method dispatch.
        """
        source = '''...'''
        result = compile_source(source, "test")
        assert "mp_obj_set_store" not in result  # NOT using set.add
```

## Running Tests

```bash
# Parallel (default via pytest-xdist)
pytest

# Sequential (for debugging)
pytest -n0

# Verbose with stop on first failure
pytest -xvs

# Skip slow C runtime tests
pytest -m "not c_runtime"

# Only C runtime tests
pytest -xvs -m c_runtime
```

## CRITICAL: Device Testing

**Unit tests passing is NOT sufficient.**

Device testing is MANDATORY for:
- New language features
- Code generation changes
- Bug fixes in emitters
- Any change to core compiler files

See root `AGENTS.md` for full device testing workflow.
