# How We Compile Python Inheritance to C: Vtables, Layout, and Pointer Casting

*How we map Python class inheritance to C structs and function pointers in `mypyc-micropython`, while keeping dispatch fast enough for ESP32-class devices.*

---

## The Challenge

Python classes feel high-level and dynamic. C is low-level and explicit. MicroPython sits between them, but it still needs concrete memory layouts, concrete function symbols, and concrete call paths.

For inheritance, we need to preserve three behaviors from Python:

- Child classes reuse parent state
- Child methods can override parent methods
- Calls can still behave correctly when types are used polymorphically

Our compiler solves this with struct embedding and vtables.

If you are new to compiler internals, here is the mental shortcut for this whole post:
Python inheritance says "a child object is also a parent object." In C, we make that statement true by
physically putting the parent layout at the beginning of the child layout, then using function-pointer
tables to decide which method implementation should run.

---

## The Big Idea: Vtable-Based Dispatch

Each class gets a table of function pointers (a vtable). Each object stores a pointer to its class's vtable.

At call time, you can dispatch through that table:

```c
self->vtable->increment(self)
```

In current generated code, we still use direct calls in many places where static type is known, but the vtable layout is established as the foundation for polymorphic behavior.

This distinction matters for understanding the implementation:

- **Direct call path**: fastest path when compiler already knows exact type
- **Vtable-ready layout**: structural setup that keeps polymorphism possible

So even where we do not dispatch through vtable at every call site today, we still generate data structures
that preserve inheritance semantics and keep future dispatch strategies open.

---

## Running Example: `Counter` and `BoundedCounter`

```python
class Counter:
    value: int
    step: int

    def __init__(self, start: int, step: int) -> None:
        self.value = start
        self.step = step

    def increment(self) -> int:
        self.value += self.step
        return self.value

    def reset(self) -> None:
        self.value = 0

    def get(self) -> int:
        return self.value


class BoundedCounter(Counter):
    min_val: int
    max_val: int

    def __init__(self, start: int, step: int, min_val: int, max_val: int) -> None:
        self.value = start
        self.step = step
        self.min_val = min_val
        self.max_val = max_val

    def increment(self) -> int:
        new_val: int = self.value + self.step
        if new_val <= self.max_val:
            self.value = new_val
        return self.value
```

`BoundedCounter` overrides `increment`, but should still inherit `get` and `reset`.

This is exactly the scenario where naive code generation often fails. A naive emitter can handle
"method defined on this class," but inheritance requires handling "method not defined here, but should
still be callable here." The rest of the article focuses on how we make that behavior explicit in C.

---

## Object and Vtable Layout in C

```c
struct _counter_Counter_vtable_t {
    mp_int_t (*increment)(counter_Counter_obj_t *self);
    void (*reset)(counter_Counter_obj_t *self);
    mp_int_t (*get)(counter_Counter_obj_t *self);
};

struct _counter_BoundedCounter_vtable_t {
    mp_int_t (*increment)(counter_BoundedCounter_obj_t *self);
    void (*reset)(counter_BoundedCounter_obj_t *self);
    mp_int_t (*get)(counter_BoundedCounter_obj_t *self);
};

struct _counter_Counter_obj_t {
    mp_obj_base_t base;
    const counter_Counter_vtable_t *vtable;
    mp_int_t value;
    mp_int_t step;
};

struct _counter_BoundedCounter_obj_t {
    counter_Counter_obj_t super;
    mp_int_t min_val;
    mp_int_t max_val;
};
```

The key design choice is this field:

```c
counter_Counter_obj_t super;
```

Placing the parent struct first gives the child the same initial memory layout as the parent. That is the basis for safe pointer reinterpretation in single inheritance.

Think of this as a contract: any function that knows how to operate on `Counter` can safely read the first
part of a `BoundedCounter`, because that first part is literally a `Counter` struct in memory.

---

## Memory View

Here is the same `BoundedCounter` object shown as a full layout diagram.

```
Memory Address ->  [BoundedCounter Instance]
                  +---------------------------------------------+
0x1000            | mp_obj_base_t base                          |
                  | (MicroPython object header / type pointer)  |
                  +---------------------------------------------+
0x1008            | const Counter_vtable_t *vtable              |
                  | (points to BoundedCounter vtable instance)  |
                  +---------------------------------------------+
0x1010            | mp_int_t value                              |
                  | (inherited from Counter)                    |
                  +---------------------------------------------+
0x1018            | mp_int_t step                               |
                  | (inherited from Counter)                    |
                  +---------------------------------------------+
0x1020            | mp_int_t min_val                            |
                  | (declared in BoundedCounter)                |
                  +---------------------------------------------+
0x1028            | mp_int_t max_val                            |
                  | (declared in BoundedCounter)                |
                  +---------------------------------------------+
```

And here is where that vtable pointer leads:

