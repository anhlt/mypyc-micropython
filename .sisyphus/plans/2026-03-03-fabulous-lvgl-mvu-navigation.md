# Fabulous-Inspired LVGL MVU + Navigation Consolidation

## TL;DR
> **Summary**: Evolve the current minimal `lvgl_mvu` retained-mode example into a Fabulous-inspired retained-component MVU architecture that also drives screen navigation, and split MVU device tests into a dedicated runner.
> **Deliverables**:
> - Consolidated navigation core used by both demos and MVU
> - MVU-driven navigation (stack push/pop/replace) + retained component render updates
> - Dedicated device runner `run_lvgl_mvu_tests.py` + `make run-lvgl-mvu-tests`
> - Device-verified memory stability for MVU + nav
> **Effort**: Large
> **Parallel**: YES - 3 waves
> **Critical Path**: Define nav+MVU contract → implement consolidated nav core → refactor MVU to use it → split device tests → device verification

## Context

### Original Request
- Separate the MVU test so it can run alone on device.
- Consolidate screen navigation code.
- Use MVU with screen navigation, not just a single label update; current implementation is too simple vs Fabulous.

### Repo Ground Truth (discovered)
- Existing device runner format: `run_lvgl_tests.py` prints `@S:<suite>` and `@D:<total>|<passed>|<failed>`.
- Existing navigation implementations:
  - `run_nav_test.py` (stack navigation + smooth animations + FPS overlay)
  - `test_screen_navigation.py` (tree navigation ScreenManager using compiled `lvgl_screens` factories)
  - `examples/lvgl/ui_screen_tree.py` + `examples/lvgl/ui_nav_core.py` (ScreenManager optionally delegating to registry)
- Existing compiled LVGL helper module: `examples/lvgl_screens.py` (screen/widget helpers + `show_screen`).
- Current MVU example: `examples/lvgl_mvu.py` uses retained LVGL objects and `lv_label_set_text_static`.

### Planning Inputs
- Constraint: avoid LVGL callbacks / event handlers for MVU (programmatic dispatch only).
- Memory constraint: `lv_label_set_text_static()` does not copy; backing strings must be pinned for label lifetime.

### Metis Review (gaps addressed)
- Explicitly lock down one navigation contract (stack-first) and screen lifecycle/deletion timing.
- Explicitly define MVU↔navigation integration ordering.
- Split MVU tests without duplicating harness formats.
- Add edge-case coverage for root pop/no-op, invalid routes, repeated transitions, re-mount after dispose.

## Work Objectives

### Core Objective
Provide a Fabulous-inspired retained-component MVU architecture that can drive LVGL screen navigation deterministically, with device-verified memory stability.

### Deliverables
- `run_lvgl_mvu_tests.py` (new) and `make run-lvgl-mvu-tests` (new target).
- Consolidated navigation runtime (compiled module) used by:
  - MVU app
  - existing navigation demos/tests (`run_nav_test.py`, `test_screen_navigation.py`, `examples/lvgl/ui_screen_tree.py`)
- MVU app upgraded from “single label update” to:
  - multiple retained widgets per screen
  - model-driven navigation stack
  - minimal per-tick allocations

### Definition of Done (agent-verifiable)
Run these commands (with real device connected):
```bash
make compile-all
make compile-lvgl
make build BOARD=ESP32_GENERIC_C6
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem101
make run-lvgl-tests PORT=/dev/cu.usbmodem101
make run-lvgl-mvu-tests PORT=/dev/cu.usbmodem101
mpremote connect /dev/cu.usbmodem101 run test_screen_navigation.py
mpremote connect /dev/cu.usbmodem101 run run_nav_test.py
```
Pass conditions:
- `make run-lvgl-tests` prints `ALL ... TESTS PASSED`.
- `make run-lvgl-mvu-tests` prints `ALL ... TESTS PASSED` and MVU memory soak reports `mem drop` below thresholds defined in the TODOs.
- `test_screen_navigation.py` passes and does not leak beyond threshold.
- `run_nav_test.py` passes and does not leak beyond threshold.

### Must Have
- Stack-first navigation contract with explicit ops: `PUSH`, `POP`, `REPLACE`, plus deterministic invalid-route handling.
- MVU tick/render path allocation-minimized (no dynamic string formatting; no per-tick lists/dicts/tuples constructed).
- Text lifetime pinned for all `lv_label_set_text_static` uses.
- Separate MVU device runner while preserving existing output conventions.

### Must NOT Have
- VDOM diffing / tree allocation per tick.
- LVGL callbacks/event handlers in MVU path.
- Unbounded screen caching (must be bounded by `nav_capacity`).
- Test runners with divergent output formats.

## Verification Strategy
> ZERO HUMAN INTERVENTION — all verification is agent-executed.
- Test decision: tests-after (device runner scripts + existing device scripts)
- Evidence: command outputs captured in tool logs; keep `@S:` / `@D:` format.

