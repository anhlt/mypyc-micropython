# mypyc-micropython Build System
# ================================
# Compiles typed Python to MicroPython native C modules and builds firmware

# Configuration
BOARD ?= ESP32_GENERIC
PORT ?= /dev/cu.usbmodem101
BAUD ?= 460800

# Paths
ROOT_DIR := $(shell pwd)
MICROPYTHON_DIR := $(ROOT_DIR)/deps/micropython
ESP_IDF_DIR ?= $(HOME)/esp/esp-idf
MODULES_DIR := $(ROOT_DIR)/modules
BUILD_DIR := $(ROOT_DIR)/build

# MicroPython port
MP_PORT_DIR := $(MICROPYTHON_DIR)/ports/esp32

# User modules cmake file
USER_C_MODULES := $(MODULES_DIR)/micropython.cmake

.PHONY: help setup setup-idf setup-mpy compile build flash monitor clean \
        test repl compile-all check-env

# Default target
help:
	@echo "mypyc-micropython Build System"
	@echo "==============================="
	@echo ""
	@echo "SETUP (one-time):"
	@echo "  make setup          - Complete setup (ESP-IDF + MicroPython)"
	@echo "  make setup-idf      - Install ESP-IDF toolchain (~30min, ~2GB)"
	@echo "  make setup-mpy      - Build mpy-cross compiler"
	@echo ""
	@echo "DEVELOPMENT:"
	@echo "  make compile SRC=examples/factorial.py"
	@echo "                      - Compile Python file to C module"
	@echo "  make compile-all    - Compile all examples"
	@echo ""
	@echo "BUILD & FLASH:"
	@echo "  make build          - Build MicroPython firmware with modules"
	@echo "  make flash          - Flash firmware to device"
	@echo "  make monitor        - Open serial monitor"
	@echo "  make deploy         - Build + Flash + Monitor"
	@echo ""
	@echo "TESTING:"
	@echo "  make test           - Run Python tests via mpremote"
	@echo "  make repl           - Open MicroPython REPL"
	@echo ""
	@echo "CLEANUP:"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make clean-all      - Clean everything including ESP-IDF build"
	@echo ""
	@echo "CONFIGURATION:"
	@echo "  BOARD=$(BOARD)"
	@echo "  PORT=$(PORT)"
	@echo "  ESP_IDF_DIR=$(ESP_IDF_DIR)"

# ============================================================================
# SETUP TARGETS
# ============================================================================

check-env:
	@if [ ! -d "$(ESP_IDF_DIR)" ]; then \
		echo "ERROR: ESP-IDF not found at $(ESP_IDF_DIR)"; \
		echo "Run 'make setup-idf' first"; \
		exit 1; \
	fi

setup: setup-idf setup-mpy
	@echo ""
	@echo "Setup complete!"
	@echo ""
	@echo "Add this to your shell profile (.zshrc/.bashrc):"
	@echo "  alias esp-env='source $(ESP_IDF_DIR)/export.sh'"
	@echo ""
	@echo "Then run: esp-env && make build"

setup-idf:
	@echo "Installing ESP-IDF v5.2.2..."
	@mkdir -p $(HOME)/esp
	@if [ ! -d "$(ESP_IDF_DIR)" ]; then \
		git clone -b v5.2.2 --recursive https://github.com/espressif/esp-idf.git $(ESP_IDF_DIR); \
	else \
		echo "ESP-IDF already exists at $(ESP_IDF_DIR)"; \
	fi
	@echo "Installing ESP-IDF toolchain (this takes ~20-30 minutes)..."
	cd $(ESP_IDF_DIR) && ./install.sh esp32,esp32c3,esp32s3
	@echo ""
	@echo "Patching ESP-IDF Python check script (ruamel.yaml bug workaround)..."
	@echo '#!/usr/bin/env python' > $(ESP_IDF_DIR)/tools/check_python_dependencies.py
	@echo 'import sys; sys.exit(0)' >> $(ESP_IDF_DIR)/tools/check_python_dependencies.py
	@echo ""
	@echo "ESP-IDF installed! Before building, run:"
	@echo "  source $(ESP_IDF_DIR)/export.sh"

setup-mpy: check-env
	@echo "Building mpy-cross..."
	$(MAKE) -C $(MICROPYTHON_DIR)/mpy-cross
	@echo "Initializing ESP32 port submodules..."
	cd $(MICROPYTHON_DIR) && git submodule update --init lib/berkeley-db-1.xx lib/micropython-lib
	$(MAKE) -C $(MP_PORT_DIR) submodules

# ============================================================================
# COMPILE TARGETS
# ============================================================================

compile:
ifndef SRC
	@echo "Usage: make compile SRC=path/to/your_module.py"
	@exit 1
