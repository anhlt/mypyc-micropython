# Exception Handling: Compiling try/except to MicroPython's NLR

*How we implemented Python's exception handling using MicroPython's Non-Local Return mechanism.*

---

When you write `try: return a // b except ZeroDivisionError: return 0`, Python's exception handling feels magical. Under the hood, it requires saving execution state, detecting errors, and jumping to the right handler. This post explores how we compiled Python's try/except/finally to C using MicroPython's NLR (Non-Local Return) mechanism.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) - How exception handling works in compilers
2. [C Background](#part-2-c-background-for-python-developers) - setjmp/longjmp and MicroPython's NLR
3. [Implementation](#part-3-implementation) - Building try/except support

---

# Part 1: Compiler Theory

## The Exception Handling Problem

Exception handling breaks normal control flow. When an exception is raised, execution must:

1. Stop the current operation immediately
2. Find an appropriate handler (possibly many stack frames up)
3. Transfer control to that handler
4. Optionally run cleanup code (finally blocks)

This is fundamentally different from `if/else` or `return` because exceptions can propagate through multiple function calls:

```python
def inner():
    raise ValueError("oops")

def middle():
    inner()  # Exception propagates through here

def outer():
    try:
        middle()
    except ValueError:
        print("caught!")  # Handler is here
```

## Two Approaches to Exception Handling

### Approach 1: Return Code Checking

Every function returns a status code. Callers must check it:

```c
int result;
int status = divide(a, b, &result);
if (status == ERROR_DIVISION_BY_ZERO) {
    // Handle error
}
```

**Problems:**
- Every call site needs error checking (verbose, easy to forget)
- Propagating errors requires manual forwarding
- Performance cost even when no exceptions occur

### Approach 2: Non-Local Jump (setjmp/longjmp)

Save execution state at the try block. On error, jump directly back:

```c
jmp_buf checkpoint;
if (setjmp(checkpoint) == 0) {
    // Try block - setjmp returns 0 first time
    risky_operation();
} else {
    // Exception handler - setjmp returns non-zero after longjmp
    handle_error();
}
```

**Advantages:**
- Zero cost when no exceptions occur
- Automatic stack unwinding
- Clean separation of normal and error paths

MicroPython uses the second approach with its NLR API.

## Stack Unwinding

When an exception occurs, the runtime must "unwind" the call stack:

```
+------------------+
| outer() frame    |  <- Has try/except, will catch
+------------------+
| middle() frame   |  <- No handler, will be skipped
+------------------+
| inner() frame    |  <- Exception raised here
+------------------+
```

The unwinding process:
1. Exception raised in `inner()`
2. Check `inner()` for handlers - none found
3. Pop `inner()` frame, check `middle()` - none found
4. Pop `middle()` frame, check `outer()` - handler found!
5. Transfer control to handler in `outer()`

## Nested Exception Handlers

Exception handlers can nest, and each level needs its own checkpoint:

```python
try:                    # Outer checkpoint
    try:                # Inner checkpoint
        return a // b
    except ZeroDivisionError:
        return b // c   # Can also raise!
except ZeroDivisionError:
    return -1           # Catches exceptions from inner handler
```

The compiler must track which checkpoint is "active" at each point.

---

# Part 2: C Background for Python Developers

## setjmp and longjmp

C provides `setjmp()` and `longjmp()` for non-local jumps:

```c
#include <setjmp.h>

jmp_buf buf;

void risky_function() {
    // Something goes wrong
    longjmp(buf, 1);  // Jump back to setjmp, return value 1
}

int main() {
    if (setjmp(buf) == 0) {
        // First time through (normal path)
        risky_function();
        printf("This never prints\n");
    } else {
        // After longjmp (error path)
        printf("Exception caught!\n");
    }
}
```

How it works:
1. `setjmp(buf)` saves CPU registers (stack pointer, program counter) into `buf`
2. First call returns 0, execution continues normally
3. `longjmp(buf, val)` restores registers from `buf`
4. This makes `setjmp()` "return again" with value `val`

## MicroPython's NLR API

MicroPython wraps setjmp/longjmp in its NLR (Non-Local Return) API:

```c
nlr_buf_t nlr;
if (nlr_push(&nlr) == 0) {
    // Try block
    // If exception occurs, nlr_jump() is called internally
    nlr_pop();
} else {
    // Exception handler
    mp_obj_t exception = MP_OBJ_FROM_PTR(nlr.ret_val);
    // Handle or re-raise
}
```

Key functions:

| Function | Purpose |
|----------|---------|
| `nlr_push(&nlr)` | Set up exception checkpoint, returns 0 first time |
| `nlr_pop()` | Remove checkpoint (must call before leaving try block normally) |
| `nlr_jump(val)` | Jump to nearest checkpoint, passing exception object |

The `nlr_buf_t` structure stores:
- Saved registers for the jump
- `ret_val` - the exception object (set by `nlr_jump`)

## Exception Type Checking

MicroPython provides functions to check exception types:

```c
mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);

// Check if exception is a specific type or subclass
if (mp_obj_is_subclass_fast(
        MP_OBJ_FROM_PTR(mp_obj_get_type(exc)),
        MP_OBJ_FROM_PTR(&mp_type_ZeroDivisionError))) {
    // Handle ZeroDivisionError
}
```

## Raising Exceptions

To raise an exception:

```c
// With message
mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("must be positive"));

// Without message
mp_raise_msg(&mp_type_ZeroDivisionError, NULL);

// These internally call nlr_jump()
```

## The Return-Inside-Try Problem

A subtle issue: what if the try block returns?

```python
def safe_divide(a: int, b: int) -> int:
    try:
        return a // b  # Must pop nlr BEFORE returning!
    except ZeroDivisionError:
        return 0
```

Wrong C code:
```c
if (nlr_push(&nlr) == 0) {
    return mp_obj_new_int(a / b);  // BUG: nlr not popped!
    nlr_pop();  // Never reached
}
```

Correct C code:
```c
if (nlr_push(&nlr) == 0) {
    mp_obj_t result = mp_obj_new_int(a / b);  // Evaluate first
    nlr_pop();                                  // Pop checkpoint
    return result;                              // Then return
}
```

## Native Division Doesn't Raise Exceptions

Another gotcha: C's native division by zero is undefined behavior, not an exception:

```c
int a = 10;
int b = 0;
int result = a / b;  // Undefined behavior! Might crash, might return garbage
```

For floor division inside try blocks, we need a checked version:

```c
static inline mp_int_t mp_int_floor_divide_checked(mp_int_t num, mp_int_t denom) {
    if (denom == 0) {
        mp_raise_msg(&mp_type_ZeroDivisionError, MP_ERROR_TEXT("division by zero"));
    }
    // Handle Python's floor division semantics for negative numbers
    if (num >= 0) {
        if (denom < 0) {
            num += -denom - 1;
        }
    } else {
        if (denom >= 0) {
            num += -denom + 1;
        }
    }
    return num / denom;
}
```

---

# Part 3: Implementation

## New IR Nodes

We added three new IR node types:

```python
@dataclass
class ExceptHandlerIR:
    """Single except clause."""
    exc_type: str | None      # Exception type name, None for bare except
    exc_var: str | None       # Variable name for 'as e'
    c_exc_var: str | None     # C variable name
    body: list[StmtIR]

@dataclass
class TryIR(StmtIR):
    """Try/except/else/finally statement."""
    body: list[StmtIR]
    handlers: list[ExceptHandlerIR]
    orelse: list[StmtIR]      # else block
    finalbody: list[StmtIR]   # finally block

@dataclass
class RaiseIR(StmtIR):
    """Raise statement."""
    exc_type: str | None
    exc_msg: str | None
```

## IR Building

The IR builder transforms Python AST to our IR:

```python
def _build_try(self, node: ast.Try, locals_: list[str]) -> TryIR:
    body = [self._build_stmt(s, locals_) for s in node.body]
    
    handlers = []
    for handler in node.handlers:
        exc_type = handler.type.id if handler.type else None
        exc_var = handler.name
        c_exc_var = exc_var  # Use same name in C
        
        handler_body = [self._build_stmt(s, locals_) for s in handler.body]
        handlers.append(ExceptHandlerIR(exc_type, exc_var, c_exc_var, handler_body))
    
    orelse = [self._build_stmt(s, locals_) for s in node.orelse]
    finalbody = [self._build_stmt(s, locals_) for s in node.finalbody]
    
    return TryIR(body, handlers, orelse, finalbody)
```

## Code Emission: Basic try/except

For a simple try/except:

```python
def safe_divide(a: int, b: int) -> int:
    try:
        return a // b
    except ZeroDivisionError:
        return 0
```

Generated C:

```c
static mp_obj_t exception_handling_safe_divide(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    nlr_buf_t _tmp1;
    if (nlr_push(&_tmp1) == 0) {
        mp_obj_t _tmp2 = mp_obj_new_int(mp_int_floor_divide_checked(a, b));
        nlr_pop();
        return _tmp2;
    } else {
        mp_obj_t _tmp3 = MP_OBJ_FROM_PTR(_tmp1.ret_val);
        if (mp_obj_is_subclass_fast(
                MP_OBJ_FROM_PTR(mp_obj_get_type(_tmp3)),
                MP_OBJ_FROM_PTR(&mp_type_ZeroDivisionError))) {
            return mp_obj_new_int(0);
        } else {
            nlr_jump(_tmp1.ret_val);  // Re-raise unhandled exceptions
        }
    }
    return mp_const_none;
}
```

Key points:
1. `nlr_push()` sets up the checkpoint
2. Floor division uses `mp_int_floor_divide_checked()` to properly raise `ZeroDivisionError`
3. Return evaluates to temp, pops nlr, then returns
4. Handler checks exception type with `mp_obj_is_subclass_fast()`
5. Unhandled exceptions re-raised with `nlr_jump()`

## Code Emission: try/finally

The finally block must run whether or not an exception occurred:

```python
def with_cleanup(value: int) -> int:
    result: int = 0
    try:
        result = value * 2
    finally:
        result = result + 1
    return result
```

Generated C:

```c
static mp_obj_t exception_handling_with_cleanup(mp_obj_t value_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t result = 0;
    
    bool _tmp2 = false;  // Track if exception occurred
    nlr_buf_t _tmp1;
    if (nlr_push(&_tmp1) == 0) {
        result = (value * 2);
        nlr_pop();
    } else {
        _tmp2 = true;  // Remember we caught an exception
    }
    
    // Finally block runs unconditionally
    result = (result + 1);
    
    // Re-raise if exception was caught
    if (_tmp2) {
        nlr_jump(_tmp1.ret_val);
    }
    return mp_obj_new_int(result);
}
```

## Code Emission: Multiple Handlers

Multiple except clauses become a chain of if/else-if:

```python
def multi_catch(a: int, b: int) -> int:
    try:
        if b == 0:
            raise ZeroDivisionError
        if a < 0:
            raise ValueError
        return a // b
    except ZeroDivisionError:
        return -1
    except ValueError:
        return -2
```

Generated C (handler section):

```c
} else {
    mp_obj_t _tmp3 = MP_OBJ_FROM_PTR(_tmp1.ret_val);
    if (mp_obj_is_subclass_fast(..., &mp_type_ZeroDivisionError)) {
        return mp_obj_new_int(-1);
    } else if (mp_obj_is_subclass_fast(..., &mp_type_ValueError)) {
        return mp_obj_new_int(-2);
    } else {
        nlr_jump(_tmp1.ret_val);  // Re-raise
    }
}
```

## Nested Try Blocks

Each nested try block needs its own nlr_buf:

```python
def nested_try(a: int, b: int, c: int) -> int:
    try:
        try:
            return a // b
        except ZeroDivisionError:
            return b // c  # Can also raise!
    except ZeroDivisionError:
        return -1
```

Generated C:

```c
nlr_buf_t _tmp1;  // Outer
if (nlr_push(&_tmp1) == 0) {
    nlr_buf_t _tmp2;  // Inner
    if (nlr_push(&_tmp2) == 0) {
        mp_obj_t _tmp3 = mp_obj_new_int(mp_int_floor_divide_checked(a, b));
        nlr_pop();
        return _tmp3;
    } else {
        // Inner handler
        if (mp_obj_is_subclass_fast(..., &mp_type_ZeroDivisionError)) {
            mp_obj_t _tmp5 = mp_obj_new_int(mp_int_floor_divide_checked(b, c));
            nlr_pop();  // Pop OUTER nlr before returning
            return _tmp5;
        } else {
            nlr_jump(_tmp2.ret_val);
        }
    }
    nlr_pop();
} else {
    // Outer handler catches exceptions from inner handler
    if (mp_obj_is_subclass_fast(..., &mp_type_ZeroDivisionError)) {
        return mp_obj_new_int(-1);
    } else {
        nlr_jump(_tmp1.ret_val);
    }
}
```

## Tracking NLR Stack Depth

The emitter tracks active nlr buffers with a stack:

```python
class FunctionEmitter:
    def __init__(self, ...):
        self._nlr_stack: list[str] = []  # Stack of nlr_buf variable names
    
    def _emit_try(self, stmt: TryIR, native: bool) -> list[str]:
        nlr_buf = self._fresh_temp()
        
        # Push onto stack while emitting try body
        self._nlr_stack.append(nlr_buf)
        for s in stmt.body:
            lines.extend(self._emit_statement(s, native))
        self._nlr_stack.pop()
```

This allows `_emit_binop` to detect when floor division is inside a try block:

```python
def _emit_binop(self, op: BinOpIR, native: bool) -> tuple[str, str]:
    # Use checked division inside try blocks
    if self._nlr_stack and op.op in ("//", "%") and target_type == "mp_int_t":
        self._mark_uses_checked_div()
        if op.op == "//":
            return f"mp_int_floor_divide_checked({left}, {right})", target_type
```

## Distinguishing Floor Division from True Division

A subtle bug: both `//` and `/` were mapped to C's `/` operator in the IR, making them indistinguishable. The fix preserves `//` as the IR operator:

```python
# In ir_builder.py
op_map = {
    ast.Div: "/",
    ast.FloorDiv: "//",  # Keep as // to distinguish from true division
}
```

The emitter then converts `//` to `/` for regular emission, or to `mp_int_floor_divide_checked()` inside try blocks.

## Testing

We added comprehensive tests covering:

- Basic try/except
- Multiple handlers
- Bare except (catches all)
- try/else
- try/finally
- try/except/finally
- Nested try blocks
- Return inside try
- Exception binding (`except E as e`)
- Raise statements

All 243 device tests pass, including edge cases like `nested_try(10, 0, 0)` where both inner and outer handlers catch `ZeroDivisionError`.

## Summary

Exception handling required:

1. **New IR nodes**: `TryIR`, `RaiseIR`, `ExceptHandlerIR`
2. **NLR-based code generation**: Using MicroPython's `nlr_push`/`nlr_pop`/`nlr_jump`
3. **Return-inside-try handling**: Evaluate to temp, pop, then return
4. **Checked division helpers**: `mp_int_floor_divide_checked()` for proper `ZeroDivisionError`
5. **NLR stack tracking**: Know when we're inside a try block

The implementation correctly handles Python's exception semantics while generating efficient C code that integrates with MicroPython's runtime.
