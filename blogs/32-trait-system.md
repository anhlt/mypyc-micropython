# 32. Trait System: Multiple Inheritance with Interface-Like Classes

This post covers the implementation of a trait system for `mypyc-micropython`, following mypyc's approach to restricted multiple inheritance. In Python, you can inherit from any number of classes. In compiled code targeting microcontrollers, that flexibility becomes a memory layout nightmare. Traits are the compromise: you get one concrete base class, but you can mix in any number of interface-like classes that define additional behavior.

## Table of Contents

- [Part 1: Compiler Theory](#part-1-compiler-theory)
- [Part 2: C Background](#part-2-c-background)
- [Part 3: Implementation](#part-3-implementation)
- [Device Testing](#device-testing)
- [Closing](#closing)

## Part 1: Compiler Theory

### The Problem with Traditional Multiple Inheritance

Consider this Python code:

```python
class A:
    x: int = 1

class B:
    y: int = 2

class C(A, B):
    z: int = 3
```

In Python, `C` has fields from both `A` and `B`. The runtime handles this with a method resolution order (MRO) and dictionary-based attribute lookup. But in compiled C code, we need concrete struct layouts:

```c
// Where does y go in C's struct?
struct C_obj_t {
    mp_obj_base_t base;
    mp_int_t x;  // from A
    mp_int_t y;  // from B - but what offset?
    mp_int_t z;  // own field
};
```

The problem is that `A` and `B` both expect their fields at specific offsets. If `A.x` is at offset 8, then `A`'s methods assume `self->x` is at offset 8. But in `C`, we might put `x` at offset 8 and `y` at offset 16. Now `B`'s methods break because they expect `y` at offset 8 (where `y` would be in a standalone `B` object).

This is the **diamond problem** and **struct layout incompatibility** that makes traditional multiple inheritance hard to compile.

### mypyc's Solution: Traits

mypyc solves this with a restricted form of multiple inheritance:

1. **One concrete base class**: You can only inherit implementation from one "real" class
2. **Multiple traits**: You can inherit from any number of traits (interface-like classes)
3. **Traits cannot be instantiated**: They define behavior but have no standalone objects

```python
from mypy_extensions import trait

@trait
class Named:
    name: str
    
    def get_name(self) -> str:
        return self.name

@trait
class Describable:
    def describe(self) -> str:
        return "An object"

class Entity:  # Concrete base
    id: int
    
    def __init__(self, id: int) -> None:
        self.id = id

class Person(Entity, Named, Describable):  # One concrete + multiple traits
    age: int
    
    def __init__(self, id: int, name: str, age: int) -> None:
        self.id = id
        self.name = name
        self.age = age
```

The key insight is that traits don't define a concrete struct layout. The implementing class (`Person`) defines where all fields go, including fields from traits.

### The Struct Layout Challenge

Here's where it gets tricky. The `Named` trait has a method `get_name()` with body `return self.name`. When we compile the trait, we generate:

```c
static mp_obj_t traits_Named_get_name_native(traits_Named_obj_t *self) {
    return self->name;
}
```

This function expects `self` to be a `traits_Named_obj_t *`. But when `Person` uses this method, `self` is actually a `traits_Person_obj_t *`, which has a different layout:

```c
// Named's expected layout
struct traits_Named_obj_t {
    mp_obj_base_t base;
    const traits_Named_vtable_t *vtable;
    mp_obj_t name;  // at offset 16
};

// Person's actual layout
struct traits_Person_obj_t {
    traits_Entity_obj_t super;  // base + vtable + id
    mp_obj_t name;              // at offset 24 (different!)
    mp_int_t age;
};
```

If we call `traits_Named_get_name_native` with a `Person` object, `self->name` reads from the wrong memory location.

### The Solution: Trait Method Wrappers

For each trait method that a class inherits (but doesn't override), we generate a wrapper function that knows the correct field offset in the implementing class:

```c
// Wrapper for Person implementing Named.get_name
static mp_obj_t traits_Person_get_name_from_traits_Named_native(
    traits_Person_obj_t *self
) {
    return self->name;  // Correct offset for Person's layout
}
```

This wrapper has the right struct type and accesses the field at the correct offset.

### IR Representation

In our intermediate representation, we track traits explicitly:

```text
Module: traits (c_name: traits)

Classes:
  Class: Named (c_name: traits_Named)
    @trait
    Methods:
      def get_name() -> MP_OBJ_T

  Class: Describable (c_name: traits_Describable)
    @trait
    Methods:
      def describe() -> MP_OBJ_T

  Class: Entity (c_name: traits_Entity)
    Methods:
      def __init__(id: MP_INT_T) -> VOID
      def get_id() -> MP_INT_T

  Class: Person (c_name: traits_Person)
    Base: Entity
    Traits: Named, Describable
    Methods:
      def __init__(id: MP_INT_T, name: MP_OBJ_T, age: MP_INT_T) -> VOID
      def describe() -> MP_OBJ_T
      def greet() -> MP_OBJ_T
```

Notice that `Person`:
- Has `Base: Entity` (one concrete base)
- Has `Traits: Named, Describable` (multiple traits)
- Defines its own `describe()` (overrides trait method)
- Doesn't define `get_name()` (inherits from trait)

## Part 2: C Background

### Struct Embedding and Pointer Casting

In C, we implement single inheritance by embedding the parent struct at the beginning of the child struct:

```c
struct Entity_obj_t {
    mp_obj_base_t base;
    const Entity_vtable_t *vtable;
    mp_int_t id;
};

struct Person_obj_t {
    Entity_obj_t super;  // Parent embedded at start
    mp_obj_t name;
    mp_int_t age;
};
```

This means a `Person_obj_t *` can be safely cast to `Entity_obj_t *` because they share the same prefix layout. But traits don't work this way - a `Person_obj_t *` cannot be cast to `Named_obj_t *` because their layouts are incompatible.

### Function Pointer Types in Vtables

Vtables store function pointers. Each function pointer has a specific type that includes the parameter types:

```c
typedef struct {
    mp_obj_t (*get_name)(Named_obj_t *self);
} Named_vtable_t;

typedef struct {
    mp_obj_t (*get_name)(Person_obj_t *self);  // Different type!
} Person_Named_vtable_t;
```

Even though both functions "do the same thing," their C types are different because the `self` parameter has a different type. This is why we can't just reuse the trait's function pointer in the implementing class's vtable.

### The MP Function Object Pattern

MicroPython methods need two parts:

1. **Native function**: The actual C implementation
2. **MP wrapper**: Converts from MicroPython's calling convention

```c
// Native function with typed self
static mp_obj_t Person_get_name_native(Person_obj_t *self) {
    return self->name;
}

// MP wrapper that unpacks self from mp_obj_t
static mp_obj_t Person_get_name_mp(mp_obj_t self_in) {
    Person_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return Person_get_name_native(self);
}

// Function object for method table
MP_DEFINE_CONST_FUN_OBJ_1(Person_get_name_obj, Person_get_name_mp);
```

The `locals_dict` (Python's method table) references `Person_get_name_obj`, not the native function directly.

## Part 3: Implementation

### Step 1: Detecting Traits in IR Building

We detect the `@trait` decorator during IR building:

```python
def _check_is_trait(self, node: ast.ClassDef) -> bool:
    """Check if class is decorated with @trait from mypy_extensions."""
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "trait":
            return True
        if isinstance(decorator, ast.Attribute):
            if decorator.attr == "trait":
                return True
    return False
```

### Step 2: Separating Concrete Base from Traits

When processing inheritance, we separate the concrete base from traits:

```python
def _process_bases(self, node: ast.ClassDef, class_ir: ClassIR) -> None:
    concrete_base = None
    traits = []
    
    for base in node.bases:
        base_name = self._get_base_name(base)
        if base_name in self.classes:
            base_ir = self.classes[base_name]
            if base_ir.is_trait:
                traits.append(base_ir)
            elif concrete_base is None:
                concrete_base = base_ir
            else:
                # Error: multiple concrete bases
                pass
    
    class_ir.base = concrete_base
    class_ir.traits = traits
```

### Step 3: Including Trait Fields in Struct

Trait fields must be included in the implementing class's struct:

```python
def get_all_fields(self) -> list[FieldIR]:
    """Get all fields including from traits."""
    fields = []
    if self.base:
        fields.extend(self.base.get_all_fields())
    # Include fields from traits
    for trait in self.traits:
        for field in trait.fields:
            if not any(f.name == field.name for f in fields):
                fields.append(field)
    fields.extend(self.fields)
    return fields
```

### Step 4: Generating Trait Method Wrappers

This is the key fix. For each inherited trait method, we generate a wrapper:

```python
def emit_trait_method_wrappers(self) -> list[str]:
    lines = []
    
    for trait in self.class_ir.get_all_traits():
        for method_name, trait_method in trait.get_all_methods().items():
            # Skip if this class overrides the method
            if self._get_own_or_base_method(method_name):
                continue
            
            wrapper_name = f"{self.c_name}_{method_name}_from_{trait.c_name}"
            
            # Check AST for simple pattern: return self.field
            body = trait_method.body_ast.body
            if len(body) == 1 and isinstance(body[0], ast.Return):
                ret_val = body[0].value
                if isinstance(ret_val, ast.Attribute):
                    if ret_val.value.id == "self":
                        field_name = ret_val.attr
                        lines.append(f"static mp_obj_t {wrapper_name}_native("
                                   f"{self.c_name}_obj_t *self) {{")
                        lines.append(f"    return self->{field_name};")
                        lines.append("}")
            
            # Also generate MP wrapper
            lines.append(f"static mp_obj_t {wrapper_name}_mp(mp_obj_t self_in) {{")
            lines.append(f"    {self.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
            lines.append(f"    return {wrapper_name}_native(self);")
            lines.append("}")
            lines.append(f"MP_DEFINE_CONST_FUN_OBJ_1({wrapper_name}_obj, "
                        f"{wrapper_name}_mp);")
    
    return lines
```

### Step 5: Using Wrappers in Locals Dict

The `locals_dict` must reference the wrapper, not the original trait method:

```python
def emit_locals_dict(self) -> list[str]:
    for name in method_names:
        own_method = self._get_own_or_base_method(name)
        if own_method is not None:
            # Method from this class or base - use normal obj
            lines.append(f"    {{ MP_ROM_QSTR(MP_QSTR_{name}), "
                        f"MP_ROM_PTR(&{method.c_name}_obj) }},")
        else:
            # Method from trait - use wrapper
            for trait in self.class_ir.get_all_traits():
                if name in trait.get_all_methods():
                    wrapper = f"{self.c_name}_{name}_from_{trait.c_name}_obj"
                    lines.append(f"    {{ MP_ROM_QSTR(MP_QSTR_{name}), "
                                f"MP_ROM_PTR(&{wrapper}) }},")
                    break
```

### Step 6: Skipping make_new for Traits

Traits cannot be instantiated:

```python
def emit_type_definition(self) -> list[str]:
    slots = []
    
    # Traits can't be instantiated - don't add make_new slot
    if not self.class_ir.is_trait:
        slots.append(f"    make_new, {self.c_name}_make_new")
```

### Generated C Code

For our `Person` class with `Named` trait, we generate:

```c
// Wrapper for trait Named.get_name
static mp_obj_t traits_Person_get_name_from_traits_Named_native(
    traits_Person_obj_t *self
) {
    return self->name;  // Correct offset for Person
}

static mp_obj_t traits_Person_get_name_from_traits_Named_mp(mp_obj_t self_in) {
    traits_Person_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return traits_Person_get_name_from_traits_Named_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(
    traits_Person_get_name_from_traits_Named_obj,
    traits_Person_get_name_from_traits_Named_mp
);

// Locals dict uses the wrapper
static const mp_rom_map_elem_t traits_Person_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get_id), MP_ROM_PTR(&traits_Entity_get_id_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_name), 
      MP_ROM_PTR(&traits_Person_get_name_from_traits_Named_obj) },  // Wrapper!
    { MP_ROM_QSTR(MP_QSTR_describe), MP_ROM_PTR(&traits_Person_describe_obj) },
    { MP_ROM_QSTR(MP_QSTR_greet), MP_ROM_PTR(&traits_Person_greet_obj) },
};
```

## Device Testing

The trait system was verified on an ESP32-C6 device:

```
@S:traits
  OK: Person id
  OK: Person name      # Trait method works!
  OK: Person age
  OK: Pet id
  OK: Pet name         # Same trait, different class
  OK: Document title
  OK: Document body
@D:375|375|0
ALL 375 TESTS PASSED
```

The C runtime test verifies the struct layout is correct:

```c
def test_c_trait_with_multiple_inheritance(compile_and_run):
    source = '''
from mypy_extensions import trait

@trait
class Named:
    name: str
    def get_name(self) -> str:
        return self.name

class Entity:
    id: int
    def __init__(self, id: int) -> None:
        self.id = id

class Person(Entity, Named):
    age: int
    def __init__(self, id: int, name: str, age: int) -> None:
        self.id = id
        self.name = name
        self.age = age
'''
    # Test that get_name reads from correct offset
    test_main_c = '''
    mp_obj_t name = test_Person_get_name_from_test_Named_native(p);
    printf("name=%s\\n", mp_obj_str_get_str(name));
    '''
    
    stdout = compile_and_run(source, "test", test_main_c)
    assert "name=Alice" in stdout  # Correct field access!
```

## Closing

The trait system enables mypyc-style multiple inheritance in compiled MicroPython code:

1. **One concrete base**: Preserves struct embedding and safe pointer casting
2. **Multiple traits**: Mix in behavior without layout conflicts
3. **Trait method wrappers**: Bridge the struct layout gap between traits and implementing classes

The key insight is that traits define behavior contracts, but the implementing class owns the memory layout. By generating wrappers that know the correct field offsets, we can reuse trait method logic while keeping memory access correct.

This approach matches mypyc's semantics, so code written for mypyc's trait system compiles correctly to MicroPython native modules.
