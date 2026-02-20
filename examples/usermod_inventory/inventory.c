#include "py/runtime.h"
#include "py/obj.h"
#include "py/objtype.h"
#include <stddef.h>

typedef struct _inventory_Inventory_obj_t inventory_Inventory_obj_t;
typedef struct _inventory_Inventory_vtable_t inventory_Inventory_vtable_t;

#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE
static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {
    if (mp_obj_is_float(obj)) {
        return mp_obj_float_get(obj);
    }
    return (mp_float_t)mp_obj_get_int(obj);
}
#endif

struct _inventory_Inventory_vtable_t {
    void (*add_item)(inventory_Inventory_obj_t *self, mp_int_t item_id, mp_int_t quantity);
    mp_int_t (*get_quantity)(inventory_Inventory_obj_t *self, mp_int_t item_id);
    mp_int_t (*item_count)(inventory_Inventory_obj_t *self);
    mp_int_t (*total_quantity)(inventory_Inventory_obj_t *self);
    bool (*has_item)(inventory_Inventory_obj_t *self, mp_int_t item_id);
};

struct _inventory_Inventory_obj_t {
    mp_obj_base_t base;
    const inventory_Inventory_vtable_t *vtable;
    mp_obj_t items;
    mp_obj_t counts;
    mp_int_t total_count;
};


static mp_obj_t inventory_Inventory___init___mp(mp_obj_t self_in) {
    inventory_Inventory_obj_t *self = MP_OBJ_TO_PTR(self_in);
    self->items = mp_obj_new_list(0, NULL);
    self->counts = mp_obj_new_dict(0);
    self->total_count = 0;
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(inventory_Inventory___init___obj, inventory_Inventory___init___mp);

static void inventory_Inventory_add_item_native(inventory_Inventory_obj_t *self, mp_int_t item_id, mp_int_t quantity) {
    mp_obj_t _tmp1 = mp_obj_list_append(self->items, mp_obj_new_int(item_id));
    (void)_tmp1;
    mp_obj_subscr(self->counts, mp_obj_new_int(item_id), mp_obj_new_int(quantity));
    self->total_count += quantity;
    return;
}

static mp_obj_t inventory_Inventory_add_item_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj) {
    inventory_Inventory_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t item_id = mp_obj_get_int(arg0_obj);
    mp_int_t quantity = mp_obj_get_int(arg1_obj);
    inventory_Inventory_add_item_native(self, item_id, quantity);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_3(inventory_Inventory_add_item_obj, inventory_Inventory_add_item_mp);

static mp_int_t inventory_Inventory_get_quantity_native(inventory_Inventory_obj_t *self, mp_int_t item_id) {
    return mp_obj_get_int(mp_obj_subscr(self->counts, mp_obj_new_int(item_id), MP_OBJ_SENTINEL));
}

static mp_obj_t inventory_Inventory_get_quantity_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    inventory_Inventory_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t item_id = mp_obj_get_int(arg0_obj);
    return mp_obj_new_int(inventory_Inventory_get_quantity_native(self, item_id));
}
MP_DEFINE_CONST_FUN_OBJ_2(inventory_Inventory_get_quantity_obj, inventory_Inventory_get_quantity_mp);

static mp_int_t inventory_Inventory_item_count_native(inventory_Inventory_obj_t *self) {
    return mp_obj_get_int(mp_obj_len(self->items));
}

