# AGENTS.md - Extended Modules

Proof-of-concept frameworks that validate compiler capabilities with real-world patterns.

## Quick Reference

```bash
# Compile all extmod packages
make compile-all BOARD=ESP32_GENERIC_C6

# Run LVGL tests on device
make run-device-lvgl-tests PORT=/dev/cu.usbmodem2101
```

## Packages

| Package | Files | LOC | Purpose |
|---------|-------|-----|---------|
| `lvgl_mvu/` | 14 | 2,791 | Model-View-Update architecture for LVGL |
| `lvui/` | 4 | 872 | Higher-level UI utilities |

## CRITICAL: Compiler Validation Role

These packages are **NOT workarounds** - they are **test harnesses** for compiler correctness.

**When MVU compilation fails, it indicates a compiler bug.** Fix the compiler, not the MVU code.

```python
# WRONG: Working around compiler limitation
# def register_factory(...):
#     pass  # Skip function references

# RIGHT: Fix the compiler to handle the pattern
# ir_builder.py: Add FuncRefIR handling
# container_emitter.py: Emit MP_OBJ_FROM_PTR(&func_obj)
```

## lvgl_mvu/ - MVU Framework

Production-grade Model-View-Update architecture for LVGL UI development.

### Architecture

```
Model (state) --> View (render) --> Widget tree (immutable)
                                        |
                                        v
                                   Reconciler (diff)
                                        |
                                        v
                                   LVGL objects (mutable)
                                        |
                                        v
                                   User interaction
                                        |
                                        v
                                   Message --> Update --> new Model
```

### Core Modules

| Module | Purpose |
|--------|---------|
| `program.py` | Program definition (init, update, view, subscribe) |
| `widget.py` | Immutable Widget descriptors |
| `attrs.py` | Attribute definitions (AttrKey enum, 150+ properties) |
| `diff.py` | O(N) widget tree diffing |
| `viewnode.py` | Persistent LVGL object wrapper |
| `reconciler.py` | Widget tree to LVGL object lifecycle |
| `app.py` | MVU runtime (message queue, tick loop) |
| `factories.py` | Widget factory functions |
| `appliers.py` | Attribute apply functions |

### Compiler Patterns Tested

1. **Module-level imports** - `import lvgl as lv`
2. **Function references** - `reconciler.register_factory(WidgetKey.LABEL, create_label)`
3. **Complex class hierarchies** - ViewNode, Reconciler, App
4. **Method dispatch** - `node.apply_diff(diff)`
5. **Callback registration** - Event handlers, timer factories
6. **Cross-module dependencies** - Imports between package submodules
7. **Frozen dataclasses** - Immutable Widget descriptors
8. **IntEnum types** - WidgetKey, AttrKey
9. **Generic TypeVars** - Model, Msg types
10. **Complex data structures** - Sorted tuples, nested lists

### Known Workarounds

Some workarounds exist due to device-specific issues (not compiler bugs):

```python
# WORKAROUND: Use index-based while loop instead of for loop.
# for attr in widget.scalar_attrs: crashes on ESP32-P4 due to
# struct-cast optimization issue in compiled C code.
scalar_attrs = widget.scalar_attrs
i: int = 0
while i < len(scalar_attrs):
    attr = scalar_attrs[i]
    # ...
    i += 1
```

These are documented and tracked as device-specific issues.

## lvui/ - UI Utilities

Higher-level wrapper around LVGL for common UI patterns.

### Modules

| Module | Purpose |
|--------|---------|
| `mvu.py` | Screen references, navigation constants |
| `screens.py` | Screen creation helpers |
| `nav.py` | ScreenManager for navigation |

### Relationship to lvgl_mvu

`lvui` builds on top of `lvgl_mvu`:
- Uses `lvgl_mvu.widget.Widget` for UI descriptions
- Uses `lvgl_mvu.reconciler.Reconciler` for widget management
- Provides simpler API for common patterns

## Testing

### Unit Tests

- `tests/test_diff.py` - Widget diffing algorithm
- `tests/test_widget.py` - Widget and attribute structures

### Device Tests

- `tests/device/run_lvgl_tests.py` - LVGL screens + MVU logic
- `tests/device/run_nav_tests.py` - Navigation flow (requires display)
- `tests/device/run_lvgl_mvu_tests.py` - MVU architecture

### Running Tests

```bash
# Compile packages
make compile-all BOARD=ESP32_GENERIC_C6

# Build and flash firmware
make build BOARD=ESP32_GENERIC_C6
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101

# Run MVU tests (no display required)
make run-device-lvgl-tests PORT=/dev/cu.usbmodem2101

# Run navigation tests (display required)
mpremote connect /dev/cu.usbmodem2101 run tests/device/run_nav_tests.py
```

## When Compilation Fails

If extmod compilation fails:

1. **Check if it's a known issue** - Look for WORKAROUND comments
2. **Identify the pattern** - What Python construct is failing?
3. **Fix the compiler** - Update ir_builder.py or emitters
4. **Add tests** - Verify the fix doesn't regress
5. **Test on device** - Verify the fix works on hardware

Do NOT:
- Comment out failing code
- Rewrite to avoid the pattern
- Add try/except to hide errors

These packages exist to catch compiler bugs. Hiding them defeats the purpose.
