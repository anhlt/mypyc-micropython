#ifndef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
#define MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef intptr_t mp_int_t;
typedef uintptr_t mp_uint_t;
typedef double mp_float_t;
typedef void *mp_obj_t;

typedef struct {
    mp_obj_t type;
} mp_obj_base_t;

typedef struct {
    mp_obj_t key;
    mp_obj_t value;
} mp_rom_map_elem_t;

typedef struct {
    mp_obj_base_t base;
} mp_obj_dict_t;

typedef struct {
    mp_obj_base_t base;
    mp_obj_dict_t *globals;
} mp_obj_module_t;

/* Match real MicroPython REPR_A small-int tagging (py/obj.h) */
#define MP_OBJ_NEW_SMALL_INT(small_int) ((mp_obj_t)((((mp_uint_t)(small_int)) << 1) | 1))
#define MP_OBJ_SMALL_INT_VALUE(o) (((mp_int_t)(o)) >> 1)
#define MP_OBJ_IS_SMALL_INT(o) ((((mp_int_t)(o)) & 1) != 0)

/* Match real MicroPython immediate object tagging (py/obj.h, MICROPY_OBJ_IMMEDIATE_OBJS) */
#define MP_OBJ_NEW_IMMEDIATE_OBJ(val) ((mp_obj_t)(((val) << 3) | 6))

/* Match real MicroPython sentinel values (py/obj.h, non-debug) */
#define MP_OBJ_NULL             ((mp_obj_t)(uintptr_t)0)
#define MP_OBJ_SENTINEL         ((mp_obj_t)(uintptr_t)4)
#define MP_OBJ_STOP_ITERATION   MP_OBJ_NULL

/* Match real MicroPython constant objects (py/obj.h) */
#define mp_const_none  MP_OBJ_NEW_IMMEDIATE_OBJ(0)   /* = 6  */
#define mp_const_false MP_OBJ_NEW_IMMEDIATE_OBJ(1)    /* = 14 */
#define mp_const_true  MP_OBJ_NEW_IMMEDIATE_OBJ(3)    /* = 30 */

static inline bool mp_obj_is_true(mp_obj_t obj) {
    if (obj == mp_const_true) return true;
    if (obj == mp_const_false || obj == mp_const_none) return false;
    if (MP_OBJ_IS_SMALL_INT(obj)) {
        return MP_OBJ_SMALL_INT_VALUE(obj) != 0;
    }
    return obj != MP_OBJ_NULL;
}

#define MICROPY_FLOAT_IMPL_NONE (0)
#define MICROPY_FLOAT_IMPL (MICROPY_FLOAT_IMPL_NONE)

#define MP_MOCK_TAG_FLOAT (0xF10A7)
#define MP_MOCK_TAG_LIST (0x1157)
#define MP_MOCK_TAG_STR (0x57A1)
#define MP_MOCK_TAG_TUPLE (0x70B1E)
#define MP_MOCK_TAG_SET (0x5E7)

typedef struct {
    int tag;
    mp_float_t value;
} mp_obj_float_struct;

typedef struct {
    int tag;
    size_t alloc;
    size_t len;
    mp_obj_t *items;
} mp_obj_list_struct;

typedef struct {
    int tag;
    size_t len;
    char *data;
} mp_obj_str_struct;

typedef struct {
    int tag;
    size_t len;
    mp_obj_t *items;
} mp_obj_tuple_struct;

typedef struct {
    int tag;
    size_t alloc;
    size_t len;
    mp_obj_t *items;
} mp_obj_set_struct;

static void *mp_type_module = NULL;

static inline void mp_mock_abort(const char *message) {
    (void)fprintf(stderr, "mock runtime error: %s\n", message);
    abort();
}

static inline bool mp_mock_is_special_const(mp_obj_t obj) {
    uintptr_t val = (uintptr_t)obj;
    return obj == MP_OBJ_NULL || obj == MP_OBJ_SENTINEL ||
           (val & 7) == 6;  /* immediate objects: none, false, true */
}

