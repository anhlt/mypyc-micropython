#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _lvgl_mvu_app_App_obj_t lvgl_mvu_app_App_obj_t;
typedef struct _lvgl_mvu_app_App_vtable_t lvgl_mvu_app_App_vtable_t;
extern const mp_obj_type_t lvgl_mvu_app_App_type;
static mp_obj_t lvgl_mvu_app_App_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static void lvgl_mvu_app_App_set_timer_factory_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t factory);
static void lvgl_mvu_app_App_dispatch_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t msg);
static bool lvgl_mvu_app_App_tick_native(lvgl_mvu_app_App_obj_t *self);
static void lvgl_mvu_app_App_dispose_native(lvgl_mvu_app_App_obj_t *self);
static bool lvgl_mvu_app_App_is_disposed_native(lvgl_mvu_app_App_obj_t *self);
static mp_int_t lvgl_mvu_app_App_queue_length_native(lvgl_mvu_app_App_obj_t *self);
static void lvgl_mvu_app_App__execute_cmd_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t cmd);
static void lvgl_mvu_app_App__setup_subscriptions_native(lvgl_mvu_app_App_obj_t *self);
static void lvgl_mvu_app_App__teardown_subscriptions_native(lvgl_mvu_app_App_obj_t *self);
static mp_obj_t lvgl_mvu_app_App__activate_sub_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t sub_def);
static mp_obj_t lvgl_mvu_app_App__activate_timer_sub_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t sub_def);
static bool lvgl_mvu_app_App__keys_match_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t new_keys);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App___init___obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_app_App___init___obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App_set_timer_factory_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App_set_timer_factory_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App_dispatch_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App_dispatch_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App_tick_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App_tick_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App_dispose_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App_dispose_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App_is_disposed_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App_is_disposed_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App_queue_length_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App_queue_length_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App__execute_cmd_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App__execute_cmd_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App__setup_subscriptions_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App__setup_subscriptions_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App__teardown_subscriptions_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App__teardown_subscriptions_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App__activate_sub_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App__activate_sub_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App__activate_timer_sub_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App__activate_timer_sub_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_app_App__keys_match_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_app_App__keys_match_obj;
#endif

typedef struct _lvgl_mvu_attrs_AttrDef_obj_t lvgl_mvu_attrs_AttrDef_obj_t;
extern const mp_obj_type_t lvgl_mvu_attrs_AttrDef_type;
static mp_obj_t lvgl_mvu_attrs_AttrDef_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
typedef struct _lvgl_mvu_attrs_AttrRegistry_obj_t lvgl_mvu_attrs_AttrRegistry_obj_t;
typedef struct _lvgl_mvu_attrs_AttrRegistry_vtable_t lvgl_mvu_attrs_AttrRegistry_vtable_t;
extern const mp_obj_type_t lvgl_mvu_attrs_AttrRegistry_type;
static mp_obj_t lvgl_mvu_attrs_AttrRegistry_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static mp_obj_t lvgl_mvu_attrs_AttrRegistry_add_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_obj_t attr_def);
static mp_obj_t lvgl_mvu_attrs_AttrRegistry_get_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_int_t key);
static mp_obj_t lvgl_mvu_attrs_AttrRegistry_get_or_raise_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_int_t key);
static mp_obj_t lvgl_mvu_attrs_AttrRegistry_all_attrs_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_attrs_AttrRegistry___init___obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_attrs_AttrRegistry___init___obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_attrs_AttrRegistry_add_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_attrs_AttrRegistry_add_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_attrs_AttrRegistry_get_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_attrs_AttrRegistry_get_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_attrs_AttrRegistry_get_or_raise_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_attrs_AttrRegistry_get_or_raise_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_attrs_AttrRegistry_all_attrs_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_attrs_AttrRegistry_all_attrs_obj;
#endif

static mp_obj_t lvgl_mvu_builders__attr_sort_key(mp_obj_t a_obj);
typedef struct _lvgl_mvu_builders_WidgetBuilder_obj_t lvgl_mvu_builders_WidgetBuilder_obj_t;
typedef struct _lvgl_mvu_builders_WidgetBuilder_vtable_t lvgl_mvu_builders_WidgetBuilder_vtable_t;
extern const mp_obj_type_t lvgl_mvu_builders_WidgetBuilder_type;
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_user_key_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t key);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_set_attr_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t attr_key, mp_obj_t value);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_on_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t event, mp_obj_t msg);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_on_value_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t event, mp_obj_t msg_fn);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_add_child_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t child);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_build_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_width_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_height_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t h);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_size_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w, mp_int_t h);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pos_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t x, mp_int_t y);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_align_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t align_value, mp_int_t x_ofs, mp_int_t y_ofs);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_bg_color_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_bg_opa_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t opa);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_border_color_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_border_width_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_radius_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t r);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_padding_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t top, mp_int_t right, mp_int_t bottom, mp_int_t left);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pad_row_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t gap);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pad_column_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t gap);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t value);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_color_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_align_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t align_value);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_shadow_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w, mp_int_t color, mp_int_t ofs_x, mp_int_t ofs_y);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_flex_flow_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t flow);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_flex_grow_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t grow);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_value_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t v);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_set_range_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t min_val, mp_int_t max_val);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_checked_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, bool state);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder___init___obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder___init___obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_user_key_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_user_key_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_set_attr_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_set_attr_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_on_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_on_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_on_value_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_on_value_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_add_child_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_add_child_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_build_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_build_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_width_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_width_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_height_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_height_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_size_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_size_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_pos_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_pos_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_align_obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_builders_WidgetBuilder_align_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_bg_color_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_bg_color_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_bg_opa_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_bg_opa_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_border_color_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_border_color_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_border_width_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_border_width_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_radius_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_radius_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_padding_obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_builders_WidgetBuilder_padding_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_pad_row_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_pad_row_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_pad_column_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_pad_column_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_text_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_text_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_text_color_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_text_color_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_text_align_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_text_align_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_shadow_obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_builders_WidgetBuilder_shadow_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_flex_flow_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_flex_flow_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_flex_grow_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_flex_grow_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_value_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_value_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_set_range_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_set_range_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_builders_WidgetBuilder_checked_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_builders_WidgetBuilder_checked_obj;
#endif

static mp_obj_t lvgl_mvu_diff_diff_scalars(mp_obj_t prev_obj, mp_obj_t next_attrs_obj);
static mp_obj_t lvgl_mvu_diff_can_reuse(mp_obj_t prev_obj, mp_obj_t next_w_obj);
static mp_obj_t lvgl_mvu_diff_diff_children(mp_obj_t prev_obj, mp_obj_t next_children_obj);
static mp_obj_t lvgl_mvu_diff__events_changed(mp_obj_t prev_obj, mp_obj_t next_evts_obj);
static mp_obj_t lvgl_mvu_diff_diff_widgets(mp_obj_t prev_obj, mp_obj_t next_w_obj);
typedef struct _lvgl_mvu_diff_AttrChange_obj_t lvgl_mvu_diff_AttrChange_obj_t;
extern const mp_obj_type_t lvgl_mvu_diff_AttrChange_type;
static mp_obj_t lvgl_mvu_diff_AttrChange_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
typedef struct _lvgl_mvu_diff_ChildChange_obj_t lvgl_mvu_diff_ChildChange_obj_t;
extern const mp_obj_type_t lvgl_mvu_diff_ChildChange_type;
static mp_obj_t lvgl_mvu_diff_ChildChange_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
typedef struct _lvgl_mvu_diff_WidgetDiff_obj_t lvgl_mvu_diff_WidgetDiff_obj_t;
typedef struct _lvgl_mvu_diff_WidgetDiff_vtable_t lvgl_mvu_diff_WidgetDiff_vtable_t;
extern const mp_obj_type_t lvgl_mvu_diff_WidgetDiff_type;
static mp_obj_t lvgl_mvu_diff_WidgetDiff_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static bool lvgl_mvu_diff_WidgetDiff_is_empty_native(lvgl_mvu_diff_WidgetDiff_obj_t *self);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_diff_WidgetDiff_is_empty_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_diff_WidgetDiff_is_empty_obj;
#endif

typedef struct _lvgl_mvu_program_Effect_obj_t lvgl_mvu_program_Effect_obj_t;
extern const mp_obj_type_t lvgl_mvu_program_Effect_type;
static mp_obj_t lvgl_mvu_program_Effect_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_program_Effect___init___obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_program_Effect___init___obj;
#endif

typedef struct _lvgl_mvu_program_Cmd_obj_t lvgl_mvu_program_Cmd_obj_t;
extern const mp_obj_type_t lvgl_mvu_program_Cmd_type;
static mp_obj_t lvgl_mvu_program_Cmd_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static mp_obj_t lvgl_mvu_program_Cmd_none_native(void);
static mp_obj_t lvgl_mvu_program_Cmd_of_msg_native(mp_obj_t msg);
static mp_obj_t lvgl_mvu_program_Cmd_batch_native(mp_obj_t cmds);
static mp_obj_t lvgl_mvu_program_Cmd_of_effect_native(mp_obj_t fn);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_program_Cmd___init___obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_program_Cmd___init___obj;
#endif

typedef struct _lvgl_mvu_program_SubDef_obj_t lvgl_mvu_program_SubDef_obj_t;
extern const mp_obj_type_t lvgl_mvu_program_SubDef_type;
static mp_obj_t lvgl_mvu_program_SubDef_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_program_SubDef___init___obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_program_SubDef___init___obj;
#endif

typedef struct _lvgl_mvu_program_Sub_obj_t lvgl_mvu_program_Sub_obj_t;
extern const mp_obj_type_t lvgl_mvu_program_Sub_type;
static mp_obj_t lvgl_mvu_program_Sub_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static mp_obj_t lvgl_mvu_program_Sub_none_native(void);
static mp_obj_t lvgl_mvu_program_Sub_timer_native(mp_int_t interval_ms, mp_obj_t msg);
static mp_obj_t lvgl_mvu_program_Sub_batch_native(mp_obj_t subs);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_program_Sub___init___obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_program_Sub___init___obj;
#endif

typedef struct _lvgl_mvu_program_Program_obj_t lvgl_mvu_program_Program_obj_t;
extern const mp_obj_type_t lvgl_mvu_program_Program_type;
static mp_obj_t lvgl_mvu_program_Program_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_program_Program___init___obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_program_Program___init___obj;
#endif

typedef struct _lvgl_mvu_reconciler_Reconciler_obj_t lvgl_mvu_reconciler_Reconciler_obj_t;
typedef struct _lvgl_mvu_reconciler_Reconciler_vtable_t lvgl_mvu_reconciler_Reconciler_vtable_t;
extern const mp_obj_type_t lvgl_mvu_reconciler_Reconciler_type;
static mp_obj_t lvgl_mvu_reconciler_Reconciler_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static void lvgl_mvu_reconciler_Reconciler_register_factory_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_int_t widget_key, mp_obj_t factory);
static void lvgl_mvu_reconciler_Reconciler_set_delete_fn_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t delete_fn);
static void lvgl_mvu_reconciler_Reconciler_set_event_binder_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t binder);
static mp_obj_t lvgl_mvu_reconciler_Reconciler_reconcile_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget, mp_obj_t parent_lv_obj);
static mp_obj_t lvgl_mvu_reconciler_Reconciler__create_node_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t widget, mp_obj_t parent_lv_obj);
static void lvgl_mvu_reconciler_Reconciler__reconcile_children_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget, mp_obj_t changes);
static void lvgl_mvu_reconciler_Reconciler__register_handlers_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget);
static void lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget);
static void lvgl_mvu_reconciler_Reconciler_dispose_tree_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler___init___obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler___init___obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler_register_factory_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler_register_factory_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler_set_delete_fn_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler_set_delete_fn_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler_set_event_binder_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler_set_event_binder_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler_reconcile_obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_reconciler_Reconciler_reconcile_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler__create_node_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler__create_node_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler__reconcile_children_obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_reconciler_Reconciler__reconcile_children_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler__register_handlers_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler__register_handlers_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler__reconcile_handlers_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler__reconcile_handlers_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_reconciler_Reconciler_dispose_tree_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_reconciler_Reconciler_dispose_tree_obj;
#endif

typedef struct _lvgl_mvu_viewnode_ViewNode_obj_t lvgl_mvu_viewnode_ViewNode_obj_t;
typedef struct _lvgl_mvu_viewnode_ViewNode_vtable_t lvgl_mvu_viewnode_ViewNode_vtable_t;
extern const mp_obj_type_t lvgl_mvu_viewnode_ViewNode_type;
static mp_obj_t lvgl_mvu_viewnode_ViewNode_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
static void lvgl_mvu_viewnode_ViewNode_apply_scalar_change_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t change);
static void lvgl_mvu_viewnode_ViewNode_apply_diff_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t diff);
static void lvgl_mvu_viewnode_ViewNode_update_widget_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t widget);
static void lvgl_mvu_viewnode_ViewNode_add_child_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t child, mp_int_t index);
static mp_obj_t lvgl_mvu_viewnode_ViewNode_remove_child_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t index);
static mp_obj_t lvgl_mvu_viewnode_ViewNode_get_child_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t index);
static mp_int_t lvgl_mvu_viewnode_ViewNode_child_count_native(lvgl_mvu_viewnode_ViewNode_obj_t *self);
static void lvgl_mvu_viewnode_ViewNode_register_handler_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t event_type, mp_obj_t handler);
static mp_obj_t lvgl_mvu_viewnode_ViewNode_unregister_handler_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t event_type);
static mp_obj_t lvgl_mvu_viewnode_ViewNode_clear_handlers_native(lvgl_mvu_viewnode_ViewNode_obj_t *self);
static void lvgl_mvu_viewnode_ViewNode_dispose_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t delete_fn);
static bool lvgl_mvu_viewnode_ViewNode_is_disposed_native(lvgl_mvu_viewnode_ViewNode_obj_t *self);

#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode___init___obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_viewnode_ViewNode___init___obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_apply_scalar_change_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_apply_scalar_change_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_apply_diff_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_apply_diff_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_update_widget_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_update_widget_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_add_child_obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_viewnode_ViewNode_add_child_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_remove_child_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_remove_child_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_get_child_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_get_child_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_child_count_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_child_count_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_register_handler_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_register_handler_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_unregister_handler_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_unregister_handler_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_clear_handlers_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_clear_handlers_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_dispose_obj;
#else
extern const mp_obj_fun_builtin_var_t lvgl_mvu_viewnode_ViewNode_dispose_obj;
#endif
#ifdef MYPYC_MICROPYTHON_FUNCTIONAL_RUNTIME_H
extern const int lvgl_mvu_viewnode_ViewNode_is_disposed_obj;
#else
extern const mp_obj_fun_builtin_fixed_t lvgl_mvu_viewnode_ViewNode_is_disposed_obj;
#endif

typedef struct _lvgl_mvu_widget_ScalarAttr_obj_t lvgl_mvu_widget_ScalarAttr_obj_t;
extern const mp_obj_type_t lvgl_mvu_widget_ScalarAttr_type;
static mp_obj_t lvgl_mvu_widget_ScalarAttr_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);
typedef struct _lvgl_mvu_widget_Widget_obj_t lvgl_mvu_widget_Widget_obj_t;
extern const mp_obj_type_t lvgl_mvu_widget_Widget_type;
static mp_obj_t lvgl_mvu_widget_Widget_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args);

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _lvgl_mvu_app_App_vtable_t {
    void (*set_timer_factory)(lvgl_mvu_app_App_obj_t *self, mp_obj_t factory);
    void (*dispatch)(lvgl_mvu_app_App_obj_t *self, mp_obj_t msg);
    bool (*tick)(lvgl_mvu_app_App_obj_t *self);
    void (*dispose)(lvgl_mvu_app_App_obj_t *self);
    bool (*is_disposed)(lvgl_mvu_app_App_obj_t *self);
    mp_int_t (*queue_length)(lvgl_mvu_app_App_obj_t *self);
    void (*_execute_cmd)(lvgl_mvu_app_App_obj_t *self, mp_obj_t cmd);
    void (*_setup_subscriptions)(lvgl_mvu_app_App_obj_t *self);
    void (*_teardown_subscriptions)(lvgl_mvu_app_App_obj_t *self);
    mp_obj_t (*_activate_sub)(lvgl_mvu_app_App_obj_t *self, mp_obj_t sub_def);
    mp_obj_t (*_activate_timer_sub)(lvgl_mvu_app_App_obj_t *self, mp_obj_t sub_def);
    bool (*_keys_match)(lvgl_mvu_app_App_obj_t *self, mp_obj_t new_keys);
};

struct _lvgl_mvu_app_App_obj_t {
    mp_obj_base_t base;
    const lvgl_mvu_app_App_vtable_t *vtable;
    mp_obj_t program;
    mp_obj_t reconciler;
    mp_obj_t model;
    mp_obj_t root_node;
    mp_obj_t _msg_queue;
    mp_obj_t _root_lv_obj;
    mp_obj_t _active_teardowns;
    mp_obj_t _sub_keys;
    mp_obj_t _timer_factory;
    bool _disposed;
};

struct _lvgl_mvu_attrs_AttrDef_obj_t {
    mp_obj_base_t base;
    mp_int_t key;
    mp_obj_t name;
    mp_obj_t default_val;
    mp_obj_t apply_fn;
    mp_obj_t compare_fn;
};

struct _lvgl_mvu_attrs_AttrRegistry_vtable_t {
    mp_obj_t (*add)(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_obj_t attr_def);
    mp_obj_t (*get)(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_int_t key);
    mp_obj_t (*get_or_raise)(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_int_t key);
    mp_obj_t (*all_attrs)(lvgl_mvu_attrs_AttrRegistry_obj_t *self);
};

struct _lvgl_mvu_attrs_AttrRegistry_obj_t {
    mp_obj_base_t base;
    const lvgl_mvu_attrs_AttrRegistry_vtable_t *vtable;
    mp_obj_t _attrs;
};

struct _lvgl_mvu_builders_WidgetBuilder_vtable_t {
    mp_obj_t (*user_key)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t key);
    mp_obj_t (*set_attr)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t attr_key, mp_obj_t value);
    mp_obj_t (*on)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t event, mp_obj_t msg);
    mp_obj_t (*on_value)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t event, mp_obj_t msg_fn);
    mp_obj_t (*add_child)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t child);
    mp_obj_t (*build)(lvgl_mvu_builders_WidgetBuilder_obj_t *self);
    mp_obj_t (*width)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w);
    mp_obj_t (*height)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t h);
    mp_obj_t (*size)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w, mp_int_t h);
    mp_obj_t (*pos)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t x, mp_int_t y);
    mp_obj_t (*align)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t align_value, mp_int_t x_ofs, mp_int_t y_ofs);
    mp_obj_t (*bg_color)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color);
    mp_obj_t (*bg_opa)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t opa);
    mp_obj_t (*border_color)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color);
    mp_obj_t (*border_width)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w);
    mp_obj_t (*radius)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t r);
    mp_obj_t (*padding)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t top, mp_int_t right, mp_int_t bottom, mp_int_t left);
    mp_obj_t (*pad_row)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t gap);
    mp_obj_t (*pad_column)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t gap);
    mp_obj_t (*text)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t value);
    mp_obj_t (*text_color)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color);
    mp_obj_t (*text_align)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t align_value);
    mp_obj_t (*shadow)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w, mp_int_t color, mp_int_t ofs_x, mp_int_t ofs_y);
    mp_obj_t (*flex_flow)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t flow);
    mp_obj_t (*flex_grow)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t grow);
    mp_obj_t (*value)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t v);
    mp_obj_t (*set_range)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t min_val, mp_int_t max_val);
    mp_obj_t (*checked)(lvgl_mvu_builders_WidgetBuilder_obj_t *self, bool state);
};

struct _lvgl_mvu_builders_WidgetBuilder_obj_t {
    mp_obj_base_t base;
    const lvgl_mvu_builders_WidgetBuilder_vtable_t *vtable;
    mp_int_t _key;
    mp_obj_t _user_key;
    mp_obj_t _attrs;
    mp_obj_t _children;
    mp_obj_t _handlers;
};

struct _lvgl_mvu_diff_AttrChange_obj_t {
    mp_obj_base_t base;
    mp_obj_t kind;
    mp_int_t key;
    mp_obj_t old_value;
    mp_obj_t new_value;
};

struct _lvgl_mvu_diff_ChildChange_obj_t {
    mp_obj_base_t base;
    mp_obj_t kind;
    mp_int_t index;
    mp_obj_t widget;
    mp_obj_t diff;
};

