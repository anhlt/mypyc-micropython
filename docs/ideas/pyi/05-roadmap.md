# C Bindings Roadmap

> **Last Updated**: Feb 2026
> **Current Phase**: Phase 7 (Emitter Fixes)
> **Overall Goal**: General-purpose C binding system that can wrap any C header

## Status Overview

Phases 1-6 (original implementation plan) are **complete**. The .pyi stub system
works end-to-end: stubs generate MicroPython C modules, LVGL runs on ESP32 hardware,
and callbacks function via trampolines. Blogs [21](../../../blogs/21-pyi-stub-c-bindings.md)
and [22](../../../blogs/22-lvgl-display-driver-esp32.md) document this work.

Phases 7-9 evolve the system from "LVGL-specific stub tool" into a
**general-purpose C binding generator** that can wrap any C library.

## Completed Phases (1-6)

| Phase | Status | Deliverables | Documented In |
|-------|--------|-------------|---------------|
| 1. Foundation | Done | `c_types.py`, `c_ir.py` | [04-implementation-plan.md](04-implementation-plan.md) |
| 2. Stub Parser | Done | `stub_parser.py` — full .pyi parsing | [04-implementation-plan.md](04-implementation-plan.md) |
| 3. C Emitter | Done | `c_emitter.py`, `cmake_emitter.py` | Blog 21 |
| 4. CLI & Integration | Done | `cli.py`, `compiler.py`, `mpy-compile-c` command | Blog 21 |
| 5. LVGL MVP Stub | Done | `stubs/lvgl/lvgl.pyi` — 55 functions, 7 structs, 2 enums | Blog 21 |
| 6. Callbacks & Events | Done | Callback trampolines, event handling on ESP32 | Blog 22 |

### What Works Today

```bash
# Generate LVGL bindings from stub
mpy-compile-c stubs/lvgl/lvgl.pyi -o modules/usermod_lvgl/

# Build firmware with bindings
make build BOARD=ESP32_GENERIC_C6
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101
```

```python
# On ESP32-C6 with ST7789 display
>>> import lvgl
>>> lvgl.init_display()
>>> scr = lvgl.lv_screen_active()
>>> label = lvgl.lv_label_create(scr)
>>> lvgl.lv_label_set_text(label, "Hello")
>>> lvgl.lv_obj_center(label)
>>> lvgl.timer_handler()
```

### Known Limitations (Motivating Phases 7-9)

1. **Pointer wrapping uses integers** — `scr` prints as `1082247348` instead of `LvObj(0x407a38b4)`. Works but loses type safety and readability.
2. **Callback trampoline is LVGL-specific** — hardcodes `lv_event_get_user_data()`. Cannot wrap other libraries without modifying the emitter.
3. **Callbacks lack GC protection** — static `mp_obj_t` array is invisible to MicroPython's garbage collector. Risk of use-after-free if Python callback has no other references.
4. **Callback type matching grabs first-found** — if a library has multiple callback types, the wrong trampoline signature is used.
5. **Writing stubs by hand** — workable for 55 functions (LVGL), unworkable for 500+ (ESP-IDF, full LVGL).
6. **No struct field access** — non-opaque structs are parsed correctly but the emitter never generates attribute handlers.

---

## Phase 7: Fix the Emitter (Next)

> **Goal**: Make generated C correct and library-agnostic. No new input formats.
> **Effort**: Medium
> **Dependencies**: None — works with existing .pyi stubs

### 7.1 Proper Pointer Wrapper Objects

