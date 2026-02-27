# 25. Generator Support: Simple `yield` Lowered to a State Machine

This post documents Phase 5.2 generator support, the smallest useful slice of Python generators: `yield` as a statement inside a function, compiled into a MicroPython iterator object.

The punchline is simple: a generator function becomes a heap allocated object with fields for its locals, plus an `iternext` function that resumes execution by jumping to a saved label.

## Table of Contents

- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [Part 2: C Background](#part-2-c-background)
- [Part 3: Implementation](#part-3-implementation)
- [MVP Restrictions](#mvp-restrictions)

## Part 1: Compiler Theory

### Generators force the compiler to model suspension

Most features we've compiled so far run straight through: enter function, execute statements, return.

Generators break that shape. Each `yield` suspends execution and returns a value to the caller. The next iteration must resume right after the `yield`, with all locals preserved.

That changes what "a function" means inside the compiler:

- Normal functions compile to a C function.
- Generator functions compile to an object constructor, plus a resumable `iternext` entry point.

### The three stage pipeline: Python to IR to C

This compiler still follows the same pipeline:

1. Parse Python into an AST.
2. Build an IR that makes control flow explicit.
3. Emit C that calls MicroPython's runtime APIs.

Generators mainly stress step 2. We need IR that can represent a yield point, and we need a concrete plan for "where to resume".

In this project, a `yield` statement becomes a `YieldIR` node with an integer `state_id`. Emission then lowers those state ids into labels in C.

### IR dump: simple generators

Input Python, from `examples/generators.py`:

```python
def countdown(n: int):
    while n > 0:
        yield n
        n -= 1


def squares(n: int):
    for i in range(n):
        yield i * i
```

IR dump, produced by `mpy-compile examples/generators.py --dump-ir text`:

```text
Module: generators (c_name: generators)

Functions:
  def countdown(n: MP_INT_T) -> MP_OBJ_T:
    c_name: generators_countdown
    max_temp: 0
    locals: {n: MP_INT_T}
    body:
      while (n > 0):
        yield n [state_id=1]
        n -= 1

  def squares(n: MP_INT_T) -> MP_OBJ_T:
    c_name: generators_squares
    max_temp: 0
    locals: {n: MP_INT_T, i: MP_INT_T}
    body:
      for i in range(0, n, 1):
        yield (i * i) [state_id=1]
```

Two details matter here:

- `YieldIR` is statement level IR, not an expression, so the compiler can treat it as a control flow split point.
- Each yield site carries a `state_id`. In these tiny examples there is one yield point, so the id is `1`.

## Part 2: C Background

### MicroPython generators are iterators

MicroPython drives iteration by repeatedly calling an `iternext` function. When the iterator is done, `iternext` returns a sentinel value:

- `MP_OBJ_STOP_ITERATION`

The C side does not throw a Python `StopIteration` exception here, it returns the sentinel to the runtime.

### Objects are structs on the heap

A compiled generator is a heap allocated struct. It always starts with a base header:

```c
mp_obj_base_t base;
```

After that, we can add fields. For generators, we need:

- A `state` field that records where to resume
- Storage for parameters and locals that must survive across yields

To turn the boxed `mp_obj_t` into a typed pointer to our struct, generated code uses:

```c
generators_countdown_gen_t *self = MP_OBJ_TO_PTR(self_in);
```

Then `self->field` reads and writes the generator's saved locals.

### The arrow operator and why locals live in `self`

When you see `self->n -= 1;`, that is not a fancy new operator. It's just "field `n` inside the struct pointed to by `self`".

Putting locals into the struct is the key trick that makes suspension work. If execution returns to the caller, stack locals are gone. Heap fields persist.

## Part 3: Implementation

### IRBuilder: detect generator functions and enforce the MVP

In `src/mypyc_micropython/ir_builder.py`, `IRBuilder.build_function()` first detects generator functions by scanning the AST for `ast.Yield` or `ast.YieldFrom`.

If the function is a generator, the builder rejects unsupported shapes early (today these raise `NotImplementedError`):

- `yield from`
- `try`, `with`, `async with` inside generator functions
- `return <value>` inside generator functions
- `yield` inside non `range(...)` for loops
- unsupported `range(...)` forms for generator loops

The supported `range(...)` subset is intentionally tiny. The helper `_is_supported_generator_range_call()` allows:

- `range(n)` where `n` is an int constant or a name
- `range(0, n)` where `n` is an int constant or a name
- `range(0, n, 1)` only
- no keyword arguments

Separately, `yield` is only supported as a statement. Using `yield` as an expression is rejected in `_build_expr()`.

### YieldIR: a yield point is a statement with a resume id

The IR node itself is small, defined in `src/mypyc_micropython/ir.py`:

```python
@dataclass
class YieldIR(StmtIR):
    value: ValueIR | None = None
    prelude: list[InstrIR] = field(default_factory=list)
    state_id: int = 0
```

During IR building, each yield statement gets a fresh `state_id` from `_next_yield_state_id()`. That id becomes the label name we resume from during codegen.

### GeneratorEmitter: lower the function into (struct + iternext + wrapper)

The generator emitter lives in `src/mypyc_micropython/generator_emitter.py`. It turns a generator `FuncIR` into three pieces:

1. A generator struct type that stores state and locals
2. An `*_gen_iternext()` function that resumes execution via `switch` and `goto`
3. A wrapper function that allocates and initializes the generator object

The most important mapping is how locals are handled:

- The emitted struct contains all parameters, plus every local in `func_ir.locals_`.
- Reads of `NameIR` are emitted as `self->name`, so expressions naturally use the saved fields.
- Assignments are emitted as writes to `self->name`, so updates persist across yields.

### Generated C: struct layout and `iternext` state machine

Here is a real excerpt from `modules/usermod_generators/generators.c`, generated by `make compile SRC=examples/generators.py`.

The generator object for `countdown()`:

```c
typedef struct _generators_countdown_gen_t {
    mp_obj_base_t base;
    uint16_t state;
    mp_int_t n;
} generators_countdown_gen_t;
```

The resumable `iternext` function starts by reading and clearing the state, then jumping to the right label:

```c
static mp_obj_t generators_countdown_gen_iternext(mp_obj_t self_in) {
    generators_countdown_gen_t *self = MP_OBJ_TO_PTR(self_in);
    uint16_t st = self->state;
    self->state = 65535;

    switch (st) {
        case 0: goto state_0;
        case 1: goto state_1;
        case 65535: return MP_OBJ_STOP_ITERATION;
        default: return MP_OBJ_STOP_ITERATION;
    }

state_0:
    {
    while ((self->n > 0)) {
        {
        self->state = 1;
        return mp_obj_new_int(self->n);
        }
    state_1:
        self->n -= 1;
    }
    }
    self->state = 65535;
    return MP_OBJ_STOP_ITERATION;
}
```

The yield point is the two line pattern to look for:

- store a resume id: `self->state = 1;`
- return the yielded value

Resumption happens at the `state_1:` label, which sits right after the return.

Finally, the wrapper allocates the object and initializes fields:

```c
static mp_obj_t generators_countdown(mp_obj_t n_obj) {
    generators_countdown_gen_t *gen = mp_obj_malloc(generators_countdown_gen_t, &generators_countdown_gen_type);
    gen->state = 0;
    gen->n = mp_obj_get_int(n_obj);
    return MP_OBJ_FROM_PTR(gen);
}
```

That wrapper is what the Python level "call" returns. `countdown(3)` is not running the loop, it is building a generator object.

## Extended Pattern Support

After the initial MVP, we extended generator support to handle two additional iteration patterns.

### Pattern 1: `range(start, end)` with non-zero start

The original MVP only supported `range(n)` and `range(0, n)`. We extended this to support any start value:

```python
def range_with_start(n: int):
    for i in range(1, n):  # start=1, not just 0
        yield i
```

**IR dump:**
```text
def range_with_start(n: MP_INT_T) -> MP_OBJ_T:
  c_name: generators_range_with_start
  max_temp: 0
  locals: {n: MP_INT_T, i: MP_INT_T}
  body:
    for i in range(1, n, 1):
      yield i [state_id=1]
```

**Generated C:**
```c
typedef struct _generators_range_with_start_gen_t {
    mp_obj_base_t base;
    uint16_t state;
    mp_int_t n;
    mp_int_t i;
} generators_range_with_start_gen_t;

static mp_obj_t generators_range_with_start_gen_iternext(mp_obj_t self_in) {
    generators_range_with_start_gen_t *self = MP_OBJ_TO_PTR(self_in);
    uint16_t st = self->state;
    self->state = 65535;

    switch (st) {
        case 0: goto state_0;
        case 1: goto state_1;
        case 65535: return MP_OBJ_STOP_ITERATION;
        default: return MP_OBJ_STOP_ITERATION;
    }

state_0:
    {
    self->i = 1;  // <-- Initialize from start value, not 0
    while (self->i < self->n) {
        {
        self->state = 1;
        return mp_obj_new_int(self->i);
        }
    state_1:
        self->i++;
    }
    }
    self->state = 65535;
    return MP_OBJ_STOP_ITERATION;
}
```

The key change is in `_emit_for_range_stmt()` in `generator_emitter.py`: instead of always initializing to 0, we emit the actual start expression.

### Pattern 2: `for x in items` (arbitrary iterable iteration)

This is the more significant extension. It allows generators to iterate over any iterable, not just `range()`:

```python
def iter_items(items: list[object]):
    for x in items:
        yield x
```

**IR dump:**
```text
def iter_items(items: MP_OBJ_T) -> MP_OBJ_T:
  c_name: generators_iter_items
  max_temp: 0
  locals: {items: MP_OBJ_T, x: MP_OBJ_T}
  body:
    for x in items:
      yield x [state_id=1]
```

**Generated C:**
```c
typedef struct _generators_iter_items_gen_t {
    mp_obj_base_t base;
    uint16_t state;
    mp_obj_t items;     // The original iterable parameter
    mp_obj_t x;         // Current loop item
    mp_obj_t iter_x;    // Iterator object (NEW)
} generators_iter_items_gen_t;
```

The struct now has an `iter_x` field to store the iterator object across yields.

**The iternext function:**
```c
static mp_obj_t generators_iter_items_gen_iternext(mp_obj_t self_in) {
    generators_iter_items_gen_t *self = MP_OBJ_TO_PTR(self_in);
    uint16_t st = self->state;
    self->state = 65535;

    switch (st) {
        case 0: goto state_0;
        case 1: goto state_1;
        case 65535: return MP_OBJ_STOP_ITERATION;
        default: return MP_OBJ_STOP_ITERATION;
    }

state_0:
    {
    // Get iterator from iterable (NULL = MicroPython manages buffer)
    self->iter_x = mp_getiter(self->items, NULL);
    
    // Loop: get next item, check for stop
    while ((self->x = mp_iternext(self->iter_x)) != MP_OBJ_STOP_ITERATION) {
        {
        self->state = 1;
        return self->x;
        }
    state_1:
        (void)0;  // No-op for C99 label compatibility
    }
    }
    self->state = 65535;
    return MP_OBJ_STOP_ITERATION;
}
```

### MicroPython Iterator Protocol

The for-iter pattern uses MicroPython's iterator protocol:

1. **`mp_getiter(iterable, buf)`** - Creates an iterator from an iterable
   - `buf` can be NULL (MicroPython allocates internally) or a `mp_obj_iter_buf_t*`
   - Returns an `mp_obj_t` iterator object

2. **`mp_iternext(iter)`** - Gets the next item from an iterator
   - Returns the next item, or `MP_OBJ_STOP_ITERATION` when exhausted
   - Note: `MP_OBJ_STOP_ITERATION` is typically `MP_OBJ_NULL` (0)

### The `(void)0;` Workaround

You might notice `(void)0;` after the yield's resume label. This is a C99 compatibility fix.

In C, a label cannot be at the end of a compound statement without a following statement:
```c
// This is invalid C99:
while (...) {
    state_1:  // ERROR: label at end of block
}

// This is valid:
while (...) {
    state_1:
        (void)0;  // No-op statement makes it valid
}
```

For `for-range` loops, the `self->i++;` increment naturally follows the label. For `for-iter` loops, there's no increment, so we add an explicit no-op.

### Implementation Changes Summary

**`ir_builder.py`:**
- `_is_supported_generator_range_call()`: Extended to accept `range(start, end)` where both are int constants or names
- Generator restriction check: Now allows `ForIterIR` in generators (not just `ForRangeIR`)

**`generator_emitter.py`:**
- Added `ForIterIR` to imports
- `_emit_for_range_stmt()`: Initializes loop variable from start expression (not always 0)
- Added `_emit_for_iter()`: Emits `mp_getiter`/`mp_iternext` pattern for arbitrary iterables
- `_all_gen_fields()`: Walks body to find `ForIterIR` loops and adds `iter_{var}` fields to struct

## Deep Dive: MicroPython Generator Internals at the C Level

This section explains how MicroPython implements generators in C, and how our compiled generators integrate with MicroPython's runtime.

### Understanding `mp_obj_type_t`: The Type System Foundation

Every Python object in MicroPython has a type, represented by `mp_obj_type_t`. This structure defines how the runtime interacts with objects of that type:

```c
struct _mp_obj_type_t {
    mp_obj_base_t base;       // Points to mp_type_type
    uint16_t flags;           // Behavior flags (iteration, equality, etc.)
    uint16_t name;            // Type name as qstr
    
    // Slot indices (point to functions in slots[] array)
    uint8_t slot_index_make_new;    // __new__ / __init__
    uint8_t slot_index_print;       // __repr__ / __str__
    uint8_t slot_index_call;        // __call__
    uint8_t slot_index_unary_op;    // Unary operators
    uint8_t slot_index_binary_op;   // Binary operators
    uint8_t slot_index_attr;        // Attribute access
    uint8_t slot_index_subscr;      // Subscript access
    uint8_t slot_index_iter;        // Iterator behavior
    uint8_t slot_index_buffer;      // Buffer protocol
    uint8_t slot_index_protocol;    // Stream protocol, etc.
    uint8_t slot_index_parent;      // Parent type(s)
    uint8_t slot_index_locals_dict; // Methods dictionary
    
    const void *slots[];      // Variable-length array of function pointers
};
```

The `slot_index_iter` field is critical for generators. Its behavior depends on the `flags` field.

### Iterator Flags: How MicroPython Knows What to Call

MicroPython uses flags to determine how iteration works for a type:

```c
#define MP_TYPE_FLAG_ITER_IS_GETITER (0x0000)   // Default: iter slot is getiter
#define MP_TYPE_FLAG_ITER_IS_ITERNEXT (0x0080)  // iter slot is iternext directly
#define MP_TYPE_FLAG_ITER_IS_CUSTOM (0x0100)    // iter slot points to custom struct
#define MP_TYPE_FLAG_ITER_IS_STREAM (0x0180)    // Combination for stream iteration
```

**`MP_TYPE_FLAG_ITER_IS_ITERNEXT`** is the key flag for generators. When set:
- The `iter` slot points directly to an `iternext` function (not `getiter`)
- `mp_getiter()` automatically returns `self` (the object is its own iterator)
- `mp_iternext()` calls the function in the `iter` slot

This is exactly what a generator needs: the generator object IS the iterator, and calling `next()` on it should resume execution.

### Runtime Dispatch: `mp_getiter()` and `mp_iternext()`

When Python code iterates over an object, MicroPython's runtime calls these functions:

**`mp_getiter()` — Get an iterator from an iterable:**

```c
mp_obj_t mp_getiter(mp_obj_t o_in, mp_obj_iter_buf_t *iter_buf) {
    const mp_obj_type_t *type = mp_obj_get_type(o_in);
    
    // Fast path: if ITER_IS_ITERNEXT, the object IS its own iterator
    if ((type->flags & MP_TYPE_FLAG_ITER_IS_ITERNEXT) == MP_TYPE_FLAG_ITER_IS_ITERNEXT) {
        return o_in;  // Return self — no allocation needed!
    }
    
    // Otherwise, call the getiter function from the slot
    if (MP_OBJ_TYPE_HAS_SLOT(type, iter)) {
        mp_getiter_fun_t getiter = (mp_getiter_fun_t)MP_OBJ_TYPE_GET_SLOT(type, iter);
        return getiter(o_in, iter_buf);
    }
    
    // Fallback: check for __getitem__ protocol
    // ...
}
```

**`mp_iternext()` — Get the next item from an iterator:**

```c
mp_obj_t mp_iternext(mp_obj_t o_in) {
    mp_cstack_check();  // Protect against stack overflow
    const mp_obj_type_t *type = mp_obj_get_type(o_in);
    
    if (TYPE_HAS_ITERNEXT(type)) {
        // Call the iternext function directly
        return type_get_iternext(type)(o_in);
    }
    // ...
}

// Helper to get the iternext function pointer
static mp_fun_1_t type_get_iternext(const mp_obj_type_t *type) {
    if (type->flags & MP_TYPE_FLAG_ITER_IS_ITERNEXT) {
        // The iter slot IS the iternext function
        return (mp_fun_1_t)MP_OBJ_TYPE_GET_SLOT(type, iter);
    }
    // ...
}
```

The key insight: when `MP_TYPE_FLAG_ITER_IS_ITERNEXT` is set, both `getiter` (return self) and `iternext` (call the slot) are handled automatically by the runtime. We just need to provide ONE function.

### Memory Layout: Generator Objects on the Heap

A generator object must persist across `yield` points. Our generated struct layout:

```c
typedef struct _module_mygenerator_gen_t {
    mp_obj_base_t base;   // Required: points to type object
    uint16_t state;       // Execution state (which label to resume at)
    mp_int_t n;           // Parameters and locals...
    mp_int_t i;           // ..stored as struct fields
} module_mygenerator_gen_t;
```

**Why this layout?**

1. **`mp_obj_base_t base`** — Every MicroPython object starts with this. It contains a pointer to the type object, which the runtime uses to find methods and behavior.

2. **`uint16_t state`** — Our state machine variable. Values:
   - `0` = Initial state, start from beginning
   - `1`, `2`, ... = Resume points after yields
   - `0xFFFF` (65535) = Generator exhausted

3. **Local variables** — All parameters and locals that must survive across yields are stored as struct fields. Stack variables would be lost when `iternext` returns!

### Object Allocation: `mp_obj_malloc()`

MicroPython provides `mp_obj_malloc()` to allocate typed objects:

```c
// Allocate a new generator object
module_countdown_gen_t *gen = mp_obj_malloc(
    module_countdown_gen_t,        // Struct type (determines size)
    &module_countdown_gen_type     // Pointer to type object
);
```

This macro:
1. Allocates `sizeof(module_countdown_gen_t)` bytes from the heap
2. Sets `gen->base.type = &module_countdown_gen_type`
3. Returns a properly typed pointer

The type pointer is critical — it's how `mp_getiter()` and `mp_iternext()` know which functions to call.

### Type Registration: `MP_DEFINE_CONST_OBJ_TYPE`

We register our generator type using this macro:

```c
MP_DEFINE_CONST_OBJ_TYPE(
    module_countdown_gen_type,      // Type object name
    MP_QSTR_generator,              // Python-visible type name
    MP_TYPE_FLAG_ITER_IS_ITERNEXT,  // This is an iterator type
    iter, module_countdown_gen_iternext  // The iternext function
);
```

Breaking this down:
- **`MP_QSTR_generator`** — The type name shown in Python (`type(gen)` returns `<class 'generator'>`)
- **`MP_TYPE_FLAG_ITER_IS_ITERNEXT`** — Tells runtime our `iter` slot IS the `iternext` function
- **`iter, function`** — The slot assignment: `iter` slot = our `iternext` function

### Complete Generator Lifecycle

Let's trace through what happens when Python code runs `list(countdown(3))`:

```
Python: gen = countdown(3)
```
1. Runtime calls our wrapper function `module_countdown(3_obj)`
2. Wrapper allocates `gen` via `mp_obj_malloc()`
3. Wrapper initializes: `gen->state = 0`, `gen->n = 3`
4. Wrapper returns `MP_OBJ_FROM_PTR(gen)` — boxed pointer to generator object

```
Python: list(gen)  # Starts iterating
```
5. `list()` calls `mp_getiter(gen)` → returns `gen` (because `ITER_IS_ITERNEXT`)
6. `list()` calls `mp_iternext(gen)` to get first item

```
C: module_countdown_gen_iternext(gen)
```
7. Read state: `st = self->state` (0)
8. Mark as "running": `self->state = 65535`
9. Switch on `st`: `case 0: goto state_0;`
10. Execute until yield: `return mp_obj_new_int(self->n)` with `self->state = 1`

```
Python: # First iteration returns 3
```
11. `list()` stores `3`, calls `mp_iternext(gen)` again

```
C: module_countdown_gen_iternext(gen)  # Second call
```
12. Read state: `st = 1`, then `self->state = 65535`
13. Switch: `case 1: goto state_1;`
14. Resume after yield: `self->n -= 1`, continue loop...

```
Eventually:
```
15. Loop exits, function falls through to:
    ```c
    self->state = 65535;
    return MP_OBJ_STOP_ITERATION;
    ```
16. `list()` sees `MP_OBJ_STOP_ITERATION`, stops iterating
17. Result: `[3, 2, 1]`

### State Machine Transformation

The core compilation trick is transforming sequential Python code into a resumable state machine:

**Python (sequential):**
```python
def countdown(n: int):
    while n > 0:
        yield n      # Suspend here, return n
        n -= 1       # Resume here next time
```

**C (state machine):**
```c
static mp_obj_t countdown_gen_iternext(mp_obj_t self_in) {
    countdown_gen_t *self = MP_OBJ_TO_PTR(self_in);
    uint16_t st = self->state;
    self->state = 65535;  // Mark as "running" / exhausted
    
    switch (st) {
        case 0: goto state_0;   // Fresh start
        case 1: goto state_1;   // Resume after yield
        case 65535: return MP_OBJ_STOP_ITERATION;  // Already done
        default: return MP_OBJ_STOP_ITERATION;
    }
    
state_0:
    while (self->n > 0) {
        // YIELD POINT:
        self->state = 1;              // Save resume point
        return mp_obj_new_int(self->n);  // Return to caller
        
    state_1:                          // Resume here
        self->n -= 1;
    }
    
    self->state = 65535;
    return MP_OBJ_STOP_ITERATION;
}
```

**Key transformation rules:**

1. **Variables → Struct fields**: `n` becomes `self->n` (survives across returns)
2. **Yield → Return + Label**: `yield n` becomes `return n` with a label after it
3. **State tracking**: Each yield gets a unique state ID for resumption
4. **Entry dispatch**: `switch(state)` jumps to the right resume point

### Memory Efficiency

Our compiled generators are memory-efficient:

| Component | Size | Notes |
|-----------|------|-------|
| `base` | 4-8 bytes | Pointer to type (32/64-bit) |
| `state` | 2 bytes | uint16_t, supports 65534 yield points |
| Each local | 4-8 bytes | `mp_int_t` or `mp_obj_t` per variable |

A simple generator like `countdown` uses ~14-22 bytes total, compared to MicroPython's bytecode generators which need space for the entire bytecode state machine.

### Comparison: Our Generators vs MicroPython's Native Generators

MicroPython has its own generator implementation in `objgenerator.c`. Key differences:

| Aspect | MicroPython (Bytecode) | Our Compiled Generators |
|--------|----------------------|------------------------|
| Storage | `mp_code_state_t` with bytecode state | Custom struct with C locals |
| Execution | VM interprets bytecode | Direct C execution (native) |
| State | Bytecode instruction pointer | Integer state ID |
| Resume | VM resumes at saved IP | `goto` to labeled position |
| `send()` | Supported | Not supported (MVP) |
| `throw()` | Supported | Not supported (MVP) |

Our approach trades features for performance — we generate direct C code that runs without interpretation overhead.

## MVP Restrictions (Updated)

This implementation is intentionally narrow. It is meant to be a reliable stepping stone, not full CPython generator semantics.

**Supported patterns:**
- `while` loops with `yield`
- `for i in range(n)` with `yield`
- `for i in range(start, end)` with `yield` (any start value)
- `for x in iterable` with `yield` (lists, tuples, dicts, sets, etc.)

**Not supported:**
- `yield` as expression (`x = yield value`)
- `yield from`
- `try`/`with`/`async with` inside generators
- `return <value>` inside generators
- Generator methods (`send`, `throw`, `close`)
- Generator expressions (`(x for x in ...)`)
