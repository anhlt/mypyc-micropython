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

static mp_obj_t string_operations_concat_strings(mp_obj_t a_obj, mp_obj_t b_obj) {
    mp_obj_t a = a_obj;
    mp_obj_t b = b_obj;

    return mp_binary_op(MP_BINARY_OP_ADD, a, b);
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_concat_strings_obj, string_operations_concat_strings);
static mp_obj_t string_operations_repeat_string(mp_obj_t s_obj, mp_obj_t n_obj) {
    mp_obj_t s = s_obj;
    mp_int_t n = mp_obj_get_int(n_obj);

    return mp_binary_op(MP_BINARY_OP_MULTIPLY, s, mp_obj_new_int(n));
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_repeat_string_obj, string_operations_repeat_string);
static mp_obj_t string_operations_to_upper(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_upper));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_to_upper_obj, string_operations_to_upper);
static mp_obj_t string_operations_to_lower(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_lower));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_to_lower_obj, string_operations_to_lower);
static mp_obj_t string_operations_find_substring(mp_obj_t s_obj, mp_obj_t sub_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t sub = sub_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_find), sub);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_find_substring_obj, string_operations_find_substring);
static mp_obj_t string_operations_rfind_substring(mp_obj_t s_obj, mp_obj_t sub_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t sub = sub_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_rfind), sub);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_rfind_substring_obj, string_operations_rfind_substring);
static mp_obj_t string_operations_count_substring(mp_obj_t s_obj, mp_obj_t sub_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t sub = sub_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_count), sub);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_count_substring_obj, string_operations_count_substring);
static mp_obj_t string_operations_split_string(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_split));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_split_string_obj, string_operations_split_string);
static mp_obj_t string_operations_split_on_sep(mp_obj_t s_obj, mp_obj_t sep_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t sep = sep_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_split), sep);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_split_on_sep_obj, string_operations_split_on_sep);
static mp_obj_t string_operations_join_strings(mp_obj_t sep_obj, mp_obj_t items_obj) {
    mp_obj_t sep = sep_obj;
    mp_obj_t items = items_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(sep, MP_QSTR_join), items);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_join_strings_obj, string_operations_join_strings);
static mp_obj_t string_operations_strip_string(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_strip));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_strip_string_obj, string_operations_strip_string);
static mp_obj_t string_operations_lstrip_string(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_lstrip));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_lstrip_string_obj, string_operations_lstrip_string);
static mp_obj_t string_operations_rstrip_string(mp_obj_t s_obj) {
    mp_obj_t s = s_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(s, MP_QSTR_rstrip));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_rstrip_string_obj, string_operations_rstrip_string);
static mp_obj_t string_operations_strip_chars(mp_obj_t s_obj, mp_obj_t chars_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t chars = chars_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_strip), chars);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_strip_chars_obj, string_operations_strip_chars);
static mp_obj_t string_operations_replace_string(mp_obj_t s_obj, mp_obj_t old_obj, mp_obj_t new_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t old = old_obj;
    mp_obj_t new = new_obj;

    mp_obj_t _tmp1 = mp_call_function_n_kw(mp_load_attr(s, MP_QSTR_replace), 2, 0, (mp_obj_t[]){old, new});
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_3(string_operations_replace_string_obj, string_operations_replace_string);
static mp_obj_t string_operations_starts_with(mp_obj_t s_obj, mp_obj_t prefix_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t prefix = prefix_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_startswith), prefix);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_starts_with_obj, string_operations_starts_with);
static mp_obj_t string_operations_ends_with(mp_obj_t s_obj, mp_obj_t suffix_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t suffix = suffix_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_endswith), suffix);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_ends_with_obj, string_operations_ends_with);
static mp_obj_t string_operations_center_string(mp_obj_t s_obj, mp_obj_t width_obj) {
    mp_obj_t s = s_obj;
    mp_int_t width = mp_obj_get_int(width_obj);

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_center), mp_obj_new_int(width));
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_center_string_obj, string_operations_center_string);
static mp_obj_t string_operations_partition_string(mp_obj_t s_obj, mp_obj_t sep_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t sep = sep_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_partition), sep);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_partition_string_obj, string_operations_partition_string);
static mp_obj_t string_operations_rpartition_string(mp_obj_t s_obj, mp_obj_t sep_obj) {
    mp_obj_t s = s_obj;
    mp_obj_t sep = sep_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(s, MP_QSTR_rpartition), sep);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_2(string_operations_rpartition_string_obj, string_operations_rpartition_string);
static mp_obj_t string_operations_process_csv_line(mp_obj_t line_obj) {
    mp_obj_t line = line_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(line, MP_QSTR_split), mp_obj_new_str(",", 1));
    mp_obj_t parts = _tmp1;
    mp_obj_t result = mp_obj_new_list(0, NULL);
    mp_obj_t part;
    mp_obj_iter_buf_t _tmp5;
    mp_obj_t _tmp4 = mp_getiter(parts, &_tmp5);
    while ((part = mp_iternext(_tmp4)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_t _tmp2 = mp_call_function_0(mp_load_attr(part, MP_QSTR_strip));
        mp_obj_t _tmp3 = mp_obj_list_append(result, _tmp2);
        (void)_tmp3;
    }
    return result;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_process_csv_line_obj, string_operations_process_csv_line);
