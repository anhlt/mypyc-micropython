# mypyc-micropython Build System
# ================================
# Compiles typed Python to MicroPython native C modules and builds firmware

# Configuration
BOARD ?= ESP32_GENERIC
PORT ?= /dev/ttyACM0
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
        test test-device test-device-only run-device-tests \
        test-factorial test-point test-counter test-sensor test-list test-dict test-all-modules \
        repl compile-all check-env

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
	@echo "  make test           - Run Python tests locally (pytest)"
	@echo "  make test-device    - Full cycle: compile + build + flash + test"
	@echo "  make test-device-only - Run device tests only (requires firmware flashed)"
	@echo "  make test-all-modules - Quick test all modules on device"
	@echo "  make test-factorial - Test factorial module"
	@echo "  make test-point     - Test point module (classes)"
	@echo "  make test-counter   - Test counter module"
	@echo "  make test-sensor    - Test sensor module"
	@echo "  make test-list      - Test list_operations module"
	@echo "  make test-dict      - Test dict_operations module"
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
	@echo "Installing ESP-IDF v5.4.2..."
	@mkdir -p $(HOME)/esp
	@if [ ! -d "$(ESP_IDF_DIR)" ]; then \
		git clone -b v5.4.2 --recursive https://github.com/espressif/esp-idf.git $(ESP_IDF_DIR); \
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
	@echo "Cleaning old usermod directories..."
	@rm -rf $(MODULES_DIR)/usermod_*
	@rm -f $(MODULES_DIR)/micropython.cmake
	@echo "Compiling all examples in parallel..."
	@printf '%s\n' examples/*.py | xargs -P $$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4) -n1 sh -c '\
		MOD_NAME=$$(basename "$$1" .py); \
		echo "Compiling $$1 -> modules/usermod_$$MOD_NAME/"; \
		mpy-compile "$$1" -o modules/usermod_$$MOD_NAME \
	' _
	@for d in examples/*/; do \
		if [ -f "$${d}__init__.py" ]; then \
			PKG_NAME=$$(basename "$$d"); \
			echo "Compiling package $$d -> modules/usermod_$$PKG_NAME/"; \
			mpy-compile "$$d" -o $(MODULES_DIR)/usermod_$$PKG_NAME || exit 1; \
		fi; \
	done
	@echo ""
	@echo "Generating $(MODULES_DIR)/micropython.cmake..."
	@echo "# Auto-generated - include all compiled modules" > $(MODULES_DIR)/micropython.cmake
	@for f in examples/*.py; do \
		MOD_NAME=$$(basename "$$f" .py); \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_$$MOD_NAME/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	done
	@for d in examples/*/; do \
		if [ -f "$${d}__init__.py" ]; then \
			PKG_NAME=$$(basename "$$d"); \
			echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_$$PKG_NAME/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
		fi; \
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
		source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) USER_C_MODULES=$(USER_C_MODULES) \
	'

flash: check-env
	@echo "Flashing firmware to $(PORT)..."
	@bash -c 'source $(ESP_IDF_DIR)/export.sh 2>/dev/null && \
		cd $(MP_PORT_DIR) && \
		idf.py -D MICROPY_BOARD=$(BOARD) \
			-D MICROPY_BOARD_DIR="$$(pwd)/boards/$(BOARD)" \
			-B build-$(BOARD) \
			-p $(PORT) flash'

erase: check-env
	@echo "Erasing flash..."
	@bash -c 'source $(ESP_IDF_DIR)/export.sh 2>/dev/null && \
		cd $(MP_PORT_DIR) && \
		idf.py -D MICROPY_BOARD=$(BOARD) \
			-D MICROPY_BOARD_DIR="$$(pwd)/boards/$(BOARD)" \
			-B build-$(BOARD) \
			-p $(PORT) erase_flash'

monitor: check-env
	@echo "Opening serial monitor on $(PORT)..."
	@echo "(Press Ctrl+] to exit)"
	@bash -c 'source $(ESP_IDF_DIR)/export.sh 2>/dev/null && \
		cd $(MP_PORT_DIR) && \
		idf.py -D MICROPY_BOARD=$(BOARD) \
			-D MICROPY_BOARD_DIR="$$(pwd)/boards/$(BOARD)" \
			-B build-$(BOARD) \
			-p $(PORT) monitor'

deploy: build flash
	@sleep 2
	@$(MAKE) monitor

# ============================================================================
# TESTING TARGETS
# ============================================================================

test:
	@echo "Running Python tests locally..."
	pytest -x

test-device: compile-all build flash run-device-tests
	@echo "Device testing complete!"

test-device-only:
	@echo "Running device tests on $(PORT)..."
	mpremote connect $(PORT) run run_device_tests.py

run-device-tests:
	@echo "Running device tests on $(PORT)..."
	mpremote connect $(PORT) run run_device_tests.py

benchmark:
	@echo "Running benchmarks: Native C vs Vanilla MicroPython on $(PORT)..."
	mpremote connect $(PORT) run run_benchmarks.py

test-factorial:
	@echo "Testing factorial module on device..."
	@mpremote connect $(PORT) exec "import factorial; print('factorial(5):', factorial.factorial(5)); print('fib(10):', factorial.fib(10))"

test-point:
	@echo "Testing point module on device..."
	@mpremote connect $(PORT) exec "import point; p = point.Point(3, 4); print(p); print('distance_squared:', p.distance_squared())"

test-counter:
	@echo "Testing counter module on device..."
	@mpremote connect $(PORT) exec "import counter; c = counter.Counter(10, 2); print(c); c.increment(); print('after inc:', c.get())"

test-sensor:
	@echo "Testing sensor module on device..."
	@mpremote connect $(PORT) exec "import sensor; r = sensor.SensorReading(1, 25.5, 60.0); print(r); b = sensor.SensorBuffer(); b.add_reading(25.0, 55.0); print('avg temp:', b.avg_temperature())"

test-list:
	@echo "Testing list_operations module on device..."
	@mpremote connect $(PORT) exec "import list_operations; print('sum_list:', list_operations.sum_list([1, 2, 3, 4, 5])); print('build_squares:', list_operations.build_squares(5))"

test-dict:
	@echo "Testing dict_operations module on device..."
	@python3 run_device_tests.py --port $(PORT)

test-all-modules: test-factorial test-point test-counter test-sensor test-list
	@echo "All module tests complete!"

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
	rm -rf $(MP_PORT_DIR)/build-*

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
