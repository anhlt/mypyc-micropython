# How We Compile Python Inheritance to C: A Deep Dive into Vtables and Pointers

When you write `class BoundedCounter(Counter)` in Python, inheritance feels magical and effortless. But when compiling Python to C for microcontrollers like the ESP32, there's no "magic" — only pointers, memory layouts, and careful bookkeeping. In this post, I'll explain how we implement Python-style inheritance using **vtable-based virtual dispatch**, with a focus on understanding the pointers that make it all work.

*Target audience: Python developers curious about what happens under the hood, with minimal C knowledge.*

---

## The Challenge: Python Classes on a Microcontroller

MicroPython lets you run Python on microcontrollers, but it has a catch: it's interpreted, which means slower execution and higher memory usage. Our compiler, `mypyc-micropython`, takes a different approach — it **compiles typed Python directly to C**, which then gets compiled to native machine code and flashed to the device.

But C doesn't have classes. It has structs and functions. So how do we get Python's inheritance, method overriding, and polymorphism?

---

## The Big Idea: Vtables (Virtual Method Tables)

The solution is a technique borrowed from C++ and other object-oriented languages: **vtable-based dispatch**. Here's the intuition:

> Each class has a table of function pointers — one for each virtual method. Every object carries a pointer to its class's table. When you call a method, you follow the pointer to the table, then follow another pointer to the actual function.

This is the same mechanism that makes `obj.method()` work polymorphically in C++, Java, and yes — our compiled Python.

---

## Memory Layout: What Does an Object Look Like?

Let's start with a concrete example. Here's our Python code:

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

    def decrement(self) -> int:
        self.value -= self.step
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

`BoundedCounter` inherits from `Counter` and **overrides** the `increment` method to add bounds checking.

### The Generated C Structs

Here's what the compiler generates (simplified for clarity):

```c
// === The Vtable Types ===
// Each vtable is a struct containing function pointers

struct _counter_Counter_vtable_t {
    mp_int_t (*increment)(counter_Counter_obj_t *self);
    mp_int_t (*decrement)(counter_Counter_obj_t *self);
    void (*reset)(counter_Counter_obj_t *self);
    mp_int_t (*get)(counter_Counter_obj_t *self);
};

struct _counter_BoundedCounter_vtable_t {
    mp_int_t (*increment)(counter_BoundedCounter_obj_t *self);
    mp_int_t (*decrement)(counter_BoundedCounter_obj_t *self);
    void (*reset)(counter_BoundedCounter_obj_t *self);
    mp_int_t (*get)(counter_BoundedCounter_obj_t *self);
};

// === The Object Structs ===

struct _counter_Counter_obj_t {
    mp_obj_base_t base;                    // MicroPython's base object header
    const counter_Counter_vtable_t *vtable; // ← POINTER to vtable
    mp_int_t value;                        // Field: value
    mp_int_t step;                         // Field: step
};

struct _counter_BoundedCounter_obj_t {
    counter_Counter_obj_t super;           // ← Parent struct EMBEDDED here
    mp_int_t min_val;                      // Field: min_val
    mp_int_t max_val;                      // Field: max_val
};
```

### Key Insight: Struct Embedding for Inheritance

Notice how `BoundedCounter` doesn't repeat the `value` and `step` fields. Instead, it embeds the **entire parent struct** as its first member:

```c
counter_Counter_obj_t super;  // Parent's data lives here
```

This is the C idiom for inheritance. Because `super` is the first field:
- A pointer to `BoundedCounter` can be treated as a pointer to `Counter`
- The parent's fields (`value`, `step`) live at the same memory offsets
- The parent's methods work on the child object

---

## Visual Memory Layout

Here's what a `BoundedCounter` instance looks like in memory:

