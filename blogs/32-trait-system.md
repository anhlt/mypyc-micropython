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

Here's what this looks like in memory. Notice the critical difference at offset 8:

```
MEMORY LAYOUT: WHY TRAIT CASTING FAILS

Entity_obj_t:                    Named_obj_t (trait):
+---------------------+ 0        +---------------------+ 0
| base (8 bytes)      |          | base (8 bytes)      |
+---------------------+ 8        +---------------------+ 8
| id (8 bytes)        |          | vtable* (8 bytes)   |   <-- DIFFERENT!
+---------------------+ 16       +---------------------+ 16
                                 | name (8 bytes)      |
                                 +---------------------+ 24

Person_obj_t (Entity + Named):
+---------------------+ 0
| super.base (8)      |          Can cast to Entity* at offset 0
+---------------------+ 8
| super.id (8)        |          Entity fields at same offset - SAFE
+---------------------+ 16
| name (8 bytes)      |          Named expects name at 16 - MATCH!
+---------------------+ 24       BUT Named expects vtable* at offset 8,
| age (8 bytes)       |          Person has super.id there - MISMATCH!
+---------------------+ 32
```

The problem is subtle: even though `name` happens to be at offset 16 in both `Named_obj_t` and after Entity's fields in `Person_obj_t`, the **vtable pointer** is in a different place. Named expects `vtable*` at offset 8, but Person has `id` there.

If we cast `Person*` to `Named*` and call a trait method that accesses `self->vtable`, it reads `id` instead of the vtable pointer - causing crashes or undefined behavior.

### Inside vs Outside: Two Different Problems

The struct layout incompatibility manifests in two different ways:

```
TWO TRAIT ACCESS PATTERNS

1. INSIDE CALL: trait method accessing self.field
   ================================================
   
   @trait
   class Named:
       name: str
       def get_name(self) -> str:
           return self.name       # <-- self is what type?
   
   class Person(Entity, Named):   # Person implements Named
       ...
   
   p = Person(1, "Alice", 30)
   p.get_name()                   # <-- self is Person, not Named!
   
   Problem: get_name() body expects Named_obj_t* but gets Person_obj_t*
   Solution: Generate WRAPPER function with correct Person_obj_t* type


2. OUTSIDE CALL: function with trait-typed parameter
   ================================================
   
   def greet(n: Named) -> str:    # n could be ANY Named implementer
       return "Hello " + n.name  # <-- which struct layout?
   
   p = Person(1, "Alice", 30)
   e = Employee(2, "Bob", "Sales", 50000)
   greet(p)                       # n.name at offset 16 in Person
   greet(e)                       # n.name at offset 32 in Employee!
   
   Problem: Can't generate direct field access - offset varies by class
   Solution: Use mp_load_attr() for DYNAMIC lookup at runtime
```

**Key insight**: "Inside" and "outside" need different solutions:
- **Inside** (trait method body): We know at compile time which class implements the trait, so we generate class-specific wrappers
- **Outside** (trait-typed param): We don't know at compile time which class will be passed, so we use runtime dynamic dispatch

If we call `traits_Named_get_name_native` with a `Person` object, `self->name` reads from offset 16, which is actually the `id` field!

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

The wrapper knows that for `Person`, the `name` field is at offset 24:

```
WRAPPER SOLUTION

Original trait method:                  Generated wrapper for Person:

traits_Named_get_name_native(self)      traits_Person_get_name_from_Named_native(self)
|                                        |
| self is traits_Named_obj_t *           | self is traits_Person_obj_t *
| reads self->name at offset 16          | reads self->name at offset 24
|                                        |
v                                        v
+---------------------------+            +---------------------------+
| Offset 16: ??? (WRONG!)   |            | Offset 24: name (CORRECT) |
+---------------------------+            +---------------------------+
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

Here's the memory layout showing struct embedding:

```
SINGLE INHERITANCE: STRUCT EMBEDDING

Entity_obj_t:                           Person_obj_t:

+---------------------------+           +---------------------------+
| mp_obj_base_t base        |           | Entity_obj_t super:       |
| (8 bytes)                 |           |   +---------------------+ |
+---------------------------+           |   | mp_obj_base_t base  | |
| Entity_vtable_t *vtable   |           |   | (8 bytes)           | |
| (8 bytes)                 |           |   +---------------------+ |
+---------------------------+    ====   |   | vtable ptr          | |
| mp_int_t id               |    SAME   |   | (8 bytes)           | |
| (8 bytes)                 |    ====   |   +---------------------+ |
+---------------------------+           |   | mp_int_t id         | |
                                        |   | (8 bytes)           | |
                                        |   +---------------------+ |
                                        +---------------------------+
                                        | mp_obj_t name             |
                                        | (8 bytes)                 |
                                        +---------------------------+
                                        | mp_int_t age              |
                                        | (8 bytes)                 |
                                        +---------------------------+

