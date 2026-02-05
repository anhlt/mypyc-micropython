#include "py/runtime.h"
#include "py/obj.h"

static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}

static mp_obj_t algorithms_is_prime(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    if ((n < 2)) {
        return false ? mp_const_true : mp_const_false;
    }
    if ((n == 2)) {
        return true ? mp_const_true : mp_const_false;
    }
    if (((n % 2) == 0)) {
        return false ? mp_const_true : mp_const_false;
    }
    mp_int_t i = 3;
    while (((i * i) <= n)) {
        if (((n % i) == 0)) {
            return false ? mp_const_true : mp_const_false;
        }
        i = (i + 2);
    }
    return true ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(algorithms_is_prime_obj, algorithms_is_prime);

static mp_obj_t algorithms_gcd(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    if ((b == 0)) {
        return mp_obj_new_int(a);
    }
    return mp_obj_new_int(mp_obj_get_int(algorithms_gcd(mp_obj_new_int(b), mp_obj_new_int((a % b)))));
}
MP_DEFINE_CONST_FUN_OBJ_2(algorithms_gcd_obj, algorithms_gcd);

static mp_obj_t algorithms_lcm(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_obj_new_int(((a * b) / mp_obj_get_int(algorithms_gcd(mp_obj_new_int(a), mp_obj_new_int(b)))));
}
MP_DEFINE_CONST_FUN_OBJ_2(algorithms_lcm_obj, algorithms_lcm);

static mp_obj_t algorithms_power(mp_obj_t base_obj, mp_obj_t exp_obj) {
    mp_int_t base = mp_obj_get_int(base_obj);
    mp_int_t exp = mp_obj_get_int(exp_obj);

    if ((exp == 0)) {
        return mp_obj_new_int(1);
    }
    if ((exp == 1)) {
        return mp_obj_new_int(base);
    }
    mp_int_t half = mp_obj_get_int(algorithms_power(mp_obj_new_int(base), mp_obj_new_int((exp / 2))));
    if (((exp % 2) == 0)) {
        return mp_obj_new_int((half * half));
    }
    return mp_obj_new_int(((half * half) * base));
}
MP_DEFINE_CONST_FUN_OBJ_2(algorithms_power_obj, algorithms_power);

static const mp_rom_map_elem_t algorithms_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_algorithms) },
    { MP_ROM_QSTR(MP_QSTR_is_prime), MP_ROM_PTR(&algorithms_is_prime_obj) },
    { MP_ROM_QSTR(MP_QSTR_gcd), MP_ROM_PTR(&algorithms_gcd_obj) },
    { MP_ROM_QSTR(MP_QSTR_lcm), MP_ROM_PTR(&algorithms_lcm_obj) },
    { MP_ROM_QSTR(MP_QSTR_power), MP_ROM_PTR(&algorithms_power_obj) },
};
MP_DEFINE_CONST_DICT(algorithms_module_globals, algorithms_module_globals_table);

const mp_obj_module_t algorithms_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&algorithms_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_algorithms, algorithms_user_cmodule);