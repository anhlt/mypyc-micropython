# Nested Functions and Closures

Research findings on how mypyc handles nested functions, and our implementation strategy for mypyc-micropython.

## Current Status

**Decision**: Compile-time error for nested functions (Phase 6.3)

Nested functions are detected and rejected with a clear error message. Full closure support is deferred to Phase 5.

## How Mypyc Handles Nested Functions

### 1. Detection

Mypyc uses `FuncInfo` context tracking in `mypyc/irbuild/context.py`:

```python
class FuncInfo:
    def __init__(
        self,
        ...
        is_nested: bool = False,       # This function is inside another
        contains_nested: bool = False,  # This function contains nested functions
        add_nested_funcs_to_env: bool = False,
    ) -> None:
```

### 2. The Environment Class Pattern

From `mypyc/irbuild/env_class.py`, mypyc generates a class to hold captured variables:

```python
def setup_env_class(builder: IRBuilder) -> ClassIR:
    """Generate a class representing a function environment.
    
    If we have a nested function that has non-local (free) variables,
    access to the non-locals is via an instance of an environment class.
    """
    env_class = ClassIR(
        f"{builder.fn_info.namespaced_name()}_env",
        builder.module_name,
        is_generated=True,
    )
    env_class.attributes[SELF_NAME] = RInstance(env_class)
    
    # If nested, point to parent's environment
    if builder.fn_info.is_nested:
        env_class.attributes[ENV_ATTR_NAME] = RInstance(builder.fn_infos[-2].env_class)
```

### 3. Example Transformation

```python
# Python source:
def outer():
    x = 10
    def inner():
        return x + 1
    return inner()

# Mypyc generates:
class outer_env:
    __mypyc_self__: outer_env  # Self reference
    x: int                      # Captured variable

def outer():
    env = outer_env()
    env.x = 10
    return inner(env)  # Pass env as implicit arg

def inner(env: outer_env):
    return env.x + 1
```

### 4. Captured Variable Access

Variables referenced in nested functions are added to the environment class:

```python
def add_vars_to_env(builder: IRBuilder, prefix: str = "") -> None:
    """Add all variables declared in current function that are
    referenced in nested functions to this function's environment class."""
    
    if builder.fn_info.fitem in builder.free_variables:
        for var in builder.free_variables[builder.fn_info.fitem]:
            builder.add_var_to_env_class(var, rtype, env_for_func)
```

### 5. Mutable vs Read-Only Captures

Mypyc treats ALL captures as potentially mutable:
- Variables stored in heap-allocated environment class
- Both reads and writes go through `GetAttr`/`SetAttr`
- No distinction at IR level

```c
// Generated C for reading:
mp_int_t x = ((outer_env*)env)->x;

// Generated C for writing:
((outer_env*)env)->x = new_value;
```

## Generator Implementation

Mypyc transforms generators into state machine classes:

```python
# Python:
def countdown(n: int):
    while n > 0:
        yield n
        n -= 1

# Generated class:
class countdown_generator:
    __mypyc_env__: countdown_env      # Environment (holds 'n')
    __mypyc_next_label__: int         # State machine position
    
    def __next__(self) -> object:
        return self.__mypyc_helper__(...)
    
    def __iter__(self) -> countdown_generator:
        return self
```

Key methods generated:
- `__iter__()` - Returns self
- `__next__()` - Advances state machine
- `send()` - Send value into generator
- `throw()` - Throw exception into generator
- `close()` - Close generator

## Implementation Options

### Option 1: Full Closure Support (4-6 weeks)

Implement mypyc's environment class pattern:
- Generate `FuncName_env` struct for captured variables
- Pass env as implicit first argument
- Support mutable captures

**Pros**: Full Python semantics
**Cons**: Complex, significant IR changes

### Option 2: Read-Only Closures (2-3 weeks)

Capture values at definition time:
- Copy captured values into nested function struct
- Reject mutations at compile time

```python
# Supported:
def outer():
    x = 10
    def inner():
        return x + 1  # OK - read only

# Rejected:
def outer():
    x = 10
    def inner():
        x += 1  # ERROR: Cannot mutate captured variable
```

**Pros**: Simpler, covers 80% of use cases
**Cons**: Not full Python semantics

### Option 3: Compile-Time Error (Current Choice)

Detect nested functions and raise error:

```
CompilationError: Nested functions not supported at line 5.
  Hint: Refactor to module-level function.
```

**Pros**: Explicit, no silent failures
**Cons**: Limits expressiveness

## Future Work (Phase 5)

When implementing closures:

1. **Start with read-only closures** - Simpler and covers most use cases
2. **Track free variables** - Detect which variables are captured
3. **Generate environment struct** - Hold captured values
4. **Pass as implicit argument** - Nested function receives env pointer

### MicroPython Considerations

MicroPython's C API doesn't have built-in closure support. Options:
- Custom struct for environment
- Use `mp_obj_t` wrapper for closure object
- Store env pointer in function object's extra data

## References

- `mypyc/irbuild/env_class.py` - Environment class generation
- `mypyc/irbuild/function.py` - Nested function detection
- `mypyc/irbuild/context.py` - FuncInfo with is_nested flag
- `mypyc/irbuild/generator.py` - Generator state machine

## See Also

- [05-roadmap.md](../05-roadmap.md) - Phase 5: Advanced Features
- [04-feature-scope.md](../04-feature-scope.md) - Feature scope definition
