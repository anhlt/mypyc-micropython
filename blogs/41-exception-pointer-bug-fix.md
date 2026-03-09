# Exception Pointer Bug Fix: Understanding nlr_buf.ret_val

*How a subtle pointer casting bug caused device crashes, and the MicroPython internals that explain why.*

---

When exception handling code works perfectly in unit tests but crashes on real hardware with "Load access fault" at tiny addresses like `0x0000000e`, you know something fundamental is wrong. This post documents a critical bug in our exception handling code generation and the MicroPython internals that made it so hard to find.

## Table of Contents

1. [The Bug](#the-bug) - What went wrong
2. [MicroPython's NLR Mechanism](#micropythons-nlr-mechanism) - How exceptions really work
3. [The Fix](#the-fix) - Correct pointer handling
4. [Why Unit Tests Passed](#why-unit-tests-passed) - The testing gap

---

# The Bug

## Symptoms

Our compiled code crashed on ESP32-P4 when executing try/except blocks in loops:

```
Guru Meditation Error: Core 1 panic'ed (Load access fault)
MTVAL: 0x0000000e
```

The faulting address `0x0000000e` is suspiciously small - it looks like an offset or small integer being dereferenced as a pointer.

## The Buggy Code

Our exception handling emitter generated this C code:

```c
nlr_buf_t nlr_buf;
if (nlr_push(&nlr_buf) == 0) {
    // try block
    risky_operation();
    nlr_pop();
} else {
    // except block - BUG HERE!
    mp_obj_t exc = MP_OBJ_FROM_PTR(nlr_buf.ret_val);
    
    if (mp_obj_is_subclass_fast(
            MP_OBJ_FROM_PTR(mp_obj_get_type(exc)),
            MP_OBJ_FROM_PTR(&mp_type_KeyError))) {
        // handle KeyError
    }
}
```

The bug is in this line:

```c
mp_obj_t exc = MP_OBJ_FROM_PTR(nlr_buf.ret_val);
```

## Why It's Wrong

`nlr_buf.ret_val` is a `void *` that **already points directly to the exception object**. Using `MP_OBJ_FROM_PTR()` on it corrupts the pointer because:

1. `MP_OBJ_FROM_PTR(ptr)` is meant to convert a **raw C pointer** (obtained via `MP_OBJ_TO_PTR()`) back to an `mp_obj_t`
2. But `nlr_buf.ret_val` is not a raw pointer - it's already the exception object pointer
3. The macro applies bit manipulation that corrupts valid pointers

---

# MicroPython's NLR Mechanism

## What is NLR?

NLR (Non-Local Return) is MicroPython's exception mechanism, similar to setjmp/longjmp but optimized for the interpreter. When an exception is raised:

1. `nlr_push()` saves the current execution state (registers, stack pointer)
2. Code executes normally until an exception occurs
3. `nlr_jump()` restores the saved state and returns to the `nlr_push()` call site
4. The second return from `nlr_push()` indicates an exception occurred

## The nlr_buf Structure

```c
typedef struct _nlr_buf_t {
    // Platform-specific saved registers
    void *ret_val;  // Exception object pointer
    // ... more saved state
} nlr_buf_t;
```

The key field is `ret_val`:
- Set by `nlr_jump(val)` when throwing an exception
- Contains a **direct pointer** to the exception object
- The object is an `mp_obj_base_t *` which can be cast to access the type

## How MicroPython Uses It Internally

Looking at MicroPython's own code in `py/vm.c`:

```c
if (nlr_push(&nlr) == 0) {
    // normal execution
} else {
    // exception handling
    mp_obj_base_t *exc = (mp_obj_base_t *)nlr.ret_val;
    // Access type via: exc->type
}
```

MicroPython casts `ret_val` directly to `mp_obj_base_t *` - no `MP_OBJ_FROM_PTR()` involved!

## Understanding mp_obj_t

In MicroPython, `mp_obj_t` is a tagged pointer:

```c
typedef void *mp_obj_t;
```

But not all `void *` pointers are valid `mp_obj_t` values. MicroPython uses the low bits for tagging:
- Small integers are encoded directly in the pointer value
- Object pointers have specific alignment requirements

The `MP_OBJ_FROM_PTR()` and `MP_OBJ_TO_PTR()` macros handle this tagging:

```c
#define MP_OBJ_FROM_PTR(p) ((mp_obj_t)(p))
#define MP_OBJ_TO_PTR(o) ((void *)(o))
```

On most platforms these are identity operations, but the **semantics matter** - they indicate the programmer's intent about pointer ownership and validity.

---

# The Fix

## Correct Exception Handling Code

```c
nlr_buf_t nlr_buf;
if (nlr_push(&nlr_buf) == 0) {
    // try block
    risky_operation();
    nlr_pop();
} else {
    // except block - FIXED
    mp_obj_base_t *exc = (mp_obj_base_t *)nlr_buf.ret_val;
    
    if (mp_obj_is_subclass_fast(
            MP_OBJ_FROM_PTR(exc->type),  // Access type field directly
            MP_OBJ_FROM_PTR(&mp_type_KeyError))) {
        // handle KeyError
    }
}
```

Key changes:

1. **Cast directly**: `(mp_obj_base_t *)nlr_buf.ret_val` instead of `MP_OBJ_FROM_PTR()`
2. **Access type via field**: `exc->type` instead of `mp_obj_get_type(exc)`
3. **Convert type to mp_obj_t**: `MP_OBJ_FROM_PTR(exc->type)` for the subclass check

## Binding Exception to Variable

When the user writes `except KeyError as e:`, we need to provide `e` as an `mp_obj_t`:

```c
// For: except KeyError as e:
mp_obj_base_t *exc = (mp_obj_base_t *)nlr_buf.ret_val;
if (mp_obj_is_subclass_fast(...)) {
    mp_obj_t e = MP_OBJ_FROM_PTR(exc);  // Convert back for user access
    // user code can use 'e'
}
```

Here `MP_OBJ_FROM_PTR(exc)` is correct because `exc` is a valid object pointer that we're converting to the `mp_obj_t` representation for user code.

## The Emitter Changes

In `function_emitter.py` and `class_emitter.py`:

```python
# OLD (buggy)
lines.append(f"mp_obj_t {exc_var} = MP_OBJ_FROM_PTR({nlr_buf}.ret_val);")
cond = f"mp_obj_is_subclass_fast(MP_OBJ_FROM_PTR(mp_obj_get_type({exc_var})), ...)"

# NEW (fixed)
lines.append(f"mp_obj_base_t *{exc_var} = (mp_obj_base_t *){nlr_buf}.ret_val;")
cond = f"mp_obj_is_subclass_fast(MP_OBJ_FROM_PTR({exc_var}->type), ...)"

# For exception binding (except E as e:)
lines.append(f"mp_obj_t {target} = MP_OBJ_FROM_PTR({exc_var});")
```

---

# Why Unit Tests Passed

## The Testing Gap

Our C runtime tests compile generated code with gcc on the host machine and run it locally. The tests passed because:

1. **Memory layout differences**: x86-64 has different pointer sizes and alignment than RISC-V
2. **Pointer tagging behavior**: The corruption might produce valid-looking pointers on x86-64
3. **Exception object placement**: Host malloc might place objects at addresses that survive the corruption

## The Real Test

The bug only manifested on actual ESP32-P4 hardware because:

1. **32-bit RISC-V architecture**: Different pointer arithmetic
2. **MicroPython's GC heap**: Objects placed at specific addresses
3. **Real exception flow**: The full NLR mechanism exercised

This is why device testing is mandatory for compiler changes - unit tests cannot catch all pointer-related bugs.

## Test Coverage Improvement

We added specific tests to catch this pattern:

```python
def test_exception_handling_in_loop(compile_and_run):
    """Regression test for nlr.ret_val pointer handling."""
    source = '''
def process_items(items: list) -> int:
    count: int = 0
    i: int = 0
    while i < len(items):
        item = items[i]
        try:
            if item < 0:
                raise ValueError("negative")
            count += item
        except ValueError:
            pass  # Skip negative values
        i += 1
    return count
'''
    # Test exercises exception handling in a loop
    test_main = '''
    int items[] = {1, -2, 3, -4, 5};
    // ... test code
    '''
    stdout = compile_and_run(source, "test", test_main)
    assert "9" in stdout  # 1 + 3 + 5
```

---

## Summary

| Aspect | Wrong | Correct |
|--------|-------|---------|
| Get exception | `MP_OBJ_FROM_PTR(nlr.ret_val)` | `(mp_obj_base_t *)nlr.ret_val` |
| Get type | `mp_obj_get_type(exc)` | `exc->type` |
| Type check | `MP_OBJ_FROM_PTR(mp_obj_get_type(...))` | `MP_OBJ_FROM_PTR(exc->type)` |
| Bind to var | Already wrong | `MP_OBJ_FROM_PTR(exc)` |

The key insight: `nlr_buf.ret_val` is a raw `void *` pointing directly to the exception object. Cast it to `mp_obj_base_t *` to access fields, don't try to convert it with `MP_OBJ_FROM_PTR()`.

## Files Modified

- `src/mypyc_micropython/function_emitter.py` - Fixed exception handling emission
- `src/mypyc_micropython/class_emitter.py` - Same fix for class methods
- `tests/test_emitters.py` - Added regression tests

## Lessons Learned

1. **Match the runtime's patterns**: When in doubt, look at how MicroPython itself handles the same situation
2. **Device testing is essential**: Pointer bugs often hide on different architectures
3. **Small addresses in crashes**: Values like `0x0000000e` strongly suggest pointer corruption, not null pointer dereference