```
Memory Address →  [BoundedCounter Instance]
                  ┌─────────────────────────────────────┐
0x1000            │ mp_obj_base_t base                  │ ← MicroPython header
                  │ (type pointer, refcount)            │
                  ├─────────────────────────────────────┤
0x1008            │ const Counter_vtable_t *vtable      │ ← POINTER to vtable
                  ├─────────────────────────────────────┤
0x1010            │ mp_int_t value                      │ ← From Counter
                  ├─────────────────────────────────────┤
0x1018            │ mp_int_t step                       │ ← From Counter
                  ├─────────────────────────────────────┤
0x1020            │ mp_int_t min_val                    │ ← BoundedCounter's own
                  ├─────────────────────────────────────┤
0x1028            │ mp_int_t max_val                    │ ← BoundedCounter's own
                  └─────────────────────────────────────┘

Total size: 48 bytes (on 64-bit system)
```

Notice the **vtable pointer** at offset 8. Every object has one, and it points to the vtable for its *actual* class (not necessarily the type of the variable holding it).

---

## The Vtable Instances: Where Methods Live

Each class has a **static vtable instance** — a global constant struct filled with function pointers. Here's what they look like:

```c
// Counter's vtable — all methods point to Counter's implementations
static const counter_Counter_vtable_t counter_Counter_vtable_inst = {
    .increment = counter_Counter_increment_native,
    .decrement = counter_Counter_decrement_native,
    .reset = counter_Counter_reset_native,
    .get = counter_Counter_get_native,
};

// BoundedCounter's vtable — note the mix of own and parent methods
static const counter_BoundedCounter_vtable_t counter_BoundedCounter_vtable_inst = {
    .increment = counter_BoundedCounter_increment_native,  // ← Own implementation
    .decrement = counter_BoundedCounter_decrement_native,  // ← Own implementation
    .reset = (void (*)(counter_BoundedCounter_obj_t *))counter_Counter_reset_native,
                                                           // ↑ Cast of parent's method
    .get = (mp_int_t (*)(counter_BoundedCounter_obj_t *))counter_Counter_get_native,
                                                           // ↑ Cast of parent's method
};
```

### The Function Pointer Cast

Notice those ugly casts on `reset` and `get`:

```c
(void (*)(counter_BoundedCounter_obj_t *))counter_Counter_reset_native
```

This is necessary because:
- `reset` was originally defined taking `Counter *`
- But the vtable expects a function taking `BoundedCounter *`
- These are compatible (due to struct embedding), but C's type system needs convincing
- The cast tells the compiler: "Trust me, this is safe"

At runtime, when `reset` is called through the vtable, the `BoundedCounter *` pointer is passed, but the function treats it as `Counter *` — which works because the parent's fields are at the same offsets!

---

## Construction: Setting Up the Vtable Pointer

When you create an object, the constructor assigns the vtable pointer. Here's `BoundedCounter`'s `make_new`:

```c
static mp_obj_t counter_BoundedCounter_make_new(
    const mp_obj_type_t *type, 
    size_t n_args, 
    size_t n_kw, 
    const mp_obj_t *args
) {
    // Allocate memory
    counter_BoundedCounter_obj_t *self = mp_obj_malloc(counter_BoundedCounter_obj_t, type);
    
    // CRITICAL: Set the vtable pointer!
    self->super.vtable = (const counter_Counter_vtable_t *)&counter_BoundedCounter_vtable_inst;
    //                      ↑↑↑↑↑↑↑↑
    //                      Note: casting to parent's vtable type
    
    // Initialize fields to defaults
    self->super.value = 0;
    self->super.step = 0;
    self->min_val = 0;
    self->max_val = 0;
    
    // Call __init__ with provided arguments
    // ... (init code)
    
    return MP_OBJ_FROM_PTR(self);
}
```

### The Vtable Access Path

Notice we set `self->super.vtable`, not `self->vtable`. Why?

Because `BoundedCounter` doesn't have its own vtable field! It inherited the one from `Counter`, nested inside the `super` struct. The compiler computes the correct access path:

