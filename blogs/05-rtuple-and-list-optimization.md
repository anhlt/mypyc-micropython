# RTuple and List Optimization: From 3x to 47x Speedup

*How type-aware compilation transforms tuple and list operations from interpreted overhead to native C performance.*

---

When you write `point = (x, y)` in Python, what actually happens? In standard MicroPython, the runtime allocates a tuple object on the heap, boxes each element, and stores pointers to those boxed values. Every access to `point[0]` requires a function call, bounds checking, and pointer dereferencing. For tight loops processing thousands of coordinates, this overhead dominates execution time.

But what if the compiler knew that `point` was always a 2-tuple of integers? It could store `x` and `y` directly in a C struct, access them with simple field lookups, and skip all the boxing overhead. This is exactly what RTuple optimization does, and it delivers a **47x speedup** on ESP32.

## The Problem: Tuple Overhead in Hot Loops

Consider a common pattern in embedded systems: processing sensor data as coordinate tuples.

```python
def sum_coordinates(n: int) -> int:
    total: int = 0
    i: int = 0
    while i < n:
        point: tuple[int, int] = (i, i * 2)
        total += point[0] + point[1]
        i += 1
    return total
```

In vanilla MicroPython, each iteration:
1. Allocates a new tuple object (heap allocation)
2. Boxes `i` and `i * 2` as `mp_obj_t` (two more allocations)
3. Stores pointers in the tuple's items array
4. Calls `mp_obj_subscr()` twice for `point[0]` and `point[1]`
5. Unboxes the results back to integers

That's at least 3 heap allocations and 4 function calls per iteration. For 1000 iterations, we're looking at 3000 allocations and 4000 function calls just for tuple operations.

## The Solution: RTuple (Register Tuple)

The key insight comes from mypyc, the ahead-of-time compiler for Python. When mypyc sees a tuple with a fixed type signature like `tuple[int, int]`, it can represent it as a C struct instead of a heap-allocated object.

```c
typedef struct {
    mp_int_t f0;
    mp_int_t f1;
} rtuple_int_int_t;
```

Now our loop becomes:

```c
mp_int_t total = 0;
mp_int_t i = 0;
while (i < n) {
    rtuple_int_int_t point = {i, i * 2};  // Stack allocation, no heap!
    total += point.f0 + point.f1;         // Direct field access, no function calls!
    i += 1;
}
```

The transformation is dramatic:
- **Zero heap allocations** (struct lives on stack)
- **Zero function calls** for element access
- **Zero boxing/unboxing** (native integers throughout)

## Implementation: Type-Driven Code Generation

### Step 1: Parsing RTuple Annotations

When the compiler encounters a type annotation like `tuple[int, int, int]`, it creates an `RTuple` IR node:

```python
@dataclass(frozen=True)
class RTuple:
    element_types: tuple[CType, ...]
    
    @classmethod
    def from_annotation(cls, node: ast.Subscript) -> RTuple | None:
        if not (isinstance(node.value, ast.Name) and node.value.id == "tuple"):
            return None
        
        # Extract element types: tuple[int, float, bool] -> (MP_INT_T, MP_FLOAT_T, BOOL)
        element_types = []
        if isinstance(node.slice, ast.Tuple):
            for elt in node.slice.elts:
                if isinstance(elt, ast.Name):
                    element_types.append(CType.from_python_type(elt.id))
        
        return cls(tuple(element_types)) if element_types else None
```

### Step 2: Generating Struct Typedefs

Each unique RTuple signature generates a C struct typedef:

```python
def get_c_struct_typedef(self) -> str:
    type_suffix = "_".join(ct.to_type_suffix() for ct in self.element_types)
    struct_name = f"rtuple_{type_suffix}_t"
    
    fields = []
    for i, ct in enumerate(self.element_types):
        fields.append(f"    {ct.to_c_type_str()} f{i};")
    
    return f"typedef struct {{\n" + "\n".join(fields) + f"\n}} {struct_name};"
```

This produces:
```c
typedef struct {
    mp_int_t f0;
    mp_int_t f1;
    mp_int_t f2;
} rtuple_int_int_int_t;
```

