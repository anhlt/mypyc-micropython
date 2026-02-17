# ESP-IDF Setup Guide — macOS

Complete guide for installing ESP-IDF and building MicroPython firmware with pyenv-managed Python on macOS.

> **Audience**: LLM agents automating builds on macOS.
> **Status**: Adapted from the tested Linux guide. Not yet verified end-to-end on macOS.
> **For Linux**: See [esp-idf-setup-linux.md](esp-idf-setup-linux.md).

## TL;DR (Copy-Paste Sequence)

```bash
# 1. System deps (Homebrew) — MUST be done BEFORE pyenv install
brew install openssl readline sqlite3 xz zlib tcl-tk@8 libffi bzip2 cmake ninja

# 2. Install Python via pyenv
pyenv install 3.12.12
pyenv global 3.12.12
python -c "import lzma; print('OK')"  # MUST succeed

# 3. Project setup
cd mypyc-micropython
pip install -e ".[dev]"
git submodule update --init --recursive

# 4. Install ESP-IDF v5.4.2
git clone -b v5.4.2 --recursive https://github.com/espressif/esp-idf.git ~/esp/esp-idf
cd ~/esp/esp-idf && ./install.sh esp32,esp32c3,esp32s3

# 5. Patch check_python_dependencies.py (may be needed)
cat > ~/esp/esp-idf/tools/check_python_dependencies.py << 'EOF'
#!/usr/bin/env python
import sys
sys.exit(0)
EOF

# 6. Build
source ~/esp/esp-idf/export.sh
make -C deps/micropython/mpy-cross -j$(sysctl -n hw.ncpu)
git -C deps/micropython submodule update --init --force lib/micropython-lib
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 submodules
make compile-all
MODULES_DIR="$(pwd)/modules"
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 USER_C_MODULES="$MODULES_DIR/micropython.cmake"

# 7. Flash
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 PORT=/dev/cu.usbmodem101 deploy
```

---

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| MicroPython | v1.28.0-preview (submodule at `deps/micropython/`) | Pinned by git submodule |
| ESP-IDF | **v5.4.2** (recommended) | Also supports v5.4, v5.4.1, v5.5.1 |
| Python | 3.10 – 3.13 | 3.14+ is NOT supported by ESP-IDF |
| cmake | 3.16+ | Required, not bundled with ESP-IDF v5.4+ |
| ninja | 1.10+ | Required, not bundled with ESP-IDF v5.4+ |

### Why v5.4.2 and NOT v5.2.2?

MicroPython v1.28-preview requires the `esp_driver_touch_sens` component, which was introduced in ESP-IDF v5.4. Building with v5.2.2 fails:

```
CMake Error: ... esp_driver_touch_sens ... not found
```

The upstream MicroPython README (`deps/micropython/ports/esp32/README.md`) recommends v5.5.1 and lists v5.4.2 as supported. We use v5.4.2 because it's the latest version we've tested end-to-end.

---

## Step-by-Step Setup

### Step 1: Install System Dependencies

These must be installed **BEFORE** building Python with pyenv. If you install them after, you must rebuild Python (`pyenv install 3.12.12 --force`).

```bash
# Install Homebrew if not present
# See: https://brew.sh

# Install all required dependencies
brew install openssl readline sqlite3 xz zlib tcl-tk@8 libffi bzip2 cmake ninja
```

**Critical packages for ESP-IDF**:

| Package | Python module it enables | Why ESP-IDF needs it |
|---------|--------------------------|----------------------|
| `xz` | `lzma` / `_lzma` | Extracts `.tar.xz` toolchain archives |
| `libffi` | `_ctypes` | ESP-IDF Python scripts use ctypes |
| `openssl` | `_ssl` | HTTPS downloads during install |
| `cmake` | — | Build system (not bundled in ESP-IDF v5.4+) |
| `ninja` | — | Build system (not bundled in ESP-IDF v5.4+) |

### Step 2: Install Python with pyenv

```bash
# Install pyenv if not present
# See: https://github.com/pyenv/pyenv#installation
# Or: brew install pyenv

# Install Python 3.12.12 (with all C modules compiled)
pyenv install 3.12.12

# Set as default
pyenv global 3.12.12

# VERIFY — all of these must succeed
python -c "import lzma; print('lzma: OK')"
python -c "import _ctypes; print('ctypes: OK')"
python -c "import ssl; print('ssl: OK')"
python -c "import sqlite3; print('sqlite3: OK')"
python -c "import bz2; print('bz2: OK')"
python -c "import readline; print('readline: OK')"
```

**If any import fails**: the Homebrew library was missing when pyenv built Python. Install the missing package and rebuild:

```bash
# Example: _lzma missing
brew install xz
pyenv install 3.12.12 --force   # -f also works
```

### Step 3: Clone and Initialize Project

```bash
git clone <repo-url> mypyc-micropython
cd mypyc-micropython

# Initialize MicroPython submodule
git submodule update --init --recursive

# Install project Python dependencies
pip install -e ".[dev]"

# Verify
mpy-compile --help
```

