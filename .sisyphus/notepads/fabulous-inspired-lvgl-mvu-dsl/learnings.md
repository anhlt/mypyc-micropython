# Learnings

- `lv_label_set_text_static()` does not copy; keep Python strings alive for label lifetime (cache strings on the App).
- Module-level `import lvgl as lv` is the known-good pattern for codegen (see `examples/lvgl_screens.py`).

## LVGL Module-Level Import Fix (2026-03-03)

When generating C modules for LVGL, module-level imports (`import lvgl as lv`) are required to prevent `lvgl` undeclared errors during compilation.

**Problem**: Local function-level imports like `def func(): import lvgl` cause codegen failures.

**Solution**: 
- Use `import lvgl as lv` at module level
- Replace all local `import lvgl` with direct `lv.*` calls
- Ensures consistent symbol resolution during C code generation

**Rationale**: 
- Compiler needs global symbol visibility
- Local imports break static analysis and type tracking
- Module-level imports provide predictable symbol resolution

**Example Fix**:
```python
# BAD
def func():
    import lvgl  # Breaks codegen
    lvgl.some_call()

# GOOD
import lvgl as lv  # Module-level import
def func():
    lv.some_call()  # Direct method call
```

## LVGL MVU Example Cleanup (2026-03-03)

Cleaned up `examples/lvgl_mvu.py` to:
- Remove duplicate function definitions
- Ensure only module-level `import lvgl as lv`
- Preserve existing MVU logic and retained-mode text caching
- Maintain type annotations and function signatures

**Key Observations**:
- Duplicate function definitions can cause compilation issues
- Local imports break symbol resolution in compiled C modules
- Retained-mode text caching is crucial for LVGL label performance

## LVGL MVU Mount/Dispose De-dup Fix (2026-03-03)

- Keep `import lvgl as lv` before helper definitions that call `lv.*` to avoid fragile symbol resolution in generated C.
- A second `if self.root is None:` block after `return` in `mount()` is unreachable and can hide stale logic paths.
- `dispose()` should perform one cleanup/delete/reset pass only; duplicate reset blocks can mask lifecycle bugs.
- `lv.lv_obj_center(label)` is a safer centering pattern than hardcoded align constants for this example.
