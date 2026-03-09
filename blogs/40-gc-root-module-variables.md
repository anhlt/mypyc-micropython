# GC Roots for Module Variables: Fixing a MicroPython Crash in Compiled Modules

*A module-level `dict` can look permanent in Python, but in MicroPython it can be collected if the C code that holds it is not registered as a GC root.*

---

## Table of Contents

1. [Memory Management in Embedded Systems](#part-1-memory-management-in-embedded-systems) -- Why GC matters for MicroPython, what roots are
2. [C Background](#part-2-c-background) -- `static` storage, `MP_REGISTER_ROOT_POINTER`, how MicroPython scans roots
3. [The Bug and Fix](#part-3-the-bug-and-fix) -- The crash, why it happens, and the compiler change

---

# Part 1: Memory Management in Embedded Systems

Microcontrollers are a strange place to run Python.

- RAM is small.
- You often can't afford to pre-allocate everything.
- You still want dynamic data structures like `dict` and `list`.

MicroPython solves this by using a garbage-collected heap. That heap is where most Python objects live.

The key idea for this post is simple, and it is easy to forget if you mostly write Python:

In C, an object is not kept alive because you "once assigned it" to a variable. It is kept alive because the garbage collector can still find it by following pointers starting from a set of roots.

## 1) What garbage collection does, in one picture

MicroPython's garbage collector is a classic mark-and-sweep collector.

1. Mark: start from roots, follow pointers, mark everything reachable.
2. Sweep: free everything on the heap that was not marked.

If the collector does not know a pointer exists, it can't mark the object it points to.

## 2) What is a GC root, and why it matters

A GC root is a pointer location that the collector will scan to find heap objects.

In a Python mental model, "globals live forever" is almost true.

In MicroPython's C implementation, globals only live forever if MicroPython's GC can find them.

Roots usually include:

- The C stack (locals, temporaries)
- VM state (internals like the current exception, globals dict, etc.)
- Explicit root pointer registrations (a fixed table of pointers the GC must scan)

The bug in this post happens when compiled user modules create module-level mutable objects, store them in C `static` variables, and then forget to register those variables as GC roots.

## 3) Why "static" does not automatically mean "root"

It is tempting to assume:

"This is a C `static` variable, it sits in memory, so the GC will see it."

That assumption is wrong in MicroPython.

MicroPython's GC does not just scan all memory or the whole `.bss` and `.data` regions looking for words that look like pointers. Doing that would:

- cost time on every collection
- risk keeping garbage alive by accident (false positives)
- require port-specific knowledge of memory layout

Instead, MicroPython scans a known root set.

So if your only reference to a heap object lives in a `static mp_obj_t` that is not in the root set, the object is eligible for collection.

---

# Part 2: C Background

This section is for Python developers. We'll build just enough C knowledge to understand the fix.

## 1) `static` variables in C

In C, `static` on a global variable means:

- Static storage duration: the variable exists for the entire program lifetime.
- Internal linkage (at file scope): the symbol is visible only inside that C file.

For example:

```c
static int counter;
```

On embedded targets, `counter` usually lives in `.bss` (zero-initialized) or `.data` (non-zero initialized).

Important: where it lives is not the same as being scanned by a GC.

## 2) `mp_obj_t` is just a word

MicroPython represents every Python value as an `mp_obj_t`.

On common builds, `mp_obj_t` is pointer-sized:

- For small integers and some special values, the bits inside the word encode the value directly.
- For heap objects like `dict` and `list`, the `mp_obj_t` holds a pointer to a heap-allocated C struct.

So this C variable:

```c
static mp_obj_t test__CACHE;
```

is just one machine word. If it happens to contain a pointer to a heap `dict`, the GC must know to look at this word during marking.

## 3) Macros: what `MP_REGISTER_ROOT_POINTER` really is

C macros are a compile-time text substitution system. You write something that looks like a function call, but it expands into code or declarations.

MicroPython uses this macro to register a pointer location as a root:

```c
MP_REGISTER_ROOT_POINTER(mp_obj_t test__CACHE);
```

You can think of it as:

- "Please include the address of `test__CACHE` in the GC's root pointer table."

The exact expansion varies by port and configuration, but the effect is the same: the GC is told that `test__CACHE` is a location that may contain a pointer to a heap object.

## 4) How MicroPython scans roots

At a high level, a GC cycle looks like this:

1. Stop the world (no user code runs while marking).
2. Start from roots.
3. For each root pointer location, read the `mp_obj_t` stored there.
4. If it is a heap object pointer, mark the object.
5. Follow pointers inside that object (for a dict, that means its table; for a list, its items array).
6. After marking, sweep: free all unmarked heap blocks.

If a pointer location is not part of the root set, it is invisible to step 2.

That is exactly what went wrong for module-level mutable variables.

---

# Part 3: The Bug and Fix

The symptom was an intermittent crash on ESP32 boards, usually after memory pressure caused a GC cycle.

The root cause was deterministic: module-level mutable variables were stored in C `static mp_obj_t` variables, but those variables were not registered as GC roots.

## 1) The Python pattern that triggered the bug

This is normal Python, and it is a common embedded pattern:

```python
_CACHE: dict = {}
```

You create a cache once at import time, then reuse it.

To make the example concrete, here is a module that reads and writes `_CACHE`:

```python
_CACHE: dict = {}

def get_value(k: str) -> int:
    if k in _CACHE:
        return _CACHE[k]
    _CACHE[k] = 123
    return 123
```

## 2) IR: what the compiler knows at the Python level

`mypyc-micropython` uses an intermediate representation (IR) to represent the program after parsing and type analysis.

For this example, the function IR shows `_CACHE` as a global name (it is not in `locals`), which is the key clue that it is not a normal stack-rooted local variable:

```
def get_value(k: MP_OBJ_T) -> MP_INT_T:
  c_name: test_get_value
  max_temp: 0
  locals: {k: MP_OBJ_T}
  body:
    if (k in _CACHE):
      return _CACHE[k]
    _CACHE[k] = 123
    return 123
```

IR is not where the bug lived. The bug lived later, during module emission, when module-level variables are turned into C storage.

## 3) Generated C before the fix: a dangling pointer waiting for GC

Before the fix, module-level mutable variables were emitted like this:

```c
static mp_obj_t test__CACHE;
static void test__module_init(void) {
    test__CACHE = mp_obj_new_dict(0);
}
```

There is one reference to the new dict: the `static mp_obj_t test__CACHE` word.

If MicroPython's GC does not scan that word as a root, the dict looks unreachable.

### Why this causes crashes

Step by step:

1. Import runs `test__module_init()`, which allocates a dict on the GC heap.
2. `test__CACHE` now contains a pointer to that dict.
3. Later, the heap gets tight and MicroPython runs GC.
4. GC scans roots: stack, VM state, registered root pointers.
5. `test__CACHE` is not in any of those scanned root sets.
6. The dict has no references from scanned roots, so it is not marked.
7. Sweep frees the dict. The heap block can be reused for a different object.
8. Later code executes `if k in _CACHE:`. The C code loads `test__CACHE` and treats it as a valid dict pointer.
9. That pointer now points to freed or repurposed memory. The next field access can read garbage and crash.

On ESP32 this often shows up as a hard fault like a "Load access fault", because the CPU tries to read from an invalid address.

This kind of failure is nasty:

- It depends on whether GC happened to run.
- It can corrupt memory before it crashes.
- The crash site is far away from the actual bug.

## 4) Generated C after the fix: register the root pointer

The fix is to tell MicroPython's GC that the `static mp_obj_t` is a root pointer location.

After the fix, the compiler emits:

```c
static mp_obj_t test__CACHE;
MP_REGISTER_ROOT_POINTER(mp_obj_t test__CACHE);
```

Now the GC's marking phase will read the word `test__CACHE` during root scanning. If it contains a heap object pointer, the dict will be marked and kept alive.

## 5) Where the fix lives in the compiler

This change is implemented in the module emitter, where module-level variables are declared.

In `src/mypyc_micropython/module_emitter.py`, `_emit_module_var_declarations()` now emits two things for every module variable entry:

1. The `static mp_obj_t` declaration
2. The `MP_REGISTER_ROOT_POINTER(...)` registration

```python
def _emit_module_var_declarations(self, entries: list[tuple[str, str, str]]) -> list[str]:
    lines: list[str] = []
    for module_c_name, var_name, _ in entries:
        c_var_name = f"{module_c_name}_{sanitize_name(var_name)}"
        lines.append(f"static mp_obj_t {c_var_name};")
    # Register each module variable as a GC root to prevent collection
    for module_c_name, var_name, _ in entries:
        c_var_name = f"{module_c_name}_{sanitize_name(var_name)}"
        lines.append(f"MP_REGISTER_ROOT_POINTER(mp_obj_t {c_var_name});")
    return lines
```

This is intentionally boring code. The important part is correctness.

## 6) Why this fix is the right layer

Registering GC roots is not a property of a particular function.

It is a property of how the module stores state across calls.

That is why the fix belongs in module emission, next to the `static` declarations.

Once root registration is in place, module-level caches work the way Python developers expect:

- The module variable keeps the object alive.
- GC can still collect things inside the dict when they become unreachable.
- The dict itself won't be reclaimed while the module is loaded.
