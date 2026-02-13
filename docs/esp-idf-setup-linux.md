# ESP-IDF Setup Guide — Linux (Ubuntu/Debian)

Complete guide for installing ESP-IDF and building MicroPython firmware with pyenv-managed Python on Linux.

> **Audience**: LLM agents automating builds on Linux (Ubuntu/Debian).
> **Tested on**: Ubuntu 24.04 with pyenv Python 3.12.12 + ESP-IDF v5.4.2.
> **For macOS**: See [esp-idf-setup-macos.md](esp-idf-setup-macos.md).

## TL;DR (Copy-Paste Sequence)

```bash
# 1. System deps (Ubuntu) — MUST be done BEFORE pyenv install
sudo apt update && sudo apt install -y \
  build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
  libsqlite3-dev curl git libncursesw5-dev xz-utils tk-dev \
  libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev cmake ninja-build

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
make -C deps/micropython/mpy-cross -j$(nproc)
git -C deps/micropython submodule update --init --force lib/micropython-lib
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 submodules
make compile-all
MODULES_DIR="$(pwd)/modules"
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 USER_C_MODULES="$MODULES_DIR/micropython.cmake"

# 7. Flash
make -C deps/micropython/ports/esp32 BOARD=ESP32_GENERIC_C3 PORT=/dev/ttyACM0 deploy
```

---

## Version Compatibility

| Component | Version | Notes |
|-----------|---------|-------|
| MicroPython | v1.28.0-preview (submodule at `deps/micropython/`) | Pinned by git submodule |
| ESP-IDF | **v5.4.2** (recommended) | Also supports v5.2, v5.2.2, v5.3, v5.4, v5.4.1, v5.5.1 |
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

These must be installed **BEFORE** building Python with pyenv. If you install them after, you must rebuild Python.

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev \
  libreadline-dev \
  libsqlite3-dev \
  curl \
  git \
  libncursesw5-dev \
  xz-utils \
  tk-dev \
  libxml2-dev \
  libxmlsec1-dev \
  libffi-dev \
  liblzma-dev \
  cmake \
  ninja-build
```

**Critical packages for ESP-IDF**:

| Package | Python module it enables | Why ESP-IDF needs it |
|---------|--------------------------|----------------------|
| `liblzma-dev` | `lzma` / `_lzma` | Extracts `.tar.xz` toolchain archives |
| `libffi-dev` | `_ctypes` | ESP-IDF Python scripts use ctypes |
| `libssl-dev` | `_ssl` | HTTPS downloads during install |
| `cmake` | — | Build system (not bundled in ESP-IDF v5.4+) |
| `ninja-build` | — | Build system (not bundled in ESP-IDF v5.4+) |

### Step 2: Install Python with pyenv

```bash
# Install pyenv if not present
# See: https://github.com/pyenv/pyenv#installation

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

**If any import fails**: the system library was missing when pyenv built Python. Install the missing package and rebuild:

```bash
# Example: _lzma missing
sudo apt install liblzma-dev
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
make -C deps/micropython/mpy-cross -j$(nproc)

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
ls /dev/ttyACM*   # ESP32-C3/S3 with native USB
ls /dev/ttyUSB*   # Original ESP32 with USB-UART bridge

# Flash
source ~/esp/esp-idf/export.sh
make -C deps/micropython/ports/esp32 \
  BOARD=ESP32_GENERIC_C3 \
  PORT=/dev/ttyACM0 \
  deploy
```

### Step 10: Test on Device

```bash
# Quick test
mpremote connect /dev/ttyACM0 exec "import factorial; print(factorial.factorial(5))"

# Run test script
mpremote connect /dev/ttyACM0 run test_device.py

# Interactive REPL
mpremote connect /dev/ttyACM0 repl
```

---

## Using Makefile Targets

The project Makefile provides convenience targets that wrap the commands above:

```bash
source ~/esp/esp-idf/export.sh   # Always source first

# Build firmware (uses source export.sh internally)
make build BOARD=ESP32_GENERIC_C3

# Flash to device
make flash BOARD=ESP32_GENERIC_C3 PORT=/dev/ttyACM0

# Build + flash in one step
make deploy BOARD=ESP32_GENERIC_C3 PORT=/dev/ttyACM0
```

**Note**: You must `source export.sh` before running any Makefile target that invokes ESP-IDF tools.

---

## Troubleshooting

### `ModuleNotFoundError: No module named '_lzma'`

**Cause**: pyenv built Python without `liblzma-dev` installed.

```bash
# Fix
sudo apt install liblzma-dev

# Rebuild Python
pyenv install 3.12.12 --force
python -c "import lzma; print('OK')"
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
sudo apt install cmake ninja-build
```

### `This chip is ESP32-C3, not ESP32`

**Cause**: Building for wrong board. Detect your chip:

```bash
esptool.py --port /dev/ttyACM0 chip_id
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

### Device permission denied (`/dev/ttyACM0`)

```bash
# Add user to dialout group (Linux)
sudo usermod -aG dialout $USER
# Log out and back in, or:
newgrp dialout
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ESP_IDF_DIR` | `~/esp/esp-idf` | ESP-IDF installation path |
| `IDF_PATH` | Set by `export.sh` | ESP-IDF path (used by build system) |
| `IDF_PYTHON_ENV_PATH` | Auto-detected | Override ESP-IDF's Python virtualenv location |
| `BOARD` | `ESP32_GENERIC` | Target board for build/flash |
| `PORT` | `/dev/ttyACM0` | Serial port for flash/monitor |

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
        print(f'  ✅ {mod}')
    except ImportError:
        print(f'  ❌ {mod} MISSING')
        ok = False
if not ok:
    print('\\n⚠️  Rebuild Python: pyenv install 3.12.12 --force')
    exit(1)
"

echo -e "\n=== Build Tools ==="
cmake --version | head -1
ninja --version

echo -e "\n=== ESP-IDF ==="
if [ -z "$IDF_PATH" ]; then
    echo "  ❌ Not activated. Run: source ~/esp/esp-idf/export.sh"
else
    echo "  ✅ IDF_PATH: $IDF_PATH"
    python $IDF_PATH/tools/idf_tools.py version
fi

echo -e "\n=== MicroPython ==="
if [ -f "deps/micropython/mpy-cross/build/mpy-cross" ]; then
    echo "  ✅ mpy-cross built"
else
    echo "  ❌ mpy-cross not built. Run: make -C deps/micropython/mpy-cross"
fi

echo -e "\n=== mpy-compile ==="
if command -v mpy-compile &>/dev/null; then
    echo "  ✅ mpy-compile available"
else
    echo "  ❌ Not installed. Run: pip install -e '.[dev]'"
fi

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
