#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _point_Point_obj_t point_Point_obj_t;
typedef struct _point_Point_vtable_t point_Point_vtable_t;
typedef struct _point_Point3D_obj_t point_Point3D_obj_t;
typedef struct _point_Point3D_vtable_t point_Point3D_vtable_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _point_Point_vtable_t {
    mp_int_t (*distance_squared)(point_Point_obj_t *self);
    mp_int_t (*add)(point_Point_obj_t *self, mp_int_t other_x, mp_int_t other_y);
};

struct _point_Point_obj_t {
    mp_obj_base_t base;
    const point_Point_vtable_t *vtable;
    mp_int_t x;
    mp_int_t y;
};

struct _point_Point3D_vtable_t {
    mp_int_t (*distance_squared)(point_Point3D_obj_t *self);
    mp_int_t (*add)(point_Point3D_obj_t *self, mp_int_t other_x, mp_int_t other_y);
    mp_int_t (*distance_squared_3d)(point_Point3D_obj_t *self);
};

struct _point_Point3D_obj_t {
    point_Point_obj_t super;
    mp_int_t z;
};


static mp_int_t point_Point_distance_squared_native(point_Point_obj_t *self) {
    return ((self->x * self->x) + (self->y * self->y));
}

static mp_obj_t point_Point_distance_squared_mp(mp_obj_t self_in) {
    point_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(point_Point_distance_squared_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(point_Point_distance_squared_obj, point_Point_distance_squared_mp);

static mp_int_t point_Point_add_native(point_Point_obj_t *self, mp_int_t other_x, mp_int_t other_y) {
    return (((self->x + other_x) + self->y) + other_y);
}

static mp_obj_t point_Point_add_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    point_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t other_x = mp_obj_get_int(arg0_obj);
    mp_int_t other_y = mp_obj_get_int(arg1_obj);
    return mp_obj_new_int(point_Point_add_native(self, other_x, other_y));
}
MP_DEFINE_CONST_FUN_OBJ_3(point_Point_add_obj, point_Point_add_mp);

static mp_int_t point_Point3D_distance_squared_3d_native(point_Point3D_obj_t *self) {
    return (((self->super.x * self->super.x) + (self->super.y * self->super.y)) + (self->z * self->z));
}

static mp_obj_t point_Point3D_distance_squared_3d_mp(mp_obj_t self_in) {
    point_Point3D_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(point_Point3D_distance_squared_3d_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(point_Point3D_distance_squared_3d_obj, point_Point3D_distance_squared_3d_mp);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} point_Point_field_t;

static const point_Point_field_t point_Point_fields[] = {
    { MP_QSTR_x, offsetof(point_Point_obj_t, x), 1 },
    { MP_QSTR_y, offsetof(point_Point_obj_t, y), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void point_Point_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    point_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const point_Point_field_t *f = point_Point_fields; f->name != MP_QSTR_NULL; f++) {
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

static void point_Point_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    point_Point_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Point(");
    mp_printf(print, "x=%d", (int)self->x);
    mp_printf(print, ", y=%d", (int)self->y);
    mp_printf(print, ")");
}

static mp_obj_t point_Point_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, &point_Point_type)) {
        return mp_const_false;
    }

    point_Point_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    point_Point_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        lhs->x == rhs->x &&
        lhs->y == rhs->y
    );
}

static const point_Point_vtable_t point_Point_vtable_inst = {
    .distance_squared = point_Point_distance_squared_native,
    .add = point_Point_add_native,
};

static mp_obj_t point_Point_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
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

    point_Point_obj_t *self = mp_obj_malloc(point_Point_obj_t, type);
    self->vtable = &point_Point_vtable_inst;
    self->x = parsed[ARG_x].u_int;
    self->y = parsed[ARG_y].u_int;

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t point_Point_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_distance_squared), MP_ROM_PTR(&point_Point_distance_squared_obj) },
    { MP_ROM_QSTR(MP_QSTR_add), MP_ROM_PTR(&point_Point_add_obj) },
};
static MP_DEFINE_CONST_DICT(point_Point_locals_dict, point_Point_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    point_Point_type,
    MP_QSTR_Point,
    MP_TYPE_FLAG_NONE,
    make_new, point_Point_make_new,
    attr, point_Point_attr,
    print, point_Point_print,
    binary_op, point_Point_binary_op,
    locals_dict, &point_Point_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} point_Point3D_field_t;

static const point_Point3D_field_t point_Point3D_fields[] = {
    { MP_QSTR_x, offsetof(point_Point3D_obj_t, super.x), 1 },
    { MP_QSTR_y, offsetof(point_Point3D_obj_t, super.y), 1 },
    { MP_QSTR_z, offsetof(point_Point3D_obj_t, z), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void point_Point3D_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    point_Point3D_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const point_Point3D_field_t *f = point_Point3D_fields; f->name != MP_QSTR_NULL; f++) {
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

static void point_Point3D_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    point_Point3D_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Point3D(");
    mp_printf(print, "x=%d", (int)self->super.x);
    mp_printf(print, ", y=%d", (int)self->super.y);
    mp_printf(print, ", z=%d", (int)self->z);
    mp_printf(print, ")");
}

static mp_obj_t point_Point3D_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, &point_Point3D_type)) {
        return mp_const_false;
    }

    point_Point3D_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    point_Point3D_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        lhs->super.x == rhs->super.x &&
        lhs->super.y == rhs->super.y &&
        lhs->z == rhs->z
    );
}

static const point_Point3D_vtable_t point_Point3D_vtable_inst = {
    .distance_squared = point_Point_distance_squared_native,
    .add = point_Point_add_native,
    .distance_squared_3d = point_Point3D_distance_squared_3d_native,
};

static mp_obj_t point_Point3D_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_x,
        ARG_y,
        ARG_z,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_x, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_y, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_z, MP_ARG_REQUIRED | MP_ARG_INT },
    };

    mp_arg_val_t parsed[3];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 3, allowed_args, parsed);

    point_Point3D_obj_t *self = mp_obj_malloc(point_Point3D_obj_t, type);
    self->super.x = parsed[ARG_x].u_int;
    self->super.y = parsed[ARG_y].u_int;
    self->z = parsed[ARG_z].u_int;

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t point_Point3D_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_distance_squared_3d), MP_ROM_PTR(&point_Point3D_distance_squared_3d_obj) },
};
static MP_DEFINE_CONST_DICT(point_Point3D_locals_dict, point_Point3D_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    point_Point3D_type,
    MP_QSTR_Point3D,
    MP_TYPE_FLAG_NONE,
    make_new, point_Point3D_make_new,
    attr, point_Point3D_attr,
    print, point_Point3D_print,
    binary_op, point_Point3D_binary_op,
    parent, &point_Point_type,
    locals_dict, &point_Point3D_locals_dict
);

static const mp_rom_map_elem_t point_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_point) },
    { MP_ROM_QSTR(MP_QSTR_Point), MP_ROM_PTR(&point_Point_type) },
    { MP_ROM_QSTR(MP_QSTR_Point3D), MP_ROM_PTR(&point_Point3D_type) },
};
MP_DEFINE_CONST_DICT(point_module_globals, point_module_globals_table);

const mp_obj_module_t point_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&point_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_point, point_user_cmodule);