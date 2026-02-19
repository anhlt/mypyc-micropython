# Adding String Operations to mypyc-micropython

*Implementing comprehensive string method support by leveraging MicroPython's dynamic method dispatch pattern.*

---

## Where We Left Off

After implementing container types (lists, dicts, tuples, sets) and class support, the compiler handled most Python data structures. But string operations beyond basic concatenation were missing. Python code like `s.upper()` or `text.replace("old", "new")` would fail to compile.

This blog covers adding full string method support using the same method dispatch pattern established for container operations.

## What We Added

### String Methods: The Full List

We added support for 25+ string methods organized into categories:

| Category | Methods |
|----------|---------|
| **Case** | `upper()`, `lower()`, `capitalize()`, `title()`, `swapcase()` |
| **Search** | `find()`, `rfind()`, `index()`, `rindex()`, `count()` |
| **Check** | `startswith()`, `endswith()`, `isdigit()`, `isalpha()`, `isspace()`, `isupper()`, `islower()` |
| **Modify** | `replace()`, `strip()`, `lstrip()`, `rstrip()` |
| **Split/Join** | `split()`, `rsplit()`, `join()`, `partition()`, `rpartition()` |
| **Padding** | `center()`, `ljust()`, `rjust()`, `zfill()` |
| **Other** | `encode()` |

Plus the operators: `+` (concat), `*` (repeat), `in` (contains), `[]` (indexing/slicing), `len()`.

### Method Dispatch Pattern

String methods use the same dynamic dispatch pattern as dict methods. MicroPython doesn't expose string methods as public C functions, so we use `mp_load_attr()` + `mp_call_function_n_kw()`:

**Python:**
```python
def to_upper(s: str) -> str:
    return s.upper()
```

**Generated C:**
```c
static mp_obj_t string_operations_to_upper(mp_obj_t s) {
    mp_obj_t _method = mp_load_attr(s, MP_QSTR_upper);
    return mp_call_function_n_kw(_method, 0, 0, NULL);
}
```

The pattern works because every `mp_obj_t` has a type pointer, and `mp_load_attr()` walks the type's method table to find the named attribute.

### Variable Argument Methods

Some string methods take 0-2 arguments. Consider `split()`:

```python
s.split()           # Split on whitespace
s.split(",")        # Split on comma  
s.split(",", 2)     # Split on comma, max 2 splits
```

The compiler tracks argument count and generates the right call:

**0 args:**
```c
mp_obj_t _method = mp_load_attr(s, MP_QSTR_split);
return mp_call_function_n_kw(_method, 0, 0, NULL);
```

**1 arg:**
```c
mp_obj_t _method = mp_load_attr(s, MP_QSTR_split);
mp_obj_t _args[] = {sep};
return mp_call_function_n_kw(_method, 1, 0, _args);
```

**2 args:**
```c
mp_obj_t _method = mp_load_attr(s, MP_QSTR_split);
mp_obj_t _args[] = {sep, maxsplit};
return mp_call_function_n_kw(_method, 2, 0, _args);
```

This is handled by `_emit_two_arg_method()` in the container emitter, which checks argument count and generates the appropriate variant.

### String Concatenation and Repetition

String `+` and `*` operators compile to `mp_binary_op()`:

**Concatenation:**
```python
def concat(a: str, b: str) -> str:
    return a + b
```

```c
return mp_binary_op(MP_BINARY_OP_ADD, a, b);
```

**Repetition:**
```python
def repeat(s: str, n: int) -> str:
    return s * n
```

```c
return mp_binary_op(MP_BINARY_OP_MULTIPLY, s, mp_obj_new_int(n));
```

MicroPython's `mp_binary_op()` is polymorphic and handles string operands correctly.

### The `in` Operator

String containment checks use `mp_binary_op()` with `MP_BINARY_OP_IN`:

```python
def has_sub(s: str, sub: str) -> bool:
    return sub in s
```

```c
mp_obj_t _result = mp_binary_op(MP_BINARY_OP_IN, sub, s);
return _result;
```

Note the operand order: `sub in s` becomes `mp_binary_op(IN, sub, s)`.

### Method Table Extension

The container emitter's method table maps Python method names to emission handlers:

