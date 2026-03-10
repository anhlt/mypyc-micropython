# When mypy Says Any: How Silent Type Erasure Broke Our Compiled Code

*A story about one word, two type systems, and why “it still type-checks” can be the most dangerous outcome.*

## Table of Contents

- [Part 1: Compiler Theory, The Dual Type System](#part-1-compiler-theory-the-dual-type-system)
- [Part 2: C Background, Why Type Info Affects Code Generation](#part-2-c-background-why-type-info-affects-code-generation)
- [Part 3: Implementation, The Bug, Fix, and Package-Level Solution](#part-3-implementation-the-bug-fix-and-package-level-solution)

## Part 1: Compiler Theory, The Dual Type System

This project compiles typed Python into a MicroPython C module. The compiler looks like a straight pipeline:

```
Python source -> ast.parse() -> IRBuilder -> FuncIR/ClassIR -> Emitters -> C code
```

That pipeline hides a second, parallel stream: type tracking. When it works, it enables direct struct access, fewer runtime calls, and simpler generated C. When it breaks, the compiler still produces C, but it often produces the wrong C.

### Two type representations, always together

For every variable, field, and intermediate value in the IR, we carry two type representations:

1. `CType` (an enum)
   - The C-level type used in generated code.
   - Values: `MP_INT_T`, `MP_FLOAT_T`, `BOOL`, `MP_OBJ_T`, `VOID`.
   - This is what the C compiler sees.

2. `py_type` (a string)
   - The Python-level type name used by the IR builder for decisions.
   - Values: `"int"`, `"str"`, `"Config"`, `"list"`, `"object"`, `"Any"`.
   - This is what drives specialization and access strategy.

It’s tempting to think only `CType` matters, because it lands in the final C signature. That’s not true.

`CType` controls boxing and unboxing:

- `int` becomes `mp_int_t` (unboxed integer arithmetic).
- `str` stays `mp_obj_t` (boxed object, because it’s a MicroPython object).

`py_type` controls access patterns:

- `py_type="Config"` enables native struct field access.
- `py_type="object"` forces generic `mp_load_attr()` lookups.
- `py_type="Any"` behaves like `"object"` in the compiler, it blocks optimizations because it removes safe assumptions.

### The critical insight: same `CType`, different code

Multiple Python types map to the same `CType`. In particular, many values in MicroPython are represented as `mp_obj_t`, so we often end up with `CType.MP_OBJ_T`. That does not mean we generate the same code.

These three cases can all be `CType.MP_OBJ_T`, but they produce very different C:

```text
py_type="Config" + CType.MP_OBJ_T  -> direct struct access
py_type="object" + CType.MP_OBJ_T  -> generic attr lookup
py_type="Any" + CType.MP_OBJ_T     -> treated as object (generic)
```

Concrete examples:

```c
// Fast path: the compiler knows the concrete class.
((myapp_Config_obj_t *)MP_OBJ_TO_PTR(self->config))->value
```

```c
// Generic path: the compiler only knows “some object”.
mp_load_attr(self->config, MP_QSTR_value)
```

With `Any`, we must use the generic path. Even worse, `Any` can poison chained attribute tracking so the compiler loses the thread halfway through a chain.

### The type resolution pipeline

To understand how `Any` can quietly ruin type tracking, it helps to see how type information flows.

Normal case:

```text
Python annotation  -->  mypy resolution  -->  py_type string  -->  CType enum
"config: Config"       "Config"              "Config"            MP_OBJ_T
"value: int"           "int"                 "int"               MP_INT_T
"data: object"         "object"              "object"            MP_OBJ_T
```

Broken case, the annotation stays the same but mypy reports `Any`:

```text
Python annotation  -->  mypy resolution  -->  py_type string  -->  CType enum
"config: Config"       "Any" (broken!)       "Any"               MP_OBJ_T
```

Notice what happens: `CType` still looks reasonable (`MP_OBJ_T`). If you only track the C-level representation, nothing looks wrong. The compiler continues to generate valid C. It just no longer has the semantic Python type name that unlocks the correct access strategy.

### ASCII diagram: the dual track in the compiler

The compiler maintains both tracks side by side.

```text
                 +-----------------------------+
Python AST        | IRBuilder                   |        Emitters
(annotations) --> | (build IR + attach types)   | ----> (C generation)
                 +-----------------------------+
                           |              |
                           |              |
                           v              v
                     py_type (string)   CType (enum)
                     "Config"          MP_OBJ_T
                     "int"             MP_INT_T
                     "Any"             MP_OBJ_T
```

When `py_type` becomes `"Any"` unexpectedly, the IR is still well-formed. The emitted C is still compilable. The generated behavior can be wrong because we lost the information that selects the safe fast path.

## Part 2: C Background, Why Type Info Affects Code Generation

If you write Python all day, the difference between `obj.value` and a hash table lookup is easy to forget, because CPython hides it and optimizes heavily. In MicroPython, and especially in generated C, you see it directly.

### Two ways to read a field

1. Native struct access (fast, specialized)

```c
((myapp_Config_obj_t *)MP_OBJ_TO_PTR(self->config))->value
```

2. Generic attribute lookup (slow, dynamic)

```c
mp_load_attr(self->config, MP_QSTR_value)
```

The generic path must do a runtime lookup: take the object, inspect its type, search for the attribute by name (typically through a map or method table), and return the result as a boxed `mp_obj_t`. It is correct for arbitrary objects, but it’s much more expensive than direct memory access.

The native path is just pointer math.

### A concrete struct layout

The compiler generates C structs for classes. A simplified view of a `Config` object might look like this:

```c
typedef struct _myapp_Config_obj_t {
    mp_obj_base_t base;
    mp_int_t value;
} myapp_Config_obj_t;
```

In memory:

```text
myapp_Config_obj_t
+---------------------------+
| base (mp_obj_base_t)      |  header: type pointer, flags
+---------------------------+
| value (mp_int_t)          |  direct field storage
+---------------------------+
```

When we compile `self.config.value`, we want to end up reading that `value` field directly.

### The casting chain, from mp_obj_t to struct field

MicroPython represents objects as `mp_obj_t` values. Many ports use tagged pointers or word-sized values to represent either small ints or pointers. The details vary by port, but the pattern in generated code stays consistent.

The fast path is a chain of operations:

```text
mp_obj_t (boxed) -> MP_OBJ_TO_PTR -> (void *) pointer -> (Config_obj_t *) cast -> ->value
```

In C:

```c
myapp_Config_obj_t *cfg = (myapp_Config_obj_t *)MP_OBJ_TO_PTR(self->config);
mp_int_t v = cfg->value;
```

This is only safe if the compiler knows the object is actually a `Config`. That knowledge comes from `py_type`, not from `CType` alone.

If all you know is “some `mp_obj_t`”, you cannot cast. You must use the generic attribute lookup path.

### How the bug surfaced: a None comparison that became constant

The failure mode that hurt most was not “slower code”, it was “wrong control flow”.

The compiler has a fallback when it cannot resolve a chained attribute access. Instead of generating an invalid pointer dereference, it substitutes a safe sentinel value. One of those sentinel values is `mp_const_none`.

That is a reasonable escape hatch for genuinely unsupported cases, but it becomes dangerous when type tracking is broken.

If the compiler cannot resolve a type like `Program`, it may treat a chained attribute like `self.program.subscribe_fn` as “unresolvable”, and substitute `mp_const_none`. In that situation, a check like this:

```python
if self.program.subscribe_fn is None:
    return
```

turns into “always true”, because the compiler already replaced the expression with `None`.

That was the real cost of `Any`: it did not just remove an optimization, it removed the compiler’s ability to follow a chain of fields and methods that were required for correct behavior.

## Part 3: Implementation, The Bug, Fix, and Package-Level Solution

This bug took a while to diagnose because nothing crashed during compilation. The generated C was valid. The runtime behavior was wrong.

### Bug 5 story: the root cause chain

The symptom was simple: timer subscriptions never activated. The underlying chain looked like this:

1. `app.py` imports `from lvgl_mvu.program import Program`
2. mypy type-checks `app.py` in isolation (per-file mode, `follow_imports="skip"`)
3. mypy can’t follow the import, so it reports `Program` fields as `Any`
4. The IR builder receives `py_type="Any"` for the `self.program` field
5. When the compiler sees `self.program.subscribe_fn`, it can’t resolve the chain
6. Chained attribute codegen falls back to `mp_const_none` (unresolvable)
7. The condition `if self.program.subscribe_fn is None` becomes always true
8. `_setup_subscriptions()` returns early every time, no subscriptions, no timers

The key point is step 3. The Python annotation did not change, but the mypy result did.

### The fallback fix: prefer the annotation over mypy’s Any

The fastest safe fix was to treat `Any` as “suspicious” when an AST annotation names a known class.

If mypy returns `Any` or `object`, and the source has an explicit annotation, use the annotation to recover a concrete `py_type` when possible.

```python
if mypy_py in ("Any", "object") and inner_annotation is not None:
    ann_py = self._annotation_to_py_type(inner_annotation)
    if ann_py in self._known_classes:
        py_type = ann_py  # Use annotation instead of mypy's Any
```

This is intentionally conservative:

- It only triggers when there is an annotation.
- It only accepts annotations that name classes the compiler already knows how to emit.

It is a bandage, but it turned a silent type erasure into a recoverable case.

### The real fix: package-level type checking

The real problem was running mypy in per-file mode with imports skipped. That configuration is attractive because it is fast and it avoids pulling in the world, but it breaks cross-module type resolution. In a compiler, that is not “slightly worse types”, it is “wrong compilation decisions”.

The solution was to type-check the whole package at once.

Instead of `type_check_source()` per file, add `type_check_package()` that:

- uses `follow_imports="normal"`
- sets `mypy_path=[parent_dir]` so in-package imports resolve
- creates `BuildSource` entries for every `.py` file in the package
- runs mypy once, producing a single coherent view of types across modules
- distributes results back to per-file compilation through a `mypy_type_result` parameter

Conceptually:

```text
Before
  file A.py -> mypy(A.py, follow_imports=skip) -> types(A) with Any holes
  file B.py -> mypy(B.py, follow_imports=skip) -> types(B) with Any holes

After
  package/  -> mypy(all files, follow_imports=normal) -> types(A,B,...) consistent
  compile each file with shared mypy results
```

This changes the failure mode. When a type can’t be resolved now, it’s much more likely to be a real missing stub or a genuine typing issue, not an artifact of our configuration.

### IR dump: what “good” looks like

When type tracking is intact, the IR makes the access explicit, and it looks boring. That’s the point.

```text
# prelude:
  _tmp1 = self.config.value
return _tmp1
```

That single line `_tmp1 = self.config.value` is where `py_type` matters. If `self.config` is known to be `Config`, the emitter can choose the direct struct access path.

### Generated C: proper type resolution

With correct type resolution, `get_value` becomes a native function that returns an unboxed `mp_int_t` and reads the field directly:

```c
static mp_int_t myapp_App_get_value_native(myapp_App_obj_t *self) {
    mp_int_t _tmp1 = ((myapp_Config_obj_t *)MP_OBJ_TO_PTR(self->config))->value;
    return _tmp1;
}
```

Two details matter here:

- Return type is `mp_int_t` (unboxed), driven by `CType.MP_INT_T`.
- Field access is `->value` after a cast to `myapp_Config_obj_t *`, driven by `py_type="Config"`.

### Generated C: what happens with Any

With `Any`, the emitter can no longer prove that `self->config` is a `Config`, so it must fall back to the generic attribute lookup path. That changes both the access and, often, the return type:

```c
static mp_obj_t myapp_App_get_value_native(myapp_App_obj_t *self) {
    mp_obj_t _tmp1 = mp_load_attr(self->config, MP_QSTR_value);
    return _tmp1;
}
```

This is valid C, and it often “works”, but it is a different contract:

- The function now returns `mp_obj_t`.
- The caller must treat the result as boxed.
- The access incurs runtime lookup.

This is why “both map to `MP_OBJ_T`” is not enough. `py_type` is the key that keeps the compiler on the right side of the specialization boundary.

### Tightening types once package checking works

After switching to package-level type checking, mypy starts telling the truth about what it can and can’t prove across modules. Some annotations that were previously vague become active problems.

One example was an initializer that had been typed as `object`. That hides intent from mypy and from the compiler. Changing it to a precise callable type made the contract explicit:

```python
init_fn: Callable[[], tuple[object, Cmd]]
```

This is not about pleasing mypy. It is about keeping the compiler’s type pipeline intact so the IR builder can keep producing concrete `py_type` strings that unlock correct code generation.

### What this enables next

With package-level typing and a resilient `Any` fallback, the compiler can safely lean harder on `py_type`:

- More native fast paths for attribute chains that cross module boundaries.
- Fewer “unresolvable chain” fallbacks that quietly turn expressions into `None`.
- Clearer rules for when a value can be unboxed, and when it must stay boxed.

The bigger win is confidence. If a type degrades to `Any` now, it is a real signal. We can treat it as a typing problem to fix, not a mystery that only shows up after C is generated and flashed to a device.
