#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _chained_attr_Point_obj_t chained_attr_Point_obj_t;
typedef struct _chained_attr_Rectangle_obj_t chained_attr_Rectangle_obj_t;
typedef struct _chained_attr_Node_obj_t chained_attr_Node_obj_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _chained_attr_Point_obj_t {
    mp_obj_base_t base;
    mp_int_t x;
    mp_int_t y;
};

struct _chained_attr_Rectangle_obj_t {
    mp_obj_base_t base;
    mp_obj_t top_left;
    mp_obj_t bottom_right;
};

struct _chained_attr_Node_obj_t {
    mp_obj_base_t base;
    mp_int_t value;
    mp_obj_t next;
};


static mp_obj_t chained_attr_get_width(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    return mp_binary_op(MP_BINARY_OP_SUBTRACT, mp_const_none, mp_const_none);
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_width_obj, chained_attr_get_width);
static mp_obj_t chained_attr_get_height(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    return mp_binary_op(MP_BINARY_OP_SUBTRACT, mp_const_none, mp_const_none);
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_height_obj, chained_attr_get_height);
static mp_obj_t chained_attr_get_area(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    mp_obj_t width = mp_binary_op(MP_BINARY_OP_SUBTRACT, mp_const_none, mp_const_none);
    mp_obj_t height = mp_binary_op(MP_BINARY_OP_SUBTRACT, mp_const_none, mp_const_none);
    return mp_binary_op(MP_BINARY_OP_MULTIPLY, width, height);
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_area_obj, chained_attr_get_area);
static mp_obj_t chained_attr_get_top_left_x(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_top_left_x_obj, chained_attr_get_top_left_x);
static mp_obj_t chained_attr_get_top_left_y(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_top_left_y_obj, chained_attr_get_top_left_y);
static mp_obj_t chained_attr_get_bottom_right_x(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_bottom_right_x_obj, chained_attr_get_bottom_right_x);
static mp_obj_t chained_attr_get_bottom_right_y(mp_obj_t rect_obj) {
    mp_obj_t rect = rect_obj;

    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_bottom_right_y_obj, chained_attr_get_bottom_right_y);
static mp_obj_t chained_attr_get_next_value(mp_obj_t node_obj) {
    mp_obj_t node = node_obj;

    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(chained_attr_get_next_value_obj, chained_attr_get_next_value);
typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} chained_attr_Point_field_t;

static const chained_attr_Point_field_t chained_attr_Point_fields[] = {
    { MP_QSTR_x, offsetof(chained_attr_Point_obj_t, x), 1 },
    { MP_QSTR_y, offsetof(chained_attr_Point_obj_t, y), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void chained_attr_Point_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    chained_attr_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const chained_attr_Point_field_t *f = chained_attr_Point_fields; f->name != MP_QSTR_NULL; f++) {
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

static void chained_attr_Point_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    chained_attr_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Point(");
    mp_printf(print, "x=%d", (int)self->x);
    mp_printf(print, ", y=%d", (int)self->y);
    mp_printf(print, ")");
}

static mp_obj_t chained_attr_Point_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    chained_attr_Point_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    chained_attr_Point_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        lhs->x == rhs->x &&
        lhs->y == rhs->y
    );
}

static mp_obj_t chained_attr_Point_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_x,
        ARG_y,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_x, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_y, MP_ARG_REQUIRED | MP_ARG_INT },
    };

    mp_arg_val_t parsed[2];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 2, allowed_args, parsed);

    chained_attr_Point_obj_t *self = mp_obj_malloc(chained_attr_Point_obj_t, type);
    self->x = parsed[ARG_x].u_int;
    self->y = parsed[ARG_y].u_int;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    chained_attr_Point_type,
    MP_QSTR_Point,
    MP_TYPE_FLAG_NONE,
    make_new, chained_attr_Point_make_new,
    attr, chained_attr_Point_attr,
    print, chained_attr_Point_print,
    binary_op, chained_attr_Point_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} chained_attr_Rectangle_field_t;

