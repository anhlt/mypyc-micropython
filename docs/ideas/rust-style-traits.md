# Rust-Style Traits in mypyc-micropython

This proposes Rust-style trait support for `mypyc-micropython` by generating per-trait vtables and using explicit fat pointers only at trait boundaries.
Objects remain unchanged, so there is zero per-object memory cost. Trait-typed values pay an explicit cost: 8 bytes per trait value on ESP32 and one indirect call per trait-dispatched method.

This is a concrete, implementation-ready plan. It fits the current architecture: single inheritance `ClassIR`, existing class vtable generation, and MicroPython's runtime constraints.

## Goals

- Express structural polymorphism across unrelated classes in typed Python.
- Keep object layout stable and compatible with existing generated classes.
- Make dynamic dispatch explicit and localized, like Rust `dyn Trait`.
- Generate C that is readable and debuggable, with clear symbols and IR dumps.
- Keep ROM and SRAM costs predictable on ESP32-class microcontrollers.

## Non-goals

- Multiple inheritance in the MicroPython type system.
- Making traits real MicroPython runtime types.
- `isinstance(obj, Trait)` semantics from interpreted MicroPython.
- Cross-module trait implementations (trait in module A, impl in module B).
- Default method bodies in traits.
- Trait inheritance.
- Generics over traits.

## Current Architecture (What We Must Not Break)

### Class IR Shape

The compiler models classes with single inheritance and a class vtable pointer in the root object layout.
`ClassIR` today (from `src/mypyc_micropython/ir.py`):

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClassIR:
    name: str
    c_name: str
    module_name: str
    base: ClassIR | None = None       # Single inheritance only
    fields: list[FieldIR]
    methods: dict[str, MethodIR]
    virtual_methods: list[str]
    vtable_size: int = 0
    is_dataclass: bool = False
    mp_slots: set[str]
```

Important details:

- The object layout includes a `const <root>_vtable_t *vtable;` in the root struct.
- Derived objects embed the base as a `super` field.
- Virtual dispatch goes through `self->super.vtable->slot(...)`.

### Current Generated C Pattern (Class Dispatch)

This is the existing shape that must remain valid.

```c
// Root class struct has vtable pointer.
typedef struct _parent_obj_t parent_obj_t;
typedef struct _child_obj_t child_obj_t;

typedef struct _parent_vtable_t {
    mp_obj_t (*method1)(mp_obj_t self_in, mp_obj_t arg0);
} parent_vtable_t;

struct _parent_obj_t {
    mp_obj_base_t base;
    const parent_vtable_t *vtable;
    mp_int_t x;
};

// Child embeds parent via super.
struct _child_obj_t {
    parent_obj_t super;
    mp_int_t y;
};

// Vtable is root class's type, populated per-class.
static const parent_vtable_t child_vtable_inst = {
    .method1 = (mp_obj_t (*)(mp_obj_t, mp_obj_t))child_method1_native,
};

// Constructor sets vtable.
static void child_init_native(child_obj_t *self) {
    self->super.vtable = &child_vtable_inst;
}
```

### Why Traits Must Be Separate

MicroPython has no multiple inheritance, and objects embed `mp_obj_base_t` as the first field.
Changing object layout to attach multiple interface vtable pointers would break everything, and it would increase per-object RAM cost.

So traits must not change object layout. That forces a separate trait dispatch mechanism.

## The Problem Traits Solve

Typed Python wants polymorphism without forcing a shared base class. Today you can:

- Use concrete types everywhere, which blocks reuse.
- Use inheritance, which forces a layout and hierarchy.
- Use `typing.Protocol` for type checking, but codegen cannot use it for efficient dispatch.

Traits add a compiler-supported interface layer: structural typing plus fast dispatch in the generated C.

## Cross-Language Research Summary (Why This Design)

| Language | Mechanism | Per-Object Cost | Dispatch Cost | Key Insight |
|----------|-----------|----------------|---------------|-------------|
| C++ | Multiple vtable pointers + thunks | +ptr per base | 1 indirect call | Pointer adjustment via thunks |
| Java | itable / interface search | 0 | O(n) lookup, cached | Needs caching and metadata |
| Scala | JVM interface model | 0 | Same as Java | Deterministic ordering matters |
| Rust | static monomorphization / `dyn Trait` fat pointer | 0 / +word(s) per reference | 0 / 1 indirect call | Fat pointers make dynamic cost explicit |
| Ours | trait vtables + fat pointers at boundaries | 0 per object | type check once, then 1 indirect call | Rust model fits embedded constraints |

Decision: copy the Rust split. Static dispatch when concrete type is known, fat pointer dispatch only when a value is erased to a trait.

## Proposed Design (Opinionated)

### Runtime Model

- Traits are not MicroPython runtime types.
- Runtime values remain normal `mp_obj_t` objects of concrete classes.
- Trait-typed locals and parameters inside compiled C are represented as fat pointers.

Fat pointer layout (ESP32, 32-bit pointers):

```
trait_obj_t (stack local, passed by value)

  +0  mp_obj_t obj
  +4  const trait_vtable_t *vtable
  +8  end
