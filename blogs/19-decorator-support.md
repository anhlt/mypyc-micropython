# Decorator Support: @property, @staticmethod, and @classmethod

*How `mypyc-micropython` lowers Python decorators into MicroPython type slots and descriptor wrappers.*

---

Decorators look like a small, local rewrite in Python source, but they change how attribute lookup behaves at runtime.
For an ahead-of-time compiler that emits MicroPython C modules, that is the whole problem: the generated C type has to participate in MicroPython's attribute and method lookup rules, not just expose C functions.

This post documents how `mypyc-micropython` implements three decorators that show up constantly in real code:

- `@property` (getter and optional setter)
- `@staticmethod`
- `@classmethod`

All examples and outputs below come from `examples/decorators.py` and the generated module `modules/usermod_decorators/decorators.c`.

---

## Table of Contents

1. [Part 1: Compiler Theory](#part-1-compiler-theory)
2. [Part 2: C Background for Python Developers](#part-2-c-background-for-python-developers)
3. [Part 3: Implementation](#part-3-implementation)
4. [Key Design Decisions](#key-design-decisions)
5. [Device Testing](#device-testing)
6. [Part 5: Future Improvements](#part-5-future-improvements)
7. [Closing](#closing)

---

# Part 1: Compiler Theory

## What decorators mean to a compiler

Inside a class body, a decorator is not "just metadata". It changes what object is stored under the method name in the class namespace.

Conceptually:

```text
@decorator
def f(...): ...

becomes

f = decorator(f)
```

That replacement matters because later attribute lookup sees the *decorated object*, not the original function.

- `@staticmethod` replaces the function with a wrapper that prevents binding `self`.
- `@classmethod` replaces the function with a wrapper that binds the *type* (class) as the first argument.
- `@property` replaces a function with a descriptor that runs code on `obj.attr` load (and optionally on store).

## Why decorators are challenging for a MicroPython C-module compiler

`mypyc-micropython` does not emit Python bytecode that the VM can re-interpret. It emits a native C type definition (via `MP_DEFINE_CONST_OBJ_TYPE`) plus a `locals_dict` and optional type slots like `attr`.

So the decorator question becomes:

"Where should this behavior live in the generated MicroPython type?"

There are two main places to hook attribute lookup for user-defined native types:

1. `locals_dict`: a dictionary of methods and class attributes
2. `type->attr` slot: a C function that handles attribute load and store

Decorators split cleanly along that line:

- `@staticmethod` and `@classmethod` are handled by putting a *decorator wrapper object* in `locals_dict`, because MicroPython already knows how to unwrap them during member lookup.
- `@property` is handled by generating logic in `type->attr`, because for C-defined types we need to run the getter or setter during attribute access.

## Descriptor protocol, but only the part we need

In Python terms, `@property` is a descriptor. It controls `obj.attr` and `obj.attr = value`.
For this compiler, we care about two effects:

- A load (`obj.area`) should call a getter and produce a value.
- A store (`obj.celsius = 10`) should call a setter and return success, or raise if the property is read-only.

Our strategy is to represent that as a compile-time known mapping:

```text
property name -> (getter MethodIR, optional setter MethodIR)
```

That mapping gets emitted into the class `attr` handler.

# Part 2: C Background for Python Developers

This section focuses on the MicroPython mechanisms that make these decorators work for native (C-defined) types.

## Attribute lookup order for native types: attr first, then locals_dict

MicroPython attempts a type's `attr` slot first. If the slot indicates "not handled", MicroPython falls back to `locals_dict`.

This is the key control point (from `deps/micropython/py/runtime.c`):

```c
if (MP_OBJ_TYPE_HAS_SLOT(type, attr)) {
    MP_OBJ_TYPE_GET_SLOT(type, attr)(obj, attr, dest);
    // If type->attr has set dest[1] = MP_OBJ_SENTINEL, we should proceed
    // with lookups below (i.e. in locals_dict). If not, return right away.
    if (dest[1] != MP_OBJ_SENTINEL) {
        return;
    }
    dest[1] = MP_OBJ_NULL;
}
if (MP_OBJ_TYPE_HAS_SLOT(type, locals_dict)) {
    mp_map_t *locals_map = &MP_OBJ_TYPE_GET_SLOT(type, locals_dict)->map;
    mp_map_elem_t *elem = mp_map_lookup(locals_map, MP_OBJ_NEW_QSTR(attr), MP_MAP_LOOKUP);
    if (elem != NULL) {
        mp_convert_member_lookup(obj, type, elem->value, dest);
    }
    return;
}
```

This explains two things you'll see in our generated code:

- Properties must be handled in `attr`, because `attr` runs before `locals_dict`.
- When our `attr` handler does not recognize a name, it sets `dest[1] = MP_OBJ_SENTINEL` to request fallback into `locals_dict`.

## The dest[0] / dest[1] protocol (getter vs setter)

MicroPython uses a two-element array `dest` to communicate what kind of attribute operation is happening and what the result is.

- For loads, `dest[0] == MP_OBJ_NULL` and the handler should write the loaded value into `dest[0]`.
- For stores, `dest[1] != MP_OBJ_NULL` and the handler should consume `dest[1]` as the value being assigned.

The compiler's own C API notes show this common pattern (from `docs/03-micropython-c-api.md`):

```c
static void point_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    point_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (dest[0] == MP_OBJ_NULL) {
        // Load attribute
        ...
    } else if (dest[1] != MP_OBJ_NULL) {
        // Store attribute
        ...
    }
}
```

For properties, this `dest` protocol is exactly what we need: a getter lives in the load branch, and a setter lives in the store branch.

## Why staticmethod and classmethod use a wrapper struct

MicroPython's member lookup phase understands `staticmethod` and `classmethod` wrappers.
The unwrapping logic lives in `mp_convert_member_lookup` (from `deps/micropython/py/runtime.c`):

```c
} else if (m_type == &mp_type_staticmethod) {
    // `member` is a staticmethod, return the function that it wraps.
    dest[0] = ((mp_obj_static_class_method_t *)MP_OBJ_TO_PTR(member))->fun;
} else if (m_type == &mp_type_classmethod) {
    // `member` is a classmethod, return a bound method with self being the type of
    // this object.
    ...
    dest[0] = ((mp_obj_static_class_method_t *)MP_OBJ_TO_PTR(member))->fun;
    dest[1] = MP_OBJ_FROM_PTR(type);
}
```

So for our generated types, the simplest correct approach is:

1. Emit a normal MicroPython function object for the implementation (for example, `decorators_Rectangle_is_square_dims_fun_obj`).
2. Wrap it in a `mp_rom_obj_static_class_method_t` object whose base type is either `mp_type_staticmethod` or `mp_type_classmethod`.
3. Store the wrapper in `locals_dict` under the attribute name.

From `modules/usermod_decorators/decorators.c`:

```c
static const mp_rom_obj_static_class_method_t decorators_Rectangle_is_square_dims_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&decorators_Rectangle_is_square_dims_fun_obj)
};
static const mp_rom_obj_static_class_method_t decorators_Rectangle_square_obj = {
    {&mp_type_classmethod}, MP_ROM_PTR(&decorators_Rectangle_square_fun_obj)
};
```

## Why properties need special handling in attr (not locals_dict)

If a property lived only in `locals_dict`, MicroPython's lookup would find the property object and return it as a value.
For native types, `mp_convert_member_lookup` unpacks staticmethod/classmethod and binds normal functions, but it does not "execute a property" for you.

That is why we emit property dispatch directly into the generated `attr` handler.

# Part 3: Implementation

## Running example (`examples/decorators.py`)

```python
"""Demonstrate @property, @staticmethod, and @classmethod decorators."""


class Rectangle:
    """A rectangle with computed properties and utility methods."""

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
        """Create a square rectangle."""
        return cls


class Temperature:
    """Temperature with read-write property."""

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
    """Counter with static utility and property."""

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

## IR dump (actual command output)

Command run:

```bash
mpy-compile examples/decorators.py --dump-ir text
```

Output:

```text
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

The class-level IR keeps decorator intent as flags on `MethodIR` and as a `properties` mapping on `ClassIR`.

## IR trees for each decorator type (actual command output)

### @staticmethod (`Rectangle.is_square_dims`)

Command run:

```bash
mpy-compile examples/decorators.py --dump-ir tree --ir-function is_square_dims
```

Output:

```text
`-- root: MethodIR
    |-- name: "is_square_dims"
    |-- c_name: "decorators_Rectangle_is_square_dims"
    |-- params: list[2]
    |   |-- [0]: tuple[2]
    |   `-- [1]: tuple[2]
    |-- return_type: CType.BOOL
    |-- is_virtual: False
    |-- is_static: True
    |-- is_classmethod: False
    |-- is_property: False
    |-- vtable_index: -1
    |-- is_special: False
    |-- docstring: None
    `-- max_temp: 0
```

### @classmethod (`Rectangle.square`)

Command run:

```bash
mpy-compile examples/decorators.py --dump-ir tree --ir-function square
```

Output:

```text
`-- root: MethodIR
    |-- name: "square"
    |-- c_name: "decorators_Rectangle_square"
    |-- params: list[2]
    |   |-- [0]: tuple[2]
    |   `-- [1]: tuple[2]
    |-- return_type: CType.MP_OBJ_T
    |-- is_virtual: False
    |-- is_static: False
    |-- is_classmethod: True
    |-- is_property: False
    |-- vtable_index: -1
    |-- is_special: False
    |-- docstring: "Create a square rectangle."
    `-- max_temp: 0
```

### @property (`Rectangle.area`)

Command run:

```bash
mpy-compile examples/decorators.py --dump-ir tree --ir-function area
```

Output:

```text
`-- root: MethodIR
    |-- name: "area"
    |-- c_name: "decorators_Rectangle_area"
    |-- return_type: CType.MP_INT_T
    |-- is_virtual: False
    |-- is_static: False
    |-- is_classmethod: False
    |-- is_property: True
    |-- vtable_index: -1
    |-- is_special: False
    |-- docstring: None
    `-- max_temp: 0
```

## Three-stage view: Python -> IR -> C

Below, each decorator gets a concrete walkthrough.

## @property: computed attributes with optional setter

### Stage A: Python intent

```python
@property
def area(self) -> int:
    return self.width * self.height

@property
def celsius(self) -> int:
    return self._celsius

@celsius.setter
def celsius(self, value: int) -> None:
    self._celsius = value
```

### Stage B: IR intent

- The getter methods are marked `is_property=True` (see the `MethodIR` trees above).
- `Temperature.celsius` has both a getter and a setter in class IR, so the emitter can generate both load and store logic.

ASCII view of what `ClassIR.properties` represents:

```text
properties:
  area      -> getter=Rectangle.area, setter=None
  perimeter -> getter=Rectangle.perimeter, setter=None
  celsius   -> getter=Temperature.celsius, setter=Temperature.celsius(value)
```

### Stage C: emitted C

The key pattern is:

1. Emit a fast native getter that works with typed fields.
2. In the `attr` handler, call the native getter on load.
3. For setters, call the native setter on store.

From `modules/usermod_decorators/decorators.c`:

```c
static mp_int_t decorators_Rectangle_area_native(decorators_Rectangle_obj_t *self) {
    return (self->width * self->height);
}

static void decorators_Rectangle_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    decorators_Rectangle_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (attr == MP_QSTR_area) {
        if (dest[0] == MP_OBJ_NULL) {
            dest[0] = mp_obj_new_int(decorators_Rectangle_area_native(self));
            return;
        }
        if (dest[1] != MP_OBJ_NULL) {
            dest[1] = MP_OBJ_SENTINEL;
            return;
        }
    }
    ...
    dest[1] = MP_OBJ_SENTINEL;
}
```

And a read-write property example (setter is handled in the store branch):

```c
static void decorators_Temperature_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    decorators_Temperature_obj_t *self = MP_OBJ_TO_PTR(self_in);

    if (attr == MP_QSTR_celsius) {
        if (dest[0] == MP_OBJ_NULL) {
            dest[0] = mp_obj_new_int(decorators_Temperature_celsius_native(self));
            return;
        }
        if (dest[1] != MP_OBJ_NULL) {
            decorators_Temperature_celsius_setter_native(self, mp_obj_get_int(dest[1]));
            dest[0] = MP_OBJ_NULL;
            return;
        }
    }
    ...
}
```

### Step-by-step lowering

#### Property load (`r.area`)

1. IR builder sees `@property` on a method, marks `MethodIR.is_property=True`.
2. IR builder records `ClassIR.properties["area"] = PropertyInfo(getter=..., setter=None)`.
3. Class emitter generates `decorators_Rectangle_attr`.
4. On `MP_QSTR_area` + load (`dest[0] == MP_OBJ_NULL`), C computes the value and writes `dest[0]`.

#### Property store (`t.celsius = 10`)

1. IR builder sees `@celsius.setter` and attaches the setter to the existing `celsius` property.
2. Class emitter generates a store branch in `decorators_Temperature_attr`.
3. On `MP_QSTR_celsius` + store (`dest[1] != MP_OBJ_NULL`), C calls the native setter and signals success by setting `dest[0] = MP_OBJ_NULL`.

## @staticmethod: no binding, still lives in locals_dict

### Stage A: Python intent

```python
@staticmethod
def is_square_dims(w: int, h: int) -> bool:
    return w == h

@staticmethod
def add(a: int, b: int) -> int:
    return a + b
```

### Stage B: IR intent

The `MethodIR` tree shows `is_static: True` for `Rectangle.is_square_dims`.

### Stage C: emitted C

First, the compiler emits a function object for the implementation:

```c
static bool decorators_Rectangle_is_square_dims_native(mp_int_t w, mp_int_t h) {
    return (w == h);
}

static mp_obj_t decorators_Rectangle_is_square_dims_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    mp_int_t w = mp_obj_get_int(arg0_obj);
    mp_int_t h = mp_obj_get_int(arg1_obj);
    return decorators_Rectangle_is_square_dims_native(w, h) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(decorators_Rectangle_is_square_dims_fun_obj, decorators_Rectangle_is_square_dims_mp);
```

Then it wraps it in a `staticmethod` wrapper object and stores it in `locals_dict`:

```c
static const mp_rom_obj_static_class_method_t decorators_Rectangle_is_square_dims_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&decorators_Rectangle_is_square_dims_fun_obj)
};

static const mp_rom_map_elem_t decorators_Rectangle_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_is_square_dims), MP_ROM_PTR(&decorators_Rectangle_is_square_dims_obj) },
    ...
};
```

ASCII dispatch diagram:

```text
Rectangle.is_square_dims
  -> type->attr runs first
     -> not a property, so it sets dest[1] = MP_OBJ_SENTINEL
  -> locals_dict lookup finds a staticmethod wrapper object
  -> mp_convert_member_lookup sees mp_type_staticmethod
     -> returns the wrapped function without binding self
```

### Step-by-step lowering

1. IR builder marks `MethodIR.is_static=True`.
2. Emitter generates an `_mp` wrapper with no `self_in` parameter.
3. Emitter emits a `mp_rom_obj_static_class_method_t` wrapper with base `&mp_type_staticmethod`.
4. Wrapper goes into `locals_dict` so `mp_convert_member_lookup` can unwrap it.

## @classmethod: bind the type as the first argument

### Stage A: Python intent

```python
@classmethod
def square(cls, size: int) -> object:
    return cls
```

### Stage B: IR intent

The `MethodIR` tree shows `is_classmethod: True` for `Rectangle.square`.

### Stage C: emitted C

The implementation is a normal function object, and the wrapper is of type `classmethod`:

```c
static mp_obj_t decorators_Rectangle_square_native(mp_obj_t cls, mp_int_t size) {
    return cls;
}

static mp_obj_t decorators_Rectangle_square_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    mp_obj_t cls = arg0_obj;
    mp_int_t size = mp_obj_get_int(arg1_obj);
    return decorators_Rectangle_square_native(cls, size);
}
MP_DEFINE_CONST_FUN_OBJ_2(decorators_Rectangle_square_fun_obj, decorators_Rectangle_square_mp);

static const mp_rom_obj_static_class_method_t decorators_Rectangle_square_obj = {
    {&mp_type_classmethod}, MP_ROM_PTR(&decorators_Rectangle_square_fun_obj)
};
```

ASCII dispatch diagram:

```text
Rectangle.square
  -> locals_dict lookup finds a classmethod wrapper object
  -> mp_convert_member_lookup sees mp_type_classmethod
     -> dest[0] = wrapped function
     -> dest[1] = the type object (bound as the first argument)
```

This is why `@classmethod` composes cleanly with our C ABI: the runtime hands us the class object in `arg0_obj`.

### Step-by-step lowering

1. IR builder marks `MethodIR.is_classmethod=True`.
2. Emitter generates an `_mp` wrapper that expects `cls` as the first argument.
3. Emitter emits a `mp_rom_obj_static_class_method_t` wrapper with base `&mp_type_classmethod`.
4. Wrapper goes into `locals_dict`, and MicroPython binds the type during lookup.

# Key Design Decisions

## Why properties go in the attr handler (not locals_dict)

MicroPython only falls back to `locals_dict` after `type->attr`, and only if `attr` signals fallback via `dest[1] = MP_OBJ_SENTINEL`.
More importantly, `mp_convert_member_lookup` explicitly handles `staticmethod` and `classmethod`, but it does not execute property getters or setters for native types.

So for `@property`, the only place we can reliably implement "load runs getter" and "store runs setter" is the generated `attr` handler.

## Why staticmethod and classmethod use mp_rom_obj_static_class_method_t

MicroPython already has member-lookup support for `mp_type_staticmethod` and `mp_type_classmethod`.
Wrapping our function objects in `mp_rom_obj_static_class_method_t` makes them look like the built-in decorator results, so `mp_convert_member_lookup` does the right thing.

## Why properties are excluded from the vtable

The vtable is for virtual method dispatch (`self->vtable->method(...)`).
A property access is not a method call in Python syntax, and in our generated code it becomes an attribute operation handled by `type->attr`.

You can see this separation directly in the generated C:

- `decorators_Rectangle_vtable_t` contains `scale`, but it does not contain `area` or `perimeter`.
- `area` and `perimeter` are handled by `decorators_Rectangle_attr` via `MP_QSTR_area` and `MP_QSTR_perimeter`.

# Device Testing

The compiler's roadmap documents the current device-test status for the ESP32-C6 integration.
From `docs/05-roadmap.md`:

```text
- **ESP32**: All 17 compiled modules verified on real ESP32-C6 hardware (262 device tests pass)
```

To run the same device suite locally (ESP32-C6 example from this repo's build docs):

```bash
make compile-all
make build BOARD=ESP32_GENERIC_C6
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101
make run-device-tests PORT=/dev/cu.usbmodem2101
```

# Part 5: Future Improvements

## Near-Term Enhancements

1. **@classmethod with constructor calls**: The current `@classmethod` implementation passes `cls` as a raw `mp_obj_t`, but does not support calling `cls(...)` to construct a new instance. Supporting `return cls(size, size)` inside a classmethod would require emitting a `mp_call_function_n_kw()` call on `cls`. This is the most obvious gap -- the `Rectangle.square(5)` example currently returns the class itself rather than a new Rectangle.

2. **Cached property**: A `@cached_property` pattern (compute once, store result on the instance) could be supported by writing the getter result back into a field during the first access. This would require a sentinel value to detect the uninitialized state.

3. **Property with delete**: Python properties support `@prop.deleter` for `del obj.prop`. The `attr` handler already receives a signal for deletion (`dest[0] != MP_OBJ_NULL` and `dest[1] == MP_OBJ_NULL`), so adding deleter support is a matter of detecting the decorator and emitting the third dispatch branch.

## Language Coverage

4. **Stacked decorators**: Currently only a single decorator per method is recognized. Patterns like `@staticmethod` combined with custom decorators (or even `@property` combined with `@abstractmethod`) are not handled. Supporting stacked decorators requires processing the decorator list in reverse order, matching Python's application semantics.

5. **Computed properties returning object types**: Properties that return `list`, `dict`, or other class instances currently box the return value through `mp_obj_t`. When the return type is known (e.g., `-> list`), the getter could skip boxing if the value is already an `mp_obj_t` field.

6. **@property on inherited classes**: A child class that overrides a parent's property getter or adds a setter to a read-only parent property would require the child's `attr` handler to check for the property before falling through to the parent's handler. This is not yet implemented.

## Performance Optimizations

7. **Inlined property access**: For simple field-returning properties like `@property def count(self) -> int: return self._count`, the compiler could inline the field read directly into the `attr` handler instead of calling a native function. This eliminates one function call per property access.

8. **Static method devirtualization**: When a static method is called on a known type (e.g., `Rectangle.is_square_dims(3, 4)` where `Rectangle` is resolved at compile time), the compiler could emit a direct C call bypassing `locals_dict` lookup entirely.

9. **Property type specialization**: Properties with `int` or `bool` return types already emit type-aware boxing (`mp_obj_new_int`). Extending this to emit unboxed native returns when the caller is also in compiled code (intra-module calls) would eliminate boxing overhead on the hot path.

---

# Closing

`@staticmethod` and `@classmethod` are a good example of "let the runtime do what it already knows": we emit wrapper objects that MicroPython already understands.
`@property` goes the other way: we must implement descriptor-like behavior ourselves, because for native types the runtime does not automatically run property dispatch during member lookup.

The result is decorator behavior that fits MicroPython's lookup model, stays close to the generated C type representation, and keeps property access on a fast path (native getter/setter invoked directly from `type->attr`).
