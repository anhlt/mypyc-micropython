# Offline Topographic Map Viewer for ESP32

Status: Idea / Research

Summary: Build an offline map tile viewer as an MVU application using the `lvgl_mvu` framework, written in typed Python, compiled to native C via mypyc-micropython. Uses OpenTopoMap tiles stored on SD card, rendered via LVGL on ESP32-P4/C6 displays.

## Table of Contents

- [1. Motivation](#1-motivation)
- [2. Architecture](#2-architecture)
- [3. Data Pipeline - Tile Preparation (PC Side)](#3-data-pipeline---tile-preparation-pc-side)
- [4. Python Implementation (What Gets Compiled)](#4-python-implementation-what-gets-compiled)
- [5. MVU Integration](#5-mvu-integration)
- [6. Hardware Acceleration (ESP32-P4)](#6-hardware-acceleration-esp32-p4)
- [7. Compiler Feature Requirements](#7-compiler-feature-requirements)
- [8. Reference Implementation](#8-reference-implementation)
- [9. Target Hardware](#9-target-hardware)
- [10. Milestones](#10-milestones)
- [11. How to Run](#11-how-to-run)
- [12. Open Questions](#12-open-questions)
- [13. Why This Project Matters for mypyc-micropython](#13-why-this-project-matters-for-mypyc-micropython)

## 1. Motivation

The mypyc-micropython compiler needs a real-world application showcase beyond toy examples.
An offline topographic map viewer is a good fit because it is both useful and compiler-stressing.

- Demonstrates the full pipeline: typed Python -> compiled C -> firmware -> device.
- Builds something that makes sense on embedded hardware: offline hiking and outdoor navigation.
- Exercises compiler features at scale: classes, float math, file I/O, MVU framework integration, cross-module imports.
- Produces a benchmarkable hot path: coordinate conversion and tile selection.
- Validates the MVU framework with a non-trivial real-world application.

## 2. Architecture

End-to-end pipeline:

```
PC side (tile preparation):
  OpenTopoMap tile server -> Python download script -> PNG tiles -> RGB565 .bin converter -> SD card

ESP32 side (runtime):
  SD card -> TileLoader -> MapDisplay (MVU App) -> lvgl_mvu Reconciler -> LVGL image widgets -> Display
```

Everything on the ESP32 side is typed Python compiled to C via mypyc. The map viewer is an MVU application built on top of the existing `extmod/lvgl_mvu/` framework.

### MVU data flow

```
Model (MapState)
  |
  v
view(model) -> Widget tree (Screen > Container > Image tiles)
  |
  v
lvgl_mvu Reconciler -> diffs previous tree -> applies minimal LVGL updates
  |
  v
User input (touch pan, zoom buttons)
  |
  v
Msg (Pan, ZoomIn, ZoomOut, TileLoaded)
  |
  v
update(msg, model) -> new MapState, Cmd
```

### Module layout

```
extmod/map_viewer/
  __init__.py             # package init
  tile_math.py            # pure math: lat/lon <-> tile coords
  tile_loader.py          # SD card file I/O for RGB565 tiles
  map_app.py              # MVU Program: Model, Msg, init, update, view

extmod/lvgl_mvu/          # existing framework (already compiled)
  widget.py               # WidgetKey.IMAGE = 9 (already defined)
  attrs.py                # AttrKey.SRC = 144 (already defined)
  factories.py            # needs: create_image factory
  appliers.py             # needs: apply_image_src applier
  dsl.py                  # needs: Image() DSL function
  ...                     # rest of framework unchanged
```

The map viewer package imports from `lvgl_mvu` for all UI concerns. The `tile_math.py` and `tile_loader.py` modules are pure utilities with no LVGL dependency.

### Viewport model

```
MapState:
  zoom: int
  center_x: int            # tile X coordinate
  center_y: int            # tile Y coordinate
  grid_cols: int            # e.g. 4 for P4, 2 for C6
  grid_rows: int            # e.g. 3 for P4, 2 for C6
  tiles: dict[str, bytes]   # loaded tile data keyed by "z/x/y"
```

## 3. Data Pipeline - Tile Preparation (PC Side)

This project uses OpenTopoMap raster tiles, then converts them into a format that is fast to load and render on device.

### 3.1 Tile source

Tile URL pattern:

`https://{a|b|c}.tile.opentopomap.org/{z}/{x}/{y}.png`

License note: OpenTopoMap tiles are CC-BY-SA. The device UI and documentation should include attribution and license text appropriate for redistribution.

### 3.2 Slippy map math (lat/lon -> tile X/Y)

For Web Mercator (EPSG:3857) slippy tiles:

```
x = floor((lon + 180) / 360 * 2^zoom)
y = floor((1 - ln(tan(lat_rad) + 1/cos(lat_rad)) / pi) / 2 * 2^zoom)
```

Where `lat_rad = lat * pi / 180`.

### 3.3 Device-friendly tile format

Goal: minimize runtime CPU and allocations.

- Input: PNG 256x256 from OpenTopoMap
- Output: RGB565 raw pixels, row-major, 2 bytes per pixel
- Container: one `.bin` file per tile

Proposed `.bin` layout:

- 12-byte header (little endian)
- 256 * 256 * 2 bytes of pixel data

Header (12 bytes):

```
offset  size  field
0       4     magic = b"MTL0"
4       2     width = 256
6       2     height = 256
8       2     fmt = 1 (RGB565)
10      2     reserved = 0
```

This keeps parsing trivial and lets future formats exist without breaking old data.

Format tradeoffs (what you store on SD card):

| Format on SD | Decode on ESP32 | CPU cost | RAM cost | Notes |
|-------------|------------------|----------|----------|-------|
| PNG | libpng (or MicroPython decoder) | High | Medium to high | Smaller files, but slow and complex on device |
| JPEG | jpeg decoder | Medium | Medium | Smaller files, but lossy and still decode-heavy |
| RGB565 raw | None | Low | High | Fastest render path, largest storage |

This design intentionally chooses RGB565 raw so the runtime path is simple and predictable.

On ESP32-P4, an alternative is storing tiles as JPEG and using the hardware JPEG decoder (see Section 6.3). This trades ~2ms decode time per tile for 10x storage savings. The convert script can output either format.

### 3.4 SD card directory layout

Directory layout on the SD card:

`/{tile_type}/{zoom}/{x}/{y}.bin`

Example:

`/topo/13/7261/3224.bin`

### 3.5 Concrete tile download + convert scripts

These scripts run on a PC, not on the ESP32. They are intentionally simple and deterministic.

`scripts/download_tiles.py` (example):

```python
from __future__ import annotations

import argparse
import math
import os
import time
import urllib.request


def lon_to_tile_x(lon: float, zoom: int) -> int:
    n = 1 << zoom
    return int((lon + 180.0) / 360.0 * n)


def lat_to_tile_y(lat: float, zoom: int) -> int:
    n = 1 << zoom
    lat_rad = lat * math.pi / 180.0
    return int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)


def parse_bbox(s: str) -> tuple[float, float, float, float]:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) != 4:
        raise SystemExit("bbox must be: lat_min,lon_min,lat_max,lon_max")
    lat_min, lon_min, lat_max, lon_max = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
    return lat_min, lon_min, lat_max, lon_max


def parse_zoom_range(s: str) -> list[int]:
    if "-" in s:
        a, b = s.split("-", 1)
        start, end = int(a), int(b)
        return list(range(start, end + 1))
    return [int(s)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", required=True)
    ap.add_argument("--zoom", required=True, help='e.g. "13-14" or "15"')
    ap.add_argument("--output", required=True)
    ap.add_argument("--tile-type", default="topo")
    ap.add_argument("--delay", type=float, default=0.2, help="seconds between requests")
    args = ap.parse_args()

    lat_min, lon_min, lat_max, lon_max = parse_bbox(args.bbox)
    zooms = parse_zoom_range(args.zoom)

    # Note: y increases southward in slippy tiles.
    for z in zooms:
        x0 = lon_to_tile_x(lon_min, z)
        x1 = lon_to_tile_x(lon_max, z)
        y0 = lat_to_tile_y(lat_max, z)
        y1 = lat_to_tile_y(lat_min, z)

        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                url = f"https://a.tile.opentopomap.org/{z}/{x}/{y}.png"
                out_dir = os.path.join(args.output, args.tile_type, str(z), str(x))
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, f"{y}.png")

                if os.path.exists(out_path):
                    continue

                with urllib.request.urlopen(url, timeout=30) as resp:
                    data = resp.read()
                with open(out_path, "wb") as f:
                    f.write(data)

                time.sleep(args.delay)


if __name__ == "__main__":
    main()
```

`scripts/convert_tiles.py` (example, Pillow required):

```python
from __future__ import annotations

import argparse
import os
import struct
from pathlib import Path

from PIL import Image


MAGIC = b"MTL0"
FMT_RGB565 = 1


def rgb888_to_rgb565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def convert_png_to_bin(png_path: Path, bin_path: Path) -> None:
    img = Image.open(png_path).convert("RGB")
    w, h = img.size
    if (w, h) != (256, 256):
        raise RuntimeError(f"unexpected tile size: {w}x{h} {png_path}")

    pixels = img.load()
    out = bytearray()
    out += struct.pack("<4sHHHH", MAGIC, w, h, FMT_RGB565, 0)

    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            p = rgb888_to_rgb565(r, g, b)
            out += struct.pack("<H", p)

    bin_path.parent.mkdir(parents=True, exist_ok=True)
    bin_path.write_bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    in_root = Path(args.input)
    out_root = Path(args.output)

    # Expected input structure:
    #   <input>/<tile_type>/<z>/<x>/<y>.png
    for png_path in in_root.rglob("*.png"):
        rel = png_path.relative_to(in_root)
        bin_rel = rel.with_suffix(".bin")
        convert_png_to_bin(png_path, out_root / bin_rel)


if __name__ == "__main__":
    main()
```

Notes:

- Tile download rate limiting is not optional. Treat it as part of the design.
- Keep the conversion deterministic: no resizing, no dithering.

### 3.6 Storage calculations

Each RGB565 256x256 tile is 131,072 bytes of pixel data plus a 12 byte header. Round to 128 KiB per tile for planning.

| Region | Zoom levels | Tiles | SD card space |
|--------|------------|-------|---------------|
| Mt. Fuji (50x50km) | 12-14 | ~2,100 | ~260 MB |
| Tokyo metro (30x30km) | 13-15 | ~4,500 | ~560 MB |
| Single hiking trail (5x5km) | 13-15 | ~350 | ~44 MB |

These numbers assume no PNG compression on device. That is the point. Read a file, blast pixels.

## 4. Python Implementation (What Gets Compiled)

All ESP32 code is typed Python compiled to C via mypyc. The map viewer is structured as an MVU application using the existing `lvgl_mvu` framework.

### 4.1 `tile_math.py`

Pure math functions, no dependencies besides `math`:

```python
import math

def lon_to_tile_x(lon: float, zoom: int) -> int:
    n: int = 1 << zoom  # 2^zoom using bit shift
    return int((lon + 180.0) / 360.0 * n)

def lat_to_tile_y(lat: float, zoom: int) -> int:
    n: int = 1 << zoom
    lat_rad: float = lat * math.pi / 180.0
    return int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)

def tile_x_to_lon(x: int, zoom: int) -> float:
    n: int = 1 << zoom
    return x / n * 360.0 - 180.0

def tile_y_to_lat(y: int, zoom: int) -> float:
    n: int = 1 << zoom
    lat_rad: float = math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n)))
    return lat_rad * 180.0 / math.pi
```

### 4.2 `tile_loader.py`

Tile I/O using MicroPython file APIs:

```python
from __future__ import annotations

TILE_SIZE: int = 256
HEADER_SIZE: int = 12
TILE_BYTES: int = TILE_SIZE * TILE_SIZE * 2  # RGB565

class TileLoader:
    def __init__(self, base_path: str, tile_type: str) -> None:
        self.base_path: str = base_path
        self.tile_type: str = tile_type
        self.zoom: int = 13

    def tile_path(self, x: int, y: int) -> str:
        return self.base_path + "/" + self.tile_type + "/" + str(self.zoom) + "/" + str(x) + "/" + str(y) + ".bin"

    def load_tile_data(self, x: int, y: int) -> bytes:
        path: str = self.tile_path(x, y)
        f = open(path, "rb")
        f.read(HEADER_SIZE)  # skip header
        data: bytes = f.read(TILE_BYTES)
        f.close()
        return data

    def set_zoom(self, zoom: int) -> None:
        self.zoom = zoom

    def tile_key(self, x: int, y: int) -> str:
        return str(self.zoom) + "/" + str(x) + "/" + str(y)
```

### 4.3 `map_app.py` (MVU Application)

The map display is an MVU Program using `lvgl_mvu`. Model holds the map state, view produces a Widget tree of IMAGE tiles, update handles pan/zoom messages.

```python
from __future__ import annotations

from lvgl_mvu.program import Cmd, Program
from lvgl_mvu.widget import Widget, WidgetKey
from lvgl_mvu.attrs import AttrKey
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.dsl import Screen, Container
from map_viewer.tile_math import lon_to_tile_x, lat_to_tile_y
from map_viewer.tile_loader import TileLoader

TILE_PX: int = 256

# --- Message types (int tags) ---

MSG_PAN: int = 0
MSG_ZOOM_IN: int = 1
MSG_ZOOM_OUT: int = 2

# --- Model ---

class MapState:
    zoom: int
    center_x: int
    center_y: int
    grid_cols: int
    grid_rows: int
    loader: TileLoader

    def __init__(self, zoom: int, center_x: int, center_y: int,
                 grid_cols: int, grid_rows: int, loader: TileLoader) -> None:
        self.zoom = zoom
        self.center_x = center_x
        self.center_y = center_y
        self.grid_cols = grid_cols
        self.grid_rows = grid_rows
        self.loader = loader


class PanMsg:
    dx: int
    dy: int
    def __init__(self, dx: int, dy: int) -> None:
        self.dx = dx
        self.dy = dy


# --- init ---

def map_init() -> tuple[object, Cmd]:
    loader = TileLoader("/sd", "topo")
    # Default: Mt. Fuji area, zoom 13
    lat: float = 35.3606
    lon: float = 138.7274
    zoom: int = 13
    cx: int = lon_to_tile_x(lon, zoom)
    cy: int = lat_to_tile_y(lat, zoom)
    loader.set_zoom(zoom)
    model = MapState(zoom, cx, cy, 4, 3, loader)
    return (model, Cmd.none())


# --- update ---

def map_update(msg: object, model: object) -> tuple[object, Cmd]:
    state: MapState = model  # type: ignore[assignment]

    if isinstance(msg, PanMsg):
        state.center_x = state.center_x + msg.dx
        state.center_y = state.center_y + msg.dy
        return (state, Cmd.none())

    # int-tagged messages
    msg_tag: int = msg  # type: ignore[assignment]
    if msg_tag == MSG_ZOOM_IN:
        state.center_x = state.center_x * 2
        state.center_y = state.center_y * 2
        state.zoom = state.zoom + 1
        state.loader.set_zoom(state.zoom)
    elif msg_tag == MSG_ZOOM_OUT:
        state.center_x = state.center_x // 2
        state.center_y = state.center_y // 2
        state.zoom = state.zoom - 1
        state.loader.set_zoom(state.zoom)

    return (state, Cmd.none())


# --- view ---

def map_view(model: object) -> Widget:
    state: MapState = model  # type: ignore[assignment]

    half_c: int = state.grid_cols // 2
    half_r: int = state.grid_rows // 2

    tile_widgets: list[Widget] = []
    row: int = -half_r
    while row <= half_r:
        col: int = -half_c
        while col <= half_c:
            tx: int = state.center_x + col
            ty: int = state.center_y + row
            px: int = (col + half_c) * TILE_PX
            py: int = (row + half_r) * TILE_PX

            tile_w: Widget = (
                WidgetBuilder(WidgetKey.IMAGE)
                .user_key(state.loader.tile_key(tx, ty))
                .pos(px, py)
                .size(TILE_PX, TILE_PX)
                .set_attr(AttrKey.SRC, state.loader.tile_key(tx, ty))
                .build()
            )
            tile_widgets.append(tile_w)
            col = col + 1
        row = row + 1

    return (
        WidgetBuilder(WidgetKey.SCREEN)
        .bg_color(0x000000)
        .with_children(tile_widgets)
    )


# --- Program ---

def create_map_program() -> Program:
    return Program(
        init_fn=map_init,
        update_fn=map_update,
        view_fn=map_view,
    )
```

### 4.4 Grid visualization

Viewport interpretation (4x3 grid on ESP32-P4, 1024x600 display):

```
tile coords (col, row) relative to center

(-2,-1)  (-1,-1)  (0,-1)  (+1,-1)
(-2, 0)  (-1, 0)  (0, 0)  (+1, 0)
(-2,+1)  (-1,+1)  (0,+1)  (+1,+1)

Each tile: 256x256 pixels
4 cols x 3 rows = 1024 x 768 (covers 1024x600 display)
```

ESP32-C6 (172x320 display): 1x2 grid, 256x512 pixels with clipping.

## 5. MVU Integration

The map viewer is an MVU application. The existing `lvgl_mvu` framework handles all LVGL lifecycle management. The map viewer only needs to define Model, Msg, init, update, view.

### 5.1 What lvgl_mvu provides (already exists)

- `Widget` / `WidgetBuilder` - immutable widget descriptors with fluent builder API
- `WidgetKey` - widget type enum (includes `IMAGE = 9`)
- `AttrKey` - attribute enum (includes `SRC = 144`)
- `diff_widgets` - O(N) tree diffing
- `Reconciler` - bridges Widget tree to LVGL objects
- `App` - MVU runtime with message queue and tick loop
- `Program` - connects init/update/view/subscribe functions

### 5.2 What lvgl_mvu needs (new additions for map viewer)

The framework already defines `WidgetKey.IMAGE = 9` and `AttrKey.SRC = 144` but lacks their implementations:

**factories.py** - add IMAGE factory:

```python
def create_image(parent: object) -> object:
    """Create an LVGL image widget."""
    return lv.lv_image_create(parent)

# In register_p0_factories:
reconciler.register_factory(WidgetKey.IMAGE, create_image)
```

**appliers.py** - add IMAGE source applier:

```python
def apply_image_src(lv_obj: object, value: object) -> None:
    """Set image source from an image descriptor.

    For the map viewer, value is a tile key string like "13/7261/3224".
    The actual image data loading is handled by a custom image source
    callback registered with LVGL.
    """
    lv.lv_image_set_src(lv_obj, value)

# In register_p0_appliers:
registry.add(AttrDef(AttrKey.SRC, "src", None, apply_image_src))
```

**dsl.py** - add Image DSL function:

```python
def Image() -> WidgetBuilder:
    """Create an image widget."""
    return WidgetBuilder(WidgetKey.IMAGE)
```

### 5.3 Image data loading strategy

The tricky part is getting RGB565 tile data into LVGL image widgets. Two approaches:

**Approach A: LVGL image descriptor (recommended)**

Create an `lv_image_dsc_t` per tile slot and set it as the image source. The tile data (RGB565 bytes from SD card) is pointed to by the descriptor. The reconciler's SRC applier creates/updates these descriptors.

This requires a thin helper function (compiled Python or interpreted) that:
1. Takes raw RGB565 bytes and tile dimensions
2. Creates an `lv_image_dsc_t` with the correct header
3. Calls `lv_image_set_src(img_obj, descriptor)`

**Approach B: LVGL file system driver**

Register a custom LVGL file system that reads `.bin` files from SD card. The SRC attribute becomes a file path string. LVGL handles the reading internally.

Approach A gives more control and is easier to implement incrementally.

### 5.4 App bootstrap (interpreted `main.py`)

The app entrypoint stays interpreted for fast iteration:

```python
# main.py (interpreted MicroPython, NOT compiled)
from map_viewer.map_app import create_map_program
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.attrs import AttrRegistry
from lvgl_mvu.factories import register_p0_factories, delete_lv_obj
from lvgl_mvu.appliers import register_p0_appliers
from lvgl_mvu.app import App
import lvgl as lv

# Setup
registry = AttrRegistry()
register_p0_appliers(registry)
reconciler = Reconciler(registry)
register_p0_factories(reconciler)
reconciler.set_delete_fn(delete_lv_obj)

# Create and run map app
program = create_map_program()
app = App(program, reconciler, lv.lv_screen_active())

# Main loop
while True:
    app.tick()
    lv.lv_timer_handler()
```

## 6. Hardware Acceleration (ESP32-P4)

The ESP32-P4 has dedicated hardware accelerators for image operations. The map viewer benefits from these automatically through LVGL, and can optionally leverage the JPEG decoder for storage savings.

### 6.1 PPA (Pixel Processing Accelerator)

The P4's primary graphics accelerator. Three hardware operations:

| Operation | API | What it does | Map viewer use |
|-----------|-----|-------------|----------------|
| **SRM** | `ppa_do_scale_rotate_mirror()` | Hardware bilinear blit/scale/rotate of image blocks | Tile blitting to framebuffer, zoom scaling |
| **Blend** | `ppa_do_blend()` | Alpha compositing two images | UI overlay on map (GPS marker, coordinates) |
| **Fill** | `ppa_do_fill()` | Fast solid rectangle fill | Background clearing between tiles |

Supported color formats: RGB565, RGB888, ARGB8888, YUV420/422/444, GRAY8.

Performance (256x256 RGB565 tile):

| Method | Time per tile | 12-tile grid | CPU usage |
|--------|---------------|-------------|-----------|
| CPU memcpy | ~5 ms | ~60 ms (16 fps) | 100% (blocking) |
| PPA hardware blit | ~1-2 ms | ~18 ms (55 fps) | <5% (DMA, non-blocking) |

PPA processes blocks via 2D-DMA, bypassing the CPU entirely. Performance scales with block size, not picture size. PSRAM bandwidth (250 MHz octal SPI, ~500 MB/s theoretical) is the bottleneck when multiple peripherals share PSRAM.

### 6.2 LVGL PPA Integration (automatic)

LVGL 9.4+ has built-in PPA support for ESP32-P4. When enabled, LVGL automatically uses PPA for:

- `lv_image_set_src()` -- PPA-accelerated blit (our tile rendering path)
- Rectangle fills -- PPA fill
- Alpha blending -- PPA blend for overlays

This means our MVU reconciler's IMAGE widget updates go through PPA hardware automatically. No changes to Python code needed.

**Firmware build requirement** -- enable in sdkconfig or menuconfig:

```
CONFIG_LV_USE_PPA=y
CONFIG_LV_PPA_BURST_LENGTH=128
```

Buffer alignment requirement: `CONFIG_LV_DRAW_BUF_ALIGN` must equal `CONFIG_CACHE_L2_CACHE_LINE_SIZE` (64 bytes on P4).

Performance gain from LVGL PPA integration: ~30% faster rendering, ~30% lower CPU usage compared to software rendering.

### 6.3 Hardware JPEG Decoder (optional optimization)

The P4 has a dedicated JPEG codec that decodes directly to RGB565 in hardware.

| | RGB565 raw (baseline) | JPEG + hardware decode |
|---|---|---|
| Tile size on SD | 128 KB | ~12 KB (10:1 compression) |
| Mt. Fuji 50km, zoom 12-14 | ~260 MB | ~26 MB |
| Tokyo metro 30km, zoom 13-15 | ~560 MB | ~56 MB |
| Decode time per tile | 0 ms (raw blit) | ~2 ms (hardware) |
| 12-tile refresh | ~18 ms | ~24 ms |
| Quality | Lossless | Lossy (configurable) |

API: `#include "driver/jpeg_decode.h"`

```c
jpeg_decoder_handle_t decoder;
jpeg_decode_engine_cfg_t dec_cfg = { .timeout_ms = 40 };
jpeg_new_decoder_engine(&dec_cfg, &decoder);

jpeg_decode_cfg_t decode_cfg = {
    .output_format = JPEG_DECODE_OUT_FORMAT_RGB565,
};
jpeg_decoder_process(decoder, &decode_cfg,
                     jpeg_data, jpeg_size,
                     rgb565_output, output_buf_size, &out_size);
```

Trade-off: JPEG saves 10x storage at the cost of ~6ms per frame and lossy quality. Worth it for larger coverage areas or when SD card space is limited.

### 6.4 PPA-Based Zoom (future optimization)

Instead of storing tiles at every zoom level, store fewer levels and use PPA's hardware bilinear scaling to interpolate between them:

- Store zoom 12 and 14 only
- For zoom 13, load zoom 12 tiles and use PPA SRM with `scale_x = 2.0, scale_y = 2.0`
- Halves storage requirements at the cost of slight interpolation blur
- Hardware scaling is fast: 256x256 -> 512x512 in ~2ms

This requires the SRC applier to detect the zoom mismatch and trigger a PPA scale operation.

### 6.5 What P4 does NOT have

- No GPU or graphics coprocessor (PPA is the "2D GPU")
- No hardware compositor or overlay layers (single-layer framebuffer)
- No RISC-V vector extension (RVV)
- No MicroPython PPA bindings (LVGL uses PPA automatically; direct PPA access requires C)

### 6.6 ESP32-P4 vs ESP32-S3 for graphics

| Feature | ESP32-P4 | ESP32-S3 |
|---------|----------|----------|
| CPU | 400 MHz RISC-V dual-core | 240 MHz Xtensa LX7 dual-core |
| SRAM | 768 KB | 512 KB |
| PSRAM | 16/32 MB (in-package, 250 MHz) | 8 MB (external) |
| Display interface | MIPI-DSI (up to 1080p) | Parallel RGB (up to 800x600) |
| PPA | Yes (SRM + Blend + Fill) | No |
| 2D-DMA | Yes (dedicated) | No (general GDMA only) |
| Hardware JPEG | Yes (encode + decode) | No |
| H.264 encoder | Yes (1080p@30fps) | No |

The P4 is purpose-built for image-heavy HMI applications.

### 6.7 Memory architecture notes

| Region | Size | Best use |
|--------|------|----------|
| HP SRAM | 768 KB (200 MHz, zero-wait) | Framebuffer, hot tile cache |
| TCM RAM | 8 KB (400 MHz) | Critical code paths |
| PSRAM | 16-32 MB (250 MHz) | Tile cache, decompression buffers |

PSRAM bandwidth is shared across display controller, PPA, JPEG decoder, and CPU. During tile rendering, minimize other PSRAM-heavy operations.

Cache configuration: L1 cache line 32 bytes, L2 cache line 64 bytes. PPA requires 128-byte burst alignment for maximum throughput.

## 7. Compiler Feature Requirements

The goal is to keep the compiled Python layer strictly within supported features.

| Feature | Used in | Status | Notes |
|---------|---------|--------|-------|
| `import math` | tile_math.py | Supported | math.sin, cos, tan, log, atan, sinh, pi |
| Float arithmetic | tile_math.py | Supported | *, /, +, - on floats |
| Bit shift (`<<`) | tile_math.py | Supported | For 2^zoom |
| `int()` cast | tile_math.py | Supported | Float to int conversion |
| Classes with `__init__` | tile_loader.py, map_app.py | Supported | |
| String concatenation | tile_loader.py | Supported | For path building |
| `str()` builtin | tile_loader.py | Supported | int to string |
| `open()` / file I/O | tile_loader.py | Needs runtime | MicroPython runtime call |
| `bytes` type | tile_loader.py | Needs investigation | May need runtime pass-through |
| `list[Widget]` | map_app.py | Supported | Lists |
| Cross-module imports | map_app.py imports tile_math | Supported | Package compilation |
| Import from lvgl_mvu | map_app.py | Supported | Cross-package imports |
| `isinstance()` check | map_app.py | Supported | For message dispatch |
| `WidgetBuilder` fluent API | map_app.py | Supported | Method chaining on objects |
| `tuple` returns | map_app.py | Supported | (Model, Cmd) return type |

## 8. Reference Implementation

Reference implementation to study:

- `0015/map_tiles` (MIT-licensed ESP-IDF component)
  - GitHub: https://github.com/0015/map_tiles
  - ESP Component Registry: https://components.espressif.com/components/0015/map_tiles
  - Example projects: https://github.com/0015/map_tiles_projects (includes ESP32-P4 example)

This is a pure C implementation. The goal here is to rewrite the logic in typed Python and compile it, not to compete with it on features.

Full GPS navigator reference:

- IceNav-v3: https://github.com/jgauchia/IceNav-v3

## 9. Target Hardware

| Board | Chip | Display | Resolution | RAM | Notes |
|-------|------|---------|-----------|-----|-------|
| ESP32-P4 Function EV Board | ESP32-P4 | 7-inch MIPI-DSI (ST7701 via EK79007AD) | 1024x600 | 32MB PSRAM | Primary target |
| ESP32-C6 Dev Board | ESP32-C6 | ST7789 SPI | 172x320 | 512KB SRAM | Secondary, constrained |

Memory budget planning:

- One RGB565 256x256 tile is 128 KiB.
- 4x3 grid (12 tiles) is about 1.5 MiB of pixel data.
- 2x2 grid (4 tiles) is about 0.5 MiB of pixel data.

ESP32-P4 with PSRAM handles this easily.
ESP32-C6 needs a smaller grid (1x2 or 2x2).

Suggested initial configurations:

| Board | Display | Default zoom | Grid | Tile slots | Coverage | Rationale |
|-------|---------|--------------|------|-----------:|----------|-----------|
| ESP32-P4 | 1024x600 | 13 | 4x3 | 12 | 1024x768 (overflow clipped) | Fills display, PSRAM friendly |
| ESP32-C6 | 172x320 | 14 | 1x2 | 2 | 256x512 (clipped to 172x320) | Fit in SRAM |

SD card interface:

- ESP32-P4: MicroSD slot with 4-bit SDMMC mode
- ESP32-C6: External SD card module via SPI

## 10. Milestones

Milestone 1: Tile Math Module (estimated: 1-2 days)

- Write `extmod/map_viewer/tile_math.py` with coordinate conversion functions.
- Compile to C with mypyc-micropython.
- Unit test: verify tile coordinates match known values.
- Device test: import and call from MicroPython REPL.
- Validates: float math, math module imports, bit shifts.

Milestone 2: Tile Preparation Pipeline (estimated: 1 day)

- Python script on PC to download OpenTopoMap tiles for a bounding box.
- Python script to convert PNG -> RGB565 .bin.
- Prepare test dataset: small area around Mt. Fuji (5x5km, zoom 13-14).
- Copy to SD card.

Milestone 3: Tile Loader Module (estimated: 2-3 days)

- Write `extmod/map_viewer/tile_loader.py` with SD card file reading.
- Compile to C.
- Device test: load a tile from SD card, verify data size and content.
- Validates: classes, string operations, file I/O integration.

Milestone 4: IMAGE Widget Support in lvgl_mvu (estimated: 2-3 days)

- Add `create_image` factory to `extmod/lvgl_mvu/factories.py`.
- Add `apply_image_src` applier to `extmod/lvgl_mvu/appliers.py`.
- Add `Image()` DSL function to `extmod/lvgl_mvu/dsl.py`.
- Write helper for creating `lv_image_dsc_t` from RGB565 bytes.
- Device test: display a single RGB565 tile as an LVGL image widget.
- Validates: extending the MVU framework with new widget types.

Milestone 5: Map Display MVU App (estimated: 3-5 days)

- Write `extmod/map_viewer/map_app.py` with MVU Program (init, update, view).
- Integrate tile_math and tile_loader.
- Build firmware and test on ESP32-P4.
- Goal: static map display showing tile grid at a fixed GPS location (Mt. Fuji).
- Validates: cross-package imports, MVU app lifecycle, Widget tree construction.

Milestone 6: Interactive Features (estimated: 3-5 days)

- Touch-based panning (drag to move map via PanMsg).
- Zoom in/out buttons (via MSG_ZOOM_IN/MSG_ZOOM_OUT).
- GPS coordinate display overlay.
- Smooth tile transitions on pan/zoom.

Milestone 7: Documentation and Blog Post (estimated: 2 days)

- Write blog post for blogs/ directory.
- Update AGENTS.md if needed.
- Record demo video.

## 11. How to Run

Step-by-step commands:

```bash
# 1. Prepare tiles (on PC)
python scripts/download_tiles.py --bbox "35.3,138.6,35.5,138.9" --zoom 13-14 --output tiles/
python scripts/convert_tiles.py --input tiles/ --output sdcard/

# 2. Copy tiles to SD card
# (physically copy sdcard/ directory to FAT32-formatted SD card)

# 3. Compile all extmod packages to C (includes map_viewer + lvgl_mvu)
make compile-all BOARD=ESP32_GENERIC_P4

# 4. Build firmware
make build BOARD=ESP32_GENERIC_P4

# 5. Flash and test
make flash BOARD=ESP32_GENERIC_P4 PORT=/dev/cu.usbmodem2101
make run-device-base-tests PORT=/dev/cu.usbmodem2101
```

For ESP32-C6, swap `BOARD=ESP32_GENERIC_C6` and use the correct serial port.

Practical runtime notes:

- SD card mount is board-specific. Keep it in `boot.py` or an interpreted `main.py` while iterating.
- The first rendering milestone can hard-code a known tile center and zoom to simplify bring-up.
- The interpreted `main.py` bootstraps the MVU app and runs the tick loop.

## 12. Open Questions

- `bytes` type support in the compiler: is it handled as mp_obj_t pass-through or does it need special support?
- Best approach for `lv_image_dsc_t` creation from Python: thin C helper vs. runtime construction via LVGL bindings?
- How to handle SD card mount (board-specific, stays in interpreted `main.py` or `boot.py`).
- Rate limiting for tile downloads: need to respect OpenTopoMap's usage policy.
- Tile caching strategy when PSRAM is limited (ESP32-C6 case).
- Can the image SRC applier load tile data lazily (on first render) or must tiles be pre-loaded into memory?
- Performance of MVU reconciliation with 12 image tiles -- is the diff overhead acceptable at 30fps?
- JPEG vs RGB565 tile format: should we support both and let the user choose at download time?
- PPA zoom interpolation: practical quality of 2x bilinear upscale for skipping zoom levels?
- Firmware build: is `LV_USE_PPA=1` already enabled in the current MicroPython LVGL build, or does it need sdkconfig changes?

## 13. Why This Project Matters for mypyc-micropython

- First non-trivial MVU application built with the compiler.
- Validates the `lvgl_mvu` framework with a real use case beyond counter/button demos.
- Exercises nearly every supported feature: math, classes, lists, tuples, strings, cross-module imports, cross-package imports.
- Tests real hardware integration (SD card, display, touch).
- Proves the value proposition: "Write Python, get native C performance on ESP32".
- The tile math functions are a perfect benchmark target (heavy float computation).
- Enables a clean comparison: compiled tile math vs interpreted MicroPython tile math.
- Extends the MVU framework with IMAGE widget support, benefiting other future apps.
- Demonstrates ESP32-P4 hardware acceleration (PPA, JPEG decoder) working transparently through the LVGL + MVU stack.
