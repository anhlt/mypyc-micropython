#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

static mp_obj_t sensor_lib_converters_celsius_to_fahrenheit(mp_obj_t c_obj) {
    mp_int_t c = mp_obj_get_int(c_obj);

    return mp_obj_new_int((((c * 9) / 5) + 32));
}
MP_DEFINE_CONST_FUN_OBJ_1(sensor_lib_converters_celsius_to_fahrenheit_obj, sensor_lib_converters_celsius_to_fahrenheit);
static mp_obj_t sensor_lib_converters_fahrenheit_to_celsius(mp_obj_t f_obj) {
    mp_int_t f = mp_obj_get_int(f_obj);

    return mp_obj_new_int((((f - 32) * 5) / 9));
}
MP_DEFINE_CONST_FUN_OBJ_1(sensor_lib_converters_fahrenheit_to_celsius_obj, sensor_lib_converters_fahrenheit_to_celsius);
static mp_obj_t sensor_lib_converters_mm_to_inches(mp_obj_t mm_obj) {
    mp_int_t mm = mp_obj_get_int(mm_obj);

    return mp_obj_new_int(((mm * 100) / 254));
}
MP_DEFINE_CONST_FUN_OBJ_1(sensor_lib_converters_mm_to_inches_obj, sensor_lib_converters_mm_to_inches);
static mp_obj_t sensor_lib_filters_clamp(mp_obj_t value_obj, mp_obj_t low_obj, mp_obj_t high_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t low = mp_obj_get_int(low_obj);
    mp_int_t high = mp_obj_get_int(high_obj);

    if ((value < low)) {
        return mp_obj_new_int(low);
    }
    if ((value > high)) {
        return mp_obj_new_int(high);
    }
    return mp_obj_new_int(value);
}
MP_DEFINE_CONST_FUN_OBJ_3(sensor_lib_filters_clamp_obj, sensor_lib_filters_clamp);
static mp_obj_t sensor_lib_filters_moving_avg(mp_obj_t prev_obj, mp_obj_t new_val_obj, mp_obj_t alpha_obj) {
    mp_int_t prev = mp_obj_get_int(prev_obj);
    mp_int_t new_val = mp_obj_get_int(new_val_obj);
    mp_int_t alpha = mp_obj_get_int(alpha_obj);

    return mp_obj_new_int((((alpha * new_val) + ((100 - alpha) * prev)) / 100));
}
MP_DEFINE_CONST_FUN_OBJ_3(sensor_lib_filters_moving_avg_obj, sensor_lib_filters_moving_avg);
static mp_obj_t sensor_lib_filters_threshold(mp_obj_t value_obj, mp_obj_t thresh_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t thresh = mp_obj_get_int(thresh_obj);

    return (value > thresh) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(sensor_lib_filters_threshold_obj, sensor_lib_filters_threshold);
static mp_obj_t sensor_lib_math_helpers_distance(size_t n_args, const mp_obj_t *args) {
    mp_int_t x1 = mp_obj_get_int(args[0]);
    mp_int_t y1 = mp_obj_get_int(args[1]);
    mp_int_t x2 = mp_obj_get_int(args[2]);
    mp_int_t y2 = mp_obj_get_int(args[3]);

    mp_int_t dx = (x2 - x1);
    mp_int_t dy = (y2 - y1);
    return mp_obj_new_int(((dx * dx) + (dy * dy)));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(sensor_lib_math_helpers_distance_obj, 4, 4, sensor_lib_math_helpers_distance);
static mp_obj_t sensor_lib_math_helpers_midpoint(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_obj_new_int(((a + b) / 2));
}
MP_DEFINE_CONST_FUN_OBJ_2(sensor_lib_math_helpers_midpoint_obj, sensor_lib_math_helpers_midpoint);
static mp_obj_t sensor_lib_math_helpers_scale(mp_obj_t value_obj, mp_obj_t factor_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t factor = mp_obj_get_int(factor_obj);

    return mp_obj_new_int((value * factor));
}
MP_DEFINE_CONST_FUN_OBJ_2(sensor_lib_math_helpers_scale_obj, sensor_lib_math_helpers_scale);
static mp_obj_t sensor_lib_processing_version(void) {
    return mp_obj_new_int(1);
}
MP_DEFINE_CONST_FUN_OBJ_0(sensor_lib_processing_version_obj, sensor_lib_processing_version);
static mp_obj_t sensor_lib_processing_calibration_apply_offset(mp_obj_t value_obj, mp_obj_t offset_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t offset = mp_obj_get_int(offset_obj);

    return mp_obj_new_int((value + offset));
}
MP_DEFINE_CONST_FUN_OBJ_2(sensor_lib_processing_calibration_apply_offset_obj, sensor_lib_processing_calibration_apply_offset);
static mp_obj_t sensor_lib_processing_calibration_apply_scale(mp_obj_t value_obj, mp_obj_t scale_num_obj, mp_obj_t scale_den_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t scale_num = mp_obj_get_int(scale_num_obj);
    mp_int_t scale_den = mp_obj_get_int(scale_den_obj);

    return mp_obj_new_int(((value * scale_num) / scale_den));
}
MP_DEFINE_CONST_FUN_OBJ_3(sensor_lib_processing_calibration_apply_scale_obj, sensor_lib_processing_calibration_apply_scale);
static mp_obj_t sensor_lib_processing_smoothing_exponential_avg(mp_obj_t prev_obj, mp_obj_t new_val_obj, mp_obj_t weight_obj) {
    mp_int_t prev = mp_obj_get_int(prev_obj);
    mp_int_t new_val = mp_obj_get_int(new_val_obj);
    mp_int_t weight = mp_obj_get_int(weight_obj);

    return mp_obj_new_int((((weight * new_val) + ((100 - weight) * prev)) / 100));
}
MP_DEFINE_CONST_FUN_OBJ_3(sensor_lib_processing_smoothing_exponential_avg_obj, sensor_lib_processing_smoothing_exponential_avg);
static mp_obj_t sensor_lib_processing_smoothing_simple_avg(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_obj_new_int(((a + b) / 2));
}
MP_DEFINE_CONST_FUN_OBJ_2(sensor_lib_processing_smoothing_simple_avg_obj, sensor_lib_processing_smoothing_simple_avg);
static const mp_rom_map_elem_t sensor_lib_converters_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_converters) },
    { MP_ROM_QSTR(MP_QSTR_celsius_to_fahrenheit), MP_ROM_PTR(&sensor_lib_converters_celsius_to_fahrenheit_obj) },
    { MP_ROM_QSTR(MP_QSTR_fahrenheit_to_celsius), MP_ROM_PTR(&sensor_lib_converters_fahrenheit_to_celsius_obj) },
    { MP_ROM_QSTR(MP_QSTR_mm_to_inches), MP_ROM_PTR(&sensor_lib_converters_mm_to_inches_obj) },
};
MP_DEFINE_CONST_DICT(sensor_lib_converters_globals, sensor_lib_converters_globals_table);

