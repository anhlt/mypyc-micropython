#!/bin/bash
set -e

ESP_IDF_VERSION="v5.2.3"
ESP_IDF_DIR="${ESP_IDF_DIR:-$HOME/esp/esp-idf}"

echo "=========================================="
echo "ESP-IDF Setup for mypyc-micropython"
echo "=========================================="
echo ""
echo "This will install:"
echo "  - ESP-IDF $ESP_IDF_VERSION (~2GB download)"
echo "  - Toolchains for ESP32, ESP32-C3, ESP32-S3"
echo ""
echo "Installation directory: $ESP_IDF_DIR"
echo ""
read -p "Continue? [y/N] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

mkdir -p "$(dirname "$ESP_IDF_DIR")"

if [ ! -d "$ESP_IDF_DIR" ]; then
    echo "Cloning ESP-IDF $ESP_IDF_VERSION..."
    git clone -b "$ESP_IDF_VERSION" --recursive \
        https://github.com/espressif/esp-idf.git "$ESP_IDF_DIR"
else
    echo "ESP-IDF already exists at $ESP_IDF_DIR"
    echo "Updating to $ESP_IDF_VERSION..."
    cd "$ESP_IDF_DIR"
    git fetch --tags
    git checkout "$ESP_IDF_VERSION"
    git submodule update --init --recursive
fi

echo ""
echo "Installing toolchains (this takes 15-30 minutes)..."
cd "$ESP_IDF_DIR"
./install.sh esp32,esp32c3,esp32s3

echo ""
echo "=========================================="
echo "ESP-IDF installation complete!"
echo "=========================================="
echo ""
echo "Add to your shell profile (~/.zshrc or ~/.bashrc):"
echo ""
echo "  alias esp-env='source $ESP_IDF_DIR/export.sh'"
echo ""
echo "Then use:"
echo "  esp-env              # Activate ESP-IDF environment"
echo "  make setup-mpy       # Build mpy-cross compiler"
echo "  make compile-all     # Compile Python examples to C"
echo "  make build           # Build firmware"
echo "  make flash           # Flash to device"
echo ""
