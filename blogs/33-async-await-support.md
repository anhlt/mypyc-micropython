# 33. Async/Await Support: Coroutines and the Yield-From Pattern

This post documents the implementation of `async`/`await` support in mypyc-micropython. Async functions compile to coroutine objects that work with MicroPython's `asyncio` event loop, enabling compiled native code to integrate seamlessly with cooperative multitasking.

The core insight: an async function is essentially a generator with extra methods (`__await__`, `send`, `throw`, `close`) and special handling for `await` expressions using yield-from semantics.

## Table of Contents

- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [Part 2: C Background](#part-2-c-background)
- [Part 3: Implementation](#part-3-implementation)
- [The Bug and Fix](#the-bug-and-fix)

## Part 1: Compiler Theory

### What async/await really means

At the language level, `async def` marks a function as a coroutine factory. Calling it returns a coroutine object that can be driven by an event loop. The `await` keyword suspends execution until the awaited object completes.

```python
async def delayed_double(n: int) -> int:
    await asyncio.sleep(0)  # Yield control to event loop
    return n * 2
```

Under the hood, this is remarkably similar to generators:

| Generator | Coroutine |
|-----------|-----------|
| `yield value` suspends | `await awaitable` suspends |
| `for x in gen()` drives | `asyncio.run(coro())` drives |
| Returns via `StopIteration` | Returns via `StopIteration` |
| `send(value)` resumes | `send(value)` resumes |

The key difference: `await` doesn't just suspend and return a value. It delegates to another awaitable, driving it to completion before continuing. This is the **yield-from pattern**.

### Yield-from: the heart of await

Consider this Python code:

```python
async def countdown_with_delay(start: int) -> int:
    count = start
    while count > 0:
        await asyncio.sleep(0)  # Each await is a suspension point
        count = count - 1
    return count  # Returns 0 when done
```

The `await asyncio.sleep(0)` doesn't just return the sleep object to the event loop. It:

1. Creates the awaitable (the sleep coroutine)
2. Calls the awaitable's iterator repeatedly until it completes
3. Captures the awaitable's return value
4. Continues to the next statement

This is exactly what `yield from` does in generators. In fact, the PEP that introduced `await` (PEP 492) specifies that `await expr` is semantically equivalent to `yield from expr.__await__()`.

### State machine transformation

Like generators, async functions compile to state machines. But await points are more complex than yields:

**Python:**
```python
async def example():
    x = await some_async_call()  # Suspension point
    return x + 1
```

**State machine logic:**
```
state_0: (initial)
    create awaitable from some_async_call()
    store in _await_iter
    goto await_loop

await_loop:
    result = iterate(_await_iter)
    if not done:
        save state, return result (yield to event loop)
    else:
        x = awaitable's return value
        goto state_after_await

state_after_await:
    return x + 1
```

The crucial insight: we need to iterate the awaitable multiple times (it might yield several values before completing), staying at the same state until it finishes.

### IR representation

We introduce two new IR nodes:

**AwaitIR** - simple await on an expression:
```python
@dataclass
class AwaitIR(StmtIR):
    value: ValueIR        # The awaitable expression
    result: str | None    # Variable to store result
    state_id: int         # Resumption point
```

**AwaitModuleCallIR** - await on a module function call (common pattern):
```python
@dataclass
class AwaitModuleCallIR(StmtIR):
    module_name: str      # e.g., "asyncio"
    func_name: str        # e.g., "sleep"
    args: list[ValueIR]   # Function arguments
    result: str | None    # Variable to store result
    state_id: int         # Resumption point
```

The specialized `AwaitModuleCallIR` handles the ubiquitous `await module.func(args)` pattern efficiently, importing the module at runtime and calling the function in a single operation.

## Part 2: C Background

### Coroutine object structure

A compiled coroutine needs more fields than a generator:

```c
typedef struct _async_demo_delayed_double_coro_t {
    mp_obj_base_t base;     // MicroPython object header
    uint16_t state;          // Current state in state machine
    mp_obj_t send_value;     // Value passed via send()
    mp_obj_t _await_iter;    // Active awaitable being iterated
    mp_int_t n;              // Function parameter
} async_demo_delayed_double_coro_t;
```

The `_await_iter` field is critical: it stores the awaitable we're currently driving via yield-from. When `_await_iter` is `mp_const_none`, we haven't started the await yet.

### The mp_iternext pattern

MicroPython's iteration protocol uses `mp_iternext()`:

```c
mp_obj_t mp_iternext(mp_obj_t o);
```

Returns:
- A yielded value if the iterator has more
- `MP_OBJ_STOP_ITERATION` when exhausted

When an iterator completes, its return value (if any) is stored in `MP_STATE_THREAD(stop_iteration_arg)`. This is how `return` values propagate from sub-coroutines.

### The awaitable protocol

For an object to be awaitable, it must:
1. Have an `__await__` method that returns an iterator
2. That iterator yields values to suspend execution
3. When exhausted, the iterator's return value becomes the await result

In MicroPython, coroutines implement this by having `__await__` return `self` - the coroutine is its own iterator.

## Part 3: Implementation

### AsyncEmitter: extending GeneratorEmitter

Since coroutines are structurally similar to generators, `AsyncEmitter` extends `GeneratorEmitter`:

```python
class AsyncEmitter(GeneratorEmitter):
    """Emit async functions as MicroPython coroutine objects.
    
    Extends GeneratorEmitter with:
    - __await__ method (returns self)
    - send() method with value parameter
    - Handling for AwaitIR and AwaitModuleCallIR nodes
    """
```

### Coroutine type definition

The generated coroutine type includes all required methods:

```c
static const mp_rom_map_elem_t delayed_double_coro_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_send), MP_ROM_PTR(&delayed_double_coro_send_obj) },
    { MP_ROM_QSTR(MP_QSTR___await__), MP_ROM_PTR(&delayed_double_coro_await_obj) },
    { MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&delayed_double_coro_close_obj) },
    { MP_ROM_QSTR(MP_QSTR_throw), MP_ROM_PTR(&delayed_double_coro_throw_obj) },
};

MP_DEFINE_CONST_OBJ_TYPE(
    delayed_double_coro_type,
    MP_QSTR_coroutine,
    MP_TYPE_FLAG_ITER_IS_ITERNEXT,
    iter, delayed_double_coro_iternext,
    locals_dict, &delayed_double_coro_locals_dict
);
```

### The __await__ method

Trivially returns self, making the coroutine awaitable:

```c
static mp_obj_t delayed_double_coro_await(mp_obj_t self_in) {
    return self_in;  // Coroutine is its own iterator
}
```

### The send method

Stores the sent value and drives the coroutine:

```c
static mp_obj_t delayed_double_coro_send(mp_obj_t self_in, mp_obj_t value) {
    delayed_double_coro_t *self = MP_OBJ_TO_PTR(self_in);
    self->send_value = value;
    mp_obj_t result = delayed_double_coro_iternext(self_in);
    
    if (result == MP_OBJ_STOP_ITERATION) {
        // Coroutine completed - raise StopIteration with return value
        mp_obj_t ret_val = MP_STATE_THREAD(stop_iteration_arg);
        mp_raise_StopIteration(ret_val);
    }
    return result;
}
```

### Return statement handling

Unlike generators (which ignore return values), async functions must propagate their return value:

```c
// For: return n * 2
self->state = 65535;  // Mark as done
return mp_make_stop_iteration(mp_obj_new_int((self->n * 2)));
```

The `mp_make_stop_iteration(value)` function stores the value in `MP_STATE_THREAD(stop_iteration_arg)` and returns `MP_OBJ_STOP_ITERATION`.

## The Bug and Fix

### The initial (broken) approach

The first implementation of await simply returned the awaitable object:

```c
// WRONG: Just returns the awaitable, doesn't iterate it
state_1:
{
    mp_obj_t _mod = mp_import_name(...);
    mp_obj_t _fn = mp_load_attr(_mod, "sleep");
    mp_obj_t awaitable = mp_call_function_1(_fn, arg);
    self->state = 2;
    return awaitable;  // BUG: Returns whole awaitable, not its yielded values
}
state_2:
    self->result = self->send_value;  // BUG: Gets wrong value
```

This worked for the simplest cases where the event loop happened to handle things correctly, but failed when:
- The awaitable yielded multiple times
- The awaitable's return value needed to be captured
- Multiple awaits appeared in sequence

### The correct yield-from pattern

The fix implements proper yield-from semantics:

```c
state_1:
{
    // First entry: create awaitable and store it
    if (self->_await_iter == mp_const_none) {
        mp_obj_t _mod = mp_import_name(qstr_from_str("asyncio"), ...);
        mp_obj_t _fn = mp_load_attr(_mod, qstr_from_str("sleep"));
        self->_await_iter = mp_call_function_1(_fn, arg);
    }
    
    // Iterate the awaitable
    mp_obj_t _ret_val = mp_iternext(self->_await_iter);
    
    if (_ret_val != MP_OBJ_STOP_ITERATION) {
        // Awaitable yielded - stay at this state, return the yielded value
        self->state = 1;  // Stay at same state!
        return _ret_val;
    }
    
    // Awaitable completed - capture result and continue
    self->_await_iter = mp_const_none;  // Clear for next await
    mp_obj_t await_result = MP_STATE_THREAD(stop_iteration_arg);
    if (await_result == MP_OBJ_NULL) { await_result = mp_const_none; }
    // Store result if needed, then fall through to next statement
}
```

Key changes:
1. **Persistent awaitable storage**: `_await_iter` field holds the awaitable across iterations
2. **Loop-until-done**: Stay at the same state until `MP_OBJ_STOP_ITERATION`
3. **Proper result capture**: Get the awaitable's return value from `stop_iteration_arg`
4. **Clean separation**: First entry creates awaitable, subsequent entries just iterate

### Complete example: delayed_double

**Input Python:**
```python
async def delayed_double(n: int) -> int:
    await asyncio.sleep(0)
    return n * 2
```

**Generated C (simplified):**
```c
typedef struct _delayed_double_coro_t {
    mp_obj_base_t base;
    uint16_t state;
    mp_obj_t send_value;
    mp_obj_t _await_iter;  // For yield-from
    mp_int_t n;
} delayed_double_coro_t;

static mp_obj_t delayed_double_coro_iternext(mp_obj_t self_in) {
    delayed_double_coro_t *self = MP_OBJ_TO_PTR(self_in);
    uint16_t st = self->state;
    self->state = 65535;
    
    switch (st) {
        case 0: goto state_0;
        case 1: goto state_1;
        case 65535: return MP_OBJ_STOP_ITERATION;
        default: return MP_OBJ_STOP_ITERATION;
    }

state_0:
    // Fall through to first await

state_1:
    {
        // Create awaitable on first entry
        if (self->_await_iter == mp_const_none) {
            mp_obj_t _mod = mp_import_name(qstr_from_str("asyncio"), 
                                           mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
            mp_obj_t _fn = mp_load_attr(_mod, qstr_from_str("sleep"));
            self->_await_iter = mp_call_function_1(_fn, mp_obj_new_int(0));
        }
        
        // Iterate awaitable
        mp_obj_t _ret_val = mp_iternext(self->_await_iter);
        if (_ret_val != MP_OBJ_STOP_ITERATION) {
            self->state = 1;  // Stay here
            return _ret_val;
        }
        
        // Await completed
        self->_await_iter = mp_const_none;
    }
    
    // return n * 2
    self->state = 65535;
    return mp_make_stop_iteration(mp_obj_new_int((self->n * 2)));
}

// Wrapper creates coroutine object
static mp_obj_t async_demo_delayed_double(mp_obj_t n_obj) {
    delayed_double_coro_t *coro = mp_obj_malloc(delayed_double_coro_t, 
                                                 &delayed_double_coro_type);
    coro->state = 0;
    coro->send_value = mp_const_none;
    coro->_await_iter = mp_const_none;
    coro->n = mp_obj_get_int(n_obj);
    return MP_OBJ_FROM_PTR(coro);
}
```

### Usage with asyncio

The compiled coroutine integrates seamlessly with MicroPython's event loop:

```python
import asyncio
import async_demo

async def main():
    result = await async_demo.delayed_double(21)
    print(result)  # 42

asyncio.run(main())
```

Or directly:
```python
>>> asyncio.run(async_demo.delayed_double(21))
42
>>> asyncio.run(async_demo.countdown_with_delay(5))
0
```

## Summary

Async/await support builds on the generator infrastructure with key additions:

1. **Coroutine type** with `__await__`, `send`, `throw`, `close` methods
2. **Return value propagation** via `mp_make_stop_iteration(value)`
3. **Yield-from semantics** for await expressions using `_await_iter` field
4. **Runtime module import** for `await module.func()` patterns

The critical insight is that `await` is not a simple yield - it's a yield-from loop that drives the awaitable to completion, capturing its return value. This requires:
- Persistent storage for the active awaitable
- Loop-until-done iteration at the same state
- Result capture from `MP_STATE_THREAD(stop_iteration_arg)`

With this implementation, compiled async functions work correctly with MicroPython's asyncio, enabling native-speed coroutines on microcontrollers.
