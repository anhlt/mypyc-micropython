# Blog Post 39: Fixing Cross-Module Attribute Access for Dataclass Instances

## The Problem: When Attributes Disappear into `None`

While testing the LVGL MVU reconciler on device, we encountered a mysterious watchdog timer crash. The reconciler's "update existing node" test would run successfully through several test cases, then suddenly reset the device. The crash happened at this line:

```python
def reconcile(self, node: ViewNode | None, widget: Widget, parent_lv_obj) -> ViewNode:
    # ... code ...
    diff = diff_widgets(node.widget, widget)
    node.apply_diff(diff)
    self._reconcile_children(node, widget, diff.child_changes)  # <-- CRASH HERE
    if diff.event_changes:
        self._reconcile_handlers(node, widget)
```

The `_reconcile_children` method expects a list of child changes, but was receiving `None` instead. Let's trace how this happened and why the compiler was at fault.

## Part 1: Understanding the Compilation Pipeline

### The Three-Stage Journey

When you write typed Python for mypyc-micropython, your code goes through three transformations:

1. **Python AST** — Python's built-in parser converts your source into an Abstract Syntax Tree
2. **Intermediate Representation (IR)** — Our IR builder translates the AST into typed IR nodes
3. **C Code** — Emitters convert IR to MicroPython C API calls

The bug we're fixing lives in stage 2: the IR builder wasn't tracking type information correctly for certain variable assignments.

### Why Intermediate Representation Matters

The IR is where the compiler makes critical decisions about code generation. Consider this Python code:

```python
diff = diff_widgets(node.widget, widget)
x = diff.child_changes
```

The IR builder must answer: "What is `diff`?" If it doesn't know `diff` is a `WidgetDiff` dataclass, it can't generate direct struct field access. Instead, it falls back to dynamic attribute lookup or, in our buggy case, `None`.

### The Prelude Pattern and Type Tracking

The IR builder uses a prelude pattern where expressions return `(ValueIR, list[InstrIR])`:

```python
# IR for: diff = diff_widgets(node.widget, widget)
value, prelude = self._build_expr(call_expr, locals_)
# value = TempIR or NameIR holding the result
# prelude = [CallIR(...)] instructions that produce the value

# Then create assignment:
return AssignIR(target='diff', value=value, prelude=prelude)
```

For attribute access like `diff.child_changes` to work, the IR builder needs to know:
1. What type is `diff`? (Answer: `WidgetDiff`)
2. What fields does `WidgetDiff` have? (From the class IR)
3. What are the C types and struct offsets? (For code generation)

This type information is stored in `self._class_typed_params`, which maps variable names to class names.

## Part 2: C Structs and Pointer Casting

### MicroPython's Object Model

In MicroPython's C API, everything is an `mp_obj_t` — a pointer-sized value that can represent integers, booleans, or pointers to heap objects:

```c
typedef uintptr_t mp_obj_t;  // Could be an immediate value or a pointer
```

For dataclass instances, `mp_obj_t` is actually a pointer to a struct:

```c
typedef struct _lvgl_mvu_diff_WidgetDiff_obj_t {
    mp_obj_base_t base;           // Type info (required first field)
    mp_obj_t scalar_changes;      // List of scalar attribute changes
    mp_obj_t child_changes;       // List of child widget changes  
    bool event_changes;           // Flag: any event handler changes?
} lvgl_mvu_diff_WidgetDiff_obj_t;
```

### The Two Ways to Access Fields

**Method 1: Direct Struct Access** (Fast, type-safe)
```c
// Cast mp_obj_t to the specific struct pointer, then access field
mp_obj_t child_changes = ((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(diff))->child_changes;
```

This is what we want. The cast tells the C compiler "this `mp_obj_t` is actually a pointer to a `WidgetDiff` struct", then the arrow operator `->` accesses the field directly.

**Method 2: Dynamic Attribute Lookup** (Slow, runtime overhead)
```c
// Search the object's attribute dict at runtime
mp_obj_t child_changes = mp_load_attr(diff, MP_QSTR_child_changes);
```

This is the fallback when the compiler doesn't know the type. It's slower and defeats the purpose of compilation.

**Method 3: The Bug** (Wrong!)
```c
// Just use None when type tracking fails
mp_obj_t child_changes = mp_const_none;
```

This is what our buggy compiler was doing! When it couldn't resolve the type of `diff`, instead of falling back to dynamic lookup, it fell through to a catch-all case that returned `ConstIR(value=None)`.

### Why the Arrow Operator?

In C, there are two ways to access struct members:
- **Dot operator** `.` for struct values: `point.x`
- **Arrow operator** `->` for struct pointers: `point->x`

