# Integrating Mypy for Strict Type Checking

*Using mypy's semantic analysis to validate code and unlock future optimizations.*

---

When you write `def add(a: int, b: int) -> int`, Python treats it as documentation. But for a compiler targeting native code, these type hints are instructions for generating efficient code. This post explores how we integrated mypy's type checker to validate code at compile time and generate type-aware IR.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) — Why type information matters and how AST falls short
2. [C Background](#part-2-c-background-for-python-developers) — Boxing, unboxing, and the MicroPython object system
3. [Implementation](#part-3-implementation) — How we built mypy integration and what it enables

---

# Part 1: Compiler Theory

## The Problem with AST-Only Type Information

Our compiler transforms typed Python to C:

```
Python source -> AST -> IR -> C code
```

When parsing `def foo(x: int) -> int`, Python's `ast` module gives us the annotation nodes directly. But AST annotations have fundamental limitations:

### Limitation 1: No Resolution of Generics

```python
def process(items: list[int]) -> int:
    return items[0]
```

At the AST level, `list` and `list[int]` look almost identical - both are just `ast.Subscript` nodes. The AST doesn't "understand" that `int` is the element type.

### Limitation 2: No Type Inference

```python
def process(items: list[int]) -> int:
    total = 0          # What type is total? AST doesn't know
    for x in items:    # What type is x? AST sees list, not list[int]
        total += x
    return total
```

The AST has no way to infer that `total` is `int` or that `x` iterates over integers.

### Limitation 3: No Validation

```python
def broken(x: int) -> str:
    return x + 1  # Type error: returns int, not str
```

The AST parses this just fine. The type error only surfaces when:
- The C compiler sees mismatched types, OR
- The code crashes at runtime

Neither is a good developer experience.

## What Mypy Provides

Mypy performs **semantic analysis** - it builds a complete type model of your code:

| Information | AST Only | With Mypy |
|-------------|----------|-----------|
| `list[int]` element type | Not available | `int` |
| Inferred local types | Unknown | Resolved |
| Type errors | Runtime crash | Compile-time error |
| Generic resolution | Raw annotation | Fully resolved |

### The Type String Format

Mypy represents resolved types as qualified strings:

| Python Annotation | Mypy Type String |
|-------------------|------------------|
| `int` | `"builtins.int"` |
| `list[int]` | `"builtins.list[builtins.int]"` |
| `dict[str, int]` | `"builtins.dict[builtins.str, builtins.int]"` |
| `tuple[int, int]` | `"tuple[builtins.int, builtins.int]"` |

We parse these strings to extract element types for containers.

## How Type Annotations Affect Our IR

The IR builder maps Python type annotations to internal IR types:

| Python Type | IR Type | Purpose |
|-------------|---------|---------|
| `int` | `MP_INT_T` | Native integer operations |
| `float` | `MP_FLOAT_T` | Native float operations |
| `bool` | `BOOL` | Native boolean operations |
| `str` | `MP_OBJ_T` | Object - runtime operations |
| `list` | `MP_OBJ_T` | Object - runtime operations |
| `dict` | `MP_OBJ_T` | Object - runtime operations |
| `None` | `VOID` | No return value |
| (untyped) | `MP_OBJ_T` | Fallback - runtime dispatch |

Primitive types (`int`, `float`, `bool`) get special handling - they're unboxed to native C types for efficient arithmetic. Object types stay as `mp_obj_t` and use MicroPython's runtime APIs.

## The Compilation Pipeline with Type Checking

With mypy integration, our pipeline gains a validation step:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Python    │ → │    Mypy     │ → │     AST     │ → │     IR      │ → │   C Code    │
│   Source    │    │  Type Check │    │   (Tree)    │    │  (Typed)    │    │  (String)   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                         ↑                   ↑                   ↑                   ↑
                    Validate +          ast.parse()         IR Builder          Emitters
                    Extract types
```

Type errors are caught early, before any C code is generated.

---

# Part 2: C Background for Python Developers

Before diving into implementation, let's understand how MicroPython represents Python objects in C.

## The Universal Object Type: mp_obj_t

In MicroPython, every Python object is represented as `mp_obj_t`:

```c
typedef void *mp_obj_t;  // Simplified: it's a pointer-sized value
```

This single type can hold:
- Small integers (encoded directly in the pointer)
- Pointers to heap-allocated objects
- Special values like `None`, `True`, `False`

## Boxing and Unboxing

**Boxing** wraps a native C value into a Python object:

```c
mp_int_t n = 42;                    // Native C integer
mp_obj_t obj = mp_obj_new_int(n);   // Boxed Python integer
```

**Unboxing** extracts the native value from a Python object:

```c
mp_obj_t obj = ...;                 // Python integer object
mp_int_t n = mp_obj_get_int(obj);   // Native C integer
```

### Why Boxing/Unboxing Matters

MicroPython functions always receive `mp_obj_t` parameters (boxed). To do efficient arithmetic, we need to:

1. **Unbox** at function entry - extract native values
2. **Compute** using native C operations
3. **Box** at function return - wrap result back

```c
// Python: def add(a: int, b: int) -> int: return a + b

static mp_obj_t add(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);   // Unbox
    mp_int_t b = mp_obj_get_int(b_obj);   // Unbox
    return mp_obj_new_int(a + b);          // Compute + Box
}
```

Without type annotations, we can't unbox - we don't know the types!

## Boxing/Unboxing Functions by Type

| Type | Unbox Function | Box Function |
|------|----------------|--------------|
| `int` | `mp_obj_get_int(obj)` | `mp_obj_new_int(n)` |
| `float` | `mp_obj_get_float(obj)` | `mp_obj_new_float(f)` |
| `bool` | `mp_obj_is_true(obj)` | `mp_const_true` / `mp_const_false` |
| `None` | - | `mp_const_none` |

For object types (`str`, `list`, `dict`), no boxing/unboxing is needed - they're already `mp_obj_t`.

## Runtime Type Dispatch: mp_binary_op

Without type information, MicroPython uses runtime dispatch:

```c
mp_obj_t result = mp_binary_op(MP_BINARY_OP_ADD, a, b);
```

This function must:
1. Check the types of both `a` and `b`
2. Look up the appropriate `__add__` method
3. Handle type coercion (e.g., `int + float`)
4. Return the boxed result

This is flexible but slow - the type check happens on every operation.

## Typed vs Untyped: Performance Comparison

```c
// TYPED: int + int (knows types at compile time)
mp_int_t a = mp_obj_get_int(a_obj);  // Unbox once
mp_int_t b = mp_obj_get_int(b_obj);  // Unbox once
return mp_obj_new_int(a + b);         // Direct C addition, box once

// UNTYPED: unknown + unknown (runtime dispatch)
return mp_binary_op(MP_BINARY_OP_ADD, a, b);  // Type check every time
```

The typed version:
- Unboxes once at function entry
- Uses direct C `+` operator (single CPU instruction)
- Boxes once at return

The untyped version:
- Calls `mp_binary_op()` which must check types
- Looks up method tables
- Handles type coercion
- Returns boxed result

For arithmetic-heavy code, typed can be **3-5x faster**.

---

# Part 3: Implementation

Now let's see how we integrated mypy and what the IR looks like for each type.

## Mypy's Build API

Mypy isn't just a command-line tool - it has a programmatic API:

```python
from mypy import build as mypy_build
from mypy.options import Options

options = Options()
options.python_version = (3, 10)
options.disallow_any_generics = True   # Require list[int], not list
options.disallow_untyped_defs = True   # All functions must have annotations

result = mypy_build.build(
    sources=[mypy_build.BuildSource(path, module_name, text=source)],
    options=options
)

if result.errors:
    # Type errors found - fail compilation
    for error in result.errors:
        print(error)
```

## Type Checking Flow

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

## Data Structures for Type Information

We create dataclasses to hold extracted type info:

```python
@dataclass
class FunctionTypeInfo:
    name: str
    params: list[tuple[str, str]]  # (param_name, type_string)
    return_type: str
    is_method: bool = False

@dataclass
class TypeCheckResult:
    success: bool
    errors: list[str]
    functions: dict[str, FunctionTypeInfo]
    classes: dict[str, ClassTypeInfo]
    module_types: dict[str, str]
```

## Strict Mode: Why We Made It Default

Previously, type checking was opt-in:

```python
# Old default: no type checking
compile_source(source, "module")
```

Now, strict type checking is the default:

```python
# New default: strict type checking enabled
compile_source(source, "module")

# Can disable for rapid prototyping
compile_source(source, "module", type_check=False)
```

The key strict option is `disallow_any_generics` - it requires `list[int]` instead of bare `list`.

## IR Output for Each Type

Let's see the concrete IR and C code generated for each type annotation.

### Primitive Types (`int`, `float`, `bool`)

Primitive types are unboxed to native C types. Here's an example with `int`:

```python
def add(a: int, b: int) -> int:
    return a + b
```

**IR Output:**
```
def add(a: MP_INT_T, b: MP_INT_T) -> MP_INT_T:
  c_name: test_int_add
  max_temp: 0
  locals: {a: MP_INT_T, b: MP_INT_T}
  body:
    return (a + b)
```

**Generated C:**
```c
static mp_obj_t test_int_add(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);   // Unbox to native int
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_obj_new_int((a + b));       // Box result back
}
```

The pattern is identical for `float` and `bool` - only the unbox/box functions differ (see the quick reference table in the Summary).

### Object Types (`str`, `list`, `dict`)

Object types stay as `mp_obj_t` - no unboxing happens:

```python
def greet(name: str) -> str:
    return "Hello " + name
