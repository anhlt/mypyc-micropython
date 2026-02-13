# Type Mapping: Python to C

This document explains how Python types map to C types in the MicroPython runtime.

## Table of Contents

- [The Boxing Problem](#the-boxing-problem)
- [Primitive Types](#primitive-types)
- [The mp_obj_t Universal Type](#the-mp_obj_t-universal-type)
- [Small Integer Optimization](#small-integer-optimization)
- [Type Checking at Runtime](#type-checking-at-runtime)
- [Boxing and Unboxing Operations](#boxing-and-unboxing-operations)

## The Boxing Problem

Python is dynamically typed - a variable can hold any type:

```python
x = 42        # int
x = "hello"   # now it's a string
x = [1, 2, 3] # now it's a list
```

C is statically typed - every variable has a fixed type at compile time:

```c
int x = 42;
// x = "hello";  // ERROR: incompatible types
```

**The solution**: MicroPython uses a universal pointer type `mp_obj_t` that can point to any Python object. This is called "boxing" - wrapping a value in an object.

```
┌─────────────────────────────────────────────────────────────┐
│                    BOXING CONCEPT                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   Python:  x = 42                                           │
│                                                             │
│   C (unboxed):  mp_int_t x = 42;     // Fast, but rigid    │
│                                                             │
│   C (boxed):    mp_obj_t x = mp_obj_new_int(42);           │
│                 // Flexible, but slower                     │
│                                                             │
│   ┌─────────┐                                               │
│   │ mp_obj_t│──────►┌──────────────────┐                   │
│   │ (ptr)   │       │ mp_obj_int_t     │                   │
│   └─────────┘       │ ┌──────────────┐ │                   │
│                     │ │ base (type)  │ │                   │
│                     │ ├──────────────┤ │                   │
│                     │ │ value: 42    │ │                   │
│                     │ └──────────────┘ │                   │
│                     └──────────────────┘                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Primitive Types

### Integer Mapping

| Python | C Type | Size | Range |
|--------|--------|------|-------|
| `int` (small) | `mp_int_t` | Platform word | -2^30 to 2^30-1 (32-bit) |
| `int` (large) | `mpz_t` | Arbitrary | Unlimited (heap allocated) |

```c
// MicroPython defines mp_int_t based on platform
#if MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A
    typedef intptr_t mp_int_t;   // Same size as pointer
    typedef uintptr_t mp_uint_t;
#endif
```

**Why `mp_int_t` instead of `int`?**

- `int` is 32-bit even on 64-bit systems
- `mp_int_t` matches pointer size for efficient tagging
- Allows small integers to be stored without heap allocation

### Float Mapping

| Python | C Type | Precision |
|--------|--------|-----------|
| `float` | `mp_float_t` | Configurable |

```c
// MicroPython float configuration
#if MICROPY_FLOAT_IMPL == MICROPY_FLOAT_IMPL_FLOAT
    typedef float mp_float_t;    // 32-bit, saves RAM
#elif MICROPY_FLOAT_IMPL == MICROPY_FLOAT_IMPL_DOUBLE
    typedef double mp_float_t;   // 64-bit, more precision
#endif
```

**ESP32 typically uses single-precision (32-bit) floats to save memory.**

### Boolean Mapping

| Python | C Type | Values |
|--------|--------|--------|
| `bool` | `bool` or tagged pointer | `true`/`false` |

```c
// Booleans are singleton objects
#define mp_const_true  ((mp_obj_t)&mp_const_true_obj)
#define mp_const_false ((mp_obj_t)&mp_const_false_obj)

// Converting C bool to Python bool
mp_obj_t result = condition ? mp_const_true : mp_const_false;
```

### None Mapping

| Python | C | Representation |
|--------|---|----------------|
| `None` | `mp_const_none` | Singleton pointer |

```c
#define mp_const_none ((mp_obj_t)&mp_const_none_obj)

// Checking for None
if (obj == mp_const_none) {
    // handle None case
}
```

## The mp_obj_t Universal Type

`mp_obj_t` is the cornerstone of MicroPython's type system:

```c
typedef void *mp_obj_t;  // It's just a pointer!
```

But it's not always a real pointer. MicroPython uses **tagged pointers** to encode small values directly:

```
┌─────────────────────────────────────────────────────────────┐
│                mp_obj_t BIT LAYOUT (32-bit)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Small Integer (MICROPY_OBJ_REPR_A):                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ VVVVVVVV VVVVVVVV VVVVVVVV VVVVVVV1 │               │   │
│  └─────────────────────────────────────────────────────┘   │
│    └──────────── 31-bit value ──────────┘ └─ tag bit       │
│                                                             │
│  Pointer to object:                                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ PPPPPPPP PPPPPPPP PPPPPPPP PPPPPP00 │               │   │
│  └─────────────────────────────────────────────────────┘   │
│    └──────────── 30-bit pointer ────────┘ └─ tag bits      │
│                                                             │
│  Why this works:                                            │
│  - Heap-allocated objects are word-aligned (4-byte)        │
│  - Lower 2 bits of real pointers are always 00             │
│  - We can use those bits as tags!                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Object Representations

MicroPython supports multiple object representations for different platforms:

| Repr | Small Int Range | Use Case |
|------|-----------------|----------|
| `REPR_A` | ±2^30 | 32-bit systems (ESP32) |
| `REPR_B` | ±2^30 | 32-bit, qstr optimization |
| `REPR_C` | ±2^62 | 64-bit systems |
| `REPR_D` | ±2^47 | 64-bit with NaN boxing |

## Small Integer Optimization

Small integers are stored **directly in the pointer** without heap allocation:

```c
// Check if mp_obj_t is a small int
static inline bool mp_obj_is_small_int(mp_obj_t o) {
    return (((mp_int_t)(o)) & 1) != 0;
}

// Extract value from small int
static inline mp_int_t mp_obj_get_small_int(mp_obj_t o) {
    return ((mp_int_t)(o)) >> 1;
}

// Create small int from value
static inline mp_obj_t mp_obj_new_small_int(mp_int_t value) {
    return (mp_obj_t)((value << 1) | 1);
}
```

**Why this matters for performance:**

```
┌─────────────────────────────────────────────────────────────┐
│              SMALL INT vs HEAP INT COMPARISON               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Small int (x = 42):                                        │
│  ┌────────────┐                                             │
│  │ 0x00000055 │  ← Value encoded directly (42 << 1 | 1)    │
│  └────────────┘                                             │
│  Memory: 4 bytes (just the variable)                        │
│  Allocation: NONE                                           │
│                                                             │
│  Heap int (x = 2**32):                                      │
│  ┌────────────┐     ┌─────────────────────┐                │
│  │ 0x20001000 │────►│ mp_obj_int_t        │                │
│  └────────────┘     │ ├─────────────────┤ │                │
│                     │ │ base (type ptr) │ │                │
│                     │ ├─────────────────┤ │                │
│                     │ │ value (mpz_t)   │ │                │
│                     │ └─────────────────┘ │                │
│                     └─────────────────────┘                │
│  Memory: 4 + 12+ bytes                                      │
│  Allocation: malloc() call                                  │
│                                                             │
│  Performance impact:                                        │
│  - Small int: ~3 CPU cycles                                 │
│  - Heap int: ~50-200 CPU cycles (malloc overhead)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Type Checking at Runtime

Every heap-allocated object has a type pointer:

```c
// Object header structure
struct _mp_obj_base_t {
    const mp_obj_type_t *type;
};

// Get type of any object
const mp_obj_type_t *mp_obj_get_type(mp_obj_t obj) {
    if (mp_obj_is_small_int(obj)) {
        return &mp_type_int;
    } else if (mp_obj_is_qstr(obj)) {
        return &mp_type_str;
    } else {
        return ((mp_obj_base_t*)obj)->type;
    }
}
```

Type checking example:

```c
// Python: isinstance(x, int)
bool is_int = mp_obj_is_int(obj);

// Python: isinstance(x, list)  
bool is_list = mp_obj_is_type(obj, &mp_type_list);

// Python: type(x).__name__
qstr type_name = mp_obj_get_type(obj)->name;
```

## Boxing and Unboxing Operations

### Boxing (C value → Python object)

```c
// int → mp_obj_t
mp_obj_t boxed_int = mp_obj_new_int(42);

// float → mp_obj_t
mp_obj_t boxed_float = mp_obj_new_float(3.14);

// bool → mp_obj_t
mp_obj_t boxed_bool = value ? mp_const_true : mp_const_false;

// C string → mp_obj_t
mp_obj_t boxed_str = mp_obj_new_str("hello", 5);
```

### Unboxing (Python object → C value)

```c
// mp_obj_t → int
mp_int_t unboxed_int = mp_obj_get_int(obj);

// mp_obj_t → float (with int promotion)
mp_float_t unboxed_float = mp_obj_get_float(obj);

// mp_obj_t → bool
bool unboxed_bool = mp_obj_is_true(obj);

// mp_obj_t → C string
const char *unboxed_str = mp_obj_str_get_str(obj);
```

### Cost of Boxing/Unboxing

```
┌─────────────────────────────────────────────────────────────┐
│                  BOXING OVERHEAD ANALYSIS                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Operation              │ Small Int │ Heap Int │ Float     │
│  ───────────────────────┼───────────┼──────────┼───────────│
│  Box (create obj)       │ ~3 cycles │ ~100 cyc │ ~100 cyc  │
│  Unbox (extract value)  │ ~2 cycles │ ~5 cyc   │ ~5 cyc    │
│  Type check             │ ~2 cycles │ ~3 cyc   │ ~3 cyc    │
│                                                             │
│  Example: sum of 1000 integers                              │
│                                                             │
│  Pure C (unboxed):                                          │
│    for (int i = 0; i < 1000; i++) sum += arr[i];           │
│    → ~1000 cycles                                           │
│                                                             │
│  MicroPython (boxed):                                       │
│    for each element:                                        │
│      - type check (~3 cycles)                               │
│      - unbox (~2 cycles)                                    │
│      - add (~1 cycle)                                       │
│      - box result (~3 cycles)                               │
│    → ~9000 cycles (9x slower)                               │
│                                                             │
│  mypyc-compiled (unboxed loop, boxed I/O):                  │
│    - unbox input once                                       │
│    - pure C loop (~1000 cycles)                             │
│    - box output once                                        │
│    → ~1100 cycles (close to pure C!)                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**This is why mypyc compilation gives 10-30x speedups** - it eliminates boxing/unboxing inside loops.

## Practical Code Generation

Here's how our compiler translates a typed function:

**Python:**
```python
def add(a: int, b: int) -> int:
    return a + b
```

**Generated C:**
```c
static mp_obj_t module_add(mp_obj_t a_obj, mp_obj_t b_obj) {
    // Unbox inputs (Python → C)
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    
    // Pure C computation (fast!)
    mp_int_t result = a + b;
    
    // Box output (C → Python)
    return mp_obj_new_int(result);
}
```

The overhead is only at function boundaries, not inside the function body.

## See Also

- [02-memory-layout.md](02-memory-layout.md) - How objects are laid out in memory
- [03-list-internals.md](03-list-internals.md) - Deep dive into list implementation
- [04-function-calling.md](04-function-calling.md) - Function call conventions
