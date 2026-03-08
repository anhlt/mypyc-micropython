/**
 * GT911 Touch driver interface for mypyc-micropython LVGL integration.
 */

#ifndef TOUCH_DRIVER_H
#define TOUCH_DRIVER_H

#include "py/obj.h"
#include "esp_err.h"

// Initialize GT911 touch driver and register with LVGL
esp_err_t gt911_touch_init(void);

// Deinitialize touch driver
void gt911_touch_deinit(void);

// MicroPython function objects
extern const mp_obj_fun_builtin_fixed_t lvgl_init_touch_obj;
extern const mp_obj_fun_builtin_fixed_t lvgl_deinit_touch_obj;
extern const mp_obj_fun_builtin_fixed_t lvgl_get_touch_obj;

#endif // TOUCH_DRIVER_H
