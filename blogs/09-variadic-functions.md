# Variadic Functions: *args and **kwargs in C

*Teaching MicroPython to accept "as many arguments as you want."*

---

Python's `*args` and `**kwargs` are powerful: functions can accept unlimited positional or keyword arguments. But C functions have fixed signatures. How do we bridge that gap?

This post explores how we implemented variadic function support, using MicroPython's VAR and KW macros to handle Python's most flexible calling patterns.

## The Python Patterns

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

These patterns appear everywhere: logging, configuration, decorators, wrappers. Any serious Python-to-C compiler needs them.

## MicroPython's Variadic Macros

MicroPython provides two macros for variadic functions:

**`MP_DEFINE_CONST_FUN_OBJ_VAR`** — Unlimited positional arguments:
```c
MP_DEFINE_CONST_FUN_OBJ_VAR(name_obj, min_args, func);

// Function signature:
static mp_obj_t func(size_t n_args, const mp_obj_t *args);
```

**`MP_DEFINE_CONST_FUN_OBJ_KW`** — Positional and keyword arguments:
```c
MP_DEFINE_CONST_FUN_OBJ_KW(name_obj, min_positional, func);

// Function signature:
static mp_obj_t func(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args);
```

The KW variant gives us a hash map (`mp_map_t`) of keyword arguments, while positional arguments come as a separate array.

## IR Representation

We extended our IR to track star parameters:

```python
class ArgKind(Enum):
    ARG_POS = 0      # Required positional: def f(a)
    ARG_OPT = 1      # Optional positional: def f(a=1)
    ARG_STAR = 2     # Star args: def f(*args)
    ARG_STAR2 = 3    # Star kwargs: def f(**kwargs)

@dataclass
class ParamIR:
    name: str
    c_type: CType
    kind: ArgKind
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

For `def sum_all(*numbers) -> int`, we generate:

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

The `mp_obj_new_tuple(n_args, args)` creates a Python tuple from the C array. The function body treats it like any other tuple.

## Generating **kwargs

For `def configure(**options) -> dict`, we generate:

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

The `mp_map_t` is MicroPython's internal hash table. We iterate its slots and copy filled entries to a Python dict.

## Combined: Positional + *args + **kwargs

The most complex case: `def call(name: str, *args, **kwargs) -> dict`:

```c
static mp_obj_t module_call(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    // Required positional argument
    mp_obj_t name = pos_args[0];
    
    // *args: tuple from remaining positional arguments (skip the first one)
    mp_obj_t _star_args = mp_obj_new_tuple(
        n_args > 1 ? n_args - 1 : 0,      // count
        n_args > 1 ? pos_args + 1 : NULL  // start pointer
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

Key details:
- The `1` in `MP_DEFINE_CONST_FUN_OBJ_KW` means 1 required positional argument
- `*args` gets remaining positional args after the required ones
- `**kwargs` gets all keyword arguments

## The Name Collision Problem

What if someone writes `def f(*args)`? The parameter is named `args`, but our C function also has a parameter called `args`:

```c
static mp_obj_t func(size_t n_args, const mp_obj_t *args) {
    mp_obj_t args = mp_obj_new_tuple(...);  // ERROR: redefinition!
}
```

We solve this by prefixing star parameter names with `_star_`:

```c
static mp_obj_t func(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_args = mp_obj_new_tuple(n_args, args);  // OK
}
```

The IR builder tracks this mapping so references to `args` in the function body correctly resolve to `_star_args` in the generated C.

## Macro Selection Logic

The emitter chooses the right macro based on what the function needs:

```python
def _emit_signature(self) -> tuple[str, str]:
    if self.func_ir.has_star_kwargs:
        # **kwargs always needs KW macro (handles *args too)
        return (
            f"static mp_obj_t {name}(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args)",
            f"MP_DEFINE_CONST_FUN_OBJ_KW({name}_obj, {min_args}, {name});"
        )
    
    if self.func_ir.has_star_args:
        # *args without **kwargs uses VAR macro
        return (
            f"static mp_obj_t {name}(size_t n_args, const mp_obj_t *args)",
            f"MP_DEFINE_CONST_FUN_OBJ_VAR({name}_obj, {min_args}, {name});"
        )
    
    # No star args - use fixed-count or VAR_BETWEEN
    # ...
```

## Why This Matters

Variadic functions enable idiomatic Python patterns:

```python
def log(level: str, *messages):
    for msg in messages:
        print(f"[{level}] {msg}")

def make_request(url: str, **options):
    timeout = options.get("timeout", 30)
    # ...

def decorator(func, *args, **kwargs):
    # Wrap and forward
    return func(*args, **kwargs)
```

Without `*args` and `**kwargs`, users would need awkward workarounds like passing lists or dicts explicitly. With them, Python code that uses these patterns can compile directly.

## Performance Notes

Creating tuple and dict objects for star arguments has overhead:
- Memory allocation for the container
- Copying argument values

For performance-critical code, users can refactor to avoid star args. But for most use cases — logging, configuration, wrappers — the flexibility is worth the cost.

## The Complete Picture

With default arguments from the previous post plus variadic functions:

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
1. Validates at least 1 argument (MicroPython runtime check)
2. Extracts `required` from `pos_args[0]`
3. Extracts `optional` from `pos_args[1]` or uses default `10`
4. Builds `_star_args` tuple from remaining positional args
5. Builds `_star_kwargs` dict from keyword args
6. Executes the function body with all values available

Python's full function signature flexibility, compiled to efficient C.

---

*Variadic functions complete our function signature support. From fixed arguments to defaults to unlimited *args/**kwargs — Python functions compile naturally to MicroPython.*