static inline mp_obj_list_struct *mp_mock_list_from_obj(mp_obj_t obj) {
    if (MP_OBJ_IS_SMALL_INT(obj) || mp_mock_is_special_const(obj)) {
        mp_mock_abort("expected list object");
    }

    mp_obj_list_struct *list = (mp_obj_list_struct *)obj;
    if (list->tag != MP_MOCK_TAG_LIST) {
        mp_mock_abort("object is not a list");
    }
    return list;
}

static inline size_t mp_mock_normalize_index(mp_int_t idx, size_t len) {
    mp_int_t normalized = idx;
    if (normalized < 0) {
        normalized += (mp_int_t)len;
    }

    if (normalized < 0 || (size_t)normalized >= len) {
        mp_mock_abort("list index out of range");
    }

    return (size_t)normalized;
}

static inline void mp_mock_list_ensure_capacity(mp_obj_list_struct *list, size_t needed) {
    if (needed <= list->alloc) {
        return;
    }

    size_t new_alloc = list->alloc == 0 ? 4 : list->alloc;
    while (new_alloc < needed) {
        new_alloc *= 2;
    }

    mp_obj_t *new_items = (mp_obj_t *)realloc(list->items, new_alloc * sizeof(*new_items));
    if (new_items == NULL) {
        mp_mock_abort("out of memory while growing list");
    }

    list->items = new_items;
    list->alloc = new_alloc;
}

static inline mp_obj_t mp_obj_new_int(mp_int_t val) {
    return MP_OBJ_NEW_SMALL_INT(val);
}

static inline mp_int_t mp_obj_get_int(mp_obj_t obj) {
    if (MP_OBJ_IS_SMALL_INT(obj)) {
        return MP_OBJ_SMALL_INT_VALUE(obj);
    }
    if (obj == mp_const_true) {
        return 1;
    }
    if (obj == mp_const_false) {
        return 0;
    }
    if (!mp_mock_is_special_const(obj)) {
        mp_obj_float_struct *as_float = (mp_obj_float_struct *)obj;
        if (as_float->tag == MP_MOCK_TAG_FLOAT) {
            return (mp_int_t)as_float->value;
        }
    }
    mp_mock_abort("cannot convert object to int");
    return 0;
}

static inline mp_obj_t mp_obj_new_float(mp_float_t val) {
    mp_obj_float_struct *obj = (mp_obj_float_struct *)malloc(sizeof(*obj));
    if (obj == NULL) {
        mp_mock_abort("out of memory while allocating float");
    }
    obj->tag = MP_MOCK_TAG_FLOAT;
    obj->value = val;
    return (mp_obj_t)obj;
}

static inline bool mp_obj_is_float(mp_obj_t obj) {
    if (MP_OBJ_IS_SMALL_INT(obj) || mp_mock_is_special_const(obj)) {
        return false;
    }
    mp_obj_float_struct *as_float = (mp_obj_float_struct *)obj;
    return as_float->tag == MP_MOCK_TAG_FLOAT;
}

static inline mp_float_t mp_obj_float_get(mp_obj_t obj) {
    if (MP_OBJ_IS_SMALL_INT(obj)) {
        return (mp_float_t)MP_OBJ_SMALL_INT_VALUE(obj);
    }
    if (mp_obj_is_float(obj)) {
        return ((mp_obj_float_struct *)obj)->value;
    }
    mp_mock_abort("cannot convert object to float");
    return 0.0;
}

static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}

static inline mp_obj_t mp_obj_new_str(const char *data, size_t len) {
    mp_obj_str_struct *obj = (mp_obj_str_struct *)malloc(sizeof(*obj));
    if (obj == NULL) {
        mp_mock_abort("out of memory while allocating string object");
    }

    obj->data = (char *)malloc(len + 1);
    if (obj->data == NULL) {
        free(obj);
        mp_mock_abort("out of memory while allocating string data");
    }

    if (len > 0) {
        memcpy(obj->data, data, len);
    }
    obj->data[len] = '\0';
    obj->tag = MP_MOCK_TAG_STR;
    obj->len = len;
    return (mp_obj_t)obj;
}