- **Base class** (`Counter`): `self->vtable`
- **Child class** (`BoundedCounter`): `self->super.vtable`
- **Grandchild**: `self->super.super.vtable`

This is handled by the `_vtable_access_path()` helper in our compiler:

```python
def _vtable_access_path(self) -> str:
    """Compute the C access path for the vtable pointer.
    
    Base class: 'vtable'
    Child class: 'super.vtable'
    Grandchild: 'super.super.vtable'
    """
    depth = 0
    cls = self.class_ir
    while cls.base:
        depth += 1
        cls = cls.base
    if depth == 0:
        return "vtable"
    return "super." * depth + "vtable"
```

---

## Method Dispatch: How Calls Actually Work

When you write `counter.increment()` in Python, what happens at the C level?

### Native Method Calls (Within the Same Class)

If the compiler can see that you're calling a method on `self` of the same class, it can optimize:

```c
// Inside BoundedCounter_increment_native:
self->value += self->step;  // Direct field access
```

No vtable indirection needed — the compiler knows exactly which struct type `self` is.

### MicroPython Wrapper Methods

But Python is dynamic. Someone could write:

```python
def use_counter(c):
    return c.increment()  # Could be Counter OR BoundedCounter!
```

For these cases, we generate **wrapper functions** that MicroPython can call:

```c
static mp_obj_t counter_BoundedCounter_increment_mp(mp_obj_t self_in) {
    // Convert MicroPython object to our struct pointer
    counter_BoundedCounter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    
    // Call the native implementation
    return mp_obj_new_int(counter_BoundedCounter_increment_native(self));
}
```

These wrappers are what get registered in MicroPython's `locals_dict` (the method table that Python code actually uses).

### The Full Dispatch Chain

Here's the complete flow when Python calls `bounded.increment()`:

```
1. Python code: bounded.increment()
                  ↓
2. MicroPython looks up "increment" in bounded's type locals_dict
   → Finds: counter_BoundedCounter_increment_obj (wrapper function)
                  ↓
3. Wrapper converts mp_obj_t → counter_BoundedCounter_obj_t*
                  ↓
4. Wrapper calls: counter_BoundedCounter_increment_native(self)
                  ↓
5. Native method executes: self->value += self->step (direct field access)
```

### What About Polymorphic Dispatch?

If we wanted true vtable dispatch (calling through the vtable pointer), it would look like:

```c
// Hypothetical vtable dispatch:
mp_int_t result = self->super.vtable->increment(self);
//                 ↑      ↑      ↑         ↑
//                 │      │      │         └── Pass self as argument
//                 │      │      └──────────── Function pointer from vtable
//                 │      └─────────────────── Vtable pointer
//                 └────────────────────────── Object pointer
```

Currently, our compiler generates **direct calls** for methods within the same object (step 4 above). The vtable is set up and ready for polymorphic dispatch, but we haven't yet implemented calling through it — that's a future optimization for when we need to support interfaces or more complex polymorphism.

---

## Multi-Level Inheritance: Going Deeper

What if we had `class C(BoundedCounter)`? The pattern extends naturally:

```c
struct _counter_C_obj_t {
    counter_BoundedCounter_obj_t super;  // Embeds BoundedCounter
    // ... C's own fields
};

// Vtable access path: self->super.super.vtable
```

The memory layout becomes:

```
[C Instance]
├─ base (MicroPython header)
├─ vtable pointer (from Counter)
├─ value (from Counter)
├─ step (from Counter)
├─ min_val (from BoundedCounter)
├─ max_val (from BoundedCounter)
└─ ... C's fields
```

And the `_vtable_access_path()` correctly computes `super.super.vtable`.

---

## A Complete Example: Point and Point3D

Let's look at a cleaner example using `@dataclass`:

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

    def distance_squared(self) -> int:
        return self.x * self.x + self.y * self.y

