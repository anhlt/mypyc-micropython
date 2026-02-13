#include "py/runtime.h"
#include "py/obj.h"

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

static mp_obj_t dict_operations_create_config(void) {
    mp_obj_t _tmp1 = mp_obj_new_dict(3);
    mp_obj_dict_store(_tmp1, mp_obj_new_str("name", 4), mp_obj_new_str("test", 4));
    mp_obj_dict_store(_tmp1, mp_obj_new_str("value", 5), mp_obj_new_int(42));
    mp_obj_dict_store(_tmp1, mp_obj_new_str("enabled", 7), (true ? mp_const_true : mp_const_false));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_0(dict_operations_create_config_obj, dict_operations_create_config);

static mp_obj_t dict_operations_get_value(mp_obj_t d_obj, mp_obj_t key_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;

    return mp_obj_subscr(d, key, MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_2(dict_operations_get_value_obj, dict_operations_get_value);

static mp_obj_t dict_operations_set_value(mp_obj_t d_obj, mp_obj_t key_obj, mp_obj_t value_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    mp_obj_subscr(d, key, mp_obj_new_int(value));
    return d;
}
MP_DEFINE_CONST_FUN_OBJ_3(dict_operations_set_value_obj, dict_operations_set_value);

static mp_obj_t dict_operations_get_with_default(mp_obj_t d_obj, mp_obj_t key_obj, mp_obj_t default_val_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;
    mp_int_t default_val = mp_obj_get_int(default_val_obj);

    return mp_call_function_n_kw(mp_load_attr(d, MP_QSTR_get), 2, 0, (mp_obj_t[]){key, mp_obj_new_int(default_val)});
}
MP_DEFINE_CONST_FUN_OBJ_3(dict_operations_get_with_default_obj, dict_operations_get_with_default);

static mp_obj_t dict_operations_count_items(mp_obj_t d_obj) {
    mp_obj_t d = d_obj;

    return mp_obj_new_int(mp_obj_get_int(mp_obj_len(d)));
}
MP_DEFINE_CONST_FUN_OBJ_1(dict_operations_count_items_obj, dict_operations_count_items);

static mp_obj_t dict_operations_create_counter(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t result = mp_obj_new_dict(0);
    mp_int_t i;
    mp_int_t _tmp2 = n;
    for (i = 0; i < _tmp2; i++) {
        mp_obj_subscr(result, mp_obj_new_int(i), mp_obj_new_int((i * i)));
    }
    return result;
}
MP_DEFINE_CONST_FUN_OBJ_1(dict_operations_create_counter_obj, dict_operations_create_counter);

static mp_obj_t dict_operations_merge_dicts(mp_obj_t d1_obj, mp_obj_t d2_obj) {
    mp_obj_t d1 = d1_obj;
    mp_obj_t d2 = d2_obj;

    mp_obj_t result = mp_obj_new_dict(0);
    mp_obj_t key;
    mp_obj_iter_buf_t _tmp4;
    mp_obj_t _tmp3 = mp_getiter(mp_call_function_0(mp_load_attr(d1, MP_QSTR_keys)), &_tmp4);
    while ((key = mp_iternext(_tmp3)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_subscr(result, key, mp_obj_subscr(d1, key, MP_OBJ_SENTINEL));
    }
    mp_obj_iter_buf_t _tmp6;
    mp_obj_t _tmp5 = mp_getiter(mp_call_function_0(mp_load_attr(d2, MP_QSTR_keys)), &_tmp6);
    while ((key = mp_iternext(_tmp5)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_subscr(result, key, mp_obj_subscr(d2, key, MP_OBJ_SENTINEL));
    }
    return result;
}
MP_DEFINE_CONST_FUN_OBJ_2(dict_operations_merge_dicts_obj, dict_operations_merge_dicts);

static mp_obj_t dict_operations_has_key(mp_obj_t d_obj, mp_obj_t key_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;

    return (mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, key, d))) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(dict_operations_has_key_obj, dict_operations_has_key);

static mp_obj_t dict_operations_missing_key(mp_obj_t d_obj, mp_obj_t key_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;

    return (!mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, key, d))) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(dict_operations_missing_key_obj, dict_operations_missing_key);

static mp_obj_t dict_operations_copy_dict(mp_obj_t d_obj) {
    mp_obj_t d = d_obj;

    return mp_call_function_0(mp_load_attr(d, MP_QSTR_copy));
}
MP_DEFINE_CONST_FUN_OBJ_1(dict_operations_copy_dict_obj, dict_operations_copy_dict);

static mp_obj_t dict_operations_clear_dict(mp_obj_t d_obj) {
    mp_obj_t d = d_obj;

    (void)mp_call_function_0(mp_load_attr(d, MP_QSTR_clear));
    return d;
}
MP_DEFINE_CONST_FUN_OBJ_1(dict_operations_clear_dict_obj, dict_operations_clear_dict);

static mp_obj_t dict_operations_setdefault_key(mp_obj_t d_obj, mp_obj_t key_obj, mp_obj_t value_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    return mp_call_function_n_kw(mp_load_attr(d, MP_QSTR_setdefault), 2, 0, (mp_obj_t[]){key, mp_obj_new_int(value)});
}
MP_DEFINE_CONST_FUN_OBJ_3(dict_operations_setdefault_key_obj, dict_operations_setdefault_key);

static mp_obj_t dict_operations_pop_key(mp_obj_t d_obj, mp_obj_t key_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;

    return ({ mp_obj_t __method[3]; mp_load_method(d, MP_QSTR_pop, __method); __method[2] = key; mp_call_method_n_kw(1, 0, __method); });
}
MP_DEFINE_CONST_FUN_OBJ_2(dict_operations_pop_key_obj, dict_operations_pop_key);

static mp_obj_t dict_operations_pop_key_default(mp_obj_t d_obj, mp_obj_t key_obj, mp_obj_t default_val_obj) {
    mp_obj_t d = d_obj;
    mp_obj_t key = key_obj;
    mp_int_t default_val = mp_obj_get_int(default_val_obj);

    return ({ mp_obj_t __method[4]; mp_load_method(d, MP_QSTR_pop, __method); __method[2] = key; __method[3] = mp_obj_new_int(default_val); mp_call_method_n_kw(2, 0, __method); });
}
MP_DEFINE_CONST_FUN_OBJ_3(dict_operations_pop_key_default_obj, dict_operations_pop_key_default);

static mp_obj_t dict_operations_popitem_last(mp_obj_t d_obj) {
    mp_obj_t d = d_obj;

    return mp_call_function_0(mp_load_attr(d, MP_QSTR_popitem));
}
MP_DEFINE_CONST_FUN_OBJ_1(dict_operations_popitem_last_obj, dict_operations_popitem_last);

static mp_obj_t dict_operations_update_dict(mp_obj_t d1_obj, mp_obj_t d2_obj) {
    mp_obj_t d1 = d1_obj;
    mp_obj_t d2 = d2_obj;

    (void)mp_call_function_1(mp_load_attr(d1, MP_QSTR_update), d2);
    return d1;
}
MP_DEFINE_CONST_FUN_OBJ_2(dict_operations_update_dict_obj, dict_operations_update_dict);

static mp_obj_t dict_operations_copy_constructor(mp_obj_t d_obj) {
    mp_obj_t d = d_obj;

    return mp_obj_dict_copy(d);
}
MP_DEFINE_CONST_FUN_OBJ_1(dict_operations_copy_constructor_obj, dict_operations_copy_constructor);

static const mp_rom_map_elem_t dict_operations_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_dict_operations) },
    { MP_ROM_QSTR(MP_QSTR_create_config), MP_ROM_PTR(&dict_operations_create_config_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_value), MP_ROM_PTR(&dict_operations_get_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_value), MP_ROM_PTR(&dict_operations_set_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_with_default), MP_ROM_PTR(&dict_operations_get_with_default_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_items), MP_ROM_PTR(&dict_operations_count_items_obj) },
    { MP_ROM_QSTR(MP_QSTR_create_counter), MP_ROM_PTR(&dict_operations_create_counter_obj) },
    { MP_ROM_QSTR(MP_QSTR_merge_dicts), MP_ROM_PTR(&dict_operations_merge_dicts_obj) },
    { MP_ROM_QSTR(MP_QSTR_has_key), MP_ROM_PTR(&dict_operations_has_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_missing_key), MP_ROM_PTR(&dict_operations_missing_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_copy_dict), MP_ROM_PTR(&dict_operations_copy_dict_obj) },
    { MP_ROM_QSTR(MP_QSTR_clear_dict), MP_ROM_PTR(&dict_operations_clear_dict_obj) },
    { MP_ROM_QSTR(MP_QSTR_setdefault_key), MP_ROM_PTR(&dict_operations_setdefault_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_pop_key), MP_ROM_PTR(&dict_operations_pop_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_pop_key_default), MP_ROM_PTR(&dict_operations_pop_key_default_obj) },
    { MP_ROM_QSTR(MP_QSTR_popitem_last), MP_ROM_PTR(&dict_operations_popitem_last_obj) },
    { MP_ROM_QSTR(MP_QSTR_update_dict), MP_ROM_PTR(&dict_operations_update_dict_obj) },
    { MP_ROM_QSTR(MP_QSTR_copy_constructor), MP_ROM_PTR(&dict_operations_copy_constructor_obj) },
};
MP_DEFINE_CONST_DICT(dict_operations_module_globals, dict_operations_module_globals_table);

const mp_obj_module_t dict_operations_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&dict_operations_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_dict_operations, dict_operations_user_cmodule);