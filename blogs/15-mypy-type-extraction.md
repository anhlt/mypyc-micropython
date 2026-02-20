# Extracting Type Information from Mypy

*A deep dive into how we access mypy's semantic analysis to get type information for compilation.*

---

When compiling typed Python to C, we need precise type information: parameter types, return types, local variable types, and class field types. Python's `ast` module gives us the annotation syntax, but mypy gives us the **resolved types** after semantic analysis. This post explains how we extract that information.

## Table of Contents

1. [The Mypy Build API](#part-1-the-mypy-build-api) - How to run mypy programmatically
2. [Mypy's Data Structures](#part-2-mypys-data-structures) - The AST nodes mypy uses
3. [Type Extraction Pipeline](#part-3-type-extraction-pipeline) - How we extract and convert types
4. [Class Attribute Type Inference](#advanced-class-attribute-type-inference) - How `point.x` gets its type

---

# Part 1: The Mypy Build API

## Running Mypy Programmatically

Mypy isn't just a command-line tool - it has a full programmatic API. Here's the core pattern:

```python
from mypy import build as mypy_build
from mypy.options import Options

# Configure mypy
options = Options()
options.python_version = (3, 10)
options.preserve_asts = True  # Keep AST bodies for local type extraction
options.disallow_untyped_defs = True

# Create build source
sources = [mypy_build.BuildSource(file_path, module_name, None)]

# Run semantic analysis + type checking
build_result = mypy_build.build(sources=sources, options=options)
```

### Key Options We Use

| Option | Value | Purpose |
|--------|-------|---------|
| `python_version` | `(3, 10)` | Target Python version |
| `preserve_asts` | `True` | Keep function bodies for local type extraction |
| `disallow_untyped_defs` | `True` | Require type annotations |
| `strict_optional` | `True` | Distinguish `T` from `T | None` |

### What `build()` Returns

The `build()` function returns a `BuildResult` object with:

```python
build_result.errors      # List of error messages
build_result.files       # Dict[str, MypyFile] - typed AST per module
```

The magic is in `build_result.files` - this contains mypy's typed AST where every expression and variable has resolved type information attached.

---

# Part 2: Mypy's Data Structures

## The MypyFile Structure

After `build()`, we get a `MypyFile` for each module:

```python
mypy_file = build_result.files.get(module_name)

# MypyFile has:
mypy_file.names     # SymbolTable: maps names to SymbolTableNode
mypy_file.defs      # List of top-level definitions (less useful)
```

The symbol table (`names`) is where the type information lives.

## Key Mypy Node Types

| Node Type | Python Construct | What It Contains |
|-----------|------------------|------------------|
| `FuncDef` | `def foo(): ...` | Function with typed parameters, body |
| `TypeInfo` | `class Foo: ...` | Class with fields, methods, bases |
| `Var` | Variable | Type of variable (inferred or annotated) |
| `AssignmentStmt` | `x = expr` | Assignment with typed lvalue |
| `NameExpr` | `x` | Reference to a name with `.node` pointing to definition |
| `CallableType` | Function type | Parameter types and return type |

## How Types Are Represented

Mypy represents types as strings in a qualified format:

```
Python Type          Mypy Type String
-----------          ----------------
int                  "builtins.int"
str                  "builtins.str"
list[int]            "builtins.list[builtins.int]"
dict[str, int]       "builtins.dict[builtins.str, builtins.int]"
Point (user class)   "module_name.Point"
None                 "None"
```

### The `builtins.` Prefix

Mypy qualifies all built-in types with `builtins.`. We clean this up:

```python
def _clean_type_str(type_str: str) -> str:
    type_str = type_str.replace("builtins.", "")
    type_str = type_str.replace("?", "")  # Remove unresolved markers
    return type_str

# "builtins.int" -> "int"
# "builtins.list[builtins.str]" -> "list[str]"
```

---

# Part 3: Type Extraction Pipeline

## Overview

```
MypyFile
    |
    v
Symbol Table (names)
    |
    +-- FuncDef -----> FunctionTypeInfo
    |                     - params: [(name, type), ...]
    |                     - return_type: str
    |                     - local_types: {name: type, ...}
    |
    +-- TypeInfo ----> ClassTypeInfo
    |                     - fields: [(name, type), ...]
    |                     - methods: [FunctionTypeInfo, ...]
    |                     - base_class: str | None
    |
    +-- Var ---------> module_types: {name: type}
```

## Extracting Function Types

For a function like:

```python
def add(a: int, b: int) -> int:
    result = a + b
    return result
```

We extract from `FuncDef`:

```python
def _extract_function_info(func_def: FuncDef) -> FunctionTypeInfo:
    # 1. Extract parameter types from arguments
    params = []
    for arg in func_def.arguments:
        param_name = arg.variable.name
        param_type = str(arg.type_annotation)  # "builtins.int"
        params.append((param_name, _clean_type_str(param_type)))
    
    # 2. Extract return type from function's CallableType
    if isinstance(func_def.type, CallableType):
        return_type = str(func_def.type.ret_type)  # "builtins.int"
    
    # 3. Extract local variable types from body
    local_types = {}
    _extract_local_types(func_def.body.body, local_types)
    
    return FunctionTypeInfo(
        name=func_def.name,
        params=params,  # [("a", "int"), ("b", "int")]
        return_type=return_type,  # "int"
        local_types=local_types,  # {"result": "int"}
    )
```

### Extracting Local Variable Types

This is the key insight: mypy stores inferred types on `Var` nodes, which are attached to `NameExpr` lvalues in assignments:

```python
def _extract_local_types(stmts: list, local_types: dict[str, str]) -> None:
    for stmt in stmts:
        if isinstance(stmt, AssignmentStmt):
            for lvalue in stmt.lvalues:
                # NameExpr.node points to a Var with the inferred type
                if isinstance(lvalue, NameExpr) and isinstance(lvalue.node, Var):
                    var_node = lvalue.node
                    if var_node.type is not None:
                        local_types[lvalue.name] = str(var_node.type)
        
        # Recursively handle control flow
        elif isinstance(stmt, IfStmt):
            for body in stmt.body:
                _extract_local_types(body.body, local_types)
        # ... similar for while, for, with
```

### Example: Bool Operations

```python
def test(a: bool, b: bool) -> bool:
    x = a and b    # What type is x?
    y = a & b      # What type is y?
    z = a + b      # What type is z?
    return x
```

Mypy infers:
- `x`: `bool` (logical AND of bools)
- `y`: `bool` (bitwise AND of bools)  
- `z`: `int` (bool + bool promotes to int)

We extract this via `var_node.type`:

```python
local_types = {"x": "bool", "y": "bool", "z": "int"}
```

## Extracting Class Types

For a class like:

```python
@dataclass
class Rectangle:
    top_left: Point
    bottom_right: Point
```

We extract from mypy's `TypeInfo`:

```python
def _extract_class_info_from_typeinfo(type_info: MypyTypeInfo) -> ClassTypeInfo:
    fields = []
    methods = []
    
    # Iterate symbol table for class members
    for member_name, sym in type_info.names.items():
        node = sym.node
        
        if isinstance(node, FuncDef):
            # It's a method
            method_info = _extract_function_info(node)
            methods.append(method_info)
        
        elif isinstance(node, Var):
            # It's a field - Var.type has the resolved type
            field_type = str(node.type)  # "module.Point"
            fields.append((member_name, field_type))
    
    return ClassTypeInfo(
        name=type_info.name,
        fields=fields,  # [("top_left", "module.Point"), ...]
        methods=methods,
    )
```

### Handling Qualified Class Names

Mypy returns field types as qualified names like `"module.Point"`. We need to extract just `"Point"` for our type lookups:

```python
def _mypy_type_to_py_type(mypy_type: str) -> str:
    base_type = mypy_type.split("[")[0].strip()  # Remove generic params
    
    # Built-in types
    if base_type in ("int", "float", "bool", "str", "list", "dict", "tuple", "set", "None"):
        return base_type
    
    # Qualified class names: "module.Point" -> "Point"
    if "." in base_type:
        return base_type.split(".")[-1]
    
    return base_type if base_type else "object"
```

This is critical for chained attribute access like `rect.top_left.x` where we need to look up `Point` in our known classes.

## Converting to C Types

Once we have Python type strings, we map to C types:

```python
def _mypy_type_to_c_type(mypy_type: str) -> str:
    type_map = {
        "int": "mp_int_t",
        "float": "mp_float_t",
        "bool": "bool",
        "str": "mp_obj_t",
        "None": "void",
        "list": "mp_obj_t",
        "dict": "mp_obj_t",
        "tuple": "mp_obj_t",
        "set": "mp_obj_t",
        "object": "mp_obj_t",
        "Any": "mp_obj_t",
    }
    base_type = mypy_type.split("[")[0].strip()
    return type_map.get(base_type, "mp_obj_t")
```

### Type Conversion Summary

| Mypy Type | Python Type | C Type | IR Type |
|-----------|-------------|--------|---------|
| `builtins.int` | `int` | `mp_int_t` | `IRType.INT` |
| `builtins.float` | `float` | `mp_float_t` | `IRType.FLOAT` |
| `builtins.bool` | `bool` | `bool` | `IRType.BOOL` |
| `builtins.str` | `str` | `mp_obj_t` | `IRType.OBJ` |
| `builtins.list[builtins.int]` | `list` | `mp_obj_t` | `IRType.OBJ` |
| `module.Point` | `Point` | `mp_obj_t` | `IRType.OBJ` |
| `None` | `None` | `void` | - |

## Complete Example

Let's trace a complete example:

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

def distance_squared(p1: Point, p2: Point) -> int:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx * dx + dy * dy
```

### Step 1: Mypy Build

```python
build_result = mypy_build.build(sources, options)
mypy_file = build_result.files["module"]
```

### Step 2: Extract Class Types

From `mypy_file.names["Point"]`:

```python
ClassTypeInfo(
    name="Point",
    fields=[("x", "int"), ("y", "int")],
    methods=[...],
)
```

### Step 3: Extract Function Types

From `mypy_file.names["distance_squared"]`:

```python
FunctionTypeInfo(
    name="distance_squared",
    params=[("p1", "Point"), ("p2", "Point")],
    return_type="int",
    local_types={"dx": "int", "dy": "int"},
)
```

Note how mypy inferred `dx` and `dy` are `int` even without annotations!

### Step 4: IR Building Uses These Types

```python
# In IRBuilder._build_assign():
if var_name in self._mypy_local_types:
    c_type = self._mypy_type_to_c_type(self._mypy_local_types[var_name])
    # "int" -> "mp_int_t"
```

### Step 5: Generated C Code

```c
static mp_obj_t module_distance_squared(mp_obj_t p1_obj, mp_obj_t p2_obj) {
    mp_obj_t p1 = p1_obj;
    mp_obj_t p2 = p2_obj;

    mp_int_t dx = (((module_Point_obj_t *)MP_OBJ_TO_PTR(p2))->x - 
                   ((module_Point_obj_t *)MP_OBJ_TO_PTR(p1))->x);
    mp_int_t dy = (((module_Point_obj_t *)MP_OBJ_TO_PTR(p2))->y - 
                   ((module_Point_obj_t *)MP_OBJ_TO_PTR(p1))->y);
    return mp_obj_new_int(((dx * dx) + (dy * dy)));
}
```

The local variables `dx` and `dy` are correctly typed as `mp_int_t` because mypy told us they're `int`.

---

## Advanced: Class Attribute Type Inference

When we access `point.x`, how do we know it's an `int`? This requires combining multiple sources of type information.

### The Challenge

```python
class Point:
    x: int
    y: int

def add_to_x(p: Point, n: int) -> int:
    result = p.x + n  # What type is p.x? What type is result?
    return result
```

We need to:
1. Know that `p` is of type `Point`
2. Look up `Point.x` to find it's `int`
3. Infer `int + int = int` for `result`

### Step 1: Track Class-Typed Parameters

When building a function, we detect parameters with class type annotations:

```python
# In IRBuilder.build_function():
for arg in node.args.args:
    if isinstance(arg.annotation, ast.Name):
        type_name = arg.annotation.id  # "Point"
        if type_name in self._known_classes:
            # Remember: parameter 'p' has type 'Point'
            self._class_typed_params[arg.arg] = type_name
```

After this, `_class_typed_params = {"p": "Point"}`.

### Step 2: Resolve Attribute Type from ClassIR

When we encounter `p.x`, we look up the field type:

```python
# In IRBuilder._build_attribute():
if isinstance(expr.value, ast.Name):
    var_name = expr.value.id  # "p"
    if var_name in self._class_typed_params:
        class_name = self._class_typed_params[var_name]  # "Point"
        class_ir = self._known_classes[class_name]
        
        # Find field 'x' in Point's fields
        for fld in class_ir.get_all_fields():
            if fld.name == attr_name:  # "x"
                # fld.c_type is CType.MP_INT_T (from class definition)
                result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                return ParamAttrIR(
                    ir_type=result_type,  # IRType.INT
                    param_name=var_name,
                    attr_name=attr_name,
                    class_c_name=class_ir.c_name,
                    result_type=result_type,
                ), []
```

The key insight: `ClassIR` stores field types from the class definition. When `p: Point` and we access `p.x`, we look up `Point.x` in `ClassIR.fields` to get `CType.MP_INT_T`.

### Step 3: Mypy Infers the Expression Type

Meanwhile, mypy independently infers the type of `result`:

```python
# Mypy's inference:
# p.x: int (from Point.x annotation)
# n: int (from parameter annotation)
# p.x + n: int (int + int = int)
# result = p.x + n => result: int
```

We extract this via `_extract_local_types()`:

```python
local_types = {"result": "int"}
```

### Step 4: Generated Code

The IR builder creates `ParamAttrIR` for `p.x`:

```python
ParamAttrIR(
    ir_type=IRType.INT,
    param_name="p",
    attr_name="x", 
    class_c_name="test_Point",
    result_type=IRType.INT,
)
```

The function emitter generates direct struct access:

```c
static mp_obj_t test_add_to_x(mp_obj_t p_obj, mp_obj_t n_obj) {
    mp_obj_t p = p_obj;
    mp_int_t n = mp_obj_get_int(n_obj);

    // p.x compiles to direct struct field access
    // result is mp_int_t because mypy told us it's int
    mp_int_t result = (((test_Point_obj_t *)MP_OBJ_TO_PTR(p))->x + n);
    return mp_obj_new_int(result);
}
```

### Chained Attribute Access

For nested classes like `rect.top_left.x`:

```python
@dataclass
class Point:
    x: int
    y: int

@dataclass  
class Rectangle:
    top_left: Point
    bottom_right: Point

def get_left_x(rect: Rectangle) -> int:
    return rect.top_left.x
```

We recursively resolve types:

```python
# In _get_class_type_of_attr():
def _get_class_type_of_attr(self, expr: ast.Attribute) -> str | None:
    if isinstance(expr.value, ast.Name):
        # Base case: rect.top_left
        var_name = expr.value.id  # "rect"
        class_name = self._class_typed_params[var_name]  # "Rectangle"
        class_ir = self._known_classes[class_name]
        for fld in class_ir.get_all_fields():
            if fld.name == expr.attr:  # "top_left"
                return fld.py_type  # "Point"
    
    elif isinstance(expr.value, ast.Attribute):
        # Recursive case: rect.top_left.x
        parent_class = self._get_class_type_of_attr(expr.value)  # "Point"
        class_ir = self._known_classes[parent_class]
        for fld in class_ir.get_all_fields():
            if fld.name == expr.attr:  # "x"
                return fld.py_type  # "int"
```

Generated code for `rect.top_left.x`:

```c
// Step 1: rect.top_left -> _tmp1 (Point)
mp_obj_t _tmp1 = ((test_Rectangle_obj_t *)MP_OBJ_TO_PTR(rect))->top_left;
// Step 2: _tmp1.x -> mp_int_t
mp_int_t result = ((test_Point_obj_t *)MP_OBJ_TO_PTR(_tmp1))->x;
```

### Type Information Sources Summary

| Expression | Type Source | How We Get It |
|------------|-------------|---------------|
| `p` (parameter) | AST annotation | `arg.annotation.id` -> `_class_typed_params` |
| `p.x` (attribute) | ClassIR fields | `class_ir.get_all_fields()` -> `fld.c_type` |
| `result` (local) | Mypy inference | `var_node.type` -> `_mypy_local_types` |
| `p.x + n` | Mypy inference | Expression type propagation |

---

## Summary

We extract type information from mypy in three stages:

1. **Run mypy's build API** with `preserve_asts=True` to get typed AST
2. **Walk the symbol table** to extract function and class definitions
3. **Convert mypy type strings** to Python types then to C types

Key data structures:

| Our Type | Source | Contains |
|----------|--------|----------|
| `FunctionTypeInfo` | `FuncDef` | params, return_type, local_types |
| `ClassTypeInfo` | `TypeInfo` | fields, methods, base_class |
| `TypeCheckResult` | `MypyFile` | functions, classes, module_types |

Key conversions:

| From | To | Example |
|------|----|---------|
| `FuncDef.arguments` | `params` | `[("a", "int"), ("b", "int")]` |
| `Var.type` | `local_types` | `{"x": "bool"}` |
| `"builtins.int"` | `"int"` | Clean type string |
| `"module.Point"` | `"Point"` | Extract class name |
| `"int"` | `"mp_int_t"` | Map to C type |

This pipeline lets us leverage mypy's sophisticated type inference for generating efficient, correctly-typed C code.
