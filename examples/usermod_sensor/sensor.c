#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _sensor_SensorReading_obj_t sensor_SensorReading_obj_t;
typedef struct _sensor_SensorBuffer_obj_t sensor_SensorBuffer_obj_t;
typedef struct _sensor_SensorBuffer_vtable_t sensor_SensorBuffer_vtable_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _sensor_SensorReading_obj_t {
    mp_obj_base_t base;
    mp_int_t sensor_id;
    mp_float_t temperature;
    mp_float_t humidity;
    bool valid;
};

struct _sensor_SensorBuffer_vtable_t {
    void (*add_reading)(sensor_SensorBuffer_obj_t *self, mp_float_t temp, mp_float_t humidity);
    mp_float_t (*avg_temperature)(sensor_SensorBuffer_obj_t *self);
    mp_float_t (*avg_humidity)(sensor_SensorBuffer_obj_t *self);
    void (*reset)(sensor_SensorBuffer_obj_t *self);
};

struct _sensor_SensorBuffer_obj_t {
    mp_obj_base_t base;
    const sensor_SensorBuffer_vtable_t *vtable;
    mp_int_t count;
    mp_float_t sum_temp;
    mp_float_t sum_humidity;
};


static mp_obj_t sensor_SensorBuffer___init___mp(mp_obj_t self_in) {
    sensor_SensorBuffer_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->count = 0;
    self->sum_temp = 0.0;
    self->sum_humidity = 0.0;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(sensor_SensorBuffer___init___obj, sensor_SensorBuffer___init___mp);

static void sensor_SensorBuffer_add_reading_native(sensor_SensorBuffer_obj_t *self, mp_float_t temp, mp_float_t humidity) {
    self->count += 1;
    self->sum_temp += temp;
    self->sum_humidity += humidity;
    return;
}

static mp_obj_t sensor_SensorBuffer_add_reading_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    sensor_SensorBuffer_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_float_t temp = mp_obj_get_float(arg0_obj);
    mp_float_t humidity = mp_obj_get_float(arg1_obj);
    sensor_SensorBuffer_add_reading_native(self, temp, humidity);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(sensor_SensorBuffer_add_reading_obj, sensor_SensorBuffer_add_reading_mp);

static mp_float_t sensor_SensorBuffer_avg_temperature_native(sensor_SensorBuffer_obj_t *self) {
    if ((self->count == 0)) {
        return 0.0;
    }
    return (self->sum_temp / self->count);
}

static mp_obj_t sensor_SensorBuffer_avg_temperature_mp(mp_obj_t self_in) {
    sensor_SensorBuffer_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_float(sensor_SensorBuffer_avg_temperature_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(sensor_SensorBuffer_avg_temperature_obj, sensor_SensorBuffer_avg_temperature_mp);

static mp_float_t sensor_SensorBuffer_avg_humidity_native(sensor_SensorBuffer_obj_t *self) {
    if ((self->count == 0)) {
        return 0.0;
    }
    return (self->sum_humidity / self->count);
}

static mp_obj_t sensor_SensorBuffer_avg_humidity_mp(mp_obj_t self_in) {
    sensor_SensorBuffer_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_float(sensor_SensorBuffer_avg_humidity_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(sensor_SensorBuffer_avg_humidity_obj, sensor_SensorBuffer_avg_humidity_mp);

static void sensor_SensorBuffer_reset_native(sensor_SensorBuffer_obj_t *self) {
    self->count = 0;
    self->sum_temp = 0.0;
    self->sum_humidity = 0.0;
    return;
}

static mp_obj_t sensor_SensorBuffer_reset_mp(mp_obj_t self_in) {
    sensor_SensorBuffer_obj_t *self = MP_OBJ_TO_PTR(self_in);
    sensor_SensorBuffer_reset_native(self);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(sensor_SensorBuffer_reset_obj, sensor_SensorBuffer_reset_mp);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} sensor_SensorReading_field_t;

static const sensor_SensorReading_field_t sensor_SensorReading_fields[] = {
    { MP_QSTR_sensor_id, offsetof(sensor_SensorReading_obj_t, sensor_id), 1 },
    { MP_QSTR_temperature, offsetof(sensor_SensorReading_obj_t, temperature), 2 },
    { MP_QSTR_humidity, offsetof(sensor_SensorReading_obj_t, humidity), 2 },
    { MP_QSTR_valid, offsetof(sensor_SensorReading_obj_t, valid), 3 },
    { MP_QSTR_NULL, 0, 0 }
};

static void sensor_SensorReading_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    sensor_SensorReading_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const sensor_SensorReading_field_t *f = sensor_SensorReading_fields; f->name != MP_QSTR_NULL; f++) {
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

static void sensor_SensorReading_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    sensor_SensorReading_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "SensorReading(");
    mp_printf(print, "sensor_id=%d", (int)self->sensor_id);
    mp_printf(print, ", temperature=");
    mp_obj_print_helper(print, mp_obj_new_float(self->temperature), PRINT_REPR);
    mp_printf(print, ", humidity=");
    mp_obj_print_helper(print, mp_obj_new_float(self->humidity), PRINT_REPR);
    mp_printf(print, ", valid=%s", self->valid ? "True" : "False");
    mp_printf(print, ")");
}

static mp_obj_t sensor_SensorReading_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op != MP_BINARY_OP_EQUAL) {
        return MP_OBJ_NULL;
    }

    if (!mp_obj_is_type(rhs_in, &sensor_SensorReading_type)) {
        return mp_const_false;
    }

    sensor_SensorReading_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
    sensor_SensorReading_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);

    return mp_obj_new_bool(
        lhs->sensor_id == rhs->sensor_id &&
        lhs->temperature == rhs->temperature &&
        lhs->humidity == rhs->humidity &&
        lhs->valid == rhs->valid
    );
}

