/*
 * MicroPython bindings for lvgl
 * Auto-generated from lvgl.pyi - do not edit
 * 
 * This file demonstrates what mpy-compile-c would generate
 * from the lvgl.pyi stub file.
 */

#include "py/runtime.h"
#include "py/obj.h"
#include "lvgl.h"

/* ========================================================================
 * Helper functions
 * ======================================================================== */

static inline void *mp_to_ptr(mp_obj_t obj) {
    if (obj == mp_const_none) return NULL;
    return MP_OBJ_TO_PTR(obj);
}

static inline mp_obj_t ptr_to_mp(void *ptr) {
    if (ptr == NULL) return mp_const_none;
    return MP_OBJ_FROM_PTR(ptr);
}

/* ========================================================================
 * Wrapper: lv_screen_active
 * Source:  def lv_screen_active() -> c_ptr[LvObj]
 * ======================================================================== */
static mp_obj_t lv_screen_active_wrapper(void) {
    lv_obj_t *result = lv_scr_act();
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_0(lv_screen_active_obj, lv_screen_active_wrapper);

/* ========================================================================
 * Wrapper: lv_screen_load
 * Source:  def lv_screen_load(scr: c_ptr[LvObj]) -> None
 * ======================================================================== */
static mp_obj_t lv_screen_load_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_scr = mp_to_ptr(arg0);
    lv_scr_load(c_scr);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_screen_load_obj, lv_screen_load_wrapper);

/* ========================================================================
 * Wrapper: lv_obj_create
 * Source:  def lv_obj_create(parent: c_ptr[LvObj] | None) -> c_ptr[LvObj]
 * ======================================================================== */
static mp_obj_t lv_obj_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = (arg0 == mp_const_none) ? NULL : mp_to_ptr(arg0);
    lv_obj_t *result = lv_obj_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_obj_create_obj, lv_obj_create_wrapper);

/* ========================================================================
 * Wrapper: lv_obj_delete
 * Source:  def lv_obj_delete(obj: c_ptr[LvObj]) -> None
 * ======================================================================== */
static mp_obj_t lv_obj_delete_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    lv_obj_delete(c_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_obj_delete_obj, lv_obj_delete_wrapper);

/* ========================================================================
 * Wrapper: lv_obj_set_size
 * Source:  def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None
 * ======================================================================== */
static mp_obj_t lv_obj_set_size_wrapper(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    int32_t c_w = mp_obj_get_int(arg1);
    int32_t c_h = mp_obj_get_int(arg2);
    lv_obj_set_size(c_obj, c_w, c_h);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(lv_obj_set_size_obj, lv_obj_set_size_wrapper);

/* ========================================================================
 * Wrapper: lv_obj_set_pos
 * Source:  def lv_obj_set_pos(obj: c_ptr[LvObj], x: c_int, y: c_int) -> None
 * ======================================================================== */
static mp_obj_t lv_obj_set_pos_wrapper(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    int32_t c_x = mp_obj_get_int(arg1);
    int32_t c_y = mp_obj_get_int(arg2);
    lv_obj_set_pos(c_obj, c_x, c_y);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(lv_obj_set_pos_obj, lv_obj_set_pos_wrapper);

/* ========================================================================
 * Wrapper: lv_obj_center
 * Source:  def lv_obj_center(obj: c_ptr[LvObj]) -> None
 * ======================================================================== */
static mp_obj_t lv_obj_center_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    lv_obj_center(c_obj);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_obj_center_obj, lv_obj_center_wrapper);

/* ========================================================================
 * Wrapper: lv_obj_add_flag
 * Source:  def lv_obj_add_flag(obj: c_ptr[LvObj], flag: c_uint) -> None
 * ======================================================================== */
static mp_obj_t lv_obj_add_flag_wrapper(mp_obj_t arg0, mp_obj_t arg1) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    uint32_t c_flag = (uint32_t)mp_obj_get_int(arg1);
    lv_obj_add_flag(c_obj, c_flag);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(lv_obj_add_flag_obj, lv_obj_add_flag_wrapper);

/* ========================================================================
 * Wrapper: lv_obj_remove_flag
 * Source:  def lv_obj_remove_flag(obj: c_ptr[LvObj], flag: c_uint) -> None
 * ======================================================================== */
static mp_obj_t lv_obj_remove_flag_wrapper(mp_obj_t arg0, mp_obj_t arg1) {
    lv_obj_t *c_obj = mp_to_ptr(arg0);
    uint32_t c_flag = (uint32_t)mp_obj_get_int(arg1);
    lv_obj_remove_flag(c_obj, c_flag);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(lv_obj_remove_flag_obj, lv_obj_remove_flag_wrapper);

/* ========================================================================
 * Wrapper: lv_btn_create
 * Source:  def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]
 * ======================================================================== */
static mp_obj_t lv_btn_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = mp_to_ptr(arg0);
    lv_obj_t *result = lv_btn_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_btn_create_obj, lv_btn_create_wrapper);

/* ========================================================================
 * Wrapper: lv_label_create
 * Source:  def lv_label_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]
 * ======================================================================== */
static mp_obj_t lv_label_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = mp_to_ptr(arg0);
    lv_obj_t *result = lv_label_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_label_create_obj, lv_label_create_wrapper);

