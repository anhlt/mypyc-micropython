# Implementation Roadmap

A 6-phase roadmap for mypyc-micropython from the current proof-of-concept to production-ready compiler.

## Table of Contents

- [Current State](#current-state)
- [Phase Overview](#phase-overview)
- [Phase 1: Core Completion](#phase-1-core-completion)
- [Phase 2: Functions & Arguments](#phase-2-functions--arguments)
- [Phase 3: Classes](#phase-3-classes)
- [Phase 4: Exception Handling](#phase-4-exception-handling)
- [Phase 5: Advanced Features](#phase-5-advanced-features)
- [Phase 6: Integration & Polish](#phase-6-integration--polish)
- [Timeline Estimates](#timeline-estimates)
- [Dependencies](#dependencies)

## Current State

### What Works Now ✅

- Basic function compilation with type annotations
- Primitive types: `int`, `float`, `bool`
- Arithmetic, comparison, bitwise, logical operators
- Control flow: `if`/`elif`/`else`, `while` loops
- Local variables (typed and inferred)
- Recursion
- Basic built-ins: `abs()`, `int()`, `float()`
- Module generation with build system integration

### What's Missing ❌

- `for` loops
- Collections (`list`, `tuple`, `dict`, `set`)
- Default arguments, `*args`, `**kwargs`
- Classes and methods
- Exception handling
- Closures and generators

## Phase Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        IMPLEMENTATION PHASES                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: Core Completion                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ for loops │ list │ tuple │ dict │ set │ range │ len │ print │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  Phase 2: Functions & Arguments                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ default args │ *args │ **kwargs │ enumerate │ zip │ sorted │    │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  Phase 3: Classes                                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ class def │ __init__ │ methods │ @property │ inheritance    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  Phase 4: Exception Handling                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ try/except │ try/finally │ raise │ custom exceptions        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  Phase 5: Advanced Features                                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ closures │ generators │ list comprehensions │ map/filter    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│  Phase 6: Integration & Polish                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ESP32 modules │ optimization │ error messages │ docs        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Phase 1: Core Completion

**Goal:** Make the compiler useful for basic data processing tasks.

### 1.1 For Loops

**Python:**
```python
def sum_list(items: list[int]) -> int:
    total = 0
    for x in items:
        total += x
    return total
```

**Generated C:**
```c
static mp_obj_t sum_list(mp_obj_t items_obj) {
    mp_int_t total = 0;
    
    mp_obj_t iter = mp_getiter(items_obj, NULL);
    mp_obj_t x_obj;
    while ((x_obj = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
        mp_int_t x = mp_obj_get_int(x_obj);
        total += x;
    }
    
    return mp_obj_new_int(total);
}
```

**Tasks:**
- [ ] Implement `for` loop AST translation
- [ ] Handle `range()` iteration (optimized path)
- [ ] Handle generic iterable iteration
- [ ] Support `break` and `continue`
- [ ] Support `else` clause on loops

### 1.2 List Support

**Tasks:**
- [ ] List creation: `[1, 2, 3]`
- [ ] List indexing: `items[0]`, `items[-1]`
- [ ] List slicing: `items[1:3]`, `items[::2]`
- [ ] List methods: `append`, `extend`, `pop`, `insert`
- [ ] List concatenation: `list1 + list2`
- [ ] List multiplication: `[0] * 10`
- [ ] `in` operator: `x in items`

### 1.3 Tuple Support

**Tasks:**
- [ ] Tuple creation: `(1, 2, 3)`
- [ ] Tuple unpacking: `a, b, c = tuple`
- [ ] Tuple indexing
- [ ] Named tuple (lower priority)

### 1.4 Dict Support

**Tasks:**
- [ ] Dict creation: `{"a": 1, "b": 2}`
- [ ] Dict access: `d["key"]`, `d.get("key", default)`
- [ ] Dict methods: `keys()`, `values()`, `items()`
- [ ] Dict iteration
- [ ] `in` operator for keys

### 1.5 Set Support

**Tasks:**
- [ ] Set creation: `{1, 2, 3}`
- [ ] Set operations: `union`, `intersection`, `difference`
- [ ] `in` operator
- [ ] Set iteration

### 1.6 Built-in Functions

**Tasks:**
- [ ] `range(start, stop, step)`
- [ ] `len(obj)`
- [ ] `print(*args)` - basic support
- [ ] `bool(obj)`
- [ ] `min(iterable)` / `max(iterable)`
- [ ] `sum(iterable)`

### 1.7 Deliverables

- [ ] All Phase 1 features pass test suite
- [ ] Example: data processing script compiles and runs
- [ ] Documentation updated

---

## Phase 2: Functions & Arguments

**Goal:** Full function signature support.

### 2.1 Default Arguments

**Python:**
```python
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"
```

**Generated C:**
```c
// Default value stored as module constant
static const mp_obj_t default_greeting = MP_ROM_QSTR(MP_QSTR_Hello);

static mp_obj_t greet(size_t n_args, const mp_obj_t *args) {
    const char *name = mp_obj_str_get_str(args[0]);
    const char *greeting;
    
    if (n_args >= 2) {
        greeting = mp_obj_str_get_str(args[1]);
    } else {
        greeting = mp_obj_str_get_str(default_greeting);
    }
    
    // Format string...
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(greet_obj, 1, 2, greet);
```

**Tasks:**
- [ ] Parse default argument values in function signatures
- [ ] Generate wrapper with argument count checking
- [ ] Store defaults as module constants
- [ ] Handle mutable defaults correctly (warn or error)

### 2.2 *args Support

**Python:**
```python
def sum_all(*args: int) -> int:
    return sum(args)
```

**Generated C:**
```c
static mp_obj_t sum_all(size_t n_args, const mp_obj_t *args) {
    mp_int_t total = 0;
    for (size_t i = 0; i < n_args; i++) {
        total += mp_obj_get_int(args[i]);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(sum_all_obj, 0, sum_all);
```

**Tasks:**
- [ ] Detect `*args` in function signature
- [ ] Generate variadic function wrapper
- [ ] Handle mixed positional + `*args`

### 2.3 **kwargs Support

**Python:**
```python
def configure(**kwargs: str) -> dict:
    return kwargs
```

**Generated C:**
```c
static mp_obj_t configure(size_t n_args, const mp_obj_t *args, mp_map_t *kw_args) {
    // Build dict from kw_args
    mp_obj_t result = mp_obj_new_dict(kw_args->used);
    for (size_t i = 0; i < kw_args->alloc; i++) {
        if (mp_map_slot_is_filled(kw_args, i)) {
            mp_obj_dict_store(result, 
                              kw_args->table[i].key, 
                              kw_args->table[i].value);
        }
    }
    return result;
}
MP_DEFINE_CONST_FUN_OBJ_KW(configure_obj, 0, configure);
```

**Tasks:**
- [ ] Detect `**kwargs` in function signature
- [ ] Generate KW function wrapper using `mp_arg_parse_all`
- [ ] Handle mixed positional + `*args` + `**kwargs`

### 2.4 Keyword-Only Arguments

**Python:**
```python
def process(data: list, *, validate: bool = True) -> list:
    ...
```

**Tasks:**
- [ ] Parse keyword-only arguments (after `*`)
- [ ] Generate appropriate argument parsing

### 2.5 Additional Built-ins

**Tasks:**
- [ ] `enumerate(iterable, start=0)`
- [ ] `zip(*iterables)`
- [ ] `sorted(iterable, key=None, reverse=False)`
- [ ] `reversed(sequence)`

### 2.6 Deliverables

- [ ] Full function signature support
- [ ] Example: flexible API function compiles
- [ ] Argument parsing matches Python semantics

---

## Phase 3: Classes

**Goal:** Basic OOP support.

### 3.1 Basic Class Definition

**Python:**
```python
class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
    
    def distance(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5
```

**Tasks:**
- [ ] Parse class definitions
- [ ] Generate struct for instance data
- [ ] Generate `make_new` (constructor)
- [ ] Generate type definition

### 3.2 Instance Methods

**Tasks:**
- [ ] Translate methods with `self` parameter
- [ ] Generate method binding
- [ ] Handle method calls on instances

### 3.3 Properties

**Python:**
```python
class Circle:
    def __init__(self, radius: float) -> None:
        self._radius = radius
    
    @property
    def radius(self) -> float:
        return self._radius
    
    @radius.setter
    def radius(self, value: float) -> None:
        if value < 0:
            raise ValueError("Radius cannot be negative")
        self._radius = value
```

**Tasks:**
- [ ] Detect `@property` decorator
- [ ] Generate getter/setter in attr handler
- [ ] Support read-only properties

### 3.4 Static and Class Methods

**Tasks:**
- [ ] `@staticmethod` - no self parameter
- [ ] `@classmethod` - cls parameter

### 3.5 Single Inheritance

**Python:**
```python
class Animal:
    def speak(self) -> str:
        return "..."

class Dog(Animal):
    def speak(self) -> str:
        return "Woof!"
```

**Tasks:**
- [ ] Parse inheritance
- [ ] Set parent type in type definition
- [ ] Method resolution (child overrides parent)
- [ ] Super calls: `super().__init__()`

### 3.6 Special Methods

**Tasks:**
- [ ] `__str__` / `__repr__`
- [ ] `__len__`
- [ ] `__getitem__` / `__setitem__`
- [ ] `__eq__` / `__ne__` / `__lt__` / etc.
- [ ] `__hash__`
- [ ] `__iter__` / `__next__`

### 3.7 Deliverables

- [ ] Basic classes work end-to-end
- [ ] Example: Point/Vector class compiles
- [ ] Single inheritance works

---

## Phase 4: Exception Handling

**Goal:** Robust error handling.

### 4.1 Try/Except

**Python:**
```python
def safe_divide(a: int, b: int) -> int:
    try:
        return a // b
    except ZeroDivisionError:
        return 0
```

**Generated C:**
```c
static mp_obj_t safe_divide(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        if (b == 0) {
            mp_raise_msg(&mp_type_ZeroDivisionError, NULL);
        }
        mp_obj_t result = mp_obj_new_int(a / b);
        nlr_pop();
        return result;
    } else {
        mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);
        if (mp_obj_is_subclass_fast(
                MP_OBJ_FROM_PTR(mp_obj_get_type(exc)),
                MP_OBJ_FROM_PTR(&mp_type_ZeroDivisionError))) {
            return mp_obj_new_int(0);
        }
        nlr_jump(nlr.ret_val);
    }
}
```

**Tasks:**
- [ ] Parse try/except blocks
- [ ] Generate nlr_push/nlr_pop pattern
- [ ] Exception type matching
- [ ] Multiple except clauses
- [ ] Catch-all except

### 4.2 Try/Finally

**Tasks:**
- [ ] Parse try/finally blocks
- [ ] Ensure finally runs on all paths
- [ ] Combine try/except/finally

### 4.3 Raise

**Tasks:**
- [ ] `raise ExceptionType(message)`
- [ ] `raise` (re-raise current exception)
- [ ] `raise ... from ...` (basic support)

### 4.4 Custom Exceptions

**Python:**
```python
class ValidationError(ValueError):
    pass

def validate(x: int) -> None:
    if x < 0:
        raise ValidationError("Must be non-negative")
```

**Tasks:**
- [ ] Custom exception class definition
- [ ] Inheritance from built-in exceptions

### 4.5 Deliverables

- [ ] Full try/except/finally support
- [ ] Custom exceptions work
- [ ] Example: robust API with error handling

---

## Phase 5: Advanced Features

**Goal:** Support functional programming patterns.

### 5.1 Closures (Read-Only)

**Python:**
```python
def make_multiplier(factor: int) -> Callable[[int], int]:
    def multiply(x: int) -> int:
        return x * factor  # Read-only capture
    return multiply
```

**Tasks:**
- [ ] Detect captured variables
- [ ] Generate environment struct
- [ ] Generate callable closure type
- [ ] Limit to read-only captures initially

### 5.2 Simple Generators

**Python:**
```python
def countdown(n: int) -> Generator[int, None, None]:
    while n > 0:
        yield n
        n -= 1
```

**Tasks:**
- [ ] Detect generator functions (contain yield)
- [ ] Transform to state machine
- [ ] Generate iterator type
- [ ] Handle `return` in generators

### 5.3 List Comprehensions (Simple)

**Python:**
```python
squares = [x * x for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]
```

**Tasks:**
- [ ] Parse simple list comprehensions
- [ ] Generate equivalent loop code
- [ ] Support single `if` filter

### 5.4 Additional Built-ins

**Tasks:**
- [ ] `map(func, iterable)`
- [ ] `filter(func, iterable)`
- [ ] `any(iterable)` / `all(iterable)`

### 5.5 Deliverables

- [ ] Closures work for read-only captures
- [ ] Simple generators work
- [ ] Example: lazy data processing pipeline

---

## Phase 6: Integration & Polish

**Goal:** Production-ready quality.

### 6.1 ESP32 Module Integration

**Tasks:**
- [ ] Document ESP32 module calling patterns
- [ ] Create helper macros/functions for common modules
- [ ] Example: GPIO blink using machine.Pin
- [ ] Example: WiFi connection using network.WLAN
- [ ] Test on actual ESP32 hardware

### 6.2 Optimization

**Tasks:**
- [ ] Constant folding
- [ ] Dead code elimination
- [ ] Inline small functions
- [ ] Reduce boxing/unboxing operations
- [ ] Profile and optimize hot paths

### 6.3 Error Messages

**Tasks:**
- [ ] Clear error messages for unsupported features
- [ ] Line number references in errors
- [ ] Suggestions for common mistakes
- [ ] Warnings for potential issues

### 6.4 Documentation

**Tasks:**
- [ ] Complete API reference
- [ ] Tutorial: Getting Started
- [ ] Tutorial: ESP32 Development
- [ ] Migration guide from pure Python
- [ ] Performance comparison benchmarks

### 6.5 Testing & CI

**Tasks:**
- [ ] Comprehensive test suite
- [ ] CI/CD pipeline
- [ ] Test on multiple MicroPython versions
- [ ] Test on multiple targets (Unix, ESP32, RP2040)

### 6.6 Deliverables

- [ ] Production-ready compiler
- [ ] Comprehensive documentation
- [ ] Real-world ESP32 examples working

---

## Timeline Estimates

| Phase | Estimated Duration | Cumulative |
|-------|-------------------|------------|
| Phase 1: Core | 4-6 weeks | 4-6 weeks |
| Phase 2: Functions | 2-3 weeks | 6-9 weeks |
| Phase 3: Classes | 4-6 weeks | 10-15 weeks |
| Phase 4: Exceptions | 2-3 weeks | 12-18 weeks |
| Phase 5: Advanced | 4-6 weeks | 16-24 weeks |
| Phase 6: Polish | 4-6 weeks | 20-30 weeks |

**Total: 5-8 months** for feature-complete compiler

## Dependencies

### Phase Dependencies

```
Phase 1 (Core)
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

- [04-feature-scope.md](04-feature-scope.md) - Feature scope definition
- [02-mypyc-reference.md](02-mypyc-reference.md) - Implementation reference
- [01-architecture.md](01-architecture.md) - Architecture overview