```

**IR Output:**
```
def greet(name: MP_OBJ_T) -> MP_OBJ_T:
  c_name: test_str_greet
  max_temp: 0
  locals: {name: MP_OBJ_T}
  body:
    return ("Hello " + name)
```

**Generated C:**
```c
static mp_obj_t test_str_greet(mp_obj_t name_obj) {
    mp_obj_t name = name_obj;                    // No unboxing needed

    return mp_binary_op(MP_BINARY_OP_ADD,        // Runtime string concat
        mp_obj_new_str("Hello ", 6), name);
}
```

The same pattern applies to `list` and `dict` - they use `MP_OBJ_T` and runtime APIs.

### `None` Return Type

```python
def do_nothing() -> None:
    pass
```

**IR Output:**
```
def do_nothing() -> VOID:
  c_name: test_none_do_nothing
  max_temp: 0
  body:
    pass
```

**Generated C:**
```c
static mp_obj_t test_none_do_nothing(void) {
    return mp_const_none;                        // Return None singleton
}
```

### Untyped (No Annotations)

```python
def add(a, b):
    return a + b
```

**IR Output:**
```
def add(a: MP_OBJ_T, b: MP_OBJ_T) -> MP_OBJ_T:
  c_name: test_untyped_add
  max_temp: 0
  locals: {a: MP_OBJ_T, b: MP_OBJ_T}
  body:
    return (a + b)
