# Adding String Operations to mypyc-micropython

*Implementing string method support by leveraging MicroPython's dynamic method dispatch.*

---

## Part 1: Compiler Theory

### The Compilation Pipeline

When you write `s.upper()` in Python, our compiler transforms it through several stages:

```
Python source → AST → IR (Intermediate Representation) → C code
```

For string operations, the key insight is that we don't compile the string methods themselves - MicroPython already has them. We just need to generate C code that *calls* those methods at runtime.

### The Prelude Pattern

Method calls have side effects - they execute code and return values. Our IR separates "what value" from "what side effects" using the prelude pattern:

```
def to_upper(s: MP_OBJ_T) -> MP_OBJ_T:
  c_name: string_operations_to_upper
  max_temp: 1
  locals: {s: MP_OBJ_T}
  body:
    # prelude:
      _tmp1 = s.upper()    <-- Side effect: call method, store result
    return _tmp1           <-- Value: use the stored result
```

The prelude contains instructions that must execute before the return value is valid.

### Two Patterns for Strings

String support requires two different compilation patterns:

1. **Method calls** (`s.upper()`) → Generate dynamic dispatch code
2. **`str()` builtin** (`str(42)`) → Generate type constructor call

---

## Part 2: C Background for Python Developers

### MicroPython's Object System

Every Python object in MicroPython is an `mp_obj_t` - a pointer-sized value that can hold:
- Small integers directly (tagged)
- Pointers to heap objects

```c
typedef void *mp_obj_t;  // Simplified - actually more complex
```

### Type Objects

In Python, `str` is both a type and a callable. In MicroPython's C code, it's a struct:

```c
const mp_obj_type_t mp_type_str = {
    { &mp_type_type },
    .name = MP_QSTR_str,
    .make_new = mp_obj_str_make_new,  // Constructor function
    .print = str_print,
    // ... other slots
};
```

When you call `str(42)` in Python, MicroPython:
1. Sees you're calling a type object
2. Looks up its `.make_new` slot
3. Calls that function with your arguments

### Boxing and Unboxing

Native C integers (`mp_int_t`) must be "boxed" into Python objects (`mp_obj_t`) before passing to MicroPython APIs:

```c
mp_int_t n = 42;                    // Native C integer
mp_obj_t boxed = mp_obj_new_int(n); // Python int object
```

### Key MicroPython APIs

| Function | Purpose |
|----------|---------|
| `mp_load_attr(obj, qstr)` | Look up attribute on object |
| `mp_call_function_n_kw(fn, n, kw, args)` | Call function with args |
| `mp_call_function_1(fn, arg)` | Call function with 1 arg |
| `mp_binary_op(op, lhs, rhs)` | Binary operation (+, *, in, etc.) |
| `MP_OBJ_FROM_PTR(ptr)` | Convert C pointer to mp_obj_t |

---

## Part 3: Implementation

### Problem: String Methods Not Compiling

Before this change, code like `s.upper()` failed to compile. The compiler didn't know how to handle string method calls.

### Solution 1: Method Dispatch Pattern

String methods use dynamic dispatch via `mp_load_attr()`. MicroPython's string methods are `static` in `py/objstr.c` - not publicly accessible - so we call them indirectly.

**Python:**
```python
def to_upper(s: str) -> str:
    return s.upper()
```

**IR:**
```
def to_upper(s: MP_OBJ_T) -> MP_OBJ_T:
  c_name: string_operations_to_upper
  max_temp: 1
  locals: {s: MP_OBJ_T}
  body:
    # prelude:
      _tmp1 = s.upper()
    return _tmp1
```

**Generated C:**
```c
static mp_obj_t string_operations_to_upper(mp_obj_t s) {
    mp_obj_t _tmp1 = mp_call_function_n_kw(
        mp_load_attr(s, MP_QSTR_upper),  // Look up "upper" method
        0, 0, NULL                        // 0 args
    );
    return _tmp1;
}
```

How `mp_load_attr(s, MP_QSTR_upper)` works:
1. Get the type of `s` (which is `mp_type_str`)
2. Search the type's attribute table for `MP_QSTR_upper`
3. Return a bound method object

For methods with arguments like `s.replace("a", "b")`:

**IR:**
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

**Generated C:**
```c
static mp_obj_t string_operations_replace_string(mp_obj_t s, mp_obj_t old, mp_obj_t new) {
    mp_obj_t _args[] = {old, new};
    mp_obj_t _tmp1 = mp_call_function_n_kw(
        mp_load_attr(s, MP_QSTR_replace),
        2, 0, _args  // 2 positional args
    );
    return _tmp1;
}
```

### Solution 2: The `str()` Builtin

Converting values to strings requires calling the `str` type directly:

**Python:**
```python
def int_to_str(n: int) -> str:
    return str(n)
```

**Generated C:**
```c
static mp_obj_t int_to_str(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    return mp_call_function_1(
        MP_OBJ_FROM_PTR(&mp_type_str),  // The str type itself
        mp_obj_new_int(n)                // Box the int argument
    );
}
```

Step-by-step execution:
```
str(42)
    |
    v
mp_call_function_1(&mp_type_str, mp_obj_new_int(42))
    |
    v
MicroPython sees we're calling a type object
    |
    v
Looks up mp_type_str.make_new -> mp_obj_str_make_new
    |
    v
mp_obj_str_make_new converts 42 to string "42"
    |
    v
Returns mp_obj_t pointing to "42"
```

Why use `mp_call_function_1` instead of `mp_obj_str_make_new` directly? Because `mp_obj_str_make_new` is `static` - not part of MicroPython's public API.

### Bug Fix: `str` Type Mapping

One bug discovered: the compiler mapped `str` type annotations to `const char*`:

```python
"str": "const char*"  # Wrong!
```

This broke method calls because you can't call `.upper()` on a C string pointer. The fix:

```python
"str": "mp_obj_t"  # Correct - Python string object
```

### Operators

String operators compile to `mp_binary_op()`:

```c
// a + b (concatenation)
mp_binary_op(MP_BINARY_OP_ADD, a, b);

// s * 3 (repetition)
mp_binary_op(MP_BINARY_OP_MULTIPLY, s, mp_obj_new_int(3));

// "x" in s (containment)
mp_binary_op(MP_BINARY_OP_IN, substring, s);
```

### MicroPython ESP32 Limitations

Some string methods aren't available in the default ESP32 build:
- `capitalize()`, `title()`, `swapcase()`
- `ljust()`, `rjust()`, `zfill()`

These require `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` in firmware config.

---

## Summary

String operations use two patterns:

1. **Methods** (`s.upper()`) - `mp_load_attr()` + `mp_call_function_n_kw()` for dynamic dispatch
2. **`str()` builtin** - `mp_call_function_1(&mp_type_str, arg)` to call the type constructor

Both delegate to MicroPython's runtime since string internals aren't public C APIs. The speedup comes from native C control flow around these calls.
