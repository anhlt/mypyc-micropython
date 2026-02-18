# From Monolith to Pipeline: Refactoring the Compiler to Full IR

*A technical deep-dive into replacing the 2400-line TypedPythonTranslator with a clean IR-based architecture.*

---

## The Problem with Direct Translation

Our original compiler had a single monolithic class: `TypedPythonTranslator`. At 2400+ lines, it was responsible for everything from parsing type annotations to emitting C code. The class had grown organically, with each new feature adding more methods like `_translate_list`, `_translate_dict`, `_translate_method_call_expr`, and dozens of helper functions.

The core issue was **mixing concerns**. When translating `result.append(i * i)`, the translator had to simultaneously:
1. Build the expression `i * i`
2. Determine it needs boxing
3. Generate the method call
4. Handle the temp variable for the result

This led to complex, interleaved code that was difficult to test and maintain.

## The New Architecture

We replaced this with a clean two-phase pipeline:

```
Python AST → IR Builder → IR → Emitters → C Code
```

### Key Files

| File | Responsibility |
|------|----------------|
| `ir.py` | IR dataclass definitions (ValueIR, StmtIR, ExprIR) |
| `ir_builder.py` | AST → IR translation |
| `function_emitter.py` | FuncIR/MethodIR → C code |
| `module_emitter.py` | Complete module assembly |
| `class_emitter.py` | ClassIR → C structs and vtables |
| `container_emitter.py` | Container operation IR → C code |

## IR Design: Values, Statements, and Instructions

### Value IR (Expression Results)

Every expression evaluates to a `ValueIR`:

```python
@dataclass
class ValueIR:
    ir_type: IRType  # OBJ, INT, FLOAT, BOOL

@dataclass
class ConstIR(ValueIR):
    value: int | float | str | bool | None

@dataclass
class NameIR(ValueIR):
    py_name: str
    c_name: str

@dataclass
class TempIR(ValueIR):
    name: str  # e.g., "_tmp1"

@dataclass
class BinOpIR(ValueIR):
    left: ValueIR
    op: str  # "+", "-", "*", etc.
    right: ValueIR
    left_prelude: list[InstrIR]
    right_prelude: list[InstrIR]
```

The key insight is separating the **value** from the **instructions needed to compute it**. A `BinOpIR` contains not just the left/right operands, but also any prelude instructions that must execute before the operation.

### Statement IR

Control flow and assignments:

```python
@dataclass
class ReturnIR(StmtIR):
    value: ValueIR | None
    prelude: list[InstrIR]

@dataclass
class IfIR(StmtIR):
    test: ValueIR
    body: list[StmtIR]
    orelse: list[StmtIR]
    test_prelude: list[InstrIR]

@dataclass
class ForRangeIR(StmtIR):
    loop_var: str
    c_loop_var: str
    start: ValueIR
    end: ValueIR
    step: ValueIR | None
    body: list[StmtIR]
    is_new_var: bool
```

### Instruction IR (Preludes)

Side-effecting operations that produce values:

```python
@dataclass
class TupleNewIR(InstrIR):
    result: TempIR
    items: list[ValueIR]

@dataclass
class MethodCallIR(InstrIR):
    result: TempIR | None
    receiver: ValueIR
    method: str
    args: list[ValueIR]
```

## Building IR from AST

The `IRBuilder` class transforms AST nodes into IR. Here's how it handles common patterns:

### Simple Expressions

```python
def _build_expr(self, expr: ast.expr, locals_: list[str]) -> tuple[ValueIR, list]:
    if isinstance(expr, ast.Constant):
        return self._build_constant(expr), []
    elif isinstance(expr, ast.Name):
        return self._build_name(expr, locals_), []
    elif isinstance(expr, ast.BinOp):
        return self._build_binop(expr, locals_)
    # ... more cases
```

The return type `tuple[ValueIR, list]` is crucial - it returns both the value and any prelude instructions needed to compute it.

### Binary Operations