struct _lvgl_mvu_diff_WidgetDiff_vtable_t {
    bool (*is_empty)(lvgl_mvu_diff_WidgetDiff_obj_t *self);
};

struct _lvgl_mvu_diff_WidgetDiff_obj_t {
    mp_obj_base_t base;
    const lvgl_mvu_diff_WidgetDiff_vtable_t *vtable;
    mp_obj_t scalar_changes;
    mp_obj_t child_changes;
    bool event_changes;
};

struct _lvgl_mvu_program_Effect_obj_t {
    mp_obj_base_t base;
    mp_int_t kind;
    mp_obj_t data;
};

struct _lvgl_mvu_program_Cmd_obj_t {
    mp_obj_base_t base;
    mp_obj_t effects;
};

struct _lvgl_mvu_program_SubDef_obj_t {
    mp_obj_base_t base;
    mp_int_t kind;
    mp_obj_t key;
    mp_obj_t data;
};

struct _lvgl_mvu_program_Sub_obj_t {
    mp_obj_base_t base;
    mp_obj_t defs;
};

struct _lvgl_mvu_program_Program_obj_t {
    mp_obj_base_t base;
    mp_obj_t init_fn;
    mp_obj_t update_fn;
    mp_obj_t view_fn;
    mp_obj_t subscribe_fn;
};

struct _lvgl_mvu_reconciler_Reconciler_vtable_t {
    void (*register_factory)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_int_t widget_key, mp_obj_t factory);
    void (*set_delete_fn)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t delete_fn);
    void (*set_event_binder)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t binder);
    mp_obj_t (*reconcile)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget, mp_obj_t parent_lv_obj);
    mp_obj_t (*_create_node)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t widget, mp_obj_t parent_lv_obj);
    void (*_reconcile_children)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget, mp_obj_t changes);
    void (*_register_handlers)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget);
    void (*_reconcile_handlers)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget);
    void (*dispose_tree)(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node);
};

struct _lvgl_mvu_reconciler_Reconciler_obj_t {
    mp_obj_base_t base;
    const lvgl_mvu_reconciler_Reconciler_vtable_t *vtable;
    mp_obj_t _factories;
    mp_obj_t _delete_fn;
    mp_obj_t _event_binder;
    mp_obj_t _attr_registry;
};

struct _lvgl_mvu_viewnode_ViewNode_vtable_t {
    void (*apply_scalar_change)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t change);
    void (*apply_diff)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t diff);
    void (*update_widget)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t widget);
    void (*add_child)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t child, mp_int_t index);
    mp_obj_t (*remove_child)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t index);
    mp_obj_t (*get_child)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t index);
    mp_int_t (*child_count)(lvgl_mvu_viewnode_ViewNode_obj_t *self);
    void (*register_handler)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t event_type, mp_obj_t handler);
    mp_obj_t (*unregister_handler)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t event_type);
    mp_obj_t (*clear_handlers)(lvgl_mvu_viewnode_ViewNode_obj_t *self);
    void (*dispose)(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t delete_fn);
    bool (*is_disposed)(lvgl_mvu_viewnode_ViewNode_obj_t *self);
};

struct _lvgl_mvu_viewnode_ViewNode_obj_t {
    mp_obj_base_t base;
    const lvgl_mvu_viewnode_ViewNode_vtable_t *vtable;
    mp_obj_t lv_obj;
    mp_obj_t widget;
    mp_obj_t children;
    mp_obj_t handlers;
    bool _disposed;
    mp_obj_t _attr_registry;
};

struct _lvgl_mvu_widget_ScalarAttr_obj_t {
    mp_obj_base_t base;
    mp_int_t key;
    mp_obj_t value;
};

struct _lvgl_mvu_widget_Widget_obj_t {
    mp_obj_base_t base;
    mp_int_t key;
    mp_obj_t user_key;
    mp_obj_t scalar_attrs;
    mp_obj_t children;
    mp_obj_t event_handlers;
};


static mp_obj_t lvgl_mvu_app_App__activate_sub_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t sub_def) {
    if ((((lvgl_mvu_program_SubDef_obj_t *)MP_OBJ_TO_PTR(sub_def))->kind == 0)) {
        return lvgl_mvu_app_App__activate_timer_sub_native(self, sub_def);
    }
    return mp_const_none;
}

static mp_obj_t lvgl_mvu_app_App__activate_sub_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t sub_def = arg0_obj;
    return lvgl_mvu_app_App__activate_sub_native(self, sub_def);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_app_App__activate_sub_obj, lvgl_mvu_app_App__activate_sub_mp);

static mp_obj_t lvgl_mvu_app_App__activate_timer_sub_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t sub_def) {
    if ((self->_timer_factory == mp_const_none)) {
        return mp_const_none;
    }
    mp_obj_t timer_data = ((lvgl_mvu_program_SubDef_obj_t *)MP_OBJ_TO_PTR(sub_def))->data;
    mp_int_t interval_ms = mp_obj_get_int(mp_obj_subscr(timer_data, mp_obj_new_int(0), MP_OBJ_SENTINEL));
    mp_obj_t msg = mp_obj_subscr(timer_data, mp_obj_new_int(1), MP_OBJ_SENTINEL);
    mp_obj_t _tmp1 = self->_timer_factory;
    mp_obj_t teardown = mp_call_function_n_kw(_tmp1, 3, 0, (const mp_obj_t[]){mp_obj_new_int(interval_ms), MP_OBJ_FROM_PTR(self), msg});
    return teardown;
}

static mp_obj_t lvgl_mvu_app_App__activate_timer_sub_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t sub_def = arg0_obj;
    return lvgl_mvu_app_App__activate_timer_sub_native(self, sub_def);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_app_App__activate_timer_sub_obj, lvgl_mvu_app_App__activate_timer_sub_mp);

static void lvgl_mvu_app_App__execute_cmd_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t cmd) {
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(((lvgl_mvu_program_Cmd_obj_t *)MP_OBJ_TO_PTR(cmd))->effects)))) {
        mp_obj_t effect = mp_obj_subscr(((lvgl_mvu_program_Cmd_obj_t *)MP_OBJ_TO_PTR(cmd))->effects, mp_obj_new_int(i), MP_OBJ_SENTINEL);
        if ((((lvgl_mvu_program_Effect_obj_t *)MP_OBJ_TO_PTR(effect))->kind == 0)) {
            (void)lvgl_mvu_app_App_dispatch_native(self, ((lvgl_mvu_program_Effect_obj_t *)MP_OBJ_TO_PTR(effect))->data);
        } else {
            if ((((lvgl_mvu_program_Effect_obj_t *)MP_OBJ_TO_PTR(effect))->kind == 1)) {
                mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(effect, MP_QSTR_data, __method); __method[2] = mp_obj_new_bound_meth(MP_OBJ_FROM_PTR(&lvgl_mvu_app_App_dispatch_obj), MP_OBJ_FROM_PTR(self)); mp_call_method_n_kw(1, 0, __method); });
                (void)_tmp1;
            }
        }
        i += 1;
    }
    return;
}

static mp_obj_t lvgl_mvu_app_App__execute_cmd_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t cmd = arg0_obj;
    lvgl_mvu_app_App__execute_cmd_native(self, cmd);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_app_App__execute_cmd_obj, lvgl_mvu_app_App__execute_cmd_mp);

static bool lvgl_mvu_app_App__keys_match_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t new_keys) {
    if ((mp_obj_get_int(mp_obj_len(new_keys)) != mp_obj_get_int(mp_obj_len(self->_sub_keys)))) {
        return false;
    }
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(new_keys)))) {
        if ((!mp_obj_equal(mp_obj_subscr(new_keys, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_obj_subscr(self->_sub_keys, mp_obj_new_int(i), MP_OBJ_SENTINEL)))) {
            return false;
        }
        i += 1;
    }
    return true;
}

static mp_obj_t lvgl_mvu_app_App__keys_match_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t new_keys = arg0_obj;
    return lvgl_mvu_app_App__keys_match_native(self, new_keys) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_app_App__keys_match_obj, lvgl_mvu_app_App__keys_match_mp);

static void lvgl_mvu_app_App__setup_subscriptions_native(lvgl_mvu_app_App_obj_t *self) {
    mp_obj_t _tmp1 = ((lvgl_mvu_program_Program_obj_t *)MP_OBJ_TO_PTR(self->program))->subscribe_fn;
    if ((_tmp1 == mp_const_none)) {
        return;
    }
    mp_obj_t _tmp2 = ({ mp_obj_t __method[3]; mp_load_method(self->program, MP_QSTR_subscribe_fn, __method); __method[2] = self->model; mp_call_method_n_kw(1, 0, __method); });
    mp_obj_t sub = _tmp2;
    mp_obj_t new_keys = mp_obj_new_list(0, NULL);
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(((lvgl_mvu_program_Sub_obj_t *)MP_OBJ_TO_PTR(sub))->defs)))) {
        mp_obj_t _tmp3 = mp_obj_list_append(new_keys, mp_const_none);
        (void)_tmp3;
        i += 1;
    }
    if (lvgl_mvu_app_App__keys_match_native(self, new_keys)) {
        return;
    }
    (void)lvgl_mvu_app_App__teardown_subscriptions_native(self);
    i = 0;
    mp_obj_t activated_keys = mp_obj_new_list(0, NULL);
    while ((i < mp_obj_get_int(mp_obj_len(((lvgl_mvu_program_Sub_obj_t *)MP_OBJ_TO_PTR(sub))->defs)))) {
        mp_obj_t sub_def = mp_obj_subscr(((lvgl_mvu_program_Sub_obj_t *)MP_OBJ_TO_PTR(sub))->defs, mp_obj_new_int(i), MP_OBJ_SENTINEL);
        mp_obj_t teardown = lvgl_mvu_app_App__activate_sub_native(self, sub_def);
        if ((teardown != mp_const_none)) {
            mp_obj_t _tmp4 = mp_obj_list_append(self->_active_teardowns, teardown);
            (void)_tmp4;
            mp_obj_t _tmp5 = mp_obj_list_append(activated_keys, ((lvgl_mvu_program_SubDef_obj_t *)MP_OBJ_TO_PTR(sub_def))->key);
            (void)_tmp5;
        }
        i += 1;
    }
    self->_sub_keys = activated_keys;
}

static mp_obj_t lvgl_mvu_app_App__setup_subscriptions_mp(mp_obj_t self_in) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    lvgl_mvu_app_App__setup_subscriptions_native(self);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_app_App__setup_subscriptions_obj, lvgl_mvu_app_App__setup_subscriptions_mp);

static void lvgl_mvu_app_App__teardown_subscriptions_native(lvgl_mvu_app_App_obj_t *self) {
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(self->_active_teardowns)))) {
        mp_obj_t teardown = mp_obj_subscr(self->_active_teardowns, mp_obj_new_int(i), MP_OBJ_SENTINEL);
        (void)mp_call_function_0(teardown);
        i += 1;
    }
    self->_active_teardowns = mp_obj_new_list(0, NULL);
    self->_sub_keys = mp_obj_new_list(0, NULL);
    return;
}

static mp_obj_t lvgl_mvu_app_App__teardown_subscriptions_mp(mp_obj_t self_in) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    lvgl_mvu_app_App__teardown_subscriptions_native(self);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_app_App__teardown_subscriptions_obj, lvgl_mvu_app_App__teardown_subscriptions_mp);

static void lvgl_mvu_app_App_dispatch_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t msg) {
    if ((!self->_disposed)) {
        mp_obj_t _tmp1 = mp_obj_list_append(self->_msg_queue, msg);
        (void)_tmp1;
    }
    return;
}

static mp_obj_t lvgl_mvu_app_App_dispatch_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t msg = arg0_obj;
    lvgl_mvu_app_App_dispatch_native(self, msg);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_app_App_dispatch_obj, lvgl_mvu_app_App_dispatch_mp);

static void lvgl_mvu_app_App_dispose_native(lvgl_mvu_app_App_obj_t *self) {
    if (self->_disposed) {
        return;
    }
    self->_disposed = true;
    (void)lvgl_mvu_app_App__teardown_subscriptions_native(self);
    if ((self->root_node != mp_const_none)) {
        mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(self->reconciler, MP_QSTR_dispose_tree, __method); __method[2] = self->root_node; mp_call_method_n_kw(1, 0, __method); });
        (void)_tmp1;
        self->root_node = mp_const_none;
    }
    self->_msg_queue = mp_obj_new_list(0, NULL);
}

static mp_obj_t lvgl_mvu_app_App_dispose_mp(mp_obj_t self_in) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    lvgl_mvu_app_App_dispose_native(self);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_app_App_dispose_obj, lvgl_mvu_app_App_dispose_mp);

static bool lvgl_mvu_app_App_is_disposed_native(lvgl_mvu_app_App_obj_t *self) {
    return self->_disposed;
}

static mp_obj_t lvgl_mvu_app_App_is_disposed_mp(mp_obj_t self_in) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return lvgl_mvu_app_App_is_disposed_native(self) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_app_App_is_disposed_obj, lvgl_mvu_app_App_is_disposed_mp);

static mp_int_t lvgl_mvu_app_App_queue_length_native(lvgl_mvu_app_App_obj_t *self) {
    return mp_obj_get_int(mp_obj_len(self->_msg_queue));
}

static mp_obj_t lvgl_mvu_app_App_queue_length_mp(mp_obj_t self_in) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(lvgl_mvu_app_App_queue_length_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_app_App_queue_length_obj, lvgl_mvu_app_App_queue_length_mp);

static void lvgl_mvu_app_App_set_timer_factory_native(lvgl_mvu_app_App_obj_t *self, mp_obj_t factory) {
    self->_timer_factory = factory;
    return;
}

static mp_obj_t lvgl_mvu_app_App_set_timer_factory_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t factory = arg0_obj;
    lvgl_mvu_app_App_set_timer_factory_native(self, factory);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_app_App_set_timer_factory_obj, lvgl_mvu_app_App_set_timer_factory_mp);

static bool lvgl_mvu_app_App_tick_native(lvgl_mvu_app_App_obj_t *self) {
    if (self->_disposed) {
        return false;
    }
    bool changed = false;
    while ((mp_obj_get_int(mp_obj_len(self->_msg_queue)) > 0)) {
        mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(self->_msg_queue, MP_QSTR_pop, __method); __method[2] = mp_obj_new_int(0); mp_call_method_n_kw(1, 0, __method); });
        mp_obj_t msg = _tmp1;
        mp_obj_t _tmp2 = ({ mp_obj_t __method[4]; mp_load_method(self->program, MP_QSTR_update_fn, __method); __method[2] = msg; __method[3] = self->model; mp_call_method_n_kw(2, 0, __method); });
        mp_obj_t update_result = _tmp2;
        self->model = mp_obj_subscr(update_result, mp_obj_new_int(0), MP_OBJ_SENTINEL);
        mp_obj_t cmd = mp_obj_subscr(update_result, mp_obj_new_int(1), MP_OBJ_SENTINEL);
        (void)lvgl_mvu_app_App__execute_cmd_native(self, cmd);
        changed = true;
    }
    if ((changed || (self->root_node == mp_const_none))) {
        mp_obj_t _tmp3 = ({ mp_obj_t __method[3]; mp_load_method(self->program, MP_QSTR_view_fn, __method); __method[2] = self->model; mp_call_method_n_kw(1, 0, __method); });
        mp_obj_t widget = _tmp3;
        mp_obj_t _tmp4 = ({ mp_obj_t __method[5]; mp_load_method(self->reconciler, MP_QSTR_reconcile, __method); __method[2] = self->root_node; __method[3] = widget; __method[4] = self->_root_lv_obj; mp_call_method_n_kw(3, 0, __method); });
        self->root_node = _tmp4;
        mp_obj_t _tmp5 = ((lvgl_mvu_program_Program_obj_t *)MP_OBJ_TO_PTR(self->program))->subscribe_fn;
        if ((changed && (_tmp5 != mp_const_none))) {
            (void)lvgl_mvu_app_App__setup_subscriptions_native(self);
        }
    }
    return changed;
}

static mp_obj_t lvgl_mvu_app_App_tick_mp(mp_obj_t self_in) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return lvgl_mvu_app_App_tick_native(self) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_app_App_tick_obj, lvgl_mvu_app_App_tick_mp);

static mp_obj_t lvgl_mvu_app_App___init___mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t program = args[1];
    mp_obj_t reconciler = args[2];
    mp_obj_t root_lv_obj = (n_args > 3) ? args[3] : mp_const_none;
    self->program = program;
    self->reconciler = reconciler;
    self->model = mp_const_none;
    self->root_node = mp_const_none;
    self->_msg_queue = mp_obj_new_list(0, NULL);
    self->_root_lv_obj = root_lv_obj;
    self->_active_teardowns = mp_obj_new_list(0, NULL);
    self->_sub_keys = mp_obj_new_list(0, NULL);
    self->_timer_factory = mp_const_none;
    self->_disposed = false;
    mp_obj_t _tmp1 = ({ mp_obj_t __method[2]; mp_load_method(program, MP_QSTR_init_fn, __method); mp_call_method_n_kw(0, 0, __method); });
    mp_obj_t init_result = _tmp1;
    self->model = mp_obj_subscr(init_result, mp_obj_new_int(0), MP_OBJ_SENTINEL);
    mp_obj_t init_cmd = mp_obj_subscr(init_result, mp_obj_new_int(1), MP_OBJ_SENTINEL);
    (void)lvgl_mvu_app_App__execute_cmd_native(self, init_cmd);
    (void)lvgl_mvu_app_App__setup_subscriptions_native(self);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_app_App___init___obj, 3, 4, lvgl_mvu_app_App___init___mp);

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_add_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_obj_t attr_def) {
    mp_obj_subscr(self->_attrs, mp_obj_new_int(((lvgl_mvu_attrs_AttrDef_obj_t *)MP_OBJ_TO_PTR(attr_def))->key), attr_def);
    return attr_def;
}

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_add_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_attrs_AttrRegistry_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t attr_def = arg0_obj;
    return lvgl_mvu_attrs_AttrRegistry_add_native(self, attr_def);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_attrs_AttrRegistry_add_obj, lvgl_mvu_attrs_AttrRegistry_add_mp);

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_all_attrs_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self) {
    mp_obj_t result = mp_obj_new_dict(0);
    mp_obj_t k;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(self->_attrs, &_tmp2);
    while ((k = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_subscr(result, k, mp_obj_subscr(self->_attrs, k, MP_OBJ_SENTINEL));
    }
    return result;
}

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_all_attrs_mp(mp_obj_t self_in) {
    lvgl_mvu_attrs_AttrRegistry_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return lvgl_mvu_attrs_AttrRegistry_all_attrs_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_attrs_AttrRegistry_all_attrs_obj, lvgl_mvu_attrs_AttrRegistry_all_attrs_mp);

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_get_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_int_t key) {
    if ((mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, mp_obj_new_int(key), self->_attrs)))) {
        return mp_obj_subscr(self->_attrs, mp_obj_new_int(key), MP_OBJ_SENTINEL);
    }
    return mp_const_none;
}

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_get_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_attrs_AttrRegistry_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t key = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_attrs_AttrRegistry_get_native(self, key);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_attrs_AttrRegistry_get_obj, lvgl_mvu_attrs_AttrRegistry_get_mp);

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_get_or_raise_native(lvgl_mvu_attrs_AttrRegistry_obj_t *self, mp_int_t key) {
    return mp_obj_subscr(self->_attrs, mp_obj_new_int(key), MP_OBJ_SENTINEL);
}

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_get_or_raise_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_attrs_AttrRegistry_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t key = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_attrs_AttrRegistry_get_or_raise_native(self, key);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_attrs_AttrRegistry_get_or_raise_obj, lvgl_mvu_attrs_AttrRegistry_get_or_raise_mp);

static mp_obj_t lvgl_mvu_attrs_AttrRegistry___init___mp(mp_obj_t self_in) {
    lvgl_mvu_attrs_AttrRegistry_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->_attrs = mp_obj_new_dict(0);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_attrs_AttrRegistry___init___obj, lvgl_mvu_attrs_AttrRegistry___init___mp);

