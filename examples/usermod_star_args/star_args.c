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

static mp_obj_t star_args_sum_all(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_numbers = mp_obj_new_tuple(n_args > 0 ? n_args - 0 : 0, n_args > 0 ? args + 0 : NULL);

    mp_int_t total = 0;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_numbers, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(star_args_sum_all_obj, 0, star_args_sum_all);
static mp_obj_t star_args_sum_args(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_args = mp_obj_new_tuple(n_args > 0 ? n_args - 0 : 0, n_args > 0 ? args + 0 : NULL);

    mp_int_t total = 0;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_args, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(star_args_sum_args_obj, 0, star_args_sum_args);
static mp_obj_t star_args_count_args(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_items = mp_obj_new_tuple(n_args > 0 ? n_args - 0 : 0, n_args > 0 ? args + 0 : NULL);

    mp_int_t count = 0;
    mp_obj_t _;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_items, &_tmp2);
    while ((_ = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        count += 1;
    }
    return mp_obj_new_int(count);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(star_args_count_args_obj, 0, star_args_count_args);
static mp_obj_t star_args_first_or_default(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_values = mp_obj_new_tuple(n_args > 0 ? n_args - 0 : 0, n_args > 0 ? args + 0 : NULL);

    mp_obj_t v;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_values, &_tmp2);
    while ((v = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        return v;
    }
    return mp_obj_new_int((-1));
}
MP_DEFINE_CONST_FUN_OBJ_VAR(star_args_first_or_default_obj, 0, star_args_first_or_default);
static mp_obj_t star_args_log_values(size_t n_args, const mp_obj_t *args) {
    mp_int_t prefix = mp_obj_get_int(args[0]);
    mp_obj_t _star_values = mp_obj_new_tuple(n_args > 1 ? n_args - 1 : 0, n_args > 1 ? args + 1 : NULL);

    mp_int_t total = prefix;
    mp_obj_t v;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_values, &_tmp2);
    while ((v = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(v);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(star_args_log_values_obj, 1, star_args_log_values);
static mp_obj_t star_args_count_kwargs(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    mp_obj_t _star_kwargs = mp_obj_new_dict(kw_args ? kw_args->used : 0);
    if (kw_args) {
        for (size_t i = 0; i < kw_args->alloc; i++) {
            if (mp_map_slot_is_filled(kw_args, i)) {
                mp_obj_dict_store(_star_kwargs, kw_args->table[i].key, kw_args->table[i].value);
            }
        }
    }

    mp_int_t count = 0;
    mp_obj_t k;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_kwargs, &_tmp2);
    while ((k = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        count += 1;
    }
    return mp_obj_new_int(count);
}
MP_DEFINE_CONST_FUN_OBJ_KW(star_args_count_kwargs_obj, 0, star_args_count_kwargs);
static mp_obj_t star_args_make_config(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    mp_obj_t _star_options = mp_obj_new_dict(kw_args ? kw_args->used : 0);
    if (kw_args) {
        for (size_t i = 0; i < kw_args->alloc; i++) {
            if (mp_map_slot_is_filled(kw_args, i)) {
                mp_obj_dict_store(_star_options, kw_args->table[i].key, kw_args->table[i].value);
            }
        }
    }

    return _star_options;
}
MP_DEFINE_CONST_FUN_OBJ_KW(star_args_make_config_obj, 0, star_args_make_config);
static mp_obj_t star_args_process(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args) {
    mp_int_t name = mp_obj_get_int(pos_args[0]);
    mp_obj_t _star_args = mp_obj_new_tuple(n_args > 1 ? n_args - 1 : 0, n_args > 1 ? pos_args + 1 : NULL);
    mp_obj_t _star_kwargs = mp_obj_new_dict(kw_args ? kw_args->used : 0);
    if (kw_args) {
        for (size_t i = 0; i < kw_args->alloc; i++) {
            if (mp_map_slot_is_filled(kw_args, i)) {
                mp_obj_dict_store(_star_kwargs, kw_args->table[i].key, kw_args->table[i].value);
            }
        }
    }

    mp_int_t total = name;
    mp_obj_t a;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_args, &_tmp2);
    while ((a = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(a);
    }
    mp_obj_t k;
    mp_obj_iter_buf_t _tmp4;
    mp_obj_t _tmp3 = mp_getiter(_star_kwargs, &_tmp4);
    while ((k = mp_iternext(_tmp3)) != MP_OBJ_STOP_ITERATION) {
        total += 1;
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_KW(star_args_process_obj, 1, star_args_process);
static mp_obj_t star_args_max_of_args(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_nums = mp_obj_new_tuple(n_args > 0 ? n_args - 0 : 0, n_args > 0 ? args + 0 : NULL);

    mp_int_t result = 0;
    bool first = true;
    mp_obj_t n;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_nums, &_tmp2);
    while ((n = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        mp_int_t val = mp_obj_get_int(n);
        if (first) {
            result = val;
            first = false;
        } else {
            if ((val > result)) {
                result = val;
            }
        }
    }
    return mp_obj_new_int(result);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(star_args_max_of_args_obj, 0, star_args_max_of_args);
static mp_obj_t star_args_min_of_args(size_t n_args, const mp_obj_t *args) {
    mp_obj_t _star_nums = mp_obj_new_tuple(n_args > 0 ? n_args - 0 : 0, n_args > 0 ? args + 0 : NULL);

    mp_int_t result = 0;
    bool first = true;
    mp_obj_t n;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(_star_nums, &_tmp2);
    while ((n = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        mp_int_t val = mp_obj_get_int(n);
        if (first) {
            result = val;
            first = false;
        } else {
            if ((val < result)) {
                result = val;
            }
        }
    }
    return mp_obj_new_int(result);
}
MP_DEFINE_CONST_FUN_OBJ_VAR(star_args_min_of_args_obj, 0, star_args_min_of_args);
static const mp_rom_map_elem_t star_args_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_star_args) },
    { MP_ROM_QSTR(MP_QSTR_sum_all), MP_ROM_PTR(&star_args_sum_all_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_args), MP_ROM_PTR(&star_args_sum_args_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_args), MP_ROM_PTR(&star_args_count_args_obj) },
    { MP_ROM_QSTR(MP_QSTR_first_or_default), MP_ROM_PTR(&star_args_first_or_default_obj) },
    { MP_ROM_QSTR(MP_QSTR_log_values), MP_ROM_PTR(&star_args_log_values_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_kwargs), MP_ROM_PTR(&star_args_count_kwargs_obj) },
    { MP_ROM_QSTR(MP_QSTR_make_config), MP_ROM_PTR(&star_args_make_config_obj) },
    { MP_ROM_QSTR(MP_QSTR_process), MP_ROM_PTR(&star_args_process_obj) },
    { MP_ROM_QSTR(MP_QSTR_max_of_args), MP_ROM_PTR(&star_args_max_of_args_obj) },
    { MP_ROM_QSTR(MP_QSTR_min_of_args), MP_ROM_PTR(&star_args_min_of_args_obj) },
};
MP_DEFINE_CONST_DICT(star_args_module_globals, star_args_module_globals_table);

const mp_obj_module_t star_args_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&star_args_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_star_args, star_args_user_cmodule);