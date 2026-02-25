#define _POSIX_C_SOURCE 200809L

#ifndef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
#define MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

typedef intptr_t mp_int_t;
typedef uintptr_t mp_uint_t;
typedef double mp_float_t;
typedef void *mp_obj_t;

typedef struct {
    mp_obj_t type;
} mp_obj_base_t;

typedef struct _mp_obj_type_t {
    int unused;
} mp_obj_type_t;

typedef struct {
    mp_obj_base_t base;
    mp_obj_t fun;
} mp_rom_obj_static_class_method_t;

static mp_obj_type_t mp_type_staticmethod = {0};
static mp_obj_type_t mp_type_classmethod = {0};

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
#define MP_MOCK_TAG_DICT (0xD1C7)

typedef struct {
    mp_obj_t key;
    mp_obj_t value;
} mp_map_elem_t;

typedef struct {
    size_t alloc;
    size_t used;
    mp_map_elem_t *table;
} mp_map_t;

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

typedef struct {
    int tag;
    size_t alloc;
    size_t used;
    mp_map_elem_t *table;
} mp_obj_dict_struct;

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

static inline mp_float_t mp_obj_get_float(mp_obj_t obj) {
    return mp_obj_float_get(obj);
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

static inline mp_obj_t mp_obj_new_tuple(size_t n, const mp_obj_t *items) {
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

#define MP_QSTR_NULL ((qstr)0)
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

    mp_obj_dict_struct *as_dict = (mp_obj_dict_struct *)container;
    if (as_dict->tag == MP_MOCK_TAG_DICT) {
        while (iter->idx < as_dict->alloc) {
            if (as_dict->table[iter->idx].key != MP_OBJ_NULL) {
                return as_dict->table[iter->idx++].key;
            }
            iter->idx++;
        }
        return MP_OBJ_NULL;
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
#define MP_OBJ_TO_PTR(o) ((void *)(o))
#define mp_obj_malloc(type_name, type_ptr) ((type_name *)calloc(1, sizeof(type_name)))

static inline void mp_arg_check_num(
    size_t n_args,
    size_t n_kw,
    size_t n_args_min,
    size_t n_args_max,
    bool takes_kw
) {
    (void)n_args;
    (void)n_kw;
    (void)n_args_min;
    (void)n_args_max;
    (void)takes_kw;
}

#define MP_MOCK_BUILTIN_TAG_MIN 1001
#define MP_MOCK_BUILTIN_TAG_MAX 1002
#define MP_MOCK_BUILTIN_TAG_SUM 1003
#define MP_MOCK_BUILTIN_TAG_SORTED 1004
#define MP_MOCK_TYPE_TAG_ENUMERATE 2001
#define MP_MOCK_TYPE_TAG_ZIP 2002
#define MP_MOCK_TYPE_TAG_LIST 2003

typedef struct {
    int tag;
} mp_builtin_obj_t;

static mp_builtin_obj_t mp_builtin_min_obj __attribute__((unused)) = { MP_MOCK_BUILTIN_TAG_MIN };
static mp_builtin_obj_t mp_builtin_max_obj __attribute__((unused)) = { MP_MOCK_BUILTIN_TAG_MAX };
static mp_builtin_obj_t mp_builtin_sum_obj __attribute__((unused)) = { MP_MOCK_BUILTIN_TAG_SUM };
static mp_builtin_obj_t mp_builtin_sorted_obj __attribute__((unused)) = { MP_MOCK_BUILTIN_TAG_SORTED };
static mp_builtin_obj_t mp_type_enumerate __attribute__((unused)) = { MP_MOCK_TYPE_TAG_ENUMERATE };
static mp_builtin_obj_t mp_type_zip __attribute__((unused)) = { MP_MOCK_TYPE_TAG_ZIP };
static mp_builtin_obj_t mp_type_list __attribute__((unused)) = { MP_MOCK_TYPE_TAG_LIST };

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

#define MP_MOCK_TAG_ENUMERATE_OBJ (0xE707)
#define MP_MOCK_TAG_ZIP_OBJ (0x21B0)

typedef struct {
    int tag;
    mp_obj_t iter;
    mp_int_t index;
} mp_obj_enumerate_struct;

typedef struct {
    int tag;
    size_t n_iters;
    mp_obj_t *iters;
} mp_obj_zip_struct;

static mp_obj_t mp_mock_enumerate_make(mp_obj_t iterable, mp_int_t start) {
    mp_obj_enumerate_struct *e = (mp_obj_enumerate_struct *)malloc(sizeof(*e));
    if (e == NULL) {
        mp_mock_abort("out of memory");
    }
    e->tag = MP_MOCK_TAG_ENUMERATE_OBJ;
    e->iter = mp_getiter(iterable, NULL);
    e->index = start;
    return (mp_obj_t)e;
}

static mp_obj_t mp_mock_enumerate_iternext(mp_obj_t self_in) {
    mp_obj_enumerate_struct *self = (mp_obj_enumerate_struct *)self_in;
    mp_obj_t next = mp_iternext(self->iter);
    if (next == MP_OBJ_STOP_ITERATION) {
        return MP_OBJ_STOP_ITERATION;
    }
    mp_obj_t items[] = { mp_obj_new_int(self->index++), next };
    return mp_obj_new_tuple(2, items);
}

static mp_obj_t mp_mock_zip_make(size_t n_args, const mp_obj_t *args) {
    mp_obj_zip_struct *z = (mp_obj_zip_struct *)malloc(sizeof(*z));
    if (z == NULL) {
        mp_mock_abort("out of memory");
    }
    z->tag = MP_MOCK_TAG_ZIP_OBJ;
    z->n_iters = n_args;
    z->iters = (mp_obj_t *)malloc(n_args * sizeof(mp_obj_t));
    if (z->iters == NULL && n_args > 0) {
        free(z);
        mp_mock_abort("out of memory");
    }
    for (size_t i = 0; i < n_args; i++) {
        z->iters[i] = mp_getiter(args[i], NULL);
    }
    return (mp_obj_t)z;
}

static mp_obj_t mp_mock_zip_iternext(mp_obj_t self_in) {
    mp_obj_zip_struct *self = (mp_obj_zip_struct *)self_in;
    mp_obj_t *items = (mp_obj_t *)malloc(self->n_iters * sizeof(mp_obj_t));
    if (items == NULL && self->n_iters > 0) {
        mp_mock_abort("out of memory");
    }
    for (size_t i = 0; i < self->n_iters; i++) {
        mp_obj_t next = mp_iternext(self->iters[i]);
        if (next == MP_OBJ_STOP_ITERATION) {
            free(items);
            return MP_OBJ_STOP_ITERATION;
        }
        items[i] = next;
    }
    mp_obj_t result = mp_obj_new_tuple(self->n_iters, items);
    free(items);
    return result;
}

static mp_obj_t mp_mock_sorted(mp_obj_t iterable) {
    mp_obj_list_struct *in_list = mp_mock_list_from_obj(iterable);
    mp_obj_t result = mp_obj_new_list(in_list->len, in_list->items);
    mp_obj_list_struct *out_list = mp_mock_list_from_obj(result);
    for (size_t i = 0; i < out_list->len; i++) {
        for (size_t j = i + 1; j < out_list->len; j++) {
            if (mp_obj_get_int(out_list->items[i]) > mp_obj_get_int(out_list->items[j])) {
                mp_obj_t tmp = out_list->items[i];
                out_list->items[i] = out_list->items[j];
                out_list->items[j] = tmp;
            }
        }
    }
    return result;
}

static mp_obj_t mp_mock_list_from_iter(mp_obj_t iterable) {
    mp_obj_t result = mp_obj_new_list(0, NULL);

    mp_obj_enumerate_struct *as_enum = (mp_obj_enumerate_struct *)iterable;
    if (as_enum->tag == MP_MOCK_TAG_ENUMERATE_OBJ) {
        mp_obj_t item;
        while ((item = mp_mock_enumerate_iternext(iterable)) != MP_OBJ_STOP_ITERATION) {
            mp_obj_list_append(result, item);
        }
        return result;
    }

    mp_obj_zip_struct *as_zip = (mp_obj_zip_struct *)iterable;
    if (as_zip->tag == MP_MOCK_TAG_ZIP_OBJ) {
        mp_obj_t item;
        while ((item = mp_mock_zip_iternext(iterable)) != MP_OBJ_STOP_ITERATION) {
            mp_obj_list_append(result, item);
        }
        return result;
    }

    mp_obj_t iter = mp_getiter(iterable, NULL);
    mp_obj_t item;
    while ((item = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_list_append(result, item);
    }
    return result;
}

static inline mp_obj_t mp_call_function_0(mp_obj_t fun) {
    mp_builtin_obj_t *builtin = (mp_builtin_obj_t *)fun;
    if (builtin->tag == MP_MOCK_TYPE_TAG_ZIP) {
        return mp_mock_zip_make(0, NULL);
    }
    mp_mock_abort("mp_call_function_0: unknown builtin");
    return mp_const_none;
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
    if (builtin->tag == MP_MOCK_BUILTIN_TAG_SORTED) {
        return mp_mock_sorted(arg);
    }
    if (builtin->tag == MP_MOCK_TYPE_TAG_ENUMERATE) {
        return mp_mock_enumerate_make(arg, 0);
    }
    if (builtin->tag == MP_MOCK_TYPE_TAG_ZIP) {
        mp_obj_t args[] = { arg };
        return mp_mock_zip_make(1, args);
    }
    if (builtin->tag == MP_MOCK_TYPE_TAG_LIST) {
        return mp_mock_list_from_iter(arg);
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
    if (builtin->tag == MP_MOCK_TYPE_TAG_ENUMERATE) {
        return mp_mock_enumerate_make(arg1, mp_obj_get_int(arg2));
    }
    if (builtin->tag == MP_MOCK_TYPE_TAG_ZIP) {
        mp_obj_t args[] = { arg1, arg2 };
        return mp_mock_zip_make(2, args);
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
    if (builtin->tag == MP_MOCK_TYPE_TAG_ZIP) {
        return mp_mock_zip_make(n_args, args);
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
#define MP_DEFINE_CONST_FUN_OBJ_VAR(obj_name, min, fun_name) static const int obj_name = 0
#define MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(obj_name, min, max, fun_name) \
    static const int obj_name = 0
#define MP_DEFINE_CONST_FUN_OBJ_KW(obj_name, min, fun_name) static const int obj_name = 0
#define MP_DEFINE_CONST_DICT(dict_name, table_name) const int dict_name = 0
#define MP_TYPE_FLAG_NONE (0)
#define MP_DEFINE_CONST_OBJ_TYPE(obj_name, qstr, flags, ...) const mp_obj_type_t obj_name = {0}
#define MP_REGISTER_MODULE(qstr, mod)

static inline bool mp_map_slot_is_filled(mp_map_t *map, size_t slot) {
    return map->table[slot].key != MP_OBJ_NULL;
}

static inline mp_obj_t mp_obj_new_dict(size_t n) {
    mp_obj_dict_struct *dict = (mp_obj_dict_struct *)malloc(sizeof(*dict));
    if (dict == NULL) {
        mp_mock_abort("out of memory while allocating dict object");
    }

    size_t alloc = n == 0 ? 4 : n * 2;
    dict->table = (mp_map_elem_t *)calloc(alloc, sizeof(mp_map_elem_t));
    if (dict->table == NULL) {
        free(dict);
        mp_mock_abort("out of memory while allocating dict table");
    }

    dict->tag = MP_MOCK_TAG_DICT;
    dict->alloc = alloc;
    dict->used = 0;
    return (mp_obj_t)dict;
}

static inline void mp_obj_dict_store(mp_obj_t dict_obj, mp_obj_t key, mp_obj_t value) {
    mp_obj_dict_struct *dict = (mp_obj_dict_struct *)dict_obj;
    if (dict->tag != MP_MOCK_TAG_DICT) {
        mp_mock_abort("mp_obj_dict_store: not a dict");
    }

    for (size_t i = 0; i < dict->alloc; i++) {
        if (dict->table[i].key == MP_OBJ_NULL) {
            dict->table[i].key = key;
            dict->table[i].value = value;
            dict->used++;
            return;
        }
        if (dict->table[i].key == key) {
            dict->table[i].value = value;
            return;
        }
    }
    mp_mock_abort("mp_obj_dict_store: dict full (should grow but not implemented)");
}

static inline mp_obj_t mp_obj_dict_get(mp_obj_t dict_obj, mp_obj_t key) {
    mp_obj_dict_struct *dict = (mp_obj_dict_struct *)dict_obj;
    if (dict->tag != MP_MOCK_TAG_DICT) {
        mp_mock_abort("mp_obj_dict_get: not a dict");
    }

    for (size_t i = 0; i < dict->alloc; i++) {
        if (dict->table[i].key == key) {
            return dict->table[i].value;
        }
    }
    return MP_OBJ_NULL;
}

static inline size_t mp_mock_dict_len(mp_obj_t dict_obj) {
    mp_obj_dict_struct *dict = (mp_obj_dict_struct *)dict_obj;
    if (dict->tag != MP_MOCK_TAG_DICT) {
        mp_mock_abort("mp_mock_dict_len: not a dict");
    }
    return dict->used;
}

#include <setjmp.h>

typedef struct _nlr_buf_t {
    jmp_buf buf;
    void *ret_val;
} nlr_buf_t;

static __thread nlr_buf_t *_nlr_top = NULL;

static inline int nlr_push(nlr_buf_t *nlr) {
    nlr->ret_val = NULL;
    nlr_buf_t *prev = _nlr_top;
    _nlr_top = nlr;
    int r = setjmp(nlr->buf);
    if (r != 0) {
        _nlr_top = prev;
    }
    return r;
}

static inline void nlr_pop(void) {
    if (_nlr_top != NULL) {
        nlr_buf_t *prev = (nlr_buf_t *)((char *)_nlr_top - sizeof(nlr_buf_t));
        _nlr_top = (_nlr_top == prev) ? NULL : prev;
    }
}

__attribute__((noreturn))
static inline void nlr_jump(void *val) {
    if (_nlr_top == NULL) {
        mp_mock_abort("nlr_jump called with no nlr_push");
    }
    _nlr_top->ret_val = val;
    longjmp(_nlr_top->buf, 1);
}

#define MP_MOCK_TAG_EXCEPTION (0xE4CE97)

typedef struct {
    int tag;
    int exc_type;
    char *message;
} mp_obj_exception_struct;

#define MP_EXC_TYPE_BASE_EXCEPTION 0
#define MP_EXC_TYPE_EXCEPTION 1
#define MP_EXC_TYPE_TYPE_ERROR 2
#define MP_EXC_TYPE_VALUE_ERROR 3
#define MP_EXC_TYPE_RUNTIME_ERROR 4
#define MP_EXC_TYPE_KEY_ERROR 5
#define MP_EXC_TYPE_INDEX_ERROR 6
#define MP_EXC_TYPE_ATTRIBUTE_ERROR 7
#define MP_EXC_TYPE_STOP_ITERATION 8
#define MP_EXC_TYPE_ZERO_DIVISION_ERROR 9
#define MP_EXC_TYPE_OVERFLOW_ERROR 10
#define MP_EXC_TYPE_MEMORY_ERROR 11
#define MP_EXC_TYPE_OS_ERROR 12
#define MP_EXC_TYPE_NOT_IMPLEMENTED_ERROR 13
#define MP_EXC_TYPE_ASSERTION_ERROR 14

#ifdef __GNUC__
#define MP_UNUSED __attribute__((unused))
#else
#define MP_UNUSED
#endif

static int mp_type_BaseException MP_UNUSED = MP_EXC_TYPE_BASE_EXCEPTION;
static int mp_type_Exception MP_UNUSED = MP_EXC_TYPE_EXCEPTION;
static int mp_type_TypeError MP_UNUSED = MP_EXC_TYPE_TYPE_ERROR;
static int mp_type_ValueError MP_UNUSED = MP_EXC_TYPE_VALUE_ERROR;
static int mp_type_RuntimeError MP_UNUSED = MP_EXC_TYPE_RUNTIME_ERROR;
static int mp_type_KeyError MP_UNUSED = MP_EXC_TYPE_KEY_ERROR;
static int mp_type_IndexError MP_UNUSED = MP_EXC_TYPE_INDEX_ERROR;
static int mp_type_AttributeError MP_UNUSED = MP_EXC_TYPE_ATTRIBUTE_ERROR;
static int mp_type_StopIteration MP_UNUSED = MP_EXC_TYPE_STOP_ITERATION;
static int mp_type_ZeroDivisionError MP_UNUSED = MP_EXC_TYPE_ZERO_DIVISION_ERROR;
static int mp_type_OverflowError MP_UNUSED = MP_EXC_TYPE_OVERFLOW_ERROR;
static int mp_type_MemoryError MP_UNUSED = MP_EXC_TYPE_MEMORY_ERROR;
static int mp_type_OSError MP_UNUSED = MP_EXC_TYPE_OS_ERROR;
static int mp_type_NotImplementedError MP_UNUSED = MP_EXC_TYPE_NOT_IMPLEMENTED_ERROR;
static int mp_type_AssertionError MP_UNUSED = MP_EXC_TYPE_ASSERTION_ERROR;

static inline mp_obj_t mp_obj_new_exception_msg(int *exc_type, const char *msg) {
    mp_obj_exception_struct *exc = (mp_obj_exception_struct *)malloc(sizeof(mp_obj_exception_struct));
    exc->tag = MP_MOCK_TAG_EXCEPTION;
    exc->exc_type = *exc_type;
    exc->message = msg ? strdup(msg) : NULL;
    return (mp_obj_t)exc;
}

static inline int *mp_obj_get_type(mp_obj_t obj) {
    if (!mp_mock_is_special_const(obj) && !MP_OBJ_IS_SMALL_INT(obj)) {
        mp_obj_exception_struct *exc = (mp_obj_exception_struct *)obj;
        if (exc->tag == MP_MOCK_TAG_EXCEPTION) {
            if (exc->exc_type == MP_EXC_TYPE_ZERO_DIVISION_ERROR) return &mp_type_ZeroDivisionError;
            if (exc->exc_type == MP_EXC_TYPE_VALUE_ERROR) return &mp_type_ValueError;
            if (exc->exc_type == MP_EXC_TYPE_TYPE_ERROR) return &mp_type_TypeError;
            if (exc->exc_type == MP_EXC_TYPE_RUNTIME_ERROR) return &mp_type_RuntimeError;
            if (exc->exc_type == MP_EXC_TYPE_KEY_ERROR) return &mp_type_KeyError;
            if (exc->exc_type == MP_EXC_TYPE_INDEX_ERROR) return &mp_type_IndexError;
            return &mp_type_Exception;
        }
    }
    return &mp_type_Exception;
}

static inline bool mp_obj_is_subclass_fast(mp_obj_t obj_type, mp_obj_t base_type) {
    int *exc_type = (int *)MP_OBJ_TO_PTR(obj_type);
    int *base = (int *)MP_OBJ_TO_PTR(base_type);
    if (exc_type == base) return true;
    if (base == &mp_type_Exception) {
        return *exc_type != MP_EXC_TYPE_BASE_EXCEPTION;
    }
    if (base == &mp_type_BaseException) return true;
    return false;
}

#define MP_ERROR_TEXT(s) (s)

__attribute__((noreturn))
static inline void mp_raise_msg(int *exc_type, const char *msg) {
    mp_obj_t exc = mp_obj_new_exception_msg(exc_type, msg);
    nlr_jump(exc);
}

__attribute__((noreturn))
static inline void mp_raise_msg_varg(int *exc_type, const char *fmt, ...) {
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    mp_raise_msg(exc_type, buf);
}

#define MP_OBJ_FROM_PTR(p) ((mp_obj_t)(p))
#define MP_OBJ_TO_PTR(o) ((void *)(o))

#endif
