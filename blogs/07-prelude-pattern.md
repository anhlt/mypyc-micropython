# The Prelude Pattern: Separating Side Effects from Values

*How a simple tuple return type solved one of the trickiest problems in compiling Python to C.*

---

When you compile `result.append(i * i)` from Python to C, where does the multiplication happen? Before the method call? During it? The answer seems obvious in Python — it's all one expression. But in C, you need to be explicit about order of operations and where intermediate values live.

This post explores the **prelude pattern** — a design that cleanly separates "what value does this expression produce" from "what must happen first to compute it." It's the key insight that made our IR-based compiler work.

## The Problem: Expressions with Side Effects

Consider this innocent Python code:

```python
def build_squares(n: int) -> list:
    result: list = []
    for i in range(n):
        result.append(i * i)
    return result
```

The expression `result.append(i * i)` looks atomic in Python, but to generate C, we need to:

1. Evaluate `i * i` (pure computation)
2. Box the result as a MicroPython object
3. Call `mp_obj_list_append()` (side effect)
4. Handle the return value (None for append)

Now consider something more complex:

```python
def nested_example(lst: list) -> int:
    return lst[get_index()] + compute_value()
```

Here we have:
- A function call `get_index()` that must execute first
- A subscript operation using that result
- Another function call `compute_value()`
- A binary operation combining both

The order matters. If `get_index()` modifies global state that `compute_value()` reads, swapping them would be a bug.

## The Naive Approach: String Concatenation Hell

Our first compiler tried to handle this by returning C code strings directly:

```python
def _translate_expr(self, expr) -> str:
    if isinstance(expr, ast.BinOp):
        left = self._translate_expr(expr.left)
        right = self._translate_expr(expr.right)
        return f"({left} + {right})"
    elif isinstance(expr, ast.Call):
        # Uh oh... this might need temp variables
        # And those need to be declared somewhere...
        pass
```

This breaks down immediately for method calls. We can't just inline `lst.append(x)` into a larger expression because:

1. `mp_obj_list_append()` returns `mp_obj_t` (None), not the list
2. We might need temp variables for intermediate results
3. C requires variables to be declared at specific scopes

We ended up with a "pending temps" queue, flushing accumulated setup code at statement boundaries. It was fragile, hard to debug, and broke in subtle ways with nested expressions.

## The Solution: Value + Prelude

The breakthrough was realizing that every expression produces two things:

1. **A value** — what the expression evaluates to
2. **A prelude** — instructions that must execute before the value is valid

We encode this as a simple return type:

```python
def _build_expr(self, expr: ast.expr, locals_: list[str]) -> tuple[ValueIR, list[InstrIR]]:
    """Build IR for an expression.
    
    Returns:
        tuple of (value_ir, prelude_instructions)
    """
```

The `ValueIR` represents the result — it might be a constant, a variable reference, a temp variable, or a complex expression. The `list[InstrIR]` contains any instructions that must execute first.

## How It Works: Building Expressions

### Simple Cases: No Prelude

Constants and variable references have no prelude — they're immediately available:

```python
def _build_constant(self, expr: ast.Constant) -> ConstIR:
    return ConstIR(ir_type=IRType.INT, value=42), []

def _build_name(self, expr: ast.Name, locals_: list[str]) -> NameIR:
    return NameIR(ir_type=IRType.INT, py_name="x", c_name="x"), []
```

### Binary Operations: Combining Preludes

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
    ), left_prelude + right_prelude
```

The BinOpIR stores both the operands AND their preludes. This is crucial for correct emission order.

### Method Calls: Creating Preludes

Here's where it gets interesting. A method call like `lst.append(x)`:

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
```

The method call instruction goes into the prelude, and we return a `TempIR` pointing to where the result will be stored.

### Container Literals: Multi-Step Construction

List literals like `[1, 2, 3]` require multiple C statements:

```python
def _build_list(self, expr: ast.List, locals_: list[str]) -> tuple[ValueIR, list]:
    items: list[ValueIR] = []
    all_preludes: list = []
    
    for elt in expr.elts:
        val, prelude = self._build_expr(elt, locals_)
        all_preludes.extend(prelude)
        items.append(val)
    
    result = TempIR(ir_type=IRType.OBJ, name=self._fresh_temp())
    list_new = ListNewIR(result=result, items=items)
    
    return result, all_preludes + [list_new]
```

## Instruction IR: The Prelude Contents

Preludes contain `InstrIR` nodes — side-effecting operations that produce values:

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
class TupleNewIR(InstrIR):
    result: TempIR
    items: list[ValueIR]

@dataclass
class DictNewIR(InstrIR):
    result: TempIR
    keys: list[ValueIR]
    values: list[ValueIR]