static const mp_obj_module_t sensor_lib_converters_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_lib_converters_globals,
};

static const mp_rom_map_elem_t sensor_lib_filters_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_filters) },
    { MP_ROM_QSTR(MP_QSTR_clamp), MP_ROM_PTR(&sensor_lib_filters_clamp_obj) },
    { MP_ROM_QSTR(MP_QSTR_moving_avg), MP_ROM_PTR(&sensor_lib_filters_moving_avg_obj) },
    { MP_ROM_QSTR(MP_QSTR_threshold), MP_ROM_PTR(&sensor_lib_filters_threshold_obj) },
};
MP_DEFINE_CONST_DICT(sensor_lib_filters_globals, sensor_lib_filters_globals_table);

static const mp_obj_module_t sensor_lib_filters_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_lib_filters_globals,
};

static const mp_rom_map_elem_t sensor_lib_math_helpers_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_math_helpers) },
    { MP_ROM_QSTR(MP_QSTR_distance), MP_ROM_PTR(&sensor_lib_math_helpers_distance_obj) },
    { MP_ROM_QSTR(MP_QSTR_midpoint), MP_ROM_PTR(&sensor_lib_math_helpers_midpoint_obj) },
    { MP_ROM_QSTR(MP_QSTR_scale), MP_ROM_PTR(&sensor_lib_math_helpers_scale_obj) },
};
MP_DEFINE_CONST_DICT(sensor_lib_math_helpers_globals, sensor_lib_math_helpers_globals_table);

static const mp_obj_module_t sensor_lib_math_helpers_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_lib_math_helpers_globals,
};

static const mp_rom_map_elem_t sensor_lib_processing_calibration_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_calibration) },
    { MP_ROM_QSTR(MP_QSTR_apply_offset), MP_ROM_PTR(&sensor_lib_processing_calibration_apply_offset_obj) },
    { MP_ROM_QSTR(MP_QSTR_apply_scale), MP_ROM_PTR(&sensor_lib_processing_calibration_apply_scale_obj) },
};
MP_DEFINE_CONST_DICT(sensor_lib_processing_calibration_globals, sensor_lib_processing_calibration_globals_table);

static const mp_obj_module_t sensor_lib_processing_calibration_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_lib_processing_calibration_globals,
};

static const mp_rom_map_elem_t sensor_lib_processing_smoothing_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_smoothing) },
    { MP_ROM_QSTR(MP_QSTR_exponential_avg), MP_ROM_PTR(&sensor_lib_processing_smoothing_exponential_avg_obj) },
    { MP_ROM_QSTR(MP_QSTR_simple_avg), MP_ROM_PTR(&sensor_lib_processing_smoothing_simple_avg_obj) },
};
MP_DEFINE_CONST_DICT(sensor_lib_processing_smoothing_globals, sensor_lib_processing_smoothing_globals_table);

static const mp_obj_module_t sensor_lib_processing_smoothing_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_lib_processing_smoothing_globals,
};

static const mp_rom_map_elem_t sensor_lib_processing_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_processing) },
    { MP_ROM_QSTR(MP_QSTR_version), MP_ROM_PTR(&sensor_lib_processing_version_obj) },
    { MP_ROM_QSTR(MP_QSTR_calibration), MP_ROM_PTR(&sensor_lib_processing_calibration_module) },
    { MP_ROM_QSTR(MP_QSTR_smoothing), MP_ROM_PTR(&sensor_lib_processing_smoothing_module) },
};
MP_DEFINE_CONST_DICT(sensor_lib_processing_globals, sensor_lib_processing_globals_table);

static const mp_obj_module_t sensor_lib_processing_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_lib_processing_globals,
};

static const mp_rom_map_elem_t sensor_lib_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sensor_lib) },
    { MP_ROM_QSTR(MP_QSTR_converters), MP_ROM_PTR(&sensor_lib_converters_module) },
    { MP_ROM_QSTR(MP_QSTR_filters), MP_ROM_PTR(&sensor_lib_filters_module) },
    { MP_ROM_QSTR(MP_QSTR_math_helpers), MP_ROM_PTR(&sensor_lib_math_helpers_module) },
    { MP_ROM_QSTR(MP_QSTR_processing), MP_ROM_PTR(&sensor_lib_processing_module) },
};
MP_DEFINE_CONST_DICT(sensor_lib_module_globals, sensor_lib_module_globals_table);

const mp_obj_module_t sensor_lib_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&sensor_lib_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_sensor_lib, sensor_lib_user_cmodule);