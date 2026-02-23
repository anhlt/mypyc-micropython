# Waveshare ESP32-C6-LCD-1.47 Board Reference

Board: [ESP32-C6-LCD-1.47](https://www.waveshare.com/esp32-c6-lcd-1.47.htm)
Wiki: [ESP32-C6-LCD-1.47 Wiki](https://www.waveshare.com/wiki/ESP32-C6-LCD-1.47)

## Overview

- **MCU**: ESP32-C6FH4 (RISC-V, 160MHz single-core, 4MB flash built-in)
- **Display**: 1.47" TFT LCD, 172x320, 262K color, ST7789 controller
- **Wireless**: WiFi 6 (802.11ax), Bluetooth 5, Zigbee 3.0, Thread (802.15.4)
- **Memory**: 320KB ROM, 512KB HP SRAM, 16KB LP SRAM, 4MB Flash
- **LDO**: ME6217C33M5G (800mA max)
- **USB**: Full-speed USB serial (Type-C)
- **Other**: TF card slot, BOOT button, RESET button, patch ceramic antenna

## GPIO Pin Mapping

### LCD (SPI)

| LCD Pin  | ESP32-C6 GPIO | Notes            |
|----------|---------------|------------------|
| MOSI     | GPIO6         | Shared with TF   |
| SCLK     | GPIO7         | Shared with TF   |
| LCD_CS   | GPIO14        |                  |
| LCD_DC   | GPIO15        |                  |
| LCD_RST  | GPIO21        |                  |
| LCD_BL   | GPIO22        | Backlight PWM    |

### RGB LED (WS2812 / NeoPixel)

| Function      | ESP32-C6 GPIO | Notes                              |
|---------------|---------------|------------------------------------|
| RGB_Control   | GPIO8         | Single-wire WS2812 addressable LED |

The RGB LED is a WS2812-style (NeoPixel) addressable LED. On MicroPython,
use the `neopixel` module:

```python
from machine import Pin
from neopixel import NeoPixel

np = NeoPixel(Pin(8), 1)  # 1 LED on GPIO8
np[0] = (255, 0, 0)       # Red
np.write()
```

### TF Card (SPI, shared bus with LCD)

| TF Card Pin | ESP32-C6 GPIO | Notes            |
|-------------|---------------|------------------|
| MISO        | GPIO5         |                  |
| MOSI        | GPIO6         | Shared with LCD  |
| SCLK        | GPIO7         | Shared with LCD  |
| CS          | GPIO4         |                  |
| SD_D1       | NC            |                  |
| SD_D2       | NC            |                  |

### Buttons

| Button | Function                                 |
|--------|------------------------------------------|
| BOOT   | Hold during reset to enter download mode  |
| RESET  | Hardware reset                            |

## MicroPython Build Configuration

```bash
# This board uses the generic ESP32-C6 target
BOARD=ESP32_GENERIC_C6
PORT=/dev/cu.usbmodem2101    # macOS typical

# Build + flash
make build BOARD=ESP32_GENERIC_C6
make flash BOARD=ESP32_GENERIC_C6 PORT=/dev/cu.usbmodem2101
```

## Troubleshooting

- **Can't flash**: Hold BOOT, press RESET, release RESET, release BOOT to enter download mode
- **USB flicker/reset loop**: Flash may be blank. Enter download mode and flash firmware
- **Shared SPI bus**: LCD and TF card share MOSI (GPIO6) and SCLK (GPIO7) -- they use separate CS pins
