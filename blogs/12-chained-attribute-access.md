# Chained Attribute Access: Navigating Nested Class Structures

*Enabling `rect.top_left.x` — accessing attributes through multiple levels of class composition.*

---

When you write `rect.bottom_right.x` in Python, you're traversing a chain of objects: `rect` contains a `bottom_right` which contains an `x`. This post explores how we implemented support for chained attribute access on nested class types, enabling natural object-oriented patterns in compiled code.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) — How nested attribute access flows through compilation
2. [C Background](#part-2-c-background-for-python-developers) — Pointer chains, struct composition, and nested access
3. [Implementation](#part-3-implementation) — The recursive solution for arbitrary depth

---

# Part 1: Compiler Theory

## The Nested Access Problem

Consider this common object-oriented pattern:

```python
@dataclass
class Point:
    x: int
    y: int

@dataclass
class Rectangle:
    top_left: Point
    bottom_right: Point

def get_width(rect: Rectangle) -> int:
    return rect.bottom_right.x - rect.top_left.x
```

The expression `rect.bottom_right.x` involves two attribute accesses:
1. `rect.bottom_right` → returns a `Point` object
2. `.x` on that `Point` → returns an `int`

## AST Structure for Chained Access

Python's AST represents `rect.bottom_right.x` as nested `Attribute` nodes:

```
Attribute(
    value=Attribute(
        value=Name(id='rect'),
        attr='bottom_right'
    ),
    attr='x'
)
```

The outer `Attribute` has another `Attribute` as its `value`, not a simple `Name`. This nesting can continue to arbitrary depth.

## The Original Limitation

Our initial `_build_attribute` only handled single-level access:

```python
def _build_attribute(self, expr: ast.Attribute, locals_):
    if not isinstance(expr.value, ast.Name):  # Only handles Name!
        return ConstIR(ir_type=IRType.OBJ, value=None), []
    # ... handle param.attr
```

When `expr.value` was another `Attribute`, we returned `None` — breaking chained access.

## The Recursive Insight

The solution is recursive: to access `a.b.c`:
1. First build `a.b` (which might itself be chained)
2. Then access `.c` on the result

Each level produces:
- A **value** (temp variable holding the intermediate object)
- A **prelude** (instructions to compute that value)

The preludes accumulate as we descend the chain.

## Type Tracking Across the Chain

The key challenge: after accessing `rect.bottom_right`, how do we know the result is a `Point`?

We need to track **field types**. When `Rectangle` declares `bottom_right: Point`, we record that accessing `bottom_right` on a `Rectangle` returns a `Point`. This lets us generate the correct cast for the next level.

---

# Part 2: C Background for Python Developers

## Struct Composition

In C, structs can contain other structs (or pointers to them):

```c
typedef struct {
    int x;
    int y;
} Point;

typedef struct {
    Point *top_left;      // Pointer to Point
    Point *bottom_right;  // Pointer to Point
} Rectangle;
```

In MicroPython, class fields are stored as `mp_obj_t` (pointers):

```c
typedef struct {
    mp_obj_base_t base;
    mp_obj_t top_left;      // Points to a Point object
    mp_obj_t bottom_right;  // Points to a Point object
} Rectangle_obj_t;
```

## Chained Pointer Access

To access `rect->bottom_right->x` in C:

```c
Rectangle_obj_t *rect = ...;

// Step 1: Get bottom_right (returns mp_obj_t)
mp_obj_t br = rect->bottom_right;

// Step 2: Cast to Point and access x
Point_obj_t *br_point = (Point_obj_t *)MP_OBJ_TO_PTR(br);
int x = br_point->x;
```

Each level requires:
1. Access the field (returns `mp_obj_t`)
2. Cast to the concrete type
3. Access the next field

## Visual: Memory Layout

```
rect (Rectangle_obj_t*)
  |
  v
+------------------+
| base (type info) |
| top_left --------|-------> +------------------+
| bottom_right ----|---+     | base (type info) |
+------------------+   |     | x: 0             |
                       |     | y: 0             |
                       |     +------------------+
                       |       (Point_obj_t)
                       |
                       +---> +------------------+
                             | base (type info) |
                             | x: 100           |
                             | y: 50            |
                             +------------------+
                               (Point_obj_t)
```

## The Cast Chain Pattern

For `rect.bottom_right.x`, we generate:

```c
// Access bottom_right on Rectangle
mp_obj_t _tmp1 = ((Rectangle_obj_t *)MP_OBJ_TO_PTR(rect))->bottom_right;

// Access x on Point
mp_int_t _tmp2 = ((Point_obj_t *)MP_OBJ_TO_PTR(_tmp1))->x;
```

Each level:
1. `MP_OBJ_TO_PTR(obj)` — extract raw pointer from `mp_obj_t`
2. `(Type_obj_t *)` — cast to concrete struct type
3. `->field` — access the field

---

# Part 3: Implementation

## The General Solution

We implemented a recursive approach that handles arbitrary chain depth:

1. If the base is a `Name` (simple variable) → use existing `ParamAttrIR`
2. If the base is an `Attribute` → recursively build it first, then access the final attribute

## New IR Instruction: AttrAccessIR

We added `AttrAccessIR` to represent attribute access with a prelude:

```python
@dataclass
class AttrAccessIR(InstrIR):
    result: TempIR        # Where to store the result
    obj: ValueIR          # The object to access (could be another attr access)
    attr_name: str        # Attribute name
    class_c_name: str     # Class type for casting
    result_type: IRType   # Type of the result
```

This goes in the **prelude** — it's an instruction that must execute before the value is used.

## Recursive Attribute Building

The updated `_build_attribute`:

```python
def _build_attribute(self, expr: ast.Attribute, locals_):
    attr_name = expr.attr

    # Case 1: Simple name (rect.x)
    if isinstance(expr.value, ast.Name):
        var_name = expr.value.id
        if var_name in self._class_typed_params:
            # ... existing ParamAttrIR logic
            return ParamAttrIR(...), []

    # Case 2: Chained access (rect.bottom_right.x)
    if isinstance(expr.value, ast.Attribute):
        # Recursively build the base
        base_value, base_prelude = self._build_attribute(expr.value, locals_)

        # Determine what class type the base returns
        base_class_name = self._get_class_type_of_attr(expr.value)

        if base_class_name and base_class_name in self._known_classes:
            base_class_ir = self._known_classes[base_class_name]

            # Find the field and its type
            for fld in base_class_ir.get_all_fields():
                if fld.name == attr_name:
                    result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                    temp_name = self._fresh_temp()
                    result_temp = TempIR(ir_type=result_type, name=temp_name)

                    # Create the attribute access instruction
                    attr_access = AttrAccessIR(
                        result=result_temp,
                        obj=base_value,
                        attr_name=attr_name,
                        class_c_name=base_class_ir.c_name,
                        result_type=result_type,
                    )

                    # Return value + accumulated prelude
                    return result_temp, base_prelude + [attr_access]

    return ConstIR(ir_type=IRType.OBJ, value=None), []
```

## Type Tracking Helper

The `_get_class_type_of_attr` function traces the chain to determine types:

```python
def _get_class_type_of_attr(self, expr: ast.Attribute) -> str | None:
    if isinstance(expr.value, ast.Name):
        var_name = expr.value.id
        if var_name in self._class_typed_params:
            class_name = self._class_typed_params[var_name]
            if class_name in self._known_classes:
                class_ir = self._known_classes[class_name]
                for fld in class_ir.get_all_fields():
                    if fld.name == expr.attr:
                        return fld.py_type  # "Point" for bottom_right
    elif isinstance(expr.value, ast.Attribute):
        # Recursive: get parent's type, then look up this attr
        parent_class = self._get_class_type_of_attr(expr.value)
        if parent_class and parent_class in self._known_classes:
            class_ir = self._known_classes[parent_class]
            for fld in class_ir.get_all_fields():
                if fld.name == expr.attr:
                    return fld.py_type
    return None
```

## Code Emission

The `emit_attr_access` in `ContainerEmitter`:

```python
def emit_attr_access(self, instr: AttrAccessIR) -> list[str]:
    result_name = instr.result.name
    obj_c = self._value_to_c(instr.obj)
    c_type = instr.result_type.to_c_type_str()
    access_expr = (
        f"(({instr.class_c_name}_obj_t *)MP_OBJ_TO_PTR({obj_c}))->{instr.attr_name}"
    )
    return [f"    {c_type} {result_name} = {access_expr};"]
```

## Complete Example: Step by Step

### Python Input

```python
@dataclass
class Point:
    x: int
    y: int

@dataclass
class Rectangle:
    top_left: Point
    bottom_right: Point

def get_width(rect: Rectangle) -> int:
    return rect.bottom_right.x - rect.top_left.x
```

### IR Output

```
def get_width(rect: MP_OBJ_T) -> MP_INT_T:
  c_name: module_get_width
  max_temp: 2
  locals: {rect: MP_OBJ_T}
  body:
    # prelude:
      _tmp1 = rect.bottom_right.x
      _tmp2 = rect.top_left.x
    return (_tmp1 - _tmp2)
```

The IR shows:
- Two temp variables allocated (`max_temp: 2`)
- Prelude with chained access: `_tmp1 = rect.bottom_right.x`
- Final expression uses temps: `(_tmp1 - _tmp2)`

### Generated C

```c
static mp_obj_t module_get_width(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    mp_int_t _tmp1 = ((module_Point_obj_t *)MP_OBJ_TO_PTR(
        ((module_Rectangle_obj_t *)MP_OBJ_TO_PTR(rect))->bottom_right))->x;
    mp_int_t _tmp2 = ((module_Point_obj_t *)MP_OBJ_TO_PTR(
        ((module_Rectangle_obj_t *)MP_OBJ_TO_PTR(rect))->top_left))->x;
    return mp_obj_new_int((_tmp1 - _tmp2));
}
```

Breaking down `_tmp1`:
1. `MP_OBJ_TO_PTR(rect)` — get raw pointer from rect
2. `(module_Rectangle_obj_t *)` — cast to Rectangle struct
3. `->bottom_right` — access field (returns `mp_obj_t`)
4. `MP_OBJ_TO_PTR(...)` — get raw pointer from bottom_right
5. `(module_Point_obj_t *)` — cast to Point struct
6. `->x` — access final field (returns `mp_int_t`)

## Supported Patterns

### Self-Referencing Classes

```python
@dataclass
class Node:
    value: int
    next: Node

def get_next_value(n: Node) -> int:
    return n.next.value
```

IR:
```
# prelude:
  _tmp1 = n.next.value
return _tmp1
```

### Mutual References

```python
@dataclass
class Employee:
    name: str
    department: Department

@dataclass
class Department:
    name: str
    manager: Employee

def get_manager_dept(dept: Department) -> str:
    return dept.manager.department.name  # 3 levels!
```

IR:
```
# prelude:
  _tmp1 = dept.manager.department
  _tmp2 = _tmp1.name
return _tmp2
```

### Arbitrary Depth

The recursive implementation handles any chain length:

```python
a.b.c.d.e.f  # 6 levels - works!
```

Each level adds one `AttrAccessIR` to the prelude.

## Testing

Unit tests verify the generated patterns:

```python
def test_simple_chained_access(self):
    source = '''
@dataclass
class Point:
    x: int
    y: int

@dataclass
class Rectangle:
    top_left: Point
    bottom_right: Point

def get_width(rect: Rectangle) -> int:
    return rect.bottom_right.x - rect.top_left.x
'''
    result = compile_source(source, "test")
    assert "->bottom_right" in result
    assert "->top_left" in result
    assert "->x" in result
    assert "mp_const_none" not in result  # No fallback to None
```

## Performance Consideration

Each level of chained access adds one pointer dereference:

| Chain Depth | Operations |
|-------------|------------|
| `obj.x` | 1 cast + 1 deref |
| `obj.a.x` | 2 casts + 2 derefs |
| `obj.a.b.x` | 3 casts + 3 derefs |

This matches what handwritten C would do. The temp variables ensure each intermediate value is computed once.

---

## Conclusion

Chained attribute access required:

1. **Recursive IR building** — handle `Attribute` as base, not just `Name`
2. **Type tracking** — know what class type each intermediate access returns
3. **Prelude accumulation** — each level adds an `AttrAccessIR` instruction
4. **Proper casting** — generate `(ClassName_obj_t *)MP_OBJ_TO_PTR(obj)->field`

The pattern generalizes: any expression that returns a class-typed value can have attributes accessed on it. The recursive approach handles arbitrary composition depth naturally.

---

*Chained attribute access enables natural object-oriented patterns. The implementation in `ir_builder.py` uses recursion with type tracking, while `container_emitter.py` generates the nested cast expressions.*
