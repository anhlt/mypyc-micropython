# LVGL Display Driver on ESP32: From SPI Wires to Pixels on Screen

*Building a display driver for the Waveshare ESP32-C6-LCD-1.47, debugging a pointer corruption crash, and rendering live text from MicroPython.*

---

The previous post showed how `.pyi` stubs generate MicroPython C bindings for LVGL. But calling `lv_label_set_text` does nothing visible without a display driver -- the piece of code that takes rendered pixels and pushes them to the physical LCD over a wire. This post covers that missing piece: a 180-line C driver for the ST7789 display on the Waveshare ESP32-C6-LCD-1.47 board, the pointer wrapping bug that crashed the firmware, and the fix that made `"Good morning"` appear on screen.

## Table of Contents

1. [Display Driver Theory](#part-1-display-driver-theory) -- SPI, framebuffers, DMA, and LVGL's rendering model
2. [C Background](#part-2-c-background-for-python-developers) -- ESP-IDF components, ISR callbacks, static variables
3. [Implementation](#part-3-implementation) -- The ST7789 driver, the pointer bug, and live text rendering

---

# Part 1: Display Driver Theory

## How a Microcontroller Talks to a Display

A Python developer might think of a screen as a thing you write pixels to, like drawing on a canvas. On a microcontroller, the screen is a separate chip -- the ST7789 -- connected by wires. To change a pixel, the ESP32 must:

1. Encode the pixel color as two bytes (RGB565 format)
2. Send those bytes over a serial wire protocol (SPI)
3. Tell the ST7789 which row and column to write to

This happens for every pixel. A 172x320 display has 55,040 pixels. At 16 bits per pixel, that is 110,080 bytes per frame. The wire protocol, SPI, sends bits one at a time on a clock.

## SPI: Serial Peripheral Interface

SPI uses four wires:

```
ESP32-C6                         ST7789 Display
+----------+                     +----------+
|   GPIO6  |------- MOSI ------->|  SDA     |  (data: ESP32 -> display)
|   GPIO7  |------- SCLK ------->|  SCL     |  (clock: timing signal)
|   GPIO14 |------- CS --------->|  CS      |  (chip select: "I'm talking to you")
|   GPIO15 |------- DC --------->|  DC      |  (data/command: pixel data or instruction)
|   GPIO21 |------- RST -------->|  RES     |  (reset: hardware reset)
|   GPIO22 |------- BL --------->|  BL      |  (backlight: on/off)
+----------+                     +----------+
```

- **MOSI** (Master Out Slave In): The data line. The ESP32 sends pixel bytes here.
- **SCLK** (Serial Clock): A clock signal. The display reads one bit of MOSI on each clock tick.
- **CS** (Chip Select): Pulled low when the ESP32 wants to talk to this specific display.
- **DC** (Data/Command): High means "the bytes on MOSI are pixel data." Low means "the bytes are a command" (like "set the write window to row 10, column 20").

At 40MHz clock speed, SPI can transfer 5 megabytes per second. A full frame (110KB) takes about 22 milliseconds -- fast enough for 30+ FPS.

## Framebuffers and GRAM

The ST7789 has its own memory called GRAM (Graphics RAM) -- 172x320x2 = 110,080 bytes. Once you write pixels to GRAM, they stay on screen until overwritten. The display continuously reads GRAM and drives the LCD panel.

This means: if the ESP32 resets but the ST7789 does not lose power, the old image stays on screen. We saw this during development -- after resetting the ESP32, the display still showed text from a previous run.

## DMA: Let the Hardware Copy Bytes

DMA (Direct Memory Access) is hardware that copies data from memory to a peripheral (like SPI) without involving the CPU. Without DMA, the CPU would spend 22ms per frame doing nothing but feeding bytes to the SPI controller. With DMA:

```
Time --->

CPU:  [render frame 1] [render frame 2] [render frame 3]
DMA:       [send frame 1 via SPI] [send frame 2 via SPI]
                                                          
                 ^-- CPU and DMA work in parallel
```

The CPU fills a buffer with pixel data, tells DMA to send it, then immediately starts rendering the next batch. DMA runs independently.

## Double Buffering

With one buffer, the CPU must wait for DMA to finish before it can render new pixels (otherwise it would overwrite the buffer DMA is still reading). With two buffers:

```
Buffer A: [CPU renders here] -----> [DMA sends this]
Buffer B: [DMA sends this]  -----> [CPU renders here]
                                                      
They swap roles each frame.
```

LVGL uses this pattern. We allocate two DMA-capable buffers, and LVGL alternates between them.

## LVGL's Rendering Model

LVGL does not redraw the entire screen every frame. It tracks which areas are "dirty" (changed) and only redraws those regions. The workflow:

1. You change something (e.g., set label text)
2. LVGL marks the label's bounding box as dirty
3. On the next `lv_timer_handler()` call, LVGL renders only the dirty area into a draw buffer
4. LVGL calls your **flush callback** with the buffer and the coordinates
5. Your flush callback sends the pixels to the display via SPI/DMA
6. When DMA finishes, you call `lv_display_flush_ready()` to tell LVGL the buffer is free

This is the "display driver contract." LVGL handles rendering; you handle the hardware.

---

# Part 2: C Background for Python Developers

## ESP-IDF's esp_lcd Component

ESP-IDF (Espressif's development framework) provides an abstraction layer for LCD panels. Instead of writing raw SPI commands, you use:

```c
// Create a panel handle (opaque pointer)
esp_lcd_panel_handle_t panel;
esp_lcd_new_panel_st7789(io, &config, &panel);

// Use the handle to control the display
esp_lcd_panel_reset(panel);
esp_lcd_panel_init(panel);
esp_lcd_panel_draw_bitmap(panel, x1, y1, x2, y2, pixel_data);
```

`esp_lcd_panel_handle_t` is an **opaque handle** -- you never see what is inside it. You pass it to functions that know how to use it. This is the C equivalent of encapsulation.

## Configuration Structs

C does not have keyword arguments. Instead, you fill a struct with named fields:

```c
spi_bus_config_t bus_cfg = {
    .sclk_io_num = 7,      // GPIO7 for clock
    .mosi_io_num = 6,      // GPIO6 for data
    .miso_io_num = -1,     // not used (display is write-only)
    .quadwp_io_num = -1,   // not used
    .quadhd_io_num = -1,   // not used
    .max_transfer_sz = 172 * 40 * 2,  // max bytes per DMA transfer
};
```

The `.field = value` syntax is a C99 "designated initializer." Any field you do not mention is initialized to zero.

## ESP_ERROR_CHECK

ESP-IDF functions return `esp_err_t` (an error code). `ESP_ERROR_CHECK` is a macro that aborts the program if the error code is not `ESP_OK`:

```c
ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO));
// If this fails, the program prints the error and halts.
```

This is like Python's `assert` but for hardware initialization.

## ISR Callbacks: Code That Runs in Interrupt Context

When DMA finishes sending pixels, the hardware triggers an **interrupt** -- a signal that pauses whatever the CPU was doing and runs a special function (the ISR, Interrupt Service Routine).

```c
static bool notify_flush_ready(esp_lcd_panel_io_handle_t panel_io,
                               esp_lcd_panel_io_event_data_t *edata,
                               void *user_ctx)
{
    lv_display_t *disp = (lv_display_t *)user_ctx;
    lv_display_flush_ready(disp);
    return false;
}
```

This function runs in interrupt context. It must:
- Be fast (no loops, no printf)
- Not allocate memory
- Not call most MicroPython functions

All it does is tell LVGL: "the DMA transfer finished, you can reuse the buffer now."

## Static Variables and the Soft Reset Problem

In C, `static` variables inside a function (or at file scope) persist for the lifetime of the program:

```c
static bool s_initialized = false;
```

When MicroPython does a "soft reset" (Ctrl-D in the REPL), it reinitializes all Python state -- variables, modules, imports. But C static variables are untouched. Our driver checks `s_initialized` to avoid double-init:

```c
static void st7789_driver_init(void) {
    if (s_initialized) {
        return;  // skip -- but LVGL state may be stale!
    }
    // ... init hardware ...
    s_initialized = true;
}
```

After a soft reset, `s_initialized` is still `true`, so `init_display()` does nothing. The old LVGL objects are gone but the hardware is still configured. New LVGL calls create new objects that the display never renders -- because LVGL was never re-initialized.

The fix: use `machine.reset()` (hard reset) to reinitialize everything, including C statics.

---

# Part 3: Implementation

## The Hardware

The Waveshare ESP32-C6-LCD-1.47 has a built-in ST7789 display:

| Parameter | Value |
|-|-|
| Resolution | 172 x 320 pixels |
| Color depth | RGB565 (16-bit, 65,536 colors) |
| Interface | SPI at 40MHz |
| Controller | ST7789V |
| Controller width | 240 pixels (wider than the panel) |
| X offset | 34 pixels (172 centered in 240) |

Pin mapping:

| Signal | GPIO | Purpose |
|-|-|-|
| MOSI | 6 | Pixel data to display |
| SCLK | 7 | SPI clock |
| CS | 14 | Chip select |
| DC | 15 | Data / command |
| RST | 21 | Hardware reset |
| BL | 22 | Backlight on/off |

### The Offset Problem

The ST7789 controller addresses a 240-pixel-wide memory. Our 172-pixel-wide panel is centered in that memory, starting at column 34. If you write pixel (0,0), it actually goes to controller column (34,0). The `esp_lcd_panel_set_gap` function handles this:

```c
esp_lcd_panel_set_gap(panel, 34, 0);  // x_gap=34, y_gap=0
```

### The Byte Order Problem

SPI sends bytes in big-endian order (most significant byte first). LVGL renders RGB565 pixels in little-endian order (native to the ESP32's RISC-V CPU). Without correction, reds and blues are swapped.

LVGL v9 provides a swap function:

```c
lv_draw_sw_rgb565_swap(px_map, w * h);
```

We call this in the flush callback before sending pixels to the display.

## The Driver Code

### Initialization (st7789_driver_init)

The init function runs once and sets up the entire display pipeline:

```c
static void st7789_driver_init(void)
{
    if (s_initialized) return;

    /* 1. Backlight off during init */
    gpio_config_t bl_cfg = {
        .mode = GPIO_MODE_OUTPUT,
        .pin_bit_mask = 1ULL << 22,
    };
    gpio_config(&bl_cfg);
    gpio_set_level(22, 0);

    /* 2. SPI bus */
    spi_bus_config_t bus_cfg = {
        .sclk_io_num = 7,
        .mosi_io_num = 6,
        .miso_io_num = -1,
        .max_transfer_sz = 172 * 40 * sizeof(uint16_t),
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO));

    /* 3. SPI panel IO */
    esp_lcd_panel_io_spi_config_t io_cfg = {
        .dc_gpio_num = 15,
        .cs_gpio_num = 14,
        .pclk_hz = 40 * 1000 * 1000,
        .spi_mode = 0,
        .trans_queue_depth = 10,
    };
    esp_lcd_panel_io_handle_t io;
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi(SPI2_HOST, &io_cfg, &io));

    /* 4. ST7789 panel */
    esp_lcd_panel_dev_config_t panel_cfg = {
        .reset_gpio_num = 21,
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_BGR,
        .bits_per_pixel = 16,
    };
    ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(io, &panel_cfg, &s_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_reset(s_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_init(s_panel));
    ESP_ERROR_CHECK(esp_lcd_panel_invert_color(s_panel, true));
    ESP_ERROR_CHECK(esp_lcd_panel_set_gap(s_panel, 34, 0));
    ESP_ERROR_CHECK(esp_lcd_panel_disp_on_off(s_panel, true));

    /* 5. LVGL init */
    lv_init();
    lv_tick_set_cb(tick_cb);  // microsecond timer for LVGL's clock

    /* 6. Create LVGL display */
    s_disp = lv_display_create(172, 320);
    lv_display_set_color_format(s_disp, LV_COLOR_FORMAT_RGB565);
    lv_display_set_user_data(s_disp, s_panel);
    lv_display_set_flush_cb(s_disp, flush_cb);

    /* 7. DMA draw buffers (double-buffered) */
    size_t buf_size = 172 * 40 * sizeof(uint16_t);  // 40 lines at a time
    void *buf1 = heap_caps_malloc(buf_size, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    void *buf2 = heap_caps_malloc(buf_size, MALLOC_CAP_DMA | MALLOC_CAP_INTERNAL);
    lv_display_set_buffers(s_disp, buf1, buf2, buf_size,
                           LV_DISPLAY_RENDER_MODE_PARTIAL);

    /* 8. DMA-done callback */
    esp_lcd_panel_io_callbacks_t io_cbs = {
        .on_color_trans_done = notify_flush_ready,
    };
    ESP_ERROR_CHECK(esp_lcd_panel_io_register_event_callbacks(io, &io_cbs, s_disp));

    /* 9. Backlight on */
    gpio_set_level(22, 1);
    s_initialized = true;
}
```

The 40-line buffer (`172 * 40 * 2 = 13,760 bytes`) means LVGL renders 40 rows at a time, calling the flush callback 8 times to paint the full 320-row display. Two buffers = 27,520 bytes of DMA memory.

### The Flush Callback

```c
static void flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    esp_lcd_panel_handle_t panel = lv_display_get_user_data(disp);
    int w = area->x2 - area->x1 + 1;
    int h = area->y2 - area->y1 + 1;
    lv_draw_sw_rgb565_swap(px_map, w * h);  // fix byte order
    esp_lcd_panel_draw_bitmap(panel, area->x1, area->y1,
                              area->x2 + 1, area->y2 + 1, px_map);
}
```

This is called by LVGL whenever it has a buffer of pixels ready. The function:
1. Gets the panel handle from LVGL's user data
2. Swaps RGB565 bytes for SPI
3. Sends the pixel rectangle to the display via DMA

### MicroPython Wrappers

Three functions are exposed to Python:

```c
/* lvgl.init_display() */
static mp_obj_t mp_init_display(void) {
    st7789_driver_init();
    return mp_const_none;
}

/* lvgl.timer_handler() -> ms until next call */
static mp_obj_t mp_timer_handler(void) {
    uint32_t ms = lv_timer_handler();
    return mp_obj_new_int(ms);
}

/* lvgl.backlight(on: bool) */
static mp_obj_t mp_backlight(mp_obj_t on_obj) {
    gpio_set_level(22, mp_obj_is_true(on_obj) ? 1 : 0);
    return mp_const_none;
}
```

## The Pointer Wrapping Bug

This was the hardest bug to find. After `init_display()` succeeded, calling `lv_screen_active()` crashed with `LoadProhibited` at address `0xba1d302e`.

### The Symptom

```python
>>> import lvgl
>>> lvgl.init_display()    # OK
>>> lvgl.timer_handler()   # OK
>>> lvgl.lv_screen_active()  # CRASH: LoadProhibited
```

### The Root Cause

The auto-generated wrapper for `lv_screen_active` was:

```c
static mp_obj_t lv_screen_active_wrapper(void) {
    lv_obj_t *result = lv_screen_active();
    return ptr_to_mp((void *)result);  // <-- bug is here
}
```

And `ptr_to_mp` was:

```c
static inline mp_obj_t ptr_to_mp(void *ptr) {
    if (ptr == NULL) return mp_const_none;
    return MP_OBJ_FROM_PTR(ptr);  // WRONG!
}
```

`MP_OBJ_FROM_PTR` is a simple cast -- it reinterprets the pointer value as `mp_obj_t`. This works when the pointer comes from MicroPython's heap, because those addresses are always word-aligned (low 2 bits = `00`), which MicroPython interprets as "this is a pointer to a heap object."

But `lv_screen_active()` returns a pointer from LVGL's internal allocator. LVGL uses its own 48KB memory pool. The returned address might be anything:

```
MicroPython tagged pointer layout:

  bit 0 = 1  -->  small integer
  bits 0-2 = 010  -->  interned string (qstr)
  bits 0-2 = 110  -->  immediate (None, True, False)
  bits 0-1 = 00   -->  pointer to MicroPython heap object

LVGL pointer example: 0x407a38b4
  Binary: ...10110100
  Bits 0-1: 00  --> MicroPython thinks: heap object pointer!
  But it points to LVGL memory, not a valid MicroPython object.
  Accessing ->type dereferences garbage --> LoadProhibited crash.

Another LVGL pointer: 0x407a38b5  (if it ended in 1)
  Bits 0: 1  --> MicroPython thinks: small integer!
  Tries to do integer arithmetic on what is actually a pointer.
```

When MicroPython receives the return value, it examines the low bits. If the LVGL pointer happens to look like a heap object pointer (low bits `00`), MicroPython tries to read its `->type` field -- but that memory is an LVGL widget struct, not a MicroPython object. The `->type` field contains garbage, and dereferencing it crashes.

### The Fix

Replace `MP_OBJ_FROM_PTR` with `mp_obj_new_int_from_uint`:

```c
static inline mp_obj_t ptr_to_mp(void *ptr) {
    if (ptr == NULL) return mp_const_none;
    return mp_obj_new_int_from_uint((uintptr_t)ptr);
}

static inline void *mp_to_ptr(mp_obj_t obj) {
    if (obj == mp_const_none) return NULL;
    return (void *)(uintptr_t)mp_obj_get_int(obj);
}
```

Now LVGL pointers are wrapped as Python integers. MicroPython never tries to interpret them as heap objects. The pointer value is preserved exactly -- it just travels through Python-land as a number.

```python
>>> scr = lvgl.lv_screen_active()
>>> scr
1082247348   # the LVGL pointer, as a Python integer
>>> type(scr)
<class 'int'>
```

## On Device

After the fix, the full pipeline works:

```python
import lvgl
import time

lvgl.init_display()
scr = lvgl.lv_screen_active()
lvgl.lv_obj_clean(scr)  # clear any previous widgets

label = lvgl.lv_label_create(scr)
lvgl.lv_obj_center(label)

# Show "Good morning" for 5 seconds
lvgl.lv_label_set_text(label, "Good morning")
for i in range(500):
    lvgl.timer_handler()
    time.sleep_ms(10)

# Switch to "Hello" for 5 seconds
lvgl.lv_label_set_text(label, "Hello")
for i in range(500):
    lvgl.timer_handler()
    time.sleep_ms(10)
```

The text changes dynamically on the physical display. LVGL detects that the label content changed, redraws only the affected area, and the flush callback sends the new pixels to the ST7789 via DMA.

### Gotcha: Soft Reset

After a MicroPython soft reset (Ctrl-D), `s_initialized` remains `true`, so `init_display()` silently does nothing. LVGL is not re-initialized, and new widgets are not rendered. Use `machine.reset()` for a hard reset, or unplug and replug the board.

## Summary

| Component | Lines | Purpose |
|-|-|-|
| `st7789_driver.c` | 180 | SPI init, LVGL display driver, MicroPython wrappers |
| `lvgl.c` (modified) | 744 | Added extern declarations and globals table entries |
| `lv_conf.h` | 208 | LVGL config: 48KB RAM, 7 widgets, RGB565 |
| `micropython.cmake` (modified) | ~30 | Added st7789_driver.c source, esp_lcd component |
| `partitions-lvgl.csv` | 6 | Custom partition: 2.56MB app, 1.4MB VFS |

The firmware binary is 2.49MB with 7% free space in the 2.56MB app partition. It runs on the ESP32-C6 at 160MHz with MicroPython v1.24.1, LVGL v9.2.0, and ESP-IDF v5.2.2.