```

Per-object overhead remains unchanged.

### What Is A Trait Boundary

The compiler inserts trait packing only when a value flows into a trait-typed slot:

- Passing into a trait-typed parameter.
- Assigning into a trait-typed local.
- Returning from a function whose native return type is a trait.

After packing, method calls do not re-check type. They dispatch via the stored trait vtable pointer.

### Surface Syntax (User-Facing Python)

Users write normal typed Python. Two ways to define a trait are supported.

Option A: `@trait` decorator (preferred for clarity).

```python
from __future__ import annotations

from mypyc_micropython.traits import trait


@trait
class Drawable:
    def draw(self) -> None: ...
    def area(self) -> float: ...
```

Option B: `typing.Protocol` (accepted).

```python
from __future__ import annotations

from typing import Protocol


class Drawable(Protocol):
    def draw(self) -> None: ...
    def area(self) -> float: ...
```

Implementation registration is explicit via `@implements` (recommended), with optional auto-registration when the compiler can prove it is safe.

```python
from __future__ import annotations

from mypyc_micropython.traits import implements


@implements(Drawable)
class Circle:
    radius: float

    def __init__(self, r: float) -> None:
        self.radius = r

    def draw(self) -> None:
        print("circle")

    def area(self) -> float:
        return 3.14 * self.radius * self.radius
```

Using a trait:

```python
def render(shape: Drawable) -> float:
    shape.draw()
    return shape.area()
```

Trait return types are supported in compiled native code:

```python
def pick(flag: bool, a: Circle, b: Circle) -> Drawable:
    if flag:
        return a
    return b
```

At runtime, this returns a normal `Circle` object as `mp_obj_t`. Only compiled native code carries the fat pointer.

### Dispatch Path Diagram

Dispatch through a trait is always:

```
trait local (fat pointer)
  obj    -> mp_obj_t (concrete object)
  vtable -> trait vtable instance for the dynamic concrete type

call
  vtable->slot(obj, args...)
```

The dynamic type check happens once during packing.

## IR And Codegen Additions

### New IR Definitions (Module Level)

Traits become first-class IR objects stored on `ModuleIR`.

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TraitMethodSigIR:
    """One method signature in a trait definition.

    The signature defines the trait vtable ABI.
    `arg_types` excludes `self`.
    """

    name: str
    arg_types: list[CType]
    ret_type: CType


@dataclass
class TraitIR:
    """A trait (interface) definition.

    No fields, only method signatures.
    `methods` order defines vtable slot layout.
    """

    name: str
    c_name: str
    module_name: str
    methods: list[TraitMethodSigIR]


@dataclass
class TraitImplIR:
    """Records that a specific class implements a specific trait."""

    trait: TraitIR
    cls: ClassIR
    # trait method name -> thunk C symbol
    method_thunks: dict[str, str]


# Added to ModuleIR:
trait_defs: dict[str, TraitIR]
trait_impls: dict[tuple[str, str], TraitImplIR]  # (trait_name, class_c_name)
```

Design choices:

- `TraitIR.methods` order is source order and becomes the vtable layout.
- `trait_impls` key uses `(trait_name, class_c_name)` for deterministic uniqueness.

### New IR Instruction And Expression Forms

Packing is a side-effectful operation and belongs in the prelude instruction list.

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TraitPackIR(InstrIR):
    """Pack a concrete mp_obj_t into a trait fat pointer."""

    dest: TempIR
    src: ValueIR
    trait: TraitIR


@dataclass
class TraitMethodCallIR(ExprIR):
    """Call a trait method via trait vtable."""

    recv: ValueIR  # trait fat pointer value
    trait: TraitIR
    method: str
    args: list[ValueIR]
