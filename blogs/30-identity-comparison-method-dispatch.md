# 30. Identity Comparisons and Method Argument Dispatch

*Two subtle bugs that broke `is None` checks and object-passing in class methods.*

---

## Table of Contents

1. [Part 1: Compiler Theory](#part-1-compiler-theory)
   - [1.1 Two kinds of comparison](#11-two-kinds-of-comparison)
   - [1.2 The prelude pattern and expression contexts](#12-the-prelude-pattern-and-expression-contexts)
   - [1.3 Why method bodies need special handling](#13-why-method-bodies-need-special-handling)
2. [Part 2: C Background](#part-2-c-background)
   - [2.1 Pointer comparison vs value comparison](#21-pointer-comparison-vs-value-comparison)
   - [2.2 What mp_obj_get_int does](#22-what-mp_obj_get_int-does)
   - [2.3 The boxing/unboxing decision](#23-the-boxingunboxing-decision)
   - [2.4 Native function signatures](#24-native-function-signatures)
3. [Part 3: Implementation](#part-3-implementation)
   - [3.1 Bug 1: Missing identity operators](#31-bug-1-missing-identity-operators)
   - [3.2 Bug 2: Over-eager unboxing](#32-bug-2-over-eager-unboxing)
4. [Device Testing](#device-testing)
5. [Closing](#closing)

---

# Part 1: Compiler Theory

This post documents two bugs found while testing the LVGL navigation module on an ESP32-C6. Both bugs involved the same symptom: "can't convert NoneType to int" or "can't convert LvObj to int". The root causes were different but related to how the compiler handles class method bodies.

## 1.1 Two kinds of comparison

Python has two comparison families that look similar but mean different things:

| Operator | What it tests | Python example |
|----------|---------------|----------------|
| `==`, `!=` | Value equality | `x == 5` |
| `is`, `is not` | Object identity | `x is None` |

For primitive types like integers, `==` compares numeric values. For objects, `==` calls `__eq__` and can be customized. But `is` always checks whether two references point to the same object in memory.

This distinction matters for `None` checks:

```python
# Correct: identity check
if allowed_children is None:
    return True

# Wrong: equality check (calls __eq__)
if allowed_children == None:
    return True
```

The first form is idiomatic Python. It checks if `allowed_children` literally points to the singleton `None` object. The second form works but is slower and can misbehave if the object has a broken `__eq__`.

## 1.2 The prelude pattern and expression contexts

In `mypyc-micropython`, every expression builds into a pair:

```
(ValueIR, list[InstrIR])
```

- **ValueIR**: The result value (a name, constant, temp, or compound expression)
- **list[InstrIR]**: Instructions that must execute before the value is valid (the "prelude")

This separation is critical. Consider:

```python
if self._allowed_children is None:
```

The comparison `self._allowed_children is None` must:
1. Load `self._allowed_children` (an attribute access)
2. Load `None` (a constant)
3. Compare them with identity semantics

The IR builder parses this into a `CompareIR` node with:
- `left`: a `SelfAttrIR` for `self._allowed_children`
- `ops`: `["is"]`
- `comparators`: a `ConstIR` with value `None`

## 1.3 Why method bodies need special handling

The IR builder has two code paths for building expressions:

1. **`_build_expr`** - For standalone functions
2. **`_build_method_expr`** - For class methods

Method bodies need special handling because they can access:
- `self.attr` - Instance attributes
- `self.method()` - Instance method calls
- `param.attr` - Typed parameter attributes (when parameter is a known class)

The method expression builder must recognize these patterns and emit the correct IR nodes (`SelfAttrIR`, `SelfMethodCallIR`, `ParamAttrIR`).

Here's the problem: these two builders evolved separately, and the method builder was missing some operator mappings that the function builder had.

---

# Part 2: C Background

## 2.1 Pointer comparison vs value comparison

In C, comparing two pointers checks if they point to the same memory address:

```c
mp_obj_t a = mp_const_none;
mp_obj_t b = mp_const_none;

if (a == b) {
    // True: both point to the same singleton
}
```

This is exactly what Python's `is` operator should compile to. The `mp_const_none` is a global singleton, and any `None` in Python points to it.

Contrast with value comparison:

```c
mp_int_t x = mp_obj_get_int(obj_a);
mp_int_t y = mp_obj_get_int(obj_b);

if (x == y) {
    // Compares numeric values
}
```

This extracts integer values from boxed objects and compares them. It's appropriate for `==` on integers, but wrong for identity checks.

## 2.2 What mp_obj_get_int does

MicroPython's `mp_obj_get_int` extracts an integer from a boxed object:

```c
mp_int_t mp_obj_get_int(mp_obj_t obj);
```

If `obj` is a small integer (tagged pointer), it extracts the value. If `obj` is a heap-allocated big integer, it reads from the object. But if `obj` is `None`, a string, or any non-integer type, it raises:

```
TypeError: can't convert NoneType to int
```

This is the error we saw. The compiler was incorrectly calling `mp_obj_get_int` on objects that weren't integers.

## 2.3 The boxing/unboxing decision

When generating native C code, the compiler must decide:
- Should this value stay boxed as `mp_obj_t`?
- Should it be unboxed to a native type like `mp_int_t`?

The decision depends on how the value will be used:

| Context | Decision |
|---------|----------|
| Arithmetic operations | Unbox to `mp_int_t` or `mp_float_t` |
| Comparison with `==`, `<`, etc. | Usually unbox for primitives |
| Identity comparison (`is`) | Keep boxed, compare pointers |
| Passing to functions expecting `mp_obj_t` | Keep boxed |
| Storing in `mp_obj_t` fields | Keep boxed |

The bugs we found involved incorrect unboxing decisions.

## 2.4 Native function signatures

When the compiler generates a class method, it emits two functions:

```c
// Native version: uses C types directly
static void Nav__safe_delete_native(Nav_obj_t *self, mp_obj_t screen);

// MP wrapper: converts from/to mp_obj_t for runtime calls
static mp_obj_t Nav__safe_delete_mp(mp_obj_t self_in, mp_obj_t screen_obj);
```

When native code calls another native method (like `self._safe_delete(screen)`), it should call the `_native` version directly with the correct types. If the parameter expects `mp_obj_t`, the argument should be passed as-is, not unboxed.

---

# Part 3: Implementation

## 3.1 Bug 1: Missing identity operators

### The symptom

Testing the `Nav` class with `_allowed_children: tuple | None`:

```python
def _is_allowed_child(self, child_id: int) -> bool:
    if self._allowed_children is None:
        return True
    # ... rest of method
```

Runtime error:
```
TypeError: can't convert NoneType to int
```

### The diagnosis

Dumping the IR revealed the problem:

```bash
mpy-compile examples/lvgl_nav.py --dump-ir text --ir-function _is_allowed_child
```

```
def _is_allowed_child(child_id: MP_INT_T) -> BOOL:
  c_name: lvgl_nav_Nav__is_allowed_child
  max_temp: 0
  body:
    if (self._allowed_children == None):  # <-- Should be "is"!
      return True
    return False
```

The IR showed `==` instead of `is`. The generated C confirmed:

```c
static bool lvgl_nav_Nav__is_allowed_child_native(lvgl_nav_Nav_obj_t *self, mp_int_t child_id) {
    // WRONG: using mp_obj_get_int on both sides
    if ((mp_obj_get_int(self->_allowed_children) == mp_obj_get_int(mp_const_none))) {
        return true;
    }
    // ...
}
```

### The root cause

In `ir_builder.py`, the `_build_method_expr` function had an incomplete operator map:

```python
# Before (buggy):
op_map = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.In: "in",
    ast.NotIn: "not in",
    # MISSING: ast.Is and ast.IsNot!
}
```

The `get()` call with default `"=="` caused `is` to become `==`:

```python
c_op = op_map.get(type(op), "==")  # Defaults to "==" for unknown ops
```

Compare with `_build_compare` for standalone functions, which had the complete map:

```python
op_map = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.In: "in",
    ast.NotIn: "not in",
    ast.Is: "is",        # Present!
    ast.IsNot: "is not", # Present!
}
```

### The fix

Add the missing operators to `_build_method_expr`:

```python
# After (fixed):
op_map = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.In: "in",
    ast.NotIn: "not in",
    ast.Is: "is",
    ast.IsNot: "is not",
}
```

### The result

IR now shows correct operator:

```
if (self._allowed_children is None):
```

Generated C uses pointer comparison:

```c
if ((self->_allowed_children == mp_const_none)) {
    return true;
}
```

No `mp_obj_get_int` calls. Direct pointer comparison.

---

## 3.2 Bug 2: Over-eager unboxing

### The symptom

After fixing Bug 1, a new error appeared during `Nav.pop()`:

```
TypeError: can't convert LvObj to int
```

The LVGL screen object was being converted to int when passed to a method.

### The diagnosis

The generated C for `pop()` showed:

```c
if ((old_screen != mp_const_none)) {
    // WRONG: mp_obj_get_int on an LVGL object!
    (void)lvgl_nav_Nav__safe_delete_native(self, mp_obj_get_int(old_screen));
}
```

But `_safe_delete_native` expects `mp_obj_t`:

```c
static void lvgl_nav_Nav__safe_delete_native(lvgl_nav_Nav_obj_t *self, mp_obj_t screen);
```

The compiler was incorrectly unboxing the `screen` argument.

### The root cause

In `function_emitter.py`, the `_emit_self_method_call` function:

```python
def _emit_self_method_call(self, call: SelfMethodCallIR, native: bool = False):
    args = ["self"]
    for arg in call.args:
        arg_expr, arg_type = self._emit_expr(arg, native)
        if self._should_unbox_self_method_args(call, native):
            # BUG: No target type specified!
            args.append(self._unbox_if_needed(arg_expr, arg_type))
        else:
            args.append(arg_expr)
```

The `_unbox_if_needed` method:

```python
def _unbox_if_needed(self, expr: str, expr_type: str, target_type: str = "mp_int_t") -> str:
    if expr_type == "mp_obj_t" and target_type != "mp_obj_t":
        if target_type == "mp_float_t":
            return f"mp_get_float_checked({expr})"
        else:
            return f"mp_obj_get_int({expr})"  # Default: convert to int
    return expr
```

When called without a `target_type`, it defaults to `"mp_int_t"` and unboxes everything. But `old_screen` has IR type `OBJ` (meaning `mp_obj_t`), which should NOT be unboxed.

### The fix

Pass the argument's expected type from the IR:

```python
def _emit_self_method_call(self, call: SelfMethodCallIR, native: bool = False):
    args = ["self"]
    for arg in call.args:
        arg_expr, arg_type = self._emit_expr(arg, native)
        if self._should_unbox_self_method_args(call, native):
            # FIXED: Use the IR's expected type as target
            target_type = arg.ir_type.to_c_type_str()
            args.append(self._unbox_if_needed(arg_expr, arg_type, target_type))
        else:
            args.append(arg_expr)
```

Now when `arg.ir_type` is `IRType.OBJ`, `target_type` becomes `"mp_obj_t"`, and `_unbox_if_needed` returns the expression unchanged.

### The result

Generated C passes the object directly:

```c
if ((old_screen != mp_const_none)) {
    (void)lvgl_nav_Nav__safe_delete_native(self, old_screen);  // No conversion
}
```

---

# Device Testing

After both fixes, the full navigation test passes on ESP32-C6:

```
@S:nav_smooth
  ScreenManager initialized (smooth transitions + FPS counter)

  === PUSH Phase (slide from right) ===
  Stack grows: Home -> Settings -> Display

  [PUSH] Home          | Stack: Home | FPS: 6
  OK: push_home
  [PUSH] Settings      | Stack: Home > Settings | FPS: 5
  OK: push_settings
  [PUSH] Display       | Stack: Home > Settings > Display | FPS: 5
  OK: push_display

  === POP Phase (slide to right) ===
  Stack shrinks: Display -> Settings -> Home

  [POP]  -> Settings    | Stack: Home > Settings | FPS: 6
  OK: pop_to_settings
  [POP]  -> Home       | Stack: Home | FPS: 5
  OK: pop_to_home
  [REPL] Home          | Stack: Home | FPS: 6
  OK: replace_home
  OK: pop_at_root

  Memory: start=239744, end=239872, diff=-128
  OK: memory_stable

========================================
Smooth Navigation Test Results
========================================
Total:  8
Passed: 8
Failed: 0
========================================
ALL TESTS PASSED
```

The display shows smooth slide animations (5-6 FPS during transitions) with proper screen management.

---

# Closing

## Lessons learned

1. **Keep operator maps synchronized.** When there are parallel code paths (function vs method building), they need identical operator support. The `is`/`is not` operators were present in one path but missing in the other.

2. **Unboxing decisions need target type information.** The default "unbox to int" assumption fails for object-typed parameters. The IR carries the expected type; use it.

3. **Device testing catches what unit tests miss.** Both bugs compiled without errors and passed unit tests (which verify C code generation). Only real device execution revealed the runtime type errors.

## The pattern

Both bugs followed the same pattern:

| Bug | What was missing | Effect |
|-----|------------------|--------|
| Bug 1 | Operator mapping | Wrong comparison semantics |
| Bug 2 | Target type | Wrong unboxing decision |

In both cases, the compiler had the information it needed (the AST operator type, the IR argument type) but wasn't using it in the right place.

## Files changed

- `src/mypyc_micropython/ir_builder.py` - Added `ast.Is` and `ast.IsNot` to method expression builder
- `src/mypyc_micropython/function_emitter.py` - Pass target type to `_unbox_if_needed` in self method calls

Both fixes are small (2 lines and 2 lines) but required tracing through the full compilation pipeline to diagnose.
