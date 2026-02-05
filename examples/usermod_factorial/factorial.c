#include "py/runtime.h"
#include "py/obj.h"

static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}

static mp_obj_t factorial_factorial(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    if ((n <= 1)) {
        return mp_obj_new_int(1);
    }
    return mp_obj_new_int((n * mp_obj_get_int(factorial_factorial(mp_obj_new_int((n - 1))))));
}
MP_DEFINE_CONST_FUN_OBJ_1(factorial_factorial_obj, factorial_factorial);

static mp_obj_t factorial_fib(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    if ((n <= 1)) {
        return mp_obj_new_int(n);
    }
    return mp_obj_new_int((mp_obj_get_int(factorial_fib(mp_obj_new_int((n - 2)))) + mp_obj_get_int(factorial_fib(mp_obj_new_int((n - 1))))));
}
MP_DEFINE_CONST_FUN_OBJ_1(factorial_fib_obj, factorial_fib);

static mp_obj_t factorial_add(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_obj_new_int((a + b));
}
MP_DEFINE_CONST_FUN_OBJ_2(factorial_add_obj, factorial_add);

static mp_obj_t factorial_multiply(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_float_t a = mp_get_float_checked(a_obj);
    mp_float_t b = mp_get_float_checked(b_obj);

    return mp_obj_new_float((a * b));
}
MP_DEFINE_CONST_FUN_OBJ_2(factorial_multiply_obj, factorial_multiply);

static mp_obj_t factorial_is_even(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    return ((n % 2) == 0) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(factorial_is_even_obj, factorial_is_even);

static const mp_rom_map_elem_t factorial_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_factorial) },
    { MP_ROM_QSTR(MP_QSTR_factorial), MP_ROM_PTR(&factorial_factorial_obj) },
    { MP_ROM_QSTR(MP_QSTR_fib), MP_ROM_PTR(&factorial_fib_obj) },
    { MP_ROM_QSTR(MP_QSTR_add), MP_ROM_PTR(&factorial_add_obj) },
    { MP_ROM_QSTR(MP_QSTR_multiply), MP_ROM_PTR(&factorial_multiply_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_even), MP_ROM_PTR(&factorial_is_even_obj) },
};
MP_DEFINE_CONST_DICT(factorial_module_globals, factorial_module_globals_table);

const mp_obj_module_t factorial_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&factorial_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_factorial, factorial_user_cmodule);