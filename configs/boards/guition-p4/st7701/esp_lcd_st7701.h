/*
 * SPDX-FileCopyrightText: 2023-2025 Espressif Systems (Shanghai) CO LTD
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#pragma once

#include <stdint.h>

#include "hal/lcd_types.h"
#include "esp_lcd_panel_vendor.h"
#include "esp_idf_version.h"

#if SOC_LCD_RGB_SUPPORTED
#include "esp_lcd_panel_rgb.h"
#endif

#if SOC_MIPI_DSI_SUPPORTED
#include "esp_lcd_mipi_dsi.h"
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define ESP_LCD_ST7701_VER_MAJOR 2
#define ESP_LCD_ST7701_VER_MINOR 0
#define ESP_LCD_ST7701_VER_PATCH 2

/**
 * @brief LCD panel initialization commands.
 */
typedef struct {
    int cmd;                /*<! The specific LCD command */
    const void *data;       /*<! Buffer that holds the command specific data */
    size_t data_bytes;      /*<! Size of `data` in memory, in bytes */
    unsigned int delay_ms;  /*<! Delay in milliseconds after this command */
} st7701_lcd_init_cmd_t;

/**
 * @brief LCD panel vendor configuration.
 */
typedef struct {
    const st7701_lcd_init_cmd_t *init_cmds;
    uint16_t init_cmds_size;
#if SOC_MIPI_DSI_SUPPORTED
    struct {
        esp_lcd_dsi_bus_handle_t dsi_bus;
        const esp_lcd_dpi_panel_config_t *dpi_config;
    } mipi_config;
#endif
    struct {
        unsigned int use_mipi_interface: 1;
        unsigned int mirror_by_cmd: 1;
        unsigned int auto_del_panel_io: 1;
    } flags;
} st7701_vendor_config_t;

/**
 * @brief Create LCD panel for model ST7701
 */
esp_err_t esp_lcd_new_panel_st7701(const esp_lcd_panel_io_handle_t io, const esp_lcd_panel_dev_config_t *panel_dev_config, esp_lcd_panel_handle_t *ret_panel);

#ifdef __cplusplus
}
#endif