static mp_obj_t string_operations_normalize_text(mp_obj_t text_obj) {
    mp_obj_t text = text_obj;

    mp_obj_t _tmp1 = mp_call_function_0(mp_load_attr(text, MP_QSTR_lower));
    mp_obj_t s = _tmp1;
    mp_obj_t _tmp2 = mp_call_function_0(mp_load_attr(s, MP_QSTR_strip));
    s = _tmp2;
    while ((mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, mp_obj_new_str("  ", 2), s)))) {
        mp_obj_t _tmp3 = mp_call_function_n_kw(mp_load_attr(s, MP_QSTR_replace), 2, 0, (mp_obj_t[]){mp_obj_new_str("  ", 2), mp_obj_new_str(" ", 1)});
        s = _tmp3;
    }
    return s;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_normalize_text_obj, string_operations_normalize_text);
static mp_obj_t string_operations_build_path(mp_obj_t parts_obj) {
    mp_obj_t parts = parts_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(mp_obj_new_str("/", 1), MP_QSTR_join), parts);
    return _tmp1;
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_build_path_obj, string_operations_build_path);
static mp_obj_t string_operations_extract_extension(mp_obj_t filename_obj) {
    mp_obj_t filename = filename_obj;

    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(filename, MP_QSTR_rfind), mp_obj_new_str(".", 1));
    mp_int_t idx = mp_obj_get_int(_tmp1);
    if ((idx == (-1))) {
        return mp_obj_new_str("", 0);
    }
    return mp_obj_subscr(filename, mp_obj_new_slice(mp_obj_new_int((idx + 1)), mp_const_none, mp_const_none), MP_OBJ_SENTINEL);
}
MP_DEFINE_CONST_FUN_OBJ_1(string_operations_extract_extension_obj, string_operations_extract_extension);
static const mp_rom_map_elem_t string_operations_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_string_operations) },
    { MP_ROM_QSTR(MP_QSTR_concat_strings), MP_ROM_PTR(&string_operations_concat_strings_obj) },
    { MP_ROM_QSTR(MP_QSTR_repeat_string), MP_ROM_PTR(&string_operations_repeat_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_to_upper), MP_ROM_PTR(&string_operations_to_upper_obj) },
    { MP_ROM_QSTR(MP_QSTR_to_lower), MP_ROM_PTR(&string_operations_to_lower_obj) },
    { MP_ROM_QSTR(MP_QSTR_find_substring), MP_ROM_PTR(&string_operations_find_substring_obj) },
    { MP_ROM_QSTR(MP_QSTR_rfind_substring), MP_ROM_PTR(&string_operations_rfind_substring_obj) },
    { MP_ROM_QSTR(MP_QSTR_count_substring), MP_ROM_PTR(&string_operations_count_substring_obj) },
    { MP_ROM_QSTR(MP_QSTR_split_string), MP_ROM_PTR(&string_operations_split_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_split_on_sep), MP_ROM_PTR(&string_operations_split_on_sep_obj) },
    { MP_ROM_QSTR(MP_QSTR_join_strings), MP_ROM_PTR(&string_operations_join_strings_obj) },
    { MP_ROM_QSTR(MP_QSTR_strip_string), MP_ROM_PTR(&string_operations_strip_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_lstrip_string), MP_ROM_PTR(&string_operations_lstrip_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_rstrip_string), MP_ROM_PTR(&string_operations_rstrip_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_strip_chars), MP_ROM_PTR(&string_operations_strip_chars_obj) },
    { MP_ROM_QSTR(MP_QSTR_replace_string), MP_ROM_PTR(&string_operations_replace_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_starts_with), MP_ROM_PTR(&string_operations_starts_with_obj) },
    { MP_ROM_QSTR(MP_QSTR_ends_with), MP_ROM_PTR(&string_operations_ends_with_obj) },
    { MP_ROM_QSTR(MP_QSTR_center_string), MP_ROM_PTR(&string_operations_center_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_partition_string), MP_ROM_PTR(&string_operations_partition_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_rpartition_string), MP_ROM_PTR(&string_operations_rpartition_string_obj) },
    { MP_ROM_QSTR(MP_QSTR_process_csv_line), MP_ROM_PTR(&string_operations_process_csv_line_obj) },
    { MP_ROM_QSTR(MP_QSTR_normalize_text), MP_ROM_PTR(&string_operations_normalize_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_build_path), MP_ROM_PTR(&string_operations_build_path_obj) },
    { MP_ROM_QSTR(MP_QSTR_extract_extension), MP_ROM_PTR(&string_operations_extract_extension_obj) },
};
MP_DEFINE_CONST_DICT(string_operations_module_globals, string_operations_module_globals_table);

const mp_obj_module_t string_operations_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&string_operations_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_string_operations, string_operations_user_cmodule);