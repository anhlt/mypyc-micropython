# Adding List & For-Loop Support to mypyc-micropython

*How we taught a Python-to-C compiler to handle lists, loops, and method dispatch — and built a test harness that catches bugs before they reach the ESP32.*

---

## The Starting Point

[mypyc-micropython](https://github.com/anhlt/mypyc-micropython) compiles typed Python functions into native C modules for MicroPython. Before this PR, the compiler could handle the basics: arithmetic, `if/else`, `while` loops, recursion, and simple types like `int`, `float`, and `bool`. You could write a factorial function in Python and get a C module that runs on an ESP32 at native speed.

But you couldn't use a `for` loop. You couldn't use a list. For a language where `for i in range(n)` is the bread-and-butter construct, that's a big gap.

This PR closes that gap.

## What We Added

### Lists as First-Class Citizens

Python lists become MicroPython `mp_obj_t` heap objects. The compiler now translates:

```python
def build_squares(n: int) -> list:
    result: list = []
    for i in range(n):
        result.append(i * i)
    return result
```

into C that allocates a list with `mp_obj_new_list()`, grows it with `mp_obj_list_append()`, and returns it as a boxed object:

```c
static mp_obj_t list_operations_build_squares(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t result = mp_obj_new_list(0, NULL);
    mp_int_t i;
    mp_int_t _tmp2 = n;
    for (i = 0; i < _tmp2; i++) {
        (void)mp_obj_list_append(result, mp_obj_new_int((i * i)));
    }
    return result;
}
```

We support list literals (`[1, 2, 3]`), indexing (`lst[i]` for both get and set), `len()`, `append()`, `pop()`, and generic type annotations like `list[int]`.

### For Loops Over `range()`

The compiler recognizes `range()` with 1, 2, or 3 arguments and generates optimized C `for` loops. It detects constant step values to emit tighter loop constructs — `i++` for step 1, `i--` for step -1 — instead of always using `i += step`.

```python
# Negative step range
def reverse_sum(n: int) -> int:
    total: int = 0
    for i in range(n, 0, -1):
        total += i
    return total
```

becomes:

```c
for (i = n; i > _tmp9; i--) {
    total += i;
}
```

For-each over lists uses MicroPython's subscript API with an index counter — not the iterator protocol — which maps cleanly to C without needing to manage iterator state.

### Break and Continue

Both `break` and `continue` translate directly to their C equivalents. The compiler tracks loop depth, so it emits an error comment if you write `break` outside a loop instead of generating invalid C.

## The Bugs We Found (And Why They Mattered)

The initial implementation had several bugs. Some were logic errors in the example Python code, others were deeper issues in how the compiler handles MicroPython's type system.

### Bug 1: Comparing Pointers Instead of Values

The original `find_first_negative` compared the loop index against zero instead of the list element:

```python
# WRONG: checks if index i < 0 (never true for range)
if i < 0:
    return i

# FIXED: checks if element at index i is negative
if lst[i] < 0:
    return i
```

### Bug 2: The Boxing/Unboxing Boundary

This was the most interesting class of bug. MicroPython has two worlds: native C types (`mp_int_t`, `mp_float_t`) and boxed objects (`mp_obj_t`). The boundary between them is where bugs hide.

When you write `lst[i] < 0`, the subscript `lst[i]` returns an `mp_obj_t` (a tagged pointer), while `0` is an `mp_int_t`. Comparing them directly in C is a type error — you're comparing a pointer to an integer.

The fix was `_unbox_if_needed()`, a helper that detects when an `mp_obj_t` is being used in a context that expects a native type, and inserts `mp_obj_get_int()` to extract the value:

```python
def _unbox_if_needed(self, expr, expr_type, target_type="mp_int_t"):
    if expr_type == "mp_obj_t" and target_type != "mp_obj_t":
        return f"mp_obj_get_int({expr})", "mp_int_t"
    return expr, expr_type
```

This same boundary issue showed up in three places: comparisons, binary operations, and augmented assignments (`+=`). We also caught it in annotated assignments — `val: int = lst.pop(0)` was generating `mp_int_t val = <mp_obj_t>` without unwrapping.

### Bug 3: `list.pop()` Is Static in MicroPython

This one was subtle. We initially generated `mp_obj_list_pop(lst)` for `lst.pop()`. It compiled fine against our mock runtime. But `mp_obj_list_pop` is declared `static` in the real MicroPython source (`py/objlist.c`). It would fail at link time on a real firmware build.

The fix was to use MicroPython's method dispatch protocol instead:

```c
// What we generate now:
mp_obj_t __method[2];
mp_load_method(lst, MP_QSTR_pop, __method);
mp_call_method_n_kw(0, 0, __method);
```

This is how MicroPython itself calls `list.pop()` internally — load the method from the object's type table, then call it through the standard method calling convention. It's more code, but it's the only way that actually links.

Note: `mp_obj_list_append()` *is* public in MicroPython's API, so `append()` still uses the direct call. We only use method dispatch where we have to.

## Building a Real Test Harness

Python-level tests caught the logic bugs but missed the C-level ones. A test that checks "the generated C code contains `mp_obj_get_int`" tells you the string is there, but not whether the generated program actually computes the right answer.

We built an end-to-end C runtime test infrastructure:

### The Mock Runtime

`tests/mock_mp/runtime.h` is a single-header functional mock of MicroPython's runtime. It implements the same APIs with the same semantics — but in ~350 lines instead of thousands, and without needing the ESP-IDF toolchain.

Getting the mock right was critical. We verified every constant and struct layout against the real MicroPython source in `deps/micropython/py/`:

- **Small-int tagging**: MicroPython uses REPR_A encoding where small integers are `(value << 1) | 1`. Our mock matches this exactly.
- **Immediate objects**: `mp_const_none` = 6, `mp_const_false` = 14, `mp_const_true` = 30. These aren't arbitrary — they're `(val << 3) | 6` per MicroPython's `MP_OBJ_NEW_IMMEDIATE_OBJ` macro.
- **Sentinel values**: `MP_OBJ_NULL` = 0, `MP_OBJ_SENTINEL` = 4 (non-debug mode).
- **List struct layout**: `{tag, alloc, len, items}` matching MicroPython's `{base, alloc, len, items}`.

### The Test Pattern

Each test compiles Python source → generates C → appends a `main()` that calls the generated functions → compiles with gcc → runs the binary → asserts on stdout:

```python
def test_c_sum_range_returns_correct_sum(compile_and_run):
    source = """
def sum_range(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_sum_range(mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"
```

This catches everything: type mismatches that gcc would flag, runtime crashes from bad pointer arithmetic, and wrong answers from incorrect unboxing. If the test passes, the generated C code compiles and produces the right answer.

We have 15 C runtime tests covering: range loops (1/2/3 args), list building, list summation, negative element search, `break`, `continue`, nested loops, negative step ranges, recursion (factorial), `pop()` (last, at index, in loops, interleaved with append), and float arithmetic.

## The Final Numbers

- **96 tests passing**: 81 compiler unit tests + 15 end-to-end C runtime tests
- **8 functions** compilable from `examples/list_operations.py`
- **~19x average speedup** over interpreted MicroPython on ESP32 (measured with `benchmarks/benchmark_device.py`)

## What's Next

The compiler still has gaps:

- **Classes** — no `class` support yet
- **Exceptions** — no `try/except`
- **Dictionaries** — only lists for now
- **String operations** — basic string creation works, but no slicing or methods
- **Generic method dispatch** — only `pop` uses `mp_load_method`; other methods that turn out to be `static` in MicroPython will need the same treatment

Each of these follows the same pattern we established here: implement the translation, verify against real MicroPython source, test with the C runtime harness. The infrastructure is in place — it's just more features on the conveyor belt.

---

*PR: [#1 — Add list type and for-loop support](https://github.com/anhlt/mypyc-micropython/pull/1)*
