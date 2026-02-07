# mypyc Reference: How mypyc Implements Complex Features

This document analyzes how mypyc handles complex Python features, providing a reference for implementing similar functionality in mypyc-micropython.

## Table of Contents

- [Overview](#overview)
- [Compilation Pipeline](#compilation-pipeline)
- [Function Arguments](#function-arguments)
- [Closures](#closures)
- [Generators](#generators)
- [Classes](#classes)
- [Exception Handling](#exception-handling)
- [Lessons for mypyc-micropython](#lessons-for-mypyc-micropython)

## Overview

mypyc compiles typed Python to C extension modules through an intermediate representation (IR). Understanding this approach helps us design mypyc-micropython's more advanced features.

### Key mypyc Concepts

| Concept | Description |
|---------|-------------|
| `FuncIR` | IR representation of a function |
| `BasicBlock` | Sequence of operations ending in control flow |
| `Op` | Single IR operation (load, store, call, etc.) |
| `RType` | Runtime type representation |
| `Value` | Result of an operation (has an RType) |

## Compilation Pipeline

```
Python Source
     │
     ▼
┌─────────────────┐
│   mypy parse    │  AST + Type information
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   IR Builder    │  mypyc/irbuild/
│                 │  - Converts AST → IR ops
│                 │  - Type-aware code gen
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  IR Transforms  │  mypyc/transform/
│                 │  - Optimize IR
│                 │  - Lower complex ops
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   C Codegen     │  mypyc/codegen/
│                 │  - Emit C code
│                 │  - CPython API calls
└─────────────────┘
```

## Function Arguments

### Default Arguments

mypyc handles default arguments using a bitmap to track which arguments were provided.

**Python:**
```python
def greet(name: str, greeting: str = "Hello") -> str:
    return f"{greeting}, {name}!"
```

**mypyc IR Approach:**
```c
// Generated wrapper function
PyObject *greet_wrapper(PyObject *self, PyObject *const *args, 
                        Py_ssize_t nargs, PyObject *kwnames) {
    // Bitmap: bit 0 = name provided, bit 1 = greeting provided
    static const char *kwlist[] = {"name", "greeting", NULL};
    
    PyObject *name;
    PyObject *greeting = NULL;  // NULL means use default
    
    // Parse args with CPyArg_ParseStackAndKeywords
    if (!CPyArg_ParseStackAndKeywords(args, nargs, kwnames,
            &CPyModule_greet_globals, kwlist, &name, &greeting)) {
        return NULL;
    }
    
    // Check if greeting was provided, else use default
    if (greeting == NULL) {
        greeting = PyUnicode_FromString("Hello");
    }
    
    return greet_impl(name, greeting);
}
```

**Key Data Structure - `RuntimeArg`:**
```python
@dataclass
class RuntimeArg:
    name: str
    typ: RType
    kind: ArgKind  # ARG_POS, ARG_OPT, ARG_STAR, ARG_STAR2, ARG_NAMED, etc.
    pos_only: bool = False
```

### *args and **kwargs

**Python:**
```python
def variadic(*args: int, **kwargs: str) -> None:
    pass
```

**mypyc IR Representation:**
```python
# Function signature in IR
FuncSignature(
    args=[
        RuntimeArg("args", tuple_rprimitive, ARG_STAR),
        RuntimeArg("kwargs", dict_rprimitive, ARG_STAR2),
    ],
    ret_type=none_rprimitive
)
```

**Generated C Wrapper:**
```c
// Native function receives unpacked args
static PyObject *variadic_impl(PyObject *args_tuple, PyObject *kwargs_dict) {
    // args_tuple is a tuple of all positional args
    // kwargs_dict is a dict of all keyword args
    
    Py_ssize_t n_args = PyTuple_GET_SIZE(args_tuple);
    for (Py_ssize_t i = 0; i < n_args; i++) {
        PyObject *arg = PyTuple_GET_ITEM(args_tuple, i);
        // Process each arg...
    }
    
    // Process kwargs...
    Py_RETURN_NONE;
}

// Wrapper handles CPython calling convention
static PyObject *variadic_wrapper(PyObject *self, PyObject *args, PyObject *kwargs) {
    return variadic_impl(args, kwargs ? kwargs : PyDict_New());
}
```

### MicroPython Equivalent

For mypyc-micropython, we'd use:

```c
// MicroPython variadic function
static mp_obj_t variadic(size_t n_args, const mp_obj_t *args, mp_map_t *kwargs) {
    // n_args = number of positional args
    // args = array of positional args
    // kwargs = map of keyword args (can be NULL)
    
    for (size_t i = 0; i < n_args; i++) {
        mp_obj_t arg = args[i];
        // Process...
    }
    
    if (kwargs != NULL) {
        for (size_t i = 0; i < kwargs->alloc; i++) {
            if (mp_map_slot_is_filled(kwargs, i)) {
                mp_obj_t key = kwargs->table[i].key;
                mp_obj_t value = kwargs->table[i].value;
                // Process...
            }
        }
    }
    
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(variadic_obj, 0, variadic);
```

## Closures

mypyc transforms closures into callable class instances with captured variables stored in an environment object.

### How mypyc Does It

**Python:**
```python
def make_counter(start: int) -> Callable[[], int]:
    count = start
    def increment() -> int:
        nonlocal count
        count += 1
        return count
    return increment
```

**mypyc Transformation:**
```c
// Environment struct holds captured variables
typedef struct {
    PyObject_HEAD
    CPyTagged count;  // Captured variable
} make_counter_env;

// Inner function as a class with __call__
typedef struct {
    PyObject_HEAD
    make_counter_env *env;
} increment_closure;

// The __call__ method
static PyObject *increment_call(increment_closure *self) {
    make_counter_env *env = self->env;
    env->count = CPyTagged_Add(env->count, 2);  // Tagged int: 1 << 1 = 2
    return CPyTagged_AsObject(env->count);
}

// Outer function creates the closure
static PyObject *make_counter(CPyTagged start) {
    // Allocate environment
    make_counter_env *env = PyObject_New(make_counter_env, &make_counter_env_type);
    env->count = start;
    
    // Create closure object pointing to environment
    increment_closure *closure = PyObject_New(increment_closure, &increment_type);
    closure->env = env;
    Py_INCREF(env);
    
    return (PyObject *)closure;
}
```

### MicroPython Equivalent

```c
// Environment object
typedef struct {
    mp_obj_base_t base;
    mp_int_t count;
} counter_env_t;

// Closure object
typedef struct {
    mp_obj_base_t base;
    counter_env_t *env;
} increment_closure_t;

// Call the closure
static mp_obj_t increment_call(mp_obj_t self_in) {
    increment_closure_t *self = MP_OBJ_TO_PTR(self_in);
    self->env->count += 1;
    return mp_obj_new_int(self->env->count);
}

// Type for the closure (makes it callable)
static const mp_obj_type_t increment_type = {
    { &mp_type_type },
    .name = MP_QSTR_increment,
    .call = increment_call,
};

// Outer function
static mp_obj_t make_counter(mp_obj_t start_obj) {
    mp_int_t start = mp_obj_get_int(start_obj);
    
    // Allocate environment
    counter_env_t *env = m_new_obj(counter_env_t);
    env->base.type = &counter_env_type;
    env->count = start;
    
    // Create closure
    increment_closure_t *closure = m_new_obj(increment_closure_t);
    closure->base.type = &increment_type;
    closure->env = env;
    
    return MP_OBJ_FROM_PTR(closure);
}
```

## Generators

mypyc transforms generators into state machines implemented as classes.

### How mypyc Does It

**Python:**
```python
def countdown(n: int) -> Generator[int, None, None]:
    while n > 0:
        yield n
        n -= 1
```

**mypyc State Machine:**
```c
// Generator state struct
typedef struct {
    PyObject_HEAD
    int state;           // Current state in state machine
    CPyTagged n;         // Local variable
} countdown_generator;

// States
#define STATE_INITIAL 0
#define STATE_AFTER_YIELD_1 1
#define STATE_EXHAUSTED -1

// __next__ implementation
static PyObject *countdown_next(countdown_generator *self) {
    switch (self->state) {
        case STATE_INITIAL:
            goto state_initial;
        case STATE_AFTER_YIELD_1:
            goto state_after_yield_1;
        default:
            PyErr_SetNone(PyExc_StopIteration);
            return NULL;
    }

state_initial:
    // while n > 0:
    while (CPyTagged_IsGt(self->n, 0)) {
        // yield n
        PyObject *result = CPyTagged_AsObject(self->n);
        self->state = STATE_AFTER_YIELD_1;
        return result;
        
state_after_yield_1:
        // n -= 1
        self->n = CPyTagged_Subtract(self->n, 2);
    }
    
    // Generator exhausted
    self->state = STATE_EXHAUSTED;
    PyErr_SetNone(PyExc_StopIteration);
    return NULL;
}
```

### MicroPython Equivalent

```c
typedef struct {
    mp_obj_base_t base;
    mp_int_t state;
    mp_int_t n;
} countdown_gen_t;

static mp_obj_t countdown_iternext(mp_obj_t self_in) {
    countdown_gen_t *self = MP_OBJ_TO_PTR(self_in);
    
    switch (self->state) {
        case 0: goto state_0;
        case 1: goto state_1;
        default: return MP_OBJ_STOP_ITERATION;
    }
    
state_0:
    while (self->n > 0) {
        mp_obj_t result = mp_obj_new_int(self->n);
        self->state = 1;
        return result;
        
state_1:
        self->n -= 1;
    }
    
    self->state = -1;
    return MP_OBJ_STOP_ITERATION;
}

static const mp_obj_type_t countdown_gen_type = {
    { &mp_type_type },
    .name = MP_QSTR_generator,
    .getiter = mp_identity_getiter,
    .iternext = countdown_iternext,
};

static mp_obj_t countdown(mp_obj_t n_obj) {
    countdown_gen_t *gen = m_new_obj(countdown_gen_t);
    gen->base.type = &countdown_gen_type;
    gen->state = 0;
    gen->n = mp_obj_get_int(n_obj);
    return MP_OBJ_FROM_PTR(gen);
}
```

## Classes

mypyc compiles classes to C extension types with optimized attribute access.

### How mypyc Does It

**Python:**
```python
class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
    
    def distance(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5
```

**mypyc Generated C:**
```c
// Object struct with fixed layout
typedef struct {
    PyObject_HEAD
    CPyTagged x;  // Stored unboxed for efficiency
    CPyTagged y;
} PointObject;

// Attribute offsets for fast access
#define POINT_X_OFFSET offsetof(PointObject, x)
#define POINT_Y_OFFSET offsetof(PointObject, y)

// __init__
static int Point_init(PointObject *self, PyObject *args, PyObject *kwds) {
    PyObject *x_obj, *y_obj;
    if (!PyArg_ParseTuple(args, "OO", &x_obj, &y_obj)) {
        return -1;
    }
    self->x = CPyTagged_FromObject(x_obj);
    self->y = CPyTagged_FromObject(y_obj);
    return 0;
}

// distance method - uses direct field access
static PyObject *Point_distance(PointObject *self) {
    double x = CPyTagged_IsInt(self->x) ? (double)(self->x >> 1) : ...;
    double y = CPyTagged_IsInt(self->y) ? (double)(self->y >> 1) : ...;
    double result = sqrt(x * x + y * y);
    return PyFloat_FromDouble(result);
}

// Vtable for methods (enables fast method dispatch)
static CPyVTable Point_vtable = {
    .distance = Point_distance,
};
```

### MicroPython Equivalent

```c
// Object struct
typedef struct {
    mp_obj_base_t base;
    mp_int_t x;
    mp_int_t y;
} point_obj_t;

// Constructor
static mp_obj_t point_make_new(const mp_obj_type_t *type, 
                                size_t n_args, size_t n_kw, 
                                const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);
    
    point_obj_t *self = mp_obj_malloc(point_obj_t, type);
    self->x = mp_obj_get_int(args[0]);
    self->y = mp_obj_get_int(args[1]);
    return MP_OBJ_FROM_PTR(self);
}

// distance method
static mp_obj_t point_distance(mp_obj_t self_in) {
    point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_float_t x = (mp_float_t)self->x;
    mp_float_t y = (mp_float_t)self->y;
    mp_float_t result = MICROPY_FLOAT_C_FUN(sqrt)(x * x + y * y);
    return mp_obj_new_float(result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(point_distance_obj, point_distance);

// Attribute access
static void point_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    
    if (dest[0] == MP_OBJ_NULL) {
        // Load attribute
        if (attr == MP_QSTR_x) {
            dest[0] = mp_obj_new_int(self->x);
        } else if (attr == MP_QSTR_y) {
            dest[0] = mp_obj_new_int(self->y);
        } else if (attr == MP_QSTR_distance) {
            dest[0] = MP_OBJ_FROM_PTR(&point_distance_obj);
            dest[1] = self_in;  // Bind self
        }
    } else if (dest[1] != MP_OBJ_NULL) {
        // Store attribute
        if (attr == MP_QSTR_x) {
            self->x = mp_obj_get_int(dest[1]);
            dest[0] = MP_OBJ_NULL;
        } else if (attr == MP_QSTR_y) {
            self->y = mp_obj_get_int(dest[1]);
            dest[0] = MP_OBJ_NULL;
        }
    }
}

// Type definition
static const mp_obj_type_t point_type = {
    { &mp_type_type },
    .name = MP_QSTR_Point,
    .make_new = point_make_new,
    .attr = point_attr,
};
```

## Exception Handling

### How mypyc Does It

mypyc uses CPython's exception mechanism directly:

```python
def safe_divide(a: int, b: int) -> int:
    try:
        return a // b
    except ZeroDivisionError:
        return 0
```

**Generated C:**
```c
static PyObject *safe_divide(CPyTagged a, CPyTagged b) {
    PyObject *result;
    
    // try block
    if (CPyTagged_IsZero(b)) {
        PyErr_SetString(PyExc_ZeroDivisionError, "division by zero");
        goto error;
    }
    result = CPyTagged_FloorDivide(a, b);
    if (result == NULL) {
        goto error;
    }
    return result;
    
error:
    // except ZeroDivisionError:
    if (PyErr_ExceptionMatches(PyExc_ZeroDivisionError)) {
        PyErr_Clear();
        return CPyTagged_AsObject(0);
    }
    return NULL;  // Re-raise
}
```

### MicroPython Equivalent

MicroPython uses `nlr_push`/`nlr_pop` (non-local return) for exception handling:

```c
static mp_obj_t safe_divide(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        // try block
        if (b == 0) {
            mp_raise_ZeroDivisionError(NULL);
        }
        mp_obj_t result = mp_obj_new_int(a / b);
        nlr_pop();
        return result;
    } else {
        // except block
        mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);
        if (mp_obj_is_subclass_fast(MP_OBJ_FROM_PTR(mp_obj_get_type(exc)),
                                     MP_OBJ_FROM_PTR(&mp_type_ZeroDivisionError))) {
            return mp_obj_new_int(0);
        }
        // Re-raise
        nlr_jump(nlr.ret_val);
    }
}
```

## Lessons for mypyc-micropython

### What to Adopt from mypyc

| Feature | mypyc Approach | Adaptation for MicroPython |
|---------|---------------|---------------------------|
| **IR Design** | Typed IR with ops | Simplify - fewer op types needed |
| **Closure Transform** | Environment objects + callable classes | Same pattern works |
| **Generator Transform** | State machine with goto | Same pattern works |
| **Class Layout** | Fixed struct with vtable | Use `mp_obj_type_t` attr handler |
| **Type Tracking** | RType system | Map to MicroPython types |

### Key Differences

| Aspect | mypyc (CPython) | mypyc-micropython |
|--------|-----------------|-------------------|
| **Integer Boxing** | Tagged integers (CPyTagged) | `mp_int_t` / `mp_obj_t` |
| **String Handling** | PyUnicode API | MicroPython string API |
| **Memory Management** | Reference counting | MicroPython GC |
| **Exception Handling** | PyErr_* functions | nlr_push/nlr_pop |
| **Object Model** | PyObject with refcount | mp_obj_t (may be tagged) |

### Implementation Priority

Based on mypyc's complexity, recommended implementation order:

1. **Default Arguments** (Low complexity)
   - Wrapper functions with NULL checks
   - Store defaults as module-level constants

2. ***args/**kwargs** (Medium complexity)
   - Use `MP_DEFINE_CONST_FUN_OBJ_KW`
   - Tuple/dict unpacking in wrapper

3. **Simple Classes** (Medium complexity)
   - Fixed struct layout
   - attr handler for get/set
   - make_new for constructor

4. **Exception Handling** (Medium complexity)
   - nlr_push/nlr_pop pattern
   - Exception type matching

5. **Closures** (High complexity)
   - Environment struct
   - Callable closure type

6. **Generators** (High complexity)
   - State machine transformation
   - Iterator protocol

## See Also

- [01-architecture.md](01-architecture.md) - mypyc-micropython architecture
- [03-micropython-c-api.md](03-micropython-c-api.md) - MicroPython C API reference
- [mypyc source code](https://github.com/python/mypy/tree/master/mypyc) - Original implementation
