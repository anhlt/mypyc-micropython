# 45. Class Constants: Final and ClassVar Support

Python classes often define constants as class attributes. On MicroPython, accessing `ClassName.CONSTANT` at runtime requires attribute lookup, which costs cycles and RAM. This post explains how `mypyc-micropython` compiles `Final[T]` class constants to C `#define` macros for zero-cost access.

## Table of Contents

- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [Part 2: C Background](#part-2-c-background)
- [Part 3: Implementation](#part-3-implementation)
- [Device Testing](#device-testing)
- [Closing](#closing)

## Part 1: Compiler Theory

### The Problem with Runtime Constants

In standard Python, class constants are just class attributes:

```python
class LvEvent:
    CLICKED = 10
    LONG_PRESSED = 20
```

When you write `LvEvent.CLICKED`, Python performs attribute lookup at runtime:
1. Look up `LvEvent` in the module namespace
2. Look up `CLICKED` in the class's `__dict__`
3. Return the value

This is flexible (you can modify class attributes at runtime) but expensive for embedded systems where these values never change.

### mypyc's Approach: Immutable Namespaces

The mypyc documentation describes a pattern for [immutable namespaces](https://mypyc.readthedocs.io/en/stable/native_classes.html#immutable-namespaces):

```python
from typing import Final

class LvEvent:
    CLICKED: Final[int] = 10
    LONG_PRESSED: Final[int] = 20
```

The `Final[T]` annotation tells the type checker (and our compiler) that this value will never change. This enables compile-time constant propagation.

### Two Kinds of Class Attributes

Python's typing module distinguishes two patterns:

| Annotation | Meaning | Compiler Strategy |
|------------|---------|-------------------|
| `attr: Final[T] = value` | Immutable constant | Compile-time `#define` |
| `attr: ClassVar[T] = value` | Mutable class variable | Runtime module-level storage |
| `attr: T` (no annotation) | Instance attribute | Per-instance field |

For `Final` attributes, the compiler can replace all references with the literal value. For `ClassVar` attributes, we need runtime storage but can still optimize the access path.

### IR Representation

The compiler introduces two new IR nodes:

**ClassConstIR** - Represents access to a `Final` class constant:
```
ClassConstIR(
    class_name='LvEvent',
    attr_name='CLICKED',
    c_name='LvEvent_CLICKED',
    value=10,
    value_ctype=CType.MP_INT_T
)
```

**ClassVarIR** - Represents access to a `ClassVar` class variable:
```
ClassVarIR(
    class_name='Config',
    attr_name='counter',
    c_name='Config_counter',
    value_ctype=CType.MP_INT_T
)
```

### Constant Folding at IR Build Time

When the IR builder encounters `LvEvent.CLICKED`:

1. Recognize `LvEvent` as a known class
2. Look up `CLICKED` in the class's fields
3. Check if the field has `is_final=True`
4. If final: create `ClassConstIR` with the literal value
5. If classvar: create `ClassVarIR` for runtime lookup
6. Otherwise: compile as normal attribute access

The key insight is that `Final` constants are resolved at IR build time, not at C code emission time. This allows them to participate in further optimizations.

## Part 2: C Background

### C Preprocessor Macros

C's `#define` directive creates compile-time text substitution:

```c
#define LvEvent_CLICKED ((mp_int_t)10)

// Later in code:
if (event_code == LvEvent_CLICKED) { ... }

// Preprocessor expands to:
if (event_code == ((mp_int_t)10)) { ... }
```

This has zero runtime cost. The compiler sees the literal value directly.

### Declaration Order Matters

In C, identifiers must be declared before use. This code fails:

```c
// ERROR: LvEvent_CLICKED not declared yet
mp_obj_t get_click_event(void) {
    return mp_obj_new_int(LvEvent_CLICKED);
}

// Too late - function already compiled
#define LvEvent_CLICKED ((mp_int_t)10)
```

The fix is to emit `#define` statements before any functions that use them:

```c
// First: all constants
#define LvEvent_CLICKED ((mp_int_t)10)
#define LvEvent_LONG_PRESSED ((mp_int_t)20)

// Then: functions that use them
mp_obj_t get_click_event(void) {
    return mp_obj_new_int(LvEvent_CLICKED);
}
```

This ordering requirement drove a significant part of the implementation.

### Type Casting in Macros

We wrap constant values in type casts:

```c
#define LvEvent_CLICKED ((mp_int_t)10)     // Integer
#define Config_DEBUG_MODE ((bool)true)      // Boolean
#define Config_PI ((mp_float_t)3.14159)     // Float
```

This ensures the preprocessor substitution has the expected type, avoiding implicit conversion warnings.

## Part 3: Implementation

### Step 1: Field Detection in IR Builder

When building a class, detect `Final` and `ClassVar` annotations:

```python
# ir_builder.py
def _parse_field_annotation(self, annotation: ast.expr) -> tuple[CType, bool, bool]:
    """Parse type annotation, returning (ctype, is_final, is_classvar)."""
    
    if isinstance(annotation, ast.Subscript):
        # Check for Final[T] or ClassVar[T]
        if isinstance(annotation.value, ast.Name):
            if annotation.value.id == "Final":
                inner_type = self._get_subscript_inner_type(annotation)
                return (CType.from_python_type(inner_type), True, False)
            elif annotation.value.id == "ClassVar":
                inner_type = self._get_subscript_inner_type(annotation)
                return (CType.from_python_type(inner_type), False, True)
    
    return (CType.from_python_type(annotation), False, False)
```

### Step 2: Store Constant Values in ClassIR

The `FieldIR` dataclass tracks whether a field is final and stores its value:

```python
@dataclass
class FieldIR:
    name: str
    ctype: CType
    is_final: bool = False      # Final[T] - compile-time constant
    is_classvar: bool = False   # ClassVar[T] - mutable class variable
    final_value: object = None  # Literal value for Final fields
```

### Step 3: Emit Class Constants in ClassEmitter

The `ClassEmitter` generates `#define` statements for `Final` fields:

```python
def emit_class_constants(self) -> list[str]:
    """Emit #define constants for Final class attributes."""
    lines: list[str] = []
    
    for field in self.class_ir.fields.values():
        if not field.is_final or field.final_value is None:
            continue
        
        c_name = f"{self.c_name}_{field.name}"
        
        if field.ctype == CType.MP_INT_T:
            lines.append(f"#define {c_name} ((mp_int_t){field.final_value})")
        elif field.ctype == CType.BOOL:
            val_str = "true" if field.final_value else "false"
            lines.append(f"#define {c_name} ((bool){val_str})")
        elif field.ctype == CType.MP_FLOAT_T:
            lines.append(f"#define {c_name} ((mp_float_t){field.final_value})")
    
    return lines
```

### Step 4: Handle ClassName.ATTR Access

When the IR builder sees `ClassName.ATTR`:

```python
def _build_attribute(self, node: ast.Attribute, locals_: dict) -> tuple[ValueIR, list[InstrIR]]:
    """Build attribute access, checking for class constants."""
    
    if isinstance(node.value, ast.Name):
        class_name = node.value.id
        attr_name = node.attr
        
        # Check if this is a known class
        if class_name in self.known_classes:
            class_ir = self.known_classes[class_name]
            
            if attr_name in class_ir.fields:
                field = class_ir.fields[attr_name]
                
                if field.is_final and field.final_value is not None:
                    # Compile-time constant access
                    return ClassConstIR(
                        class_name=class_name,
                        attr_name=attr_name,
                        c_name=f"{class_ir.c_name}_{attr_name}",
                        value=field.final_value,
                        value_ctype=field.ctype,
                    ), []
                
                if field.is_classvar:
                    # Runtime class variable access
                    return ClassVarIR(
                        class_name=class_name,
                        attr_name=attr_name,
                        c_name=f"{class_ir.c_name}_{attr_name}",
                        value_ctype=field.ctype,
                    ), []
    
    # Fall through to normal attribute access
    ...
```

### Step 5: Emit C Code for ClassConstIR

In `container_emitter.py`:

```python
def _value_to_c(self, value: ValueIR) -> str:
    if isinstance(value, ClassConstIR):
        # Direct reference to #define constant
        return value.c_name
    
    if isinstance(value, ClassVarIR):
        # Reference to module-level variable
        return value.c_name
    
    ...
```

### Step 6: Fix Code Emission Order

The critical fix was ensuring constants are emitted before functions. In `module_emitter.py`:

```python
def emit(self, ..., class_constants: list[str], function_code: list[str], ...) -> str:
    lines: list[str] = []
    
    # ... includes, forward decls, structs ...
    
    # Emit class constants BEFORE functions
    if class_constants:
        lines.extend(class_constants)
        lines.append("")
    
    # Now functions can use the constants
    for func_code in function_code:
        lines.append(func_code)
    
    ...
```

### IR Dump Example

For this Python code:

```python
from typing import Final

class LvEvent:
    CLICKED: Final[int] = 10
    LONG_PRESSED: Final[int] = 20

def get_click_event() -> int:
    return LvEvent.CLICKED
```

The IR dump (`mpy-compile --dump-ir text`) shows:

```
def get_click_event() -> MP_INT_T:
  c_name: class_constants_get_click_event
  max_temp: 0
  locals: {}
  body:
    return LvEvent.CLICKED  # Final constant
```

### Generated C Code

```c
// Constants emitted first
#define class_constants_LvEvent_CLICKED ((mp_int_t)10)
#define class_constants_LvEvent_LONG_PRESSED ((mp_int_t)20)

// Functions can now use them
static mp_obj_t class_constants_get_click_event(void) {
    return mp_obj_new_int(class_constants_LvEvent_CLICKED);
}
```

## Device Testing

The implementation was verified on an ESP32-P4 device:

```python
# tests/device/run_device_tests.py

suite("class_constants")
import class_constants as cc

# Test LvEvent class constants via Class.ATTR syntax
t("LvEvent.CLICKED", cc.get_click_event(), "10")
t("LvEvent.LONG_PRESSED", cc.get_long_press_event(), "20")

# Test Config class constants
t("Config.DEBUG_MODE", cc.is_debug(), "True")
t("Config.MAX_ITEMS", cc.get_max_items(), "100")

# Test function using class constants in comparisons
t("check_event(10)", cc.check_event(10), "True")
t("check_event(99)", cc.check_event(99), "False")

# Test using class constants in if/else
t("compare_events eq", cc.compare_events(5, 5), "10")   # Returns CLICKED
t("compare_events neq", cc.compare_events(5, 10), "30") # Returns RELEASED
```

All 480 device tests pass, including the 8 new class constant tests.

## Closing

### What We Built

1. **ClassConstIR** - New IR node for `Final[T]` class constant access
2. **ClassVarIR** - New IR node for `ClassVar[T]` class variable access
3. **FieldIR extensions** - Track `is_final`, `is_classvar`, and `final_value`
4. **ClassEmitter.emit_class_constants()** - Generate `#define` statements
5. **Code ordering fix** - Emit constants before functions that use them

### Performance Impact

| Access Pattern | Runtime Cost |
|----------------|--------------|
| Python `ClassName.ATTR` | Dict lookup (several us) |
| Compiled `Final` constant | Zero (preprocessor substitution) |
| Compiled `ClassVar` access | Module variable read (~1 us) |

### When to Use Each Pattern

```python
from typing import Final, ClassVar

class Config:
    # Use Final for true constants
    VERSION: Final[int] = 1
    MAX_ITEMS: Final[int] = 100
    
    # Use ClassVar for mutable class state
    instance_count: ClassVar[int] = 0
    
    # No annotation = instance attribute
    name: str  # Each instance has its own name
```

### The Key Insight

Declaration order in C is not optional. When a function references a `#define` constant, that constant must be defined earlier in the file. The fix required threading `class_constants` through the entire compilation pipeline:

```
ClassEmitter.emit_class_constants()
    -> _ModuleCompileParts.class_constants
        -> ModuleEmitter.emit(class_constants=...)
            -> Emit constants BEFORE function_code
```

This ordering constraint is invisible in Python but fundamental in C.