static inline mp_obj_t mp_obj_new_list(size_t n, mp_obj_t *items) {
    mp_obj_list_struct *list = (mp_obj_list_struct *)malloc(sizeof(*list));
    if (list == NULL) {
        mp_mock_abort("out of memory while allocating list object");
    }

    size_t alloc = n == 0 ? 4 : n;
    list->items = (mp_obj_t *)malloc(alloc * sizeof(*list->items));
    if (list->items == NULL) {
        free(list);
        mp_mock_abort("out of memory while allocating list items");
    }

    if (n > 0 && items != NULL) {
        memcpy(list->items, items, n * sizeof(*list->items));
    }

    list->tag = MP_MOCK_TAG_LIST;
    list->len = n;
    list->alloc = alloc;
    return (mp_obj_t)list;
}

static inline mp_obj_t mp_obj_new_tuple(size_t n, mp_obj_t *items) {
    mp_obj_tuple_struct *tuple = (mp_obj_tuple_struct *)malloc(sizeof(*tuple));
    if (tuple == NULL) {
        mp_mock_abort("out of memory while allocating tuple object");
    }

    if (n > 0) {
        tuple->items = (mp_obj_t *)malloc(n * sizeof(*tuple->items));
        if (tuple->items == NULL) {
            free(tuple);
            mp_mock_abort("out of memory while allocating tuple items");
        }
        if (items != NULL) {
            memcpy(tuple->items, items, n * sizeof(*tuple->items));
        }
    } else {
        tuple->items = NULL;
    }

    tuple->tag = MP_MOCK_TAG_TUPLE;
    tuple->len = n;
    return (mp_obj_t)tuple;
}

static inline bool mp_mock_is_tuple(mp_obj_t obj) {
    if (MP_OBJ_IS_SMALL_INT(obj) || mp_mock_is_special_const(obj)) {
        return false;
    }
    mp_obj_tuple_struct *as_tuple = (mp_obj_tuple_struct *)obj;
    return as_tuple->tag == MP_MOCK_TAG_TUPLE;
}

static inline mp_obj_t mp_obj_new_set(size_t n, mp_obj_t *items) {
    mp_obj_set_struct *set = (mp_obj_set_struct *)malloc(sizeof(*set));
    if (set == NULL) {
        mp_mock_abort("out of memory while allocating set object");
    }

    size_t alloc = n == 0 ? 4 : n;
    set->items = (mp_obj_t *)malloc(alloc * sizeof(*set->items));
    if (set->items == NULL) {
        free(set);
        mp_mock_abort("out of memory while allocating set items");
    }

    set->tag = MP_MOCK_TAG_SET;
    set->len = 0;
    set->alloc = alloc;

    if (n > 0 && items != NULL) {
        for (size_t i = 0; i < n; i++) {
            bool found = false;
            for (size_t j = 0; j < set->len; j++) {
                if (mp_obj_get_int(set->items[j]) == mp_obj_get_int(items[i])) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                set->items[set->len++] = items[i];
            }
        }
    }

    return (mp_obj_t)set;
}

static inline bool mp_mock_is_set(mp_obj_t obj) {
    if (MP_OBJ_IS_SMALL_INT(obj) || mp_mock_is_special_const(obj)) {
        return false;
    }
    mp_obj_set_struct *as_set = (mp_obj_set_struct *)obj;
    return as_set->tag == MP_MOCK_TAG_SET;
}

static inline void mp_obj_set_store(mp_obj_t set_obj, mp_obj_t item) {
    if (!mp_mock_is_set(set_obj)) {
        mp_mock_abort("expected set object");
    }
    mp_obj_set_struct *set = (mp_obj_set_struct *)set_obj;

    for (size_t i = 0; i < set->len; i++) {
        if (mp_obj_get_int(set->items[i]) == mp_obj_get_int(item)) {
            return;
        }
    }

    if (set->len >= set->alloc) {
        size_t new_alloc = set->alloc == 0 ? 4 : set->alloc * 2;
        mp_obj_t *new_items = (mp_obj_t *)realloc(set->items, new_alloc * sizeof(*new_items));
        if (new_items == NULL) {
            mp_mock_abort("out of memory while growing set");
        }
        set->items = new_items;
        set->alloc = new_alloc;
    }

    set->items[set->len++] = item;
}

