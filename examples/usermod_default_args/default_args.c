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

static mp_obj_t default_args_add_with_default(size_t n_args, const mp_obj_t *args) {
    mp_int_t a = mp_obj_get_int(args[0]);
    mp_int_t b = (n_args > 1) ? mp_obj_get_int(args[1]) : 10;

    return mp_obj_new_int((a + b));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_add_with_default_obj, 1, 2, default_args_add_with_default);
static mp_obj_t default_args_scale(size_t n_args, const mp_obj_t *args) {
    mp_float_t x = mp_get_float_checked(args[0]);
    mp_float_t factor = (n_args > 1) ? mp_get_float_checked(args[1]) : 2.0;

    return mp_obj_new_float((x * factor));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_scale_obj, 1, 2, default_args_scale);
static mp_obj_t default_args_clamp(size_t n_args, const mp_obj_t *args) {
    mp_int_t value = mp_obj_get_int(args[0]);
    mp_int_t low = (n_args > 1) ? mp_obj_get_int(args[1]) : 0;
    mp_int_t high = (n_args > 2) ? mp_obj_get_int(args[2]) : 100;

    if ((value < low)) {
        return mp_obj_new_int(low);
    }
    if ((value > high)) {
        return mp_obj_new_int(high);
    }
    return mp_obj_new_int(value);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_clamp_obj, 1, 3, default_args_clamp);
static mp_obj_t default_args_increment(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[0]);
    mp_int_t step = (n_args > 1) ? mp_obj_get_int(args[1]) : 1;

    return mp_obj_new_int((x + step));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_increment_obj, 1, 2, default_args_increment);
static mp_obj_t default_args_double_if_flag(size_t n_args, const mp_obj_t *args) {
    mp_int_t x = mp_obj_get_int(args[0]);
    bool flag = (n_args > 1) ? mp_obj_is_true(args[1]) : true;

    if (flag) {
        return mp_obj_new_int((x * 2));
    }
    return mp_obj_new_int(x);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_double_if_flag_obj, 1, 2, default_args_double_if_flag);
static mp_obj_t default_args_format_number(size_t n_args, const mp_obj_t *args) {
    mp_int_t n = mp_obj_get_int(args[0]);
    mp_obj_t prefix = (n_args > 1) ? args[1] : mp_obj_new_str("#", 1);

    return prefix;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_format_number_obj, 1, 2, default_args_format_number);
static mp_obj_t default_args_sum_with_start(size_t n_args, const mp_obj_t *args) {
    mp_obj_t lst = args[0];
    mp_int_t start = (n_args > 1) ? mp_obj_get_int(args[1]) : 0;

    mp_int_t total = start;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(lst, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_sum_with_start_obj, 1, 2, default_args_sum_with_start);
static mp_obj_t default_args_all_defaults(size_t n_args, const mp_obj_t *args) {
    mp_int_t a = (n_args > 0) ? mp_obj_get_int(args[0]) : 1;
    mp_int_t b = (n_args > 1) ? mp_obj_get_int(args[1]) : 2;
    mp_int_t c = (n_args > 2) ? mp_obj_get_int(args[2]) : 3;

    return mp_obj_new_int(((a + b) + c));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_all_defaults_obj, 0, 3, default_args_all_defaults);
static mp_obj_t default_args_power(size_t n_args, const mp_obj_t *args) {
    mp_int_t base = mp_obj_get_int(args[0]);
    mp_int_t exp = (n_args > 1) ? mp_obj_get_int(args[1]) : 2;

    mp_int_t result = 1;
    mp_int_t _;
    mp_int_t _tmp1 = exp;
    for (_ = 0; _ < _tmp1; _++) {
        result *= base;
    }
    return mp_obj_new_int(result);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_power_obj, 1, 2, default_args_power);
static mp_obj_t default_args_lerp(size_t n_args, const mp_obj_t *args) {
    mp_float_t a = mp_get_float_checked(args[0]);
    mp_float_t b = mp_get_float_checked(args[1]);
    mp_float_t t = (n_args > 2) ? mp_get_float_checked(args[2]) : 0.5;

    return mp_obj_new_float((a + ((b - a) * t)));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(default_args_lerp_obj, 2, 3, default_args_lerp);
static const mp_rom_map_elem_t default_args_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_default_args) },
    { MP_ROM_QSTR(MP_QSTR_add_with_default), MP_ROM_PTR(&default_args_add_with_default_obj) },
    { MP_ROM_QSTR(MP_QSTR_scale), MP_ROM_PTR(&default_args_scale_obj) },
    { MP_ROM_QSTR(MP_QSTR_clamp), MP_ROM_PTR(&default_args_clamp_obj) },
    { MP_ROM_QSTR(MP_QSTR_increment), MP_ROM_PTR(&default_args_increment_obj) },
    { MP_ROM_QSTR(MP_QSTR_double_if_flag), MP_ROM_PTR(&default_args_double_if_flag_obj) },
    { MP_ROM_QSTR(MP_QSTR_format_number), MP_ROM_PTR(&default_args_format_number_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_with_start), MP_ROM_PTR(&default_args_sum_with_start_obj) },
    { MP_ROM_QSTR(MP_QSTR_all_defaults), MP_ROM_PTR(&default_args_all_defaults_obj) },
    { MP_ROM_QSTR(MP_QSTR_power), MP_ROM_PTR(&default_args_power_obj) },
    { MP_ROM_QSTR(MP_QSTR_lerp), MP_ROM_PTR(&default_args_lerp_obj) },
};
MP_DEFINE_CONST_DICT(default_args_module_globals, default_args_module_globals_table);

const mp_obj_module_t default_args_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&default_args_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_default_args, default_args_user_cmodule);