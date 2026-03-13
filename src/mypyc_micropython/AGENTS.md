# AGENTS.md - Core Compiler

Two-phase IR pipeline: Python AST to typed IR to MicroPython C code.

## Quick Reference

```bash
# Compile and inspect IR
mpy-compile examples/factorial.py --dump-ir text
mpy-compile examples/factorial.py --dump-ir tree --ir-function factorial

# Run tests
pytest tests/test_compiler.py -xvs              # Full compilation tests
pytest tests/test_ir_builder.py -xvs            # IR builder tests
pytest tests/test_emitters.py -xvs              # Emitter tests
```

## File Overview

| File | LOC | Purpose |
|------|-----|---------|
| `ir.py` | 1,873 | IR dataclass definitions (60+ types) |
| `ir_builder.py` | 3,989 | AST to IR translation (LARGEST) |
| `base_emitter.py` | 1,519 | Shared emitter utilities, builtin dispatch |
| `class_emitter.py` | 1,306 | ClassIR to C structs/vtables |
| `container_emitter.py` | 1,054 | Container/expression IR to C |
| `ir_visualizer.py` | 938 | IR debugging (text/tree/JSON) |
| `compiler.py` | 920 | Top-level orchestration |
| `type_checker.py` | 694 | mypy integration |
| `module_emitter.py` | 577 | Module assembly |
| `generator_emitter.py` | 444 | Generator/yield support |
| `async_emitter.py` | 386 | Async/await support |
| `method_emitter.py` | 366 | Method dispatch |
| `function_emitter.py` | 353 | FuncIR to C code |
| `cli.py` | 163 | CLI entry point |
| `cache.py` | 157 | Incremental compilation |

## Compilation Pipeline

```
Python source
    |
    v
ast.parse() --> AST
    |
    v
IRBuilder --> FuncIR, ClassIR, ModuleIR
    |
    v
FunctionEmitter, ClassEmitter, ContainerEmitter --> C code fragments
    |
    v
ModuleEmitter --> Complete C module with registration
```

## Complexity Hotspots

Three methods account for most complexity:

1. **`base_emitter.py::_emit_builtin_call()`** - 218 lines, 40+ builtins
2. **`ir_builder.py::_build_expr()`** - 264 lines, 50+ AST expression types
3. **`container_emitter.py::_value_to_c()`** - 312 lines, 40+ ValueIR types

## The Prelude Pattern

Every expression returns `tuple[ValueIR, list[InstrIR]]`:
- **ValueIR**: The result value
- **list[InstrIR]**: Instructions that must execute BEFORE the value is valid

```python
# Example: a.b.c requires evaluating a.b first
def _build_expr(self, node: ast.expr) -> tuple[ValueIR, list[InstrIR]]:
    if isinstance(node, ast.Attribute):
        obj_val, obj_prelude = self._build_expr(node.value)
        temp = self._fresh_temp()
        instr = AttrGetIR(obj=obj_val, attr=node.attr, dest=temp)
        return NameIR(temp, ...), obj_prelude + [instr]
```

## Adding New IR Classes

When adding a new IR class:

1. **Define in `ir.py`** - Add dataclass with proper fields
2. **Build in `ir_builder.py`** - Generate IR from AST
3. **Emit in emitters** - Convert IR to C code
4. **Visualize in `ir_visualizer.py`** - CRITICAL: Add handling or dumps show `/* unknown */`

```python
# ir.py
@dataclass
class NewFeatureIR(InstrIR):
    field1: str
    field2: ValueIR

# ir_visualizer.py - MUST ADD
elif isinstance(node, NewFeatureIR):
    return f"NewFeature({node.field1}, {_fmt(node.field2)})"
```

## Type System

**CType enum** maps Python types to C types:
- `MP_OBJ_T` - boxed `mp_obj_t` (str, list, dict, tuple, set)
- `MP_INT_T` - unboxed `mp_int_t` (int)
- `MP_FLOAT_T` - unboxed `mp_float_t` (float)
- `BOOL` - native `bool`
- `VOID` - void (None returns)
- `GENERAL` - unknown/dynamic (object, Any)

**Type erasure**:
- `Literal[3]` erases to `int`
- `TypeVar("T")` erases to upper bound (or `object` if unbounded)

## Key Functions

```python
# Core compilation API
compile_source(source, module_name, *, type_check=True, strict=True) -> str
compile_to_micropython(path, output_dir, *, incremental=True, force=False) -> CompilationResult

# IR building
IRBuilder(module_name).build_function(ast_node) -> FuncIR
IRBuilder(module_name).build_class(ast_node) -> ClassIR

# Code emission
FunctionEmitter(func_ir).emit() -> tuple[str, str]  # native + wrapper
ClassEmitter(class_ir, module_name).emit() -> str
ModuleEmitter(module_ir).emit() -> str
```

## Debugging Workflow

1. **Compilation fails?** Dump IR:
   ```bash
   mpy-compile myfile.py --dump-ir text --ir-function problematic_func
   ```

2. **Check prelude** - Look for `# prelude:` in text output

3. **Verify temps** - Check `max_temp` matches usage

4. **Compare formats** - Use tree for structure, json for tooling

## Common Patterns

### Boxing/Unboxing
```c
// Unbox: mp_obj_t -> C type
mp_int_t n = mp_obj_get_int(n_obj);

// Box: C type -> mp_obj_t
return mp_obj_new_int(result);
```

### Method Dispatch
```c
// Direct call (known type)
mp_obj_list_append(list, item);

// Dynamic call (unknown type)
mp_call_method_n_kw(1, 0, dest);
```

### Temp Variables
```c
mp_obj_t _tmp1 = ...;  // Allocated by ir_builder._fresh_temp()
mp_obj_t _tmp2 = ...;  // max_temp tracks highest index
```

## Testing Requirements

Every compiler change needs tests at multiple levels:

1. **`test_ir_builder.py`** - Verify IR generation
2. **`test_emitters.py`** - Verify C code emission (isolated)
3. **`test_compiler.py`** - End-to-end compilation
4. **`test_c_runtime.py`** - Compile and execute C (if applicable)

## Files NOT to Modify Directly

- `c_bindings/` - Separate subsystem (see `c_bindings/AGENTS.md`)
- Generated `.c` files in `modules/` - Regenerated on compile