static inline mp_obj_t mp_obj_len(mp_obj_t obj) {
    if (MP_OBJ_IS_SMALL_INT(obj) || mp_mock_is_special_const(obj)) {
        mp_mock_abort("len() unsupported for this object");
    }

    mp_obj_list_struct *as_list = (mp_obj_list_struct *)obj;
    if (as_list->tag == MP_MOCK_TAG_LIST) {
        return mp_obj_new_int((mp_int_t)as_list->len);
    }

    mp_obj_str_struct *as_str = (mp_obj_str_struct *)obj;
    if (as_str->tag == MP_MOCK_TAG_STR) {
        return mp_obj_new_int((mp_int_t)as_str->len);
    }

    mp_obj_tuple_struct *as_tuple = (mp_obj_tuple_struct *)obj;
    if (as_tuple->tag == MP_MOCK_TAG_TUPLE) {
        return mp_obj_new_int((mp_int_t)as_tuple->len);
    }

    mp_obj_set_struct *as_set = (mp_obj_set_struct *)obj;
    if (as_set->tag == MP_MOCK_TAG_SET) {
        return mp_obj_new_int((mp_int_t)as_set->len);
    }

    mp_mock_abort("len() unsupported for this object");
    return mp_const_none;
}

static inline mp_obj_t mp_obj_subscr(mp_obj_t obj, mp_obj_t idx, mp_obj_t val) {
    if (MP_OBJ_IS_SMALL_INT(obj) || mp_mock_is_special_const(obj)) {
        mp_mock_abort("subscript unsupported for this object");
    }

    mp_obj_list_struct *as_list = (mp_obj_list_struct *)obj;
    if (as_list->tag == MP_MOCK_TAG_LIST) {
        size_t pos = mp_mock_normalize_index(mp_obj_get_int(idx), as_list->len);
        if (val == MP_OBJ_SENTINEL) {
            return as_list->items[pos];
        }
        as_list->items[pos] = val;
        return mp_const_none;
    }

    mp_obj_tuple_struct *as_tuple = (mp_obj_tuple_struct *)obj;
    if (as_tuple->tag == MP_MOCK_TAG_TUPLE) {
        mp_int_t i = mp_obj_get_int(idx);
        if (i < 0) {
            i += (mp_int_t)as_tuple->len;
        }
        if (i < 0 || (size_t)i >= as_tuple->len) {
            mp_mock_abort("tuple index out of range");
        }
        if (val != MP_OBJ_SENTINEL) {
            mp_mock_abort("tuples are immutable");
        }
        return as_tuple->items[i];
    }

    mp_mock_abort("subscript unsupported for this object");
    return mp_const_none;
}

static inline mp_obj_t mp_obj_list_append(mp_obj_t list_obj, mp_obj_t item) {
    mp_obj_list_struct *list = mp_mock_list_from_obj(list_obj);
    mp_mock_list_ensure_capacity(list, list->len + 1);
    list->items[list->len] = item;
    list->len += 1;
    return mp_const_none;
}

typedef uintptr_t qstr;

typedef enum {
    MP_BINARY_OP_ADD,
    MP_BINARY_OP_SUBTRACT,
    MP_BINARY_OP_MULTIPLY,
    MP_BINARY_OP_IN,
} mp_binary_op_t;

