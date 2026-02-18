# Class Parameter Attribute Access: Bridging Python's Object Model to C

*How we enabled functions to work with user-defined class types as parameters.*

---

When you write `def distance_squared(p1: Point, p2: Point) -> int`, Python's type hints are just documentation. But for a compiler targeting native code, these hints unlock powerful optimizations. This post explores how we implemented class parameter attribute access — letting standalone functions directly access fields of user-defined class instances.

## The Problem: What Happens to `p.x`?

Consider this Python code:

```python
@dataclass
class Point:
    x: int
    y: int

def distance_squared(p1: Point, p2: Point) -> int:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx * dx + dy * dy
```

In pure Python, `p1.x` triggers attribute lookup at runtime — checking `__dict__`, descriptors, `__getattr__`, etc. But we know at compile time that:

1. `p1` is typed as `Point`
2. `Point` has a field `x: int`
3. Our compiler generates `Point` as a C struct

So instead of runtime lookup, we can generate direct struct field access. The question is: how do we track this through the IR and emit the right C code?

## The Missing Case: Attribute Access on Parameters

Our existing code handled attribute access in methods via `SelfAttrIR`:

```python
if isinstance(expr.value, ast.Name) and expr.value.id == "self":
    # Handle self.x -> self->x in C
    return SelfAttrIR(attr_name=attr_name, ...)
```

But for standalone functions, `_build_expr()` had no case for `ast.Attribute` at all. Accessing `p.x` fell through to the default:

```python
return ConstIR(ir_type=IRType.OBJ, value=None), []  # Bug!
```

This generated `mp_const_none` for every class parameter attribute access — completely wrong.

## The Solution: ParamAttrIR

We introduced a new IR node specifically for class parameter attribute access:

```python
@dataclass
class ParamAttrIR(ExprIR):
    param_name: str      # Python parameter name (e.g., "p1")
    c_param_name: str    # C parameter name (sanitized)
    attr_name: str       # Attribute name (e.g., "x")
    class_c_name: str    # C class name (e.g., "module_Point")
    result_type: IRType  # Type of the field
```

The key insight: we need to track which function parameters are typed as user-defined classes. We added a dictionary to the IR builder:

```python
self._class_typed_params: dict[str, str] = {}  # param_name -> class_name
```

During function parsing, when we see a parameter with a class type annotation:

```python
if isinstance(arg.annotation, ast.Name):
    type_name = arg.annotation.id
    if type_name in self._known_classes:
        self._class_typed_params[arg.arg] = type_name
```

Then in `_build_expr()`, we check for attribute access:

```python
def _build_attribute(self, expr: ast.Attribute, locals_: list[str]) -> tuple[ValueIR, list]:
    if not isinstance(expr.value, ast.Name):
        return ConstIR(ir_type=IRType.OBJ, value=None), []
    
    var_name = expr.value.id
    attr_name = expr.attr
    
    if var_name in self._class_typed_params:
        class_name = self._class_typed_params[var_name]
        class_ir = self._known_classes[class_name]
        
        # Find the field and its type
        for fld in class_ir.get_all_fields():
            if fld.name == attr_name:
                result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                return ParamAttrIR(
                    ir_type=result_type,
                    param_name=var_name,
                    c_param_name=sanitize_name(var_name),
                    attr_name=attr_name,
                    class_c_name=class_ir.c_name,
                    result_type=result_type,
                ), []
```

## Code Emission: The C Pattern

The emitter generates direct struct access through a pointer cast:

```python
def _emit_param_attr(self, attr: ParamAttrIR) -> tuple[str, str]:
    expr = f"(({attr.class_c_name}_obj_t *)MP_OBJ_TO_PTR({attr.c_param_name}))->{attr.attr_name}"
    return expr, attr.result_type.to_c_type_str()
```

For `p1.x` where `p1: Point`, this generates:

```c
((module_Point_obj_t *)MP_OBJ_TO_PTR(p1))->x
```

### Understanding `MP_OBJ_TO_PTR`

`MP_OBJ_TO_PTR` is a MicroPython macro defined in `py/obj.h`:

```c
#define MP_OBJ_TO_PTR(o) ((void *)(o))
// or for 64-bit NaN boxing representation:
#define MP_OBJ_TO_PTR(o) ((void *)(uintptr_t)(o))
```

In MicroPython, `mp_obj_t` is the universal object handle type. It can represent:
- **Small integers**: Encoded directly in the pointer (tagged)
- **QStrings**: Interned strings encoded in the pointer
- **Full objects**: Actual pointers to heap-allocated structs

For "full" objects like our class instances, `mp_obj_t` is essentially a pointer to the object's memory. `MP_OBJ_TO_PTR` extracts this raw pointer so we can cast it to our specific struct type.

The inverse macro `MP_OBJ_FROM_PTR(p)` converts a struct pointer back to `mp_obj_t`:

```c
#define MP_OBJ_FROM_PTR(p) ((mp_obj_t)(p))
```

