# 37. Optional Narrowing: Turning `X | None` Guards into Static Dispatch

This post builds directly on blog 36, where trait types and union types forced the compiler to choose between fast, unsafe struct access and slower, correct dynamic attribute lookup.

`Optional[T]` (spelled `T | None`) looks like a small union, but it shows up everywhere in real code, especially in UI diffing and tree algorithms. The key idea is type narrowing: after a `None` guard, the compiler can treat a value as its concrete class type again.

In `mypyc-micropython`, that narrowing becomes a concrete optimization: after a `None` check, field access can use direct struct reads instead of `mp_load_attr`.

## Part 1: Compiler Theory - Type Narrowing

### What `Optional` means in Python's type system

When you write:

```python
def get_x(p: Point | None) -> int:
    ...
```

you are telling the type checker that `p` is either:

- an instance of `Point`, or
- the singleton `None`

`Point | None` is just a union. In typing terms, it is the same idea as `Union[Point, None]`.

### Why `Optional` creates the same layout problem as traits

In blog 36, trait types forced dynamic dispatch because the compiler could not know the concrete struct layout at the access site. `Optional` creates the same shape of problem:

- For a concrete class `Point`, the compiler can pick `Point_obj_t` and use a fixed offset for `x`.
- For `Point | None`, the compiler cannot blindly cast, because `None` is not a `Point`.

So `Optional` values have an "unknown layout" problem too. It is smaller than a trait, but it is still "not always that struct".

### What type narrowing is

Type narrowing is a control flow rule:

```python
if p is not None:
    # In this block, p is Point (not Point | None)
    return p.x
```

The check splits the program into two paths:

- `p is None`
- `p is Point`

Inside the `p is not None` branch, `p` is narrowed from `Point | None` to `Point`.

There is also an "early return" narrowing pattern:

```python
if p is None:
    return -1
# After the guard, p is Point
return p.y
```

The important part is that narrowing is not a new runtime feature. It is a compile-time fact derived from a runtime test.

### Why narrowing enables optimization

Once a variable is narrowed to a concrete class type, the compiler can safely treat attribute access as static dispatch:

- Before narrowing: treat `p.x` like a trait access, use dynamic lookup.
- After narrowing: emit a direct struct dereference.

This matters because Optional parameters are common, and the code inside the guard is often the hot path.

### Type narrowing in other languages

If you have used other typed languages, you have seen the same concept:

- TypeScript: `if (x !== null) { x.y }` narrows `x`.
- Kotlin: `if (x != null) { x.y }` narrows, and `x?.y` is the safe optional access operator.
- Swift: `if let x = x { x.y }` unwraps and narrows.

Python does not have a special syntax for unwrap, it uses ordinary `None` checks. The idea is the same.

### The problem without narrowing

If the compiler treats `Point | None` as "unknown layout" everywhere, it is forced into dynamic dispatch even after a guard.

That means code like this would still compile as if `p` might be `None`:

```python
def get_x_or_default(p: Point | None, default: int) -> int:
    if p is not None:
        return p.x
    return default
```

The whole point of narrowing is to avoid that pessimism and let the compiler use the concrete layout in the narrowed region.

## Part 2: C Background

### Struct field access vs `mp_load_attr`

From blog 36, the two ways to implement `obj.field` in generated C are:

1. Static dispatch (fast): cast the `mp_obj_t` to a known struct pointer type and read a field offset.
2. Dynamic dispatch (correct for unknown layout): ask the MicroPython runtime to resolve the attribute name at runtime.

The static path looks like:

```c
((optional_narrowing_Point_obj_t *)MP_OBJ_TO_PTR(p))->x
```

The dynamic path looks like:

```c
mp_load_attr(p, MP_QSTR_x)
```

### `None` at the C level

In MicroPython, `None` is a special singleton object exposed in C as `mp_const_none`.

That gives us a very fast check:

```c
if (p == mp_const_none) {
    ...
}
```

This is a pointer comparison. It is cheap and it matches Python's `is` semantics.

### Why dereferencing `None` is unsafe

The struct cast pattern is only valid when the runtime object really is a `Point` instance.

If `p` is actually `mp_const_none`, then:

```c
((Point_obj_t *)MP_OBJ_TO_PTR(p))->x
```

is undefined behavior. You are reading a field offset from an object that does not have that layout. Best case you get garbage, worst case you crash.

### The safety guarantee narrowing provides

Type narrowing connects the fast cast to a runtime safety check:

- The code checks `p != mp_const_none`.
- Only inside the "not None" region does it emit the struct dereference.

That is the whole trick: static field access stays correct because it is guarded.

## Part 3: Implementation - Optional Narrowing Optimization

This optimization lives in the IR builder, because narrowing is a control flow property, not an emitter trick.

### The core idea in `ir_builder.py`

The IR builder tracks which variables are "optional class typed" during function translation:

- `_optional_class_params: set[str]` contains variables that are typed as `X | None`.

When building attribute access on a class-typed variable, it uses that set to decide whether attribute access must be treated as dynamic:

```python
# src/mypyc_micropython/ir_builder.py
use_dynamic = class_ir.is_trait or var_name in self._optional_class_params
...
ParamAttrIR(..., is_trait_type=use_dynamic)
```

The naming is inherited from blog 36. In the IR dump, `ParamAttrIR` prints `# trait` when `is_trait_type=True`. For Optional values, that marker really means "dynamic dispatch required".

### Detecting `None` checks

The builder recognizes `None` checks in `_detect_none_check()`:

- `x is None`
- `x is not None`