```

Optional helpers (recommended for clean wrappers and debug output):

```python
@dataclass
class TraitObjGetIR(ExprIR):
    recv: ValueIR
    trait: TraitIR


@dataclass
class TraitIsIR(ExprIR):
    obj: ValueIR
    trait: TraitIR
```

### IR Dump Examples (Expected)

Traits must show up clearly when running `mpy-compile ... --dump-ir text`.

Example dump for `render(shape: Drawable) -> float`:

```text
def render(shape: Drawable) -> MP_FLOAT_T:
  c_name: shapes_render
  locals: {shape: drawable_obj_t}
  body:
    # prelude:
      _tmp0 = pack_trait Drawable from arg0
    call_trait Drawable.draw(_tmp0)
    return call_trait Drawable.area(_tmp0)
```

This requires adding renderers in `src/mypyc_micropython/ir_visualizer.py` for new node types.

### C Type Support For Trait Fat Pointers

The compiler needs to represent a trait fat pointer as a native C type, for locals and native function signatures.
This means extending the internal C type system.

Concrete requirement:

- A trait-typed local has a real C type name like `drawable_obj_t`.
- A native function may accept `drawable_obj_t` by value.
- A native function may return `drawable_obj_t` by value.

Implementation options:

- Add a `CType.TraitObj(trait: TraitIR)` representation.
- Or keep primitive `CType` enums and add a separate `CTypeRef(name: str)` for generated typedef types.

Pick one and thread it through:

- function signatures (`FuncIR`, `MethodIR`)
- locals and temps
- `function_emitter.py` C declarations
- wrapper boxing and unboxing

## Generated C Pattern For Traits (Complete Examples)

The trait code generator produces:

1. One vtable type per trait.
2. One fat pointer type per trait.
3. Thunks that adapt concrete native methods to the trait ABI.
4. One vtable instance per (trait, implementing class).
5. A packer function `trait_from_obj(mp_obj_t)` that selects the right vtable instance.

### A) Trait Definition -> Vtable Type + Fat Pointer Type

Input:

```python
@trait
class Drawable:
    def draw(self) -> None: ...
    def area(self) -> float: ...
```

Output in C (one per trait):

```c
#include "py/obj.h"
#include "py/runtime.h"

typedef struct _drawable_vtable_t drawable_vtable_t;
typedef struct _drawable_obj_t drawable_obj_t;

struct _drawable_vtable_t {
    void (*draw)(mp_obj_t self_in);
    mp_float_t (*area)(mp_obj_t self_in);
};

struct _drawable_obj_t {
    mp_obj_t obj;
    const drawable_vtable_t *vtable;
};
```

Notes:

- Receiver is always `mp_obj_t`.
- Argument and return types follow existing `CType` lowering rules.
- The fat pointer is stack-only. It is never a MicroPython object.

### B) Class Implements Trait -> Thunks + Vtable Instance

Assume the class emitter already produces the concrete object type and native method symbols.
For Circle, it looks like:

- `typedef struct _circle_obj_t circle_obj_t;`
- `extern const mp_obj_type_t circle_type;`
- `static void circle_draw_native(circle_obj_t *self);`
- `static mp_float_t circle_area_native(circle_obj_t *self);`

Trait thunks:

```c
typedef struct _circle_obj_t circle_obj_t;
extern const mp_obj_type_t circle_type;

static void circle_draw_native(circle_obj_t *self);
static mp_float_t circle_area_native(circle_obj_t *self);

static void circle_draw__drawable_thunk(mp_obj_t self_in) {
    circle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    circle_draw_native(self);
}

static mp_float_t circle_area__drawable_thunk(mp_obj_t self_in) {
    circle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return circle_area_native(self);
}

static const drawable_vtable_t drawable__circle_vtable = {
    .draw = circle_draw__drawable_thunk,
    .area = circle_area__drawable_thunk,
};
```

Properties:

- One thunk per method per (trait, class).
- Thunks are small and should live in flash.
- Thunks do no type checking, they assume the packer checked.

### C) Pack Function -> `mp_obj_t` to Fat Pointer

Packing is where runtime checks happen.
The packer is generated per trait per compiled module.
It lists implementers that exist in that module.

```c
static drawable_obj_t drawable_from_obj(mp_obj_t obj) {
    if (mp_obj_is_type(obj, &circle_type)) {
        return (drawable_obj_t){
            .obj = obj,
            .vtable = &drawable__circle_vtable,
        };
    }

    mp_raise_TypeError(MP_ERROR_TEXT("does not implement Drawable"));
}
```

Determinism rule:

- If multiple implementers exist, order checks by most-derived first, then by `ClassIR.c_name` lexical.

### D) Function With Trait Parameter -> Pack Once, Dispatch Many

Python:

```python
def render(shape: Drawable) -> float:
    shape.draw()
    return shape.area()