```
self->super.vtable
      |
      v
+--------------------------------------------------+
| counter_BoundedCounter_vtable_inst               |
|  increment -> counter_BoundedCounter_increment   |
|  reset     -> counter_Counter_reset (cast)       |
|  get       -> counter_Counter_get (cast)         |
+--------------------------------------------------+
```

The first 4 slots (`base`, `vtable`, `value`, `step`) are layout-compatible with `Counter`.
That is exactly why parent logic can operate on child instances safely.

Another way to say it: inheritance becomes a prefix guarantee. If the prefix is stable, parent behavior is
stable. Child-specific fields are appended after that prefix and do not break parent code.

---

## Construction and Access Paths

When allocating a child object, constructor code sets the inherited vtable slot path:

```c
self->super.vtable = (const counter_Counter_vtable_t *)&counter_BoundedCounter_vtable_inst;
```

The compiler computes this path generically based on inheritance depth:

- Base class: `self->vtable`
- Child class: `self->super.vtable`
- Grandchild: `self->super.super.vtable`

In `mypyc-micropython`, this is derived by `_vtable_access_path()` so class emission does not hardcode depth-specific logic.

That helper is important for maintainability. Without it, each new inheritance depth would require
special-case code generation logic. With it, the emitter simply asks for "the correct access path" and
emits what it receives.

---

## Method Dispatch Flow

Python calls go through MicroPython wrappers, then into native generated functions.

```c
static mp_obj_t counter_BoundedCounter_increment_mp(mp_obj_t self_in) {
    counter_BoundedCounter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(counter_BoundedCounter_increment_native(self));
}
```

Flow:

1. Python calls `bounded.increment()`
2. MicroPython resolves method in class locals table
3. Wrapper converts `mp_obj_t` to typed pointer
4. Native function executes
5. Result is boxed back to `mp_obj_t`

For statically known self-type, code can call native methods directly. For dynamic method exposure, wrappers bridge runtime object model and generated C functions.

### Full Dispatch Chain (Step-by-Step)

```
Python code: bounded.increment()
        |
        v
MicroPython method lookup in BoundedCounter locals_dict
        |
        v
counter_BoundedCounter_increment_mp(mp_obj_t self_in)
        |
        v
counter_BoundedCounter_increment_native(counter_BoundedCounter_obj_t *self)
        |
        v
Direct field updates and return mp_int_t
        |
        v
Wrapper boxes result -> mp_obj_new_int(...)
```

For inherited methods that are not overridden (for example `get`), the lookup lands on the parent-backed entry exposed by the child type table.

This is where the runtime model and compile-time model meet. Compile time decides which method entries
belong in each class table; runtime lookup uses that table to resolve what Python code can call.

---

## Deep Dive: The Pointer Casting Mechanism

This is the core technique that lets inherited methods remain callable without cloning parent implementations.

Cloning parent code into each child would bloat generated output and make behavior harder to keep consistent.
Pointer-cast reuse keeps one implementation and wires it into child slots where layout compatibility allows.

### Problem

Parent method signatures use parent pointer types:

```c
static mp_int_t counter_Counter_get_native(counter_Counter_obj_t *self) {
    return self->value;
}
```

But child vtables expect child pointer signatures:

```c
mp_int_t (*get)(counter_BoundedCounter_obj_t *self)
```

### Technique

Assign parent implementation into child vtable slot with explicit cast:

```c
static const counter_BoundedCounter_vtable_t counter_BoundedCounter_vtable_inst = {
    .increment = counter_BoundedCounter_increment_native,
    .get = (mp_int_t (*)(counter_BoundedCounter_obj_t *))counter_Counter_get_native,
};
```

You can read this cast as: "use `Counter_get_native`, but treat it as a function that accepts
`BoundedCounter*` so it fits this vtable slot type."

### Why It Works Here

- Child embeds parent struct at offset 0
- Parent fields remain at identical offsets
- Parent code reads only parent layout
- Single inheritance keeps layout simple and predictable

At runtime, passing `BoundedCounter*` to parent method logic works because the beginning of both objects is layout-compatible.

Important nuance: this is not "casts are always safe." This is "this cast is safe under this generated-layout
contract." The safety comes from disciplined struct layout generation, not from casting by itself.

### Compatibility Sketch

```
Counter* view (expects):
  [base][vtable][value][step]

BoundedCounter* actual:
  [base][vtable][value][step][min_val][max_val]

Shared prefix is identical -> parent method reads correct fields.
```

### Runtime Call Example

```c
counter_BoundedCounter_obj_t *bc = /* ... */;
mp_int_t result = bc->super.vtable->get(bc);
```

The `get` slot points to the cast parent implementation. Inside `counter_Counter_get_native`,
`self->value` resolves to the same offset where `value` lives in the child object.

### Practical Compiler Impact

The low-level mechanism already existed in emitted C patterns. The missing piece was method discovery across inheritance chains.

