# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]


### Added
- `.pyi` stub-based C bindings system (`src/mypyc_micropython/c_bindings/`)
  - `StubParser`: parses `.pyi` files into `CLibraryDef` IR
  - `CEmitter`: generates MicroPython C wrapper code with proper `mp_c_ptr_t` pointer wrapping
  - `CMakeEmitter`: generates `micropython.cmake` build files
  - `CBindingCompiler`: top-level orchestration
  - `mpy-compile-c` CLI entry point
- LVGL v9.6 integration for ESP32-C6 with Waveshare ESP32-C6-LCD-1.47 display
  - 55+ wrapped LVGL functions (label, button, slider, switch, checkbox, bar, arc)
  - ST7789 display driver with SPI/DMA double-buffered rendering
  - `lv_conf.h` configuration (48KB RAM, RGB565, 7 widgets)
  - Custom partition table (2.56MB app) for LVGL firmware
- Automated LVGL build pipeline (`make deploy-lvgl`)
  - `compile-lvgl`: generates C from `.pyi` stub, copies driver, patches `lvgl.c`
  - `build-lvgl`: compiles all modules + LVGL with custom partition table
  - `flash-lvgl`: flashes firmware with LVGL partition table
  - `deploy-lvgl`: one-command compile + build + flash
  - `test-lvgl`: quick smoke test on device
- `scripts/patch_lvgl_c.py` for auto-patching generated C with driver entries
- `docs/lvgl-build-guide.md` with complete build workflow documentation
- `docs/ideas/pyi/05-roadmap.md` for C bindings roadmap
- Blog posts: 21 (pyi stub system), 22 (display driver), 23 (emitter rewrite)

### Fixed
- C emitter pointer wrapping: replaced `MP_OBJ_FROM_PTR` with `mp_c_ptr_t` struct wrapper
- C emitter GC safety: module-prefixed callback registry with `MP_REGISTER_ROOT_POINTER`
- C emitter callback trampolines: generic user_data extraction instead of hardcoded LVGL
- C emitter callback dispatch: match by callback name, not just first callback
- C emitter argument conversion: unified `CType.to_c_decl()`/`to_mp_unbox()` path

### Added
 **Exception handling support**: `try`/`except`/`else`/`finally`/`raise` statements
  - `try`/`except ExceptionType:` - catch specific exception types
  - `try`/`except ExceptionType as e:` - catch with variable binding
  - `try`/`except:` - bare except (catch-all)
  - Multiple `except` handlers in order
  - `try`/`finally` - cleanup pattern (always runs)
  - `try`/`except`/`finally` - combined handlers
  - `try`/`except`/`else` - else block runs when no exception
  - `raise ExceptionType` - raise exception without message
  - `raise ExceptionType("message")` - raise with message
  - Nested `try` blocks
  - Uses MicroPython's `nlr_push`/`nlr_pop` for exception handling
  - Supports: `ZeroDivisionError`, `ValueError`, `TypeError`, `RuntimeError`, `KeyError`, `IndexError`, `AttributeError`, `OverflowError`, `MemoryError`, `OSError`, `NotImplementedError`, `AssertionError`
 New IR nodes: `TryIR`, `RaiseIR`, `ExceptHandlerIR`
 IR visualizer support for `TryIR` and `RaiseIR` nodes
 `examples/exception_handling.py` - demonstrating exception handling patterns (10 functions)
 `mp_int_floor_divide_checked()` helper for proper `ZeroDivisionError` in native division
 `mp_int_modulo_checked()` helper for proper `ZeroDivisionError` in native modulo
 11 unit tests for exception handling compilation
 4 C runtime tests for exception handling behavior
 18 device tests for exception_handling module
 Mock runtime support for `nlr_push`/`nlr_pop` and exception types
 Blog post: `16-exception-handling.md` documenting the implementation
 **List comprehensions**: `[expr for x in iterable]` and `[expr for x in iterable if cond]` syntax support
  - Range-based: `[x * x for x in range(n)]`, `[x for x in range(n) if x % 2 == 0]`
  - Iterator-based: `[x * 2 for x in items]`, `[x for x in items if x > 0]`
  - `ListCompIR` node for IR representation
  - Inline C code generation with proper temp variable allocation
 `examples/list_comprehension.py` - demonstrating list comprehension patterns (6 functions)
 6 unit tests for list comprehension compilation
 3 C runtime tests for list comprehension behavior
 6 device tests for list_comprehension module
- **`enumerate()` builtin**: Iterate with index over sequences (e.g., `for i, val in enumerate(lst)`)
  - `enumerate(iterable)` - start from 0
  - `enumerate(iterable, start)` - start from custom index
  - Uses `mp_type_enumerate` via `mp_call_function_1/2`
