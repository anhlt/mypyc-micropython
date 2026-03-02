# Fixing the Code Generator: From Pointer Bugs to Pixels on Screen

*Rewriting the C emitter to fix five critical bugs, then proving it works by building LVGL firmware and rendering widgets on a real ESP32-C6 display.*

---

Blog 21 introduced the `.pyi` stub system: describe a C library with Python type stubs, then auto-generate a MicroPython C module.

Blog 22 built the missing hardware half, a hand-written ST7789 display driver for the Waveshare ESP32-C6-LCD-1.47, then hit a nasty crash from pointer wrapping. That crash was a gift. It proved that "the wrappers compile" is not the same as "the wrappers are correct".

This post goes back to the code generator itself.

The goal is simple and strict: make the emitter correct under a real C compiler, under MicroPython's GC, and under real device behavior. Then validate end-to-end by generating LVGL bindings from a `.pyi` stub, building firmware for an ESP32-C6, and rendering widgets on the physical display.

## Table of Contents

1. [Code Generator Theory](#part-1-code-generator-theory) -- What an emitter does, and why it fails in practice
2. [C Background](#part-2-c-background-for-python-developers) -- Tagged pointers, GC roots, type objects, include guards
3. [Implementation](#part-3-implementation) -- Five fixes in the emitter, then an end-to-end LVGL build on device

---

# Part 1: Code Generator Theory

## The Emitter's Job

The `.pyi` parser (from blog 21) turns a stub into a small IR describing a C library. In this project that IR includes objects like:

- `CLibraryDef`: the whole library (headers, include dirs, funcs, structs, enums, callbacks)
- `CFuncDef`: one C function signature (name, params, return type)
- `CStructDef`: a C struct type exposed to Python (opaque handles like `lv_obj_t`)
- `CCallbackDef`: a function pointer type (like LVGL event callbacks)

The emitter takes that IR and generates a complete MicroPython module in C. For each function, it has to:

1. Emit a wrapper with the MicroPython calling convention (`mp_obj_t` arguments, `mp_obj_t` return)
2. Convert each `mp_obj_t` argument into the correct C type
3. Call the real C function
4. Convert the C return value back into an `mp_obj_t`
5. Register wrappers in the module globals table

In short: the emitter is a compiler backend for an FFI.

## Why Code Generators Have Bugs

Emitters fail in a specific way: they output text that looks plausible.

If your tests only check that the generated C contains certain strings, you can miss whole classes of failures:

- The C compiles, but returns a value that MicroPython misinterprets.
- The C runs, but MicroPython's GC frees something you "stored" in a static array.
- Callbacks work in one case, but dispatch the wrong Python function when multiple callback types exist.
- A trampoline assumes a single library pattern, and quietly breaks for a different callback signature.

The LVGL case in blog 22 made this visible. The firmware booted and the driver init worked. The crash happened only when a generated wrapper returned an LVGL pointer.

This post fixes five bugs that were invisible to the earlier string-based tests.

## The Five Bug Categories (Preview)

Here are the five categories, in the order they showed up once the generated module ran on a device:

1. Pointer wrapping: using `MP_OBJ_FROM_PTR` on external pointers
2. Callback GC safety: storing callback objects in bare C arrays instead of GC roots
3. Trampoline generality: hardcoding `lv_event_get_user_data` into every trampoline
4. Callback dispatch: matching the wrong callback type when multiple exist
5. Argument conversion: a growing `if/elif` chain instead of a unified conversion path

The fixes share a theme: stop treating C as "a string we print" and start treating C as a language with rules, runtime contracts, and memory ownership.

---

# Part 2: C Background for Python Developers

This section covers the C and MicroPython runtime concepts behind all five bugs. Each concept shows up again in Part 3.

## Tagged Pointers in MicroPython

MicroPython represents every Python value as an `mp_obj_t`. It is pointer-sized, but it is not "always a pointer".

Many builds use tagged pointers, where the low bits encode what kind of thing the value is. A simplified view:

```
mp_obj_t bit layout (conceptual):

  ...xxxxxxx1   small int (value = bits >> 1)
  ...xxxxx010   qstr (interned string id)
  ...xxxxx110   immediate (None, True, False)
  ...xxxxxx00   pointer to MicroPython heap object
```

The important rule is the last line: a value that looks like a heap pointer is assumed to point to a MicroPython object struct whose first field is `mp_obj_base_t`.

This is why `MP_OBJ_FROM_PTR(ptr)` exists: it takes a C pointer and "wraps" it into an `mp_obj_t` with no allocation.

But there is a catch.

`MP_OBJ_FROM_PTR` only works if `ptr` points to a real MicroPython heap object. It is not a general "wrap any pointer" function.

An LVGL pointer is not a MicroPython object. Treating it as one corrupts the runtime's type checks, and often crashes.

## mp_obj_malloc and Custom Types

If you want MicroPython to treat something as a Python object, you must allocate a real object, with a `base` field MicroPython understands.

MicroPython provides `mp_obj_malloc(type, mp_obj_type_t *type_obj)` for this.

For external pointers, a common pattern is a wrapper struct:

```c
typedef struct _mp_c_ptr_t {
    mp_obj_base_t base;
    void *ptr;
} mp_c_ptr_t;
```

This struct is a MicroPython heap object. It is GC-managed. It can be type-checked. It can safely carry a `void *` pointer to foreign memory.

Two key properties:

- The wrapper itself is allocated by MicroPython, so it always follows the expected object layout.
- The foreign pointer is stored as data inside that wrapper, so it is never interpreted as a tagged `mp_obj_t`.

This solves the "pointer wrapping" crash while also enabling nicer Python-side ergonomics: you can print `<LvObj>` instead of a raw integer.

## MP_DEFINE_CONST_OBJ_TYPE

MicroPython uses `mp_obj_type_t` objects to represent Python types in C.

When you create a wrapper object like `mp_c_ptr_t`, you also need a type object so MicroPython can distinguish different pointer wrapper types. LVGL has many pointer-ish types: `lv_obj_t *`, `lv_display_t *`, `lv_event_t *`, and so on.

Each exposed struct type gets its own `mp_obj_type_t`, created with `MP_DEFINE_CONST_OBJ_TYPE`.

Conceptually:

```c
MP_DEFINE_CONST_OBJ_TYPE(
    mp_type_LvObj,
    MP_QSTR_LvObj,
    MP_TYPE_FLAG_NONE,
    print, lvobj_print
);
```

Then a wrapper allocation can attach that type:

```c
mp_c_ptr_t *o = mp_obj_malloc(mp_c_ptr_t, &mp_type_LvObj);
o->ptr = ptr;
return MP_OBJ_FROM_PTR(o);
```

Now the MicroPython runtime can check and route behavior based on the object type.

## GC Root Pointers

MicroPython's GC traces pointers to find live objects.

If you store an `mp_obj_t` in a place the GC does not know about, that object can be collected. Later, when you try to call it, you crash.

This is exactly what happens with callback registries.

The naive emitter approach is:

```c
static mp_obj_t event_callbacks[32];
```

That array is just raw C storage. The GC does not automatically scan arbitrary C globals unless they are registered.

MicroPython provides a mechanism for this: `MP_REGISTER_ROOT_POINTER`.

The idea is to expose a pointer for the GC root scanner. Then the GC treats your registry as a list of live `mp_obj_t` references.

If you want to keep Python callback functions alive across time, you need this.

## Include Guards for Shared Generated Types

When you generate multiple modules, each module might want to define the same helper type.

For example, the pointer wrapper `mp_c_ptr_t` is a generic base type. You do not want to redefine it in every generated `.c` file if the build can compile and link multiple generated usermods together.

The standard C fix is an include guard pattern:

```c
#ifndef MP_C_PTR_T_DEFINED
#define MP_C_PTR_T_DEFINED

typedef struct _mp_c_ptr_t {
    mp_obj_base_t base;
    void *ptr;
} mp_c_ptr_t;

#endif
```

Now you can safely include or emit this block from multiple modules without a redefinition error.

---

# Part 3: Implementation

This section walks through five concrete fixes in the emitter, then validates the whole system by generating LVGL bindings, building firmware, flashing the ESP32-C6, and rendering widgets.

## Bug 1: Pointer Wrapping (Pointer Corruption Crash)

This is the crash from blog 22, but the fix here is stronger.

### Before: MP_OBJ_FROM_PTR on External Pointers

The emitter treated any `T *` return value as something it could wrap with `MP_OBJ_FROM_PTR`.

That is a cast, not a conversion.

If the pointer points to LVGL memory, MicroPython might interpret it as:

- a small int
- a qstr
- an immediate
- or (worst) a MicroPython heap object pointer

In the last case, MicroPython tries to read `->type` from LVGL memory and crashes.

### After: Typed Wrapper Objects

The rewritten emitter generates a wrapper type and per-struct type objects.

The shared base wrapper (guarded):

```c
#ifndef MP_C_PTR_T_DEFINED
#define MP_C_PTR_T_DEFINED

typedef struct _mp_c_ptr_t {
    mp_obj_base_t base;
    void *ptr;
} mp_c_ptr_t;

#endif
```

For each exposed struct type like `LvObj`, it generates:

- A MicroPython type object `mp_type_LvObj`
- A `wrap_LvObj(lv_obj_t *ptr) -> mp_obj_t`
- An `unwrap_LvObj(mp_obj_t obj) -> lv_obj_t *`

Sketch of the emitted helpers:

```c
static mp_obj_t wrap_LvObj(lv_obj_t *ptr) {
    if (ptr == NULL) {
        return mp_const_none;
    }
    mp_c_ptr_t *o = mp_obj_malloc(mp_c_ptr_t, &mp_type_LvObj);
    o->ptr = (void *)ptr;
    return MP_OBJ_FROM_PTR(o);
}

static lv_obj_t *unwrap_LvObj(mp_obj_t obj) {
    if (obj == mp_const_none) {
        return NULL;
    }
    mp_c_ptr_t *o = MP_OBJ_TO_PTR(obj);
    return (lv_obj_t *)o->ptr;
}
```

### Generated C: lv_screen_active

This is the wrapper that crashed in blog 22.

```c
// Before (broken):
static mp_obj_t lv_screen_active_wrapper(void) {
    lv_obj_t *result = lv_screen_active();
    return MP_OBJ_FROM_PTR(result);  // CRASH: not a MicroPython object
}

// After (fixed):
static mp_obj_t lv_screen_active_wrapper(void) {
    lv_obj_t *_c_result = lv_screen_active();
    return wrap_LvObj(_c_result);
}
```

### On Device

The return value now prints as a typed object:

```python
>>> import lvgl
>>> lvgl.init_display()
>>> scr = lvgl.lv_screen_active()
>>> scr
<LvObj>
```

That single output line is doing a lot of work. It proves:

- the pointer survived the wrapper boundary
- MicroPython did not misinterpret low bits
- the object has a real MicroPython type
- the print hook for the type is wired up

## Bug 2: GC-Safe Callbacks

LVGL heavily uses callbacks. The emitter stores Python functions so a C trampoline can call them later.

### Before: Bare C Arrays

The original emitter generated something like:

```c
#define MAX_EVENT_CALLBACKS 32
static mp_obj_t event_callbacks[MAX_EVENT_CALLBACKS];
static int event_callback_count = 0;
```

This looks fine in C. It is not fine for a tracing garbage collector.

The callback function object is a normal Python heap object. If the only reference lives in `event_callbacks[]`, and the GC does not scan that memory, it can be collected.

Then the next event calls the trampoline, the trampoline reads a freed pointer, and the firmware crashes.

### After: Root-Registered Registry

The fix is to make the registry visible to the GC.

The rewritten emitter generates a module-prefixed registry and registers it as a root pointer:

```c
#define LVGL_MAX_CALLBACKS 32

static mp_obj_t lvgl_cb_registry[LVGL_MAX_CALLBACKS];
static size_t lvgl_cb_registry_len = 0;

MP_REGISTER_ROOT_POINTER(mp_obj_t *lvgl_cb_registry_root);
static mp_obj_t *lvgl_cb_registry_root = lvgl_cb_registry;
```

Now the GC knows to treat `lvgl_cb_registry` as an array of `mp_obj_t` references.

The critical behavior change is not in the wrapper function. It is in the runtime: the callbacks stay alive.

## Bug 3: Generic Trampolines

The first callback support assumed LVGL events and hardcoded one pattern.

### Before: Hardcoded lv_event_get_user_data

Every trampoline looked like this:

```c
static void some_cb_trampoline(lv_event_t *e) {
    int idx = (int)(intptr_t)lv_event_get_user_data(e);
    mp_obj_t cb = lvgl_cb_registry[idx];
    // ... call Python cb ...
}
```

That only works for one kind of callback:

- the callback parameter is `lv_event_t *`
- LVGL provides `lv_event_get_user_data(e)`

As soon as the stub describes a callback with a different signature, or a struct type with a different `*_get_user_data` function, the trampoline is wrong.

### After: Two Trampoline Strategies

The emitter rewrite made trampolines match the callback definition.

Strategy A: explicit `user_data` parameter.

If the callback type includes an explicit `user_data` parameter, the trampoline extracts the index from that parameter position. In other words: "use the parameter the signature gives you".

Strategy B: struct-embedded user data via naming convention.

If the callback does not have an explicit `user_data` parameter, the emitter falls back to a naming convention:

```
{c_name.removesuffix("_t")}_get_user_data(p0)
```

Meaning:

- If the first parameter type is a `foo_t *`, look for `foo_get_user_data(foo)`.

This is still a convention, but it is at least a generic rule instead of a hardcoded LVGL event special case.

## Bug 4: Callback Type Matching

Once you support more than one callback type in a library, you must match the correct callback when emitting wrappers.

### Before: Always Use the First Callback

The buggy emitter effectively did:

- library has callbacks: `[EventCallback, TimerCallback, ...]`
- wrapper sees a function param annotated as "some callback"
- emitter picks the first callback in the list

That can compile and even run, while calling the wrong Python function at runtime.

This bug is subtle because:

- It does not necessarily crash.
- It can appear as "my callback never fires".
- It can appear as "a different callback fires".

### After: Match by callback_name

The fix is to use the IR information.

Each callback-bearing parameter should carry a `callback_name` that identifies its callback type. The rewritten emitter:

1. Matches by `callback_name` first
2. Falls back to the first callback only when no name is available

That keeps old stubs working while making multi-callback libraries correct.

## Bug 5: Simplified Argument Conversion

Every new C type previously added new branches to a conversion chain.

### Before: A Growing if/elif Chain

The old emitter had a long chain that checked every `CType` variant and manually selected:

- C parameter declaration
- unboxing expression from `mp_obj_t`
- boxing expression back to `mp_obj_t`

This is fragile because:

- You can update one path and forget the other.
- Adding a type means editing a large conditional.
- The logic gets duplicated between param and return handling.

### After: Unified CType Methods

The rewrite moves conversion logic onto the type representation.

The emitter asks the type:

- "What does your C declaration look like?" via `CType.to_c_decl()`
- "How do I unbox you from an mp_obj_t?" via `CType.to_mp_unbox()`

This changes the emitter from "a long list of cases" into "a dispatcher".

Practically, this means:

- adding a new `CType` updates one place
- parameter and return conversion share the same type-based code
- the wrapper body becomes shorter and easier to audit

## End-to-End LVGL Build: Proving It Works

After these five fixes, the validation is not a unit test. It is a firmware build.

Here is the full pipeline that ran on the Waveshare ESP32-C6-LCD-1.47 (ST7789 172x320 SPI), with LVGL 9.6, MicroPython v1.24.1, and ESP-IDF v5.2.2.

### Step 1: Stub

`lvgl.pyi` describes:

- 55+ functions
- 5 struct types
- 3 enums
- 1 callback

The important change from blog 22 is semantic: struct pointers are no longer "just integers". They are typed wrapper objects.

### Step 2: Compile

Generate a user module folder from the stub:

```bash
mpy-compile-c lvgl.pyi -o modules/usermod_lvgl/
```

The generated `lvgl.c` is 873 lines of C.

### Step 3: Support Files

The LVGL firmware build includes support files alongside the generated binding:

- `lv_conf.h` (110 lines): LVGL v9.6 config, 48KB RAM, 7 widgets, RGB565
- `st7789_driver.c` (138 lines): display driver for ESP32-C6 + ST7789
- `micropython.cmake` (33 lines): build config that pulls in LVGL source and `esp_lcd`

### Step 4: Build

Build the firmware:

```bash
make build-lvgl BOARD=ESP32_GENERIC_C6
```

Build stats:

- Binary size: 2.49MB
- Free space: 6% in a 2.56MB app partition

### Step 5: Flash and Test in the REPL

The device-side proof is that:

- the module imports
- display init works
- wrapper return values are typed objects
- widgets render on the physical screen

```python
>>> import lvgl
>>> lvgl.init_display()
>>> scr = lvgl.lv_screen_active()
>>> scr
<LvObj>                          # proper typed wrapper, not a raw int
>>> label = lvgl.lv_label_create(scr)
>>> lvgl.lv_label_set_text(label, 'Hello World')
>>> lvgl.timer_handler()
```

On the display, widgets render correctly. Tested widgets include label, button, slider, bar, and arc.

### Step 6: Performance Test

The quick stress test was a "count to 1000" loop with a 30fps target, updating a label each tick.

Effective result with label redraws: 22.8 FPS.

That number matters because it exercises the full stack:

- Python calls into generated wrappers
- wrappers call LVGL
- LVGL renders dirty areas
- the flush callback pushes pixels via SPI

Any pointer bug, callback bug, or conversion bug shows up fast.

## What Changed (Concrete Output)

Here is a compact view of the deliverables that made the end-to-end build work.

| Component | Lines | Purpose |
|-----------|-------|---------|
| `c_emitter.py` (rewritten) | 425 | IR to C code generator with proper pointer wrapping |
| `lvgl.c` (generated) | 873 | Auto-generated LVGL bindings from .pyi stub |
| `st7789_driver.c` | 138 | ST7789 display driver for ESP32-C6 |
| `lv_conf.h` | 110 | LVGL v9.6 config: 48KB RAM, 7 widgets, RGB565 |
| `micropython.cmake` | 33 | Build config with LVGL source + esp_lcd |

## Takeaway

FFI code generation is where "almost correct" becomes "crashes at runtime".

The five fixes in this post are not LVGL-specific. They are the minimum contracts you must satisfy whenever you emit C that runs under MicroPython:

- Never wrap foreign pointers with `MP_OBJ_FROM_PTR`
- If you store `mp_obj_t` across time, register it as a GC root
- Generate trampolines based on callback signatures, not library-specific assumptions
- Match callback types explicitly when multiple exist
- Centralize conversions in the type system, not in a growing conditional

With those contracts enforced by the emitter, the final validation is the one that counts: pixels on screen, on real hardware.