static inline mp_obj_t mp_binary_op(mp_binary_op_t op, mp_obj_t lhs, mp_obj_t rhs) {
    if (op == MP_BINARY_OP_IN) {
        if (!MP_OBJ_IS_SMALL_INT(rhs) && !mp_mock_is_special_const(rhs)) {
            mp_obj_tuple_struct *as_tuple = (mp_obj_tuple_struct *)rhs;
            if (as_tuple->tag == MP_MOCK_TAG_TUPLE) {
                mp_int_t needle = mp_obj_get_int(lhs);
                for (size_t i = 0; i < as_tuple->len; i++) {
                    if (mp_obj_get_int(as_tuple->items[i]) == needle) {
                        return mp_const_true;
                    }
                }
                return mp_const_false;
            }

            mp_obj_set_struct *as_set = (mp_obj_set_struct *)rhs;
            if (as_set->tag == MP_MOCK_TAG_SET) {
                mp_int_t needle = mp_obj_get_int(lhs);
                for (size_t i = 0; i < as_set->len; i++) {
                    if (mp_obj_get_int(as_set->items[i]) == needle) {
                        return mp_const_true;
                    }
                }
                return mp_const_false;
            }

            mp_obj_list_struct *as_list = (mp_obj_list_struct *)rhs;
            if (as_list->tag == MP_MOCK_TAG_LIST) {
                mp_int_t needle = mp_obj_get_int(lhs);
                for (size_t i = 0; i < as_list->len; i++) {
                    if (mp_obj_get_int(as_list->items[i]) == needle) {
                        return mp_const_true;
                    }
                }
                return mp_const_false;
            }
        }
        mp_mock_abort("mp_binary_op: 'in' unsupported for this type");
    }

    if (op == MP_BINARY_OP_ADD) {
        if (mp_mock_is_tuple(lhs) && mp_mock_is_tuple(rhs)) {
            mp_obj_tuple_struct *t1 = (mp_obj_tuple_struct *)lhs;
            mp_obj_tuple_struct *t2 = (mp_obj_tuple_struct *)rhs;
            size_t new_len = t1->len + t2->len;
            mp_obj_t *new_items = (mp_obj_t *)malloc(new_len * sizeof(*new_items));
            if (new_items == NULL) {
                mp_mock_abort("out of memory");
            }
            memcpy(new_items, t1->items, t1->len * sizeof(*new_items));
            memcpy(new_items + t1->len, t2->items, t2->len * sizeof(*new_items));
            mp_obj_t result = mp_obj_new_tuple(new_len, new_items);
            free(new_items);
            return result;
        }
        return mp_obj_new_int(mp_obj_get_int(lhs) + mp_obj_get_int(rhs));
    }

    if (op == MP_BINARY_OP_MULTIPLY) {
        if (mp_mock_is_tuple(lhs) && MP_OBJ_IS_SMALL_INT(rhs)) {
            mp_obj_tuple_struct *t = (mp_obj_tuple_struct *)lhs;
            mp_int_t n = mp_obj_get_int(rhs);
            if (n <= 0) {
                return mp_obj_new_tuple(0, NULL);
            }
            size_t new_len = t->len * (size_t)n;
            mp_obj_t *new_items = (mp_obj_t *)malloc(new_len * sizeof(*new_items));
            if (new_items == NULL) {
                mp_mock_abort("out of memory");
            }
            for (mp_int_t i = 0; i < n; i++) {
                memcpy(new_items + (size_t)i * t->len, t->items, t->len * sizeof(*new_items));
            }
            mp_obj_t result = mp_obj_new_tuple(new_len, new_items);
            free(new_items);
            return result;
        }
        return mp_obj_new_int(mp_obj_get_int(lhs) * mp_obj_get_int(rhs));
    }

    mp_mock_abort("mp_binary_op: unsupported operation");
    return mp_const_none;
}

#define MP_QSTR_pop   ((qstr)0x1001)
#define MP_QSTR_append ((qstr)0x1002)

#define MP_MOCK_TAG_ITER (0x173A)

typedef struct {
    int tag;
    mp_obj_t container;
    size_t idx;
} mp_obj_iter_struct;

typedef mp_obj_iter_struct mp_obj_iter_buf_t;

static inline mp_obj_t mp_getiter(mp_obj_t obj, void *buf) {
    (void)buf;
    mp_obj_iter_struct *iter = (mp_obj_iter_struct *)malloc(sizeof(*iter));
    if (iter == NULL) {
        mp_mock_abort("out of memory while allocating iterator");
    }
    iter->tag = MP_MOCK_TAG_ITER;
    iter->container = obj;
    iter->idx = 0;
    return (mp_obj_t)iter;
}

static inline mp_obj_t mp_iternext(mp_obj_t iter_obj) {
    mp_obj_iter_struct *iter = (mp_obj_iter_struct *)iter_obj;
    if (iter->tag != MP_MOCK_TAG_ITER) {
        mp_mock_abort("expected iterator");
    }

    mp_obj_t container = iter->container;
    if (MP_OBJ_IS_SMALL_INT(container) || mp_mock_is_special_const(container)) {
        return MP_OBJ_NULL;
    }

    mp_obj_tuple_struct *as_tuple = (mp_obj_tuple_struct *)container;
    if (as_tuple->tag == MP_MOCK_TAG_TUPLE) {
        if (iter->idx >= as_tuple->len) {
            return MP_OBJ_NULL;
        }
        return as_tuple->items[iter->idx++];
    }

    mp_obj_set_struct *as_set = (mp_obj_set_struct *)container;
    if (as_set->tag == MP_MOCK_TAG_SET) {
        if (iter->idx >= as_set->len) {
            return MP_OBJ_NULL;
        }
        return as_set->items[iter->idx++];
    }

    mp_obj_list_struct *as_list = (mp_obj_list_struct *)container;
    if (as_list->tag == MP_MOCK_TAG_LIST) {
        if (iter->idx >= as_list->len) {
            return MP_OBJ_NULL;
        }
        return as_list->items[iter->idx++];
    }

    return MP_OBJ_NULL;
}