- **`zip()` builtin**: Iterate over multiple sequences in parallel (e.g., `for x, y in zip(a, b)`)
  - `zip(a)` - single iterable
  - `zip(a, b)` - two iterables
  - `zip(a, b, c, ...)` - multiple iterables via `mp_call_function_n_kw`
  - Uses `mp_type_zip`
- **`sorted()` builtin**: Return new sorted list from iterable
  - `sorted(iterable)` - returns sorted list
  - Uses `mp_builtin_sorted_obj` via `mp_call_function_1`
- `examples/itertools_builtins.py` - demonstrating enumerate/zip/sorted patterns
- 7 unit tests for enumerate/zip/sorted compilation
- 6 C runtime tests for builtin behavior
- 8 device tests for itertools_builtins module
- Mock runtime support for enumerate/zip/sorted in test framework
- **List methods**: `extend()`, `insert()`, `reverse()`, `sort()` via dynamic method dispatch
- `list(iterable)` constructor for creating lists from iterables
- **Mypy local type inference**: Use mypy's inferred types for local variables instead of expression-based inference
  - Correctly types `a and b` as `bool` (was incorrectly typed before)
  - Correctly types `a & b` as `bool` for bool operands
  - Correctly types `a + b` as `int` for bool operands (Python promotes bool+bool to int)
  - Extracts local variable types from mypy's semantic analysis via `FunctionTypeInfo.local_types`
- **Comprehensive string operations support**: 25+ string methods via dynamic method dispatch
  - Case methods: `upper()`, `lower()`, `capitalize()`, `title()`, `swapcase()`
  - Search methods: `find()`, `rfind()`, `index()`, `rindex()`, `count()`
  - Check methods: `startswith()`, `endswith()`, `isdigit()`, `isalpha()`, `isspace()`, `isupper()`, `islower()`
  - Modify methods: `replace()`, `strip()`, `lstrip()`, `rstrip()`
  - Split/Join methods: `split()`, `rsplit()`, `join()`, `partition()`, `rpartition()`
  - Padding methods: `center()`, `ljust()`, `rjust()`, `zfill()`
  - Other: `encode()`
  - Operators: `+` (concat), `*` (repeat), `in` (contains), `[]` (indexing/slicing), `len()`
- `examples/string_operations.py` - demonstrating all string operation patterns (26 functions)
- 35 unit tests for string operations compilation
- 40 device tests for string_operations module
- 8 string operation benchmarks (upper, replace, find, split, join, strip, concat, normalize)
- Blog post: `13-string-operations.md` documenting the method dispatch implementation
- Updated roadmap: String Operations section (1.7) added to Phase 1
- **Chained class attribute access**: Access attributes through multiple levels of class composition (e.g., `rect.bottom_right.x`, `dept.manager.department.name`)
- `AttrAccessIR` instruction for IR representation of chained attribute access
- `_get_class_type_of_attr()` helper for recursive type tracking through attribute chains
- `examples/chained_attr.py` - demonstrating nested class attribute access patterns
- 4 unit tests for chained attribute access compilation
- 8 device tests for chained_attr module
- Blog post: `12-chained-attribute-access.md` documenting the recursive solution
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
- `super()` call support in child class methods (`super().__init__()`, `super().method()`)

### Changed
- `make compile-all` now cleans old usermod directories and deps/ build folder before compiling
- Move generated usermod files from `examples/` to `modules/`
- Update roadmap: mark inherited method propagation as done (Phase 3 ~95%)
- Update roadmap: mark `print()` as done in builtins table

### Fixed
- `BinOpIR` with `mp_obj_t` operands now correctly uses `mp_binary_op()` instead of native C operators
- `CompareIR` with `mp_obj_t` operands now correctly uses `mp_binary_op()` + `mp_obj_is_true()` for proper comparison
- Void functions now properly return `mp_const_none` instead of falling through
- Tuple unpacking with typed variables now correctly unboxes values (e.g., `a: int; b: int; a, b = t`)
- `set.add()` and other void-returning methods no longer generate invalid C code
- **Type coercion in assignments**: Reassigning `mp_obj_t` values to typed variables (e.g., `result: int = 0; result = n` where `n` is a loop variable) now correctly preserves the declared type and inserts `mp_obj_get_int()`/`mp_obj_get_float()` conversion
- Blog post: `10-type-coercion-fix.md` documenting the assignment type coercion bug and fix
- **List augmented assignment**: `+=` and `*=` on `list` (and other `mp_obj_t`) types now correctly use `mp_binary_op(MP_BINARY_OP_INPLACE_ADD, ...)` instead of native C operations

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
