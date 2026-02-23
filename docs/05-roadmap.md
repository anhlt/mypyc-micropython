# Implementation Roadmap

A 7-phase roadmap for mypyc-micropython from proof-of-concept to production-ready compiler.

## Table of Contents

- [Current State](#current-state)
- [Phase Overview](#phase-overview)
- [Phase 1: Core Completion](#phase-1-core-completion)
- [Phase 2: Functions & Arguments](#phase-2-functions--arguments)
- [Phase 3: Classes](#phase-3-classes)
- [Phase 4: Exception Handling](#phase-4-exception-handling)
- [Phase 5: Advanced Features](#phase-5-advanced-features)
- [Phase 6: Integration & Polish](#phase-6-integration--polish)
- [Phase 7: Type-Based Optimizations](#phase-7-type-based-optimizations)
- [MicroPython C API Reference](#micropython-c-api-reference)
- [Timeline Estimates](#timeline-estimates)
- [Dependencies](#dependencies)

## Current State

### What Works Now ✅

- **Functions**: Typed parameters (`int`, `float`, `bool`), return values, recursion, default
  arguments, `*args`, `**kwargs`
- **Operators**: Arithmetic, comparison, bitwise, logical, augmented assignment, ternary
- **Control flow**: `if`/`elif`/`else`, `while` loops, `for` loops (range, list, dict, generic
  iterable), `break`, `continue`
- **Lists**: Literals, indexing, assignment, `append()`, `pop()`, `len()`, iteration, slicing,
  concatenation, repetition
- **Dicts**: Literals, indexing, assignment, `get()`, `keys()`, `values()`, `items()`, `copy()`,
  `clear()`, `setdefault()`, `pop()`, `popitem()`, `update()`, `in`/`not in`, `dict(d)` copy
- **Tuples**: Literals, indexing, slicing, unpacking, concatenation, repetition, `tuple()`,
  `tuple(iterable)`, iteration
- **Sets**: Literals, `set()`, `set(iterable)`, `add()`, `remove()`, `discard()`, `update()`,
  `clear()`, `copy()`, `pop()`, `in` operator, iteration
- **Built-ins**: `abs()`, `int()`, `float()`, `len()`, `range()` (1/2/3 args), `list()`, `dict()`,
  `print()`, `bool()`, `min()`, `max()`, `sum()` (with inline optimization for typed lists)
- **Classes**: Class definitions with typed fields, `__init__`, instance methods, `@dataclass`,
  single inheritance with vtable-based virtual dispatch, `__eq__`, `__len__`, `__getitem__`,
  `__setitem__`, class fields with `list`/`dict` types, augmented assignment on fields
- **IR pipeline**: Full two-phase architecture (IRBuilder → Emitters), StmtIR/ExprIR/ValueIR
  hierarchies, prelude pattern for side effects, BinOp type inference, RTuple optimization
- **ESP32**: All 16 compiled modules verified on real ESP32-C6 hardware (161 device tests pass)
- **Performance**: RTuple internal ops (57x speedup), list[tuple] (9.2x speedup), 22 benchmarks
  suite with 11.8x average speedup
- **Testing**: 518 tests (unit + C runtime), comprehensive device test coverage
- **Strings**: Full method support (`split`, `join`, `replace`, `find`, `strip`, `upper`, `lower`, etc.)
- **Type Checking**: Optional mypy integration via `type_check=True` parameter, extracts function/class signatures
- **Exception Handling**: `try`/`except`/`else`/`finally`, `raise`, multiple handlers, exception variable binding
- **Other**: Local variables (typed and inferred), string literals, `None`, `True`/`False`

### What's Next ❌

- `sum(generator_expr)` — inline loop optimization (Phase 5)
- Remaining list methods (`extend`, `insert`, `remove`, `count`, `index`, `reverse`, `sort`)
- List/dict comprehensions
- Keyword-only arguments, positional-only arguments
- `@property`, `@staticmethod`, `@classmethod`
 Custom exception classes
- Closures and generators

## Phase Overview

```
Phase 1: Core Completion        ██████████████░  ~90% done
  for loops ✅ │ lists ✅ │ dicts ✅ │ tuples ✅ │ sets ✅ │ strings ✅ │ builtins (partial)

Phase 2: Functions & Arguments  █████████████░░  ~85% done
  default args ✅ │ *args ✅ │ **kwargs ✅ │ bool ✅ │ min/max ✅ │ sum ✅
  enumerate ✅ │ zip ✅ │ sorted ✅ │ keyword-only args │ positional-only args

Phase 3: Classes                ███████████████  ~95% done
  class def ✅ │ __init__ ✅ │ methods ✅ │ @dataclass ✅ │ inheritance ✅
  vtable dispatch ✅ │ __eq__/__len__/__getitem__/__setitem__ ✅ │ inherited methods ✅
  @property │ @staticmethod │ @classmethod

Phase 4: Exception Handling     ███████████████  ~95% done
  try/except ✅ │ try/finally ✅ │ try/except/else ✅ │ raise ✅ │ custom exceptions

Phase 5: Advanced Features      ░░░░░░░░░░░░░░░  TODO
  closures │ generators │ list comprehensions │ map/filter

Phase 6: Integration & Polish   █████████████░░  ~85% done
  ESP32 modules ✅ (17 modules on ESP32-C6) │ RTuple optimization ✅ (57x speedup)
  list access optimization ✅ │ benchmarks ✅ (22 tests, 11.8x avg) │ Full IR pipeline ✅
  504 tests ✅ │ type checking ✅ (strict by default) │ error messages │ docs

Phase 7: Type-Based Optimizations  ░░░░░░░░░░░░░░░  TODO (new!)
  native int arithmetic │ typed local variables │ typed list access
  typed iteration │ dict value types │ expression type propagation
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

| Feature | Status | C API |
|---------|--------|-------|
| Tuple creation: `(1, 2, 3)` | ✅ | `mp_obj_new_tuple()` |
| Empty tuple: `()` | ✅ | `mp_const_empty_tuple` |
| Tuple indexing: `t[n]` | ✅ | `mp_obj_subscr()` |
| Tuple slicing: `t[n:m]` | ✅ | `mp_obj_subscr()` with `mp_obj_new_slice()` |
| Tuple unpacking: `a, b, c = t` | ✅ | Sequential `mp_obj_subscr()` |
| Tuple concatenation: `t1 + t2` | ✅ | `mp_binary_op(MP_BINARY_OP_ADD)` |
| Tuple repetition: `t * n` | ✅ | `mp_binary_op(MP_BINARY_OP_MULTIPLY)` |
| `tuple()` constructor | ✅ | `mp_const_empty_tuple` |
| `tuple(iterable)` | ✅ | `mp_obj_tuple_make_new()` |
| `len(t)` | ✅ | `mp_obj_len()` |
| Tuple iteration | ✅ | `mp_getiter()`/`mp_iternext()` |
| Named tuple | ❌ TODO (low priority) | |

### 1.5 Set Support

| Feature | Status | C API |
|---------|--------|-------|
| Set creation: `{1, 2, 3}` | ✅ | `mp_obj_new_set()` |
| Empty set: `set()` | ✅ | `mp_obj_new_set(0, NULL)` |
| `set(iterable)` | ✅ | `mp_obj_set_make_new()` |
| `in` operator | ✅ | `mp_binary_op(MP_BINARY_OP_IN)` |
| `s.add(item)` | ✅ | `mp_obj_set_store()` |
| `s.remove(item)` | ✅ | `mp_load_attr(MP_QSTR_remove)` + call |
| `s.discard(item)` | ✅ | `mp_load_attr(MP_QSTR_discard)` + call |
| `s.update(iterable)` | ✅ | `mp_load_attr(MP_QSTR_update)` + call |
| `s.clear()` | ✅ | `mp_load_attr(MP_QSTR_clear)` + call |
| `s.copy()` | ✅ | `mp_load_attr(MP_QSTR_copy)` + call |
| `s.pop()` | ✅ | `mp_load_attr(MP_QSTR_pop)` + call |
| `len(s)` | ✅ | `mp_obj_len()` |
| Set iteration | ✅ | `mp_getiter()`/`mp_iternext()` |
| Set operations: `union`, `intersection`, `difference` | ❌ TODO | |

### 1.6 String Operations ✅ DONE

**Implemented: Full string method support via MicroPython runtime**

String operations are implemented using MicroPython's `mp_load_attr(MP_QSTR_method)` + call pattern,
matching mypyc's approach of delegating to the runtime for string operations.

**Note:** Some methods (`capitalize`, `title`, `swapcase`, `ljust`, `rjust`, `zfill`) are not
available in MicroPython ESP32 by default. They require `MICROPY_PY_BUILTINS_STR_UNICODE_FULL`.

#### Construction

| Operation | Status | C API |
|-----------|--------|-------|
| `"hello"` | ✅ | `mp_obj_new_str("hello", 5)` |
| `str(x)` | ✅ | `mp_call_function_1(&mp_type_str, x)` |

#### Operators

| Operation | Status | C API |
|-----------|--------|-------|
| `s1 + s2` | ✅ | `mp_binary_op(MP_BINARY_OP_ADD)` |
| `s[n]` | ✅ | `mp_obj_subscr()` |
| `s[n:m]` | ✅ | `mp_obj_subscr()` with slice |
| `s1 == s2` | ✅ | `mp_binary_op(MP_BINARY_OP_EQUAL)` |
| `s1 += s2` | ✅ | `mp_binary_op(MP_BINARY_OP_INPLACE_ADD)` |
| `s1 in s2` | ✅ | `mp_binary_op(MP_BINARY_OP_IN)` |

#### Methods (Available on ESP32)

| Operation | Status | C API |
|-----------|--------|-------|
| `s.split()` | ✅ | `mp_load_attr(MP_QSTR_split)` + call |
| `s.split(sep)` | ✅ | With separator argument |
| `s.split(sep, maxsplit)` | ✅ | With maxsplit argument |
| `s.rsplit()` | ✅ | Right-to-left split |
| `s.join(iterable)` | ✅ | `mp_load_attr(MP_QSTR_join)` + call |
| `s.replace(old, new)` | ✅ | `mp_load_attr(MP_QSTR_replace)` + call |
| `s.replace(old, new, count)` | ✅ | With count limit |
| `s.startswith(prefix)` | ✅ | `mp_load_attr(MP_QSTR_startswith)` + call |
| `s.endswith(suffix)` | ✅ | `mp_load_attr(MP_QSTR_endswith)` + call |
| `s.find(sub)` | ✅ | `mp_load_attr(MP_QSTR_find)` + call |
| `s.find(sub, start)` | ✅ | With start position |
| `s.find(sub, start, end)` | ✅ | With start and end |
| `s.rfind(sub)` | ✅ | Right-to-left find |
| `s.strip()` | ✅ | `mp_load_attr(MP_QSTR_strip)` + call |
| `s.strip(chars)` | ✅ | Strip specific chars |
| `s.lstrip()` | ✅ | Left strip |
| `s.rstrip()` | ✅ | Right strip |
| `s.upper()` | ✅ | `mp_load_attr(MP_QSTR_upper)` + call |
| `s.lower()` | ✅ | `mp_load_attr(MP_QSTR_lower)` + call |
| `s.center(width)` | ✅ | `mp_load_attr(MP_QSTR_center)` + call |
| `s.isdigit()` | ✅ | `mp_load_attr(MP_QSTR_isdigit)` + call |
| `s.isalpha()` | ✅ | `mp_load_attr(MP_QSTR_isalpha)` + call |
| `s.isspace()` | ✅ | `mp_load_attr(MP_QSTR_isspace)` + call |
| `s.isupper()` | ✅ | `mp_load_attr(MP_QSTR_isupper)` + call |
| `s.islower()` | ✅ | `mp_load_attr(MP_QSTR_islower)` + call |
| `s.partition(sep)` | ✅ | `mp_load_attr(MP_QSTR_partition)` + call |
| `s.rpartition(sep)` | ✅ | `mp_load_attr(MP_QSTR_rpartition)` + call |
| `s.splitlines()` | ✅ | `mp_load_attr(MP_QSTR_splitlines)` + call |
| `s.encode()` | ✅ | `mp_load_attr(MP_QSTR_encode)` + call |
| `s.count(sub)` | ✅ | `mp_load_attr(MP_QSTR_count)` + call |

#### Functions

| Operation | Status | C API |
|-----------|--------|-------|
| `len(s)` | ✅ | `mp_obj_len()` |
| `ord(s)` | ✅ | `mp_ord()` via builtin |

### 1.7 Built-in Functions

| Feature | Status | Notes |
|---------|--------|-------|
| `range(start, stop, step)` | ✅ | 1/2/3 arg forms, optimized in for-loops |
| `len(obj)` | ✅ | Returns `mp_int_t` via `mp_obj_len()` |
| `abs(x)` | ✅ | Native expression: `((a) < 0 ? -(a) : (a))` |
| `int(x)` | ✅ | Cast: `((mp_int_t)(x))` |
| `float(x)` | ✅ | Cast: `((mp_float_t)(x))` |
| `list()` | ✅ | Empty list constructor |
| `dict()` / `dict(d)` | ✅ | Empty or copy constructor |
| `print(*args)` | ✅ | `mp_obj_print_helper()` with space separator |
| `bool(obj)` | ✅ | `mp_obj_is_true()` for truthiness check |
| `min()` / `max()` | ✅ | 2+ args via `mp_builtin_min_obj`/`mp_builtin_max_obj` |
| `sum(iterable)` | ✅ | Via `mp_builtin_sum_obj`, optional start value |

---

## Phase 2: Functions & Arguments

**Goal:** Full function signature support.

### 2.1 Default Arguments ✅ DONE

```python
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"
```

Implemented:
- [x] Parse default argument values in function signatures
- [x] Generate wrapper with argument count checking (`MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN`)
- [x] Store defaults as inline C literals in ternary expressions
- [x] Support for `int`, `float`, `bool`, `str`, `None` defaults
- [x] Support for empty container defaults: `[]`, `{}`, `()`
- [x] Negative numeric defaults
- [x] Mixed required + optional parameters

### 2.2 *args Support ✅ DONE

```python
def sum_all(*args: int) -> int:
    return sum(args)
```

Implemented:
- [x] Detect `*args` in function signature
- [x] Generate variadic function wrapper (`MP_DEFINE_CONST_FUN_OBJ_VAR`)
- [x] Handle mixed positional + `*args`
- [x] Create tuple from args via `mp_obj_new_tuple(n_args, args)`
- [x] Use `_star_` prefix for C variable naming to avoid shadowing

### 2.3 **kwargs Support ✅ DONE

```python
def configure(**kwargs: str) -> dict:
    return kwargs
```

Implemented:
- [x] Detect `**kwargs` in function signature
- [x] Generate KW function wrapper (`MP_DEFINE_CONST_FUN_OBJ_KW`)
- [x] Handle mixed positional + `*args` + `**kwargs`
- [x] Create dict from `mp_map_t` by iterating slots
- [x] Proper slot iteration with `mp_map_slot_is_filled()` check

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
| `bool(obj)` | ✅ Implemented |
| `min()` / `max()` | ✅ Implemented |
| `sum(iterable)` | ✅ Implemented |
| `enumerate(iterable, start=0)` | ✅ Implemented |
| `zip(*iterables)` | ✅ Implemented |
| `sorted(iterable, key=None, reverse=False)` | ✅ Implemented (basic, no key/reverse) |
| `reversed(sequence)` | ❌ TODO |

---

## Phase 3: Classes

**Goal:** Basic OOP support.

### 3.1 Basic Class Definition ✅ DONE

```python
class Counter:
    value: int
    step: int

    def __init__(self, start: int, step: int) -> None:
        self.value = start
        self.step = step

    def increment(self) -> int:
        self.value += self.step
        return self.value
```

Tasks:
- [x] Parse class definitions
- [x] Generate struct for instance data (native C types: `mp_int_t`, `mp_float_t`, `bool`, `mp_obj_t`)
- [x] Generate `make_new` (constructor)
- [x] Generate type definition with `attr` handler
- [x] Support `@dataclass` classes with auto-generated `__init__` and `__eq__`

### 3.2 Instance Methods ✅ DONE

Tasks:
- [x] Translate methods with `self` parameter (native and boxed calling conventions)
- [x] Generate method binding (`MP_DEFINE_CONST_FUN_OBJ_*`)
- [x] Handle method calls on instances via `locals_dict`
- [x] Support `VAR_BETWEEN` calling convention for methods with >3 args
- [x] Support list/dict fields in methods (container IR + prelude flush)
- [x] Augmented assignment on `self.field` (e.g., `self.count += 1`)

### 3.3 Properties

Tasks:
- [ ] Detect `@property` decorator
- [ ] Generate getter/setter in attr handler
- [ ] Support read-only properties

### 3.4 Static and Class Methods

Tasks:
- [ ] `@staticmethod` — no self parameter
- [ ] `@classmethod` — cls parameter

### 3.5 Single Inheritance ✅ DONE (with known limitations)

```python
class BoundedCounter(Counter):
    min_val: int
    max_val: int

    def increment(self) -> int:   # overrides Counter.increment
        self.value += self.step
        if self.value > self.max_val:
            self.value = self.max_val
        return self.value
```

Tasks:
- [x] Parse inheritance (`class Child(Parent)`)
- [x] Struct embedding via `super` field for parent data
- [x] Vtable-based virtual method dispatch
- [x] Vtable type generation with function pointers
- [x] Child class vtable with correct pointer casts for inherited methods
- [x] Vtable access path computation for deep inheritance (`super.super.vtable`)
- [x] `__eq__` using `mp_obj_get_type()` for correct runtime type checking
- [x] Multi-level inheritance (grandchild classes)
- [x] Inherited method propagation — non-overridden parent methods now visible
  in child class `locals_dict`
- [x] `super()` calls in methods (e.g., `super().__init__(...)`)

### 3.6 Special Methods (Partial)

Tasks:
- [ ] `__str__` / `__repr__`
- [x] `__len__` — supported in `locals_dict`
- [x] `__getitem__` / `__setitem__` — supported in `locals_dict`
- [x] `__eq__` — auto-generated for `@dataclass`, field-by-field comparison
- [ ] `__ne__` / `__lt__` / `__gt__` / `__le__` / `__ge__`
- [ ] `__hash__`
- [ ] `__iter__` / `__next__`

### 3.7 Known Limitations & Future Improvements

| Issue | Description | Workaround |
|-------|-------------|------------|
| No `@property` | No getter/setter decorator support | Use explicit getter/setter methods |
| No `@staticmethod`/`@classmethod` | Only instance methods supported | Use module-level functions instead |

---

## Phase 4: Exception Handling

**Goal:** Robust error handling.

### 4.1 Try/Except ✅ DONE

```python
def safe_divide(a: int, b: int) -> int:
    try:
        return a // b
    except ZeroDivisionError:
        return 0
```

Generated C uses `nlr_push`/`nlr_pop` pattern with `mp_obj_is_subclass_fast` for type matching.

Tasks:
- [x] Parse try/except blocks
- [x] Generate `nlr_push`/`nlr_pop` pattern
- [x] Exception type matching
- [x] Multiple except clauses
- [x] Catch-all except
- [x] Exception variable binding (`except E as e:`)
- [x] Try/except/else blocks

### 4.2 Try/Finally ✅ DONE

Tasks:
- [x] Parse try/finally blocks
- [x] Ensure finally runs on all paths
- [x] Combine try/except/finally
- [x] Re-raise after finally if exception was not caught

### 4.3 Raise ✅ DONE

Tasks:
- [x] `raise ExceptionType(message)`
- [x] `raise ExceptionType` (without message)
- [ ] `raise` (re-raise current exception) — TODO
- [ ] `raise ... from ...` (basic support) — TODO

### 4.4 Custom Exceptions

Tasks:
- [ ] Custom exception class definition
- [ ] Inheritance from built-in exceptions

### 4.5 Supported Exception Types

The following built-in exception types are supported:
- `ZeroDivisionError`, `ValueError`, `TypeError`, `RuntimeError`
- `KeyError`, `IndexError`, `AttributeError`, `OverflowError`
- `MemoryError`, `OSError`, `NotImplementedError`, `AssertionError`

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
- [ ] `sum(generator_expr)` — inline loop optimization (mypyc-style)

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

**Research Finding (from mypyc analysis):**
mypyc uses **type erasure** for container element types - `list[int]` and `list[str]` generate
identical code. However, **fixed-length tuples** (`tuple[int, int]`) are special: they become
**unboxed C structs** allocated on stack/registers, not heap-allocated Python objects.

| Type | Representation | Boxing |
|------|----------------|--------|
| `int`, `float`, `bool` | Native C types | Unboxed (value type) |
| `tuple[int, int]` | C struct | Unboxed until passed to Python |
| `tuple[int, ...]` | Python tuple | Always boxed |
| `list[int]`, `set[int]` | Python objects | Always boxed (elements too) |

**Optimization Phases:**

#### Phase A: Native Fixed-Length Tuples (RTuple-style) ✅ DONE

For `tuple[int, int]`, generate C struct instead of Python tuple:
```c
typedef struct { mp_int_t f0; mp_int_t f1; } rtuple_int_int_t;
static rtuple_int_int_t make_point(void) { return (rtuple_int_int_t){10, 20}; }
```

Tasks:
- [x] Track tuple element types in IR (`RTuple` with element `CType` list)
- [x] Generate C struct typedefs for fixed-length tuples
- [x] Emit struct literals instead of `mp_obj_new_tuple()`
- [x] Direct field access instead of `mp_obj_subscr()`
- [x] Box to `mp_obj_t` only when passing to MicroPython APIs
- [x] Direct `tup->items[]` access for unboxing from list elements

**Benchmark Results (ESP32-C6):**
| Benchmark | Native (us) | Python (us) | Speedup |
|-----------|-------------|-------------|---------|
| rtuple_internal x100 | 18,429 | 866,774 | **47.0x** |
| list[tuple] x500 | 61,669 | 414,369 | **6.7x** |

#### Phase B: Optimized List Access ✅ DONE

When accessing typed list variables, bypass generic `mp_obj_subscr()` dispatch:
```c
// Generic (slow): mp_obj_subscr(list, MP_OBJ_NEW_SMALL_INT(i), MP_OBJ_SENTINEL)
// Optimized (fast): mp_list_get_int(list, i) -> direct items[] access
```

Tasks:
- [x] Track `list` variables via annotation
- [x] Generate `mp_list_get_*` helpers for direct access
- [x] Inline `mp_list_len_fast()` for `len(lst)` on known lists

#### Phase C: Optimized Iteration Patterns ❌ TODO

When iterating typed containers, inline unboxing:
```c
// Instead of mp_obj_subscr + mp_obj_get_int per element:
mp_obj_list_t *list = MP_OBJ_TO_PTR(lst);
for (size_t i = 0; i < list->len; i++) {
    sum += mp_obj_get_int(list->items[i]);
}
```

Tasks:
- [ ] Detect `for x in lst` where `lst: list[int]`
- [ ] Use direct `mp_obj_list_t` struct access
- [ ] Inline `mp_obj_get_int()` in loop body

#### Phase D: Additional Optimizations ❌ TODO

Tasks:
- [ ] Constant folding
- [ ] Dead code elimination
- [ ] Inline small functions

---

## Phase 7: Type-Based Optimizations

**Goal:** Use mypy's resolved type information to generate faster code.

### Background: What Mypy Gives Us

With strict type checking enabled (default), mypy provides:

1. **Resolved generic types**: `list[int]` element type, `dict[str, int]` key/value types
2. **Inferred local variable types**: Even without annotations
3. **Expression types**: Type of every subexpression in the AST

**Current usage**: Parameter/return C types, `len()`/`sum()` optimizations for typed lists.

**Opportunity**: Much richer optimization potential remains untapped.

### 7.1 Native Integer Arithmetic ❌ TODO

**Problem**: Integer operations sometimes use `mp_binary_op()` even when both operands are known `int`.

**Current code** (suboptimal case):
```c
mp_obj_t result = mp_binary_op(MP_BINARY_OP_ADD, a_obj, b_obj);
```

**Optimized code** (when both are `int`):
```c
mp_int_t result = a + b;
```

| Pattern | Current | Optimized | Est. Speedup |
|---------|---------|-----------|--------------|
| `a + b` | Sometimes `mp_binary_op` | Native `a + b` | 3-5x |
| `a * b` | Sometimes `mp_binary_op` | Native `a * b` | 3-5x |
| `a < b` | Sometimes `mp_binary_op` | Native `a < b` | 2-3x |

**Implementation**:
- [ ] Track expression types through IR using mypy info
- [ ] Propagate `IRType.INT` for arithmetic on two `int` operands
- [ ] Emit native C operators when both sides are unboxed

### 7.2 Typed Local Variable Tracking ❌ TODO

**Problem**: Local variables inferred by mypy are stored as `mp_obj_t` even when type is known.

```python
def process(items: list[int]) -> int:
    total = 0          # mypy knows: int, but we use mp_obj_t
    for x in items:    # mypy knows: x is int
        total += x
    return total
```

**Current**:
```c
mp_obj_t total = mp_obj_new_int(0);
// ... box/unbox on every operation
```

**Optimized**:
```c
mp_int_t total = 0;
// ... native operations throughout
```

**Implementation**:
- [ ] Pass mypy's `module_types` to IRBuilder
- [ ] Track local variable types from mypy inference
- [ ] Use `mp_int_t` for variables mypy identifies as `int`
- [ ] Box only when passing to MicroPython APIs

### 7.3 Typed List Element Access ❌ TODO

**Problem**: `list[int]` element access boxes/unboxes on every operation.

```python
def sum_list(items: list[int]) -> int:
    total = 0
    for i in range(len(items)):
        total += items[i]  # Two calls: subscr + unbox
    return total
```

**Current**:
```c
mp_obj_t elem = mp_obj_subscr(items, mp_obj_new_int(i), MP_OBJ_SENTINEL);
total += mp_obj_get_int(elem);
```

**Optimized** (when type is `list[int]`):
```c
mp_obj_list_t *lst = MP_OBJ_TO_PTR(items);
total += mp_obj_get_int(lst->items[i]);  // Direct array access
```

**Implementation**:
- [ ] Extract element type from mypy's `list[int]` resolution
- [ ] Generate direct `items[]` access for known list types
- [ ] Combine with native arithmetic for maximum benefit

### 7.4 Typed Iterator Unboxing ❌ TODO

**Problem**: `for x in list[int]` boxes/unboxes on every iteration.

**Current**:
```c
mp_obj_t iter = mp_getiter(items);
mp_obj_t x_obj;
while ((x_obj = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
    mp_int_t x = mp_obj_get_int(x_obj);  // Unbox per iteration
    // ...
}
```

**Optimized** (when type is `list[int]`):
```c
mp_obj_list_t *lst = MP_OBJ_TO_PTR(items);
for (size_t _i = 0; _i < lst->len; _i++) {
    mp_int_t x = mp_obj_get_int(lst->items[_i]);
    // ... native operations on x
}
```

**Implementation**:
- [ ] Detect `for x in container` where container is typed
- [ ] Generate direct struct access loop
- [ ] Inline unboxing once per element

### 7.5 Dict Value Type Optimization ❌ TODO

**Problem**: `dict[str, int]` value access doesn't use value type information.

**Current**:
```c
mp_obj_t val = mp_obj_subscr(d, key, MP_OBJ_SENTINEL);
// val is mp_obj_t, must unbox explicitly
```

**Optimized** (when value type is `int`):
```c
mp_int_t val = mp_obj_get_int(mp_obj_subscr(d, key, MP_OBJ_SENTINEL));
// Direct to native type
```

**Implementation**:
- [ ] Extract value type from mypy's `dict[K, V]` resolution
- [ ] Automatically unbox subscript results to native type
- [ ] Track result type through expressions

### Expected Impact

| Optimization | Patterns Affected | Est. Speedup |
|-------------|-------------------|--------------|
| Native int arithmetic | All int math | 3-5x |
| Typed locals | Functions with int locals | 2x |
| List element access | `list[int]` indexing | 2-3x |
| Typed iteration | `for x in list[int]` | 3-5x |
| Dict value types | `dict[str, int]` access | 2x |

**Combined effect**: 2-10x speedup for numeric code with proper type annotations.

### Prerequisites

- [x] Mypy integration (`type_check=True` default)
- [x] `MypyTypeInfo` passed to IRBuilder
- [ ] Expression-level type tracking in IR
- [ ] Type propagation through assignments

---

### 6.3 Error Messages

Tasks:
- [x] Detect nested functions and raise compile error with line number and suggestion
- [ ] Clear error messages for other unsupported features
- [ ] Suggestions for common mistakes

See [docs/ideas/nested-functions.md](ideas/nested-functions.md) for mypyc research findings on closures.

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
| Phase 7: Type Optimizations | 4-6 weeks | 22-33 weeks |

## Dependencies

```
Phase 1 (Core) ← ~90% done
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
                                    │
                                    └── Phase 7 (Type Optimizations) ─── needs stable IR + mypy integration
```

### External Dependencies

- MicroPython source (for headers and reference)
- mypy (for strict compile-time type checking, enabled by default)
- ESP-IDF (for ESP32 builds)
- Cross-compiler toolchain

## See Also

- [04-feature-scope.md](04-feature-scope.md) — Feature scope definition
- [02-mypyc-reference.md](02-mypyc-reference.md) — Implementation reference
- [01-architecture.md](01-architecture.md) — Architecture overview
- [03-micropython-c-api.md](03-micropython-c-api.md) — Full MicroPython C API reference