### Step 3: Translating Tuple Literals

When we see `point: tuple[int, int] = (10, 20)`, we generate a struct initializer:

```python
def _translate_rtuple_init(self, value: ast.Tuple, rtuple: RTuple) -> str:
    field_values = []
    for elt, expected_type in zip(value.elts, rtuple.element_types):
        expr, expr_type = self._translate_expr(elt)
        # Coerce types if needed
        if expected_type == CType.MP_INT_T and expr_type == "mp_obj_t":
            expr = f"mp_obj_get_int({expr})"
        field_values.append(expr)
    
    return "{" + ", ".join(field_values) + "}"
```

Output:
```c
rtuple_int_int_t point = {10, 20};
```

### Step 4: Direct Field Access

The magic happens when we translate subscript operations. Instead of calling `mp_obj_subscr()`, we emit direct field access:

```python
def _translate_subscript(self, expr: ast.Subscript) -> tuple[str, str]:
    var_name = expr.value.id
    if var_name in self._rtuple_types:
        rtuple = self._rtuple_types[var_name]
        idx = expr.slice.value  # Constant index like 0, 1, 2
        
        if 0 <= idx < rtuple.arity:
            element_type = rtuple.element_types[idx]
            return f"{var_name}.f{idx}", element_type.to_c_type_str()
    
    # Fall back to generic subscript
    return f"mp_obj_subscr(...)", "mp_obj_t"
```

So `point[0] + point[1]` becomes `point.f0 + point.f1`.

### Step 5: Boxing on Return

When returning an RTuple to Python code, we must box it back into an `mp_obj_t` tuple:

```python
def _box_rtuple(self, var_name: str, rtuple: RTuple) -> str:
    field_boxes = []
    for i, ct in enumerate(rtuple.element_types):
        field_access = f"{var_name}.f{i}"
        if ct == CType.MP_INT_T:
            field_boxes.append(f"mp_obj_new_int({field_access})")
        elif ct == CType.MP_FLOAT_T:
            field_boxes.append(f"mp_obj_new_float({field_access})")
        elif ct == CType.BOOL:
            field_boxes.append(f"({field_access} ? mp_const_true : mp_const_false)")
    
    items = ", ".join(field_boxes)
    return f"mp_obj_new_tuple({rtuple.arity}, (mp_obj_t[]){{{items}}})"
```

This ensures that functions returning `tuple[int, int]` still return valid Python tuples.

## The Next Challenge: RTuple from List Elements

RTuple optimization works beautifully when tuples are created from literals. But what about this pattern?

```python
def sum_points(points: list, count: int) -> int:
    total: int = 0
    i: int = 0
    while i < count:
        p: tuple[int, int, int] = points[i]  # RTuple from list element!
        total += p[0] + p[1] + p[2]
        i += 1
    return total
```

Here, `points[i]` returns an `mp_obj_t`, but we want to store it in an RTuple struct. We need to "unbox" the tuple.

### Initial Implementation: mp_obj_subscr()

The first implementation used `mp_obj_subscr()` to extract each element:

```c
mp_obj_t _tmp1 = mp_list_get_int(points, i);
rtuple_int_int_int_t p;
p.f0 = mp_obj_get_int(mp_obj_subscr(_tmp1, MP_OBJ_NEW_SMALL_INT(0), MP_OBJ_SENTINEL));
p.f1 = mp_obj_get_int(mp_obj_subscr(_tmp1, MP_OBJ_NEW_SMALL_INT(1), MP_OBJ_SENTINEL));
p.f2 = mp_obj_get_int(mp_obj_subscr(_tmp1, MP_OBJ_NEW_SMALL_INT(2), MP_OBJ_SENTINEL));
```

This achieves a **3x speedup**, but each `mp_obj_subscr()` call involves:
- Type checking the object
- Method dispatch to find the subscript handler
- Creating a small int for the index
- Bounds checking

### Optimized Implementation: Direct items[] Access

MicroPython's tuple structure provides direct array access:

```c
typedef struct _mp_obj_tuple_t {
    mp_obj_base_t base;
    size_t len;
    mp_obj_t items[];  // Flexible array member - direct access!
} mp_obj_tuple_t;
```

