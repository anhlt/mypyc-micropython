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

static mp_obj_t math_utils_celsius_to_fahrenheit(mp_obj_t c_obj) {
    mp_float_t c = mp_get_float_checked(c_obj);

    return mp_obj_new_float(((c * 1.8) + 32.0));
}
MP_DEFINE_CONST_FUN_OBJ_1(math_utils_celsius_to_fahrenheit_obj, math_utils_celsius_to_fahrenheit);
static mp_obj_t math_utils_fahrenheit_to_celsius(mp_obj_t f_obj) {
    mp_float_t f = mp_get_float_checked(f_obj);

    return mp_obj_new_float(((f - 32.0) / 1.8));
}
MP_DEFINE_CONST_FUN_OBJ_1(math_utils_fahrenheit_to_celsius_obj, math_utils_fahrenheit_to_celsius);
static mp_obj_t math_utils_clamp(mp_obj_t value_obj, mp_obj_t min_val_obj, mp_obj_t max_val_obj) {
    mp_float_t value = mp_get_float_checked(value_obj);
    mp_float_t min_val = mp_get_float_checked(min_val_obj);
    mp_float_t max_val = mp_get_float_checked(max_val_obj);

    if ((value < min_val)) {
        return mp_obj_new_float(min_val);
    }
    if ((value > max_val)) {
        return mp_obj_new_float(max_val);
    }
    return mp_obj_new_float(value);
}
MP_DEFINE_CONST_FUN_OBJ_3(math_utils_clamp_obj, math_utils_clamp);
static mp_obj_t math_utils_lerp(mp_obj_t a_obj, mp_obj_t b_obj, mp_obj_t t_obj) {
    mp_float_t a = mp_get_float_checked(a_obj);
    mp_float_t b = mp_get_float_checked(b_obj);
    mp_float_t t = mp_get_float_checked(t_obj);

    return mp_obj_new_float((a + ((b - a) * t)));
}
MP_DEFINE_CONST_FUN_OBJ_3(math_utils_lerp_obj, math_utils_lerp);
static const mp_rom_map_elem_t math_utils_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_math_utils) },
    { MP_ROM_QSTR(MP_QSTR_celsius_to_fahrenheit), MP_ROM_PTR(&math_utils_celsius_to_fahrenheit_obj) },
    { MP_ROM_QSTR(MP_QSTR_fahrenheit_to_celsius), MP_ROM_PTR(&math_utils_fahrenheit_to_celsius_obj) },
    { MP_ROM_QSTR(MP_QSTR_clamp), MP_ROM_PTR(&math_utils_clamp_obj) },
    { MP_ROM_QSTR(MP_QSTR_lerp), MP_ROM_PTR(&math_utils_lerp_obj) },
};
MP_DEFINE_CONST_DICT(math_utils_module_globals, math_utils_module_globals_table);

const mp_obj_module_t math_utils_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&math_utils_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_math_utils, math_utils_user_cmodule);