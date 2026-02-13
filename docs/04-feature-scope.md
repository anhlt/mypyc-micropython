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
| `str` | 🔄 Partial | Basic support implemented |
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
| Default arguments | 📋 Planned | Phase 2 |
| `*args` | 📋 Planned | Phase 2 |
| `**kwargs` | 📋 Planned | Phase 2 |
| Keyword-only arguments | 📋 Planned | Phase 2 |
| Positional-only arguments | 📋 Planned | Phase 2 |

### Data Structures ✅

| Feature | Status | Notes |
|---------|--------|-------|
| `list` | ✅ Implemented | Literals, indexing, `append()`, `pop()`, `len()` |
| `tuple` | 📋 Planned | Phase 2 |
| `dict` | ✅ Implemented | Literals, indexing, `get()`, `keys()`, `values()`, `items()` |
| `set` | 📋 Planned | Phase 2 |
| `frozenset` | 📋 Planned | Lower priority |

### Classes 📋

| Feature | Status | Notes |
|---------|--------|-------|
| Class definition | 📋 Planned | Phase 3 |
| `__init__` | 📋 Planned | Phase 3 |
| Instance methods | 📋 Planned | Phase 3 |
| Instance attributes | 📋 Planned | Phase 3 |
| Class attributes | 📋 Planned | Phase 3 |
| `@property` | 📋 Planned | Phase 3 |
| `@staticmethod` | 📋 Planned | Phase 3 |
| `@classmethod` | 📋 Planned | Phase 3 |
| Single inheritance | 📋 Planned | Phase 3 |
| `__str__`/`__repr__` | 📋 Planned | Phase 3 |

### Exception Handling 📋

| Feature | Status | Notes |
|---------|--------|-------|
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
| `bool()` | 📋 Planned | Phase 2 |
| `len()` | ✅ Implemented | For list, dict, and other collections |
| `range()` | ✅ Implemented | 1, 2, and 3 argument forms |
| `print()` | 📋 Planned | Phase 2 |
| `min()`/`max()` | 📋 Planned | Phase 2 |
| `sum()` | 📋 Planned | Phase 2 |
| `enumerate()` | 📋 Planned | Phase 2 |
| `zip()` | 📋 Planned | Phase 2 |
| `map()`/`filter()` | 📋 Planned | Phase 5 |
| `sorted()` | 📋 Planned | Phase 2 |
| `isinstance()` | 📋 Planned | Phase 3 |
| `type()` | 📋 Planned | Phase 3 |
| `hasattr()`/`getattr()`/`setattr()` | 📋 Planned | Phase 3 |
| `list()` | ✅ Implemented | Empty list constructor |
| `dict()` | ✅ Implemented | Empty dict constructor |

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

### Generators ⚠️

**Supported (Phase 5):**
```python
# Simple generators
def countdown(n: int) -> Generator[int, None, None]:
    while n > 0:
        yield n
        n -= 1
```

**NOT Supported:**
```python
# Generator expressions
gen = (x * x for x in range(10))  # ❌

# yield from
def chain(*iterables):
    for it in iterables:
        yield from it  # ❌

# Generator with send/throw
def echo():
    while True:
        x = yield  # ❌ Receiving values not supported
```

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

### Type Annotations ⚠️

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

**NOT Supported:**
```python
# TypeVar
T = TypeVar('T')
def identity(x: T) -> T: ...  # ❌

# Callable types
def higher_order(f: Callable[[int], int]) -> int: ...  # ⚠️ Limited

# Protocol
class MyProtocol(Protocol): ...  # ❌

# Literal types
def specific(x: Literal[1, 2, 3]) -> int: ...  # ❌
```

### String Operations ⚠️

**Supported:**
```python
# Basic operations
s = "hello"
length = len(s)
upper = s.upper()
concat = s + " world"
```

**NOT Supported:**
```python
# f-strings with expressions
f"{x + y}"  # ❌ Complex expressions in f-strings

# String formatting
"{:04d}".format(42)  # ❌ Complex format specs
```

## Out-of-Scope Features

These features will NOT be supported and will raise compilation errors.

### Async/Await ❌

```python
# NOT SUPPORTED
async def fetch_data() -> str:
    await some_coroutine()
    return "data"

# Reason: MicroPython's async implementation differs significantly
# from CPython. Users should use MicroPython's native uasyncio.
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

### Multiple Inheritance (for native classes) ❌

```python
# NOT SUPPORTED for compiled classes
class Child(Parent1, Parent2):
    pass

# Reason: Complex MRO and diamond problem handling.
# Single inheritance only for compiled classes.
# MicroPython built-in types can still be used as mixins.
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
| **1 (Core)** | `for` loops, `list`, `tuple`, `dict`, `set`, `range()`, `len()`, `print()` |
| **2 (Functions)** | Default args, `*args`, `**kwargs`, `enumerate()`, `zip()` |
| **3 (Classes)** | Basic classes, methods, properties, single inheritance |
| **4 (Exceptions)** | `try`/`except`/`finally`, `raise`, custom exceptions |
| **5 (Advanced)** | Simple closures, simple generators, `map()`/`filter()` |
| **6 (Polish)** | Optimization, edge cases, documentation |

## See Also

- [05-roadmap.md](05-roadmap.md) - Detailed implementation roadmap
- [02-mypyc-reference.md](02-mypyc-reference.md) - How mypyc handles these features
- [01-architecture.md](01-architecture.md) - Architecture overview