A Person_obj_t* can be cast to Entity_obj_t* because the
first 24 bytes have identical layout.
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

Here's the complete picture of how a method call flows:

```
METHOD CALL FLOW: person.get_name()

Python call: person.get_name()
                |
                v
+----------------------------------+
| MicroPython Runtime              |
| 1. Look up 'get_name' in type    |
| 2. Find Person_get_name_obj      |
+----------------------------------+
                |
                v
+----------------------------------+
| Person_get_name_mp(self_in)      |  <-- MP wrapper
| {                                |
|   Person_obj_t *self =           |
|     MP_OBJ_TO_PTR(self_in);      |      Unbox: mp_obj_t -> typed ptr
|   return Person_get_name_native( |
|     self);                       |
| }                                |
+----------------------------------+
                |
                v
+----------------------------------+
| Person_get_name_native(self)     |  <-- Native function
| {                                |
|   return self->name;             |      Direct field access at offset 24
| }                                |
+----------------------------------+
                |
                v
           mp_obj_t (the name string)
```

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

### Step 7: Trait-Typed Parameters and Dynamic Attribute Lookup

There's another layout challenge: what happens when a function parameter is typed as a trait?

```python
def greet_named(n: Named) -> str:
    return "Hello, " + n.name  # n could be Person, Pet, or any Named implementer
```

The parameter `n` could be ANY class that implements `Named`. At compile time, we don't know which specific struct layout `n` will have. We can't generate `self->name` because the offset differs for each class:

```
TRAIT-TYPED PARAMETER PROBLEM

Function: greet_named(n: Named)

n could be:                               Field offset for 'name':

  Person_obj_t                            offset 24
  Pet_obj_t                               offset 24 (same, by coincidence)
  Employee_obj_t                          offset 32 (different base class)
  Document_obj_t                          offset 16 (no base class)

We CANNOT generate: ((Named_obj_t*)n)->name
Because Named_obj_t layout doesn't match any of these!
```

The solution is **dynamic attribute lookup** using MicroPython's runtime: `mp_load_attr(obj, MP_QSTR_name)`.

#### How mp_load_attr Works Internally

When we call `mp_load_attr(obj, MP_QSTR_name)`, MicroPython performs these steps:

```
mp_load_attr(obj, MP_QSTR_name) EXECUTION FLOW

Step 1: Get object's actual type
+----------------------------------+
| const mp_obj_type_t *type =      |
|     mp_obj_get_type(obj);        |
|                                  |
| If obj is Person: type = &traits_Person_type
| If obj is Pet:    type = &traits_Pet_type
+----------------------------------+
              |
              v
Step 2: Look up the attr handler
+----------------------------------+
| mp_attr_fun_t attr_fun =         |
|     type->ext[0].attr;           |
|                                  |
| Points to OUR generated handler: |
|   traits_Person_attr  or         |
|   traits_Pet_attr                |
+----------------------------------+
              |
              v
Step 3: Call the attr handler
+----------------------------------+
| mp_obj_t dest[2] = {MP_OBJ_NULL};|
| attr_fun(obj, MP_QSTR_name, dest);|
|                                  |
| dest[0] now contains the value   |
+----------------------------------+
              |
              v
         Return dest[0]
```

#### Generated attr Handler Per Class

Each class has its own `attr` handler that knows its exact struct layout:

```c
// Person's attr handler - knows name is at offset 24
static void traits_Person_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    traits_Person_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (dest[0] == MP_OBJ_NULL) {  // Load attribute
        if (attr == MP_QSTR_id) { dest[0] = mp_obj_new_int(self->id); return; }
        if (attr == MP_QSTR_name) { dest[0] = self->name; return; }  // offset 24
        if (attr == MP_QSTR_age) { dest[0] = mp_obj_new_int(self->age); return; }
    } else if (dest[1] != MP_OBJ_NULL) {  // Store attribute
        if (attr == MP_QSTR_name) { self->name = dest[1]; dest[0] = MP_OBJ_NULL; return; }
        // ... other fields
    }
    // Fall through to locals_dict for methods
}

// Employee's attr handler - knows name is at offset 32
static void traits_Employee_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    traits_Employee_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (dest[0] == MP_OBJ_NULL) {  // Load attribute
        if (attr == MP_QSTR_id) { dest[0] = mp_obj_new_int(self->id); return; }
        if (attr == MP_QSTR_dept) { dest[0] = self->dept; return; }
        if (attr == MP_QSTR_name) { dest[0] = self->name; return; }  // offset 32!
        if (attr == MP_QSTR_salary) { dest[0] = mp_obj_new_int(self->salary); return; }
    }
    // ...
}
```

