#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _container_attrs_Container_obj_t container_attrs_Container_obj_t;
typedef struct _container_attrs_Inner_obj_t container_attrs_Inner_obj_t;
typedef struct _container_attrs_Outer_obj_t container_attrs_Outer_obj_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _container_attrs_Container_obj_t {
    mp_obj_base_t base;
    mp_obj_t items;
    mp_obj_t mapping;
    mp_obj_t unique;
};

struct _container_attrs_Inner_obj_t {
    mp_obj_base_t base;
    mp_obj_t items;
    mp_obj_t data;
};

struct _container_attrs_Outer_obj_t {
    mp_obj_base_t base;
    mp_obj_t inner;
    mp_obj_t name;
};


static mp_obj_t container_attrs_get_items(mp_obj_t c_obj) {
    mp_obj_t c = c_obj;

    return ((container_attrs_Container_obj_t *)MP_OBJ_TO_PTR(c))->items;
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_get_items_obj, container_attrs_get_items);
static mp_obj_t container_attrs_get_mapping(mp_obj_t c_obj) {
    mp_obj_t c = c_obj;

    return ((container_attrs_Container_obj_t *)MP_OBJ_TO_PTR(c))->mapping;
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_get_mapping_obj, container_attrs_get_mapping);
static mp_obj_t container_attrs_get_unique(mp_obj_t c_obj) {
    mp_obj_t c = c_obj;

    return ((container_attrs_Container_obj_t *)MP_OBJ_TO_PTR(c))->unique;
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_get_unique_obj, container_attrs_get_unique);
static mp_obj_t container_attrs_get_first_item(mp_obj_t c_obj) {
    mp_obj_t c = c_obj;

    return mp_obj_subscr(((container_attrs_Container_obj_t *)MP_OBJ_TO_PTR(c))->items, mp_obj_new_int(0), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_get_first_item_obj, container_attrs_get_first_item);
static mp_obj_t container_attrs_get_mapping_key(mp_obj_t c_obj, mp_obj_t key_obj) {
    mp_obj_t c = c_obj;
    mp_obj_t key = key_obj;

    return mp_obj_subscr(((container_attrs_Container_obj_t *)MP_OBJ_TO_PTR(c))->mapping, key, MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_2(container_attrs_get_mapping_key_obj, container_attrs_get_mapping_key);
static mp_obj_t container_attrs_has_in_unique(mp_obj_t c_obj, mp_obj_t val_obj) {
    mp_obj_t c = c_obj;
    mp_int_t val = mp_obj_get_int(val_obj);

    return (mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, mp_obj_new_int(val), ((container_attrs_Container_obj_t *)MP_OBJ_TO_PTR(c))->unique))) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(container_attrs_has_in_unique_obj, container_attrs_has_in_unique);
static mp_obj_t container_attrs_get_inner_items(mp_obj_t o_obj) {
    mp_obj_t o = o_obj;

    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_get_inner_items_obj, container_attrs_get_inner_items);
static mp_obj_t container_attrs_get_inner_data(mp_obj_t o_obj) {
    mp_obj_t o = o_obj;

    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_get_inner_data_obj, container_attrs_get_inner_data);
static mp_obj_t container_attrs_get_first_inner_item(mp_obj_t o_obj) {
    mp_obj_t o = o_obj;

    return mp_obj_subscr(mp_const_none, mp_obj_new_int(0), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_get_first_inner_item_obj, container_attrs_get_first_inner_item);
static mp_obj_t container_attrs_get_inner_data_key(mp_obj_t o_obj, mp_obj_t key_obj) {
    mp_obj_t o = o_obj;
    mp_obj_t key = key_obj;

    return mp_obj_subscr(mp_const_none, key, MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_2(container_attrs_get_inner_data_key_obj, container_attrs_get_inner_data_key);
static mp_obj_t container_attrs_count_inner_items(mp_obj_t o_obj) {
    mp_obj_t o = o_obj;

    return mp_obj_new_int(mp_obj_get_int(mp_obj_len(mp_const_none)));
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_count_inner_items_obj, container_attrs_count_inner_items);
static mp_obj_t container_attrs_sum_inner_items(mp_obj_t o_obj) {
    mp_obj_t o = o_obj;

    mp_int_t total = 0;
    mp_obj_t item;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(mp_const_none, &_tmp2);
    while ((item = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total = mp_obj_get_int(mp_binary_op(MP_BINARY_OP_ADD, mp_obj_new_int(total), item));
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(container_attrs_sum_inner_items_obj, container_attrs_sum_inner_items);
static mp_obj_t container_attrs_benchmark_inner_list_update(mp_obj_t o_obj, mp_obj_t iterations_obj) {
    mp_obj_t o = o_obj;
    mp_int_t iterations = mp_obj_get_int(iterations_obj);

    mp_int_t i = 0;
    while ((i < iterations)) {
        mp_obj_subscr(mp_const_none, mp_obj_new_int(0), mp_obj_new_int(i));
        i = (i + 1);
    }
    return mp_obj_subscr(mp_const_none, mp_obj_new_int(0), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_2(container_attrs_benchmark_inner_list_update_obj, container_attrs_benchmark_inner_list_update);
typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} container_attrs_Container_field_t;

static const container_attrs_Container_field_t container_attrs_Container_fields[] = {
    { MP_QSTR_items, offsetof(container_attrs_Container_obj_t, items), 0 },
    { MP_QSTR_mapping, offsetof(container_attrs_Container_obj_t, mapping), 0 },
    { MP_QSTR_unique, offsetof(container_attrs_Container_obj_t, unique), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void container_attrs_Container_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    container_attrs_Container_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const container_attrs_Container_field_t *f = container_attrs_Container_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void container_attrs_Container_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    container_attrs_Container_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Container(");
    mp_printf(print, "items=");
    mp_obj_print_helper(print, self->items, PRINT_REPR);
    mp_printf(print, ", mapping=");
    mp_obj_print_helper(print, self->mapping, PRINT_REPR);
    mp_printf(print, ", unique=");
    mp_obj_print_helper(print, self->unique, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t container_attrs_Container_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    container_attrs_Container_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    container_attrs_Container_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        mp_obj_equal(lhs->items, rhs->items) &&
        mp_obj_equal(lhs->mapping, rhs->mapping) &&
        mp_obj_equal(lhs->unique, rhs->unique)
    );
}

static mp_obj_t container_attrs_Container_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_items,
        ARG_mapping,
        ARG_unique,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_items, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_mapping, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_unique, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[3];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 3, allowed_args, parsed);

    container_attrs_Container_obj_t *self = mp_obj_malloc(container_attrs_Container_obj_t, type);
    self->items = parsed[ARG_items].u_obj;
    self->mapping = parsed[ARG_mapping].u_obj;
    self->unique = parsed[ARG_unique].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    container_attrs_Container_type,
    MP_QSTR_Container,
    MP_TYPE_FLAG_NONE,
    make_new, container_attrs_Container_make_new,
    attr, container_attrs_Container_attr,
    print, container_attrs_Container_print,
    binary_op, container_attrs_Container_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} container_attrs_Inner_field_t;

static const container_attrs_Inner_field_t container_attrs_Inner_fields[] = {
    { MP_QSTR_items, offsetof(container_attrs_Inner_obj_t, items), 0 },
    { MP_QSTR_data, offsetof(container_attrs_Inner_obj_t, data), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void container_attrs_Inner_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    container_attrs_Inner_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const container_attrs_Inner_field_t *f = container_attrs_Inner_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void container_attrs_Inner_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    container_attrs_Inner_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Inner(");
    mp_printf(print, "items=");
    mp_obj_print_helper(print, self->items, PRINT_REPR);
    mp_printf(print, ", data=");
    mp_obj_print_helper(print, self->data, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t container_attrs_Inner_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    container_attrs_Inner_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    container_attrs_Inner_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        mp_obj_equal(lhs->items, rhs->items) &&
        mp_obj_equal(lhs->data, rhs->data)
    );
}

static mp_obj_t container_attrs_Inner_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_items,
        ARG_data,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_items, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_data, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[2];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 2, allowed_args, parsed);

    container_attrs_Inner_obj_t *self = mp_obj_malloc(container_attrs_Inner_obj_t, type);
    self->items = parsed[ARG_items].u_obj;
    self->data = parsed[ARG_data].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    container_attrs_Inner_type,
    MP_QSTR_Inner,
    MP_TYPE_FLAG_NONE,
    make_new, container_attrs_Inner_make_new,
    attr, container_attrs_Inner_attr,
    print, container_attrs_Inner_print,
    binary_op, container_attrs_Inner_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} container_attrs_Outer_field_t;

static const container_attrs_Outer_field_t container_attrs_Outer_fields[] = {
    { MP_QSTR_inner, offsetof(container_attrs_Outer_obj_t, inner), 0 },
    { MP_QSTR_name, offsetof(container_attrs_Outer_obj_t, name), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void container_attrs_Outer_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    container_attrs_Outer_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const container_attrs_Outer_field_t *f = container_attrs_Outer_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void container_attrs_Outer_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    container_attrs_Outer_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Outer(");
    mp_printf(print, "inner=");
    mp_obj_print_helper(print, self->inner, PRINT_REPR);
    mp_printf(print, ", name=");
    mp_obj_print_helper(print, self->name, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t container_attrs_Outer_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    container_attrs_Outer_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    container_attrs_Outer_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        mp_obj_equal(lhs->inner, rhs->inner) &&
        mp_obj_equal(lhs->name, rhs->name)
    );
}

static mp_obj_t container_attrs_Outer_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_inner,
        ARG_name,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_inner, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_name, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[2];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 2, allowed_args, parsed);

    container_attrs_Outer_obj_t *self = mp_obj_malloc(container_attrs_Outer_obj_t, type);
    self->inner = parsed[ARG_inner].u_obj;
    self->name = parsed[ARG_name].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    container_attrs_Outer_type,
    MP_QSTR_Outer,
    MP_TYPE_FLAG_NONE,
    make_new, container_attrs_Outer_make_new,
    attr, container_attrs_Outer_attr,
    print, container_attrs_Outer_print,
    binary_op, container_attrs_Outer_binary_op
);

static const mp_rom_map_elem_t container_attrs_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_container_attrs) },
    { MP_ROM_QSTR(MP_QSTR_get_items), MP_ROM_PTR(&container_attrs_get_items_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_mapping), MP_ROM_PTR(&container_attrs_get_mapping_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_unique), MP_ROM_PTR(&container_attrs_get_unique_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_first_item), MP_ROM_PTR(&container_attrs_get_first_item_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_mapping_key), MP_ROM_PTR(&container_attrs_get_mapping_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_has_in_unique), MP_ROM_PTR(&container_attrs_has_in_unique_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_inner_items), MP_ROM_PTR(&container_attrs_get_inner_items_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_inner_data), MP_ROM_PTR(&container_attrs_get_inner_data_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_first_inner_item), MP_ROM_PTR(&container_attrs_get_first_inner_item_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_inner_data_key), MP_ROM_PTR(&container_attrs_get_inner_data_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_inner_items), MP_ROM_PTR(&container_attrs_count_inner_items_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_inner_items), MP_ROM_PTR(&container_attrs_sum_inner_items_obj) },
    { MP_ROM_QSTR(MP_QSTR_benchmark_inner_list_update), MP_ROM_PTR(&container_attrs_benchmark_inner_list_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_Container), MP_ROM_PTR(&container_attrs_Container_type) },
    { MP_ROM_QSTR(MP_QSTR_Inner), MP_ROM_PTR(&container_attrs_Inner_type) },
    { MP_ROM_QSTR(MP_QSTR_Outer), MP_ROM_PTR(&container_attrs_Outer_type) },
};
MP_DEFINE_CONST_DICT(container_attrs_module_globals, container_attrs_module_globals_table);

const mp_obj_module_t container_attrs_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&container_attrs_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_container_attrs, container_attrs_user_cmodule);