static mp_obj_t lvgl_mvu_builders__attr_sort_key(mp_obj_t a_obj) {
    mp_obj_t a = a_obj;

    return mp_obj_new_int(((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(a))->key);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_builders__attr_sort_key_obj, lvgl_mvu_builders__attr_sort_key);
static mp_obj_t lvgl_mvu_builders_WidgetBuilder_add_child_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t child) {
    mp_obj_t _tmp1 = mp_obj_list_append(self->_children, child);
    (void)_tmp1;
    return self;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_add_child_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t child = arg0_obj;
    return lvgl_mvu_builders_WidgetBuilder_add_child_native(self, child);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_add_child_obj, lvgl_mvu_builders_WidgetBuilder_add_child_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_align_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t align_value, mp_int_t x_ofs, mp_int_t y_ofs) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[4]; mp_load_method(lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 4, mp_obj_new_int(align_value)), MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(5); __method[3] = mp_obj_new_int(x_ofs); mp_call_method_n_kw(2, 0, __method); });
    mp_obj_t _tmp2 = ({ mp_obj_t __method[4]; mp_load_method(_tmp1, MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(6); __method[3] = mp_obj_new_int(y_ofs); mp_call_method_n_kw(2, 0, __method); });
    return _tmp2;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_align_mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t align_value = mp_obj_get_int(args[1]);
    mp_int_t x_ofs = (n_args > 2) ? mp_obj_get_int(args[2]) : 0;
    mp_int_t y_ofs = (n_args > 3) ? mp_obj_get_int(args[3]) : 0;
    return lvgl_mvu_builders_WidgetBuilder_align_native(self, align_value, x_ofs, y_ofs);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_builders_WidgetBuilder_align_obj, 2, 4, lvgl_mvu_builders_WidgetBuilder_align_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_bg_color_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 40, mp_obj_new_int(color));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_bg_color_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t color = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_bg_color_native(self, color);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_bg_color_obj, lvgl_mvu_builders_WidgetBuilder_bg_color_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_bg_opa_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t opa) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 41, mp_obj_new_int(opa));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_bg_opa_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t opa = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_bg_opa_native(self, opa);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_bg_opa_obj, lvgl_mvu_builders_WidgetBuilder_bg_opa_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_border_color_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 60, mp_obj_new_int(color));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_border_color_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t color = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_border_color_native(self, color);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_border_color_obj, lvgl_mvu_builders_WidgetBuilder_border_color_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_border_width_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 61, mp_obj_new_int(w));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_border_width_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t w = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_border_width_native(self, w);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_border_width_obj, lvgl_mvu_builders_WidgetBuilder_border_width_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_build_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self) {
    mp_obj_t sorted_attrs = mp_call_function_n_kw(mp_load_global(MP_QSTR_sorted) /* mp_builtin_sorted_obj */, 1, 1, (const mp_obj_t[]){self->_attrs, MP_OBJ_NEW_QSTR(MP_QSTR_key), MP_OBJ_FROM_PTR(&lvgl_mvu_builders__attr_sort_key_obj)});
    return lvgl_mvu_widget_Widget_make_new(&lvgl_mvu_widget_Widget_type, 0, 0, (const mp_obj_t[]){});
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_build_mp(mp_obj_t self_in) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return lvgl_mvu_builders_WidgetBuilder_build_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_builders_WidgetBuilder_build_obj, lvgl_mvu_builders_WidgetBuilder_build_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_checked_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, bool state) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 143, mp_obj_new_bool(state));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_checked_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    bool state = mp_obj_is_true(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_checked_native(self, state);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_checked_obj, lvgl_mvu_builders_WidgetBuilder_checked_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_flex_flow_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t flow) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 120, mp_obj_new_int(flow));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_flex_flow_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t flow = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_flex_flow_native(self, flow);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_flex_flow_obj, lvgl_mvu_builders_WidgetBuilder_flex_flow_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_flex_grow_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t grow) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 124, mp_obj_new_int(grow));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_flex_grow_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t grow = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_flex_grow_native(self, grow);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_flex_grow_obj, lvgl_mvu_builders_WidgetBuilder_flex_grow_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_height_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t h) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 3, mp_obj_new_int(h));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_height_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t h = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_height_native(self, h);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_height_obj, lvgl_mvu_builders_WidgetBuilder_height_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_on_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t event, mp_obj_t msg) {
    mp_obj_t _tmp1_items[] = {mp_obj_new_int(event), msg};
    mp_obj_t _tmp1 = mp_obj_new_tuple(2, _tmp1_items);
    mp_obj_t _tmp2 = mp_obj_list_append(self->_handlers, _tmp1);
    (void)_tmp2;
    return self;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_on_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t event = mp_obj_get_int(arg0_obj);
    mp_obj_t msg = arg1_obj;
    return lvgl_mvu_builders_WidgetBuilder_on_native(self, event, msg);
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_builders_WidgetBuilder_on_obj, lvgl_mvu_builders_WidgetBuilder_on_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_on_value_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t event, mp_obj_t msg_fn) {
    mp_obj_t _tmp1_items[] = {mp_obj_new_str("value", 5), msg_fn};
    mp_obj_t _tmp1 = mp_obj_new_tuple(2, _tmp1_items);
    mp_obj_t _tmp2_items[] = {mp_obj_new_int(event), _tmp1};
    mp_obj_t _tmp2 = mp_obj_new_tuple(2, _tmp2_items);
    mp_obj_t _tmp3 = mp_obj_list_append(self->_handlers, _tmp2);
    (void)_tmp3;
    return self;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_on_value_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t event = mp_obj_get_int(arg0_obj);
    mp_obj_t msg_fn = arg1_obj;
    return lvgl_mvu_builders_WidgetBuilder_on_value_native(self, event, msg_fn);
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_builders_WidgetBuilder_on_value_obj, lvgl_mvu_builders_WidgetBuilder_on_value_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pad_column_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t gap) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 25, mp_obj_new_int(gap));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pad_column_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t gap = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_pad_column_native(self, gap);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_pad_column_obj, lvgl_mvu_builders_WidgetBuilder_pad_column_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pad_row_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t gap) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 24, mp_obj_new_int(gap));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pad_row_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t gap = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_pad_row_native(self, gap);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_pad_row_obj, lvgl_mvu_builders_WidgetBuilder_pad_row_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_padding_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t top, mp_int_t right, mp_int_t bottom, mp_int_t left) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[4]; mp_load_method(lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 20, mp_obj_new_int(top)), MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(21); __method[3] = mp_obj_new_int(right); mp_call_method_n_kw(2, 0, __method); });
    mp_obj_t _tmp2 = ({ mp_obj_t __method[4]; mp_load_method(_tmp1, MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(22); __method[3] = mp_obj_new_int(bottom); mp_call_method_n_kw(2, 0, __method); });
    mp_obj_t _tmp3 = ({ mp_obj_t __method[4]; mp_load_method(_tmp2, MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(23); __method[3] = mp_obj_new_int(left); mp_call_method_n_kw(2, 0, __method); });
    return _tmp3;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_padding_mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t top = mp_obj_get_int(args[1]);
    mp_int_t right = mp_obj_get_int(args[2]);
    mp_int_t bottom = mp_obj_get_int(args[3]);
    mp_int_t left = mp_obj_get_int(args[4]);
    return lvgl_mvu_builders_WidgetBuilder_padding_native(self, top, right, bottom, left);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_builders_WidgetBuilder_padding_obj, 5, 5, lvgl_mvu_builders_WidgetBuilder_padding_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pos_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t x, mp_int_t y) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[4]; mp_load_method(lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 0, mp_obj_new_int(x)), MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(1); __method[3] = mp_obj_new_int(y); mp_call_method_n_kw(2, 0, __method); });
    return _tmp1;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_pos_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t x = mp_obj_get_int(arg0_obj);
    mp_int_t y = mp_obj_get_int(arg1_obj);
    return lvgl_mvu_builders_WidgetBuilder_pos_native(self, x, y);
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_builders_WidgetBuilder_pos_obj, lvgl_mvu_builders_WidgetBuilder_pos_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_radius_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t r) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 64, mp_obj_new_int(r));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_radius_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t r = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_radius_native(self, r);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_radius_obj, lvgl_mvu_builders_WidgetBuilder_radius_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_set_attr_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t attr_key, mp_obj_t value) {
    mp_obj_t _tmp1 = mp_obj_list_append(self->_attrs, lvgl_mvu_widget_ScalarAttr_make_new(&lvgl_mvu_widget_ScalarAttr_type, 2, 0, (const mp_obj_t[]){mp_obj_new_int(attr_key), value}));
    (void)_tmp1;
    return self;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_set_attr_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t attr_key = mp_obj_get_int(arg0_obj);
    mp_obj_t value = arg1_obj;
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, attr_key, value);
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_builders_WidgetBuilder_set_attr_obj, lvgl_mvu_builders_WidgetBuilder_set_attr_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_set_range_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t min_val, mp_int_t max_val) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[4]; mp_load_method(lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 140, mp_obj_new_int(min_val)), MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(141); __method[3] = mp_obj_new_int(max_val); mp_call_method_n_kw(2, 0, __method); });
    return _tmp1;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_set_range_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t min_val = mp_obj_get_int(arg0_obj);
    mp_int_t max_val = mp_obj_get_int(arg1_obj);
    return lvgl_mvu_builders_WidgetBuilder_set_range_native(self, min_val, max_val);
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_builders_WidgetBuilder_set_range_obj, lvgl_mvu_builders_WidgetBuilder_set_range_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_shadow_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w, mp_int_t color, mp_int_t ofs_x, mp_int_t ofs_y) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[4]; mp_load_method(lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 80, mp_obj_new_int(w)), MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(81); __method[3] = mp_obj_new_int(color); mp_call_method_n_kw(2, 0, __method); });
    mp_obj_t _tmp2 = ({ mp_obj_t __method[4]; mp_load_method(_tmp1, MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(82); __method[3] = mp_obj_new_int(ofs_x); mp_call_method_n_kw(2, 0, __method); });
    mp_obj_t _tmp3 = ({ mp_obj_t __method[4]; mp_load_method(_tmp2, MP_QSTR_set_attr, __method); __method[2] = mp_obj_new_int(83); __method[3] = mp_obj_new_int(ofs_y); mp_call_method_n_kw(2, 0, __method); });
    return _tmp3;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_shadow_mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t w = mp_obj_get_int(args[1]);
    mp_int_t color = mp_obj_get_int(args[2]);
    mp_int_t ofs_x = (n_args > 3) ? mp_obj_get_int(args[3]) : 0;
    mp_int_t ofs_y = (n_args > 4) ? mp_obj_get_int(args[4]) : 0;
    return lvgl_mvu_builders_WidgetBuilder_shadow_native(self, w, color, ofs_x, ofs_y);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_builders_WidgetBuilder_shadow_obj, 3, 5, lvgl_mvu_builders_WidgetBuilder_shadow_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_size_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w, mp_int_t h) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(lvgl_mvu_builders_WidgetBuilder_width_native(self, w), MP_QSTR_height, __method); __method[2] = mp_obj_new_int(h); mp_call_method_n_kw(1, 0, __method); });
    return _tmp1;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_size_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t w = mp_obj_get_int(arg0_obj);
    mp_int_t h = mp_obj_get_int(arg1_obj);
    return lvgl_mvu_builders_WidgetBuilder_size_native(self, w, h);
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_builders_WidgetBuilder_size_obj, lvgl_mvu_builders_WidgetBuilder_size_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t value) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 100, value);
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t value = arg0_obj;
    return lvgl_mvu_builders_WidgetBuilder_text_native(self, value);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_text_obj, lvgl_mvu_builders_WidgetBuilder_text_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_align_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t align_value) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 104, mp_obj_new_int(align_value));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_align_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t align_value = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_text_align_native(self, align_value);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_text_align_obj, lvgl_mvu_builders_WidgetBuilder_text_align_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_color_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t color) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 101, mp_obj_new_int(color));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_text_color_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t color = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_text_color_native(self, color);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_text_color_obj, lvgl_mvu_builders_WidgetBuilder_text_color_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_user_key_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_obj_t key) {
    self->_user_key = key;
    return self;
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_user_key_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t key = arg0_obj;
    return lvgl_mvu_builders_WidgetBuilder_user_key_native(self, key);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_user_key_obj, lvgl_mvu_builders_WidgetBuilder_user_key_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_value_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t v) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 142, mp_obj_new_int(v));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_value_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t v = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_value_native(self, v);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_value_obj, lvgl_mvu_builders_WidgetBuilder_value_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_width_native(lvgl_mvu_builders_WidgetBuilder_obj_t *self, mp_int_t w) {
    return lvgl_mvu_builders_WidgetBuilder_set_attr_native(self, 2, mp_obj_new_int(w));
}

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_width_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t w = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_builders_WidgetBuilder_width_native(self, w);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder_width_obj, lvgl_mvu_builders_WidgetBuilder_width_mp);

static mp_obj_t lvgl_mvu_builders_WidgetBuilder___init___mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t key = mp_obj_get_int(arg0_obj);
    self->_key = key;
    self->_user_key = mp_obj_new_str("", 0);
    self->_attrs = mp_obj_new_list(0, NULL);
    self->_children = mp_obj_new_list(0, NULL);
    self->_handlers = mp_obj_new_list(0, NULL);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_builders_WidgetBuilder___init___obj, lvgl_mvu_builders_WidgetBuilder___init___mp);

static mp_obj_t lvgl_mvu_diff_diff_scalars(mp_obj_t prev_obj, mp_obj_t next_attrs_obj) {
    mp_obj_t prev = prev_obj;
    mp_obj_t next_attrs = next_attrs_obj;

    mp_obj_t changes = mp_obj_new_list(0, NULL);
    mp_int_t i = 0;
    mp_int_t j = 0;
    while (((i < mp_obj_get_int(mp_obj_len(prev))) || (j < mp_obj_get_int(mp_obj_len(next_attrs))))) {
        if ((i >= mp_obj_get_int(mp_obj_len(prev)))) {
            mp_int_t _tmp1 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->key;
            mp_obj_t _tmp2 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->value;
            mp_obj_t _tmp3 = mp_obj_list_append(changes, lvgl_mvu_diff_AttrChange_make_new(&lvgl_mvu_diff_AttrChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("added", 5), mp_obj_new_int(_tmp1), mp_const_none, _tmp2}));
            (void)_tmp3;
            j += 1;
        } else {
            if ((j >= mp_obj_get_int(mp_obj_len(next_attrs)))) {
                mp_int_t _tmp4 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->key;
                mp_obj_t _tmp5 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->value;
                mp_obj_t _tmp6 = mp_obj_list_append(changes, lvgl_mvu_diff_AttrChange_make_new(&lvgl_mvu_diff_AttrChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("removed", 7), mp_obj_new_int(_tmp4), _tmp5, mp_const_none}));
                (void)_tmp6;
                i += 1;
            } else {
                mp_int_t _tmp7 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->key;
                mp_int_t _tmp8 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->key;
                if ((_tmp7 < _tmp8)) {
                    mp_int_t _tmp9 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->key;
                    mp_obj_t _tmp10 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->value;
                    mp_obj_t _tmp11 = mp_obj_list_append(changes, lvgl_mvu_diff_AttrChange_make_new(&lvgl_mvu_diff_AttrChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("removed", 7), mp_obj_new_int(_tmp9), _tmp10, mp_const_none}));
                    (void)_tmp11;
                    i += 1;
                } else {
                    mp_int_t _tmp12 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->key;
                    mp_int_t _tmp13 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->key;
                    if ((_tmp12 > _tmp13)) {
                        mp_int_t _tmp14 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->key;
                        mp_obj_t _tmp15 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->value;
                        mp_obj_t _tmp16 = mp_obj_list_append(changes, lvgl_mvu_diff_AttrChange_make_new(&lvgl_mvu_diff_AttrChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("added", 5), mp_obj_new_int(_tmp14), mp_const_none, _tmp15}));
                        (void)_tmp16;
                        j += 1;
                    } else {
                        mp_obj_t _tmp17 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->value;
                        mp_obj_t _tmp18 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->value;
                        if ((!mp_obj_equal(_tmp17, _tmp18))) {
                            mp_int_t _tmp19 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->key;
                            mp_obj_t _tmp20 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->value;
                            mp_obj_t _tmp21 = ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(next_attrs, mp_obj_new_int(j), MP_OBJ_SENTINEL)))->value;
                            mp_obj_t _tmp22 = mp_obj_list_append(changes, lvgl_mvu_diff_AttrChange_make_new(&lvgl_mvu_diff_AttrChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("updated", 7), mp_obj_new_int(_tmp19), _tmp20, _tmp21}));
                            (void)_tmp22;
                        }
                        i += 1;
                        j += 1;
                    }
                }
            }
        }
    }
    return changes;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_diff_diff_scalars_obj, lvgl_mvu_diff_diff_scalars);
static mp_obj_t lvgl_mvu_diff_can_reuse(mp_obj_t prev_obj, mp_obj_t next_w_obj) {
    mp_obj_t prev = prev_obj;
    mp_obj_t next_w = next_w_obj;

    if ((((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(prev))->key != ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->key)) {
        return false ? mp_const_true : mp_const_false;
    }
    if (((!mp_obj_equal(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(prev))->user_key, mp_obj_new_str("", 0))) || (!mp_obj_equal(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->user_key, mp_obj_new_str("", 0))))) {
        return mp_obj_equal(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(prev))->user_key, ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->user_key) ? mp_const_true : mp_const_false;
    }
    return true ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_diff_can_reuse_obj, lvgl_mvu_diff_can_reuse);
static mp_obj_t lvgl_mvu_diff_diff_children(mp_obj_t prev_obj, mp_obj_t next_children_obj) {
    mp_obj_t prev = prev_obj;
    mp_obj_t next_children = next_children_obj;

    mp_obj_t changes = mp_obj_new_list(0, NULL);
    mp_int_t prev_len = mp_obj_get_int(mp_obj_len(prev));
    mp_int_t next_len = mp_obj_get_int(mp_obj_len(next_children));
    mp_int_t max_len = prev_len;
    if ((next_len > max_len)) {
        max_len = next_len;
    }
    mp_int_t i = 0;
    while ((i < max_len)) {
        if ((i >= next_len)) {
            mp_obj_t _tmp1 = mp_obj_list_append(changes, lvgl_mvu_diff_ChildChange_make_new(&lvgl_mvu_diff_ChildChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("remove", 6), mp_obj_new_int(i), mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_const_none}));
            (void)_tmp1;
        } else {
            if ((i >= prev_len)) {
                mp_obj_t _tmp2 = mp_obj_list_append(changes, lvgl_mvu_diff_ChildChange_make_new(&lvgl_mvu_diff_ChildChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("insert", 6), mp_obj_new_int(i), mp_obj_subscr(next_children, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_const_none}));
                (void)_tmp2;
            } else {
                if (mp_obj_is_true(lvgl_mvu_diff_can_reuse(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_obj_subscr(next_children, mp_obj_new_int(i), MP_OBJ_SENTINEL)))) {
                    mp_obj_t child_diff = lvgl_mvu_diff_diff_widgets(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_obj_subscr(next_children, mp_obj_new_int(i), MP_OBJ_SENTINEL));
                    mp_obj_t _tmp3 = ({ mp_obj_t __method[2]; mp_load_method(child_diff, MP_QSTR_is_empty, __method); mp_call_method_n_kw(0, 0, __method); });
                    if ((!mp_obj_is_true(_tmp3))) {
                        mp_obj_t _tmp4 = mp_obj_list_append(changes, lvgl_mvu_diff_ChildChange_make_new(&lvgl_mvu_diff_ChildChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("update", 6), mp_obj_new_int(i), mp_obj_subscr(next_children, mp_obj_new_int(i), MP_OBJ_SENTINEL), child_diff}));
                        (void)_tmp4;
                    }
                } else {
                    mp_obj_t _tmp5 = mp_obj_list_append(changes, lvgl_mvu_diff_ChildChange_make_new(&lvgl_mvu_diff_ChildChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("replace", 7), mp_obj_new_int(i), mp_obj_subscr(next_children, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_const_none}));
                    (void)_tmp5;
                }
            }
        }
        i += 1;
    }
    return changes;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_diff_diff_children_obj, lvgl_mvu_diff_diff_children);
