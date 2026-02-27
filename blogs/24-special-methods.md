# 24. Special Methods: Comparison Operators, Hashing, and the Iterator Protocol

This post covers a feature that looks small from Python, but touches some of the deepest seams in MicroPython's runtime model. We added support for three groups of special methods on compiled classes:

- Comparison operators: `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__`
- Hashing: `__hash__`
- The iterator protocol: `__iter__`, `__next__`

Along the way, we hit a few bugs that only show up when Python semantics meet C representation: `return self` being boxed as an integer, `raise` statements silently disappearing, and class typed locals not being treated as class objects during attribute access.

## Table of Contents

- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [Part 2: C Background](#part-2-c-background)
- [Part 3: Implementation](#part-3-implementation)
- [Device Testing](#device-testing)
- [Closing](#closing)

## Part 1: Compiler Theory

### The real problem: Python's magic methods are not magic

In CPython, writing `a < b` feels like it directly calls `a.__lt__(b)`. That's a useful mental model, but runtimes do something more structured:

1. The VM sees an operation, like a comparison.
2. It asks the left operand's type how to handle that operation.
3. The type decides whether it can handle it, and if so it returns a result.

MicroPython uses a slot based type architecture. A type object holds a table of function pointers. When an operation happens, the runtime calls a slot if it exists.

For a compiler like `mypyc-micropython`, that means:

- We can't just compile `def __lt__` and call it a day.
- We must also hook that method into MicroPython's type slots so the VM calls it when it evaluates `<`.

### The three stage pipeline: Python to IR to C

This project compiles typed Python to C user modules for MicroPython.

- Stage 1: parse Python into an AST and type check it.
- Stage 2: build an intermediate representation (IR) that makes control flow and data access explicit.
- Stage 3: emit C code that uses MicroPython's C API.

Special methods test the pipeline because they force the compiler to connect user written Python methods to runtime entry points.

### Why we track special methods on `ClassIR`

In the compiler's internal model, a compiled class becomes a `ClassIR` with fields and methods. To wire special methods into slots, the emitter needs to know which methods exist.

The simplest way is to add boolean flags like:

- `has_eq`, `has_lt`, `has_hash`
- `has_iter`, `has_next`

Then the class emitter can generate a `binary_op` slot only when any comparison method exists, generate a `unary_op` slot only when `__hash__` exists, and generate iterator slot logic only when iterator methods exist.

This is a common compiler pattern: detect features during IR building, then drive code generation with explicit feature flags.

### IR dump: module overview

The IR dump is the bridge between the Python you wrote and the C we generate. Here is the module level view for this example.

```text
Module: special_methods (c_name: special_methods)

Classes:
  Class: Number (c_name: special_methods_Number)
    Fields:
      value: int (MP_INT_T)
    Methods:
      def __init__(value: MP_INT_T) -> VOID
      def __eq__(other: MP_OBJ_T) -> BOOL
      def __ne__(other: MP_OBJ_T) -> BOOL
      def __lt__(other: MP_OBJ_T) -> BOOL
      def __le__(other: MP_OBJ_T) -> BOOL
      def __gt__(other: MP_OBJ_T) -> BOOL
      def __ge__(other: MP_OBJ_T) -> BOOL
      def __hash__() -> MP_INT_T
      def get_value() -> MP_INT_T

  Class: Counter (c_name: special_methods_Counter)
    Fields:
      current: int (MP_INT_T)
      limit: int (MP_INT_T)
    Methods:
      def __init__(limit: MP_INT_T) -> VOID
      def __iter__() -> MP_OBJ_T
      def __next__() -> MP_INT_T
      def get_current() -> MP_INT_T
```

Even before we look at C, we can see two important translation choices:

- Some methods use `MP_OBJ_T` (boxed objects) rather than a concrete type. For example, `__eq__` accepts `object` in Python.
- `__next__` returns `MP_INT_T` in IR, but it must still return `mp_obj_t` in C because MicroPython calls all methods through the object ABI.

## Part 2: C Background

This section explains the C concepts you need to read the generated code. The goal is not to teach all of C, only the parts that show up in MicroPython's slot mechanism and in the emitted functions.

### `mp_obj_t`: everything is an object at the boundary

MicroPython represents Python values as an `mp_obj_t`. Think of it as a word sized value that can either:

- directly encode small integers (tagged representation), or
- point to a heap allocated object (like an instance of a class).

The key takeaway for compiler output:

- Runtime entry points like `binary_op` and `iter` always take and return `mp_obj_t`.
- If our method body wants to read a field like `self.value` (an `int`), we must convert `self_in: mp_obj_t` into a typed pointer to the instance struct.

### Pointers and the arrow operator

If you have a pointer to a struct, like `special_methods_Number_obj_t *self`, field access uses `->`:

```c
self->value
```

That is equivalent to `(*self).value`, just easier to read.

### Casting `mp_obj_t` to a typed instance

Generated methods start by turning the boxed object into a typed pointer:

```c
special_methods_Number_obj_t *self = MP_OBJ_TO_PTR(self_in);
```

This does two things:

1. `MP_OBJ_TO_PTR` converts an `mp_obj_t` to a raw pointer (it is safe when the object is a heap allocated instance).
2. The cast tells the C compiler which struct layout to use.

Once we have `self`, `self->value` is just a struct field read.

### Slots: MicroPython's "vtable" for Python operations

In C++ terms, a slot table looks like a vtable, a set of function pointers used for dynamic dispatch. In Python terms, it is the runtime hook for operations.

MicroPython defines type objects with a macro that fills in these slots.

Here is the shape we care about, simplified:

```c
MP_DEFINE_CONST_OBJ_TYPE(
    type_name,
    MP_QSTR_ClassName,
    flags,
    make_new, ClassName_make_new,
    attr, ClassName_attr,
    binary_op, ClassName_binary_op,
    unary_op, ClassName_unary_op,
    iter, ClassName_iter_or_iternext,
    locals_dict, &ClassName_locals_dict
);
```

Think of the slots like this:

```text
             +------------------------------+
             | mp_obj_type_t (the type)     |
             +------------------------------+
             | name: "Counter"              |
             | flags: ITER_IS_ITERNEXT      |
             | make_new:   fn(...)          |
             | attr:       fn(...)          |
             | binary_op:  fn(op,lhs,rhs)   |  <-- comparisons
             | unary_op:   fn(op,self)      |  <-- hash
             | iter:       fn(self)         |  <-- getiter or iternext
             | locals_dict: {methods...}    |
             +------------------------------+
```

The key idea is that the VM does not look up `__lt__` by name when it sees `<`. It calls `type->binary_op(type, MP_BINARY_OP_LESS, ...)`.

### `binary_op`: mapping comparisons to enum values

MicroPython encodes operations as an enum:

```c
typedef enum {
    MP_BINARY_OP_LESS,
    MP_BINARY_OP_MORE,
    MP_BINARY_OP_EQUAL,
    MP_BINARY_OP_LESS_EQUAL,
    MP_BINARY_OP_MORE_EQUAL,
    MP_BINARY_OP_NOT_EQUAL,
} mp_binary_op_t;
```

The `binary_op` slot takes that enum, plus `lhs_in` and `rhs_in` objects. It returns:

- an `mp_obj_t` result if it supports the operation, or
- `MP_OBJ_NULL` to tell the runtime "I don't support that op".

That last detail matters. Returning `MP_OBJ_NULL` lets MicroPython try the other operand, or fall back to a default behavior.

### `unary_op`: hashing is a unary slot

Hashing is a unary operation, so MicroPython uses a separate slot:

```c
typedef enum {
    MP_UNARY_OP_BOOL,
    MP_UNARY_OP_LEN,
    MP_UNARY_OP_HASH,
} mp_unary_op_t;
```

If a type implements `MP_UNARY_OP_HASH`, that is how `hash(obj)` is evaluated.

### Iteration and the single `iter` slot

Python's iterator protocol uses two methods:

- `__iter__` returns an iterator
- `__next__` returns the next item or raises `StopIteration`

MicroPython has a single `iter` slot, plus flags that describe what that slot means.

```text
iter slot meaning is controlled by flags:

  no flag (default)          iter slot is getiter(self) -> iterator
  ITER_IS_ITERNEXT           iter slot is iternext(self) -> next item
  ITER_IS_CUSTOM             iter slot points to custom struct
  ITER_IS_STREAM             iter slot is stream iterator helper
```

For self iterators, where `__iter__` returns `self` and `__next__` advances state, `ITER_IS_ITERNEXT` is the best fit.

- The runtime treats instances as their own iterator.
- It calls the iter slot as iternext.
- It automatically returns `self` from `mp_getiter`.

That avoids generating a separate getiter wrapper function.

### Exceptions in MicroPython: NLR (non local return)

MicroPython implements exceptions using a setjmp/longjmp style mechanism.

- `nlr_push` saves a jump target (like `setjmp`).
- If the code throws, MicroPython jumps back (like `longjmp`).

In C, this looks like:

```c
nlr_buf_t nlr;
if (nlr_push(&nlr) == 0) {
    // normal path
    nlr_pop();
} else {
    // exception path
}
```

When implementing `iternext`, this is critical. The Python level `__next__` raises `StopIteration`, but the runtime level iternext function must return a sentinel `MP_OBJ_STOP_ITERATION` instead.

So we wrap the call, catch `StopIteration`, and translate it into the sentinel.

### Table: special methods to slots

| Python syntax | Special method | MicroPython hook | Enum value |
| --- | --- | --- | --- |
| `a == b` | `__eq__` | `binary_op(lhs,rhs)` | `MP_BINARY_OP_EQUAL` |
| `a != b` | `__ne__` | `binary_op(lhs,rhs)` | `MP_BINARY_OP_NOT_EQUAL` |
| `a < b` | `__lt__` | `binary_op(lhs,rhs)` | `MP_BINARY_OP_LESS` |
| `a <= b` | `__le__` | `binary_op(lhs,rhs)` | `MP_BINARY_OP_LESS_EQUAL` |
| `a > b` | `__gt__` | `binary_op(lhs,rhs)` | `MP_BINARY_OP_MORE` |
| `a >= b` | `__ge__` | `binary_op(lhs,rhs)` | `MP_BINARY_OP_MORE_EQUAL` |
| `hash(a)` | `__hash__` | `unary_op(self)` | `MP_UNARY_OP_HASH` |
| `iter(a)` | `__iter__` | `iter slot + flags` | `ITER_IS_GETITER` or auto self |
| `next(it)` | `__next__` | `iter slot + flags` | `ITER_IS_ITERNEXT` |

## Part 3: Implementation

We'll walk through the feature from user code, to IR, to C, then cover the bug fixes that made it correct on device.

### What the compiler had to learn

Supporting special methods required work in three layers:

1. IR model: `ClassIR` gained feature flags like `has_lt`, `has_hash`, `has_iter`, and `has_next` so later stages can make slot decisions without re scanning method names.
2. IR builder: method names are recognized as special, those flags are set, and class typed locals and parameters are tracked so `o.value` becomes a struct field read.
3. Class emission: the type definition gains slot handlers (`binary_op`, `unary_op`, `iter`) and, for iteration, an iternext wrapper that translates `StopIteration` into `MP_OBJ_STOP_ITERATION`.

All three are required. If you compile `__lt__` but never set the `binary_op` slot, `<` will never call your method.

### Python input

This is the source used in `examples/special_methods.py`.

```python
class Number:
    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        o: Number = other  # type: ignore[assignment]
        return self.value == o.value

    def __ne__(self, other: object) -> bool:
        o: Number = other  # type: ignore[assignment]
        return self.value != o.value

    def __lt__(self, other: Number) -> bool:
        o: Number = other
        return self.value < o.value

    def __le__(self, other: Number) -> bool:
        o: Number = other
        return self.value <= o.value

    def __gt__(self, other: Number) -> bool:
        o: Number = other
        return self.value > o.value

    def __ge__(self, other: Number) -> bool:
        o: Number = other
        return self.value >= o.value

    def __hash__(self) -> int:
        return self.value

    def get_value(self) -> int:
        return self.value


class Counter:
    current: int
    limit: int

    def __init__(self, limit: int) -> None:
        self.current = 0
        self.limit = limit

    def __iter__(self) -> object:
        return self

    def __next__(self) -> int:
        if self.current >= self.limit:
            raise StopIteration()
        val: int = self.current
        self.current = self.current + 1
        return val

    def get_current(self) -> int:
        return self.current
```

### Three stage view 1: `Number.__lt__`

#### IR

```text
def __lt__(other: MP_OBJ_T) -> BOOL:
  c_name: special_methods_Number___lt__
  max_temp: 0
  body:
    o: mp_obj_t = other
    return (self.value < o.value)
```

This IR is doing something subtle.

- It assigns `other` (an `mp_obj_t`) to `o`.
- It then reads `o.value` as if `o` were a `Number` instance.

That only works if the compiler tracks that `o` is class typed. One of the key bug fixes in this feature was teaching the IR builder to remember "this local has class type Number" so attribute access emits struct field reads instead of a generic attribute lookup.

#### C output

```c
static mp_obj_t special_methods_Number___lt___mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    special_methods_Number_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t other = arg0_obj;
    mp_obj_t o = other;
    return (self->value < ((special_methods_Number_obj_t *)MP_OBJ_TO_PTR(o))->value) ? mp_const_true : mp_const_false;
}
```

Read it top to bottom:

1. `self_in` is the boxed Python object.
2. `self` is a typed pointer so `self->value` works.
3. `o` is still an `mp_obj_t`, but we cast it to `special_methods_Number_obj_t *` at the point of field access.
4. The result is a Python `bool`, so we return `mp_const_true` or `mp_const_false`.

### Three stage view 2: `Number.__hash__`

#### IR

```text
def __hash__() -> MP_INT_T:
  c_name: special_methods_Number___hash__
  max_temp: 0
  body:
    return self.value
```

`__hash__` is a plain field read in Python. In MicroPython, hashing is driven through the `unary_op` slot. That means we compile `__hash__` as a normal method, and separately generate a `unary_op` dispatcher to call it.

### Slot wiring: generated `binary_op` and `unary_op` handlers

The compiler generates a slot handler that maps enum values to user methods. Here is the `Number` `binary_op` handler:

```c
static mp_obj_t special_methods_Number_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op == MP_BINARY_OP_EQUAL) {
        return special_methods_Number___eq___mp(lhs_in, rhs_in);
    }
    if (op == MP_BINARY_OP_NOT_EQUAL) {
        return special_methods_Number___ne___mp(lhs_in, rhs_in);
    }
    if (op == MP_BINARY_OP_LESS) {
        return special_methods_Number___lt___mp(lhs_in, rhs_in);
    }
    if (op == MP_BINARY_OP_LESS_EQUAL) {
        return special_methods_Number___le___mp(lhs_in, rhs_in);
    }
    if (op == MP_BINARY_OP_MORE) {
        return special_methods_Number___gt___mp(lhs_in, rhs_in);
    }
    if (op == MP_BINARY_OP_MORE_EQUAL) {
        return special_methods_Number___ge___mp(lhs_in, rhs_in);
    }
    return MP_OBJ_NULL;
}
```

This function is not Python visible. It is the runtime entry point used by the VM.

The same pattern applies to `__hash__`, except it is a unary op:

```c
static mp_obj_t Number_unary_op(mp_unary_op_t op, mp_obj_t self_in) {
    if (op == MP_UNARY_OP_HASH) {
        return Number___hash___mp(self_in);
    }
    return MP_OBJ_NULL;
}
```

That code is short, but it is the whole feature: Python syntax becomes a slot dispatch, and the slot dispatch calls the compiled method.

### Three stage view 3: `Counter.__next__` and iterator slot

#### IR

```text
def __next__() -> MP_INT_T:
  c_name: special_methods_Counter___next__
  max_temp: 0
  body:
    if (self.current >= self.limit):
      raise StopIteration
    val: mp_int_t = self.current
    self.current = (self.current + 1)
    return val
```

This IR includes a `raise`. That matters because the iternext wrapper relies on `__next__` raising `StopIteration` at the right time.

#### C output: `__next__` logic

```c
static mp_obj_t special_methods_Counter___next___mp(mp_obj_t self_in) {
    special_methods_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if ((self->current >= self->limit)) {
        mp_raise_msg(&mp_type_StopIteration, NULL);
    }
    mp_int_t val = self->current;
    self->current = (self->current + 1);
    return mp_obj_new_int(val);
}
```

Two important C details:

- The function returns `mp_obj_t`, even though the IR return type is `MP_INT_T`. We still box the integer with `mp_obj_new_int` because MicroPython calls through the object ABI.
- `raise StopIteration()` becomes `mp_raise_msg(&mp_type_StopIteration, NULL);`, a C call that triggers the exception mechanism.

#### C output: type definition for a self iterator

The `Counter` type uses `MP_TYPE_FLAG_ITER_IS_ITERNEXT`:

```c
MP_DEFINE_CONST_OBJ_TYPE(
    special_methods_Counter_type,
    MP_QSTR_Counter,
    MP_TYPE_FLAG_ITER_IS_ITERNEXT,
    make_new, special_methods_Counter_make_new,
    attr, special_methods_Counter_attr,
    iter, special_methods_Counter_iternext,
    locals_dict, &special_methods_Counter_locals_dict
);
```

This means the `iter` slot is not getiter. It is iternext. The runtime will:

```text
for x in Counter(...):

  it = mp_getiter(obj)
    with ITER_IS_ITERNEXT: it is obj

  loop:
    x = type(obj)->iter(obj)   // iternext
    if x == STOP_ITERATION: break
```

#### C output: iternext wrapper with NLR

```c
static mp_obj_t special_methods_Counter_iternext(mp_obj_t self_in) {
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        mp_obj_t result = special_methods_Counter___next___mp(self_in);
        nlr_pop();
        return result;
    } else {
        mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);
        if (mp_obj_is_subclass_fast(MP_OBJ_FROM_PTR(mp_obj_get_type(exc)), MP_OBJ_FROM_PTR(&mp_type_StopIteration))) {
            return MP_OBJ_STOP_ITERATION;
        }
        nlr_jump(nlr.ret_val);
    }
}
```

The wrapper is the key difference between Python `__next__` and runtime iternext.

- Python signals completion by raising `StopIteration`.
- MicroPython's iterator loop expects a sentinel return.

So we catch that specific exception and convert it.

One more detail matters for correctness. The wrapper checks whether the exception is a `StopIteration` instance (or subclass) and only then returns the sentinel. Everything else is re thrown.

```text
exc = MP_OBJ_FROM_PTR(nlr.ret_val)
exc_type = mp_obj_get_type(exc)
if mp_obj_is_subclass_fast(exc_type, &mp_type_StopIteration):
    return MP_OBJ_STOP_ITERATION
else:
    nlr_jump(nlr.ret_val)
```

### The `return self` bug, and why it was nasty

The `Counter.__iter__` method returns `self`. That sounds simple, but it crosses the Python object boundary.

`self` inside a method is not a raw pointer. It is an `mp_obj_t` value.

The buggy code path treated `return self` as if it were returning an `int` and generated:

```text
mp_obj_new_int(self)
```

On a 32 bit microcontroller that is a fast path to a crash, because it boxes a pointer value as a small int.

The fix is equally small, but it must be deliberate: return the original boxed object, `self_in`.

```c
static mp_obj_t special_methods_Counter___iter___mp(mp_obj_t self_in) {
    special_methods_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return self_in;  // Fixed: was generating mp_obj_new_int(self)
}
```

The `self` local is still used for field access in other methods, but for `return self` we want the boxed handle, not the struct pointer.

### The missing `raise` bug, and the device crash it caused

Another bug was more subtle: `ast.Raise` inside method bodies was not handled by the method statement builder. The compiler quietly dropped the `raise StopIteration()` statement.

What happens then?

- `__next__` never raises.
- The iternext wrapper never returns `MP_OBJ_STOP_ITERATION`.
- A `for` loop becomes infinite.
- On device, that can crash the board due to watchdog resets or memory pressure.

This is the kind of bug that unit tests can miss if they do not execute real iteration on device. Fixing it required adding explicit IR building for raises in methods.

### Class typed locals and parameters: making `o.value` work

The comparisons in `Number` use this pattern:

```python
o: Number = other
return self.value < o.value
```

In MicroPython, a compiled instance stores its fields in a C struct. The fastest way to access `o.value` is a struct field read.

The compiler already knew how to emit struct field reads for `self.value`. It failed for `o.value` when `o` was a local variable or a method parameter of class type.

Symptom:

- `o.value` compiled to `mp_const_none`, or to a generic attribute access that does not match the compiled layout.

Root cause:

- The IR builder tracked "class typed" variables for some contexts, but method bodies were not populating that tracking for locals and parameters.

Fix:

- Track class typed locals and parameters in a dedicated set (for example `_class_typed_params`) while building method bodies.
- Ensure method bodies can see their own class type by registering the class in `_known_classes` before parsing the class body.

The takeaway is that types matter even for locals. If the compiler loses the fact that a variable is a `Number`, you lose the ability to compile `o.value` into a direct struct read.

### Why class registration timing matters

The compiler keeps a registry of known classes during IR building so it can resolve annotations and class types.

If the class is registered after parsing its body, then methods inside the class cannot resolve references to the class type while they are being built. That breaks patterns like `other: Number`.

Registering the class early is a classic frontend fix: populate the symbol table before descending into dependent nodes.



## Device Testing

Special methods affect codegen and runtime behavior, so device testing matters more than usual. Infinite loops and wrong boxing are hard to spot on a desktop but obvious on an ESP32.

Results:

Results:

- All 364 device tests pass on ESP32-C6.
- This includes 24 new `special_methods` tests:

  - 14 comparison operator tests (eq/ne/lt/le/gt/ge with true and false cases)
  - 2 hash tests
  - 1 `get_value` test
  - 3 `Counter` iterator tests (normal iteration, post iteration state, empty counter)
  - 2 free function tests (`compare_numbers`, `sum_counter`)

## Closing

Special methods are the point where "Python code" becomes "runtime behavior". Supporting them in a compiler is less about parsing `def __lt__` and more about wiring the method into the VM's slot dispatch model.

This feature added that wiring for comparisons, hashing, and iteration, and it forced a few correctness fixes in the IR builder and function emitter. The final result is that compiled classes can participate in core Python protocols with fast struct field access and MicroPython compatible runtime entry points.
