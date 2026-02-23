#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _super_calls_Animal_obj_t super_calls_Animal_obj_t;
typedef struct _super_calls_Animal_vtable_t super_calls_Animal_vtable_t;
typedef struct _super_calls_Dog_obj_t super_calls_Dog_obj_t;
typedef struct _super_calls_Dog_vtable_t super_calls_Dog_vtable_t;
typedef struct _super_calls_ShowDog_obj_t super_calls_ShowDog_obj_t;
typedef struct _super_calls_ShowDog_vtable_t super_calls_ShowDog_vtable_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _super_calls_Animal_vtable_t {
    mp_obj_t (*speak)(super_calls_Animal_obj_t *self);
    mp_obj_t (*describe)(super_calls_Animal_obj_t *self);
};

struct _super_calls_Animal_obj_t {
    mp_obj_base_t base;
    const super_calls_Animal_vtable_t *vtable;
    mp_obj_t name;
    mp_obj_t sound;
};

struct _super_calls_Dog_vtable_t {
    mp_obj_t (*speak)(super_calls_Dog_obj_t *self);
    mp_obj_t (*describe)(super_calls_Dog_obj_t *self);
    mp_int_t (*get_tricks)(super_calls_Dog_obj_t *self);
};

struct _super_calls_Dog_obj_t {
    super_calls_Animal_obj_t super;
    mp_int_t tricks;
};

struct _super_calls_ShowDog_vtable_t {
    mp_obj_t (*speak)(super_calls_ShowDog_obj_t *self);
    mp_obj_t (*describe)(super_calls_ShowDog_obj_t *self);
    mp_int_t (*get_tricks)(super_calls_ShowDog_obj_t *self);
    mp_int_t (*get_awards)(super_calls_ShowDog_obj_t *self);
    mp_int_t (*get_total_score)(super_calls_ShowDog_obj_t *self);
};

struct _super_calls_ShowDog_obj_t {
    super_calls_Dog_obj_t super;
    mp_int_t awards;
};


static mp_obj_t super_calls_Animal___init___mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    super_calls_Animal_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t name = arg0_obj;
    mp_obj_t sound = arg1_obj;
    self->name = name;
    self->sound = sound;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(super_calls_Animal___init___obj, super_calls_Animal___init___mp);

static mp_obj_t super_calls_Animal_speak_native(super_calls_Animal_obj_t *self) {
    return self->sound;
}