```

Generated C should separate wrapper ABI (`mp_obj_t`) and native ABI (typed locals and fat pointers).

```c
static mp_float_t mod_render_native(drawable_obj_t shape) {
    shape.vtable->draw(shape.obj);
    return shape.vtable->area(shape.obj);
}

static mp_obj_t mod_render(mp_obj_t shape_in) {
    drawable_obj_t shape = drawable_from_obj(shape_in);
    mp_float_t out = mod_render_native(shape);
    return mp_obj_new_float(out);
}
```

This is the core dispatch shape.

### E) Static Dispatch When Concrete Type Is Known

Python:

```python
def render_circle(c: Circle) -> float:
    c.draw()
    return c.area()
```

Generated native C must be direct calls.

```c
static mp_float_t mod_render_circle_native(circle_obj_t *c) {
    circle_draw_native(c);
    return circle_area_native(c);
}
```

Explicit erasure remains possible:

```python
def render_dyn(c: Circle) -> float:
    x: Drawable = c
    x.draw()
    return x.area()
```

Then the compiler packs at the assignment, not at each call.

### F) Multiple Traits On One Class

Python:

```python
@trait
class Drawable:
    def draw(self) -> None: ...


@trait
class Movable:
    def move(self, dx: int, dy: int) -> None: ...


@implements(Drawable)
@implements(Movable)
class Sprite:
    x: int
    y: int

    def draw(self) -> None:
        print("sprite")

    def move(self, dx: int, dy: int) -> None:
        self.x += dx
        self.y += dy
```

Memory layout diagram:

```
Sprite heap object

  +0  mp_obj_base_t base
  +4  const sprite_vtable_t *vtable      (existing class vtable pointer)
  +8  mp_int_t x
  +12 mp_int_t y

Trait locals (stack)

  drawable_obj_t { obj, &drawable__sprite_vtable }
  movable_obj_t  { obj, &movable__sprite_vtable }
