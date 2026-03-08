# GUITION JC4880P443C Board Reference

Board: GUITION JC4880P443C_I_W
Product: [AliExpress listing](https://www.aliexpress.com/item/1005009618259341.html)
Review: [CNX Software](https://www.cnx-software.com/2025/08/12/4-3-inch-touch-display-board-features-single-esp32-p4-esp32-c6-module-supports-camera-and-speakers/)
Example Code: [Hello World (Arduino)](https://github.com/cubcrafts/Guition-JC4880P443C_I_W---Hello-World-Example)
BSP (ESP-IDF): [csvke/esp32_p4_jc4880p433c_bsp](https://github.com/csvke/esp32_p4_jc4880p433c_bsp)
P4-C6 Comms + SD Card: [buccaneer-jak/JC4880P443C](https://github.com/buccaneer-jak/JC4880P443C-P4-to-C6-RS232-communication-and-SD-Card-connection)
LVGL-MicroPython Issue: [lvgl-micropython#518](https://github.com/lvgl-micropython/lvgl_micropython/issues/518)

## Overview

- **MCU**: ESP32-P4 (dual-core RISC-V, up to 400MHz) + ESP32-C6 coprocessor (WiFi/BLE)
- **Display**: 4.3" IPS TFT LCD, 480x800, ST7701S controller, MIPI DSI interface (2-lane)
- **Touch**: Capacitive touch, GT911 controller (I2C)
- **Wireless**: WiFi 6 (802.11ax), Bluetooth 5 LE, Zigbee/Thread (via ESP32-C6 over SDIO)
- **Memory**: 768KB HP L2MEM, 32KB LP SRAM, 128KB HP ROM
- **PSRAM**: 32MB
- **Flash**: 16MB
- **Audio**: ES8311 audio codec, NS4150B audio PA, onboard microphone, speaker connector
- **Camera**: MIPI CSI connector, OV02C10 2MP sensor (I2C control at 0x36)
- **Storage**: MicroSD card slot (SDMMC 4-bit mode)
- **Other**: UART connector, RS-485 connector, I2C connector, 26-pin GPIO header, lithium battery interface

## USB Ports

This board has **two USB Type-C ports**, both connected to the ESP32-P4:

| USB-C Port       | ESP32-P4 Peripheral     | Purpose                                        | Serial device? |
|-------------------|-------------------------|-------------------------------------------------|----------------|
| USB Serial/JTAG   | Built-in USB-Serial/JTAG | Firmware flashing (esptool), JTAG debug, REPL   | Yes            |
| USB Full-speed OTG | USB 2.0 OTG             | USB device/host mode, power                     | No             |

The ESP32-C6 coprocessor has **no external USB port**. It communicates with the
P4 over SDIO and is pre-flashed with ESP-Hosted slave firmware. To reflash the
C6, use the dedicated UART programming header with an external USB-UART adapter
(e.g., ESP-Prog).

**For all firmware operations, use the USB Serial/JTAG port** (the one that
shows up as `/dev/cu.usbmodemXXXX` on macOS).

### Identifying the Correct Port

```bash
# List USB serial devices
ls /dev/cu.usb*

# Verify it's the P4 (not a different board)
esptool.py --port /dev/cu.usbmodem1101 chip_id
# Should report: "Detecting chip type... ESP32-P4"
```

## GPIO Pin Mapping

### Display (MIPI DSI -- ST7701S)

The ST7701S display uses the ESP32-P4's **MIPI DSI** peripheral (not SPI, not
parallel RGB GPIO). The DSI data lanes are internal differential pairs routed
through the MIPI PHY -- they do not consume GPIO pins.

| Function       | ESP32-P4 GPIO | Notes                                    |
|----------------|---------------|------------------------------------------|
| LCD_RST        | GPIO 5        | Reset signal (Kconfig default; some boards NC) |
| LCD_BL         | GPIO 23       | PWM backlight control via LEDC (20 kHz)  |
| DSI PHY power  | --            | Internal LDO channel 3 @ 2500 mV         |
| DSI data lanes | --            | Internal MIPI PHY (2-lane, 500 Mbps/lane) |

### Display Configuration

| Parameter              | Value                      |
|------------------------|----------------------------|
| H_RES                  | 480                        |
| V_RES                  | 800                        |
| Color format           | RGB565 (16-bit)            |
| Interface              | MIPI DSI (2-lane)          |
| DSI lane bitrate       | 500 Mbps/lane              |
| DPI clock              | 34 MHz (~60 Hz refresh)    |
| Frame buffers          | 2 (double-buffered in PSRAM) |
| Backlight PWM freq     | 20 kHz                     |
| Backlight resolution   | 10-bit (0-1023)            |

### Display Timing (DPI)

| Timing Parameter    | Value |
|---------------------|-------|
| HSYNC pulse width   | 12    |
| HSYNC back porch    | 42    |
| HSYNC front porch   | 42    |
| VSYNC pulse width   | 2     |
| VSYNC back porch    | 8     |
| VSYNC front porch   | 166   |

The full ST7701S vendor initialization sequence (~40 register commands) is
available in the BSP at
[bsp_display.c](https://github.com/csvke/esp32_p4_jc4880p433c_bsp/blob/main/src/bsp_display.c).
This sequence is board-specific and required for display bringup.

### Touch (I2C -- GT911)

| Function | ESP32-P4 GPIO | Notes                              |
|----------|---------------|------------------------------------|
| TP_SDA   | GPIO 7        | I2C data (shared with camera)      |
| TP_SCL   | GPIO 8        | I2C clock (shared with camera)     |
| TP_RST   | -1            | Not connected                      |
| TP_INT   | -1            | Not connected                      |

| Parameter       | Value                               |
|-----------------|-------------------------------------|
| I2C address     | 0x14 or 0x5D (auto-detect)          |
| I2C frequency   | 400 kHz                             |
| Pull-ups        | External hardware (internal disabled) |
| Glitch filter   | 7 clock cycles                      |

**Note:** The I2C bus on GPIO7/8 is **shared** between the GT911 touch
controller and the OV02C10 camera sensor. Both devices coexist on the same bus.

### Camera (MIPI CSI -- OV02C10)

The camera uses the ESP32-P4's MIPI CSI peripheral. Like DSI, the CSI data
lanes are internal differential pairs through the MIPI PHY. Camera control
uses the shared I2C bus.

| Function         | ESP32-P4 GPIO | Notes                              |
|------------------|---------------|------------------------------------|
| I2C SDA (control)| GPIO 7        | Shared with GT911 touch            |
| I2C SCL (control)| GPIO 8        | Shared with GT911 touch            |
| CSI data lanes   | --            | Internal MIPI PHY (1 or 2 lane)    |
| CSI clock        | --            | Internal MIPI PHY                  |
| Reset            | NC            | Not connected (configurable)       |
| Power-down       | NC            | Not connected (configurable)       |

| Parameter       | Value                               |
|-----------------|-------------------------------------|
| Sensor          | OV02C10 (OmniVision, 2MP)          |
| I2C address     | 0x36                                |
| Max resolution  | 1920x1080                           |
| Output format   | 10-bit RAW Bayer GBRG              |
| Modes           | 1288x728@30fps (1-lane), 1920x1080@30fps (1 or 2-lane) |

Camera connector pinout:

| CSI Connector Pin | Function                        |
|-------------------|---------------------------------|
| Pin 13            | I2C_SCL (GPIO 8) -- shared      |
| Pin 14            | I2C_SDA (GPIO 7) -- shared      |
| Differential      | MIPI CSI D0+/D0- (lane 0)      |
| Differential      | MIPI CSI D1+/D1- (lane 1, optional) |
| Differential      | MIPI CSI CLK+/CLK-             |

Camera sensor drivers are **not** part of the board BSP. They come from
[esp-video-components](https://github.com/espressif/esp-video-components)
(`esp_cam_sensor` component). See the BSP's
[CAMERA_INTEGRATION.md](https://github.com/csvke/esp32_p4_jc4880p433c_bsp/blob/main/CAMERA_INTEGRATION.md)
for integration details.

### Audio (I2S -- ES8311 + NS4150B)

| Function         | ESP32-P4 GPIO | Notes                              |
|------------------|---------------|------------------------------------|
| I2S_SCLK         | GPIO 12       | Bit clock                          |
| I2S_MCLK         | GPIO 13       | Master clock                       |
| I2S_LCLK         | GPIO 10       | Word select / LRCLK               |
| I2S_DOUT         | GPIO 9        | Speaker data out                   |
| I2S_DSIN         | GPIO 48       | Microphone data in                 |
| POWER_AMP_IO     | GPIO 11       | NS4150B amplifier enable           |

The ES8311 audio codec handles both speaker output and microphone input.
The NS4150B is a Class-D audio power amplifier for the speaker.

### P4 <-> C6 SDIO Interface (WiFi/BLE)

The ESP32-C6 coprocessor communicates with the P4 over a 4-bit SDIO bus
using the ESP-Hosted protocol.

| Function         | ESP32-P4 GPIO | Notes                              |
|------------------|---------------|------------------------------------|
| SDIO CMD         | GPIO 19       | Command line                       |
| SDIO CLK         | GPIO 18       | Clock signal                       |
| SDIO D0          | GPIO 14       | Data line 0                        |
| SDIO D1          | GPIO 15       | Data line 1                        |
| SDIO D2          | GPIO 16       | Data line 2                        |
| SDIO D3          | GPIO 17       | Data line 3                        |
| C6 Reset         | GPIO 54       | C6_CHIP_PU (reset control)         |

| Parameter       | Value                               |
|-----------------|-------------------------------------|
| Bus width       | 4-bit                               |
| Clock           | 40 MHz                              |
| Protocol        | ESP-Hosted                          |
| ESP-IDF deps    | `esp_hosted`, `esp_wifi_remote`     |

Standard `esp_wifi_*` APIs work transparently -- the ESP-Hosted + WiFi Remote
layer makes WiFi calls on the P4 execute on the C6 radio.

### SD Card (SDMMC)

| Function         | ESP32-P4 GPIO | Notes                              |
|------------------|---------------|------------------------------------|
| SD_CLK           | GPIO 43       | Clock                              |
| SD_CMD           | GPIO 44       | Command                            |
| SD_DATA0         | GPIO 39       | Data line 0                        |
| SD_DATA1         | GPIO 40       | Data line 1                        |
| SD_DATA2         | GPIO 42       | Data line 2                        |
| SD_DATA3         | GPIO 41       | Data line 3                        |

Mode: 4-bit SDMMC. Tested and verified working with FAT32-formatted cards.

### P4 <-> C6 UART (JP1 Header)

For serial communication between the P4 and C6 (separate from SDIO WiFi).
Also used for reflashing the C6 firmware via external USB-UART adapter.

| Function         | ESP32-P4 GPIO | JP1 Pin | Notes                       |
|------------------|---------------|---------|------------------------------|
| P4 TX -> C6 RX   | GPIO 29       | Pin 14  | Also RMII_RXD0              |
| P4 RX <- C6 TX   | GPIO 30       | Pin 12  | Also RMII_RXD1              |

Baud rate: 115200 (8N1). These GPIOs double as RMII Ethernet pins but are
used for UART on this board.

**Programming the C6:** Connect ESP-Prog to JP1 pin 20 (C6_U0RXD) and pin 22
(C6_U0TXD). Note: C6_U0TXD connects to ESP-TXD and C6_U0RXD to ESP-RXD.

### RMII Ethernet Pins (Header -- Not Used for WiFi)

These pins are exposed on the board header for potential Ethernet PHY support.
They are **not used** for WiFi (WiFi uses the SDIO interface above).

| Function     | ESP32-P4 GPIO |
|--------------|---------------|
| RMII_RXDV    | GPIO 28       |
| RMII_RXD0    | GPIO 29       |
| RMII_RXD1    | GPIO 30       |
| MDC          | GPIO 31       |
| RMII_TXD0    | GPIO 34       |
| RMII_TXD1    | GPIO 35       |
| RMII_TXEN    | GPIO 49       |
| RMII_CLK     | GPIO 50       |
| PHY_RSTN     | GPIO 51       |
| MDIO         | GPIO 52       |

### Complete GPIO Summary

| GPIO | Function               | Peripheral                          |
|------|------------------------|-------------------------------------|
| 5    | LCD_RST                | Display reset (configurable)        |
| 7    | I2C SDA                | Touch (GT911) + Camera (OV02C10)    |
| 8    | I2C SCL                | Touch (GT911) + Camera (OV02C10)    |
| 9    | I2S DOUT               | Audio (ES8311) speaker data         |
| 10   | I2S LCLK               | Audio (ES8311) word select          |
| 11   | POWER_AMP_IO           | Audio (NS4150B) amplifier enable    |
| 12   | I2S SCLK               | Audio (ES8311) bit clock            |
| 13   | I2S MCLK               | Audio (ES8311) master clock         |
| 14   | SDIO D0                | P4<->C6 WiFi                       |
| 15   | SDIO D1                | P4<->C6 WiFi                       |
| 16   | SDIO D2                | P4<->C6 WiFi                       |
| 17   | SDIO D3                | P4<->C6 WiFi                       |
| 18   | SDIO CLK               | P4<->C6 WiFi                       |
| 19   | SDIO CMD               | P4<->C6 WiFi                       |
| 23   | LCD_BL                 | Display backlight (PWM)             |
| 28   | RMII_RXDV              | Ethernet (header, unused)           |
| 29   | UART TX / RMII_RXD0    | P4<->C6 serial / Ethernet          |
| 30   | UART RX / RMII_RXD1    | P4<->C6 serial / Ethernet          |
| 31   | MDC                    | Ethernet (header, unused)           |
| 34   | RMII_TXD0              | Ethernet (header, unused)           |
| 35   | RMII_TXD1              | Ethernet (header, unused)           |
| 39   | SD_DATA0               | MicroSD card                        |
| 40   | SD_DATA1               | MicroSD card                        |
| 41   | SD_DATA3               | MicroSD card                        |
| 42   | SD_DATA2               | MicroSD card                        |
| 43   | SD_CLK                 | MicroSD card                        |
| 44   | SD_CMD                 | MicroSD card                        |
| 48   | I2S DSIN               | Audio (ES8311) mic input            |
| 49   | RMII_TXEN              | Ethernet (header, unused)           |
| 50   | RMII_CLK               | Ethernet (header, unused)           |
| 51   | PHY_RSTN               | Ethernet (header, unused)           |
| 52   | MDIO                   | Ethernet (header, unused)           |
| 54   | C6_CHIP_PU             | C6 reset control                    |
| --   | MIPI DSI lanes         | Display (internal PHY)              |
| --   | MIPI CSI lanes         | Camera (internal PHY)               |

## Architecture

```
+-------------------------------------------+
|         GUITION JC4880P443C               |
|                                           |
|  +----------+    SDIO    +----------+     |
|  | ESP32-P4 |<---------->| ESP32-C6 |     |
|  | (main)   | GPIO 14-19 | (WiFi/BT)|     |
|  +--+--+--+-+            +-----+----+     |
|     |  |  |                    |          |
|   USB USB MIPI-DSI        UART header     |
|   JTAG OTG (display)     (ESP-Prog)      |
|     |  |  |                               |
|   [C1][C2][LCD]                           |
|                                           |
|  C1 = Flash/Debug/REPL (use this one)     |
|  C2 = USB OTG / Power                    |
|                                           |
|  I2C bus (GPIO 7/8):                      |
|    GT911 touch (0x14/0x5D)                |
|    OV02C10 camera (0x36)                  |
|                                           |
|  I2S (GPIO 9-13, 48):                     |
|    ES8311 codec + NS4150B PA              |
|                                           |
|  SDMMC (GPIO 39-44):                      |
|    MicroSD card slot                      |
+-------------------------------------------+
```

## MicroPython Build Configuration

### Board and Variant

```bash
BOARD=ESP32_GENERIC_P4
BOARD_VARIANT=C6_WIFI
PORT=/dev/cu.usbmodem1101    # macOS typical (verify with esptool)
```

### Prerequisites

- **ESP-IDF**: v5.4.2+ (with `esp32p4` toolchain installed)
- **MicroPython**: v1.27.0+ (first version with `ESP32_GENERIC_P4` board)

### Build + Flash

```bash
# Build firmware
make build BOARD=ESP32_GENERIC_P4 BOARD_VARIANT=C6_WIFI

# Erase flash (first time only)
make erase BOARD=ESP32_GENERIC_P4 PORT=/dev/cu.usbmodem1101

# Flash firmware
make flash BOARD=ESP32_GENERIC_P4 BOARD_VARIANT=C6_WIFI PORT=/dev/cu.usbmodem1101

# Open REPL
make repl PORT=/dev/cu.usbmodem1101
```

### Build Output

The `C6_WIFI` variant automatically configures:

| Setting              | Value                                         |
|----------------------|-----------------------------------------------|
| IDF_TARGET           | esp32p4                                       |
| Flash mode           | QIO, 16MB                                     |
| SPIRAM               | Enabled (32MB on this board)                  |
| WiFi/BLE             | Via ESP-Hosted framework (C6 over SDIO)       |
| sdkconfig            | sdkconfig.base + sdkconfig.p4 + sdkconfig.p4_wifi_common + sdkconfig.p4_wifi_c6 |
| Build directory      | build-ESP32_GENERIC_P4-C6_WIFI/               |
| Flash offset         | 0x2000                                        |

### Pre-built Firmware

Official pre-built binaries (no custom C modules) are available at:
[micropython.org/download/ESP32_GENERIC_P4](https://micropython.org/download/ESP32_GENERIC_P4/)

Download the **"Support for external C6 WiFi/BLE"** variant.

```bash
# Flash pre-built binary directly
esptool.py --port /dev/cu.usbmodem1101 erase_flash
esptool.py --port /dev/cu.usbmodem1101 --baud 460800 write_flash 0x2000 firmware.bin
```

## Display Support Status

**Base MicroPython does not include a display driver for this board.** The
ST7701S uses the MIPI DSI interface which requires platform-specific ESP-IDF
drivers (`esp_lcd_mipi_dsi`, `esp_lcd_st7701`).

Options for display support:

1. **lvgl_micropython** -- Community project working on ESP32-P4 support
   ([issue #518](https://github.com/lvgl-micropython/lvgl_micropython/issues/518)).
   Not yet merged as of March 2026.

2. **Custom framebuffer driver** -- Write a MicroPython C module that
   initializes the MIPI DSI bus and exposes a framebuffer. Requires porting
   the ST7701S init sequence from the BSP.

3. **ESP-IDF native** -- Use the csvke BSP directly with ESP-IDF. Production-
   ready but not MicroPython-compatible without integration work.

Key resources for display bringup:
- [BSP display source](https://github.com/csvke/esp32_p4_jc4880p433c_bsp/blob/main/src/bsp_display.c) -- ST7701S init sequence and MIPI DSI configuration
- [ESP-IDF MIPI DSI docs](https://docs.espressif.com/projects/esp-idf/en/latest/esp32p4/api-reference/peripherals/lcd/mipi_dsi.html)
- [esp_lcd_st7701 component](https://components.espressif.com/components/espressif/esp_lcd_st7701)

## Troubleshooting

- **esptool detects ESP32-C6 instead of P4**: You are connected to a different board or the C6 programming header. Verify with `esptool.py chip_id` -- it must report `ESP32-P4`.
- **Only one USB device appears with both cables**: This is normal. Only the USB Serial/JTAG port creates a serial device. The OTG port does not.
- **WiFi not working**: The C6 coprocessor must have compatible ESP-Hosted slave firmware. If you see "Version on Host is NEWER than version on co-processor" warnings, the C6 firmware needs updating via the UART programming header.
- **Display not working with MicroPython**: The ST7701S uses MIPI DSI interface which requires platform-specific display driver support. See "Display Support Status" section above.
- **Boot mode**: Hold BOOT, press RESET, release RESET, release BOOT to enter download mode if automatic flashing fails.
- **Touch not responding**: Verify I2C connections (SCL=GPIO8, SDA=GPIO7). Check GT911 power supply. Use `i2cdetect` to scan bus (GT911 address: 0x14 or 0x5D).
- **Camera not detected**: Camera shares I2C bus with touch (GPIO7/8). Verify power supply and check I2C scan for address 0x36 (OV02C10).
- **SD card mount failed**: Card must be FAT32 formatted. Uses SDMMC 4-bit mode on GPIO 39-44.

## Comparison with ESP32-C6 Board

| Feature         | Waveshare ESP32-C6-LCD-1.47 | GUITION JC4880P443C        |
|-----------------|------------------------------|----------------------------|
| Main MCU        | ESP32-C6 (single RISC-V)    | ESP32-P4 (dual RISC-V)     |
| Clock           | 160 MHz                      | 400 MHz                    |
| WiFi/BLE        | Native on chip               | Via C6 coprocessor (SDIO)  |
| Flash           | 4 MB                         | 16 MB                      |
| PSRAM           | None                         | 32 MB                      |
| Display         | 1.47" SPI (ST7789)           | 4.3" MIPI DSI (ST7701S)    |
| Touch           | None                         | Capacitive (GT911)         |
| Camera          | None                         | MIPI CSI (OV02C10 2MP)     |
| Audio           | None                         | ES8311 + NS4150B           |
| SD Card         | None                         | SDMMC 4-bit                |
| Board target    | ESP32_GENERIC_C6             | ESP32_GENERIC_P4            |
| Board variant   | (none)                       | C6_WIFI                    |
| Flash offset    | 0x0                          | 0x2000                     |

## Community Resources

- [csvke/esp32_p4_jc4880p433c_bsp](https://github.com/csvke/esp32_p4_jc4880p433c_bsp) -- Production-ready ESP-IDF BSP with display, touch, camera, I2C, SPIFFS support
- [cubcrafts/Guition-JC4880P443C_I_W](https://github.com/cubcrafts/Guition-JC4880P443C_I_W---Hello-World-Example) -- Arduino Hello World with LVGL
- [buccaneer-jak/JC4880P443C](https://github.com/buccaneer-jak/JC4880P443C-P4-to-C6-RS232-communication-and-SD-Card-connection) -- P4<->C6 UART communication and SD card test
- [csvke/phone_p4_JC4880P433C](https://github.com/csvke/phone_p4_JC4880P433C) -- ESP-Brookesia phone UI demo project
- [lvgl-micropython#518](https://github.com/lvgl-micropython/lvgl_micropython/issues/518) -- MicroPython/LVGL support request
- [ESP-Hosted](https://github.com/espressif/esp-hosted) -- ESP-IDF WiFi proxy framework (P4<->C6)
- [esp-video-components](https://github.com/espressif/esp-video-components) -- Camera sensor drivers (OV02C10)