static mp_obj_t lvgl_mvu_diff__events_changed(mp_obj_t prev_obj, mp_obj_t next_evts_obj) {
    mp_obj_t prev = prev_obj;
    mp_obj_t next_evts = next_evts_obj;

    if ((mp_obj_get_int(mp_obj_len(prev)) != mp_obj_get_int(mp_obj_len(next_evts)))) {
        return true ? mp_const_true : mp_const_false;
    }
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(prev)))) {
        if ((!mp_obj_equal(mp_obj_subscr(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_obj_new_int(0), MP_OBJ_SENTINEL), mp_obj_subscr(mp_obj_subscr(next_evts, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_obj_new_int(0), MP_OBJ_SENTINEL)))) {
            return true ? mp_const_true : mp_const_false;
        }
        if ((!mp_obj_equal(mp_obj_subscr(mp_obj_subscr(prev, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_obj_new_int(1), MP_OBJ_SENTINEL), mp_obj_subscr(mp_obj_subscr(next_evts, mp_obj_new_int(i), MP_OBJ_SENTINEL), mp_obj_new_int(1), MP_OBJ_SENTINEL)))) {
            return true ? mp_const_true : mp_const_false;
        }
        i += 1;
    }
    return false ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_diff__events_changed_obj, lvgl_mvu_diff__events_changed);
static mp_obj_t lvgl_mvu_diff_diff_widgets(mp_obj_t prev_obj, mp_obj_t next_w_obj) {
    mp_obj_t prev = prev_obj;
    mp_obj_t next_w = next_w_obj;

    if ((prev == mp_const_none)) {
        mp_obj_t scalar_changes = mp_obj_new_list(0, NULL);
        mp_obj_t a;
        mp_obj_iter_buf_t _tmp4;
        mp_obj_t _tmp3 = mp_getiter(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->scalar_attrs, &_tmp4);
        while ((a = mp_iternext(_tmp3)) != MP_OBJ_STOP_ITERATION) {
            mp_obj_t _tmp1 = mp_obj_list_append(scalar_changes, lvgl_mvu_diff_AttrChange_make_new(&lvgl_mvu_diff_AttrChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("added", 5), mp_obj_new_int(((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(a))->key), mp_const_none, ((lvgl_mvu_widget_ScalarAttr_obj_t *)MP_OBJ_TO_PTR(a))->value}));
            (void)_tmp1;
        }
        mp_obj_t child_changes = mp_obj_new_list(0, NULL);
        mp_int_t i = 0;
        mp_obj_t c;
        mp_obj_iter_buf_t _tmp6;
        mp_obj_t _tmp5 = mp_getiter(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->children, &_tmp6);
        while ((c = mp_iternext(_tmp5)) != MP_OBJ_STOP_ITERATION) {
            mp_obj_t _tmp2 = mp_obj_list_append(child_changes, lvgl_mvu_diff_ChildChange_make_new(&lvgl_mvu_diff_ChildChange_type, 4, 0, (const mp_obj_t[]){mp_obj_new_str("insert", 6), mp_obj_new_int(i), c, mp_const_none}));
            (void)_tmp2;
            i += 1;
        }
        bool has_events = (mp_obj_get_int(mp_obj_len(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->event_handlers)) > 0);
        return lvgl_mvu_diff_WidgetDiff_make_new(&lvgl_mvu_diff_WidgetDiff_type, 3, 0, (const mp_obj_t[]){scalar_changes, child_changes, mp_obj_new_bool(has_events)});
    }
    return lvgl_mvu_diff_WidgetDiff_make_new(&lvgl_mvu_diff_WidgetDiff_type, 3, 0, (const mp_obj_t[]){lvgl_mvu_diff_diff_scalars(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(prev))->scalar_attrs, ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->scalar_attrs), lvgl_mvu_diff_diff_children(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(prev))->children, ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->children), lvgl_mvu_diff__events_changed(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(prev))->event_handlers, ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(next_w))->event_handlers)});
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_diff_diff_widgets_obj, lvgl_mvu_diff_diff_widgets);
static bool lvgl_mvu_diff_WidgetDiff_is_empty_native(lvgl_mvu_diff_WidgetDiff_obj_t *self) {
    return (((mp_obj_get_int(mp_obj_len(self->scalar_changes)) == 0) && (mp_obj_get_int(mp_obj_len(self->child_changes)) == 0)) && (!self->event_changes));
}

static mp_obj_t lvgl_mvu_diff_WidgetDiff_is_empty_mp(mp_obj_t self_in) {
    lvgl_mvu_diff_WidgetDiff_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return lvgl_mvu_diff_WidgetDiff_is_empty_native(self) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_diff_WidgetDiff_is_empty_obj, lvgl_mvu_diff_WidgetDiff_is_empty_mp);

static mp_obj_t lvgl_mvu_program_Effect___init___mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_program_Effect_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t kind = mp_obj_get_int(arg0_obj);
    mp_obj_t data = arg1_obj;
    self->kind = kind;
    self->data = data;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_program_Effect___init___obj, lvgl_mvu_program_Effect___init___mp);

static mp_obj_t lvgl_mvu_program_Cmd_batch_native(mp_obj_t cmds) {
    mp_obj_t result = lvgl_mvu_program_Cmd_make_new(&lvgl_mvu_program_Cmd_type, 0, 0, (const mp_obj_t[]){});
    mp_obj_t effects = mp_obj_new_list(0, NULL);
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(cmds)))) {
        mp_int_t j = 0;
        mp_obj_t _tmp1 = ((lvgl_mvu_program_Cmd_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(cmds, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->effects;
        while ((j < mp_obj_get_int(mp_obj_len(_tmp1)))) {
            mp_obj_t _tmp2 = ((lvgl_mvu_program_Cmd_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(cmds, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->effects;
            mp_obj_t _tmp3 = mp_obj_list_append(effects, mp_obj_subscr(_tmp2, mp_obj_new_int(j), MP_OBJ_SENTINEL));
            (void)_tmp3;
            j += 1;
        }
        i += 1;
    }
    mp_store_attr(result, MP_QSTR_effects, effects);
    return result;
}

static mp_obj_t lvgl_mvu_program_Cmd_batch_mp(mp_obj_t arg0_obj) {
    mp_obj_t cmds = arg0_obj;
    return lvgl_mvu_program_Cmd_batch_native(cmds);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_program_Cmd_batch_fun_obj, lvgl_mvu_program_Cmd_batch_mp);

static mp_obj_t lvgl_mvu_program_Cmd_none_native(void) {
    return lvgl_mvu_program_Cmd_make_new(&lvgl_mvu_program_Cmd_type, 0, 0, (const mp_obj_t[]){});
}

static mp_obj_t lvgl_mvu_program_Cmd_none_mp(void) {
    return lvgl_mvu_program_Cmd_none_native();
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_mvu_program_Cmd_none_fun_obj, lvgl_mvu_program_Cmd_none_mp);

static mp_obj_t lvgl_mvu_program_Cmd_of_effect_native(mp_obj_t fn) {
    mp_obj_t cmd = lvgl_mvu_program_Cmd_make_new(&lvgl_mvu_program_Cmd_type, 0, 0, (const mp_obj_t[]){});
    mp_obj_t _tmp1_items[] = {lvgl_mvu_program_Effect_make_new(&lvgl_mvu_program_Effect_type, 2, 0, (const mp_obj_t[]){mp_obj_new_int(1), fn})};
    mp_obj_t _tmp1 = mp_obj_new_list(1, _tmp1_items);
    mp_store_attr(cmd, MP_QSTR_effects, _tmp1);
    return cmd;
}

static mp_obj_t lvgl_mvu_program_Cmd_of_effect_mp(mp_obj_t arg0_obj) {
    mp_obj_t fn = arg0_obj;
    return lvgl_mvu_program_Cmd_of_effect_native(fn);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_program_Cmd_of_effect_fun_obj, lvgl_mvu_program_Cmd_of_effect_mp);

static mp_obj_t lvgl_mvu_program_Cmd_of_msg_native(mp_obj_t msg) {
    mp_obj_t cmd = lvgl_mvu_program_Cmd_make_new(&lvgl_mvu_program_Cmd_type, 0, 0, (const mp_obj_t[]){});
    mp_obj_t _tmp1_items[] = {lvgl_mvu_program_Effect_make_new(&lvgl_mvu_program_Effect_type, 2, 0, (const mp_obj_t[]){mp_obj_new_int(0), msg})};
    mp_obj_t _tmp1 = mp_obj_new_list(1, _tmp1_items);
    mp_store_attr(cmd, MP_QSTR_effects, _tmp1);
    return cmd;
}

static mp_obj_t lvgl_mvu_program_Cmd_of_msg_mp(mp_obj_t arg0_obj) {
    mp_obj_t msg = arg0_obj;
    return lvgl_mvu_program_Cmd_of_msg_native(msg);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_program_Cmd_of_msg_fun_obj, lvgl_mvu_program_Cmd_of_msg_mp);

static mp_obj_t lvgl_mvu_program_Cmd___init___mp(mp_obj_t self_in) {
    lvgl_mvu_program_Cmd_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->effects = mp_obj_new_list(0, NULL);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_program_Cmd___init___obj, lvgl_mvu_program_Cmd___init___mp);

static mp_obj_t lvgl_mvu_program_SubDef___init___mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_program_SubDef_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_int_t kind = mp_obj_get_int(args[1]);
    mp_obj_t key = args[2];
    mp_obj_t data = args[3];
    self->kind = kind;
    self->key = key;
    self->data = data;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_program_SubDef___init___obj, 4, 4, lvgl_mvu_program_SubDef___init___mp);

static mp_obj_t lvgl_mvu_program_Sub_batch_native(mp_obj_t subs) {
    mp_obj_t result = lvgl_mvu_program_Sub_make_new(&lvgl_mvu_program_Sub_type, 0, 0, (const mp_obj_t[]){});
    mp_obj_t defs = mp_obj_new_list(0, NULL);
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(subs)))) {
        mp_int_t j = 0;
        mp_obj_t _tmp1 = ((lvgl_mvu_program_Sub_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(subs, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->defs;
        while ((j < mp_obj_get_int(mp_obj_len(_tmp1)))) {
            mp_obj_t _tmp2 = ((lvgl_mvu_program_Sub_obj_t *)MP_OBJ_TO_PTR(mp_obj_subscr(subs, mp_obj_new_int(i), MP_OBJ_SENTINEL)))->defs;
            mp_obj_t _tmp3 = mp_obj_list_append(defs, mp_obj_subscr(_tmp2, mp_obj_new_int(j), MP_OBJ_SENTINEL));
            (void)_tmp3;
            j += 1;
        }
        i += 1;
    }
    mp_store_attr(result, MP_QSTR_defs, defs);
    return result;
}

static mp_obj_t lvgl_mvu_program_Sub_batch_mp(mp_obj_t arg0_obj) {
    mp_obj_t subs = arg0_obj;
    return lvgl_mvu_program_Sub_batch_native(subs);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_program_Sub_batch_fun_obj, lvgl_mvu_program_Sub_batch_mp);

static mp_obj_t lvgl_mvu_program_Sub_none_native(void) {
    return lvgl_mvu_program_Sub_make_new(&lvgl_mvu_program_Sub_type, 0, 0, (const mp_obj_t[]){});
}

static mp_obj_t lvgl_mvu_program_Sub_none_mp(void) {
    return lvgl_mvu_program_Sub_none_native();
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_mvu_program_Sub_none_fun_obj, lvgl_mvu_program_Sub_none_mp);

static mp_obj_t lvgl_mvu_program_Sub_timer_native(mp_int_t interval_ms, mp_obj_t msg) {
    mp_obj_t sub = lvgl_mvu_program_Sub_make_new(&lvgl_mvu_program_Sub_type, 0, 0, (const mp_obj_t[]){});
    mp_obj_t key = mp_binary_op(MP_BINARY_OP_ADD, mp_obj_new_str("timer_", 6), mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_str), mp_obj_new_int(interval_ms)));
    mp_obj_t _tmp1_items[] = {mp_obj_new_int(interval_ms), msg};
    mp_obj_t _tmp1 = mp_obj_new_tuple(2, _tmp1_items);
    mp_obj_t _tmp2_items[] = {lvgl_mvu_program_SubDef_make_new(&lvgl_mvu_program_SubDef_type, 3, 0, (const mp_obj_t[]){mp_obj_new_int(0), key, _tmp1})};
    mp_obj_t _tmp2 = mp_obj_new_list(1, _tmp2_items);
    mp_store_attr(sub, MP_QSTR_defs, _tmp2);
    return sub;
}

static mp_obj_t lvgl_mvu_program_Sub_timer_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    mp_int_t interval_ms = mp_obj_get_int(arg0_obj);
    mp_obj_t msg = arg1_obj;
    return lvgl_mvu_program_Sub_timer_native(interval_ms, msg);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_program_Sub_timer_fun_obj, lvgl_mvu_program_Sub_timer_mp);

static mp_obj_t lvgl_mvu_program_Sub___init___mp(mp_obj_t self_in) {
    lvgl_mvu_program_Sub_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->defs = mp_obj_new_list(0, NULL);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_program_Sub___init___obj, lvgl_mvu_program_Sub___init___mp);

static mp_obj_t lvgl_mvu_program_Program___init___mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_program_Program_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t init_fn = args[1];
    mp_obj_t update_fn = args[2];
    mp_obj_t view_fn = args[3];
    mp_obj_t subscribe_fn = (n_args > 4) ? args[4] : mp_const_none;
    self->init_fn = init_fn;
    self->update_fn = update_fn;
    self->view_fn = view_fn;
    self->subscribe_fn = subscribe_fn;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_program_Program___init___obj, 4, 5, lvgl_mvu_program_Program___init___mp);

static mp_obj_t lvgl_mvu_reconciler_Reconciler__create_node_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t widget, mp_obj_t parent_lv_obj) {
    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(self->_factories, MP_QSTR_get), mp_obj_new_int(((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(widget))->key));
    mp_obj_t factory = _tmp1;
    if ((factory == mp_const_none)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("%s"), mp_obj_str_get_str(mp_const_none));
    }
    mp_obj_t lv_obj = mp_call_function_1(factory, parent_lv_obj);
    mp_obj_t node = lvgl_mvu_viewnode_ViewNode_make_new(&lvgl_mvu_viewnode_ViewNode_type, 3, 0, (const mp_obj_t[]){lv_obj, widget, self->_attr_registry});
    mp_obj_t scalar_attrs = ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(widget))->scalar_attrs;
    mp_int_t i = 0;
    while ((i < mp_obj_get_int(mp_obj_len(scalar_attrs)))) {
        mp_obj_t attr = mp_obj_subscr(scalar_attrs, mp_obj_new_int(i), MP_OBJ_SENTINEL);
        mp_obj_t _tmp2 = mp_call_function_1(mp_load_attr(self->_attr_registry, MP_QSTR_get), mp_load_attr(attr, MP_QSTR_key));
        mp_obj_t attr_def = _tmp2;
        if ((attr_def != mp_const_none)) {
            mp_obj_t _tmp3 = ({ mp_obj_t __method[4]; mp_load_method(attr_def, MP_QSTR_apply_fn, __method); __method[2] = lv_obj; __method[3] = mp_load_attr(attr, MP_QSTR_value); mp_call_method_n_kw(2, 0, __method); });
            (void)_tmp3;
        }
        i += 1;
    }
    mp_obj_t children = ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(widget))->children;
    mp_int_t j = 0;
    while ((j < mp_obj_get_int(mp_obj_len(children)))) {
        mp_obj_t child_widget = mp_obj_subscr(children, mp_obj_new_int(j), MP_OBJ_SENTINEL);
        mp_obj_t child_node = lvgl_mvu_reconciler_Reconciler__create_node_native(self, child_widget, lv_obj);
        mp_obj_t _tmp4 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_add_child, __method); __method[2] = child_node; mp_call_method_n_kw(1, 0, __method); });
        (void)_tmp4;
        j += 1;
    }
    (void)lvgl_mvu_reconciler_Reconciler__register_handlers_native(self, node, widget);
    return node;
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler__create_node_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t widget = arg0_obj;
    mp_obj_t parent_lv_obj = arg1_obj;
    return lvgl_mvu_reconciler_Reconciler__create_node_native(self, widget, parent_lv_obj);
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_reconciler_Reconciler__create_node_obj, lvgl_mvu_reconciler_Reconciler__create_node_mp);

