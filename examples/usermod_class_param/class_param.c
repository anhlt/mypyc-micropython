#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _class_param_Point_obj_t class_param_Point_obj_t;
typedef struct _class_param_Vector_obj_t class_param_Vector_obj_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _class_param_Point_obj_t {
    mp_obj_base_t base;
    mp_int_t x;
    mp_int_t y;
};

struct _class_param_Vector_obj_t {
    mp_obj_base_t base;
    mp_float_t dx;
    mp_float_t dy;
};


static mp_obj_t class_param_get_x(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;

    return mp_obj_new_int(((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p))->x);
}
MP_DEFINE_CONST_FUN_OBJ_1(class_param_get_x_obj, class_param_get_x);
static mp_obj_t class_param_get_y(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;

    return mp_obj_new_int(((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p))->y);
}
MP_DEFINE_CONST_FUN_OBJ_1(class_param_get_y_obj, class_param_get_y);
static mp_obj_t class_param_add_coords(mp_obj_t p_obj) {
    mp_obj_t p = p_obj;

    return mp_obj_new_int((((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p))->x + ((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p))->y));
}
MP_DEFINE_CONST_FUN_OBJ_1(class_param_add_coords_obj, class_param_add_coords);
static mp_obj_t class_param_distance_squared(mp_obj_t p1_obj, mp_obj_t p2_obj) {
    mp_obj_t p1 = p1_obj;
    mp_obj_t p2 = p2_obj;

    mp_int_t dx = (((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p2))->x - ((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p1))->x);
    mp_int_t dy = (((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p2))->y - ((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p1))->y);
    return mp_obj_new_int(((dx * dx) + (dy * dy)));
}
MP_DEFINE_CONST_FUN_OBJ_2(class_param_distance_squared_obj, class_param_distance_squared);
static mp_obj_t class_param_midpoint_x(mp_obj_t p1_obj, mp_obj_t p2_obj) {
    mp_obj_t p1 = p1_obj;
    mp_obj_t p2 = p2_obj;

    return mp_obj_new_int(((((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p1))->x + ((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p2))->x) / 2));
}
MP_DEFINE_CONST_FUN_OBJ_2(class_param_midpoint_x_obj, class_param_midpoint_x);
static mp_obj_t class_param_scale_point(mp_obj_t p_obj, mp_obj_t factor_obj) {
    mp_obj_t p = p_obj;
    mp_int_t factor = mp_obj_get_int(factor_obj);

    return mp_obj_new_int(((((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p))->x * factor) + (((class_param_Point_obj_t *)MP_OBJ_TO_PTR(p))->y * factor)));
}
MP_DEFINE_CONST_FUN_OBJ_2(class_param_scale_point_obj, class_param_scale_point);
static mp_obj_t class_param_dot_product(mp_obj_t v1_obj, mp_obj_t v2_obj) {
    mp_obj_t v1 = v1_obj;
    mp_obj_t v2 = v2_obj;

    return mp_obj_new_float(((((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v1))->dx * ((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v2))->dx) + (((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v1))->dy * ((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v2))->dy)));
}
MP_DEFINE_CONST_FUN_OBJ_2(class_param_dot_product_obj, class_param_dot_product);
static mp_obj_t class_param_length_squared(mp_obj_t v_obj) {
    mp_obj_t v = v_obj;

    return mp_obj_new_float(((((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v))->dx * ((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v))->dx) + (((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v))->dy * ((class_param_Vector_obj_t *)MP_OBJ_TO_PTR(v))->dy)));
}
MP_DEFINE_CONST_FUN_OBJ_1(class_param_length_squared_obj, class_param_length_squared);
typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} class_param_Point_field_t;

static const class_param_Point_field_t class_param_Point_fields[] = {
    { MP_QSTR_x, offsetof(class_param_Point_obj_t, x), 1 },
    { MP_QSTR_y, offsetof(class_param_Point_obj_t, y), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void class_param_Point_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    class_param_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const class_param_Point_field_t *f = class_param_Point_fields; f->name != MP_QSTR_NULL; f++) {
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

static void class_param_Point_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    class_param_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Point(");
    mp_printf(print, "x=%d", (int)self->x);
    mp_printf(print, ", y=%d", (int)self->y);
    mp_printf(print, ")");
}

static mp_obj_t class_param_Point_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    class_param_Point_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    class_param_Point_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        lhs->x == rhs->x &&
        lhs->y == rhs->y
    );
}

