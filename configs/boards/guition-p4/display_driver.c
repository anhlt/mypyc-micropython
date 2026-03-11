/**
 * ST7701 MIPI-DSI Display Driver for GUITION JC4880P443C (ESP32-P4)
 * 
 * Display: 4.3" IPS TFT LCD, 480x800, RGB565
 * Interface: MIPI-DSI (2-lane)
 * Controller: ST7701
 * 
 * Uses esp_lcd_st7701 component wrapper which properly handles:
 * - Hardware reset via GPIO
 * - Vendor initialization commands
 * - Panel init/reset/mirror operations
 */

#include "py/runtime.h"
#include "py/obj.h"

#include <string.h>
#include "lvgl.h"

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "esp_heap_caps.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_mipi_dsi.h"
#include "esp_lcd_panel_io.h"
#include "esp_ldo_regulator.h"
#include "esp_timer.h"
#include "esp_log.h"

// ST7701 component header (from st7701/ subdirectory)
#include "st7701/esp_lcd_st7701.h"

static const char *TAG = "st7701_driver";

// Display configuration for GUITION JC4880P443C
#define LCD_H_RES           480
#define LCD_V_RES           800
#define LCD_BIT_PER_PIXEL   16      // RGB565

// MIPI-DSI PHY power (ESP32-P4 internal LDO)
#define MIPI_DSI_PHY_PWR_LDO_CHAN       3       // LDO_VO3 for MIPI DPHY
#define MIPI_DSI_PHY_PWR_LDO_VOLTAGE_MV 2500

// Pin configuration (from GUITION board)
#define LCD_RST_GPIO        GPIO_NUM_5   // Reset GPIO (from working JC4880P443C code)
#define LCD_BL_GPIO         GPIO_NUM_23  // Backlight (from Arduino example)

// MIPI-DSI timing for 480x800 @ ~60Hz
#define MIPI_DSI_LANE_BITRATE_MBPS  500   // Working value from JC4880P443C examples
#define MIPI_DPI_CLK_MHZ            34    // Must match working reference

// Driver state
static bool s_initialized = false;
static esp_lcd_panel_handle_t s_panel = NULL;
static esp_lcd_panel_io_handle_t s_io = NULL;
static esp_lcd_dsi_bus_handle_t s_dsi_bus = NULL;
static lv_display_t *s_disp = NULL;

