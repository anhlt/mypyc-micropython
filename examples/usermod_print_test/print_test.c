#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>
#include "py/mpprint.h"

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

static mp_obj_t print_test_test_print_string(void) {
    mp_obj_print_helper(&mp_plat_print, mp_obj_new_str("Hello from compiled C!", 22), PRINT_STR);
    mp_print_str(&mp_plat_print, "\n");
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(print_test_test_print_string_obj, print_test_test_print_string);
static mp_obj_t print_test_test_print_int(void) {
    mp_obj_print_helper(&mp_plat_print, mp_obj_new_int(42), PRINT_STR);
    mp_print_str(&mp_plat_print, "\n");
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(print_test_test_print_int_obj, print_test_test_print_int);
static mp_obj_t print_test_test_print_multiple(void) {
    mp_obj_print_helper(&mp_plat_print, mp_obj_new_str("a", 1), PRINT_STR);
    mp_print_str(&mp_plat_print, " ");
    mp_obj_print_helper(&mp_plat_print, mp_obj_new_str("b", 1), PRINT_STR);
    mp_print_str(&mp_plat_print, " ");
    mp_obj_print_helper(&mp_plat_print, mp_obj_new_str("c", 1), PRINT_STR);
    mp_print_str(&mp_plat_print, "\n");
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(print_test_test_print_multiple_obj, print_test_test_print_multiple);
static mp_obj_t print_test_test_print_calc(void) {
    mp_int_t x = 10;
    mp_int_t y = 20;
    mp_obj_print_helper(&mp_plat_print, mp_obj_new_int((x + y)), PRINT_STR);
    mp_print_str(&mp_plat_print, "\n");
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(print_test_test_print_calc_obj, print_test_test_print_calc);
static mp_obj_t print_test_greet(mp_obj_t name_obj) {
    mp_obj_t name = name_obj;

    mp_obj_print_helper(&mp_plat_print, mp_obj_new_str("Hello,", 6), PRINT_STR);
    mp_print_str(&mp_plat_print, " ");
    mp_obj_print_helper(&mp_plat_print, name, PRINT_STR);
    mp_print_str(&mp_plat_print, "\n");
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(print_test_greet_obj, print_test_greet);
static const mp_rom_map_elem_t print_test_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_print_test) },
    { MP_ROM_QSTR(MP_QSTR_test_print_string), MP_ROM_PTR(&print_test_test_print_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_test_print_int), MP_ROM_PTR(&print_test_test_print_int_obj) },
    { MP_ROM_QSTR(MP_QSTR_test_print_multiple), MP_ROM_PTR(&print_test_test_print_multiple_obj) },
    { MP_ROM_QSTR(MP_QSTR_test_print_calc), MP_ROM_PTR(&print_test_test_print_calc_obj) },
    { MP_ROM_QSTR(MP_QSTR_greet), MP_ROM_PTR(&print_test_greet_obj) },
};
MP_DEFINE_CONST_DICT(print_test_module_globals, print_test_module_globals_table);

const mp_obj_module_t print_test_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&print_test_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_print_test, print_test_user_cmodule);