```

Each instruction knows its result temp variable and its inputs. The emitter can then generate proper C code in the right order.

## Emitting Preludes: Order Matters

The emitter processes preludes before using their values:

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

## Real Example: `result.append(i * i)`

Let's trace through `result.append(i * i)`:

### Step 1: Build the Expression

```python
# Building i * i
i_left = NameIR(py_name="i", c_name="i")
i_right = NameIR(py_name="i", c_name="i")
multiply = BinOpIR(left=i_left, op="*", right=i_right)
# Prelude: [] (no side effects)

# Building result.append(i * i)
receiver = NameIR(py_name="result", c_name="result")
result_temp = TempIR(name="_tmp1")
method_call = MethodCallIR(
    result=result_temp,
    receiver=receiver,
    method="append",
    args=[multiply]
)
# Value: result_temp
# Prelude: [method_call]
```

### Step 2: Build the Statement

```python
ExprStmtIR(
    expr=result_temp,  # The value (unused for append)
    prelude=[method_call]  # The actual work
)
```

### Step 3: Emit C Code

```python
def _emit_expr_stmt(self, stmt: ExprStmtIR) -> list[str]:
    lines = self._emit_prelude(stmt.prelude)
    # For ExprStmt, we just emit the prelude; the value is discarded
    return lines
```

Generated C:

```c
mp_obj_list_append(result, mp_obj_new_int((i * i)));
```

## Nested Example: Complex Expressions

Consider `return items[get_idx()].value + compute()`:

### IR Structure

```
ReturnIR:
  value: BinOpIR(+)
    left: AttributeIR(.value)
      value: SubscriptIR
        value: NameIR("items")
        slice: CallIR("get_idx")
          prelude: [call_instr_1]  # _tmp1 = get_idx()
    right: CallIR("compute")
      prelude: [call_instr_2]  # _tmp2 = compute()
  prelude: [call_instr_1, call_instr_2]
```

### Generated C

```c
mp_obj_t _tmp1 = module_get_idx();
mp_obj_t _tmp2 = module_compute();
mp_obj_t _subscript = mp_obj_subscr(items, _tmp1, MP_OBJ_SENTINEL);
mp_obj_t _attr = mp_load_attr(_subscript, MP_QSTR_value);
return mp_binary_op(MP_BINARY_OP_ADD, _attr, _tmp2);
```

The prelude ensures `get_idx()` and `compute()` are called in the right order, their results are stored, and then used in the final expression.

## Benefits of the Prelude Pattern

### 1. Correct Evaluation Order

Side effects happen in the order Python specifies. No accidental reordering.

### 2. Clean Temp Variable Management

Temps are created at IR build time, not scattered through string manipulation.

### 3. Composability

Complex expressions compose naturally — each sub-expression's prelude is accumulated.

### 4. Separation of Concerns

The IR builder focuses on structure; the emitter focuses on C syntax.

### 5. Debuggability

You can inspect the IR and see exactly what instructions will execute and in what order.

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

For `if items.pop() > 0:`, the prelude contains the `pop()` call, and the test uses the temp result:

```c
mp_obj_t _tmp1 = mp_call_method_1(...);  // Prelude
if (mp_obj_get_int(_tmp1) > 0) {         // Test uses _tmp1
    ...
}
```

## RTuple Optimization: Prelude Detection

The prelude pattern enabled our RTuple optimization. When we see:

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

The emitter can detect the `TupleNewIR` in the prelude and emit optimized struct initialization:

```c
// Instead of: mp_obj_t _tmp1 = mp_obj_new_tuple(2, items); ...
rtuple_int_int_t point = {10, 20};  // Direct struct init!
```

Without the prelude pattern, this optimization would require complex pattern matching on string output.

## Lessons Learned

### 1. Make Side Effects Explicit

The prelude pattern forces you to think about what's pure and what has effects. This clarity propagates through the entire compiler.

### 2. Tuples Are Your Friend

The `tuple[ValueIR, list[InstrIR]]` return type is simple but powerful. Every expression builder follows the same contract.

### 3. Accumulation > Generation

Building up preludes and emitting them later is more robust than generating code inline. You have full information when you finally emit.

### 4. IR Enables Optimization

With structured preludes, we can inspect, reorder (when safe), and optimize before emission. String concatenation doesn't allow this.

## Future Directions

The prelude pattern opens doors for:

1. **Dead Code Elimination**: If a prelude's result is never used, skip emitting it
2. **Common Subexpression Elimination**: Detect duplicate preludes and reuse temps
3. **Instruction Scheduling**: Reorder independent preludes for better cache behavior
4. **Exception Handling**: Preludes provide natural points for try/catch boundaries

---

*The prelude pattern is implemented in `ir_builder.py` (building) and `function_emitter.py` (emission). The instruction types are defined in `ir.py`.*
