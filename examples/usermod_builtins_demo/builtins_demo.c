#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>
#include "py/builtin.h"

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

#include "py/objlist.h"

static inline mp_obj_t mp_list_get_fast(mp_obj_t list, size_t index) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);
    return self->items[index];
}

static inline mp_obj_t mp_list_get_neg(mp_obj_t list, mp_int_t index) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);
    return self->items[self->len + index];
}

static inline mp_obj_t mp_list_get_int(mp_obj_t list, mp_int_t index) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);
    if (index < 0) {
        index += self->len;
    }
    return self->items[index];
}

static inline size_t mp_list_len_fast(mp_obj_t list) {
    return ((mp_obj_list_t *)MP_OBJ_TO_PTR(list))->len;
}

static inline mp_int_t mp_list_sum_int(mp_obj_t list) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);
    mp_int_t sum = 0;
    for (size_t i = 0; i < self->len; i++) {
        sum += mp_obj_get_int(self->items[i]);
    }
    return sum;
}

static inline mp_float_t mp_list_sum_float(mp_obj_t list) {
    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);
    mp_float_t sum = 0.0;
    for (size_t i = 0; i < self->len; i++) {
        mp_obj_t item = self->items[i];
        if (mp_obj_is_float(item)) {
            sum += mp_obj_float_get(item);
        } else {
            sum += (mp_float_t)mp_obj_get_int(item);
        }
    }
    return sum;
}

