# Implementation Roadmap

A 6-phase roadmap for mypyc-micropython from proof-of-concept to production-ready compiler.

## Table of Contents

- [Current State](#current-state)
- [Phase Overview](#phase-overview)
- [Phase 1: Core Completion](#phase-1-core-completion)
- [Phase 2: Functions & Arguments](#phase-2-functions--arguments)
- [Phase 3: Classes](#phase-3-classes)
- [Phase 4: Exception Handling](#phase-4-exception-handling)
- [Phase 5: Advanced Features](#phase-5-advanced-features)
- [Phase 6: Integration & Polish](#phase-6-integration--polish)
- [MicroPython C API Reference](#micropython-c-api-reference)
- [Timeline Estimates](#timeline-estimates)
- [Dependencies](#dependencies)

## Current State

### What Works Now ✅

- **Functions**: Typed parameters (`int`, `float`, `bool`), return values, recursion
- **Operators**: Arithmetic, comparison, bitwise, logical, augmented assignment, ternary
- **Control flow**: `if`/`elif`/`else`, `while` loops, `for` loops (range, list, dict, generic
  iterable), `break`, `continue`
- **Lists**: Literals, indexing, assignment, `append()`, `pop()`, `len()`, iteration
- **Dicts**: Literals, indexing, assignment, `get()`, `keys()`, `values()`, `items()`, `copy()`,
  `clear()`, `setdefault()`, `pop()`, `popitem()`, `update()`, `in`/`not in`, `dict(d)` copy
- **Built-ins**: `abs()`, `int()`, `float()`, `len()`, `range()` (1/2/3 args), `list()`, `dict()`
- **Other**: Local variables (typed and inferred), string literals, `None`, `True`/`False`

### What's Next ❌

- Tuples, sets, string operations
- `print()`, `bool()`, `min()`, `max()`, `sum()`
- Remaining list methods (`extend`, `insert`, `remove`, `count`, `index`, `reverse`, `sort`)
- List/dict slicing, concatenation, comprehensions
- Default arguments, `*args`, `**kwargs`
- Classes and methods
- Exception handling
- Closures and generators

## Phase Overview

```
Phase 1: Core Completion        ██████████░░░░░  ~65% done
  for loops ✅ │ lists (partial) │ dicts (86%) │ tuples │ sets │ builtins

Phase 2: Functions & Arguments  ░░░░░░░░░░░░░░░  TODO
  default args │ *args │ **kwargs │ enumerate │ zip │ sorted

Phase 3: Classes                ░░░░░░░░░░░░░░░  TODO
  class def │ __init__ │ methods │ @property │ inheritance

Phase 4: Exception Handling     ░░░░░░░░░░░░░░░  TODO
  try/except │ try/finally │ raise │ custom exceptions

Phase 5: Advanced Features      ░░░░░░░░░░░░░░░  TODO
  closures │ generators │ list comprehensions │ map/filter

Phase 6: Integration & Polish   ░░░░░░░░░░░░░░░  TODO
  ESP32 modules │ optimization │ error messages │ docs
```

---

## Phase 1: Core Completion

**Goal:** Make the compiler useful for basic data processing tasks.

### 1.1 For Loops ✅ DONE

All for-loop forms are implemented:

| Feature | Status | Implementation |
|---------|--------|----------------|
| `for x in range(n)` | ✅ | `_translate_for_range()` — optimized C for-loop |
| `for x in range(a, b)` | ✅ | 2-arg range with start/stop |
| `for x in range(a, b, step)` | ✅ | 3-arg range with constant-step optimization |
| `for x in iterable` | ✅ | `_translate_for_iterable()` — `mp_getiter()`/`mp_iternext()` |
| `break` | ✅ | Inline C `break` |
| `continue` | ✅ | Inline C `continue` |
| `for...else` | ❌ TODO | |

### 1.2 List Operations

**Implemented: 8/23 operations (35%)**

#### Construction

| Operation | Status | C API |
|-----------|--------|-------|
| `[item0, ..., itemN]` | ✅ | `mp_obj_new_list()` |
| `[]` | ✅ | `mp_obj_new_list(0, NULL)` |
| `list()` | ✅ | `mp_obj_new_list(0, NULL)` |
| `list(iterable)` | ❌ TODO | `mp_obj_list_make_new()` |
| `[expr for x in iter]` | ❌ TODO | List comprehension (Phase 5) |
| `[expr for x in iter if cond]` | ❌ TODO | Filtered comprehension (Phase 5) |

#### Operators

| Operation | Status | C API |
|-----------|--------|-------|
| `lst[n]` | ✅ | `mp_obj_subscr(lst, idx, MP_OBJ_SENTINEL)` |
| `lst[n:m]`, `lst[n:]`, `lst[:m]`, `lst[:]` | ❌ TODO | `mp_obj_subscr()` with `mp_obj_new_slice()` |
| `lst1 + lst2` | ❌ TODO | `mp_binary_op(MP_BINARY_OP_ADD, ...)` |
| `lst += iter` | ❌ TODO | `mp_binary_op(MP_BINARY_OP_INPLACE_ADD, ...)` |
| `lst * n` / `n * lst` | ❌ TODO | `mp_binary_op(MP_BINARY_OP_MULTIPLY, ...)` |
| `lst *= n` | ❌ TODO | `mp_binary_op(MP_BINARY_OP_INPLACE_MULTIPLY, ...)` |
| `obj in lst` | ❌ TODO | `mp_binary_op(MP_BINARY_OP_IN, ...)` |

#### Statements

| Operation | Status | C API |
|-----------|--------|-------|
| `lst[n] = x` | ✅ | `mp_obj_subscr(lst, idx, val)` |
| `for item in lst:` | ✅ | `mp_getiter()`/`mp_iternext()` |

#### Methods

| Operation | Status | C API |
|-----------|--------|-------|
| `lst.append(obj)` | ✅ | `mp_obj_list_append()` |
| `lst.pop()` / `lst.pop(i)` | ✅ | `mp_load_method(MP_QSTR_pop)` + call |
| `lst.extend(iterable)` | ❌ TODO | `mp_load_attr(MP_QSTR_extend)` + call |
| `lst.insert(i, obj)` | ❌ TODO | `mp_load_attr(MP_QSTR_insert)` + call |
| `lst.remove(obj)` | ❌ TODO | `mp_load_attr(MP_QSTR_remove)` + call |
| `lst.count(obj)` | ❌ TODO | `mp_load_attr(MP_QSTR_count)` + call |
| `lst.index(obj)` | ❌ TODO | `mp_load_attr(MP_QSTR_index)` + call |
| `lst.reverse()` | ❌ TODO | `mp_load_attr(MP_QSTR_reverse)` + call |
| `lst.sort()` | ❌ TODO | `mp_load_attr(MP_QSTR_sort)` + call |

#### Functions

| Operation | Status | C API |
|-----------|--------|-------|
| `len(lst)` | ✅ | `mp_obj_len()` |

### 1.3 Dict Operations

**Implemented: 18/21 operations (86%)**

#### Construction

| Operation | Status | C API |
|-----------|--------|-------|
| `{key: value, ...}` | ✅ | `mp_obj_new_dict()` + `mp_obj_dict_store()` |
| `{}` | ✅ | `mp_obj_new_dict(0)` |
| `dict()` | ✅ | `mp_obj_new_dict(0)` |
| `dict(d)` | ✅ | Copy from existing dict |
| `dict(iterable)` | ❌ TODO | Construct from iterable of pairs |
| `{k: v for x in iter}` | ❌ TODO | Dict comprehension (Phase 5) |
| `{k: v for x in iter if cond}` | ❌ TODO | Filtered comprehension (Phase 5) |

#### Operators

| Operation | Status | C API |
|-----------|--------|-------|
| `d[key]` | ✅ | `mp_obj_subscr()` |
| `key in d` | ✅ | `mp_binary_op(MP_BINARY_OP_IN, ...)` |

#### Statements

| Operation | Status | C API |
|-----------|--------|-------|
| `d[key] = value` | ✅ | `mp_obj_subscr()` |
| `for key in d:` | ✅ | `mp_getiter()`/`mp_iternext()` |

#### Methods

| Operation | Status | C API |
|-----------|--------|-------|
| `d.get(key)` | ✅ | `mp_obj_dict_get()` |
| `d.get(key, default)` | ✅ | Method call with 2 args |
| `d.keys()` | ✅ | `mp_load_attr(MP_QSTR_keys)` + call |
| `d.values()` | ✅ | `mp_load_attr(MP_QSTR_values)` + call |
| `d.items()` | ✅ | `mp_load_attr(MP_QSTR_items)` + call |
| `d.copy()` | ✅ | `mp_load_attr(MP_QSTR_copy)` + call |
| `d.clear()` | ✅ | `mp_load_attr(MP_QSTR_clear)` + call |
| `d.setdefault(key)` | ✅ | `mp_call_function_1()` |
| `d.setdefault(key, value)` | ✅ | `mp_call_function_n_kw()` |
| `d.update(d2)` | ✅ | `mp_load_attr(MP_QSTR_update)` + call |
| `d.pop(key)` | ✅ | `mp_load_method(MP_QSTR_pop)` + call |
| `d.pop(key, default)` | ✅ | `mp_load_method(MP_QSTR_pop)` + call |
| `d.popitem()` | ✅ | `mp_load_attr(MP_QSTR_popitem)` + call |

#### Functions

| Operation | Status | C API |
|-----------|--------|-------|
| `len(d)` | ✅ | `mp_obj_len()` |

### 1.4 Tuple Support

| Feature | Status |
|---------|--------|
| Tuple creation: `(1, 2, 3)` | ❌ TODO |
| Tuple unpacking: `a, b, c = tup` | ❌ TODO |
| Tuple indexing | ❌ TODO |
| Named tuple | ❌ TODO (low priority) |

### 1.5 Set Support

| Feature | Status |
|---------|--------|
| Set creation: `{1, 2, 3}` | ❌ TODO |
| Set operations: `union`, `intersection`, `difference` | ❌ TODO |
| `in` operator | ❌ TODO |
| Set iteration | ❌ TODO |

### 1.6 Built-in Functions

| Feature | Status | Notes |
|---------|--------|-------|
| `range(start, stop, step)` | ✅ | 1/2/3 arg forms, optimized in for-loops |
| `len(obj)` | ✅ | Returns `mp_int_t` via `mp_obj_len()` |
| `abs(x)` | ✅ | Native expression: `((a) < 0 ? -(a) : (a))` |
| `int(x)` | ✅ | Cast: `((mp_int_t)(x))` |
| `float(x)` | ✅ | Cast: `((mp_float_t)(x))` |
| `list()` | ✅ | Empty list constructor |
| `dict()` / `dict(d)` | ✅ | Empty or copy constructor |
| `print(*args)` | ❌ TODO | |
| `bool(obj)` | ❌ TODO | |
| `min()` / `max()` | ❌ TODO | |
| `sum(iterable)` | ❌ TODO | |

---

## Phase 2: Functions & Arguments

**Goal:** Full function signature support.

### 2.1 Default Arguments

```python
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"
```

Tasks:
- [ ] Parse default argument values in function signatures
- [ ] Generate wrapper with argument count checking (`MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN`)
- [ ] Store defaults as module constants
- [ ] Handle mutable defaults correctly (warn or error)

### 2.2 *args Support

```python
def sum_all(*args: int) -> int:
    return sum(args)
```

Tasks:
- [ ] Detect `*args` in function signature
- [ ] Generate variadic function wrapper (`MP_DEFINE_CONST_FUN_OBJ_VAR`)
- [ ] Handle mixed positional + `*args`

### 2.3 **kwargs Support

```python
def configure(**kwargs: str) -> dict:
    return kwargs
```

Tasks:
- [ ] Detect `**kwargs` in function signature
- [ ] Generate KW function wrapper (`MP_DEFINE_CONST_FUN_OBJ_KW`) using `mp_arg_parse_all`
- [ ] Handle mixed positional + `*args` + `**kwargs`

### 2.4 Keyword-Only Arguments

```python
def process(data: list, *, validate: bool = True) -> list:
    ...
```

Tasks:
- [ ] Parse keyword-only arguments (after `*`)
- [ ] Generate appropriate argument parsing

### 2.5 Additional Built-ins

| Feature | Status |
|---------|--------|
| `enumerate(iterable, start=0)` | ❌ TODO |
| `zip(*iterables)` | ❌ TODO |
| `sorted(iterable, key=None, reverse=False)` | ❌ TODO |
| `reversed(sequence)` | ❌ TODO |

---

## Phase 3: Classes

**Goal:** Basic OOP support.

### 3.1 Basic Class Definition

```python
class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def distance(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5
```

Tasks:
- [ ] Parse class definitions
- [ ] Generate struct for instance data
- [ ] Generate `make_new` (constructor)
- [ ] Generate type definition

### 3.2 Instance Methods

Tasks:
- [ ] Translate methods with `self` parameter
- [ ] Generate method binding
- [ ] Handle method calls on instances

### 3.3 Properties

Tasks:
- [ ] Detect `@property` decorator
- [ ] Generate getter/setter in attr handler
- [ ] Support read-only properties

### 3.4 Static and Class Methods

Tasks:
- [ ] `@staticmethod` — no self parameter
- [ ] `@classmethod` — cls parameter

### 3.5 Single Inheritance

Tasks:
- [ ] Parse inheritance
- [ ] Set parent type in type definition
- [ ] Method resolution (child overrides parent)
- [ ] Super calls: `super().__init__()`

### 3.6 Special Methods

Tasks:
- [ ] `__str__` / `__repr__`
- [ ] `__len__`
- [ ] `__getitem__` / `__setitem__`
- [ ] `__eq__` / `__ne__` / `__lt__` / etc.
- [ ] `__hash__`
- [ ] `__iter__` / `__next__`

---

## Phase 4: Exception Handling

**Goal:** Robust error handling.

### 4.1 Try/Except

```python
def safe_divide(a: int, b: int) -> int:
    try:
        return a // b
    except ZeroDivisionError:
        return 0
```

Generated C uses `nlr_push`/`nlr_pop` pattern with `mp_obj_is_subclass_fast` for type matching.

Tasks:
- [ ] Parse try/except blocks
- [ ] Generate `nlr_push`/`nlr_pop` pattern
- [ ] Exception type matching
- [ ] Multiple except clauses
- [ ] Catch-all except

### 4.2 Try/Finally

Tasks:
- [ ] Parse try/finally blocks
- [ ] Ensure finally runs on all paths
- [ ] Combine try/except/finally

### 4.3 Raise

Tasks:
- [ ] `raise ExceptionType(message)`
- [ ] `raise` (re-raise current exception)
- [ ] `raise ... from ...` (basic support)

### 4.4 Custom Exceptions

Tasks:
- [ ] Custom exception class definition
- [ ] Inheritance from built-in exceptions

---

## Phase 5: Advanced Features

**Goal:** Support functional programming patterns.

### 5.1 Closures (Read-Only)

```python
def make_multiplier(factor: int) -> Callable[[int], int]:
    def multiply(x: int) -> int:
        return x * factor  # Read-only capture
    return multiply
```

Tasks:
- [ ] Detect captured variables
- [ ] Generate environment struct
- [ ] Generate callable closure type
- [ ] Limit to read-only captures initially

### 5.2 Simple Generators

```python
def countdown(n: int) -> Generator[int, None, None]:
    while n > 0:
        yield n
        n -= 1
```

Tasks:
- [ ] Detect generator functions (contain yield)
- [ ] Transform to state machine
- [ ] Generate iterator type
- [ ] Handle `return` in generators

### 5.3 Comprehensions

Tasks:
- [ ] List comprehensions: `[expr for x in iter]`, with optional `if` filter
- [ ] Dict comprehensions: `{k: v for x in iter}`, with optional `if` filter
- [ ] Generate equivalent loop code

### 5.4 Additional Built-ins

Tasks:
- [ ] `map(func, iterable)`
- [ ] `filter(func, iterable)`
- [ ] `any(iterable)` / `all(iterable)`

---

## Phase 6: Integration & Polish

**Goal:** Production-ready quality.

### 6.1 ESP32 Module Integration

Tasks:
- [ ] Document ESP32 module calling patterns
- [ ] Create helper macros for common modules
- [ ] Example: GPIO blink using `machine.Pin`
- [ ] Example: WiFi connection using `network.WLAN`
- [ ] Test on actual ESP32 hardware

### 6.2 Optimization

Tasks:
- [ ] Constant folding
- [ ] Dead code elimination
- [ ] Inline small functions
- [ ] Reduce boxing/unboxing operations

### 6.3 Error Messages

Tasks:
- [ ] Clear error messages for unsupported features
- [ ] Line number references in errors
- [ ] Suggestions for common mistakes

### 6.4 Documentation & Testing

Tasks:
- [ ] Complete API reference
- [ ] Tutorial: Getting Started
- [ ] Tutorial: ESP32 Development
- [ ] Comprehensive test suite
- [ ] CI/CD pipeline
- [ ] Test on multiple targets (Unix, ESP32, RP2040)

---

## MicroPython C API Reference

Quick reference for the C APIs used in generated code.

### List Operations

| Python | C API | Notes |
|--------|-------|-------|
| `lst[n]` | `mp_obj_subscr(lst, idx, MP_OBJ_SENTINEL)` | Get item |
| `lst[n] = x` | `mp_obj_subscr(lst, idx, val)` | Set item |
| `obj in lst` | `mp_binary_op(MP_BINARY_OP_IN, obj, lst)` | Membership |
| `lst.append(obj)` | `mp_obj_list_append(lst, obj)` | Direct API |
| `lst.extend(iter)` | `mp_load_attr(MP_QSTR_extend)` + call | Method call |
| `lst.insert(i, obj)` | `mp_load_attr(MP_QSTR_insert)` + call | Method call |
| `lst.pop()` | `mp_load_method(MP_QSTR_pop)` + call | 0/1/2-arg forms |
| `lst.remove(obj)` | `mp_load_attr(MP_QSTR_remove)` + call | Method call |
| `lst.count(obj)` | `mp_load_attr(MP_QSTR_count)` + call | Method call |
| `lst.index(obj)` | `mp_load_attr(MP_QSTR_index)` + call | Method call |
| `lst.reverse()` | `mp_load_attr(MP_QSTR_reverse)` + call | Method call |
| `lst.sort()` | `mp_load_attr(MP_QSTR_sort)` + call | Method call |
| `len(lst)` | `mp_obj_len(lst)` | Returns `mp_obj_t` |
| `lst[n:m]` | `mp_obj_subscr(lst, mp_obj_new_slice(...), ...)` | Slice object |
| `lst1 + lst2` | `mp_binary_op(MP_BINARY_OP_ADD, lst1, lst2)` | Binary op |

### Dict Operations

| Python | C API | Notes |
|--------|-------|-------|
| `d[key]` | `mp_obj_subscr(d, key, MP_OBJ_SENTINEL)` | Get item |
| `d[key] = val` | `mp_obj_subscr(d, key, val)` | Set item |
| `key in d` | `mp_binary_op(MP_BINARY_OP_IN, key, d)` | Membership |
| `d.get(key)` | `mp_obj_dict_get(d, key)` | Direct API |
| `d.get(key, default)` | `mp_call_function_n_kw(...)` | Method call, 2 args |
| `d.keys()` | `mp_load_attr(MP_QSTR_keys)` + call | Returns view |
| `d.values()` | `mp_load_attr(MP_QSTR_values)` + call | Returns view |
| `d.items()` | `mp_load_attr(MP_QSTR_items)` + call | Returns view |
| `d.copy()` | `mp_load_attr(MP_QSTR_copy)` + call | Returns new dict |
| `d.clear()` | `mp_load_attr(MP_QSTR_clear)` + call | Returns None |
| `d.setdefault(k, v)` | `mp_call_function_n_kw(...)` | 1 or 2 args |
| `d.update(d2)` | `mp_load_attr(MP_QSTR_update)` + call | Method call |
| `d.pop(key)` | `mp_load_method(MP_QSTR_pop)` + call | 1 or 2 args |
| `d.popitem()` | `mp_load_attr(MP_QSTR_popitem)` + call | Returns tuple |
| `len(d)` | `mp_obj_len(d)` | Returns `mp_obj_t` |

---

## Timeline Estimates

| Phase | Estimated Duration | Cumulative |
|-------|-------------------|------------|
| Phase 1: Core (remaining) | 2-3 weeks | 2-3 weeks |
| Phase 2: Functions | 2-3 weeks | 4-6 weeks |
| Phase 3: Classes | 4-6 weeks | 8-12 weeks |
| Phase 4: Exceptions | 2-3 weeks | 10-15 weeks |
| Phase 5: Advanced | 4-6 weeks | 14-21 weeks |
| Phase 6: Polish | 4-6 weeks | 18-27 weeks |

## Dependencies

```
Phase 1 (Core) ← ~65% done
    │
    ├── Phase 2 (Functions) ─── needs list/tuple for *args
    │
    └── Phase 3 (Classes) ─── needs Phase 2 for method signatures
            │
            └── Phase 4 (Exceptions) ─── needs classes for custom exceptions
                    │
                    └── Phase 5 (Advanced) ─── needs exceptions for generators
                            │
                            └── Phase 6 (Polish)
```

### External Dependencies

- MicroPython source (for headers and reference)
- mypy (for type checking, optional future integration)
- ESP-IDF (for ESP32 builds)
- Cross-compiler toolchain

## See Also

- [04-feature-scope.md](04-feature-scope.md) — Feature scope definition
- [02-mypyc-reference.md](02-mypyc-reference.md) — Implementation reference
- [01-architecture.md](01-architecture.md) — Architecture overview
- [03-micropython-c-api.md](03-micropython-c-api.md) — Full MicroPython C API reference
