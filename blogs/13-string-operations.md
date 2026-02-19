# Adding String Operations to mypyc-micropython

*Implementing string method support by leveraging MicroPython's dynamic method dispatch.*

---

## The Problem

After implementing container types, string operations beyond basic concatenation were missing. Code like `s.upper()` or `text.replace("old", "new")` wouldn't compile.

## Two Patterns: Methods vs Builtins

String support requires two different patterns:

1. **Method calls** (`s.upper()`, `s.split(",")`) - Dynamic dispatch via `mp_load_attr()`
2. **The `str()` builtin** (`str(42)`) - Calling the type object directly

### Pattern 1: Method Dispatch

String methods use the same pattern as dict methods. MicroPython doesn't expose string methods as public C functions (they're `static` in `py/objstr.c`), so we use dynamic dispatch:

**Python:**
```python
def to_upper(s: str) -> str:
    return s.upper()
```

**Generated C:**
```c
static mp_obj_t to_upper(mp_obj_t s) {
    mp_obj_t _method = mp_load_attr(s, MP_QSTR_upper);
    return mp_call_function_n_kw(_method, 0, 0, NULL);
}
```

How this works in MicroPython:

1. `mp_load_attr(s, MP_QSTR_upper)` - Look up the `upper` attribute on the string object. MicroPython walks the type's method table and returns a bound method object.

2. `mp_call_function_n_kw(_method, 0, 0, NULL)` - Call the method with 0 positional args, 0 keyword args, and no args array.

For methods with arguments like `s.split(",")`:

```c
mp_obj_t _method = mp_load_attr(s, MP_QSTR_split);
mp_obj_t _args[] = {sep};
return mp_call_function_n_kw(_method, 1, 0, _args);
```

### Pattern 2: The `str()` Builtin

Converting values to strings (`str(42)`) requires a different approach. We call the `str` type object directly:

**Python:**
```python
def format_number(n: int) -> str:
    s: str = str(n)
    return s
```

**Generated C:**
```c
static mp_obj_t format_number(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    mp_obj_t s = mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_str), mp_obj_new_int(n));
    return s;
}
```

How this works:

1. **`mp_type_str`** - MicroPython's type object for strings. In Python terms, this is literally the `str` class itself. It's defined in `py/objstr.c`:

```c
const mp_obj_type_t mp_type_str = {
    { &mp_type_type },
    .name = MP_QSTR_str,
    .make_new = mp_obj_str_make_new,  // Constructor
    // ...
};
```

2. **`MP_OBJ_FROM_PTR(&mp_type_str)`** - Convert the C pointer to an `mp_obj_t`. MicroPython uses tagged pointers, so all Python objects are represented as `mp_obj_t`.

3. **`mp_call_function_1(callable, arg)`** - MicroPython's generic function call. When you "call" a type object, MicroPython:
   - Sees it's a type object
   - Looks up its `.make_new` slot (`mp_obj_str_make_new`)
   - Calls that constructor with the argument

4. **`mp_obj_new_int(n)`** - Box the native `mp_int_t` into a Python int object, since `mp_call_function_1` expects `mp_obj_t` arguments.

The flow:
```
str(42) in Python
    |
    v
mp_call_function_1(&mp_type_str, mp_obj_new_int(42))
    |
    v
MicroPython sees we're calling a type object
    |
    v
Looks up mp_type_str.make_new = mp_obj_str_make_new
    |
    v
mp_obj_str_make_new converts int to string "42"
    |
    v
Returns mp_obj_t pointing to new string
```

Why not call `mp_obj_str_make_new` directly? It's declared `static` - not part of MicroPython's public API. Using `mp_call_function_1` is the stable, portable approach.

## Operators

String operators compile to `mp_binary_op()`:

```python
# Concatenation: a + b
mp_binary_op(MP_BINARY_OP_ADD, a, b)

# Repetition: s * 3
mp_binary_op(MP_BINARY_OP_MULTIPLY, s, mp_obj_new_int(3))

# Containment: "x" in s
mp_binary_op(MP_BINARY_OP_IN, substring, s)
```

MicroPython's `mp_binary_op()` is polymorphic and dispatches to the correct implementation based on operand types.

## Type Mapping Fix

One bug discovered: the compiler was mapping `str` type annotations to `const char*` instead of `mp_obj_t`. This caused variables like `s: str` to be declared incorrectly.

**Before (broken):**
```c
const char* s = ...;  // Wrong! Can't call methods on this
```

**After (fixed):**
```c
mp_obj_t s = ...;  // Correct - can call s.upper() etc.
```

The fix was simple: change the type mapping in `ir_builder.py`:
```python
"str": "mp_obj_t"  # Was "const char*"
```

## MicroPython ESP32 Limitations

Some string methods aren't available in the default MicroPython ESP32 build:
- `capitalize()`, `title()`, `swapcase()`
- `ljust()`, `rjust()`, `zfill()`

These require `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` in the firmware config.

## Summary

String operations use two patterns:

1. **Methods** (`s.upper()`) - `mp_load_attr()` + `mp_call_function_n_kw()` for dynamic dispatch
2. **`str()` builtin** - `mp_call_function_1(&mp_type_str, arg)` to call the type's constructor

Both patterns delegate to MicroPython's runtime, which is necessary since string internals aren't exposed as public C APIs. The speedup comes from native C control flow around these calls, not from the string operations themselves.
