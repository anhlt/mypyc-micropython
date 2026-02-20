#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct {
    mp_int_t f0;
    mp_int_t f1;
    mp_int_t f2;
} rtuple_int_int_int_t;
typedef struct {
    mp_int_t f0;
    mp_int_t f1;
} rtuple_int_int_t;

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

static mp_obj_t tuple_operations_make_point(void) {
    mp_obj_t _tmp1_items[] = {mp_obj_new_int(10), mp_obj_new_int(20)};
    mp_obj_t _tmp1 = mp_obj_new_tuple(2, _tmp1_items);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_0(tuple_operations_make_point_obj, tuple_operations_make_point);
static mp_obj_t tuple_operations_make_triple(mp_obj_t a_obj, mp_obj_t b_obj, mp_obj_t c_obj) {
    mp_int_t a = mp_obj_get_int(a_obj);
    mp_int_t b = mp_obj_get_int(b_obj);
    mp_int_t c = mp_obj_get_int(c_obj);

    mp_obj_t _tmp1_items[] = {mp_obj_new_int(a), mp_obj_new_int(b), mp_obj_new_int(c)};
    mp_obj_t _tmp1 = mp_obj_new_tuple(3, _tmp1_items);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_3(tuple_operations_make_triple_obj, tuple_operations_make_triple);
static mp_obj_t tuple_operations_get_first(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    return mp_obj_subscr(t, mp_obj_new_int(0), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_get_first_obj, tuple_operations_get_first);
static mp_obj_t tuple_operations_get_last(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    return mp_obj_subscr(t, mp_obj_new_int((-1)), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_get_last_obj, tuple_operations_get_last);
static mp_obj_t tuple_operations_tuple_len(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    return mp_obj_new_int(mp_obj_get_int(mp_obj_len(t)));
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_tuple_len_obj, tuple_operations_tuple_len);
static mp_obj_t tuple_operations_sum_tuple(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    mp_int_t total = 0;
    mp_obj_t x;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(t, &_tmp2);
    while ((x = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(x);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_sum_tuple_obj, tuple_operations_sum_tuple);
static mp_obj_t tuple_operations_tuple_contains(mp_obj_t t_obj, mp_obj_t value_obj) {
    mp_obj_t t = t_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    return (mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, mp_obj_new_int(value), t))) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(tuple_operations_tuple_contains_obj, tuple_operations_tuple_contains);
static mp_obj_t tuple_operations_tuple_not_contains(mp_obj_t t_obj, mp_obj_t value_obj) {
    mp_obj_t t = t_obj;
    mp_int_t value = mp_obj_get_int(value_obj);

    return (!mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, mp_obj_new_int(value), t))) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(tuple_operations_tuple_not_contains_obj, tuple_operations_tuple_not_contains);
static mp_obj_t tuple_operations_unpack_pair(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    mp_int_t a = 0;
    mp_int_t b = 0;
    mp_obj_t _tmp1 = t;
    a = mp_obj_get_int(mp_obj_subscr(_tmp1, mp_obj_new_int(0), MP_OBJ_SENTINEL));
    b = mp_obj_get_int(mp_obj_subscr(_tmp1, mp_obj_new_int(1), MP_OBJ_SENTINEL));
    return mp_obj_new_int((a + b));
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_unpack_pair_obj, tuple_operations_unpack_pair);
static mp_obj_t tuple_operations_unpack_triple(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    mp_int_t x = 0;
    mp_int_t y = 0;
    mp_int_t z = 0;
    mp_obj_t _tmp1 = t;
    x = mp_obj_get_int(mp_obj_subscr(_tmp1, mp_obj_new_int(0), MP_OBJ_SENTINEL));
    y = mp_obj_get_int(mp_obj_subscr(_tmp1, mp_obj_new_int(1), MP_OBJ_SENTINEL));
    z = mp_obj_get_int(mp_obj_subscr(_tmp1, mp_obj_new_int(2), MP_OBJ_SENTINEL));
    return mp_obj_new_int(((x * y) * z));
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_unpack_triple_obj, tuple_operations_unpack_triple);
static mp_obj_t tuple_operations_concat_tuples(mp_obj_t t1_obj, mp_obj_t t2_obj) {
    mp_obj_t t1 = t1_obj;
    mp_obj_t t2 = t2_obj;

    return mp_binary_op(MP_BINARY_OP_ADD, t1, t2);
}
MP_DEFINE_CONST_FUN_OBJ_2(tuple_operations_concat_tuples_obj, tuple_operations_concat_tuples);
static mp_obj_t tuple_operations_repeat_tuple(mp_obj_t t_obj, mp_obj_t n_obj) {
    mp_obj_t t = t_obj;
    mp_int_t n = mp_obj_get_int(n_obj);

    return mp_binary_op(MP_BINARY_OP_MULTIPLY, t, mp_obj_new_int(n));
}
MP_DEFINE_CONST_FUN_OBJ_2(tuple_operations_repeat_tuple_obj, tuple_operations_repeat_tuple);
static mp_obj_t tuple_operations_empty_tuple(void) {
    return mp_const_empty_tuple;
}
MP_DEFINE_CONST_FUN_OBJ_0(tuple_operations_empty_tuple_obj, tuple_operations_empty_tuple);
static mp_obj_t tuple_operations_single_element(void) {
    mp_obj_t _tmp1_items[] = {mp_obj_new_int(42)};
    mp_obj_t _tmp1 = mp_obj_new_tuple(1, _tmp1_items);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_0(tuple_operations_single_element_obj, tuple_operations_single_element);
static mp_obj_t tuple_operations_nested_iteration(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    mp_int_t total = 0;
    mp_int_t idx = 0;
    mp_obj_t val;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(t, &_tmp2);
    while ((val = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        total += mp_obj_get_int(mp_binary_op(MP_BINARY_OP_MULTIPLY, val, mp_obj_new_int(idx)));
        idx += 1;
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_nested_iteration_obj, tuple_operations_nested_iteration);
static mp_obj_t tuple_operations_slice_tuple(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    return mp_obj_subscr(t, mp_obj_new_slice(mp_obj_new_int(1), mp_obj_new_int(3), mp_const_none), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_slice_tuple_obj, tuple_operations_slice_tuple);
static mp_obj_t tuple_operations_reverse_tuple(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    return mp_obj_subscr(t, mp_obj_new_slice(mp_const_none, mp_const_none, mp_obj_new_int((-1))), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_reverse_tuple_obj, tuple_operations_reverse_tuple);
static mp_obj_t tuple_operations_step_slice(mp_obj_t t_obj) {
    mp_obj_t t = t_obj;

    return mp_obj_subscr(t, mp_obj_new_slice(mp_const_none, mp_const_none, mp_obj_new_int(2)), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_step_slice_obj, tuple_operations_step_slice);
static mp_obj_t tuple_operations_from_range(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    return mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_tuple), mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_range), mp_obj_new_int(n)));
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_from_range_obj, tuple_operations_from_range);
static mp_obj_t tuple_operations_rtuple_point(void) {
    rtuple_int_int_t point = {100, 200};
    mp_obj_t _ret_items[] = {mp_obj_new_int(point.f0), mp_obj_new_int(point.f1)};
    return mp_obj_new_tuple(2, _ret_items);
}
MP_DEFINE_CONST_FUN_OBJ_0(tuple_operations_rtuple_point_obj, tuple_operations_rtuple_point);
static mp_obj_t tuple_operations_rtuple_add_coords(size_t n_args, const mp_obj_t *args) {
    mp_int_t x1 = mp_obj_get_int(args[0]);
    mp_int_t y1 = mp_obj_get_int(args[1]);
    mp_int_t x2 = mp_obj_get_int(args[2]);
    mp_int_t y2 = mp_obj_get_int(args[3]);

    rtuple_int_int_t p1 = {x1, y1};
    rtuple_int_int_t p2 = {x2, y2};
    rtuple_int_int_t result = {(p1.f0 + p2.f0), (p1.f1 + p2.f1)};
    mp_obj_t _ret_items[] = {mp_obj_new_int(result.f0), mp_obj_new_int(result.f1)};
    return mp_obj_new_tuple(2, _ret_items);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(tuple_operations_rtuple_add_coords_obj, 4, 4, tuple_operations_rtuple_add_coords);
static mp_obj_t tuple_operations_rtuple_sum_fields(void) {
    rtuple_int_int_t point = {15, 25};
    return mp_obj_new_int((point.f0 + point.f1));
}
MP_DEFINE_CONST_FUN_OBJ_0(tuple_operations_rtuple_sum_fields_obj, tuple_operations_rtuple_sum_fields);
static mp_obj_t tuple_operations_rtuple_distance_squared(size_t n_args, const mp_obj_t *args) {
    mp_int_t x1 = mp_obj_get_int(args[0]);
    mp_int_t y1 = mp_obj_get_int(args[1]);
    mp_int_t x2 = mp_obj_get_int(args[2]);
    mp_int_t y2 = mp_obj_get_int(args[3]);

    rtuple_int_int_t p1 = {x1, y1};
    rtuple_int_int_t p2 = {x2, y2};
    mp_int_t dx = (p2.f0 - p1.f0);
    mp_int_t dy = (p2.f1 - p1.f1);
    return mp_obj_new_int(((dx * dx) + (dy * dy)));
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(tuple_operations_rtuple_distance_squared_obj, 4, 4, tuple_operations_rtuple_distance_squared);
static mp_obj_t tuple_operations_rtuple_rgb(void) {
    rtuple_int_int_int_t color = {255, 128, 64};
    mp_obj_t _ret_items[] = {mp_obj_new_int(color.f0), mp_obj_new_int(color.f1), mp_obj_new_int(color.f2)};
    return mp_obj_new_tuple(3, _ret_items);
}
MP_DEFINE_CONST_FUN_OBJ_0(tuple_operations_rtuple_rgb_obj, tuple_operations_rtuple_rgb);
static mp_obj_t tuple_operations_rtuple_sum_rgb(mp_obj_t r_obj, mp_obj_t g_obj, mp_obj_t b_obj) {
    mp_int_t r = mp_obj_get_int(r_obj);
    mp_int_t g = mp_obj_get_int(g_obj);
    mp_int_t b = mp_obj_get_int(b_obj);

    rtuple_int_int_int_t color = {r, g, b};
    return mp_obj_new_int(((color.f0 + color.f1) + color.f2));
}
MP_DEFINE_CONST_FUN_OBJ_3(tuple_operations_rtuple_sum_rgb_obj, tuple_operations_rtuple_sum_rgb);
static mp_obj_t tuple_operations_rtuple_blend_colors(size_t n_args, const mp_obj_t *args) {
    mp_int_t r1 = mp_obj_get_int(args[0]);
    mp_int_t g1 = mp_obj_get_int(args[1]);
    mp_int_t b1 = mp_obj_get_int(args[2]);
    mp_int_t r2 = mp_obj_get_int(args[3]);
    mp_int_t g2 = mp_obj_get_int(args[4]);
    mp_int_t b2 = mp_obj_get_int(args[5]);

    rtuple_int_int_int_t c1 = {r1, g1, b1};
    rtuple_int_int_int_t c2 = {r2, g2, b2};
    rtuple_int_int_int_t result = {((c1.f0 + c2.f0) / 2), ((c1.f1 + c2.f1) / 2), ((c1.f2 + c2.f2) / 2)};
    mp_obj_t _ret_items[] = {mp_obj_new_int(result.f0), mp_obj_new_int(result.f1), mp_obj_new_int(result.f2)};
    return mp_obj_new_tuple(3, _ret_items);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(tuple_operations_rtuple_blend_colors_obj, 6, 6, tuple_operations_rtuple_blend_colors);
static mp_obj_t tuple_operations_rtuple_benchmark_internal(mp_obj_t n_obj) {
    mp_int_t n = mp_obj_get_int(n_obj);

    mp_int_t total = 0;
    mp_int_t i = 0;
    while ((i < n)) {
        rtuple_int_int_t point = {i, (i * 2)};
        total += (point.f0 + point.f1);
        i += 1;
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_1(tuple_operations_rtuple_benchmark_internal_obj, tuple_operations_rtuple_benchmark_internal);
static mp_obj_t tuple_operations_sum_points_list(mp_obj_t points_obj, mp_obj_t count_obj) {
    mp_obj_t points = points_obj;
    mp_int_t count = mp_obj_get_int(count_obj);

    mp_int_t total = 0;
    mp_int_t i = 0;
    while ((i < count)) {
        mp_obj_tuple_t *_tmp1 = MP_OBJ_TO_PTR(mp_list_get_int(points, i));
        rtuple_int_int_int_t p = { mp_obj_get_int(_tmp1->items[0]), mp_obj_get_int(_tmp1->items[1]), mp_obj_get_int(_tmp1->items[2]) };
        total = (((total + p.f0) + p.f1) + p.f2);
        i = (i + 1);
    }
    return mp_obj_new_int(total);
}
MP_DEFINE_CONST_FUN_OBJ_2(tuple_operations_sum_points_list_obj, tuple_operations_sum_points_list);
static const mp_rom_map_elem_t tuple_operations_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_tuple_operations) },
    { MP_ROM_QSTR(MP_QSTR_make_point), MP_ROM_PTR(&tuple_operations_make_point_obj) },
    { MP_ROM_QSTR(MP_QSTR_make_triple), MP_ROM_PTR(&tuple_operations_make_triple_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_first), MP_ROM_PTR(&tuple_operations_get_first_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_last), MP_ROM_PTR(&tuple_operations_get_last_obj) },
    { MP_ROM_QSTR(MP_QSTR_tuple_len), MP_ROM_PTR(&tuple_operations_tuple_len_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_tuple), MP_ROM_PTR(&tuple_operations_sum_tuple_obj) },
    { MP_ROM_QSTR(MP_QSTR_tuple_contains), MP_ROM_PTR(&tuple_operations_tuple_contains_obj) },
    { MP_ROM_QSTR(MP_QSTR_tuple_not_contains), MP_ROM_PTR(&tuple_operations_tuple_not_contains_obj) },
    { MP_ROM_QSTR(MP_QSTR_unpack_pair), MP_ROM_PTR(&tuple_operations_unpack_pair_obj) },
    { MP_ROM_QSTR(MP_QSTR_unpack_triple), MP_ROM_PTR(&tuple_operations_unpack_triple_obj) },
    { MP_ROM_QSTR(MP_QSTR_concat_tuples), MP_ROM_PTR(&tuple_operations_concat_tuples_obj) },
    { MP_ROM_QSTR(MP_QSTR_repeat_tuple), MP_ROM_PTR(&tuple_operations_repeat_tuple_obj) },
    { MP_ROM_QSTR(MP_QSTR_empty_tuple), MP_ROM_PTR(&tuple_operations_empty_tuple_obj) },
    { MP_ROM_QSTR(MP_QSTR_single_element), MP_ROM_PTR(&tuple_operations_single_element_obj) },
    { MP_ROM_QSTR(MP_QSTR_nested_iteration), MP_ROM_PTR(&tuple_operations_nested_iteration_obj) },
    { MP_ROM_QSTR(MP_QSTR_slice_tuple), MP_ROM_PTR(&tuple_operations_slice_tuple_obj) },
    { MP_ROM_QSTR(MP_QSTR_reverse_tuple), MP_ROM_PTR(&tuple_operations_reverse_tuple_obj) },
    { MP_ROM_QSTR(MP_QSTR_step_slice), MP_ROM_PTR(&tuple_operations_step_slice_obj) },
    { MP_ROM_QSTR(MP_QSTR_from_range), MP_ROM_PTR(&tuple_operations_from_range_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_point), MP_ROM_PTR(&tuple_operations_rtuple_point_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_add_coords), MP_ROM_PTR(&tuple_operations_rtuple_add_coords_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_sum_fields), MP_ROM_PTR(&tuple_operations_rtuple_sum_fields_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_distance_squared), MP_ROM_PTR(&tuple_operations_rtuple_distance_squared_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_rgb), MP_ROM_PTR(&tuple_operations_rtuple_rgb_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_sum_rgb), MP_ROM_PTR(&tuple_operations_rtuple_sum_rgb_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_blend_colors), MP_ROM_PTR(&tuple_operations_rtuple_blend_colors_obj) },
    { MP_ROM_QSTR(MP_QSTR_rtuple_benchmark_internal), MP_ROM_PTR(&tuple_operations_rtuple_benchmark_internal_obj) },
    { MP_ROM_QSTR(MP_QSTR_sum_points_list), MP_ROM_PTR(&tuple_operations_sum_points_list_obj) },
};
MP_DEFINE_CONST_DICT(tuple_operations_module_globals, tuple_operations_module_globals_table);

const mp_obj_module_t tuple_operations_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&tuple_operations_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_tuple_operations, tuple_operations_user_cmodule);