Compiler fix direction:

- Before: class locals table listed only methods declared directly on child
- After: class locals table includes inherited parent methods unless overridden

This made inherited methods callable from Python without duplicating native implementations.

That change is easy to underestimate. From a user perspective, it flips inheritance from "partially working"
to "language-consistent": if a method exists on the parent and is not overridden, calling it on the child
works exactly as expected.

---

## Multi-Level Inheritance: Going Deeper

If we add one more level, nothing fundamentally changes; the same rules repeat.

```python
class C(BoundedCounter):
    extra: int
```

Generated C shape (simplified):

```c
struct _counter_C_obj_t {
    counter_BoundedCounter_obj_t super;
    mp_int_t extra;
};
```

Now access paths become one level longer:

- Vtable path: `self->super.super.vtable`
- Inherited `Counter` field: `self->super.super.value`
- Inherited `BoundedCounter` field: `self->super.min_val`
- Local field on `C`: `self->extra`

Visualizing the nested prefix:

```
[C Instance]
  [Counter prefix]
    base
    vtable
    value
    step
  [BoundedCounter extension]
    min_val
    max_val
  [C extension]
    extra
```

The compiler does not special-case each depth. It computes depth-based access paths and emits the correct `super.` chain for fields and vtable access.

This scales naturally when the hierarchy grows. A deeper tree increases path length, but it does not require
new conceptual machinery.

---

## Why This Matters on Microcontrollers

On ESP32-class targets, this model is practical because:

- Vtables are static data (flash-friendly)
- Object overhead is small (data + one pointer)
- Native method bodies avoid interpreter overhead
- Layout is predictable, which helps performance and debugging

It keeps object-oriented semantics while staying close to C's cost model.

In embedded systems, predictability is often more valuable than peak abstraction. This approach gives both:
predictable low-level layout and familiar high-level class behavior.

---

## What's Next

With inheritance and callable inherited methods in place, useful next steps are:

1. `super()` support in child methods
2. More true vtable call sites where static type is unknown
3. Interface-like dispatch extensions if language surface grows

---

## Try It Yourself

```bash
# Compile Python to C module
mpy-compile examples/counter.py -o modules/usermod_counter/

# Build and flash firmware
make build BOARD=ESP32_GENERIC_C3
make flash BOARD=ESP32_GENERIC_C3

# Run device tests
python run_device_tests.py --port /dev/ttyACM0
```

Open generated files under `modules/usermod_*/` to inspect struct layouts, wrappers, and vtable initialization.

---

## Appendix: Pointer Cheat Sheet

| Syntax | Meaning |
|--------|---------|
| `int *p` | `p` points to an integer |
| `*p` | value pointed to by `p` |
| `p->field` | field access through pointer |
| `&x` | address of `x` |
| `const T *p` | pointer to read-only `T` |
| `T (*f)(int)` | function pointer |
| `Obj **pp` | pointer to a pointer |
| `(Type *)expr` | explicit cast to `Type *` |
| `(*fn)(arg)` | call through a function pointer |
| `const VTable *vt` | pointer to immutable vtable data |

Key call pattern:

```c
self->vtable->increment(self)
```

Read left to right:

1. `self` is a pointer to the current object
2. `self->vtable` dereferences object pointer, then reads its `vtable` field
3. `self->vtable->increment` gets the function pointer stored in that slot
4. `(self)` passes the object pointer as the first argument

### Parent vs Child Pointer View

```c
counter_Counter_obj_t *as_parent = (counter_Counter_obj_t *)child_ptr;
```

This cast is valid in this design because child objects embed parent layout at offset 0.

### Why `->` Instead of `.`

- Use `.` when you have a struct value: `obj.value`
- Use `->` when you have a struct pointer: `obj_ptr->value`

In generated methods, `self` is a pointer, so `self->field` is the standard form.

### Function Pointer Slot Example

```c
typedef mp_int_t (*inc_fn_t)(counter_BoundedCounter_obj_t *self);

typedef struct {
    inc_fn_t increment;
} counter_BoundedCounter_vtable_t;
```

`increment` is not a direct function. It is a variable that stores a function address.

### Cast Pattern Used for Inherited Methods

```c
.get = (mp_int_t (*)(counter_BoundedCounter_obj_t *))counter_Counter_get_native,
```

This tells the compiler to treat the parent implementation as compatible with the child slot type.

When reading generated code, you can interpret this as "inherit method implementation by reference" rather
than "inherit by re-generating source." It is a wiring decision, not a logic rewrite.

### Minimal End-to-End Dispatch Example

```c
counter_BoundedCounter_obj_t *bc = /* allocated object */;
mp_int_t out = bc->super.vtable->get(bc);
```

- `bc->super.vtable` selects the vtable pointer
- `->get` selects function pointer slot
- `(bc)` calls that function with current object
