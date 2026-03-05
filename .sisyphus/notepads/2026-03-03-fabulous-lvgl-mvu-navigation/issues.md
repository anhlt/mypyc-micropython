# Issues

- `time.ticks_ms`, `time.ticks_diff`, and `time.sleep_ms` trigger strict attr-defined errors in this environment when accessed directly from `time`; resolved via `getattr` indirection.
- `pop()` and stack slot reads require explicit `None` guards because `_screens` is `list[object | None]` for fixed-size preallocation.
- `dispose()` intentionally keeps the blank active screen alive (not deleted) to preserve the "never delete active screen" policy; this leaves one active placeholder allocated until caller replaces/disposes the display state.

- Generated C still inserts broad mp_obj_get_int(...) casts around some LVGL object/text flows in this compiler backend; only the requested ...lv_obj_create... cast pattern was eliminated in this task.

- Host verification can only perform syntax checks (`python -m py_compile`) for `run_lvgl_mvu_tests.py`; full `ALL ... TESTS PASSED` validation still requires connected hardware via `make run-lvgl-mvu-tests PORT=...`.

- `lvgl_nav.Nav` pumps transitions internally, so `run_nav_test.py` no longer has frame-accurate in-loop FPS sampling; it reports operation-time FPS estimates per push/pop/replace call.

- Nav-level tree validation requires callers to provide a complete `allowed_children` table entry for every parent that should permit transitions; missing parents now intentionally deny all children.
