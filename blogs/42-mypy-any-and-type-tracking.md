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

Before tracing the bug, we need to walk through the actual code that extracts, transforms, and consumes type information. Every function in this chain is a place where `Any` can silently corrupt the output.

### Step 1: mypy extraction -- `TypeCheckResult` and `_extract_type_info`

The type checker module (`type_checker.py`) runs mypy on source files and returns structured results. The key data structures:

```python
@dataclass
class ClassTypeInfo:
    name: str
    fields: list[tuple[str, str]]    # (field_name, type_string) pairs
    methods: list[FunctionTypeInfo]
    base_class: str | None = None

@dataclass
class FunctionTypeInfo:
    name: str
    params: list[tuple[str, str]]    # (param_name, type_string) pairs
    return_type: str
    local_types: dict[str, str] = field(default_factory=dict)

@dataclass
class TypeCheckResult:
    success: bool
    errors: list[str]
    functions: dict[str, FunctionTypeInfo]
    classes: dict[str, ClassTypeInfo]
    module_types: dict[str, str]
```

The extraction happens in `_extract_type_info()`. For each class, mypy provides a `TypeInfo` object with a symbol table. We iterate over it:

```python
# From _extract_class_info_from_typeinfo()
for member_name, sym in type_info.names.items():
    node = sym.node
    if isinstance(node, Var):
        field_type = str(node.type) if node.type else "Any"
        field_type = _clean_type_str(field_type)
        fields.append((member_name, field_type))
```

This is where the problem begins. When mypy cannot resolve an import, `node.type` still exists -- it just evaluates to `Any`. The `str()` call produces `"Any"`, and that string propagates forward.

For a working import, this produces `("subscribe_fn", "Callable[[], Sub] | None")`. For a broken import, it produces `("subscribe_fn", "Any")`.

### Step 2: passing mypy results to the IR builder

The compiler wraps the extracted information into `MypyTypeInfo` and passes it to `IRBuilder`:

```python
@dataclass
class MypyTypeInfo:
    functions: dict[str, FunctionTypeInfo]
    classes: dict[str, ClassTypeInfo]
    module_types: dict[str, str]

class IRBuilder:
    def __init__(self, module_name, ..., mypy_types=None):
        self._mypy_types = mypy_types   # stored for later lookups
        self._known_classes = ...        # ClassIR registry (all compiled classes)
```

The IR builder receives two inputs that both carry type information:

1. **`mypy_types`** -- mypy's semantic analysis results (what mypy proved)
2. **`_known_classes`** -- the compiler's own registry of compiled class IR (what we built)

These two sources can disagree. That disagreement is the root of the bug.

### Step 3: field type resolution in `_parse_class_body`

When the IR builder encounters a class field annotation like `program: Program`, it must decide on a `py_type` and a `CType`. The logic in `_parse_class_body()` has three tiers:

```python
# Tier 1: mypy provided a type for this field
if field_name in mypy_field_types:
    mypy_py = self._mypy_type_to_py_type(mypy_field_types[field_name])
    # ... use mypy_py ...
    c_type = CType.from_python_type(py_type)

# Tier 2: no mypy info, but there is an annotation in the source
elif inner_annotation is not None:
    py_type = self._annotation_to_py_type(inner_annotation)
    c_type = CType.from_python_type(py_type)

# Tier 3: bare Final without type -- infer from value
else:
    py_type = "object"
```

Two helper functions do the actual string conversion:

**`_mypy_type_to_py_type()`** converts mypy's type string to our `py_type` convention:

```python
def _mypy_type_to_py_type(self, mypy_type: str) -> str:
    base_type = mypy_type.split("[")[0].strip()  # "list[int]" -> "list"
    if base_type in ("int", "float", "bool", "str", "list", ...):
        return base_type
    if "." in base_type:
        return base_type.split(".")[-1]           # "pkg.Config" -> "Config"
    return base_type if base_type else "object"
```

**`_annotation_to_py_type()`** reads directly from the Python AST annotation node:

```python
def _annotation_to_py_type(self, annotation: ast.expr | None) -> str:
    if annotation is None:
        return "object"
    if isinstance(annotation, ast.Name):
        return annotation.id                        # "Program" -> "Program"
    elif isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name):
            return annotation.value.id              # "list[int]" -> "list"
    return "object"
```