```

**Generated C:**
```c
static mp_obj_t test_untyped_add(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_obj_t a = a_obj;
    mp_obj_t b = b_obj;

    return mp_binary_op(MP_BINARY_OP_ADD, a, b); // Runtime type dispatch
}
```

Without type annotations, everything is `mp_obj_t` and uses runtime dispatch.

## What's NOT Yet Optimized: Generic Type Parameters

Currently, `list[int]` and `list` generate **identical IR**:

```python
# Both produce the same IR!
def get_first(items: list[int]) -> int:
    return items[0]

def get_first(items: list) -> int:
    return items[0]
```

**IR Output (same for both):**
```
def get_first(items: MP_OBJ_T) -> MP_INT_T:
  c_name: list_int_get_first
  max_temp: 0
  locals: {items: MP_OBJ_T}
  body:
    return items[0]
```

The element type `int` from `list[int]` is **not yet extracted** from the annotation. This is a future optimization opportunity.

## Future Optimization Opportunities

With resolved types from mypy, future phases can implement:

| Optimization | Description | Est. Speedup |
|--------------|-------------|--------------|
| Native int arithmetic | `a + b` as C `+` instead of `mp_binary_op()` | 3-5x |
| Typed list access | Direct `items->items[]` for `list[int]` | 2-3x |
| Typed iteration | Native C loop for `for x in list[int]` | 3-5x |
| Typed locals | Use `mp_int_t` for inferred `int` variables | 2x |

### Current vs Future: Typed Iteration

**Current** (generic iteration):
```c
// for x in items where items: list[int]
mp_obj_iter_buf_t iter_buf;
mp_obj_t iter = mp_getiter(items, &iter_buf);
mp_obj_t x;
while ((x = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
    mp_int_t val = mp_obj_get_int(x);  // Unbox every iteration
    // ...
}
```

**Future** (typed iteration):
```c
// for x in items where items: list[int] - knowing it's a list of ints
mp_obj_list_t *list = MP_OBJ_TO_PTR(items);
for (size_t i = 0; i < list->len; i++) {
    mp_int_t val = mp_obj_get_int(list->items[i]);  // Direct array loop
    // ...
}
```

The mypy integration captures `list[int]` type information - we just need to use it in code generation.

---

## Summary

We integrated mypy's type checking into the compiler:

1. **Type validation**: Catch type errors at compile time, not runtime
2. **Type extraction**: Parse mypy's semantic analysis results into structured type info
3. **IR generation**: Use type annotations to generate typed IR with proper boxing/unboxing
4. **Strict by default**: Enable `disallow_any_generics` and other strict checks
5. **Future-ready**: Type information available for future optimization passes

### Type-to-IR Quick Reference

| Python Type | IR Type | C Type | Unbox | Box |
|-------------|---------|--------|-------|-----|
| `int` | `MP_INT_T` | `mp_int_t` | `mp_obj_get_int()` | `mp_obj_new_int()` |
| `float` | `MP_FLOAT_T` | `mp_float_t` | `mp_get_float_checked()` | `mp_obj_new_float()` |
| `bool` | `BOOL` | `bool` | `mp_obj_is_true()` | `mp_const_true/false` |
| `str/list/dict` | `MP_OBJ_T` | `mp_obj_t` | (none) | (none) |
| `None` | `VOID` | - | - | `mp_const_none` |
| (untyped) | `MP_OBJ_T` | `mp_obj_t` | (none) | (none) |

### Files Changed

| File | Changes |
|------|---------|
| `type_checker.py` | New module for mypy integration |
| `compiler.py` | Default `type_check=True, strict=True` |
| `cli.py` | `--no-type-check` flag |
| `examples/*.py` | All updated with generic annotations |

### Test Results

- 480 unit tests pass
- All 21 example modules compile with strict type checking
