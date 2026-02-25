# Compiling Python Decorators to C: @property, @staticmethod, and @classmethod

*How `mypyc-micropython` compiles Python class decorators into efficient C dispatch code for MicroPython.*

---

Decorators in Python look like simple annotations above a method definition, but they fundamentally change how a method behaves at runtime. `@staticmethod` removes the implicit `self` parameter, `@classmethod` binds the class instead of the instance, and `@property` transforms a method into an attribute access.

For an ahead-of-time compiler targeting MicroPython's C API, each of these requires a different compilation strategy. This post walks through how we implemented all three.

---

## Table of Contents

1. [Part 1: Compiler Theory](#part-1-compiler-theory)
2. [Part 2: C Background for Python Developers](#part-2-c-background-for-python-developers)
3. [Part 3: Implementation](#part-3-implementation)
4. [Part 4: Device Testing](#part-4-device-testing)

---

# Part 1: Compiler Theory

## What Decorators Actually Do

In Python, decorators are syntactic sugar for wrapping a function. When you write:

```python
class Rectangle:
    @staticmethod
    def is_square_dims(w: int, h: int) -> bool:
        return w == h
```

Python transforms this into:

```python
class Rectangle:
    def is_square_dims(w: int, h: int) -> bool:
        return w == h
    is_square_dims = staticmethod(is_square_dims)
```

The `staticmethod()` wrapper tells Python's attribute lookup machinery: "don't bind this to an instance -- just return the raw function."

Similarly, `@classmethod` wraps the function so that attribute lookup binds the **class** (not the instance) as the first argument, and `@property` wraps it so that attribute lookup **calls** the function and returns the result.

## Why Decorators Are Challenging for Compilers

The challenge is that each decorator type requires a different dispatch mechanism at the C level:

| Decorator | Python Behavior | Compilation Strategy |
|-----------|----------------|---------------------|
| `@staticmethod` | No `self` parameter, callable from class or instance | Wrapper struct in `locals_dict` |
| `@classmethod` | `cls` parameter bound automatically | Wrapper struct in `locals_dict` |
| `@property` | Attribute access calls getter/setter | Inline dispatch in `attr` handler |

The key insight is that MicroPython's type system already handles `@staticmethod` and `@classmethod` for us through its `locals_dict` lookup mechanism, but `@property` requires a completely different approach because MicroPython's C type system does **not** support the descriptor protocol for C-defined types.

## Our Compilation Strategy

For each decorator type, we:

1. **Detect** the decorator during IR building (AST analysis)
2. **Record** decorator metadata in the IR (`MethodIR.is_static`, `is_classmethod`, `is_property`)
3. **Emit** different C code based on the decorator type:
   - Static/class methods: generate a wrapper struct and add to `locals_dict`
   - Properties: generate inline dispatch code in the `attr` handler function

---

# Part 2: C Background for Python Developers

## How MicroPython Dispatches Attribute Access

When Python code accesses an attribute like `obj.method`, MicroPython follows a specific lookup protocol. For C-defined types, this involves:

1. Call the type's `attr` handler function (if defined)
2. If `attr` handler doesn't handle it, fall back to `locals_dict` lookup
3. For `locals_dict` entries, call `mp_convert_member_lookup()` to handle special wrappers

The `attr` handler receives a `dest` array that determines whether we are getting or setting:

```
attr handler protocol:
  dest[0] == MP_OBJ_NULL  -->  "get" request
  dest[1] != MP_OBJ_NULL  -->  "set" request (dest[1] = new value)
```

This protocol is central to understanding how properties work.

## The `mp_rom_obj_static_class_method_t` Wrapper

MicroPython has a special struct for marking methods as static or class methods:

```c
typedef struct _mp_rom_obj_static_class_method_t {
    mp_obj_base_t base;       // Points to &mp_type_staticmethod or &mp_type_classmethod
    mp_rom_obj_t fun;         // The actual function object
} mp_rom_obj_static_class_method_t;
```

When MicroPython's `mp_convert_member_lookup()` encounters this struct in `locals_dict`, it checks the base type:

- If `&mp_type_staticmethod`: return the raw function (no instance binding)
- If `&mp_type_classmethod`: bind the class as the first argument

This means the C runtime already knows how to dispatch these -- we just need to put the right wrapper in `locals_dict`.

## Why Properties Cannot Use `locals_dict`

For Python-defined classes, MicroPython handles `@property` through the descriptor protocol. But for **C-defined types** (like our compiled classes), `mp_convert_member_lookup()` does NOT check for property descriptors. It only handles `staticmethod` and `classmethod` wrappers.

This means we must handle property dispatch ourselves, directly in the `attr` handler function. We generate inline code that:

1. Checks if the attribute name matches a property
2. On **get** (`dest[0] == MP_OBJ_NULL`): calls the getter function and stores the result
3. On **set** (`dest[1] != MP_OBJ_NULL`): calls the setter function with the new value

```
Dispatch flow for attribute access on a compiled class:

  obj.attr
    |
    v
  attr_handler(self, attr, dest)
    |
    +-- Is attr a @property name?
    |     YES --> dest[0] is NULL? call getter : call setter
    |     return
    |
    +-- Is attr a field name?
    |     YES --> read/write struct field
    |     return
    |
    +-- Fall through to locals_dict
          (handles regular methods, @staticmethod, @classmethod)
```

## The dest Protocol for Getters and Setters

The `dest` array in MicroPython's `attr` handler has a specific meaning:

```c
static void MyClass_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    // GETTER: dest[0] == MP_OBJ_NULL means "get this attribute"
    if (dest[0] == MP_OBJ_NULL) {
        dest[0] = /* computed value */;  // Store result here
        return;
    }

    // SETTER: dest[1] != MP_OBJ_NULL means "set this attribute to dest[1]"
    if (dest[1] != MP_OBJ_NULL) {
        /* use dest[1] as the new value */
        dest[0] = MP_OBJ_NULL;  // Signal success
        return;
    }
}
```

For a read-only property (getter only, no setter), we signal "not settable" by setting `dest[1] = MP_OBJ_SENTINEL`:

```c
if (dest[1] != MP_OBJ_NULL) {
    dest[1] = MP_OBJ_SENTINEL;  // "I don't handle setting this"
    return;
}
```

---

# Part 3: Implementation

## The Python Source

Here is the example code that exercises all three decorator types:

```python
class Rectangle:
    width: int
    height: int

    def __init__(self, w: int, h: int) -> None:
        self.width = w
        self.height = h

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def perimeter(self) -> int:
        return 2 * (self.width + self.height)

    def scale(self, factor: int) -> None:
        self.width = self.width * factor
        self.height = self.height * factor

    @staticmethod
    def is_square_dims(w: int, h: int) -> bool:
        return w == h

    @classmethod
    def square(cls, size: int) -> object:
        return cls


class Temperature:
    _celsius: int

    def __init__(self, c: int) -> None:
        self._celsius = c

    @property
    def celsius(self) -> int:
        return self._celsius

    @celsius.setter
    def celsius(self, value: int) -> None:
        self._celsius = value

    def get_fahrenheit(self) -> int:
        return self._celsius * 9 // 5 + 32


class Counter:
    _count: int

    def __init__(self, start: int) -> None:
        self._count = start

    @property
    def count(self) -> int:
        return self._count

    def increment(self) -> None:
        self._count = self._count + 1

    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b
```

## IR Output

Running `mpy-compile examples/decorators.py --dump-ir text` produces:

```
Module: decorators (c_name: decorators)

Classes:
  Class: Rectangle (c_name: decorators_Rectangle)
    Fields:
      width: int (MP_INT_T)
      height: int (MP_INT_T)
    Methods:
      def __init__(w: MP_INT_T, h: MP_INT_T) -> VOID
      @property def area() -> MP_INT_T
      @property def perimeter() -> MP_INT_T
      def scale(factor: MP_INT_T) -> VOID
      @staticmethod def is_square_dims(w: MP_INT_T, h: MP_INT_T) -> BOOL
      @classmethod def square(cls: MP_OBJ_T, size: MP_INT_T) -> MP_OBJ_T

  Class: Temperature (c_name: decorators_Temperature)
    Fields:
      _celsius: int (MP_INT_T)
    Methods:
      def __init__(c: MP_INT_T) -> VOID
      @property def celsius() -> MP_INT_T
      @property def celsius(value: MP_INT_T) -> VOID
      def get_fahrenheit() -> MP_INT_T

  Class: Counter (c_name: decorators_Counter)
    Fields:
      _count: int (MP_INT_T)
    Methods:
      def __init__(start: MP_INT_T) -> VOID
      @property def count() -> MP_INT_T
      def increment() -> VOID
      @staticmethod def add(a: MP_INT_T, b: MP_INT_T) -> MP_INT_T
```

Notice the decorator annotations in the IR: `@property`, `@staticmethod`, `@classmethod` are preserved as metadata on each `MethodIR`, guiding the emitter to generate different C code for each.

### IR Tree for Each Decorator Type

**@staticmethod** (`--dump-ir tree --ir-function is_square_dims`):

```
`-- root: MethodIR
    |-- name: "is_square_dims"
    |-- c_name: "decorators_Rectangle_is_square_dims"
    |-- params: list[2]
    |   |-- [0]: tuple[2]
    |   `-- [1]: tuple[2]
    |-- return_type: CType.BOOL
    |-- is_static: True
    |-- is_classmethod: False
    |-- is_property: False
    `-- vtable_index: -1
```

Key: `is_static: True` tells the emitter to skip the `self` parameter entirely.

**@classmethod** (`--dump-ir tree --ir-function square`):

```
`-- root: MethodIR
    |-- name: "square"
    |-- c_name: "decorators_Rectangle_square"
    |-- params: list[2]
    |   |-- [0]: tuple[2]     <-- cls parameter
    |   `-- [1]: tuple[2]     <-- size parameter
    |-- return_type: CType.MP_OBJ_T
    |-- is_static: False
    |-- is_classmethod: True
    |-- is_property: False
    `-- vtable_index: -1
```

Key: `is_classmethod: True`, and `cls` is in the params list as `MP_OBJ_T`.

**@property** (`--dump-ir tree --ir-function area`):

```
`-- root: MethodIR
    |-- name: "area"
    |-- c_name: "decorators_Rectangle_area"
    |-- return_type: CType.MP_INT_T
    |-- is_static: False
    |-- is_classmethod: False
    |-- is_property: True
    `-- vtable_index: -1
```

Key: `is_property: True` and `vtable_index: -1` (properties are excluded from the vtable).

## Generated C: @staticmethod

For `@staticmethod`, we generate two things: the function itself (no `self` parameter) and a wrapper struct in `locals_dict`.

**The function:**

```c
// Native function -- no self parameter, just the args directly
static bool decorators_Rectangle_is_square_dims_native(mp_int_t w, mp_int_t h) {
    return (w == h);
}

// MicroPython wrapper -- unbox args, call native, box result
static mp_obj_t decorators_Rectangle_is_square_dims_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    mp_int_t w = mp_obj_get_int(arg0_obj);
    mp_int_t h = mp_obj_get_int(arg1_obj);
    return decorators_Rectangle_is_square_dims_native(w, h) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(decorators_Rectangle_is_square_dims_fun_obj,
                           decorators_Rectangle_is_square_dims_mp);
```

**The wrapper struct:**

```c
static const mp_rom_obj_static_class_method_t decorators_Rectangle_is_square_dims_obj = {
    {&mp_type_staticmethod},                                     // <-- marks as static
    MP_ROM_PTR(&decorators_Rectangle_is_square_dims_fun_obj)     // <-- the actual function
};
```

**In `locals_dict`:**

```c
static const mp_rom_map_elem_t decorators_Rectangle_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_scale), MP_ROM_PTR(&decorators_Rectangle_scale_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_square_dims), MP_ROM_PTR(&decorators_Rectangle_is_square_dims_obj) },
    { MP_ROM_QSTR(MP_QSTR_square), MP_ROM_PTR(&decorators_Rectangle_square_obj) },
};
```

When MicroPython looks up `Rectangle.is_square_dims`, it finds the wrapper in `locals_dict`. The runtime's `mp_convert_member_lookup()` sees `&mp_type_staticmethod` as the base type and returns the raw function without binding an instance.

## Generated C: @classmethod

`@classmethod` follows the same pattern as `@staticmethod` but uses `&mp_type_classmethod` as the wrapper base type:

**The function:**

```c
// cls is received as mp_obj_t -- the MicroPython runtime binds it automatically
static mp_obj_t decorators_Rectangle_square_native(mp_obj_t cls, mp_int_t size) {
    return cls;
}

static mp_obj_t decorators_Rectangle_square_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    mp_obj_t cls = arg0_obj;
    mp_int_t size = mp_obj_get_int(arg1_obj);
    return decorators_Rectangle_square_native(cls, size);
}
MP_DEFINE_CONST_FUN_OBJ_2(decorators_Rectangle_square_fun_obj,
                           decorators_Rectangle_square_mp);
```

**The wrapper struct:**

```c
static const mp_rom_obj_static_class_method_t decorators_Rectangle_square_obj = {
    {&mp_type_classmethod},                                  // <-- marks as classmethod
    MP_ROM_PTR(&decorators_Rectangle_square_fun_obj)
};
```

The only difference from `@staticmethod` is `&mp_type_classmethod`. When `mp_convert_member_lookup()` sees this, it wraps the function so that the **class type** is passed as the first argument.

## Generated C: @property (Getter)

Properties are fundamentally different from static/class methods. They generate inline dispatch code in the `attr` handler function:

**The getter function:**

```c
static mp_int_t decorators_Rectangle_area_native(decorators_Rectangle_obj_t *self) {
    return (self->width * self->height);
}
```

**The dispatch in `attr` handler:**

```c
static void decorators_Rectangle_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    decorators_Rectangle_obj_t *self = MP_OBJ_TO_PTR(self_in);

    // @property: area (read-only)
    if (attr == MP_QSTR_area) {
        if (dest[0] == MP_OBJ_NULL) {
            // Getter: call native function, box the result
            dest[0] = mp_obj_new_int(decorators_Rectangle_area_native(self));
            return;
        }
        if (dest[1] != MP_OBJ_NULL) {
            // No setter -- signal "not settable"
            dest[1] = MP_OBJ_SENTINEL;
            return;
        }
    }

    // ... field access, other properties, fall through to locals_dict
}
```

The property getter is called **inline** during attribute access. There is no method object created, no function call overhead through the MicroPython runtime -- just a direct C function call to compute and return the value.

## Generated C: @property with Setter

The `Temperature.celsius` property has both a getter and a setter:

```c
// Getter
static mp_int_t decorators_Temperature_celsius_native(decorators_Temperature_obj_t *self) {
    return self->_celsius;
}

// Setter
static void decorators_Temperature_celsius_setter_native(
    decorators_Temperature_obj_t *self, mp_int_t value
) {
    self->_celsius = value;
    return;
}
```

**The dispatch in `attr` handler:**

```c
if (attr == MP_QSTR_celsius) {
    if (dest[0] == MP_OBJ_NULL) {
        // Getter
        dest[0] = mp_obj_new_int(decorators_Temperature_celsius_native(self));
        return;
    }
    if (dest[1] != MP_OBJ_NULL) {
        // Setter: unbox the new value, call setter, signal success
        decorators_Temperature_celsius_setter_native(self, mp_obj_get_int(dest[1]));
        dest[0] = MP_OBJ_NULL;
        return;
    }
}
```

Notice `dest[0] = MP_OBJ_NULL` after the setter call -- this signals to MicroPython that the attribute was successfully set.

## Decorator Detection in the IR Builder

The IR builder detects decorators by examining `ast.FunctionDef.decorator_list`:

```python
# In ir_builder.py, simplified

for decorator in node.decorator_list:
    if isinstance(decorator, ast.Name):
        if decorator.id == "staticmethod":
            method.is_static = True
        elif decorator.id == "classmethod":
            method.is_classmethod = True
        elif decorator.id == "property":
            method.is_property = True
            # Create PropertyInfo with this method as getter
            class_ir.properties[method.name] = PropertyInfo(
                name=method.name, getter=method
            )

    elif isinstance(decorator, ast.Attribute):
        # Handle @prop_name.setter pattern
        if decorator.attr == "setter":
            prop_name = decorator.value.id  # e.g., "celsius"
            if prop_name in class_ir.properties:
                class_ir.properties[prop_name].setter = method
```

The `@celsius.setter` detection is the trickiest part -- the AST represents it as an `ast.Attribute` node where `value` is the property name and `attr` is `"setter"`.

## Key Design Decisions

### Why Properties Go in `attr`, Not `locals_dict`

MicroPython's `mp_convert_member_lookup()` handles `staticmethod` and `classmethod` wrappers automatically. But it does **not** implement the descriptor protocol for C-defined types. Property objects placed in `locals_dict` would be returned as raw objects -- they would not trigger getter/setter calls.

By generating inline dispatch code in the `attr` handler, we bypass `locals_dict` entirely for properties. The getter/setter call happens before `locals_dict` is ever consulted.

### Why Static/Class Methods Use Wrapper Structs

We could have generated `attr` handler code for static/class methods too (as we do for properties). But using `mp_rom_obj_static_class_method_t` wrappers in `locals_dict` is:

1. **Less code** -- MicroPython's runtime does the dispatch for us
2. **More correct** -- handles edge cases like calling via instance (`self.is_square_dims()`)
3. **ROM-friendly** -- wrapper structs can be placed in read-only memory (important for microcontrollers)

### Why Properties Are Excluded from the Vtable

Properties are dispatched through the `attr` handler, not through method calls. Including them in the vtable would be misleading -- they have no method binding, and the vtable is specifically for virtual method dispatch.

In the IR, property methods have `vtable_index: -1` and are not added to the vtable struct.

---

# Part 4: Device Testing

All decorator features were verified on real ESP32-C6 hardware:

```
[TEST] Testing decorators module...
  Rectangle.is_square_dims(3, 3) staticmethod... PASS
  Rectangle.is_square_dims(3, 4) staticmethod... PASS
  Counter.add(3, 4) staticmethod... PASS
  Rectangle.square(5) classmethod returns cls... PASS
  Rectangle.area property... PASS
  Rectangle.perimeter property... PASS
  Temperature.celsius property getter... PASS
  Temperature.celsius property setter... PASS
  Counter.count property... PASS
  Counter.count after increment... PASS
  Counter.add via instance... PASS
  Temperature.get_fahrenheit with property... PASS
  Rectangle.area after scale... PASS

Total tests run: 262
Passed: 262
Success rate: 100.0%
```

All 13 decorator-specific tests pass, along with the full suite of 262 device tests. The generated C code compiles cleanly with the RISC-V cross-compiler and runs correctly on the 32-bit ESP32-C6 microcontroller.

---

## Summary

| Decorator | IR Flag | C Dispatch | Lives In |
|-----------|---------|-----------|----------|
| `@staticmethod` | `is_static: True` | `mp_rom_obj_static_class_method_t` + `mp_type_staticmethod` | `locals_dict` |
| `@classmethod` | `is_classmethod: True` | `mp_rom_obj_static_class_method_t` + `mp_type_classmethod` | `locals_dict` |
| `@property` (getter) | `is_property: True` | Inline `dest[0] = getter(self)` | `attr` handler |
| `@property` (setter) | `PropertyInfo.setter` | Inline `setter(self, dest[1])` | `attr` handler |

The key architectural insight: let MicroPython's runtime handle what it already knows how to do (`staticmethod`/`classmethod` via `locals_dict`), and generate custom dispatch only where the runtime falls short (`@property` via `attr` handler).
