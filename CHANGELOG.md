# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- LVGL MVU (Retained Mode UI) example with memory soak test
  - Demonstrates `lv_label_set_text_static()` with string lifetime management
  - Adds default partitions CSV for ESP32 LVGL firmware
- Cross-module external C library call support (`CLibCallIR`, `CLibEnumIR`)

- Makefile LVGL partition-table restore reliability: avoid `git checkout` and prevent `.index.lock` conflicts

- C emitter pointer wrapping: replaced `MP_OBJ_FROM_PTR` with `mp_c_ptr_t` struct wrapper
- C emitter GC safety: module-prefixed callback registry with `MP_REGISTER_ROOT_POINTER`
- C emitter callback trampolines: generic user_data extraction instead of hardcoded LVGL
- C emitter callback dispatch: match by callback name, not just first callback
- C emitter argument conversion: unified `CType.to_c_decl()`/`to_mp_unbox()` path

- Serial port contention in `run_device_tests.py`: added `_wait_for_port()` with retry and backoff
- Serial port contention in `run_benchmarks.py`: same retry logic
- Fixed pre-existing corruption (duplicated entries) in `run_benchmarks.py`

- `BinOpIR` with `mp_obj_t` operands now correctly uses `mp_binary_op()` instead of native C operators
- `CompareIR` with `mp_obj_t` operands now correctly uses `mp_binary_op()` + `mp_obj_is_true()` for proper comparison
- Void functions now properly return `mp_const_none` instead of falling through
- Tuple unpacking with typed variables now correctly unboxes values (e.g., `a: int; b: int; a, b = t`)
- `set.add()` and other void-returning methods no longer generate invalid C code
- **Type coercion in assignments**: Reassigning `mp_obj_t` values to typed variables (e.g., `result: int = 0; result = n` where `n` is a loop variable) now correctly preserves the declared type and inserts `mp_obj_get_int()`/`mp_obj_get_float()` conversion
- Blog post: `10-type-coercion-fix.md` documenting the assignment type coercion bug and fix
- **List augmented assignment**: `+=` and `*=` on `list` (and other `mp_obj_t`) types now correctly use `mp_binary_op(MP_BINARY_OP_INPLACE_ADD, ...)` instead of native C operations

## [0.1.0] - 2024-02-07

