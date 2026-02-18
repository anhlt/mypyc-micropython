# Type Coercion in Assignments: When Types Collide

*Fixing a subtle bug where loop variables lost their type identity.*

---

Compiling `result = n` seems trivial — just emit `result = n;` in C, right? Not when `result` is an unboxed `mp_int_t` and `n` is a boxed `mp_obj_t`. This post explores a type coercion bug that caused silent data corruption and how we fixed it.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) — Type systems, boxing/unboxing, and why assignments need type awareness
2. [C Background](#part-2-c-background-for-python-developers) — Type coercion, undefined behavior, and how C handles type mismatches
3. [Implementation](#part-3-implementation) — The bug, the fix, and lessons learned

---

# Part 1: Compiler Theory

## Type Systems in Compilers

Every compiler deals with types. Our compiler has two type systems:

| System | Where | Purpose |
|--------|-------|---------|
| **Python types** | Source code | User annotations (`int`, `list`, `Point`) |
| **C types** | Generated code | Runtime representation (`mp_int_t`, `mp_obj_t`) |

The compiler must **map** Python types to C types and handle conversions between them.

## Boxing and Unboxing

MicroPython uses **boxing** to represent Python values uniformly:

```
Python int (42) --[box]--> mp_obj_t (pointer to object)
                           |
                           v
mp_obj_t (pointer) --[unbox]--> C int (42)
```

**Boxing**: Wrap a raw value in a MicroPython object
**Unboxing**: Extract the raw value from a MicroPython object

```c
// Boxing: int -> mp_obj_t
mp_obj_t boxed = mp_obj_new_int(42);

// Unboxing: mp_obj_t -> int
mp_int_t unboxed = mp_obj_get_int(boxed);
```

## Why Mixed Types Occur

In our IR, variables have C types determined at declaration:

```python
result: int = 0        # result is mp_int_t (unboxed)
for n in items:        # n is mp_obj_t (boxed, always)
    result = n         # Assigning mp_obj_t to mp_int_t!
```

**Key insight**: Loop variables are always boxed (`mp_obj_t`) because iterators return objects. But typed local variables can be unboxed (`mp_int_t`).

## Type Information Flow

When compiling an assignment `x = expr`:

```
+-------------+     +-------------+
| expr's type | --> | What we GET |
+-------------+     +-------------+
       vs
+-------------+     +-------------+
|  x's type   | --> | What we NEED|
+-------------+     +-------------+
```

If these differ, the compiler must insert a **type conversion**.

## The Compilation Pipeline Problem

Our pipeline had a gap:

```
+------------------+    +------------------+    +------------------+
|    IR Builder    | -> |    Emitter       | -> |     C Code       |
|                  |    |                  |    |                  |
| Knows both types |    | Lost target type |    | No conversion    |
+------------------+    +------------------+    +------------------+
        OK                    BUG!                   BUG!
```

Type information wasn't flowing correctly from IR to emission.

---

# Part 2: C Background for Python Developers

## Implicit Type Conversions

C performs implicit conversions between compatible types:

```c
int a = 42;
long b = a;      // OK: int to long (widening)
float c = a;     // OK: int to float (widening)
```

But C also allows dangerous implicit conversions:

```c
void *ptr = 0x12345678;
int value = (int)ptr;    // Compiles! But probably wrong.
```

C doesn't prevent you from mixing pointers and integers.

## Undefined Behavior

When types don't match in unexpected ways, C gives **undefined behavior**:

```c
// BAD: Pointer stored as integer
mp_obj_t obj = mp_obj_new_int(42);  // obj is a pointer
mp_int_t value = obj;                // Treating pointer as integer!
// Value is now some garbage memory address, not 42
```

The compiler doesn't warn. The code runs. The results are wrong.

## Visual: What Goes Wrong

```
Correct path (with unboxing):
  mp_obj_t obj = mp_obj_new_int(42)
        |
        v
  +------------------+
  | Object at 0x8000 |
  | type: int_type   |
  | value: 42        |
  +------------------+
        |
        v [mp_obj_get_int]
  mp_int_t value = 42  [Correct!]


Wrong path (no unboxing):
  mp_obj_t obj = mp_obj_new_int(42)
        |
        v
  +------------------+
  | Object at 0x8000 |
  | type: int_type   |
  | value: 42        |
  +------------------+
        |
        v [direct assignment]
  mp_int_t value = 0x8000  [WRONG! This is the address, not 42]
```

## Boxing/Unboxing Functions

MicroPython provides type-specific conversions:

| Operation | Function | From | To |
|-----------|----------|------|-----|
| Unbox int | `mp_obj_get_int(obj)` | `mp_obj_t` | `mp_int_t` |
| Unbox float | `mp_obj_get_float(obj)` | `mp_obj_t` | `mp_float_t` |
| Unbox bool | `mp_obj_is_true(obj)` | `mp_obj_t` | `bool` |
| Box int | `mp_obj_new_int(val)` | `mp_int_t` | `mp_obj_t` |
| Box float | `mp_obj_new_float(val)` | `mp_float_t` | `mp_obj_t` |
| Box bool | `mp_obj_new_bool(val)` | `bool` | `mp_obj_t` |

Without these, raw C assignment gives garbage.

## Why C Doesn't Catch This

```c
mp_int_t result = n;  // C sees: long = void*
```

C allows this because:
1. Pointers can be cast to integers (for low-level programming)
2. No `-Werror` for pointer-to-int in many configs
3. `mp_obj_t` is typedef'd to `void*`, hiding the pointer nature

The bug compiles silently.

---

# Part 3: Implementation

## The Bug: Real Code

Consider this Python function:

```python
def max_of_args(*nums) -> int:
    result: int = nums[0]
    for n in nums:
        if n > result:
            result = n
    return result
```

### Generated C (Buggy)

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

### What Went Wrong

```
Line: result = n

Expected:
  result (mp_int_t) = mp_obj_get_int(n)  // Unbox first!
  
Actual:
  result (mp_int_t) = n (mp_obj_t)       // No unboxing = garbage!
```

## Root Cause Analysis

The bug had two parts:

### Part 1: IR Builder Overwrote Types

When building IR for `result = n`:

```python
def _build_assign(self, stmt, locals_):
    value_type = self._get_value_ir_type(value)
    c_type = value_type.to_c_type_str()  # Gets "mp_obj_t" from n
    self._var_types[var_name] = c_type   # Overwrites result's type!
```

The target's type was being reset to match the value's type, losing the original declaration.

### Part 2: Emitter Didn't Convert

The emitter blindly copied without checking types:

```python
def _emit_assign(self, stmt, native=False):
    expr, _ = self._emit_expr(stmt.value, native)  # Ignored type!
    lines.append(f"    {stmt.c_target} = {expr};")  # No conversion
```

Even if Part 1 was fixed, the emitter wouldn't insert `mp_obj_get_int()`.

## The Fix

### Fix 1: Preserve Existing Variable Types

For reassignments, keep the original declared type:

```python
def _build_assign(self, stmt, locals_):
    is_new_var = var_name not in locals_
    if is_new_var:
        # New variable: infer type from value
        locals_.append(var_name)
        value_type = self._get_value_ir_type(value)
        c_type = value_type.to_c_type_str()
        self._var_types[var_name] = c_type
    else:
        # Existing variable: keep original type!
        c_type = self._var_types.get(var_name, "mp_obj_t")
```

### Fix 2: Type-Aware Code Emission

Check types and insert conversion when needed:

```python
def _emit_assign(self, stmt, native=False):
    expr, expr_type = self._emit_expr(stmt.value, native)
    
    # Check if types differ
    if stmt.c_type != expr_type:
        expr = self._unbox_if_needed(expr, expr_type, stmt.c_type)
    
    lines.append(f"    {stmt.c_target} = {expr};")
```

### The Unboxing Helper

```python
def _unbox_if_needed(self, expr: str, from_type: str, to_type: str) -> str:
    """Convert expression if types differ."""
    if from_type == "mp_obj_t" and to_type == "mp_int_t":
        return f"mp_obj_get_int({expr})"
    elif from_type == "mp_obj_t" and to_type == "mp_float_t":
        return f"mp_obj_get_float({expr})"
    elif from_type == "mp_obj_t" and to_type == "bool":
        return f"mp_obj_is_true({expr})"
    # ... other conversions
    return expr  # No conversion needed
```

## The Result

### Before (Buggy)

```c
result = n;              // BUG: pointer assigned to integer
return result;           // BUG: integer returned as pointer
```

### After (Fixed)

```c
result = mp_obj_get_int(n);      // Correct: unbox first
return mp_obj_new_int(result);   // Correct: box for return
```

## Visual: The Fix in Action

```
Assignment: result = n (where result: int, n: mp_obj_t)

BEFORE FIX:
  n (mp_obj_t) -----> result (mp_int_t)
                      [Wrong! Pointer as integer]

AFTER FIX:
  n (mp_obj_t) --[mp_obj_get_int]--> result (mp_int_t)
                                     [Correct! Extracted value]
```

## Why This Was Hard to Catch

The bug was insidious:

| Reason | Why It Hid |
|--------|------------|
| **Compiled without warnings** | C allows pointer-to-int |
| **Simple cases worked** | `result = 10` needs no conversion |
| **Silent corruption** | Wrong values, not crashes |
| **Loop-specific** | Only appeared with iteration variables |

## Testing

We added tests specifically for type mismatches:

```python
def test_assign_boxed_to_unboxed(self):
    source = '''
def max_of_args(*nums) -> int:
    result: int = nums[0]
    for n in nums:
        if n > result:
            result = n
    return result
'''
    result = compile_source(source, "test")
    # Verify unboxing in assignment
    assert "mp_obj_get_int" in result
    # Verify boxing in return
    assert "mp_obj_new_int" in result
```

## The Broader Pattern

This fix applies to any type mismatch:

```python
result: int = some_dict[key]     # dict subscript returns mp_obj_t
result: int = some_func()        # function call returns mp_obj_t
result: int = some_list.pop()    # method call returns mp_obj_t
```

All now correctly insert unboxing conversions.

## Lessons Learned

### 1. Type Information Flows in Two Directions

```
Expression type --> What you HAVE
Variable type  --> What you NEED
                    ^
                    Must bridge the gap!
```

### 2. Don't Overwrite Type Declarations

A variable's type is set at declaration. Reassignments must respect that type.

### 3. Test Type Mismatches Explicitly

Homogeneous tests pass. Heterogeneous tests catch conversion bugs.

### 4. Silent Bugs Are the Worst

Crashes are obvious. Wrong values are silent. Add assertions.

---

## Conclusion

Type coercion bugs occur when:
1. Variables have different C representations (boxed vs unboxed)
2. The compiler loses track of declared types
3. The emitter doesn't insert conversions

The fix:
1. **Preserve declared types** in the IR builder
2. **Check type compatibility** in the emitter
3. **Insert conversions** when types differ

Type information must flow through the entire pipeline — from annotation parsing to C emission.

---

*Type coercion is handled in `ir_builder.py` (type tracking) and `function_emitter.py` (conversion insertion). The conversion functions are documented in `ir.py`.*
