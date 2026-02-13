# Adding Dict Support to mypyc-micropython

*How we extended the compiler to handle dictionaries — and what the differences from lists taught us about MicroPython's C internals.*

---

## Where We Left Off

After the [list and for-loop PR](01-list-and-forloop-support.md), the compiler could handle lists, `range()` loops, and for-each iteration over lists. Dicts were next on the roadmap. On the surface, dicts look similar to lists — they're both heap-allocated `mp_obj_t` containers — but the implementation diverged in almost every layer: construction, subscripting, method dispatch, and iteration.

## What We Added

### Dict Literals

Python dict literals become a sequence of `mp_obj_dict_store()` calls. Compare with lists:

**List construction** — pass all items as a C array in one call:

```c
mp_obj_t _tmp1_items[] = {mp_obj_new_int(1), mp_obj_new_int(2), mp_obj_new_int(3)};
mp_obj_t _tmp1 = mp_obj_new_list(3, _tmp1_items);
```

**Dict construction** — allocate empty, then insert key-value pairs one by one:

```c
mp_obj_t _tmp1 = mp_obj_new_dict(3);
mp_obj_dict_store(_tmp1, mp_obj_new_str("name", 4), mp_obj_new_str("test", 4));
mp_obj_dict_store(_tmp1, mp_obj_new_str("value", 5), mp_obj_new_int(42));
mp_obj_dict_store(_tmp1, mp_obj_new_str("enabled", 7), (true ? mp_const_true : mp_const_false));
```

Lists can use a C array initializer because they're a flat sequence of values. Dicts can't — key-value pairs don't fit into a simple array, and MicroPython doesn't expose a bulk-insert API. So construction is always O(n) calls instead of one.

Both use the same "pending temps" pattern internally. The compiler defers the allocation code until the next statement flush, so the temp variable is declared at the right scope. Dict support extended this by adding `_pending_dict_temps` alongside the existing `_pending_list_temps`, both flushed by `_flush_pending_list_temps()`.

### The `_box_value()` Refactoring

With lists, boxing logic was duplicated wherever we needed to wrap a native C type as an `mp_obj_t`. When dicts arrived — needing boxing for both keys and values — we extracted `_box_value()`:

```python
def _box_value(self, expr: str, expr_type: str) -> str:
    if expr_type == "mp_int_t":
        return f"mp_obj_new_int({expr})"
    elif expr_type == "mp_float_t":
        return f"mp_obj_new_float({expr})"
    elif expr_type == "bool":
        return f"({expr} ? mp_const_true : mp_const_false)"
    return expr
```

This helper is now used in dict literal construction, subscript operations, method arguments, and list append — anywhere a native value crosses the boundary into `mp_obj_t` territory. The list code was refactored to use it too, removing the duplicated boxing that had accumulated in the first PR.

### Subscript Generalization

Before dicts, subscript operations (`x[i]`) always boxed the index as an integer:

```c
// Before: hardcoded int boxing
mp_obj_subscr(lst, mp_obj_new_int(i), MP_OBJ_SENTINEL);
```

Dict keys can be strings, integers, floats, or booleans. So `_translate_subscript()` now uses `_box_value()` to handle any key type:

```c
// After: generic boxing via _box_value()
mp_obj_subscr(d, mp_obj_new_str("key", 3), MP_OBJ_SENTINEL);
```

The same change applies to subscript assignment (`d["key"] = value`), which generates `mp_obj_subscr(d, boxed_key, boxed_value)`.

### Type Tracking with `_var_types`

This was the change that surprised us most. Before dicts, the compiler could mostly get away without remembering variable types after assignment — local variables were almost always `mp_int_t`, and the few `mp_obj_t` variables (lists) were used in contexts where the type was obvious from the AST.

Dicts broke this assumption. Consider:

```python
def lookup(d: dict, key: str) -> int:
    return d[key]
```