static mp_obj_t inventory_Inventory_item_count_mp(mp_obj_t self_in) {
    inventory_Inventory_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(inventory_Inventory_item_count_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(inventory_Inventory_item_count_obj, inventory_Inventory_item_count_mp);

static mp_int_t inventory_Inventory_total_quantity_native(inventory_Inventory_obj_t *self) {
    mp_int_t total = 0;
    mp_int_t n = mp_obj_get_int(mp_obj_len(self->items));
    mp_int_t i;
    mp_int_t _tmp1 = n;
    for (i = 0; i < _tmp1; i++) {
        total += mp_obj_get_int(mp_obj_subscr(self->counts, mp_obj_subscr(self->items, mp_obj_new_int(i), MP_OBJ_SENTINEL), MP_OBJ_SENTINEL));
    }
    return total;
}

static mp_obj_t inventory_Inventory_total_quantity_mp(mp_obj_t self_in) {
    inventory_Inventory_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_int(inventory_Inventory_total_quantity_native(self));
}
MP_DEFINE_CONST_FUN_OBJ_1(inventory_Inventory_total_quantity_obj, inventory_Inventory_total_quantity_mp);

static bool inventory_Inventory_has_item_native(inventory_Inventory_obj_t *self, mp_int_t item_id) {
    mp_int_t n = mp_obj_get_int(mp_obj_len(self->items));
    mp_int_t i;
    mp_int_t _tmp1 = n;
    for (i = 0; i < _tmp1; i++) {
        mp_int_t val = mp_obj_get_int(mp_obj_subscr(self->items, mp_obj_new_int(i), MP_OBJ_SENTINEL));
        if ((val == item_id)) {
            return true;
        }
    }
    return false;
}

static mp_obj_t inventory_Inventory_has_item_mp(mp_obj_t self_in, mp_obj_t arg0_obj) {
    inventory_Inventory_obj_t *self = MP_OBJ_TO_PTR(self_in);
    mp_int_t item_id = mp_obj_get_int(arg0_obj);
    return inventory_Inventory_has_item_native(self, item_id) ? mp_const_true : mp_const_false;
}
MP_DEFINE_CONST_FUN_OBJ_2(inventory_Inventory_has_item_obj, inventory_Inventory_has_item_mp);

typedef struct {
    qstr name;
    uint16_t offset;
    uint8_t type;
} inventory_Inventory_field_t;

static const inventory_Inventory_field_t inventory_Inventory_fields[] = {
    { MP_QSTR_items, offsetof(inventory_Inventory_obj_t, items), 0 },
    { MP_QSTR_counts, offsetof(inventory_Inventory_obj_t, counts), 0 },
    { MP_QSTR_total_count, offsetof(inventory_Inventory_obj_t, total_count), 1 },
    { MP_QSTR_NULL, 0, 0 }
};

static void inventory_Inventory_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {
    inventory_Inventory_obj_t *self = MP_OBJ_TO_PTR(self_in);

    for (const inventory_Inventory_field_t *f = inventory_Inventory_fields; f->name != MP_QSTR_NULL; f++) {
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

static const inventory_Inventory_vtable_t inventory_Inventory_vtable_inst = {
    .add_item = inventory_Inventory_add_item_native,
    .get_quantity = inventory_Inventory_get_quantity_native,
    .item_count = inventory_Inventory_item_count_native,
    .total_quantity = inventory_Inventory_total_quantity_native,
    .has_item = inventory_Inventory_has_item_native,
};

static mp_obj_t inventory_Inventory_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);

    inventory_Inventory_obj_t *self = mp_obj_malloc(inventory_Inventory_obj_t, type);
    self->vtable = &inventory_Inventory_vtable_inst;
    self->items = mp_const_none;
    self->counts = mp_const_none;
    self->total_count = 0;

    inventory_Inventory___init___mp(MP_OBJ_FROM_PTR(self));

    return MP_OBJ_FROM_PTR(self);
}

static const mp_rom_map_elem_t inventory_Inventory_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_add_item), MP_ROM_PTR(&inventory_Inventory_add_item_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_quantity), MP_ROM_PTR(&inventory_Inventory_get_quantity_obj) },
    { MP_ROM_QSTR(MP_QSTR_item_count), MP_ROM_PTR(&inventory_Inventory_item_count_obj) },
    { MP_ROM_QSTR(MP_QSTR_total_quantity), MP_ROM_PTR(&inventory_Inventory_total_quantity_obj) },
    { MP_ROM_QSTR(MP_QSTR_has_item), MP_ROM_PTR(&inventory_Inventory_has_item_obj) },
};
static MP_DEFINE_CONST_DICT(inventory_Inventory_locals_dict, inventory_Inventory_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    inventory_Inventory_type,
    MP_QSTR_Inventory,
    MP_TYPE_FLAG_NONE,
    make_new, inventory_Inventory_make_new,
    attr, inventory_Inventory_attr,
    locals_dict, &inventory_Inventory_locals_dict
);

static const mp_rom_map_elem_t inventory_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_inventory) },
    { MP_ROM_QSTR(MP_QSTR_Inventory), MP_ROM_PTR(&inventory_Inventory_type) },
};
MP_DEFINE_CONST_DICT(inventory_module_globals, inventory_module_globals_table);

const mp_obj_module_t inventory_user_cmodule = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&inventory_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_inventory, inventory_user_cmodule);