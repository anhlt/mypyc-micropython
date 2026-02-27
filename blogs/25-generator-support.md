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