When translating `d[key]`, the compiler needs to know that `key` is a `str` (type `mp_obj_t`) to box it correctly. But by the time it encounters the subscript expression, it's looking at an `ast.Name` node for `key` — which has no type annotation. The old compiler would default to `mp_int_t` and generate `mp_obj_new_int(key)`, which is wrong.

The fix: `_var_types`, a dict that tracks every variable's C type throughout a function. It's populated when:
- Function parameters are processed (from type annotations)
- Local variables are assigned (from the expression type)
- Loop variables are declared (from the iteration context)

And consulted in `_translate_name()`:

```python
def _translate_name(self, expr: ast.Name, locals_: list[str]) -> tuple[str, str]:
    c_name = sanitize_name(name)
    var_type = self._var_types.get(name, "mp_int_t")
    return c_name, var_type
```

This isn't just a dict feature — it fixed a whole class of type-inference bugs that happened to be masked when the only container type was `list[int]`.

### Iterator Protocol for For-Each

In the list PR, for-each over lists used index-based access:

```c
// Old: index-based iteration (list only)
mp_int_t _idx = 0;
mp_int_t _len = mp_obj_get_int(mp_obj_len(lst));
for (_idx = 0; _idx < _len; _idx++) {
    mp_obj_t item = mp_obj_subscr(lst, mp_obj_new_int(_idx), MP_OBJ_SENTINEL);
    // ...
}
```

This works for lists but not dicts — dicts don't support integer indexing. So we switched to MicroPython's proper iterator protocol:

```c
// New: iterator protocol (works for any iterable)
mp_obj_iter_buf_t _tmp2;
mp_obj_t _tmp1 = mp_getiter(d, &_tmp2);
while ((key = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
    // ...
}
```

`mp_getiter()` gets an iterator from any iterable object. `mp_iternext()` returns the next item, or `MP_OBJ_STOP_ITERATION` when exhausted. This is how MicroPython's own `for` statement works internally, and it handles lists, dicts, tuples, generators — anything with `__iter__`.

The old index-based approach was actually a leftover from the initial list implementation. Switching to the iterator protocol was the right fix regardless of dicts.

### Method Dispatch: Two Patterns

List methods use a mix of direct C API calls and method dispatch. Dict methods are almost entirely method dispatch. Here's why.

**Direct API call** (list `append`):

```c
mp_obj_list_append(lst, mp_obj_new_int(42));
```

`mp_obj_list_append()` is declared as a public function in MicroPython's headers. We can call it directly.

**Method dispatch** (dict `keys`, `values`, `items`, `copy`, `clear`, `popitem`, `setdefault`, `update`):

```c
mp_call_function_0(mp_load_attr(d, MP_QSTR_keys));
```

Most dict operations aren't exposed as public C functions in MicroPython. `mp_obj_dict_get()` and `mp_obj_dict_store()` exist, but there's no `mp_obj_dict_keys()` or `mp_obj_dict_clear()`. So we use `mp_load_attr()` to load the method from the object's type table, then `mp_call_function_N()` to invoke it.

We learned this lesson the hard way with `list.pop()` in the previous PR — it's declared `static` in MicroPython, so calling it directly fails at link time. Dict methods use the dispatch pattern from the start.

The one exception is `dict.get()` with a single argument (no default), which uses the public `mp_obj_dict_get()`:

```c
// d.get(key) — direct API
mp_obj_dict_get(d, boxed_key);

// d.get(key, default) — method dispatch (mp_obj_dict_get doesn't accept a default)
mp_call_function_n_kw(mp_load_attr(d, MP_QSTR_get), 2, 0, (mp_obj_t[]){boxed_key, boxed_default});
```

`dict.pop()` also needed special handling. List `pop()` takes 0 or 1 argument (index). Dict `pop()` takes 1 or 2 arguments (key, optional default). We extended the existing `pop` handler to support the 3-arg form using `mp_load_method` + `mp_call_method_n_kw`.

### C Reserved Word Handling