static inline void mp_unpack_sequence(mp_obj_t seq, size_t num, mp_obj_t *dest) {
    if (MP_OBJ_IS_SMALL_INT(seq) || mp_mock_is_special_const(seq)) {
        mp_mock_abort("cannot unpack this object");
    }

    mp_obj_tuple_struct *as_tuple = (mp_obj_tuple_struct *)seq;
    if (as_tuple->tag == MP_MOCK_TAG_TUPLE) {
        if (as_tuple->len != num) {
            mp_mock_abort("wrong number of values to unpack");
        }
        for (size_t i = 0; i < num; i++) {
            dest[i] = as_tuple->items[i];
        }
        return;
    }

    mp_obj_list_struct *as_list = (mp_obj_list_struct *)seq;
    if (as_list->tag == MP_MOCK_TAG_LIST) {
        if (as_list->len != num) {
            mp_mock_abort("wrong number of values to unpack");
        }
        for (size_t i = 0; i < num; i++) {
            dest[i] = as_list->items[i];
        }
        return;
    }

    mp_mock_abort("cannot unpack this object");
}

static inline mp_obj_t mp_mock_list_pop_impl(size_t n_args, const mp_obj_t *args) {
    mp_obj_list_struct *list = mp_mock_list_from_obj(args[0]);
    if (list->len == 0) {
        mp_mock_abort("pop from empty list");
    }

    size_t pos;
    if (n_args == 1) {
        pos = list->len - 1;
    } else {
        pos = mp_mock_normalize_index(mp_obj_get_int(args[1]), list->len);
    }

    mp_obj_t popped = list->items[pos];
    if (pos + 1 < list->len) {
        memmove(&list->items[pos],
                &list->items[pos + 1],
                (list->len - pos - 1) * sizeof(*list->items));
    }
    list->len -= 1;
    return popped;
}

typedef mp_obj_t (*mp_mock_method_fun_t)(size_t n_args, const mp_obj_t *args);

static inline void mp_load_method(mp_obj_t base, qstr attr, mp_obj_t *dest) {
    if (MP_OBJ_IS_SMALL_INT(base) || mp_mock_is_special_const(base)) {
        mp_mock_abort("mp_load_method: cannot load method on non-object");
    }

    mp_obj_list_struct *as_list = (mp_obj_list_struct *)base;
    if (as_list->tag == MP_MOCK_TAG_LIST && attr == MP_QSTR_pop) {
        dest[0] = (mp_obj_t)mp_mock_list_pop_impl;
        dest[1] = base;
        return;
    }

    mp_mock_abort("mp_load_method: method not found");
}

static inline mp_obj_t mp_call_method_n_kw(size_t n_args, size_t n_kw, const mp_obj_t *args) {
    (void)n_kw;
    mp_mock_method_fun_t method = (mp_mock_method_fun_t)args[0];
    mp_obj_t self = args[1];

    mp_obj_t call_args[3];
    call_args[0] = self;
    size_t total = 1 + n_args;
    for (size_t i = 0; i < n_args; i++) {
        call_args[1 + i] = args[2 + i];
    }

    return method(total, call_args);
}

#define MP_OBJ_FROM_PTR(p) ((mp_obj_t)(p))

#define MP_MOCK_BUILTIN_TAG_MIN 1001
#define MP_MOCK_BUILTIN_TAG_MAX 1002
#define MP_MOCK_BUILTIN_TAG_SUM 1003

typedef struct {
    int tag;
} mp_builtin_obj_t;