@dataclass
class Point3D(Point):
    z: int

    def distance_squared_3d(self) -> int:
        return self.x * self.x + self.y * self.y + self.z * self.z
```

### The Generated C

```c
// Point vtable type
struct _point_Point_vtable_t {
    mp_int_t (*distance_squared)(point_Point_obj_t *self);
};

// Point object
struct _point_Point_obj_t {
    mp_obj_base_t base;
    const point_Point_vtable_t *vtable;
    mp_int_t x;
    mp_int_t y;
};

// Point3D vtable type — extends parent's methods
struct _point_Point3D_vtable_t {
    mp_int_t (*distance_squared)(point_Point3D_obj_t *self);      // Inherited
    mp_int_t (*distance_squared_3d)(point_Point3D_obj_t *self);   // New
};

// Point3D object
struct _point_Point3D_obj_t {
    point_Point_obj_t super;  // Parent embedded
    mp_int_t z;
};
```

### Accessing Parent Fields in Child Methods

When `Point3D.distance_squared_3d()` accesses `self.x`, the generated C is:

```c
static mp_int_t point_Point3D_distance_squared_3d_native(point_Point3D_obj_t *self) {
    return ((self->super.x * self->super.x) + 
            (self->super.y * self->super.y) + 
            (self->z * self->z));
}
```

The compiler computes the full access path: `super.x` for inherited fields, just `z` for own fields.

---

## Key Takeaways

### 1. Inheritance = Struct Embedding
```c
struct Child {
    Parent super;   // Parent data embedded as first member
    int child_field;
};
```

### 2. Virtual Methods = Function Pointers in a Table
```c
struct Vtable {
    int (*method)(Object *self);
};
```

### 3. Every Object Carries a Pointer to Its Class's Vtable
```c
struct Object {
    const Vtable *vtable;  // Set at construction, never changes
    // ... fields
};
```

### 4. Method Overriding = Different Function in Child's Vtable
The child's vtable has the overriding function pointer; the parent's has the original.

### 5. Casting Makes It Work
Parent methods can operate on child objects because:
- The child embeds the parent's struct layout
- A cast tells the compiler "trust me, this pointer is compatible"
- At runtime, memory layouts match

---

## Why This Matters for Microcontrollers

On an ESP32 with 512KB RAM:

- **Vtables are static constants** — stored in flash, not RAM
- **Each object is just its data + one pointer** — minimal overhead
- **Native methods are direct C functions** — no interpreter overhead
- **Memory layout is cache-friendly** — fields accessed together are stored together

Compared to a pure Python object (which needs a dict for attributes, a type pointer, GC header, etc.), our compiled objects are tiny and fast.

---

## How Inherited Methods Become Callable: The Pointer Casting Mechanism

When `BoundedCounter` inherits from `Counter`, it should be able to call `get()` and `reset()`—methods defined in the parent. But how does this work at the C level? The answer lies in **struct embedding** and **pointer casting**.

### The Problem: Method Visibility vs. Method Implementation

There's a subtle distinction in our compiler:

1. **Method Implementation**: The actual C function that executes the method logic
2. **Method Visibility**: Whether Python code can find and call the method

The implementation was always there. When we compile `Counter`, we generate `Counter_get_native()` and `Counter_reset_native()`. These functions work with `Counter*` pointers. The question is: how do we make them accessible on `BoundedCounter` instances?

### The Solution: Parent Pointers Work on Children

Recall that `BoundedCounter` embeds `Counter` as its first member:

```c
struct _counter_BoundedCounter_obj_t {
    counter_Counter_obj_t super;   // ← Parent is FIRST
    mp_int_t min_val;
    mp_int_t max_val;
};
```

This creates a **subtyping relationship** in C. Because `super` is the first field:

- A `BoundedCounter*` points to the same memory location as a `Counter*`
- The parent's fields (`value`, `step`) are at identical offsets in both structs
- Any code expecting `Counter*` can safely receive `BoundedCounter*`

This is the same principle that makes C++ inheritance work.

### Pointer Casting: The Magic That Makes It Work

When `BoundedCounter` needs to expose `get()` to Python, it doesn't create a new implementation. It **reuses** `Counter`'s implementation through pointer casting:

```c
// Parent's implementation (works on Counter*)
static mp_int_t counter_Counter_get_native(counter_Counter_obj_t *self) {
    return self->value;  // Accesses field at offset 16
}

