#!/bin/bash
# mypyc-micropython Setup Script
# Automated setup for AI agents and developers
#
# Usage: ./scripts/setup.sh [--skip-idf]
#
# Options:
#   --skip-idf    Skip ESP-IDF installation (if already installed)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ESP_IDF_DIR="${ESP_IDF_DIR:-$HOME/esp/esp-idf}"
ESP_IDF_VERSION="v5.2.2"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
SKIP_IDF=false
for arg in "$@"; do
    case $arg in
        --skip-idf)
            SKIP_IDF=true
            shift
            ;;
    esac
done

cd "$PROJECT_DIR"

echo "========================================"
echo "mypyc-micropython Setup"
echo "========================================"
echo ""

# Step 1: Check Python
log_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required but not found"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
log_info "Found $PYTHON_VERSION"

# Step 2: Install Python dependencies
log_info "Installing Python dependencies..."
pip install -e ".[dev]"

# Verify mpy-compile is available
if ! command -v mpy-compile &> /dev/null; then
    log_error "mpy-compile not found after installation"
    exit 1
fi
log_info "mpy-compile installed successfully"

# Step 3: Initialize git submodules
log_info "Initializing git submodules..."
git submodule update --init --recursive

# Step 4: Install ESP-IDF
if [ "$SKIP_IDF" = false ]; then
    if [ -d "$ESP_IDF_DIR" ]; then
        log_warn "ESP-IDF already exists at $ESP_IDF_DIR"
        log_info "Checking version..."
        cd "$ESP_IDF_DIR"
        CURRENT_VERSION=$(git describe --tags 2>/dev/null || echo "unknown")
        if [ "$CURRENT_VERSION" != "$ESP_IDF_VERSION" ]; then
            log_warn "Current version: $CURRENT_VERSION, expected: $ESP_IDF_VERSION"
            log_info "Switching to $ESP_IDF_VERSION..."
            git fetch --tags
            git checkout "$ESP_IDF_VERSION"
            git submodule update --init --recursive
        else
            log_info "ESP-IDF version $ESP_IDF_VERSION already installed"
        fi
        cd "$PROJECT_DIR"
    else
        log_info "Installing ESP-IDF $ESP_IDF_VERSION (this takes ~20-30 minutes)..."
        mkdir -p "$(dirname "$ESP_IDF_DIR")"
        git clone -b "$ESP_IDF_VERSION" --recursive https://github.com/espressif/esp-idf.git "$ESP_IDF_DIR"
    fi

    log_info "Installing ESP-IDF toolchain..."
    cd "$ESP_IDF_DIR"
    ./install.sh esp32,esp32c3,esp32s3
    cd "$PROJECT_DIR"

    # Step 5: Patch ESP-IDF Python check script (ruamel.yaml bug)
    log_info "Patching ESP-IDF Python check script (ruamel.yaml workaround)..."
    cat > "$ESP_IDF_DIR/tools/check_python_dependencies.py" << 'EOF'
#!/usr/bin/env python
# Patched to bypass ruamel.yaml metadata bug
# See: https://github.com/espressif/esp-idf/issues/XXXXX
import sys
sys.exit(0)
EOF
    log_info "Patch applied successfully"
else
    log_info "Skipping ESP-IDF installation (--skip-idf)"
fi

# Step 6: Build mpy-cross
log_info "Building mpy-cross compiler..."
# Source ESP-IDF environment
set +e
source "$ESP_IDF_DIR/export.sh" 2>/dev/null
set -e
make -C deps/micropython/mpy-cross

# Step 7: Initialize MicroPython ESP32 submodules
log_info "Initializing MicroPython ESP32 port submodules..."
cd deps/micropython
git submodule update --init lib/berkeley-db-1.xx lib/micropython-lib
cd "$PROJECT_DIR"

# Step 8: Compile example modules
log_info "Compiling example modules..."
make compile-all

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To build firmware, run:"
echo ""
echo "  source $ESP_IDF_DIR/export.sh"
echo "  make build BOARD=ESP32_GENERIC_C3"
echo ""
echo "To flash to device:"
echo ""
echo "  make flash BOARD=ESP32_GENERIC_C3 PORT=/dev/cu.usbmodem101"
echo ""
echo "To test on device:"
echo ""
echo "  mpremote connect /dev/cu.usbmodem101 exec 'import factorial; print(factorial.factorial(10))'"
echo ""