static void lvgl_mvu_reconciler_Reconciler__reconcile_children_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget, mp_obj_t changes) {
    mp_obj_t removes = mp_obj_new_list(0, NULL);
    mp_obj_t inserts = mp_obj_new_list(0, NULL);
    mp_obj_t updates = mp_obj_new_list(0, NULL);
    mp_obj_t replaces = mp_obj_new_list(0, NULL);
    mp_obj_t old_child = mp_const_none;
    mp_obj_t new_child = mp_const_none;
    mp_obj_t change;
    mp_obj_iter_buf_t _tmp15;
    mp_obj_t _tmp14 = mp_getiter(changes, &_tmp15);
    while ((change = mp_iternext(_tmp14)) != MP_OBJ_STOP_ITERATION) {
        if (mp_obj_equal(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->kind, mp_obj_new_str("remove", 6))) {
            mp_obj_t _tmp1 = mp_obj_list_append(removes, change);
            (void)_tmp1;
        } else {
            if (mp_obj_equal(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->kind, mp_obj_new_str("insert", 6))) {
                mp_obj_t _tmp2 = mp_obj_list_append(inserts, change);
                (void)_tmp2;
            } else {
                if (mp_obj_equal(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->kind, mp_obj_new_str("update", 6))) {
                    mp_obj_t _tmp3 = mp_obj_list_append(updates, change);
                    (void)_tmp3;
                } else {
                    if (mp_obj_equal(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->kind, mp_obj_new_str("replace", 7))) {
                        mp_obj_t _tmp4 = mp_obj_list_append(replaces, change);
                        (void)_tmp4;
                    }
                }
            }
        }
    }
    mp_obj_iter_buf_t _tmp17;
    mp_obj_t _tmp16 = mp_getiter(updates, &_tmp17);
    while ((change = mp_iternext(_tmp16)) != MP_OBJ_STOP_ITERATION) {
        if (((((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->diff != mp_const_none) && (((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget != mp_const_none))) {
            mp_obj_t _tmp5 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_get_child, __method); __method[2] = mp_obj_new_int(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->index); mp_call_method_n_kw(1, 0, __method); });
            mp_obj_t child_node = _tmp5;
            if ((child_node != mp_const_none)) {
                mp_obj_t _tmp6 = ({ mp_obj_t __method[3]; mp_load_method(child_node, MP_QSTR_apply_diff, __method); __method[2] = ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->diff; mp_call_method_n_kw(1, 0, __method); });
                (void)_tmp6;
                (void)lvgl_mvu_reconciler_Reconciler__reconcile_children_native(self, child_node, ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget, mp_const_none);
                if (mp_obj_is_true(mp_const_none)) {
                    (void)lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native(self, child_node, ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget);
                }
                mp_obj_t _tmp7 = ({ mp_obj_t __method[3]; mp_load_method(child_node, MP_QSTR_update_widget, __method); __method[2] = ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget; mp_call_method_n_kw(1, 0, __method); });
                (void)_tmp7;
            }
        }
    }
    mp_obj_iter_buf_t _tmp19;
    mp_obj_t _tmp18 = mp_getiter(replaces, &_tmp19);
    while ((change = mp_iternext(_tmp18)) != MP_OBJ_STOP_ITERATION) {
        if ((((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget != mp_const_none)) {
            mp_obj_t _tmp8 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_remove_child, __method); __method[2] = mp_obj_new_int(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->index); mp_call_method_n_kw(1, 0, __method); });
            old_child = _tmp8;
            if ((old_child != mp_const_none)) {
                mp_obj_t _tmp9 = ({ mp_obj_t __method[3]; mp_load_method(old_child, MP_QSTR_dispose, __method); __method[2] = self->_delete_fn; mp_call_method_n_kw(1, 0, __method); });
                (void)_tmp9;
            }
            new_child = lvgl_mvu_reconciler_Reconciler__create_node_native(self, ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget, ((lvgl_mvu_viewnode_ViewNode_obj_t *)MP_OBJ_TO_PTR(node))->lv_obj);
            mp_obj_t _tmp10 = ({ mp_obj_t __method[4]; mp_load_method(node, MP_QSTR_add_child, __method); __method[2] = new_child; __method[3] = mp_obj_new_int(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->index); mp_call_method_n_kw(2, 0, __method); });
            (void)_tmp10;
        }
    }
    mp_obj_t removes_sorted = mp_call_function_n_kw(mp_load_global(MP_QSTR_sorted) /* mp_builtin_sorted_obj */, 1, 2, (const mp_obj_t[]){removes, MP_OBJ_NEW_QSTR(MP_QSTR_key), mp_const_none, MP_OBJ_NEW_QSTR(MP_QSTR_reverse), mp_obj_new_bool(true)});
    mp_obj_iter_buf_t _tmp21;
    mp_obj_t _tmp20 = mp_getiter(removes_sorted, &_tmp21);
    while ((change = mp_iternext(_tmp20)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_t _tmp11 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_remove_child, __method); __method[2] = mp_obj_new_int(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->index); mp_call_method_n_kw(1, 0, __method); });
        old_child = _tmp11;
        if ((old_child != mp_const_none)) {
            mp_obj_t _tmp12 = ({ mp_obj_t __method[3]; mp_load_method(old_child, MP_QSTR_dispose, __method); __method[2] = self->_delete_fn; mp_call_method_n_kw(1, 0, __method); });
            (void)_tmp12;
        }
    }
    mp_obj_t inserts_sorted = mp_call_function_n_kw(mp_load_global(MP_QSTR_sorted) /* mp_builtin_sorted_obj */, 1, 1, (const mp_obj_t[]){inserts, MP_OBJ_NEW_QSTR(MP_QSTR_key), mp_const_none});
    mp_obj_iter_buf_t _tmp23;
    mp_obj_t _tmp22 = mp_getiter(inserts_sorted, &_tmp23);
    while ((change = mp_iternext(_tmp22)) != MP_OBJ_STOP_ITERATION) {
        if ((((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget != mp_const_none)) {
            new_child = lvgl_mvu_reconciler_Reconciler__create_node_native(self, ((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->widget, ((lvgl_mvu_viewnode_ViewNode_obj_t *)MP_OBJ_TO_PTR(node))->lv_obj);
            mp_obj_t _tmp13 = ({ mp_obj_t __method[4]; mp_load_method(node, MP_QSTR_add_child, __method); __method[2] = new_child; __method[3] = mp_obj_new_int(((lvgl_mvu_diff_ChildChange_obj_t *)MP_OBJ_TO_PTR(change))->index); mp_call_method_n_kw(2, 0, __method); });
            (void)_tmp13;
        }
    }
    return;
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler__reconcile_children_mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t node = args[1];
    mp_obj_t widget = args[2];
    mp_obj_t changes = args[3];
    lvgl_mvu_reconciler_Reconciler__reconcile_children_native(self, node, widget, changes);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_reconciler_Reconciler__reconcile_children_obj, 4, 4, lvgl_mvu_reconciler_Reconciler__reconcile_children_mp);

static void lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget) {
    if ((self->_event_binder == mp_const_none)) {
        mp_obj_t _tmp1 = ({ mp_obj_t __method[2]; mp_load_method(node, MP_QSTR_clear_handlers, __method); mp_call_method_n_kw(0, 0, __method); });
        (void)_tmp1;
        return;
    }
    mp_obj_t _tmp2 = ({ mp_obj_t __method[2]; mp_load_method(node, MP_QSTR_clear_handlers, __method); mp_call_method_n_kw(0, 0, __method); });
    mp_obj_t old_handlers = _tmp2;
    mp_obj_t _tmp4 = mp_call_function_0(mp_load_attr(old_handlers, MP_QSTR_items));
    mp_obj_t _item_2;
    mp_obj_iter_buf_t _tmp7;
    mp_obj_t _tmp6 = mp_getiter(_tmp4, &_tmp7);
    while ((_item_2 = mp_iternext(_tmp6)) != MP_OBJ_STOP_ITERATION) {
        mp_obj_t _tmp8 = _item_2;
        mp_obj_t event_type = mp_obj_subscr(_tmp8, mp_obj_new_int(0), MP_OBJ_SENTINEL);
        mp_obj_t handler = mp_obj_subscr(_tmp8, mp_obj_new_int(1), MP_OBJ_SENTINEL);
        mp_obj_t _tmp5 = ({ mp_obj_t __method[5]; mp_load_method(self->_event_binder, MP_QSTR_unbind, __method); __method[2] = ((lvgl_mvu_viewnode_ViewNode_obj_t *)MP_OBJ_TO_PTR(node))->lv_obj; __method[3] = event_type; __method[4] = handler; mp_call_method_n_kw(3, 0, __method); });
        (void)_tmp5;
    }
    (void)lvgl_mvu_reconciler_Reconciler__register_handlers_native(self, node, widget);
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler__reconcile_handlers_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t node = arg0_obj;
    mp_obj_t widget = arg1_obj;
    lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native(self, node, widget);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_reconciler_Reconciler__reconcile_handlers_obj, lvgl_mvu_reconciler_Reconciler__reconcile_handlers_mp);

static void lvgl_mvu_reconciler_Reconciler__register_handlers_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget) {
    if ((self->_event_binder == mp_const_none)) {
        return;
    }
    mp_obj_t event_handlers = ((lvgl_mvu_widget_Widget_obj_t *)MP_OBJ_TO_PTR(widget))->event_handlers;
    mp_int_t eh_idx = 0;
    while ((eh_idx < mp_obj_get_int(mp_obj_len(event_handlers)))) {
        mp_obj_t event_type_msg = mp_obj_subscr(event_handlers, mp_obj_new_int(eh_idx), MP_OBJ_SENTINEL);
        mp_int_t event_type = mp_obj_get_int(mp_obj_subscr(event_type_msg, mp_obj_new_int(0), MP_OBJ_SENTINEL));
        mp_obj_t msg = mp_obj_subscr(event_type_msg, mp_obj_new_int(1), MP_OBJ_SENTINEL);
        mp_obj_t _tmp1 = ({ mp_obj_t __method[5]; mp_load_method(self->_event_binder, MP_QSTR_bind, __method); __method[2] = ((lvgl_mvu_viewnode_ViewNode_obj_t *)MP_OBJ_TO_PTR(node))->lv_obj; __method[3] = mp_obj_new_int(event_type); __method[4] = msg; mp_call_method_n_kw(3, 0, __method); });
        mp_obj_t handler = _tmp1;
        mp_obj_t _tmp2 = ({ mp_obj_t __method[4]; mp_load_method(node, MP_QSTR_register_handler, __method); __method[2] = mp_obj_new_int(event_type); __method[3] = handler; mp_call_method_n_kw(2, 0, __method); });
        (void)_tmp2;
        eh_idx += 1;
    }
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler__register_handlers_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t node = arg0_obj;
    mp_obj_t widget = arg1_obj;
    lvgl_mvu_reconciler_Reconciler__register_handlers_native(self, node, widget);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_reconciler_Reconciler__register_handlers_obj, lvgl_mvu_reconciler_Reconciler__register_handlers_mp);

static void lvgl_mvu_reconciler_Reconciler_dispose_tree_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_dispose, __method); __method[2] = self->_delete_fn; mp_call_method_n_kw(1, 0, __method); });
    (void)_tmp1;
    return;
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler_dispose_tree_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t node = arg0_obj;
    lvgl_mvu_reconciler_Reconciler_dispose_tree_native(self, node);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_reconciler_Reconciler_dispose_tree_obj, lvgl_mvu_reconciler_Reconciler_dispose_tree_mp);

static mp_obj_t lvgl_mvu_reconciler_Reconciler_reconcile_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t node, mp_obj_t widget, mp_obj_t parent_lv_obj) {
    if ((node == mp_const_none)) {
        return lvgl_mvu_reconciler_Reconciler__create_node_native(self, widget, parent_lv_obj);
    }
    if ((!mp_obj_is_true(lvgl_mvu_diff_can_reuse(((lvgl_mvu_viewnode_ViewNode_obj_t *)MP_OBJ_TO_PTR(node))->widget, widget)))) {
        mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_dispose, __method); __method[2] = self->_delete_fn; mp_call_method_n_kw(1, 0, __method); });
        (void)_tmp1;
        return lvgl_mvu_reconciler_Reconciler__create_node_native(self, widget, parent_lv_obj);
    }
    mp_obj_t diff = lvgl_mvu_diff_diff_widgets(((lvgl_mvu_viewnode_ViewNode_obj_t *)MP_OBJ_TO_PTR(node))->widget, widget);
    mp_obj_t _tmp2 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_apply_diff, __method); __method[2] = diff; mp_call_method_n_kw(1, 0, __method); });
    (void)_tmp2;
    (void)lvgl_mvu_reconciler_Reconciler__reconcile_children_native(self, node, widget, ((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(diff))->child_changes);
    if (((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(diff))->event_changes) {
        (void)lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native(self, node, widget);
    }
    mp_obj_t _tmp3 = ({ mp_obj_t __method[3]; mp_load_method(node, MP_QSTR_update_widget, __method); __method[2] = widget; mp_call_method_n_kw(1, 0, __method); });
    (void)_tmp3;
    return node;
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler_reconcile_mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t node = args[1];
    mp_obj_t widget = args[2];
    mp_obj_t parent_lv_obj = (n_args > 3) ? args[3] : mp_const_none;
    return lvgl_mvu_reconciler_Reconciler_reconcile_native(self, node, widget, parent_lv_obj);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_reconciler_Reconciler_reconcile_obj, 3, 4, lvgl_mvu_reconciler_Reconciler_reconcile_mp);

static void lvgl_mvu_reconciler_Reconciler_register_factory_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_int_t widget_key, mp_obj_t factory) {
    mp_obj_subscr(self->_factories, mp_obj_new_int(widget_key), factory);
    return;
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler_register_factory_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t widget_key = mp_obj_get_int(arg0_obj);
    mp_obj_t factory = arg1_obj;
    lvgl_mvu_reconciler_Reconciler_register_factory_native(self, widget_key, factory);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_reconciler_Reconciler_register_factory_obj, lvgl_mvu_reconciler_Reconciler_register_factory_mp);

static void lvgl_mvu_reconciler_Reconciler_set_delete_fn_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t delete_fn) {
    self->_delete_fn = delete_fn;
    return;
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler_set_delete_fn_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t delete_fn = arg0_obj;
    lvgl_mvu_reconciler_Reconciler_set_delete_fn_native(self, delete_fn);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_reconciler_Reconciler_set_delete_fn_obj, lvgl_mvu_reconciler_Reconciler_set_delete_fn_mp);

static void lvgl_mvu_reconciler_Reconciler_set_event_binder_native(lvgl_mvu_reconciler_Reconciler_obj_t *self, mp_obj_t binder) {
    self->_event_binder = binder;
    return;
}

static mp_obj_t lvgl_mvu_reconciler_Reconciler_set_event_binder_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t binder = arg0_obj;
    lvgl_mvu_reconciler_Reconciler_set_event_binder_native(self, binder);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_reconciler_Reconciler_set_event_binder_obj, lvgl_mvu_reconciler_Reconciler_set_event_binder_mp);

static mp_obj_t lvgl_mvu_reconciler_Reconciler___init___mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t attr_registry = arg0_obj;
    self->_factories = mp_obj_new_dict(0);
    self->_delete_fn = mp_const_none;
    self->_event_binder = mp_const_none;
    self->_attr_registry = attr_registry;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_reconciler_Reconciler___init___obj, lvgl_mvu_reconciler_Reconciler___init___mp);

static void lvgl_mvu_viewnode_ViewNode_add_child_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t child, mp_int_t index) {
    if (((index < 0) || (index >= mp_obj_get_int(mp_obj_len(self->children))))) {
        mp_obj_t _tmp1 = mp_obj_list_append(self->children, child);
        (void)_tmp1;
    } else {
        mp_obj_t _tmp2 = mp_call_function_n_kw(mp_load_attr(self->children, MP_QSTR_insert), 2, 0, (mp_obj_t[]){mp_obj_new_int(index), child});
        (void)_tmp2;
    }
    return;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_add_child_mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t child = args[1];
    mp_int_t index = (n_args > 2) ? mp_obj_get_int(args[2]) : -1;
    lvgl_mvu_viewnode_ViewNode_add_child_native(self, child, index);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_viewnode_ViewNode_add_child_obj, 2, 3, lvgl_mvu_viewnode_ViewNode_add_child_mp);

static void lvgl_mvu_viewnode_ViewNode_apply_diff_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t diff) {
    if (self->_disposed) {
        return;
    }
    mp_obj_t change;
    mp_obj_iter_buf_t _tmp2;
    mp_obj_t _tmp1 = mp_getiter(((lvgl_mvu_diff_WidgetDiff_obj_t *)MP_OBJ_TO_PTR(diff))->scalar_changes, &_tmp2);
    while ((change = mp_iternext(_tmp1)) != MP_OBJ_STOP_ITERATION) {
        (void)lvgl_mvu_viewnode_ViewNode_apply_scalar_change_native(self, change);
    }
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_apply_diff_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t diff = arg0_obj;
    lvgl_mvu_viewnode_ViewNode_apply_diff_native(self, diff);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_viewnode_ViewNode_apply_diff_obj, lvgl_mvu_viewnode_ViewNode_apply_diff_mp);

static void lvgl_mvu_viewnode_ViewNode_apply_scalar_change_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t change) {
    if (self->_disposed) {
        return;
    }
    mp_obj_t _tmp1 = mp_call_function_1(mp_load_attr(self->_attr_registry, MP_QSTR_get), mp_obj_new_int(((lvgl_mvu_diff_AttrChange_obj_t *)MP_OBJ_TO_PTR(change))->key));
    mp_obj_t attr_def = _tmp1;
    if ((attr_def == mp_const_none)) {
        return;
    }
    mp_obj_t kind = ((lvgl_mvu_diff_AttrChange_obj_t *)MP_OBJ_TO_PTR(change))->kind;
    if (mp_obj_equal(kind, mp_obj_new_str("removed", 7))) {
        mp_obj_t _tmp2 = ({ mp_obj_t __method[4]; mp_load_method(attr_def, MP_QSTR_apply_fn, __method); __method[2] = self->lv_obj; __method[3] = ((lvgl_mvu_attrs_AttrDef_obj_t *)MP_OBJ_TO_PTR(attr_def))->default_val; mp_call_method_n_kw(2, 0, __method); });
        (void)_tmp2;
    } else {
        if ((mp_obj_equal(kind, mp_obj_new_str("added", 5)) || mp_obj_equal(kind, mp_obj_new_str("updated", 7)))) {
            mp_obj_t _tmp3 = ({ mp_obj_t __method[4]; mp_load_method(attr_def, MP_QSTR_apply_fn, __method); __method[2] = self->lv_obj; __method[3] = ((lvgl_mvu_diff_AttrChange_obj_t *)MP_OBJ_TO_PTR(change))->new_value; mp_call_method_n_kw(2, 0, __method); });
            (void)_tmp3;
        }
    }
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_apply_scalar_change_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t change = arg0_obj;
    lvgl_mvu_viewnode_ViewNode_apply_scalar_change_native(self, change);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_viewnode_ViewNode_apply_scalar_change_obj, lvgl_mvu_viewnode_ViewNode_apply_scalar_change_mp);

static mp_int_t lvgl_mvu_viewnode_ViewNode_child_count_native(lvgl_mvu_viewnode_ViewNode_obj_t *self) {
    return mp_obj_get_int(mp_obj_len(self->children));
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_child_count_mp(mp_obj_t self_in) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(lvgl_mvu_viewnode_ViewNode_child_count_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_viewnode_ViewNode_child_count_obj, lvgl_mvu_viewnode_ViewNode_child_count_mp);

static mp_obj_t lvgl_mvu_viewnode_ViewNode_clear_handlers_native(lvgl_mvu_viewnode_ViewNode_obj_t *self) {
    mp_obj_t old_handlers = self->handlers;
    self->handlers = mp_obj_new_dict(0);
    return old_handlers;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_clear_handlers_mp(mp_obj_t self_in) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return lvgl_mvu_viewnode_ViewNode_clear_handlers_native(self);
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_viewnode_ViewNode_clear_handlers_obj, lvgl_mvu_viewnode_ViewNode_clear_handlers_mp);

static void lvgl_mvu_viewnode_ViewNode_dispose_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t delete_fn) {
    if (self->_disposed) {
        return;
    }
    mp_int_t child_count = mp_obj_get_int(mp_obj_len(self->children));
    mp_int_t idx = 0;
    while ((idx < child_count)) {
        mp_obj_t child_node = mp_obj_subscr(self->children, mp_obj_new_int(idx), MP_OBJ_SENTINEL);
        mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(child_node, MP_QSTR_dispose, __method); __method[2] = delete_fn; mp_call_method_n_kw(1, 0, __method); });
        (void)_tmp1;
        idx += 1;
    }
    self->children = mp_obj_new_list(0, NULL);
    self->handlers = mp_obj_new_dict(0);
    if ((delete_fn != mp_const_none)) {
        (void)mp_call_function_1(delete_fn, self->lv_obj);
    }
    self->_disposed = true;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_dispose_mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t delete_fn = (n_args > 1) ? args[1] : mp_const_none;
    lvgl_mvu_viewnode_ViewNode_dispose_native(self, delete_fn);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_viewnode_ViewNode_dispose_obj, 1, 2, lvgl_mvu_viewnode_ViewNode_dispose_mp);

static mp_obj_t lvgl_mvu_viewnode_ViewNode_get_child_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t index) {
    if (((0 <= index) && (index < mp_obj_get_int(mp_obj_len(self->children))))) {
        return mp_obj_subscr(self->children, mp_obj_new_int(index), MP_OBJ_SENTINEL);
    }
    return mp_const_none;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_get_child_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t index = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_viewnode_ViewNode_get_child_native(self, index);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_viewnode_ViewNode_get_child_obj, lvgl_mvu_viewnode_ViewNode_get_child_mp);

static bool lvgl_mvu_viewnode_ViewNode_is_disposed_native(lvgl_mvu_viewnode_ViewNode_obj_t *self) {
    return self->_disposed;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_is_disposed_mp(mp_obj_t self_in) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return lvgl_mvu_viewnode_ViewNode_is_disposed_native(self) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_mvu_viewnode_ViewNode_is_disposed_obj, lvgl_mvu_viewnode_ViewNode_is_disposed_mp);

static void lvgl_mvu_viewnode_ViewNode_register_handler_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t event_type, mp_obj_t handler) {
    mp_obj_subscr(self->handlers, mp_obj_new_int(event_type), handler);
    return;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_register_handler_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t event_type = mp_obj_get_int(arg0_obj);
    mp_obj_t handler = arg1_obj;
    lvgl_mvu_viewnode_ViewNode_register_handler_native(self, event_type, handler);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(lvgl_mvu_viewnode_ViewNode_register_handler_obj, lvgl_mvu_viewnode_ViewNode_register_handler_mp);

static mp_obj_t lvgl_mvu_viewnode_ViewNode_remove_child_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t index) {
    if (((0 <= index) && (index < mp_obj_get_int(mp_obj_len(self->children))))) {
        mp_obj_t _tmp1 = ({ mp_obj_t __method[3]; mp_load_method(self->children, MP_QSTR_pop, __method); __method[2] = mp_obj_new_int(index); mp_call_method_n_kw(1, 0, __method); });
        return _tmp1;
    }
    return mp_const_none;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_remove_child_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t index = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_viewnode_ViewNode_remove_child_native(self, index);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_viewnode_ViewNode_remove_child_obj, lvgl_mvu_viewnode_ViewNode_remove_child_mp);

static mp_obj_t lvgl_mvu_viewnode_ViewNode_unregister_handler_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_int_t event_type) {
    mp_obj_t _tmp1 = ({ mp_obj_t __method[4]; mp_load_method(self->handlers, MP_QSTR_pop, __method); __method[2] = mp_obj_new_int(event_type); __method[3] = mp_const_none; mp_call_method_n_kw(2, 0, __method); });
    return _tmp1;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_unregister_handler_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t event_type = mp_obj_get_int(arg0_obj);
    return lvgl_mvu_viewnode_ViewNode_unregister_handler_native(self, event_type);
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_viewnode_ViewNode_unregister_handler_obj, lvgl_mvu_viewnode_ViewNode_unregister_handler_mp);

static void lvgl_mvu_viewnode_ViewNode_update_widget_native(lvgl_mvu_viewnode_ViewNode_obj_t *self, mp_obj_t widget) {
    self->widget = widget;
    return;
}

static mp_obj_t lvgl_mvu_viewnode_ViewNode_update_widget_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_obj_t widget = arg0_obj;
    lvgl_mvu_viewnode_ViewNode_update_widget_native(self, widget);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(lvgl_mvu_viewnode_ViewNode_update_widget_obj, lvgl_mvu_viewnode_ViewNode_update_widget_mp);

static mp_obj_t lvgl_mvu_viewnode_ViewNode___init___mp(size_t n_args, const mp_obj_t *args) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    mp_obj_t lv_obj = args[1];
    mp_obj_t widget = args[2];
    mp_obj_t attr_registry = args[3];
    self->lv_obj = lv_obj;
    self->widget = widget;
    self->children = mp_obj_new_list(0, NULL);
    self->handlers = mp_obj_new_dict(0);
    self->_disposed = false;
    self->_attr_registry = attr_registry;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(lvgl_mvu_viewnode_ViewNode___init___obj, 4, 4, lvgl_mvu_viewnode_ViewNode___init___mp);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_app_App_field_t;

