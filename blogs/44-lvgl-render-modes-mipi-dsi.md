# LVGL Render Modes on MIPI-DSI: From Screen Tearing to Tear-Free Display

*Three render modes, one video-mode panel, and the small detail that decides whether you get tearing, ghosting, or a clean screen.*

## Table of Contents

- [Part 1: Display Rendering Theory](#part-1-display-rendering-theory)
- [Part 2: C Background for Python Developers](#part-2-c-background-for-python-developers)
- [Part 3: Implementation - Three Modes We Tried](#part-3-implementation---three-modes-we-tried)

## Part 1: Display Rendering Theory

This post is about a video-mode MIPI-DSI panel on an ESP32-P4. That combination behaves very differently from SPI or MCU-style "command mode" panels, which is what many embedded display examples focus on.

### Framebuffer: pixels as a memory region

A framebuffer is a chunk of RAM that holds the screen image. Think of it as a 2D array laid out in memory:

- Each pixel takes a fixed number of bytes (for example, RGB565 is 2 bytes per pixel).
- Each row is stored left to right.
- Rows are stored top to bottom.

If your display is 480x800 RGB565, one full framebuffer is:

`480 * 800 * 2 = 768,000 bytes` (about 750 KiB)

When software "draws" a rectangle, it writes new pixel values into the framebuffer addresses that correspond to that rectangle.

### MIPI-DSI DPI (video mode): the panel keeps scanning

In MIPI-DSI DPI (video mode), the display pipeline continuously scans the framebuffer at a fixed refresh rate (typically 60 Hz). The controller reads pixels row by row from top to bottom, then starts again.

This is the key mental model:

- The hardware is reading the framebuffer all the time.
- Your UI code is writing to a framebuffer some of the time.
- If those overlap, you see artifacts.

ASCII view of the scan line moving down:

```
Frame start
  +---------------------------------+
  |  row 0   <== scan line reads    |
  |  row 1                           |
  |  row 2                           |
  |  ...                             |
  |  row 799                         |
  +---------------------------------+
               time ->

Later in the same frame
  +---------------------------------+
  |  row 0                           |
  |  row 1                           |
  |  row 2                           |
  |  ...                             |
  |  row 400 <== scan line reads     |
  |  ...                             |
  |  row 799                         |
  +---------------------------------+
```

### Screen tearing: writing while the scan line reads

Tearing happens when the display reads a mixture of "old" and "new" pixels in a single refresh.

Example: your code updates a label while the panel is scanning somewhere near the bottom. The top part of the frame contains the old label, the bottom part contains the new label, and the boundary becomes a visible tear line.

```
  +---------------------------------+
  | old frame content               |
  | old frame content               |
  | old frame content               |
  |----------- TEAR LINE -----------|  <== software writes here
  | new frame content               |
  | new frame content               |
  +---------------------------------+
```

You can "get lucky" and not notice tearing when updates are small or happen during quiet periods, but the underlying race is still there.

### Vsync and the vertical blanking interval

Between frames, there is a short period where the display finishes the last row and starts the next frame. This is the vertical blanking interval (vblank). If you swap which framebuffer is being scanned during vblank, the whole next frame is consistent.

People often say "wait for vsync". What they mean is "only change what the scanout hardware reads between frames".

### Double buffering: front buffer, back buffer, swap at vsync

Double buffering uses two framebuffers:

- Front buffer: the one currently scanned by the panel.
- Back buffer: the one your software renders into.

At vsync, you swap them. That removes tearing, as long as swaps only happen at vsync.

```
Time slice A: scanout uses FB0, software draws into FB1

  Scanout -> [FB0]    Render -> [FB1]

Vsync: swap pointers

Time slice B: scanout uses FB1, software draws into FB0

  Scanout -> [FB1]    Render -> [FB0]
```

On a video-mode panel, this is the cleanest approach, but it only works if you respect the swap timing.

## Part 2: C Background for Python Developers

The fixes below happen in a C display driver, because the hardware rules (DMA, interrupts, vsync) live there.

### DMA: copying pixels without burning CPU

DMA (Direct Memory Access) is hardware that copies memory on your behalf. For displays, it commonly moves pixel data from RAM into a peripheral or into another RAM region used by the display engine.

Why it matters:

- Copying even a small rectangle is thousands of bytes.
- Doing that with the CPU can starve your UI task.
- DMA runs in the background and can signal completion.

On the ESP32-P4, the DPI driver can use 2D DMA (DMA2D) for fast rectangle copies when `use_dma2d=true`.

### ISR callbacks and `IRAM_ATTR`

An ISR (interrupt service routine) is code that runs when hardware raises an interrupt. It can preempt normal tasks. That means:

- Keep it short.
- Don't block.
- Use ISR-safe APIs.

ESP-IDF uses `IRAM_ATTR` to place a function into IRAM (fast internal RAM). During some flash cache states, code in flash may not be safe to run, so ISR callbacks that must be reliable are often marked with `IRAM_ATTR`.

### `heap_caps_malloc`: allocating the right kind of RAM

ESP-IDF has multiple memory regions with different capabilities. `heap_caps_malloc()` lets you request memory that satisfies a set of flags.

For DMA, the important flag is `MALLOC_CAP_DMA`, meaning the memory is accessible by DMA engines.

```c
#include "esp_heap_caps.h"

void *buf = heap_caps_malloc(size, MALLOC_CAP_DMA);
if (buf == NULL) {
    // handle out-of-memory
}
```

If you give DMA a pointer to memory it can't access, you'll get hard-to-debug failures or corrupted pixels.

### Semaphores: signaling between ISR and a task

FreeRTOS semaphores are synchronization primitives. A common pattern is:

- A task starts a DMA transfer.
- The DMA completion interrupt runs an ISR callback.
- The ISR "gives" a semaphore.
- The task "takes" the semaphore to wait for completion.

The ISR uses `xSemaphoreGiveFromISR()` and can request a context switch if it woke a higher-priority task.

### `esp_lcd_panel_draw_bitmap`: the "push pixels" API

In ESP-IDF's LCD abstraction, `esp_lcd_panel_draw_bitmap()` is the function that tells the panel driver to update a rectangle.

```c
esp_err_t esp_lcd_panel_draw_bitmap(
    esp_lcd_panel_handle_t panel,
    int x_start,
    int y_start,
    int x_end,
    int y_end,
    const void *color_data
);
```

Conceptually:

- `(x_start, y_start)` is the top-left corner.
- `(x_end, y_end)` is the bottom-right boundary, usually treated as exclusive.
- `color_data` points to pixel bytes in the format the panel expects.

On a video-mode DPI panel, this call often does more than a simple copy. It may perform cache write-back, schedule DMA2D work, and coordinate which framebuffer becomes active.

### DPI panel event callbacks: DMA done vs frame done

The DPI driver can notify you at two different times:

- Color transfer done: the pixel transfer (DMA or copy) finished.
- Refresh done: the panel finished a full frame refresh (vsync boundary).

In ESP-IDF, the callbacks are registered through a struct like this:

```c
typedef struct {
    bool (*on_color_trans_done)(
        esp_lcd_panel_handle_t panel,
        const esp_lcd_dpi_panel_event_data_t *edata,
        void *user_ctx
    );
    bool (*on_refresh_done)(
        esp_lcd_panel_handle_t panel,
        const esp_lcd_dpi_panel_event_data_t *edata,
        void *user_ctx
    );
} esp_lcd_dpi_panel_event_callbacks_t;
```

Which one you should use depends on what your flush is actually doing. If your flush triggers a buffer swap, you care about vsync. If your flush is just "copy this rectangle", you often care about DMA completion.

## Part 3: Implementation - Three Modes We Tried

### Context

Hardware and software setup:

- Board: Guition JC4880P443C ESP32-P4
- Panel: ST7701, 480x800, MIPI-DSI DPI (video mode)
- LVGL: v9
- ESP-IDF DPI panel: `num_fbs=2` (double framebuffer), `use_dma2d=true`

All code lives in `configs/boards/guition-p4/display_driver.c`.

The predecessor for SPI panels was blog 22. This post exists because video mode changes the rules: the panel is scanning continuously, and "just write pixels" is not automatically safe.

### The comparison at a glance

| Mode | Tearing | Ghost Text | Updates Work | Why |
|------|---------|------------|-------------|-----|
| DIRECT (original) | N/A | No | No | `flush_cb` was a no-op |
| DIRECT + `draw_bitmap` | Yes | No | Yes | Buffer swap can happen mid-scan |
| DIRECT + `on_refresh_done` | Reduced | No | Yes | Partial renders still trigger multiple swaps |
| DIRECT + semaphore vsync | Still present | No | Yes | Same partial render problem |
| FULL | No | Yes | Yes | Second framebuffer contains stale pixels |
| PARTIAL | No | No | Yes | DMA copies dirty regions, driver owns swaps |

### Mode 1: DIRECT mode (original)

DIRECT mode means LVGL renders directly into the framebuffer(s) you give it. On the ESP-IDF DPI driver, you can obtain the panel-owned framebuffer pointers via `esp_lcd_dpi_panel_get_frame_buffer()`.

The original `flush_cb` looked like this:

```c
static void lvgl_flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    (void)area;
    (void)px_map;
    lv_display_flush_ready(disp);
}
```

Problem 1: the display never updated.

Even though LVGL wrote pixels into a buffer, the DPI driver still needed an explicit "this region is ready" signal so it could handle cache synchronization and present the new buffer. With a no-op flush, that step never happened.

#### DIRECT fix: call `esp_lcd_panel_draw_bitmap()`, delay `flush_ready`

We changed `flush_cb` to call `draw_bitmap()`. Because the transfer is asynchronous, we only call `lv_display_flush_ready()` when the driver reports completion.

```c
static void lvgl_flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    esp_lcd_panel_handle_t panel = (esp_lcd_panel_handle_t)lv_display_get_user_data(disp);

    int x1 = area->x1;
    int y1 = area->y1;
    int x2 = area->x2 + 1;
    int y2 = area->y2 + 1;

    esp_lcd_panel_draw_bitmap(panel, x1, y1, x2, y2, px_map);
    // lv_display_flush_ready(disp) happens in on_color_trans_done
}
```

```c
static bool IRAM_ATTR on_color_trans_done(
    esp_lcd_panel_handle_t panel,
    const esp_lcd_dpi_panel_event_data_t *edata,
    void *user_ctx
)
{
    (void)panel;
    (void)edata;
    lv_display_t *disp = (lv_display_t *)user_ctx;
    lv_display_flush_ready(disp);
    return false;
}
```

Problem 2: screen tearing at the bottom.

The moment we started triggering the panel driver to present updates, the tearing became visible, most often near the bottom edge. The symptom matched a mid-scan swap: the panel was reading one framebuffer, then the "present" happened while it was part-way through scanning, so the last rows came from a different buffer.

### Mode 1b: DIRECT + `on_refresh_done` vsync

If the problem is swapping at the wrong time, the obvious attempt is "wait for vsync". That maps to the DPI callback `on_refresh_done`.

We changed the callback used to signal LVGL:

- Instead of `on_color_trans_done`, call `lv_display_flush_ready()` from `on_refresh_done`.

Result: flickering reduced, but still present.

Why: in DIRECT mode, LVGL is free to flush multiple times per frame because it can render different dirty rectangles independently. If each flush ends up causing the driver to present or swap, you have multiple opportunities per frame to land on a bad boundary.

### Mode 1c: DIRECT + semaphore vsync

Next attempt: make flush synchronous. The idea was:

- `flush_cb` blocks until a vsync event.
- `on_refresh_done` gives a semaphore from ISR.

The pattern (simplified):

```c
static SemaphoreHandle_t vsync_sem;

static void lvgl_flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    esp_lcd_panel_handle_t panel = (esp_lcd_panel_handle_t)lv_display_get_user_data(disp);
    esp_lcd_panel_draw_bitmap(panel, area->x1, area->y1, area->x2 + 1, area->y2 + 1, px_map);
    xSemaphoreTake(vsync_sem, portMAX_DELAY);
    lv_display_flush_ready(disp);
}
```

```c
static bool IRAM_ATTR on_refresh_done(
    esp_lcd_panel_handle_t panel,
    const esp_lcd_dpi_panel_event_data_t *edata,
    void *user_ctx
)
{
    (void)panel;
    (void)edata;
    BaseType_t woke = pdFALSE;
    xSemaphoreGiveFromISR((SemaphoreHandle_t)user_ctx, &woke);
    return woke == pdTRUE;
}
```

Result: flickering still showed up at the bottom.

This was the point where it became clear that the core issue was not "we forgot to wait". It was that DIRECT mode encourages partial-area flushing, and the DPI driver's internal buffering and swap behavior did not match LVGL's assumption that "writing pixels into the framebuffer" is the whole story.

### Mode 2: FULL mode

FULL mode sounds like the solution because it suggests "one flush per frame".

We changed LVGL to full-screen rendering while still using the panel-owned framebuffers:

```c
lv_display_set_buffers(
    disp,
    fb0,
    fb1,
    480 * 800 * 2,
    LV_DISPLAY_RENDER_MODE_FULL
);
```

Result: no flickering, but ghost text.

What we saw was old label text persisting under new text, like the background was not being cleared.

Root cause: double framebuffer history.

With `num_fbs=2`, the DPI driver alternates between two full-screen buffers. On frame N:

- LVGL draws into buffer A.
- The driver presents A.
- Next frame, LVGL draws into buffer B.

The trap is that buffer B contains whatever pixels were left from two frames ago. FULL render mode does not mean "clear the whole screen and redraw every pixel". LVGL still redraws only the areas it thinks changed. Unchanged areas in the "other" framebuffer keep stale pixels, which is exactly what ghosting looks like.

If you come from immediate-mode rendering on a single framebuffer, this feels surprising. With buffer flipping, every buffer needs a consistent baseline, either by full redraw or by copying forward previous content. FULL mode did not provide that baseline by itself.

### Mode 3: PARTIAL mode (winner)

The working solution was to stop having LVGL render directly into the DPI framebuffers.

Instead:

- Allocate separate, small LVGL draw buffers in DMA-capable memory.
- Use PARTIAL render mode so LVGL only renders dirty rectangles into those buffers.
- In `flush_cb`, call `esp_lcd_panel_draw_bitmap()` to copy that rectangle into the panel driver.
- Use `on_color_trans_done` to tell LVGL when the copy is complete.

This changes the ownership model:

- LVGL owns the draw buffer memory.
- The DPI driver owns the true scanout buffers and swaps them at vsync internally.
- `draw_bitmap()` becomes "patch the next framebuffer" rather than "swap right now".

#### Buffer setup with `heap_caps_malloc`

We used 100 lines per draw buffer as a practical trade-off (small enough to fit, large enough to keep flush overhead reasonable):

```c
static void *buf1;
static void *buf2;

static void lvgl_setup_buffers(lv_display_t *disp)
{
    const int width = 480;
    const int lines = 100;
    const int bytes_per_pixel = 2; // RGB565
    size_t buf_size = (size_t)width * (size_t)lines * (size_t)bytes_per_pixel;

    buf1 = heap_caps_malloc(buf_size, MALLOC_CAP_DMA);
    buf2 = heap_caps_malloc(buf_size, MALLOC_CAP_DMA);

    lv_display_set_buffers(disp, buf1, buf2, buf_size, LV_DISPLAY_RENDER_MODE_PARTIAL);
}
```

#### Final `flush_cb` and DMA-done callback

`flush_cb` becomes "copy this dirty rectangle". Note how we do not block on vsync, we only wait for the copy to finish.

```c
static void lvgl_flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map)
{
    esp_lcd_panel_handle_t panel = (esp_lcd_panel_handle_t)lv_display_get_user_data(disp);

    int x1 = area->x1;
    int y1 = area->y1;
    int x2 = area->x2 + 1;
    int y2 = area->y2 + 1;

    esp_lcd_panel_draw_bitmap(panel, x1, y1, x2, y2, px_map);
    // lv_display_flush_ready(disp) happens in on_color_trans_done
}
```

```c
static bool IRAM_ATTR on_color_trans_done(
    esp_lcd_panel_handle_t panel,
    const esp_lcd_dpi_panel_event_data_t *edata,
    void *user_ctx
)
{
    (void)panel;
    (void)edata;
    lv_display_t *disp = (lv_display_t *)user_ctx;
    lv_display_flush_ready(disp);
    return false;
}
```

#### Why PARTIAL works on this DPI setup

With `num_fbs=2`, the DPI driver has two scanout-sized framebuffers and owns the swap timing. In this model:

- LVGL renders into its own small buffers.
- `draw_bitmap()` copies the dirty region into the DPI driver's internal framebuffer.
- The DPI driver performs the actual buffer swap at vsync.

That division of responsibility is exactly what we wanted:

- LVGL never writes into the memory being actively scanned.
- The only operation during a frame is a DMA copy into a buffer the driver can schedule safely.
- Vsync is handled once, centrally, by the DPI driver.

In practice, this removed tearing and ghosting, and it made rapid UI updates stable. In a stress test of 10,000 label updates, the loop completed in about 1.2 seconds, around 8,300 updates per second.

### One more thing: garbage on first display

After switching to PARTIAL mode, the display worked perfectly during updates -- but the very first frame after `init_display()` showed overlapping garbage text. Old pixel data from a previous session was stuck in the DPI framebuffers.

The root cause: the DPI panel allocates its two framebuffers in PSRAM via `num_fbs=2`. PSRAM is not zeroed on allocation. The DPI hardware starts scanning immediately after `esp_lcd_panel_init()`, so whatever random bytes were in PSRAM show up on screen before LVGL has a chance to render anything.

The fix has three parts:

First, get the DPI framebuffer pointers (we are not using them as LVGL buffers, but we still need to clear them):

```c
void *fb0 = NULL;
void *fb1_dpi = NULL;
esp_lcd_dpi_panel_get_frame_buffer(panel, 2, &fb0, &fb1_dpi);
```

Second, zero both buffers. `memset` with zero produces black pixels in RGB565:

```c
size_t fb_size = 480 * 800 * 2;  // width * height * bytes_per_pixel
memset(fb0, 0, fb_size);
memset(fb1_dpi, 0, fb_size);
```

Third, force LVGL to render the default screen (a blank background) and flush it before turning on the backlight:

```c
lv_obj_invalidate(lv_screen_active());
lv_timer_handler();
set_backlight(true);  // only now turn on the light
```

By clearing the framebuffers and doing a full LVGL render pass before the backlight turns on, the user never sees garbage. The display appears to turn on with a clean screen.

The key takeaway is simple: on a video-mode MIPI-DSI DPI panel with driver-managed double framebuffers, PARTIAL mode is the correct choice because LVGL should not own scanout buffers. LVGL should render into DMA-friendly scratch buffers, and the DPI driver should manage the real framebuffers and vsync swaps. And always clear the framebuffers before turning on the backlight -- PSRAM does not initialize to zero.
