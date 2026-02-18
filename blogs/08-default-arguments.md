# Default Arguments: When Less is More

*Implementing Python's flexible function signatures in MicroPython's rigid C API.*

---

Python's default arguments feel natural: `def greet(name, greeting="Hello")`. But MicroPython's C API expects a fixed number of arguments per function. How do you bridge that gap?

This post explores how we implemented default argument support, translating Python's flexible calling conventions into MicroPython's macro-based function definitions.

## The Challenge: Python Flexibility vs C Rigidity

In Python, these calls are all valid:

```python
def connect(host: str, port: int = 8080, timeout: int = 30) -> bool:
    # ...
    return True

connect("localhost")           # port=8080, timeout=30
connect("localhost", 443)      # timeout=30  
connect("localhost", 443, 60)  # all explicit
```

But MicroPython's standard function macros are rigid:

```c
// Fixed argument counts
MP_DEFINE_CONST_FUN_OBJ_0(name_obj, func);  // exactly 0 args
MP_DEFINE_CONST_FUN_OBJ_1(name_obj, func);  // exactly 1 arg
MP_DEFINE_CONST_FUN_OBJ_2(name_obj, func);  // exactly 2 args
MP_DEFINE_CONST_FUN_OBJ_3(name_obj, func);  // exactly 3 args
```

There's no `MP_DEFINE_CONST_FUN_OBJ_1_TO_3` for "1 required, 2 optional."

## The Solution: VAR_BETWEEN

MicroPython provides `MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN` for variable argument counts:

```c
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(name_obj, min_args, max_args, func);
```

The function receives arguments as an array:

```c
static mp_obj_t my_func(size_t n_args, const mp_obj_t *args) {
    // n_args tells us how many were actually passed
    // args[0], args[1], ... contain the values
}
```

For our `connect` example with 1 required and 2 optional arguments:

```c
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(connect_obj, 1, 3, connect);
```

## Tracking Defaults in the IR

We added `DefaultArg` to capture default values at compile time:

```python
@dataclass
class DefaultArg:
    value: int | float | bool | str | None
    c_expr: str  # Pre-computed C expression
```

The IR builder extracts defaults from the AST:

```python
def _parse_defaults(self, args: ast.arguments, num_params: int) -> dict[int, DefaultArg]:
    defaults = {}
    # Python stores defaults for the LAST N parameters
    # If we have 3 params and 2 defaults, defaults apply to params[1] and params[2]
    first_default_idx = num_params - len(args.defaults)
    
    for i, default_node in enumerate(args.defaults):
        param_idx = first_default_idx + i
        value, c_expr = self._eval_default(default_node)
        defaults[param_idx] = DefaultArg(value=value, c_expr=c_expr)
    
    return defaults
```

## Generating the Conditional Unboxing

The key trick is conditional argument extraction. Instead of:

```c
mp_int_t port = mp_obj_get_int(args[1]);  // Crashes if n_args < 2!
```

We generate:

```c
mp_int_t port = (n_args > 1) ? mp_obj_get_int(args[1]) : 8080;
```

This ternary pattern handles all argument types:

```c
// Integer with default
mp_int_t port = (n_args > 1) ? mp_obj_get_int(args[1]) : 8080;

// Float with default
mp_float_t factor = (n_args > 1) ? mp_get_float_checked(args[1]) : 1.5;

// Bool with default
bool verbose = (n_args > 1) ? mp_obj_is_true(args[1]) : false;

// Object with default (string, None, etc.)
mp_obj_t name = (n_args > 1) ? args[1] : mp_obj_new_str("default", 7);
```

## The Complete Picture

Here's what `def greet(name: str, greeting: str = "Hello") -> str` compiles to:

```c
static mp_obj_t module_greet(size_t n_args, const mp_obj_t *args) {
    mp_obj_t name = args[0];  // Required - always present
    mp_obj_t greeting = (n_args > 1) ? args[1] : mp_obj_new_str("Hello", 5);
    
    // Function body...
    return result;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(module_greet_obj, 1, 2, module_greet);
```

The macro ensures MicroPython validates argument count before calling our function:
- `n_args < 1` → MicroPython raises TypeError
- `n_args > 2` → MicroPython raises TypeError
- `1 <= n_args <= 2` → Our function runs

## Edge Cases

**All arguments have defaults:**
```python
def config(a: int = 1, b: int = 2) -> int:
    return a + b
```

Generates `min_args=0`:
```c
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(config_obj, 0, 2, config);
```

**Container defaults (mutable default antipattern):**
```python
def append_to(items: list = []) -> list:
    return items
```

We generate a fresh container each call:
```c
mp_obj_t items = (n_args > 0) ? args[0] : mp_obj_new_list(0, NULL);
```

This actually avoids Python's infamous mutable default gotcha! Each call gets a new empty list if none is provided.

## Performance Consideration

The ternary checks add minimal overhead — a single comparison per optional argument. For hot paths, users can always pass all arguments explicitly to skip the conditionals.

The real win is API ergonomics. Functions like `connect(host, port=8080, timeout=30)` are now natural to write and use, matching Python's expectations while generating efficient C.

## What's Next

Default arguments handle "fewer arguments than parameters." But what about "more arguments than parameters"? That's where `*args` and `**kwargs` come in — variadic functions that accept unlimited positional or keyword arguments.

---

*Default arguments bridge Python's flexible calling conventions with C's rigid function signatures. The VAR_BETWEEN macro and conditional unboxing make it seamless.*