// ST7701 initialization commands for GUITION JC4880P443C 480x800
// Source: ESPHome PR #12068 (verified working for this exact display)
static const st7701_lcd_init_cmd_t st7701_init_cmds[] = {
    {0xFF, (uint8_t []){0x77, 0x01, 0x00, 0x00, 0x13}, 5, 0},
    {0xEF, (uint8_t []){0x08}, 1, 0},
    {0xFF, (uint8_t []){0x77, 0x01, 0x00, 0x00, 0x10}, 5, 0},
    {0xC0, (uint8_t []){0x63, 0x00}, 2, 0},
    {0xC1, (uint8_t []){0x0D, 0x02}, 2, 0},
    {0xC2, (uint8_t []){0x10, 0x08}, 2, 0},
    {0xCC, (uint8_t []){0x10}, 1, 0},

    {0xB0, (uint8_t []){0x80, 0x09, 0x53, 0x0C, 0xD0, 0x07, 0x0C, 0x09, 0x09, 0x28, 0x06, 0xD4, 0x13, 0x69, 0x2B, 0x71}, 16, 0},
    {0xB1, (uint8_t []){0x80, 0x94, 0x5A, 0x10, 0xD3, 0x06, 0x0A, 0x08, 0x08, 0x25, 0x03, 0xD3, 0x12, 0x66, 0x6A, 0x0D}, 16, 0},
    {0xFF, (uint8_t []){0x77, 0x01, 0x00, 0x00, 0x11}, 5, 0},

    {0xB0, (uint8_t []){0x5D}, 1, 0},
    {0xB1, (uint8_t []){0x58}, 1, 0},
    {0xB2, (uint8_t []){0x87}, 1, 0},
    {0xB3, (uint8_t []){0x80}, 1, 0},
    {0xB5, (uint8_t []){0x4E}, 1, 0},
    {0xB7, (uint8_t []){0x85}, 1, 0},
    {0xB8, (uint8_t []){0x21}, 1, 0},
    {0xB9, (uint8_t []){0x10, 0x1F}, 2, 0},
    {0xBB, (uint8_t []){0x03}, 1, 0},
    {0xBC, (uint8_t []){0x00}, 1, 0},

    {0xC1, (uint8_t []){0x78}, 1, 0},
    {0xC2, (uint8_t []){0x78}, 1, 0},
    {0xD0, (uint8_t []){0x88}, 1, 0},

    {0xE0, (uint8_t []){0x00, 0x3A, 0x02}, 3, 0},
    {0xE1, (uint8_t []){0x04, 0xA0, 0x00, 0xA0, 0x05, 0xA0, 0x00, 0xA0, 0x00, 0x40, 0x40}, 11, 0},
    {0xE2, (uint8_t []){0x30, 0x00, 0x40, 0x40, 0x32, 0xA0, 0x00, 0xA0, 0x00, 0xA0, 0x00, 0xA0, 0x00}, 13, 0},
    {0xE3, (uint8_t []){0x00, 0x00, 0x33, 0x33}, 4, 0},
    {0xE4, (uint8_t []){0x44, 0x44}, 2, 0},
    {0xE5, (uint8_t []){0x09, 0x2E, 0xA0, 0xA0, 0x0B, 0x30, 0xA0, 0xA0, 0x05, 0x2A, 0xA0, 0xA0, 0x07, 0x2C, 0xA0, 0xA0}, 16, 0},
    {0xE6, (uint8_t []){0x00, 0x00, 0x33, 0x33}, 4, 0},
    {0xE7, (uint8_t []){0x44, 0x44}, 2, 0},
    {0xE8, (uint8_t []){0x08, 0x2D, 0xA0, 0xA0, 0x0A, 0x2F, 0xA0, 0xA0, 0x04, 0x29, 0xA0, 0xA0, 0x06, 0x2B, 0xA0, 0xA0}, 16, 0},

    {0xEB, (uint8_t []){0x00, 0x00, 0x4E, 0x4E, 0x00, 0x00, 0x00}, 7, 0},
    {0xEC, (uint8_t []){0x08, 0x01}, 2, 0},

    {0xED, (uint8_t []){0xB0, 0x2B, 0x98, 0xA4, 0x56, 0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0xF7, 0x65, 0x4A, 0x89, 0xB2, 0x0B}, 16, 0},
    {0xEF, (uint8_t []){0x08, 0x08, 0x08, 0x45, 0x3F, 0x54}, 6, 0},
    {0xFF, (uint8_t []){0x77, 0x01, 0x00, 0x00, 0x00}, 5, 0},

    {0x11, (uint8_t []){0x00}, 0, 120},  // Sleep out + 120ms delay
    {0x29, (uint8_t []){0x00}, 0, 20},   // Display on + 20ms delay
};

// LVGL tick callback
static uint32_t tick_cb(void) {
    return (uint32_t)(esp_timer_get_time() / 1000);
}

// LVGL flush callback for MIPI-DSI (PARTIAL mode)
// Copies the draw buffer to the DPI panel framebuffer via DMA.
// lv_display_flush_ready() is called by on_color_trans_done when DMA completes.
static void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map) {
    esp_lcd_panel_handle_t panel_handle = (esp_lcd_panel_handle_t)lv_display_get_user_data(disp);
    esp_lcd_panel_draw_bitmap(panel_handle, area->x1, area->y1, area->x2 + 1, area->y2 + 1, px_map);
}

// DMA transfer done callback - signals LVGL that flush is complete.
static bool IRAM_ATTR on_color_trans_done(esp_lcd_panel_handle_t panel,
                                          esp_lcd_dpi_panel_event_data_t *edata,
                                          void *user_ctx) {
    lv_display_t *disp = (lv_display_t *)user_ctx;
    lv_display_flush_ready(disp);
    return false;
}

// Enable MIPI-DSI PHY power (ESP32-P4 specific)
static esp_err_t enable_dsi_phy_power(void) {
    esp_ldo_channel_handle_t ldo_mipi_phy = NULL;
    esp_ldo_channel_config_t ldo_cfg = {
        .chan_id = MIPI_DSI_PHY_PWR_LDO_CHAN,
        .voltage_mv = MIPI_DSI_PHY_PWR_LDO_VOLTAGE_MV,
    };
    esp_err_t ret = esp_ldo_acquire_channel(&ldo_cfg, &ldo_mipi_phy);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "MIPI DSI PHY powered on (LDO3 @ 2.5V)");
    }
    return ret;
}

