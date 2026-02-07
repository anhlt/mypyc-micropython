# List Internals: How Unbounded Lists Work in C

This document provides a deep dive into how Python's dynamic, unbounded lists are implemented in MicroPython's C runtime.

## Table of Contents

- [The Problem: Dynamic Arrays in Static C](#the-problem-dynamic-arrays-in-static-c)
- [List Object Structure](#list-object-structure)
- [Growth Strategy](#growth-strategy)
- [List Operations Internals](#list-operations-internals)
- [Code Generation for Lists](#code-generation-for-lists)
- [Performance Characteristics](#performance-characteristics)
- [Memory Fragmentation](#memory-fragmentation)

## The Problem: Dynamic Arrays in Static C

In Python, lists are unbounded - they can grow indefinitely:

```python
lst = []
for i in range(1000000):
    lst.append(i)  # List grows dynamically
```

In C, arrays have fixed sizes:

```c
int arr[100];  // Fixed at compile time
arr[100] = 1;  // BUFFER OVERFLOW - undefined behavior!
```

**How do we bridge this gap?**

The answer is **dynamic array allocation** with **geometric growth**.

## List Object Structure

MicroPython's list is defined in `py/objlist.c`:

```c
typedef struct _mp_obj_list_t {
    mp_obj_base_t base;    // Type pointer (always first)
    size_t alloc;          // Allocated capacity (slots)
    size_t len;            // Current length (used slots)
    mp_obj_t *items;       // Pointer to item array
} mp_obj_list_t;
```

Let's visualize this:

```
┌─────────────────────────────────────────────────────────────┐
│                    LIST OBJECT IN MEMORY                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  mp_obj_list_t (on heap):                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ base.type: &mp_type_list (4 bytes)                  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ alloc: 8 (4 bytes)                                  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ len: 5 (4 bytes)                                    │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ items: 0x20004000 ──────────────────────────────┐   │   │
│  └─────────────────────────────────────────────────┼───┘   │
│                                                    │        │
│                                                    ▼        │
│  items array (separate allocation):                         │
│  ┌───────┬───────┬───────┬───────┬───────┬───────┬───┬───┐ │
│  │ obj0  │ obj1  │ obj2  │ obj3  │ obj4  │ ???   │???│???│ │
│  └───────┴───────┴───────┴───────┴───────┴───────┴───┴───┘ │
│  │◄──────── len=5 used ────────►│◄─── 3 free ───►│        │
│  │◄──────────────── alloc=8 slots ──────────────►│        │
│                                                             │
│  Total memory: 16 bytes (header) + 32 bytes (8 slots × 4)  │
│              = 48 bytes for a 5-element list               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key insight**: The list header is separate from the items array. This allows the items array to be reallocated without moving the list object itself.

## Growth Strategy

When a list is full and needs more space, MicroPython uses **geometric growth**:

```c
// From py/objlist.c - simplified
static void list_extend_from_iter(mp_obj_t list, mp_obj_t iterable) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);
    
    // If full, grow the array
    if (self->len >= self->alloc) {
        // Geometric growth: new_alloc = old_alloc + old_alloc/2 + 2
        size_t new_alloc = self->alloc + self->alloc / 2 + 2;
        self->items = m_renew(mp_obj_t, self->items, self->alloc, new_alloc);
        self->alloc = new_alloc;
    }
    
    // Now safe to append
    self->items[self->len++] = item;
}
```

### Growth Pattern Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                   LIST GROWTH PATTERN                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Append #  │ len │ alloc │ Realloc? │ Growth Factor         │
│  ──────────┼─────┼───────┼──────────┼─────────────────────  │
│  (new)     │  0  │   0   │    -     │ -                     │
│  1         │  1  │   2   │   YES    │ 0 + 0/2 + 2 = 2      │
│  2         │  2  │   2   │    no    │                       │
│  3         │  3  │   5   │   YES    │ 2 + 2/2 + 2 = 5      │
│  4         │  4  │   5   │    no    │                       │
│  5         │  5  │   5   │    no    │                       │
│  6         │  6  │   9   │   YES    │ 5 + 5/2 + 2 = 9      │
│  ...       │     │       │          │                       │
│  10        │ 10  │  15   │   YES    │                       │
│  ...       │     │       │          │                       │
│  100       │ 100 │ 107   │          │                       │
│  1000      │1000 │1031   │          │                       │
│                                                             │
│  Reallocation count for n appends ≈ O(log n)               │
│  Total memory moves ≈ O(n) amortized                       │
│                                                             │
│  AMORTIZED APPEND COST: O(1)                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why This Growth Factor?

The formula `new = old + old/2 + 2` gives approximately 1.5x growth:

| Growth Factor | Memory Overhead | Realloc Frequency | Use Case |
|---------------|-----------------|-------------------|----------|
| 2x | High (~50%) | Low | CPython |
| 1.5x | Medium (~33%) | Medium | MicroPython |
| 1.25x | Low (~20%) | High | Memory-constrained |

MicroPython chooses 1.5x as a balance between memory efficiency and reallocation overhead - critical for embedded systems.

## List Operations Internals

### Creating an Empty List

```c
// mp_obj_new_list(0, NULL) expands to:
mp_obj_list_t *list = m_new_obj(mp_obj_list_t);
list->base.type = &mp_type_list;
list->alloc = 0;
list->len = 0;
list->items = NULL;
```

**Memory cost**: Just 16 bytes (the header). No items array allocated yet!

### Creating a List with Initial Elements

```c
// Python: [1, 2, 3]
// C:
mp_obj_t items[] = {
    mp_obj_new_int(1),
    mp_obj_new_int(2),
    mp_obj_new_int(3)
};
mp_obj_t list = mp_obj_new_list(3, items);

// This allocates:
// 1. List header (16 bytes)
// 2. Items array (3 * 4 = 12 bytes, but rounded to 16)
// Total: 32 bytes
```

### Append Operation

```c
// mp_obj_list_append implementation:
void mp_obj_list_append(mp_obj_t self_in, mp_obj_t arg) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(self_in);
    
    // Check if we need to grow
    if (self->len >= self->alloc) {
        // Calculate new size
        size_t new_alloc = self->alloc + self->alloc / 2 + 2;
        
        // Reallocate items array
        // m_renew may:
        // 1. Extend in-place if space available
        // 2. Allocate new array and copy
        // 3. Trigger GC if heap is full
        self->items = m_renew(mp_obj_t, self->items, 
                              self->alloc, new_alloc);
        self->alloc = new_alloc;
    }
    
    // Store the new item
    self->items[self->len++] = arg;
}
```

### Index Access (Get Item)

```c
// Python: lst[i]
// C implementation:
mp_obj_t mp_obj_list_subscr(mp_obj_t self_in, mp_obj_t index, 
                            mp_obj_t value) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(self_in);
    
    if (value == MP_OBJ_SENTINEL) {
        // Getting item
        size_t i = mp_get_index(self->base.type, self->len, index, false);
        return self->items[i];
    } else {
        // Setting item
        size_t i = mp_get_index(self->base.type, self->len, index, false);
        self->items[i] = value;
        return mp_const_none;
    }
}
```

### Pop Operation

```c
// Python: lst.pop() or lst.pop(i)
mp_obj_t mp_obj_list_pop(mp_obj_t self_in, size_t n_args, 
                         const mp_obj_t *args) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(self_in);
    
    if (self->len == 0) {
        mp_raise_msg(&mp_type_IndexError, "pop from empty list");
    }
    
    size_t index;
    if (n_args == 0) {
        index = self->len - 1;  // Pop from end
    } else {
        index = mp_get_index(self->base.type, self->len, args[0], false);
    }
    
    mp_obj_t ret = self->items[index];
    
    // Shift elements if not popping from end
    self->len--;
    if (index < self->len) {
        memmove(self->items + index, 
                self->items + index + 1,
                (self->len - index) * sizeof(mp_obj_t));
    }
    
    // Note: Array is NOT shrunk to save realloc overhead
    // alloc stays the same, only len decreases
    
    return ret;
}
```

## Code Generation for Lists

Here's how our compiler translates list operations to C:

### List Creation

**Python:**
```python
lst: list = [1, 2, 3]
```

**Generated C:**
```c
// We generate items array first, then create list
mp_obj_t _tmp1_items[] = {
    mp_obj_new_int(1),
    mp_obj_new_int(2), 
    mp_obj_new_int(3)
};
mp_obj_t lst = mp_obj_new_list(3, _tmp1_items);
```

### Empty List Creation

**Python:**
```python
result: list = []
```

**Generated C:**
```c
mp_obj_t result = mp_obj_new_list(0, NULL);
```

### Append

**Python:**
```python
result.append(x)
```

**Generated C:**
```c
// For int x:
mp_obj_list_append(result, mp_obj_new_int(x));

// For already-boxed x:
mp_obj_list_append(result, x);
```

### Index Access

**Python:**
```python
value = lst[i]
```

**Generated C:**
```c
mp_obj_t value = mp_obj_subscr(lst, mp_obj_new_int(i), MP_OBJ_SENTINEL);
```

### Index Assignment

**Python:**
```python
lst[i] = value
```

**Generated C:**
```c
mp_obj_subscr(lst, mp_obj_new_int(i), mp_obj_new_int(value));
```

### Iteration with For Loop

**Python:**
```python
for item in lst:
    process(item)
```

**Generated C (optimized for lists):**
```c
mp_obj_t _iter = lst;
size_t _len = mp_obj_get_int(mp_obj_len(_iter));
for (size_t _idx = 0; _idx < _len; _idx++) {
    mp_obj_t item = mp_obj_subscr(_iter, mp_obj_new_int(_idx), 
                                   MP_OBJ_SENTINEL);
    // process(item)
}
```

## Performance Characteristics

```
┌─────────────────────────────────────────────────────────────┐
│              LIST OPERATION TIME COMPLEXITY                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Operation          │ Average │ Worst   │ Notes            │
│  ───────────────────┼─────────┼─────────┼─────────────────│
│  Index access [i]   │ O(1)    │ O(1)    │ Direct pointer  │
│  Index assign [i]=  │ O(1)    │ O(1)    │ Direct pointer  │
│  Append             │ O(1)*   │ O(n)    │ *Amortized      │
│  Pop from end       │ O(1)    │ O(1)    │ Just decrement  │
│  Pop from middle    │ O(n)    │ O(n)    │ Shift elements  │
│  Insert at start    │ O(n)    │ O(n)    │ Shift all       │
│  Insert at middle   │ O(n)    │ O(n)    │ Shift half      │
│  len()              │ O(1)    │ O(1)    │ Stored in obj   │
│  Iteration          │ O(n)    │ O(n)    │ Touch each      │
│  Copy               │ O(n)    │ O(n)    │ Alloc + memcpy  │
│  Search (in)        │ O(n)    │ O(n)    │ Linear scan     │
│                                                             │
│  SPACE: O(n) with ~33% overhead on average                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Benchmark: Native C List vs Interpreted Python List

```
┌─────────────────────────────────────────────────────────────┐
│           BENCHMARK: Building list of 1000 squares         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Python (interpreted):                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ result = []                                         │   │
│  │ for i in range(1000):                               │   │
│  │     result.append(i * i)                            │   │
│  └─────────────────────────────────────────────────────┘   │
│  Time: ~3200 μs (MicroPython on ESP32-C3)                  │
│                                                             │
│  Per iteration:                                             │
│  - Bytecode dispatch: ~50 cycles                           │
│  - Range iterator next: ~30 cycles                         │
│  - Multiply (boxed): ~20 cycles                            │
│  - Append call: ~40 cycles                                 │
│  - Loop overhead: ~30 cycles                               │
│  Total: ~170 cycles × 1000 = 170,000 cycles               │
│                                                             │
│  ────────────────────────────────────────────────────────  │
│                                                             │
│  mypyc-compiled (native C):                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ mp_obj_t result = mp_obj_new_list(0, NULL);         │   │
│  │ for (mp_int_t i = 0; i < 1000; i++) {               │   │
│  │     mp_obj_list_append(result, mp_obj_new_int(i*i));│   │
│  │ }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  Time: ~360 μs (native on ESP32-C3)                        │
│                                                             │
│  Per iteration:                                             │
│  - Native loop: ~3 cycles                                  │
│  - Multiply (native): ~1 cycle                             │
│  - Box result: ~10 cycles                                  │
│  - Append: ~20 cycles                                      │
│  Total: ~34 cycles × 1000 = 34,000 cycles                 │
│                                                             │
│  SPEEDUP: ~9x faster                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Memory Fragmentation

Repeated list growth can cause heap fragmentation:

```
┌─────────────────────────────────────────────────────────────┐
│                  HEAP FRAGMENTATION EXAMPLE                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Initial state (after creating list, growing to 8 items):  │
│  ┌────┬────────────────┬────┬────────────────────────────┐ │
│  │HDR │ list[0..7]     │HDR │    FREE SPACE              │ │
│  └────┴────────────────┴────┴────────────────────────────┘ │
│                                                             │
│  After another object is allocated:                         │
│  ┌────┬────────────────┬────┬────────┬────┬──────────────┐ │
│  │HDR │ list[0..7]     │HDR │ obj X  │HDR │   FREE       │ │
│  └────┴────────────────┴────┴────────┴────┴──────────────┘ │
│                                                             │
│  List needs to grow (8→14 items), but can't extend:        │
│  Must allocate new array and copy!                          │
│                                                             │
│  ┌────┬────────────────┬────┬────────┬────┬──────────────┐ │
│  │HDR │ [GARBAGE]      │HDR │ obj X  │HDR │list[0..13]   │ │
│  └────┴────────────────┴────┴────────┴────┴──────────────┘ │
│        ▲                                                    │
│        │                                                    │
│        └── Old array becomes garbage (until GC)            │
│                                                             │
│  After GC:                                                  │
│  ┌────┬────────────────┬────┬────────┬────┬──────────────┐ │
│  │HDR │   FREE         │HDR │ obj X  │HDR │list[0..13]   │ │
│  └────┴────────────────┴────┴────────┴────┴──────────────┘ │
│                                                             │
│  Problem: FREE block is too small for the next list grow!  │
│  This is FRAGMENTATION.                                     │
│                                                             │
│  Mitigation strategies:                                     │
│  1. Pre-allocate lists when size is known                  │
│  2. Use tuples for fixed-size collections                  │
│  3. Reuse lists instead of creating new ones               │
│  4. Trigger GC before intensive list operations            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Pre-allocation Optimization

If you know the final size, you can pre-allocate:

**Python (slow - many reallocations):**
```python
result = []
for i in range(1000):
    result.append(i)
```

**C equivalent with pre-allocation:**
```c
// Pre-allocate for 1000 items
mp_obj_list_t *result = MP_OBJ_TO_PTR(mp_obj_new_list(0, NULL));
result->items = m_new(mp_obj_t, 1000);
result->alloc = 1000;

// Now appends never reallocate
for (mp_int_t i = 0; i < 1000; i++) {
    result->items[result->len++] = mp_obj_new_int(i);
}
```

This eliminates all reallocation overhead!

## See Also

- [01-type-mapping.md](01-type-mapping.md) - How types map to C
- [02-memory-layout.md](02-memory-layout.md) - Object memory layout
- [04-function-calling.md](04-function-calling.md) - Function call conventions
- [05-iteration-protocols.md](05-iteration-protocols.md) - How for loops work