Notice the difference: `_mypy_type_to_py_type` trusts whatever mypy says. `_annotation_to_py_type` reads the raw AST. When mypy is wrong, the AST is still right.

The `py_type` then gets converted to a `CType` via a static mapping:

```python
class CType(Enum):
    @staticmethod
    def from_python_type(type_str: str) -> CType:
        mapping = {
            "int": CType.MP_INT_T,
            "float": CType.MP_FLOAT_T,
            "bool": CType.BOOL,
            "str": CType.MP_OBJ_T,
            "object": CType.MP_OBJ_T,
            # ... everything else maps to MP_OBJ_T
        }
        return mapping.get(base_type, CType.MP_OBJ_T)
```

This is the critical collapse point. Both `"Program"` and `"Any"` map to `CType.MP_OBJ_T`. The `CType` is identical. Only `py_type` remembers the difference.

The resulting field ends up in the IR:

```python
field_ir = FieldIR(
    name="program",
    py_type="Program",   # or "Any" if mypy lost the type
    c_type=CType.MP_OBJ_T,
    ...
)
class_ir.fields.append(field_ir)
```

### Step 4: chained attribute resolution -- `_get_method_attr_class_type`

When the compiler encounters `self.program.subscribe_fn`, it must resolve the type at each step in the chain. This is where `py_type` on the field IR becomes the make-or-break decision point.

The function `_get_method_attr_class_type()` walks the chain recursively:

```python
def _get_method_attr_class_type(self, expr, class_ir) -> str | None:
    if isinstance(expr.value, ast.Name):
        var_name = expr.value.id
        if var_name == "self":
            # Look up field py_type from the current class
            for fld in class_ir.get_all_fields():
                if fld.name == expr.attr:
                    return self._resolve_class_name_from_type_str(fld.py_type)

    elif isinstance(expr.value, ast.Attribute):
        # Recursive: resolve the parent first, then look up the attr
        parent_type = self._get_method_attr_class_type(expr.value, class_ir)
        if parent_type and parent_type in self._known_classes:
            parent_ir = self._known_classes[parent_type]
            for fld in parent_ir.get_all_fields():
                if fld.name == expr.attr:
                    return self._resolve_class_name_from_type_str(fld.py_type)
    return None
```

Follow the chain for `self.program.subscribe_fn`:

```text
Step 1: expr = Attribute(value=Attribute(value=Name('self'), attr='program'), attr='subscribe_fn')
        -> Recurse on Attribute(value=Name('self'), attr='program')

Step 2: var_name = 'self', attr = 'program'
        -> Find field 'program' in App's fields
        -> fld.py_type = ???

  If py_type = "Program":  -> _resolve_class_name_from_type_str("Program") -> "Program"
                           -> Look up Program in _known_classes -> found
                           -> Find 'subscribe_fn' in Program's fields -> success
                           -> Return the field's type -> enables native access

  If py_type = "Any":      -> _resolve_class_name_from_type_str("Any") -> None
                           -> Return None
                           -> Caller gets None -> falls back to mp_const_none
```

The `_resolve_class_name_from_type_str()` function handles edge cases like `Optional` unions and dotted module paths, but it cannot recover from `"Any"` -- that string does not name a class, so it returns `None`.

### Step 5: emitter -- how py_type becomes C code

At emission time, the IR carries enough information for the emitter to choose a path. The `_emit_obj_attr_assign()` method in `function_emitter.py` shows the fork clearly:

```python
def _emit_obj_attr_assign(self, stmt, native=False) -> list[str]:
    if stmt.obj_class is not None:
        # Native path: direct struct field access
        lines.append(
            f"    (({stmt.obj_class}_obj_t *)MP_OBJ_TO_PTR({stmt.obj_name}))"
            f"->{stmt.attr_path} = {value_expr};"
        )
    else:
        # Generic path: runtime attribute lookup
        boxed_value = self._box_value(value_expr, value_type)
        lines.append(
            f"    mp_store_attr({stmt.obj_name}, MP_QSTR_{stmt.attr_name}, {boxed_value});"
        )
```