#### The Magic: Polymorphism via Dynamic Dispatch

```
DYNAMIC DISPATCH FOR TRAIT PARAMETERS

Python code:                         Generated C code:

def greet_named(n: Named) -> str:    static mp_obj_t greet_named(mp_obj_t n) {
    return "Hello, " + n.name           mp_obj_t name = mp_load_attr(n, MP_QSTR_name);
                                         // ... string concat ...
                                     }

At runtime with Person:              At runtime with Employee:

mp_load_attr(person, QSTR_name)      mp_load_attr(employee, QSTR_name)
        |                                    |
        v                                    v
mp_obj_get_type(person)              mp_obj_get_type(employee)
= &traits_Person_type                = &traits_Employee_type
        |                                    |
        v                                    v
type->ext[0].attr                    type->ext[0].attr
= traits_Person_attr                 = traits_Employee_attr
        |                                    |
        v                                    v
self->name at offset 24              self->name at offset 32
        |                                    |
        v                                    v
    "Alice"                              "Bob"
```

The SAME generated code (`mp_load_attr(n, MP_QSTR_name)`) works for ANY object that has a `name` attribute, regardless of where that field sits in memory. Each class's attr handler knows its own layout.

#### IR Tracking: is_trait_type Flag

To detect when to use `mp_load_attr` vs direct field access, we track trait-typed parameters in the IR:

```python
@dataclass
class ParamAttrIR(ExprIR):
    param_name: str
    attr_name: str
    is_trait_type: bool = False  # True if param is typed as a trait
```

During IR building, we check if the parameter's type annotation refers to a trait:

```python
def _build_param_attr(self, param_name: str, attr_name: str) -> ParamAttrIR:
    is_trait = False
    if param_name in self.param_types:
        type_name = self.param_types[param_name]
        if type_name in self.classes and self.classes[type_name].is_trait:
            is_trait = True
    return ParamAttrIR(param_name=param_name, attr_name=attr_name, is_trait_type=is_trait)
```

#### Code Generation for Trait-Typed Parameters

The emitter checks `is_trait_type` and generates appropriate code:

```python
def _emit_param_attr(self, ir: ParamAttrIR) -> str:
    if ir.is_trait_type:
        # Dynamic lookup - param could be any implementing class
        return f"mp_load_attr({ir.param_name}, MP_QSTR_{ir.attr_name})"
    else:
        # Direct field access - we know the exact struct layout
        return f"{ir.param_name}->{ir.attr_name}"
```

#### Two Approaches to the Same Problem

We now have two complementary solutions for trait struct layout incompatibility:

```
TRAIT LAYOUT SOLUTIONS

+----------------------------+----------------------------+
| SELF ACCESS (in methods)   | PARAM ACCESS (trait-typed) |
+----------------------------+----------------------------+
| Problem: Trait method body | Problem: Function param is |
| uses self.field, but self  | typed as trait, could be   |
| is actually implementing   | any implementing class     |
| class with different layout|                            |
+----------------------------+----------------------------+
| Solution: Generate wrapper | Solution: Use mp_load_attr |
| function per implementing  | for dynamic lookup at      |
| class with correct struct  | runtime                    |
| type                       |                            |
+----------------------------+----------------------------+
| When: Compile-time known   | When: Runtime polymorphism |
| (class inherits trait)     | (any Named implementer)    |
+----------------------------+----------------------------+
| Cost: Code size (one       | Cost: Runtime overhead     |
| wrapper per class)         | (attr lookup vs direct)    |
+----------------------------+----------------------------+
```

Both solutions handle the fundamental problem that traits don't have a fixed struct layout.
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


## Closing

The trait system enables mypyc-style multiple inheritance in compiled MicroPython code:

1. **One concrete base**: Preserves struct embedding and safe pointer casting
2. **Multiple traits**: Mix in behavior without layout conflicts
3. **Trait method wrappers**: Bridge the struct layout gap between traits and implementing classes

The key insight is that traits define behavior contracts, but the implementing class owns the memory layout. By generating wrappers that know the correct field offsets, we can reuse trait method logic while keeping memory access correct.

This approach matches mypyc's semantics, so code written for mypyc's trait system compiles correctly to MicroPython native modules.
