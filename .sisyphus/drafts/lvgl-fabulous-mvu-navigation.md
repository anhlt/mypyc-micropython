# Draft: Fabulous-Inspired LVGL MVU + Navigation

## Requirements (confirmed)
- Separate MVU test runner so MVU can be run alone on device.
- Consolidate screen navigation implementation (avoid multiple divergent ScreenManagers).
- Use MVU with screen navigation (model-driven navigation + retained-mode UI updates).
- Keep memory stable on device (avoid per-tick allocations; safe `lv_label_set_text_static()` usage).

## Technical Decisions
- MVU is retained-mode (no VDOM diff); render updates existing LVGL objects only.
- Navigation is MVU-driven: update emits nav commands (push/pop/replace) and a controller applies LVGL screen transitions.
- Dynamic strings are prohibited in steady-state tick/render; use pooled strings with stable lifetime.

## Research Findings
- Existing navigation code paths:
  - `run_nav_test.py`: stack navigation + animations + FPS overlay.
  - `test_screen_navigation.py`: tree navigation via pure-Python ScreenManager using compiled `lvgl_screens` factories.
  - `examples/lvgl/ui_screen_tree.py` + `examples/lvgl/ui_nav_core.py`: ScreenManager optionally delegates to a simple nav_core registry.
- Existing LVGL device test harness:
  - `run_lvgl_tests.py` runs `lvgl_screens` and `lvgl_mvu` suites with `@S:`/`@D:` summary format.
- Memory constraint: `lv_label_set_text_static()` does not copy; text must remain alive.

## Open Questions
- None (defaults applied: keep integer screen IDs; use stack nav + optional tree validation; keep `run_lvgl_tests.py` format).

## Scope Boundaries
- INCLUDE: MVU runtime, nav controller, retained components, dedicated MVU device test runner, Makefile targets.
- EXCLUDE: Full Fabulous API parity; LVGL callbacks/event handlers; VDOM diffing.
