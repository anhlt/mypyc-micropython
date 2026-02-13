# mypyc-micropython

Compile typed Python to MicroPython native C modules.

## Overview

`mypyc-micropython` takes a typed Python file and generates a MicroPython user module folder containing:

- `<module>.c` - MicroPython-compatible C code
- `micropython.mk` - Make build integration
- `micropython.cmake` - CMake build integration

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

### Command Line

```bash
# Compile a Python file
mpy-compile examples/factorial.py

# With verbose output
mpy-compile examples/factorial.py -v

# Specify output directory
mpy-compile mymodule.py -o /path/to/output
```

### Python API

```python
from mypyc_micropython import compile_to_micropython

result = compile_to_micropython("mymodule.py")
if result.success:
    print(f"Generated: {result.module_name}")
    print(result.c_code)
else:
    print(f"Errors: {result.errors}")
```

## Supported Python Features

| Feature | Status |
|---------|--------|
| Functions with `int`, `float`, `bool` parameters | ✅ |
| Arithmetic operators (`+`, `-`, `*`, `/`, `%`) | ✅ |
| Augmented assignment (`+=`, `-=`, `*=`, etc.) | ✅ |
| Bitwise operators (`&`, `\|`, `^`, `<<`, `>>`) | ✅ |
| Comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`) | ✅ |
| `if`/`else` statements | ✅ |
| `while` loops | ✅ |
| `for` loops (range, list, dict) | ✅ |
| Ternary expressions (`x if cond else y`) | ✅ |
| Recursion | ✅ |
| Local variables (typed and untyped) | ✅ |
| Built-ins: `abs`, `int`, `float`, `len`, `range` | ✅ |
| Lists: literals, indexing, `append()`, `pop()` | ✅ |
| Dicts: literals, indexing, `get()`, `keys()`, `values()`, `items()` | ✅ |
| Strings (basic) | Partial |
| Classes | ❌ |
| Exceptions | ❌ |

## Example

**Input:** `examples/factorial.py`

```python
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 2) + fib(n - 1)

def add(a: int, b: int) -> int:
    return a + b
```

**Output:** `examples/usermod_factorial/factorial.c`

```c
#include "py/runtime.h"
#include "py/obj.h"

static mp_obj_t factorial_factorial(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    if ((n <= 1)) {
        return mp_obj_new_int(1);
    }
    return mp_obj_new_int((n * mp_obj_get_int(factorial_factorial(mp_obj_new_int((n - 1))))));
}
static MP_DEFINE_CONST_FUN_OBJ_1(factorial_factorial_obj, factorial_factorial);

// ... more functions ...

MP_REGISTER_MODULE(MP_QSTR_factorial, factorial_user_cmodule);
```

## Integrating with MicroPython

1. Clone MicroPython:
   ```bash
   git clone https://github.com/micropython/micropython.git
   cd micropython
   ```

2. Copy the generated usermod folder:
   ```bash
   cp -r /path/to/usermod_factorial ports/unix/modules/
   ```

3. Build with user modules:
   ```bash
   cd ports/unix
   make USER_C_MODULES=modules/usermod_factorial/micropython.cmake
   ```

4. Test in MicroPython:
   ```python
   >>> import factorial
   >>> factorial.factorial(5)
   120
   >>> factorial.fib(10)
   55
   ```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/
```

## Architecture

The compiler works by:

1. Parsing Python source with `ast.parse()`
2. Walking the AST to extract typed function definitions
3. Translating each function to MicroPython C API calls
4. Generating module registration boilerplate

Key classes:
- `TypedPythonTranslator` - AST-to-C translator
- `CompilationResult` - Result container with generated code

## License

MIT
