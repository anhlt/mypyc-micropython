# Integrating Mypy for Strict Type Checking

*Using mypy's semantic analysis to validate code and unlock future optimizations.*

---

## Part 1: Why Type Checking Matters for a Compiler

### The Problem with AST-Only Type Information

Our compiler transforms typed Python to C:

```
Python source -> AST -> IR -> C code
```

When parsing `def foo(x: int) -> int`, the AST gives us the annotation nodes directly. But AST annotations have limitations:

1. **No resolution of generics**: `list` and `list[int]` look the same at the AST level
2. **No type inference**: Local variables without annotations have unknown types
3. **No validation**: Type errors only surface at C compilation or runtime

```python
def process(items: list[int]) -> int:
    total = 0          # What type is total? AST doesn't know
    for x in items:    # What type is x? AST sees list, not list[int]
        total += x
    return total
```

### What Mypy Provides

Mypy performs **semantic analysis** - it builds a complete type model of your code:

| Information | AST Only | With Mypy |
|-------------|----------|-----------|
| `list[int]` element type | Not available | `int` |
| Inferred local types | Unknown | Resolved |
| Type errors | Runtime crash | Compile-time error |
| Generic resolution | Raw annotation | Fully resolved |

### Our Goal

1. **Validation**: Catch type errors before generating C code
2. **Information**: Extract resolved types for better code generation
3. **Future optimization**: Use type info for performance improvements

---

## Part 2: How Mypy Works (For Compiler Writers)

### Mypy's Build API

Mypy isn't just a command-line tool - it has a programmatic API:

```python
from mypy import build as mypy_build
from mypy.options import Options

options = Options()
options.python_version = (3, 10)
options.disallow_untyped_defs = True

result = mypy_build.build(
    sources=[mypy_build.BuildSource(path, module_name, text=source)],
    options=options
)
```

The result contains:
- **Errors**: Type violations found
- **Files**: Parsed modules with type information
- **Types**: Resolved types for all expressions

### Extracting Type Information

Mypy's AST nodes have type annotations attached:

```python
def extract_function_types(func_def: FuncDef) -> FunctionTypeInfo:
    func_type = func_def.type
    if isinstance(func_type, CallableType):
        params = []
        for name, arg_type in zip(func_def.arg_names, func_type.arg_types):
            params.append((name, str(arg_type)))
        return FunctionTypeInfo(
            name=func_def.name,
            params=params,
            return_type=str(func_type.ret_type)
        )
```

### The Type String Format

Mypy represents types as strings:

| Python Annotation | Mypy Type String |
|-------------------|------------------|
| `int` | `"builtins.int"` |
| `list[int]` | `"builtins.list[builtins.int]"` |
| `dict[str, int]` | `"builtins.dict[builtins.str, builtins.int]"` |
| `tuple[int, int]` | `"tuple[builtins.int, builtins.int]"` |

We parse these strings to extract element types for containers.

---

## Part 3: Implementation

### Data Structures for Type Information

We create dataclasses to hold extracted type info:

```python
@dataclass
class FunctionTypeInfo:
    name: str
    params: list[tuple[str, str]]  # (param_name, type_string)
    return_type: str
    is_method: bool = False

@dataclass
class ClassTypeInfo:
    name: str
    fields: list[tuple[str, str]]  # (field_name, type_string)
    methods: list[FunctionTypeInfo]
    base_class: str | None = None

@dataclass
class TypeCheckResult:
    success: bool
    errors: list[str]
    functions: dict[str, FunctionTypeInfo]
    classes: dict[str, ClassTypeInfo]
    module_types: dict[str, str]
```

### Type Checking Flow

```
Source code
    |
    v
+-------------------+
| mypy.build()      |  <-- Run mypy's semantic analysis
+-------------------+
    |
    v
+-------------------+
| Extract types     |  <-- Walk mypy's AST, collect type info
+-------------------+
    |
    v
+-------------------+
| TypeCheckResult   |  <-- Package for IRBuilder consumption
+-------------------+
    |
    v
+-------------------+
| IRBuilder         |  <-- Use types during IR construction
+-------------------+
```

### Strict Mode Options

We configure mypy for strict checking:

```python
def create_mypy_options(strict: bool = False) -> Options:
    options = Options()
    options.python_version = (3, 10)
    options.strict_optional = True
    
    if strict:
        options.disallow_any_generics = True      # list -> error, list[int] -> ok
        options.disallow_untyped_defs = True      # All functions must have annotations
        options.disallow_untyped_calls = True     # Can't call untyped functions
        options.warn_return_any = True            # Warn if returning Any
        options.strict_equality = True            # Stricter == comparisons
    
    return options
```

