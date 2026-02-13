# Low-Level Implementation Documentation

This directory contains deep technical documentation about how Python constructs are mapped to C code in the MicroPython runtime.

## Document Index

| Document | Description |
|----------|-------------|
| [01-type-mapping.md](01-type-mapping.md) | How Python types map to C types, boxing/unboxing, small int optimization |
| [02-memory-layout.md](02-memory-layout.md) | Object structures in memory, heap allocation, GC considerations |
| [03-list-internals.md](03-list-internals.md) | How unbounded Python lists work in C with dynamic arrays |
| [04-function-calling.md](04-function-calling.md) | Function signatures, argument passing, return value boxing |
| [05-iteration-protocols.md](05-iteration-protocols.md) | Iterator protocol, for loop optimization, range() internals |

## Key Concepts

### The Boxing Problem

Python is dynamically typed - any variable can hold any type. C is statically typed. The bridge is **boxing**: wrapping values in objects.

```
Python: x = 42          →  C: mp_obj_t x = mp_obj_new_int(42);
Python: y = x + 1       →  C: mp_int_t val = mp_obj_get_int(x);
                               mp_obj_t y = mp_obj_new_int(val + 1);
```

### Why mypyc Compilation is Fast

The key insight: **eliminate boxing inside loops**.

```python
# Interpreted: boxes/unboxes every iteration
for i in range(1000):
    total += i  # Box i, unbox total, add, box result

# mypyc-compiled: boxes only at boundaries
mp_int_t total = 0;
for (mp_int_t i = 0; i < 1000; i++) {
    total += i;  # Pure C arithmetic
}
return mp_obj_new_int(total);  # Box once at end
```

This gives **10-30x speedups** on typical code.

### Memory Efficiency

MicroPython is designed for embedded systems with limited RAM:

- **Small int optimization**: Integers -2^30 to 2^30 stored in pointer, no allocation
- **String interning**: Common strings stored once
- **Geometric list growth**: 1.5x factor balances memory vs reallocation
- **Mark-and-sweep GC**: No reference counting overhead

## Reading Order

For understanding the compilation pipeline:

1. **[01-type-mapping.md](01-type-mapping.md)** - Foundation: how types work
2. **[02-memory-layout.md](02-memory-layout.md)** - How objects live in RAM
3. **[04-function-calling.md](04-function-calling.md)** - Function boundaries
4. **[05-iteration-protocols.md](05-iteration-protocols.md)** - Loop optimization
5. **[03-list-internals.md](03-list-internals.md)** - Complex data structure deep dive

## Quick Reference

### Common Type Mappings

| Python | C Type | Boxing | Unboxing |
|--------|--------|--------|----------|
| `int` | `mp_int_t` | `mp_obj_new_int(v)` | `mp_obj_get_int(o)` |
| `float` | `mp_float_t` | `mp_obj_new_float(v)` | `mp_obj_get_float(o)` |
| `bool` | `bool` | `v ? mp_const_true : mp_const_false` | `mp_obj_is_true(o)` |
| `str` | `const char*` | `mp_obj_new_str(s, len)` | `mp_obj_str_get_str(o)` |
| `list` | `mp_obj_t` | already boxed | `MP_OBJ_TO_PTR(o)` |
| `None` | `mp_obj_t` | `mp_const_none` | - |

### Common Operations

```c
// List operations
mp_obj_t lst = mp_obj_new_list(0, NULL);           // []
mp_obj_list_append(lst, item);                      // lst.append(item)
mp_obj_t item = mp_obj_subscr(lst, idx, MP_OBJ_SENTINEL);  // lst[idx]
mp_obj_subscr(lst, idx, value);                     // lst[idx] = value
size_t len = mp_obj_get_int(mp_obj_len(lst));      // len(lst)

// Type checking
bool is_int = mp_obj_is_int(obj);
bool is_list = mp_obj_is_type(obj, &mp_type_list);
const mp_obj_type_t *type = mp_obj_get_type(obj);
```

## See Also

- [../01-architecture.md](../01-architecture.md) - High-level architecture overview
- [../03-micropython-c-api.md](../03-micropython-c-api.md) - MicroPython C API reference
- [MicroPython source](https://github.com/micropython/micropython) - The definitive reference
