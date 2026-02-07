# List Operations Implementation Plan

This document maps mypyc's native list operations to mypyc-micropython support status and implementation priorities.

**Reference:** [mypyc Native list operations](https://mypyc.readthedocs.io/en/latest/list_operations.html)

## Overview

mypyc provides optimized native implementations for common list operations. This document tracks which operations mypyc-micropython supports, plans to support, or will not support.

## Operation Status Matrix

### Construction

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `[item0, ..., itemN]` | ✅ | ✅ Implemented | List literals via `mp_obj_new_list()` |
| `[]` | ✅ | ✅ Implemented | Empty list via `mp_obj_new_list(0, NULL)` |
| `list()` | ✅ | ✅ Implemented | Empty list constructor |
| `list(x: Iterable)` | ✅ | 📋 TODO | Construct from iterable |
| `[... for ... in ...]` | ✅ | 📋 TODO | List comprehension |
| `[... for ... in ... if ...]` | ✅ | 📋 TODO | List comprehension with filter |

### Operators

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `lst[n]` | ✅ | ✅ Implemented | Via `mp_obj_subscr()` |
| `lst[n:m]` | ✅ | 📋 TODO | Slicing with start and end |
| `lst[n:]` | ✅ | 📋 TODO | Slicing from start |
| `lst[:m]` | ✅ | 📋 TODO | Slicing to end |
| `lst[:]` | ✅ | 📋 TODO | Full slice (copy) |
| `lst1 + lst2` | ✅ | 📋 TODO | List concatenation |
| `lst += iter` | ✅ | 📋 TODO | In-place extend |
| `lst * n` | ✅ | 📋 TODO | List repetition |
| `n * lst` | ✅ | 📋 TODO | List repetition (reverse) |
| `lst *= n` | ✅ | 📋 TODO | In-place repetition |
| `obj in lst` | ✅ | 📋 TODO | Membership test |

### Statements

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `lst[n] = x` | ✅ | ✅ Implemented | Via `mp_obj_subscr()` |
| `for item in lst:` | ✅ | ✅ Implemented | Via `mp_getiter()`/`mp_iternext()` |

### Methods

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `lst.append(obj)` | ✅ | ✅ Implemented | Via `mp_obj_list_append()` |
| `lst.extend(x: Iterable)` | ✅ | 📋 TODO | Extend from iterable |
| `lst.insert(index, obj)` | ✅ | 📋 TODO | Insert at position |
| `lst.pop(index=-1)` | ✅ | ✅ Implemented | Via `mp_obj_list_pop()` |
| `lst.remove(obj)` | ✅ | 📋 TODO | Remove first occurrence |
| `lst.count(obj)` | ✅ | 📋 TODO | Count occurrences |
| `lst.index(obj)` | ✅ | 📋 TODO | Find index of item |
| `lst.reverse()` | ✅ | 📋 TODO | Reverse in place |
| `lst.sort()` | ✅ | 📋 TODO | Sort in place |

### Functions

| Operation | mypyc Native | mypyc-micropython | Notes |
|-----------|--------------|-------------------|-------|
| `len(lst: list)` | ✅ | ✅ Implemented | Via `mp_obj_len()` |

## Implementation Summary

**Implemented: 8/23 operations (35%)**

| Category | Implemented | TODO |
|----------|-------------|------|
| Construction | 3 | 3 |
| Operators | 2 | 9 |
| Statements | 2 | 0 |
| Methods | 3 | 6 |
| Functions | 1 | 0 |

## Implementation Tasks

### Phase 1 - Core (Current - DONE)

Already implemented in `compiler.py`:
- ✅ List literals: `_translate_list()` → `mp_obj_new_list()`
- ✅ Empty list: `[]`, `list()` 
- ✅ Indexing: `_translate_subscript()` → `mp_obj_subscr()`
- ✅ Index assignment: `_translate_subscript_assign()` → `mp_obj_subscr()`
- ✅ `append()`: `_translate_method_call()` → `mp_obj_list_append()`
- ✅ `pop()`: `_translate_method_call()` → `mp_obj_list_pop()`
- ✅ Iteration: `_translate_for_iterable()` → `mp_getiter()`/`mp_iternext()`
- ✅ `len()`: `_translate_call()` → `mp_obj_len()`

### Phase 2 - Essential Methods (HIGH PRIORITY)

**Task 2.1: Add `obj in lst` membership test**
- Location: `_translate_compare()` in `compiler.py`
- Handle `ast.In` and `ast.NotIn` operators
- C API: `mp_call_function_2(mp_load_attr(lst, MP_QSTR___contains__), obj)` or direct iteration
- Example: `if x in my_list:` → membership check

**Task 2.2: Add `lst.extend(iterable)`**
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_1(mp_load_attr(lst, MP_QSTR_extend), iter)`
- Example: `my_list.extend([1, 2, 3])`

**Task 2.3: Add `lst.insert(index, obj)`**
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_2(mp_load_attr(lst, MP_QSTR_insert), idx, obj)`
- Example: `my_list.insert(0, "first")`

**Task 2.4: Add `lst.remove(obj)`**
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_1(mp_load_attr(lst, MP_QSTR_remove), obj)`
- Example: `my_list.remove(42)`

**Task 2.5: Add `lst.index(obj)`**
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_1(mp_load_attr(lst, MP_QSTR_index), obj)`
- Returns: `mp_int_t` (index position)
- Example: `idx = my_list.index(42)`

**Task 2.6: Add `lst.count(obj)`**
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_1(mp_load_attr(lst, MP_QSTR_count), obj)`
- Returns: `mp_int_t` (count)
- Example: `n = my_list.count(42)`

### Phase 3 - Slicing & Concatenation (MEDIUM PRIORITY)

**Task 3.1: Add slicing support `lst[n:m]`**
- Location: `_translate_subscript()` in `compiler.py`
- Handle `ast.Slice` in addition to simple index
- C API: `mp_obj_subscr(lst, mp_obj_new_slice(start, stop, step), MP_OBJ_SENTINEL)`
- Variants: `lst[n:]`, `lst[:m]`, `lst[:]`, `lst[::step]`

**Task 3.2: Add `lst1 + lst2` concatenation**
- Location: `_translate_binop()` in `compiler.py`
- Detect when operands are lists and `ast.Add`
- C API: `mp_binary_op(MP_BINARY_OP_ADD, lst1, lst2)`

**Task 3.3: Add `lst += iter` in-place extend**
- Location: `_translate_aug_assign()` in `compiler.py`
- Special case for list with `ast.Add`
- C API: `mp_binary_op(MP_BINARY_OP_INPLACE_ADD, lst, iter)`

**Task 3.4: Add `lst.reverse()`**
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_0(mp_load_attr(lst, MP_QSTR_reverse))`

**Task 3.5: Add `lst.sort()`**
- Location: `_translate_method_call()` in `compiler.py`
- C API: `mp_call_function_0(mp_load_attr(lst, MP_QSTR_sort))`
- Note: Initially without `key` or `reverse` parameters

### Phase 4 - Comprehensions (MEDIUM PRIORITY)

**Task 4.1: Add list comprehension `[expr for x in iter]`**
- Location: New `_translate_listcomp()` in `compiler.py`
- Handle `ast.ListComp` in `_translate_expr()`
- Generate: create list → for loop → append
- Example: `[x*2 for x in range(10)]`

**Task 4.2: Add filtered comprehension `[expr for x in iter if cond]`**
- Extension of Task 4.1
- Add conditional before append
- Example: `[x for x in range(10) if x % 2 == 0]`

### Phase 5 - Advanced (LOW PRIORITY)

**Task 5.1: Add `lst * n` repetition**
- Location: `_translate_binop()` in `compiler.py`
- C API: `mp_binary_op(MP_BINARY_OP_MULTIPLY, lst, n)`

**Task 5.2: Add `lst *= n` in-place repetition**
- Location: `_translate_aug_assign()` in `compiler.py`
- C API: `mp_binary_op(MP_BINARY_OP_INPLACE_MULTIPLY, lst, n)`

**Task 5.3: Add `list(iterable)` constructor**
- Location: `_translate_call()` in `compiler.py`
- C API: `mp_obj_list_make_new(&mp_type_list, 1, 0, &iter)`

## MicroPython C API Reference

| Python Operation | MicroPython C API | Notes |
|------------------|-------------------|-------|
| `lst[n]` | `mp_obj_subscr(lst, idx, MP_OBJ_SENTINEL)` | Get item |
| `lst[n] = x` | `mp_obj_subscr(lst, idx, val)` | Set item |
| `obj in lst` | `mp_call_function_2(mp_load_attr(lst, MP_QSTR___contains__), obj)` | Membership |
| `lst.append(obj)` | `mp_obj_list_append(lst, obj)` | Direct API |
| `lst.extend(iter)` | `mp_call_function_1(mp_load_attr(lst, MP_QSTR_extend), iter)` | Method call |
| `lst.insert(i, obj)` | `mp_call_function_2(mp_load_attr(lst, MP_QSTR_insert), i, obj)` | Method call |
| `lst.pop()` | `mp_obj_list_pop(lst, 1, NULL)` | Direct API |
| `lst.pop(i)` | `mp_obj_list_pop(lst, 1, args)` | With index |
| `lst.remove(obj)` | `mp_call_function_1(mp_load_attr(lst, MP_QSTR_remove), obj)` | Method call |
| `lst.count(obj)` | `mp_call_function_1(mp_load_attr(lst, MP_QSTR_count), obj)` | Method call |
| `lst.index(obj)` | `mp_call_function_1(mp_load_attr(lst, MP_QSTR_index), obj)` | Method call |
| `lst.reverse()` | `mp_call_function_0(mp_load_attr(lst, MP_QSTR_reverse))` | Method call |
| `lst.sort()` | `mp_call_function_0(mp_load_attr(lst, MP_QSTR_sort))` | Method call |
| `len(lst)` | `mp_obj_len(lst)` | Returns mp_obj_t |
| `lst[n:m]` | `mp_obj_subscr(lst, mp_obj_new_slice(...), MP_OBJ_SENTINEL)` | Slice object |
| `lst1 + lst2` | `mp_binary_op(MP_BINARY_OP_ADD, lst1, lst2)` | Binary op |

## Test Cases to Add

For each new operation, add tests to `tests/test_compiler.py`:

```python
# Phase 2 tests
def test_list_membership():
    """Test 'in' operator for lists"""
    
def test_list_extend():
    """Test lst.extend(iterable)"""
    
def test_list_insert():
    """Test lst.insert(index, obj)"""
    
def test_list_remove():
    """Test lst.remove(obj)"""
    
def test_list_index():
    """Test lst.index(obj)"""
    
def test_list_count():
    """Test lst.count(obj)"""

# Phase 3 tests
def test_list_slicing():
    """Test lst[n:m], lst[n:], lst[:m], lst[:]"""
    
def test_list_concatenation():
    """Test lst1 + lst2"""
    
def test_list_inplace_extend():
    """Test lst += iter"""
    
def test_list_reverse():
    """Test lst.reverse()"""
    
def test_list_sort():
    """Test lst.sort()"""

# Phase 4 tests
def test_list_comprehension():
    """Test [expr for x in iter]"""
    
def test_list_comprehension_filtered():
    """Test [expr for x in iter if cond]"""
```

## See Also

- [08-dict-operations-plan.md](08-dict-operations-plan.md) - Dict operations plan
- [04-feature-scope.md](04-feature-scope.md) - Overall feature scope
- [05-roadmap.md](05-roadmap.md) - Implementation roadmap
- [03-micropython-c-api.md](03-micropython-c-api.md) - MicroPython C API reference
