#include "py/runtime.h"
#include "py/obj.h"

#include "lvgl.h"

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_err.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_timer.h"
#include "hal/spi_types.h"

#define LCD_MOSI 6
#define LCD_SCLK 7
#define LCD_CS 14
#define LCD_DC 15
#define LCD_RST 21
#define LCD_BL 22
#define LCD_H_RES 172
#define LCD_V_RES 320
#define LCD_X_GAP 34
#define LCD_BUF_LINES 40

static bool s_initialized = false;
static esp_lcd_panel_handle_t s_panel = NULL;
static lv_display_t *s_disp = NULL;

static uint32_t tick_cb(void) {
    return (uint32_t)(esp_timer_get_time() / 1000);
}

static bool IRAM_ATTR notify_flush_ready(
    esp_lcd_panel_io_handle_t panel_io,
    esp_lcd_panel_io_event_data_t *edata,
    void *user_ctx) {
    (void)panel_io;
    (void)edata;
    lv_display_t *disp = (lv_display_t *)user_ctx;
    lv_display_flush_ready(disp);
    return false;
}

static void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map) {
    esp_lcd_panel_handle_t panel = lv_display_get_user_data(disp);
    int w = area->x2 - area->x1 + 1;
    int h = area->y2 - area->y1 + 1;
    lv_draw_sw_rgb565_swap(px_map, (uint32_t)(w * h));
    esp_lcd_panel_draw_bitmap(panel, area->x1, area->y1, area->x2 + 1, area->y2 + 1, px_map);
}

static void st7789_driver_init(void) {
    if (s_initialized) {
        return;
    }

    gpio_config_t bl_cfg = {
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = 1ULL << LCD_BL,
    };
    ESP_ERROR_CHECK(gpio_config(&bl_cfg));
    ESP_ERROR_CHECK(gpio_set_level(LCD_BL, 0));

    spi_bus_config_t bus_cfg = {
        .sclk_io_num = LCD_SCLK,
        .mosi_io_num = LCD_MOSI,
        .miso_io_num = -1,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = LCD_H_RES * LCD_BUF_LINES * (int)sizeof(uint16_t),
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO));

    esp_lcd_panel_io_spi_config_t io_cfg = {
        .dc_gpio_num = LCD_DC,
        .cs_gpio_num = LCD_CS,
        .pclk_hz = 40 * 1000 * 1000,
        .spi_mode = 0,
        .trans_queue_depth = 10,
        .lcd_cmd_bits = 8,
        .lcd_param_bits = 8,
    };
    esp_lcd_panel_io_handle_t io;
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi((esp_lcd_spi_bus_handle_t)SPI2_HOST, &io_cfg, &io));

    esp_lcd_panel_dev_config_t panel_cfg = {
        .reset_gpio_num = LCD_RST,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_BGR,
        .bits_per_pixel = 16,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(io, &panel_cfg, &s_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_reset(s_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_init(s_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_invert_color(s_panel, true));
    ESP_ERROR_CHECK(esp_lcd_panel_set_gap(s_panel, LCD_X_GAP, 0));
    ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(s_panel, true));

    lv_init();
    lv_tick_set_cb(tick_cb);

    s_disp = lv_display_create(LCD_H_RES, LCD_V_RES);
    lv_display_set_color_format(s_disp, LV_COLOR_FORMAT_RGB565);
    lv_display_set_user_data(s_disp, s_panel);
    lv_display_set_flush_cb(s_disp, flush_cb);

    size_t buf_size = LCD_H_RES * LCD_BUF_LINES * sizeof(uint16_t);
    void *buf1 = heap_caps_malloc(buf_size, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    void *buf2 = heap_caps_malloc(buf_size, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    lv_display_set_buffers(s_disp, buf1, buf2, buf_size, LV_DISPLAY_RENDER_MODE_PARTIAL);

    esp_lcd_panel_io_callbacks_t io_cbs = {
        .on_color_trans_done = notify_flush_ready,
    };
    ESP_ERROR_CHECK(esp_lcd_panel_io_register_event_callbacks(io, &io_cbs, s_disp));

    ESP_ERROR_CHECK(gpio_set_level(LCD_BL, 1));
    s_initialized = true;
}

static mp_obj_t lvgl_init_display(void) {
    st7789_driver_init();
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_init_display_obj, lvgl_init_display);

static mp_obj_t lvgl_timer_handler(void) {
    uint32_t ms = lv_timer_handler();
    return mp_obj_new_int_from_uint(ms);
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_timer_handler_obj, lvgl_timer_handler);

static mp_obj_t lvgl_backlight(mp_obj_t on_obj) {
    ESP_ERROR_CHECK(gpio_set_level(LCD_BL, mp_obj_is_true(on_obj) ? 1 : 0));
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_backlight_obj, lvgl_backlight);
