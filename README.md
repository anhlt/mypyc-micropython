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
| Default arguments, `*args`, `**kwargs` | ✅ |
| Arithmetic operators (`+`, `-`, `*`, `/`, `%`, `**`) | ✅ |
| Augmented assignment (`+=`, `-=`, `*=`, etc.) | ✅ |
| Bitwise operators (`&`, `\|`, `^`, `<<`, `>>`) | ✅ |
| Comparison operators (`==`, `!=`, `<`, `>`, `<=`, `>=`) | ✅ |
| Logical operators (`and`, `or`, `not`) | ✅ |
| `if`/`elif`/`else` statements | ✅ |
| `while` loops with `break`/`continue` | ✅ |
| `for` loops (range, list, dict, iterables) | ✅ |
| Ternary expressions (`x if cond else y`) | ✅ |
| Recursion | ✅ |
| Local variables (typed and inferred) | ✅ |
| Built-ins: `abs`, `int`, `float`, `bool`, `len`, `range`, `print`, `min`, `max`, `sum` | ✅ |
| Lists: literals, indexing, slicing, `append()`, `pop()`, iteration | ✅ |
| Dicts: literals, indexing, `get()`, `keys()`, `values()`, `items()`, full API | ✅ |
| Tuples: literals, indexing, slicing, unpacking, RTuple optimization | ✅ |
| Sets: literals, `add()`, `remove()`, `in` operator, iteration | ✅ |
| Strings: full method support (`split`, `join`, `replace`, `find`, `strip`, etc.) | ✅ |
| Classes: typed fields, `__init__`, methods, `@dataclass`, single inheritance | ✅ |
| Class features: `@property`, `@staticmethod`, `@classmethod`, vtable dispatch | ✅ |
| Special methods: `__str__`, `__repr__`, `__eq__`, `__len__`, `__getitem__`, `__setitem__` | ✅ |
| Exception handling: `try`/`except`/`else`/`finally`, `raise` | ✅ |
| Generators: `yield` in `while`/`for` loops | ✅ |
| Itertools: `enumerate()`, `zip()`, `sorted()` | ✅ |

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

The compiler uses a two-phase IR pipeline:

1. **Parsing**: Python source with `ast.parse()`
2. **IR Building**: AST to typed IR (FuncIR, ClassIR, StmtIR, ExprIR)
3. **Code Emission**: IR to MicroPython C API calls
4. **Module Assembly**: Generate module registration boilerplate

Key modules:
- `ir.py` - IR type definitions
- `ir_builder.py` - AST to IR translation
- `function_emitter.py` - FuncIR to C code
- `module_emitter.py` - Complete module assembly
- `class_emitter.py` - ClassIR to C structs and vtables

## License

MIT