static mp_obj_t super_calls_Animal_speak_mp(mp_obj_t self_in) {
    super_calls_Animal_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return super_calls_Animal_speak_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(super_calls_Animal_speak_obj, super_calls_Animal_speak_mp);

static mp_obj_t super_calls_Animal_describe_native(super_calls_Animal_obj_t *self) {
    return self->name;
}

static mp_obj_t super_calls_Animal_describe_mp(mp_obj_t self_in) {
    super_calls_Animal_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return super_calls_Animal_describe_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(super_calls_Animal_describe_obj, super_calls_Animal_describe_mp);

static mp_obj_t super_calls_Dog___init___mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    super_calls_Dog_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t name = arg0_obj;
    mp_int_t tricks = mp_obj_get_int(arg1_obj);
    (void)(super_calls_Animal___init___mp(MP_OBJ_FROM_PTR(self), name, mp_obj_new_str("Woof", 4)), mp_const_none);
    self->tricks = tricks;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(super_calls_Dog___init___obj, super_calls_Dog___init___mp);

static mp_obj_t super_calls_Dog_describe_native(super_calls_Dog_obj_t *self) {
    mp_obj_t base = super_calls_Animal_describe_native((super_calls_Animal_obj_t *)self);
    return base;
}

static mp_obj_t super_calls_Dog_describe_mp(mp_obj_t self_in) {
    super_calls_Dog_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return super_calls_Dog_describe_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(super_calls_Dog_describe_obj, super_calls_Dog_describe_mp);

static mp_int_t super_calls_Dog_get_tricks_native(super_calls_Dog_obj_t *self) {
    return self->tricks;
}

static mp_obj_t super_calls_Dog_get_tricks_mp(mp_obj_t self_in) {
    super_calls_Dog_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(super_calls_Dog_get_tricks_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(super_calls_Dog_get_tricks_obj, super_calls_Dog_get_tricks_mp);

static mp_obj_t super_calls_ShowDog___init___mp(size_t n_args, const mp_obj_t *args) {
    super_calls_ShowDog_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t name = args[1];
    mp_int_t tricks = mp_obj_get_int(args[2]);
    mp_int_t awards = mp_obj_get_int(args[3]);
    (void)(super_calls_Dog___init___mp(MP_OBJ_FROM_PTR(self), name, mp_obj_new_int(tricks)), mp_const_none);
    self->awards = awards;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(super_calls_ShowDog___init___obj, 4, 4, super_calls_ShowDog___init___mp);

static mp_obj_t super_calls_ShowDog_describe_native(super_calls_ShowDog_obj_t *self) {
    mp_obj_t base = super_calls_Dog_describe_native((super_calls_Dog_obj_t *)self);
    return base;
}

static mp_obj_t super_calls_ShowDog_describe_mp(mp_obj_t self_in) {
    super_calls_ShowDog_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return super_calls_ShowDog_describe_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(super_calls_ShowDog_describe_obj, super_calls_ShowDog_describe_mp);

static mp_int_t super_calls_ShowDog_get_awards_native(super_calls_ShowDog_obj_t *self) {
    return self->awards;
}

static mp_obj_t super_calls_ShowDog_get_awards_mp(mp_obj_t self_in) {
    super_calls_ShowDog_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(super_calls_ShowDog_get_awards_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(super_calls_ShowDog_get_awards_obj, super_calls_ShowDog_get_awards_mp);

static mp_int_t super_calls_ShowDog_get_total_score_native(super_calls_ShowDog_obj_t *self) {
    return (self->super.tricks + self->awards);
}

static mp_obj_t super_calls_ShowDog_get_total_score_mp(mp_obj_t self_in) {
    super_calls_ShowDog_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(super_calls_ShowDog_get_total_score_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(super_calls_ShowDog_get_total_score_obj, super_calls_ShowDog_get_total_score_mp);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} super_calls_Animal_field_t;

static const super_calls_Animal_field_t super_calls_Animal_fields[] = {
    { MP_QSTR_name, offsetof(super_calls_Animal_obj_t, name), 0 },
    { MP_QSTR_sound, offsetof(super_calls_Animal_obj_t, sound), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void super_calls_Animal_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    super_calls_Animal_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const super_calls_Animal_field_t *f = super_calls_Animal_fields; f->name != MP_QSTR_NULL; f++) {
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

static const super_calls_Animal_vtable_t super_calls_Animal_vtable_inst = {
    .speak = super_calls_Animal_speak_native,
    .describe = super_calls_Animal_describe_native,
};

static mp_obj_t super_calls_Animal_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);

    super_calls_Animal_obj_t *self = mp_obj_malloc(super_calls_Animal_obj_t, type);
    self->vtable = &super_calls_Animal_vtable_inst;
    self->name = mp_const_none;
    self->sound = mp_const_none;

    super_calls_Animal___init___mp(MP_OBJ_FROM_PTR(self), args[0], args[1]);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t super_calls_Animal_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_speak), MP_ROM_PTR(&super_calls_Animal_speak_obj) },
    { MP_ROM_QSTR(MP_QSTR_describe), MP_ROM_PTR(&super_calls_Animal_describe_obj) },
};
static MP_DEFINE_CONST_DICT(super_calls_Animal_locals_dict, super_calls_Animal_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    super_calls_Animal_type,
    MP_QSTR_Animal,
    MP_TYPE_FLAG_NONE,
    make_new, super_calls_Animal_make_new,
    attr, super_calls_Animal_attr,
    locals_dict, &super_calls_Animal_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} super_calls_Dog_field_t;

static const super_calls_Dog_field_t super_calls_Dog_fields[] = {
    { MP_QSTR_name, offsetof(super_calls_Dog_obj_t, super.name), 0 },
    { MP_QSTR_sound, offsetof(super_calls_Dog_obj_t, super.sound), 0 },
    { MP_QSTR_tricks, offsetof(super_calls_Dog_obj_t, tricks), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void super_calls_Dog_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    super_calls_Dog_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const super_calls_Dog_field_t *f = super_calls_Dog_fields; f->name != MP_QSTR_NULL; f++) {
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

static const super_calls_Dog_vtable_t super_calls_Dog_vtable_inst = {
    .speak = (mp_obj_t (*)(super_calls_Dog_obj_t *))super_calls_Animal_speak_native,
    .describe = super_calls_Dog_describe_native,
    .get_tricks = super_calls_Dog_get_tricks_native,
};

static mp_obj_t super_calls_Dog_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);

    super_calls_Dog_obj_t *self = mp_obj_malloc(super_calls_Dog_obj_t, type);
    self->super.vtable = (const super_calls_Animal_vtable_t *)&super_calls_Dog_vtable_inst;
    self->tricks = 0;

    super_calls_Dog___init___mp(MP_OBJ_FROM_PTR(self), args[0], args[1]);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t super_calls_Dog_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_speak), MP_ROM_PTR(&super_calls_Animal_speak_obj) },
    { MP_ROM_QSTR(MP_QSTR_describe), MP_ROM_PTR(&super_calls_Dog_describe_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_tricks), MP_ROM_PTR(&super_calls_Dog_get_tricks_obj) },
};
static MP_DEFINE_CONST_DICT(super_calls_Dog_locals_dict, super_calls_Dog_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    super_calls_Dog_type,
    MP_QSTR_Dog,
    MP_TYPE_FLAG_NONE,
    make_new, super_calls_Dog_make_new,
    attr, super_calls_Dog_attr,
    parent, &super_calls_Animal_type,
    locals_dict, &super_calls_Dog_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} super_calls_ShowDog_field_t;

static const super_calls_ShowDog_field_t super_calls_ShowDog_fields[] = {
    { MP_QSTR_name, offsetof(super_calls_ShowDog_obj_t, super.super.name), 0 },
    { MP_QSTR_sound, offsetof(super_calls_ShowDog_obj_t, super.super.sound), 0 },
    { MP_QSTR_tricks, offsetof(super_calls_ShowDog_obj_t, super.tricks), 1 },
    { MP_QSTR_awards, offsetof(super_calls_ShowDog_obj_t, awards), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void super_calls_ShowDog_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    super_calls_ShowDog_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const super_calls_ShowDog_field_t *f = super_calls_ShowDog_fields; f->name != MP_QSTR_NULL; f++) {
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

static const super_calls_ShowDog_vtable_t super_calls_ShowDog_vtable_inst = {
    .speak = (mp_obj_t (*)(super_calls_ShowDog_obj_t *))super_calls_Animal_speak_native,
    .describe = super_calls_ShowDog_describe_native,
    .get_tricks = (mp_int_t (*)(super_calls_ShowDog_obj_t *))super_calls_Dog_get_tricks_native,
    .get_awards = super_calls_ShowDog_get_awards_native,
    .get_total_score = super_calls_ShowDog_get_total_score_native,
};

static mp_obj_t super_calls_ShowDog_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 3, 3, false);

    super_calls_ShowDog_obj_t *self = mp_obj_malloc(super_calls_ShowDog_obj_t, type);
    self->super.super.vtable = (const super_calls_Animal_vtable_t *)&super_calls_ShowDog_vtable_inst;
    self->awards = 0;

    mp_obj_t init_args[4];
    init_args[0] = MP_OBJ_FROM_PTR(self);
    init_args[1] = args[0];
    init_args[2] = args[1];
    init_args[3] = args[2];
    super_calls_ShowDog___init___mp(4, init_args);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t super_calls_ShowDog_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_speak), MP_ROM_PTR(&super_calls_Animal_speak_obj) },
    { MP_ROM_QSTR(MP_QSTR_describe), MP_ROM_PTR(&super_calls_ShowDog_describe_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_tricks), MP_ROM_PTR(&super_calls_Dog_get_tricks_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_awards), MP_ROM_PTR(&super_calls_ShowDog_get_awards_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_total_score), MP_ROM_PTR(&super_calls_ShowDog_get_total_score_obj) },
};
static MP_DEFINE_CONST_DICT(super_calls_ShowDog_locals_dict, super_calls_ShowDog_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    super_calls_ShowDog_type,
    MP_QSTR_ShowDog,
    MP_TYPE_FLAG_NONE,
    make_new, super_calls_ShowDog_make_new,
    attr, super_calls_ShowDog_attr,
    parent, &super_calls_Dog_type,
    locals_dict, &super_calls_ShowDog_locals_dict
);

static const mp_rom_map_elem_t super_calls_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_super_calls) },
    { MP_ROM_QSTR(MP_QSTR_Animal), MP_ROM_PTR(&super_calls_Animal_type) },
    { MP_ROM_QSTR(MP_QSTR_Dog), MP_ROM_PTR(&super_calls_Dog_type) },
    { MP_ROM_QSTR(MP_QSTR_ShowDog), MP_ROM_PTR(&super_calls_ShowDog_type) },
};
MP_DEFINE_CONST_DICT(super_calls_module_globals, super_calls_module_globals_table);

const mp_obj_module_t super_calls_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&super_calls_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_super_calls, super_calls_user_cmodule);