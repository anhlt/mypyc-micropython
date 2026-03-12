# Callback GC Prevention: Keeping Lambda Closures Alive in LVGL Event Handlers

*When you pass a Python callback to a C library, the callback can be garbage collected if nothing in Python holds a reference to it. This causes crashes with cryptic error messages like `'ScalarAttr' object isn't callable`.*

---

## Table of Contents

1. [The Problem](#part-1-the-problem) -- Mysterious crashes after pressing buttons
2. [Understanding the Bug](#part-2-understanding-the-bug) -- Why callbacks get collected
3. [The Fix](#part-3-the-fix) -- Storing callback references to prevent GC

---

# Part 1: The Problem

We built a counter app with LVGL buttons using the MVU (Model-View-Update) architecture. The app worked... sometimes. After pressing buttons a few times, we got crashes:

```
TypeError: 'ScalarAttr' object isn't callable
```

Or sometimes:

```
TypeError: 'WidgetBuilder' object isn't callable
```

Or the device would crash entirely and reset.

The error messages were bizarre. `ScalarAttr` is a dataclass for widget attributes. `WidgetBuilder` is a fluent builder class. Neither should ever be "called" as a function. Yet Python was trying to call them.

## 1.1) The Pattern: Random Objects Being Called

The key insight was that the error wasn't about `ScalarAttr` or `WidgetBuilder` specifically. The error was that *some random object in memory* was being called as if it were a function.

This is the signature of memory corruption -- specifically, a pointer that once pointed to a valid function now points to garbage (or to a different object that happened to be allocated in the same memory location).

## 1.2) When Did It Happen?

The crash happened:

- After multiple button presses (not immediately)
- More reliably after garbage collection ran
- Only with real touch events (not simulated dispatches)

This pointed to the LVGL event callback system. Something was being collected that shouldn't be.

---

# Part 2: Understanding the Bug

## 2.1) How Event Callbacks Work

When you register an event handler in LVGL, you pass a callback function:

```python
# In EventBinder.bind()
def bind(self, lv_obj: object, event_type: int, msg: object) -> EventHandler:
    handler = EventHandler(HandlerKind.MSG, msg)
    dispatch_fn = self._dispatch_fn

    # Create a closure that captures handler, dispatch_fn, and msg
    callback = lambda event: _dispatch_msg(handler, dispatch_fn, msg)

    # Pass callback to LVGL
    lv.lv_obj_add_event_cb(lv_obj, callback, event_type, None)
    return handler
```

The callback is a lambda that captures three variables in its closure:
- `handler` -- the EventHandler object
- `dispatch_fn` -- the MVU dispatch function
- `msg` -- the message to dispatch

## 2.2) The Reference Chain Problem

Here's what the reference chain looked like:

```
EventHandler (returned to caller, kept alive)
    |
    +-- active: bool
    +-- kind: int
    +-- payload: object (the msg)

callback (lambda) --> PASSED TO LVGL, NO PYTHON REFERENCE KEPT
    |
    +-- closure captures: handler, dispatch_fn, msg
```

The `EventHandler` was kept alive because the `ViewNode` stored it in a dictionary. But the `callback` lambda itself had no Python reference -- it was only stored inside LVGL's C data structures.

## 2.3) Why This Causes GC Problems

MicroPython's garbage collector marks objects starting from GC roots. It follows Python references to find reachable objects.

LVGL is a C library. When you pass a Python object to LVGL via the bindings, LVGL stores a pointer to it. But that pointer is in C memory, not in Python's object graph.

The critical insight:

**LVGL holds a C pointer to the callback, but MicroPython's GC doesn't know about it.**

When GC runs:

1. GC starts from roots (Python stack, module globals, registered root pointers)
2. GC follows Python references to mark reachable objects
3. The callback lambda is NOT reachable from Python -- only from LVGL's C code
4. GC marks the callback as garbage
5. GC frees the callback's memory
6. Later, LVGL tries to invoke the callback
7. The memory now contains a different object (like `ScalarAttr`)
8. Python tries to call it -- crash!

## 2.4) Memory Reuse Makes It Worse

MicroPython reuses memory aggressively. After the callback is freed, its memory might be allocated for a new object. When LVGL tries to call the "callback", it actually calls whatever object now lives at that address.

This explains the random error messages:

- `'ScalarAttr' object isn't callable` -- a ScalarAttr was allocated where the callback used to be
- `'WidgetBuilder' object isn't callable` -- a WidgetBuilder was allocated there
- `'' object isn't callable` -- an empty string was allocated there
- Device crash -- the memory contained invalid data

---

# Part 3: The Fix

## 3.1) The Solution: Keep a Python Reference

The fix is simple: store the callback in a Python object that won't be garbage collected.

```python
class EventHandler:
    """Reference to a registered LVGL event callback."""

    active: bool
    kind: int
    payload: object
    _callback: object  # NEW: prevent GC of the lambda

    def __init__(self, kind: int, payload: object) -> None:
        self.active = True
        self.kind = kind
        self.payload = payload
        self._callback = None  # set by EventBinder.bind()

    def store_callback(self, callback: object) -> None:
        """Store callback reference to prevent garbage collection."""
        self._callback = callback

    def deactivate(self) -> None:
        """Deactivate this handler. The LVGL callback becomes a no-op."""
        self.active = False
```

Now update `bind()` to store the callback:

```python
def bind(self, lv_obj: object, event_type: int, msg: object) -> EventHandler:
    handler = EventHandler(HandlerKind.MSG, msg)
    dispatch_fn = self._dispatch_fn

    # Closure captures: handler, dispatch_fn, msg
    callback = lambda event: _dispatch_msg(handler, dispatch_fn, msg)

    # Store callback in handler to prevent garbage collection
    handler.store_callback(callback)

    lv.lv_obj_add_event_cb(lv_obj, callback, event_type, None)
    return handler
```

## 3.2) The New Reference Chain

After the fix:

```
EventHandler (kept alive by ViewNode)
    |
    +-- active: bool
    +-- kind: int
    +-- payload: object (the msg)
    +-- _callback: object (the lambda) <-- NEW

callback (lambda) --> ALSO PASSED TO LVGL
    |
    +-- closure captures: handler, dispatch_fn, msg
```

Now the callback is reachable from Python:

```
GC Root --> ViewNode --> handlers dict --> EventHandler --> _callback --> lambda
```

The lambda stays alive as long as the EventHandler stays alive.

## 3.3) Testing the Fix

After the fix, the counter app ran for 60 seconds with 31 forced garbage collections:

```
Touch buttons! Test callback GC fix.
60 seconds...
[GC #1]
[GC #2]
Count: 1
Count: 2
...
[GC #15]
Count: 25
Count: 26
...
[GC #31]
Done, count: -7
```

No crashes, even with aggressive garbage collection every 2 seconds.

---

# Lessons Learned

## 1) C Libraries Don't Participate in Python GC

When you pass a Python object to a C library, you must ensure Python keeps a reference to it. The C library's pointer doesn't count as a reference for garbage collection purposes.

## 2) Random "X object isn't callable" = Memory Corruption

If you see errors like `'SomeUnrelatedClass' object isn't callable`, it usually means:

- A function pointer was collected
- Its memory was reused for a different object
- Something tried to call the old function pointer

## 3) The Fix Is Always "Keep a Python Reference"

The solution is always the same: store the object in a Python data structure that won't be collected. Common patterns:

- Store in `self._callback` on a long-lived object
- Add to a module-level list/dict
- Use `MP_REGISTER_ROOT_POINTER` for C-level storage (see blog 40)

## 4) Test with Forced GC

To verify a GC fix, force garbage collection periodically:

```python
import gc
gc.collect()  # Run after each operation
```

If the bug is GC-related, forcing collection makes it reproduce immediately instead of randomly.

---

# Summary

| Symptom | Cause | Fix |
|---------|-------|-----|
| `'X' object isn't callable` where X is random | Callback GC'd, memory reused | Store callback in Python object |
| Crash after multiple operations | Delayed GC finally runs | Same as above |
| Works in simulation, fails with real events | Real events trigger more allocations → more GC | Same as above |

The fundamental rule: **If C code holds a pointer to a Python object, Python code must also hold a reference to that object.**

LVGL event callbacks, timer callbacks, interrupt handlers -- any time Python code crosses into C and expects to be called back, you need to keep Python references alive.
