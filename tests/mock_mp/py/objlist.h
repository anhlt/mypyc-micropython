#ifndef MYPYC_MICROPYTHON_MOCK_OBJLIST_H
#define MYPYC_MICROPYTHON_MOCK_OBJLIST_H

#include "runtime.h"

typedef struct _mp_obj_list_t {
    mp_obj_base_t base;
    size_t alloc;
    size_t len;
    mp_obj_t *items;
} mp_obj_list_t;

#define MP_OBJ_TO_PTR(o) ((void *)(o))
#define MP_OBJ_FROM_PTR(p) ((mp_obj_t)(p))

#endif
