/**
 * GT911 Capacitive Touch Driver for GUITION JC4880P443C (ESP32-P4)
 * 
 * Touch: GT911 via I2C (SDA=GPIO7, SCL=GPIO8)
 * 
 * Based on:
 * - Espressif esp_lcd_touch_gt911 component
 * - cubcrafts/Guition-JC4880P443C_I_W---Hello-World-Example
 */

#include "py/runtime.h"
#include "py/obj.h"

#include "lvgl.h"

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_err.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "gt911_touch";

// GT911 I2C configuration
#define TOUCH_I2C_SDA       GPIO_NUM_7
#define TOUCH_I2C_SCL       GPIO_NUM_8
#define TOUCH_I2C_ADDR      0x5D        // GT911 address (INT pin LOW at power-on)
#define TOUCH_I2C_FREQ_HZ   400000      // 400kHz I2C

// Touch RST/INT pins (not connected on GUITION board per docs)
#define TOUCH_RST_GPIO      GPIO_NUM_NC
#define TOUCH_INT_GPIO      GPIO_NUM_NC

// Display dimensions (must match display driver)
#define LCD_H_RES           480
#define LCD_V_RES           800

// GT911 register addresses
#define GT911_REG_PRODUCT_ID    0x8140
#define GT911_REG_CONFIG        0x8047
#define GT911_REG_STATUS        0x814E
#define GT911_REG_POINT1        0x814F

// Touch data structures
typedef struct {
    uint16_t x;
    uint16_t y;
    uint16_t strength;
    uint8_t track_id;
} touch_point_t;

// Driver state
static bool s_touch_initialized = false;
static i2c_master_bus_handle_t s_i2c_bus = NULL;
static i2c_master_dev_handle_t s_i2c_dev = NULL;
static lv_indev_t *s_indev = NULL;
static touch_point_t s_last_point = {0};
static bool s_pressed = false;

// I2C read helper
static esp_err_t gt911_read_reg(uint16_t reg, uint8_t *data, size_t len) {
    uint8_t reg_buf[2] = {(reg >> 8) & 0xFF, reg & 0xFF};
    
    esp_err_t ret = i2c_master_transmit_receive(s_i2c_dev, reg_buf, 2, data, len, 100);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C read reg 0x%04X failed: %d", reg, ret);
    }
    return ret;
}

// I2C write helper
static esp_err_t gt911_write_reg(uint16_t reg, uint8_t value) {
    uint8_t buf[3] = {(reg >> 8) & 0xFF, reg & 0xFF, value};
    
    esp_err_t ret = i2c_master_transmit(s_i2c_dev, buf, 3, 100);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2C write reg 0x%04X failed: %d", reg, ret);
    }
    return ret;
}

// Read touch data from GT911
static bool gt911_read_touch(touch_point_t *point) {
    uint8_t status;
    
    // Read status register
    if (gt911_read_reg(GT911_REG_STATUS, &status, 1) != ESP_OK) {
        return false;
    }
    
    // Check if touch data is ready (bit 7 = buffer status)
    if ((status & 0x80) == 0) {
        return false;  // No new data
    }
    
    // Get number of touch points (bits 0-3)
    uint8_t touch_cnt = status & 0x0F;
    
    // Clear status register
    gt911_write_reg(GT911_REG_STATUS, 0);
    
    if (touch_cnt == 0 || touch_cnt > 5) {
        return false;  // No valid touch or error
    }
    
    // Read first touch point (8 bytes: track_id, x_low, x_high, y_low, y_high, size_low, size_high, reserved)
    uint8_t buf[8];
    if (gt911_read_reg(GT911_REG_POINT1, buf, 8) != ESP_OK) {
        return false;
    }
    
    // Parse coordinates
    point->track_id = buf[0];
    point->x = ((uint16_t)buf[2] << 8) | buf[1];
    point->y = ((uint16_t)buf[4] << 8) | buf[3];
    point->strength = ((uint16_t)buf[6] << 8) | buf[5];
    
    return true;
}

