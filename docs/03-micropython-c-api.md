# MicroPython C API Reference

Quick reference for MicroPython C API functions used in mypyc-micropython code generation.

## Table of Contents

- [Object Basics](#object-basics)
- [Type Conversion](#type-conversion)
- [Object Creation](#object-creation)
- [Function Definition](#function-definition)
- [Module Definition](#module-definition)
- [Class/Type Definition](#classtype-definition)
- [Attribute Access](#attribute-access)
- [Method Calls](#method-calls)
- [Collections](#collections)
- [Exception Handling](#exception-handling)
- [Memory Management](#memory-management)
- [CPython vs MicroPython](#cpython-vs-micropython)

## Object Basics

### Core Types

```c
// All MicroPython objects are represented as mp_obj_t
// This is either a pointer to an object or a small int/constant

typedef void *mp_obj_t;

// Type information
typedef struct _mp_obj_type_t {
    mp_obj_base_t base;
    uint16_t flags;
    uint16_t name;  // qstr
    // ... slots for make_new, print, call, attr, etc.
} mp_obj_type_t;

// Base for all objects
typedef struct _mp_obj_base_t {
    const mp_obj_type_t *type;
} mp_obj_base_t;
```

### Common Constants

```c
mp_const_none       // Python None
mp_const_true       // Python True  
mp_const_false      // Python False
mp_const_empty_tuple // Empty tuple ()

// Check for constants
mp_obj_is_true(obj)           // Truthy check
obj == mp_const_none          // None check
```

### Object Type Checking

```c
// Type checking macros
mp_obj_is_int(obj)            // Is small int?
mp_obj_is_float(obj)          // Is float?
mp_obj_is_str(obj)            // Is string?
mp_obj_is_type(obj, &type)    // Is specific type?

// Get type
mp_obj_get_type(obj)          // Returns mp_obj_type_t*
mp_obj_get_type_str(obj)      // Returns type name as char*

// Type comparison
mp_obj_is_subclass_fast(derived, base)  // Subclass check
```

## Type Conversion

### Unboxing (mp_obj_t → C type)

```c
// Integer
mp_int_t mp_obj_get_int(mp_obj_t obj);
mp_int_t mp_obj_get_int_truncated(mp_obj_t obj);  // Large ints truncated

// Float
mp_float_t mp_obj_get_float(mp_obj_t obj);
// Alternative macro for different float implementations
mp_float_t mp_obj_float_get(mp_obj_t obj);

// Boolean
bool mp_obj_is_true(mp_obj_t obj);

// String
const char *mp_obj_str_get_str(mp_obj_t obj);
const char *mp_obj_str_get_data(mp_obj_t obj, size_t *len);

// Bytes
void mp_obj_str_get_data(mp_obj_t obj, const byte **data, size_t *len);
```

### Boxing (C type → mp_obj_t)

```c
// Integer
mp_obj_t mp_obj_new_int(mp_int_t value);
mp_obj_t mp_obj_new_int_from_uint(mp_uint_t value);
mp_obj_t mp_obj_new_int_from_ll(long long value);

// Float
mp_obj_t mp_obj_new_float(mp_float_t value);

// Boolean (use constants)
#define mp_obj_new_bool(b) ((b) ? mp_const_true : mp_const_false)

// String
mp_obj_t mp_obj_new_str(const char *data, size_t len);
mp_obj_t mp_obj_new_str_copy(const mp_obj_type_t *type, const byte *data, size_t len);

// Bytes
mp_obj_t mp_obj_new_bytes(const byte *data, size_t len);
```

## Object Creation

### General Object Allocation

```c
// Allocate object with type
#define mp_obj_malloc(struct_type, obj_type) \
    ((struct_type *)m_malloc_with_type((obj_type), sizeof(struct_type)))

// Alternative allocation
void *m_new_obj(type);                    // Allocate single object
void *m_new_obj_with_finaliser(type);     // With destructor
void *m_new(type, count);                 // Allocate array

// Example: Create custom object
typedef struct {
    mp_obj_base_t base;
    mp_int_t value;
} my_obj_t;

my_obj_t *obj = mp_obj_malloc(my_obj_t, &my_type);
obj->value = 42;
```

### Tuple Creation

```c
// Fixed-size tuple
mp_obj_t mp_obj_new_tuple(size_t n, const mp_obj_t *items);

// Build tuple from varargs
mp_obj_t tuple = mp_obj_new_tuple(3, (mp_obj_t[]){
    mp_obj_new_int(1),
    mp_obj_new_int(2),
    mp_obj_new_int(3)
});

// Empty tuple
mp_const_empty_tuple
```

### List Creation

```c
// New list with capacity
mp_obj_t mp_obj_new_list(size_t n, mp_obj_t *items);

// Operations
void mp_obj_list_append(mp_obj_t list, mp_obj_t item);
void mp_obj_list_get(mp_obj_t list, size_t *len, mp_obj_t **items);
mp_obj_t mp_obj_list_pop(mp_obj_t list, size_t index);
```

### Dict Creation

```c
// New dict
mp_obj_t mp_obj_new_dict(size_t n_args);

// Operations
void mp_obj_dict_store(mp_obj_t dict, mp_obj_t key, mp_obj_t value);
mp_obj_t mp_obj_dict_get(mp_obj_t dict, mp_obj_t key);
void mp_obj_dict_delete(mp_obj_t dict, mp_obj_t key);
```

## Function Definition

### Function Macros by Argument Count

```c
// 0 arguments
static mp_obj_t my_func_0(void) {
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(my_func_0_obj, my_func_0);

// 1 argument
static mp_obj_t my_func_1(mp_obj_t arg0) {
    return arg0;
}
static MP_DEFINE_CONST_FUN_OBJ_1(my_func_1_obj, my_func_1);

// 2 arguments
static mp_obj_t my_func_2(mp_obj_t arg0, mp_obj_t arg1) {
    return mp_obj_new_int(mp_obj_get_int(arg0) + mp_obj_get_int(arg1));
}
static MP_DEFINE_CONST_FUN_OBJ_2(my_func_2_obj, my_func_2);

// 3 arguments
static mp_obj_t my_func_3(mp_obj_t a, mp_obj_t b, mp_obj_t c) { ... }
static MP_DEFINE_CONST_FUN_OBJ_3(my_func_3_obj, my_func_3);
```

### Variable Arguments

```c
// Variable positional args (min to max)
static mp_obj_t my_func_var(size_t n_args, const mp_obj_t *args) {
    // args[0], args[1], ..., args[n_args-1]
    mp_int_t sum = 0;
    for (size_t i = 0; i < n_args; i++) {
        sum += mp_obj_get_int(args[i]);
    }
    return mp_obj_new_int(sum);
}
// min_args=1, max_args=10
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(my_func_var_obj, 1, 10, my_func_var);

// Unlimited variable args
static MP_DEFINE_CONST_FUN_OBJ_VAR(my_func_var_obj, 0, my_func_var);  // min=0
```

### Keyword Arguments

```c
// With keyword args
static mp_obj_t my_func_kw(size_t n_args, const mp_obj_t *args, mp_map_t *kw_args) {
    // Parse positional and keyword args
    enum { ARG_x, ARG_y, ARG_z };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_x, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_y, MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_z, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
    };
    
    mp_arg_val_t parsed_args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, args, kw_args, 
                     MP_ARRAY_SIZE(allowed_args), allowed_args, parsed_args);
    
    mp_int_t x = parsed_args[ARG_x].u_int;
    mp_int_t y = parsed_args[ARG_y].u_int;
    mp_int_t z = parsed_args[ARG_z].u_int;
    
    return mp_obj_new_int(x + y + z);
}
static MP_DEFINE_CONST_FUN_OBJ_KW(my_func_kw_obj, 1, my_func_kw);  // 1 required positional
```

### Argument Parsing Flags

```c
MP_ARG_REQUIRED      // Argument must be provided
MP_ARG_KW_ONLY       // Keyword-only argument
MP_ARG_BOOL          // Boolean type
MP_ARG_INT           // Integer type
MP_ARG_OBJ           // Any object type
```

## Module Definition

### Basic Module Structure

```c
// Module globals table
static const mp_rom_map_elem_t mymodule_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_mymodule) },
    { MP_ROM_QSTR(MP_QSTR_my_func), MP_ROM_PTR(&my_func_obj) },
    { MP_ROM_QSTR(MP_QSTR_MY_CONST), MP_ROM_INT(42) },
    { MP_ROM_QSTR(MP_QSTR_MyClass), MP_ROM_PTR(&my_class_type) },
};
static MP_DEFINE_CONST_DICT(mymodule_globals, mymodule_globals_table);

// Module definition
const mp_obj_module_t mymodule_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&mymodule_globals,
};

// Register module
MP_REGISTER_MODULE(MP_QSTR_mymodule, mymodule_user_cmodule);
```

### ROM Map Entry Types

```c
MP_ROM_QSTR(qstr)           // String constant
MP_ROM_PTR(&obj)            // Pointer to object
MP_ROM_INT(value)           // Integer constant
MP_ROM_NONE                 // None
MP_ROM_TRUE                 // True
MP_ROM_FALSE                // False
```

## Class/Type Definition

### Basic Type Structure

```c
// Object struct
typedef struct {
    mp_obj_base_t base;
    mp_int_t x;
    mp_int_t y;
} point_obj_t;

// Constructor (make_new)
static mp_obj_t point_make_new(const mp_obj_type_t *type,
                                size_t n_args, size_t n_kw,
                                const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);
    
    point_obj_t *self = mp_obj_malloc(point_obj_t, type);
    self->x = mp_obj_get_int(args[0]);
    self->y = mp_obj_get_int(args[1]);
    return MP_OBJ_FROM_PTR(self);
}

// Print representation
static void point_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_printf(print, "Point(%d, %d)", self->x, self->y);
}

// Method
static mp_obj_t point_distance(mp_obj_t self_in) {
    point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_float_t dist = MICROPY_FLOAT_C_FUN(sqrt)(self->x * self->x + self->y * self->y);
    return mp_obj_new_float(dist);
}
static MP_DEFINE_CONST_FUN_OBJ_1(point_distance_obj, point_distance);

// Locals dict (methods and class attributes)
static const mp_rom_map_elem_t point_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_distance), MP_ROM_PTR(&point_distance_obj) },
};
static MP_DEFINE_CONST_DICT(point_locals_dict, point_locals_dict_table);

// Type definition
MP_DEFINE_CONST_OBJ_TYPE(
    point_type,
    MP_QSTR_Point,
    MP_TYPE_FLAG_NONE,
    make_new, point_make_new,
    print, point_print,
    locals_dict, &point_locals_dict
);
```

### Attribute Access (Instance Variables)

```c
// Custom attr handler for instance attributes
static void point_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    
    if (dest[0] == MP_OBJ_NULL) {
        // Load attribute
        switch (attr) {
            case MP_QSTR_x:
                dest[0] = mp_obj_new_int(self->x);
                break;
            case MP_QSTR_y:
                dest[0] = mp_obj_new_int(self->y);
                break;
            default:
                // Delegate to locals dict for methods
                dest[0] = MP_OBJ_NULL;
                mp_obj_type_get_slot(&point_type, attr, dest, MP_TYPE_ATTR_LOAD);
        }
    } else if (dest[1] != MP_OBJ_NULL) {
        // Store attribute
        switch (attr) {
            case MP_QSTR_x:
                self->x = mp_obj_get_int(dest[1]);
                dest[0] = MP_OBJ_NULL;  // Indicate success
                break;
            case MP_QSTR_y:
                self->y = mp_obj_get_int(dest[1]);
                dest[0] = MP_OBJ_NULL;
                break;
            default:
                // Unknown attribute - raise AttributeError
                break;
        }
    }
}

// Include attr in type definition
MP_DEFINE_CONST_OBJ_TYPE(
    point_type,
    MP_QSTR_Point,
    MP_TYPE_FLAG_NONE,
    make_new, point_make_new,
    attr, point_attr,
    locals_dict, &point_locals_dict
);
```

## Attribute Access

### Getting Attributes

```c
// Get attribute by qstr
mp_obj_t mp_load_attr(mp_obj_t obj, qstr attr);

// Example
mp_obj_t value = mp_load_attr(obj, MP_QSTR_my_attr);

// Safe get (returns MP_OBJ_NULL if not found)
mp_obj_t mp_load_attr_maybe(mp_obj_t obj, qstr attr);
```

### Setting Attributes

```c
// Set attribute
void mp_store_attr(mp_obj_t obj, qstr attr, mp_obj_t value);

// Example
mp_store_attr(obj, MP_QSTR_my_attr, mp_obj_new_int(42));
```

### Deleting Attributes

```c
// Delete attribute
void mp_delete_attr(mp_obj_t obj, qstr attr);
```

## Method Calls

### Calling Functions/Methods

```c
// Call with no args
mp_obj_t mp_call_function_0(mp_obj_t fun);

// Call with 1 arg
mp_obj_t mp_call_function_1(mp_obj_t fun, mp_obj_t arg0);

// Call with 2 args
mp_obj_t mp_call_function_2(mp_obj_t fun, mp_obj_t arg0, mp_obj_t arg1);

// Call with n positional args and kw args
mp_obj_t mp_call_function_n_kw(mp_obj_t fun, size_t n_args, size_t n_kw, 
                                const mp_obj_t *args);
// args layout: [pos_arg0, pos_arg1, ..., kw_name0, kw_val0, kw_name1, kw_val1, ...]

// Call method on object
mp_obj_t mp_call_method_n_kw(size_t n_args, size_t n_kw, const mp_obj_t *args);
// args[0] = method, args[1] = self, args[2..] = arguments
```

### Practical Call Example

```c
// Equivalent to: obj.method(arg1, arg2)
mp_obj_t method = mp_load_attr(obj, MP_QSTR_method);
mp_obj_t args[] = {method, obj, arg1, arg2};
mp_obj_t result = mp_call_method_n_kw(2, 0, args);

// Equivalent to: func(a, b, key=value)
mp_obj_t call_args[] = {
    a, b,                           // 2 positional args
    MP_OBJ_NEW_QSTR(MP_QSTR_key),   // keyword name
    value                           // keyword value
};
mp_obj_t result = mp_call_function_n_kw(func, 2, 1, call_args);
```

## Collections

### List Operations

```c
// Get list internals
size_t len;
mp_obj_t *items;
mp_obj_list_get(list_obj, &len, &items);

// Append
mp_obj_list_append(list_obj, new_item);

// Get item
mp_obj_t item = mp_obj_subscr(list_obj, mp_obj_new_int(index), MP_OBJ_SENTINEL);

// Set item  
mp_obj_subscr(list_obj, mp_obj_new_int(index), new_value);
```

### Dict Operations

```c
// Store key-value
mp_obj_dict_store(dict_obj, key, value);

// Get value (raises KeyError if not found)
mp_obj_t value = mp_obj_dict_get(dict_obj, key);

// Check if key exists
mp_map_elem_t *elem = mp_map_lookup(&dict->map, key, MP_MAP_LOOKUP);
if (elem != NULL) {
    // Key exists, value is elem->value
}
```

### Iteration

```c
// Get iterator
mp_obj_t iter = mp_getiter(iterable, NULL);

// Iterate
mp_obj_t item;
while ((item = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
    // Process item
}
```

## Exception Handling

### Raising Exceptions

```c
// Raise with type only
mp_raise_TypeError(NULL);
mp_raise_ValueError(NULL);
mp_raise_OSError(errno);

// Raise with message
mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("invalid value"));
mp_raise_msg_varg(&mp_type_TypeError, MP_ERROR_TEXT("expected %s"), "int");

// Common exception types
&mp_type_TypeError
&mp_type_ValueError
&mp_type_RuntimeError
&mp_type_OSError
&mp_type_KeyError
&mp_type_IndexError
&mp_type_AttributeError
&mp_type_StopIteration
&mp_type_ZeroDivisionError
```

### Try/Except Pattern

```c
// nlr = non-local return (MicroPython's exception mechanism)
static mp_obj_t safe_operation(mp_obj_t arg) {
    nlr_buf_t nlr;
    
    if (nlr_push(&nlr) == 0) {
        // TRY block
        mp_obj_t result = risky_operation(arg);
        nlr_pop();
        return result;
    } else {
        // EXCEPT block
        mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);
        
        // Check exception type
        if (mp_obj_is_subclass_fast(
                MP_OBJ_FROM_PTR(mp_obj_get_type(exc)),
                MP_OBJ_FROM_PTR(&mp_type_ValueError))) {
            // Handle ValueError
            return mp_const_none;
        }
        
        // Re-raise unknown exceptions
        nlr_jump(nlr.ret_val);
    }
}
```

### Finally Pattern

```c
static mp_obj_t with_cleanup(mp_obj_t resource) {
    nlr_buf_t nlr;
    mp_obj_t result = mp_const_none;
    bool success = false;
    
    if (nlr_push(&nlr) == 0) {
        result = use_resource(resource);
        success = true;
        nlr_pop();
    }
    
    // FINALLY - always runs
    cleanup_resource(resource);
    
    if (!success) {
        // Re-raise the exception
        nlr_jump(nlr.ret_val);
    }
    
    return result;
}
```

## Memory Management

### Allocation

```c
// Allocate from GC heap
void *m_malloc(size_t num_bytes);
void *m_malloc_maybe(size_t num_bytes);  // Returns NULL on failure
void *m_realloc(void *ptr, size_t new_num_bytes);
void m_free(void *ptr);

// Typed allocation
#define m_new(type, num) ((type *)m_malloc(sizeof(type) * (num)))
#define m_new0(type, num) ((type *)m_malloc0(sizeof(type) * (num)))  // Zero-initialized
#define m_new_obj(type) (m_new(type, 1))
```

### GC Considerations

```c
// MicroPython uses a tracing GC
// Objects on the GC heap are automatically managed
// Stack roots are automatically found

// For external memory (e.g., hardware buffers):
// Use mp_obj_new_bytearray_by_ref() to wrap external memory
// The GC won't free the external memory, but will track the wrapper
```

## CPython vs MicroPython

| Operation | CPython | MicroPython |
|-----------|---------|-------------|
| **Object type** | `PyObject *` | `mp_obj_t` |
| **Get int** | `PyLong_AsLong(obj)` | `mp_obj_get_int(obj)` |
| **New int** | `PyLong_FromLong(val)` | `mp_obj_new_int(val)` |
| **Get float** | `PyFloat_AsDouble(obj)` | `mp_obj_get_float(obj)` |
| **New float** | `PyFloat_FromDouble(val)` | `mp_obj_new_float(val)` |
| **Get string** | `PyUnicode_AsUTF8(obj)` | `mp_obj_str_get_str(obj)` |
| **New string** | `PyUnicode_FromString(s)` | `mp_obj_new_str(s, len)` |
| **Get attr** | `PyObject_GetAttr(obj, name)` | `mp_load_attr(obj, qstr)` |
| **Set attr** | `PyObject_SetAttr(obj, name, val)` | `mp_store_attr(obj, qstr, val)` |
| **Call** | `PyObject_CallObject(func, args)` | `mp_call_function_n_kw(...)` |
| **Type check** | `PyObject_IsInstance(obj, type)` | `mp_obj_is_type(obj, type)` |
| **Raise error** | `PyErr_SetString(exc, msg)` | `mp_raise_msg(&type, msg)` |
| **None** | `Py_None` | `mp_const_none` |
| **True/False** | `Py_True`/`Py_False` | `mp_const_true`/`mp_const_false` |
| **Incref** | `Py_INCREF(obj)` | N/A (GC managed) |
| **Decref** | `Py_DECREF(obj)` | N/A (GC managed) |

## See Also

- [01-architecture.md](01-architecture.md) - mypyc-micropython architecture
- [02-mypyc-reference.md](02-mypyc-reference.md) - How mypyc implements features
- [MicroPython C Modules Docs](https://docs.micropython.org/en/latest/develop/cmodules.html)
- [MicroPython Source: py/obj.h](https://github.com/micropython/micropython/blob/master/py/obj.h)