`stmt.obj_class` is `None` when the IR builder could not resolve the class type -- which happens exactly when `py_type` was `"Any"`.

### IR preview: the complete chain, good vs broken

Here is what the IR looks like for a method that reads `self.program.subscribe_fn` and checks if it is `None`.

**With correct type resolution (`py_type="Program"`):**

```text
def _setup_subscriptions(self: MP_OBJ_T) -> VOID:
  c_name: lvgl_mvu_app_App__setup_subscriptions
  locals: {}
  body:
    # prelude:
      _tmp1 = self.program           # AttrAccessIR: class_c_name="lvgl_mvu_app_App"
      _tmp2 = _tmp1.subscribe_fn     # AttrAccessIR: class_c_name="lvgl_mvu_program_Program"
    if _tmp2 is None:
      return
    # ... subscription setup continues
```

Each `AttrAccessIR` carries a `class_c_name` that tells the emitter which struct to cast to. The chain resolves because `self.program` has `py_type="Program"`, so step 2 knows to look in `Program`'s fields.

**With broken type resolution (`py_type="Any"`):**

```text
def _setup_subscriptions(self: MP_OBJ_T) -> VOID:
  c_name: lvgl_mvu_app_App__setup_subscriptions
  locals: {}
  body:
    if mp_const_none is None:         # <- always true! subscribe_fn was unresolvable
      return
    # ... subscription setup never reached
```

The IR builder could not resolve the chain, so it substituted `mp_const_none` as a safe sentinel. The condition becomes tautologically true. No subscriptions are ever set up.

### Generated C side by side

**Correct (native chain):**

```c
// self.program -> direct struct access
lvgl_mvu_program_Program_obj_t *_tmp1 =
    (lvgl_mvu_program_Program_obj_t *)MP_OBJ_TO_PTR(self->program);
// _tmp1.subscribe_fn -> direct struct access
mp_obj_t _tmp2 = _tmp1->subscribe_fn;
// None check on actual field value
if (_tmp2 == mp_const_none) { return mp_const_none; }
```

**Broken (Any fallback):**

```c
// subscribe_fn unresolvable -- substituted with None
if (mp_const_none == mp_const_none) { return mp_const_none; }
// always returns -- subscription setup dead code
```

### Bug 5 story: the root cause chain

With the implementation walkthrough above, the failure path becomes mechanical:

1. `app.py` imports `from lvgl_mvu.program import Program`
2. mypy type-checks `app.py` in isolation (per-file mode, `follow_imports="skip"`)
3. mypy can't follow the import, so it reports `Program` fields as `Any`
4. `_extract_type_info()` stores `("program", "Any")` in `ClassTypeInfo.fields`
5. `_parse_class_body()` calls `_mypy_type_to_py_type("Any")` which returns `"Any"`
6. `CType.from_python_type("Any")` returns `MP_OBJ_T` -- looks normal
7. `FieldIR(name="program", py_type="Any", c_type=MP_OBJ_T)` -- the poison is set
8. `_get_method_attr_class_type()` looks up `fld.py_type` for `program` field
9. `_resolve_class_name_from_type_str("Any")` returns `None` -- not a known class
10. Chained attribute `self.program.subscribe_fn` is unresolvable -> `mp_const_none`
11. `if self.program.subscribe_fn is None` becomes always true
12. `_setup_subscriptions()` returns early -- no timers, no events

The key point is step 5. `CType` was fine. `py_type` was poisoned. Everything downstream followed logically from that one corrupted string.

### The fallback fix: prefer the annotation over mypy's Any

The fastest safe fix was to add a guard in `_parse_class_body()` at step 5:

```python
if field_name in mypy_field_types:
    mypy_py = self._mypy_type_to_py_type(mypy_field_types[field_name])
    # NEW: when mypy says Any, check if the AST annotation names a known class
    if mypy_py in ("Any", "object") and inner_annotation is not None:
        ann_py = self._annotation_to_py_type(inner_annotation)
        if ann_py in self._known_classes:
            py_type = ann_py  # Use annotation instead of mypy's Any
        else:
            py_type = mypy_py
    else:
        py_type = mypy_py
```