static const lvgl_mvu_app_App_field_t lvgl_mvu_app_App_fields[] = {
    { MP_QSTR_program, offsetof(lvgl_mvu_app_App_obj_t, program), 0 },
    { MP_QSTR_reconciler, offsetof(lvgl_mvu_app_App_obj_t, reconciler), 0 },
    { MP_QSTR_model, offsetof(lvgl_mvu_app_App_obj_t, model), 0 },
    { MP_QSTR_root_node, offsetof(lvgl_mvu_app_App_obj_t, root_node), 0 },
    { MP_QSTR__msg_queue, offsetof(lvgl_mvu_app_App_obj_t, _msg_queue), 0 },
    { MP_QSTR__root_lv_obj, offsetof(lvgl_mvu_app_App_obj_t, _root_lv_obj), 0 },
    { MP_QSTR__active_teardowns, offsetof(lvgl_mvu_app_App_obj_t, _active_teardowns), 0 },
    { MP_QSTR__sub_keys, offsetof(lvgl_mvu_app_App_obj_t, _sub_keys), 0 },
    { MP_QSTR__timer_factory, offsetof(lvgl_mvu_app_App_obj_t, _timer_factory), 0 },
    { MP_QSTR__disposed, offsetof(lvgl_mvu_app_App_obj_t, _disposed), 3 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_app_App_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_app_App_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_app_App_field_t *f = lvgl_mvu_app_App_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static const lvgl_mvu_app_App_vtable_t lvgl_mvu_app_App_vtable_inst = {
    .set_timer_factory = lvgl_mvu_app_App_set_timer_factory_native,
    .dispatch = lvgl_mvu_app_App_dispatch_native,
    .tick = lvgl_mvu_app_App_tick_native,
    .dispose = lvgl_mvu_app_App_dispose_native,
    .is_disposed = lvgl_mvu_app_App_is_disposed_native,
    .queue_length = lvgl_mvu_app_App_queue_length_native,
    ._execute_cmd = lvgl_mvu_app_App__execute_cmd_native,
    ._setup_subscriptions = lvgl_mvu_app_App__setup_subscriptions_native,
    ._teardown_subscriptions = lvgl_mvu_app_App__teardown_subscriptions_native,
    ._activate_sub = lvgl_mvu_app_App__activate_sub_native,
    ._activate_timer_sub = lvgl_mvu_app_App__activate_timer_sub_native,
    ._keys_match = lvgl_mvu_app_App__keys_match_native,
};

static mp_obj_t lvgl_mvu_app_App_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 3, false);

    lvgl_mvu_app_App_obj_t *self = mp_obj_malloc(lvgl_mvu_app_App_obj_t, type);
    self->vtable = &lvgl_mvu_app_App_vtable_inst;
    self->program = mp_const_none;
    self->reconciler = mp_const_none;
    self->model = mp_const_none;
    self->root_node = mp_const_none;
    self->_msg_queue = mp_const_none;
    self->_root_lv_obj = mp_const_none;
    self->_active_teardowns = mp_const_none;
    self->_sub_keys = mp_const_none;
    self->_timer_factory = mp_const_none;
    self->_disposed = false;

    mp_obj_t init_args[4];
    init_args[0] = MP_OBJ_FROM_PTR(self);
    init_args[1] = args[0];
    init_args[2] = args[1];
    init_args[3] = (n_args > 2) ? args[2] : mp_const_none;
    lvgl_mvu_app_App___init___mp(4, init_args);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t lvgl_mvu_app_App_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_set_timer_factory), MP_ROM_PTR(&lvgl_mvu_app_App_set_timer_factory_obj) },
    { MP_ROM_QSTR(MP_QSTR_dispatch), MP_ROM_PTR(&lvgl_mvu_app_App_dispatch_obj) },
    { MP_ROM_QSTR(MP_QSTR_tick), MP_ROM_PTR(&lvgl_mvu_app_App_tick_obj) },
    { MP_ROM_QSTR(MP_QSTR_dispose), MP_ROM_PTR(&lvgl_mvu_app_App_dispose_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_disposed), MP_ROM_PTR(&lvgl_mvu_app_App_is_disposed_obj) },
    { MP_ROM_QSTR(MP_QSTR_queue_length), MP_ROM_PTR(&lvgl_mvu_app_App_queue_length_obj) },
    { MP_ROM_QSTR(MP_QSTR__execute_cmd), MP_ROM_PTR(&lvgl_mvu_app_App__execute_cmd_obj) },
    { MP_ROM_QSTR(MP_QSTR__setup_subscriptions), MP_ROM_PTR(&lvgl_mvu_app_App__setup_subscriptions_obj) },
    { MP_ROM_QSTR(MP_QSTR__teardown_subscriptions), MP_ROM_PTR(&lvgl_mvu_app_App__teardown_subscriptions_obj) },
    { MP_ROM_QSTR(MP_QSTR__activate_sub), MP_ROM_PTR(&lvgl_mvu_app_App__activate_sub_obj) },
    { MP_ROM_QSTR(MP_QSTR__activate_timer_sub), MP_ROM_PTR(&lvgl_mvu_app_App__activate_timer_sub_obj) },
    { MP_ROM_QSTR(MP_QSTR__keys_match), MP_ROM_PTR(&lvgl_mvu_app_App__keys_match_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_app_App_locals_dict, lvgl_mvu_app_App_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_app_App_type,
    MP_QSTR_App,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_app_App_make_new,
    attr, lvgl_mvu_app_App_attr,
    locals_dict, &lvgl_mvu_app_App_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_attrs_AttrDef_field_t;

static const lvgl_mvu_attrs_AttrDef_field_t lvgl_mvu_attrs_AttrDef_fields[] = {
    { MP_QSTR_key, offsetof(lvgl_mvu_attrs_AttrDef_obj_t, key), 1 },
    { MP_QSTR_name, offsetof(lvgl_mvu_attrs_AttrDef_obj_t, name), 0 },
    { MP_QSTR_default_val, offsetof(lvgl_mvu_attrs_AttrDef_obj_t, default_val), 0 },
    { MP_QSTR_apply_fn, offsetof(lvgl_mvu_attrs_AttrDef_obj_t, apply_fn), 0 },
    { MP_QSTR_compare_fn, offsetof(lvgl_mvu_attrs_AttrDef_obj_t, compare_fn), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_attrs_AttrDef_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_attrs_AttrDef_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_attrs_AttrDef_field_t *f = lvgl_mvu_attrs_AttrDef_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void lvgl_mvu_attrs_AttrDef_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    lvgl_mvu_attrs_AttrDef_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "AttrDef(");
    mp_printf(print, "key=%d", (int)self->key);
    mp_printf(print, ", name=");
    mp_obj_print_helper(print, self->name, PRINT_REPR);
    mp_printf(print, ", default_val=");
    mp_obj_print_helper(print, self->default_val, PRINT_REPR);
    mp_printf(print, ", apply_fn=");
    mp_obj_print_helper(print, self->apply_fn, PRINT_REPR);
    mp_printf(print, ", compare_fn=");
    mp_obj_print_helper(print, self->compare_fn, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t lvgl_mvu_attrs_AttrDef_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op == MP_BINARY_OP_EQUAL) {
        if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
            return mp_const_false;
        }
        lvgl_mvu_attrs_AttrDef_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
        lvgl_mvu_attrs_AttrDef_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);
        return mp_obj_new_bool(
            lhs->key == rhs->key &&
            mp_obj_equal(lhs->name, rhs->name) &&
            mp_obj_equal(lhs->default_val, rhs->default_val) &&
            mp_obj_equal(lhs->apply_fn, rhs->apply_fn) &&
            mp_obj_equal(lhs->compare_fn, rhs->compare_fn)
        );
    }
    return MP_OBJ_NULL;
}

static mp_obj_t lvgl_mvu_attrs_AttrDef_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_key,
        ARG_name,
        ARG_default_val,
        ARG_apply_fn,
        ARG_compare_fn,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_key, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_name, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_default_val, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_apply_fn, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_compare_fn, MP_ARG_OBJ, {.u_obj = mp_const_none} },
    };

    mp_arg_val_t parsed[5];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 5, allowed_args, parsed);

    lvgl_mvu_attrs_AttrDef_obj_t *self = mp_obj_malloc(lvgl_mvu_attrs_AttrDef_obj_t, type);
    self->key = parsed[ARG_key].u_int;
    self->name = parsed[ARG_name].u_obj;
    self->default_val = parsed[ARG_default_val].u_obj;
    self->apply_fn = parsed[ARG_apply_fn].u_obj;
    self->compare_fn = parsed[ARG_compare_fn].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_attrs_AttrDef_type,
    MP_QSTR_AttrDef,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_attrs_AttrDef_make_new,
    attr, lvgl_mvu_attrs_AttrDef_attr,
    print, lvgl_mvu_attrs_AttrDef_print,
    binary_op, lvgl_mvu_attrs_AttrDef_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_attrs_AttrRegistry_field_t;

static const lvgl_mvu_attrs_AttrRegistry_field_t lvgl_mvu_attrs_AttrRegistry_fields[] = {
    { MP_QSTR__attrs, offsetof(lvgl_mvu_attrs_AttrRegistry_obj_t, _attrs), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_attrs_AttrRegistry_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_attrs_AttrRegistry_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_attrs_AttrRegistry_field_t *f = lvgl_mvu_attrs_AttrRegistry_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static const lvgl_mvu_attrs_AttrRegistry_vtable_t lvgl_mvu_attrs_AttrRegistry_vtable_inst = {
    .add = lvgl_mvu_attrs_AttrRegistry_add_native,
    .get = lvgl_mvu_attrs_AttrRegistry_get_native,
    .get_or_raise = lvgl_mvu_attrs_AttrRegistry_get_or_raise_native,
    .all_attrs = lvgl_mvu_attrs_AttrRegistry_all_attrs_native,
};

static mp_obj_t lvgl_mvu_attrs_AttrRegistry_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);

    lvgl_mvu_attrs_AttrRegistry_obj_t *self = mp_obj_malloc(lvgl_mvu_attrs_AttrRegistry_obj_t, type);
    self->vtable = &lvgl_mvu_attrs_AttrRegistry_vtable_inst;
    self->_attrs = mp_const_none;

    lvgl_mvu_attrs_AttrRegistry___init___mp(MP_OBJ_FROM_PTR(self));

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t lvgl_mvu_attrs_AttrRegistry_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_add), MP_ROM_PTR(&lvgl_mvu_attrs_AttrRegistry_add_obj) },
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&lvgl_mvu_attrs_AttrRegistry_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_or_raise), MP_ROM_PTR(&lvgl_mvu_attrs_AttrRegistry_get_or_raise_obj) },
    { MP_ROM_QSTR(MP_QSTR_all_attrs), MP_ROM_PTR(&lvgl_mvu_attrs_AttrRegistry_all_attrs_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_attrs_AttrRegistry_locals_dict, lvgl_mvu_attrs_AttrRegistry_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_attrs_AttrRegistry_type,
    MP_QSTR_AttrRegistry,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_attrs_AttrRegistry_make_new,
    attr, lvgl_mvu_attrs_AttrRegistry_attr,
    locals_dict, &lvgl_mvu_attrs_AttrRegistry_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_builders_WidgetBuilder_field_t;

static const lvgl_mvu_builders_WidgetBuilder_field_t lvgl_mvu_builders_WidgetBuilder_fields[] = {
    { MP_QSTR__key, offsetof(lvgl_mvu_builders_WidgetBuilder_obj_t, _key), 1 },
    { MP_QSTR__user_key, offsetof(lvgl_mvu_builders_WidgetBuilder_obj_t, _user_key), 0 },
    { MP_QSTR__attrs, offsetof(lvgl_mvu_builders_WidgetBuilder_obj_t, _attrs), 0 },
    { MP_QSTR__children, offsetof(lvgl_mvu_builders_WidgetBuilder_obj_t, _children), 0 },
    { MP_QSTR__handlers, offsetof(lvgl_mvu_builders_WidgetBuilder_obj_t, _handlers), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_builders_WidgetBuilder_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_builders_WidgetBuilder_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_builders_WidgetBuilder_field_t *f = lvgl_mvu_builders_WidgetBuilder_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static const lvgl_mvu_builders_WidgetBuilder_vtable_t lvgl_mvu_builders_WidgetBuilder_vtable_inst = {
    .user_key = lvgl_mvu_builders_WidgetBuilder_user_key_native,
    .set_attr = lvgl_mvu_builders_WidgetBuilder_set_attr_native,
    .on = lvgl_mvu_builders_WidgetBuilder_on_native,
    .on_value = lvgl_mvu_builders_WidgetBuilder_on_value_native,
    .add_child = lvgl_mvu_builders_WidgetBuilder_add_child_native,
    .build = lvgl_mvu_builders_WidgetBuilder_build_native,
    .width = lvgl_mvu_builders_WidgetBuilder_width_native,
    .height = lvgl_mvu_builders_WidgetBuilder_height_native,
    .size = lvgl_mvu_builders_WidgetBuilder_size_native,
    .pos = lvgl_mvu_builders_WidgetBuilder_pos_native,
    .align = lvgl_mvu_builders_WidgetBuilder_align_native,
    .bg_color = lvgl_mvu_builders_WidgetBuilder_bg_color_native,
    .bg_opa = lvgl_mvu_builders_WidgetBuilder_bg_opa_native,
    .border_color = lvgl_mvu_builders_WidgetBuilder_border_color_native,
    .border_width = lvgl_mvu_builders_WidgetBuilder_border_width_native,
    .radius = lvgl_mvu_builders_WidgetBuilder_radius_native,
    .padding = lvgl_mvu_builders_WidgetBuilder_padding_native,
    .pad_row = lvgl_mvu_builders_WidgetBuilder_pad_row_native,
    .pad_column = lvgl_mvu_builders_WidgetBuilder_pad_column_native,
    .text = lvgl_mvu_builders_WidgetBuilder_text_native,
    .text_color = lvgl_mvu_builders_WidgetBuilder_text_color_native,
    .text_align = lvgl_mvu_builders_WidgetBuilder_text_align_native,
    .shadow = lvgl_mvu_builders_WidgetBuilder_shadow_native,
    .flex_flow = lvgl_mvu_builders_WidgetBuilder_flex_flow_native,
    .flex_grow = lvgl_mvu_builders_WidgetBuilder_flex_grow_native,
    .value = lvgl_mvu_builders_WidgetBuilder_value_native,
    .set_range = lvgl_mvu_builders_WidgetBuilder_set_range_native,
    .checked = lvgl_mvu_builders_WidgetBuilder_checked_native,
};

static mp_obj_t lvgl_mvu_builders_WidgetBuilder_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 1, 1, false);

    lvgl_mvu_builders_WidgetBuilder_obj_t *self = mp_obj_malloc(lvgl_mvu_builders_WidgetBuilder_obj_t, type);
    self->vtable = &lvgl_mvu_builders_WidgetBuilder_vtable_inst;
    self->_key = 0;
    self->_user_key = mp_const_none;
    self->_attrs = mp_const_none;
    self->_children = mp_const_none;
    self->_handlers = mp_const_none;

    lvgl_mvu_builders_WidgetBuilder___init___mp(MP_OBJ_FROM_PTR(self), args[0]);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t lvgl_mvu_builders_WidgetBuilder_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_user_key), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_user_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_attr), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_set_attr_obj) },
    { MP_ROM_QSTR(MP_QSTR_on), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_on_obj) },
    { MP_ROM_QSTR(MP_QSTR_on_value), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_on_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_add_child), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_add_child_obj) },
    { MP_ROM_QSTR(MP_QSTR_build), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_build_obj) },
    { MP_ROM_QSTR(MP_QSTR_width), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_width_obj) },
    { MP_ROM_QSTR(MP_QSTR_height), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_height_obj) },
    { MP_ROM_QSTR(MP_QSTR_size), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_size_obj) },
    { MP_ROM_QSTR(MP_QSTR_pos), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_pos_obj) },
    { MP_ROM_QSTR(MP_QSTR_align), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_align_obj) },
    { MP_ROM_QSTR(MP_QSTR_bg_color), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_bg_color_obj) },
    { MP_ROM_QSTR(MP_QSTR_bg_opa), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_bg_opa_obj) },
    { MP_ROM_QSTR(MP_QSTR_border_color), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_border_color_obj) },
    { MP_ROM_QSTR(MP_QSTR_border_width), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_border_width_obj) },
    { MP_ROM_QSTR(MP_QSTR_radius), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_radius_obj) },
    { MP_ROM_QSTR(MP_QSTR_padding), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_padding_obj) },
    { MP_ROM_QSTR(MP_QSTR_pad_row), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_pad_row_obj) },
    { MP_ROM_QSTR(MP_QSTR_pad_column), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_pad_column_obj) },
    { MP_ROM_QSTR(MP_QSTR_text), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_text_obj) },
    { MP_ROM_QSTR(MP_QSTR_text_color), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_text_color_obj) },
    { MP_ROM_QSTR(MP_QSTR_text_align), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_text_align_obj) },
    { MP_ROM_QSTR(MP_QSTR_shadow), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_shadow_obj) },
    { MP_ROM_QSTR(MP_QSTR_flex_flow), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_flex_flow_obj) },
    { MP_ROM_QSTR(MP_QSTR_flex_grow), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_flex_grow_obj) },
    { MP_ROM_QSTR(MP_QSTR_value), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_value_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_range), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_set_range_obj) },
    { MP_ROM_QSTR(MP_QSTR_checked), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_checked_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_builders_WidgetBuilder_locals_dict, lvgl_mvu_builders_WidgetBuilder_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_builders_WidgetBuilder_type,
    MP_QSTR_WidgetBuilder,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_builders_WidgetBuilder_make_new,
    attr, lvgl_mvu_builders_WidgetBuilder_attr,
    locals_dict, &lvgl_mvu_builders_WidgetBuilder_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_diff_AttrChange_field_t;

static const lvgl_mvu_diff_AttrChange_field_t lvgl_mvu_diff_AttrChange_fields[] = {
    { MP_QSTR_kind, offsetof(lvgl_mvu_diff_AttrChange_obj_t, kind), 0 },
    { MP_QSTR_key, offsetof(lvgl_mvu_diff_AttrChange_obj_t, key), 1 },
    { MP_QSTR_old_value, offsetof(lvgl_mvu_diff_AttrChange_obj_t, old_value), 0 },
    { MP_QSTR_new_value, offsetof(lvgl_mvu_diff_AttrChange_obj_t, new_value), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_diff_AttrChange_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_diff_AttrChange_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_diff_AttrChange_field_t *f = lvgl_mvu_diff_AttrChange_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void lvgl_mvu_diff_AttrChange_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    lvgl_mvu_diff_AttrChange_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "AttrChange(");
    mp_printf(print, "kind=");
    mp_obj_print_helper(print, self->kind, PRINT_REPR);
    mp_printf(print, ", key=%d", (int)self->key);
    mp_printf(print, ", old_value=");
    mp_obj_print_helper(print, self->old_value, PRINT_REPR);
    mp_printf(print, ", new_value=");
    mp_obj_print_helper(print, self->new_value, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t lvgl_mvu_diff_AttrChange_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op == MP_BINARY_OP_EQUAL) {
        if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
            return mp_const_false;
        }
        lvgl_mvu_diff_AttrChange_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
        lvgl_mvu_diff_AttrChange_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);
        return mp_obj_new_bool(
            mp_obj_equal(lhs->kind, rhs->kind) &&
            lhs->key == rhs->key &&
            mp_obj_equal(lhs->old_value, rhs->old_value) &&
            mp_obj_equal(lhs->new_value, rhs->new_value)
        );
    }
    return MP_OBJ_NULL;
}

static mp_obj_t lvgl_mvu_diff_AttrChange_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_kind,
        ARG_key,
        ARG_old_value,
        ARG_new_value,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_kind, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_key, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_old_value, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_new_value, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[4];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 4, allowed_args, parsed);

    lvgl_mvu_diff_AttrChange_obj_t *self = mp_obj_malloc(lvgl_mvu_diff_AttrChange_obj_t, type);
    self->kind = parsed[ARG_kind].u_obj;
    self->key = parsed[ARG_key].u_int;
    self->old_value = parsed[ARG_old_value].u_obj;
    self->new_value = parsed[ARG_new_value].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_diff_AttrChange_type,
    MP_QSTR_AttrChange,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_diff_AttrChange_make_new,
    attr, lvgl_mvu_diff_AttrChange_attr,
    print, lvgl_mvu_diff_AttrChange_print,
    binary_op, lvgl_mvu_diff_AttrChange_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_diff_ChildChange_field_t;