Replace integer encoding (blog 22's `mp_obj_new_int_from_uint`) with a typed wrapper struct:

```c
// Generic wrapper for any external C pointer
typedef struct {
    mp_obj_base_t base;
    void *ptr;
} mp_c_ptr_t;

// Per-struct type object (generated per @c_struct)
static MP_DEFINE_CONST_OBJ_TYPE(
    mp_type_LvObj,
    MP_QSTR_LvObj,
    MP_TYPE_FLAG_NONE,
    print, mp_c_ptr_print
);

// Wrap: C pointer -> Python object (safe: wrapper is on MicroPython's heap)
static mp_obj_t wrap_LvObj(lv_obj_t *ptr) {
    if (ptr == NULL) return mp_const_none;
    mp_c_ptr_t *o = mp_obj_malloc(mp_c_ptr_t, &mp_type_LvObj);
    o->ptr = ptr;
    return MP_OBJ_FROM_PTR(o);
}

// Unwrap: Python object -> C pointer
static lv_obj_t *unwrap_LvObj(mp_obj_t obj) {
    if (obj == mp_const_none) return NULL;
    mp_c_ptr_t *o = MP_OBJ_TO_PTR(obj);
    return (lv_obj_t *)o->ptr;
}
```

Python sees `LvObj(0x407a38b4)` instead of `1082247348`. `MP_OBJ_FROM_PTR` is
now safe because it points to our heap-allocated wrapper, not to LVGL memory.

### 7.2 GC-Protected Callback Storage

Replace static array with GC-visible list:

```c
// GC-visible callback storage
static mp_obj_list_t cb_registry;
MP_REGISTER_ROOT_POINTER(mp_obj_list_t *mp_c_bind_callbacks);

static int cb_store(mp_obj_t callback) {
    mp_obj_list_append(MP_OBJ_FROM_PTR(&cb_registry), callback);
    return cb_registry.len - 1;
}
```

### 7.3 Generic Callback Trampolines

Remove LVGL-specific `lv_event_get_user_data()` hardcoding. Generate
trampolines per callback type — the `user_data` extraction is driven by
the `.pyi` stub's function signature, not hardcoded.

```c
// Generated per callback type — library-specific extraction in ONE place
static void cb_trampoline_EventCallback(lv_event_t *e) {
    void *user_data = lv_event_get_user_data(e);  // from stub annotation
    int idx = (int)(intptr_t)user_data;
    mp_obj_t cb = cb_registry.items[idx];
    mp_obj_t arg = wrap_LvEvent(e);
    mp_call_function_1(cb, arg);
}
```

### 7.4 Other Fixes

| Fix | What Changes | File |
|-----|-------------|------|
| Callback type matching | Match by annotation, not first-found | `c_emitter.py` |
| Simplify `_gen_arg_conversion` | Use `CType.to_mp_unbox()` directly instead of 35-line if/elif | `c_emitter.py` |
| Emit C enum references | Use actual C enum constants instead of hardcoded ints | `c_emitter.py` |
| Add `micropython.mk` generation | Some ports still use make, not cmake | `cmake_emitter.py` (or new file) |
| `_emit_enum_constants()` no-op | Method exists but does nothing — implement or remove | `c_emitter.py` |

### Deliverables

- [ ] `mp_c_ptr_t` wrapper struct replaces integer encoding
- [ ] Wrapper/unwrapper functions generated per `@c_struct`
- [ ] GC-rooted callback storage
- [ ] Per-callback-type trampoline generation
- [ ] Simplified arg conversion using `CType` methods
- [ ] All existing tests still pass
- [ ] LVGL still works on ESP32 hardware

---

## Phase 8: C Header Parser

> **Goal**: Auto-parse C headers to generate `CLibraryDef` without manual stubs.
> **Effort**: Medium-Large
> **Dependencies**: Phase 7 (clean emitter), `pycparser` dependency

### Design

New file: `header_parser.py` using **pycparser** (proven by lvgl-micropython,
pure Python, parses real C headers after preprocessing).

```python
class HeaderParser:
    """Parse C headers into CLibraryDef using pycparser."""

    def parse(self, header_path: Path, include_dirs: list[str],
              defines: list[str]) -> CLibraryDef:
        # 1. Preprocess with gcc -E (expands macros, resolves includes)
        # 2. Parse with pycparser (builds C AST)
        # 3. Walk AST -> extract functions, structs, enums, typedefs
        # 4. Build CLibraryDef (same IR as StubParser produces)
        ...
```

**Key property**: Output is the same `CLibraryDef` that `StubParser` produces.
Everything downstream (emitter, cmake) is unchanged.

### Type Inference from C Headers

```python
C_TYPE_MAP = {
    "void": CType.VOID,
    "int": CType.INT,
    "unsigned int": CType.UINT,
    "int8_t": CType.INT8,
    "uint8_t": CType.UINT8,
    "float": CType.FLOAT,
    "double": CType.DOUBLE,
    "bool": CType.BOOL,
    "_Bool": CType.BOOL,
    "char *": CType.STR,
    "const char *": CType.STR,
    # Anything with * -> CType.STRUCT_PTR or CType.PTR
}
```

### Why pycparser

- Proven by lvgl-micropython on LVGL's 2000+ function API
- Pure Python — no native compilation dependencies
- `fake_libc_include` trick handles missing system headers
- Gives a full C AST — functions, structs, enums, typedefs

### CLI Extension

```bash
# New mode: from C header directly
mpy-compile-c --header mylib.h --name mylib -o modules/usermod_mylib/

# Old mode still works
mpy-compile-c stubs/lvgl/lvgl.pyi -o modules/usermod_lvgl/
```

### New Dependency

```toml
# pyproject.toml
dependencies = [
    "mypy[mypyc]>=1.0.0",
    "pycparser>=2.21",
]
```

### Deliverables

- [ ] `header_parser.py` — pycparser-based C header parsing
- [ ] Type inference for all standard C types
- [ ] Typedef resolution (follows chains like `typedef uint32_t lv_coord_t`)
- [ ] Struct extraction (opaque by default, fields for non-opaque)
- [ ] Enum extraction with values
- [ ] `--header` CLI flag
- [ ] Tests against real-world headers (LVGL, ESP-IDF subsets)

---

## Phase 9: Hybrid System (Config + Merge)

> **Goal**: Combine auto-parsed headers with .pyi overrides via TOML config.
> **Effort**: Medium
> **Dependencies**: Phase 8 (header parser)

### Config Format (`bind.toml`)

```toml
[library]
name = "mylib"
headers = ["include/mylib.h"]
include_dirs = ["include", "deps/mylib/include"]
libraries = ["mylib"]
defines = ["MYLIB_ENABLE_FEATURE_X"]

[filter]
# Glob patterns for what to expose
include = ["mylib_*"]
exclude = ["mylib_internal_*", "mylib_debug_*"]

# Strip prefix for Python names: mylib_create_widget -> create_widget
strip_prefix = "mylib_"

[overrides]
# Optional .pyi file for annotations the parser can't infer
file = "mylib_overrides.pyi"
```

### Override .pyi (Optional, Only Special Cases)

```python
# mylib_overrides.pyi
# Only specify what the header parser can't infer:

# Mark parent as optional (parser sees mylib_widget_t*, can't know it's nullable)
def mylib_create_widget(parent: c_ptr[Widget] | None) -> c_ptr[Widget]: ...

# Mark cb as callback with user_data pattern
def mylib_set_handler(
    ctx: c_ptr[Context],
    cb: Callable[[c_ptr[Event]], None],
    user_data: c_ptr[c_void],
) -> None: ...
```

### Merge Logic

New file: `merger.py`

```python
class LibraryMerger:
    """Merge HeaderParser output + StubParser overrides + config."""

    def merge(self, parsed: CLibraryDef, overrides: CLibraryDef | None,
              config: BindConfig) -> CLibraryDef:
        # 1. Start with auto-parsed C headers
        # 2. Apply filter (include/exclude from config)
        # 3. Apply strip_prefix to Python names
        # 4. Apply .pyi overrides (optional params, callbacks, docstrings)
        # 5. Return merged CLibraryDef
        ...
```

### CLI Extension

```bash
# Full hybrid mode
mpy-compile-c --config bind.toml -o modules/usermod_mylib/

# Header-only mode (no overrides, expose everything)
mpy-compile-c --header mylib.h --name mylib -o modules/usermod_mylib/

# Stub-only mode (original, still works)
mpy-compile-c stubs/lvgl/lvgl.pyi -o modules/usermod_lvgl/
```

### Deliverables

- [ ] `config.py` — TOML config reader
- [ ] `merger.py` — merge parsed headers + overrides + filters
- [ ] `--config` CLI flag
- [ ] Include/exclude glob filtering
- [ ] Prefix stripping for Python names
- [ ] Tests: config-driven binding generation

---

## Future Ideas (Post Phase 9)

These are recorded but not planned:

| Idea | Description | Reference |
|------|-------------|-----------|
| Direct C calls | Compiled Python calling C bindings directly (skip MicroPython dispatch) | [06-direct-c-calls.md](06-direct-c-calls.md) |
| Method sugar | `obj.center()` instead of `lv_obj_center(obj)` via struct methods in .pyi | Phase 9 overrides could support this |
| Struct field access | Non-opaque struct attribute handlers | Phase 7 starts this |
| Auto-stub generation | `--emit-stub` flag to generate .pyi from parsed headers | Pairs with Phase 8 |
| Multiple library support | Merge bindings from several C libraries into one module | Extend merger |
| Memory ownership tracking | `@c_owned` / `@c_borrowed` annotations for pointer lifetime | Needs design |

---

## Architecture: How the Phases Stack

```
Phase 1-6 (DONE):
  .pyi stub --> StubParser --> CLibraryDef --> CEmitter --> C module

Phase 7 (NEXT):
  .pyi stub --> StubParser --> CLibraryDef --> CEmitter (FIXED) --> C module
                                                |
                                                +-- proper pointer wrappers
                                                +-- GC-safe callbacks
                                                +-- generic trampolines

Phase 8:
  C header (.h) --> HeaderParser --> CLibraryDef --> CEmitter --> C module
  .pyi stub -----> StubParser ---/
  (either input produces the same IR)

Phase 9:
                              +---> CLibraryDef --+
  C header --> HeaderParser --+                     |
                              +---> (raw)           |
                                      |             +--> Merger --> CLibraryDef --> CEmitter --> C module
  bind.toml --> Config ----------------+             |
                                      |             |
  overrides.pyi --> StubParser --------+---> (ovr) --+
```

**Key invariant**: `CLibraryDef` is the canonical IR throughout all phases.
All input paths produce it, all emitters consume it. Adding new inputs
(headers, config) never requires changing the emitter.

---

## Blog Progression

| Blog | Title | Covers |
|------|-------|--------|
| 21 | .pyi Stub-Based C Bindings | Phases 1-5 |
| 22 | LVGL Display Driver on ESP32 | Phase 6 + display driver |
| 23 (planned) | General C Bindings: Proper Pointer Wrapping + Generic Callbacks | Phase 7 |
| 24 (planned) | Auto-Parsing C Headers with pycparser | Phase 8 |
| 25 (planned) | Hybrid Bindings: Headers + .pyi Overrides + Config | Phase 9 |