It does not try to understand every possible way to write a check. It focuses on the most reliable one, which also maps cleanly to C pointer comparisons.

### Narrowing scopes in `_build_if()`

`_build_if()` applies narrowing by temporarily removing the variable from `_optional_class_params` in the branch where it is known to be non-None.

It also handles the early return guard pattern:

```python
if p is None:
    return ...
# p is narrowed for everything after
```

When the body always exits (return or raise), the builder narrows `p` for the remaining statements.

### A complete example: Python, IR, then C

We'll use `examples/optional_narrowing.py`.

Python:

```python
def get_x_or_default(p: Point | None, default: int) -> int:
    if p is not None:
        return p.x
    return default

def get_y_with_guard(p: Point | None) -> int:
    if p is None:
        return -1
    return p.y
```

IR dump (text format):

```
def get_x_or_default(p: MP_OBJ_T, default: MP_INT_T) -> MP_INT_T:
  c_name: optional_narrowing_get_x_or_default
  max_temp: 0
  locals: {p: MP_OBJ_T, default: MP_INT_T}
  body:
    if (p is not None):
      return p.x
    return default

def get_y_with_guard(p: MP_OBJ_T) -> MP_INT_T:
  c_name: optional_narrowing_get_y_with_guard
  max_temp: 0
  locals: {p: MP_OBJ_T}
  body:
    if (p is None):
      return (-1)
    return p.y
```

Generated C (selected excerpts):

```c
static mp_obj_t optional_narrowing_get_x_or_default(mp_obj_t p_obj, mp_obj_t default_obj) {
    mp_obj_t p = p_obj;
    mp_int_t default_ = mp_obj_get_int(default_obj);

    if ((p != mp_const_none)) {
        return mp_obj_new_int(((optional_narrowing_Point_obj_t *)MP_OBJ_TO_PTR(p))->x);
    }
    return mp_obj_new_int(default_);
}

static mp_obj_t optional_narrowing_get_y_with_guard(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;

    if ((p == mp_const_none)) {
        return mp_obj_new_int((-1));
    }
    return mp_obj_new_int(((optional_narrowing_Point_obj_t *)MP_OBJ_TO_PTR(p))->y);
}
```

Notice the two key results:

- `is None` and `is not None` compile to pointer comparisons against `mp_const_none`.
- After narrowing, `p.x` and `p.y` compile to direct struct reads.

### Before narrowing: why the compiler falls back to `mp_load_attr`

To see what "not narrowed" means in this compiler, here is a small variant that uses a guard pattern the optimizer does not recognize:

Python:

```python
def get_x_with_bad_guard(p: Point | None, default: int) -> int:
    if p != None:
        return p.x
    return default
```

IR dump (notice the `# trait` marker on `p.x`):

```
def get_x_with_bad_guard(p: MP_OBJ_T, default: MP_INT_T) -> MP_INT_T:
  c_name: blog37_optional_badcheck_get_x_with_bad_guard
  max_temp: 0
  locals: {p: MP_OBJ_T, default: MP_INT_T}
  body:
    if (p != None):
      return p.x # trait
    return default
```

Generated C (selected excerpt):

```c
static mp_obj_t blog37_optional_badcheck_get_x_with_bad_guard(mp_obj_t p_obj, mp_obj_t default_obj) {
    mp_obj_t p = p_obj;
    mp_int_t default_ = mp_obj_get_int(default_obj);

    if ((mp_obj_get_int(p) != mp_obj_get_int(mp_const_none))) {
        return mp_load_attr(p, MP_QSTR_x);
    }
    return mp_obj_new_int(default_);
}
```

This is the same static vs dynamic split from blog 36, triggered by Optional instead of traits. The recommended pattern is simple: for both correctness and optimization, use `is None` and `is not None`.

### LVGL MVU: why this matters in `diff_widgets(prev: Widget | None, ...)`

The LVGL MVU diff engine takes an Optional previous widget:

```python
def diff_widgets(prev: Widget | None, next_w: Widget) -> WidgetDiff:
    if prev is None:
        ...
        return WidgetDiff(...)

    return WidgetDiff(
        diff_scalars(prev.scalar_attrs, next_w.scalar_attrs),
        diff_children(prev.children, next_w.children),
        _events_changed(prev.event_handlers, next_w.event_handlers),
    )
```

The algorithm is O(N) and it touches `prev.scalar_attrs`, `prev.children`, and `prev.event_handlers` on every diff.

Before Optional narrowing, those `prev.*` accesses had to use dynamic attribute lookup even though the guard proves `prev` is a real `Widget` in the hot path.

With narrowing:

- the `if prev is None: return ...` becomes the early-return guard pattern
- everything after the guard sees `prev` as a concrete `Widget`
- field access can compile to direct struct reads

### When eliminating Optional entirely is better

Sometimes the best optimization is to remove the union type.

In `extmod/lvgl_mvu/diff.py`, the `user_key` logic uses an empty string sentinel instead of `str | None`:

```python
if prev.user_key != "" or next_w.user_key != "":
    return prev.user_key == next_w.user_key
```

That refactoring avoids Optional in a high-traffic field. It is a tradeoff:

- You lose the explicit "missing" value in the type system.
- You gain a simpler representation and fewer narrowing sites.

In performance-sensitive MicroPython code, using a sentinel can be the right call, especially when the empty value is already meaningful for your domain.

### Testing approach

For compiler changes like this, the most useful checks are:

- IR dumps (`mpy-compile ... --dump-ir text`) to confirm where narrowing applies.
- Generated C inspection to confirm the emitter chooses struct access in narrowed regions and `mp_load_attr` when it cannot prove layout.
