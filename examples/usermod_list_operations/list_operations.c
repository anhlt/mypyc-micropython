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

static mp_obj_t list_operations_sum_range(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_int_t total = 0;
    mp_int_t i;
    mp_int_t _tmp1 = n;
    for (i = 0; i < _tmp1; i++) {
        total += i;
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_sum_range_obj, list_operations_sum_range);
static mp_obj_t list_operations_build_squares(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t result = mp_obj_new_list(0, NULL);
    mp_int_t i;
    mp_int_t _tmp2 = n;
    for (i = 0; i < _tmp2; i++) {
        mp_obj_t _tmp1 = mp_obj_list_append(result, mp_obj_new_int((i * i)));
        (void)_tmp1;
    }
    return result;
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_build_squares_obj, list_operations_build_squares);
static mp_obj_t list_operations_sum_list(mp_obj_t lst_obj) {
    mp_obj_t lst = lst_obj;

    mp_int_t total = 0;
    mp_int_t n = mp_list_len_fast(lst);
    mp_int_t i;
    mp_int_t _tmp1 = n;
    for (i = 0; i < _tmp1; i++) {
        total += mp_obj_get_int(mp_list_get_int(lst, i));
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_sum_list_obj, list_operations_sum_list);
static mp_obj_t list_operations_find_first_negative(mp_obj_t lst_obj) {
    mp_obj_t lst = lst_obj;

    mp_int_t i;
    mp_int_t _tmp1 = mp_list_len_fast(lst);
    for (i = 0; i < _tmp1; i++) {
        if ((mp_obj_get_int(mp_list_get_int(lst, i)) < 0)) {
            return mp_obj_new_int(i);
        }
    }
    return mp_obj_new_int((-1));
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_find_first_negative_obj, list_operations_find_first_negative);
static mp_obj_t list_operations_skip_zeros(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_int_t total = 0;
    mp_int_t i;
    mp_int_t _tmp1 = n;
    for (i = 0; i < _tmp1; i++) {
        if ((i == 0)) {
            continue;
        }
        total += i;
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_skip_zeros_obj, list_operations_skip_zeros);
static mp_obj_t list_operations_count_until_ten(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_int_t count = 0;
    mp_int_t i;
    mp_int_t _tmp1 = n;
    for (i = 0; i < _tmp1; i++) {
        if ((i >= 10)) {
            break;
        }
        count += 1;
    }
    return mp_obj_new_int(count);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_count_until_ten_obj, list_operations_count_until_ten);
static mp_obj_t list_operations_matrix_sum(mp_obj_t rows_obj, mp_obj_t cols_obj) {
    mp_int_t rows = mp_obj_get_int(rows_obj);
    mp_int_t cols = mp_obj_get_int(cols_obj);

    mp_int_t total = 0;
    mp_int_t i;
    mp_int_t _tmp1 = rows;
    for (i = 0; i < _tmp1; i++) {
        mp_int_t j;
        mp_int_t _tmp2 = cols;
        for (j = 0; j < _tmp2; j++) {
            total += (i + j);
        }
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_2(list_operations_matrix_sum_obj, list_operations_matrix_sum);
static mp_obj_t list_operations_reverse_sum(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_int_t total = 0;
    mp_int_t i;
    mp_int_t _tmp1 = 0;
    for (i = n; i > _tmp1; i--) {
        total += i;
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_reverse_sum_obj, list_operations_reverse_sum);
static mp_obj_t list_operations_append_many(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t lst = mp_obj_new_list(0, NULL);
    mp_int_t i;
    mp_int_t _tmp2 = n;
    for (i = 0; i < _tmp2; i++) {
        mp_obj_t _tmp1 = mp_obj_list_append(lst, mp_obj_new_int(i));
        (void)_tmp1;
    }
    mp_int_t total = 0;
    mp_int_t _tmp3 = mp_list_len_fast(lst);
    for (i = 0; i < _tmp3; i++) {
        total += mp_obj_get_int(mp_list_get_int(lst, i));
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_append_many_obj, list_operations_append_many);
static mp_obj_t list_operations_pop_all(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t lst = mp_obj_new_list(0, NULL);
    mp_int_t i;
    mp_int_t _tmp3 = n;
    for (i = 0; i < _tmp3; i++) {
        mp_obj_t _tmp1 = mp_obj_list_append(lst, mp_obj_new_int(i));
        (void)_tmp1;
    }
    mp_int_t total = 0;
    while ((mp_list_len_fast(lst) > 0)) {
        mp_obj_t _tmp2 = ({ mp_obj_t __method[2]; mp_load_method(lst, MP_QSTR_pop, __method); mp_call_method_n_kw(0, 0, __method); });
        total += mp_obj_get_int(_tmp2);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_pop_all_obj, list_operations_pop_all);
static mp_obj_t list_operations_append_pop_cycle(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_obj_t lst = mp_obj_new_list(0, NULL);
    mp_int_t total = 0;
    mp_int_t i;
    mp_int_t _tmp4 = n;
    for (i = 0; i < _tmp4; i++) {
        mp_obj_t _tmp1 = mp_obj_list_append(lst, mp_obj_new_int(i));
        (void)_tmp1;
        if ((mp_list_len_fast(lst) > 10)) {
            mp_obj_t _tmp2 = ({ mp_obj_t __method[2]; mp_load_method(lst, MP_QSTR_pop, __method); mp_call_method_n_kw(0, 0, __method); });
            total += mp_obj_get_int(_tmp2);
        }
    }
    while ((mp_list_len_fast(lst) > 0)) {
        mp_obj_t _tmp3 = ({ mp_obj_t __method[2]; mp_load_method(lst, MP_QSTR_pop, __method); mp_call_method_n_kw(0, 0, __method); });
        total += mp_obj_get_int(_tmp3);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(list_operations_append_pop_cycle_obj, list_operations_append_pop_cycle);
static const mp_rom_map_elem_t list_operations_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_list_operations) },
    { MP_ROM_QSTR(MP_QSTR_sum_range), MP_ROM_PTR(&list_operations_sum_range_obj) },
    { MP_ROM_QSTR(MP_QSTR_build_squares), MP_ROM_PTR(&list_operations_build_squares_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_list), MP_ROM_PTR(&list_operations_sum_list_obj) },
    { MP_ROM_QSTR(MP_QSTR_find_first_negative), MP_ROM_PTR(&list_operations_find_first_negative_obj) },
    { MP_ROM_QSTR(MP_QSTR_skip_zeros), MP_ROM_PTR(&list_operations_skip_zeros_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_until_ten), MP_ROM_PTR(&list_operations_count_until_ten_obj) },
    { MP_ROM_QSTR(MP_QSTR_matrix_sum), MP_ROM_PTR(&list_operations_matrix_sum_obj) },
    { MP_ROM_QSTR(MP_QSTR_reverse_sum), MP_ROM_PTR(&list_operations_reverse_sum_obj) },
    { MP_ROM_QSTR(MP_QSTR_append_many), MP_ROM_PTR(&list_operations_append_many_obj) },
    { MP_ROM_QSTR(MP_QSTR_pop_all), MP_ROM_PTR(&list_operations_pop_all_obj) },
    { MP_ROM_QSTR(MP_QSTR_append_pop_cycle), MP_ROM_PTR(&list_operations_append_pop_cycle_obj) },
};
MP_DEFINE_CONST_DICT(list_operations_module_globals, list_operations_module_globals_table);

const mp_obj_module_t list_operations_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&list_operations_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_list_operations, list_operations_user_cmodule);