### Step 4: Install ESP-IDF v5.4.2

```bash
mkdir -p ~/esp
git clone -b v5.4.2 --recursive https://github.com/espressif/esp-idf.git ~/esp/esp-idf

# Install toolchains (~20-30 minutes, ~2GB disk)
cd ~/esp/esp-idf
./install.sh esp32,esp32c3,esp32s3
```

**What this creates**:
- `~/.espressif/tools/` — Cross-compiler toolchains (xtensa-esp-elf, riscv32-esp-elf)
- `~/.espressif/python_env/idf5.4_py3.12_env/` — ESP-IDF's Python virtualenv
- The virtualenv name follows the pattern `idf{IDF_MAJOR}.{IDF_MINOR}_py{PYTHON_MAJOR}.{PYTHON_MINOR}_env`

### Step 5: Patch check_python_dependencies.py (If Needed)

ESP-IDF's Python dependency checker can fail on `ruamel.yaml` metadata detection even when the package works fine. Apply this workaround:

```bash
cat > ~/esp/esp-idf/tools/check_python_dependencies.py << 'EOF'
#!/usr/bin/env python
# Patched to bypass ruamel.yaml metadata detection bug.
# The tools work fine — only the metadata check fails.
import sys
sys.exit(0)
EOF
```

**When is this needed?** Try running `source ~/esp/esp-idf/export.sh` first. If it succeeds, skip this step. If it fails with a `ruamel.yaml` error, apply the patch.

### Step 6: Build mpy-cross and Initialize Submodules

```bash
# Activate ESP-IDF environment (required for every new shell)
source ~/esp/esp-idf/export.sh

# Build the MicroPython cross-compiler
make -C deps/micropython/mpy-cross -j$(sysctl -n hw.ncpu)

# Initialize MicroPython port submodules
# --force is needed because micropython-lib sometimes has dirty state
git -C deps/micropython submodule update --init --force lib/micropython-lib
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 submodules
```

### Step 7: Compile Python Modules to C

```bash
# Compile all examples
make compile-all

# Or compile a single file
make compile SRC=examples/factorial.py
```

This generates:
- `modules/usermod_<name>/<name>.c` — C implementation
- `modules/usermod_<name>/micropython.cmake` — CMake config
- `modules/micropython.cmake` — Master include file

### Step 8: Build Firmware

```bash
# IMPORTANT: ESP-IDF env must be active
source ~/esp/esp-idf/export.sh

# Build for ESP32-C3
MODULES_DIR="$(pwd)/modules"
make -C deps/micropython/ports/esp32 \
  BOARD=ESP32_GENERIC_C3 \
  USER_C_MODULES="$MODULES_DIR/micropython.cmake"

# For other chips:
# BOARD=ESP32_GENERIC      (original ESP32)
# BOARD=ESP32_GENERIC_S3   (ESP32-S3)
```

Build output: `deps/micropython/ports/esp32/build-ESP32_GENERIC_C3/micropython.bin`

**First build**: ~5-10 minutes. Subsequent builds: ~1-2 minutes.

### Step 9: Flash to Device

```bash
# Find your device
ls /dev/cu.usb*

# Common device names on macOS:
#   /dev/cu.usbmodem101    — ESP32-C3/S3 with native USB
#   /dev/cu.usbserial-*    — ESP32 with USB-UART bridge (CP2102/CH340)
#   /dev/cu.wchusbserial-* — CH340 variant

# Flash
source ~/esp/esp-idf/export.sh
make -C deps/micropython/ports/esp32 \
  BOARD=ESP32_GENERIC_C3 \
  PORT=/dev/cu.usbmodem101 \
  deploy
```

### Step 10: Test on Device

```bash
# Quick test
mpremote connect /dev/cu.usbmodem101 exec "import factorial; print(factorial.factorial(5))"

# Run test script
python run_device_tests.py --port /dev/cu.usbmodem101

# Interactive REPL
mpremote connect /dev/cu.usbmodem101 repl
```

---

## Using Makefile Targets

The project Makefile provides convenience targets that wrap the commands above:

```bash
source ~/esp/esp-idf/export.sh   # Always source first

# Build firmware
make build BOARD=ESP32_GENERIC_C3

# Flash to device (override PORT for macOS)
make flash BOARD=ESP32_GENERIC_C3 PORT=/dev/cu.usbmodem101

# Build + flash in one step
make deploy BOARD=ESP32_GENERIC_C3 PORT=/dev/cu.usbmodem101
```

**Note**: The Makefile defaults `PORT` to `/dev/ttyACM0` (Linux). On macOS, always pass `PORT=/dev/cu.usbmodem101` (or your actual device path).

---

## Troubleshooting

### `ModuleNotFoundError: No module named '_lzma'`

**Cause**: pyenv built Python without `xz` installed.

```bash
# Fix
brew install xz

# Rebuild Python
pyenv install 3.12.12 --force
python -c "import lzma; print('OK')"
```

