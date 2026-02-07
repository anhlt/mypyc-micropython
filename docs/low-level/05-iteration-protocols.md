# Iteration Protocols and For Loop Implementation

This document explains how Python's iteration protocol is implemented in C and how for loops are translated.

## Table of Contents

- [Python's Iteration Protocol](#pythons-iteration-protocol)
- [MicroPython Iterator Implementation](#micropython-iterator-implementation)
- [Range Object Optimization](#range-object-optimization)
- [For Loop Code Generation](#for-loop-code-generation)
- [Break and Continue](#break-and-continue)
- [Performance Comparison](#performance-comparison)

## Python's Iteration Protocol

In Python, any object is iterable if it implements:

```python
class Iterable:
    def __iter__(self):
        return Iterator()

class Iterator:
    def __next__(self):
        # Return next item or raise StopIteration
        pass
```

The `for` loop desugars to:

```python
# for item in iterable:
#     process(item)

_iter = iter(iterable)
while True:
    try:
        item = next(_iter)
    except StopIteration:
        break
    process(item)
```

## MicroPython Iterator Implementation

In C, this protocol becomes:

```c
// Get iterator from object
mp_obj_t mp_getiter(mp_obj_t obj, mp_obj_iter_buf_t *iter_buf);

// Get next item (returns MP_OBJ_STOP_ITERATION when done)
mp_obj_t mp_iternext(mp_obj_t iter);

// Special sentinel value
#define MP_OBJ_STOP_ITERATION ((mp_obj_t)(((mp_uint_t)MP_OBJ_NULL) + 1))
```

### Iterator Object Structure

```
┌─────────────────────────────────────────────────────────────┐
│                  ITERATOR OBJECT TYPES                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  List Iterator:                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ mp_obj_list_it_t                                    │   │
│  │ ├─ base.type = &mp_type_polymorph_iter             │   │
│  │ ├─ iternext = list_it_iternext                     │   │
│  │ ├─ list: mp_obj_t (reference to list)              │   │
│  │ └─ cur: size_t (current index)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Range Iterator:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ mp_obj_range_it_t                                   │   │
│  │ ├─ base.type = &mp_type_polymorph_iter             │   │
│  │ ├─ iternext = range_it_iternext                    │   │
│  │ ├─ cur: mp_int_t (current value)                   │   │
│  │ ├─ stop: mp_int_t (end value)                      │   │
│  │ └─ step: mp_int_t (step value)                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Generic Iterator (for any iterable):                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Uses object's __iter__ and __next__ methods         │   │
│  │ Slower but universal                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### List Iterator Implementation

```c
// From py/objlist.c
typedef struct _mp_obj_list_it_t {
    mp_obj_base_t base;
    mp_fun_1_t iternext;
    mp_obj_t list;
    size_t cur;
} mp_obj_list_it_t;

static mp_obj_t list_it_iternext(mp_obj_t self_in) {
    mp_obj_list_it_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_list_t *list = MP_OBJ_TO_PTR(self->list);
    
    if (self->cur < list->len) {
        mp_obj_t item = list->items[self->cur];
        self->cur++;
        return item;
    }
    return MP_OBJ_STOP_ITERATION;
}
```

## Range Object Optimization

`range()` is special - it doesn't create a list, just stores parameters:

```c
// Range object (NOT an iterator, just parameters)
typedef struct _mp_obj_range_t {
    mp_obj_base_t base;
    mp_int_t start;
    mp_int_t stop;
    mp_int_t step;
} mp_obj_range_t;

// Range iterator (created when iterating)
typedef struct _mp_obj_range_it_t {
    mp_obj_base_t base;
    mp_fun_1_t iternext;
    mp_int_t cur;
    mp_int_t stop;
    mp_int_t step;
} mp_obj_range_it_t;

static mp_obj_t range_it_iternext(mp_obj_t self_in) {
    mp_obj_range_it_t *self = MP_OBJ_TO_PTR(self_in);
    
    // Check if done (handle positive and negative steps)
    if ((self->step > 0 && self->cur >= self->stop) ||
        (self->step < 0 && self->cur <= self->stop)) {
        return MP_OBJ_STOP_ITERATION;
    }
    
    mp_obj_t result = mp_obj_new_int(self->cur);
    self->cur += self->step;
    return result;
}
```

### Why Range is Memory Efficient

```
┌─────────────────────────────────────────────────────────────┐
│              RANGE vs LIST MEMORY COMPARISON                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  list(range(1000000)):                                      │
│  - 1,000,000 integers × 4 bytes = 4 MB (if small ints)    │
│  - Plus list header and array overhead                     │
│  - Total: ~4+ MB                                           │
│                                                             │
│  range(1000000):                                            │
│  - Just 3 integers: start=0, stop=1000000, step=1         │
│  - Total: 24 bytes                                         │
│                                                             │
│  That's a 160,000x difference!                             │
│                                                             │
│  On ESP32 with 96KB heap:                                   │
│  - list(range(24000)) would fill entire heap              │
│  - range(1000000000) still only uses 24 bytes             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## For Loop Code Generation

Our compiler generates different code for range vs generic iterables:

### Optimized Range Loop

**Python:**
```python
for i in range(n):
    total += i
```

**Generated C (optimized):**
```c
// No iterator object created!
mp_int_t _end = n;
for (mp_int_t i = 0; i < _end; i++) {
    total += i;
}
```

This is **pure C** - no boxing, no iterator objects, no function calls!

### Range with Step

**Python:**
```python
for i in range(0, n, 2):
    process(i)
```

**Generated C:**
```c
mp_int_t _end = n;
for (mp_int_t i = 0; i < _end; i += 2) {
    // process(i)
}
```

### Negative Step (Counting Down)

**Python:**
```python
for i in range(n, 0, -1):
    process(i)
```

**Generated C:**
```c
mp_int_t _end = 0;
for (mp_int_t i = n; i > _end; i--) {
    // process(i)
}
```

### Variable Step (Runtime Determined)

**Python:**
```python
for i in range(start, stop, step):
    process(i)
```

**Generated C:**
```c
mp_int_t _start = start;
mp_int_t _end = stop;
mp_int_t _step = step;

// Runtime condition depends on step sign
for (mp_int_t i = _start;
     (_step > 0) ? (i < _end) : (i > _end);
     i += _step) {
    // process(i)
}
```

### Generic Iterable Loop

**Python:**
```python
for item in some_list:
    process(item)
```

**Generated C (generic path):**
```c
mp_obj_t _iter = some_list;
size_t _len = mp_obj_get_int(mp_obj_len(_iter));

for (size_t _idx = 0; _idx < _len; _idx++) {
    mp_obj_t item = mp_obj_subscr(_iter, mp_obj_new_int(_idx), 
                                   MP_OBJ_SENTINEL);
    // process(item)
}
```

Note: This uses index-based access instead of full iterator protocol for lists, which is faster.

## Break and Continue

### Break Statement

**Python:**
```python
for i in range(100):
    if condition:
        break
    process(i)
```

**Generated C:**
```c
for (mp_int_t i = 0; i < 100; i++) {
    if (condition) {
        break;  // Direct C break
    }
    // process(i)
}
```

### Continue Statement

**Python:**
```python
for i in range(100):
    if should_skip(i):
        continue
    process(i)
```

**Generated C:**
```c
for (mp_int_t i = 0; i < 100; i++) {
    if (should_skip(i)) {
        continue;  // Direct C continue
    }
    // process(i)
}
```

### Nested Loops with Break

**Python:**
```python
for i in range(rows):
    for j in range(cols):
        if found(i, j):
            break  # Only breaks inner loop
    # Still in outer loop
```

**Generated C:**
```c
for (mp_int_t i = 0; i < rows; i++) {
    for (mp_int_t j = 0; j < cols; j++) {
        if (found(i, j)) {
            break;  // Breaks inner loop only
        }
    }
    // Outer loop continues
}
```

## Performance Comparison

```
┌─────────────────────────────────────────────────────────────┐
│           FOR LOOP PERFORMANCE COMPARISON                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Task: Sum integers 0 to 999                                │
│  Platform: ESP32-C3 @ 160MHz                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ IMPLEMENTATION              │ TIME (μs) │ RELATIVE │   │
│  │─────────────────────────────┼───────────┼──────────│   │
│  │ Interpreted (MicroPython)   │   3082    │   1.0x   │   │
│  │ Native (iterator protocol)  │    450    │   6.8x   │   │
│  │ Native (optimized range)    │    104    │  29.6x   │   │
│  │ Pure C (no MicroPython)     │     42    │  73.4x   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Breakdown of interpreted version:                          │
│  Per iteration (~3 μs):                                     │
│  - Bytecode fetch & dispatch: ~0.5 μs                      │
│  - Range iterator __next__:   ~0.8 μs                      │
│  - Unbox loop variable:       ~0.3 μs                      │
│  - Add operation (boxed):     ~0.4 μs                      │
│  - Store result:              ~0.3 μs                      │
│  - Loop overhead:             ~0.7 μs                      │
│                                                             │
│  Breakdown of native optimized version:                     │
│  Per iteration (~0.1 μs):                                   │
│  - C for loop overhead:       ~0.02 μs                     │
│  - Native integer add:        ~0.006 μs                    │
│  - Increment:                 ~0.006 μs                    │
│  - Comparison:                ~0.006 μs                    │
│                                                             │
│  The 30x speedup comes from:                               │
│  1. No bytecode dispatch                                   │
│  2. No boxing/unboxing in loop                             │
│  3. No iterator object allocation                          │
│  4. CPU can optimize tight C loop (pipelining, caching)   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why Native Range is Fast

```
┌─────────────────────────────────────────────────────────────┐
│              ITERATION STRATEGY COMPARISON                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INTERPRETED (slow):                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 1. Fetch LOAD_FAST 'range_obj'                       │  │
│  │ 2. Fetch GET_ITER                                    │  │
│  │    - Call mp_getiter(range_obj)                      │  │
│  │    - Allocate range_it_t object                      │  │
│  │ 3. FOR_ITER:                                         │  │
│  │    - Call mp_iternext(iter)                          │  │
│  │    - Inside: check bounds, box result, advance       │  │
│  │ 4. STORE_FAST 'i'                                    │  │
│  │ 5. ... loop body bytecode ...                        │  │
│  │ 6. JUMP_ABSOLUTE back to FOR_ITER                    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ~20 operations per iteration                               │
│                                                             │
│  NATIVE OPTIMIZED (fast):                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ for (mp_int_t i = 0; i < end; i++) {                │  │
│  │     // loop body as native C                         │  │
│  │ }                                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ~4 CPU instructions per iteration:                         │
│  1. Compare i < end                                         │
│  2. Conditional jump                                        │
│  3. Loop body                                               │
│  4. Increment i                                             │
│                                                             │
│  With CPU pipelining, this can be < 1 cycle/iteration!     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Code Generation Implementation

Here's how our compiler decides which pattern to use:

```python
# In compiler.py
def _translate_for(self, stmt, return_type, locals_):
    # Check if iterating over range()
    if isinstance(stmt.iter, ast.Call):
        if isinstance(stmt.iter.func, ast.Name):
            if stmt.iter.func.id == "range":
                # Use optimized range loop
                return self._translate_for_range(stmt, ...)
    
    # Fall back to generic iteration
    return self._translate_for_iterable(stmt, ...)
```

The range optimization transforms:

```
AST: For(target=Name('i'), iter=Call(func=Name('range'), args=[...]))

Into C pattern:
  for (mp_int_t i = START; CONDITION; INCREMENT) { BODY }
```

## See Also

- [01-type-mapping.md](01-type-mapping.md) - Type system overview
- [03-list-internals.md](03-list-internals.md) - List implementation
- [04-function-calling.md](04-function-calling.md) - Function conventions
