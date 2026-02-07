# AI Agent Instructions for mypyc-micropython

This document provides instructions for AI agents to set up, build, and deploy this project.

## Project Overview

**mypyc-micropython** compiles typed Python functions to native C modules for MicroPython, enabling high-performance code on embedded devices like ESP32.

```
Python source → mypyc compiler → C module → MicroPython firmware → ESP32 device
```

## Quick Reference

| Task | Command |
|------|---------|
| Install Python deps | `pip install -e ".[dev]"` |
| Install ESP-IDF | `make setup-idf` (30 min, 2GB) |
| Build mpy-cross | `make setup-mpy` |
| Compile Python→C | `make compile SRC=examples/factorial.py` |
| Compile all examples | `make compile-all` |
| Build firmware | `source ~/esp/esp-idf/export.sh && make build BOARD=ESP32_GENERIC_C3` |
| Flash to device | `make flash BOARD=ESP32_GENERIC_C3 PORT=/dev/cu.usbmodem101` |
| Test on device | `mpremote connect /dev/cu.usbmodem101 exec "import factorial; print(factorial.factorial(5))"` |

## Directory Structure

```
mypyc-micropython/
├── src/                    # Python compiler source code
├── examples/               # Example Python files to compile
├── modules/                # Output: compiled C modules
│   ├── micropython.cmake   # Auto-generated cmake includes
│   └── usermod_*/          # Generated C module folders
├── deps/
│   └── micropython/        # MicroPython git submodule (v1.24.1)
├── Makefile                # Build automation
└── AGENTS.md               # This file
```

## Setup Instructions (Fresh Machine)

### Prerequisites

- macOS or Linux
- Python 3.9+ with pip
- Git
- ~3GB disk space for ESP-IDF toolchain

### Step 1: Clone and Initialize

```bash
git clone <repo-url> mypyc-micropython
cd mypyc-micropython

# Initialize MicroPython submodule
git submodule update --init --recursive
```

### Step 2: Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Or with pyenv
pyenv virtualenv 3.10.15 mypyc-micropython
pyenv activate mypyc-micropython

# Install project dependencies
pip install -e ".[dev]"

# Verify installation
mpy-compile --help
```

### Step 3: Install ESP-IDF Toolchain

**IMPORTANT**: MicroPython v1.24.1 requires ESP-IDF v5.2.2 (NOT v5.2.3+)

```bash
# Clone ESP-IDF v5.2.2
mkdir -p ~/esp
git clone -b v5.2.2 --recursive https://github.com/espressif/esp-idf.git ~/esp/esp-idf

# Install toolchain for ESP32 variants (~20-30 minutes)
cd ~/esp/esp-idf
./install.sh esp32,esp32c3,esp32s3
```

### Step 4: Fix ESP-IDF Python Check Bug (Required)

ESP-IDF v5.2.x has a known bug with `ruamel.yaml` metadata detection. Apply this workaround:

```bash
# Patch the check script to always succeed
cat > ~/esp/esp-idf/tools/check_python_dependencies.py << 'EOF'
#!/usr/bin/env python
# Patched to bypass ruamel.yaml metadata bug
import sys
sys.exit(0)
EOF
```

**Why this is needed**: The `ruamel.yaml` package installs correctly but its metadata isn't recognized by `importlib.metadata`, causing false failures in ESP-IDF's dependency checker. The tools work fine despite this.

### Step 5: Build mpy-cross Compiler

```bash
source ~/esp/esp-idf/export.sh
make setup-mpy
```

## Building Firmware

### Compile Python to C Modules

```bash
# Compile single file
make compile SRC=examples/factorial.py

# Compile all examples
make compile-all
```

This generates:
- `modules/usermod_<name>/<name>.c` - C implementation
- `modules/usermod_<name>/micropython.cmake` - CMake config
- `modules/micropython.cmake` - Master include file

### Build MicroPython Firmware

**Always source ESP-IDF environment first!**

```bash
source ~/esp/esp-idf/export.sh

# For ESP32-C3 (common dev boards)
make build BOARD=ESP32_GENERIC_C3

# For ESP32 (original)
make build BOARD=ESP32_GENERIC

# For ESP32-S3
make build BOARD=ESP32_GENERIC_S3
```

Build output: `deps/micropython/ports/esp32/build-<BOARD>/micropython.bin`

### Flash to Device

```bash
# Find USB device
ls /dev/cu.usb*  # macOS
ls /dev/ttyUSB*  # Linux

# Flash
source ~/esp/esp-idf/export.sh
make flash BOARD=ESP32_GENERIC_C3 PORT=/dev/cu.usbmodem101
```

## Testing on Device

### Using mpremote

```bash
# Interactive REPL
mpremote connect /dev/cu.usbmodem101 repl

# Execute code
mpremote connect /dev/cu.usbmodem101 exec "
import factorial
print(factorial.factorial(10))
print(factorial.fib(15))
"

