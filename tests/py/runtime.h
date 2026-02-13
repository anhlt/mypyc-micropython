#ifndef MICROPYTHON_MOCK_RUNTIME_H
#define MICROPYTHON_MOCK_RUNTIME_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

typedef intptr_t mp_int_t;
typedef uintptr_t mp_uint_t;
typedef double mp_float_t;

typedef void *mp_obj_t;

#define mp_const_none ((mp_obj_t)0)
#define mp_const_true ((mp_obj_t)1)
#define mp_const_false ((mp_obj_t)2)
#define MP_OBJ_SENTINEL ((mp_obj_t)3)

static inline mp_int_t mp_obj_get_int(mp_obj_t obj) { (void)obj; return 0; }
static inline mp_obj_t mp_obj_new_int(mp_int_t val) { (void)val; return (mp_obj_t)0; }
static inline mp_obj_t mp_obj_new_float(mp_float_t val) { (void)val; return (mp_obj_t)0; }
static inline mp_float_t mp_obj_float_get(mp_obj_t obj) { (void)obj; return 0.0; }
static inline bool mp_obj_is_float(mp_obj_t obj) { (void)obj; return false; }
static inline mp_obj_t mp_obj_new_str(const char *data, size_t len) { (void)data; (void)len; return (mp_obj_t)0; }
static inline mp_obj_t mp_obj_new_list(size_t n, mp_obj_t *items) { (void)n; (void)items; return (mp_obj_t)0; }
static inline mp_obj_t mp_obj_len(mp_obj_t obj) { (void)obj; return (mp_obj_t)0; }
static inline mp_obj_t mp_obj_subscr(mp_obj_t obj, mp_obj_t idx, mp_obj_t val) { (void)obj; (void)idx; (void)val; return (mp_obj_t)0; }
static inline mp_obj_t mp_obj_list_append(mp_obj_t list, mp_obj_t item) { (void)list; (void)item; return (mp_obj_t)0; }
static inline mp_obj_t mp_obj_list_pop(mp_obj_t list, size_t n_args, mp_obj_t *args) { (void)list; (void)n_args; (void)args; return (mp_obj_t)0; }

typedef struct {
    mp_obj_t type;
} mp_obj_base_t;

typedef struct {
    mp_obj_t key;
    mp_obj_t value;
} mp_rom_map_elem_t;

typedef struct {
    mp_obj_base_t base;
} mp_obj_dict_t;

typedef struct {
    mp_obj_base_t base;
    mp_obj_dict_t *globals;
} mp_obj_module_t;

extern mp_obj_t mp_type_module;

#define MP_ROM_QSTR(x) ((mp_obj_t)0)
#define MP_ROM_PTR(x) ((mp_obj_t)0)
#define MP_QSTR___name__ 0
#define MP_DEFINE_CONST_FUN_OBJ_0(obj_name, fun_name) \
    static const int obj_name = 0;
#define MP_DEFINE_CONST_FUN_OBJ_1(obj_name, fun_name) \
    static const int obj_name = 0;
#define MP_DEFINE_CONST_FUN_OBJ_2(obj_name, fun_name) \
    static const int obj_name = 0;
#define MP_DEFINE_CONST_FUN_OBJ_3(obj_name, fun_name) \
    static const int obj_name = 0;
#define MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(obj_name, min, max, fun_name) \
    static const int obj_name = 0;
#define MP_DEFINE_CONST_DICT(dict_name, table_name) \
    static const int dict_name = 0;
#define MP_REGISTER_MODULE(qstr, mod)

#endif