static mp_obj_t builtins_demo_is_truthy(mp_obj_t x_obj) {
    mp_int_t x = mp_obj_get_int(x_obj);

    return mp_obj_is_true(mp_obj_new_int(x)) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(builtins_demo_is_truthy_obj, builtins_demo_is_truthy);
static mp_obj_t builtins_demo_is_list_empty(mp_obj_t lst_obj) {
    mp_obj_t lst = lst_obj;

    return (!mp_obj_is_true(lst)) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(builtins_demo_is_list_empty_obj, builtins_demo_is_list_empty);
static mp_obj_t builtins_demo_find_min_two(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_obj_new_int(((a) < (b) ? (a) : (b)));
}
MP_DEFINE_CONST_FUN_OBJ_2(builtins_demo_find_min_two_obj, builtins_demo_find_min_two);
static mp_obj_t builtins_demo_find_min_three(mp_obj_t a_obj, mp_obj_t b_obj, mp_obj_t c_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    mp_int_t c = mp_obj_get_int(c_obj);

    return mp_obj_new_int(((a) < (b) ? ((a) < (c) ? (a) : (c)) : ((b) < (c) ? (b) : (c))));
}
MP_DEFINE_CONST_FUN_OBJ_3(builtins_demo_find_min_three_obj, builtins_demo_find_min_three);
static mp_obj_t builtins_demo_find_max_two(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_obj_new_int(((a) > (b) ? (a) : (b)));
}
MP_DEFINE_CONST_FUN_OBJ_2(builtins_demo_find_max_two_obj, builtins_demo_find_max_two);
static mp_obj_t builtins_demo_find_max_three(mp_obj_t a_obj, mp_obj_t b_obj, mp_obj_t c_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    mp_int_t c = mp_obj_get_int(c_obj);

    return mp_obj_new_int(((a) > (b) ? ((a) > (c) ? (a) : (c)) : ((b) > (c) ? (b) : (c))));
}
MP_DEFINE_CONST_FUN_OBJ_3(builtins_demo_find_max_three_obj, builtins_demo_find_max_three);
static mp_obj_t builtins_demo_sum_list(mp_obj_t lst_obj) {
    mp_obj_t lst = lst_obj;

    mp_int_t total = 0;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(lst, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(builtins_demo_sum_list_obj, builtins_demo_sum_list);
static mp_obj_t builtins_demo_sum_list_with_start(mp_obj_t lst_obj, mp_obj_t start_obj) {
    mp_obj_t lst = lst_obj;
    mp_int_t start = mp_obj_get_int(start_obj);

    mp_int_t total = start;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(lst, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_2(builtins_demo_sum_list_with_start_obj, builtins_demo_sum_list_with_start);
static mp_obj_t builtins_demo_sum_int_list(mp_obj_t nums_obj) {
    mp_obj_t nums = nums_obj;

    return mp_obj_new_int(mp_list_sum_int(nums));
}
MP_DEFINE_CONST_FUN_OBJ_1(builtins_demo_sum_int_list_obj, builtins_demo_sum_int_list);
static mp_obj_t builtins_demo_clamp(mp_obj_t val_obj, mp_obj_t low_obj, mp_obj_t high_obj) {
    mp_int_t val = mp_obj_get_int(val_obj);
    mp_int_t low = mp_obj_get_int(low_obj);
    mp_int_t high = mp_obj_get_int(high_obj);

    return mp_obj_new_int(((low) > (((val) < (high) ? (val) : (high))) ? (low) : (((val) < (high) ? (val) : (high)))));
}
MP_DEFINE_CONST_FUN_OBJ_3(builtins_demo_clamp_obj, builtins_demo_clamp);
static mp_obj_t builtins_demo_abs_diff(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    return mp_binary_op(MP_BINARY_OP_SUBTRACT, mp_obj_new_int(((a) > (b) ? (a) : (b))), mp_obj_new_int(((a) < (b) ? (a) : (b))));
}
MP_DEFINE_CONST_FUN_OBJ_2(builtins_demo_abs_diff_obj, builtins_demo_abs_diff);
static mp_obj_t builtins_demo_clamp_list(mp_obj_t values_obj, mp_obj_t low_obj, mp_obj_t high_obj) {
    mp_obj_t values = values_obj;
    mp_int_t low = mp_obj_get_int(low_obj);
    mp_int_t high = mp_obj_get_int(high_obj);

    mp_obj_t result = mp_obj_new_list(0, NULL);
    mp_obj_t v;
    mp_obj_iter_buf_t _tmp3;
    mp_obj_t _tmp2 = mp_getiter(values, &_tmp3);
    while ((v = mp_iternext(_tmp2)) != MP_OBJ_STOP_ITERATION) {
        mp_int_t clamped = ((low) > (mp_obj_get_int(mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_builtin_min_obj), 2, 0, (const mp_obj_t[]){v, mp_obj_new_int(high)}))) ? (low) : (mp_obj_get_int(mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_builtin_min_obj), 2, 0, (const mp_obj_t[]){v, mp_obj_new_int(high)}))));
        mp_obj_t _tmp1 = mp_obj_list_append(result, mp_obj_new_int(clamped));
        (void)_tmp1;
    }
    return result;
}
MP_DEFINE_CONST_FUN_OBJ_3(builtins_demo_clamp_list_obj, builtins_demo_clamp_list);
static mp_obj_t builtins_demo_find_extremes_sum(mp_obj_t lst_obj) {
    mp_obj_t lst = lst_obj;

    mp_int_t min_val = mp_obj_get_int(mp_list_get_fast(lst, 0));
    mp_int_t max_val = mp_obj_get_int(mp_list_get_fast(lst, 0));
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(lst, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        if ((mp_obj_get_int(x) < min_val)) {
            min_val = mp_obj_get_int(x);
        }
        if ((mp_obj_get_int(x) > max_val)) {
            max_val = mp_obj_get_int(x);
        }
    }
    return mp_obj_new_int((min_val + max_val));
}
MP_DEFINE_CONST_FUN_OBJ_1(builtins_demo_find_extremes_sum_obj, builtins_demo_find_extremes_sum);
static const mp_rom_map_elem_t builtins_demo_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_builtins_demo) },
    { MP_ROM_QSTR(MP_QSTR_is_truthy), MP_ROM_PTR(&builtins_demo_is_truthy_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_list_empty), MP_ROM_PTR(&builtins_demo_is_list_empty_obj) },
    { MP_ROM_QSTR(MP_QSTR_find_min_two), MP_ROM_PTR(&builtins_demo_find_min_two_obj) },
    { MP_ROM_QSTR(MP_QSTR_find_min_three), MP_ROM_PTR(&builtins_demo_find_min_three_obj) },
    { MP_ROM_QSTR(MP_QSTR_find_max_two), MP_ROM_PTR(&builtins_demo_find_max_two_obj) },
    { MP_ROM_QSTR(MP_QSTR_find_max_three), MP_ROM_PTR(&builtins_demo_find_max_three_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_list), MP_ROM_PTR(&builtins_demo_sum_list_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_list_with_start), MP_ROM_PTR(&builtins_demo_sum_list_with_start_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_int_list), MP_ROM_PTR(&builtins_demo_sum_int_list_obj) },
    { MP_ROM_QSTR(MP_QSTR_clamp), MP_ROM_PTR(&builtins_demo_clamp_obj) },
    { MP_ROM_QSTR(MP_QSTR_abs_diff), MP_ROM_PTR(&builtins_demo_abs_diff_obj) },
    { MP_ROM_QSTR(MP_QSTR_clamp_list), MP_ROM_PTR(&builtins_demo_clamp_list_obj) },
    { MP_ROM_QSTR(MP_QSTR_find_extremes_sum), MP_ROM_PTR(&builtins_demo_find_extremes_sum_obj) },
};
MP_DEFINE_CONST_DICT(builtins_demo_module_globals, builtins_demo_module_globals_table);

const mp_obj_module_t builtins_demo_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&builtins_demo_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_builtins_demo, builtins_demo_user_cmodule);