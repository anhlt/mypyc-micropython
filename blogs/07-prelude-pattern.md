# The Prelude Pattern: Separating Side Effects from Values

*How a simple tuple return type solved one of the trickiest problems in compiling Python to C.*

---

When you compile `result.append(i * i)` from Python to C, where does the multiplication happen? Before the method call? During it? The answer seems obvious in Python — it's all one expression. But in C, you need to be explicit about order of operations and where intermediate values live.

This post explores the **prelude pattern** — a design that cleanly separates "what value does this expression produce" from "what must happen first to compute it." It's the key insight that made our IR-based compiler work.

## Table of Contents

1. [Compiler Theory](#part-1-compiler-theory) — Why expression evaluation order matters in compilation
2. [C Background](#part-2-c-background-for-python-developers) — Statements vs expressions, temporary variables, and evaluation order
3. [Implementation](#part-3-implementation) — How we built the prelude pattern

---

# Part 1: Compiler Theory

## The Expression Evaluation Problem

Compilers must decide **when** and **where** each computation happens. In Python, expressions can have side effects:

```python
def example():
    return get_a() + get_b()  # Which function runs first?
```

Python guarantees left-to-right evaluation. Our generated C must preserve this order.

## Pure vs Impure Expressions

Compiler theory distinguishes:

| Type | Description | Example |
|------|-------------|---------|
| **Pure** | No side effects, same inputs = same outputs | `a + b`, `x * 2` |
| **Impure** | Has side effects or depends on external state | `list.pop()`, `get_input()` |

Pure expressions can be reordered freely. Impure expressions cannot.

```python
# These are NOT equivalent if get_a() modifies state that get_b() reads
return get_a() + get_b()  # Must call get_a() first
return get_b() + get_a()  # Would call get_b() first - different behavior!
```

## The Compilation Pipeline and Side Effects

Our pipeline must track side effects through each phase:

```
+------------------+    +------------------+    +------------------+
|  Python Source   | -> |       IR         | -> |     C Code       |
|                  |    |                  |    |                  |
| lst.append(x*2)  |    | Value + Prelude  |    | Sequential stmts |
+------------------+    +------------------+    +------------------+
```

The challenge: Python allows impure expressions anywhere. C separates statements (side effects) from expressions (values).

## Why Naive Translation Fails

Consider translating `result.append(i * i)`:

```python
# Python: One expression with embedded side effect
result.append(i * i)
```

A naive approach generates C expressions inline:

```c
// Attempt 1: Inline everything
mp_obj_list_append(result, mp_obj_new_int(i * i));  // Works!
```

This works for simple cases. But what about:

```python
# Python: Multiple side effects in one expression
return items[get_index()] + compute_value()
```

```c
// Attempt 2: Inline fails
return mp_obj_subscr(items, get_index(), ...) + compute_value();  // Wrong!
// Problem: get_index() and compute_value() might be called in wrong order
// C doesn't guarantee left-to-right evaluation of function arguments!
```

## The Key Insight: Separate Value from Setup

Every expression produces two things:

1. **A value** — what the expression evaluates to
2. **A prelude** — instructions that must execute before the value is valid

```
Expression: items[get_index()] + compute_value()

Value: (_tmp1 + _tmp2)

Prelude: [
    _tmp1 = mp_obj_subscr(items, get_index(), ...),
    _tmp2 = compute_value()
]
```

The prelude captures side effects. The value is now pure — just variable references.

## Prelude Accumulation

Preludes compose naturally. For nested expressions, we accumulate preludes:

```
Expression: outer(inner())

Building inner():
  Value: _tmp1
  Prelude: [_tmp1 = inner()]

Building outer(inner()):
  Value: _tmp2
  Prelude: [_tmp1 = inner(), _tmp2 = outer(_tmp1)]
         = inner_prelude + [outer_call]
```

This recursive structure handles arbitrary nesting.

---

# Part 2: C Background for Python Developers

## Statements vs Expressions

C strictly separates **statements** (do something) from **expressions** (compute a value):

```c
// Statement: Does something, no value
printf("Hello");

// Expression: Computes a value
3 + 4

// Assignment is a statement that uses an expression
int x = 3 + 4;  // Statement containing expression
```

Python blurs this distinction. `list.append(x)` is an expression (returns None) that has a side effect. In C, we must be explicit.

## Temporary Variables

Temporary variables store intermediate results:

```c
// Without temps: Arguments evaluated in unspecified order
return func_a() + func_b();  // C doesn't guarantee order!

// With temps: Explicit order
int _tmp1 = func_a();  // First
int _tmp2 = func_b();  // Second
return _tmp1 + _tmp2;  // Now order is guaranteed
```

**Visual: Temp variable flow**

```
Python: get_a() + get_b()

C with temps:
  +-------+     +-------+
  | tmp1  | <-- | get_a |  Step 1: Call get_a, store result
  +-------+     +-------+
  
  +-------+     +-------+
  | tmp2  | <-- | get_b |  Step 2: Call get_b, store result
  +-------+     +-------+
  
  +-------+     +-------+     +-------+
  | result| <-- | tmp1  | + | tmp2  |  Step 3: Add stored results
  +-------+     +-------+     +-------+
```

## C Evaluation Order Pitfalls

C has **undefined** argument evaluation order:

```c
// DANGEROUS: Order of f() and g() is undefined!
int result = combine(f(), g());

// f() might run first, or g() might run first
// Different compilers, different results
```

Python guarantees left-to-right. To preserve Python semantics in C:

```c
// SAFE: Explicit ordering with temps
int _tmp1 = f();  // Guaranteed first
int _tmp2 = g();  // Guaranteed second
int result = combine(_tmp1, _tmp2);
```

## MicroPython Object Model

In MicroPython, everything is an `mp_obj_t`:

```c
// mp_obj_t is a pointer-sized value that represents any Python object
typedef void *mp_obj_t;

// Method calls return mp_obj_t
mp_obj_t result = mp_obj_list_pop(list);

// Even "void" operations return mp_const_none
mp_obj_list_append(list, item);  // Returns mp_const_none
```

This means every Python expression has a C value, even if we ignore it.

## Scope and Declaration

C requires variable declaration before use:

```c
// C89: Declarations at block start
{
    int a;
    int b;
    // ... code ...
    a = compute();  // OK
}

// C99+: Declarations anywhere
{
    // ... code ...
    int a = compute();  // OK
}
```

Our generated code uses C99-style declarations, placing temps where needed:

```c
static mp_obj_t func(...) {
    // Temps declared inline as needed
    mp_obj_t _tmp1 = get_index();
    mp_obj_t _tmp2 = items[_tmp1];
    // ...
}
```

---

# Part 3: Implementation

## The Core Data Structure

We encode the prelude pattern as a return type:

```python
def _build_expr(self, expr: ast.expr, locals_: list[str]) -> tuple[ValueIR, list[InstrIR]]:
    """Build IR for an expression.
    
    Returns:
        tuple of (value_ir, prelude_instructions)
    """
```

- `ValueIR`: The result value (constant, variable, temp, or compound expression)
- `list[InstrIR]`: Instructions that must execute first

## Simple Cases: No Prelude

Constants and variable references are pure — no prelude needed:

```python
def _build_constant(self, expr: ast.Constant) -> tuple[ConstIR, list]:
    return ConstIR(ir_type=IRType.INT, value=42), []
    #                                              ^^ Empty prelude

def _build_name(self, expr: ast.Name, locals_: list[str]) -> tuple[NameIR, list]:
    return NameIR(ir_type=IRType.INT, py_name="x", c_name="x"), []
```

## Binary Operations: Combining Preludes

For `a + b`, we build both operands and combine their preludes:

```python
def _build_binop(self, expr: ast.BinOp, locals_: list[str]) -> tuple[BinOpIR, list]:
    left, left_prelude = self._build_expr(expr.left, locals_)
    right, right_prelude = self._build_expr(expr.right, locals_)
    
    return BinOpIR(
        ir_type=IRType.INT,
        left=left,
        op="+",
        right=right,
        left_prelude=left_prelude,
        right_prelude=right_prelude,
    ), left_prelude + right_prelude  # Combine preludes in order
```

**Visual: Prelude combination**

```
Expression: get_a() + get_b()

Build get_a():
  Value: _tmp1
  Prelude: [call_a]

Build get_b():
  Value: _tmp2
  Prelude: [call_b]

Build get_a() + get_b():
  Value: BinOpIR(_tmp1, +, _tmp2)
  Prelude: [call_a, call_b]  # Left prelude, then right prelude
```

## Method Calls: Creating Preludes

Method calls have side effects and create preludes:

```python
def _build_method_call(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
    receiver, recv_prelude = self._build_expr(expr.func.value, locals_)
    
    args: list[ValueIR] = []
    all_preludes = list(recv_prelude)
    for arg in expr.args:
        val, prelude = self._build_expr(arg, locals_)
        all_preludes.extend(prelude)
        args.append(val)
    
    # Create a temp variable for the result
    result = TempIR(ir_type=IRType.OBJ, name=self._fresh_temp())
    
    # The method call itself becomes a prelude instruction
    method_call = MethodCallIR(
        result=result,
        receiver=receiver,
        method="append",
        args=args
    )
    
    return result, all_preludes + [method_call]
    #      ^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #      Value   Prelude (includes the call!)
```

## Instruction IR Types

Preludes contain `InstrIR` nodes — side-effecting operations:

```python
@dataclass
class ListNewIR(InstrIR):
    result: TempIR
    items: list[ValueIR]

@dataclass
class MethodCallIR(InstrIR):
    result: TempIR | None
    receiver: ValueIR
    method: str
    args: list[ValueIR]

@dataclass
class DictNewIR(InstrIR):
    result: TempIR
    keys: list[ValueIR]
    values: list[ValueIR]
```

Each instruction knows its result temp and inputs.

## Emitting Preludes

The emitter processes preludes before using values:

```python
def _emit_return(self, stmt: ReturnIR) -> list[str]:
    # First, emit all prelude instructions
    lines = self._emit_prelude(stmt.prelude)
    
    # Now the value is ready to use
    if stmt.value is None:
        lines.append("    return mp_const_none;")
    else:
        value_expr, _ = self._emit_expr(stmt.value)
        boxed = self._box_value(value_expr, ...)
        lines.append(f"    return {boxed};")
    
    return lines

def _emit_prelude(self, prelude: list[InstrIR]) -> list[str]:
    lines = []
    for instr in prelude:
        if isinstance(instr, ListNewIR):
            lines.extend(self._emit_list_new(instr))
        elif isinstance(instr, MethodCallIR):
            lines.extend(self._emit_method_call(instr))
        # ... other instruction types
    return lines
```

## Complete Example: `result.append(i * i)`

Let's trace through the full compilation:

### Step 1: Build the Expression

```python
# Building i * i
i_left = NameIR(py_name="i", c_name="i")
i_right = NameIR(py_name="i", c_name="i")
multiply = BinOpIR(left=i_left, op="*", right=i_right)
# Value: BinOpIR
# Prelude: [] (pure expression)

# Building result.append(i * i)
receiver = NameIR(py_name="result", c_name="result")
result_temp = TempIR(name="_tmp1")
method_call = MethodCallIR(
    result=result_temp,
    receiver=receiver,
    method="append",
    args=[multiply]
)
# Value: result_temp (points to call result)
# Prelude: [method_call]
```

### Step 2: Build the Statement

```python
ExprStmtIR(
    expr=result_temp,      # The value (unused for append)
    prelude=[method_call]  # The actual work
)
```

### Step 3: Emit C Code

```python
def _emit_expr_stmt(self, stmt: ExprStmtIR) -> list[str]:
    lines = self._emit_prelude(stmt.prelude)
    # For ExprStmt, we emit prelude; value is discarded
    return lines
```

**Generated C:**

```c
mp_obj_list_append(result, mp_obj_new_int((i * i)));
```

## Complex Example: Nested Calls

For `return items[get_idx()].value + compute()`:

### IR Structure

```
ReturnIR:
  prelude: [
    CallIR(result=_tmp1, func="get_idx"),
    SubscriptIR(result=_tmp2, obj=items, index=_tmp1),
    AttrIR(result=_tmp3, obj=_tmp2, attr="value"),
    CallIR(result=_tmp4, func="compute"),
  ]
  value: BinOpIR(left=_tmp3, op="+", right=_tmp4)
```

### Generated C

```c
mp_obj_t _tmp1 = module_get_idx();                              // 1. Call get_idx
mp_obj_t _tmp2 = mp_obj_subscr(items, _tmp1, MP_OBJ_SENTINEL);  // 2. Subscript
mp_obj_t _tmp3 = mp_load_attr(_tmp2, MP_QSTR_value);            // 3. Get attribute
mp_obj_t _tmp4 = module_compute();                              // 4. Call compute
return mp_binary_op(MP_BINARY_OP_ADD, _tmp3, _tmp4);            // 5. Add and return
```

The prelude guarantees correct evaluation order.

## Statements Get Preludes Too

The pattern extends to statements. An `if` statement's test might need setup:

```python
@dataclass
class IfIR(StmtIR):
    test: ValueIR
    body: list[StmtIR]
    orelse: list[StmtIR]
    test_prelude: list[InstrIR]  # Setup for the test expression
```

For `if items.pop() > 0:`:

```c
mp_obj_t _tmp1 = mp_obj_list_pop(items);  // Prelude: execute pop()
if (mp_obj_get_int(_tmp1) > 0) {          // Test uses _tmp1
    ...
}
```

## RTuple Optimization: Prelude Detection

The prelude pattern enables optimizations. When we see:

```python
point: tuple[int, int] = (10, 20)
```

The IR builder creates:

```python
AnnAssignIR(
    target="point",
    c_type="rtuple_int_int_t",
    value=TempIR("_tmp1"),
    prelude=[TupleNewIR(result="_tmp1", items=[10, 20])]
)
```

The emitter detects `TupleNewIR` in the prelude and emits optimized code:

```c
// Instead of:
mp_obj_t _tmp1 = mp_obj_new_tuple(2, items);
rtuple_int_int_t point = unpack(_tmp1);

// Optimized:
rtuple_int_int_t point = {10, 20};  // Direct struct initialization!
```

## Benefits of the Prelude Pattern

| Benefit | Description |
|---------|-------------|
| **Correct Order** | Side effects happen in Python-specified order |
| **Clean Temps** | Temp variables created at IR build time |
| **Composability** | Sub-expression preludes accumulate naturally |
| **Separation** | IR builder handles structure; emitter handles syntax |
| **Debuggability** | IR shows exactly what executes and when |
| **Optimization** | Can inspect/transform before emission |

## Testing

Unit tests verify prelude handling:

```python
def test_method_call_in_expression(self):
    source = '''
def test() -> int:
    items: list = [1, 2, 3]
    return items.pop() + 10
'''
    result = compile_source(source, "test")
    # Verify temp variable is created
    assert "_tmp" in result
    # Verify pop happens before addition
    assert result.index("mp_obj_list_pop") < result.index("mp_binary_op")
```

---

## Conclusion

The prelude pattern solves expression evaluation order by:

1. **Separating concerns**: Value (what) vs prelude (how/when)
2. **Accumulating side effects**: Preludes compose recursively
3. **Explicit ordering**: Emitted C preserves Python semantics

The `tuple[ValueIR, list[InstrIR]]` return type is simple but powerful. Every expression builder follows the same contract, making the compiler predictable and extensible.

---

*The prelude pattern is implemented in `ir_builder.py` (building) and `function_emitter.py` (emission). The instruction types are defined in `ir.py`.*