static mp_obj_t class_param_Point_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
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

    class_param_Point_obj_t *self = mp_obj_malloc(class_param_Point_obj_t, type);
    self->x = parsed[ARG_x].u_int;
    self->y = parsed[ARG_y].u_int;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    class_param_Point_type,
    MP_QSTR_Point,
    MP_TYPE_FLAG_NONE,
    make_new, class_param_Point_make_new,
    attr, class_param_Point_attr,
    print, class_param_Point_print,
    binary_op, class_param_Point_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} class_param_Vector_field_t;

static const class_param_Vector_field_t class_param_Vector_fields[] = {
    { MP_QSTR_dx, offsetof(class_param_Vector_obj_t, dx), 2 },
    { MP_QSTR_dy, offsetof(class_param_Vector_obj_t, dy), 2 },
    { MP_QSTR_NULL, 0, 0 }
};

static void class_param_Vector_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    class_param_Vector_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const class_param_Vector_field_t *f = class_param_Vector_fields; f->name != MP_QSTR_NULL; f++) {
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

static void class_param_Vector_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    class_param_Vector_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Vector(");
    mp_printf(print, "dx=");
    mp_obj_print_helper(print, mp_obj_new_float(self->dx), PRINT_REPR);
    mp_printf(print, ", dy=");
    mp_obj_print_helper(print, mp_obj_new_float(self->dy), PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t class_param_Vector_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
        return mp_const_false;
    }

    class_param_Vector_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    class_param_Vector_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        lhs->dx == rhs->dx &&
        lhs->dy == rhs->dy
    );
}

static mp_obj_t class_param_Vector_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_dx,
        ARG_dy,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_dx, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_dy, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[2];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 2, allowed_args, parsed);

    class_param_Vector_obj_t *self = mp_obj_malloc(class_param_Vector_obj_t, type);
    self->dx = mp_obj_get_float(parsed[ARG_dx].u_obj);
    self->dy = mp_obj_get_float(parsed[ARG_dy].u_obj);

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    class_param_Vector_type,
    MP_QSTR_Vector,
    MP_TYPE_FLAG_NONE,
    make_new, class_param_Vector_make_new,
    attr, class_param_Vector_attr,
    print, class_param_Vector_print,
    binary_op, class_param_Vector_binary_op
);

static const mp_rom_map_elem_t class_param_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_class_param) },
    { MP_ROM_QSTR(MP_QSTR_get_x), MP_ROM_PTR(&class_param_get_x_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_y), MP_ROM_PTR(&class_param_get_y_obj) },
    { MP_ROM_QSTR(MP_QSTR_add_coords), MP_ROM_PTR(&class_param_add_coords_obj) },
    { MP_ROM_QSTR(MP_QSTR_distance_squared), MP_ROM_PTR(&class_param_distance_squared_obj) },
    { MP_ROM_QSTR(MP_QSTR_midpoint_x), MP_ROM_PTR(&class_param_midpoint_x_obj) },
    { MP_ROM_QSTR(MP_QSTR_scale_point), MP_ROM_PTR(&class_param_scale_point_obj) },
    { MP_ROM_QSTR(MP_QSTR_dot_product), MP_ROM_PTR(&class_param_dot_product_obj) },
    { MP_ROM_QSTR(MP_QSTR_length_squared), MP_ROM_PTR(&class_param_length_squared_obj) },
    { MP_ROM_QSTR(MP_QSTR_Point), MP_ROM_PTR(&class_param_Point_type) },
    { MP_ROM_QSTR(MP_QSTR_Vector), MP_ROM_PTR(&class_param_Vector_type) },
};
MP_DEFINE_CONST_DICT(class_param_module_globals, class_param_module_globals_table);

const mp_obj_module_t class_param_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&class_param_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_class_param, class_param_user_cmodule);