```

The object is unchanged. Trait views are separate.

### G) Trait As Return Type (Native And Wrapper)

Native-to-native code uses fat pointer returns.
Wrapper code returns only `.obj` to MicroPython.

Native:

```c
static drawable_obj_t mod_pick_native(bool flag, mp_obj_t a, mp_obj_t b) {
    if (flag) {
        return drawable_from_obj(a);
    }
    return drawable_from_obj(b);
}
```

Wrapper:

```c
static mp_obj_t mod_pick(mp_obj_t flag_in, mp_obj_t a_in, mp_obj_t b_in) {
    bool flag = mp_obj_is_true(flag_in);
    drawable_obj_t out = mod_pick_native(flag, a_in, b_in);
    return out.obj;
}
```

This keeps the runtime model consistent: Python sees normal objects.

## How This Hooks Into The Existing Pipeline

The repo pipeline is: Python source -> AST -> IRBuilder -> IR -> emitters -> C.
Traits add nodes and one new emission stage.

### IR Builder Changes (`src/mypyc_micropython/ir_builder.py`)

Trait definition detection:

- `@trait` on a class definition.
- Or base class is `typing.Protocol`.

Validation (MVP):

- No fields.
- Only method definitions.
- Method bodies must be `...` or `pass`.
- Disallow `@staticmethod`, `@classmethod`, `@property` in MVP.
- Disallow generics and `TypeVar` in MVP.

Signature extraction:

- Use mypy's analyzed types to convert to `CType` (or your current type mapping).
- Drop `self` from arg types.
- Preserve method order from source.

Lowering:

- Create `TraitIR` and put it in `ModuleIR.trait_defs`.
- Do not create `ClassIR`.
- Do not emit MicroPython type objects for the trait.

Trait method calls:

- If the receiver is trait-typed, lower to `TraitMethodCallIR`.
- If receiver is concrete class-typed, keep existing lowering and direct calls.

Trait boundaries:

- When assigning to a trait-typed local, insert `TraitPackIR` into the prelude.
- When calling a wrapper with a trait-typed param, wrapper inserts `TraitPackIR` before calling native.

### Trait Implementation Registration

This proposal is explicit and deterministic.

- Preferred: `@implements(Trait)` on the class definition.
- Optional: auto-register when the compiler sees a concrete class value packed to a trait and the implementing class set is unambiguous.

Implementation resolution for a class that implements a trait:

- For each trait method name, find the concrete method in `ClassIR.methods` or follow `ClassIR.base` chain.
- Use the resolved `MethodIR` native symbol for thunk calls.
- Record thunk symbols in `TraitImplIR.method_thunks`.

### Trait Code Emission (New Emitter)

Add `src/mypyc_micropython/trait_emitter.py` and invoke it from `src/mypyc_micropython/module_emitter.py`.
Emission order matters because C needs typedefs before use.

Emission order per module:

1. Emit all trait vtable and fat pointer types.
2. Emit all per-impl thunks.
3. Emit all per-impl vtable instances.
4. Emit packers `trait_from_obj()`.
5. Optionally emit `is_<trait>()` helpers.

All symbols should be `static` unless explicitly exported as module functions.

### Function Emitter Changes (`src/mypyc_micropython/function_emitter.py`)

Handle `TraitMethodCallIR`.
Given a receiver expression `recv` of type `<trait>_obj_t`, emit:

- `recv.vtable->slot(recv.obj, ...)`.

For return types:

- If the trait method returns `mp_obj_t`, it returns a normal object.
- If it returns a primitive, return unboxed type.
- If it returns a trait fat pointer, return `<othertrait>_obj_t` by value.

### Wrapper Changes (Trait Args And Returns)

Wrappers are MicroPython ABI.
Native functions are typed ABI.

Rules:

- Wrapper parameters are always `mp_obj_t`.
- If the native expects a trait fat pointer, wrapper packs using `trait_from_obj()`.
- If the native returns a trait fat pointer, wrapper returns `.obj`.

This implies the wrapper generator must understand the new trait `CType`.

### IR Visualization Changes (Required)

Any new IR node added to `src/mypyc_micropython/ir.py` must be supported in `src/mypyc_micropython/ir_visualizer.py`.
Otherwise dumps will show unknown nodes and debugging becomes guesswork.

Add renderers for:

- `TraitIR` and `TraitMethodSigIR`
- `TraitImplIR`
- `TraitPackIR`
- `TraitMethodCallIR`
- optional helper nodes

## MicroPython Interaction

Traits are not MicroPython types.
That keeps ROM usage low and avoids touching MicroPython internals.

Consequences:

- No `isinstance(obj, Trait)` in interpreted code.
- No trait objects in the heap.

Optional helper generation:

- Emit `is_<trait>(obj) -> bool` as a normal exported module function.

Example:

```c
static mp_obj_t mod_is_drawable(mp_obj_t obj) {
    if (mp_obj_is_type(obj, &circle_type)) {
        return mp_const_true;
    }
    return mp_const_false;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_is_drawable_obj, mod_is_drawable);
