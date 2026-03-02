# Compiled Classes vs Interpreted MicroPython Classes

*What actually changes when `mypyc-micropython` compiles classes: memory layout, attribute access, method dispatch, inheritance, and especially `list[Class]` behavior.*

---

## Table of Contents

1. [Part 1: Runtime Internals](#part-1-runtime-internals)
2. [Part 2: C Background](#part-2-c-background)
3. [Part 3: What The Compiler Does](#part-3-what-the-compiler-does)
4. [Direct Answer: "How are our classes different?"](#direct-answer-how-are-our-classes-different)
5. [Direct Answer: `list[Class]` in both worlds](#direct-answer-listclass-in-both-worlds)
6. [Trade-offs: what you gain and what you lose](#trade-offs-what-you-gain-and-what-you-lose)
7. [Appendix A: Full load-trace for `points[0].x`](#appendix-a-full-load-trace-for-points0x)

---

# Part 1: Runtime Internals

If you read blog 20, you already saw the core idea:

MicroPython has to preserve Python's dynamic object model.

That means instance fields are not fixed offsets.

They are entries in a hash table.

This section focuses on the interpreted baseline first, because that is what our compiler is replacing for typed classes.

## 1.1 `mp_obj_t` is the universal value container

In MicroPython, everything is an `mp_obj_t`.

On REPR_A builds, this is pointer-sized and tag-encoded.

From `deps/micropython/py/obj.h`:

```c
typedef void *mp_obj_t;
typedef const void *mp_const_obj_t;

struct _mp_obj_base_t {
    const mp_obj_type_t *type MICROPY_OBJ_BASE_ALIGNMENT;
};
typedef struct _mp_obj_base_t mp_obj_base_t;
```

So any heap object starts with `mp_obj_base_t`.

That first pointer is how runtime dispatch finds the object's type.

## 1.2 Interpreted class instances are `mp_obj_instance_t`

This is the key struct for normal interpreted Python classes.

From `deps/micropython/py/objtype.h`:

```c
typedef struct _mp_obj_instance_t {
    mp_obj_base_t base;
    mp_map_t members;
    mp_obj_t subobj[];
    // TODO maybe cache __getattr__ and __setattr__ for efficient lookup of them
} mp_obj_instance_t;
```

The important field is `members`.

`members` is the per-instance attribute hash table.

`self.x = 1` is not "write offset +8".

It is effectively "insert key-value into map".

`key = MP_QSTR_x`, `value = MP_OBJ_NEW_SMALL_INT(1)`.

## 1.3 What `mp_map_t` looks like

From `deps/micropython/py/obj.h`:

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

So every interpreted instance carries map metadata and map storage.

This is why a tiny object still has non-trivial overhead.

## 1.4 Memory picture: interpreted `Point(x=1, y=2)`

Assume 32-bit pointers.

Approximate instance memory:

- `mp_obj_instance_t`: around 16 bytes (base + map metadata pointers/fields)
- map table allocation (commonly at least 4 entries): `4 * sizeof(mp_map_elem_t)`
- each `mp_map_elem_t` is 8 bytes on 32-bit (`key`, `value`)

Rough total for just `x` and `y`:

`16 + (4 * 8) = ~48 bytes`

That is the estimate we used in blog 20.

ASCII diagram:

```text
Interpreted Point instance (32-bit rough layout)

mp_obj_instance_t (heap)
+0x00  base.type     -> &Point_type
+0x04  members.flags+used
+0x08  members.alloc -> 4
+0x0C  members.table -> 0x3000

members.table (separate heap allocation)
0x3000  [key=MP_QSTR_x, value=SMALL_INT(1)]
0x3008  [empty or tombstone]
0x3010  [key=MP_QSTR_y, value=SMALL_INT(2)]
0x3018  [empty or tombstone]
```

## 1.5 Interpreted method and attribute dispatch path

For attribute load, interpreted runtime goes through `mp_obj_instance_load_attr`.

From `deps/micropython/py/objtype.c` (core path):

```c
static void mp_obj_instance_load_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    assert(mp_obj_is_instance_type(mp_obj_get_type(self_in)));
    mp_obj_instance_t *self = MP_OBJ_TO_PTR(self_in);

    mp_map_elem_t *elem = mp_map_lookup(&self->members, MP_OBJ_NEW_QSTR(attr), MP_MAP_LOOKUP);
    if (elem != NULL) {
        dest[0] = elem->value;
        return;
    }

    struct class_lookup_data lookup = {
        .obj = self,
        .attr = attr,
        .slot_offset = 0,
        .dest = dest,
        .is_type = false,
    };
    mp_obj_class_lookup(&lookup, self->base.type);
    ...
}
```

Conceptually:

1. Look in instance map (`self->members`)
2. If not found, look in class dict
3. If not found, walk base classes (MRO-like hierarchy walk)
4. Handle descriptors/properties
5. Potentially delegate to `__getattr__`

That gives Python semantics, but it costs lookups and branches.

## 1.6 How interpreted `list[Point]` works

This is your key question.

The list container itself is `mp_obj_list_t` in both cases.

From `deps/micropython/py/objlist.h`:

```c
typedef struct _mp_obj_list_t {
    mp_obj_base_t base;
    size_t alloc;
    size_t len;
    mp_obj_t *items;
} mp_obj_list_t;
```

`items` is an array of `mp_obj_t`.

So list elements are opaque object references.

For interpreted classes:

- each `items[i]` points to an `mp_obj_instance_t`
- that instance owns a `members` hash table
- field access on that item uses hash lookup

ASCII view:

```text
Interpreted MicroPython: list[Point]

mp_obj_list_t
  +-- items[0] -> mp_obj_instance_t { members: {x: 1, y: 2} }  ~48 bytes
  +-- items[1] -> mp_obj_instance_t { members: {x: 3, y: 4} }  ~48 bytes
  +-- items[2] -> mp_obj_instance_t { members: {x: 5, y: 6} }  ~48 bytes
```

For `points[0].x` in interpreted mode:

1. list subscript machinery to fetch `items[0]`
2. attribute load machinery to resolve `x`
3. hash/probe in instance map

Roughly around a dozen loads/branches in the hot path.

We often summarize it as `~13 loads`.

## 1.7 Interpreted memory estimate for three objects in list

For `[Point(1,2), Point(3,4), Point(5,6)]` rough 32-bit estimate:

- list header: 16 bytes
- items array for 3 pointers: 12 bytes
- 3 interpreted Point instances: `3 * 48 = 144 bytes`

Total:

`16 + 12 + 144 = ~172 bytes`

The exact number depends on allocator alignment and table growth state.

But order-of-magnitude is what matters.

---

# Part 2: C Background

Now let us switch to the C model that compiled classes rely on.

This section is short and focused.

Blog 03 already covered vtables deeply.

Here we connect that to this class comparison.

## 2.1 Fixed-layout struct vs hash table map

In C, typed fields usually live at fixed offsets.

Example:

```c
struct Point {
    mp_obj_base_t base;
    mp_int_t x;
    mp_int_t y;
};
```

On 32-bit, this is typically 12 bytes.

On 64-bit host builds it may be 24 bytes because of pointer/int sizes and alignment.

In this blog we use the embedded 32-bit mental model because this project targets ESP32-class boards.

For 32-bit, an equivalent fixed-layout object is commonly discussed as 16 bytes in our compiler examples.

The exact number depends on whether an extra pointer field (for vtable) exists and padding/alignment rules.

The key idea is not exact byte parity.

The key idea is that fields are fixed offsets.

Load `x` means "base + constant".

No key hash.

No probe chain.

No string-key compare.

Hash table, by contrast:

- variable-sized storage
- key hashing
- slot probing
- key match checks
- collisions and tombstones

Big-O average for hash lookup is good.

But constant factors are much bigger than direct offset loads.

## 2.2 Vtables in one minute

From blog 03:

- each class has a static function-pointer table
- object stores pointer to class vtable
- override means child vtable points to child implementation
- inherited methods can reuse parent function pointers (possibly casted for signature compatibility)

Minimal shape:

```c
typedef struct {
    mp_int_t (*get)(Entity_obj_t *self);
    mp_obj_t (*describe)(Entity_obj_t *self);
} Entity_vtable_t;
```

The vtable itself is one static object per class.

Instances do not duplicate method code.

They carry one pointer to shared class-level behavior.

## 2.3 Struct embedding for inheritance

This is the core layout trick our compiler uses.

```c
struct Entity_obj_t {
    mp_obj_base_t base;
    vtable_t *vtable;
    mp_obj_t name;
    mp_int_t _id;
};

struct Sensor_obj_t {
    Entity_obj_t super;
    mp_float_t _value;
    mp_obj_t location;
};
```

Because `super` is first, a `Sensor_obj_t *` can be safely viewed as `Entity_obj_t *` for inherited prefix fields.

That is why this cast works in generated code:

```c
(classes_Entity_obj_t *)self
```

for parent methods.

## 2.4 Why layout matters for speed

If field offsets are known at compile time:

- code generation can emit direct loads/stores
- inheritance depth becomes fixed `super.super...` path
- no runtime field-name lookup is needed

This is exactly where compiled classes diverge from interpreted classes.

---

# Part 3: What The Compiler Does

Now we use real generated code from:

- `examples/classes.py`
- `modules/usermod_classes/classes.c`

This section is the direct class-vs-class comparison.

## 3.1 Python source model (`examples/classes.py`)

The example has:

- `Location` dataclass
- `Entity` base class
- `Sensor(Entity)` child
- `SmartSensor(Sensor)` grandchild

and it exercises:

- fields
- inheritance
- `super()`
- `@property`
- `@staticmethod`
- `@classmethod`
- chained attribute access
- cross-level field access

Small source slice:

```python
class SmartSensor(Sensor):
    threshold: float
    alert_count: int
    active: bool

    def check_value(self) -> bool:
        if self._value > self.threshold:
            self.alert_count += 1
            return True
        return False

    def get_total_score(self) -> int:
        return self._id + self.alert_count
```

## 3.2 IR view (required bridge)

Compiler IR (text format) style for classes:

```text
Class: Entity (c_name: classes_Entity)
  Fields:
    name: str (MP_OBJ_T)
    _id: int (MP_INT_T)
    tags: list (MP_OBJ_T)
  Methods:
    def __init__(name: MP_OBJ_T, eid: MP_INT_T) -> VOID
    @property def id() -> MP_INT_T
    @staticmethod def validate_name(name: MP_OBJ_T) -> BOOL
    def add_tag(tag: MP_INT_T) -> VOID
    def tag_count() -> MP_INT_T
    def has_tag(tag: MP_INT_T) -> BOOL
    def describe() -> MP_OBJ_T

Class: Sensor (c_name: classes_Sensor)
  Base: Entity
  Fields:
    _value: float (MP_FLOAT_T)
    location: Location (MP_OBJ_T)
    readings: dict (MP_OBJ_T)
  Methods:
    def __init__(name: MP_OBJ_T, eid: MP_INT_T, loc: MP_OBJ_T) -> VOID
    @property def value() -> MP_FLOAT_T
    @value.setter def value(v: MP_FLOAT_T) -> VOID
    @classmethod def create(cls: MP_OBJ_T, name: MP_OBJ_T) -> MP_OBJ_T
    def record(ts: MP_INT_T, val: MP_FLOAT_T) -> VOID
    def reading_count() -> MP_INT_T
    def get_reading(ts: MP_INT_T) -> MP_FLOAT_T
    def get_location_x() -> MP_INT_T
    def get_location_y() -> MP_INT_T
    def describe() -> MP_OBJ_T
```

The IR is where inheritance is resolved.

By C emission time, offsets and ownership are known.

## 3.3 Generated C struct hierarchy

From `modules/usermod_classes/classes.c`:

```c
struct _classes_Entity_obj_t {
    mp_obj_base_t base;
    const classes_Entity_vtable_t *vtable;
    mp_obj_t name;
    mp_int_t _id;
    mp_obj_t tags;
};

struct _classes_Sensor_obj_t {
    classes_Entity_obj_t super;
    mp_float_t _value;
    mp_obj_t location;
    mp_obj_t readings;
};

struct _classes_SmartSensor_obj_t {
    classes_Sensor_obj_t super;
    mp_float_t threshold;
    mp_int_t alert_count;
    bool active;
};
```

This already shows the biggest difference from interpreted instances.

No per-instance hash table.

Fields are concrete C members.

## 3.4 Field access comparison: `self._value > self.threshold`

### Interpreted MicroPython

`self._value` and `self.threshold` each require attribute lookup.

That means two map/lookup operations on dynamic objects.

### Compiled (`mypyc-micropython`)

Real generated C:

```c
static bool classes_SmartSensor_check_value_native(classes_SmartSensor_obj_t *self) {
    if ((self->super._value > self->threshold)) {
        self->alert_count += 1;
        return true;
    }
    return false;
}
```

That is two direct memory reads.

Zero hash lookups.

It is exactly the same semantics at Python level.

But a radically different machine-level path.

## 3.5 Cross-level field access: `self._id + self.alert_count`

Python source in grandchild method:

```python
return self._id + self.alert_count
```

Generated C:

```c
static mp_int_t classes_SmartSensor_get_total_score_native(classes_SmartSensor_obj_t *self) {
    return (self->super.super._id + self->alert_count);
}
```

`self->super.super._id` means:

- one level from `SmartSensor` to `Sensor`
- one more level from `Sensor` to `Entity`
- then fixed offset load of `_id`

The compiler resolves this chain at compile time.

There is no runtime parent-field name lookup.

## 3.6 Chained attr access: `self.location.x`

Generated C for `Sensor.get_location_x`:

```c
static mp_int_t classes_Sensor_get_location_x_native(classes_Sensor_obj_t *self) {
    mp_int_t _tmp1 = ((classes_Location_obj_t *)MP_OBJ_TO_PTR(self->location))->x;
    return _tmp1;
}
```

This is two-step, still important:

1. Load `self->location` (an `mp_obj_t` reference field)
2. Convert to typed pointer and load `.x` at fixed offset

Compared to interpreted:

- interpreted `self.location` is hash lookup
- interpreted `.x` on that result is another hash lookup

So compiled path removes two hash lookups in this pattern.

## 3.7 `super()` call chain

Interpreted `super().__init__()`:

- runtime resolves parent descriptor and method target using class hierarchy rules

Compiled constructor chain in generated C:

```c
static mp_obj_t classes_Sensor___init___mp(size_t n_args, const mp_obj_t *args) {
    classes_Sensor_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t name = args[1];
    mp_int_t eid = mp_obj_get_int(args[2]);
    mp_obj_t loc = args[3];
    (void)(classes_Entity___init___mp(MP_OBJ_FROM_PTR(self), name, mp_obj_new_int(eid)), mp_const_none);
    self->_value = 0.0;
    self->location = loc;
    self->readings = mp_obj_new_dict(0);
    return mp_const_none;
}
```

Parent call is explicit and direct.

No runtime MRO search for this call path.

`SmartSensor` does the same to call `Sensor` constructor.

## 3.8 `@property`, `@staticmethod`, `@classmethod`

### Property

Property access is compiled into attr-handler branches.

From generated `classes_Sensor_attr`:

```c
if (attr == MP_QSTR_value) {
    if (dest[0] == MP_OBJ_NULL) {
        dest[0] = mp_obj_new_float(classes_Sensor_value_native(self));
        return;
    }
    if (dest[1] != MP_OBJ_NULL) {
        classes_Sensor_value_setter_native(self, mp_obj_get_float(dest[1]));
        dest[0] = MP_OBJ_NULL;
        return;
    }
}
```

So getter/setter body is still direct native function logic.

### Staticmethod

Generated object registration:

```c
static const mp_rom_obj_static_class_method_t classes_Entity_validate_name_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&classes_Entity_validate_name_fun_obj)
};
```

Implementation is a plain function taking declared args.

No `self` required.

### Classmethod

Generated registration for `Sensor.create`:

```c
static const mp_rom_obj_static_class_method_t classes_Sensor_create_obj = {
    {&mp_type_classmethod}, MP_ROM_PTR(&classes_Sensor_create_fun_obj)
};
```

Implementation receives class as first arg:

```c
static mp_obj_t classes_Sensor_create_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    mp_obj_t cls = arg0_obj;
    mp_obj_t name = arg1_obj;
    return classes_Sensor_create_native(cls, name);
}
```

## 3.9 Direct answer: why compiled classes feel different

You asked:

"I still don't understand fully how our classes are different from MicroPython class."

The shortest correct answer is:

- Interpreted class instances are dynamic hash maps of fields.
- Compiled class instances are fixed-layout C structs.

Everything else follows from that.

Hash map model gives dynamic flexibility.

Fixed layout gives predictable speed and smaller per-instance memory.

---

## Direct Answer: How Are Our Classes Different?

Below is a strict side-by-side.

### 1) Instance representation

Interpreted:

```text
mp_obj_instance_t + mp_map_t members hash table
```

Compiled:

```text
generated struct with typed fields at fixed offsets
```

### 2) Field access

Interpreted `self.x`:

```text
attribute name -> map lookup -> maybe class lookup
```

Compiled `self.x`:

```text
pointer cast -> constant offset load/store
```

### 3) Inheritance field access

Interpreted:

```text
still lookup by attribute name, runtime path
```

Compiled:

```text
self->super.super.field  (depth known at compile time)
```

### 4) Method resolution and calls

Interpreted:

```text
class dict lookup, base search, descriptor handling
```

Compiled:

```text
direct native calls when type is known, vtable-ready layout for polymorphism
```

### 5) Dynamic features

Interpreted:

```text
can add/delete fields at runtime, supports __getattr__/metaclass machinery
```

Compiled:

```text
fixed field set; dynamic structural tricks are intentionally restricted
```

---

## Direct Answer: `list[Class]` in both worlds

This is the most confusing part because the container is the same.

### 3.10 What is identical

`list` is still MicroPython list.

Container type is still `mp_obj_list_t`.

`items` is still `mp_obj_t *items`.

So both interpreted and compiled class objects live behind `mp_obj_t` references in the same list storage.

The list does not know class internals.

The list does not care.

### 3.11 What is different

The pointed-to objects differ.

Interpreted item points to `mp_obj_instance_t` with hash table members.

Compiled item points to generated struct with fixed fields.

That changes per-item memory and field access cost.

### 3.12 Side-by-side layout

```text
Interpreted MicroPython: list[Point]

  mp_obj_list_t
  +-- items[0] -> mp_obj_instance_t { members: {x: 1, y: 2} }  ~48 bytes
  +-- items[1] -> mp_obj_instance_t { members: {x: 3, y: 4} }  ~48 bytes
  +-- items[2] -> mp_obj_instance_t { members: {x: 5, y: 6} }  ~48 bytes

  points[0].x:
    1. mp_obj_subscr(list, 0) -> get items[0] pointer
    2. mp_load_attr(item, "x") -> hash "x" -> probe table -> load value
    ~13 loads
```

```text
Compiled mypyc-micropython: list[Point]

  mp_obj_list_t
  +-- items[0] -> Point_obj_t { base, x=1, y=2 }               16 bytes
  +-- items[1] -> Point_obj_t { base, x=3, y=4 }               16 bytes
  +-- items[2] -> Point_obj_t { base, x=5, y=6 }               16 bytes

  points[0].x:
    1. mp_list_get(list, 0) -> get items[0] pointer
    2. ((Point_obj_t *)ptr)->x -> load at fixed offset
    ~3 loads
```

The list container is identical.

Only item representation and item access path differ.

This is the exact reason the behavior is easy to misunderstand at first.

### 3.13 Memory comparison for list of three points

Interpreted rough estimate:

- list header: 16
- items array: 12
- item objects: `3 * 48`

`16 + 12 + 144 = ~172 bytes`

Compiled rough estimate:

- list header: 16
- items array: 12
- item objects: `3 * 16`

`16 + 12 + 48 = ~76 bytes`

Again, list overhead is same.

Delta is entirely in item object footprint.

---

## 3.14 Python -> IR -> C: three-stage walk for one expression

Let us trace `self._value > self.threshold` in `SmartSensor.check_value`.

### Stage 1: Python source

```python
def check_value(self) -> bool:
    if self._value > self.threshold:
        self.alert_count += 1
        return True
    return False
```

### Stage 2: IR concept (text style)

```text
def check_value(self: SmartSensor) -> bool:
  body:
    if (self._value > self.threshold):
      self.alert_count = self.alert_count + 1
      return True
    return False
```

The important IR fact:

`self._value` is a typed field access on known class chain.

`self.threshold` is a typed local field access.

No dynamic name lookup nodes are needed for these fields.

### Stage 3: generated C

```c
static bool classes_SmartSensor_check_value_native(classes_SmartSensor_obj_t *self) {
    if ((self->super._value > self->threshold)) {
        self->alert_count += 1;
        return true;
    }
    return false;
}
```

This is the structural payoff.

---

## 3.15 Another three-stage walk: cross-level access

Expression:

```python
self._id + self.alert_count
```

IR concept:

```text
return (field(self, base=Entity, name=_id) + field(self, base=SmartSensor, name=alert_count))
```

Generated C:

```c
return (self->super.super._id + self->alert_count);
```

No runtime parent traversal.

Depth is known and encoded.

---

## 3.16 How locals dict still exists in compiled classes

One subtle point.

Compiled classes still expose methods through MicroPython type `locals_dict`.

From generated `classes_SmartSensor_locals_dict_table`:

```c
{ MP_ROM_QSTR(MP_QSTR_check_value), MP_ROM_PTR(&classes_SmartSensor_check_value_obj) },
{ MP_ROM_QSTR(MP_QSTR_get_alert_count), MP_ROM_PTR(&classes_SmartSensor_get_alert_count_obj) },
{ MP_ROM_QSTR(MP_QSTR_get_total_score), MP_ROM_PTR(&classes_SmartSensor_get_total_score_obj) },
```

So Python-level method access still integrates with normal object model.

What changes is instance storage and native body execution path.

## 3.17 Attr handlers in compiled classes

Generated classes provide `attr` handler functions, for example:

- `classes_Entity_attr`
- `classes_Sensor_attr`
- `classes_SmartSensor_attr`

These handlers map QSTR names to fixed offsets.

Example from `classes_SmartSensor_fields`:

```c
{ MP_QSTR_name, offsetof(classes_SmartSensor_obj_t, super.super.name), 0 },
{ MP_QSTR__id, offsetof(classes_SmartSensor_obj_t, super.super._id), 1 },
{ MP_QSTR_threshold, offsetof(classes_SmartSensor_obj_t, threshold), 2 },
{ MP_QSTR_alert_count, offsetof(classes_SmartSensor_obj_t, alert_count), 1 },
{ MP_QSTR_active, offsetof(classes_SmartSensor_obj_t, active), 3 },
```

So even when attribute API is used dynamically, field location is table-driven by `offsetof` metadata, not per-instance hash map membership.

That still preserves a lot of speed and memory wins.

## 3.18 What this means for polymorphism

Generated object embeds parent prefix.

Generated vtables wire inherited and overridden methods.

Example from `classes_SmartSensor_vtable_inst`:

```c
.describe = classes_SmartSensor_describe_native,
.record = (void (*)(classes_SmartSensor_obj_t *, mp_int_t, mp_float_t))classes_Sensor_record_native,
.get_location_x = (mp_int_t (*)(classes_SmartSensor_obj_t *))classes_Sensor_get_location_x_native,
```

So child object can reuse parent implementations safely via embedded layout.

Same concept as blog 03, now in this concrete class family.

---

## 3.19 Summary table

| Feature | Interpreted MicroPython | Compiled (mypyc-micropython) |
|---|---|---|
| Instance memory (Point) | ~48 bytes | 16 bytes |
| Field access | hash table probe | struct offset load |
| Method call | class dict search + base walk | direct C function call/wrapper |
| `super()` call | runtime parent resolution | compile-time direct parent call |
| `list[Point]` per-item | ~48 bytes | 16 bytes |
| `points[i].x` | ~13 loads | ~3 loads |
| Add field at runtime (`self.z = 1`) | Yes | No (fixed layout) |
| Delete field (`del self.z`) | Yes | No |
| `__getattr__` override flexibility | Yes | Not supported in compiled class model |
| Metaclass flexibility | Yes | Not supported in compiled class model |

The table is intentionally blunt.

This is a performance-vs-dynamism trade.

---

## Trade-offs: what you gain and what you lose

You gain:

- lower per-instance memory
- faster hot-path field access
- predictable inheritance field paths
- simpler generated machine behavior

You lose dynamic features that depend on per-instance hash maps.

### 3.20 Dynamic features you give up

1. No arbitrary new field insertion at runtime.

```python
self.new_attr = 123
```

Not supported in fixed-layout compiled class.

2. No dynamic field deletion.

```python
del self.some_field
```

Not supported.

3. No generic `__getattr__` / `__setattr__` customization in this compiled class model.

4. No metaclass-oriented dynamic behavior.

5. Fields must be declared with known types for layout generation.

These are not accidental omissions.

They are exactly the features enabled by hash-table instance storage.

When storage changes to fixed struct fields, those features naturally disappear.

---

## 3.21 Final mental model

If one sentence has to stick, use this one:

`mypyc-micropython` keeps MicroPython's module/type integration, but replaces per-instance dynamic field maps with compile-time struct layouts for typed classes.

That is why:

- `list` looks the same
- Python API looks familiar
- but memory and attribute access behavior are very different

And that directly answers your original confusion around `list[Class]`.

---

# Direct Answer: "How are our classes different?"

Short checklist version.

Use this when reviewing generated code quickly.

- Interpreted instance -> `mp_obj_instance_t` with `mp_map_t members`
- Compiled instance -> generated `*_obj_t` with typed fields
- Interpreted field read -> map lookup + class lookup fallback
- Compiled field read -> direct pointer+offset load
- Interpreted inheritance field access -> dynamic name path
- Compiled inheritance field access -> explicit `super.super.field`
- Interpreted `super()` -> runtime path
- Compiled `super()` -> direct C call to known parent function
- Interpreted list items -> pointers to map-backed instances
- Compiled list items -> pointers to fixed-layout structs

---

# Direct Answer: `list[Class]` in both worlds

One more explicit restatement because this is the main question.

The list container is the same.

The item representation is different.

That is all.

And that is enough to change both memory and speed meaningfully.

If you inspect only list internals, they look identical.

If you inspect pointed objects, they diverge completely.

---

# Appendix A: Full load-trace for `points[0].x`

These are conceptual traces, not cycle-accurate micro-ops.

They are useful for reasoning.

## A.1 Interpreted conceptual trace

```text
Expression: points[0].x

Step 1: evaluate points variable
Step 2: ensure object is list-compatible for subscr
Step 3: route through mp_obj_subscr/list slot path
Step 4: fetch items pointer from mp_obj_list_t
Step 5: compute slot address for index 0
Step 6: load mp_obj_t item reference
Step 7: start attribute load for 'x'
Step 8: get type from item base
Step 9: instance attr loader checks members map
Step 10: hash MP_QSTR_x
Step 11: modulo/probe first slot
Step 12: compare key
Step 13: load value from map elem
Step 14: return value as mp_obj_t
```

Approximate memory load count in this path is often discussed as `~13`.

Depends on inline fast paths and cache conditions.

## A.2 Compiled conceptual trace

```text
Expression: points[0].x

Step 1: evaluate points variable
Step 2: get item pointer from list storage
Step 3: cast item pointer to Point_obj_t *
Step 4: load x at fixed offset
Step 5: box/unbox as needed by expression context
```

Often summarized as `~3` loads for core fetch path.

Again approximate, but directionally accurate.

## A.3 Why this difference compounds

Single read is small.

But if you do this in loops over thousands of elements:

- interpreted: repeated hash path per field access
- compiled: repeated offset load

That is where the practical speedup appears.

---

# Closing

If you remember only two points, remember these:

1. Interpreted classes store fields in per-instance hash tables.

2. Compiled classes store fields in fixed C struct offsets.

And for your `list[Class]` question specifically:

- list container is unchanged
- item representation changes
- therefore `points[i].x` path and per-item memory change dramatically

That is the entire difference in one frame.
