# 38. LVGL MVU Diffing Engine: Compiling a Widget Tree Reconciler to C

This post covers the compilation of a real-world algorithmic module -- an O(N) widget tree diffing engine for an LVGL Model-View-Update framework -- and the compiler improvements required to get it running natively on an ESP32-C6 microcontroller.

The diffing engine is not a toy example. It uses `@dataclass`, `Optional` type narrowing, module-level variables, function-as-value references, cross-package class instantiation, and boxed object comparison. Getting all of these to compile correctly exposed several gaps in the compiler that this post walks through.

## Part 1: Compiler Theory - What a Diffing Engine Needs

### The problem: virtual DOM reconciliation on a microcontroller

The Model-View-Update (MVU) architecture describes UI as a pure function from state to widget trees. When state changes, the framework builds a new widget tree and compares it against the previous one. The diff drives minimal updates to the real UI objects.

On a desktop, this is React or Elm. On a microcontroller running MicroPython with LVGL, the same algorithm needs to run in native C for acceptable frame rates.

The diffing engine has four functions:

| Function | Purpose |
|----------|---------|
| `diff_scalars` | Two-pointer merge diff on sorted attribute tuples |
| `can_reuse` | Check if an LVGL object can be reused (type + key match) |
| `diff_children` | Positional child diffing with insert/remove/replace/update |
| `diff_widgets` | Top-level orchestration with Optional narrowing for initial render |

### Why this is a hard compilation target

The diffing code uses almost every feature the compiler supports:

1. **`@dataclass` construction inside loops** -- `AttrChange(...)` and `ChildChange(...)` created during iteration
2. **Optional narrowing** -- `diff_widgets(prev: Widget | None, next_w: Widget)` branches on `prev is None`
3. **Boxed object comparison** -- `prev[i].value != next_attrs[j].value` where values are `object` (any MicroPython type)
4. **Boolean expressions in conditions** -- `while i < len(prev) or j < len(next_attrs)`
5. **Cross-package class references** -- `diff.py` instantiates `AttrChange` and `ChildChange` from the same package
6. **Method calls with preludes** -- list `.append()` inside while loops with complex arguments

Each of these required either new IR support or fixes to existing emission.

### The compilation pipeline for a package module

The LVGL MVU framework is a Python package:

```
extmod/lvgl_mvu/
    __init__.py
    widget.py      # Widget, ScalarAttr dataclasses + WidgetKey IntEnum
    attrs.py       # Attribute key constants
    builders.py    # Widget builder functions
    diff.py        # Diffing engine (this post)
```

The compiler processes this as a single C module with namespaced submodules. Each `.py` file becomes a set of C functions with a module-prefix (`widget_`, `diff_`, etc.), and they can call each other through direct C function calls -- no Python import overhead at runtime.

## Part 2: C Background - Boxed Object Comparison

### The `mp_obj_t` equality problem

In MicroPython's C API, all Python objects are represented as `mp_obj_t` (a machine-word-sized value). When comparing two `mp_obj_t` values, you cannot simply use C's `==` operator. Consider:

```c
// WRONG: C pointer equality, not Python value equality
if (prev_value == next_value) { ... }

// RIGHT: Python-semantics equality
if (mp_obj_equal(prev_value, next_value)) { ... }
```

`mp_obj_equal()` calls the object's `__eq__` method, handles small-int optimization, and correctly compares strings by value. The C `==` only checks pointer identity.

For ordering comparisons (`<`, `<=`, `>`, `>=`), MicroPython provides `mp_binary_op()`:

```c
// Python: a < b (where a, b are arbitrary objects)
mp_obj_is_true(mp_binary_op(MP_BINARY_OP_LESS, a, b))
```

The `mp_binary_op` returns a Python bool object, which `mp_obj_is_true` converts to a C `bool`.

### When to use `mp_obj_equal` vs native comparison

The compiler must decide at each comparison site:

| Left type | Right type | Strategy |
|-----------|-----------|----------|
| `mp_int_t` | `mp_int_t` | Native C: `a == b` |
| `mp_int_t` | `mp_obj_t` | Unbox right: `a == mp_obj_get_int(b)` |
| `mp_obj_t` | `mp_obj_t` | Boxed: `mp_obj_equal(a, b)` |

Before this change, the compiler would always try to unbox both sides to `mp_int_t` when either was `mp_obj_t`. This was wrong for `object`-typed values (strings, floats, nested objects) -- unboxing a string to int crashes at runtime.

### Boolean truthiness conversion

Another subtle issue: MicroPython's `mp_obj_t` booleans are not C booleans. When an `mp_obj_t` value is used in a C `if()` or `while()` condition, it must be converted:

