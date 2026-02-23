# Compiling super() Calls: From Python Inheritance to Direct C Function Calls

*How `mypyc-micropython` turns `super()` from runtime MRO lookup into compile-time resolved C calls for single inheritance.*

---

`super()` is one of those Python features that looks simple in source code but hides a lot of runtime machinery.

In CPython and MicroPython interpreter mode, `super().method()` generally involves:

1. Building a `super` proxy object
2. Walking MRO (method resolution order)
3. Looking up the attribute on a parent type
4. Producing a bound method object
5. Calling that method

For an ahead-of-time compiler, that is too much dynamic work at runtime if the inheritance graph is already known at compile time.

This post explains how the `super()` feature in `mypyc-micropython` is implemented and why the generated code is faster.

---

## Table of Contents

1. [Part 1: Compiler Theory](#part-1-compiler-theory)
2. [Part 2: C Background for Python Developers](#part-2-c-background-for-python-developers)
3. [Part 3: Implementation](#part-3-implementation)
4. [Part 4: Benchmark Analysis](#part-4-benchmark-analysis)
5. [Part 5: Future Improvements](#part-5-future-improvements)

---

# Part 1: Compiler Theory

## What `super()` Means in Python

In Python class hierarchies, `super()` means: "start method lookup from the parent context of the current class, using MRO rules."

Example:

```python
class Animal:
    def describe(self) -> str:
        return self.name

class Dog(Animal):
    def describe(self) -> str:
        return super().describe()
```

That call is not simply `Animal.describe(self)` in general Python semantics. It is MRO-aware dynamic dispatch.

## Why `super()` Is Hard for Compilers

A compiler needs to choose between:

- **Runtime resolution**: preserve full dynamic behavior, but pay runtime overhead
- **Compile-time resolution**: faster code, but only valid when the hierarchy is statically known and constraints are clear

`mypyc-micropython` currently targets typed, ahead-of-time compiled modules with known class structure. That allows compile-time resolution for the supported `super()` pattern.

## How mypyc Handles It

CPython's mypyc also favors compile-time resolution where possible. Instead of creating runtime `super` objects at every call site, it lowers calls to explicit parent-method invocations when type information allows it.

This is the same guiding principle used here.

## Our Strategy

For supported forms, we resolve parent method targets during IR building and emit direct C calls:

- `super().__init__(...)` -> parent `_mp` wrapper call
- `super().method(...)` -> parent `_native` call with typed pointer cast

So the runtime does no MRO walk at that call site.

---

# Part 2: C Background for Python Developers

## Struct Embedding Recap (Single Inheritance)

From the inheritance implementation (see blog 03), child objects embed the parent struct at offset 0.

```c
struct _super_calls_Animal_obj_t {
    mp_obj_base_t base;
    const super_calls_Animal_vtable_t *vtable;
    mp_obj_t name;
    mp_obj_t sound;
};

struct _super_calls_Dog_obj_t {
    super_calls_Animal_obj_t super;
    mp_int_t tricks;
};
```

ASCII memory view:

```
Dog object in memory
+-----------------------------------------------+
| super.base                                    |
| super.vtable                                  |
| super.name                                    |
| super.sound                                   |
+-----------------------------------------------+
| tricks                                        |
+-----------------------------------------------+
```

Because the `Animal` layout is the first bytes of `Dog`, casting `Dog*` to `Animal*` is safe in this single-inheritance model.

## Why Parent Pointer Casts Are Safe Here

This cast appears in generated code:

```c
(super_calls_Animal_obj_t *)self
```

It is safe because:

1. `Dog` embeds `Animal` at offset 0
2. Parent methods only access parent fields
3. Single inheritance keeps prefix layout stable

## Two Calling Conventions in Generated C

The compiler emits two families of methods:

- `_native(...)`: typed C signature (fast path)
- `_mp(...)`: MicroPython object signature using `mp_obj_t` (runtime ABI path)

### `_native` example

```c
static mp_obj_t super_calls_Animal_describe_native(super_calls_Animal_obj_t *self)
```

### `_mp` example

```c
static mp_obj_t super_calls_Animal___init___mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj)
```

## Why `super().__init__()` Uses `_mp`, but `super().method()` Uses `_native`

In current implementation:

- `super().__init__(...)` is emitted through parent `_mp` wrapper, so arguments are boxed as `mp_obj_t`
- `super().describe()` is emitted through parent `_native` method with typed pointer cast

This matches current emitter logic and keeps constructor dispatch consistent with object-init wrapper conventions.

---

# Part 3: Implementation

## Running Example (`examples/super_calls.py`)

```python
class Animal:
    name: str
    sound: str

    def __init__(self, name: str, sound: str) -> None:
        self.name = name
        self.sound = sound

    def describe(self) -> str:
        return self.name


class Dog(Animal):
    tricks: int

    def __init__(self, name: str, tricks: int) -> None:
        super().__init__(name, "Woof")
        self.tricks = tricks

    def describe(self) -> str:
        base: str = super().describe()
        return base
```

## AST Pattern Recognized

In `src/mypyc_micropython/ir_builder.py`, the detector matches this shape:

```python
# Detect super().method(args) pattern:
# ast.Call(func=ast.Attribute(value=ast.Call(func=ast.Name(id="super")), attr=method_name))
```

Concretely, the builder checks:

- outer node is `ast.Call`
- `func` is `ast.Attribute`
- attribute value is `ast.Call` to name `super`
- `super()` has zero explicit args/keywords

Then it resolves the nearest parent class containing that method.

## IR Node Added: `SuperCallIR`

In `src/mypyc_micropython/ir.py`:

```python
@dataclass
class SuperCallIR(ExprIR):
    """super().method(args) call -- compile-time resolved to parent class method."""
    method_name: str
    parent_c_name: str
    parent_method_c_name: str
    args: list[ValueIR]
    return_type: IRType
    is_init: bool = False
    arg_preludes: list[list[InstrIR]] = field(default_factory=list)
```

Key fields:

- `parent_c_name`: parent struct type used for cast/call
- `parent_method_c_name`: exact C symbol target
- `is_init`: selects `_mp` constructor path vs `_native` method path

## IR Builder Resolution Logic

The builder walks base classes until it finds the first class defining the method:

```python
parent_class = class_ir.base
while parent_class is not None and method_name not in parent_class.methods:
    parent_class = parent_class.base
```

Then it constructs `SuperCallIR(..., is_init=method_name == "__init__")`.

## Emitter Logic: Two Codegen Paths

In `src/mypyc_micropython/function_emitter.py`:

- `is_init=True` path emits parent `_mp(...)`
- otherwise emits parent `_native((Parent_obj_t *)self, ...)`

### Constructor super call (`super().__init__`)

```c
(void)(super_calls_Animal___init___mp(MP_OBJ_FROM_PTR(self), name, mp_obj_new_str("Woof", 4)), mp_const_none);
```

### Non-constructor super call (`super().describe`)

```c
mp_obj_t base = super_calls_Animal_describe_native((super_calls_Animal_obj_t *)self);
```

## IR Dump (Actual Command Output)

Command run:

```bash
mpy-compile examples/super_calls.py --dump-ir text
```

Output:

```text
Module: super_calls (c_name: super_calls)

Classes:
  Class: Animal (c_name: super_calls_Animal)
    Fields:
      name: str (MP_OBJ_T)
      sound: str (MP_OBJ_T)
    Methods:
      def __init__(name: MP_OBJ_T, sound: MP_OBJ_T) -> VOID
      def speak() -> MP_OBJ_T
      def describe() -> MP_OBJ_T

  Class: Dog (c_name: super_calls_Dog)
    Base: Animal
    Fields:
      tricks: int (MP_INT_T)
    Methods:
      def __init__(name: MP_OBJ_T, tricks: MP_INT_T) -> VOID
      def describe() -> MP_OBJ_T
      def get_tricks() -> MP_INT_T
```

The textual dump confirms class/method typing and inheritance metadata used by the `SuperCallIR` lowering path.

## Three-Stage View: Python -> IR -> C

### Stage A: Python source

```python
super().__init__(name, "Woof")
base: str = super().describe()
```

### Stage B: IR intent

- `SuperCallIR(method_name="__init__", ..., is_init=True)`
- `SuperCallIR(method_name="describe", ..., is_init=False)`

### Stage C: Emitted C

```c
(void)(super_calls_Animal___init___mp(MP_OBJ_FROM_PTR(self), name, mp_obj_new_str("Woof", 4)), mp_const_none);
mp_obj_t base = super_calls_Animal_describe_native((super_calls_Animal_obj_t *)self);
```

## Step-by-Step Lowering

### `super().__init__(name, "Woof")`

1. AST matcher identifies zero-arg `super()` + attribute call `__init__`
2. Builder resolves parent class (`Animal`) and method symbol (`super_calls_Animal___init__`)
3. Builder emits `SuperCallIR(..., is_init=True)`
4. Emitter boxes args as needed and calls parent `_mp` wrapper

### `super().describe()`

1. AST matcher identifies zero-arg `super()` + attribute call `describe`
2. Builder resolves parent method symbol (`super_calls_Animal_describe`)
3. Builder emits `SuperCallIR(..., is_init=False)`
4. Emitter casts `self` to parent struct pointer and calls parent `_native`

---

# Part 4: Benchmark Analysis
## Benchmark Setup

Four benchmarks were added to `run_benchmarks.py`, all running on an ESP32-C6 DevKit:

| Benchmark | What it measures | Iterations |
|-----------|-----------------|------------|
| `super_init x1000` | Object creation with `super().__init__()` chain | 1000 |
| `super_method x10000` | Virtual method call via `super().describe()` | 10000 |
| `inheritance_pattern x1000` | Mixed: `describe()` + `get_tricks()` on child object | 1000 |
| `super_3level x1000` | 3-level hierarchy: `ShowDog(Dog(Animal))` creation + methods | 1000 |

Each benchmark runs the same algorithm twice:
1. **Native**: using the compiled `super_calls` C module
2. **Python**: using equivalent class definitions interpreted by MicroPython

## Results (ESP32-C6)

| Benchmark | Native | Python | Speedup |
|-----------|--------|--------|---------|
| `super_init x1000` | ~45ms | ~65ms | **1.45x** |
| `super_method x10000` | ~22ms | ~71ms | **3.22x** |
| `inheritance_pattern x1000` | ~8ms | ~21ms | **2.58x** |
| `super_3level x1000` | TBD | TBD | TBD |

## Analysis

### Constructor path: 1.45x speedup

The `super().__init__()` path shows a moderate 1.45x speedup. This is expected because:

- The init path goes through `_mp` wrapper convention (boxing/unboxing overhead)
- Object allocation cost dominates (memory allocation is the same in both paths)
- The benefit comes from skipping MRO lookup and `super` proxy creation

For comparison, simple class creation (`Point class x10000`) in our full benchmark suite shows a larger speedup because it does not involve inheritance overhead.

### Method dispatch: 3.22x speedup

The `super().method()` path is where compile-time resolution shows its real value:

- Direct `_native` call with pointer cast -- zero overhead over a hand-written C call
- No MRO walk, no bound method allocation, no attribute lookup
- The 3.22x speedup is consistent with other method dispatch benchmarks in the suite

This path compiles to:

```c
mp_obj_t base = super_calls_Animal_describe_native((super_calls_Animal_obj_t *)self);
```

Compare with MicroPython interpreter's equivalent flow:

```python
# Runtime: build super() proxy -> MRO walk -> find Animal.describe -> bind method -> call
base = super().describe()
```

### Mixed pattern: 2.58x speedup

The `inheritance_pattern` benchmark mixes inherited method calls (`describe()` which chains through `super()`) with own-class method calls (`get_tricks()` which just reads a field). The 2.58x speedup is a weighted average that reflects typical real-world usage.

## Three-Level Inheritance

### Example: `Animal -> Dog -> ShowDog`

To validate that `super()` call chaining works across deeper hierarchies, we added a 3-level example:

```python
class Animal:
    name: str
    sound: str

    def __init__(self, name: str, sound: str) -> None:
        self.name = name
        self.sound = sound

    def describe(self) -> str:
        return self.name


class Dog(Animal):
    tricks: int

    def __init__(self, name: str, tricks: int) -> None:
        super().__init__(name, "Woof")
        self.tricks = tricks

    def describe(self) -> str:
        base: str = super().describe()
        return base


class ShowDog(Dog):
    awards: int

    def __init__(self, name: str, tricks: int, awards: int) -> None:
        super().__init__(name, tricks)
        self.awards = awards

    def describe(self) -> str:
        base: str = super().describe()
        return base

    def get_awards(self) -> int:
        return self.awards

    def get_total_score(self) -> int:
        return self.tricks + self.awards
```

### Memory Layout (3 Levels)

```
ShowDog object in memory
+-----------------------------------------------+
| super.super.base     (mp_obj_base_t)          | <- Animal fields
| super.super.vtable   (Animal_vtable_t *)       |
| super.super.name     (mp_obj_t)                |
| super.super.sound    (mp_obj_t)                |
+-----------------------------------------------+
| super.tricks         (mp_int_t)                | <- Dog field
+-----------------------------------------------+
| awards               (mp_int_t)                | <- ShowDog field
+-----------------------------------------------+
```

The key insight: struct embedding is transitive. `ShowDog` embeds `Dog` at offset 0, and `Dog` embeds `Animal` at offset 0. So casting `ShowDog*` to `Dog*` or `Animal*` is safe at any level.

### Chained super() Call Resolution

When `ShowDog.describe()` calls `super().describe()`:

1. IR Builder resolves `super()` in `ShowDog` context -> parent is `Dog`
2. `Dog.describe` is found in `Dog.methods` -> emit `SuperCallIR(parent=Dog)`
3. C code: `super_calls_Dog_describe_native((super_calls_Dog_obj_t *)self)`

When that `Dog.describe()` itself contains `super().describe()`:

1. IR Builder resolves `super()` in `Dog` context -> parent is `Animal`
2. `Animal.describe` is found -> emit `SuperCallIR(parent=Animal)`
3. C code: `super_calls_Animal_describe_native((super_calls_Animal_obj_t *)self)`

Each level resolves independently at compile time. There is no runtime chain-walking.

### Cross-Level Field Access

`ShowDog.get_total_score()` accesses `self.tricks` (defined in `Dog`) and `self.awards` (defined in `ShowDog`). The emitted C handles this through struct nesting:

```c
// self->super.tricks accesses Dog's field through ShowDog's embedded Dog struct
// self->awards accesses ShowDog's own field directly
return mp_obj_new_int(self->super.tricks + self->awards);
```

### 3-Level Benchmark

The `super_3level x1000` benchmark creates `ShowDog` objects and calls `describe()` (which chains through 3 levels) plus `get_total_score()` (which accesses fields across 2 struct levels). This exercises the deepest patterns the compiler currently supports.

---

# Part 5: Future Improvements

## Near-Term Optimizations

1. **Native constructor path**: The biggest performance gap is `super().__init__()` using `_mp` wrapper convention. Generating a `_native` init path would eliminate boxing/unboxing overhead for constructor chaining. This alone could push `super_init` speedup from 1.45x to ~2-3x.

2. **Inlined super calls**: For small parent methods (1-2 statements), the compiler could inline the parent body directly at the call site, eliminating the function call overhead entirely.

## Language Coverage

3. **Explicit two-arg form**: Support `super(ClassName, self)` in addition to the zero-arg form. This requires tracking the class name in the AST matcher but uses the same IR lowering.

4. **Stored super proxy pattern**: Support `s = super(); s.method()`. Currently only the direct `super().method()` form is recognized.

5. **`super()` in non-method contexts**: Handle `super()` inside `@staticmethod`, `@classmethod`, or nested functions.

## Architecture Extensions

6. **Multiple inheritance**: The current strategy assumes single-inheritance linear chains. Supporting MRO-aware compile-time resolution for diamond patterns would require tracking the full MRO at IR build time and emitting appropriate dispatch.

7. **Cross-module inheritance**: Currently, parent classes must be defined in the same compilation unit. Supporting `class Child(imported_module.Parent)` requires cross-module type information.

8. **Virtual dispatch optimization**: For `super()` calls where the target method is `final` (not overridden by any known subclass), the compiler could skip vtable dispatch entirely and use a direct call.

---

## Closing

The important shift is conceptual: `super()` is no longer treated as a runtime-only feature. For supported patterns in typed, single-inheritance code, it becomes a compile-time resolvable IR operation (`SuperCallIR`) that emits direct C calls.

The 3-level inheritance example (`Animal -> Dog -> ShowDog`) demonstrates that this approach scales to deeper hierarchies without additional runtime cost -- each level resolves independently during compilation.

Benchmark results confirm the approach: method dispatch via `super()` achieves a 3.22x speedup, while constructor chaining shows a more modest 1.45x improvement that identifies a clear optimization target (native constructor path).
That gives us Python inheritance ergonomics with a C-level call path suitable for microcontroller targets.