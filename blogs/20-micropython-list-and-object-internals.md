# MicroPython List and Object Internals: Why Python Containers Are Slow and How Compilation Helps

*MicroPython makes Python fit in kilobytes, but the object model makes containers and attributes costlier
than they look.*

---

When you write `points[0].x` in Python, it seems simple. But underneath, MicroPython performs roughly
13 pointer dereferences, a hash table lookup, and multiple function calls, while the same operation in
C or Java takes 1 to 3 memory loads. This post dissects exactly where that overhead comes from,
byte by byte.

## Table of Contents

1. [Runtime Internals](#part-1-runtime-internals) -- How MicroPython represents lists and objects
2. [C Background](#part-2-c-background-for-python-developers) -- Tagged pointers, structs, hash tables
3. [What the Compiler Does](#part-3-what-the-compiler-does-about-it) -- Which layers compilation cuts

---

# Part 1: Runtime Internals

MicroPython is a C program that implements Python. That sounds obvious, but it hides the key idea:
every Python value has to fit into a single C type (`mp_obj_t`), and every dynamic operation has to be
recovered from that one word.

This part shows the exact object layouts and the exact C code paths MicroPython takes.

---

## 1) `mp_obj_t` and the tagged pointer scheme

In MicroPython, the universal value type is `mp_obj_t`. For the common object representation (REPR_A),
it is literally a pointer-sized value.

From `deps/micropython/py/obj.h`:

```c
// This is the definition of the opaque MicroPython object type.
// All concrete objects have an encoding within this type and the
// particular encoding is specified by MICROPY_OBJ_REPR.
#if MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_D
typedef uint64_t mp_obj_t;
typedef uint64_t mp_const_obj_t;
#else
typedef void *mp_obj_t;
typedef const void *mp_const_obj_t;
#endif

// These macros/inline functions operate on objects and depend on the
// particular object representation.  They are used to query, pack and
// unpack small ints, qstrs and full object pointers.

#if MICROPY_OBJ_REPR == MICROPY_OBJ_REPR_A

static inline bool mp_obj_is_small_int(mp_const_obj_t o) {
    return (((mp_int_t)(o)) & 1) != 0;
}
#define MP_OBJ_SMALL_INT_VALUE(o) (((mp_int_t)(o)) >> 1)
#define MP_OBJ_NEW_SMALL_INT(small_int) ((mp_obj_t)((((mp_uint_t)(small_int)) << 1) | 1))

static inline bool mp_obj_is_qstr(mp_const_obj_t o) {
    return (((mp_int_t)(o)) & 7) == 2;
}
#define MP_OBJ_QSTR_VALUE(o) (((mp_uint_t)(o)) >> 3)
#define MP_OBJ_NEW_QSTR(qst) ((mp_obj_t)((((mp_uint_t)(qst)) << 3) | 2))

static inline bool mp_obj_is_immediate_obj(mp_const_obj_t o) {
    return (((mp_int_t)(o)) & 7) == 6;
}
#define MP_OBJ_IMMEDIATE_OBJ_VALUE(o) (((mp_uint_t)(o)) >> 3)
#define MP_OBJ_NEW_IMMEDIATE_OBJ(val) ((mp_obj_t)(((val) << 3) | 6))

static inline bool mp_obj_is_obj(mp_const_obj_t o) {
    return (((mp_int_t)(o)) & 3) == 0;
}
```

That encoding is why `mp_obj_t` can store:

- Small ints without allocation: `MP_OBJ_NEW_SMALL_INT(small_int)` does `((small_int << 1) | 1)`.
- QSTRs (interned strings) without allocation: `MP_OBJ_NEW_QSTR(qst)` does `((qst << 3) | 2)`.
- Immediate constants (like `None`, `True`, `False`) without allocation.
- Heap objects as real pointers, identified by low bits being zero.

For REPR_A, you can think of the low bits as a type tag:

```
xxxx...xxx1  -> small int (value >> 1)
xxxx...x010  -> qstr (interned string)
xxxx...x110  -> immediate (None, True, False)
xxxx...xx00  -> pointer to heap object
```

The last line matters for everything else in this post. If the bottom bits are `00`, MicroPython can
treat the `mp_obj_t` as a pointer to a C struct whose first field is an `mp_obj_base_t`, which begins
with a pointer to the type object.

---

## 2) Lists: `mp_obj_list_t` and why a tiny list is not tiny

MicroPython's list object is a heap struct that points at a separate heap array of `mp_obj_t` items.
The definition comes straight from `deps/micropython/py/objlist.h`:

```c
typedef struct _mp_obj_list_t {
    mp_obj_base_t base;
    size_t alloc;
    size_t len;
    mp_obj_t *items;
} mp_obj_list_t;
```

Two important details are in the implementation, not in the struct.

From `deps/micropython/py/objlist.c`:

```c
// TODO: Move to mpconfig.h
#define LIST_MIN_ALLOC 4

mp_obj_t mp_obj_list_append(mp_obj_t self_in, mp_obj_t arg) {
    mp_check_self(mp_obj_is_type(self_in, &mp_type_list));
    mp_obj_list_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->len >= self->alloc) {
        self->items = m_renew(mp_obj_t, self->items, self->alloc, self->alloc * 2);
        self->alloc *= 2;
        mp_seq_clear(self->items, self->len + 1, self->alloc, sizeof(*self->items));
    }
    self->items[self->len++] = arg;
    return mp_const_none; // return None, as per CPython
}
```

- `LIST_MIN_ALLOC` is 4, so even `[]` grows into at least 4 slots.
- Append grows by doubling: `self->alloc *= 2`.

### Memory diagram: list `[1, 2, 3]` on a 32-bit build

Assume 32-bit pointers and 32-bit `size_t`, so each field is 4 bytes.

```
Heap object: mp_obj_list_t (16 bytes)

  +0x00  base.type  -> &mp_type_list
  +0x04  alloc      -> 4
  +0x08  len        -> 3
  +0x0C  items      -> 0x2000

Separate heap allocation: items array (min 4 slots, 16 bytes)

  0x2000  items[0]  -> MP_OBJ_NEW_SMALL_INT(1)  ( ...0001 )
  0x2004  items[1]  -> MP_OBJ_NEW_SMALL_INT(2)  ( ...0011 )
  0x2008  items[2]  -> MP_OBJ_NEW_SMALL_INT(3)  ( ...0101 )
  0x200C  items[3]  -> MP_OBJ_NULL (empty slot)
```

Total footprint for three small integers:

- 16 bytes for `mp_obj_list_t`
- 16 bytes for the minimum items array (4 slots)
- Total: 32 bytes

In C, an `int32_t[3]` is 12 bytes. MicroPython spends more because it stores a dynamic, uniform
`mp_obj_t` array, plus capacity, plus a type pointer for runtime dispatch.

---

## 3) Instances: `mp_obj_instance_t` and the hidden hash table

A user-defined class instance is not a C struct with fixed field offsets. It is a heap object that
contains a hash table of attributes.

From `deps/micropython/py/objtype.h`:

```c
typedef struct _mp_obj_instance_t {
    mp_obj_base_t base;
    mp_map_t members;
    mp_obj_t subobj[];
    // TODO maybe cache __getattr__ and __setattr__ for efficient lookup of them
} mp_obj_instance_t;
```

And the map types come from `deps/micropython/py/obj.h`:

```c
typedef struct _mp_map_elem_t {
    mp_obj_t key;
    mp_obj_t value;
} mp_map_elem_t;

typedef struct _mp_map_t {
    size_t all_keys_are_qstrs : 1;
    size_t is_fixed : 1;    // if set, table is fixed/read-only and can't be modified
    size_t is_ordered : 1;  // if set, table is an ordered array, not a hash map
    size_t used : (8 * sizeof(size_t) - 3);
    size_t alloc;
    mp_map_elem_t *table;
} mp_map_t;
```

On a 32-bit build, `(8 * sizeof(size_t) - 3)` is 29, so `used` is a 29-bit counter packed into the
first word with three flags.

### Memory diagram: `Point(x=1, y=2)` as an interpreted MicroPython instance

Assume a simple Python class where the instance has just `x` and `y` set, and no native bases.

```
Heap object: mp_obj_instance_t (16 bytes on 32-bit)

  +0x00  base.type          -> &Point_type
  +0x04  members.flags+used  (bitfields packed into size_t)
  +0x08  members.alloc      -> 4
  +0x0C  members.table      -> 0x3000
  +0x10  subobj[]           (empty for pure Python class)

Separate heap allocation: members.table (hash table, alloc slots)

  0x3000  table[0]  { key = MP_OBJ_NEW_QSTR(MP_QSTR_x), value = MP_OBJ_NEW_SMALL_INT(1) }
  0x3008  table[1]  { key = MP_OBJ_NULL,              value = ... }
  0x3010  table[2]  { key = MP_OBJ_NEW_QSTR(MP_QSTR_y), value = MP_OBJ_NEW_SMALL_INT(2) }
  0x3018  table[3]  { key = MP_OBJ_NULL,              value = ... }
```

Each `mp_map_elem_t` is 8 bytes (two `mp_obj_t` words). The hash table also needs empty slots for
probing. With an allocation of 4 slots, the rough total is:

- 16 bytes for `mp_obj_instance_t`
- 32 bytes for the `mp_map_elem_t[4]` table
- Total: about 48 bytes for two integers

In C, `struct { int32_t x; int32_t y; }` is 8 bytes.

---

## 4) Attribute lookup: not a vtable, a hash table

`p.x` in interpreted MicroPython is a map lookup on `p`'s `members`, and if that fails, a class
hierarchy search.

The instance fast path is in `deps/micropython/py/objtype.c`:

```c
static void mp_obj_instance_load_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    // logic: look in instance members then class locals
    assert(mp_obj_is_instance_type(mp_obj_get_type(self_in)));
    mp_obj_instance_t *self = MP_OBJ_TO_PTR(self_in);

    // Note: This is fast-path'ed in the VM for the MP_BC_LOAD_ATTR operation.
    mp_map_elem_t *elem = mp_map_lookup(&self->members, MP_OBJ_NEW_QSTR(attr), MP_MAP_LOOKUP);
    if (elem != NULL) {
        // object member, always treated as a value
        dest[0] = elem->value;
        return;
    }
    #if MICROPY_CPYTHON_COMPAT
    if (attr == MP_QSTR___dict__) {
        // Create a new dict with a copy of the instance's map items.
        // This creates, unlike CPython, a read-only __dict__ that can't be modified.
        mp_obj_dict_t dict;
        dict.base.type = &mp_type_dict;
        dict.map = self->members;
        dest[0] = mp_obj_dict_copy(MP_OBJ_FROM_PTR(&dict));
        mp_obj_dict_t *dest_dict = MP_OBJ_TO_PTR(dest[0]);
        dest_dict->map.is_fixed = 1;
        return;
    }
    #endif
    struct class_lookup_data lookup = {
        .obj = self,
        .attr = attr,
        .slot_offset = 0,
        .dest = dest,
        .is_type = false,
    };
    mp_obj_class_lookup(&lookup, self->base.type);
    mp_obj_t member = dest[0];
    if (member != MP_OBJ_NULL) {
        if (!(self->base.type->flags & MP_TYPE_FLAG_HAS_SPECIAL_ACCESSORS)) {
            // Class doesn't have any special accessors to check so return straight away
            return;
        }
```

If the attribute isn't on the instance, MicroPython searches the class dictionary (`locals_dict`).
From `deps/micropython/py/objtype.c`:

```c
mp_map_t *locals_map = &MP_OBJ_TYPE_GET_SLOT(type, locals_dict)->map;
mp_map_elem_t *elem = mp_map_lookup(locals_map, MP_OBJ_NEW_QSTR(lookup->attr), MP_MAP_LOOKUP);
```

If that still fails, `mp_obj_class_lookup()` keeps searching base classes.

The heavy lifting inside that first line, `mp_map_lookup(...)`, is a real hash-table lookup.
From `deps/micropython/py/map.c`:

```c
// get hash of index, with fast path for common case of qstr
mp_uint_t hash;
if (mp_obj_is_qstr(index)) {
    hash = qstr_hash(MP_OBJ_QSTR_VALUE(index));
} else {
    hash = MP_OBJ_SMALL_INT_VALUE(mp_unary_op(MP_UNARY_OP_HASH, index));
}

size_t pos = hash % map->alloc;
size_t start_pos = pos;
mp_map_elem_t *avail_slot = NULL;
for (;;) {
    mp_map_elem_t *slot = &map->table[pos];
    if (slot->key == MP_OBJ_NULL) {
        // found NULL slot, so index is not in table
        if (lookup_kind == MP_MAP_LOOKUP_ADD_IF_NOT_FOUND) {
            map->used += 1;
            if (avail_slot == NULL) {
                avail_slot = slot;
            }
            avail_slot->key = index;
            avail_slot->value = MP_OBJ_NULL;
            if (!mp_obj_is_qstr(index)) {
                map->all_keys_are_qstrs = 0;
            }
            return avail_slot;
        } else {
            return NULL;
        }
    } else if (slot->key == MP_OBJ_SENTINEL) {
        // found deleted slot, remember for later
        if (avail_slot == NULL) {
            avail_slot = slot;
        }
    } else if (slot->key == index || (!compare_only_ptrs && mp_obj_equal(slot->key, index))) {
        // found index
        // Note: CPython does not replace the index; try x={True:'true'};x[1]='one';x
        if (lookup_kind == MP_MAP_LOOKUP_REMOVE_IF_FOUND) {
            // delete element in this slot
            map->used--;
            if (map->table[(pos + 1) % map->alloc].key == MP_OBJ_NULL) {
                // optimisation if next slot is empty
                slot->key = MP_OBJ_NULL;
            } else {
                slot->key = MP_OBJ_SENTINEL;
            }
            // keep slot->value so that caller can access it if needed
        }
        MAP_CACHE_SET(index, pos);
        return slot;
    }

    // not yet found, keep searching in this table
    pos = (pos + 1) % map->alloc;
```

This is why attribute access in Python is hard to make cheap.

- Every instance can add attributes at runtime: `obj.z = 99`.
- Every instance can delete attributes: `del obj.x`.
- A class can override lookup with descriptors and `__getattr__`.

MicroPython has to support that model, so it uses a hash table.

---

## 5) Comparison with Java: fixed offsets and one load

Java objects are dynamic in many ways, but field layout is fixed once the class is loaded. A `Point`
instance in Java has fields at known offsets, and the JIT can emit a single load.

- Java `Point`: 24 bytes (12-byte header + 8 bytes for x,y + 4 padding)
- Fields at fixed offsets known at class load time: x at offset 12, y at offset 16
- JIT emits: `mov eax, [rdx+12]`

Python cannot do that with a normal instance because the set of attributes is not fixed. MicroPython
leans into correctness, then relies on other techniques (like compilation) to regain speed.

### Memory and load-count comparison

| Component | C struct | Java | MicroPython (interpreted) | mypyc-micropython (compiled) |
|---|---|---|---|---|
| Point(1, 2) | 8 B | 24 B | ~48 B | 16 B |
| list of 3 Points | 24 B | 124 B | ~176 B | ~80 B |
| `points[0].x` loads | 1 | 3 | ~13 | 2 |

---

# Part 2: C Background for Python Developers

If you have written a lot of Python, the performance story above can feel mysterious. In C, these are
the core mechanics that explain it.

---

## 1) Tagged pointers: bit tricks to dodge allocations

Allocating a heap object for every `1`, `2`, `3` would be too expensive. Tagged pointers store small
values in the pointer itself.

MicroPython REPR_A uses the low bits as tags:

- Small int: `(value << 1) | 1`
- QSTR: `(qst << 3) | 2`
- Immediate: `(val << 3) | 6`
- Heap object: pointer aligned so low bits are `00`

Tagged pointers are a trade:

- Fast and allocation-free for common cases.
- Every operation starts with bit tests and branches to decide which case it is.

---

## 2) Hash tables vs fixed-offset structs

When you write `p.x` in C for `struct Point { int x; int y; };`, the compiler knows the layout:

- `x` is at offset 0
- `y` is at offset 4

Access is just: `*(base + offset)`.

A hash table lookup is not that.

- Compute a hash
- Reduce it to a slot index (`hash % alloc`)
- Probe until you find the key or an empty slot
- Compare keys (pointer compare for QSTRs, full equality for others)
- Load the value

That is a lot of work for a property access.

---

## 3) Indirect function calls vs direct calls

MicroPython also has a different kind of indirection: type operations are dispatched through a type's
slot table.

Slot access uses these macros from `deps/micropython/py/obj.h`:

```c
#define MP_OBJ_TYPE_HAS_SLOT(t, f) ((t)->slot_index_##f)
#define MP_OBJ_TYPE_GET_SLOT(t, f) (_MP_OBJ_TYPE_SLOT_TYPE_##f(t)->slots[(t)->slot_index_##f - 1])
```

And a subscripting operation goes through that slot dispatch. From `deps/micropython/py/obj.c`:

```c
mp_obj_t mp_obj_subscr(mp_obj_t base, mp_obj_t index, mp_obj_t value) {
    const mp_obj_type_t *type = mp_obj_get_type(base);
    if (MP_OBJ_TYPE_HAS_SLOT(type, subscr)) {
        mp_obj_t ret = MP_OBJ_TYPE_GET_SLOT(type, subscr)(base, index, value);
        if (ret != MP_OBJ_NULL) {
            return ret;
        }
        // TODO: call base classes here?
    }
    if (value == MP_OBJ_NULL) {
        #if MICROPY_ERROR_REPORTING <= MICROPY_ERROR_REPORTING_TERSE
        mp_raise_TypeError(MP_ERROR_TEXT("object doesn't support item deletion"));
        #else
        mp_raise_msg_varg(&mp_type_TypeError,
            MP_ERROR_TEXT("'%s' object doesn't support item deletion"), mp_obj_get_type_str(base));
        #endif
    } else if (value == MP_OBJ_SENTINEL) {
        #if MICROPY_ERROR_REPORTING <= MICROPY_ERROR_REPORTING_TERSE
        mp_raise_TypeError(MP_ERROR_TEXT("object isn't subscriptable"));
        #else
        mp_raise_msg_varg(&mp_type_TypeError,
            MP_ERROR_TEXT("'%s' object isn't subscriptable"), mp_obj_get_type_str(base));
        #endif
    } else {
        #if MICROPY_ERROR_REPORTING <= MICROPY_ERROR_REPORTING_TERSE
        mp_raise_TypeError(MP_ERROR_TEXT("object doesn't support item assignment"));
        #else
        mp_raise_msg_varg(&mp_type_TypeError,
            MP_ERROR_TEXT("'%s' object doesn't support item assignment"), mp_obj_get_type_str(base));
        #endif
    }
}
```

So `lst[i]` is not a direct indexing operation. It is:

- Determine the type of `lst`.
- Fetch the `subscr` slot function pointer.
- Call it.

In compiled C code where you already know you have a list, you can often call a list helper directly.
That doesn't change semantics, it just skips the generic dispatch.

---

## 4) Bytecode interpreter overhead: the dispatch loop

Even after you pay for objects, tags, maps, and slots, the interpreter adds one more layer: every
operation is driven by a bytecode loop.

From `deps/micropython/py/vm.c`:

```c
#if MICROPY_OPT_COMPUTED_GOTO
    #include "py/vmentrytable.h"
    #define DISPATCH() do { \
        TRACE(ip); \
        MARK_EXC_IP_GLOBAL(); \
        TRACE_TICK(ip, sp, false); \
        goto *entry_table[*ip++]; \
    } while (0)
```

Every bytecode op does:

- Fetch an opcode byte (`*ip++`)
- Dispatch to its handler (`goto *entry_table[...]`)
- Run a chunk of C that manipulates `mp_obj_t` values
- Return to the dispatch loop

That dispatch cost is small per operation, but Python programs do a lot of operations.

---

# Part 3: What the Compiler Does About It

`mypyc-micropython` takes typed Python and emits C. That doesn't magically remove all overhead,
because the result still runs inside MicroPython's runtime. But it can remove several layers:

- It removes the bytecode dispatch loop by emitting straight-line C.
- It replaces generic, dynamic calls with type-specialized helpers.
- For typed classes, it can replace hash table attribute lookup with fixed-offset loads.

The best way to see the difference is side by side: Python input, IR, generated C.

---

## 1) Lists: compiled `sum_list`

**Python input:**

```python
def sum_list(lst: list[int]) -> int:
    total: int = 0
    n: int = len(lst)
    for i in range(n):
        total += lst[i]
    return total
```

**IR representation:**

```
def sum_list(lst: MP_OBJ_T) -> MP_INT_T:
  c_name: list_operations_sum_list
  max_temp: 0
  locals: {lst: MP_OBJ_T, total: MP_INT_T, n: MP_INT_T, i: MP_INT_T}
  body:
    total: mp_int_t = 0
    n: mp_int_t = len(lst)
    for i in range(0, n, 1):
      total += lst[i]
    return total
```

**Generated C:**

```c
static mp_obj_t example_sum_list(mp_obj_t lst_obj) {
    mp_obj_t lst = lst_obj;
    mp_int_t total = 0;
    mp_int_t n = mp_list_len_fast(lst);
    mp_int_t i;
    mp_int_t _tmp1 = n;
    for (i = 0; i < _tmp1; i++) {
        total += mp_obj_get_int(mp_list_get_int(lst, i));
    }
    return mp_obj_new_int(total);
}
```

**What's eliminated:**

- Bytecode dispatch loop (eliminated, this is a native C `for` loop)
- Iterator object allocation (eliminated, `range()` becomes a counter)
- Boxing of the loop variable (eliminated, `i` is an `mp_int_t`)
- Generic `mp_obj_subscr` dispatch (replaced with `mp_list_get_int`)

**What remains:**

- Bounds checking (still needed)
- Unboxing list elements (`mp_obj_get_int`)
- Boxing the return (`mp_obj_new_int`)

---

## 2) List building: compiled `build_squares`

**Python input:**

```python
def build_squares(n: int) -> list[int]:
    result: list[int] = []
    for i in range(n):
        result.append(i * i)
    return result
```

**IR representation:**

```
def build_squares(n: MP_INT_T) -> MP_OBJ_T:
  c_name: list_operations_build_squares
  max_temp: 1
  locals: {n: MP_INT_T, result: MP_OBJ_T, i: MP_INT_T}
  body:
    result: mp_obj_t = []
    for i in range(0, n, 1):
      # prelude:
        _tmp1 = result.append((i * i))
      _tmp1
    return result
```

**Generated C:**

```c
static mp_obj_t example_build_squares(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);
    mp_obj_t result = mp_obj_new_list(0, NULL);
    mp_int_t i;
    mp_int_t _tmp2 = n;
    for (i = 0; i < _tmp2; i++) {
        mp_obj_t _tmp1 = mp_obj_list_append(result, mp_obj_new_int((i * i)));
        (void)_tmp1;
    }
    return result;
}
```

The big win is the same: there is no bytecode loop, and the loop counter stays unboxed.

---

## 3) Classes: the biggest win, fixed-offset field loads

For a normal interpreted instance, `p.x` is a hash table lookup.

With typed classes, `mypyc-micropython` can generate a C struct with fields at fixed offsets. Then
`p.x` becomes the same kind of operation Java and C do: add a constant offset and load.

**Python input:**

```python
@dataclass
class Point:
    x: int
    y: int

def get_x(p: Point) -> int:
    return p.x

def add_coords(p: Point) -> int:
    return p.x + p.y
```

**IR representation:**

```
def get_x(p: MP_OBJ_T) -> MP_INT_T:
  c_name: class_param_get_x
  max_temp: 0
  locals: {p: MP_OBJ_T}
  body:
    return p.x

def add_coords(p: MP_OBJ_T) -> MP_INT_T:
  c_name: class_param_add_coords
  max_temp: 0
  locals: {p: MP_OBJ_T}
  body:
    return (p.x + p.y)
```

**Generated C:**

```c
// The compiler generates a C STRUCT instead of using mp_obj_instance_t + hash table:
// (This struct is generated by the class emitter, not shown in function output)
// typedef struct {
//     mp_obj_base_t base;
//     mp_int_t x;    // FIXED OFFSET -- no hash table!
//     mp_int_t y;    // FIXED OFFSET -- no hash table!
// } example_Point_obj_t;

static mp_obj_t example_get_x(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;
    return mp_obj_new_int(((example_Point_obj_t *)MP_OBJ_TO_PTR(p))->x);
}

static mp_obj_t example_add_coords(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;
    return mp_obj_new_int(
        (((example_Point_obj_t *)MP_OBJ_TO_PTR(p))->x + 
         ((example_Point_obj_t *)MP_OBJ_TO_PTR(p))->y));
}
```

### The key comparison: interpreted `p.x` vs compiled `p.x`

Interpreted MicroPython `p.x`:

```
mp_load_attr(p, MP_QSTR_x)
-> mp_obj_get_type(p) -> check tagged pointer -> deref base.type
-> mp_obj_instance_attr(p, attr, dest) 
-> mp_obj_instance_load_attr(p, attr, dest)
-> mp_map_lookup(&self->members, QSTR_x, LOOKUP)
  -> check cache -> hash(QSTR_x) -> pos = hash % alloc -> probe table -> compare key -> load value
~13 pointer dereferences, ~50-100 instructions
```

Compiled `mypyc-micropython` `p.x`:

```c
((example_Point_obj_t *)MP_OBJ_TO_PTR(p))->x
// 1. Strip tag bits from p (MP_OBJ_TO_PTR)
// 2. Cast to struct pointer
// 3. Load field at FIXED offset
// ~2 pointer dereferences, ~2-3 instructions
```

This is the Java-like optimization: the field offset is a compile-time constant.

---

## 4) Hash table vs vtable: MicroPython uses both

MicroPython has two different dynamic lookup mechanisms:

- Type operations (`lst[i]`, binary ops, iteration) use a slot table (vtable-like).
- Instance attributes (`self.x`) use an `mp_map_t` hash table.

Compilation helps in two different ways:

- It can skip generic type dispatch by calling a specialized helper directly.
- It can skip hash table attribute lookup by generating a fixed-layout C struct for typed classes.

---

## 5) What compilation eliminates (and what it cannot)

| Overhead Layer | Interpreted MicroPython | Compiled (mypyc-micropython) | Eliminated? |
|---|---|---|---|
| Bytecode dispatch | ~10 cycles/op | 0 | Yes |
| Type dispatch (mp_obj_subscr) | ~5-8 function pointer hops | Direct call | Yes |
| Hash table attribute lookup | hash + probe + compare | Fixed-offset struct access | Yes |
| Iterator object allocation | 16 bytes/loop | Loop counter in register | Yes |
| Boxing loop variables | Tagged pointer manipulation | Native mp_int_t | Yes |
| Bounds checking | Still needed | Still needed | No |
| Boxing at API boundaries | Still needed | Still needed | No |

The takeaway is not that Python is "slow". It's that Python's dynamism costs memory loads, branches,
and indirections. MicroPython keeps the semantics, then compilation uses type information to punch
holes through the layers when it is safe.