```c
// WRONG: mp_obj_t is a pointer, always truthy (non-NULL)
if (some_mp_obj) { ... }

// RIGHT: check Python truthiness
if (mp_obj_is_true(some_mp_obj)) { ... }
```

The compiler now inserts `_to_bool_expr()` calls at every branch point: `if`, `while`, ternary `?:`, and `not` operator.

## Part 3: Implementation - Seven Compiler Improvements

### 1. FuncRefIR: Functions as first-class values

The builders module uses `sorted()` with a `key=` argument:

```python
def _sort_attrs(attrs: list[ScalarAttr]) -> list[ScalarAttr]:
    return sorted(attrs, key=_attr_sort_key)
```

Previously, the compiler had no way to reference a module-level function as a value. The new `FuncRefIR` node handles this:

```
IR: FuncRefIR(py_name="_attr_sort_key", c_name="builders__attr_sort_key")
C:  MP_OBJ_FROM_PTR(&builders__attr_sort_key_obj)
```

The compiler pre-scans all function definitions in a module before building IR, so forward references work -- a function defined on line 50 can reference a function defined on line 100.

### 2. kwargs in CallIR: `sorted(items, key=func)`

`sorted()` with keyword arguments required extending `CallIR` with a `kwargs` field. The emission generates a `mp_call_function_n_kw` call:

```c
// sorted(attrs, key=_attr_sort_key)
mp_call_function_n_kw(
    mp_load_global(MP_QSTR_sorted),
    1, 1,  // 1 positional, 1 keyword
    (const mp_obj_t[]){
        boxed_attrs,
        MP_OBJ_NEW_QSTR(MP_QSTR_key),
        MP_OBJ_FROM_PTR(&builders__attr_sort_key_obj)
    }
)
```

### 3. Boxed comparison: `mp_obj_equal()` for `mp_obj_t` operands

The diff engine compares `ScalarAttr.value` fields, which are typed as `object`. The IR for this looks like:

```
IR: CompareIR(left=_tmp17, ops=["!="], comparators=[_tmp18])
    where _tmp17 and _tmp18 are both MP_OBJ_T
```

The emitter now detects when both sides are `mp_obj_t` and emits:

```c
// prev[i].value != next_attrs[j].value
(!mp_obj_equal(_tmp17, _tmp18))
```

Instead of the previous incorrect:

```c
// WRONG: would crash trying to mp_obj_get_int() on a string
(mp_obj_get_int(_tmp17) != mp_obj_get_int(_tmp18))
```

### 4. Boolean truthiness: `_to_bool_expr()` at branch points

The `can_reuse` function has this condition:

```python
if prev.user_key != "" or next_w.user_key != "":
```

The IR for this is:

```
def can_reuse(prev: MP_OBJ_T, next_w: MP_OBJ_T) -> BOOL:
  c_name: diff_can_reuse
  body:
    if (prev.key != next_w.key):
      return False
    if ((prev.user_key != "") || (next_w.user_key != "")):
      return (prev.user_key == next_w.user_key)
    return True
```

The `||` operator produces an `mp_obj_t` in C when the operands are boxed comparisons. The emitter now wraps it with truthiness conversion so the `if()` condition is a proper C boolean.

### 5. Module-level variables: lazy initialization

The diff module uses module-level constant strings:

```python
CHANGE_ADDED: str = "added"
CHANGE_REMOVED: str = "removed"
CHILD_INSERT: str = "insert"
```

These are registered as module constants and inlined at use sites. But some modules also need module-level mutable containers (dicts, lists). The new `register_module_var()` method tracks these, and the module emitter generates:

```c
static mp_obj_t module_my_dict;
static bool module__module_inited = false;

static void module__module_init(void) {
    if (module__module_inited) return;
    module__module_inited = true;
    module_my_dict = mp_obj_new_dict(0);
}
```

Every function in the module gets an `module__module_init()` call injected at the top. The boolean guard ensures initialization happens exactly once.

### 6. Cross-package enum resolution

The `widget.py` module defines `WidgetKey` as an `IntEnum`. When `diff.py` (in the same package) references these values, the compiler needs to resolve them across module boundaries. The `known_enums` parameter now flows through the compilation pipeline alongside `known_classes`, so sibling modules can resolve each other's enum constants at compile time.

### 7. SelfMethodCallIR param type boxing

When a method calls another method on `self`, the arguments need correct boxing based on the target method's parameter types, not the caller's expression types. The new `param_types` field on `SelfMethodCallIR` carries this information from the IR builder to the emitter:

```python
# If target method expects mp_obj_t but caller has mp_int_t:
args.append(mp_obj_new_int(native_int_value))

# If target method expects mp_int_t and caller has mp_int_t:
args.append(native_int_value)  # no boxing needed
```

## The diff_widgets IR

