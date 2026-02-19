# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Class parameter attribute access**: Functions can now take user-defined class types as parameters and access their attributes (e.g., `def get_x(p: Point) -> int: return p.x`)
- `ParamAttrIR` for IR representation of class parameter attribute access
- `examples/class_param.py` - demonstrating class parameter attribute access patterns
- **`*args` support**: Functions can accept unlimited positional arguments via `*args` (e.g., `def f(*args)`)
- **`**kwargs` support**: Functions can accept keyword arguments via `**kwargs` (e.g., `def f(**kwargs)`)
- Combined `*args` and `**kwargs` support (e.g., `def f(name, *args, **kwargs)`)
- Uses `MP_DEFINE_CONST_FUN_OBJ_VAR` for `*args` only functions
- Uses `MP_DEFINE_CONST_FUN_OBJ_KW` for `**kwargs` functions
- `examples/star_args.py` - demonstrating variadic function patterns (12 functions)
- 9 unit tests for `*args`/`**kwargs` compilation
- 6 C runtime tests for variadic function behavior
- Blog posts: `08-default-arguments.md` and `09-variadic-functions.md`
- **Default argument support**: Functions can now have default parameter values (e.g., `def f(a: int, b: int = 10)`)
- Support for `int`, `float`, `bool`, `str`, and `None` default values
- Support for empty container defaults: `[]`, `{}`, `()`
- Negative numeric defaults (e.g., `offset: int = -5`)
- Functions with all parameters having defaults (e.g., `def f(a: int = 1, b: int = 2)`)
- `examples/default_args.py` - demonstrating default argument functionality (10 functions)
- 12 unit tests for default argument compilation
- 6 C runtime tests verifying default argument behavior
- 17 device tests for default_args module
- `bool()` builtin function for truthiness checks via `mp_obj_is_true()`
- `min()` builtin function with 2+ arguments (e.g., `min(a, b)`, `min(a, b, c)`)
- `max()` builtin function with 2+ arguments (e.g., `max(a, b)`, `max(a, b, c)`)
- `sum()` builtin function for iterables with optional start value (e.g., `sum(lst)`, `sum(lst, 10)`)
- **Optimized `sum()` for typed lists**: `sum(lst)` where `lst: list[int]` or `lst: list[float]` generates inline C loop instead of runtime call
- List element type tracking in IR builder for optimization decisions
- `mp_list_sum_int()` and `mp_list_sum_float()` inline helper functions
- `examples/builtins_demo.py` - demonstrating bool, min, max, sum builtins
- C runtime tests for new builtins (11 tests including typed list sum)
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
- **Type coercion in assignments**: Reassigning `mp_obj_t` values to typed variables (e.g., `result: int = 0; result = n` where `n` is a loop variable) now correctly preserves the declared type and inserts `mp_obj_get_int()`/`mp_obj_get_float()` conversion
- Blog post: `10-type-coercion-fix.md` documenting the assignment type coercion bug and fix

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
