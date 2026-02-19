# Variadic Functions: *args and **kwargs in C

*Teaching MicroPython to accept "as many arguments as you want."*

---

Python's `*args` and `**kwargs` let functions accept unlimited arguments. But C functions have fixed signatures determined at compile time. This post explores how we bridged that gap, implementing variadic function support using MicroPython's VAR and KW macros.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) — How variadic signatures flow through the compilation pipeline
2. [C Background](#part-2-c-background-for-python-developers) — Pointer arithmetic, hash tables, and MicroPython's variadic macros
3. [Implementation](#part-3-implementation) — How we built *args and **kwargs support

---

# Part 1: Compiler Theory

## Variadic Functions in the Compilation Pipeline

Variadic functions require special handling at every compilation stage:

```
+------------------+    +------------------+    +------------------+    +------------------+
|  Python Source   | -> |       AST        | -> |       IR         | -> |     C Code       |
|                  |    |                  |    |                  |    |                  |
| def f(*args)     |    | FunctionDef      |    | FuncIR with      |    | VAR/KW macro     |
| def g(**kwargs)  |    | vararg, kwarg    |    | star_args field  |    | + tuple/dict     |
+------------------+    +------------------+    +------------------+    +------------------+
```

### Phase 1: AST Extraction

Python's `ast` module stores variadic parameters separately from regular parameters:

```python
# Python source
def log(level: str, *messages, **options):
    pass
```

```python
# AST representation (simplified)
FunctionDef(
    name='log',
    args=arguments(
        args=[arg(arg='level', annotation=Name(id='str'))],
        vararg=arg(arg='messages'),  # *args
        kwarg=arg(arg='options'),    # **kwargs
    )
)
```

Key insight: `vararg` and `kwarg` are separate fields, not part of the `args` list.

### Phase 2: IR Building

We capture variadic information in the IR:

```python
class ArgKind(Enum):
    ARG_POS = 0      # Required positional: def f(a)
    ARG_OPT = 1      # Optional positional: def f(a=1)
    ARG_STAR = 2     # Star args: def f(*args)
    ARG_STAR2 = 3    # Star kwargs: def f(**kwargs)

@dataclass
class FuncIR:
    name: str
    c_name: str
    params: list[ParamIR]
    star_args: ParamIR | None    # *args
    star_kwargs: ParamIR | None  # **kwargs
    min_args: int                # Required positional count
```

### Phase 3: Code Emission

The emitter generates:
1. The appropriate macro (VAR or KW)
2. Container construction for star parameters
3. Correct parameter name mapping

## Why Variadic Functions Are Different

Regular parameters have a 1:1 mapping: Python parameter -> C variable. Variadic parameters break this:

| Pattern | Python | C Representation |
|---------|--------|------------------|
| `def f(a)` | `a` is one value | `a` is one variable |
| `def f(*args)` | `args` is a tuple | Need to BUILD a tuple |
| `def f(**kwargs)` | `kwargs` is a dict | Need to BUILD a dict |

The compiler must generate code that **constructs** the expected Python containers at runtime.

## The Argument Kinds Hierarchy

Understanding how Python handles arguments helps us generate correct C:

```
def example(a, b=10, *args, **kwargs):
            ^  ^      ^       ^
            |  |      |       +-- Collects keyword arguments into dict
            |  |      +-- Collects extra positional args into tuple
            |  +-- Optional (has default)
            +-- Required positional

Call: example(1, 2, 3, 4, x=5, y=6)
                      ^  ^  ^   ^
                      |  |  |   +-- Goes to kwargs["y"]
                      |  |  +-- Goes to kwargs["x"]
                      |  +-- Goes to args[1]
                      +-- Goes to args[0] (after a, b consumed)
```

The compiler must emit code that:
1. Extracts required/optional positional args first
2. Builds a tuple from remaining positional args
3. Builds a dict from keyword args

---

# Part 2: C Background for Python Developers

## Pointer Arithmetic: Navigating Arrays

In C, pointers support arithmetic operations:

```c
int nums[] = {10, 20, 30, 40, 50};
int *p = nums;      // p points to nums[0]

p + 1               // Points to nums[1] (address + sizeof(int))
p + 2               // Points to nums[2]
*(p + 3)            // Value at nums[3] = 40
```

**Visual:**

```
nums:     +----+----+----+----+----+
          | 10 | 20 | 30 | 40 | 50 |
          +----+----+----+----+----+
Address:  p    p+1  p+2  p+3  p+4
```

### Why This Matters

When we have `def f(a, b, *args)` and receive 5 arguments:

```c
const mp_obj_t *args = ...;  // Array of all arguments
// args[0] = a, args[1] = b, args[2..4] = *args

// To get just the *args portion:
mp_obj_t *star_args_start = args + 2;  // Skip first 2
size_t star_args_count = n_args - 2;   // Remaining count
```

Pointer arithmetic lets us "slice" the array without copying.

## Hash Tables: MicroPython's mp_map_t

Python dicts and keyword arguments use hash tables. MicroPython implements these with `mp_map_t`:

```c
typedef struct _mp_map_t {
    size_t alloc;           // Allocated slots
    size_t used;            // Filled slots
    mp_map_elem_t *table;   // Array of key-value pairs
} mp_map_t;

typedef struct _mp_map_elem_t {
    mp_obj_t key;
    mp_obj_t value;
} mp_map_elem_t;
```

**Visual: Hash table with 4 slots, 2 used:**

```
mp_map_t:
+-------+------+-----------------+
| alloc | used | table           |
|   4   |   2  | ----+           |
+-------+------+-----|-----------+
                     v
                +--------+--------+--------+--------+
table:          | "x": 1 | (empty)| "y": 2 | (empty)|
                +--------+--------+--------+--------+
                   [0]      [1]      [2]      [3]
```

### Iterating a Hash Table

Hash tables aren't contiguous — we must check each slot:

```c
for (size_t i = 0; i < kw_args->alloc; i++) {
    if (mp_map_slot_is_filled(kw_args, i)) {
        // This slot has data
        mp_obj_t key = kw_args->table[i].key;
        mp_obj_t value = kw_args->table[i].value;
    }
}
```

## MicroPython's Variadic Macros

### MP_DEFINE_CONST_FUN_OBJ_VAR — Unlimited Positional

```c
MP_DEFINE_CONST_FUN_OBJ_VAR(name_obj, min_args, func);

static mp_obj_t func(size_t n_args, const mp_obj_t *args) {
    // n_args: actual argument count
    // args: array of all arguments
}
```

**Visual: Calling `sum_all(1, 2, 3)`:**

```
Python: sum_all(1, 2, 3)
                 |
        MicroPython validates: n_args >= min_args
                 |
C receives:
  n_args = 3
  args -> +-----+-----+-----+
          |  1  |  2  |  3  |
          +-----+-----+-----+
           [0]   [1]   [2]
```

### MP_DEFINE_CONST_FUN_OBJ_KW — Positional + Keywords

```c
MP_DEFINE_CONST_FUN_OBJ_KW(name_obj, min_positional, func);

static mp_obj_t func(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    // n_args: positional argument count
    // pos_args: array of positional arguments
    // kw_args: hash table of keyword arguments (may be NULL)
}
```

**Visual: Calling `config("host", timeout=30, debug=True)`:**

```
Python: config("host", timeout=30, debug=True)
                 |
C receives:
  n_args = 1
  pos_args -> +--------+
              | "host" |
              +--------+
                 [0]
  
  kw_args -> mp_map_t with:
             table[i] = {"timeout": 30}
             table[j] = {"debug": True}
```

## Tuple and Dict Construction

MicroPython provides functions to create containers:

### Creating Tuples

```c
// Create tuple from array
mp_obj_t tuple = mp_obj_new_tuple(count, array);

// Example: Make tuple from args[2] onwards
mp_obj_t star_args = mp_obj_new_tuple(
    n_args - 2,      // count
    args + 2         // pointer to first element
);
```

### Creating Dicts

```c
// Create empty dict with size hint
mp_obj_t dict = mp_obj_new_dict(initial_size);

// Add entries
mp_obj_dict_store(dict, key, value);
```

---

# Part 3: Implementation

## The Python Patterns We Support

```python
def log(*messages):
    for msg in messages:
        print(msg)

def configure(**options):
    for key, value in options.items():
        print(f"{key}={value}")

def call(name, *args, **kwargs):
    # name is required, everything else is optional
    pass
```

These patterns appear everywhere: logging, configuration, decorators, wrappers.

## IR Representation

We track star parameters in the IR:

```python
@dataclass
class ParamIR:
    name: str
    c_type: CType
    kind: ArgKind  # ARG_STAR or ARG_STAR2
    default: DefaultArg | None = None

@dataclass
class FuncIR:
    # ... existing fields ...
    star_args: ParamIR | None = None
    star_kwargs: ParamIR | None = None
```

The IR builder extracts these from Python's AST:

```python
def _parse_star_args(self, args: ast.arguments) -> tuple[ParamIR | None, ParamIR | None]:
    star_args = None
    star_kwargs = None
    
    if args.vararg:  # *args
        star_args = ParamIR(
            name=args.vararg.arg,
            c_type=CType.MP_OBJ_T,
            kind=ArgKind.ARG_STAR,
        )
    
    if args.kwarg:  # **kwargs
        star_kwargs = ParamIR(
            name=args.kwarg.arg,
            c_type=CType.MP_OBJ_T,
            kind=ArgKind.ARG_STAR2,
        )
    
    return star_args, star_kwargs
```

## Generating *args

For `def sum_all(*numbers) -> int`:

```c
static mp_obj_t module_sum_all(size_t n_args, const mp_obj_t *args) {
    // Build tuple from all arguments
    mp_obj_t _star_numbers = mp_obj_new_tuple(n_args, args);
    
    // Function body can iterate _star_numbers as a normal tuple
    mp_int_t total = 0;
    mp_obj_t x;
    mp_obj_iter_buf_t iter_buf;
    mp_obj_t iter = mp_getiter(_star_numbers, &iter_buf);
    while ((x = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(module_sum_all_obj, 0, module_sum_all);
```

**Visualizing the transformation:**

```
Python call: sum_all(10, 20, 30)

C function receives:
  n_args = 3
  args -> +----+----+----+
          | 10 | 20 | 30 |
          +----+----+----+

After mp_obj_new_tuple(n_args, args):
  _star_numbers -> (10, 20, 30)  # Python tuple object
```

## Generating **kwargs

For `def configure(**options) -> dict`:

```c
static mp_obj_t module_configure(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    // Build dict from keyword arguments
    mp_obj_t _star_options = mp_obj_new_dict(kw_args ? kw_args->used : 0);
    if (kw_args) {
        for (size_t i = 0; i < kw_args->alloc; i++) {
            if (mp_map_slot_is_filled(kw_args, i)) {
                mp_obj_dict_store(_star_options, 
                                  kw_args->table[i].key, 
                                  kw_args->table[i].value);
            }
        }
    }
    
    // Function body uses _star_options as a normal dict
    return _star_options;
}
MP_DEFINE_CONST_FUN_OBJ_KW(module_configure_obj, 0, module_configure);
```

**Visualizing the transformation:**

```
Python call: configure(debug=True, timeout=30)

C function receives:
  kw_args -> mp_map_t:
    table[0] = {key: "debug", value: True}
    table[3] = {key: "timeout", value: 30}
    (other slots empty)

After iteration:
  _star_options -> {"debug": True, "timeout": 30}  # Python dict object
```

## Combined: Positional + *args + **kwargs

The most complex case: `def call(name: str, *args, **kwargs) -> dict`:

```c
static mp_obj_t module_call(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    // Required positional argument
    mp_obj_t name = pos_args[0];
    
    // *args: tuple from remaining positional arguments (skip the first one)
    mp_obj_t _star_args = mp_obj_new_tuple(
        n_args > 1 ? n_args - 1 : 0,      // count
        n_args > 1 ? pos_args + 1 : NULL  // start pointer (uses pointer arithmetic!)
    );
    
    // **kwargs: dict from keyword arguments
    mp_obj_t _star_kwargs = mp_obj_new_dict(kw_args ? kw_args->used : 0);
    if (kw_args) {
        for (size_t i = 0; i < kw_args->alloc; i++) {
            if (mp_map_slot_is_filled(kw_args, i)) {
                mp_obj_dict_store(_star_kwargs, 
                                  kw_args->table[i].key, 
                                  kw_args->table[i].value);
            }
        }
    }
    
    // Function body...
}
MP_DEFINE_CONST_FUN_OBJ_KW(module_call_obj, 1, module_call);  // 1 required positional
```

**Complete example flow:**

```
Python call: call("test", 1, 2, 3, x=10, y=20)

C function receives:
  n_args = 4 (positional only)
  pos_args -> +--------+-----+-----+-----+
              | "test" |  1  |  2  |  3  |
              +--------+-----+-----+-----+
                 [0]     [1]   [2]   [3]
  
  kw_args -> {"x": 10, "y": 20}

After extraction:
  name = "test"
  _star_args = (1, 2, 3)           # pos_args + 1, count = 3
  _star_kwargs = {"x": 10, "y": 20}
```

## The Name Collision Problem

What if someone writes `def f(*args)`? The Python parameter is named `args`, but MicroPython's C signature also has `args`:

```c
static mp_obj_t func(size_t n_args, const mp_obj_t *args) {
    mp_obj_t args = mp_obj_new_tuple(...);  // ERROR: redefinition!
}
```

We solve this by prefixing star parameter names with `_star_`:

```c
static mp_obj_t func(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_args = mp_obj_new_tuple(n_args, args);  // OK!
}
```

The IR builder tracks this mapping so references to `args` in the Python function body correctly resolve to `_star_args` in the generated C.

## Macro Selection Logic

The emitter chooses the right macro based on function signature:

```python
def _select_macro(self) -> str:
    if self.func_ir.star_kwargs:
        # **kwargs needs KW macro (also handles *args)
        return "MP_DEFINE_CONST_FUN_OBJ_KW"
    
    if self.func_ir.star_args:
        # *args only uses VAR macro
        return "MP_DEFINE_CONST_FUN_OBJ_VAR"
    
    if self.func_ir.defaults:
        # Has defaults but no star params
        return "MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN"
    
    # Fixed argument count
    return f"MP_DEFINE_CONST_FUN_OBJ_{len(self.func_ir.params)}"
```

### Macro Selection Table

| Function Signature | Macro |
|-------------------|-------|
| `def f(a, b)` | `OBJ_2` |
| `def f(a, b=1)` | `VAR_BETWEEN` |
| `def f(*args)` | `VAR` |
| `def f(**kwargs)` | `KW` |
| `def f(a, *args)` | `VAR` |
| `def f(a, **kwargs)` | `KW` |
| `def f(*args, **kwargs)` | `KW` |

## Performance Considerations

Creating containers for star arguments has overhead:

| Operation | Cost |
|-----------|------|
| `mp_obj_new_tuple(n, arr)` | Allocate + copy n pointers |
| `mp_obj_new_dict(n)` | Allocate hash table |
| `mp_obj_dict_store` | Hash key + insert |

For performance-critical code, users can refactor to avoid star args:

```python
# Slower: creates tuple each call
def sum_all(*numbers):
    return sum(numbers)

# Faster: no container allocation
def sum_list(numbers: list):
    return sum(numbers)
```

But for most use cases — logging, configuration, wrappers — the flexibility is worth the cost.

## Testing

Unit tests verify the generated patterns:

```python
def test_star_args_only(self):
    source = '''
def sum_all(*numbers) -> int:
    total = 0
    for n in numbers:
        total += n
    return total
'''
    result = compile_source(source, "test")
    assert "MP_DEFINE_CONST_FUN_OBJ_VAR" in result
    assert "_star_numbers" in result
    assert "mp_obj_new_tuple" in result
```

Device tests verify actual execution on ESP32:

```python
test(
    "sum_all_star_args",
    "import m; print(m.sum_all(1, 2, 3, 4, 5))",
    "15",
)
test(
    "configure_kwargs",
    "import m; d = m.configure(debug=True, timeout=30); print(d['debug'])",
    "True",
)
```

## Complete Example: Full Signature

Combining everything from this post and the previous one:

```python
def flexible(required: int, optional: int = 10, *args, **kwargs) -> dict:
    return {
        "required": required,
        "optional": optional,
        "args": args,
        "kwargs": kwargs
    }
```

This compiles to C that:

1. Uses `MP_DEFINE_CONST_FUN_OBJ_KW` (because of **kwargs)
2. Validates at least 1 argument (MicroPython runtime check)
3. Extracts `required` from `pos_args[0]`
4. Extracts `optional` from `pos_args[1]` or uses default `10`
5. Builds `_star_args` tuple from remaining positional args (pointer arithmetic)
6. Builds `_star_kwargs` dict from `kw_args` hash table
7. Executes the function body with all values available

Python's full function signature flexibility, compiled to efficient C.

---

## Conclusion

Variadic functions required us to:

1. **Track star parameters in IR**: Separate fields for `*args` and `**kwargs`
2. **Generate container construction**: Build tuples and dicts at runtime
3. **Handle naming conflicts**: Prefix star params with `_star_`
4. **Select correct macros**: VAR for positional-only, KW for keywords

The pattern of extracting information during IR building and generating appropriate C during emission applies here just as it did for default arguments. Each Python feature maps to specific MicroPython C API calls.

---

*Variadic functions complete our function signature support. From fixed arguments to defaults to unlimited *args/**kwargs — Python functions compile naturally to MicroPython.*
