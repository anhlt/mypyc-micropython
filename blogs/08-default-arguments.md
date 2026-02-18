# Default Arguments: When Less is More

*Implementing Python's flexible function signatures in MicroPython's rigid C API.*

---

When you write `def greet(name, greeting="Hello")`, Python handles the complexity of optional arguments automatically. But MicroPython's C API expects fixed argument counts. This post explores how we bridged that gap, teaching our compiler to generate flexible function signatures from Python's default arguments.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) — How function signatures flow through the compilation pipeline
2. [C Background](#part-2-c-background-for-python-developers) — Arrays, ternary operators, and MicroPython's function macros
3. [Implementation](#part-3-implementation) — How we built default argument support

---

# Part 1: Compiler Theory

## Function Signatures in the Compilation Pipeline

Our compiler transforms Python functions through several stages. Default arguments affect multiple phases:

```
+------------------+    +------------------+    +------------------+    +------------------+
|  Python Source   | -> |       AST        | -> |       IR         | -> |     C Code       |
|                  |    |                  |    |                  |    |                  |
| def f(a, b=10)   |    | FunctionDef      |    | FuncIR with      |    | VAR_BETWEEN      |
|                  |    | with defaults    |    | DefaultArg       |    | + conditionals   |
+------------------+    +------------------+    +------------------+    +------------------+
```

### Phase 1: AST Extraction

Python's `ast` module gives us the default values in a specific format:

```python
# Python source
def connect(host: str, port: int = 8080, timeout: int = 30) -> bool:
    return True
```

```python
# AST representation (simplified)
FunctionDef(
    name='connect',
    args=arguments(
        args=[
            arg(arg='host', annotation=Name(id='str')),
            arg(arg='port', annotation=Name(id='int')),
            arg(arg='timeout', annotation=Name(id='int')),
        ],
        defaults=[Constant(value=8080), Constant(value=30)]  # Only 2 defaults!
    )
)
```

**Key insight**: Python stores defaults for only the LAST N parameters. If a function has 3 parameters and 2 defaults, the defaults apply to parameters 1 and 2 (0-indexed), not 0 and 1.

### Phase 2: IR Building

We transform the AST into our typed IR, capturing default information:

```python
@dataclass
class DefaultArg:
    value: int | float | bool | str | None
    c_expr: str  # Pre-computed C expression

@dataclass
class FuncIR:
    name: str
    c_name: str
    params: list[tuple[str, CType]]
    defaults: dict[int, DefaultArg]  # param_index -> default
    min_args: int  # Number of required arguments
    max_args: int  # Total parameters
```

The IR builder computes which arguments are required vs optional:

```python
def _parse_defaults(self, args: ast.arguments, num_params: int) -> dict[int, DefaultArg]:
    defaults = {}
    # defaults apply to the LAST N parameters
    first_default_idx = num_params - len(args.defaults)
    
    for i, default_node in enumerate(args.defaults):
        param_idx = first_default_idx + i
        value, c_expr = self._eval_default(default_node)
        defaults[param_idx] = DefaultArg(value=value, c_expr=c_expr)
    
    return defaults
```

### Phase 3: Code Emission

The emitter must generate:
1. A function signature accepting variable argument count
2. Logic to extract each argument OR use its default

This is where C knowledge becomes essential.

## Why IR Matters for Defaults

Without IR, we'd need to track default information during C emission while also parsing AST. By capturing defaults in the IR, we separate concerns:

| Phase | Responsibility |
|-------|---------------|
| IR Builder | Extract defaults from AST, compute min/max args |
| Emitter | Generate VAR_BETWEEN macro, conditional extraction |

The IR serves as a clean contract between phases.

## Compile-Time vs Runtime Defaults

Python evaluates default values at function **definition** time, not call time:

```python
def dangerous(items=[]):  # This list is created ONCE
    items.append(1)
    return items

dangerous()  # [1]
dangerous()  # [1, 1]  -- Same list!
```

Our compiled code avoids this gotcha by creating fresh containers each call. The default value in IR represents what to create, not a shared object.

---

# Part 2: C Background for Python Developers

## Arrays: Contiguous Memory Blocks

Unlike Python lists, C arrays are fixed-size contiguous memory:

```c
int nums[3] = {10, 20, 30};
```

**Memory layout:**

```
Address:   0x1000    0x1004    0x1008
          +---------+---------+---------+
Values:   |   10    |   20    |   30    |
          +---------+---------+---------+
Index:        [0]       [1]       [2]
```

Array access is simple pointer arithmetic: `nums[i]` means "go to start address, add `i * sizeof(int)`, read value."

### Arrays and Pointers

In C, arrays decay to pointers when passed to functions:

```c
void print_array(int *arr, size_t len) {
    for (size_t i = 0; i < len; i++) {
        printf("%d\n", arr[i]);
    }
}

int nums[3] = {10, 20, 30};
print_array(nums, 3);  // nums decays to &nums[0]
```

MicroPython passes arguments the same way: as an array of `mp_obj_t` plus a count.

## The Ternary Operator: Inline Conditionals

The **ternary operator** is C's inline if-else:

```c
condition ? value_if_true : value_if_false
```

Examples:

```c
int max = (a > b) ? a : b;           // max of two values
int abs_x = (x < 0) ? -x : x;        // absolute value
char *msg = success ? "OK" : "ERR";  // select string
```

The ternary is an **expression** that returns a value, unlike `if` which is a statement. This matters because we can use it in assignments:

```c
// With ternary - one assignment
mp_int_t port = (n_args > 1) ? mp_obj_get_int(args[1]) : 8080;

// Without ternary - multiple statements
mp_int_t port;
if (n_args > 1) {
    port = mp_obj_get_int(args[1]);
} else {
    port = 8080;
}
```

### Why Ternary for Defaults

We use ternary operators because:
1. Each parameter initialization is a single statement
2. Code is more readable than nested if-else
3. Generated C is compact

## MicroPython Function Macros

MicroPython provides macros to define C functions callable from Python:

### Fixed Argument Macros

```c
// Exactly N arguments - MicroPython validates before calling
MP_DEFINE_CONST_FUN_OBJ_0(name_obj, func);  // func()
MP_DEFINE_CONST_FUN_OBJ_1(name_obj, func);  // func(a)
MP_DEFINE_CONST_FUN_OBJ_2(name_obj, func);  // func(a, b)
MP_DEFINE_CONST_FUN_OBJ_3(name_obj, func);  // func(a, b, c)
```

Each generates a function object with built-in argument count validation.

### Variable Argument Macros

```c
// Between min and max arguments
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(name_obj, min, max, func);
```

The function signature changes to receive an array:

```c
static mp_obj_t func(size_t n_args, const mp_obj_t *args) {
    // n_args: how many arguments were actually passed
    // args: array of argument values
    // args[0], args[1], ... up to args[n_args-1]
}
```

MicroPython validates `min <= n_args <= max` before calling. If validation fails, it raises `TypeError` automatically.

### Visual: Argument Passing

When Python calls `connect("localhost", 443)`:

```
Python call:  connect("localhost", 443)
                      |
MicroPython validates: n_args=2, min=1, max=3  [OK]
                      |
C function receives:
  n_args = 2
  args -> +-------------------+-------------------+
          | "localhost" (obj) |    443 (obj)      |
          +-------------------+-------------------+
               args[0]              args[1]
```

## Type Conversion Functions

MicroPython provides functions to extract C types from `mp_obj_t`:

| Python Type | C Type | Extraction Function |
|-------------|--------|---------------------|
| `int` | `mp_int_t` | `mp_obj_get_int(obj)` |
| `float` | `mp_float_t` | `mp_obj_get_float(obj)` |
| `bool` | `bool` | `mp_obj_is_true(obj)` |
| `str` | `const char *` | `mp_obj_str_get_str(obj)` |

For object types (str, list, dict), we can keep them as `mp_obj_t` without conversion.

---

# Part 3: Implementation

## The Challenge: Python Flexibility vs C Rigidity

In Python, these calls are all valid:

```python
def connect(host: str, port: int = 8080, timeout: int = 30) -> bool:
    return True

connect("localhost")           # port=8080, timeout=30
connect("localhost", 443)      # timeout=30  
connect("localhost", 443, 60)  # all explicit
```

But there's no `MP_DEFINE_CONST_FUN_OBJ_1_TO_3` for "1 required, 2 optional."

## The Solution: VAR_BETWEEN + Conditional Extraction

We generate:

```c
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(connect_obj, 1, 3, connect);
```

And inside the function, conditional extraction:

```c
static mp_obj_t module_connect(size_t n_args, const mp_obj_t *args) {
    // Required argument - always present (validated by macro)
    mp_obj_t host = args[0];
    
    // Optional arguments - check n_args before accessing
    mp_int_t port = (n_args > 1) ? mp_obj_get_int(args[1]) : 8080;
    mp_int_t timeout = (n_args > 2) ? mp_obj_get_int(args[2]) : 30;
    
    // Function body...
    return mp_const_true;
}
```

### Visualizing Argument Extraction

```
Call: connect("localhost")        Call: connect("localhost", 443)
      n_args = 1                        n_args = 2

args: +-------------+              args: +-------------+-------------+
      | "localhost" |                    | "localhost" |     443     |
      +-------------+                    +-------------+-------------+
           [0]                                [0]            [1]

Extraction:                         Extraction:
  host = args[0]  [OK]                host = args[0]  [OK]
  n_args > 1? NO -> port = 8080       n_args > 1? YES -> port = args[1]
  n_args > 2? NO -> timeout = 30      n_args > 2? NO -> timeout = 30
```

## IR Representation

We track defaults in the IR:

```python
@dataclass
class DefaultArg:
    value: int | float | bool | str | None
    c_expr: str  # Pre-computed C expression

# Example for port=8080
DefaultArg(value=8080, c_expr="8080")

# Example for greeting="Hello"
DefaultArg(value="Hello", c_expr='mp_obj_new_str("Hello", 5)')
```

The `c_expr` field lets us emit different C code for different types:

| Python Default | `c_expr` |
|---------------|----------|
| `8080` | `"8080"` |
| `1.5` | `"1.5"` |
| `True` | `"true"` |
| `"Hello"` | `'mp_obj_new_str("Hello", 5)'` |
| `None` | `"mp_const_none"` |
| `[]` | `"mp_obj_new_list(0, NULL)"` |

## Code Emission Patterns

### Integer/Float with Default

```python
def scale(value: int, factor: int = 2) -> int:
    return value * factor
```

```c
mp_int_t factor = (n_args > 1) ? mp_obj_get_int(args[1]) : 2;
```

### Boolean with Default

```python
def log(msg: str, verbose: bool = False) -> None:
    pass
```

```c
bool verbose = (n_args > 1) ? mp_obj_is_true(args[1]) : false;
```

### String with Default

```python
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}"
```

```c
mp_obj_t greeting = (n_args > 1) ? args[1] : mp_obj_new_str("Hello", 5);
```

### Container Defaults

```python
def append_to(items: list = []) -> list:
    return items
```

```c
mp_obj_t items = (n_args > 0) ? args[0] : mp_obj_new_list(0, NULL);
```

**Note**: This actually **improves** on Python! Each call gets a fresh list if none is provided, avoiding the mutable default gotcha.

## Complete Generated Code Example

For this Python function:

```python
def greet(name: str, greeting: str = "Hello") -> str:
    return greeting
```

We generate:

```c
static mp_obj_t module_greet(size_t n_args, const mp_obj_t *args) {
    // Required argument
    mp_obj_t name = args[0];
    
    // Optional argument with default
    mp_obj_t greeting = (n_args > 1) ? args[1] : mp_obj_new_str("Hello", 5);
    
    // Function body
    return greeting;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(module_greet_obj, 1, 2, module_greet);
```

### Macro Breakdown

```c
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(module_greet_obj, 1, 2, module_greet);
//                                  ^                 ^  ^  ^
//                                  |                 |  |  +-- C function name
//                                  |                 |  +-- max args (all params)
//                                  |                 +-- min args (required only)
//                                  +-- Python-visible function object
```

The macro ensures:
- `n_args < 1` -> MicroPython raises `TypeError: function missing required argument`
- `n_args > 2` -> MicroPython raises `TypeError: function takes at most 2 arguments`
- `1 <= n_args <= 2` -> Our function runs

## Edge Cases

### All Arguments Have Defaults

```python
def config(a: int = 1, b: int = 2) -> int:
    return a + b
```

Generates `min_args=0`:

```c
static mp_obj_t module_config(size_t n_args, const mp_obj_t *args) {
    mp_int_t a = (n_args > 0) ? mp_obj_get_int(args[0]) : 1;
    mp_int_t b = (n_args > 1) ? mp_obj_get_int(args[1]) : 2;
    return mp_obj_new_int((a + b));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(module_config_obj, 0, 2, module_config);
```

### Mixed Required and Optional

```python
def connect(host: str, port: int = 8080, timeout: int = 30) -> bool:
    return True
```

```c
static mp_obj_t module_connect(size_t n_args, const mp_obj_t *args) {
    mp_obj_t host = args[0];  // Always present - required
    mp_int_t port = (n_args > 1) ? mp_obj_get_int(args[1]) : 8080;
    mp_int_t timeout = (n_args > 2) ? mp_obj_get_int(args[2]) : 30;
    return mp_const_true;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(module_connect_obj, 1, 3, module_connect);
```

## Performance Consideration

The ternary checks add minimal overhead:

```c
mp_int_t port = (n_args > 1) ? mp_obj_get_int(args[1]) : 8080;
//              +-- Single integer comparison
```

This is one CPU comparison instruction per optional argument. For hot paths, users can pass all arguments explicitly to skip the conditionals.

The real win is **API ergonomics**. Functions like `connect(host, port=8080, timeout=30)` are natural to write and use, matching Python's expectations.

## Testing

Unit tests verify the generated patterns:

```python
def test_default_argument_int(self):
    source = '''
def scale(value: int, factor: int = 2) -> int:
    return value * factor
'''
    result = compile_source(source, "test")
    assert "VAR_BETWEEN" in result
    assert "(n_args > 1)" in result
    assert ": 2" in result  # default value
```

Device tests verify actual execution on ESP32:

```python
test(
    "scale_with_default",
    "import m; print(m.scale(5))",
    "10",  # 5 * 2 (default)
)
test(
    "scale_with_explicit",
    "import m; print(m.scale(5, 3))",
    "15",  # 5 * 3 (explicit)
)
```

---

## What's Next

Default arguments handle "fewer arguments than parameters." But what about "more arguments than parameters"? That's where `*args` and `**kwargs` come in — variadic functions that accept unlimited positional or keyword arguments.

---

*Default arguments bridge Python's flexible calling conventions with C's rigid function signatures. The VAR_BETWEEN macro handles argument count validation, while conditional extraction with ternary operators fills in defaults at runtime.*