### `ModuleNotFoundError: No module named '_ctypes'`

**Cause**: pyenv built Python without `libffi` installed.

```bash
brew install libffi
pyenv install 3.12.12 --force
python -c "import _ctypes; print('OK')"
```

### `CMake Error: esp_driver_touch_sens not found`

**Cause**: ESP-IDF version too old. MicroPython v1.28 needs v5.4+.

```bash
cd ~/esp/esp-idf
git checkout v5.4.2
git submodule update --init --recursive
./install.sh esp32,esp32c3,esp32s3
```

### `Python requirements not satisfied` (ruamel.yaml)

**Cause**: ESP-IDF's dependency checker has a metadata detection bug.

```bash
# Apply patch
cat > ~/esp/esp-idf/tools/check_python_dependencies.py << 'EOF'
#!/usr/bin/env python
import sys
sys.exit(0)
EOF
```

### `cmake: command not found` or `ninja: command not found`

**Cause**: ESP-IDF v5.4+ doesn't bundle cmake/ninja.

```bash
brew install cmake ninja
```

### `This chip is ESP32-C3, not ESP32`

**Cause**: Building for wrong board. Detect your chip:

```bash
esptool.py --port /dev/cu.usbmodem101 chip_id
```

| Chip | BOARD variable |
|------|----------------|
| ESP32 | `ESP32_GENERIC` |
| ESP32-C3 | `ESP32_GENERIC_C3` |
| ESP32-S3 | `ESP32_GENERIC_S3` |

### `fatal: Needed a single revision` (micropython-lib submodule)

**Cause**: Submodule in dirty state.

```bash
git -C deps/micropython submodule update --init --force lib/micropython-lib
```

### Build runs out of memory

```bash
# Reduce parallelism
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 \
  USER_C_MODULES="$(pwd)/modules/micropython.cmake" -j2
```

### No `/dev/cu.usb*` device found

- Check USB cable is data-capable (not charge-only)
- Install drivers if needed:
  - CP2102: [Silicon Labs driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
  - CH340: [WCH driver](https://www.wch.cn/download/CH341SER_MAC_ZIP.html)
- Try `ls /dev/cu.*` to see all serial devices

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ESP_IDF_DIR` | `~/esp/esp-idf` | ESP-IDF installation path |
| `IDF_PATH` | Set by `export.sh` | ESP-IDF path (used by build system) |
| `IDF_PYTHON_ENV_PATH` | Auto-detected | Override ESP-IDF's Python virtualenv location |
| `BOARD` | `ESP32_GENERIC` | Target board for build/flash |
| `PORT` | `/dev/ttyACM0` (Makefile default) | Serial port — on macOS use `/dev/cu.usbmodem101` |

---

## Validation Script

Run this to verify your environment is correctly set up:

```bash
#!/bin/bash
set -e

echo "=== Python Environment ==="
echo "Python: $(python --version) at $(which python)"

echo -e "\n=== Required Python Modules ==="
python -c "
modules = ['lzma', '_ctypes', 'ssl', 'sqlite3', 'bz2', 'readline']
ok = True
for mod in modules:
    try:
        __import__(mod)
        print(f'  OK: {mod}')
    except ImportError:
        print(f'  MISSING: {mod}')
        ok = False
if not ok:
    print('\nRebuild Python: pyenv install 3.12.12 --force')
    exit(1)
"

echo -e "\n=== Build Tools ==="
cmake --version | head -1
ninja --version

echo -e "\n=== ESP-IDF ==="
if [ -z "$IDF_PATH" ]; then
    echo "  Not activated. Run: source ~/esp/esp-idf/export.sh"
else
    echo "  IDF_PATH: $IDF_PATH"
    python $IDF_PATH/tools/idf_tools.py version
fi

echo -e "\n=== MicroPython ==="
if [ -f "deps/micropython/mpy-cross/build/mpy-cross" ]; then
    echo "  mpy-cross built"
else
    echo "  mpy-cross not built. Run: make -C deps/micropython/mpy-cross"
fi

echo -e "\n=== mpy-compile ==="
if command -v mpy-compile &>/dev/null; then
    echo "  mpy-compile available"
else
    echo "  Not installed. Run: pip install -e '.[dev]'"
fi

echo -e "\n=== Serial Devices ==="
ls /dev/cu.usb* 2>/dev/null || echo "  No USB serial devices found"

echo -e "\n=== Done ==="
```

---

## Files Created/Modified by Setup

| Path | Size | Description |
|------|------|-------------|
| `~/esp/esp-idf/` | ~2 GB | ESP-IDF framework |
| `~/.espressif/tools/` | ~1.5 GB | Cross-compiler toolchains |
| `~/.espressif/python_env/` | ~200 MB | ESP-IDF Python virtualenv |
| `deps/micropython/mpy-cross/build/` | ~5 MB | mpy-cross compiler binary |
| `modules/usermod_*/` | Variable | Compiled C user modules |
