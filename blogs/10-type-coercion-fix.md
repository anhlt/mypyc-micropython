# Type Coercion in Assignments: When Types Collide

*Fixing a subtle bug where loop variables lost their type identity.*

---

Compiling `result = n` seems trivial — just emit `result = n;` in C, right? Not when `result` is an unboxed `mp_int_t` and `n` is a boxed `mp_obj_t`. This post explores a type coercion bug that caused silent data corruption and how we fixed it.

## The Bug

Consider this innocent Python code:

```python
def max_of_args(*nums) -> int:
    result: int = nums[0]
    for n in nums:
        if n > result:
            result = n
    return result
```

The generated C had two problems:

```c
static mp_obj_t test_max_of_args(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_nums = mp_obj_new_tuple(...);
    
    mp_int_t result = mp_obj_get_int(mp_obj_subscr(...));  // OK: unboxed
    mp_obj_t n;
    while ((n = mp_iternext(...)) != MP_OBJ_STOP_ITERATION) {
        if ((mp_obj_get_int(n) > result)) {
            result = n;      // BUG: assigning mp_obj_t to mp_int_t!
        }
    }
    return result;           // BUG: returning mp_int_t as mp_obj_t!
}
```

The assignment `result = n` was copying a pointer (`mp_obj_t`) into an integer (`mp_int_t`). The return was passing an integer where a pointer was expected. Both are undefined behavior in C.

## Root Cause Analysis

The bug had two parts:

**Part 1: IR Builder (`_build_assign`)**

When building IR for `result = n`, we determined the target's C type from the *value's* type:

```python
def _build_assign(self, stmt, locals_):
    value_type = self._get_value_ir_type(value)
    c_type = value_type.to_c_type_str()  # "mp_obj_t" from n
    self._var_types[var_name] = c_type   # Overwrote result's type!
```

This meant `result`'s type changed from `mp_int_t` to `mp_obj_t` after the assignment, losing the original declaration.

**Part 2: Code Emitter (`_emit_assign`)**

The emitter blindly copied the expression without type conversion:

```python
def _emit_assign(self, stmt, native=False):
    expr, _ = self._emit_expr(stmt.value, native)  # Discarded type info!
    lines.append(f"    {stmt.c_target} = {expr};")  # No conversion
```

Even if we fixed Part 1, the emitter wouldn't insert the necessary `mp_obj_get_int()` call.

## The Fix

**Fix 1: Preserve existing variable types**

For reassignments, use the previously declared type instead of the value's type:

```python
def _build_assign(self, stmt, locals_):
    is_new_var = var_name not in locals_
    if is_new_var:
        locals_.append(var_name)
        value_type = self._get_value_ir_type(value)
        c_type = value_type.to_c_type_str()
        self._var_types[var_name] = c_type
    else:
        c_type = self._var_types.get(var_name, "mp_obj_t")  # Keep original!
```

**Fix 2: Type-aware code emission**

Check if types differ and insert conversion:

```python
def _emit_assign(self, stmt, native=False):
    expr, expr_type = self._emit_expr(stmt.value, native)
    
    if stmt.c_type != expr_type:
        expr = self._unbox_if_needed(expr, expr_type, stmt.c_type)
    
    lines.append(f"    {stmt.c_target} = {expr};")
```

## The Result

Now `result = n` generates correct code:

```c
// Before (broken)
result = n;

// After (fixed)
result = mp_obj_get_int(n);
```

And the return properly boxes:

```c
// Before (broken)
return result;

// After (fixed)
return mp_obj_new_int(result);
```

## Why This Was Hard to Catch

The bug was insidious because:

1. **It compiled without warnings** — C happily converts between `void*` and integers
2. **Simple cases worked** — `result = 10` emits `result = 10;` (both are integers)
3. **The corruption was silent** — wrong values, not crashes
4. **It only appeared in loops** — iteration variables are always boxed

## Lessons Learned

**Type information flows in two directions.** When compiling `x = expr`:
- The expression's type tells you what you *have*
- The variable's type tells you what you *need*
- The emitter must bridge the gap

**Don't overwrite type declarations.** A variable's type is set at declaration (`x: int = 0`). Subsequent assignments must respect that type, not override it.

**Test with type mismatches.** Our existing tests used homogeneous types. We needed tests where loop variables (boxed) are assigned to typed variables (unboxed).

## The Broader Pattern

This fix applies beyond loop variables. Any expression returning `mp_obj_t` assigned to a typed variable needs unboxing:

```python
result: int = some_dict[key]  # dict subscript returns mp_obj_t
result: int = some_func()      # function call returns mp_obj_t
result: int = some_list.pop()  # method call returns mp_obj_t
```

The fix handles all these cases uniformly by checking `stmt.c_type != expr_type` and converting as needed.

---

*Type coercion bugs are subtle because they exploit C's permissive type system. The fix: track declared types carefully and convert explicitly at assignment boundaries.*
