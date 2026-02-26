# 23. Private Methods, @final, and Constant Folding

*Three ways `mypyc-micropython` turns "this can't happen" into smaller and faster C code.*

---

## Table of Contents

1. [Part 1: Compiler Theory](#part-1-compiler-theory)
2. [Part 2: C Background](#part-2-c-background)
3. [Part 3: Implementation](#part-3-implementation)
4. [Benchmarks](#benchmarks)
5. [Device Testing](#device-testing)
6. [Closing](#closing)

---

# Part 1: Compiler Theory

Ahead-of-time compilers win when they can replace runtime decisions with compile-time facts. In Python, many decisions are intentionally deferred to runtime: attribute lookup is dynamic, methods can be replaced, and subclassing can change dispatch.

This post is about three compiler facts that tighten those rules:

| Fact the compiler learns | What it removes | What becomes possible |
|---|---|---|
| "This method is private to the class" | external access and override paths | no MicroPython wrapper, no registration in the type dictionary |
| "This class is final" | subclassing and virtual dispatch | no vtable pointer in instances, no vtable struct |
| "This attribute is Final" | runtime variability of its value | constant folding into literals in native code |

There is a common thread: visibility and finality are not just style choices. They shape the dynamic surface area that the runtime must support.

## Why "private" matters in an embedded AOT setting

For compiled code running on MicroPython, "public" is a promise to the runtime:

- The method must be callable from the REPL.
- The method must be discoverable by attribute lookup on the object.
- The method must accept `mp_obj_t` arguments and return `mp_obj_t`.

That promise forces extra generated code.

If the compiler can prove a method is never called from the runtime surface, it can stop generating that glue. In `mypyc-micropython`, double-underscore methods are treated as class-private, and that gives the compiler permission to remove the MP-callable wrapper and the registration hooks.

## Why "final" matters to dispatch

In object-oriented code generation, dynamic dispatch is the big fixed cost. It is not expensive because of the function pointer call itself. It is expensive because you need infrastructure:

- a per-class function pointer table (a vtable)
- a per-instance pointer to the vtable (so you can dispatch through the instance)
- method layouts that account for overrides

If a class is declared `@final`, there is no override story. That lets the compiler erase virtual dispatch machinery for that class.

## How mypyc-style compilers use these annotations

This is not unique to this project. mypyc and other typed Python AOT compilers lean on similar facts:

- private members can be lowered as internal-only calls
- final classes and final methods can be devirtualized
- final constants can become literals

The difference here is that the cost model is harsher. On a 32-bit microcontroller, a single pointer per instance and a pile of wrapper functions can be a noticeable fraction of memory and flash.

---

# Part 2: C Background

This section fills in the C and MicroPython runtime pieces that appear in the generated code in Part 3.

## 2.1 Vtables are function pointer tables

A vtable is a struct of function pointers. An instance stores a pointer to its class vtable, and a virtual method call is an indirect call through that table.

Minimal shape:

```c
typedef struct {
    mp_int_t (*compute)(Calculator_obj_t *self, mp_int_t x);
} Calculator_vtable_t;

typedef struct {
    mp_obj_base_t base;
    const Calculator_vtable_t *vtable;
    mp_int_t value;
} Calculator_obj_t;
```

This is a classic C representation of dynamic dispatch. It is also a concrete memory cost: on a 32-bit MCU, `vtable` is 4 bytes per instance.

## 2.2 Native functions vs MP wrapper functions

When this compiler emits C, it often emits two layers for a method:

- a typed native function, for calls inside compiled code
- a MicroPython wrapper, so the runtime can call it with `mp_obj_t` arguments

The wrapper exists because MicroPython is dynamically typed and represents values as `mp_obj_t`. The wrapper's job is to convert between "Python objects" and "native C values".

## 2.3 Boxing and unboxing overhead

"Boxing" means turning a C value into an `mp_obj_t`, usually by allocating or tagging it. "Unboxing" means extracting the C value back out.

Common patterns:

```c
mp_int_t x = mp_obj_get_int(arg0_obj);    // unbox
return mp_obj_new_int(result);            // box
```

Those conversions are pure overhead when the call is internal to compiled code, because the native types are already known.

## 2.4 What `static` means in C

At file scope, `static` gives internal linkage. The symbol is not exported to the linker as a public name for other translation units.

For this project, `static` is also a statement of intent:

- `_native` methods are typically `static` because they are internal implementation details
- MP wrappers and registration objects are also often `static`, but they are still reachable through MicroPython's type tables

## 2.5 What `MP_DEFINE_CONST_FUN_OBJ` does

MicroPython represents callable functions as objects. A C function becomes a MicroPython callable by wrapping it in a function object.

For a two-argument callable, the macro looks like this in generated code:

```c
MP_DEFINE_CONST_FUN_OBJ_2(name_obj, name_mp);
```

Conceptually:

- `name_mp` is a C function with the MicroPython calling convention (`mp_obj_t` args)
- `name_obj` is a constant object that describes how to call it

The object is what gets placed into the type's `locals_dict` so `obj.method(...)` can be resolved and invoked from the runtime.

## 2.6 What `locals_dict` is

Every generated type has a dictionary of attributes it exposes to the runtime. That is the type's `locals_dict`.

For methods, `locals_dict` maps the method name QSTR to the function object:

```c
static const mp_rom_map_elem_t Calculator_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_compute), MP_ROM_PTR(&Calculator_compute_obj) },
};
```

If a method is not in `locals_dict`, it is not visible to normal MicroPython attribute lookup.

---

# Part 3: Implementation

This compiler feature set is best understood as three optimization tiers. Each tier is "the same program" at Python level, with increasingly constrained dynamic behavior that the compiler exploits.

The format below follows the same bridge used across this repo's blogs:

1. Python input
2. IR output (`mpy-compile --dump-ir text`)
3. Generated C excerpt

## Tier 1: `__` Private Methods (no MP wrapper)

### Stage A: Python input

```python
class Calculator:
    value: int
    def __init__(self, v: int) -> None:
        self.value = v
    def __compute(self, x: int) -> int:
        return self.value + x * x
    def compute(self, x: int) -> int:
        return self.__compute(x)
```

### Stage B: IR output

Class summary:

```text
Class: Calculator (c_name: private_methods_Calculator)
    Fields:
      value: int (MP_INT_T)
    Methods:
      def __init__(v: MP_INT_T) -> VOID
      [private] def __compute(x: MP_INT_T) -> MP_INT_T
      def compute(x: MP_INT_T) -> MP_INT_T
```

Function IR for `__compute`:

```text
def __compute(x: MP_INT_T) -> MP_INT_T:
  c_name: private_methods_Calculator___compute
  max_temp: 0
  body:
    return (self.value + (x * x))
```

The important IR fact is the `[private]` marker. It is not "name mangling" for readability. It is a permission slip to change what gets emitted.

Compile-time enforcement matters here. If code outside the class tries to call `obj.__compute(...)`, the compiler rejects it. That is what makes it safe to remove runtime visibility.

### Stage C: generated C

Private method gets only a native function. No wrapper, no function object, no vtable entry, no `locals_dict` registration:

```c
// __compute: native only -- no MP wrapper, no vtable entry
static mp_int_t private_methods_Calculator___compute_native(
    private_methods_Calculator_obj_t *self, mp_int_t x) {
    return (self->value + (x * x));
}

// compute: has both native + MP wrapper
static mp_int_t private_methods_Calculator_compute_native(
    private_methods_Calculator_obj_t *self, mp_int_t x) {
    return private_methods_Calculator___compute_native(self, x);
}
static mp_obj_t private_methods_Calculator_compute_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    private_methods_Calculator_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t x = mp_obj_get_int(arg0_obj);
    return mp_obj_new_int(private_methods_Calculator_compute_native(self, x));
}
MP_DEFINE_CONST_FUN_OBJ_2(private_methods_Calculator_compute_obj, private_methods_Calculator_compute_mp);

// vtable: only compute, no __compute
static const private_methods_Calculator_vtable_t private_methods_Calculator_vtable_inst = {
    .compute = private_methods_Calculator_compute_native,
};

// locals_dict: only compute, no __compute
static const mp_rom_map_elem_t private_methods_Calculator_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_compute), MP_ROM_PTR(&private_methods_Calculator_compute_obj) },
};
```

What this buys you:

| Aspect | Public method | `__` private method |
|---|---|---|
| Callable from REPL | Yes | No (compile-time error if attempted) |
| `_mp` wrapper | Yes | No |
| `MP_DEFINE_CONST_FUN_OBJ_*` | Yes | No |
| Entry in `locals_dict` | Yes | No |
| Vtable entry | Maybe (if virtual) | No |

The runtime surface shrinks. Internal compiled calls still remain direct C calls, so you do not lose speed.

## Tier 2: `@final` Class Devirtualization

This tier targets the per-instance vtable pointer and the per-class vtable struct.

### Stage A: Python input

```python
from typing import final

@final
class FastCounter:
    count: int
    step: int
    def __init__(self, step: int) -> None:
        self.count = 0
        self.step = step
    def increment(self) -> int:
        self.count += self.step
        return self.count
```

### Stage B: IR output

Class summary:

```text
Class: FastCounter (c_name: private_methods_FastCounter)
    @final
    Fields:
      count: int (MP_INT_T)
      step: int (MP_INT_T)
    Methods:
      @final def __init__(step: MP_INT_T) -> VOID
      @final def increment() -> MP_INT_T
      @final def reset() -> VOID
      @final def get() -> MP_INT_T
```

Function IR for `increment`:

```text
def increment() -> MP_INT_T:
  c_name: private_methods_FastCounter_increment
  max_temp: 0
  body:
    self.count += self.step
    return self.count
```

The signal is the class-level `@final`. The compiler does not need to plan for overrides, so it can erase virtual dispatch for this type.

### Stage C: generated C

The most visible effect is what is missing.

```c
// No vtable struct for FastCounter! (compare with Calculator which has one)
struct _private_methods_FastCounter_obj_t {
    mp_obj_base_t base;
    mp_int_t count;
    mp_int_t step;
};
// No vtable pointer in struct -- saves 4 bytes per instance on 32-bit MCU
```

ASCII memory layout comparison (32-bit mental model):

```text
Calculator instance (vtable-backed)

  +0x00  base.type  -> &private_methods_Calculator_type
  +0x04  vtable     -> &private_methods_Calculator_vtable_inst
  +0x08  value      (mp_int_t)

FastCounter instance (@final, devirtualized)

  +0x00  base.type  -> &private_methods_FastCounter_type
  +0x04  count      (mp_int_t)
  +0x08  step       (mp_int_t)
```

This is not a micro-optimization. On a heap full of tiny objects, one pointer field adds up.

Important boundary: `@final` does not mean "not callable". These methods still get MP wrappers and still live in `locals_dict`, because the runtime must be able to call them from normal MicroPython code.

### What about @final classes that inherit?

One question that comes up immediately: what happens when a `@final` class inherits from a non-final parent?

```python
class Animal:
    name: str
    def speak(self) -> str:
        return self.name

@final
class Cat(Animal):
    color: str
    def speak(self) -> str:
        return self.name
    def purr(self) -> str:
        return self.color
```

PEP 591 is clear: a `@final` class **can** inherit from a non-final parent. The `@final` decorator only prevents further subclassing of `Cat`, not Cat's own inheritance.

#### What mypy enforces

| Scenario | Allowed? | mypy error |
|---|---|---|
| `@final class Cat(Animal)` | YES | None |
| `class Kitten(Cat)` where Cat is `@final` | NO | `Cannot inherit from final class "Cat"` |
| Override `@final` method in child | NO | `Cannot override final attribute "locked"` |
| Call parent's `@final` method from child | YES | None |

Since our compiler runs mypy in strict mode before code generation, all three prohibited cases are caught at the type-checking stage. No additional checks are needed in the IR builder or emitter.

#### What the compiler generates

This is the interesting part. When `Cat` is `@final`, we clear its `virtual_methods` list and mark all its own methods `is_final=True`. But `Cat` inherits from `Animal`, and `Animal` defined a vtable with `speak` in it.

Tracing through the IR:

```
Animal.virtual_methods = ['speak']
Animal.get_vtable_entries() = [('speak', Animal.speak)]

Cat.virtual_methods = []            (cleared by @final)
Cat.get_vtable_entries() = [('speak', Animal.speak)]  (inherited from parent!)
```

The `get_vtable_entries()` method walks up to the parent first, then adds from the child's `virtual_methods`. Since `Cat`'s list is empty, the parent's entries pass through unchanged.

This means `Cat` still gets a vtable instance in the generated C:

```c
// Animal defines the vtable layout
struct _Animal_vtable_t {
    mp_obj_t (*speak)(Animal_obj_t *self);
};

struct _Animal_obj_t {
    mp_obj_base_t base;
    const Animal_vtable_t *vtable;  // <-- vtable pointer lives here
    mp_obj_t name;
};

// Cat embeds Animal (struct inheritance)
struct _Cat_obj_t {
    Animal_obj_t super;  // contains base + vtable pointer + name
    mp_obj_t color;
};

// Cat MUST populate the vtable (for polymorphism)
static const Cat_vtable_t Cat_vtable_inst = {
    .speak = (mp_obj_t (*)(Cat_obj_t *))Cat_speak_native,
};

// In make_new:
self->super.vtable = (const Animal_vtable_t *)&Cat_vtable_inst;
```

#### Why the vtable is still needed

This looks like it contradicts the Tier 2 optimization ("no vtable for `@final` classes"). But it does not. The rule is:

- A `@final` **root** class (no parent) skips the vtable entirely. No vtable struct, no vtable pointer, no vtable instance. This is `FastCounter`.
- A `@final` **child** class still needs the parent's vtable, because polymorphic code may call `animal.speak()` on a `Cat` instance through the parent type's vtable pointer.

The `@final` child still benefits from the optimization in a different way: **Cat's own new methods (`purr`) are not added to the vtable.** Only the inherited slots are preserved. And no further subclass can extend or override Cat's methods.

```
+---------------------------+     +---------------------------+
| Animal (non-final)        |     | Cat (@final, child)       |
|                           |     |                           |
| vtable: { speak }         |     | vtable: { speak }         |
| struct: base + vtable +   |     | struct: Animal super +    |
|         name              |     |         color             |
| locals_dict: speak        |     | locals_dict: speak, purr  |
+---------------------------+     +---------------------------+
                                  purr is NOT in vtable
                                  (Cat is @final, no override possible)
```

---

## Tier 3: `Final` Attribute Constant Folding

This tier is about eliminating loads and making generated code more literal.

### Stage A: Python input

```python
from typing import Final

class Config:
    MAX_ITERS: Final[int] = 1000
    SCALE: Final[int] = 2
    value: int
    def __init__(self, v: int) -> None:
        self.value = v
    def scaled_value(self) -> int:
        return self.value * self.SCALE
    def is_within_limit(self, n: int) -> bool:
        return n < self.MAX_ITERS
```

### Stage B: IR output

Class summary:

```text
Class: Config (c_name: private_methods_Config)
    Fields:
      MAX_ITERS: int (MP_INT_T) = 1000 [Final]
      SCALE: int (MP_INT_T) = 2 [Final]
      value: int (MP_INT_T)
```

IR for `scaled_value` (note that it still reads like `self.SCALE`):

```text
def scaled_value() -> MP_INT_T:
  c_name: private_methods_Config_scaled_value
  max_temp: 0
  body:
    return (self.value * self.SCALE)
```

The constant folding happens after this stage. The IR can remain "semantic" and the emitter can choose to replace specific field reads with literals when the `Final` guarantee holds.

### Stage C: generated C

The generated code stops loading the field and just uses the literal value:

```c
static mp_int_t private_methods_Config_scaled_value_native(
    private_methods_Config_obj_t *self) {
    return (self->value * 2);  // self.SCALE constant-folded to 2
}

static bool private_methods_Config_is_within_limit_native(
    private_methods_Config_obj_t *self, mp_int_t n) {
    return (n < 1000);  // self.MAX_ITERS constant-folded to 1000
}
```

Two consequences are worth calling out:

- Speed: you remove a load and any attribute access scaffolding that would have existed in a more dynamic model.
- Semantics: `Final` is the contract that stops you from changing `SCALE` later, which is what makes the literal substitution correct.

---

# Benchmarks

All timings below come from real ESP32-C6 device testing.

## External MP wrapper overhead vs internal native calls

```
=== EXTERNAL vs INTERNAL method call (100,000 calls each) ===
  External (REPL -> public_add via MP wrapper): 762,151us
  Internal (run_public -> public_add_native):   22,108us
  MP wrapper overhead: 34.47x slower

Per-call cost:
  External: 7.62us/call
  Internal: 0.22us/call
  Wrapper overhead: 7.4us/call
```

Table view:

| Path | Total time (100,000 calls) | Per call | Notes |
|---|---:|---:|---|
| External, MP wrapper | 762,151us | 7.62us | unbox args, call native, box result |
| Internal, native call | 22,108us | 0.22us | typed direct C call |
| Delta | 740,043us | 7.4us | wrapper overhead |

This explains why Tier 1 matters even though internal performance does not change. A private method removes the external wrapper path entirely.

## Native vs vanilla Python

```
=== NATIVE vs VANILLA PYTHON (100x1000 method calls) ===
  Native public:  22,136us
  Native private: 22,089us
  Vanilla Python: 1,235,218us
  Speedup (native vs vanilla): 55.9x
```

Two points:

- "Native public" and "native private" are the same speed internally because both resolve to direct C calls inside compiled code. The compiler does not route internal calls through MP wrappers.
- The private method still matters because it prevents the 7.4us/call external path from existing, and it shrinks the generated module (no wrapper function, no function object, no dict entry).

## `@final` FastCounter vs vanilla

```
=== @final FastCounter vs VANILLA (10000 calls) ===
  Native @final:  75,862us
  Vanilla Python: 163,685us
  Speedup: 2.16x
```

This result is smaller than the wrapper benchmark because it targets a different cost center. `@final` reduces object layout and dispatch machinery, it does not remove boxing when you call the method from the runtime.

---

# Device Testing

- Device test status: 328/333 tests pass (98.5%) on ESP32-C6.
- `private_methods` module tests: all 11 tests PASS.
- Device runner note: `run_device_tests.py` includes a serial port contention fix so repeated test runs do not fight over the port.

This project does not treat desktop compilation as proof. The output runs inside MicroPython on a 32-bit MCU, so device results are part of the definition of done.

---

# Closing

The theme across these three tiers is simple: the compiler cannot optimize what it cannot assume.

- `__` private methods reduce the runtime surface area, so the compiler can stop generating wrapper plumbing.
- `@final` erases override machinery, so instances can drop the vtable pointer and the class can drop the vtable struct.
- `Final` attributes turn field reads into literals, so the emitter can constant-fold arithmetic and comparisons.

None of these change Python syntax. They change what the compiler is allowed to believe.