```python
def _build_binop(self, expr: ast.BinOp, locals_: list[str]) -> tuple[BinOpIR, list]:
    left, left_prelude = self._build_expr(expr.left, locals_)
    right, right_prelude = self._build_expr(expr.right, locals_)
    
    op_map = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ...}
    c_op = op_map.get(type(expr.op), "+")
    
    return BinOpIR(
        ir_type=result_type,
        left=left,
        op=c_op,
        right=right,
        left_prelude=left_prelude,
        right_prelude=right_prelude,
    ), left_prelude + right_prelude
```

### Method Calls

Method calls like `result.append(i * i)` create a `MethodCallIR`:

```python
def _build_method_call(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
    receiver, recv_prelude = self._build_expr(expr.func.value, locals_)
    method_name = expr.func.attr
    
    args: list[ValueIR] = []
    all_preludes = list(recv_prelude)
    for arg in expr.args:
        val, prelude = self._build_expr(arg, locals_)
        all_preludes.extend(prelude)
        args.append(val)
    
    result = TempIR(ir_type=IRType.OBJ, name=self._fresh_temp())
    method_call = MethodCallIR(
        result=result, 
        receiver=receiver, 
        method=method_name, 
        args=args
    )
    
    return result, all_preludes + [method_call]
```

## Handling Self in Methods

Class methods require special handling for `self` access. We introduced dedicated IR types:

### Self Attribute Access

```python
@dataclass
class SelfAttrIR(ExprIR):
    attr_name: str
    attr_path: str  # C path like "base.x" for inherited fields
    result_type: IRType
```

When building method expressions, we detect `self.attr`:

```python
def _build_method_expr(self, expr: ast.expr, locals_: list[str], 
                       class_ir: ClassIR, native: bool) -> tuple[ValueIR, list]:
    if isinstance(expr, ast.Attribute):
        if isinstance(expr.value, ast.Name) and expr.value.id == "self":
            attr_name = expr.attr
            field = class_ir.get_field(attr_name)
            if field:
                return SelfAttrIR(
                    ir_type=IRType.from_c_type(field.c_type),
                    attr_name=attr_name,
                    attr_path=field.access_path,
                    result_type=IRType.from_c_type(field.c_type),
                ), []
```

### Self Augmented Assignment

A key fix during refactoring was handling `self.value += 1`:

```python
@dataclass
class SelfAugAssignIR(StmtIR):
    attr_name: str
    attr_path: str
    op: str  # "+=", "-=", etc.
    value: ValueIR
    prelude: list[InstrIR]
```

The builder detects this pattern:

```python
def _build_method_aug_assign(self, stmt: ast.AugAssign, ...):
    if isinstance(stmt.target, ast.Attribute):
        if isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == "self":
            attr_name = stmt.target.attr
            value, prelude = self._build_method_expr(stmt.value, ...)
            return SelfAugAssignIR(
                attr_name=attr_name,
                attr_path=attr_name,
                op=c_op,
                value=value,
                prelude=prelude,
            )
```

## RTuple Optimization

RTuples (`tuple[int, int]`) get special treatment for performance. Instead of boxing/unboxing through MicroPython's tuple API, we use C structs:

### RTuple Struct Definition

```c
typedef struct {
    mp_int_t f0;
    mp_int_t f1;
} rtuple_int_int_t;
```

### RTuple Initialization

When assigning a tuple literal to an RTuple variable:

```python
point: tuple[int, int] = (10, 20)
```

We detect the `TupleNewIR` in the prelude and emit direct initialization:

```python
def _emit_ann_assign(self, stmt: AnnAssignIR) -> list[str]:
    if stmt.c_type.startswith("rtuple_") and stmt.prelude:
        tuple_new = next((p for p in stmt.prelude if isinstance(p, TupleNewIR)), None)
        if tuple_new:
            items_c = [self._emit_expr(item)[0] for item in tuple_new.items]
            return [f"    {stmt.c_type} {stmt.c_target} = {{{', '.join(items_c)}}};"]
```

Generated C:
```c
rtuple_int_int_t point = {10, 20};
```

### RTuple Field Access

Subscript access on RTuples uses direct field access:

```python
# Python: point[0] + point[1]
# IR: SubscriptIR with is_rtuple=True, rtuple_index=0/1
```

```python
def _emit_subscript(self, sub: SubscriptIR) -> tuple[str, str]:
    if sub.is_rtuple and sub.rtuple_index is not None:
        return f"{value_expr}.f{sub.rtuple_index}", "mp_int_t"
    # ... normal subscript handling
```

