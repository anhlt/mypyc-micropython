# 36. Traits, Union Types, and the Static vs Dynamic Dispatch Problem

This post explains a problem that shows up the moment you mix typed Python with compilation: union types and trait types push type decisions to runtime, but C code wants decisions at compile time.

The headline issue is simple:

- If a parameter has a concrete class type, we can compile `obj.field` into a single pointer dereference.
- If a parameter is a trait type (or more generally, a union where the concrete layout is unknown), we must fall back to dynamic lookup.

In `mypyc-micropython`, that choice is controlled by a compile-time flag on the IR node used for parameter attribute access.

## Part 1: Compiler Theory - The Union Type Problem

### What union types mean in Python

Python's type syntax lets you say "this value could be one of several things":

```python
def parse(x: str | int) -> int:
    ...
```

That is a union type. At runtime, `x` is either a `str` or an `int`.

Traits (protocol-like classes, declared with `@trait`) create a similar situation:

```python
from mypy_extensions import trait

@trait
class Named:
    name: str

class Person(Named):
    name: str

class Pet(Named):
    name: str

def get_name(obj: Named) -> str:
    return obj.name
```

`Named` is not a concrete class with a fixed layout. It's a promise that "whatever you pass in has a `name`". At runtime, `obj` might be a `Person`, a `Pet`, or any other class that satisfies the trait.

If you squint, `Named` behaves like a very large union:

```
Named ~= Person | Pet | ...
```

The trait doesn't list all cases up front, but the compiled code still has the same problem: the concrete layout is unknown at compile time.

### Why a compiled language cares about layout

For compiled classes, `mypyc-micropython` represents each instance as a C struct. The easiest way to compile field access is to cast the MicroPython `mp_obj_t` to the right struct pointer and dereference a field:

```c
((module_Person_obj_t *)MP_OBJ_TO_PTR(p))->age
```

That is fast and predictable. It's also very fragile.

It only works if the compiler knows, at the access site, which struct type to cast to.

### Static dispatch vs dynamic dispatch, at an attribute access

When you write:

```python
def get_age(p: Person) -> int:
    return p.age
```

the compiler sees `p: Person` and can choose static dispatch for field access: it picks `Person_obj_t` and emits a direct offset read.

But when you write:

```python
def get_name(obj: Named) -> str:
    return obj.name
```

the compiler cannot do the same thing.

"Static dispatch" would mean choosing one struct layout and committing to it. That would force us into a lie:

```c
// This is wrong for trait types.
return ((module_Person_obj_t *)MP_OBJ_TO_PTR(obj))->name;
```

If `obj` is actually a `Pet`, the cast is wrong. You might still get a pointer, but the offset you read is not the `name` field. It is just "whatever happens to live at that byte offset inside a Pet".

The safe alternative is dynamic dispatch: ask the runtime to resolve the attribute for the actual object at runtime.

In MicroPython, that universal path is `mp_load_attr(obj, MP_QSTR_name)`.

### Why this breaks the naive compilation strategy

The naive rule is:

"Compile `obj.field` to `((ObjType *)ptr)->field`."

That rule assumes `ObjType` is known. Union types and trait types break that assumption.

There are only a few ways out:

1. Restrict unions so strongly that the compiler can always pick one concrete layout.
2. Insert runtime type tests and branch to separate static layouts.
3. Switch to a dynamic attribute path.

This project takes option (3) for trait-typed parameters today, and it is the right default:

- It preserves correctness.
- It matches MicroPython's object model.
- It doesn't require building a separate "tagged union" runtime for every union type.

### Unions and traits are the same problem, with different guarantees

`str | int` and `Named` both hide the runtime type from the compiler, but they differ in what they promise:

- A union type promises nothing about shared fields. You have to check before you access.
- A trait promises that certain members exist (fields, methods). You still don't know layout, but you do know the name is valid.

That distinction is why traits are a great bridge between Python's dynamic model and compilation:

- They keep the program well-typed.
- They still force dynamic dispatch at certain sites.
- They let the compiler use static dispatch everywhere else.

### Traits in this project

This project's trait model follows mypyc:

- One concrete base class (single inheritance for implementation and prefix layout).
- Any number of traits (interface-like).
- Traits are marked with `@trait` (or `@mypy_extensions.trait`).

The rest of this post explains how that type information becomes a concrete rule in the compiler:

"If a parameter is trait-typed, treat `param.attr` as dynamic." 

## Part 2: C Background

### Struct layout and offsets

In C, a struct is a fixed memory layout. Field offsets are baked in by the compiler.

```c
typedef struct {
    mp_obj_base_t base;
    mp_int_t age;
    mp_obj_t name;
} Person_obj_t;
```

The generated code for a field access is basically:

1. Convert `mp_obj_t` to a pointer (`MP_OBJ_TO_PTR`).
2. Cast to the expected struct pointer type.
3. Read a field at a known offset.

That is why static dispatch is fast: it is a direct read.

It is also why union and trait types are tricky: if the cast type is wrong, the offset is wrong.

### void* and casting, polymorphism by hand

In C, `void *` can point to anything, but it carries no type. Casting is how you tell the compiler what you think is behind the pointer.

That is exactly what happens when you cast `MP_OBJ_TO_PTR(obj)` to `Person_obj_t *`.

If your belief about the runtime type is wrong, C will not save you.

### Function pointers and vtables

C doesn't have methods, so the classic way to model "call method X on whatever this is" is a vtable: a table of function pointers.

From blog 03, the mental model is:

```c
self->vtable->increment(self)
```

You get dynamic dispatch because the vtable pointer you load from the object points to different function pointers depending on the runtime class.

Vtables solve dynamic method dispatch, but they do not automatically solve field layout.

Field layout is still about offsets.

### MicroPython's universal attribute access: mp_load_attr()

MicroPython can do attribute lookup for any object at runtime:

```c
mp_obj_t value = mp_load_attr(obj, MP_QSTR_name);
```

Unlike a struct field access, this does not assume a fixed offset. It asks the runtime to resolve `name` using the object's type, its slot functions, and whatever internal storage it uses.

This is the "dynamic dispatch" escape hatch.

The cost is real:

- `mp_load_attr` is effectively a runtime lookup (often hash table and slot logic).
- A struct field access is a single pointer dereference.

If you care about speed on ESP32-class devices, you want static dispatch where it is correct.

### Tagged unions

In C, a common representation for a union of types is:

```c
typedef enum { TAG_INT, TAG_STR } tag_t;

typedef struct {
    tag_t tag;
    union {
        mp_int_t i;
        mp_obj_t s;
    } as;
} int_or_str_t;
```

That pattern works when you control allocation and representation. In MicroPython, values are already `mp_obj_t` with their own tagging scheme (immediates for small ints, pointers for heap objects).

So most "union type" work in this project ends up looking like:

- keep values as `mp_obj_t`
- insert runtime checks when you need a specific representation

Trait types fit this world naturally, since they are already about runtime behavior.

## Part 3: Implementation - Making Traits Work

This section ties the theory back to the concrete implementation in `mypyc-micropython`.

The key rule is implemented in one place, but it depends on several earlier steps:

- detect traits in the AST and in mypy types
- represent trait relationships in `ClassIR`
- merge trait fields into concrete class layouts
- mark parameter attribute access IR nodes with `is_trait_type`
- in the emitter, choose between struct field access and `mp_load_attr`

We'll walk that pipeline with the example in `examples/traits.py`.

### Step 1: Detecting `@trait` in the AST

Trait classes are discovered while building class IR. The class builder checks decorators for:

- `@trait`
- `@mypy_extensions.trait`

Once detected, the `ClassIR` for the class is created with `is_trait=True`, and base classes are split into:

- `base_name` for the single concrete base
- `trait_names` for any traits

This lets the IR build carry "trait-ness" forward without guessing later.