We can cast and access elements directly:

```c
mp_obj_t _tmp1 = mp_list_get_int(points, i);
mp_obj_tuple_t *_tup1 = (mp_obj_tuple_t *)MP_OBJ_TO_PTR(_tmp1);
rtuple_int_int_int_t p;
p.f0 = mp_obj_get_int(_tup1->items[0]);
p.f1 = mp_obj_get_int(_tup1->items[1]);
p.f2 = mp_obj_get_int(_tup1->items[2]);
```

This reduces function calls from 2N+1 to N+1 for an N-element tuple (one `mp_obj_get_int()` per element, plus the initial list access).

## Bonus: List Access Optimization

While implementing RTuple, we also optimized list access for typed list variables. When the compiler knows a variable is a list (via annotation or parameter type), it can bypass the generic `mp_obj_subscr()` dispatch.

```c
// Generic list access (slow)
mp_obj_subscr(list, MP_OBJ_NEW_SMALL_INT(i), MP_OBJ_SENTINEL);

// Optimized list access (fast)
static inline mp_obj_t mp_list_get_int(mp_obj_t list, mp_int_t index) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);
    if (index < 0) {
        index += self->len;
    }
    return self->items[index];
}
```

This skips:
- Type checking (we know it's a list)
- Method dispatch (direct array access)
- Small int tagging for the index

Similarly, `len(lst)` on a known list becomes a direct field read:

```c
static inline size_t mp_list_len_fast(mp_obj_t list) {
    return ((mp_obj_list_t *)MP_OBJ_TO_PTR(list))->len;
}
```

## Benchmark Results (ESP32-C6)

### Direct items[] Access Optimization

The direct `items[]` access optimization provides a significant improvement over `mp_obj_subscr()`:

| Version | list[tuple] x500 (us) | vs Python | Improvement |
|---------|----------------------|-----------|-------------|
| Before (mp_obj_subscr) | 146,605 | 2.83x | - |
| After (direct items[]) | 61,669 | 6.72x | **2.38x faster** |

### Full Benchmark Suite

| Benchmark | Native (us) | Python (us) | Speedup |
|-----------|-------------|-------------|---------|
| rtuple_internal x100 | 18,429 | 866,774 | **47.0x** |
| list[tuple] x500 | 61,669 | 414,369 | **6.7x** |
| sum_list x1000 | 49,557 | 246,492 | 5.0x |
| Point class x10000 | 145,605 | 384,798 | 2.6x |

The **rtuple_internal** benchmark shows the full potential: **47x faster** when tuples are created and accessed internally without crossing the Python boundary.

The **list[tuple]** benchmark demonstrates the direct `items[]` access optimization: **6.7x speedup** for extracting RTuples from list elements - more than double the initial 2.83x speedup with `mp_obj_subscr()`.

## Key Takeaways

1. **Type annotations enable optimization**: `tuple[int, int]` tells the compiler exactly how to represent data in C.

2. **Stack vs heap matters**: RTuple structs live on the stack, eliminating allocation overhead in hot loops.

3. **Direct field access beats function calls**: `point.f0` is orders of magnitude faster than `mp_obj_subscr(point, 0, ...)`.

4. **Direct struct access beats method dispatch**: `tup->items[0]` is faster than `mp_obj_subscr(tup, 0, ...)`.

5. **Boxing is expensive**: The 47x vs 6.7x speedup difference shows how much boxing/unboxing costs.

6. **Gradual optimization works**: Even partial optimization (optimized access after unboxing) provides meaningful speedups.

## What's Next

Future optimizations could include:
- **RTuple parameters**: Unbox tuple parameters into RTuple structs at function entry
- **RTuple in lists**: Track `list[tuple[int, int]]` to optimize iteration
- **Escape analysis**: Skip boxing for tuples that never leave the function

The RTuple optimization demonstrates a key principle of ahead-of-time compilation: when you know types at compile time, you can make decisions that are impossible at runtime. For embedded systems where every microsecond counts, these optimizations transform Python from "too slow" to "fast enough."