// Initialize backlight
static void init_backlight(void) {
#if LCD_BL_GPIO >= 0
    gpio_config_t bl_cfg = {
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = 1ULL << LCD_BL_GPIO,
    };
    gpio_config(&bl_cfg);
    gpio_set_level(LCD_BL_GPIO, 0);  // Off initially
#endif
}

// Set backlight level
static void set_backlight(bool on) {
#if LCD_BL_GPIO >= 0
    gpio_set_level(LCD_BL_GPIO, on ? 1 : 0);
#endif
}

// Main driver initialization using ST7701 component wrapper
static void st7701_driver_init(void) {
    if (s_initialized) {
        return;
    }

    ESP_LOGI(TAG, "Initializing ST7701 MIPI-DSI display driver");
    ESP_LOGI(TAG, "Resolution: %dx%d, %d bpp", LCD_H_RES, LCD_V_RES, LCD_BIT_PER_PIXEL);

    // Step 1: Initialize backlight (off)
    init_backlight();

    // Step 2: Enable MIPI-DSI PHY power
    ESP_ERROR_CHECK(enable_dsi_phy_power());

    // Step 3: Create MIPI-DSI bus
    esp_lcd_dsi_bus_config_t bus_config = {
        .bus_id = 0,
        .num_data_lanes = 2,  // 2-lane DSI
        .phy_clk_src = MIPI_DSI_PHY_CLK_SRC_DEFAULT,
        .lane_bit_rate_mbps = MIPI_DSI_LANE_BITRATE_MBPS,
    };
    ESP_ERROR_CHECK(esp_lcd_new_dsi_bus(&bus_config, &s_dsi_bus));
    ESP_LOGI(TAG, "MIPI-DSI bus created (2 lanes @ %d Mbps)", MIPI_DSI_LANE_BITRATE_MBPS);

    // Step 4: Create DBI panel IO for sending commands
    esp_lcd_dbi_io_config_t dbi_config = {
        .virtual_channel = 0,
        .lcd_cmd_bits = 8,
        .lcd_param_bits = 8,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_dbi(s_dsi_bus, &dbi_config, &s_io));
    ESP_LOGI(TAG, "DBI panel IO created");

    // Step 5: Configure DPI panel (video mode) settings
    esp_lcd_dpi_panel_config_t dpi_config = {
        .dpi_clk_src = MIPI_DSI_DPI_CLK_SRC_DEFAULT,
        .dpi_clock_freq_mhz = MIPI_DPI_CLK_MHZ,
        .virtual_channel = 0,
        .pixel_format = LCD_COLOR_PIXEL_FORMAT_RGB565,
        .num_fbs = 2,  // Double buffering for smoother display
        .video_timing = {
            .h_size = LCD_H_RES,
            .v_size = LCD_V_RES,
            .hsync_back_porch = 42,
            .hsync_pulse_width = 12,
            .hsync_front_porch = 42,
            .vsync_back_porch = 8,
            .vsync_pulse_width = 2,
            .vsync_front_porch = 166,
        },
        .flags = {
            .use_dma2d = true,
        },
    };

    // Step 6: Configure ST7701 vendor settings
    st7701_vendor_config_t vendor_config = {
        .init_cmds = st7701_init_cmds,
        .init_cmds_size = sizeof(st7701_init_cmds) / sizeof(st7701_init_cmds[0]),
        .mipi_config = {
            .dsi_bus = s_dsi_bus,
            .dpi_config = &dpi_config,
        },
        .flags = {
            .use_mipi_interface = 1,
            .mirror_by_cmd = 1,
        },
    };

    // Step 7: Create ST7701 panel using the component wrapper
    esp_lcd_panel_dev_config_t panel_dev_config = {
        .reset_gpio_num = LCD_RST_GPIO,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .bits_per_pixel = LCD_BIT_PER_PIXEL,
        .vendor_config = &vendor_config,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_st7701(s_io, &panel_dev_config, &s_panel));
    ESP_LOGI(TAG, "ST7701 panel created");

    // Step 8: Reset and initialize panel (ST7701 wrapper handles init commands)
    ESP_ERROR_CHECK(esp_lcd_panel_reset(s_panel));
    ESP_LOGI(TAG, "Panel reset complete");
    ESP_ERROR_CHECK(esp_lcd_panel_init(s_panel));
    ESP_LOGI(TAG, "Panel initialized");

    // Note: No mirror call needed - the init commands set correct orientation
    // If display still appears mirrored, uncomment below:
    // ESP_ERROR_CHECK(esp_lcd_panel_mirror(s_panel, true, false));  // try mirror_x=true
    ESP_LOGI(TAG, "Panel orientation: default (no mirror)");

    // Step 8b: Turn display on explicitly (required for some ST7701 panels)
    ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(s_panel, true));
    ESP_LOGI(TAG, "Display turned on");

    // Step 9: Initialize LVGL
    lv_init();
    lv_tick_set_cb(tick_cb);

    // Step 10: Create LVGL display
    s_disp = lv_display_create(LCD_H_RES, LCD_V_RES);
    lv_display_set_color_format(s_disp, LV_COLOR_FORMAT_RGB565);
    lv_display_set_user_data(s_disp, s_panel);
    lv_display_set_flush_cb(s_disp, flush_cb);

    // Step 11: Allocate separate draw buffers for PARTIAL mode
    // PARTIAL mode uses its own buffers (not DPI framebuffers). LVGL renders into
    // these, then flush_cb copies dirty regions to the panel framebuffer via DMA.
    // This avoids tearing because LVGL never writes directly into the scanning buffer.
    size_t draw_buf_size = LCD_H_RES * 100 * sizeof(uint16_t);  // 100-line draw buffer
    void *buf1 = heap_caps_malloc(draw_buf_size, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    void *buf2 = heap_caps_malloc(draw_buf_size, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    assert(buf1 && buf2);
    ESP_LOGI(TAG, "Using PARTIAL mode: buf1=%p, buf2=%p, size=%zu", buf1, buf2, draw_buf_size);
    lv_display_set_buffers(s_disp, buf1, buf2, draw_buf_size, LV_DISPLAY_RENDER_MODE_PARTIAL);

    // Step 12: Register DPI event callbacks
    esp_lcd_dpi_panel_event_callbacks_t cbs = {
        .on_color_trans_done = on_color_trans_done,
    };
    ESP_ERROR_CHECK(esp_lcd_dpi_panel_register_event_callbacks(s_panel, &cbs, s_disp));

    // Step 13: Clear DPI framebuffers to black before turning on backlight
    // The DPI panel starts scanning immediately after init, but the framebuffers
    // contain random PSRAM data. Clear both to prevent garbage on first display.
    void *fb0 = NULL;
    void *fb1_dpi = NULL;
    ESP_ERROR_CHECK(esp_lcd_dpi_panel_get_frame_buffer(s_panel, 2, &fb0, &fb1_dpi));
    size_t fb_size = LCD_H_RES * LCD_V_RES * sizeof(uint16_t);
    memset(fb0, 0, fb_size);
    memset(fb1_dpi, 0, fb_size);

    // Step 14: Force initial LVGL render to flush clean screen
    lv_obj_invalidate(lv_screen_active());
    lv_timer_handler();

    // Step 15: Turn on backlight
    set_backlight(true);
    
    s_initialized = true;
    ESP_LOGI(TAG, "ST7701 display initialized successfully");
}

// MicroPython: init_display()
static mp_obj_t lvgl_init_display(void) {
    st7701_driver_init();
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_init_display_obj, lvgl_init_display);

// MicroPython: deinit_display()
static mp_obj_t lvgl_deinit_display(void) {
    if (!s_initialized) {
        return mp_const_none;
    }
    // Clean up LVGL objects
    lv_obj_t *screen = lv_screen_active();
    if (screen) lv_obj_clean(screen);
    lv_obj_t *top = lv_layer_top();
    if (top) lv_obj_clean(top);
    lv_obj_t *sys = lv_layer_sys();
    if (sys) lv_obj_clean(sys);
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_deinit_display_obj, lvgl_deinit_display);

// MicroPython: timer_handler()
static mp_obj_t lvgl_timer_handler(void) {
    uint32_t ms = lv_timer_handler();
    return mp_obj_new_int_from_uint(ms);
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_timer_handler_obj, lvgl_timer_handler);

// MicroPython: backlight(on)
static mp_obj_t lvgl_backlight(mp_obj_t on_obj) {
    set_backlight(mp_obj_is_true(on_obj));
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_1(lvgl_backlight_obj, lvgl_backlight);