## Execution Strategy

### Branching Rule (decision-complete)
Determine base branch at execution time:
1. Run: `gh pr view 36 --json mergedAt,state --jq '{state:.state,mergedAt:.mergedAt}'`
2. If `mergedAt` is non-null: base branch = `master`.
3. Else: base branch = `pr/lvgl-mvu-memory-soak` (stack work on top of it until merge).

### Parallel Execution Waves

Wave 1 (foundation)
- MVU+nav contract + consolidated nav core module scaffold
- MVU device runner scaffold + Makefile target

Wave 2 (integration)
- Refactor MVU to use consolidated nav core and add multi-widget screens
- Refactor existing navigation scripts to use consolidated nav core

Wave 3 (verification)
- Compile/build/flash + run separated MVU tests + nav tests + leak checks

### Dependency Matrix (high level)
- Nav core must exist before refactoring MVU and existing nav scripts.
- MVU device runner can be added early, but must align to finalized MVU public API.

## TODOs

- [ ] 1. Create consolidated nav core as a compiled module

  **What to do**:
  - Create `examples/lvgl_nav.py` (compiled) providing ONE navigation engine used everywhere.
  - Define exact API (no optional features):
    - Screen IDs are `int` constants.
    - Operations: `push(screen_id)`, `pop()`, `replace(screen_id)`, `current()`, `dispose()`.
    - Transition policy is fixed:
      - push uses `lv_screen_load_anim(..., OVER_LEFT, 250ms, ...)`
      - pop uses `OVER_RIGHT, 250ms`
      - replace uses `FADE_IN, 180ms`
    - Deletion policy is safe: never delete the active screen; delete old screen only after the new one is loaded and after a transition pump loop.
  - Bounded caching:
    - `nav_capacity = 8` fixed in constructor.
    - If pushing when full: treat as `replace` (no growth).

  **Must NOT do**:
  - No LVGL event callbacks.
  - No dynamic dict-based registries in steady-state; registration is at init.

  **References**:
  - Pattern (stack+animation): `run_nav_test.py`
  - Pattern (tree validation): `test_screen_navigation.py`
  - LVGL helper calls: `examples/lvgl_screens.py`

  **Acceptance Criteria**:
  - [ ] `make compile SRC=examples/lvgl_nav.py` succeeds.
  - [ ] A minimal device script importing `lvgl_nav` can push/pop without exceptions (use existing nav tests in later tasks).

  **QA Scenarios**:
  ```
  Scenario: Push/pop basic
    Tool: Bash
    Steps: make compile SRC=examples/lvgl_nav.py
    Expected: exit 0

  Scenario: Pop at root
    Tool: Bash
    Steps: mpremote connect /dev/cu.usbmodem101 exec "import lvgl as lv; import lvgl_nav as nav; lv.init_display(); n=nav.Nav(8); n.init_root(0); n.pop(); print('ok')"
    Expected: prints ok, no exception
  ```

  **Commit**: YES | Message: `feat(ui): add consolidated lvgl navigation core` | Files: `examples/lvgl_nav.py`

- [ ] 2. Define MVU+navigation contract and implement MVU-driven navigation

  **What to do**:
  - Refactor/extend `examples/lvgl_mvu.py` to:
    - model contains `nav_stack` (int IDs) + `nav_size` + `active_screen_id`.
    - update handles messages to push/pop/replace.
    - tick applies nav op before render, in strict order:
      1) drain msg queue
      2) apply nav command (if any)
      3) render active screen retained objects
      4) call `lvgl_screens.timer_handler()` only when tests request (keep app tick minimal)
  - Upgrade from single label to a scaffold per screen (at least 4 labels + 1 widget like slider/bar/arc) and update multiple values retained-mode.
  - Prohibit dynamic strings in tick/render:
    - Use precomputed pooled strings for counter/labels.
    - If numeric formatting is needed, use precomputed tables (range-limited) and clamp.
  - Use `lv_label_set_text_static` only with pooled strings whose lifetime is pinned (module-level tuple or instance list kept for app lifetime).

  **Must NOT do**:
  - No f-strings/concatenation in tick/render.
  - No allocation of LVGL objects outside mount/build paths.

  **References**:
  - Current MVU structure: `examples/lvgl_mvu.py`
  - Static text constraint: `.sisyphus/notepads/fabulous-inspired-lvgl-mvu-dsl/learnings.md`

  **Acceptance Criteria**:
  - [ ] `make compile SRC=examples/lvgl_mvu.py` succeeds.
  - [ ] Generated C does not unbox LVGL objects to ints (spot-check `modules/usermod_lvgl_mvu/lvgl_mvu.c` for absence of `mp_obj_get_int(...lv_obj_create...)`).
  - [ ] MVU can push/pop between at least 2 screens via programmatic `dispatch` in tests.

  **QA Scenarios**:
  ```
  Scenario: Compile MVU
    Tool: Bash
    Steps: make compile SRC=examples/lvgl_mvu.py
    Expected: exit 0

  Scenario: Basic mount/tick/dispose
    Tool: Bash
    Steps: mpremote connect /dev/cu.usbmodem101 exec "import lvgl as lv; import lvgl_mvu as m; lv.init_display(); a=m.App(0,8,32); a.mount(); a.dispatch(1); a.tick(1); a.dispose(); print('ok')"
    Expected: prints ok
  ```

  **Commit**: YES | Message: `feat(ui): add MVU-driven navigation and multi-widget screens` | Files: `examples/lvgl_mvu.py`

