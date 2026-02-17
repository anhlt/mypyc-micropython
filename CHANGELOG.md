# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `print()` builtin function support with space separator and trailing newline
- `print_test.py` example demonstrating print functionality
- Fallthrough `return mp_const_none;` for void functions without explicit return
- **Tuple support**: literals `(1, 2, 3)`, indexing `t[n]`, slicing `t[n:m]`, `len(t)`, iteration
- **Tuple operations**: concatenation `t1 + t2`, repetition `t * n`, unpacking `a, b, c = t`
- **Tuple constructors**: `tuple()`, `tuple(iterable)`
- **Set support**: literals `{1, 2, 3}`, `len(s)`, `in` operator, iteration
- **Set methods**: `add()`, `remove()`, `discard()`, `update()`, `clear()`, `copy()`, `pop()`
- **Set constructors**: `set()`, `set(iterable)`
- **Slicing support**: `lst[n:m]`, `lst[n:]`, `lst[:m]`, `lst[:]`, `lst[::step]` for lists and tuples
- **Container operations**: concatenation `+` and repetition `*` for lists and tuples
- `examples/tuple_operations.py` - comprehensive tuple examples (20 functions)
- `examples/set_operations.py` - comprehensive set examples (17 functions)
- C runtime tests for tuple operations (7 tests)
- C runtime tests for set operations (5 tests)

### Changed
- Move generated usermod files from `examples/` to `modules/`
- Update roadmap: mark inherited method propagation as done (Phase 3 ~95%)
- Update roadmap: mark `print()` as done in builtins table

### Fixed
- Void functions now properly return `mp_const_none` instead of falling through
- Tuple unpacking with typed variables now correctly unboxes values (e.g., `a: int; b: int; a, b = t`)
- `set.add()` and other void-returning methods no longer generate invalid C code

## [0.1.0] - 2024-02-07

### Added
- Initial release with typed Python to MicroPython C module compilation
- Support for basic types: `int`, `float`, `bool`, `str`
- Arithmetic, comparison, bitwise, and logical operators
- Control flow: `if`/`elif`/`else`, `while` loops, `for` loops
- List operations: literals, indexing, `append()`, `pop()`, `len()`
- Dict operations: literals, indexing, `get()`, `keys()`, `values()`, `items()`, etc.
- Class support with `__init__`, instance methods, `@dataclass`
- Single inheritance with vtable-based virtual dispatch
- Special methods: `__eq__`, `__len__`, `__getitem__`, `__setitem__`
- Built-ins: `abs()`, `int()`, `float()`, `len()`, `range()`, `list()`, `dict()`
- ESP32 firmware build support via Makefile
- Comprehensive test suite (180+ unit tests, 64 device tests)
