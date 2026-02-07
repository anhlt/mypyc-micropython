# Memory Layout and Object Structure

This document explains how Python objects are represented in memory within MicroPython.

## Table of Contents

- [Object Header](#object-header)
- [Type Objects](#type-objects)
- [Memory Allocation Strategy](#memory-allocation-strategy)
- [Garbage Collection Considerations](#garbage-collection-considerations)
- [Object Size Analysis](#object-size-analysis)

## Object Header

Every heap-allocated MicroPython object starts with a type pointer:

```c
// Base object structure - ALL objects have this
typedef struct _mp_obj_base_t {
    const mp_obj_type_t *type;  // Pointer to type descriptor
} mp_obj_base_t;
```

This is the **only required field**. Everything else depends on the specific type:

```
┌─────────────────────────────────────────────────────────────┐
│                    OBJECT MEMORY LAYOUT                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Integer (heap-allocated, > 30 bits):                       │
│  ┌────────────────────────────────────┐                    │
│  │ type: &mp_type_int (4 bytes)       │ ← base            │
│  ├────────────────────────────────────┤                    │
│  │ value: mpz_t struct                │ ← arbitrary       │
│  │   - neg: sign flag                 │    precision      │
│  │   - len: digit count               │    integer        │
│  │   - digits: digit array            │                    │
│  └────────────────────────────────────┘                    │
│                                                             │
│  Float:                                                     │
│  ┌────────────────────────────────────┐                    │
│  │ type: &mp_type_float (4 bytes)     │                    │
│  ├────────────────────────────────────┤                    │
│  │ value: mp_float_t (4/8 bytes)      │                    │
│  └────────────────────────────────────┘                    │
│  Total: 8 bytes (32-bit float) or 12 bytes (64-bit)        │
│                                                             │
│  String:                                                    │
│  ┌────────────────────────────────────┐                    │
│  │ type: &mp_type_str (4 bytes)       │                    │
│  ├────────────────────────────────────┤                    │
│  │ hash: cached hash (4 bytes)        │                    │
│  ├────────────────────────────────────┤                    │
│  │ len: string length (4 bytes)       │                    │
│  ├────────────────────────────────────┤                    │
│  │ data: pointer to chars OR inline   │                    │
│  └────────────────────────────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Type Objects

Every type is described by an `mp_obj_type_t` structure:

```c
struct _mp_obj_type_t {
    mp_obj_base_t base;           // Type of type is &mp_type_type
    qstr name;                     // Type name (e.g., "list", "int")
    mp_print_fun_t print;          // __repr__ / __str__
    mp_make_new_fun_t make_new;    // __new__ + __init__
    mp_call_fun_t call;            // __call__ (for callables)
    mp_unary_op_fun_t unary_op;    // __neg__, __pos__, __bool__, etc.
    mp_binary_op_fun_t binary_op;  // __add__, __sub__, __eq__, etc.
    mp_attr_fun_t attr;            // __getattr__, __setattr__
    mp_subscr_fun_t subscr;        // __getitem__, __setitem__
    mp_getiter_fun_t getiter;      // __iter__
    mp_fun_1_t iternext;           // __next__
    mp_buffer_fun_t buffer;        // Buffer protocol
    const void *protocol;          // Protocol-specific data
    const void *parent;            // Base class (for inheritance)
    mp_obj_dict_t *locals_dict;    // Class attributes
};
```

**Example: int type descriptor**

```c
const mp_obj_type_t mp_type_int = {
    .base = { &mp_type_type },
    .name = MP_QSTR_int,
    .print = mp_obj_int_print,
    .make_new = mp_obj_int_make_new,
    .unary_op = mp_obj_int_unary_op,
    .binary_op = mp_obj_int_binary_op,
};
```

## Memory Allocation Strategy

MicroPython uses a custom heap allocator optimized for embedded systems:

```
┌─────────────────────────────────────────────────────────────┐
│                   MICROPYTHON HEAP LAYOUT                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Heap start                                                 │
│  ▼                                                          │
│  ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬─────┐  │
│  │ HDR  │ OBJ1 │ HDR  │ OBJ2 │ HDR  │FREE  │ HDR  │OBJ3 │  │
│  └──────┴──────┴──────┴──────┴──────┴──────┴──────┴─────┘  │
│                                                             │
│  Each allocation has a header:                              │
│  ┌─────────────────────────────────────┐                   │
│  │ Block header (1 word)               │                   │
│  │ ├─ bits 0-1: block type             │                   │
│  │ │   00 = free                       │                   │
│  │ │   01 = head of allocation         │                   │
│  │ │   10 = tail of allocation         │                   │
│  │ │   11 = marked (during GC)         │                   │
│  │ ├─ bits 2-31: size or next ptr      │                   │
│  │ └───────────────────────────────────│                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
│  Allocation sizes are rounded to MICROPY_BYTES_PER_GC_BLOCK │
│  (typically 16 bytes on 32-bit systems)                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Allocation Functions

```c
// Allocate zeroed memory (may trigger GC)
void *m_malloc0(size_t num_bytes);

// Allocate uninitialized memory
void *m_malloc(size_t num_bytes);

// Reallocate (for growing arrays)
void *m_realloc(void *ptr, size_t new_num_bytes);

// Free memory
void m_free(void *ptr);
```

### ESP32 Memory Constraints

```
┌─────────────────────────────────────────────────────────────┐
│                  ESP32 MEMORY MAP                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ESP32 (original):                                          │
│  - Total SRAM: 520 KB                                       │
│  - Available for heap: ~200-300 KB (after firmware)        │
│  - MicroPython heap: configurable, typically 96-128 KB     │
│                                                             │
│  ESP32-C3:                                                  │
│  - Total SRAM: 400 KB                                       │
│  - Available for heap: ~150-200 KB                         │
│  - MicroPython heap: typically 64-96 KB                    │
│                                                             │
│  Impact on object design:                                   │
│  - Every byte counts!                                       │
│  - Small int optimization saves ~12 bytes per int          │
│  - String interning saves duplicate strings                │
│  - Qstr saves memory for common strings                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Garbage Collection Considerations

MicroPython uses mark-and-sweep garbage collection:

```
┌─────────────────────────────────────────────────────────────┐
│                   GARBAGE COLLECTION CYCLE                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. MARK PHASE:                                             │
│     Start from roots (stack, globals, registers)           │
│     Recursively mark all reachable objects                 │
│                                                             │
│     roots ──► obj1 ──► obj2                                │
│                │         │                                  │
│                ▼         ▼                                  │
│              obj3      obj4                                 │
│                                                             │
│     Marked: {obj1, obj2, obj3, obj4}                       │
│                                                             │
│  2. SWEEP PHASE:                                            │
│     Walk heap, free unmarked objects                       │
│                                                             │
│     ┌─────┬─────┬─────┬─────┬─────┬─────┐                 │
│     │obj1 │obj5 │obj2 │obj6 │obj3 │obj4 │                 │
│     │MARK │     │MARK │     │MARK │MARK │                 │
│     └─────┴─────┴─────┴─────┴─────┴─────┘                 │
│             ▲           ▲                                   │
│             │           │                                   │
│           FREE        FREE                                  │
│                                                             │
│  GC can be triggered:                                       │
│  - Automatically when heap is full                         │
│  - Manually via gc.collect()                               │
│  - Threshold-based (configurable)                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Writing GC-Safe Code

```c
// WRONG: obj might be collected between lines!
mp_obj_t obj = mp_obj_new_list(0, NULL);
// ... GC might run here ...
mp_obj_list_append(obj, item);  // obj could be invalid!

// CORRECT: Keep reference on stack or register as root
mp_obj_t obj = mp_obj_new_list(0, NULL);
mp_obj_list_append(obj, item);  // Use immediately
return obj;  // Or return/store it

// For complex cases, use gc_lock/gc_unlock
gc_lock();
mp_obj_t obj = mp_obj_new_list(0, NULL);
// Do complex setup...
gc_unlock();
```

## Object Size Analysis

Here's how much memory common objects consume:

| Object | Minimum Size | Typical Size | Notes |
|--------|--------------|--------------|-------|
| Small int | 0 bytes | 0 bytes | Encoded in pointer |
| Large int | 12+ bytes | varies | mpz_t grows as needed |
| Float | 8-12 bytes | 8 bytes | Depends on precision |
| True/False | 0 bytes | 0 bytes | Singletons |
| None | 0 bytes | 0 bytes | Singleton |
| Empty string | 16 bytes | 16 bytes | Header only |
| Short string | 16 bytes | 16 bytes | Inline data |
| Long string | 16 + len | varies | External data |
| Empty list | 24 bytes | 24 bytes | Header + array ptr |
| Empty dict | 32+ bytes | 48 bytes | Hash table overhead |
| Empty tuple | 8 bytes | 8 bytes | Just header |
| Function | 24+ bytes | varies | Bytecode reference |
| Closure | 32+ bytes | varies | + captured variables |

**Memory optimization tips:**

1. Prefer tuples over lists for fixed data
2. Use small integers (-2^30 to 2^30-1) when possible  
3. Reuse strings (they're interned)
4. Avoid deeply nested structures
5. Use `const` data in C modules (stored in flash, not RAM)

## See Also

- [01-type-mapping.md](01-type-mapping.md) - Type system overview
- [03-list-internals.md](03-list-internals.md) - List implementation details
- [04-function-calling.md](04-function-calling.md) - Function objects
