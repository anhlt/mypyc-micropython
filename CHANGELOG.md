# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `print()` builtin function support with space separator and trailing newline
- `print_test.py` example demonstrating print functionality
- Fallthrough `return mp_const_none;` for void functions without explicit return

### Changed
- Move generated usermod files from `examples/` to `modules/`
- Update roadmap: mark inherited method propagation as done (Phase 3 ~95%)
- Update roadmap: mark `print()` as done in builtins table

### Fixed
- Void functions now properly return `mp_const_none` instead of falling through

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
