#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _counter_Counter_obj_t counter_Counter_obj_t;
typedef struct _counter_Counter_vtable_t counter_Counter_vtable_t;
typedef struct _counter_BoundedCounter_obj_t counter_BoundedCounter_obj_t;
typedef struct _counter_BoundedCounter_vtable_t counter_BoundedCounter_vtable_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

static mp_obj_t counter_Counter___init___mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    counter_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t start = mp_obj_get_int(arg0_obj);
    mp_int_t step = mp_obj_get_int(arg1_obj);
    self->value = start;
    self->step = step;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(counter_Counter___init___obj, counter_Counter___init___mp);

static mp_int_t counter_Counter_increment_native(counter_Counter_obj_t *self) {
    self->value += self->step;
    return self->value;
}

static mp_obj_t counter_Counter_increment_mp(mp_obj_t self_in) {
    counter_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(counter_Counter_increment_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(counter_Counter_increment_obj, counter_Counter_increment_mp);

static mp_int_t counter_Counter_decrement_native(counter_Counter_obj_t *self) {
    self->value -= self->step;
    return self->value;
}

static mp_obj_t counter_Counter_decrement_mp(mp_obj_t self_in) {
    counter_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(counter_Counter_decrement_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(counter_Counter_decrement_obj, counter_Counter_decrement_mp);

static void counter_Counter_reset_native(counter_Counter_obj_t *self) {
    self->value = 0;
    return;
}

static mp_obj_t counter_Counter_reset_mp(mp_obj_t self_in) {
    counter_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    counter_Counter_reset_native(self);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(counter_Counter_reset_obj, counter_Counter_reset_mp);

static mp_int_t counter_Counter_get_native(counter_Counter_obj_t *self) {
    return self->value;
}

static mp_obj_t counter_Counter_get_mp(mp_obj_t self_in) {
    counter_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(counter_Counter_get_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(counter_Counter_get_obj, counter_Counter_get_mp);

static mp_obj_t counter_BoundedCounter___init___mp(size_t n_args, const mp_obj_t *args) {
    counter_BoundedCounter_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t start = mp_obj_get_int(args[1]);
    mp_int_t step = mp_obj_get_int(args[2]);
    mp_int_t min_val = mp_obj_get_int(args[3]);
    mp_int_t max_val = mp_obj_get_int(args[4]);
    self->value = start;
    self->step = step;
    self->min_val = min_val;
    self->max_val = max_val;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(counter_BoundedCounter___init___obj, 5, 5, counter_BoundedCounter___init___mp);

static mp_int_t counter_BoundedCounter_increment_native(counter_BoundedCounter_obj_t *self) {
    mp_int_t new_val = (self->value + self->step);
    if ((new_val <= self->max_val)) {
        self->value = new_val;
    }
    return self->value;
}

static mp_obj_t counter_BoundedCounter_increment_mp(mp_obj_t self_in) {
    counter_BoundedCounter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(counter_BoundedCounter_increment_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(counter_BoundedCounter_increment_obj, counter_BoundedCounter_increment_mp);

static mp_int_t counter_BoundedCounter_decrement_native(counter_BoundedCounter_obj_t *self) {
    mp_int_t new_val = (self->value - self->step);
    if ((new_val >= self->min_val)) {
        self->value = new_val;
    }
    return self->value;
}

static mp_obj_t counter_BoundedCounter_decrement_mp(mp_obj_t self_in) {
    counter_BoundedCounter_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(counter_BoundedCounter_decrement_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(counter_BoundedCounter_decrement_obj, counter_BoundedCounter_decrement_mp);

struct _counter_Counter_vtable_t {
    mp_int_t (*increment)(counter_Counter_obj_t *self);
    mp_int_t (*decrement)(counter_Counter_obj_t *self);
    void (*reset)(counter_Counter_obj_t *self);
    mp_int_t (*get)(counter_Counter_obj_t *self);
};

struct _counter_Counter_obj_t {
    mp_obj_base_t base;
    const counter_Counter_vtable_t *vtable;
    mp_int_t value;
    mp_int_t step;
};

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} counter_Counter_field_t;

static const counter_Counter_field_t counter_Counter_fields[] = {
    { MP_QSTR_value, offsetof(counter_Counter_obj_t, value), 1 },
    { MP_QSTR_step, offsetof(counter_Counter_obj_t, step), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void counter_Counter_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    counter_Counter_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const counter_Counter_field_t *f = counter_Counter_fields; f->name != MP_QSTR_NULL; f++) {
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

static const counter_Counter_vtable_t counter_Counter_vtable_inst = {
    .increment = counter_Counter_increment_native,
    .decrement = counter_Counter_decrement_native,
    .reset = counter_Counter_reset_native,
    .get = counter_Counter_get_native,
};

static mp_obj_t counter_Counter_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);

    counter_Counter_obj_t *self = mp_obj_malloc(counter_Counter_obj_t, type);
    self->vtable = &counter_Counter_vtable_inst;
    self->value = 0;
    self->step = 0;

    counter_Counter___init___mp(MP_OBJ_FROM_PTR(self), args[0], args[1]);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t counter_Counter_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_increment), MP_ROM_PTR(&counter_Counter_increment_obj) },
    { MP_ROM_QSTR(MP_QSTR_decrement), MP_ROM_PTR(&counter_Counter_decrement_obj) },
    { MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&counter_Counter_reset_obj) },
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&counter_Counter_get_obj) },
};
static MP_DEFINE_CONST_DICT(counter_Counter_locals_dict, counter_Counter_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    counter_Counter_type,
    MP_QSTR_Counter,
    MP_TYPE_FLAG_NONE,
    make_new, counter_Counter_make_new,
    attr, counter_Counter_attr,
    locals_dict, &counter_Counter_locals_dict
);

struct _counter_BoundedCounter_vtable_t {
    mp_int_t (*increment)(counter_BoundedCounter_obj_t *self);
    mp_int_t (*decrement)(counter_BoundedCounter_obj_t *self);
    void (*reset)(counter_BoundedCounter_obj_t *self);
    mp_int_t (*get)(counter_BoundedCounter_obj_t *self);
};

struct _counter_BoundedCounter_obj_t {
    counter_Counter_obj_t super;
    mp_int_t min_val;
    mp_int_t max_val;
};

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} counter_BoundedCounter_field_t;

static const counter_BoundedCounter_field_t counter_BoundedCounter_fields[] = {
    { MP_QSTR_value, offsetof(counter_BoundedCounter_obj_t, value), 1 },
    { MP_QSTR_step, offsetof(counter_BoundedCounter_obj_t, step), 1 },
    { MP_QSTR_min_val, offsetof(counter_BoundedCounter_obj_t, min_val), 1 },
    { MP_QSTR_max_val, offsetof(counter_BoundedCounter_obj_t, max_val), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void counter_BoundedCounter_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    counter_BoundedCounter_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const counter_BoundedCounter_field_t *f = counter_BoundedCounter_fields; f->name != MP_QSTR_NULL; f++) {
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

static const counter_BoundedCounter_vtable_t counter_BoundedCounter_vtable_inst = {
    .increment = counter_BoundedCounter_increment_native,
    .decrement = counter_BoundedCounter_decrement_native,
    .reset = counter_Counter_reset_native,
    .get = counter_Counter_get_native,
};

static mp_obj_t counter_BoundedCounter_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 4, 4, false);

    counter_BoundedCounter_obj_t *self = mp_obj_malloc(counter_BoundedCounter_obj_t, type);
    self->min_val = 0;
    self->max_val = 0;

    counter_BoundedCounter___init___mp(MP_OBJ_FROM_PTR(self), args[0], args[1], args[2], args[3]);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t counter_BoundedCounter_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_increment), MP_ROM_PTR(&counter_BoundedCounter_increment_obj) },
    { MP_ROM_QSTR(MP_QSTR_decrement), MP_ROM_PTR(&counter_BoundedCounter_decrement_obj) },
};
static MP_DEFINE_CONST_DICT(counter_BoundedCounter_locals_dict, counter_BoundedCounter_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    counter_BoundedCounter_type,
    MP_QSTR_BoundedCounter,
    MP_TYPE_FLAG_NONE,
    make_new, counter_BoundedCounter_make_new,
    attr, counter_BoundedCounter_attr,
    parent, &counter_Counter_type,
    locals_dict, &counter_BoundedCounter_locals_dict
);

static const mp_rom_map_elem_t counter_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_counter) },
    { MP_ROM_QSTR(MP_QSTR_Counter), MP_ROM_PTR(&counter_Counter_type) },
    { MP_ROM_QSTR(MP_QSTR_BoundedCounter), MP_ROM_PTR(&counter_BoundedCounter_type) },
};
MP_DEFINE_CONST_DICT(counter_module_globals, counter_module_globals_table);

const mp_obj_module_t counter_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&counter_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_counter, counter_user_cmodule);