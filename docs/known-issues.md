# Known Issues and Workarounds

This document tracks known issues in the mypyc-micropython compiler that need to be addressed.

## C Reserved Keywords in Method Names

**Status**: Documented, fix pending  
**Discovered**: 2026-03-09  
**Severity**: Build failure

### Problem

Python method names that are C reserved keywords cause compilation failures when the generated C code is compiled.

**Example**: A method named `register()` in Python:

```python
class AttrRegistry:
    def register(self, attr_def: AttrDef) -> AttrDef:
        self._attrs[attr_def.key] = attr_def
        return attr_def
```

Generates C code with `register` as a struct field name:

```c
typedef struct {
    mp_obj_t (*register)(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_obj_t attr_def);
    // ...
} lvgl_mvu_attrs_AttrRegistry_vtable_t;

static const lvgl_mvu_attrs_AttrRegistry_vtable_t lvgl_mvu_attrs_AttrRegistry_vtable_inst = {
    .register = lvgl_mvu_attrs_AttrRegistry_register__native,  // ERROR: 'register' is a C keyword
    // ...
};
```

### Error Message

```
error: expected identifier or '(' before 'register'
  130 |     mp_obj_t (*register)(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_obj_t attr_def);
      |                ^~~~~~~~
```

### C Reserved Keywords to Avoid

The following C keywords should not be used as Python method/function names:

```
auto, break, case, char, const, continue, default, do, double, else,
enum, extern, float, for, goto, if, int, long, register, return,
short, signed, sizeof, static, struct, switch, typedef, union,
unsigned, void, volatile, while
```

Additionally, C99/C11 added:
```
_Bool, _Complex, _Imaginary, inline, restrict, _Alignas, _Alignof,
_Atomic, _Generic, _Noreturn, _Static_assert, _Thread_local
```

### Current Workaround

Rename the Python method to avoid the C keyword:

```python
# Before (causes build failure)
def register(self, attr_def: AttrDef) -> AttrDef:
    ...

# After (works)
def add(self, attr_def: AttrDef) -> AttrDef:
    ...
```

### Proper Fix (TODO)

The compiler should automatically mangle C reserved keywords in generated code:

1. In `function_emitter.py` and `class_emitter.py`, check if method/function names are C reserved keywords
2. If so, append a suffix (e.g., `_` or `_py`) to the C identifier
3. The MicroPython binding should still use the original Python name via QSTR

Example fix approach:

```python
C_RESERVED_KEYWORDS = {
    'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
    'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if', 'int',
    'long', 'register', 'return', 'short', 'signed', 'sizeof', 'static',
    'struct', 'switch', 'typedef', 'union', 'unsigned', 'void', 'volatile',
    'while', 'inline', 'restrict', '_Bool', '_Complex', '_Imaginary',
}

def mangle_c_keyword(name: str) -> str:
    """Mangle C reserved keywords to avoid compilation errors."""
    if name in C_RESERVED_KEYWORDS:
        return f"{name}_py"
    return name
```

### Files to Modify

- `src/mypyc_micropython/function_emitter.py` - Function name generation
- `src/mypyc_micropython/class_emitter.py` - Method name and vtable generation
- `src/mypyc_micropython/module_emitter.py` - Module-level function registration

### Test Case to Add

```python
def test_c_reserved_keyword_method_name():
    """Methods named after C keywords should compile without errors."""
    source = '''
class Registry:
    _items: dict[int, str]
    
    def __init__(self) -> None:
        self._items = {}
    
    def register(self, key: int, value: str) -> None:
        self._items[key] = value
'''
    result = compile_source(source, "test")
    assert result  # Should not fail
    # The C code should use mangled name like 'register_py'
    assert "register_py" in result or "register_" in result
```

---

## For Loop Over Dataclass Tuple Crashes on ESP32-P4

**Status**: Documented, workaround in place  
**Discovered**: 2026-03-09  
**Severity**: Runtime crash (watchdog reset)

### Problem

Using `for` loops to iterate over dataclass tuple fields (like `widget.scalar_attrs`) causes crashes on ESP32-P4 due to struct-cast optimization issues in the generated C code.

**Example that crashes:**

```python
@dataclass(frozen=True)
class Widget:
    scalar_attrs: tuple[ScalarAttr, ...]

def apply_attrs(widget: Widget) -> None:
    for attr in widget.scalar_attrs:  # CRASHES on ESP32-P4
        process(attr)
```

**Crash symptoms:**
- `Guru Meditation Error: Core 1 panic'ed (Load access fault)`
- `HP_SYS_HP_WDT_RESET` (watchdog reset)
- Crash occurs mid-iteration, not on first access

### Current Workaround

Use index-based `while` loops instead of `for` loops:

```python
def apply_attrs(widget: Widget) -> None:
    scalar_attrs = widget.scalar_attrs
    i: int = 0
    while i < len(scalar_attrs):
        attr = scalar_attrs[i]
        process(attr)
        i += 1
```

### Affected Files

Files using this workaround:
- `extmod/lvgl_mvu/reconciler.py` - `_create_node()` method
- `extmod/lvgl_mvu/viewnode.py` - `dispose()` method

### Root Cause (TODO: Investigate)

The issue appears to be in how the compiler generates iteration code for dataclass tuple fields. Possible causes:

1. **Iterator protocol**: The generated iterator may not properly handle struct-cast pointers
2. **Temporary variable lifecycle**: Iterator temporaries may be garbage-collected mid-loop
3. **Memory alignment**: Struct field access may have alignment issues on RISC-V (ESP32-P4)

### Test Case to Add

```python
@pytest.mark.c_runtime
def test_for_loop_over_dataclass_tuple():
    source = '''
@dataclass(frozen=True)
class Item:
    key: int
    value: str

@dataclass(frozen=True)
class Container:
    items: tuple[Item, ...]

def sum_keys(c: Container) -> int:
    total: int = 0
    for item in c.items:
        total += item.key
    return total
'''
    # Should compile and run without crashing
    result = compile_and_run(source, ...)
```
