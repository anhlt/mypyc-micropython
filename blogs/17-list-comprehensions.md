# List Comprehensions: Compiling Pythonic Patterns to C

*How we transform one of Python's most beloved features into efficient MicroPython C code.*

---

List comprehensions are one of Python's most expressive features. The ability to write `[x * x for x in range(10)]` instead of a five-line loop is what makes Python feel elegant. But how do you compile this concise syntax to C, where there's no equivalent construct?

This post walks through the implementation of list comprehension support in our Python-to-MicroPython compiler, from parsing the AST to emitting optimized C code.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) - How list comprehensions fit in the compilation pipeline
2. [C Background](#part-2-c-background-for-python-developers) - MicroPython list APIs and iterator patterns
3. [Implementation](#part-3-implementation) - Building `ListCompIR` and emitting C code

---

# Part 1: Compiler Theory

## What Is a List Comprehension?

A list comprehension is syntactic sugar that combines:
1. **Iteration** - looping over a sequence
2. **Transformation** - applying an expression to each element
3. **Filtering** (optional) - selecting elements based on a condition

```python
# Basic comprehension
squares = [x * x for x in range(10)]

# With filter condition
evens = [x for x in range(20) if x % 2 == 0]
```

Semantically, these are equivalent to:

```python
# Basic comprehension expanded
squares = []
for x in range(10):
    squares.append(x * x)

# With filter expanded
evens = []
for x in range(20):
    if x % 2 == 0:
        evens.append(x)
```

## The Compilation Challenge

List comprehensions pose several challenges for compilation:

| Challenge | Description |
|-----------|-------------|
| **Embedded scope** | The loop variable `x` is created implicitly |
| **Expression position** | The comprehension appears where a value is expected |
| **Conditional logic** | The `if` clause is optional and can have multiple conditions |
| **Iterator variety** | Can iterate over `range()`, lists, or any iterable |

Unlike a regular `for` loop (which is a statement), a list comprehension is an **expression** that produces a value. This means it can appear in contexts like:

```python
return [x * 2 for x in items]  # In return statement
result = [x for x in data if x > 0]  # In assignment
print([i ** 2 for i in range(5)])  # As function argument
```

## Two Compilation Strategies

We can compile list comprehensions two ways:

### Strategy 1: Desugar to Loop (What We Do)

Transform the comprehension into equivalent IR nodes representing a loop with appends:

```
ListComp AST -> ListCompIR -> emit_list_comp() -> C loop code
```

### Strategy 2: Inline Function (Alternative)

Some compilers create an inline function that builds and returns the list. We chose not to do this because:
- Extra function call overhead
- More complex stack frame management
- Harder to optimize for `range()` iteration

## The AST Structure

Python's AST represents list comprehensions with `ast.ListComp`:

```python
import ast

source = "[x * x for x in range(n) if x % 2 == 0]"
tree = ast.parse(source, mode='eval')
listcomp = tree.body

# ListComp(
#   elt=BinOp(left=Name(id='x'), op=Mult(), right=Name(id='x')),
#   generators=[
#     comprehension(
#       target=Name(id='x'),
#       iter=Call(func=Name(id='range'), args=[Name(id='n')]),
#       ifs=[Compare(left=BinOp(...), ops=[Eq()], comparators=[Constant(0)])],
#       is_async=0
#     )
#   ]
# )
```

The key components:
- **`elt`** - The element expression (what goes in the list)
- **`generators`** - List of comprehension clauses (we support one)
- **`target`** - The loop variable
- **`iter`** - What to iterate over
- **`ifs`** - Optional filter conditions

---

# Part 2: C Background for Python Developers

## MicroPython List API

MicroPython provides C functions for list manipulation:

### Creating Lists

```c
// Create empty list with initial capacity
mp_obj_t list = mp_obj_new_list(0, NULL);

// Create list with initial items
mp_obj_t items[] = {mp_obj_new_int(1), mp_obj_new_int(2)};
mp_obj_t list = mp_obj_new_list(2, items);
```

The first argument is the initial size, and the second is an array of initial elements (or `NULL` for empty).

### Appending to Lists

```c
// Append a single item
mp_obj_list_append(list, mp_obj_new_int(42));
```

This is equivalent to Python's `list.append(42)`. The item is boxed (wrapped in `mp_obj_t`) before appending.

## Iterator Protocol in C

For iterating over arbitrary iterables (not just `range()`), MicroPython uses:

```c
// Get iterator from iterable
mp_obj_iter_buf_t iter_buf;
mp_obj_t iter = mp_getiter(iterable, &iter_buf);

// Iterate until exhausted
mp_obj_t item;
while ((item = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
    // Process item
}
```

Key points:
- **`mp_obj_iter_buf_t`** - Stack-allocated buffer for small iterators (avoids heap allocation)
- **`mp_getiter()`** - Returns an iterator object for the iterable
- **`mp_iternext()`** - Returns next item, or `MP_OBJ_STOP_ITERATION` when exhausted
- **`MP_OBJ_STOP_ITERATION`** - Sentinel value indicating iteration complete

## Range Optimization

For `range()` iteration, we can avoid the iterator protocol entirely and use native C loops:

```c
// Python: for x in range(10)
// Optimized C:
mp_int_t x;
for (x = 0; x < 10; x++) {
    // Body
}
```

This is significantly faster because:
1. No iterator object allocation
2. No function calls per iteration
3. Loop variable stays as native `mp_int_t` (not boxed)

## Boxing and Unboxing

When iterating over a list (not range), the loop variable is `mp_obj_t`:

```c
// Iterator-based: loop variable is boxed
mp_obj_t x;
while ((x = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
    // x is mp_obj_t - operations need mp_binary_op()
    mp_obj_t doubled = mp_binary_op(MP_BINARY_OP_MULTIPLY, x, mp_obj_new_int(2));
}
```

For range-based iteration, the variable is native:

```c
// Range-based: loop variable is native int
mp_int_t x;
for (x = 0; x < n; x++) {
    // x is mp_int_t - can use native C operations
    mp_int_t squared = x * x;
}
```

This type difference is critical for generating correct code.

---

# Part 3: Implementation

## The ListCompIR Node

We represent list comprehensions with a dedicated IR node:

```python
@dataclass
class ListCompIR(InstrIR):
    """List comprehension: [expr for var in iterable] or [expr for var in iterable if cond]."""

    result: TempIR                          # Temp variable holding result list
    loop_var: str                           # Python variable name
    c_loop_var: str                         # C variable name (sanitized)
    iterable: ValueIR                       # What to iterate over
    element: ValueIR                        # Expression for each element
    condition: ValueIR | None = None        # Optional filter condition
    
    # Preludes for nested expressions
    iter_prelude: list[InstrIR] = field(default_factory=list)
    element_prelude: list[InstrIR] = field(default_factory=list)
    condition_prelude: list[InstrIR] = field(default_factory=list)
    
    # Range optimization fields
    is_range: bool = False
    range_start: ValueIR | None = None
    range_end: ValueIR | None = None
    range_step: ValueIR | None = None
```

The key insight is storing **preludes** for each sub-expression. The element expression might have side effects that must execute inside the loop, not before it.

## Building ListCompIR from AST

The `_build_list_comp()` method in `IRBuilder` transforms `ast.ListComp`:

```python
def _build_list_comp(
    self, expr: ast.ListComp, locals_: list[str]
) -> tuple[ValueIR, list]:
    """Build IR for list comprehension."""
    if not expr.generators:
        return ConstIR(ir_type=IRType.OBJ, value=[]), []

    # We support single generator only
    gen = expr.generators[0]
    
    if not isinstance(gen.target, ast.Name):
        return ConstIR(ir_type=IRType.OBJ, value=[]), []

    loop_var = gen.target.id
    c_loop_var = sanitize_name(loop_var)

    # Track the loop variable
    if loop_var not in locals_:
        locals_.append(loop_var)
        self._var_types[loop_var] = "mp_obj_t"

    # Build iterable expression
    iterable, iter_prelude = self._build_expr(gen.iter, locals_)

    # Check if iterable is range() for optimization
    is_range = False
    range_start = range_end = range_step = None

    if (isinstance(gen.iter, ast.Call) and 
        isinstance(gen.iter.func, ast.Name) and 
        gen.iter.func.id == "range"):
        is_range = True
        # Extract range arguments...
        # For range-based, loop var is int
        self._var_types[loop_var] = "mp_int_t"

    # Build element expression
    element, element_prelude = self._build_expr(expr.elt, locals_)

    # Build condition if present
    condition = None
    condition_prelude = []
    if gen.ifs:
        condition, condition_prelude = self._build_expr(gen.ifs[0], locals_)
```

The critical steps:
1. **Extract loop variable** from the generator target
2. **Detect range() optimization** by checking if iter is a `Call` to `range`
3. **Set correct type** for loop variable (`mp_int_t` for range, `mp_obj_t` otherwise)
4. **Build all sub-expressions** with their preludes

## Range Detection and Optimization

When we detect `range()`, we extract the arguments:

```python
if gen.iter.func.id == "range":
    is_range = True
    range_args = gen.iter.args
    
    if len(range_args) == 1:
        # range(n) -> start=0, end=n
        range_start = ConstIR(ir_type=IRType.INT, value=0)
        range_end, _ = self._build_expr(range_args[0], locals_)
    elif len(range_args) == 2:
        # range(start, end)
        range_start, _ = self._build_expr(range_args[0], locals_)
        range_end, _ = self._build_expr(range_args[1], locals_)
    elif len(range_args) == 3:
        # range(start, end, step)
        range_start, _ = self._build_expr(range_args[0], locals_)
        range_end, _ = self._build_expr(range_args[1], locals_)
        range_step, _ = self._build_expr(range_args[2], locals_)
    
    # Loop variable is native int for range
    self._var_types[loop_var] = "mp_int_t"
```

## Emitting C Code

The `emit_list_comp()` method generates C code based on whether we have range or iterator:

```python
def emit_list_comp(self, instr: ListCompIR) -> list[str]:
    """Emit list comprehension as inline loop."""
    lines: list[str] = []
    result_name = instr.result.name

    # Create empty result list
    lines.append(f"    mp_obj_t {result_name} = mp_obj_new_list(0, NULL);")

    if instr.is_range:
        lines.extend(self._emit_list_comp_range(instr, result_name))
    else:
        lines.extend(self._emit_list_comp_iter(instr, result_name))

    return lines
```

### Range-Based Emission

For `[x * x for x in range(n)]`:

```python
def _emit_list_comp_range(self, instr: ListCompIR, result_name: str) -> list[str]:
    lines: list[str] = []
    c_loop_var = instr.c_loop_var

    # Declare loop variable as native int
    lines.append(f"    mp_int_t {c_loop_var};")

    # Store end in temp to avoid re-evaluation
    end_c = self._value_to_c(instr.range_end)
    end_var = f"{result_name}_end"
    lines.append(f"    mp_int_t {end_var} = {end_c};")

    # Generate for loop
    lines.append(f"    for ({c_loop_var} = 0; {c_loop_var} < {end_var}; {c_loop_var}++) {{")

    # Handle optional condition
    if instr.condition is not None:
        cond_c = self._value_to_c(instr.condition)
        lines.append(f"        if ({cond_c}) {{")
        element_c = self._box_value_ir(instr.element)
        lines.append(f"            mp_obj_list_append({result_name}, {element_c});")
        lines.append("        }")
    else:
        element_c = self._box_value_ir(instr.element)
        lines.append(f"        mp_obj_list_append({result_name}, {element_c});")

    lines.append("    }")
    return lines
```

Generated C for `[x * x for x in range(n)]`:

```c
mp_obj_t _tmp1 = mp_obj_new_list(0, NULL);
mp_int_t x;
mp_int_t _tmp1_end = n;
for (x = 0; x < _tmp1_end; x++) {
    mp_obj_list_append(_tmp1, mp_obj_new_int((x * x)));
}
return _tmp1;
```

### Iterator-Based Emission

For `[x * 2 for x in items]` where `items` is a list:

```python
def _emit_list_comp_iter(self, instr: ListCompIR, result_name: str) -> list[str]:
    lines: list[str] = []
    c_loop_var = instr.c_loop_var
    iter_var = f"{result_name}_iter"
    iter_buf_var = f"{result_name}_iter_buf"

    # Get iterable
    iter_c = self._value_to_c(instr.iterable)

    # Declare loop variable as mp_obj_t
    lines.append(f"    mp_obj_t {c_loop_var};")
    lines.append(f"    mp_obj_iter_buf_t {iter_buf_var};")
    lines.append(f"    mp_obj_t {iter_var} = mp_getiter({iter_c}, &{iter_buf_var});")
    
    # While loop with mp_iternext
    lines.append(
        f"    while (({c_loop_var} = mp_iternext({iter_var})) != MP_OBJ_STOP_ITERATION) {{"
    )

    # Emit element with mp_binary_op for boxed operands
    element_c = self._box_value_ir(instr.element)
    lines.append(f"        mp_obj_list_append({result_name}, {element_c});")

    lines.append("    }")
    return lines
```

Generated C for `[x * 2 for x in items]`:

```c
mp_obj_t _tmp1 = mp_obj_new_list(0, NULL);
mp_obj_t x;
mp_obj_iter_buf_t _tmp1_iter_buf;
mp_obj_t _tmp1_iter = mp_getiter(items, &_tmp1_iter_buf);
while ((x = mp_iternext(_tmp1_iter)) != MP_OBJ_STOP_ITERATION) {
    mp_obj_list_append(_tmp1, mp_binary_op(MP_BINARY_OP_MULTIPLY, x, mp_obj_new_int(2)));
}
return _tmp1;
```

## The Type-Aware Operation Bug

A critical bug we discovered: when the loop variable is `mp_obj_t` (iterator-based), operations like `x * 2` or `x > 0` cannot use native C operators.

### The Problem

```python
# Python
[x for x in items if x > 0]
```

Naive code generation would produce:

```c
// WRONG: x is mp_obj_t (a pointer), not an integer!
if (x > 0) {  // Compares pointer value, not integer value!
    mp_obj_list_append(result, x);
}
```

### The Fix

We check the type of operands in `_value_to_c()`:

```python
def _value_to_c(self, value: ValueIR) -> str:
    if isinstance(value, CompareIR):
        left_c = self._value_to_c(value.left)
        right_c = self._value_to_c(value.right)
        
        # Check if operands are mp_obj_t
        left_is_obj = isinstance(value.left, (NameIR, TempIR)) and value.left.ir_type == IRType.OBJ
        right_is_obj = isinstance(value.right, (NameIR, TempIR)) and value.right.ir_type == IRType.OBJ
        
        if left_is_obj or right_is_obj:
            # Use mp_binary_op for runtime comparison
            cmp_op_map = {
                "<": "MP_BINARY_OP_LESS",
                ">": "MP_BINARY_OP_MORE",
                "==": "MP_BINARY_OP_EQUAL",
                # ...
            }
            mp_op = cmp_op_map.get(value.op)
            if mp_op:
                # Box literal if comparing with object
                if not left_is_obj:
                    left_c = f"mp_obj_new_int({left_c})"
                if not right_is_obj:
                    right_c = f"mp_obj_new_int({right_c})"
                return f"mp_obj_is_true(mp_binary_op({mp_op}, {left_c}, {right_c}))"
        
        return f"({left_c} {value.op} {right_c})"
```

Now `[x for x in items if x > 0]` generates:

```c
while ((x = mp_iternext(_tmp1_iter)) != MP_OBJ_STOP_ITERATION) {
    if (mp_obj_is_true(mp_binary_op(MP_BINARY_OP_MORE, x, mp_obj_new_int(0)))) {
        mp_obj_list_append(_tmp1, x);
    }
}
```

## Complete Compilation Example
Let's trace `filter_positive` through the entire pipeline:
**Python source:**
```python
def filter_positive(items: list[int]) -> list[int]:
    return [x for x in items if x > 0]
```

**IR dump** (generated with `mpy-compile --dump-ir text --ir-function filter_positive`):
```
def filter_positive(items: MP_OBJ_T) -> MP_OBJ_T:
  c_name: list_comprehension_filter_positive
  max_temp: 1
  locals: {items: MP_OBJ_T, x: MP_OBJ_T}
  body:
    # prelude:
      _tmp1 = [x for x in items if (x > 0)]
    return _tmp1
```

Key observations from the IR:
- **`MP_OBJ_T`** types - Both `items` and loop variable `x` are boxed objects
- **`max_temp: 1`** - Only one temporary variable needed for the result list
- **Prelude pattern** - The `ListCompIR` instruction executes before the return value is ready
- **Compact representation** - The IR shows the comprehension in familiar Python syntax
**Generated C:**
```c
static mp_obj_t list_comprehension_filter_positive(mp_obj_t items_obj) {
    mp_obj_t items = items_obj;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp1_iter_buf;
    mp_obj_t _tmp1_iter = mp_getiter(items, &_tmp1_iter_buf);
    while ((x = mp_iternext(_tmp1_iter)) != MP_OBJ_STOP_ITERATION) {
        if (mp_obj_is_true(mp_binary_op(MP_BINARY_OP_MORE, x, mp_obj_new_int(0)))) {
            mp_obj_list_append(_tmp1, x);
        }
    }
    return _tmp1;
}
```

## More IR Examples

### Range-Based Comprehension

**Python:**
```python
def squares(n: int) -> list[int]:
    return [x * x for x in range(n)]
```

**IR dump:**
```
def squares(n: MP_INT_T) -> MP_OBJ_T:
  c_name: list_comprehension_squares
  max_temp: 1
  locals: {n: MP_INT_T, x: MP_INT_T}
  body:
    # prelude:
      _tmp1 = [(x * x) for x in range(n)]
    return _tmp1
```

Notice the difference:
- **`MP_INT_T`** for `n` and `x` - Native integers for range-based iteration
- **`range(n)`** in the IR - Signals optimized C for-loop generation

### Comprehension with Filter

**Python:**
```python
def evens(n: int) -> list[int]:
    return [x for x in range(n) if x % 2 == 0]
```

**IR dump:**
```
def evens(n: MP_INT_T) -> MP_OBJ_T:
  c_name: list_comprehension_evens
  max_temp: 1
  locals: {n: MP_INT_T, x: MP_INT_T}
  body:
    # prelude:
      _tmp1 = [x for x in range(n) if ((x % 2) == 0)]
    return _tmp1
```

The filter condition `((x % 2) == 0)` is preserved in the IR. Since `x` is `MP_INT_T`, the generated C uses native operators.

## Testing

We verify list comprehensions with:

1. **Unit tests** - Check generated C contains expected patterns
2. **C runtime tests** - Compile and execute with gcc
3. **Device tests** - Run on real ESP32 hardware

Example device test:

```python
def test_list_comprehension():
    test(
        "squares",
        "import list_comprehension as lc; print(lc.squares(5))",
        "[0, 1, 4, 9, 16]",
    )
    test(
        "filter_positive",
        "import list_comprehension as lc; print(lc.filter_positive([-1, 2, -3, 4]))",
        "[2, 4]",
    )
```

---

## Summary

List comprehensions required:

1. **New IR node** (`ListCompIR`) to represent the comprehension structure
2. **Range detection** to optimize `range()` iterations as native C loops
3. **Type-aware emission** to use `mp_binary_op()` for `mp_obj_t` operands
4. **Prelude handling** to ensure sub-expression side effects occur at the right time

The result: Pythonic list comprehensions compile to efficient C code, with range-based comprehensions using native loops and iterator-based ones properly handling boxed values.

Key lessons:
- **Type matters** - The loop variable type (`mp_int_t` vs `mp_obj_t`) determines which operations are valid
- **Optimization is essential** - Range detection avoids expensive iterator protocol
- **Testing catches bugs** - The `mp_obj_t` comparison bug only appeared on device testing