static const lvgl_mvu_diff_ChildChange_field_t lvgl_mvu_diff_ChildChange_fields[] = {
    { MP_QSTR_kind, offsetof(lvgl_mvu_diff_ChildChange_obj_t, kind), 0 },
    { MP_QSTR_index, offsetof(lvgl_mvu_diff_ChildChange_obj_t, index), 1 },
    { MP_QSTR_widget, offsetof(lvgl_mvu_diff_ChildChange_obj_t, widget), 0 },
    { MP_QSTR_diff, offsetof(lvgl_mvu_diff_ChildChange_obj_t, diff), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_diff_ChildChange_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_diff_ChildChange_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_diff_ChildChange_field_t *f = lvgl_mvu_diff_ChildChange_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void lvgl_mvu_diff_ChildChange_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    lvgl_mvu_diff_ChildChange_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "ChildChange(");
    mp_printf(print, "kind=");
    mp_obj_print_helper(print, self->kind, PRINT_REPR);
    mp_printf(print, ", index=%d", (int)self->index);
    mp_printf(print, ", widget=");
    mp_obj_print_helper(print, self->widget, PRINT_REPR);
    mp_printf(print, ", diff=");
    mp_obj_print_helper(print, self->diff, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t lvgl_mvu_diff_ChildChange_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op == MP_BINARY_OP_EQUAL) {
        if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
            return mp_const_false;
        }
        lvgl_mvu_diff_ChildChange_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
        lvgl_mvu_diff_ChildChange_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);
        return mp_obj_new_bool(
            mp_obj_equal(lhs->kind, rhs->kind) &&
            lhs->index == rhs->index &&
            mp_obj_equal(lhs->widget, rhs->widget) &&
            mp_obj_equal(lhs->diff, rhs->diff)
        );
    }
    return MP_OBJ_NULL;
}

static mp_obj_t lvgl_mvu_diff_ChildChange_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_kind,
        ARG_index,
        ARG_widget,
        ARG_diff,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_kind, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_index, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_widget, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_diff, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[4];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 4, allowed_args, parsed);

    lvgl_mvu_diff_ChildChange_obj_t *self = mp_obj_malloc(lvgl_mvu_diff_ChildChange_obj_t, type);
    self->kind = parsed[ARG_kind].u_obj;
    self->index = parsed[ARG_index].u_int;
    self->widget = parsed[ARG_widget].u_obj;
    self->diff = parsed[ARG_diff].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_diff_ChildChange_type,
    MP_QSTR_ChildChange,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_diff_ChildChange_make_new,
    attr, lvgl_mvu_diff_ChildChange_attr,
    print, lvgl_mvu_diff_ChildChange_print,
    binary_op, lvgl_mvu_diff_ChildChange_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_diff_WidgetDiff_field_t;

static const lvgl_mvu_diff_WidgetDiff_field_t lvgl_mvu_diff_WidgetDiff_fields[] = {
    { MP_QSTR_scalar_changes, offsetof(lvgl_mvu_diff_WidgetDiff_obj_t, scalar_changes), 0 },
    { MP_QSTR_child_changes, offsetof(lvgl_mvu_diff_WidgetDiff_obj_t, child_changes), 0 },
    { MP_QSTR_event_changes, offsetof(lvgl_mvu_diff_WidgetDiff_obj_t, event_changes), 3 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_diff_WidgetDiff_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_diff_WidgetDiff_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_diff_WidgetDiff_field_t *f = lvgl_mvu_diff_WidgetDiff_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void lvgl_mvu_diff_WidgetDiff_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    lvgl_mvu_diff_WidgetDiff_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "WidgetDiff(");
    mp_printf(print, "scalar_changes=");
    mp_obj_print_helper(print, self->scalar_changes, PRINT_REPR);
    mp_printf(print, ", child_changes=");
    mp_obj_print_helper(print, self->child_changes, PRINT_REPR);
    mp_printf(print, ", event_changes=%s", self->event_changes ? "True" : "False");
    mp_printf(print, ")");
}

static mp_obj_t lvgl_mvu_diff_WidgetDiff_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op == MP_BINARY_OP_EQUAL) {
        if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
            return mp_const_false;
        }
        lvgl_mvu_diff_WidgetDiff_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
        lvgl_mvu_diff_WidgetDiff_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);
        return mp_obj_new_bool(
            mp_obj_equal(lhs->scalar_changes, rhs->scalar_changes) &&
            mp_obj_equal(lhs->child_changes, rhs->child_changes) &&
            lhs->event_changes == rhs->event_changes
        );
    }
    return MP_OBJ_NULL;
}

static const lvgl_mvu_diff_WidgetDiff_vtable_t lvgl_mvu_diff_WidgetDiff_vtable_inst = {
    .is_empty = lvgl_mvu_diff_WidgetDiff_is_empty_native,
};

static mp_obj_t lvgl_mvu_diff_WidgetDiff_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_scalar_changes,
        ARG_child_changes,
        ARG_event_changes,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_scalar_changes, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_child_changes, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_event_changes, MP_ARG_BOOL, {.u_bool = false} },
    };

    mp_arg_val_t parsed[3];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 3, allowed_args, parsed);

    lvgl_mvu_diff_WidgetDiff_obj_t *self = mp_obj_malloc(lvgl_mvu_diff_WidgetDiff_obj_t, type);
    self->vtable = &lvgl_mvu_diff_WidgetDiff_vtable_inst;
    self->scalar_changes = parsed[ARG_scalar_changes].u_obj;
    self->child_changes = parsed[ARG_child_changes].u_obj;
    self->event_changes = parsed[ARG_event_changes].u_bool;

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t lvgl_mvu_diff_WidgetDiff_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_is_empty), MP_ROM_PTR(&lvgl_mvu_diff_WidgetDiff_is_empty_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_diff_WidgetDiff_locals_dict, lvgl_mvu_diff_WidgetDiff_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_diff_WidgetDiff_type,
    MP_QSTR_WidgetDiff,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_diff_WidgetDiff_make_new,
    attr, lvgl_mvu_diff_WidgetDiff_attr,
    print, lvgl_mvu_diff_WidgetDiff_print,
    binary_op, lvgl_mvu_diff_WidgetDiff_binary_op,
    locals_dict, &lvgl_mvu_diff_WidgetDiff_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_program_Effect_field_t;

static const lvgl_mvu_program_Effect_field_t lvgl_mvu_program_Effect_fields[] = {
    { MP_QSTR_kind, offsetof(lvgl_mvu_program_Effect_obj_t, kind), 1 },
    { MP_QSTR_data, offsetof(lvgl_mvu_program_Effect_obj_t, data), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_program_Effect_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_program_Effect_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_program_Effect_field_t *f = lvgl_mvu_program_Effect_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static mp_obj_t lvgl_mvu_program_Effect_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);

    lvgl_mvu_program_Effect_obj_t *self = mp_obj_malloc(lvgl_mvu_program_Effect_obj_t, type);
    self->kind = 0;
    self->data = mp_const_none;

    lvgl_mvu_program_Effect___init___mp(MP_OBJ_FROM_PTR(self), args[0], args[1]);

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_program_Effect_type,
    MP_QSTR_Effect,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_program_Effect_make_new,
    attr, lvgl_mvu_program_Effect_attr
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_program_Cmd_field_t;

static const lvgl_mvu_program_Cmd_field_t lvgl_mvu_program_Cmd_fields[] = {
    { MP_QSTR_effects, offsetof(lvgl_mvu_program_Cmd_obj_t, effects), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_program_Cmd_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_program_Cmd_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_program_Cmd_field_t *f = lvgl_mvu_program_Cmd_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static mp_obj_t lvgl_mvu_program_Cmd_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);

    lvgl_mvu_program_Cmd_obj_t *self = mp_obj_malloc(lvgl_mvu_program_Cmd_obj_t, type);
    self->effects = mp_const_none;

    lvgl_mvu_program_Cmd___init___mp(MP_OBJ_FROM_PTR(self));

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_obj_static_class_method_t lvgl_mvu_program_Cmd_none_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&lvgl_mvu_program_Cmd_none_fun_obj)
};
static const mp_rom_obj_static_class_method_t lvgl_mvu_program_Cmd_of_msg_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&lvgl_mvu_program_Cmd_of_msg_fun_obj)
};
static const mp_rom_obj_static_class_method_t lvgl_mvu_program_Cmd_batch_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&lvgl_mvu_program_Cmd_batch_fun_obj)
};
static const mp_rom_obj_static_class_method_t lvgl_mvu_program_Cmd_of_effect_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&lvgl_mvu_program_Cmd_of_effect_fun_obj)
};

static const mp_rom_map_elem_t lvgl_mvu_program_Cmd_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_none), MP_ROM_PTR(&lvgl_mvu_program_Cmd_none_obj) },
    { MP_ROM_QSTR(MP_QSTR_of_msg), MP_ROM_PTR(&lvgl_mvu_program_Cmd_of_msg_obj) },
    { MP_ROM_QSTR(MP_QSTR_batch), MP_ROM_PTR(&lvgl_mvu_program_Cmd_batch_obj) },
    { MP_ROM_QSTR(MP_QSTR_of_effect), MP_ROM_PTR(&lvgl_mvu_program_Cmd_of_effect_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_program_Cmd_locals_dict, lvgl_mvu_program_Cmd_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_program_Cmd_type,
    MP_QSTR_Cmd,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_program_Cmd_make_new,
    attr, lvgl_mvu_program_Cmd_attr,
    locals_dict, &lvgl_mvu_program_Cmd_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_program_SubDef_field_t;

static const lvgl_mvu_program_SubDef_field_t lvgl_mvu_program_SubDef_fields[] = {
    { MP_QSTR_kind, offsetof(lvgl_mvu_program_SubDef_obj_t, kind), 1 },
    { MP_QSTR_key, offsetof(lvgl_mvu_program_SubDef_obj_t, key), 0 },
    { MP_QSTR_data, offsetof(lvgl_mvu_program_SubDef_obj_t, data), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_program_SubDef_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_program_SubDef_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_program_SubDef_field_t *f = lvgl_mvu_program_SubDef_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static mp_obj_t lvgl_mvu_program_SubDef_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 3, 3, false);

    lvgl_mvu_program_SubDef_obj_t *self = mp_obj_malloc(lvgl_mvu_program_SubDef_obj_t, type);
    self->kind = 0;
    self->key = mp_const_none;
    self->data = mp_const_none;

    mp_obj_t init_args[4];
    init_args[0] = MP_OBJ_FROM_PTR(self);
    init_args[1] = args[0];
    init_args[2] = args[1];
    init_args[3] = args[2];
    lvgl_mvu_program_SubDef___init___mp(4, init_args);

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_program_SubDef_type,
    MP_QSTR_SubDef,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_program_SubDef_make_new,
    attr, lvgl_mvu_program_SubDef_attr
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_program_Sub_field_t;

static const lvgl_mvu_program_Sub_field_t lvgl_mvu_program_Sub_fields[] = {
    { MP_QSTR_defs, offsetof(lvgl_mvu_program_Sub_obj_t, defs), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_program_Sub_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_program_Sub_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_program_Sub_field_t *f = lvgl_mvu_program_Sub_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static mp_obj_t lvgl_mvu_program_Sub_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);

    lvgl_mvu_program_Sub_obj_t *self = mp_obj_malloc(lvgl_mvu_program_Sub_obj_t, type);
    self->defs = mp_const_none;

    lvgl_mvu_program_Sub___init___mp(MP_OBJ_FROM_PTR(self));

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_obj_static_class_method_t lvgl_mvu_program_Sub_none_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&lvgl_mvu_program_Sub_none_fun_obj)
};
static const mp_rom_obj_static_class_method_t lvgl_mvu_program_Sub_timer_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&lvgl_mvu_program_Sub_timer_fun_obj)
};
static const mp_rom_obj_static_class_method_t lvgl_mvu_program_Sub_batch_obj = {
    {&mp_type_staticmethod}, MP_ROM_PTR(&lvgl_mvu_program_Sub_batch_fun_obj)
};

static const mp_rom_map_elem_t lvgl_mvu_program_Sub_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_none), MP_ROM_PTR(&lvgl_mvu_program_Sub_none_obj) },
    { MP_ROM_QSTR(MP_QSTR_timer), MP_ROM_PTR(&lvgl_mvu_program_Sub_timer_obj) },
    { MP_ROM_QSTR(MP_QSTR_batch), MP_ROM_PTR(&lvgl_mvu_program_Sub_batch_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_program_Sub_locals_dict, lvgl_mvu_program_Sub_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_program_Sub_type,
    MP_QSTR_Sub,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_program_Sub_make_new,
    attr, lvgl_mvu_program_Sub_attr,
    locals_dict, &lvgl_mvu_program_Sub_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_program_Program_field_t;

static const lvgl_mvu_program_Program_field_t lvgl_mvu_program_Program_fields[] = {
    { MP_QSTR_init_fn, offsetof(lvgl_mvu_program_Program_obj_t, init_fn), 0 },
    { MP_QSTR_update_fn, offsetof(lvgl_mvu_program_Program_obj_t, update_fn), 0 },
    { MP_QSTR_view_fn, offsetof(lvgl_mvu_program_Program_obj_t, view_fn), 0 },
    { MP_QSTR_subscribe_fn, offsetof(lvgl_mvu_program_Program_obj_t, subscribe_fn), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_program_Program_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_program_Program_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_program_Program_field_t *f = lvgl_mvu_program_Program_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static mp_obj_t lvgl_mvu_program_Program_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 3, 4, false);

    lvgl_mvu_program_Program_obj_t *self = mp_obj_malloc(lvgl_mvu_program_Program_obj_t, type);
    self->init_fn = mp_const_none;
    self->update_fn = mp_const_none;
    self->view_fn = mp_const_none;
    self->subscribe_fn = mp_const_none;

    mp_obj_t init_args[5];
    init_args[0] = MP_OBJ_FROM_PTR(self);
    init_args[1] = args[0];
    init_args[2] = args[1];
    init_args[3] = args[2];
    init_args[4] = (n_args > 3) ? args[3] : mp_const_none;
    lvgl_mvu_program_Program___init___mp(5, init_args);

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_program_Program_type,
    MP_QSTR_Program,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_program_Program_make_new,
    attr, lvgl_mvu_program_Program_attr
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_reconciler_Reconciler_field_t;

static const lvgl_mvu_reconciler_Reconciler_field_t lvgl_mvu_reconciler_Reconciler_fields[] = {
    { MP_QSTR__factories, offsetof(lvgl_mvu_reconciler_Reconciler_obj_t, _factories), 0 },
    { MP_QSTR__delete_fn, offsetof(lvgl_mvu_reconciler_Reconciler_obj_t, _delete_fn), 0 },
    { MP_QSTR__event_binder, offsetof(lvgl_mvu_reconciler_Reconciler_obj_t, _event_binder), 0 },
    { MP_QSTR__attr_registry, offsetof(lvgl_mvu_reconciler_Reconciler_obj_t, _attr_registry), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_reconciler_Reconciler_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_reconciler_Reconciler_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_reconciler_Reconciler_field_t *f = lvgl_mvu_reconciler_Reconciler_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static const lvgl_mvu_reconciler_Reconciler_vtable_t lvgl_mvu_reconciler_Reconciler_vtable_inst = {
    .register_factory = lvgl_mvu_reconciler_Reconciler_register_factory_native,
    .set_delete_fn = lvgl_mvu_reconciler_Reconciler_set_delete_fn_native,
    .set_event_binder = lvgl_mvu_reconciler_Reconciler_set_event_binder_native,
    .reconcile = lvgl_mvu_reconciler_Reconciler_reconcile_native,
    ._create_node = lvgl_mvu_reconciler_Reconciler__create_node_native,
    ._reconcile_children = lvgl_mvu_reconciler_Reconciler__reconcile_children_native,
    ._register_handlers = lvgl_mvu_reconciler_Reconciler__register_handlers_native,
    ._reconcile_handlers = lvgl_mvu_reconciler_Reconciler__reconcile_handlers_native,
    .dispose_tree = lvgl_mvu_reconciler_Reconciler_dispose_tree_native,
};

static mp_obj_t lvgl_mvu_reconciler_Reconciler_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 1, 1, false);

    lvgl_mvu_reconciler_Reconciler_obj_t *self = mp_obj_malloc(lvgl_mvu_reconciler_Reconciler_obj_t, type);
    self->vtable = &lvgl_mvu_reconciler_Reconciler_vtable_inst;
    self->_factories = mp_const_none;
    self->_delete_fn = mp_const_none;
    self->_event_binder = mp_const_none;
    self->_attr_registry = mp_const_none;

    lvgl_mvu_reconciler_Reconciler___init___mp(MP_OBJ_FROM_PTR(self), args[0]);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t lvgl_mvu_reconciler_Reconciler_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_register_factory), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler_register_factory_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_delete_fn), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler_set_delete_fn_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_event_binder), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler_set_event_binder_obj) },
    { MP_ROM_QSTR(MP_QSTR_reconcile), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler_reconcile_obj) },
    { MP_ROM_QSTR(MP_QSTR__create_node), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler__create_node_obj) },
    { MP_ROM_QSTR(MP_QSTR__reconcile_children), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler__reconcile_children_obj) },
    { MP_ROM_QSTR(MP_QSTR__register_handlers), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler__register_handlers_obj) },
    { MP_ROM_QSTR(MP_QSTR__reconcile_handlers), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler__reconcile_handlers_obj) },
    { MP_ROM_QSTR(MP_QSTR_dispose_tree), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler_dispose_tree_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_reconciler_Reconciler_locals_dict, lvgl_mvu_reconciler_Reconciler_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_reconciler_Reconciler_type,
    MP_QSTR_Reconciler,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_reconciler_Reconciler_make_new,
    attr, lvgl_mvu_reconciler_Reconciler_attr,
    locals_dict, &lvgl_mvu_reconciler_Reconciler_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_viewnode_ViewNode_field_t;

static const lvgl_mvu_viewnode_ViewNode_field_t lvgl_mvu_viewnode_ViewNode_fields[] = {
    { MP_QSTR_lv_obj, offsetof(lvgl_mvu_viewnode_ViewNode_obj_t, lv_obj), 0 },
    { MP_QSTR_widget, offsetof(lvgl_mvu_viewnode_ViewNode_obj_t, widget), 0 },
    { MP_QSTR_children, offsetof(lvgl_mvu_viewnode_ViewNode_obj_t, children), 0 },
    { MP_QSTR_handlers, offsetof(lvgl_mvu_viewnode_ViewNode_obj_t, handlers), 0 },
    { MP_QSTR__disposed, offsetof(lvgl_mvu_viewnode_ViewNode_obj_t, _disposed), 3 },
    { MP_QSTR__attr_registry, offsetof(lvgl_mvu_viewnode_ViewNode_obj_t, _attr_registry), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_viewnode_ViewNode_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_viewnode_ViewNode_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_viewnode_ViewNode_field_t *f = lvgl_mvu_viewnode_ViewNode_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static const lvgl_mvu_viewnode_ViewNode_vtable_t lvgl_mvu_viewnode_ViewNode_vtable_inst = {
    .apply_scalar_change = lvgl_mvu_viewnode_ViewNode_apply_scalar_change_native,
    .apply_diff = lvgl_mvu_viewnode_ViewNode_apply_diff_native,
    .update_widget = lvgl_mvu_viewnode_ViewNode_update_widget_native,
    .add_child = lvgl_mvu_viewnode_ViewNode_add_child_native,
    .remove_child = lvgl_mvu_viewnode_ViewNode_remove_child_native,
    .get_child = lvgl_mvu_viewnode_ViewNode_get_child_native,
    .child_count = lvgl_mvu_viewnode_ViewNode_child_count_native,
    .register_handler = lvgl_mvu_viewnode_ViewNode_register_handler_native,
    .unregister_handler = lvgl_mvu_viewnode_ViewNode_unregister_handler_native,
    .clear_handlers = lvgl_mvu_viewnode_ViewNode_clear_handlers_native,
    .dispose = lvgl_mvu_viewnode_ViewNode_dispose_native,
    .is_disposed = lvgl_mvu_viewnode_ViewNode_is_disposed_native,
};

static mp_obj_t lvgl_mvu_viewnode_ViewNode_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 3, 3, false);

    lvgl_mvu_viewnode_ViewNode_obj_t *self = mp_obj_malloc(lvgl_mvu_viewnode_ViewNode_obj_t, type);
    self->vtable = &lvgl_mvu_viewnode_ViewNode_vtable_inst;
    self->lv_obj = mp_const_none;
    self->widget = mp_const_none;
    self->children = mp_const_none;
    self->handlers = mp_const_none;
    self->_disposed = false;
    self->_attr_registry = mp_const_none;

    mp_obj_t init_args[4];
    init_args[0] = MP_OBJ_FROM_PTR(self);
    init_args[1] = args[0];
    init_args[2] = args[1];
    init_args[3] = args[2];
    lvgl_mvu_viewnode_ViewNode___init___mp(4, init_args);

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t lvgl_mvu_viewnode_ViewNode_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_apply_scalar_change), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_apply_scalar_change_obj) },
    { MP_ROM_QSTR(MP_QSTR_apply_diff), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_apply_diff_obj) },
    { MP_ROM_QSTR(MP_QSTR_update_widget), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_update_widget_obj) },
    { MP_ROM_QSTR(MP_QSTR_add_child), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_add_child_obj) },
    { MP_ROM_QSTR(MP_QSTR_remove_child), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_remove_child_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_child), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_get_child_obj) },
    { MP_ROM_QSTR(MP_QSTR_child_count), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_child_count_obj) },
    { MP_ROM_QSTR(MP_QSTR_register_handler), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_register_handler_obj) },
    { MP_ROM_QSTR(MP_QSTR_unregister_handler), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_unregister_handler_obj) },
    { MP_ROM_QSTR(MP_QSTR_clear_handlers), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_clear_handlers_obj) },
    { MP_ROM_QSTR(MP_QSTR_dispose), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_dispose_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_disposed), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_is_disposed_obj) },
};
static MP_DEFINE_CONST_DICT(lvgl_mvu_viewnode_ViewNode_locals_dict, lvgl_mvu_viewnode_ViewNode_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_viewnode_ViewNode_type,
    MP_QSTR_ViewNode,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_viewnode_ViewNode_make_new,
    attr, lvgl_mvu_viewnode_ViewNode_attr,
    locals_dict, &lvgl_mvu_viewnode_ViewNode_locals_dict
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_widget_ScalarAttr_field_t;

static const lvgl_mvu_widget_ScalarAttr_field_t lvgl_mvu_widget_ScalarAttr_fields[] = {
    { MP_QSTR_key, offsetof(lvgl_mvu_widget_ScalarAttr_obj_t, key), 1 },
    { MP_QSTR_value, offsetof(lvgl_mvu_widget_ScalarAttr_obj_t, value), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_widget_ScalarAttr_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_widget_ScalarAttr_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_widget_ScalarAttr_field_t *f = lvgl_mvu_widget_ScalarAttr_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void lvgl_mvu_widget_ScalarAttr_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    lvgl_mvu_widget_ScalarAttr_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "ScalarAttr(");
    mp_printf(print, "key=%d", (int)self->key);
    mp_printf(print, ", value=");
    mp_obj_print_helper(print, self->value, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t lvgl_mvu_widget_ScalarAttr_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op == MP_BINARY_OP_EQUAL) {
        if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
            return mp_const_false;
        }
        lvgl_mvu_widget_ScalarAttr_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
        lvgl_mvu_widget_ScalarAttr_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);
        return mp_obj_new_bool(
            lhs->key == rhs->key &&
            mp_obj_equal(lhs->value, rhs->value)
        );
    }
    return MP_OBJ_NULL;
}

