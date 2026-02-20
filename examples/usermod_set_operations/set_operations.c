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

static mp_obj_t set_operations_make_set(void) {
    mp_obj_t _tmp1_items[] = {mp_obj_new_int(1), mp_obj_new_int(2), mp_obj_new_int(3)};
    mp_obj_t _tmp1 = mp_obj_new_set(3, _tmp1_items);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_0(set_operations_make_set_obj, set_operations_make_set);
static mp_obj_t set_operations_empty_set(void) {
    return mp_obj_new_set(0, NULL);
}
MP_DEFINE_CONST_FUN_OBJ_0(set_operations_empty_set_obj, set_operations_empty_set);
static mp_obj_t set_operations_set_from_range(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    return mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_set), mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_range), mp_obj_new_int(n)));
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_set_from_range_obj, set_operations_set_from_range);
static mp_obj_t set_operations_set_add(mp_obj_t s_obj, mp_obj_t value_obj) {
    mp_obj_t s = s_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    mp_obj_set_store(s, mp_obj_new_int(value));
    mp_obj_t _tmp1 = mp_const_none;
    (void)_tmp1;
    return s;
}
MP_DEFINE_CONST_FUN_OBJ_2(set_operations_set_add_obj, set_operations_set_add);
static mp_obj_t set_operations_set_discard(mp_obj_t s_obj, mp_obj_t value_obj) {
    mp_obj_t s = s_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_discard), mp_obj_new_int(value));
    (void)_tmp1;
    return s;
}
MP_DEFINE_CONST_FUN_OBJ_2(set_operations_set_discard_obj, set_operations_set_discard);
static mp_obj_t set_operations_set_remove(mp_obj_t s_obj, mp_obj_t value_obj) {
    mp_obj_t s = s_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_remove), mp_obj_new_int(value));
    (void)_tmp1;
    return s;
}
MP_DEFINE_CONST_FUN_OBJ_2(set_operations_set_remove_obj, set_operations_set_remove);
static mp_obj_t set_operations_set_pop(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = ({ mp_obj_t __method[2]; mp_load_method(s, MP_QSTR_pop, __method); mp_call_method_n_kw(0, 0, __method); });
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_set_pop_obj, set_operations_set_pop);
static mp_obj_t set_operations_set_clear(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_clear));
    (void)_tmp1;
    return s;
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_set_clear_obj, set_operations_set_clear);
static mp_obj_t set_operations_set_copy(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_copy));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_set_copy_obj, set_operations_set_copy);
static mp_obj_t set_operations_set_update(mp_obj_t s1_obj, mp_obj_t s2_obj) {
    mp_obj_t s1 = s1_obj;
    mp_obj_t s2 = s2_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s1, MP_QSTR_update), s2);
    (void)_tmp1;
    return s1;
}
MP_DEFINE_CONST_FUN_OBJ_2(set_operations_set_update_obj, set_operations_set_update);
static mp_obj_t set_operations_set_len(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    return mp_obj_new_int(mp_obj_get_int(mp_obj_len(s)));
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_set_len_obj, set_operations_set_len);
static mp_obj_t set_operations_set_contains(mp_obj_t s_obj, mp_obj_t value_obj) {
    mp_obj_t s = s_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    return (mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, mp_obj_new_int(value), s))) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(set_operations_set_contains_obj, set_operations_set_contains);
static mp_obj_t set_operations_set_not_contains(mp_obj_t s_obj, mp_obj_t value_obj) {
    mp_obj_t s = s_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    return (!mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, mp_obj_new_int(value), s))) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(set_operations_set_not_contains_obj, set_operations_set_not_contains);
static mp_obj_t set_operations_sum_set(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_int_t total = 0;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(s, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_sum_set_obj, set_operations_sum_set);
static mp_obj_t set_operations_count_unique(mp_obj_t lst_obj) {
    mp_obj_t lst = lst_obj;

    mp_obj_t s = mp_obj_new_set(0, NULL);
    mp_obj_t item;
    mp_obj_iter_buf_t _tmp3;
    mp_obj_t _tmp2 = mp_getiter(lst, &_tmp3);
    while ((item = mp_iternext(_tmp2)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_set_store(s, item);
        mp_obj_t _tmp1 = mp_const_none;
        (void)_tmp1;
    }
    return mp_obj_new_int(mp_obj_get_int(mp_obj_len(s)));
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_count_unique_obj, set_operations_count_unique);
static mp_obj_t set_operations_build_set_incremental(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t s = mp_obj_new_set(0, NULL);
    mp_int_t i;
    mp_int_t _tmp2 = n;
    for (i = 0; i < _tmp2; i++) {
        mp_obj_set_store(s, mp_obj_new_int((i % 10)));
        mp_obj_t _tmp1 = mp_const_none;
        (void)_tmp1;
    }
    return mp_obj_new_int(mp_obj_get_int(mp_obj_len(s)));
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_build_set_incremental_obj, set_operations_build_set_incremental);
static mp_obj_t set_operations_filter_duplicates(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t s = mp_obj_new_set(0, NULL);
    mp_int_t i;
    mp_int_t _tmp2 = n;
    for (i = 0; i < _tmp2; i++) {
        mp_obj_set_store(s, mp_obj_new_int((i % 5)));
        mp_obj_t _tmp1 = mp_const_none;
        (void)_tmp1;
    }
    mp_int_t total = 0;
    mp_obj_t val;
    mp_obj_iter_buf_t _tmp4;
    mp_obj_t _tmp3 = mp_getiter(s, &_tmp4);
    while ((val = mp_iternext(_tmp3)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(val);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(set_operations_filter_duplicates_obj, set_operations_filter_duplicates);
static const mp_rom_map_elem_t set_operations_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_set_operations) },
    { MP_ROM_QSTR(MP_QSTR_make_set), MP_ROM_PTR(&set_operations_make_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_empty_set), MP_ROM_PTR(&set_operations_empty_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_from_range), MP_ROM_PTR(&set_operations_set_from_range_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_add), MP_ROM_PTR(&set_operations_set_add_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_discard), MP_ROM_PTR(&set_operations_set_discard_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_remove), MP_ROM_PTR(&set_operations_set_remove_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_pop), MP_ROM_PTR(&set_operations_set_pop_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_clear), MP_ROM_PTR(&set_operations_set_clear_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_copy), MP_ROM_PTR(&set_operations_set_copy_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_update), MP_ROM_PTR(&set_operations_set_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_len), MP_ROM_PTR(&set_operations_set_len_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_contains), MP_ROM_PTR(&set_operations_set_contains_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_not_contains), MP_ROM_PTR(&set_operations_set_not_contains_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_set), MP_ROM_PTR(&set_operations_sum_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_unique), MP_ROM_PTR(&set_operations_count_unique_obj) },
    { MP_ROM_QSTR(MP_QSTR_build_set_incremental), MP_ROM_PTR(&set_operations_build_set_incremental_obj) },
    { MP_ROM_QSTR(MP_QSTR_filter_duplicates), MP_ROM_PTR(&set_operations_filter_duplicates_obj) },
};
MP_DEFINE_CONST_DICT(set_operations_module_globals, set_operations_module_globals_table);

const mp_obj_module_t set_operations_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&set_operations_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_set_operations, set_operations_user_cmodule);