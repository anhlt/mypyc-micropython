# Class Parameter Attribute Access: Bridging Python's Object Model to C

*How we enabled functions to work with user-defined class types as parameters.*

---

When you write `def distance_squared(p1: Point, p2: Point) -> int`, Python's type hints are just documentation. But for a compiler targeting native code, these hints unlock powerful optimizations. This post explores how we implemented class parameter attribute access — letting standalone functions directly access fields of user-defined class instances.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) — How compilers work and why we need IR
2. [C Background](#part-2-c-background-for-python-developers) — Essential C concepts for understanding the output
3. [Implementation](#part-3-implementation) — How we built class parameter support

---

# Part 1: Compiler Theory

## What is a Compiler?

A **compiler** translates code from one language to another. Our compiler translates Python to C, which then gets compiled to machine code. This two-step process lets us leverage existing C compilers (like GCC) for the hard work of generating optimized machine instructions.

```
Python Source → [Our Compiler] → C Code → [GCC] → Machine Code
```

### Why Not Interpret Python Directly?

MicroPython already interprets Python bytecode. So why compile to C?

| Approach | Pros | Cons |
|----------|------|------|
| **Interpreter** | Flexible, easy debugging | Slower execution, more memory |
| **Compiled C** | Fast execution, small footprint | Less flexible, compile step needed |

For embedded systems with limited resources, compiled C wins on performance.

## The Compilation Pipeline

Our compiler has distinct phases, each transforming the code into a new representation:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Python    │ → │     AST     │ → │     IR      │ → │   C Code    │
│   Source    │    │   (Tree)    │    │  (Typed)    │    │  (String)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                        ↑                   ↑                   ↑
                   ast.parse()         IR Builder          Emitters
```

### Phase 1: Parsing (Python → AST)

Python's built-in `ast` module parses source code into an **Abstract Syntax Tree** (AST). The AST represents the structure of the code:

```python
# Python source
def add(a: int, b: int) -> int:
    return a + b
```

```python
# AST representation (simplified)
FunctionDef(
    name='add',
    args=[arg('a', annotation='int'), arg('b', annotation='int')],
    returns='int',
    body=[Return(BinOp(Name('a'), Add(), Name('b')))]
)
```

The AST captures **what** the code does, but not **how** to execute it efficiently.

### Phase 2: IR Building (AST → IR)

We transform the AST into our own **Intermediate Representation** (IR). This is where we:

- Extract type information from annotations
- Determine C types for variables
- Track class definitions and their fields
- Build typed expression trees

```python
# Our IR representation
FuncIR(
    name='add',
    c_name='module_add',
    params=[('a', CType.MP_INT_T), ('b', CType.MP_INT_T)],
    return_type=CType.MP_INT_T,
    body=[ReturnIR(BinOpIR(NameIR('a'), '+', NameIR('b')))]
)
```

### Phase 3: Code Emission (IR → C)

Finally, **emitters** walk the IR and generate C code strings:

```c
static mp_obj_t module_add(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    return mp_obj_new_int((a + b));
}
```

## Why Intermediate Representation?

Why not translate Python directly to C? IR provides several benefits:

### 1. Separation of Concerns

```
┌─────────────────┐     ┌─────────────────┐
│   IR Builder    │     │    Emitter      │
├─────────────────┤     ├─────────────────┤
│ Understands     │     │ Understands     │
│ Python syntax   │     │ C syntax        │
│ Type inference  │     │ MicroPython API │
│ Class tracking  │     │ Boxing/unboxing │
└─────────────────┘     └─────────────────┘
```

Each phase focuses on one job. The IR builder doesn't need to know C; the emitter doesn't need to know Python.

### 2. Type Information Preservation

Python's AST doesn't carry type information in a useful form. Our IR nodes include types:

```python
# AST: Just knows there's an addition
BinOp(left=Name('a'), op=Add(), right=Name('b'))

# IR: Knows the types involved
BinOpIR(
    left=NameIR('a', ir_type=IRType.INT),
    right=NameIR('b', ir_type=IRType.INT),
    op='+',
    ir_type=IRType.INT  # Result type
)
```

### 3. Debugging and Visualization

The `--dump-ir` flag lets us inspect the IR:

```bash
$ mpy-compile examples/factorial.py --dump-ir text
def factorial(n: MP_INT_T) -> MP_INT_T:
  c_name: factorial_factorial
  body:
    if (n <= 1):
      return 1
    return (n * factorial((n - 1)))
```

This helps debug compiler issues without wading through generated C.

### 4. Optimization Opportunities

With IR, we can transform code before emission:

- Constant folding: `3 + 4` → `7`
- Dead code elimination
- Type specialization for faster code paths

## IR Node Design

Our IR uses a hierarchy of node types:

```
IR Node
├── FuncIR          # Function definitions
├── ClassIR         # Class definitions  
├── StmtIR          # Statements
│   ├── ReturnIR
│   ├── IfIR
│   ├── WhileIR
│   └── AssignIR
└── ExprIR          # Expressions (produce values)
    ├── BinOpIR
    ├── CallIR
    ├── NameIR
    ├── ConstIR
    ├── SelfAttrIR   # self.x access
    └── ParamAttrIR  # p.x access (NEW!)
```

Each node carries the information needed for C code generation.

## The Prelude Pattern

A key insight in our IR design: expressions can have **side effects**. Consider:

```python
result = my_list.pop()  # Side effect: modifies my_list
```

We handle this with the **prelude pattern**. Every expression returns:

```python
tuple[ValueIR, list[InstrIR]]
#     ↑              ↑
#     │              └── Instructions to execute BEFORE using the value
#     └── The resulting value
```

For `my_list.pop()`:
- **Prelude**: `_tmp = mp_obj_list_pop(my_list)` (the actual pop)
- **Value**: `_tmp` (reference to the result)

This ensures side effects happen in the right order.

---

# Part 2: C Background for Python Developers

Before diving into implementation, let's cover essential C concepts.

## Pointers: Addresses in Memory

In Python, variables are references — you don't think about memory addresses. In C, **pointers** make addresses explicit:

```c
int x = 42;        // A regular integer, stored somewhere in memory
int *ptr = &x;     // ptr holds the ADDRESS of x (& means "address of")
int value = *ptr;  // value is 42 (*ptr means "value at that address")
```

**Visual representation:**

```
Memory Address:  0x1000    0x1004    0x1008
                ┌────────┬─────────┬────────┐
Values:         │   42   │  0x1000 │   42   │
                └────────┴─────────┴────────┘
Variables:          x        ptr      value
```

The `*` symbol has two meanings:
- In declarations (`int *ptr`): "ptr is a pointer to an int"
- In expressions (`*ptr`): "get the value at this address" (dereferencing)

### Why Pointers Matter for Us

MicroPython uses pointers extensively. Every Python object is accessed through a pointer (`mp_obj_t`). Understanding pointers is key to understanding our generated code.

## Structs: Bundling Data Together

A C **struct** groups related data, like a Python class with only attributes:

```c
struct Point {
    int x;
    int y;
};

// Create and use a Point
struct Point p;
p.x = 10;
p.y = 20;

// Or initialize at once
struct Point p2 = {10, 20};
```

### Memory Layout

Struct fields are laid out sequentially in memory:

```
struct Point at address 0x2000:
┌──────────────┬──────────────┐
│      x       │      y       │
│   (4 bytes)  │   (4 bytes)  │
└──────────────┴──────────────┘
0x2000         0x2004         0x2008

p.x is at offset 0 from struct start
p.y is at offset 4 from struct start
```

Accessing a field is just adding an offset to the struct's address — very fast!

## Arrow Operator: Accessing Fields Through Pointers

When you have a **pointer to a struct**, use `->` instead of `.`:

```c
struct Point p = {10, 20};
struct Point *ptr = &p;    // ptr points to p

int x1 = p.x;              // Direct access: use dot
int x2 = ptr->x;           // Through pointer: use arrow
int x3 = (*ptr).x;         // Equivalent: dereference, then dot
```

The arrow `->` is syntactic sugar: `ptr->x` means `(*ptr).x`.

### Why This Matters

In MicroPython, objects are always accessed through pointers. We never have a `Point` directly; we have a **pointer to a Point**. So we always use `->`:

```c
Point_obj_t *point = get_point();
int x = point->x;  // Access through pointer
```

## Type Casting: Reinterpreting Data

**Casting** tells the compiler to treat data as a different type:

```c
void *generic_ptr = malloc(100);  // Generic pointer (could point to anything)
struct Point *point_ptr = (struct Point *)generic_ptr;  // Cast to Point pointer
```

The cast `(struct Point *)` says "trust me, this pointer actually points to a Point."

### When Casting is Needed

MicroPython uses `mp_obj_t` as a universal object type. To access object-specific fields, we cast to the concrete type:

```c
mp_obj_t obj = ...;                              // Generic MicroPython object
Point_obj_t *point = (Point_obj_t *)obj;         // Cast to our Point type
int x = point->x;                                // Now we can access fields
```

## Macros: Compile-Time Text Substitution

C **macros** are processed before compilation, doing text replacement:

```c
#define SQUARE(x) ((x) * (x))
#define MAX(a, b) ((a) > (b) ? (a) : (b))

int result = SQUARE(5);      // Becomes: int result = ((5) * (5));
int bigger = MAX(10, 20);    // Becomes: int bigger = ((10) > (20) ? (10) : (20));
```

Macros look like functions but:
- No type checking
- No function call overhead
- Can cause issues with side effects (e.g., `SQUARE(i++)`)

### MicroPython's Key Macros

```c
// Convert mp_obj_t to raw pointer
#define MP_OBJ_TO_PTR(o) ((void *)(o))

// Convert raw pointer to mp_obj_t
#define MP_OBJ_FROM_PTR(p) ((mp_obj_t)(p))
```

These macros are central to how we access object fields.

## Putting It Together: The Access Pattern

Here's the pattern we generate for accessing `point.x`:

```c
((Point_obj_t *)MP_OBJ_TO_PTR(point))->x
```

Let's break it down step by step:

```c
point                                    // mp_obj_t (MicroPython object handle)
MP_OBJ_TO_PTR(point)                    // void* (raw pointer)
(Point_obj_t *)MP_OBJ_TO_PTR(point)     // Point_obj_t* (typed pointer)
((Point_obj_t *)MP_OBJ_TO_PTR(point))->x // int (field value)
```

This chain:
1. Takes a generic MicroPython object
2. Extracts the raw memory pointer
3. Casts to our specific struct type
4. Accesses the field at its fixed offset

No dictionary lookups. No method resolution. Just pointer arithmetic.

---

# Part 3: Implementation

Now let's see how we implemented class parameter attribute access.

## The Problem: What Happens to `p.x`?

Consider this Python code:

```python
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

So instead of runtime lookup, we can generate direct struct field access.

## The Bug: Missing Case for Parameters

Our existing code handled `self.x` in methods via `SelfAttrIR`:

```python
if isinstance(expr.value, ast.Name) and expr.value.id == "self":
    return SelfAttrIR(attr_name=attr_name, ...)
```

But for standalone functions, `_build_expr()` had no case for `ast.Attribute`. Accessing `p.x` fell through to:

```python
return ConstIR(ir_type=IRType.OBJ, value=None), []  # Bug: returns None!
```

This generated `mp_const_none` for every class parameter attribute access — completely wrong.

## The Solution: ParamAttrIR

We introduced a new IR node:

```python
@dataclass
class ParamAttrIR(ExprIR):
    param_name: str      # Python parameter name (e.g., "p1")
    c_param_name: str    # C parameter name (sanitized)
    attr_name: str       # Attribute name (e.g., "x")
    class_c_name: str    # C class name (e.g., "module_Point")
    result_type: IRType  # Type of the field
```

### Tracking Class-Typed Parameters

The key insight: we need to know which parameters are user-defined class types. We added tracking to the IR builder:

```python
class IRBuilder:
    def __init__(self, module_name: str):
        self._known_classes: dict[str, ClassIR] = {}      # Class definitions
        self._class_typed_params: dict[str, str] = {}     # param -> class name
```

When parsing a function, we check each parameter's annotation:

```python
def build_function(self, node: ast.FunctionDef) -> FuncIR:
    self._class_typed_params.clear()  # Reset for each function
    
    for arg in node.args.args:
        if isinstance(arg.annotation, ast.Name):
            type_name = arg.annotation.id
            if type_name in self._known_classes:
                # Record: this parameter is a class type
                self._class_typed_params[arg.arg] = type_name
```

### Building the IR Node

When we encounter an attribute access like `p.x`:

```python
def _build_attribute(self, expr: ast.Attribute) -> tuple[ValueIR, list]:
    if not isinstance(expr.value, ast.Name):
        return ConstIR(ir_type=IRType.OBJ, value=None), []
    
    var_name = expr.value.id    # "p"
    attr_name = expr.attr       # "x"
    
    if var_name in self._class_typed_params:
        class_name = self._class_typed_params[var_name]  # "Point"
        class_ir = self._known_classes[class_name]
        
        # Find the field and its type
        for field in class_ir.get_all_fields():
            if field.name == attr_name:
                return ParamAttrIR(
                    ir_type=IRType.from_c_type(field.c_type),
                    param_name=var_name,
                    c_param_name=sanitize_name(var_name),
                    attr_name=attr_name,
                    class_c_name=class_ir.c_name,
                    result_type=IRType.from_c_type(field.c_type),
                ), []
    
    # Fall through to other cases...
```

## Code Emission

The emitter generates the C access pattern:

```python
def _emit_param_attr(self, attr: ParamAttrIR) -> tuple[str, str]:
    expr = f"(({attr.class_c_name}_obj_t *)MP_OBJ_TO_PTR({attr.c_param_name}))->{attr.attr_name}"
    return expr, attr.result_type.to_c_type_str()
```

For `p1.x` where `p1: Point`, this generates:

```c
((module_Point_obj_t *)MP_OBJ_TO_PTR(p1))->x
```

### Understanding MP_OBJ_TO_PTR

`MP_OBJ_TO_PTR` is a MicroPython macro:

```c
#define MP_OBJ_TO_PTR(o) ((void *)(o))
```

In MicroPython, `mp_obj_t` can represent different things:

| Value Type | How It's Stored |
|------------|-----------------|
| Small integers | Encoded in the pointer value (tagged) |
| Interned strings | Index encoded in pointer |
| Full objects | Actual pointer to heap memory |

For class instances, `mp_obj_t` is already a pointer. `MP_OBJ_TO_PTR` makes this explicit for casting.

### Our Class Struct Layout

When we compile a class like `Point`, we generate:

```c
typedef struct _module_Point_obj_t {
    mp_obj_base_t base;  // Required: MicroPython object header
    mp_int_t x;          // Field: stored inline
    mp_int_t y;          // Field: stored inline
} module_Point_obj_t;
```

The `mp_obj_base_t base` is required by MicroPython — it contains a pointer to the type object. Our fields follow directly, stored **inline** (not in a dictionary).

## Complete Example: Step by Step

Let's trace the compilation of:

```python
def get_x(p: Point) -> int:
    return p.x
```

### Step 1: Python AST

```python
FunctionDef(
    name='get_x',
    args=arguments(args=[arg(arg='p', annotation=Name(id='Point'))]),
    returns=Name(id='int'),
    body=[Return(value=Attribute(value=Name(id='p'), attr='x'))]
)
```

### Step 2: IR Building

1. See `p: Point` → Record `_class_typed_params['p'] = 'Point'`
2. Process `Return(Attribute(...))` → Call `_build_attribute()`
3. Find `p` in `_class_typed_params` → Create `ParamAttrIR`

```python
FuncIR(
    name='get_x',
    c_name='module_get_x',
    params=[('p', CType.MP_OBJ_T)],
    return_type=CType.MP_INT_T,
    body=[ReturnIR(value=ParamAttrIR(
        param_name='p',
        attr_name='x',
        class_c_name='module_Point',
        result_type=IRType.INT
    ))]
)
```

### Step 3: Code Emission

1. Emit signature: `static mp_obj_t module_get_x(mp_obj_t p_obj)`
2. Emit parameter binding: `mp_obj_t p = p_obj;`
3. Emit return with `ParamAttrIR` → `((module_Point_obj_t *)MP_OBJ_TO_PTR(p))->x`
4. Box result: `return mp_obj_new_int(...);`

### Step 4: Final C Code

```c
static mp_obj_t module_get_x(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;
    return mp_obj_new_int(((module_Point_obj_t *)MP_OBJ_TO_PTR(p))->x);
}
MP_DEFINE_CONST_FUN_OBJ_1(module_get_x_obj, module_get_x);
```

## The Full distance_squared Example

```python
def distance_squared(p1: Point, p2: Point) -> int:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx * dx + dy * dy
```

Compiles to:

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

All arithmetic happens on unboxed `mp_int_t` values. Only the final result gets boxed.

## Testing

Unit tests verify the C patterns:

```python
def test_function_with_two_class_params(self):
    source = '''
class Point:
    x: int
    y: int

def distance_squared(p1: Point, p2: Point) -> int:
    dx = p2.x - p1.x
    return dx * dx
'''
    result = compile_source(source, "test")
    assert "MP_OBJ_TO_PTR(p1)" in result
    assert "MP_OBJ_TO_PTR(p2)" in result
    assert "->x" in result
```

Device tests verify execution on ESP32:

```python
test(
    "distance_squared",
    "import m; p1 = m.Point(0,0); p2 = m.Point(3,4); print(m.distance_squared(p1,p2))",
    "25",
)
```

## Performance Comparison

| Operation | Python Runtime | Our Generated C |
|-----------|---------------|-----------------|
| `p.x` access | Hash lookup + descriptor check | Single pointer dereference |
| Type checking | Runtime `isinstance()` | Compile-time (trusted) |
| Field offset | Dictionary-based | Fixed struct offset |

For numeric code accessing many fields in loops, this difference compounds significantly.

## Limitations and Future Work

**Current limitations:**
- Only works for classes defined in the same module
- Trusts type annotations without runtime verification
- No support for inherited fields from external base classes

**Future improvements:**
- Cross-module class type tracking
- Optional runtime type checks in debug mode
- Support for `typing.Protocol` structural types

---

## Conclusion

Class parameter attribute access bridges Python's dynamic object model to C's static struct access. The key elements:

1. **IR Node (`ParamAttrIR`)**: Captures class type and field information
2. **Type Tracking**: Record which parameters are class types during IR building
3. **Code Emission**: Generate the `MP_OBJ_TO_PTR` + cast + arrow pattern

The pattern — track metadata during IR building, emit optimized code during emission — is the same one we use for RTuples, typed lists, and other optimizations. Each piece of type information the programmer provides is an opportunity for better code generation.
