# Protocol Types In Upstream mypyc, And Why mypyc-micropython Skips Them

Protocol types look like a pure typing feature.
In a compiler, they stop being a purely static idea.
Something has to happen at runtime when you write code that is type checked against a Protocol, then compiled.

Upstream mypyc (the CPython extension compiler) chooses a hybrid approach.
It treats Protocols like traits when it can, but it keeps a slow fallback when it must.
That choice buys performance for explicit inheritance, and correctness for structural subtyping.
It also buys a lot of runtime and code generation complexity.

This post documents the upstream design, using a handful of key mypyc source snippets.
Then it makes the case for why mypyc-micropython is not copying this feature.
That is a deliberate engineering decision.

## Table of Contents

- [The Shape Of The Problem](#the-shape-of-the-problem)
- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [1. Protocols Are Structural Typing](#1-protocols-are-structural-typing)
- [2. A Compiler Needs A Runtime Plan](#2-a-compiler-needs-a-runtime-plan)
- [3. Traits As A Compiled Interface](#3-traits-as-a-compiled-interface)
- [4. The Hybrid Strategy In One Sentence](#4-the-hybrid-strategy-in-one-sentence)
- [Part 2: C Background](#part-2-c-background)
- [5. What A vtable Is, Without Magic](#5-what-a-vtable-is-without-magic)
- [6. Two Dispatch Paths, One Static Type](#6-two-dispatch-paths-one-static-type)
- [7. Trait vtables And Runtime Search](#7-trait-vtables-and-runtime-search)
- [8. Attribute Access Is Harder Than Calls](#8-attribute-access-is-harder-than-calls)
- [9. Why isinstance(Protocol) Is Expensive](#9-why-isinstanceprotocol-is-expensive)
- [Part 3: Upstream mypyc Implementation Findings](#part-3-upstream-mypyc-implementation-findings)
- [10. Protocol Detection](#10-protocol-detection)
- [11. Protocols Become Traits In ClassIR](#11-protocols-become-traits-in-classir)
- [12. The Union Trick](#12-the-union-trick)
- [13. Dual-Path Codegen For Calls And Attributes](#13-dual-path-codegen-for-calls-and-attributes)
- [14. Trait vtable Layout In Upstream mypyc](#14-trait-vtable-layout-in-upstream-mypyc)
- [15. Trait Attribute Access Uses Offset Lookup](#15-trait-attribute-access-uses-offset-lookup)
- [16. Protocol isinstance() Warnings](#16-protocol-isinstance-warnings)
- [17. Docs Say "Erased", Reality Is Mixed](#17-docs-say-erased-reality-is-mixed)
- [18. Testing Reality Check](#18-testing-reality-check)
- [Comparison Tables](#comparison-tables)
- [Why We're Not Implementing This](#why-were-not-implementing-this)
- [What We'd Do Instead](#what-wed-do-instead)
- [Source File Map](#source-file-map)
- [Closing Notes](#closing-notes)

## The Shape Of The Problem

Protocols in typing are about substitutability.
"If it has these methods, treat it as that interface."

That idea is great at type checking time.
At runtime, the object is still just an object.
The compiler has to decide how to turn a method call on a Protocol-typed value into concrete operations.

Upstream mypyc compiles to CPython extension modules.
It can call CPython runtime APIs when it falls back.
It can also generate native layouts and function pointer tables for compiled classes.

Those two facts set up the main upstream trick.
Represent a Protocol-typed value as "maybe a compiled trait, maybe a plain object".
Then generate a branch.

---

## Part 1: Compiler Theory

### 1. Protocols Are Structural Typing

Most object oriented runtimes are nominal.
You have a class.
Instances of that class are recognized by a type tag.

Structural typing ignores the declared class tree.
It cares about shape.

If an object has `read()` and `close()`, it behaves like a file-like protocol.
You can satisfy the Protocol without inheriting it.

For a type checker, that is easy.
It is just a set of required members.

For a compiler, it raises a question.
How do you call `x.read()` efficiently if `x` is only known to satisfy some set of members.

There is a hidden split:

- Some values will be instances of classes that explicitly inherit the Protocol.
- Others will only match structurally.

Those two cases want different implementations.

### 2. A Compiler Needs A Runtime Plan

If your compiler only generates generic runtime calls, Protocols are trivial.
You always do attribute lookup.
You always call through the dynamic runtime.
Nothing gets faster.

If your compiler wants speed, it tends to specialize.
Specialization usually needs a concrete layout.
That means you want something like:

- fixed offsets for fields, or
- fixed vtable indices for methods.

Protocols do not promise a concrete layout.
They promise behavior.

So a compiler that wants performance has to add a new idea.
Treat Protocols like interfaces.
Then attach a runtime representation that supports fast dispatch.

But Protocols also allow structural subtyping.
That means you cannot require explicit inheritance.

The tension is unavoidable.

- Fast dispatch likes nominal tagging.
- Protocols allow structural matching.

Upstream mypyc chooses a hybrid.

### 3. Traits As A Compiled Interface

In mypyc terminology, the runtime representation for "interface-like" behavior is a trait.
This is close to interfaces in languages like Java, and close to Rust traits.

Key ideas:

- A trait has a list of methods.
- A class can implement multiple traits.
- The compiled runtime needs a way to call trait methods on an object.

The usual pattern in C is a vtable.
That is just a struct of function pointers.

A single-inheritance class can use a single vtable.
Multiple traits complicate this.
You need per-trait method tables, and a way to find the right one.

Upstream mypyc implements that machinery.
Protocols are then mapped onto it.

### 4. The Hybrid Strategy In One Sentence

Upstream mypyc treats Protocol types as a union of "compiled trait instance" and "plain object".
Then it emits code that checks which case it is, and dispatches accordingly.

Fast when explicit inheritance exists.
Correct when only structural matching exists.

---

## Part 2: C Background

This section is a C primer aimed at Python developers.
It is intentionally focused.
Only the concepts needed to understand the upstream design are covered.

### 5. What A vtable Is, Without Magic

A vtable is a data structure that supports dynamic dispatch.
In C, the simplest mental model looks like this:

```
struct VTable {
    void (*method0)(void *self);
    int  (*method1)(void *self, int x);
    ...
};

struct Obj {
    struct VTable *vtable;
    ... object fields ...
};
```

Each instance carries a pointer to its vtable.
Calling a method becomes:

```
obj->vtable->method1(obj, 123);
```

The vtable pointer selects the implementation.
The method index selects which method.

This is fast.
It is a couple of pointer reads.

In a dynamic language runtime, there are other ways.
You can store methods in dictionaries.
You can resolve attribute names at runtime.
That is flexible, but it is slower.

Upstream mypyc tries to be fast where it can.
So it uses vtables for compiled classes.

### 6. Two Dispatch Paths, One Static Type

With Protocol types, upstream mypyc wants two possibilities at runtime.

- The value is a compiled class instance that explicitly implements the protocol.
- The value is some other Python object that happens to match structurally.

For the first case, a trait vtable call is possible.
For the second case, a generic runtime attribute lookup is needed.

Here is the high level picture.
This is pseudocode, not a real upstream snippet.

```
if value_is_compiled_and_implements_trait(x, ProtocolT):
    # Fast path
    trait_vtable = find_trait_vtable(x, ProtocolT)
    return trait_vtable->method_slot(x, ...)
else:
    # Slow path
    method = runtime_getattr(x, "method")
    return runtime_call(method, ...)
```

This pseudocode is the entire design.
Everything else is about encoding the check, encoding the trait vtable, and preserving typing.

### 7. Trait vtables And Runtime Search

Single inheritance is easy.
Every object points to one vtable.
The compiler can assign fixed indices.

Traits add a new problem.

An object may implement multiple traits.
You need a way to find the trait-specific vtable.

One common approach:

- For each class, store an array of pairs.
- Each pair is (trait type object, pointer to trait vtable).
- At runtime, search that array for the trait you want.

That is what upstream mypyc does.
There is a real performance cost.

- You pay a linear search through the trait list.
- You pay one more pointer indirection.

This is still much faster than repeated attribute lookup in the generic runtime.
But it is not free.

### 8. Attribute Access Is Harder Than Calls

Method calls are conceptually simple.
They become function pointer calls.

Attributes, especially fields, are different.

Compiled classes tend to store fields in a C struct.
Access is often a fixed offset from `self`.

Traits complicate this.
An attribute in a trait might correspond to a different offset in different concrete classes.

So trait attribute access needs a runtime mapping.

- You need to find which concrete layout is in use.
- Then you need to find the offset for the trait attribute.
- Then you can read or write the field.

Upstream mypyc emits C code to perform an offset lookup.
One snippet for this is included later.

### 9. Why isinstance(Protocol) Is Expensive

Nominal `isinstance(x, SomeClass)` is fast.
The runtime can check the type pointer and the inheritance chain.

Structural `isinstance(x, SomeProtocol)` is not.
The runtime must do something like:

- Does the object have attribute A.
- Does it have attribute B.
- Are they callable, do they match signatures.

Even if the runtime caches parts of this, it is fundamentally more work.

Upstream mypyc knows this.
It annotates protocol `isinstance` checks as expensive.

---

## Part 3: Upstream mypyc Implementation Findings

This part is anchored on specific upstream mypyc source snippets.
Only snippets provided in the task are quoted.

The flow to keep in mind:

- Protocols are detected.
- Protocols are treated like traits.
- Protocol-typed values are represented as a union.
- Union operations generate runtime branches.
- Trait calls and trait attribute access use per-trait vtables.

### 10. Protocol Detection

Upstream mypyc detects Protocols through mypy's `TypeInfo.is_protocol` flag.
It then treats them like traits.

The detection lives in `mypyc/irbuild/util.py`.

```python
# mypyc/irbuild/util.py:63-64
def is_trait(cdef: ClassDef) -> bool:
    return any(is_trait_decorator(d) for d in cdef.decorators) or cdef.info.is_protocol
```

The important detail is the `or cdef.info.is_protocol`.
There is no separate "Protocol" path in this function.

That is a design statement.
Protocols are treated as the same compilation concept as traits.

### 11. Protocols Become Traits In ClassIR

The detection decision feeds into IR construction.
`ClassIR` is the internal representation of a class in the mypyc IR.

`mypyc/irbuild/prepare.py` creates `ClassIR` and passes the `is_trait` flag.

```python
# mypyc/irbuild/prepare.py:94-97
class_ir = ClassIR(
    cdef.name,
    module.fullname,
    is_trait(cdef),  # Protocols become traits here
    is_abstract=cdef.info.is_abstract,
    is_final_class=cdef.info.is_final,
)
```

If `cdef.info.is_protocol` is true, then `is_trait(cdef)` is true.
So Protocol classes become `ClassIR(is_trait=True)`.

This is not only an annotation.
It changes code generation.
Traits have different vtable structures and different call sites.

### 12. The Union Trick

The key upstream insight is the "union trick".

When a static type is a Protocol, upstream mypyc maps it to:

- a compiled instance type for fast dispatch, plus
- the generic `object` type to preserve structural behavior.

That mapping happens in `mypyc/irbuild/mapper.py`.

```python
# mypyc/irbuild/mapper.py:110-118
elif typ.type in self.type_to_ir:
    inst = RInstance(self.type_to_ir[typ.type])
    # Treat protocols as Union[protocol, object], so that we can do fast
    # method calls in the cases where the protocol is explicitly inherited from
    # and fall back to generic operations when it isn't.
    if typ.type.is_protocol:
        return RUnion([inst, object_rprimitive])
    else:
        return inst
```

This is the whole plan, encoded in one comment.

Interpretation:

- `inst` is the representation of a compiled instance of that protocol-as-trait.
- `object_rprimitive` is the representation of a generic Python object.
- `RUnion([inst, object])` says "either we can treat it as a trait instance, or we can't".

If you only read one snippet from this post, it should be this one.

#### Union Trick Diagram (Dual-Path Dispatch)

The union is a static type representation.
The compiler uses it to generate a runtime check.

```
Static type in source:

    def f(x: P) -> int:
        return x.m()

Upstream mypyc IR type (mapper):

    x : RUnion([RInstance(P_as_trait), object])

Generated shape (conceptual):

    if isinstance(x, P_as_trait):
        # Fast path
        # - find P trait vtable inside x's trait vtable array
        # - call via function pointer slot
        return call_trait_slot(x)
    else:
        # Slow path
        # - do runtime getattr and runtime call
        return call_dynamic(x, "m")
```

This is why the union contains `object`.
It forces the compiler to keep a generic route.

### 13. Dual-Path Codegen For Calls And Attributes

Once a value has a union type, many IR builder operations switch to "union mode".

Upstream mypyc has a helper that decomposes union types.
It emits an `isinstance` chain and runs specialized logic for each union arm.

The helper is in `mypyc/irbuild/ll_builder.py`.

```python
# mypyc/irbuild/ll_builder.py:2736-2797
def decompose_union_helper(
    self, obj, rtype, result_type, process_item, line):
    """Generate isinstance() + specialized operations for union items.
    Say, for Union[A, B] generate ops resembling this (pseudocode):
        if isinstance(obj, A):
            result = <result of process_item(cast(A, obj)>
        else:
            result = <result of process_item(cast(B, obj)>
    """
```

Notice what is going on.

- The union is decomposed via runtime `isinstance` checks.
- Each arm can compile to different operations.

For Protocols, the two arms are:

- the trait instance arm, for explicit inheritance
- the object arm, for structural compatibility

Attribute access uses the same union decomposition idea.
In upstream mypyc, if the object has `RUnion` type, attribute access goes through a union helper.

```python
# mypyc/irbuild/ll_builder.py:809-822
elif isinstance(obj.type, RUnion):
    return self.union_get_attr(obj, obj.type, attr, result_type, line)
```

This is one of the reasons Protocol support is not isolated.
It is entangled with the general union machinery.

If you bring in Protocols, you are bringing in:

- union type representation decisions
- union decomposition codegen
- runtime `isinstance` checks
- per-arm specialized call and attribute logic

### 14. Trait vtable Layout In Upstream mypyc

Upstream mypyc documents trait vtable layout in comments.
Those comments are in `mypyc/ir/class_ir.py`.

The following excerpt is the high-level runtime design.

```
# mypyc/ir/class_ir.py:13-63 (comments)
# Each concrete class has a vtable that contains function pointers for its methods.
# For each trait implemented by a class, we generate a separate vtable for the methods 
# in that trait. We then store an array of (trait type, trait vtable) pointers alongside
# a class's main vtable. When we want to call a trait method, we (at runtime!) search
# the array of trait vtables to find the correct one, then call through it.

# Vtable layout example:
#      T1 type object
#      ptr to B's T1 trait vtable
#      T2 type object
#      ptr to B's T2 trait vtable
#  -> | A.foo
#     | Glue function that converts between A.bar's type and B.bar
#       B.bar
#       B.baz
```

There are several important details packed into this comment.

1) "Alongside" the main vtable means there is more than one table.

2) "Search the array" is a runtime cost.
It is a linear scan.

3) The presence of "glue" functions means there is a type adaptation layer.
That is, trait method signatures might not match concrete method signatures exactly.
So mypyc generates wrapper functions.

#### Trait vtable Layout Diagram

This is an ASCII picture of the comment.
It highlights what "array of pairs" means.

```
Per concrete class (example: class B implements traits T1 and T2)

  +---------------------------------------------------------------+
  |  Trait table entries (pairs)                                  |
  +-------------------------------+-------------------------------+
  |  [0] trait type object: T1    |  [0] trait vtable ptr: &B_T1  |
  +-------------------------------+-------------------------------+
  |  [1] trait type object: T2    |  [1] trait vtable ptr: &B_T2  |
  +-------------------------------+-------------------------------+
  |  ... possibly more traits ...                                 |
  +---------------------------------------------------------------+
  |  Main vtable entries (fixed slots)                            |
  +-------------------------------+-------------------------------+
  |  slot 0: A.foo implementation pointer                         |
  |  slot 1: glue wrapper for A.bar with B.bar signature adapter   |
  |  slot 2: B.bar implementation pointer                          |
  |  slot 3: B.baz implementation pointer                          |
  |  ...                                                         |
  +---------------------------------------------------------------+

At runtime, a trait call does:

  scan trait table pairs until trait type object matches T1
  then call via &B_T1->slot_for_trait_method
```

Upstream mypyc does this because it has to.
CPython classes can implement multiple protocols.
Static typing can express that.

### 15. Trait Attribute Access Uses Offset Lookup

Trait attribute access needs offsets.
Upstream mypyc generates code to compute an offset dynamically.

The following C snippet is from `mypyc/codegen/emitfunc.py`.

```c
// mypyc/codegen/emitfunc.py:348-374
// For pure trait access find the offset first
size_t offset = CPy_FindAttrOffset(type_struct, vtable, trait_attr_index);
return *(type_cast *)((char *)obj + offset);
```

Even if you have never written C, the shapes here are readable.

- `(char *)obj + offset` means "pointer arithmetic".
  `char *` is used because it advances by bytes.
- `type_cast *` means "pretend this address points to a value of some type".
- `*(...)` means "read the value".

So trait attribute access becomes:

1) compute the offset for this trait attribute in this concrete object layout
2) add that offset to the object pointer
3) load the value

That offset computation is the hard part.
It depends on how the concrete class lays out its fields.

This is a direct example of why Protocol support is not "just typing".
It leaks into memory layout and code generation.

### 16. Protocol isinstance() Warnings

Upstream mypyc acknowledges a cost.
Structural protocol checks are expensive.
The annotation phase emits a warning.

```python
# mypyc/annotate.py:393-398
def check_isinstance_arg(self, arg):
    if isinstance(arg, RefExpr):
        if isinstance(arg.node, TypeInfo) and arg.node.is_protocol:
            self.annotate(arg, f'Expensive isinstance() check against protocol "{arg.node.name}".')
```

This is a good design tell.
If the compiler authors are warning about it, they have seen it matter.

Also notice the framing.
The cost is not "compilation cost".
It is runtime cost.

### 17. Docs Say "Erased", Reality Is Mixed

Upstream documentation includes Protocols in "erased" types.
That statement is easy to misread.

The exact line referenced in the research notes is:

```rst
# mypyc/doc/using_type_annotations.rst:238
Erased types include:
* Protocol types
```

This line is true in a narrow sense.
Protocols do not become a concrete runtime type in the same way a compiled class does.
They do not become a new Python runtime entity.

But the implementation details above show a deeper truth.

- Protocol declarations are compiled as traits.
- Protocol-typed values become unions.
- There is vtable infrastructure that exists specifically to optimize explicit protocol inheritance.

So "erased" here does not mean "ignored".
It means "not represented as a single dedicated runtime object type".

The union trick is the proof.
If it were truly erased, it would always compile to plain `object` and always use generic lookup.
That is not what upstream does.

### 18. Testing Reality Check

The research notes include a sobering point.
Protocol-specific test coverage in upstream mypyc is thin.

- No dedicated Protocol tests in the mypyc test suite.
- Protocol usage only in fixture files like `typing-full.pyi`.
- Traits have substantial tests, `run-traits.test` is around 411 lines.
- Only a few GitHub issues mention "mypyc protocol", and none are about compilation bugs.

This matters for downstream.
If a path is not heavily tested upstream, it is a risky path to import.

For mypyc-micropython, which targets a constrained runtime, the bar is higher.
Complex runtime features need to be exercised and proven.

## Comparison Tables

### Regular Class vs Protocol or Trait (Upstream Model)

| Aspect | Regular Class | Protocol/Trait |
|--------|--------------|----------------|
| Vtable | Single main vtable | Main + per-trait vtables |
| Method call | Direct vtable index | Search trait vtable array |
| Attribute access | Fixed struct offset | Runtime offset lookup |
| isinstance() | Native type check | Expensive structural check |
| Type representation | RInstance | RUnion([RInstance, object]) |

### mypyc vs mypyc-micropython (Design Choice)

| Feature | mypyc (CPython) | mypyc-micropython | Reason |
|---------|------------------|-------------------|--------|
| Protocol detection | Via mypy `is_protocol` | N/A | Not implementing |
| Trait vtables | Full implementation | Not needed | Single inheritance + vtable covers common cases |
| Union trick | `RUnion` dual-path | N/A | No structural subtyping needed |
| isinstance(Protocol) | Structural runtime check | N/A | No Protocol types |
| Method dispatch | Trait vtable search | Direct vtable index | Simpler, faster |

## Why We're Not Implementing This

Protocol support in upstream mypyc is clever.
It is also the wrong trade for this project.

The decision is not ideological.
It is about runtime constraints, code size, and risk.

### 1) MicroPython Does Not Ship typing.Protocol

On CPython, `typing.Protocol` is part of the standard library.
Projects can rely on it.

On MicroPython, the standard library is intentionally small.
`typing` is not present in the same way, and Protocol is not there.

If the target runtime does not have the feature, the compiler has choices:

- emulate the feature in the runtime, or
- treat it as a static-only construct with no runtime behavior.

Emulation is a large addition.
Static-only behavior still needs a coherent compilation story for method calls.

### 2) Dual-Path Dispatch Is Not Free

The union trick implies branching at each call site.
That means:

- runtime `isinstance` checks
- two code paths in the generated code
- more complex IR and emitter logic

On a microcontroller, branchy code is not just slower.
It is larger.
It consumes flash.

It also complicates debugging.
If a value is not in the fast arm, it silently goes to slow arm.
That behavior is correct for CPython, but it hides performance cliffs.

### 3) Trait vtable Infrastructure Is Significant Complexity

Upstream mypyc trait support is not a small feature.
It includes:

- per-trait vtables
- runtime trait vtable search arrays
- glue functions to adapt method signatures
- offset lookup mechanisms for trait attributes

This is the opposite of what mypyc-micropython is optimizing for.

We want predictable codegen.
We want straightforward dispatch.
We want to minimize runtime metadata.

### 4) Embedded Code Usually Uses Concrete Types

Protocols shine in large, layered codebases.
They let you express duck typing while staying strict.

Embedded programs are often smaller.
They also often run closer to hardware.
The types that matter are concrete.

When an embedded project needs polymorphism, it is usually one of:

- a small class hierarchy, with known concrete types
- explicit callbacks, passing functions
- an adapter object with a known wrapper API

Structural subtyping is rarely the bottleneck.
The extra runtime machinery has low payoff.

### 5) Upstream Protocol Paths Are Not Heavily Exercised

The testing notes matter.
If Protocols are not heavily tested upstream, they will not be heavily tested downstream.

For mypyc-micropython, that is a non-starter.
The target runtime is different.
The generated code runs on devices.
If a feature is brittle, it will fail in new and hard-to-debug ways.

### 6) Our Common Case Is Already Covered

The design center for mypyc-micropython is:

- typed functions
- predictable primitives
- simple object patterns
- and when classes land, mostly single-inheritance dispatch

Single inheritance and direct vtable dispatch cover the common performance story.
They do not require a trait system.

In other words:

- upstream mypyc needs Protocols to accelerate large CPython programs
- we do not need Protocols to accelerate typical MicroPython programs

## What We'd Do Instead

If we ever need Protocol-like behavior, there are safer stepping stones.
The goal is to get the useful part, without pulling in the entire upstream complexity.

### Option 1: A @trait Decorator With Explicit Inheritance Only

This is the smallest useful feature.

- Add a `@trait` decorator, similar to upstream.
- Require explicit inheritance to opt in.
- Treat it as nominal, not structural.

That eliminates the slow arm.
No union trick.
No runtime structural checks.

It also keeps performance predictable.

### Option 2: Adapter Types Instead Of Structural Checks

If code wants to accept "anything with method X", an adapter can make that explicit.

Example pattern:

- Define a concrete wrapper that stores an `mp_obj_t`.
- Provide methods that perform attribute lookup and cache bound methods.
- Call through cached callables.

This pushes structural behavior to the boundary.
It does not infect the entire compiler.

### Option 3: Callbacks And Function Parameters

Often Protocol usage in Python is "object with callable method".
On microcontrollers, passing a function is often a better fit.

It is easy to compile.
It is easy to reason about.
It is easy to test.

### Option 4: If We Truly Need It, Copy The Upstream Plan Incrementally

If a future use case is strong enough to justify it, the upstream plan is still a roadmap.
But it should be copied in layers.

The layers, in a conservative order:

1) Implement `@trait` only, explicit inheritance only.
2) Add per-trait vtables, but do not support trait attributes at first.
3) Add trait method calls, with explicit inheritance only.
4) Only then consider the union trick and the slow path.
5) Do not implement structural `isinstance` checks unless a real workload proves it is needed.

That sequence keeps complexity bounded.

## Source File Map

This is a quick map of the upstream mypyc files referenced in this research.
This post only quotes code snippets provided in the task, but it names the broader components.

| File | Role In Protocol Support |
|------|--------------------------|
| `mypyc/irbuild/util.py` | Decides "trait-ness" via `is_trait()`, Protocols count as traits |
| `mypyc/irbuild/prepare.py` | Builds `ClassIR` and sets `is_trait`, Protocols become traits here |
| `mypyc/irbuild/mapper.py` | Maps mypy types to IR types, Protocols become `RUnion([inst, object])` |
| `mypyc/irbuild/ll_builder.py` | Emits union decomposition branching via `decompose_union_helper()`, also routes union attribute access |
| `mypyc/ir/class_ir.py` | Documents trait vtable layout and the runtime search model |
| `mypyc/codegen/emitfunc.py` | Emits C code for trait attribute access, including runtime offset lookup |
| `mypyc/codegen/emitclass.py` | Sets up class and trait vtable structures for compiled classes (not quoted here) |
| `mypyc/annotate.py` | Warns about expensive `isinstance(x, Protocol)` checks |
| `mypyc/doc/using_type_annotations.rst` | Documents erased types, includes Protocols, but can be misread |

## Closing Notes

Upstream mypyc's Protocol story is not "Protocols are erased".
It is "Protocols are mostly treated like traits, but we preserve structural correctness with a union fallback".

That hybrid is pragmatic.
It is also a lot of machinery:

- IR typing tricks (`RUnion([protocol, object])`)
- union decomposition and branching
- trait vtable arrays and runtime searches
- offset lookups for trait attributes

For CPython extension modules, this is a reasonable trade.
For MicroPython on microcontrollers, it is not.

The mypyc-micropython stance is simple.
Avoid structural subtyping features that require large runtime and codegen machinery.
Prefer explicit, nominal interfaces when polymorphism is needed.
Keep the compiler small, predictable, and testable.