static mp_obj_t lvgl_mvu_widget_ScalarAttr_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_key,
        ARG_value,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_key, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_value, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[2];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 2, allowed_args, parsed);

    lvgl_mvu_widget_ScalarAttr_obj_t *self = mp_obj_malloc(lvgl_mvu_widget_ScalarAttr_obj_t, type);
    self->key = parsed[ARG_key].u_int;
    self->value = parsed[ARG_value].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_widget_ScalarAttr_type,
    MP_QSTR_ScalarAttr,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_widget_ScalarAttr_make_new,
    attr, lvgl_mvu_widget_ScalarAttr_attr,
    print, lvgl_mvu_widget_ScalarAttr_print,
    binary_op, lvgl_mvu_widget_ScalarAttr_binary_op
);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} lvgl_mvu_widget_Widget_field_t;

static const lvgl_mvu_widget_Widget_field_t lvgl_mvu_widget_Widget_fields[] = {
    { MP_QSTR_key, offsetof(lvgl_mvu_widget_Widget_obj_t, key), 1 },
    { MP_QSTR_user_key, offsetof(lvgl_mvu_widget_Widget_obj_t, user_key), 0 },
    { MP_QSTR_scalar_attrs, offsetof(lvgl_mvu_widget_Widget_obj_t, scalar_attrs), 0 },
    { MP_QSTR_children, offsetof(lvgl_mvu_widget_Widget_obj_t, children), 0 },
    { MP_QSTR_event_handlers, offsetof(lvgl_mvu_widget_Widget_obj_t, event_handlers), 0 },
    { MP_QSTR_NULL, 0, 0 }
};

static void lvgl_mvu_widget_Widget_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    lvgl_mvu_widget_Widget_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const lvgl_mvu_widget_Widget_field_t *f = lvgl_mvu_widget_Widget_fields; f->name != MP_QSTR_NULL; f++) {
        if (f->name == attr) {
            if (dest[0] == MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: dest[0] = *(mp_obj_t *)ptr; break;
                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;
                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;
                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;
                }
            } else if (dest[1] != MP_OBJ_NULL) {
                char *ptr = (char *)self + f->offset;
                switch (f->type) {
                    case 0: *(mp_obj_t *)ptr = dest[1]; break;
                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;
                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;
                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;
                }
                dest[0] = MP_OBJ_NULL;
            }
            return;
        }
    }

    dest[1] = MP_OBJ_SENTINEL;
}

static void lvgl_mvu_widget_Widget_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    lvgl_mvu_widget_Widget_obj_t *self = MP_OBJ_TO_PTR(self_in);
    (void)kind;
    mp_printf(print, "Widget(");
    mp_printf(print, "key=%d", (int)self->key);
    mp_printf(print, ", user_key=");
    mp_obj_print_helper(print, self->user_key, PRINT_REPR);
    mp_printf(print, ", scalar_attrs=");
    mp_obj_print_helper(print, self->scalar_attrs, PRINT_REPR);
    mp_printf(print, ", children=");
    mp_obj_print_helper(print, self->children, PRINT_REPR);
    mp_printf(print, ", event_handlers=");
    mp_obj_print_helper(print, self->event_handlers, PRINT_REPR);
    mp_printf(print, ")");
}

static mp_obj_t lvgl_mvu_widget_Widget_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {
    if (op == MP_BINARY_OP_EQUAL) {
        if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {
            return mp_const_false;
        }
        lvgl_mvu_widget_Widget_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);
        lvgl_mvu_widget_Widget_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);
        return mp_obj_new_bool(
            lhs->key == rhs->key &&
            mp_obj_equal(lhs->user_key, rhs->user_key) &&
            mp_obj_equal(lhs->scalar_attrs, rhs->scalar_attrs) &&
            mp_obj_equal(lhs->children, rhs->children) &&
            mp_obj_equal(lhs->event_handlers, rhs->event_handlers)
        );
    }
    return MP_OBJ_NULL;
}

static mp_obj_t lvgl_mvu_widget_Widget_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    enum {
        ARG_key,
        ARG_user_key,
        ARG_scalar_attrs,
        ARG_children,
        ARG_event_handlers,
    };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_key, MP_ARG_REQUIRED | MP_ARG_INT },
        { MP_QSTR_user_key, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_scalar_attrs, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_children, MP_ARG_REQUIRED | MP_ARG_OBJ },
        { MP_QSTR_event_handlers, MP_ARG_REQUIRED | MP_ARG_OBJ },
    };

    mp_arg_val_t parsed[5];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, 5, allowed_args, parsed);

    lvgl_mvu_widget_Widget_obj_t *self = mp_obj_malloc(lvgl_mvu_widget_Widget_obj_t, type);
    self->key = parsed[ARG_key].u_int;
    self->user_key = parsed[ARG_user_key].u_obj;
    self->scalar_attrs = parsed[ARG_scalar_attrs].u_obj;
    self->children = parsed[ARG_children].u_obj;
    self->event_handlers = parsed[ARG_event_handlers].u_obj;

    return MP_OBJ_FROM_PTR(self);
}

MP_DEFINE_CONST_OBJ_TYPE(
    lvgl_mvu_widget_Widget_type,
    MP_QSTR_Widget,
    MP_TYPE_FLAG_NONE,
    make_new, lvgl_mvu_widget_Widget_make_new,
    attr, lvgl_mvu_widget_Widget_attr,
    print, lvgl_mvu_widget_Widget_print,
    binary_op, lvgl_mvu_widget_Widget_binary_op
);

static const mp_rom_map_elem_t lvgl_mvu_app_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_app) },
    { MP_ROM_QSTR(MP_QSTR_App), MP_ROM_PTR(&lvgl_mvu_app_App_type) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_app_globals, lvgl_mvu_app_globals_table);

static const mp_obj_module_t lvgl_mvu_app_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_app_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_attrs_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_attrs) },
    { MP_ROM_QSTR(MP_QSTR_AttrDef), MP_ROM_PTR(&lvgl_mvu_attrs_AttrDef_type) },
    { MP_ROM_QSTR(MP_QSTR_AttrRegistry), MP_ROM_PTR(&lvgl_mvu_attrs_AttrRegistry_type) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_X), MP_ROM_INT(0) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_Y), MP_ROM_INT(1) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_WIDTH), MP_ROM_INT(2) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_HEIGHT), MP_ROM_INT(3) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_ALIGN), MP_ROM_INT(4) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_ALIGN_X_OFS), MP_ROM_INT(5) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_ALIGN_Y_OFS), MP_ROM_INT(6) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_PAD_TOP), MP_ROM_INT(20) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_PAD_RIGHT), MP_ROM_INT(21) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_PAD_BOTTOM), MP_ROM_INT(22) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_PAD_LEFT), MP_ROM_INT(23) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_PAD_ROW), MP_ROM_INT(24) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_PAD_COLUMN), MP_ROM_INT(25) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BG_COLOR), MP_ROM_INT(40) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BG_OPA), MP_ROM_INT(41) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BG_GRAD_COLOR), MP_ROM_INT(42) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BG_GRAD_DIR), MP_ROM_INT(43) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BORDER_COLOR), MP_ROM_INT(60) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BORDER_WIDTH), MP_ROM_INT(61) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BORDER_OPA), MP_ROM_INT(62) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_BORDER_SIDE), MP_ROM_INT(63) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_RADIUS), MP_ROM_INT(64) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SHADOW_WIDTH), MP_ROM_INT(80) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SHADOW_COLOR), MP_ROM_INT(81) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SHADOW_OFS_X), MP_ROM_INT(82) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SHADOW_OFS_Y), MP_ROM_INT(83) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SHADOW_SPREAD), MP_ROM_INT(84) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SHADOW_OPA), MP_ROM_INT(85) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_TEXT), MP_ROM_INT(100) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_TEXT_COLOR), MP_ROM_INT(101) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_TEXT_OPA), MP_ROM_INT(102) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_TEXT_FONT), MP_ROM_INT(103) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_TEXT_ALIGN), MP_ROM_INT(104) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_TEXT_DECOR), MP_ROM_INT(105) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_FLEX_FLOW), MP_ROM_INT(120) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_FLEX_MAIN_PLACE), MP_ROM_INT(121) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_FLEX_CROSS_PLACE), MP_ROM_INT(122) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_FLEX_TRACK_PLACE), MP_ROM_INT(123) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_FLEX_GROW), MP_ROM_INT(124) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_GRID_COLUMN_DSC), MP_ROM_INT(125) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_GRID_ROW_DSC), MP_ROM_INT(126) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_GRID_CELL_COLUMN_POS), MP_ROM_INT(127) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_GRID_CELL_ROW_POS), MP_ROM_INT(128) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_MIN_VALUE), MP_ROM_INT(140) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_MAX_VALUE), MP_ROM_INT(141) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_VALUE), MP_ROM_INT(142) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_CHECKED), MP_ROM_INT(143) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SRC), MP_ROM_INT(144) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_PLACEHOLDER), MP_ROM_INT(145) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_OPTIONS), MP_ROM_INT(146) },
    { MP_ROM_QSTR(MP_QSTR_AttrKey_SELECTED), MP_ROM_INT(147) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_attrs_globals, lvgl_mvu_attrs_globals_table);

static const mp_obj_module_t lvgl_mvu_attrs_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_attrs_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_builders_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_builders) },
    { MP_ROM_QSTR(MP_QSTR__attr_sort_key), MP_ROM_PTR(&lvgl_mvu_builders__attr_sort_key_obj) },
    { MP_ROM_QSTR(MP_QSTR_WidgetBuilder), MP_ROM_PTR(&lvgl_mvu_builders_WidgetBuilder_type) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_builders_globals, lvgl_mvu_builders_globals_table);

static const mp_obj_module_t lvgl_mvu_builders_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_builders_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_diff_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_diff) },
    { MP_ROM_QSTR(MP_QSTR_diff_scalars), MP_ROM_PTR(&lvgl_mvu_diff_diff_scalars_obj) },
    { MP_ROM_QSTR(MP_QSTR_can_reuse), MP_ROM_PTR(&lvgl_mvu_diff_can_reuse_obj) },
    { MP_ROM_QSTR(MP_QSTR_diff_children), MP_ROM_PTR(&lvgl_mvu_diff_diff_children_obj) },
    { MP_ROM_QSTR(MP_QSTR__events_changed), MP_ROM_PTR(&lvgl_mvu_diff__events_changed_obj) },
    { MP_ROM_QSTR(MP_QSTR_diff_widgets), MP_ROM_PTR(&lvgl_mvu_diff_diff_widgets_obj) },
    { MP_ROM_QSTR(MP_QSTR_AttrChange), MP_ROM_PTR(&lvgl_mvu_diff_AttrChange_type) },
    { MP_ROM_QSTR(MP_QSTR_ChildChange), MP_ROM_PTR(&lvgl_mvu_diff_ChildChange_type) },
    { MP_ROM_QSTR(MP_QSTR_WidgetDiff), MP_ROM_PTR(&lvgl_mvu_diff_WidgetDiff_type) },
    { MP_ROM_QSTR(MP_QSTR_CHANGE_ADDED), MP_ROM_QSTR(MP_QSTR_added) },
    { MP_ROM_QSTR(MP_QSTR_CHANGE_REMOVED), MP_ROM_QSTR(MP_QSTR_removed) },
    { MP_ROM_QSTR(MP_QSTR_CHANGE_UPDATED), MP_ROM_QSTR(MP_QSTR_updated) },
    { MP_ROM_QSTR(MP_QSTR_CHILD_INSERT), MP_ROM_QSTR(MP_QSTR_insert) },
    { MP_ROM_QSTR(MP_QSTR_CHILD_REMOVE), MP_ROM_QSTR(MP_QSTR_remove) },
    { MP_ROM_QSTR(MP_QSTR_CHILD_UPDATE), MP_ROM_QSTR(MP_QSTR_update) },
    { MP_ROM_QSTR(MP_QSTR_CHILD_REPLACE), MP_ROM_QSTR(MP_QSTR_replace) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_diff_globals, lvgl_mvu_diff_globals_table);

static const mp_obj_module_t lvgl_mvu_diff_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_diff_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_program_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_program) },
    { MP_ROM_QSTR(MP_QSTR_Effect), MP_ROM_PTR(&lvgl_mvu_program_Effect_type) },
    { MP_ROM_QSTR(MP_QSTR_Cmd), MP_ROM_PTR(&lvgl_mvu_program_Cmd_type) },
    { MP_ROM_QSTR(MP_QSTR_SubDef), MP_ROM_PTR(&lvgl_mvu_program_SubDef_type) },
    { MP_ROM_QSTR(MP_QSTR_Sub), MP_ROM_PTR(&lvgl_mvu_program_Sub_type) },
    { MP_ROM_QSTR(MP_QSTR_Program), MP_ROM_PTR(&lvgl_mvu_program_Program_type) },
    { MP_ROM_QSTR(MP_QSTR_EFFECT_MSG), MP_ROM_INT(0) },
    { MP_ROM_QSTR(MP_QSTR_EFFECT_FN), MP_ROM_INT(1) },
    { MP_ROM_QSTR(MP_QSTR_SUB_TIMER), MP_ROM_INT(0) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_program_globals, lvgl_mvu_program_globals_table);

static const mp_obj_module_t lvgl_mvu_program_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_program_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_reconciler_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_reconciler) },
    { MP_ROM_QSTR(MP_QSTR_Reconciler), MP_ROM_PTR(&lvgl_mvu_reconciler_Reconciler_type) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_reconciler_globals, lvgl_mvu_reconciler_globals_table);

static const mp_obj_module_t lvgl_mvu_reconciler_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_reconciler_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_viewnode_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_viewnode) },
    { MP_ROM_QSTR(MP_QSTR_ViewNode), MP_ROM_PTR(&lvgl_mvu_viewnode_ViewNode_type) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_viewnode_globals, lvgl_mvu_viewnode_globals_table);

static const mp_obj_module_t lvgl_mvu_viewnode_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_viewnode_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_widget_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_widget) },
    { MP_ROM_QSTR(MP_QSTR_ScalarAttr), MP_ROM_PTR(&lvgl_mvu_widget_ScalarAttr_type) },
    { MP_ROM_QSTR(MP_QSTR_Widget), MP_ROM_PTR(&lvgl_mvu_widget_Widget_type) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_SCREEN), MP_ROM_INT(0) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_CONTAINER), MP_ROM_INT(1) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_LABEL), MP_ROM_INT(2) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_BUTTON), MP_ROM_INT(3) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_SLIDER), MP_ROM_INT(4) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_BAR), MP_ROM_INT(5) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_ARC), MP_ROM_INT(6) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_SWITCH), MP_ROM_INT(7) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_CHECKBOX), MP_ROM_INT(8) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_IMAGE), MP_ROM_INT(9) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_TEXTAREA), MP_ROM_INT(10) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_DROPDOWN), MP_ROM_INT(11) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_ROLLER), MP_ROM_INT(12) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_TABLE), MP_ROM_INT(13) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_CHART), MP_ROM_INT(14) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_CALENDAR), MP_ROM_INT(15) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_KEYBOARD), MP_ROM_INT(16) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_MENU), MP_ROM_INT(17) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_TABVIEW), MP_ROM_INT(18) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_MSGBOX), MP_ROM_INT(19) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_SPINNER), MP_ROM_INT(20) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_LED), MP_ROM_INT(21) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_LINE), MP_ROM_INT(22) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_CANVAS), MP_ROM_INT(23) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_WINDOW), MP_ROM_INT(24) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_TILEVIEW), MP_ROM_INT(25) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_LIST), MP_ROM_INT(26) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_SPANGROUP), MP_ROM_INT(27) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_SPINBOX), MP_ROM_INT(28) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_SCALE), MP_ROM_INT(29) },
    { MP_ROM_QSTR(MP_QSTR_WidgetKey_BUTTONMATRIX), MP_ROM_INT(30) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_widget_globals, lvgl_mvu_widget_globals_table);

static const mp_obj_module_t lvgl_mvu_widget_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_widget_globals,
};

static const mp_rom_map_elem_t lvgl_mvu_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lvgl_mvu) },
    { MP_ROM_QSTR(MP_QSTR_app), MP_ROM_PTR(&lvgl_mvu_app_module) },
    { MP_ROM_QSTR(MP_QSTR_attrs), MP_ROM_PTR(&lvgl_mvu_attrs_module) },
    { MP_ROM_QSTR(MP_QSTR_builders), MP_ROM_PTR(&lvgl_mvu_builders_module) },
    { MP_ROM_QSTR(MP_QSTR_diff), MP_ROM_PTR(&lvgl_mvu_diff_module) },
    { MP_ROM_QSTR(MP_QSTR_program), MP_ROM_PTR(&lvgl_mvu_program_module) },
    { MP_ROM_QSTR(MP_QSTR_reconciler), MP_ROM_PTR(&lvgl_mvu_reconciler_module) },
    { MP_ROM_QSTR(MP_QSTR_viewnode), MP_ROM_PTR(&lvgl_mvu_viewnode_module) },
    { MP_ROM_QSTR(MP_QSTR_widget), MP_ROM_PTR(&lvgl_mvu_widget_module) },
};
MP_DEFINE_CONST_DICT(lvgl_mvu_module_globals, lvgl_mvu_module_globals_table);

const mp_obj_module_t lvgl_mvu_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_mvu_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_lvgl_mvu, lvgl_mvu_user_cmodule);