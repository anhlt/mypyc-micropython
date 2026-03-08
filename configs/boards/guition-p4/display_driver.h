/**
 * Display driver interface for mypyc-micropython LVGL integration.
 * 
 * Each board profile implements these functions:
 * - init_display(): Initialize display hardware and LVGL
 * - deinit_display(): Clean up display resources
 * - timer_handler(): Call LVGL timer handler
 * - backlight(on): Control backlight
 */

#ifndef DISPLAY_DRIVER_H
#define DISPLAY_DRIVER_H

#include "py/obj.h"

// MicroPython function objects - implemented by each board's display driver
extern const mp_obj_fun_builtin_fixed_t lvgl_init_display_obj;
extern const mp_obj_fun_builtin_fixed_t lvgl_deinit_display_obj;
extern const mp_obj_fun_builtin_fixed_t lvgl_timer_handler_obj;
extern const mp_obj_fun_builtin_fixed_t lvgl_backlight_obj;

#endif // DISPLAY_DRIVER_H