# Run script file
mpremote connect /dev/cu.usbmodem101 run test_script.py
```

### Expected Test Output

```python
>>> import factorial
>>> factorial.factorial(5)
120
>>> factorial.fib(10)
55
>>> factorial.add(100, 200)
300
>>> factorial.multiply(3.14, 2.0)
6.28
>>> factorial.is_even(42)
True
```

## Troubleshooting

### "ESP-IDF not found"

```bash
# Install ESP-IDF
make setup-idf

# Or manually
git clone -b v5.2.2 --recursive https://github.com/espressif/esp-idf.git ~/esp/esp-idf
cd ~/esp/esp-idf && ./install.sh esp32,esp32c3
```

### "Python requirements not satisfied" (ruamel.yaml)

Apply the patch from Step 4. This is a known ESP-IDF bug.

### "This chip is ESP32-C3, not ESP32"

You're building for the wrong board. Check your chip:

```bash
# Auto-detect chip
esptool.py --port /dev/cu.usbmodem101 chip_id
```

Then build for correct board:
- ESP32-C3 → `BOARD=ESP32_GENERIC_C3`
- ESP32 → `BOARD=ESP32_GENERIC`
- ESP32-S3 → `BOARD=ESP32_GENERIC_S3`

### "USB_SERIAL_JTAG_PACKET_SZ_BYTES undeclared"

ESP-IDF version mismatch. Use v5.2.2:

```bash
cd ~/esp/esp-idf
git checkout v5.2.2
git submodule update --init --recursive
./install.sh esp32,esp32c3
```

### Build takes too long / runs out of memory

ESP32 builds are resource-intensive. Ensure:
- 4GB+ RAM available
- Use `-j4` or lower parallelism if needed
- First build takes 5-10 minutes; subsequent builds are faster

### "No module named 'factorial'" on device

The firmware wasn't built with user modules. Verify:

```bash
# Check modules are compiled
ls modules/usermod_*/

# Check cmake includes them
cat modules/micropython.cmake

# Rebuild with modules
source ~/esp/esp-idf/export.sh
make build BOARD=ESP32_GENERIC_C3
```

## Supported Boards

| Board | BOARD Variable | Chip |
|-------|----------------|------|
| ESP32 DevKit | `ESP32_GENERIC` | ESP32 |
| ESP32-C3 DevKit | `ESP32_GENERIC_C3` | ESP32-C3 |
| ESP32-S3 DevKit | `ESP32_GENERIC_S3` | ESP32-S3 |

List all boards: `make list-boards`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOARD` | `ESP32_GENERIC` | Target board |
| `PORT` | `/dev/cu.usbmodem101` | Serial port |
| `ESP_IDF_DIR` | `~/esp/esp-idf` | ESP-IDF installation |

## Version Compatibility Matrix

| MicroPython | ESP-IDF | Status |
|-------------|---------|--------|
| v1.24.1 | v5.2.2 | ✅ Tested |
| v1.24.1 | v5.2.0 | ✅ Should work |
| v1.24.1 | v5.2.3 | ❌ Build errors on ESP32-C3 |
| v1.24.1 | v5.1.x | ⚠️ May work |

## Complete Setup Script

For automated setup, run:

```bash
#!/bin/bash
set -e

# 1. Install Python dependencies
pip install -e ".[dev]"

# 2. Initialize submodules
git submodule update --init --recursive

# 3. Install ESP-IDF v5.2.2
if [ ! -d "$HOME/esp/esp-idf" ]; then
    mkdir -p ~/esp
    git clone -b v5.2.2 --recursive https://github.com/espressif/esp-idf.git ~/esp/esp-idf
    cd ~/esp/esp-idf
    ./install.sh esp32,esp32c3,esp32s3
fi

# 4. Patch ESP-IDF check script
cat > ~/esp/esp-idf/tools/check_python_dependencies.py << 'EOF'
#!/usr/bin/env python
import sys
sys.exit(0)
EOF

# 5. Build mpy-cross
source ~/esp/esp-idf/export.sh
make -C deps/micropython/mpy-cross

# 6. Compile example modules
make compile-all

echo "Setup complete! Run:"
echo "  source ~/esp/esp-idf/export.sh"
echo "  make build BOARD=ESP32_GENERIC_C3"
```

## Files Modified by Setup

After setup, these files/directories are created:

| Path | Description |
|------|-------------|
| `~/esp/esp-idf/` | ESP-IDF installation (~2GB) |
| `~/.espressif/` | ESP-IDF tools and Python venv |
| `deps/micropython/mpy-cross/build/` | mpy-cross compiler |
| `modules/usermod_*/` | Compiled C modules |

## Cleaning Up

```bash
# Clean compiled modules
make clean

# Clean MicroPython build
make clean-all

# Full reset (removes ESP-IDF)
rm -rf ~/esp/esp-idf ~/.espressif
```