The same guard is applied in method parameter resolution:

```python
# In _parse_class_body(), method parameter processing:
for arg in method_args:
    if arg.arg in mypy_param_types:
        mypy_py = self._mypy_type_to_py_type(mypy_param_types[arg.arg])
        if mypy_py in ("Any", "object") and arg.annotation is not None:
            ann_py = self._annotation_to_py_type(arg.annotation)
            if ann_py in self._known_classes:
                py_type = ann_py
```

This is intentionally conservative:

- It only triggers when mypy explicitly returned `Any` or `object`.
- It only accepts the annotation if it names a class the compiler already knows.
- It does not override mypy when mypy returns a concrete type.

It is a bandage, but it turned a silent type erasure into a recoverable case.

### The real fix: package-level type checking

The real problem was running mypy in per-file mode with imports skipped. That configuration is attractive because it is fast and it avoids pulling in the world, but it breaks cross-module type resolution. In a compiler, that is not "slightly worse types", it is "wrong compilation decisions".

The solution was `type_check_package()` -- run mypy on the whole package at once.

The critical configuration change:

```python
# Per-file mode (old) -- fast but blind to imports
options.follow_imports = "skip"

# Package mode (new) -- sees cross-module types correctly
options.follow_imports = "normal"
options.mypy_path = [str(package_path.parent)]  # so mypy can find the package
```

The function builds a `BuildSource` for every `.py` file in the package and runs mypy once:

```python
def type_check_package(package_dir) -> dict[str, TypeCheckResult]:
    sources = []
    for py_file in sorted(package_path.glob("*.py")):
        stem = py_file.stem
        qualified = f"{pkg_name}.{stem}" if stem != "__init__" else pkg_name
        sources.append(BuildSource(str(py_file), qualified, None))

    build_result = mypy_build.build(sources=sources, options=options)

    # Distribute results back to per-file compilation
    results = {}
    for stem, qualified in submodule_names.items():
        mypy_file = build_result.files.get(qualified)
        if mypy_file:
            _extract_type_info(mypy_file, functions, classes, module_types)
        results[stem] = TypeCheckResult(...)
    return results
```

The compilation pipeline then uses pre-computed results instead of running mypy per file:

```python
# In compiler.py -- _scan_package_recursive()
pkg_type_results = type_check_package(package_dir)  # once, before compilation loop

for submodule in submodules:
    sub_type_result = pkg_type_results.get(submodule_name)
    parts = _compile_module_parts(..., mypy_type_result=sub_type_result)
```

Conceptually:

```text
Before
  file A.py -> mypy(A.py, follow_imports=skip) -> types(A) with Any holes
  file B.py -> mypy(B.py, follow_imports=skip) -> types(B) with Any holes

After
  package/  -> mypy(all files, follow_imports=normal) -> types(A,B,...) consistent
  compile each file with shared mypy results
```

This changes the failure mode. When a type can't be resolved now, it's much more likely to be a real missing stub or a genuine typing issue, not an artifact of our configuration.

### Tightening types once package checking works

After switching to package-level type checking, mypy starts telling the truth about what it can and can't prove across modules. Some annotations that were previously vague become active problems.

One example was an initializer that had been typed as `object`. That hides intent from mypy and from the compiler. Changing it to a precise callable type made the contract explicit:

```python
# Before: vague
init_fn: object
update_fn: object

# After: precise -- mypy can verify callers, compiler can track types
init_fn: Callable[[], tuple[object, Cmd]]
update_fn: Callable[[object, object], tuple[object, Cmd]]
```

This is not about pleasing mypy. It is about keeping the compiler's type pipeline intact so the IR builder can keep producing concrete `py_type` strings that unlock correct code generation.

### What this enables next

With package-level typing and a resilient `Any` fallback, the compiler can safely lean harder on `py_type`:

- More native fast paths for attribute chains that cross module boundaries.
- Fewer "unresolvable chain" fallbacks that quietly turn expressions into `None`.
- Clearer rules for when a value can be unboxed, and when it must stay boxed.

The bigger win is confidence. If a type degrades to `Any` now, it is a real signal. We can treat it as a typing problem to fix, not a mystery that only shows up after C is generated and flashed to a device.