The top-level function demonstrates Optional narrowing in action:

```
def diff_widgets(prev: MP_OBJ_T, next_w: MP_OBJ_T) -> MP_OBJ_T:
  c_name: diff_diff_widgets
  max_temp: 2
  locals: {prev: MP_OBJ_T, next_w: MP_OBJ_T, scalar_changes: MP_OBJ_T,
           a: MP_OBJ_T, child_changes: MP_OBJ_T, i: MP_INT_T,
           c: MP_OBJ_T, has_events: BOOL}
  body:
    if (prev is None):
      scalar_changes: mp_obj_t = []
      for a in next_w.scalar_attrs:
        # prelude:
          _tmp1 = scalar_changes.append(
              AttrChange(CHANGE_ADDED, a.key, None, a.value))
        _tmp1
      child_changes: mp_obj_t = []
      i: mp_int_t = 0
      for c in next_w.children:
        # prelude:
          _tmp2 = child_changes.append(
              ChildChange(CHILD_INSERT, i, c, None))
        _tmp2
        i += 1
      has_events: bool = (len(next_w.event_handlers) > 0)
      return WidgetDiff(scalar_changes, child_changes, has_events)
    return WidgetDiff(
        diff_scalars(prev.scalar_attrs, next_w.scalar_attrs),
        diff_children(prev.children, next_w.children),
        _events_changed(prev.event_handlers, next_w.event_handlers))
```

The `if (prev is None)` branch handles initial render (no previous tree). After the guard, `prev` is narrowed to `Widget` and attribute access uses dynamic dispatch through `mp_load_attr` -- correct because `Widget` is defined in a sibling module and may have different struct layouts.

## The diff_scalars IR

The two-pointer merge algorithm:

```
def diff_scalars(prev: MP_OBJ_T, next_attrs: MP_OBJ_T) -> MP_OBJ_T:
  c_name: diff_diff_scalars
  max_temp: 22
  locals: {prev: MP_OBJ_T, next_attrs: MP_OBJ_T,
           changes: MP_OBJ_T, i: MP_INT_T, j: MP_INT_T}
  body:
    changes: mp_obj_t = []
    i: mp_int_t = 0
    j: mp_int_t = 0
    while ((i < len(prev)) || (j < len(next_attrs))):
      if (i >= len(prev)):
        # prelude:
          _tmp1 = next_attrs[j].key
          _tmp2 = next_attrs[j].value
          _tmp3 = changes.append(
              AttrChange(CHANGE_ADDED, _tmp1, None, _tmp2))
        _tmp3
        j += 1
      else:
        if (j >= len(next_attrs)):
          ...
        else:
          if (_tmp7 < _tmp8):
            ...
          else:
            if (_tmp12 > _tmp13):
              ...
            else:
              if (_tmp17 != _tmp18):
                ...
              i += 1
              j += 1
    return changes
```

Note `max_temp: 22` -- the two-pointer algorithm with nested attribute access generates many temporaries. Each `next_attrs[j].key` is a subscript + attribute chain that requires a temp to hold the intermediate result. The prelude pattern keeps these side effects ordered correctly.

## Build and verification

The full pipeline: Python source to running on ESP32-C6:

```
$ pytest -q
1002 passed in 24.32s

$ make compile-all
Compiling 30+ modules + 2 packages...

$ make build BOARD=ESP32_GENERIC_C6
Using 8MiB flash + LVGL partition table (4.5MB app)
application @0x010000  2652368  (2131760 remaining)

$ make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem101

$ make run-device-tests PORT=/dev/cu.usbmodem101
@S:lvgl_mvu_diff
  OK: scalar_attr key
  OK: scalars no change
  OK: scalars updated len
  OK: scalars updated kind
  OK: ...
  OK: diff None events flag
@D:495|495|0
ALL 495 TESTS PASSED
```

45 new device tests exercise the diff engine on real hardware, covering:
- Widget and ScalarAttr construction
- Scalar diffing: no change, value updated, added, removed
- Widget reuse: same type, different type, matching/mismatching user keys
- Child diffing: no change, updated, inserted, removed, replaced
- Full widget diff: identical, scalar changes, child changes, event changes
- Optional path: `prev=None` (initial render)
- Event handler equality (value comparison, not identity)

## What this proves

A 207-line Python module implementing an O(N) two-pointer merge diff algorithm compiles to native C and runs on an ESP32-C6 with 320KB RAM. The generated code handles:
- Dynamic `@dataclass` construction in tight loops
- Boxed object comparison with correct Python semantics
- Optional narrowing for the initial-render fast path
- Cross-module function calls within a compiled package

No interpreter overhead. No Python bytecode. Just C function calls and struct operations, with correct MicroPython runtime integration for the parts that need it.