- [ ] 3. Split MVU device tests into a dedicated runner + Makefile target

  **What to do**:
  - Add `run_lvgl_mvu_tests.py` that:
    - Imports `lvgl`, `lvgl_screens` (for `timer_handler`), and `lvgl_mvu`.
    - Uses same harness functions `suite()`, `t()`, and prints `@D:` summary like `run_lvgl_tests.py`.
    - Runs MVU-only suites:
      - `mvu_mount_dispose`
      - `mvu_nav_push_pop`
      - `mvu_memory_soak_tick_20000` (mem_drop < 4096)
      - `mvu_memory_soak_nav_2000` (mem_drop < 6144)
      - `mvu_remount_no_drift` (mount→dispose→mount→dispose, drift < 1024)
  - Update `Makefile`:
    - Add `run-lvgl-mvu-tests` target that runs `mpremote connect $(PORT) run run_lvgl_mvu_tests.py`.
    - Add `run-lvgl-tests-all` target that runs both `run-lvgl-tests` and `run-lvgl-mvu-tests`.
  - Keep `run_lvgl_tests.py` format unchanged (optionally remove the inline `lvgl_mvu` suite later, but only if `run-lvgl-tests-all` covers it).

  **References**:
  - Existing harness: `run_lvgl_tests.py`
  - Existing MVU soak logic: `run_lvgl_tests.py` suite `lvgl_mvu`

  **Acceptance Criteria**:
  - [ ] `make run-lvgl-mvu-tests PORT=/dev/cu.usbmodem101` exits 0 and prints `ALL ... TESTS PASSED`.
  - [ ] MVU soak tests report `mem drop` within thresholds.

  **QA Scenarios**:
  ```
  Scenario: MVU-only device run
    Tool: Bash
    Steps: make run-lvgl-mvu-tests PORT=/dev/cu.usbmodem101
    Expected: ALL ... TESTS PASSED
  ```

  **Commit**: YES | Message: `test(device): add dedicated LVGL MVU test runner` | Files: `run_lvgl_mvu_tests.py`, `Makefile`

- [ ] 4. Consolidate navigation demos/tests to use the single nav core

  **What to do**:
  - Refactor `test_screen_navigation.py` to use `lvgl_nav` instead of its local ScreenManager logic.
  - Refactor `run_nav_test.py` to use `lvgl_nav` for stack operations and keep only the visual overlay pieces.
  - Refactor `examples/lvgl/ui_screen_tree.py` to delegate to `lvgl_nav` (or deprecate it if it is only a demo).
  - Define one deterministic invalid-route behavior:
    - For stack nav: invalid screen id raises `ValueError` with exact message `invalid screen id: <id>`.
    - For tree nav validation: provide a fixed `allowed_children` tuple per screen id in `lvgl_nav` registration; invalid navigation raises `ValueError`.

  **Acceptance Criteria**:
  - [ ] `mpremote connect /dev/cu.usbmodem101 run test_screen_navigation.py` passes.
  - [ ] `mpremote connect /dev/cu.usbmodem101 run run_nav_test.py` passes.

  **QA Scenarios**:
  ```
  Scenario: Tree navigation test passes
    Tool: Bash
    Steps: mpremote connect /dev/cu.usbmodem101 run test_screen_navigation.py
    Expected: prints OK/ALL PASS, exits 0

  Scenario: Smooth nav demo passes
    Tool: Bash
    Steps: mpremote connect /dev/cu.usbmodem101 run run_nav_test.py
    Expected: prints ALL ... TESTS PASSED, exits 0
  ```

  **Commit**: YES | Message: `refactor(ui): consolidate navigation scripts on lvgl_nav` | Files: `test_screen_navigation.py`, `run_nav_test.py`, `examples/lvgl/ui_screen_tree.py`

## Final Verification Wave (4 parallel agents, ALL must APPROVE)
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Device QA — unspecified-high
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Use small, reviewable commits aligned to TODOs 1-4.
- Do not commit `.sisyphus/`.
- Do not commit any changes under `deps/micropython` (submodule dirty state must be ignored).

## Success Criteria
- MVU tests can be run independently: `make run-lvgl-mvu-tests`.
- Navigation is single-sourced (`examples/lvgl_nav.py`) and used across scripts.
- MVU demonstrates multi-widget updates and MVU-driven navigation.
- Device memory stability holds under soak thresholds.