Since `mp_obj_t` values are pointers, we always use `->`. The arrow is syntactic sugar for dereferencing then accessing: `point->x` equals `(*point).x`.

## Part 3: The Bug and The Fix

### Bug 1: Plain Assignments Don't Track Class Types

The IR builder has `_build_assign()` for function-level assignments and `_build_method_assign()` for method-level assignments. Both looked like this:

```python
def _build_method_assign(self, stmt, locals_, class_ir, native):
    # ... handle self.attr = value ...
    
    # Handle regular assignment
    if isinstance(target, ast.Name):
        var_name = target.id
        value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)
        
        if is_new:
            locals_.append(var_name)
            self._var_types[var_name] = value.ir_type.to_c_type_str()
        
        # BUG: Never adds var_name to self._class_typed_params!
        # So later attribute access on this variable fails
        
        return AssignIR(target=var_name, value=value, ...)
```

When the reconciler assigns `diff = diff_widgets(...)`, this code runs. The variable gets added to `self._var_types` with C type `"mp_obj_t"`, but never to `self._class_typed_params` with Python type `"WidgetDiff"`.

Later, when compiling `diff.child_changes`:

```python
def _build_attribute(self, expr, locals_):
    if isinstance(expr.value, ast.Name):
        var_name = expr.value.id
        if var_name in self._class_typed_params:  # False! Not tracked
            class_name = self._class_typed_params[var_name]
            class_ir = self._known_classes[class_name]
            # ... emit ParamAttrIR for direct struct access ...
        
    # Fallthrough case - no type info available
    return ConstIR(ir_type=IRType.OBJ, value=None), []  # BUG: Returns None!
```

The attribute access fell through to the default case, which returned `None`.

### Bug 2: Optional Types Not Resolved

The second bug involved chained attribute access like `change.diff.child_changes`. The code to determine the type of `change.diff` looked like this:

```python
def _get_method_attr_class_type(self, expr, class_ir):
    # expr is: change.diff
    if isinstance(expr.value, ast.Name):
        var_name = expr.value.id  # "change"
        if var_name in self._class_typed_params:
            param_class_name = self._class_typed_params[var_name]  # "ChildChange"
            param_class_ir = self._known_classes[param_class_name]
            for fld in param_class_ir.get_all_fields():
                if fld.name == expr.attr:  # Found "diff" field
                    return fld.py_type  # BUG: Returns "WidgetDiff | None"
```

The field's Python type annotation is `diff: WidgetDiff | None`, so `fld.py_type` is the string `"WidgetDiff | None"`. But the caller expected a bare class name:

```python
parent_type = self._get_method_attr_class_type(expr.value, class_ir)
# parent_type = "WidgetDiff | None"

if parent_type and parent_type in self._known_classes:  # False! No match
    # ... would emit struct access here ...
```

The check `"WidgetDiff | None" in self._known_classes` fails because `_known_classes` only has `"WidgetDiff"`. So again, attribute access falls through to returning `None`.

### The Fix: Multi-Pronged Type Tracking

We implemented five interconnected changes to fix both bugs:

**1. Type Resolution Helper**

First, we added a helper to extract class names from type strings:

```python
def _resolve_class_name_from_type_str(self, type_str: str) -> str | None:
    """Extract a known class name from a type string, handling Optional/union."""
    # Direct match
    if type_str in self._known_classes:
        return type_str
    
    # Handle "X | None" or "None | X"
    if "|" in type_str:
        parts = [p.strip() for p in type_str.split("|")]
        non_none = [p for p in parts if p != "None"]
        if len(non_none) == 1:
            candidate = non_none[0]
            if candidate in self._known_classes:
                return candidate
    
    # Handle dotted names: "module.ClassName" -> "ClassName"
    base = type_str.split("|")[0].strip()
    if "." in base:
        short = base.rsplit(".", 1)[-1]
        if short in self._known_classes:
            return short
    
    return None
```

This handles:
- `"WidgetDiff"` → `"WidgetDiff"` (direct match)
- `"WidgetDiff | None"` → `"WidgetDiff"` (strip optional)
- `"lvgl_mvu.diff.WidgetDiff"` → `"WidgetDiff"` (strip module prefix)

**2. Fix Type Getters**

Updated all methods that return class types to use the resolver:

```python
def _get_method_attr_class_type(self, expr, class_ir):
    # ... same logic to find the field ...
    for fld in param_class_ir.get_all_fields():
        if fld.name == expr.attr:
            # OLD: return fld.py_type  # "WidgetDiff | None"
            return self._resolve_class_name_from_type_str(fld.py_type)  # "WidgetDiff"
```