Dict keys like `"int"`, `"float"`, `"return"` are valid Python strings but collide with C keywords when used as variable names. We added `C_RESERVED_WORDS` — a set of all C reserved words — and `sanitize_name()` to prefix them with an underscore:

```python
C_RESERVED_WORDS = {"auto", "break", "case", "char", "const", ...}

def sanitize_name(name: str) -> str:
    if name in C_RESERVED_WORDS:
        return f"_{name}"
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)
```

This isn't strictly a dict problem — any Python variable named `int` would collide — but dict support made it urgent because config-style dicts frequently use type names as keys.

### Membership Testing

We added `in` and `not in` operators for dicts:

```python
def has_key(d: dict, key: str) -> bool:
    return key in d
```

generates:

```c
mp_obj_t _result = mp_call_function_n_kw(
    mp_load_attr(d, MP_QSTR___contains__), 1, 0,
    (mp_obj_t[]){key}
);
return (_result == mp_const_true) ? true : false;
```

## What We Shared, What Diverged

The dict implementation reused more infrastructure than expected:

| Component | Shared with Lists | Dict-Specific |
|-----------|------------------|---------------|
| Pending temps pattern | ✅ Same flush mechanism | New `_pending_dict_temps` list |
| Boxing values | ✅ Extracted to shared `_box_value()` | — |
| Subscript get/set | ✅ Same `mp_obj_subscr()` API | Generic key boxing |
| `len()` | ✅ Same `mp_obj_len()` | — |
| Iteration | ✅ Upgraded to shared iterator protocol | — |
| Construction | ❌ | Multi-call `mp_obj_dict_store()` |
| Method dispatch | Partial (`pop` via `mp_load_method`) | Almost all methods via `mp_load_attr` |

The biggest payoff was that implementing dicts forced us to generalize code that was list-specific. `_box_value()`, the iterator protocol switch, and `_var_types` tracking all made the compiler more correct for lists too — not just dicts.

## The Numbers

- **167 tests passing**: 152 compiler unit tests + 15 C runtime tests
- **17 functions** compilable from `examples/dict_operations.py`
- **11 dict methods** supported: `get`, `keys`, `values`, `items`, `copy`, `clear`, `pop`, `popitem`, `setdefault`, `update`, plus `dict()` copy constructor

## How mypyc Does It (and Why We Didn't)