```

## Performance And Memory

Numbers assume ESP32 32-bit pointers.

Per-object cost: 0 bytes.

Per trait-typed local or parameter in native code:

- `mp_obj_t` (4 bytes)
- vtable pointer (4 bytes)
- total 8 bytes

Per vtable instance (per trait per implementer):

- `N_methods * 4` bytes

Example:

- Trait has 4 methods.
- Module has 10 implementers.

Vtable instances consume about `4 * 4 * 10 = 160` bytes plus alignment.

Packing cost:

- a chain of `mp_obj_is_type` checks
- O(k) where k is number of implementers known in this module
- paid once per boundary, not per call

This is acceptable for embedded.

## Error Handling And Diagnostics

Compile-time errors (compiler errors via `CompilationResult(errors=[...])`):

- Trait has fields.
- Trait method missing annotations.
- Unsupported decorators or features in trait definition.
- `@implements(Trait)` on a non-compiled class.
- Method signature mismatch between trait and implementer.

Runtime errors:

- Packing fails, raise `TypeError` with message `does not implement <TraitName>`.

Opinionated rule: keep runtime error messages short and deterministic.

## Determinism Rules

Vtable slot order:

- Source order in the trait definition.
- Never alphabetical.

Packer check order:

- Most-derived classes before bases (to handle subclass instances correctly).
- Break ties by `ClassIR.c_name` lexical.

This makes generated code stable across builds.

## Phased Implementation Plan (With Estimates)

Estimates are focused engineer-days.

### Phase A: MVP Trait Dispatch (2 to 3 days)

Scope: traits within a single module, trait-typed params and locals, vtable dispatch, packer generation.

Tasks:

1. Add `TraitIR`, `TraitMethodSigIR`, `TraitImplIR` to `src/mypyc_micropython/ir.py` and attach to `ModuleIR`.
   Effort: 0.5d
2. Add IR visualization support in `src/mypyc_micropython/ir_visualizer.py`.
   Effort: 0.25d
3. IRBuilder: detect traits (`@trait` or Protocol), build `TraitIR`, skip `ClassIR` emission for trait defs.
   Effort: 0.5d
4. IRBuilder: trait boundaries and trait method call lowering (`TraitPackIR`, `TraitMethodCallIR`).
   Effort: 0.75d
5. Add `src/mypyc_micropython/trait_emitter.py` and integrate with `src/mypyc_micropython/module_emitter.py`.
   Effort: 0.75d
6. FunctionEmitter: emit `TraitMethodCallIR`.
   Effort: 0.25d
7. Unit tests in `tests/test_ir_builder.py` and `tests/test_compiler.py`.
   Effort: 0.5d

Acceptance:

- `mpy-compile` supports compiling a module containing traits and trait calls.
- `--dump-ir text` shows trait nodes cleanly.
- Generated C includes vtable types, thunks, vtable instances, and packers.

### Phase B: Static Dispatch And Pack Elision (1 day)

Scope: reduce pointless packing and keep direct calls when possible.

Tasks:

1. Track whether a value is already a trait fat pointer and skip repacking.
   Effort: 0.25d
2. Minimal flow map for locals and temps to eliminate pack/unpack patterns.
   Effort: 0.5d
3. Emit direct calls in obvious concrete contexts.
   Effort: 0.25d

Acceptance:

- No repeated `trait_from_obj()` calls for the same value in the same function where not needed.
- Concrete-typed code stays direct.

### Phase C: Polish (1 to 2 days)

Scope: developer experience, explicit registration, helper functions, device tests.

Tasks:

1. Add `@implements(Trait)` recognition and deterministic impl registration.
   Effort: 0.5d
2. Emit `is_<trait>(obj) -> bool` helpers.
   Effort: 0.25d
3. Better compile-time and runtime error messages.
   Effort: 0.25d
4. Add `examples/traits_drawable.py` and update `run_device_tests.py`.
   Effort: 0.5d
5. Run device tests on ESP32.
   Effort: 0.25d

Acceptance:

- Example module works on device.
- Device tests pass.

## What Is Deferred (And Why)

### Cross-Module Trait Implementations

Packer generation needs the implementer set.
Across modules you need a registry or link-time aggregation.
That is real engineering work and it touches module boundaries.

### Default Methods

Default methods require emitting code bodies from trait definitions.
That means trait defs become codegen entities, not just signatures.
Defer.

### Trait Inheritance

Trait inheritance requires composing vtables or flattening method sets.
It is doable, but it creates a second inheritance system.
Defer.

### `isinstance(obj, Trait)`

MicroPython's runtime does not know traits.
Emulating it needs global registries and costs RAM.
Defer.

### Generics Over Traits

This is effectively monomorphization.
It is out of scope for the current compiler architecture.

## Open Questions

1. Trait fat pointer return ABI
   Returning an 8-byte struct by value should work with GCC for the ESP32 targets we care about.
   If it fails on a target ABI, switch to an out-param calling convention for trait returns.
2. Caching packing results
   For loops over `list[Drawable]`, packing per element costs a type check chain.
   A tiny cache keyed by `(mp_obj_type_t*, trait)` can eliminate repeated checks.
   This needs careful RAM budgeting and is not MVP.
3. Builtin implementers
   Allowing builtins (like `list`) to implement traits is possible but it needs special casing.
   MVP supports compiled classes only.

## Appendix: Minimal Helper Decorators

Users want `@trait` and `@implements` imports.
The runtime can keep them as no-ops; the compiler interprets them.

This is the minimal shape the compiler will look for:

```python
from __future__ import annotations

from typing import Any, Callable, TypeVar

T = TypeVar("T")


def trait(cls: type[T]) -> type[T]:
    return cls


def implements(proto: type[Any]) -> Callable[[type[T]], type[T]]:
    def dec(cls: type[T]) -> type[T]:
        return cls
    return dec
```

The compiler should not depend on runtime behavior here.
It should match decorator names and arguments in the AST.