Now chained attribute access works because the type is properly resolved.

**3. Populate Mypy Local Types for Methods**

The IR builder has access to mypy's type inference results through `self._mypy_local_types`. This dict maps local variable names to their inferred types. For functions, it was being populated:

```python
def build_function(self, node):
    mypy_func = self._get_mypy_func_type(func_name)
    if mypy_func:
        self._mypy_local_types = dict(mypy_func.local_types)
```

But for methods, it wasn't! We added:

```python
def build_method_body(self, method_ir, class_ir, native=False):
    # ... reset state ...
    
    # NEW: Populate mypy local type info for this method
    mypy_method = self._get_mypy_method_type(class_ir.name, method_ir.name)
    if mypy_method:
        self._mypy_local_types = dict(mypy_method.local_types)
    else:
        self._mypy_local_types = {}
```

Now methods have access to mypy's type inference.

**4. Track Class Types in Assignments**

Enhanced `_build_method_assign` and `_build_assign` to track class types:

```python
def _build_method_assign(self, stmt, locals_, class_ir, native):
    # ... existing logic ...
    if isinstance(target, ast.Name):
        var_name = target.id
        value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)
        
        if is_new:
            locals_.append(var_name)
            self._var_types[var_name] = value.ir_type.to_c_type_str()
        
        # NEW: Track class-typed local variables
        # First try mypy local types
        if var_name in self._mypy_local_types:
            inferred_class = self._resolve_class_name_from_type_str(
                self._mypy_local_types[var_name]
            )
            if inferred_class:
                self._class_typed_params[var_name] = inferred_class
        
        # Then try function return type: var = func_call(...)
        if var_name not in self._class_typed_params:
            if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
                func_name = stmt.value.func.id
                if func_name in self._func_class_returns:
                    self._class_typed_params[var_name] = self._func_class_returns[func_name]
        
        return AssignIR(...)
```

This is a two-level fallback:
1. First, check if mypy inferred the type (works for most cases in single-file compilation)
2. Second, check if the assignment is from a function call whose return type we know (works for cross-module cases where mypy gives up and returns `'Any'`)

**5. Scan Function Return Types During Package Compilation**

The package compilation pipeline scans all Python files twice. In the first pass, it builds class IRs. We added a second pass to scan function return types:

```python
def _scan_package_recursive(package_path, ...):
    # First pass: scan classes
    package_classes = {}
    for py_file in sorted(package_path.glob("*.py")):
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_ir = scanner.build_class(node)
                package_classes[class_ir.name] = class_ir
    
    # NEW: Second pass: scan function return types
    package_func_class_returns = {}
    for py_file in sorted(package_path.glob("*.py")):
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns and isinstance(node.returns, ast.Name):
                    ret_name = node.returns.id
                    if ret_name in package_classes:
                        package_func_class_returns[node.name] = ret_name
    
    # Pass func_class_returns to _compile_module_parts -> IRBuilder
```

Now when the IR builder sees `diff = diff_widgets(...)`, it can look up `diff_widgets` in `self._func_class_returns` and find `"WidgetDiff"`, even when mypy returned `'Any'` due to cross-module inference limitations.

### Step-by-Step: How the Fix Works

Let's trace the full compilation of the problematic code:

**Python Source:**
```python
def reconcile(self, node: ViewNode | None, widget: Widget, parent_lv_obj) -> ViewNode:
    diff = diff_widgets(node.widget, widget)
    self._reconcile_children(node, widget, diff.child_changes)
```

**Step 1: Build Method Body**

```python
# In build_method_body():
mypy_method = self._get_mypy_method_type("Reconciler", "reconcile")
# mypy_method.local_types = {'diff': 'Any'}  # Mypy gives up on cross-module inference
self._mypy_local_types = dict(mypy_method.local_types)
```

**Step 2: Build Assignment Statement**

```python
# In _build_method_assign() for: diff = diff_widgets(...)
var_name = "diff"
stmt.value = ast.Call(func=ast.Name(id="diff_widgets"), ...)

# First fallback: mypy local types
if var_name in self._mypy_local_types:  # True: 'diff' -> 'Any'
    inferred_class = self._resolve_class_name_from_type_str('Any')  # None (not a class)

# Second fallback: function return types
if var_name not in self._class_typed_params:  # True (still not tracked)
    if isinstance(stmt.value, ast.Call):  # True
        func_name = stmt.value.func.id  # "diff_widgets"
        if func_name in self._func_class_returns:  # True! Found it
            self._class_typed_params[var_name] = self._func_class_returns[func_name]
            # self._class_typed_params = {..., 'diff': 'WidgetDiff'}
```