### Our Class Struct Layout

When we define a class like `Point`, we generate this C struct:

```c
struct _class_param_Point_obj_t {
    mp_obj_base_t base;  // Required MicroPython header (contains type pointer)
    mp_int_t x;          // Our field - stored inline
    mp_int_t y;          // Our field - stored inline
};
```

The `mp_obj_base_t base` field is required by MicroPython's object system. It contains a pointer to the type object, enabling runtime type checks and method dispatch.

Our fields (`x`, `y`) are stored **inline** in the struct, not in a separate `data` wrapper. This means direct field access is just a fixed-offset pointer dereference.

### The Complete Access Pattern

Breaking down `((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p1))->x`:

1. **`p1`** — An `mp_obj_t` (the boxed MicroPython object handle)
2. **`MP_OBJ_TO_PTR(p1)`** — Extract raw `void*` pointer to the object
3. **`(class_param_Point_obj_t *)`** — Cast to our specific struct type
4. **`->x`** — Access the field at its fixed offset

No hash lookups. No descriptor protocol. Just a single pointer dereference with a compile-time-known offset.

## The Generated Code

For our `distance_squared` function:

```python
def distance_squared(p1: Point, p2: Point) -> int:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx * dx + dy * dy
```

The compiler generates:

```c
static mp_obj_t class_param_distance_squared(mp_obj_t p1_obj, mp_obj_t p2_obj) {
    mp_obj_t p1 = p1_obj;
    mp_obj_t p2 = p2_obj;

    mp_int_t dx = (((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p2))->x - 
                   ((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p1))->x);
    mp_int_t dy = (((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p2))->y - 
                   ((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p1))->y);
    return mp_obj_new_int(((dx * dx) + (dy * dy)));
}
```

All arithmetic happens on unboxed `mp_int_t` values. Only the final result gets boxed for return.

## Method Context: Not Just Functions

We also updated `_build_method_expr()` to handle class-typed parameters in methods. A method might receive another object of a known class:

```python
class Geometry:
    def distance_to(self, other: Point) -> int:
        dx = other.x - self.x
        return dx * dx
```

Here `other.x` needs `ParamAttrIR`, while `self.x` uses `SelfAttrIR`. The updated code checks both:

```python
if var_name == "self":
    return SelfAttrIR(...)
elif var_name in self._class_typed_params:
    return ParamAttrIR(...)
```

## Testing the Implementation

Unit tests verify the C patterns are generated:

```python
def test_function_with_two_class_params(self):
    source = '''
class Point:
    x: int
    y: int

def distance_squared(p1: Point, p2: Point) -> int:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx * dx + dy * dy
'''
    result = compile_source(source, "test")
    assert "MP_OBJ_TO_PTR(p1)" in result
    assert "MP_OBJ_TO_PTR(p2)" in result
    assert "->x" in result
    assert "->y" in result
```

Device tests verify actual execution on ESP32:

```python
test(
    "distance_squared two points",
    "import class_param as cp; p1 = cp.Point(0, 0); p2 = cp.Point(3, 4); "
    "print(cp.distance_squared(p1, p2))",
    "25",
)
```

## IR Visualization

The `--dump-ir` flag shows the new `ParamAttrIR` nodes:

```
$ mpy-compile examples/class_param.py --dump-ir text --ir-function distance_squared

def distance_squared(p1: MP_OBJ_T, p2: MP_OBJ_T) -> MP_INT_T:
  c_name: class_param_distance_squared
  locals: {p1: MP_OBJ_T, p2: MP_OBJ_T, dx: MP_INT_T, dy: MP_INT_T}
  body:
    (new) dx = (<ParamAttrIR> - <ParamAttrIR>)
    (new) dy = (<ParamAttrIR> - <ParamAttrIR>)
    return ((dx * dx) + (dy * dy))
```

## Performance Implications

Direct struct access vs. runtime attribute lookup:

| Operation | Python Runtime | Our Generated C |
|-----------|---------------|-----------------|
| `p.x` access | Hash lookup, descriptor check | Single pointer dereference |
| Type checking | Runtime `isinstance()` | Compile-time (trusted annotation) |
| Field offset | Dictionary-based | Fixed struct offset |

For numeric code that accesses many fields in loops, this difference compounds significantly.

## Limitations and Future Work

Current limitations:
- Only works for classes defined in the same module
- Trusts type annotations without runtime verification
- No support for inherited fields from external base classes

Future improvements could include:
- Cross-module class type tracking
- Optional runtime type checks in debug mode
- Support for `typing.Protocol` structural types

## Conclusion

Class parameter attribute access bridges Python's dynamic object model to C's static struct access. By tracking type information through the IR and generating direct field access, we get the ergonomics of Python's type hints with the performance of native code.

The pattern — track metadata during IR building, emit optimized code during emission — is the same one we use for RTuples, typed lists, and other optimizations. Each piece of type information the programmer provides is an opportunity for better code generation.