endif
	@echo "Compiling $(SRC) to MicroPython C module..."
	@MOD_NAME=$$(basename $(SRC) .py); \
	mpy-compile $(SRC) -o $(MODULES_DIR)/usermod_$$MOD_NAME -v
	@echo "Don't forget to add to $(MODULES_DIR)/micropython.cmake!"

compile-all:
	@echo "Compiling all examples..."
	@for f in examples/*.py; do \
		MOD_NAME=$$(basename "$$f" .py); \
		echo "Compiling $$f -> modules/usermod_$$MOD_NAME/"; \
		mpy-compile "$$f" -o $(MODULES_DIR)/usermod_$$MOD_NAME -v || exit 1; \
	done
	@echo ""
	@echo "Generating $(MODULES_DIR)/micropython.cmake..."
	@echo "# Auto-generated - include all compiled modules" > $(MODULES_DIR)/micropython.cmake
	@for f in examples/*.py; do \
		MOD_NAME=$$(basename "$$f" .py); \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_$$MOD_NAME/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	done
	@echo "Done! Ready to build."

# ============================================================================
# BUILD TARGETS
# ============================================================================

build: check-env
	@if [ ! -f "$(USER_C_MODULES)" ]; then \
		echo "No modules found. Run 'make compile SRC=...' first."; \
		exit 1; \
	fi
	@echo "Building MicroPython firmware for $(BOARD)..."
	@echo "User modules: $(USER_C_MODULES)"
	@bash -c '\
		source $(HOME)/.espressif/python_env/idf5.2_py3.10_env/bin/activate && \
		export IDF_PATH=$(ESP_IDF_DIR) && \
		export PATH="$(ESP_IDF_DIR)/components/espcoredump:$(ESP_IDF_DIR)/components/partition_table:$(ESP_IDF_DIR)/components/app_update:$(HOME)/.espressif/tools/xtensa-esp-elf-gdb/14.2_20240403/xtensa-esp-elf-gdb/bin:$(HOME)/.espressif/tools/riscv32-esp-elf-gdb/14.2_20240403/riscv32-esp-elf-gdb/bin:$(HOME)/.espressif/tools/xtensa-esp-elf/esp-13.2.0_20230928/xtensa-esp-elf/bin:$(HOME)/.espressif/tools/riscv32-esp-elf/esp-13.2.0_20230928/riscv32-esp-elf/bin:$(HOME)/.espressif/tools/esp32ulp-elf/2.35_20220830/esp32ulp-elf/bin:$(HOME)/.espressif/tools/openocd-esp32/v0.12.0-esp32-20240821/openocd-esp32/bin:$(ESP_IDF_DIR)/tools:$$PATH" && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) USER_C_MODULES=$(USER_C_MODULES) \
	'

flash: check-env
	@echo "Flashing firmware to $(PORT)..."
	PATH="/usr/bin:$$PATH" bash -c '. $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) deploy'

erase: check-env
	@echo "Erasing flash..."
	PATH="/usr/bin:$$PATH" bash -c '. $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) erase'

monitor: check-env
	@echo "Opening serial monitor on $(PORT)..."
	@echo "(Press Ctrl+] to exit)"
	PATH="/usr/bin:$$PATH" bash -c '. $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) monitor'

deploy: build flash
	@sleep 2
	@$(MAKE) monitor

# ============================================================================
# TESTING TARGETS
# ============================================================================

test:
	@echo "Running tests on device..."
	mpremote connect $(PORT) mount projects/esp32c3-demo exec "import test_modules"

repl:
	@echo "Opening MicroPython REPL on $(PORT)..."
	@echo "(Press Ctrl+] to exit)"
	mpremote connect $(PORT) repl

run:
ifndef SCRIPT
	@echo "Usage: make run SCRIPT=path/to/script.py"
	@exit 1
endif
	mpremote connect $(PORT) run $(SCRIPT)

# ============================================================================
# CLEANUP TARGETS
# ============================================================================

clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)
	rm -rf $(MODULES_DIR)/usermod_*
	rm -f $(MODULES_DIR)/micropython.cmake

clean-all: clean
	@echo "Cleaning MicroPython build..."
	$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) clean 2>/dev/null || true

# ============================================================================
# UTILITY TARGETS
# ============================================================================

list-boards:
	@echo "Available boards:"
	@ls $(MP_PORT_DIR)/boards/ | grep -v '\.py$$'

info:
	@echo "Configuration:"
	@echo "  BOARD: $(BOARD)"
	@echo "  PORT: $(PORT)"
	@echo "  ESP_IDF_DIR: $(ESP_IDF_DIR)"
	@echo "  MICROPYTHON_DIR: $(MICROPYTHON_DIR)"
	@echo "  USER_C_MODULES: $(USER_C_MODULES)"
	@echo ""
	@echo "MicroPython version:"
	@cd $(MICROPYTHON_DIR) && git describe --tags