// LVGL input device read callback
static void touch_read_cb(lv_indev_t *indev, lv_indev_data_t *data) {
    touch_point_t point;
    
    if (gt911_read_touch(&point)) {
        // Touch detected
        s_last_point = point;
        s_pressed = true;
        
        data->point.x = point.x;
        data->point.y = point.y;
        data->state = LV_INDEV_STATE_PRESSED;
    } else {
        // No touch or released
        if (s_pressed) {
            // Return last known position with released state
            data->point.x = s_last_point.x;
            data->point.y = s_last_point.y;
        }
        data->state = LV_INDEV_STATE_RELEASED;
        s_pressed = false;
    }
}

// Initialize GT911 touch driver
esp_err_t gt911_touch_init(void) {
    if (s_touch_initialized) {
        return ESP_OK;
    }
    
    ESP_LOGI(TAG, "Initializing GT911 touch driver");
    ESP_LOGI(TAG, "I2C: SDA=%d, SCL=%d, Addr=0x%02X", TOUCH_I2C_SDA, TOUCH_I2C_SCL, TOUCH_I2C_ADDR);
    
    // Initialize I2C bus
    i2c_master_bus_config_t bus_config = {
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .i2c_port = I2C_NUM_0,
        .sda_io_num = TOUCH_I2C_SDA,
        .scl_io_num = TOUCH_I2C_SCL,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    
    esp_err_t ret = i2c_new_master_bus(&bus_config, &s_i2c_bus);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create I2C bus: %d", ret);
        return ret;
    }
    
    // Add GT911 device
    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = TOUCH_I2C_ADDR,
        .scl_speed_hz = TOUCH_I2C_FREQ_HZ,
    };
    
    ret = i2c_master_bus_add_device(s_i2c_bus, &dev_config, &s_i2c_dev);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to add I2C device: %d", ret);
        return ret;
    }
    
    // Read and verify product ID
    uint8_t product_id[4];
    ret = gt911_read_reg(GT911_REG_PRODUCT_ID, product_id, 4);
    if (ret == ESP_OK) {
        ESP_LOGI(TAG, "GT911 Product ID: %c%c%c%c", 
                 product_id[0], product_id[1], product_id[2], product_id[3]);
    } else {
        ESP_LOGW(TAG, "Could not read GT911 product ID (may work anyway)");
    }
    
    // Register LVGL input device
    s_indev = lv_indev_create();
    lv_indev_set_type(s_indev, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(s_indev, touch_read_cb);
    
    s_touch_initialized = true;
    ESP_LOGI(TAG, "GT911 touch driver initialized");
    
    return ESP_OK;
}

// Deinitialize touch driver
void gt911_touch_deinit(void) {
    if (!s_touch_initialized) {
        return;
    }
    
    if (s_indev) {
        lv_indev_delete(s_indev);
        s_indev = NULL;
    }
    
    if (s_i2c_dev) {
        i2c_master_bus_rm_device(s_i2c_dev);
        s_i2c_dev = NULL;
    }
    
    if (s_i2c_bus) {
        i2c_del_master_bus(s_i2c_bus);
        s_i2c_bus = NULL;
    }
    
    s_touch_initialized = false;
}

// MicroPython bindings

// init_touch() -> None
static mp_obj_t lvgl_init_touch(void) {
    esp_err_t ret = gt911_touch_init();
    if (ret != ESP_OK) {
        mp_raise_OSError(ret);
    }
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_init_touch_obj, lvgl_init_touch);

// deinit_touch() -> None
static mp_obj_t lvgl_deinit_touch(void) {
    gt911_touch_deinit();
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_deinit_touch_obj, lvgl_deinit_touch);

// get_touch() -> tuple(x, y, pressed) or None
static mp_obj_t lvgl_get_touch(void) {
    if (!s_touch_initialized) {
        return mp_const_none;
    }
    
    touch_point_t point;
    if (gt911_read_touch(&point)) {
        mp_obj_t items[3] = {
            mp_obj_new_int(point.x),
            mp_obj_new_int(point.y),
            mp_const_true
        };
        return mp_obj_new_tuple(3, items);
    } else if (s_pressed) {
        // Return last known position as released
        mp_obj_t items[3] = {
            mp_obj_new_int(s_last_point.x),
            mp_obj_new_int(s_last_point.y),
            mp_const_false
        };
        s_pressed = false;
        return mp_obj_new_tuple(3, items);
    }
    
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_get_touch_obj, lvgl_get_touch);