```python
_METHOD_TABLE: dict[str, Callable[..., str]] = {
    # List methods
    "append": _emit_list_append,
    "pop": _emit_list_pop,
    
    # Dict methods  
    "keys": _emit_zero_arg_method,
    "values": _emit_zero_arg_method,
    
    # String methods (new)
    "upper": _emit_zero_arg_method,
    "lower": _emit_zero_arg_method,
    "strip": _emit_one_arg_method,
    "split": _emit_two_arg_method,
    "replace": _emit_three_arg_method,
    # ... 20+ more string methods
}
```

Most string methods use generic handlers (`_emit_zero_arg_method`, `_emit_one_arg_method`, etc.) because they follow the same dispatch pattern. Only methods with special semantics need custom handlers.

## IR Representation

String method calls generate `MethodCallIR` nodes just like container methods. Here's the IR dump for `s.replace("old", "new")`:

```
mpy-compile examples/string_operations.py --dump-ir text --ir-function replace_string
```

```
def replace_string(s: MP_OBJ_T, old: MP_OBJ_T, new: MP_OBJ_T) -> MP_OBJ_T:
  c_name: string_operations_replace_string
  max_temp: 1
  locals: {s: MP_OBJ_T, old: MP_OBJ_T, new: MP_OBJ_T}
  body:
    # prelude:
      _tmp1 = s.replace(old, new)
    return _tmp1
```

The IR shows:
- Function takes three `mp_obj_t` parameters
- Method call is in the prelude (evaluated before return)
- Result stored in temp variable

## Testing Strategy

String operations are tested at three levels:

### Unit Tests (35 tests)

Verify generated C code structure:

```python
def test_string_upper(self):
    code = '''
def to_upper(s: str) -> str:
    return s.upper()
'''
    result = self.compile(code)
    self.assertIn("mp_load_attr", result)
    self.assertIn("MP_QSTR_upper", result)
```

### Device Tests (40 tests)

Test actual execution on ESP32:

```python
test(
    "to_upper",
    "import string_operations as s; print(s.to_upper('hello'))",
    "HELLO",
)
```

### Benchmarks (8 benchmarks)

Compare native vs interpreter performance:

```python
(
    "str.upper() x10000",
    """
import string_operations as s
import time
text = "hello world"
start = time.ticks_us()
for _ in range(10000):
    s.to_upper(text)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    # ... Python equivalent
),
```

## Performance Considerations

String method calls go through `mp_load_attr()` + `mp_call_function_n_kw()`, which involves:

1. Looking up the method in the type's attribute table
2. Creating an args array
3. Invoking the method through the generic call interface

This is the same overhead as calling methods from Python code. The benefit comes from avoiding Python bytecode interpretation for the surrounding code:

```python
def normalize_text(text: str) -> str:
    s: str = text.lower()
    s = s.strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s
```

The while loop, assignments, and control flow are native C. Only the method calls go through MicroPython's runtime. For code with many method calls interspersed with computation, this can still provide 2-4x speedup.

## Implementation Notes

### Why Not Direct C Calls?

MicroPython's string methods are implemented in `py/objstr.c`, but most are declared `static`. Unlike `mp_obj_list_append()`, there's no public `mp_obj_str_upper()`. So direct calls aren't possible without modifying MicroPython itself.

The method dispatch pattern is future-proof: it works with any MicroPython version that implements the standard Python string interface.

### Type Annotations Matter

For proper code generation, parameters must have type hints:

```python
def good(s: str) -> str:     # Works - s is mp_obj_t
    return s.upper()

def bad(s) -> str:           # May fail - s type unknown
    return s.upper()
```

The compiler uses type annotations to decide boxing/unboxing. Unannotated parameters default to `mp_obj_t`, which usually works for strings, but explicit annotations ensure correct code generation.

## What's Next

With string operations complete, the compiler covers most common Python patterns:

- Numeric types (int, float, bool)
- Containers (list, dict, tuple, set)
- Strings with full method support
- Classes with inheritance
- Control flow (if/while/for)
- Functions with default args and *args/**kwargs

Areas for future work:
- List comprehensions
- Generator expressions
- Exception handling
- More builtin functions

## Summary

String operations were straightforward to add because the method dispatch infrastructure was already in place from dict support. The key insights:

1. **Reuse the pattern**: String methods use the same `mp_load_attr()` + `mp_call_function_n_kw()` dispatch as dict methods
2. **Generic handlers**: Most methods fit into zero/one/two/three arg patterns
3. **Operators work**: Concatenation, repetition, and containment use `mp_binary_op()`
4. **Test at all levels**: Unit tests for code structure, device tests for correctness, benchmarks for performance