/* ========================================================================
 * Wrapper: lv_label_set_text
 * Source:  def lv_label_set_text(label: c_ptr[LvObj], text: str) -> None
 * ======================================================================== */
static mp_obj_t lv_label_set_text_wrapper(mp_obj_t arg0, mp_obj_t arg1) {
    lv_obj_t *c_label = mp_to_ptr(arg0);
    const char *c_text = mp_obj_str_get_str(arg1);
    lv_label_set_text(c_label, c_text);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_2(lv_label_set_text_obj, lv_label_set_text_wrapper);

/* ========================================================================
 * Wrapper: lv_slider_create
 * Source:  def lv_slider_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]
 * ======================================================================== */
static mp_obj_t lv_slider_create_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_parent = mp_to_ptr(arg0);
    lv_obj_t *result = lv_slider_create(c_parent);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_slider_create_obj, lv_slider_create_wrapper);

/* ========================================================================
 * Wrapper: lv_slider_set_value
 * Source:  def lv_slider_set_value(slider: c_ptr[LvObj], value: c_int, anim: c_int) -> None
 * ======================================================================== */
static mp_obj_t lv_slider_set_value_wrapper(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2) {
    lv_obj_t *c_slider = mp_to_ptr(arg0);
    int32_t c_value = mp_obj_get_int(arg1);
    int32_t c_anim = mp_obj_get_int(arg2);
    lv_slider_set_value(c_slider, c_value, c_anim);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(lv_slider_set_value_obj, lv_slider_set_value_wrapper);

/* ========================================================================
 * Wrapper: lv_slider_get_value
 * Source:  def lv_slider_get_value(slider: c_ptr[LvObj]) -> c_int
 * ======================================================================== */
static mp_obj_t lv_slider_get_value_wrapper(mp_obj_t arg0) {
    lv_obj_t *c_slider = mp_to_ptr(arg0);
    int32_t result = lv_slider_get_value(c_slider);
    return mp_obj_new_int(result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_slider_get_value_obj, lv_slider_get_value_wrapper);

/* ========================================================================
 * Wrapper: lv_slider_set_range
 * Source:  def lv_slider_set_range(slider: c_ptr[LvObj], min_val: c_int, max_val: c_int) -> None
 * ======================================================================== */
static mp_obj_t lv_slider_set_range_wrapper(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2) {
    lv_obj_t *c_slider = mp_to_ptr(arg0);
    int32_t c_min = mp_obj_get_int(arg1);
    int32_t c_max = mp_obj_get_int(arg2);
    lv_slider_set_range(c_slider, c_min, c_max);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(lv_slider_set_range_obj, lv_slider_set_range_wrapper);

/* ========================================================================
 * Event callback support
 * ======================================================================== */

#define MAX_EVENT_CALLBACKS 32
static mp_obj_t event_callbacks[MAX_EVENT_CALLBACKS];
static int event_callback_count = 0;

static void event_callback_trampoline(lv_event_t *e) {
    int idx = (int)(intptr_t)lv_event_get_user_data(e);
    if (idx >= 0 && idx < event_callback_count) {
        mp_obj_t cb = event_callbacks[idx];
        mp_obj_t event_obj = ptr_to_mp((void *)e);
        mp_call_function_1(cb, event_obj);
    }
}

/* ========================================================================
 * Wrapper: lv_obj_add_event_cb
 * Source:  def lv_obj_add_event_cb(obj, event_cb, filter, user_data) -> None
 * ======================================================================== */
static mp_obj_t lv_obj_add_event_cb_wrapper(size_t n_args, const mp_obj_t *args) {
    lv_obj_t *c_obj = mp_to_ptr(args[0]);
    mp_obj_t callback = args[1];
    lv_event_code_t c_filter = mp_obj_get_int(args[2]);
    
    if (event_callback_count >= MAX_EVENT_CALLBACKS) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("too many event callbacks"));
    }
    
    int idx = event_callback_count++;
    event_callbacks[idx] = callback;
    
    lv_obj_add_event_cb(c_obj, event_callback_trampoline, c_filter, (void *)(intptr_t)idx);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lv_obj_add_event_cb_obj, 3, 4, lv_obj_add_event_cb_wrapper);

/* ========================================================================
 * Wrapper: lv_event_get_code
 * Source:  def lv_event_get_code(e: c_ptr[LvEvent]) -> c_int
 * ======================================================================== */
static mp_obj_t lv_event_get_code_wrapper(mp_obj_t arg0) {
    lv_event_t *c_e = mp_to_ptr(arg0);
    lv_event_code_t result = lv_event_get_code(c_e);
    return mp_obj_new_int(result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_event_get_code_obj, lv_event_get_code_wrapper);

/* ========================================================================
 * Wrapper: lv_event_get_target
 * Source:  def lv_event_get_target(e: c_ptr[LvEvent]) -> c_ptr[LvObj]
 * ======================================================================== */
static mp_obj_t lv_event_get_target_wrapper(mp_obj_t arg0) {
    lv_event_t *c_e = mp_to_ptr(arg0);
    lv_obj_t *result = lv_event_get_target(c_e);
    return ptr_to_mp((void *)result);
}
static MP_DEFINE_CONST_FUN_OBJ_1(lv_event_get_target_obj, lv_event_get_target_wrapper);

/* ========================================================================
 * Module definition
 * ======================================================================== */

static const mp_rom_map_elem_t lvgl_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lvgl) },
    
    /* Screen functions */
    { MP_ROM_QSTR(MP_QSTR_lv_screen_active), MP_ROM_PTR(&lv_screen_active_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_screen_load), MP_ROM_PTR(&lv_screen_load_obj) },
    
    /* Object functions */
    { MP_ROM_QSTR(MP_QSTR_lv_obj_create), MP_ROM_PTR(&lv_obj_create_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_delete), MP_ROM_PTR(&lv_obj_delete_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_set_size), MP_ROM_PTR(&lv_obj_set_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_set_pos), MP_ROM_PTR(&lv_obj_set_pos_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_center), MP_ROM_PTR(&lv_obj_center_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_add_flag), MP_ROM_PTR(&lv_obj_add_flag_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_remove_flag), MP_ROM_PTR(&lv_obj_remove_flag_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_obj_add_event_cb), MP_ROM_PTR(&lv_obj_add_event_cb_obj) },
    
    /* Button widget */
    { MP_ROM_QSTR(MP_QSTR_lv_btn_create), MP_ROM_PTR(&lv_btn_create_obj) },
    
    /* Label widget */
    { MP_ROM_QSTR(MP_QSTR_lv_label_create), MP_ROM_PTR(&lv_label_create_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_label_set_text), MP_ROM_PTR(&lv_label_set_text_obj) },
    
    /* Slider widget */
    { MP_ROM_QSTR(MP_QSTR_lv_slider_create), MP_ROM_PTR(&lv_slider_create_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_slider_set_value), MP_ROM_PTR(&lv_slider_set_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_slider_get_value), MP_ROM_PTR(&lv_slider_get_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_slider_set_range), MP_ROM_PTR(&lv_slider_set_range_obj) },
    
    /* Event functions */
    { MP_ROM_QSTR(MP_QSTR_lv_event_get_code), MP_ROM_PTR(&lv_event_get_code_obj) },
    { MP_ROM_QSTR(MP_QSTR_lv_event_get_target), MP_ROM_PTR(&lv_event_get_target_obj) },
    
    /* Constants - Object flags */
    { MP_ROM_QSTR(MP_QSTR_LV_OBJ_FLAG_HIDDEN), MP_ROM_INT(LV_OBJ_FLAG_HIDDEN) },
    { MP_ROM_QSTR(MP_QSTR_LV_OBJ_FLAG_CLICKABLE), MP_ROM_INT(LV_OBJ_FLAG_CLICKABLE) },
    { MP_ROM_QSTR(MP_QSTR_LV_OBJ_FLAG_SCROLLABLE), MP_ROM_INT(LV_OBJ_FLAG_SCROLLABLE) },
    
    /* Constants - Event codes */
    { MP_ROM_QSTR(MP_QSTR_LV_EVENT_CLICKED), MP_ROM_INT(LV_EVENT_CLICKED) },
    { MP_ROM_QSTR(MP_QSTR_LV_EVENT_VALUE_CHANGED), MP_ROM_INT(LV_EVENT_VALUE_CHANGED) },
};

static MP_DEFINE_CONST_DICT(lvgl_module_globals, lvgl_module_globals_table);

const mp_obj_module_t lvgl_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_lvgl, lvgl_user_cmodule);