// Child exposes parent's implementation
static const counter_BoundedCounter_vtable_t counter_BoundedCounter_vtable_inst = {
    .get = (mp_int_t (*)(counter_BoundedCounter_obj_t *))counter_Counter_get_native,
          // ↑ Cast tells compiler: "Trust me, this pointer is compatible"
};
```

The cast `(mp_int_t (*)(counter_BoundedCounter_obj_t *))` does two things:

1. **Changes the type signature** so it matches the vtable's expected type
2. **Tells the compiler not to worry** about the type mismatch

At runtime, when `get()` is called:

```c
counter_BoundedCounter_obj_t *bc = /* ... */;
// Call through vtable
mp_int_t result = bc->super.vtable->get(bc);
//                     ↑
//                     bc is BoundedCounter*, but get() receives it as Counter*
//                     This works because both point to same memory location!
```

Inside `Counter_get_native`, the code accesses `self->value`. Since `value` is at offset 16 in both `Counter` and `BoundedCounter` (because `super` is first), it reads the correct field!

### Memory Layout Visualization

Here's the critical insight—both structs share the same initial layout:

```
Counter* (points to 0x1000):
┌─────────────────────────┐
│ base header (0x1000)    │
├─────────────────────────┤
│ vtable ptr (0x1008)     │ ← same offset
├─────────────────────────┤
│ value (0x1010)          │ ← same offset
├─────────────────────────┤
│ step (0x1018)           │ ← same offset
└─────────────────────────┘

BoundedCounter* (points to 0x1000):
┌─────────────────────────┐
│ super (Counter part)    │ ← same memory as above!
│   ├── base header       │
│   ├── vtable ptr        │
│   ├── value             │
│   └── step              │
├─────────────────────────┤
│ min_val (0x1020)        │ ← extra fields after parent
├─────────────────────────┤
│ max_val (0x1028)        │
└─────────────────────────┘
```

When we cast `BoundedCounter*` to `Counter*`, we're not moving any data. We're just telling the compiler: "Treat this pointer as pointing to a Counter." Since the memory layout matches at the beginning, all parent field accesses work correctly.

### The MicroPython Wrapper Layer

The native functions work with typed pointers. But MicroPython calls methods through generic `mp_obj_t` objects. We bridge this with **wrapper functions**:

```c
// MicroPython wrapper for Counter.get
static mp_obj_t counter_Counter_get_mp(mp_obj_t self_in) {
    // Convert generic MicroPython object to typed pointer
    counter_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    
    // Call native implementation
    mp_int_t result = counter_Counter_get_native(self);
    
    // Box result back to MicroPython object
    return mp_obj_new_int(result);
}
```

For `BoundedCounter` to expose `get()`, we simply reference `Counter`'s existing wrapper:

```c
static const mp_rom_map_elem_t counter_BoundedCounter_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_increment), MP_ROM_PTR(&counter_BoundedCounter_increment_obj) },
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&counter_Counter_get_obj) },  // ← Same wrapper!
};
```

When Python calls `bc.get()`:

1. MicroPython looks up "get" in `BoundedCounter`'s `locals_dict`
2. Finds `counter_Counter_get_obj` (parent's wrapper)
3. Wrapper receives `bc` as `mp_obj_t`
4. Converts to `counter_Counter_obj_t*` (valid cast!)
5. Calls `Counter_get_native()` which accesses `self->value`
6. Returns correct result because memory layout matches

### Why This Required a Compiler Change

The mechanism always worked at the C level. The issue was in the **compiler's method discovery**:

- Before: Compiler only listed methods defined directly on `BoundedCounter`
- After: Compiler walks inheritance chain and includes all parent methods

This is why the fix was minimal—we just needed to **advertise** the inherited methods, not create new implementations. The pointer casting and struct embedding already made it possible.

### The Complete Picture: Inheritance as Composition

What we're doing is essentially:

```python
# Python view
class BoundedCounter(Counter):
    pass