The key option is `disallow_any_generics` - it requires `list[int]` instead of bare `list`.

### Passing Types to IRBuilder

The compiler creates a `MypyTypeInfo` container and passes it to IRBuilder:

```python
@dataclass
class MypyTypeInfo:
    functions: dict[str, FunctionTypeInfo]
    classes: dict[str, ClassTypeInfo]
    module_types: dict[str, str]

class IRBuilder:
    def __init__(self, module_name: str, mypy_types: MypyTypeInfo | None = None):
        self._mypy_types = mypy_types
    
    def _get_mypy_func_type(self, func_name: str) -> FunctionTypeInfo | None:
        if self._mypy_types is None:
            return None
        return self._mypy_types.functions.get(func_name)
```

### Using Mypy Types in IR Building

When building function IR, we prefer mypy's resolved types over AST annotations:

```python
def build_function(self, node: ast.FunctionDef) -> FuncIR:
    func_name = node.name
    
    # Try to get mypy's resolved types first
    mypy_func = self._get_mypy_func_type(func_name)
    
    for arg in node.args.args:
        if mypy_func and arg.arg in mypy_param_types:
            # Use mypy's resolved type (handles generics correctly)
            py_type = self._mypy_type_to_py_type(mypy_param_types[arg.arg])
            c_type = CType.from_python_type(py_type)
        else:
            # Fall back to AST annotation
            c_type = self._annotation_to_c_type(arg.annotation)
        
        params.append((arg.arg, c_type))
```

---

## Part 4: Making Strict Type Checking the Default

### The Change

Previously, type checking was opt-in:

```python
# Old default: no type checking
compile_source(source, "module")

# Had to explicitly enable
compile_source(source, "module", type_check=True, strict=True)
```

Now, strict type checking is the default:

```python
# New default: strict type checking enabled
compile_source(source, "module")

# Can disable for rapid prototyping
compile_source(source, "module", type_check=False)
```

### Why This Matters

1. **Code quality**: Type errors caught at compile time, not runtime
2. **Better error messages**: Mypy's errors are clearer than C compiler errors
3. **Future optimization**: Rich type info enables performance improvements

### CLI Changes

The `mpy-compile` command now has `--no-type-check` instead of `--type-check`:

```bash
# Default: strict type checking
mpy-compile mymodule.py

# Disable for untyped code
mpy-compile mymodule.py --no-type-check
```

### Updating Examples

All examples were updated with proper generic annotations:

```python
# Before (fails strict check)
def sum_list(items: list) -> int:
    ...

# After (passes strict check)
def sum_list(items: list[int]) -> int:
    ...
```

---

## Part 5: Future Optimization Opportunities

### What We Can Do With Type Information

With resolved types from mypy, future phases can implement:

| Optimization | Description | Est. Speedup |
|--------------|-------------|--------------|
| Native int arithmetic | `a + b` as C `+` instead of `mp_binary_op()` | 3-5x |
| Typed list access | Direct `items[]` access for `list[int]` | 2-3x |
| Typed iteration | Native C loop for `for x in list[int]` | 3-5x |
| Typed locals | Use `mp_int_t` for inferred `int` variables | 2x |

### Example: Type-Aware Code Generation

**Current** (without type optimization):
```c
// a + b where both are int
mp_obj_t result = mp_binary_op(MP_BINARY_OP_ADD, a_obj, b_obj);
```

**Future** (with type optimization):
```c
// a + b where both are known int from mypy
mp_int_t result = a + b;  // Direct C addition
```

The mypy integration lays the groundwork for these optimizations.

---

## Summary

We integrated mypy's type checking into the compiler:

1. **Type extraction**: Parse mypy's semantic analysis results into structured type info
2. **IRBuilder integration**: Pass type info to IRBuilder for use during code generation
3. **Strict by default**: Enable `disallow_any_generics` and other strict checks
4. **Future-ready**: Type information available for future optimization passes

### Files Changed

| File | Changes |
|------|---------|
| `type_checker.py` | Type extraction from mypy AST |
| `ir_builder.py` | `MypyTypeInfo` container, type-aware IR building |
| `compiler.py` | Default `type_check=True, strict=True` |
| `cli.py` | `--no-type-check` flag |
| `examples/*.py` | All updated with generic annotations |

### Test Results

- 480 unit tests pass
- 218 device tests pass on ESP32-C6
- All 20 example modules compile with strict type checking
