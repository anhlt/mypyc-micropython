# Dict Operations Implementation Plan

This document maps mypyc's native dict operations to mypyc-micropython support status and implementation priorities.

**Reference:** [mypyc Native dict operations](https://mypyc.readthedocs.io/en/latest/dict_operations.html)

## Overview

mypyc provides optimized native implementations for common dict operations. This document tracks which operations mypyc-micropython supports, plans to support, or will not support.

## Operation Status Matrix

### Construction

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `{key: value, ...}` | ✅ | ✅ Implemented | Dict literals via `mp_obj_new_dict()` + `mp_obj_dict_store()` |
| `{}` | ✅ | ✅ Implemented | Empty dict via `mp_obj_new_dict(0)` |
| `dict()` | ✅ | ✅ Implemented | Empty dict constructor |
| `dict(d: dict)` | ✅ | 📋 TODO | Copy from existing dict |
| `dict(x: Iterable)` | ✅ | 📋 TODO | Construct from iterable of pairs |
| `{...: ... for ... in ...}` | ✅ | 📋 TODO | Dict comprehension |
| `{...: ... for ... in ... if ...}` | ✅ | 📋 TODO | Dict comprehension with filter |

### Operators

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `d[key]` | ✅ | ✅ Implemented | Via `mp_obj_subscr()` |
| `key in d` | ✅ | ✅ Implemented | Membership test via `mp_binary_op(MP_BINARY_OP_IN, ...)` |

### Statements

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `d[key] = value` | ✅ | ✅ Implemented | Via `mp_obj_subscr()` |
| `for key in d:` | ✅ | ✅ Implemented | Via `mp_getiter()`/`mp_iternext()` |

### Methods

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `d.get(key)` | ✅ | ✅ Implemented | Via `mp_obj_dict_get()` |
| `d.get(key, default)` | ✅ | ✅ Implemented | Via method call with 2 args |
| `d.keys()` | ✅ | ✅ Implemented | Via `mp_load_attr()` + call |
| `d.values()` | ✅ | ✅ Implemented | Via `mp_load_attr()` + call |
| `d.items()` | ✅ | ✅ Implemented | Via `mp_load_attr()` + call |
| `d.copy()` | ✅ | ✅ Implemented | Via `mp_load_attr()` + `mp_call_function_0()` |
| `d.clear()` | ✅ | ✅ Implemented | Via `mp_load_attr()` + `mp_call_function_0()` |
| `d.setdefault(key)` | ✅ | ✅ Implemented | Via `mp_call_function_1()` |
| `d.setdefault(key, value)` | ✅ | ✅ Implemented | Via `mp_call_function_n_kw()` |
| `d1.update(d2: dict)` | ✅ | ✅ Implemented | Via `mp_call_function_1()` |
| `d.update(x: Iterable)` | ✅ | ✅ Implemented | Same impl, works for any iterable |
| `d.pop(key)` | ✅ | ✅ Implemented | Via `mp_load_method()` + `mp_call_method_n_kw()` |
| `d.pop(key, default)` | ✅ | ✅ Implemented | Via `mp_load_method()` + `mp_call_method_n_kw()` |
| `d.popitem()` | ✅ | ✅ Implemented | Via `mp_load_attr()` + `mp_call_function_0()` |

### Functions

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `len(d: dict)` | ✅ | ✅ Implemented | Via `mp_obj_len()` |

## Implementation Summary

**Implemented: 18/21 operations (86%)**

| Category | Implemented | TODO |
|----------|-------------|------|
| Construction | 3 | 4 |
| Operators | 2 | 0 |
| Statements | 2 | 0 |
| Methods | 12 | 0 |
| Functions | 1 | 0 |

## Implementation Tasks

### Phase 1 - Core (Current - DONE)

Already implemented in `compiler.py`:
- ✅ Dict literals: `_translate_dict()` → `mp_obj_new_dict()` + `mp_obj_dict_store()`
- ✅ Empty dict: `{}`, `dict()` → `mp_obj_new_dict(0)`
- ✅ Subscript get: `_translate_subscript()` → `mp_obj_subscr()`
- ✅ Subscript set: `_translate_subscript_assign()` → `mp_obj_subscr()`
- ✅ `get()`: `_translate_method_call()` → `mp_obj_dict_get()` or method call
- ✅ `keys()`: `_translate_method_call()` → `mp_load_attr()` + `mp_call_function_0()`
- ✅ `values()`: `_translate_method_call()` → `mp_load_attr()` + `mp_call_function_0()`
- ✅ `items()`: `_translate_method_call()` → `mp_load_attr()` + `mp_call_function_0()`
- ✅ Iteration: `_translate_for_iterable()` → `mp_getiter()`/`mp_iternext()`
- ✅ `len()`: `_translate_call()` → `mp_obj_len()`

### Phase 2 - Essential Methods (DONE)

**Task 2.1: Add `key in d` membership test** ✅
- Location: `_translate_compare()` in `compiler.py`
- Handle `ast.In` and `ast.NotIn` operators
- C API: `mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, key, d))`

**Task 2.2: Add `d.copy()`** ✅
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_0(mp_load_attr(d, MP_QSTR_copy))`

**Task 2.3: Add `d.clear()`** ✅
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_0(mp_load_attr(d, MP_QSTR_clear))`

**Task 2.4: Add `d.setdefault(key)` and `d.setdefault(key, value)`** ✅
- Location: `_translate_method_call()` in `compiler.py`
- C API: 1-arg uses `mp_call_function_1()`, 2-arg uses `mp_call_function_n_kw()`

**Task 2.5: Add `d.pop(key)` and `d.pop(key, default)`** ✅
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_load_method()` + `mp_call_method_n_kw()` with generic boxing

**Task 2.6: Add `d.popitem()`** ✅
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_0(mp_load_attr(d, MP_QSTR_popitem))`

### Phase 3 - Update Operations (DONE)

**Task 3.1: Add `d1.update(d2)`** ✅
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_1(mp_load_attr(d1, MP_QSTR_update), d2)`

**Task 3.2: Add `d.update(iterable)`** ✅
- Same implementation as Task 3.1, works for any iterable of pairs

**Task 3.3: Add `dict(d)` copy constructor**
- Location: `_translate_call()` in `compiler.py`
- Handle `dict()` with one dict argument
- C API: `mp_obj_dict_copy(d)` or iterate and copy
- Example: `new_dict = dict(old_dict)`

### Phase 4 - Comprehensions (MEDIUM PRIORITY)

**Task 4.1: Add dict comprehension `{k: v for x in iter}`**
- Location: New `_translate_dictcomp()` in `compiler.py`
- Handle `ast.DictComp` in `_translate_expr()`
- Generate: create dict → for loop → store key/value
- Example: `{x: x*2 for x in range(10)}`

**Task 4.2: Add filtered comprehension `{k: v for x in iter if cond}`**
- Extension of Task 4.1
- Add conditional before store
- Example: `{x: x*2 for x in range(10) if x % 2 == 0}`

### Phase 5 - Advanced (LOW PRIORITY)

**Task 5.1: Add `dict(iterable)` constructor**
- Location: `_translate_call()` in `compiler.py`
- Handle `dict()` with iterable of (key, value) pairs
- Example: `dict([("a", 1), ("b", 2)])`

## MicroPython C API Reference

| Python Operation | MicroPython C API | Notes |
|------------------|-------------------|-------|
| `d[key]` | `mp_obj_subscr(d, key, MP_OBJ_SENTINEL)` | Get item |
| `d[key] = value` | `mp_obj_subscr(d, key, value)` | Set item |
| `key in d` | `mp_call_function_2(mp_load_attr(d, MP_QSTR___contains__), key)` | Membership |
| `d.get(key)` | `mp_obj_dict_get(d, key)` | Direct API |
| `d.get(key, default)` | `mp_call_function_n_kw(...)` with 2 args | Method call |
| `d.keys()` | `mp_call_function_0(mp_load_attr(d, MP_QSTR_keys))` | Returns view |
| `d.values()` | `mp_call_function_0(mp_load_attr(d, MP_QSTR_values))` | Returns view |
| `d.items()` | `mp_call_function_0(mp_load_attr(d, MP_QSTR_items))` | Returns view |
| `d.copy()` | `mp_call_function_0(mp_load_attr(d, MP_QSTR_copy))` | Returns new dict |
| `d.clear()` | `mp_call_function_0(mp_load_attr(d, MP_QSTR_clear))` | Returns None |
| `d.setdefault(k, v)` | `mp_call_function_n_kw(...)` | Method call |
| `d.update(d2)` | `mp_call_function_1(mp_load_attr(d, MP_QSTR_update), d2)` | Method call |
| `d.pop(key)` | `mp_call_function_1(mp_load_attr(d, MP_QSTR_pop), key)` | Method call |
| `d.popitem()` | `mp_call_function_0(mp_load_attr(d, MP_QSTR_popitem))` | Returns tuple |
| `len(d)` | `mp_obj_len(d)` | Returns mp_obj_t |

## Test Cases to Add

For each new operation, add tests to `tests/test_compiler.py`:

```python
# Phase 2 tests
def test_dict_membership():
    """Test 'in' operator for dicts"""
    
def test_dict_copy():
    """Test d.copy()"""
    
def test_dict_clear():
    """Test d.clear()"""
    
def test_dict_setdefault():
    """Test d.setdefault(key) and d.setdefault(key, value)"""
    
def test_dict_pop():
    """Test d.pop(key) and d.pop(key, default)"""
    
def test_dict_popitem():
    """Test d.popitem()"""

# Phase 3 tests
def test_dict_update():
    """Test d.update(d2)"""
    
def test_dict_copy_constructor():
    """Test dict(d)"""

# Phase 4 tests
def test_dict_comprehension():
    """Test {k: v for x in iter}"""
    
def test_dict_comprehension_filtered():
    """Test {k: v for x in iter if cond}"""
```

## See Also

- [09-list-operations-plan.md](09-list-operations-plan.md) - List operations plan
- [04-feature-scope.md](04-feature-scope.md) - Overall feature scope
- [05-roadmap.md](05-roadmap.md) - Implementation roadmap
- [03-micropython-c-api.md](03-micropython-c-api.md) - MicroPython C API reference