### Step 2: ClassIR models traits explicitly

`ClassIR` stores traits separately from the concrete base:

- `base` and `base_name` for single inheritance
- `traits` and `trait_names` for trait mixes
- `is_trait` to mark the class itself as a trait

It also provides helpers that make later phases simple:

- `get_all_traits()` to collect traits from the base chain
- `get_mro()` for a method resolution order that includes traits

That last detail matters because "who wins" during method resolution is not an emitter detail. It is a class model detail.

### Step 3: Field merging, so concrete classes keep fast access

Traits can declare fields:

```python
@trait
class Named:
    name: str
```

Concrete classes that implement the trait should physically contain those fields.

This is where the design splits into two worlds:

- Inside concrete methods (where `self` is a known concrete type), we want `self->name` to be a direct field read.
- Through a trait-typed parameter (where the runtime type is unknown), we must not assume an offset.

The `ClassIR` field helpers merge trait fields into the concrete field list, and the class emitter also emits trait fields in the concrete struct.

The result is:

- "Concrete view": the struct contains `name`, so `Person` methods can use static field access.
- "Trait view": external code still cannot assume where `name` lives inside the runtime object.

### Step 4: Marking parameter attribute access with is_trait_type

When the IR builder sees `param.attr` and `param` is a class-typed parameter, it produces a `ParamAttrIR` node.

That node carries everything code generation needs:

- parameter name and its C name
- attribute name
- the concrete class C name (for struct casts)
- `attr_path` (for inherited fields like `super.x`)
- and the important bit: `is_trait_type`

`is_trait_type` is set from the parameter's class IR:

- if the parameter type is a trait, `is_trait_type=True`
- otherwise it is `False`

This flag is what turns the theory into a single, reliable emitter branch.

### Step 5: Emitting static vs dynamic attribute access

The function emitter's rule is exactly what we want:

- If `is_trait_type` is false, emit a struct cast plus field path.
- If `is_trait_type` is true, emit `mp_load_attr`.

Here is a small, self-contained example that demonstrates both cases.

Python:

```python
# Concrete type param, static dispatch
def get_age(p: Person) -> int:
    return p.age

# Trait type param, dynamic dispatch
def get_name(obj: Named) -> str:
    return obj.name
```

IR dump (text format):

```
def get_age(p: MP_OBJ_T) -> MP_INT_T:
  c_name: blog36_get_age
  max_temp: 0
  locals: {p: MP_OBJ_T}
  body:
    return p.age

def get_name(obj: MP_OBJ_T) -> MP_OBJ_T:
  c_name: blog36_get_name
  max_temp: 0
  locals: {obj: MP_OBJ_T}
  body:
    return obj.name # trait
```

Generated C (side by side):

```c
// get_age(p: Person) -> int
static mp_obj_t blog36_get_age(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;

    return mp_obj_new_int(((blog36_Person_obj_t *)MP_OBJ_TO_PTR(p))->age);
}

// get_name(obj: Named) -> str
static mp_obj_t blog36_get_name(mp_obj_t obj_obj) {
    mp_obj_t obj = obj_obj;

    return mp_load_attr(obj, MP_QSTR_name);
}
```

That one branch is the whole point:

- `->age` is correct because `p` is statically `Person`.
- `mp_load_attr(..., name)` is required because `obj` is only guaranteed to be "something Named".

### Step 6: Trait vtables and trait method wrappers

Attribute access is the easiest place to see the static vs dynamic split, but traits also imply polymorphic method calls.

If a class implements a trait but doesn't override a trait method, we still need a callable function that runs in the concrete class context.

The class emitter addresses this with two pieces:

1. Trait method wrappers
2. Per-trait vtables

Wrappers exist because the same method body, when compiled, is tied to a struct layout.

If a trait method does `return self.name`, the compiled version of that method cannot safely assume it is running on a "trait struct" layout. It must read `name` from the concrete struct.

So for inherited trait methods, the emitter generates wrapper functions of the shape:

```c
// Wrapper for trait Named.get_name
static mp_obj_t module_Person_get_name_from_Named_mp(mp_obj_t self_in) {
    module_Person_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return module_Person_get_name_from_Named_native(self);
}
```

The current wrapper generator special-cases the simplest and most common pattern:

```python
def get_name(self) -> str:
    return self.name
```

For more complex bodies, the wrapper generator has a fallback that casts to the trait struct, with a warning comment.

Per-trait vtables are emitted so each trait a class implements has a table of method pointers pointing at the right concrete implementations (or the generated wrappers).

This mirrors the core idea from blog 03, but the important change is scope: instead of a single class vtable for concrete inheritance, you get a vtable per trait interface.

### Step 7: Type checker integration, traits from mypy protocols

The AST decorator check is necessary, but it isn't enough.

Real programs will type their parameters using mypy's view of the world, and for traits that means protocols.

During type extraction, the compiler checks mypy's `TypeInfo.is_protocol`:

- if a class is a protocol, it is treated as a trait
- if a base is a protocol, it becomes a trait base (not the concrete base)

That keeps the compiler's trait model aligned with mypy's type system.

### A complete example from examples/traits.py

`examples/traits.py` includes both a trait-typed function and a call site that passes different concrete types.

Python:

```python
def get_name_direct(obj: Named) -> str:
    return obj.name

def test_trait_param() -> str:
    p = Person(1, "Alice", 30)
    cat = Pet(2, "Whiskers", "cat")
    p_direct = get_name_direct(p)
    cat_direct = get_name_direct(cat)
    return p_direct + "," + cat_direct
```

IR dump (text format, selected functions):

```
def get_name_direct(obj: MP_OBJ_T) -> MP_OBJ_T:
  c_name: traits_get_name_direct
  max_temp: 0
  locals: {obj: MP_OBJ_T}
  body:
    return obj.name # trait

def test_trait_param() -> MP_OBJ_T:
  c_name: traits_test_trait_param
  max_temp: 0
  locals: {p: MP_OBJ_T, cat: MP_OBJ_T, p_name: MP_OBJ_T, cat_name: MP_OBJ_T, p_direct: MP_OBJ_T, cat_direct: MP_OBJ_T}
  body:
    (new) p = Person(1, "Alice", 30)
    (new) cat = Pet(2, "Whiskers", "cat")
    p_name: mp_obj_t = greet_named(p)
    cat_name: mp_obj_t = greet_named(cat)
    p_direct: mp_obj_t = get_name_direct(p)
    cat_direct: mp_obj_t = get_name_direct(cat)
    return ((((((p_name + ",") + cat_name) + ",") + p_direct) + ",") + cat_direct)
```

Notice the key marker in `get_name_direct`: `# trait`.

That comment comes from the exact information the compiler needs: "this parameter is typed as a trait, so field access must not be lowered to a struct offset".

### Where union types fit next

Trait types forced us to solve the "unknown layout" problem for attribute access in a clean, local way.

Union types are the same problem, but with fewer guarantees. You only get to use the static field path for a union if you can prove a shared layout.

Two cases where that proof is possible:

1. Common concrete base contains the field. The prefix layout guarantee from single inheritance makes the offset stable.
2. The union is constrained to a single concrete class type (which is effectively not a union).

If neither is true, you need runtime checks or runtime lookup.

Traits are the practical compromise: they keep the program well-typed while admitting that dispatch must sometimes be dynamic.

### Along the way

This trait and dispatch work also surfaced a few small but important correctness fixes in nearby code paths:

- Self attribute assignments always apply type conversion, so `self.x = ...` behaves consistently with other assignments.
- Class emission orders methods so non-`__init__` methods are emitted before `__init__`, fixing bound method references that need `&Class_method_obj` to exist.
- Self-method argument unboxing uses the IR's expected target type, not a default like `mp_int_t`.

Those are not the main story here, but they are good examples of how type-driven compilation tends to uncover "this worked accidentally" assumptions.