After shipping dict support, we went back and studied how [mypyc](https://github.com/python/mypy/tree/master/mypyc) — the real mypy-to-CPython compiler — handles the same operations. The architectures diverge in almost every decision, and understanding why is useful for anyone building a compiler against a different runtime.

### Three Stages vs. One

mypyc compiles Python through three stages: AST → IR (intermediate representation) → C. Each stage has its own data structures — `DictNew`, `DictSet`, `DictGet` IR ops, register allocation, reference counting insertion — before a final C code emitter serializes everything.

mypyc-micropython goes AST → C directly. No IR. The `TypedPythonTranslator` walks the AST and emits C strings. This is simpler and faster to develop, but it means every optimization we want has to live in the AST walker itself — there's no separate pass to fold constants or eliminate dead stores.

For a project targeting MicroPython on ESP32, direct translation is the pragmatic choice. mypyc's IR exists because CPython's C API has sharp edges (reference counting, exception state, type slots) that are easier to handle in a structured intermediate form. MicroPython's API is simpler — `mp_obj_t` in, `mp_obj_t` out, garbage collector handles the rest.

### Dict Construction: One Call vs. Many

mypyc generates a single call to build a dict:

```c
// mypyc (CPython): variadic helper, one call
cpy_r_d = CPyDict_Build(3, key1, val1, key2, val2, key3, val3);
```

`CPyDict_Build` is a custom variadic C function in mypyc's runtime library (`mypyc/lib-rt/dict_ops.c`). It calls `_PyDict_NewPresized(size)` to pre-allocate, then loops through `va_arg` pairs calling `PyDict_SetItem()`. The generated code is clean — one function call per dict literal regardless of size.

We generate N+1 calls:

```c
// mypyc-micropython (MicroPython): allocate + N stores
mp_obj_t d = mp_obj_new_dict(3);
mp_obj_dict_store(d, key1, val1);
mp_obj_dict_store(d, key2, val2);
mp_obj_dict_store(d, key3, val3);
```

We could write a variadic helper too, but it's not worth it. MicroPython doesn't expose `_PyDict_NewPresized()` — `mp_obj_new_dict(n)` already pre-sizes the hash table. The per-store overhead is negligible on the microcontrollers we target, and avoiding a custom C runtime function means our generated code depends only on MicroPython's public API. Nothing to maintain, nothing to break when MicroPython updates.

### The Primitive Registry Pattern

mypyc maps Python operations to C functions through a declarative primitive registry (`mypyc/primitives/dict_ops.py`):

```python
# mypyc: declarative mapping
dict_get_item_op = method_op(
    name="__getitem__",
    arg_types=[dict_rprimitive, object_rprimitive],
    c_function_name="CPyDict_GetItem",
    error_kind=ERR_MAGIC,
)
```

There are ~25 dict primitives registered this way — `dict_set_item_op`, `dict_copy_op`, `dict_update_op`, and so on. Each declares its argument types, C function name, and error handling strategy. The IR builder looks up the right primitive, and the code generator emits the call. Adding a new dict operation means adding one registry entry plus (optionally) a C runtime function.

We use `if/elif` chains in `_translate_method_call()`:

```python
# mypyc-micropython: procedural dispatch
if method_name == "get":
    if len(node.args) == 1:
        return f"mp_obj_dict_get({obj_name}, {boxed_key})", "mp_obj_t"
    else:
        return f"mp_call_function_n_kw(...)", "mp_obj_t"
elif method_name == "keys":
    return f"mp_call_function_0(mp_load_attr({obj_name}, MP_QSTR_keys))", "mp_obj_t"
```

The registry pattern is better engineering — it separates the "what" from the "how" and makes adding operations mechanical. But for 11 dict methods in a ~900-line compiler, the `if/elif` approach is readable and local. If we ever hit 50+ operations across multiple types, a registry would make sense. We're not there yet.

### Subclass Handling: The Biggest Difference We Don't Need

Almost every C function in mypyc's dict runtime starts the same way:

```c
// mypyc/lib-rt/dict_ops.c
PyObject *CPyDict_GetItem(PyObject *dict, PyObject *key) {
    if (PyDict_CheckExact(dict)) {
        // Fast path: real dict, use internal API
        PyObject *res = PyDict_GetItemWithError(dict, key);
        // ...
    } else {
        // Slow path: dict subclass, use generic protocol
        return PyObject_GetItem(dict, key);
    }
}
```

Every function — `GetItem`, `SetItem`, `Get`, `SetDefault`, `Keys`, `Values`, `Items`, `Clear`, `Copy` — has this dual path. `PyDict_CheckExact()` tests whether the object is a plain `dict` or a subclass (like `defaultdict` or `OrderedDict`). The fast path uses CPython's internal dict API. The slow path falls back to the generic object protocol, which goes through `__getitem__`, `__setitem__`, etc.

MicroPython doesn't have dict subclasses. There's no `defaultdict`, no `OrderedDict`, no `collections` module on most embedded builds. `mp_obj_dict_store()` is the only path. This eliminates an entire category of complexity — no type checks, no fallback paths, no method resolution order concerns.

This is arguably the single biggest advantage of targeting MicroPython over CPython for a compiler project: the runtime is small enough that the "obvious" code path is the only code path.

### Iteration: Internal API vs. Public Protocol

mypyc iterates dicts using CPython's internal `PyDict_Next()` API:

```c
// mypyc: internal iteration, zero allocation
Py_ssize_t offset = 0;
PyObject *key, *value;
while (PyDict_Next(dict, &offset, &key, &value)) {
    // ...
}
```

This is a fast path that walks the dict's internal hash table directly. No iterator object is allocated. mypyc wraps this in `CPyDict_GetKeysIter()` + `CPyDict_NextKey()` (and `NextValue`, `NextItem` variants), which use the dict object itself as the "iterator" by stashing the offset in a tuple alongside the dict pointer. Three separate subclasses — `ForDictionaryKeys`, `ForDictionaryValues`, `ForDictionaryItems` — generate specialized code for each iteration mode.

mypyc also inserts `CPyDict_CheckSize()` calls in the loop body to detect dict mutation during iteration (a `RuntimeError` in Python). We don't.

We use MicroPython's public iterator protocol:

```c
// mypyc-micropython: public protocol, one iterator object
mp_obj_iter_buf_t iter_buf;
mp_obj_t iter = mp_getiter(dict, &iter_buf);
mp_obj_t key;
while ((key = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
    // ...
}
```

`mp_getiter` allocates a small iterator object (using the stack-allocated `iter_buf` to avoid heap allocation). `mp_iternext` returns the next key, or a sentinel when done. It's the same protocol as `for key in d:` in interpreted MicroPython.

The trade-off: mypyc's approach is faster (no iterator allocation, direct hash table access) but requires knowledge of CPython's internal dict layout. Our approach works with any iterable — lists, dicts, tuples, generators — through a single code path. On a microcontroller where dict sizes are typically under 100 entries, the iterator overhead is irrelevant.

### Error Handling: Explicit vs. None

mypyc has an error handling taxonomy. Every primitive declares its error kind:

- `ERR_MAGIC` — returns a magic value (like `NULL`) on error
- `ERR_FALSE` — returns `false` on error
- `ERR_NEG_INT` — returns -1 on error
- `ERR_NEVER` — operation cannot fail

The generated C code checks return values and branches to error handlers. `CPyDict_GetItem()` returns `NULL` on `KeyError`, and the generated code tests for `NULL` and jumps to the exception propagation path.

We don't generate error handling code. If `mp_obj_dict_get()` fails because the key doesn't exist, MicroPython's runtime raises the exception internally via `mp_raise_msg()`, which longjumps out of the generated code. This is how all interpreted MicroPython code works — the runtime handles exceptions, not the generated C.

This is a legitimate design trade-off. mypyc's explicit error checking enables better error messages and stack traces. Our approach is simpler but means exceptions from compiled code get MicroPython's generic error formatting instead of source-mapped tracebacks. For embedded firmware where exceptions typically mean "log and restart," this is acceptable.

### What We Could Learn From mypyc

Three patterns from mypyc are worth considering for future work:

1. **Mutation detection during iteration** — `CPyDict_CheckSize()` is a single size comparison. We could add this cheaply and catch a common bug class.

2. **Type specialization** — mypyc tracks `dict_rprimitive` vs `object_rprimitive` through the IR, enabling operations like "if both operands are exact dicts, use the fast path." Our `_var_types` dict is a primitive version of this. Expanding it to distinguish `dict` from `list` from `str` at the C type level would enable better code generation.

3. **Declarative operation registry** — If we add tuple and set support with the same method dispatch pattern, the `if/elif` chains will get unwieldy. A table mapping `(type, method_name) → C code template` would keep the translator class from growing linearly with the number of supported operations.

## What's Next

The compiler's container story is now solid for lists and dicts. The remaining gaps:

- **Tuple support** — immutable sequences, likely simpler than lists
- **String operations** — slicing, methods, f-strings
- **Set operations** — similar dispatch pattern to dicts
- **Classes** — the big one, requiring struct layout and method tables
- **Exceptions** — `try/except/finally` with proper stack unwinding

Each follows the same cycle: translate the AST nodes, handle the boxing boundaries, choose between direct API and method dispatch, and verify with the C runtime harness.

---

*PR: [#2 — Add dict type support](https://github.com/anhlt/mypyc-micropython/pull/2)*