Generated C:
```c
point.f0 + point.f1
```

### RTuple Return Boxing

Returning an RTuple requires boxing back to `mp_obj_t`:

```python
def _emit_return(self, stmt: ReturnIR) -> list[str]:
    if isinstance(stmt.value, NameIR):
        var_name = stmt.value.py_name
        if var_name in self.func_ir.rtuple_types:
            rtuple = self.func_ir.rtuple_types[var_name]
            items = ", ".join(f"mp_obj_new_int({expr}.f{i})" 
                            for i in range(rtuple.arity))
            return [
                f"    mp_obj_t _ret_items[] = {{{items}}};",
                f"    return mp_obj_new_tuple({rtuple.arity}, _ret_items);",
            ]
```

## Container Operations

The `ContainerEmitter` handles list/dict/set operations. A key improvement was making `_value_to_c` handle complex expressions:

```python
def _value_to_c(self, value: ValueIR) -> str:
    if isinstance(value, TempIR):
        return value.name
    elif isinstance(value, NameIR):
        return value.c_name
    elif isinstance(value, ConstIR):
        return self._const_to_c(value)
    elif isinstance(value, BinOpIR):
        left = self._value_to_c(value.left)
        right = self._value_to_c(value.right)
        return f"({left} {value.op} {right})"
    elif isinstance(value, UnaryOpIR):
        operand = self._value_to_c(value.operand)
        return f"({value.op}{operand})"
    # ... more cases
```

This allows expressions like `result.append(i * i)` to work correctly - the `BinOpIR` for `i * i` is passed to `_value_to_c` and emitted inline.

## Method Emission

The `MethodEmitter` handles both native (vtable) and MicroPython wrapper methods:

### Native Method

For virtual methods, we generate a native implementation:

```python
def emit_native(self, body: list[StmtIR]) -> str:
    params = [f"{class_ir.c_name}_obj_t *self"]
    for param_name, param_type in method_ir.params:
        params.append(f"{param_type.to_c_type_str()} {param_name}")
    
    lines = [f"static {ret_type} {method_ir.c_name}_native({', '.join(params)}) {{"]
    
    for stmt_ir in body:
        lines.extend(self._emit_statement(stmt_ir, native=True))
    
    lines.append("}")
    return "\n".join(lines)
```

### MicroPython Wrapper

The wrapper handles boxing/unboxing and dispatches to the native method:

```python
def emit_mp_wrapper(self, body: list[StmtIR] | None = None) -> str:
    # Unbox self
    lines.append(f"    {class_ir.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
    
    # Unbox parameters
    for i, (param_name, param_type) in enumerate(method_ir.params):
        if param_type == CType.MP_INT_T:
            lines.append(f"    mp_int_t {param_name} = mp_obj_get_int({src});")
    
    # Call native and box result
    if method_ir.is_virtual:
        lines.append(f"    return mp_obj_new_int({method_ir.c_name}_native(self));")
```

## Testing Results

After the refactoring:
- **37/37 C runtime tests pass** - All actual execution tests work correctly
- **271/271 total tests pass** - All unit tests pass including optimization assertions

The final fixes required careful type inference in `BinOpIR` to distinguish between:
- List/tuple operations that should use `mp_binary_op` (result is OBJ)
- Subscript arithmetic that should use native C operations (result is INT)

### BinOp Type Inference

A subtle but critical issue arose with expressions like `lst[i] + 1`. The problem:

1. `lst` has type `list` (OBJ)
2. `lst[i]` returns `mp_obj_t` (OBJ) at IR level
3. But semantically, `lst[i]` for a `list[int]` yields an int

The naive approach - "if either operand is OBJ, result is OBJ" - generated:

```c
mp_binary_op(MP_BINARY_OP_ADD, mp_list_get_int(lst, i), mp_obj_new_int(1))
```

This is wasteful - we're calling `mp_binary_op` for simple integer addition. The fix in `ir_builder.py`:

```python
def _build_binop(self, expr: ast.BinOp, locals_: list[str]) -> tuple[BinOpIR, list]:
    left, left_prelude = self._build_expr(expr.left, locals_)
    right, right_prelude = self._build_expr(expr.right, locals_)
    
    left_type = self._get_value_ir_type(left)
    right_type = self._get_value_ir_type(right)

    if left_type == IRType.OBJ or right_type == IRType.OBJ:
        # Key insight: subscript on list/dict returns mp_obj_t but contains int/float
        left_is_subscript = isinstance(left, SubscriptIR)
        right_is_subscript = isinstance(right, SubscriptIR)
        if left_is_subscript or right_is_subscript:
            # Arithmetic on subscript results - use native int
            result_type = IRType.INT
        else:
            # Container operations like lst * n - use mp_binary_op
            result_type = IRType.OBJ
    elif left_type == IRType.FLOAT or right_type == IRType.FLOAT:
        result_type = IRType.FLOAT
    else:
        result_type = IRType.INT
```

Now `lst[i] + 1` generates optimal C:

```c
(mp_obj_get_int(mp_list_get_int(lst, i)) + 1)
```

While `lst * 2` (list repetition) correctly generates:

```c
mp_binary_op(MP_BINARY_OP_MULTIPLY, lst, mp_obj_new_int(2))
```

### RTuple Unboxing from mp_obj_t

Another optimization challenge: when an RTuple variable receives its value from a function call or subscript (not a literal), we need to unbox the `mp_obj_t` tuple into our struct.

```python
point: tuple[int, int] = get_point()  # Returns mp_obj_t
x: int = point[0]  # Should use struct field access
```

The naive approach would lose the RTuple optimization. The fix: detect when the value source is a `TempIR` (function result) and emit unboxing code:

```python
def _emit_ann_assign(self, stmt: AnnAssignIR) -> list[str]:
    if stmt.c_type.startswith("rtuple_") and isinstance(stmt.value, TempIR):
        # Unbox mp_obj_t tuple to RTuple struct using mp_obj_tuple_t*
        rtuple_type = self._rtuple_types.get(stmt.target)
        if rtuple_type:
            field_assigns = []
            for i, elem_type in enumerate(rtuple_type.elem_types):
                if elem_type == IRType.FLOAT:
                    field_assigns.append(
                        f"mp_obj_get_float(tup->items[{i}])"
                    )
                else:
                    field_assigns.append(
                        f"mp_obj_get_int(tup->items[{i}])"
                    )
            return [
                f"    mp_obj_tuple_t *tup = MP_OBJ_TO_PTR({stmt.value.name});",
                f"    {stmt.c_type} {stmt.c_target} = {{{', '.join(field_assigns)}}};",
            ]
```

Generated C for `point: tuple[int, int] = get_point()`:

```c
mp_obj_tuple_t *tup = MP_OBJ_TO_PTR(_tmp1);
rtuple_int_int_t point = {mp_obj_get_int(tup->items[0]), mp_obj_get_int(tup->items[1])};
```

Now `point[0]` uses efficient field access `point.f0` instead of `mp_obj_subscr`.

## Lessons Learned

### 1. Separate Value from Prelude

The `tuple[ValueIR, list[InstrIR]]` return pattern was essential. It cleanly separates "what value does this produce?" from "what must happen first?"

### 2. IR Types Should Match Semantics

Having dedicated types like `SelfAttrIR`, `SelfAugAssignIR`, and `SelfMethodCallIR` makes the emitter much simpler - it knows exactly what construct it's dealing with.

### 3. RTuple Optimization Requires End-to-End Support

RTuples touch every part of the pipeline: type annotation parsing, variable tracking, subscript handling, and return boxing. The IR provides the thread that connects all these pieces.

### 4. Container Emitter Needs Expression Handling

Originally `_value_to_c` only handled simple values. Extending it to handle `BinOpIR`, `UnaryOpIR`, and `CompareIR` fixed issues with complex method arguments like `result.append(i * i)`.

## Future Work

1. **List Optimization IR**: Track list element types in IR for optimized access
2. **Exception Handling**: Add `TryIR`, `ExceptIR` for NLR-based exception support
3. **Generator Functions**: IR support for yield expressions and generator state machines

---

*The refactored code can be found in `src/mypyc_micropython/`. Key files: `ir.py` (IR definitions), `ir_builder.py` (AST to IR), `function_emitter.py` (IR to C).*