# C implementation view
class BoundedCounter:
    super = Counter()  # Composition!
    min_val = 0
    max_val = 0

# But with memory layout magic so that:
BoundedCounter_instance.super is at the same address as BoundedCounter_instance
```

This is why C programmers say "inheritance is composition with automatic forwarding." The struct embedding gives us the composition, and the pointer casting gives us the automatic forwarding.

### Implications for Method Overriding

When `BoundedCounter` overrides `increment()`:

```c
static const counter_BoundedCounter_vtable_t counter_BoundedCounter_vtable_inst = {
    .increment = counter_BoundedCounter_increment_native,  // ← Own implementation
    .get = (mp_int_t (*)(counter_BoundedCounter_obj_t *))counter_Counter_get_native,
                                              // ↑ Parent's implementation
};
```

The child vtable has:
- **Overridden methods**: Point to child's implementation
- **Inherited methods**: Point to parent's implementation (with cast)

This is exactly how C++ virtual functions work, and it's how we achieve polymorphism.

### Casting Safety

You might worry: is the cast safe? In this specific case, yes:

1. **Standard-layout structs**: Our generated structs are standard-layout (no virtual inheritance, no multiple inheritance complications)
2. **First member guarantee**: C guarantees that a pointer to a struct points to its first member
3. **No offset calculations needed**: Parent fields are at identical offsets in parent and child

The C standard explicitly allows this pattern. It's the foundation of how C++ implements single inheritance.

## What's Next?

Our vtable infrastructure and inherited method propagation are now working. Future improvements include:

1. **`super()` support**: Allow child methods to explicitly call parent's implementation (e.g., `super().reset()`)
2. **True vtable dispatch**: Use `self->vtable->method(self)` for polymorphic cases where the exact type isn't known at compile time
3. **Interface support**: Multiple interface inheritance via additional vtable pointers

These will build on the struct embedding and pointer casting foundation described in this post.

---

## Try It Yourself

Our compiler is open source. If you have an ESP32:

```bash
# Compile Python to C
mpy-compile examples/counter.py -o modules/usermod_counter/

# Build and flash firmware
make build BOARD=ESP32_GENERIC_C3
make flash BOARD=ESP32_GENERIC_C3

# Test on device
mpremote connect /dev/ttyACM0 run test_device_inventory.py
```

The generated C lives in `modules/usermod_*/`. Open it up and see the vtables in action!

---

*Happy compiling!*

---

## Appendix: Pointer Cheat Sheet

For readers new to C pointers, here's a quick reference for reading the code:

| Syntax | Meaning |
|--------|---------|
| `int *p` | `p` is a pointer to an integer |
| `*p` | Dereference `p` — get the value it points to |
| `p->field` | Access `field` of the struct that `p` points to |
| `&x` | Get the address of `x` (a pointer to `x`) |
| `const T *p` | `p` is a read-only pointer to `T` |
| `T (*f)(int)` | `f` is a pointer to a function taking `int`, returning `T` |
| `void (*reset)(Obj *)` | `reset` is a function pointer; function takes `Obj*`, returns nothing |

The key pattern in this post:
```c
self->vtable->increment(self)
│    │        │         │
│    │        │         └── Arguments to the function
│    │        └── Function pointer from vtable
│    └── Pointer to vtable (stored in object)
└── Object pointer (the instance)
```
