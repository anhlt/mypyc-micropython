# The Central Dispatch: How _value_to_c Turns IR into C Expressions

*Every IR node must eventually become a C expression string. When two node types were missing from the dispatch, the compiler silently replaced real code with `/* unknown value */`.*

## Table of Contents

- [Part 1: Compiler Theory, The Dispatch Problem](#part-1-compiler-theory-the-dispatch-problem)
- [Part 2: C Background, Expressions vs Statements in Generated Code](#part-2-c-background-expressions-vs-statements-in-generated-code)
- [Part 3: Implementation, Two Missing Cases and How They Were Found](#part-3-implementation-two-missing-cases-and-how-they-were-found)

## Part 1: Compiler Theory, The Dispatch Problem

This project compiles typed Python into MicroPython C modules. The compilation pipeline:

```
Python source -> ast.parse() -> IRBuilder -> FuncIR/ClassIR -> Emitters -> C code
```

The emitter phase is not a single component. It is split into two parallel systems that handle different contexts:

1. **FunctionEmitter** -- emits statements (assignments, if/else, loops, returns)
2. **ContainerEmitter** -- emits expressions that appear inside container operations, method chains, and preludes

Both systems must be able to convert any IR value node into a C expression string. But they do it differently.

### Why two emitters?

The split follows from the prelude pattern. Every expression in the IR returns `tuple[ValueIR, list[InstrIR]]`:

- **ValueIR**: The result value (a constant, variable name, temp variable, or compound expression)
- **list[InstrIR]**: Instructions that must execute before the value is valid

FunctionEmitter handles the top-level flow: loops, conditionals, assignments. It processes `StmtIR` nodes. When it encounters a value, it calls `_emit_expr()`, which returns a C expression string and a type tag.

ContainerEmitter handles everything that happens inside container operations and preludes. When FunctionEmitter encounters a `MethodCallIR` on a list or dict, it delegates to ContainerEmitter. When a prelude needs to evaluate a complex expression to set up a temp variable, ContainerEmitter does the work.

### The dispatch function

At the core of ContainerEmitter is `_value_to_c()`. This function takes any `ValueIR` node and returns a C expression string. It is a large `isinstance` dispatch:

```python
def _value_to_c(self, value: ValueIR) -> str:
    """Convert a ValueIR to its C expression string."""
    if isinstance(value, TempIR):
        return value.name
    elif isinstance(value, NameIR):
        return value.c_name
    elif isinstance(value, FuncRefIR):
        return f"MP_OBJ_FROM_PTR(&{value.c_name}_obj)"
    elif isinstance(value, ModuleRefIR):
        return _emit_dotted_module_import(value.module_name)
    elif isinstance(value, ModuleAttrIR):
        mod_import = _emit_dotted_module_import(value.module_name)
        return f"mp_load_attr({mod_import}, MP_QSTR_{value.attr_name})"
    elif isinstance(value, ConstIR):
        return self._const_to_c(value)
    elif isinstance(value, BinOpIR):
        # ... arithmetic
    elif isinstance(value, CompareIR):
        # ... comparisons
    elif isinstance(value, SelfAttrIR):
        return f"self->{value.attr_path}"
    elif isinstance(value, ClassInstantiationIR):
        # ... class constructor call
    # ... 15+ more cases
    return "/* unknown value */"
```

That last line is the critical default. When a new IR node type is added to the IR builder but not handled in `_value_to_c`, the generated C silently contains `/* unknown value */` wherever that node appears. The C compiler sees it as a comment. The surrounding expression gets a garbage value or fails to compile.

### The invariant

The invariant is simple: **every `ValueIR` subclass must have a case in `_value_to_c`.** When the IR builder creates a new node type, the dispatch table must be updated.

This invariant was violated twice. The consequences surfaced when we tried to compile a real MVU application that exercised patterns the test suite had not covered.

### The two missing node types

FunctionEmitter's `_emit_expr()` already handled both `ModuleCallIR` and `DynamicCallIR` -- they worked fine in statement context. But ContainerEmitter's `_value_to_c()` did not handle them. The two functions evolved independently, and the gap was invisible until a specific pattern forced both node types into a prelude context.

```text
FunctionEmitter._emit_expr()     ContainerEmitter._value_to_c()
-------------------------------  --------------------------------
TempIR             OK            TempIR               OK
NameIR             OK            NameIR               OK
ConstIR            OK            ConstIR              OK
BinOpIR            OK            BinOpIR              OK
ModuleCallIR       OK            ModuleCallIR         MISSING
DynamicCallIR      OK            DynamicCallIR        MISSING
...                              ...
```

The gap existed because most module calls and dynamic calls appear as top-level statements (where FunctionEmitter handles them). They only appear inside `_value_to_c` when they are part of a method chain or nested expression in a prelude -- a pattern that the MVU application happened to exercise.

## Part 2: C Background, Expressions vs Statements in Generated Code

### The context split in C

C makes a hard distinction between statements and expressions. A statement performs an action. An expression produces a value.

```c
// Statement: performs assignment
mp_obj_t result = mp_call_function_1(fn, arg);

// Expression: produces a value (can be used inside another expression)
mp_call_function_1(fn, arg)
```

In generated C, the same MicroPython API call can appear in either context. When the compiler emits a method chain like `Button("-").size(60, 40).on(7, 2).build()`, each step is an expression whose result feeds into the next call.

### How preludes work in generated C

The IR builder breaks complex expressions into a sequence of temp assignments (the "prelude") plus a final value. The prelude creates named variables, and the final expression references those variables.

For example, the Python expression:

```python
Label("MVU Counter Demo").text_color(0xFFFFFF).build()
```

Becomes an IR prelude with temp assignments:

```text
_tmp4 = lvgl_mvu.dsl.Label("MVU Counter Demo").text_color(16777215)
_tmp5 = _tmp4.build()
```

The emitter must produce C for each prelude instruction. Each instruction contains inner values (function arguments, receivers) that must be converted to C expression strings. That is where `_value_to_c` gets called recursively.

### GCC statement expressions

When a prelude instruction produces a value that must be used inline, the emitter wraps it in a GCC statement expression:

```c
mp_obj_t _tmp4 = ({
    mp_obj_t __method[3];
    mp_load_method(
        mp_call_function_1(
            mp_load_attr(
                mp_load_attr(
                    mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                    MP_QSTR_dsl),
                MP_QSTR_Label),
            mp_obj_new_str("MVU Counter Demo", 16)),
        MP_QSTR_text_color,
        __method);
    __method[2] = mp_obj_new_int(16777215);
    mp_call_method_n_kw(1, 0, __method);
});
```

Inside this block, `mp_call_function_1(...)` is the inner call to `Label("MVU Counter Demo")`. That call had to produce a C expression string. The `_value_to_c` function is responsible for generating it.

### The MicroPython call API

MicroPython provides several call functions, optimized by argument count:

```c
mp_call_function_0(fn)                    // 0 args
mp_call_function_1(fn, arg)               // 1 arg
mp_call_function_2(fn, arg1, arg2)        // 2 args
mp_call_function_n_kw(fn, n, kw, args[])  // N args + keyword args
```

When `_value_to_c` handles a call IR node, it must choose the right call variant based on argument count, and box each argument from its IR type to `mp_obj_t` if needed.

### Boxing: IR types to mp_obj_t

MicroPython represents all values as `mp_obj_t` at the API boundary. The compiler uses unboxed types internally (native `mp_int_t`, `mp_float_t`, `bool`) for performance. When a value crosses into a function call argument, it must be "boxed":

```c
// Unboxed int -> boxed mp_obj_t
mp_obj_new_int(42)

// Unboxed float -> boxed mp_obj_t
mp_obj_new_float(3.14)

// Unboxed bool -> boxed mp_obj_t
(cond ? mp_const_true : mp_const_false)

// Already mp_obj_t -> no boxing needed
some_obj
```

The `_box_value_ir()` helper in ContainerEmitter does this conversion. It calls `_value_to_c()` to get the raw C expression, then wraps it based on the IR type.

## Part 3: Implementation, Two Missing Cases and How They Were Found

### The trigger: compiling counter_mvu.py

The counter MVU application (`examples/counter_mvu.py`) is a 148-line Python program that creates a counter UI using the MVU (Model-View-Update) architecture. Its `view()` function builds a widget tree with method chains:

```python
def view(model: Model) -> Widget:
    count_text: str = "Count: " + str(model.count)

    return Screen()(
        VStack(spacing=20).size(320, 240)(
            Label("MVU Counter Demo").text_color(0xFFFFFF).build(),
            Label(count_text).text_color(0x00FF00).build(),
            HStack(spacing=10)(
                Button("-").size(60, 40).on(LV_EVENT_CLICKED, MSG_DECREMENT).build(),
                Button("Reset").size(80, 40).on(LV_EVENT_CLICKED, MSG_RESET).build(),
                Button("+").size(60, 40).on(LV_EVENT_CLICKED, MSG_INCREMENT).build(),
            ),
        ),
    )
```

This function exercises two patterns that had never appeared together in the test suite:

1. **Module function calls as method receivers**: `Button("-").size(60, 40)` where `Button("-")` is a `ModuleCallIR` (calling a function from an imported module), and `.size()` is a method call on the result.

2. **Callable-call-result**: `Screen()(...)` where `Screen()` returns a callable, and we immediately call the result with arguments. This produces a `DynamicCallIR`.

### Bug D: ModuleCallIR in preludes

When the IR builder processes `Button("-").size(60, 40)`, it generates:

```text
_tmp9 = lvgl_mvu.dsl.Button("-").size(60, 40)
```

The method call `.size(60, 40)` is a `MethodCallIR`. Its receiver is the result of `Button("-")`, which is a `ModuleCallIR`. The ContainerEmitter processes the `MethodCallIR` and calls `_value_to_c()` on the receiver to get the C expression for the object being called.

Before the fix, `_value_to_c()` had no case for `ModuleCallIR`. It fell through to the default:

```c
// BEFORE: receiver is /* unknown value */
mp_obj_t __method[4];
mp_load_method(/* unknown value */, MP_QSTR_size, __method);
```

The C compiler treats `/* unknown value */` as a comment. The `mp_load_method` call gets no first argument. This is either a compile error or undefined behavior.

### The ModuleCallIR fix

The fix adds a case for `ModuleCallIR` that mirrors what FunctionEmitter already does:

```python
elif isinstance(value, ModuleCallIR):
    # Module function call: module.func(args, **kwargs)
    mod_import = _emit_dotted_module_import(value.module_name)
    fn_expr = f"mp_load_attr({mod_import}, MP_QSTR_{value.func_name})"
    boxed_args = [self._box_value_ir(a) for a in value.args]
    # Build keyword args (interleaved: key, value, key, value, ...)
    boxed_kwargs = []
    for kw_name, kw_val in value.kwargs:
        boxed_kwargs.append(f"MP_OBJ_NEW_QSTR(MP_QSTR_{kw_name})")
        boxed_kwargs.append(self._box_value_ir(kw_val))
    n_args = len(boxed_args)
    n_kw = len(value.kwargs)
    if n_kw > 0:
        all_args = boxed_args + boxed_kwargs
        args_str = ", ".join(all_args)
        return (
            f"mp_call_function_n_kw({fn_expr}, "
            f"{n_args}, {n_kw}, (const mp_obj_t[]){{{args_str}}})"
        )
    if n_args == 0:
        return f"mp_call_function_0({fn_expr})"
    elif n_args == 1:
        return f"mp_call_function_1({fn_expr}, {boxed_args[0]})"
    elif n_args == 2:
        return f"mp_call_function_2({fn_expr}, {boxed_args[0]}, {boxed_args[1]})"
    else:
        args_str = ", ".join(boxed_args)
        return (
            f"mp_call_function_n_kw({fn_expr}, "
            f"{n_args}, 0, (const mp_obj_t[]){{{args_str}}})"
        )
```

The logic handles:

1. **Dotted module imports**: `lvgl_mvu.dsl` becomes a chained `mp_load_attr(mp_import_name(...), ...)` expression via the `_emit_dotted_module_import()` helper.
2. **Function lookup**: Load the function as an attribute of the imported module.
3. **Argument boxing**: Convert each argument from its native IR type to `mp_obj_t`.
4. **Keyword arguments**: Interleave `MP_OBJ_NEW_QSTR(MP_QSTR_name)` and boxed values, as MicroPython's `mp_call_function_n_kw` expects.
5. **Optimized call paths**: Use `mp_call_function_0/1/2` for small argument counts, fall back to `mp_call_function_n_kw` for larger counts.

After the fix, `Button("-").size(60, 40)` generates:

```c
mp_obj_t _tmp9 = ({
    mp_obj_t __method[4];
    mp_load_method(
        mp_call_function_1(
            mp_load_attr(
                mp_load_attr(
                    mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                    MP_QSTR_dsl),
                MP_QSTR_Button),
            mp_obj_new_str("-", 1)),
        MP_QSTR_size, __method);
    __method[2] = mp_obj_new_int(60);
    __method[3] = mp_obj_new_int(40);
    mp_call_method_n_kw(2, 0, __method);
});
```

The `mp_call_function_1(...)` call is the C expression generated by `_value_to_c(ModuleCallIR(...))`. It is now a proper expression that feeds into `mp_load_method` as the receiver.

### Bug E: DynamicCallIR in preludes

The `Screen()(...)` pattern produces a different IR structure. `Screen()` returns a callable object (a widget builder). The outer `()` call invokes that object with children arguments.

The IR builder handles this as a two-step process:

1. Evaluate the inner call (`Screen()`) and store the result in a temp variable via `TempAssignIR`.
2. Call the temp variable as a callable via `DynamicCallIR`.

```text
_tmp1 = lvgl_mvu.dsl.Screen()     <-- TempAssignIR stores ModuleCallIR result
return Screen_result(children...)  <-- DynamicCallIR calls the temp
```

The `TempAssignIR` node was added specifically for this pattern. It extends `InstrIR` (not `StmtIR`), which allows it to appear in preludes. The existing `AssignIR` is a `StmtIR` and cannot appear in prelude context.

When the `DynamicCallIR` result appears as a value inside another expression (like the return statement), `_value_to_c()` is called on it. Before the fix, `DynamicCallIR` had no case in the dispatch:

```c
// BEFORE: the call result is missing
return /* unknown value */;
```

### The DynamicCallIR fix

The fix adds a case that mirrors the `ModuleCallIR` pattern, but uses a local variable name instead of a module import as the callable:

```python
elif isinstance(value, DynamicCallIR):
    # Dynamic callable invocation: local_var(args)
    callable_var = value.callable_var
    boxed_args = [self._box_value_ir(a) for a in value.args]
    boxed_kwargs = []
    for kw_name, kw_val in value.kwargs:
        boxed_kwargs.append(f"MP_OBJ_NEW_QSTR(MP_QSTR_{kw_name})")
        boxed_kwargs.append(self._box_value_ir(kw_val))
    n_args = len(boxed_args)
    n_kw = len(value.kwargs)
    if n_kw > 0:
        all_args = boxed_args + boxed_kwargs
        args_str = ", ".join(all_args)
        return (
            f"mp_call_function_n_kw({callable_var}, "
            f"{n_args}, {n_kw}, (const mp_obj_t[]){{{args_str}}})"
        )
    if n_args == 0:
        return f"mp_call_function_0({callable_var})"
    elif n_args == 1:
        return f"mp_call_function_1({callable_var}, {boxed_args[0]})"
    elif n_args == 2:
        return (
            f"mp_call_function_2({callable_var}, {boxed_args[0]}, {boxed_args[1]})"
        )
    else:
        args_str = ", ".join(boxed_args)
        return (
            f"mp_call_function_n_kw({callable_var}, "
            f"{n_args}, 0, (const mp_obj_t[]){{{args_str}}})"
        )
```

The key difference from `ModuleCallIR`: the callable is not loaded from a module. It is a local variable (`_tmp1` in this case) that was assigned earlier by `TempAssignIR`. The C code uses the variable name directly:

```c
// Screen()(children) becomes:
mp_obj_t _tmp1 = mp_call_function_0(
    mp_load_attr(
        mp_load_attr(
            mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
            MP_QSTR_dsl),
        MP_QSTR_Screen));

return mp_call_function_1(_tmp1, children_arg);
```

The `mp_call_function_1(_tmp1, ...)` is the C expression generated by `_value_to_c(DynamicCallIR(...))`. The variable `_tmp1` holds the callable returned by `Screen()`, and we invoke it with the children.

### The full chain: how view() compiles

Here is the complete IR dump for the `view()` function after both fixes:

```text
def view(model: GENERAL) -> GENERAL:
  c_name: counter_mvu_view
  max_temp: 17
  locals: {model: MP_OBJ_T, count_text: MP_OBJ_T}
  body:
    count_text: mp_obj_t = ("Count: " + str(model.count))
    # prelude:
      _tmp1 = lvgl_mvu.dsl.Screen()
      _tmp2 = lvgl_mvu.layouts.VStack(spacing=20).size(320, 240)
      _tmp3 = _tmp2
      _tmp4 = lvgl_mvu.dsl.Label("MVU Counter Demo").text_color(16777215)
      _tmp5 = _tmp4.build()
      _tmp6 = lvgl_mvu.dsl.Label(count_text).text_color(65280)
      _tmp7 = _tmp6.build()
      _tmp8 = lvgl_mvu.layouts.HStack(spacing=10)
      _tmp9 = lvgl_mvu.dsl.Button("-").size(60, 40)
      _tmp10 = _tmp9.on(LV_EVENT_CLICKED, MSG_DECREMENT)
      _tmp11 = _tmp10.build()
      _tmp12 = lvgl_mvu.dsl.Button("Reset").size(80, 40)
      _tmp13 = _tmp12.on(LV_EVENT_CLICKED, MSG_RESET)
      _tmp14 = _tmp13.build()
      _tmp15 = lvgl_mvu.dsl.Button("+").size(60, 40)
      _tmp16 = _tmp15.on(LV_EVENT_CLICKED, MSG_INCREMENT)
      _tmp17 = _tmp16.build()
    return <DynamicCallIR>
```

Each line in the prelude maps to a `_value_to_c` call:

| IR Line | ValueIR Type | `_value_to_c` Output |
|---------|-------------|---------------------|
| `_tmp1 = lvgl_mvu.dsl.Screen()` | `ModuleCallIR` | `mp_call_function_0(mp_load_attr(...))` |
| `_tmp2 = ...VStack(spacing=20).size(320, 240)` | `MethodCallIR` receiver is `ModuleCallIR` | receiver: `mp_call_function_n_kw(...)` |
| `_tmp4 = ...Label("MVU Counter Demo").text_color(...)` | `MethodCallIR` receiver is `ModuleCallIR` | receiver: `mp_call_function_1(...)` |
| `_tmp9 = ...Button("-").size(60, 40)` | `MethodCallIR` receiver is `ModuleCallIR` | receiver: `mp_call_function_1(...)` |
| `return <DynamicCallIR>` | `DynamicCallIR` | `mp_call_function_1(_tmp1, ...)` |

Before the fix, every `ModuleCallIR` and `DynamicCallIR` in this table produced `/* unknown value */`. The generated C had 17 temp variables, many of which referenced garbage receivers. After the fix, all 194 lines of generated C are clean.

### Why this pattern only appeared in MVU code

The test suite had plenty of module calls and method chains, but they appeared in different contexts:

- **Module calls as standalone statements**: `register_p0_appliers(registry)` -- handled by FunctionEmitter's `_emit_expr()`, not ContainerEmitter's `_value_to_c()`.
- **Method chains on local variables**: `result.append(x)` -- the receiver is a `NameIR` or `TempIR`, both already handled in `_value_to_c()`.
- **Class instantiation as receiver**: `Model(0).count` -- `ClassInstantiationIR` was already in `_value_to_c()`.

The MVU application was the first real code that combined module calls with method chains in the same expression. `Button("-").size(60, 40)` requires `ModuleCallIR` as a receiver inside a `MethodCallIR`, which forces `_value_to_c()` to handle it.

Similarly, the `Screen()(...)` callable-call pattern had never appeared before. Standard Python rarely calls the return value of a function immediately. The MVU DSL uses this pattern for its Screen builder API, making `DynamicCallIR` appear in a prelude context for the first time.

### The _emit_dotted_module_import helper

Both `ModuleCallIR` and `ModuleAttrIR` need to import modules at runtime. For simple module names like `math`, this is straightforward:

```c
mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0))
```

For dotted module names like `lvgl_mvu.dsl`, a flat import does not work. MicroPython's `mp_import_name` only imports the top-level package. Submodules must be accessed via `mp_load_attr`:

```c
// WRONG: looks for a module literally named "lvgl_mvu.dsl"
mp_import_name(MP_QSTR_lvgl_mvu_dsl, mp_const_none, MP_OBJ_NEW_SMALL_INT(0))

// CORRECT: import lvgl_mvu, then access .dsl attribute
mp_load_attr(
    mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
    MP_QSTR_dsl)
```

The `_emit_dotted_module_import()` helper handles this for any depth:

```python
def _emit_dotted_module_import(module_name: str) -> str:
    """Emit a chained mp_import_name + mp_load_attr for dotted module names."""
    parts = module_name.split(".")
    expr = f"mp_import_name(MP_QSTR_{parts[0]}, mp_const_none, MP_OBJ_NEW_SMALL_INT(0))"
    for part in parts[1:]:
        expr = f"mp_load_attr({expr}, MP_QSTR_{part})"
    return expr
```

For `lvgl_mvu.program`, this produces a two-level chain. For a hypothetical `a.b.c`, it chains three `mp_load_attr` calls. The helper is shared between both emitters -- it is a standalone function at module level, not a method on either emitter class.

### The dispatch after the fix

After adding `ModuleCallIR` and `DynamicCallIR`, the `_value_to_c` dispatch handles 20 IR node types:

```text
_value_to_c dispatch table:
  TempIR                     -> variable name
  NameIR                     -> C variable name
  FuncRefIR                  -> MP_OBJ_FROM_PTR(&func_obj)
  ModuleRefIR                -> mp_import_name(...)
  ModuleAttrIR               -> mp_load_attr(mp_import_name(...), ...)
  ConstIR                    -> literal (int, float, bool, None, str)
  BinOpIR                    -> arithmetic expression or mp_binary_op
  UnaryOpIR                  -> unary expression
  CompareIR                  -> comparison or mp_binary_op
  SelfAttrIR                 -> self->field
  SelfMethodRefIR            -> mp_obj_new_bound_meth(...)
  SelfMethodCallIR           -> method_native(self, args)
  ParamAttrIR                -> struct cast + field access
  SubscriptIR                -> mp_obj_subscr(...)
  CallIR                     -> builtin calls (id, etc.)
  ClassInstantiationIR       -> make_new(...)
  SiblingClassInstantiationIR -> sibling_make_new(...)
  ModuleCallIR               -> mp_call_function_N(mp_load_attr(...), args)  [NEW]
  DynamicCallIR              -> mp_call_function_N(local_var, args)          [NEW]
  (default)                  -> /* unknown value */
```

Each case converts one IR node type to a self-contained C expression string. The caller (usually `_emit_method_chain` or a prelude handler) uses that string as a subexpression in the larger C statement it is building.

### Keeping the two emitters in sync

The root cause of both bugs was the same: FunctionEmitter supported a node type that ContainerEmitter did not. This divergence is easy to introduce because the two emitters handle different contexts and are tested differently.

The risk is structural. Any new `ValueIR` subclass added to `ir.py` must be handled in both:

1. `FunctionEmitter._emit_expr()` -- for statement-level contexts
2. `ContainerEmitter._value_to_c()` -- for expression/prelude contexts

The project convention (documented in AGENTS.md) already requires updating `ir_visualizer.py` for new IR types. The same discipline applies to the emitter dispatch tables. When you add a new IR node, you add it to all three places: visualizer, function emitter, and container emitter.

### What this enables

With all `ValueIR` types handled in `_value_to_c`, the compiler can now produce clean C for:

- **Method chains on module function results**: `Button("-").size(60, 40).on(7, 2).build()` -- each step correctly chains through `_value_to_c` calls.
- **Callable-call-result patterns**: `Screen()(children)` -- the `DynamicCallIR` correctly invokes the stored callable.
- **Mixed patterns**: `VStack(spacing=20).size(320, 240)(child1, child2, child3)` -- a module call with keyword args, chained method call, and dynamic callable invocation, all in one expression.

The counter MVU application compiles to 194 lines of clean C with zero `/* unknown value */` comments. Every temp variable in the `view()` function's 17-deep prelude resolves to a proper C expression.