static mp_obj_t sensor_SensorReading_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_sensor_id,
        ARG_temperature,
        ARG_humidity,
        ARG_valid,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_sensor_id, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_temperature, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_humidity, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_valid, MP_ARG_BOOL, {.u_bool = true} },
    };

    mp_arg_val_t parsed[4];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 4, allowed_args, parsed);

    sensor_SensorReading_obj_t *self = mp_obj_malloc(sensor_SensorReading_obj_t, type);
    self->sensor_id = parsed[ARG_sensor_id].u_int;
    self->temperature = mp_obj_get_float(parsed[ARG_temperature].u_obj);
    self->humidity = mp_obj_get_float(parsed[ARG_humidity].u_obj);
    self->valid = parsed[ARG_valid].u_bool;

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t sensor_SensorReading_locals_dict_table[] = {
};
static MP_DEFINE_CONST_DICT(sensor_SensorReading_locals_dict, sensor_SensorReading_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    sensor_SensorReading_type,
    MP_QSTR_SensorReading,
    MP_TYPE_FLAG_NONE,
    make_new, sensor_SensorReading_make_new,
    attr, sensor_SensorReading_attr,
    print, sensor_SensorReading_print,
    binary_op, sensor_SensorReading_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} sensor_SensorBuffer_field_t;

static const sensor_SensorBuffer_field_t sensor_SensorBuffer_fields[] = {
    { MP_QSTR_count, offsetof(sensor_SensorBuffer_obj_t, count), 1 },
    { MP_QSTR_sum_temp, offsetof(sensor_SensorBuffer_obj_t, sum_temp), 2 },
    { MP_QSTR_sum_humidity, offsetof(sensor_SensorBuffer_obj_t, sum_humidity), 2 },
    { MP_QSTR_NULL, 0, 0 }
};

static void sensor_SensorBuffer_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    sensor_SensorBuffer_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const sensor_SensorBuffer_field_t *f = sensor_SensorBuffer_fields; f->name != MP_QSTR_NULL; f++) {
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

static const sensor_SensorBuffer_vtable_t sensor_SensorBuffer_vtable_inst = {
    .add_reading = sensor_SensorBuffer_add_reading_native,
    .avg_temperature = sensor_SensorBuffer_avg_temperature_native,
    .avg_humidity = sensor_SensorBuffer_avg_humidity_native,
    .reset = sensor_SensorBuffer_reset_native,
};

static mp_obj_t sensor_SensorBuffer_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);

    sensor_SensorBuffer_obj_t *self = mp_obj_malloc(sensor_SensorBuffer_obj_t, type);
    self->vtable = &sensor_SensorBuffer_vtable_inst;
    self->count = 0;
    self->sum_temp = 0.0;
    self->sum_humidity = 0.0;

    sensor_SensorBuffer___init___mp(MP_OBJ_FROM_PTR(self));

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t sensor_SensorBuffer_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_add_reading), MP_ROM_PTR(&sensor_SensorBuffer_add_reading_obj) },
    { MP_ROM_QSTR(MP_QSTR_avg_temperature), MP_ROM_PTR(&sensor_SensorBuffer_avg_temperature_obj) },
    { MP_ROM_QSTR(MP_QSTR_avg_humidity), MP_ROM_PTR(&sensor_SensorBuffer_avg_humidity_obj) },
    { MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&sensor_SensorBuffer_reset_obj) },
};
static MP_DEFINE_CONST_DICT(sensor_SensorBuffer_locals_dict, sensor_SensorBuffer_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    sensor_SensorBuffer_type,
    MP_QSTR_SensorBuffer,
    MP_TYPE_FLAG_NONE,
    make_new, sensor_SensorBuffer_make_new,
    attr, sensor_SensorBuffer_attr,
    locals_dict, &sensor_SensorBuffer_locals_dict
);

static const mp_rom_map_elem_t sensor_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sensor) },
    { MP_ROM_QSTR(MP_QSTR_SensorReading), MP_ROM_PTR(&sensor_SensorReading_type) },
    { MP_ROM_QSTR(MP_QSTR_SensorBuffer), MP_ROM_PTR(&sensor_SensorBuffer_type) },
};
MP_DEFINE_CONST_DICT(sensor_module_globals, sensor_module_globals_table);

const mp_obj_module_t sensor_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_sensor, sensor_user_cmodule);