static mp_builtin_obj_t mp_builtin_min_obj __attribute__((unused)) = { MP_MOCK_BUILTIN_TAG_MIN };
static mp_builtin_obj_t mp_builtin_max_obj __attribute__((unused)) = { MP_MOCK_BUILTIN_TAG_MAX };
static mp_builtin_obj_t mp_builtin_sum_obj __attribute__((unused)) = { MP_MOCK_BUILTIN_TAG_SUM };

static mp_obj_t mp_mock_builtin_min(size_t n_args, const mp_obj_t *args) {
    if (n_args < 2) {
        mp_mock_abort("min() requires at least 2 arguments");
    }
    mp_int_t result = mp_obj_get_int(args[0]);
    for (size_t i = 1; i < n_args; i++) {
        mp_int_t val = mp_obj_get_int(args[i]);
        if (val < result) {
            result = val;
        }
    }
    return mp_obj_new_int(result);
}

static mp_obj_t mp_mock_builtin_max(size_t n_args, const mp_obj_t *args) {
    if (n_args < 2) {
        mp_mock_abort("max() requires at least 2 arguments");
    }
    mp_int_t result = mp_obj_get_int(args[0]);
    for (size_t i = 1; i < n_args; i++) {
        mp_int_t val = mp_obj_get_int(args[i]);
        if (val > result) {
            result = val;
        }
    }
    return mp_obj_new_int(result);
}

static mp_obj_t mp_mock_builtin_sum(size_t n_args, const mp_obj_t *args) {
    mp_int_t total = 0;
    if (n_args >= 2) {
        total = mp_obj_get_int(args[1]);
    }
    mp_obj_list_struct *list = mp_mock_list_from_obj(args[0]);
    for (size_t i = 0; i < list->len; i++) {
        total += mp_obj_get_int(list->items[i]);
    }
    return mp_obj_new_int(total);
}

static inline mp_obj_t mp_call_function_1(mp_obj_t fun, mp_obj_t arg) {
    mp_builtin_obj_t *builtin = (mp_builtin_obj_t *)fun;
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_MIN) {
        mp_mock_abort("min() requires at least 2 arguments");
    }
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_MAX) {
        mp_mock_abort("max() requires at least 2 arguments");
    }
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_SUM) {
        mp_obj_t args[1] = { arg };
        return mp_mock_builtin_sum(1, args);
    }
    mp_mock_abort("mp_call_function_1: unknown builtin");
    return mp_const_none;
}

static inline mp_obj_t mp_call_function_2(mp_obj_t fun, mp_obj_t arg1, mp_obj_t arg2) {
    mp_builtin_obj_t *builtin = (mp_builtin_obj_t *)fun;
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_SUM) {
        mp_obj_t args[2] = { arg1, arg2 };
        return mp_mock_builtin_sum(2, args);
    }
    mp_mock_abort("mp_call_function_2: not implemented in mock");
    return mp_const_none;
}

static inline mp_obj_t mp_call_function_n_kw(mp_obj_t fun, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    (void)n_kw;
    mp_builtin_obj_t *builtin = (mp_builtin_obj_t *)fun;
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_MIN) {
        return mp_mock_builtin_min(n_args, args);
    }
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_MAX) {
        return mp_mock_builtin_max(n_args, args);
    }
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_SUM) {
        return mp_mock_builtin_sum(n_args, args);
    }
    mp_mock_abort("mp_call_function_n_kw: unknown builtin");
    return mp_const_none;
}

#define MP_ROM_QSTR(x) ((mp_obj_t)(uintptr_t)0)
#define MP_ROM_PTR(x) ((mp_obj_t)(x))

#define MP_DEFINE_CONST_FUN_OBJ_0(obj_name, fun_name) static const int obj_name = 0
#define MP_DEFINE_CONST_FUN_OBJ_1(obj_name, fun_name) static const int obj_name = 0
#define MP_DEFINE_CONST_FUN_OBJ_2(obj_name, fun_name) static const int obj_name = 0
#define MP_DEFINE_CONST_FUN_OBJ_3(obj_name, fun_name) static const int obj_name = 0
#define MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(obj_name, min, max, fun_name) \
    static const int obj_name = 0
#define MP_DEFINE_CONST_DICT(dict_name, table_name) static const int dict_name = 0
#define MP_REGISTER_MODULE(qstr, mod)

#endif
