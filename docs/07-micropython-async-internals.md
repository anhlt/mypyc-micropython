# MicroPython Async/Await Implementation Internals

This document provides a deep dive into how async/await is implemented in MicroPython, covering the C-level generator/coroutine machinery, the Python-level asyncio library, and key differences from CPython.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [C-Level Implementation](#c-level-implementation)
- [Python-Level asyncio](#python-level-asyncio)
- [Key Differences from CPython](#key-differences-from-cpython)
- [Implications for mypyc-micropython](#implications-for-mypyc-micropython)

---

## Architecture Overview

MicroPython's async implementation consists of two layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ASYNC/AWAIT ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Python Level (extmod/asyncio/)                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  core.py    │ Event loop, sleep, create_task, run           │   │
│  │  task.py    │ Task, TaskQueue (pairing heap)                │   │
│  │  funcs.py   │ gather, wait_for                              │   │
│  │  event.py   │ Event, ThreadSafeFlag                         │   │
│  │  lock.py    │ Lock                                          │   │
│  │  stream.py  │ Stream, StreamReader, StreamWriter            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  C Level (py/, extmod/)                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  objgenerator.c  │ Generator/coroutine object               │   │
│  │  vm.c            │ YIELD_VALUE, YIELD_FROM bytecodes        │   │
│  │  compile.c       │ async def, async for, async with         │   │
│  │  modasyncio.c    │ C-optimized TaskQueue and Task           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Insight: Coroutines ARE Generators

In MicroPython (and CPython), `async def` functions are syntactic sugar over generators:

```python
# This async function:
async def fetch_data():
    await some_io()
    return "data"

# Is conceptually equivalent to:
def fetch_data():
    yield from some_io()
    return "data"
```

The `await` keyword compiles to `YIELD_FROM` bytecode, and async functions are generator objects with special flags.

---

## C-Level Implementation

### 1. Generator Object Structure

**File:** `py/objgenerator.c`

```c
// Core generator instance structure
typedef struct _mp_obj_gen_instance_t {
    mp_obj_base_t base;
    // mp_const_none: Not-running, no exception.
    // MP_OBJ_NULL: Running, no exception.
    // other: Not running, pending exception.
    mp_obj_t pend_exc;
    mp_code_state_t code_state;  // Suspended execution state
} mp_obj_gen_instance_t;
```

**Key fields:**
- `pend_exc`: Tracks pending exceptions and running state
- `code_state`: Contains the suspended bytecode state (instruction pointer, stack, locals)

### 2. Generator Creation

When you call a generator function, `gen_wrap_call()` is invoked:

```c
static mp_obj_t gen_wrap_call(mp_obj_t self_in, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_obj_fun_bc_t *self_fun = MP_OBJ_TO_PTR(self_in);
    
    // Decode prelude to get stack sizes
    const uint8_t *ip = self_fun->bytecode;
    MP_BC_PRELUDE_SIG_DECODE(ip);
    
    // Allocate generator with room for local stack and exception stack
    mp_obj_gen_instance_t *o = mp_obj_malloc_var(mp_obj_gen_instance_t, 
        code_state.state, byte,
        n_state * sizeof(mp_obj_t) + n_exc_stack * sizeof(mp_exc_stack_t),
        &mp_type_gen_instance);
    
    o->pend_exc = mp_const_none;
    o->code_state.fun_bc = self_fun;
    o->code_state.n_state = n_state;
    mp_setup_code_state(&o->code_state, n_args, n_kw, args);
    
    return MP_OBJ_FROM_PTR(o);
}
```

### 3. Generator Resume (The Core of Async)

The `mp_obj_gen_resume()` function is the heart of async execution:

```c
mp_vm_return_kind_t mp_obj_gen_resume(mp_obj_t self_in, mp_obj_t send_value, 
                                       mp_obj_t throw_value, mp_obj_t *ret_val) {
    mp_obj_gen_instance_t *self = MP_OBJ_TO_PTR(self_in);
    
    // Check if already completed
    if (self->code_state.ip == 0) {
        *ret_val = mp_const_none;
        return MP_VM_RETURN_NORMAL;  // StopIteration
    }
    
    // Prevent reentrant execution
    if (self->pend_exc == MP_OBJ_NULL) {
        mp_raise_ValueError(MP_ERROR_TEXT("generator already executing"));
    }
    
    // Handle send value (for coroutines)
    if (self->code_state.sp != state_start) {
        *self->code_state.sp = send_value;
    }
    
    // Mark as running
    self->pend_exc = MP_OBJ_NULL;
    
    // Execute bytecode until yield or return
    mp_vm_return_kind_t ret_kind = mp_execute_bytecode(&self->code_state, throw_value);
    
    // Mark as not running
    self->pend_exc = mp_const_none;
    
    switch (ret_kind) {
        case MP_VM_RETURN_NORMAL:
            self->code_state.ip = 0;  // Mark completed
            *ret_val = *self->code_state.sp;
            break;
            
        case MP_VM_RETURN_YIELD:
            *ret_val = *self->code_state.sp;
            break;
            
        case MP_VM_RETURN_EXCEPTION:
            self->code_state.ip = 0;  // Mark completed
            *ret_val = self->code_state.state[0];
            // PEP479: StopIteration -> RuntimeError inside generators
            if (mp_obj_is_subclass_fast(..., &mp_type_StopIteration)) {
                *ret_val = mp_obj_new_exception_msg(&mp_type_RuntimeError, 
                    MP_ERROR_TEXT("generator raised StopIteration"));
            }
            break;
    }
    
    return ret_kind;
}
```

### 4. VM Bytecode Handling

**File:** `py/vm.c`

The VM handles `YIELD_VALUE` and `YIELD_FROM`:

```c
// YIELD_VALUE - simple yield
ENTRY(MP_BC_YIELD_VALUE):
    *code_state->sp = return_value;
    return MP_VM_RETURN_YIELD;

// YIELD_FROM - await/yield from
ENTRY(MP_BC_YIELD_FROM): {
    mp_obj_t send_value = POP();
    mp_obj_t iter = TOP();
    
    // Try to send/throw into the sub-iterator
    mp_vm_return_kind_t ret_kind;
    mp_obj_t ret_val;
    
    if (inject_exc != MP_OBJ_NULL) {
        // throw() was called
        ret_kind = mp_obj_gen_resume(iter, mp_const_none, inject_exc, &ret_val);
    } else {
        // send() or __next__()
        ret_kind = mp_obj_gen_resume(iter, send_value, MP_OBJ_NULL, &ret_val);
    }
    
    if (ret_kind == MP_VM_RETURN_YIELD) {
        // Sub-iterator yielded, propagate up
        *code_state->sp = ret_val;
        return MP_VM_RETURN_YIELD;
    } else if (ret_kind == MP_VM_RETURN_NORMAL) {
        // Sub-iterator completed, continue execution
        SET_TOP(ret_val);  // Return value becomes result of yield from
    } else {
        // Exception from sub-iterator
        // ... exception handling ...
    }
}
```

### 5. Async Compilation

**File:** `py/compile.c`

The compiler transforms `async def`, `async for`, `async with`:

```c
// async for statement compilation
static void compile_async_for_stmt(compiler_t *comp, mp_parse_node_struct_t *pns) {
    // async for x in iterable: body
    // Compiles to:
    //   iter = type(iterable).__aiter__(iterable)
    //   while True:
    //       try:
    //           x = await type(iter).__anext__(iter)
    //       except StopAsyncIteration:
    //           break
    //       body
}

// async with statement compilation
static void compile_async_with_stmt(compiler_t *comp, mp_parse_node_struct_t *pns) {
    // async with expr as var: body
    // Compiles to use __aenter__ and __aexit__
}
```

---

## Python-Level asyncio

### 1. Task and TaskQueue

**File:** `extmod/asyncio/task.py` (Python fallback)
**File:** `extmod/modasyncio.c` (C optimized version)

```python
# Python implementation (task.py)
class Task:
    def __init__(self, coro, globals=None):
        self.coro = coro        # The coroutine to run
        self.data = None        # General data for queue it is waiting on
        self.state = True       # None, False, True, callable, or TaskQueue
        # Pairing heap fields for O(log N) scheduling
        self.ph_key = 0
        self.ph_child = None
        self.ph_child_last = None
        self.ph_next = None
        self.ph_rightmost_parent = None
    
    def __iter__(self):
        # Makes Task awaitable
        if not self.state:
            self.state = False  # Signal awaited
        elif self.state is True:
            self.state = TaskQueue()  # Create waiting queue
        return self
    
    def __next__(self):
        if not self.state:
            # Task finished, raise result
            raise self.data
        else:
            # Put calling task on waiting queue
            self.state.push(core.cur_task)
            core.cur_task.data = self
```

**C implementation** (`modasyncio.c`):

```c
typedef struct _mp_obj_task_t {
    mp_pairheap_t pairheap;    // For efficient priority queue
    mp_obj_t coro;             // The coroutine
    mp_obj_t data;             // Exception or return value
    mp_obj_t state;            // Running/done/waiting state
    mp_obj_t ph_key;           // Scheduling time (ticks)
} mp_obj_task_t;

// Task states
#define TASK_STATE_RUNNING_NOT_WAITED_ON (mp_const_true)
#define TASK_STATE_DONE_NOT_WAITED_ON (mp_const_none)
#define TASK_STATE_DONE_WAS_WAITED_ON (mp_const_false)
```

### 2. Event Loop

**File:** `extmod/asyncio/core.py`

```python
def run_until_complete(main_task=None):
    global cur_task
    # Pre-allocate to avoid heap allocation in loop
    excs_all = (CancelledError, Exception)
    excs_stop = (CancelledError, StopIteration)
    
    while True:
        # Wait for next ready task
        dt = 1
        while dt > 0:
            dt = -1
            t = _task_queue.peek()
            if t:
                # Calculate time until task is ready
                dt = max(0, ticks_diff(t.ph_key, ticks()))
            elif not _io_queue.map:
                # No tasks left
                return
            # Poll for I/O events
            _io_queue.wait_io_event(dt)
        
        # Get and run next task
        t = _task_queue.pop()
        cur_task = t
        
        try:
            exc = t.data
            if not exc:
                t.coro.send(None)  # Resume coroutine
            else:
                t.data = None
                t.coro.throw(exc)  # Throw exception into coroutine
        except excs_all as er:
            # Handle task completion/exception
            # ... wake waiting tasks, handle uncaught exceptions ...
```

### 3. Sleep Implementation (Zero Allocation)

```python
class SingletonGenerator:
    """Reusable generator to avoid heap allocation"""
    def __init__(self):
        self.state = None
        self.exc = StopIteration()
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.state is not None:
            # Schedule task to wake at self.state time
            _task_queue.push(cur_task, self.state)
            self.state = None
            return None
        else:
            # Already yielded, raise StopIteration
            self.exc.__traceback__ = None
            raise self.exc

# Global singleton - reused for every sleep_ms call
def sleep_ms(t, sgen=SingletonGenerator()):
    assert sgen.state is None
    sgen.state = ticks_add(ticks(), max(0, t))
    return sgen
```

### 4. I/O Queue

```python
class IOQueue:
    def __init__(self):
        self.poller = select.poll()
        self.map = {}  # id(stream) -> [read_task, write_task, stream]
    
    def queue_read(self, s):
        # Register stream for read and suspend current task
        self._enqueue(s, 0)
    
    def queue_write(self, s):
        # Register stream for write and suspend current task
        self._enqueue(s, 1)
    
    def wait_io_event(self, dt):
        # Poll with timeout, wake tasks when I/O ready
        for s, ev in self.poller.ipoll(dt):
            sm = self.map[id(s)]
            if ev & ~select.POLLOUT and sm[0] is not None:
                _task_queue.push(sm[0])  # Wake read waiter
                sm[0] = None
            if ev & ~select.POLLIN and sm[1] is not None:
                _task_queue.push(sm[1])  # Wake write waiter
                sm[1] = None
```

---

## Key Differences from CPython

### 1. No `Future` Class

| CPython | MicroPython |
|---------|-------------|
| `asyncio.Future` for deferred results | Not implemented |
| `loop.call_soon()`, `call_later()`, `call_at()` | Not implemented |

**Rationale:** Futures add memory overhead; Tasks suffice for embedded use cases.

### 2. Awaitable Syntax

| CPython | MicroPython |
|---------|-------------|
| `__await__()` method | `__iter__()` method |

```python
# CPython awaitable class
class Awaitable:
    def __await__(self):
        yield
        return self.result

# MicroPython awaitable class
class Awaitable:
    def __iter__(self):
        yield
        return self.result
```

**Rationale:** MicroPython's async is based on generators; `__iter__` is the native protocol.

### 3. Single Event Loop

| CPython | MicroPython |
|---------|-------------|
| Multiple event loops possible | Single global event loop |
| `asyncio.new_event_loop()` creates new loop | Resets existing loop |

### 4. MicroPython Extensions

| Feature | Description |
|---------|-------------|
| `sleep_ms(t)` | Sleep for milliseconds |
| `wait_for_ms(aw, timeout)` | Timeout in milliseconds |
| `ThreadSafeFlag` | IRQ-safe synchronization primitive |

### 5. Memory Characteristics

| CPython | MicroPython |
|---------|-------------|
| Normal heap allocation | Zero-allocation scheduler loop |
| Full exception handling | Pre-allocated exception tuples |
| Unbounded stream buffering | Explicit `drain()` required |

### 6. Task Garbage Collection

| CPython | MicroPython |
|---------|-------------|
| Must store task reference or it may be GC'd | Tasks auto-retained by scheduler |

```python
# CPython - MUST store reference
task = asyncio.create_task(coro())

# MicroPython - OK without storing
asyncio.create_task(coro())  # Won't be GC'd
```

---

## Implications for mypyc-micropython

### Why async/await Is Out of Scope

Based on this analysis, async/await is **explicitly out of scope** for mypyc-micropython because:

1. **Deep VM Integration Required**
   - Async relies on generator machinery (`YIELD_VALUE`, `YIELD_FROM` bytecodes)
   - Would require compiling to bytecode, not native C
   - State machine transformation is complex

2. **Different Implementation from CPython**
   - MicroPython uses `__iter__` instead of `__await__`
   - Single event loop assumption
   - MicroPython-specific extensions (`sleep_ms`, `ThreadSafeFlag`)

3. **Recommendation: Use Native MicroPython**
   
   For async code, users should:
   ```python
   # Keep async code as regular Python (.py files)
   # MicroPython interprets it directly
   
   async def my_async_task():
       await asyncio.sleep_ms(100)
       # ...
   
   # Compile only synchronous, performance-critical code
   # with mypyc-micropython
   
   def fast_computation(data: list[int]) -> int:
       # This can be compiled to C
       return sum(x * x for x in data)
   ```

### What COULD Be Compiled

If async support were ever added, these patterns might be feasible:

1. **Simple async functions** (no closures, no complex control flow)
2. **State machine transformation** (like mypyc does for generators)
3. **Integration with existing asyncio** (call into Python event loop)

But this would require:
- Full generator support first (Phase 5 in roadmap)
- State machine code generation
- Integration with MicroPython's `_asyncio` C module

### Current Recommendation

```
┌─────────────────────────────────────────────────────────────────────┐
│  COMPILE WITH MYPYC-MICROPYTHON        │  KEEP AS PYTHON           │
├─────────────────────────────────────────┼───────────────────────────┤
│  • Number crunching                    │  • async def functions    │
│  • Data processing loops               │  • await expressions      │
│  • Algorithms with primitives          │  • Event handlers         │
│  • Sensor data parsing                 │  • Network I/O            │
│  • Protocol encoding/decoding          │  • Hardware callbacks     │
└─────────────────────────────────────────┴───────────────────────────┘
```

---

## References

### Source Files

| File | Description |
|------|-------------|
| `py/objgenerator.c` | Generator/coroutine C implementation |
| `py/vm.c` | VM with YIELD_VALUE, YIELD_FROM |
| `py/compile.c` | async def/for/with compilation |
| `extmod/modasyncio.c` | C-optimized Task and TaskQueue |
| `extmod/asyncio/core.py` | Event loop implementation |
| `extmod/asyncio/task.py` | Python Task/TaskQueue fallback |

### External Resources

- [MicroPython asyncio docs](https://docs.micropython.org/en/latest/library/asyncio.html)
- [Peter Hinch's micropython-async](https://github.com/peterhinch/micropython-async)
- [PEP 492 - Coroutines with async and await](https://peps.python.org/pep-0492/)

---

## See Also

- [02-mypyc-reference.md](02-mypyc-reference.md) - How mypyc handles generators
- [04-feature-scope.md](04-feature-scope.md) - Why async is out of scope
- [05-roadmap.md](05-roadmap.md) - Generator support in Phase 5