static const chained_attr_Rectangle_field_t chained_attr_Rectangle_fields[] = {
    { MP_QSTR_top_left, offsetof(chained_attr_Rectangle_obj_t, top_left), 0 },
    { MP_QSTR_bottom_right, offsetof(chained_attr_Rectangle_obj_t, bottom_right), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void chained_attr_Rectangle_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    chained_attr_Rectangle_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const chained_attr_Rectangle_field_t *f = chained_attr_Rectangle_fields; f->name != MP_QSTR_NULL; f++) {
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

static void chained_attr_Rectangle_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    chained_attr_Rectangle_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Rectangle(");
    mp_printf(print, "top_left=");
    mp_obj_print_helper(print, self->top_left, PRINT_REPR);
    mp_printf(print, ", bottom_right=");
    mp_obj_print_helper(print, self->bottom_right, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t chained_attr_Rectangle_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    chained_attr_Rectangle_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    chained_attr_Rectangle_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        mp_obj_equal(lhs->top_left, rhs->top_left) &&
        mp_obj_equal(lhs->bottom_right, rhs->bottom_right)
    );
}

static mp_obj_t chained_attr_Rectangle_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_top_left,
        ARG_bottom_right,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_top_left, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_bottom_right, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[2];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 2, allowed_args, parsed);

    chained_attr_Rectangle_obj_t *self = mp_obj_malloc(chained_attr_Rectangle_obj_t, type);
    self->top_left = parsed[ARG_top_left].u_obj;
    self->bottom_right = parsed[ARG_bottom_right].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    chained_attr_Rectangle_type,
    MP_QSTR_Rectangle,
    MP_TYPE_FLAG_NONE,
    make_new, chained_attr_Rectangle_make_new,
    attr, chained_attr_Rectangle_attr,
    print, chained_attr_Rectangle_print,
    binary_op, chained_attr_Rectangle_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} chained_attr_Node_field_t;

static const chained_attr_Node_field_t chained_attr_Node_fields[] = {
    { MP_QSTR_value, offsetof(chained_attr_Node_obj_t, value), 1 },
    { MP_QSTR_next, offsetof(chained_attr_Node_obj_t, next), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void chained_attr_Node_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    chained_attr_Node_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const chained_attr_Node_field_t *f = chained_attr_Node_fields; f->name != MP_QSTR_NULL; f++) {
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

static void chained_attr_Node_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    chained_attr_Node_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Node(");
    mp_printf(print, "value=%d", (int)self->value);
    mp_printf(print, ", next=");
    mp_obj_print_helper(print, self->next, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t chained_attr_Node_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    chained_attr_Node_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    chained_attr_Node_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        lhs->value == rhs->value &&
        mp_obj_equal(lhs->next, rhs->next)
    );
}

static mp_obj_t chained_attr_Node_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_value,
        ARG_next,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_value, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_next, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[2];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 2, allowed_args, parsed);

    chained_attr_Node_obj_t *self = mp_obj_malloc(chained_attr_Node_obj_t, type);
    self->value = parsed[ARG_value].u_int;
    self->next = parsed[ARG_next].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    chained_attr_Node_type,
    MP_QSTR_Node,
    MP_TYPE_FLAG_NONE,
    make_new, chained_attr_Node_make_new,
    attr, chained_attr_Node_attr,
    print, chained_attr_Node_print,
    binary_op, chained_attr_Node_binary_op
);

static const mp_rom_map_elem_t chained_attr_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_chained_attr) },
    { MP_ROM_QSTR(MP_QSTR_get_width), MP_ROM_PTR(&chained_attr_get_width_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_height), MP_ROM_PTR(&chained_attr_get_height_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_area), MP_ROM_PTR(&chained_attr_get_area_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_top_left_x), MP_ROM_PTR(&chained_attr_get_top_left_x_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_top_left_y), MP_ROM_PTR(&chained_attr_get_top_left_y_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_bottom_right_x), MP_ROM_PTR(&chained_attr_get_bottom_right_x_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_bottom_right_y), MP_ROM_PTR(&chained_attr_get_bottom_right_y_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_next_value), MP_ROM_PTR(&chained_attr_get_next_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_Point), MP_ROM_PTR(&chained_attr_Point_type) },
    { MP_ROM_QSTR(MP_QSTR_Rectangle), MP_ROM_PTR(&chained_attr_Rectangle_type) },
    { MP_ROM_QSTR(MP_QSTR_Node), MP_ROM_PTR(&chained_attr_Node_type) },
};
MP_DEFINE_CONST_DICT(chained_attr_module_globals, chained_attr_module_globals_table);

const mp_obj_module_t chained_attr_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&chained_attr_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_chained_attr, chained_attr_user_cmodule);