**Step 3: Build Attribute Access**

```python
# In _build_attribute() for: diff.child_changes
if isinstance(expr.value, ast.Name):  # True
    var_name = expr.value.id  # "diff"
    if var_name in self._class_typed_params:  # True! Found "WidgetDiff"
        class_name = self._class_typed_params[var_name]  # "WidgetDiff"
        class_ir = self._known_classes[class_name]
        for fld in class_ir.get_all_fields():
            if fld.name == expr.attr:  # Found "child_changes"
                # Emit ParamAttrIR for direct struct access
                return ParamAttrIR(
                    param_name="diff",
                    attr_name="child_changes",
                    class_c_name="lvgl_mvu_diff_WidgetDiff",
                    result_type=IRType.OBJ,
                ), []
```

**Step 4: Emit C Code**

The `FunctionEmitter` sees `ParamAttrIR` and generates:

```c
// Cast to struct pointer and access field directly
mp_obj_t child_changes = ((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(diff))->child_changes;

// Pass to _reconcile_children_native
lvgl_mvu_reconciler_Reconciler__reconcile_children_native(self, node, widget, child_changes);
```

Perfect! No more `mp_const_none`.

### Before and After: The Generated C

**Before the fix (buggy):**
```c
static mp_obj_t lvgl_mvu_reconciler_Reconciler_reconcile_native(...) {
    mp_obj_t diff = lvgl_mvu_diff_diff_widgets(...);
    mp_obj_t _tmp2 = ({ mp_obj_t __method[3]; 
        mp_load_method(node, MP_QSTR_apply_diff, __method); 
        __method[2] = diff; 
        mp_call_method_n_kw(1, 0, __method); 
    });
    (void)_tmp2;
    
    // BUG: Passing mp_const_none instead of diff->child_changes
    (void)lvgl_mvu_reconciler_Reconciler__reconcile_children_native(
        self, node, widget, mp_const_none);
    
    // BUG: Checking mp_const_none instead of diff->event_changes
    if (mp_obj_is_true(mp_const_none)) {
        (void)lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native(
            self, node, widget);
    }
    
    return node;
}
```

**After the fix (correct):**
```c
static mp_obj_t lvgl_mvu_reconciler_Reconciler_reconcile_native(...) {
    mp_obj_t diff = lvgl_mvu_diff_diff_widgets(...);
    mp_obj_t _tmp2 = ({ mp_obj_t __method[3]; 
        mp_load_method(node, MP_QSTR_apply_diff, __method); 
        __method[2] = diff; 
        mp_call_method_n_kw(1, 0, __method); 
    });
    (void)_tmp2;
    
    // FIXED: Direct struct field access to child_changes
    (void)lvgl_mvu_reconciler_Reconciler__reconcile_children_native(
        self, node, widget, 
        ((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(diff))->child_changes);
    
    // FIXED: Direct struct field access to event_changes
    if (((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(diff))->event_changes) {
        (void)lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native(
            self, node, widget);
    }
    
    return node;
}
```

The fix also applies to chained attribute access. In `_reconcile_children`, we had:

```python
for change in changes:
    if change.kind == "update":
        child_node = node.get_child(change.old_index)
        self._reconcile_children(
            child_node, 
            change.widget, 
            change.diff.child_changes  # Chained: change -> diff -> child_changes
        )
```

**Before (buggy):**
```c
(void)lvgl_mvu_reconciler_Reconciler__reconcile_children_native(
    self, child_node, 
    ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget, 
    mp_const_none);  // BUG!
```

**After (correct):**
```c
mp_obj_t _tmp11 = ((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(
    ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->diff
))->child_changes;

(void)lvgl_mvu_reconciler_Reconciler__reconcile_children_native(
    self, child_node, 
    ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget, 
    _tmp11);  // FIXED!
```

Notice the nested casts: first cast `change` to `ChildChange_obj_t*` and access `diff`, then cast that to `WidgetDiff_obj_t*` and access `child_changes`. This is the C equivalent of `change.diff.child_changes`.

## Testing the Fix

### Unit Tests

All existing tests continued to pass:
- 742 pytest unit tests (test_compiler.py, test_ir_builder.py, test_emitters.py, test_type_checker.py)
- 112 C runtime tests (test_c_runtime.py — compile generated C with gcc and execute)

### Device Tests

The critical test was on the actual ESP32-P4 hardware:

```
@S:lvgl_mvu_reconciler
  OK: reconciler created
  OK: reconcile new
  OK: reconcile lv_obj
  OK: reconcile widget
  OK: reconcile update same        ← Previously crashed here!
  OK: reconcile widget updated
  OK: reconcile replace
  OK: reconcile old disposed
  OK: reconcile children
  OK: reconcile child0
  OK: reconcile child1
  OK: dispose_tree root
  OK: dispose_tree count

ALL 529 TESTS PASSED
```

The "reconcile update same" test, which was causing watchdog timer resets, now passes cleanly. All 529 device tests pass, up from 520/521 before the fix.

### What Was Actually Tested

The device test that exposed the bug:

```python
# In tests/device/run_device_tests.py
suite("lvgl_mvu_reconciler")
import lvgl_mvu.reconciler as rec

# Create initial widget tree
w1 = Widget("container", user_key="c1", children=[
    Widget("button", user_key="b1", scalars={"text": "Click Me"})
])

# Reconcile to create ViewNode tree
r = rec.Reconciler(None, None)
n1 = r.reconcile(None, w1, None)

# Update widget with changed text
w2 = Widget("container", user_key="c1", children=[
    Widget("button", user_key="b1", scalars={"text": "Updated"})  # Changed!
])

# THIS LINE WOULD CRASH:
n2 = r.reconcile(n1, w2, None)  # Update existing node
# Now it passes: diff.child_changes contains one "update" change,
# which recursively updates the button's text attribute

t("reconcile update same", n1 is n2, "True")  # Same ViewNode instance reused
```

## Key Takeaways

**1. Type Tracking is Critical for Native Code Generation**

The compiler must know variable types to generate direct struct access. Without it, we fall back to slower dynamic lookups or, in our buggy case, outright errors.

**2. Cross-Module Type Inference is Hard**

Mypy gives up on inferring types for variables assigned from cross-module function calls, returning `'Any'`. We need additional mechanisms (scanning function return annotations) to recover this information.

**3. Optional Types Need Special Handling**

When a field is typed as `T | None`, the compiler needs to extract the base type `T` for struct access. The optional part only affects null checks at runtime.

**4. The Prelude Pattern Separates Concerns**

By returning `(ValueIR, list[InstrIR])` from expression builders, we cleanly separate "what is the result?" from "what side effects must happen first?". This makes it easier to compose complex expressions while maintaining correct evaluation order.

**5. Multi-Level Fallbacks Improve Robustness**

Our fix uses three levels of type tracking:
- Primary: Explicit type annotations (always most reliable)
- Fallback 1: Mypy inference (works for most single-module cases)
- Fallback 2: Function return type scanning (works when mypy gives up)

This layered approach ensures we can handle a wide variety of code patterns.

**6. Device Testing is Mandatory**

This bug only appeared on real hardware. Unit tests couldn't catch it because:
- They test individual compilation units in isolation
- C runtime tests use a mock MicroPython API with different memory layout
- Only the full device has the exact struct layouts, calling conventions, and runtime behavior that exposed the crash

Always test on the target device before considering a feature complete.

## Files Modified

### src/mypyc_micropython/ir_builder.py
- Added `_resolve_class_name_from_type_str()` helper (lines 2206-2225)
- Updated `_get_class_type_of_attr()` to use resolver (lines 2237, 2244)
- Updated `_get_method_attr_class_type()` to use resolver (lines 2254, 2261, 2268)
- Populated `_mypy_local_types` in `build_method_body()` (lines 2995-3000)
- Added class tracking in `_build_method_assign()` (lines 3169-3182)
- Added class tracking in `_build_assign()` (lines 1044-1057)
- Added `func_class_returns` parameter to `__init__()` (line 208)

### src/mypyc_micropython/compiler.py
- Added function return type scanning in `_scan_package_recursive()` (lines 606-618)
- Thread `func_class_returns` through to `_compile_module_parts()` (line 635)
- Added `func_class_returns` parameter to `_compile_module_parts()` (line 291)
- Passed to IRBuilder constructor (line 323)

## Conclusion

This fix demonstrates how critical proper type tracking is in a typed-Python-to-C compiler. When the compiler loses track of variable types, it can't generate efficient native code — or worse, it generates wrong code that crashes at runtime.

The five-part fix ensures that:
1. Optional types are properly resolved to base class names
2. Mypy's type inference is fully utilized for methods
3. Function return types provide a fallback when mypy gives up
4. Plain assignments track class types through multiple inference paths
5. Cross-module attribute access works correctly

With these changes, the LVGL MVU reconciler can efficiently update widget trees on embedded hardware without runtime crashes, generating optimal C code with direct struct field access instead of expensive dynamic lookups or incorrect `None` values.
