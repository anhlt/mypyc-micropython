# Direct C Calls from Compiled Python

> **Status**: Enhancement Idea  
> **Benefit**: 10-100x faster calls to C bindings

## The Opportunity

When mypyc-micropython compiles Python code that calls LVGL (or any C binding), we have two options:

### Option A: Runtime Import (Current Default)

```python
# my_app.py
import lvgl as lv

def create_button():
    screen = lv.lv_screen_active()
    return lv.lv_btn_create(screen)
```

Generated C (dynamic dispatch):
```c
static mp_obj_t my_app_create_button(void) {
    // Runtime import
    mp_obj_t lv = mp_import_name(MP_QSTR_lvgl, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    
    // Dynamic attribute lookup
    mp_obj_t screen_active_fn = mp_load_attr(lv, MP_QSTR_lv_screen_active);
    mp_obj_t screen = mp_call_function_0(screen_active_fn);
    
    // Another dynamic lookup
    mp_obj_t btn_create_fn = mp_load_attr(lv, MP_QSTR_lv_btn_create);
    mp_obj_t result = mp_call_function_1(btn_create_fn, screen);
    
    return result;
}
```

**Problem**: Each call requires:
1. Module lookup
2. Attribute lookup (hash table search)
3. Function call through pointer

### Option B: Direct C Calls (With .pyi Knowledge)

If we know the `.pyi` stub at compile time, we can generate **direct calls**:

```c
// Declare external functions from lvgl.c
extern mp_obj_t lv_screen_active_wrapper(void);
extern mp_obj_t lv_btn_create_wrapper(mp_obj_t);

static mp_obj_t my_app_create_button(void) {
    // Direct C call - no lookup!
    mp_obj_t screen = lv_screen_active_wrapper();
    
    // Direct C call - no lookup!
    mp_obj_t result = lv_btn_create_wrapper(screen);
    
    return result;
}
```

**Benefit**: 
- No module import overhead
- No attribute lookup
- Direct function call (just a jump instruction)
- **10-100x faster** for hot paths

## Implementation

### Step 1: Load .pyi at Compile Time

```bash
mpy-compile my_app.py --c-stub lvgl.pyi -o modules/my_app/
```

The compiler reads `lvgl.pyi` and knows:
- `lv.lv_screen_active()` maps to `lv_screen_active_wrapper()`
- `lv.lv_btn_create(x)` maps to `lv_btn_create_wrapper(x)`

### Step 2: Generate Direct Calls

When the compiler sees:
```python
import lvgl as lv
screen = lv.lv_screen_active()
```

It generates:
```c
extern mp_obj_t lv_screen_active_wrapper(void);
mp_obj_t screen = lv_screen_active_wrapper();
```

### Step 3: Link at Build Time

Both modules are compiled and linked together:
```cmake
target_sources(usermod INTERFACE
    modules/my_app/my_app.c
    modules/lvgl/lvgl.c
)
```

## Type Safety Bonus

With `.pyi` knowledge, we can also:

1. **Validate types at compile time**
   ```python
   lv.lv_obj_set_size(btn, "100", 50)  # Error: str != c_int
   ```

2. **Skip unnecessary boxing/unboxing**
   ```c
   // If we know both sides expect mp_obj_t, no conversion needed
   mp_obj_t btn = lv_btn_create_wrapper(screen);
   // screen is already mp_obj_t, btn will be mp_obj_t
   ```

3. **Inline simple wrappers**
   ```c
   // Instead of calling wrapper, call C directly
   lv_obj_t *c_screen = mp_to_ptr(screen);
   lv_obj_t *c_btn = lv_btn_create(c_screen);
   mp_obj_t btn = ptr_to_mp(c_btn);
   ```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      COMPILE TIME                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐                                    │
│  │  my_app.py  │    │  lvgl.pyi   │                                    │
│  └──────┬──────┘    └──────┬──────┘                                    │
│         │                  │                                            │
│         │    ┌─────────────┘                                           │
│         │    │                                                          │
│         ▼    ▼                                                          │
│  ┌─────────────────────┐                                               │
│  │   mpy-compile       │                                               │
│  │                     │                                               │
│  │  Sees: import lvgl  │                                               │
│  │  Knows: lvgl.pyi    │                                               │
│  │  Generates: direct  │                                               │
│  │  C function calls   │                                               │
│  └──────────┬──────────┘                                               │
│             │                                                           │
│             ▼                                                           │
│  ┌─────────────────────┐                                               │
│  │  my_app.c           │                                               │
│  │                     │                                               │
│  │  extern mp_obj_t    │                                               │
│  │  lv_btn_create_...  │──────┐                                        │
│  └─────────────────────┘      │                                        │
│                               │ direct call                            │
│  ┌─────────────────────┐      │                                        │
│  │  lvgl.c             │◀─────┘                                        │
│  │  (from lvgl.pyi)    │                                               │
│  └─────────────────────┘                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Fallback Behavior

If no `.pyi` stub is provided, fall back to runtime import:

```python
import unknown_module  # No .pyi available
unknown_module.do_something()
```

Generated C (fallback):
```c
mp_obj_t mod = mp_import_name(MP_QSTR_unknown_module, ...);
mp_obj_t fn = mp_load_attr(mod, MP_QSTR_do_something);
mp_call_function_0(fn);
```

This keeps compatibility while optimizing known modules.

## Summary

| Approach | Lookup Cost | Call Cost | Total |
|----------|-------------|-----------|-------|
| Runtime import | ~100 cycles | ~20 cycles | ~120 cycles |
| Direct C call | 0 cycles | ~5 cycles | ~5 cycles |
| **Speedup** | | | **~24x** |

This optimization is especially valuable for:
- GUI code (many LVGL calls per frame)
- Sensor reading loops
- Any hot path calling C bindings
