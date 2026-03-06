# Feature Scope Definition

This document defines what Python features mypyc-micropython will support, partially support, or explicitly exclude.

## Table of Contents

- [Scope Categories](#scope-categories)
- [In-Scope Features](#in-scope-features)
- [Partially In-Scope Features](#partially-in-scope-features)
- [Out-of-Scope Features](#out-of-scope-features)
- [Decision Rationale](#decision-rationale)

## Scope Categories

| Category | Description |
|----------|-------------|
| **In-Scope** | Fully supported, will be implemented |
| **Partial** | Limited support with documented restrictions |
| **Out-of-Scope** | Explicitly not supported, will raise compile error |

## In-Scope Features

### Primitives and Literals ✅

| Feature | Status | Notes |
|---------|--------|-------|
| `int` | ✅ Implemented | Maps to `mp_int_t` |
| `float` | ✅ Implemented | Maps to `mp_float_t` |
| `bool` | ✅ Implemented | Maps to `bool` |
| `str` | ✅ Implemented | Full method support via MicroPython runtime |
| `bytes` | 📋 Planned | Phase 1 |
| `None` | ✅ Implemented | Maps to `mp_const_none` |

### Operators ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Arithmetic (`+`, `-`, `*`, `/`, `//`, `%`, `**`) | ✅ Implemented | |
| Comparison (`==`, `!=`, `<`, `>`, `<=`, `>=`) | ✅ Implemented | |
| Logical (`and`, `or`, `not`) | ✅ Implemented | Short-circuit evaluation |
| Bitwise (`&`, `\|`, `^`, `~`, `<<`, `>>`) | ✅ Implemented | |
| Augmented assignment (`+=`, `-=`, etc.) | ✅ Implemented | |
| Ternary (`x if cond else y`) | ✅ Implemented | |

### Control Flow ✅

| Feature | Status | Notes |
|---------|--------|-------|
| `if`/`elif`/`else` | ✅ Implemented | |
| `while` loops | ✅ Implemented | Including `break`/`continue` |
| `for` loops | ✅ Implemented | Over range, list, dict, and other iterables |
| `pass` | ✅ Implemented | |
| `return` | ✅ Implemented | |

### Functions ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Basic functions | ✅ Implemented | With type annotations |
| Return values | ✅ Implemented | |
| Recursion | ✅ Implemented | |
| Default arguments | ✅ Implemented | `int`, `float`, `bool`, `str`, `None`, empty containers |
| `*args` | ✅ Implemented | Via `MP_DEFINE_CONST_FUN_OBJ_VAR` |
| `**kwargs` | ✅ Implemented | Via `MP_DEFINE_CONST_FUN_OBJ_KW` |
| Keyword-only arguments | 📋 Planned | Phase 2 |
| Positional-only arguments | 📋 Planned | Phase 2 |

### Data Structures ✅

| Feature | Status | Notes |
|---------|--------|-------|
| `list` | ✅ Implemented | Literals, indexing, `append()`, `pop()`, `len()`, optimized access |
| `tuple` | ✅ Implemented | Literals, indexing, slicing, unpacking, concatenation, RTuple optimization |
| `dict` | ✅ Implemented | Literals, indexing, `get()`, `keys()`, `values()`, `items()`, full API |
| `set` | ✅ Implemented | Literals, `add()`, `remove()`, `discard()`, `in` operator, iteration |
| `frozenset` | 📋 Planned | Lower priority |

### Classes ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Class definition | ✅ Implemented | With typed fields |
| `__init__` | ✅ Implemented | Auto-generated for @dataclass |
| Instance methods | ✅ Implemented | With vtable dispatch |
| Instance attributes | ✅ Implemented | Native C types |
| Class attributes | 📋 Planned | Phase 3 |
| `@property` | ✅ Implemented | Getter + setter with type-aware boxing/unboxing |
| `@staticmethod` | ✅ Implemented | Via `mp_rom_obj_static_class_method_t` wrapper |
| `@classmethod` | ✅ Implemented | Via `mp_rom_obj_static_class_method_t` wrapper |
| Single inheritance | ✅ Implemented | With vtable-based virtual dispatch |
| Traits (`@trait`) | ✅ Implemented | Multiple inheritance via traits (one concrete base + N traits) |
| `__str__`/`__repr__` | ✅ Implemented | Via MicroPython print slot |
| `__eq__`/`__len__`/`__getitem__`/`__setitem__` | ✅ Implemented | Special methods |
| `@dataclass` | ✅ Implemented | Auto-generated `__init__` and `__eq__` |

### Exception Handling ✅

| Feature | Status | Notes |
|---------|--------|-------|
| `try`/`except` | ✅ Implemented | With `nlr_push`/`nlr_pop` |
| `try`/`finally` | ✅ Implemented | Ensures finally runs on all paths |
| `raise` | ✅ Implemented | With exception type + message |
| Exception chaining | ⚠️ Limited | Basic support only |
| Custom exceptions | 📋 Planned | Phase 4 |
| `try`/`except` | 📋 Planned | Phase 4 |
| `try`/`finally` | 📋 Planned | Phase 4 |
| `raise` | 📋 Planned | Phase 4 |
| Exception chaining | ⚠️ Limited | Basic support only |
| Custom exceptions | 📋 Planned | Phase 4 |

### Built-in Functions ✅

| Feature | Status | Notes |
|---------|--------|-------|
| `abs()` | ✅ Implemented | |
| `int()` | ✅ Implemented | |
| `float()` | ✅ Implemented | |
| `bool()` | ✅ Implemented | `mp_obj_is_true()` for truthiness |
| `len()` | ✅ Implemented | For list, dict, tuple, set, and other collections |
| `range()` | ✅ Implemented | 1, 2, and 3 argument forms |
| `print()` | ✅ Implemented | With space separator |
| `min()`/`max()` | ✅ Implemented | 2+ args, inline optimization for 2-3 int args |
| `sum()` | ✅ Implemented | With optional start, inline optimization for `list[int]` |
| `enumerate()` | ✅ Implemented | Via `mp_type_enumerate` |
| `zip()` | ✅ Implemented | Via `mp_type_zip` |
| `map()`/`filter()` | 📋 Planned | Phase 5 |
| `sorted()` | ✅ Implemented | Via `mp_builtin_sorted_obj` |
| `isinstance()` | 📋 Planned | Concrete classes + traits (see below) |
| `type()` | 📋 Planned | Phase 3 |
| `hasattr()`/`getattr()`/`setattr()` | 📋 Planned | Phase 3 |
| `list()` | ✅ Implemented | Empty list constructor |
| `dict()` | ✅ Implemented | Empty and copy constructor |
| `tuple()` | ✅ Implemented | Empty and from-iterable constructor |
| `set()` | ✅ Implemented | Empty and from-iterable constructor |

## Partially In-Scope Features

These features have limited support with documented restrictions.

### List Comprehensions ⚠️

**Supported:**
```python
# Simple comprehensions
squares = [x * x for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]
```

**NOT Supported:**
```python
# Nested comprehensions
matrix = [[i * j for j in range(5)] for i in range(5)]  # ❌

# Multiple for clauses
pairs = [(x, y) for x in range(3) for y in range(3)]  # ❌
```

### Generators ✅

**Supported:**
```python
# While-loop generators
def countdown(n: int):
    while n > 0:
        yield n
        n -= 1

# For-range generators (all forms)
def squares(n: int):
    for i in range(n):
        yield i * i

def range_with_start(n: int):
    for i in range(1, n):  # Non-zero start supported
        yield i

# For-iter generators (iterate over arbitrary iterables)
def iter_items(items: list[object]):
    for x in items:
        yield x
```

**NOT Supported:**
```python
# Generator expressions
gen = (x * x for x in range(10))  # Not supported

# yield from
def chain(*iterables):
    for it in iterables:
        yield from it  # Not supported

# Generator with send/throw
def echo():
    while True:
        x = yield  # Receiving values not supported

# try/with inside generators
def gen_with_try():
    try:
        yield 1  # Not supported - try in generators
    finally:
        pass
```
```

### isinstance() ⚠️ (Planned)

Type checking builtin - planned with different behavior for concrete classes vs traits.

**Planned Support:**
```python
# Concrete class check - simple type comparison
isinstance(obj, Person)  # ✅ Will use mp_obj_is_type()

# Trait check - requires runtime trait registry
isinstance(obj, Named)   # ⚠️ More complex implementation needed
```

**Implementation:**

| Check Type | C Implementation | Notes |
|------------|------------------|-------|
| Concrete class | `mp_obj_is_type(obj, &type)` | Fast pointer comparison |
| Trait | Runtime trait lookup | Needs trait registry in type object |

**NOT Planned:**
```python
# Tuple of types
isinstance(obj, (A, B, C))  # ❌ Multiple types not supported initially

# Abstract base classes
isinstance(obj, ABC)  # ❌ No ABC support
```

### Decorators ⚠️
### Decorators ⚠️

**Supported:**
```python
@staticmethod
def my_static_method() -> int:
    return 42

@classmethod  
def my_class_method(cls) -> str:
    return cls.__name__

@property
def my_property(self) -> int:
    return self._value
```

**NOT Supported:**
```python
# Custom decorators
@my_decorator  # ❌
def my_func():
    pass

# Decorator with arguments
@lru_cache(maxsize=100)  # ❌
def cached_func(x):
    pass

# Stacked decorators (except known combinations)
@decorator1
@decorator2  # ❌
def multi_decorated():
    pass
```

### Type Annotations ✅

Type annotations are fully supported and can be validated at compile time using mypy.

**Supported:**
```python
# Basic types
def func(x: int, y: float) -> bool: ...

# Optional
def maybe(x: Optional[int]) -> int: ...
from typing import Optional

# Union (simple cases)
def flexible(x: int | str) -> str: ...

# Generic collections
def process(items: list[int]) -> dict[str, int]: ...
```

**Type Checking (Default):**

As of v0.x, strict type checking is **enabled by default**. This ensures code quality and enables future optimizations.

```python
from mypyc_micropython import compile_source

# Default: strict type checking enabled
code = compile_source(source, "module")

# Disable type checking (for rapid prototyping)
code = compile_source(source, "module", type_check=False)
```

**CLI:**
```bash
# Default: type checking enabled
mpy-compile mymodule.py

# Disable type checking
mpy-compile mymodule.py --no-type-check
```

### Type-Based Optimization Opportunities

With strict type checking, mypy resolves generic types and infers local variable types. This information enables significant performance optimizations (planned for future phases).

#### Current Type Information Usage

| Source | Information | Current Use |
|--------|-------------|-------------|
| AST annotations | `def foo(x: int)` | C type selection (`mp_int_t`) |
| Mypy resolution | `list[int]` element type | `len()/sum()` optimizations |
| Mypy inference | Local variable types | Not yet used |

#### Planned Optimizations (Phase 7)

| Pattern | Current Generated Code | Optimized Code | Est. Speedup |
|---------|----------------------|----------------|--------------|
| `a + b` (both `int`) | `mp_binary_op(MP_BINARY_OP_ADD, a, b)` | `a + b` (native C) | 3-5x |
| `list[i]` on `list[int]` | `mp_obj_get_int(mp_obj_subscr(...))` | Direct array access | 2-3x |
| `for x in list[int]` | Box/unbox per iteration | Native C iteration | 3-5x |
| `x: int = expr` | Sometimes `mp_obj_t` | Always `mp_int_t` | 2x |
| `dict[str, int]` value | Generic subscript | Typed fast path | 2x |

#### Why Mypy Provides More Than AST

```python
def process(items: list[int]) -> int:
    total = 0          # mypy infers: int
    for x in items:    # mypy infers: x is int
        total += x     # mypy knows: int + int -> int
    return total
```

- **AST only**: Sees `total = 0` but doesn't track type through loop
- **Mypy**: Resolves `x` to `int` from `list[int]`, tracks `total` as `int` throughout

This richer type information will enable the optimizations listed above.

**NOT Supported:**
```python
# TypeVar
T = TypeVar('T')
def identity(x: T) -> T: ...  # Parses but TypeVar not tracked

# Callable types
def higher_order(f: Callable[[int], int]) -> int: ...  # Limited support

# Protocol
class MyProtocol(Protocol): ...  # Not supported

# Literal types
def specific(x: Literal[1, 2, 3]) -> int: ...  # Not supported
```

### String Operations ✅

String operations are fully supported via MicroPython's runtime, matching mypyc's native string operations.

**Note:** Some string methods are not available in MicroPython ESP32 by default:
`capitalize()`, `title()`, `swapcase()`, `ljust()`, `rjust()`, `zfill()`.
These require enabling `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` in the MicroPython build.

#### Construction

| Operation | Status | Notes |
|-----------|--------|-------|
| String literal `"hello"` | ✅ Implemented | `mp_obj_new_str()` |
| `str(x: int)` | ✅ Implemented | Via `mp_call_function_1(&mp_type_str, ...)` |
| `str(x: object)` | ✅ Implemented | Via `mp_obj_print_helper()` |

#### Operators

| Operation | Status | Notes |
|-----------|--------|-------|
| Concatenation `s1 + s2` | ✅ Implemented | `mp_binary_op(MP_BINARY_OP_ADD)` |
| Indexing `s[n]` | ✅ Implemented | `mp_obj_subscr()` |
| Slicing `s[n:m]` | ✅ Implemented | `mp_obj_subscr()` with slice |
| Comparison `==`, `!=` | ✅ Implemented | `mp_binary_op()` |
| Augmented `s1 += s2` | ✅ Implemented | `mp_binary_op(MP_BINARY_OP_INPLACE_ADD)` |
| Containment `s1 in s2` | ✅ Implemented | `mp_binary_op(MP_BINARY_OP_IN)` |

#### Methods (Available on ESP32)

| Operation | Status | Notes |
|-----------|--------|-------|
| `s.split()` | ✅ Implemented | `mp_load_attr(MP_QSTR_split)` + call |
| `s.split(sep)` | ✅ Implemented | With separator argument |
| `s.split(sep, maxsplit)` | ✅ Implemented | With maxsplit argument |
| `s.rsplit()` | ✅ Implemented | Right-to-left split |
| `s.join(iterable)` | ✅ Implemented | `mp_load_attr(MP_QSTR_join)` + call |
| `s.replace(old, new)` | ✅ Implemented | String replacement |
| `s.replace(old, new, count)` | ✅ Implemented | With count limit |
| `s.startswith(prefix)` | ✅ Implemented | Prefix check |
| `s.endswith(suffix)` | ✅ Implemented | Suffix check |
| `s.find(sub)` | ✅ Implemented | Find substring index |
| `s.find(sub, start)` | ✅ Implemented | With start position |
| `s.find(sub, start, end)` | ✅ Implemented | With start and end |
| `s.rfind(sub)` | ✅ Implemented | Right-to-left find |
| `s.strip()` | ✅ Implemented | Strip whitespace |
| `s.strip(chars)` | ✅ Implemented | Strip specific chars |
| `s.lstrip()` | ✅ Implemented | Left strip |
| `s.rstrip()` | ✅ Implemented | Right strip |
| `s.upper()` | ✅ Implemented | Uppercase conversion |
| `s.lower()` | ✅ Implemented | Lowercase conversion |
| `s.center(width)` | ✅ Implemented | Center in width |
| `s.isdigit()` | ✅ Implemented | Check if all digits |
| `s.isalpha()` | ✅ Implemented | Check if all letters |
| `s.isspace()` | ✅ Implemented | Check if all whitespace |
| `s.isupper()` | ✅ Implemented | Check if uppercase |
| `s.islower()` | ✅ Implemented | Check if lowercase |
| `s.partition(sep)` | ✅ Implemented | Split into 3 parts |
| `s.rpartition(sep)` | ✅ Implemented | Right-to-left partition |
| `s.splitlines()` | ✅ Implemented | Split by line boundaries |
| `s.encode()` | ✅ Implemented | Encode to bytes |
| `s.encode(encoding)` | ✅ Implemented | With encoding |
| `s.count(sub)` | ✅ Implemented | Count occurrences |

#### Methods (NOT available on ESP32 by default)

| Operation | Status | Notes |
|-----------|--------|-------|
| `s.capitalize()` | ⚠️ Limited | Requires `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` |
| `s.title()` | ⚠️ Limited | Requires `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` |
| `s.swapcase()` | ⚠️ Limited | Requires `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` |
| `s.ljust(width)` | ⚠️ Limited | Requires `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` |
| `s.rjust(width)` | ⚠️ Limited | Requires `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` |
| `s.zfill(width)` | ⚠️ Limited | Requires `MICROPY_PY_BUILTINS_STR_UNICODE_FULL` |

#### Functions

| Operation | Status | Notes |
|-----------|--------|-------|
| `len(s)` | ✅ Implemented | `mp_obj_len()` |
| `ord(s)` | ✅ Implemented | Get character code |

**NOT Supported:**
```python
# f-strings with expressions
f"{x + y}"  # ❌ Complex expressions in f-strings

# String formatting with complex specs
"{:04d}".format(42)  # ❌ Complex format specs
```

## Out-of-Scope Features

These features will NOT be supported and will raise compilation errors.

### Async/Await ✅ (Basic)

Basic async/await is now supported. Async functions are compiled to coroutine objects
that work with MicroPython's `uasyncio` event loop.

**Supported:**
```python
# Simple async function
async def simple_coro() -> int:
    return 42

# Async with await
async def fetch_data() -> int:
    result = await some_async_func()
    return result

# Multiple sequential awaits
async def multi_step() -> int:
    a = await first_op()
    b = await second_op()
    return a + b

# Running with uasyncio
import asyncio
result = asyncio.run(fetch_data())
```

**NOT Supported:**
```python
# async for (async iteration)
async for item in async_iterator:
    pass  # Not supported

# async with (async context managers)
async with async_resource() as r:
    pass  # Not supported

# Async generators (yield in async def)
async def async_gen():
    yield 1  # Not supported

# Exception handling in coroutines
async def with_try():
    try:
        await something()  # Limited support
    except:
        pass
```

### Metaclasses ❌

```python
# NOT SUPPORTED
class Meta(type):
    def __new__(cls, name, bases, attrs):
        return super().__new__(cls, name, bases, attrs)

class MyClass(metaclass=Meta):
    pass

# Reason: Too dynamic for static compilation. Use regular classes.
```

### Multiple Inheritance (Traits) ✅

**Supported** using mypyc-style trait system:
```python
from mypy_extensions import trait

@trait
class Named:
    name: str
    def get_name(self) -> str:
        return self.name

@trait
class Describable:
    def describe(self) -> str:
        return "object"

class Entity:
    id: int

# ONE concrete base + multiple traits
class Person(Entity, Named, Describable):  # ✅
    age: int
    def describe(self) -> str:  # Override trait method
        return f"Person: {self.name}"

# Function accepting trait-typed parameter (polymorphism)
def greet(obj: Named) -> str:
    return obj.get_name()  # Dynamic dispatch
```

**Key features:**
- `@trait` decorator marks interface-like classes
- Traits cannot be instantiated directly
- ONE concrete base class + multiple traits allowed
- Trait method wrappers handle struct layout differences
- Trait-typed parameters use dynamic attribute lookup

**NOT Supported:**
```python
# Multiple concrete base classes
class Child(Parent1, Parent2):  # ❌ Only ONE concrete base allowed
    pass

# Diamond inheritance with concrete classes
class D(B, C):  # ❌ Where both B and C inherit from A
    pass
```

### Dynamic Features ❌

```python
# NOT SUPPORTED
exec("x = 1")
eval("1 + 2")
compile("code", "<string>", "exec")

# Reason: Cannot compile dynamic code statically.
```

### Reflection/Introspection ❌

```python
# NOT SUPPORTED
globals()["x"] = 1
locals()["y"] = 2
vars(obj)["attr"] = value
__import__("module")

# Reason: Would require full Python runtime.
```

### Nested Classes ❌

```python
# NOT SUPPORTED
class Outer:
    class Inner:
        pass

# Reason: Complexity in code generation. Use module-level classes.
```

### Nested Functions ❌

```python
# NOT SUPPORTED - generates broken code (inner function silently ignored)
def outer(n: int) -> int:
    def inner(x: int) -> int:   # ❌ Inner function not compiled
        return x * 2
    return inner(n)             # ❌ Calls undefined function

# Workaround: Move inner function to module level
def _inner(x: int) -> int:
    return x * 2

def outer(n: int) -> int:
    return _inner(n)            # ✅ Works
```

**Note:** Currently nested functions are silently ignored, generating broken C code. A future version should raise a compile error. Simple read-only closures may be supported in Phase 5.

### Nested Functions with Non-Local Assignment ❌

```python
# NOT SUPPORTED (complex cases)
def outer():
    x = 1
    def inner():
        nonlocal x
        x = 2  # ❌ nonlocal assignment not supported
    inner()
    return x

# Simple closures (read-only) may be supported in Phase 5
```

### Slots and Descriptors ❌

```python
# NOT SUPPORTED
class MyClass:
    __slots__ = ['x', 'y']

class Descriptor:
    def __get__(self, obj, type=None):
        pass

# Reason: Would require implementing descriptor protocol.
```

### Context Managers (Custom) ❌

```python
# NOT SUPPORTED for custom classes
class MyContext:
    def __enter__(self):
        pass
    def __exit__(self, *args):
        pass

# Built-in context managers (like file operations) work in MicroPython
# but cannot be defined in compiled code.
```

### Star Unpacking in Assignments ❌

```python
# NOT SUPPORTED
a, *rest, b = [1, 2, 3, 4, 5]
first, *middle, last = range(10)

# Simple unpacking IS supported:
a, b, c = [1, 2, 3]  # ✅
```

### Walrus Operator ❌

```python
# NOT SUPPORTED
if (n := len(data)) > 10:
    print(f"List is too long ({n} elements)")

# Reason: Complex scoping rules.
```

## Decision Rationale

### Why These Limitations?

1. **Target Platform Constraints**
   - MicroPython runs on microcontrollers with limited RAM (often 256KB or less)
   - No room for full Python runtime
   - Must generate efficient C code

2. **Compilation Feasibility**
   - Some features are inherently dynamic and cannot be statically compiled
   - `exec`/`eval` by definition require runtime interpretation
   - Metaclasses modify class creation at runtime

3. **Implementation Complexity**
   - Features like multiple inheritance require complex MRO computation
   - Nested classes add significant code generation complexity
   - Some features have low usage vs. high implementation cost

4. **MicroPython Compatibility**
   - MicroPython itself doesn't support all CPython features
   - We can only support what MicroPython's C API allows
   - async/await differs between MicroPython and CPython

### Workarounds for Out-of-Scope Features

| Feature | Workaround |
|---------|------------|
| `async`/`await` | Use MicroPython's native `uasyncio` directly |
| Metaclasses | Use factory functions or `__init_subclass__` |
| Multiple inheritance | Use composition or single inheritance + interfaces |
| `exec`/`eval` | Pre-compute values or use lookup tables |
| Nested classes | Move to module level |
| Custom decorators | Apply transformation manually |
| Context managers | Use try/finally pattern |

## Feature Matrix by Phase

| Phase | Features |
|-------|----------|
| **1 (Core)** | `for` loops ✅, `list` ✅, `tuple` ✅, `dict` ✅, `set` ✅, `range()` ✅, `len()` ✅, `print()` ✅ |
| **2 (Functions)** | Default args ✅, `*args` ✅, `**kwargs` ✅, `bool()` ✅, `min()`/`max()` ✅, `sum()` ✅, `enumerate()` ✅, `zip()` ✅, `sorted()` ✅ |
| **3 (Classes)** | Basic classes ✅, methods ✅, @dataclass ✅, single inheritance ✅, @property ✅, @staticmethod ✅, @classmethod ✅ |
| **4 (Exceptions)** | `try`/`except`/`finally` ✅, `raise` ✅, custom exceptions |
| **5 (Advanced)** | Simple generators ✅ (while/for-range/for-iter + yield), closures, `map()`/`filter()` |
| **6 (Polish)** | Full IR pipeline ✅, RTuple optimization ✅ (47x speedup), list access optimization ✅, 504 tests ✅ |

## See Also

- [05-roadmap.md](05-roadmap.md) - Detailed implementation roadmap
- [02-mypyc-reference.md](02-mypyc-reference.md) - How mypyc handles these features
- [01-architecture.md](01-architecture.md) - Architecture overview
