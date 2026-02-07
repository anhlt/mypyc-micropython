# Function Calling Conventions

This document explains how Python function calls are translated to C, including argument passing, return values, and the various function object types.

## Table of Contents

- [MicroPython Function Object Types](#micropython-function-object-types)
- [Argument Passing Conventions](#argument-passing-conventions)
- [Return Value Boxing](#return-value-boxing)
- [Recursion Handling](#recursion-handling)
- [Generated Code Patterns](#generated-code-patterns)

## MicroPython Function Object Types

MicroPython defines several function wrapper macros depending on argument count:

```c
// 0 arguments
MP_DEFINE_CONST_FUN_OBJ_0(name_obj, func);

// 1 argument
MP_DEFINE_CONST_FUN_OBJ_1(name_obj, func);

// 2 arguments
MP_DEFINE_CONST_FUN_OBJ_2(name_obj, func);

// 3 arguments
MP_DEFINE_CONST_FUN_OBJ_3(name_obj, func);

// Variable arguments (min to max)
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(name_obj, min, max, func);

// Variable arguments (min to unlimited)
MP_DEFINE_CONST_FUN_OBJ_VAR(name_obj, min, func);

// Keyword arguments
MP_DEFINE_CONST_FUN_OBJ_KW(name_obj, min_pos, func);
```

### Function Signatures

```
┌─────────────────────────────────────────────────────────────┐
│                  FUNCTION SIGNATURE PATTERNS                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  OBJ_0:  mp_obj_t func(void)                               │
│                                                             │
│  OBJ_1:  mp_obj_t func(mp_obj_t arg0)                      │
│                                                             │
│  OBJ_2:  mp_obj_t func(mp_obj_t arg0, mp_obj_t arg1)       │
│                                                             │
│  OBJ_3:  mp_obj_t func(mp_obj_t arg0, mp_obj_t arg1,       │
│                        mp_obj_t arg2)                       │
│                                                             │
│  VAR:    mp_obj_t func(size_t n_args, const mp_obj_t *args)│
│                                                             │
│  KW:     mp_obj_t func(size_t n_args, const mp_obj_t *args,│
│                        mp_map_t *kw_args)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Argument Passing Conventions

### Fixed Arguments (0-3)

For 0-3 arguments, each is passed directly:

**Python:**
```python
def add(a: int, b: int) -> int:
    return a + b
```

**Generated C:**
```c
static mp_obj_t module_add(mp_obj_t a_obj, mp_obj_t b_obj) {
    // Unbox arguments
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    
    // Compute
    mp_int_t result = a + b;
    
    // Box and return
    return mp_obj_new_int(result);
}
MP_DEFINE_CONST_FUN_OBJ_2(module_add_obj, module_add);
```

### Variable Arguments (4+)

For 4 or more arguments, use array-based passing:

**Python:**
```python
def sum4(a: int, b: int, c: int, d: int) -> int:
    return a + b + c + d
```

**Generated C:**
```c
static mp_obj_t module_sum4(size_t n_args, const mp_obj_t *args) {
    // Unbox from array
    mp_int_t a = mp_obj_get_int(args[0]);
    mp_int_t b = mp_obj_get_int(args[1]);
    mp_int_t c = mp_obj_get_int(args[2]);
    mp_int_t d = mp_obj_get_int(args[3]);
    
    return mp_obj_new_int(a + b + c + d);
}
// min=4, max=4 (exact)
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(module_sum4_obj, 4, 4, module_sum4);
```

### Call Site Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                   FUNCTION CALL FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Python: result = add(10, 20)                              │
│                                                             │
│  1. CALLER PREPARES ARGUMENTS                              │
│     ┌────────────────────────────────────────────────┐     │
│     │ a_obj = mp_obj_new_int(10)   // Box 10        │     │
│     │ b_obj = mp_obj_new_int(20)   // Box 20        │     │
│     └────────────────────────────────────────────────┘     │
│                         │                                   │
│                         ▼                                   │
│  2. CALL FUNCTION                                          │
│     ┌────────────────────────────────────────────────┐     │
│     │ ret = module_add(a_obj, b_obj)                │     │
│     └────────────────────────────────────────────────┘     │
│                         │                                   │
│                         ▼                                   │
│  3. FUNCTION UNBOXES                                       │
│     ┌────────────────────────────────────────────────┐     │
│     │ a = mp_obj_get_int(a_obj)    // a = 10        │     │
│     │ b = mp_obj_get_int(b_obj)    // b = 20        │     │
│     └────────────────────────────────────────────────┘     │
│                         │                                   │
│                         ▼                                   │
│  4. COMPUTE (native C)                                     │
│     ┌────────────────────────────────────────────────┐     │
│     │ result = a + b               // result = 30   │     │
│     └────────────────────────────────────────────────┘     │
│                         │                                   │
│                         ▼                                   │
│  5. FUNCTION BOXES RETURN VALUE                            │
│     ┌────────────────────────────────────────────────┐     │
│     │ return mp_obj_new_int(result) // Box 30       │     │
│     └────────────────────────────────────────────────┘     │
│                         │                                   │
│                         ▼                                   │
│  6. CALLER RECEIVES                                        │
│     ┌────────────────────────────────────────────────┐     │
│     │ // ret is mp_obj_t containing 30              │     │
│     └────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Return Value Boxing

Different return types require different boxing:

```c
// Returning int
return mp_obj_new_int(value);

// Returning float
return mp_obj_new_float(value);

// Returning bool
return value ? mp_const_true : mp_const_false;

// Returning None
return mp_const_none;

// Returning string
return mp_obj_new_str(str, len);

// Returning list (already boxed)
return list_obj;
```

### Return Type Inference

Our compiler infers return type from the function annotation:

```c
// Python: def foo() -> int
// Return int → need to box
return mp_obj_new_int(result);

// Python: def bar() -> bool  
// Return bool → use constants
return condition ? mp_const_true : mp_const_false;

// Python: def baz() -> list
// Return list → already boxed
return result;  // result is mp_obj_t
```

## Recursion Handling

Recursive functions call themselves through the boxed interface:

**Python:**
```python
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

**Generated C:**
```c
static mp_obj_t module_factorial(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    
    if (n <= 1) {
        return mp_obj_new_int(1);
    }
    
    // Recursive call: must box arg and unbox result
    mp_obj_t rec_result = module_factorial(mp_obj_new_int(n - 1));
    mp_int_t rec_value = mp_obj_get_int(rec_result);
    
    return mp_obj_new_int(n * rec_value);
}
```

### Recursion Overhead Analysis

```
┌─────────────────────────────────────────────────────────────┐
│                RECURSION BOXING OVERHEAD                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  factorial(5) call tree:                                    │
│                                                             │
│  factorial(5)                                               │
│    │ box(4) → factorial(4)                                 │
│    │   │ box(3) → factorial(3)                             │
│    │   │   │ box(2) → factorial(2)                         │
│    │   │   │   │ box(1) → factorial(1)                     │
│    │   │   │   │   └─ return box(1)                        │
│    │   │   │   └─ unbox, compute 2*1, return box(2)        │
│    │   │   └─ unbox, compute 3*2, return box(6)            │
│    │   └─ unbox, compute 4*6, return box(24)               │
│    └─ unbox, compute 5*24, return box(120)                 │
│                                                             │
│  Boxing operations: 4 box + 4 unbox = 8 per recursion      │
│  For factorial(n): 8 × n boxing operations                  │
│                                                             │
│  Optimization opportunity: Tail call elimination           │
│  (Not currently implemented)                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Generated Code Patterns

### Pattern 1: Simple Function

```python
def double(x: int) -> int:
    return x * 2
```

```c
static mp_obj_t module_double(mp_obj_t x_obj) {
    mp_int_t x = mp_obj_get_int(x_obj);
    return mp_obj_new_int(x * 2);
}
MP_DEFINE_CONST_FUN_OBJ_1(module_double_obj, module_double);
```

### Pattern 2: Multiple Returns (Branching)

```python
def abs_val(x: int) -> int:
    if x < 0:
        return -x
    return x
```

```c
static mp_obj_t module_abs_val(mp_obj_t x_obj) {
    mp_int_t x = mp_obj_get_int(x_obj);
    
    if (x < 0) {
        return mp_obj_new_int(-x);
    }
    return mp_obj_new_int(x);
}
MP_DEFINE_CONST_FUN_OBJ_1(module_abs_val_obj, module_abs_val);
```

### Pattern 3: Loop with Accumulator

```python
def sum_to(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i
    return total
```

```c
static mp_obj_t module_sum_to(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    
    mp_int_t total = 0;
    mp_int_t _end = n;
    for (mp_int_t i = 0; i < _end; i++) {
        total += i;
    }
    
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(module_sum_to_obj, module_sum_to);
```

### Pattern 4: Function Calling Function

```python
def helper(x: int) -> int:
    return x * x

def sum_squares(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += helper(i)
    return total
```

```c
static mp_obj_t module_helper(mp_obj_t x_obj) {
    mp_int_t x = mp_obj_get_int(x_obj);
    return mp_obj_new_int(x * x);
}
MP_DEFINE_CONST_FUN_OBJ_1(module_helper_obj, module_helper);

static mp_obj_t module_sum_squares(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    
    mp_int_t total = 0;
    for (mp_int_t i = 0; i < n; i++) {
        // Call helper through boxed interface
        mp_obj_t ret = module_helper(mp_obj_new_int(i));
        total += mp_obj_get_int(ret);
    }
    
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(module_sum_squares_obj, module_sum_squares);
```

## Module Registration

All functions must be registered in the module table:

```c
// Function implementations above...

// Module globals table
static const mp_rom_map_elem_t module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mymodule) },
    { MP_ROM_QSTR(MP_QSTR_double), MP_ROM_PTR(&module_double_obj) },
    { MP_ROM_QSTR(MP_QSTR_abs_val), MP_ROM_PTR(&module_abs_val_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_to), MP_ROM_PTR(&module_sum_to_obj) },
};
MP_DEFINE_CONST_DICT(module_globals, module_globals_table);

// Module definition
const mp_obj_module_t mymodule_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&module_globals,
};

// Register module
MP_REGISTER_MODULE(MP_QSTR_mymodule, mymodule_user_cmodule);
```

### Module Structure Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    MODULE STRUCTURE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MP_REGISTER_MODULE creates entry in:                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ SYSTEM MODULE TABLE                                 │   │
│  │ ├─ "sys"     → &mp_module_sys                      │   │
│  │ ├─ "gc"      → &mp_module_gc                       │   │
│  │ ├─ ...                                             │   │
│  │ └─ "mymodule" → &mymodule_user_cmodule            │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ mymodule_user_cmodule (mp_obj_module_t)             │   │
│  │ ├─ .base.type = &mp_type_module                    │   │
│  │ └─ .globals ─────────────────────────────────┐     │   │
│  └──────────────────────────────────────────────┼─────┘   │
│                                                  │          │
│                                                  ▼          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ module_globals (mp_obj_dict_t)                      │   │
│  │ ├─ "__name__" → "mymodule"                         │   │
│  │ ├─ "double"   → &module_double_obj ─────────┐      │   │
│  │ ├─ "abs_val"  → &module_abs_val_obj         │      │   │
│  │ └─ "sum_to"   → &module_sum_to_obj          │      │   │
│  └─────────────────────────────────────────────┼──────┘   │
│                                                 │           │
│                                                 ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ module_double_obj (mp_obj_fun_builtin_fixed_t)     │   │
│  │ ├─ .base.type = &mp_type_fun_builtin_1            │   │
│  │ └─ .fun = module_double (function pointer)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  When Python calls: mymodule.double(5)                     │
│  1. Look up "mymodule" → get module object                 │
│  2. Look up "double" in module.globals → get func object   │
│  3. Call func.fun(mp_obj_new_int(5))                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## See Also

- [01-type-mapping.md](01-type-mapping.md) - Type system overview
- [02-memory-layout.md](02-memory-layout.md) - Object memory layout
- [03-list-internals.md](03-list-internals.md) - List implementation
- [05-iteration-protocols.md](05-iteration-protocols.md) - For loop internals
