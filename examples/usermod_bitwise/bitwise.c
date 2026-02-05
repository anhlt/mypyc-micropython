#include "py/runtime.h"
#include "py/obj.h"

static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}

static mp_obj_t bitwise_set_bit(mp_obj_t value_obj, mp_obj_t bit_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t bit = mp_obj_get_int(bit_obj);

    return mp_obj_new_int((value | (1 << bit)));
}
MP_DEFINE_CONST_FUN_OBJ_2(bitwise_set_bit_obj, bitwise_set_bit);

static mp_obj_t bitwise_clear_bit(mp_obj_t value_obj, mp_obj_t bit_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t bit = mp_obj_get_int(bit_obj);

    return mp_obj_new_int((value & (~(1 << bit))));
}
MP_DEFINE_CONST_FUN_OBJ_2(bitwise_clear_bit_obj, bitwise_clear_bit);

static mp_obj_t bitwise_toggle_bit(mp_obj_t value_obj, mp_obj_t bit_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t bit = mp_obj_get_int(bit_obj);

    return mp_obj_new_int((value ^ (1 << bit)));
}
MP_DEFINE_CONST_FUN_OBJ_2(bitwise_toggle_bit_obj, bitwise_toggle_bit);

static mp_obj_t bitwise_check_bit(mp_obj_t value_obj, mp_obj_t bit_obj) {
    mp_int_t value = mp_obj_get_int(value_obj);
    mp_int_t bit = mp_obj_get_int(bit_obj);

    return ((value & (1 << bit)) != 0) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(bitwise_check_bit_obj, bitwise_check_bit);

static mp_obj_t bitwise_count_ones(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_int_t count = 0;
    while ((n > 0)) {
        count = (count + (n & 1));
        n = (n >> 1);
    }
    return mp_obj_new_int(count);
}
MP_DEFINE_CONST_FUN_OBJ_1(bitwise_count_ones_obj, bitwise_count_ones);

static mp_obj_t bitwise_is_power_of_two(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    if ((n <= 0)) {
        return false ? mp_const_true : mp_const_false;
    }
    return ((n & (n - 1)) == 0) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(bitwise_is_power_of_two_obj, bitwise_is_power_of_two);

static const mp_rom_map_elem_t bitwise_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bitwise) },
    { MP_ROM_QSTR(MP_QSTR_set_bit), MP_ROM_PTR(&bitwise_set_bit_obj) },
    { MP_ROM_QSTR(MP_QSTR_clear_bit), MP_ROM_PTR(&bitwise_clear_bit_obj) },
    { MP_ROM_QSTR(MP_QSTR_toggle_bit), MP_ROM_PTR(&bitwise_toggle_bit_obj) },
    { MP_ROM_QSTR(MP_QSTR_check_bit), MP_ROM_PTR(&bitwise_check_bit_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_ones), MP_ROM_PTR(&bitwise_count_ones_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_power_of_two), MP_ROM_PTR(&bitwise_is_power_of_two_obj) },
};
MP_DEFINE_CONST_DICT(bitwise_module_globals, bitwise_module_globals_table);

const mp_obj_module_t bitwise_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&bitwise_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_bitwise, bitwise_user_cmodule);