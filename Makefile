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

# LVGL paths
LVGL_STUB_DIR := $(ROOT_DIR)/src/mypyc_micropython/c_bindings/stubs/lvgl
LVGL_MODULE_DIR := $(MODULES_DIR)/usermod_lvgl

# MicroPython port
MP_PORT_DIR := $(MICROPYTHON_DIR)/ports/esp32

# User modules cmake file
USER_C_MODULES := $(MODULES_DIR)/micropython.cmake

.PHONY: help setup setup-idf setup-mpy compile build flash monitor clean \
        test test-device test-device-only run-device-tests \
        test-factorial test-point test-counter test-sensor test-list test-dict test-all-modules \
        repl compile-all check-env compile-lvgl build-lvgl flash-lvgl deploy-lvgl test-lvgl

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
	@echo "  make compile-lvgl   - Generate LVGL C bindings from .pyi stub"
	@echo ""
	@echo "BUILD & FLASH:"
	@echo "  make build          - Build MicroPython firmware with modules"
	@echo "  make flash          - Flash firmware to device"
	@echo "  make monitor        - Open serial monitor"
	@echo "  make deploy         - Build + Flash + Monitor"
	@echo ""
	@echo "LVGL (display):"
	@echo "  make deploy-lvgl    - One command: compile + build + flash LVGL firmware"
	@echo "  make build-lvgl     - Build firmware with LVGL (larger partition)"
	@echo "  make flash-lvgl     - Flash LVGL firmware to device"
	@echo "  make test-lvgl      - Quick display test on device"
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
	@echo "Compiling all examples..."
	@for f in examples/*.py; do \
		MOD_NAME=$$(basename "$$f" .py); \
		if [ "$$MOD_NAME" = "lvgl_app" ]; then continue; fi; \
		echo "Compiling $$f -> modules/usermod_$$MOD_NAME/"; \
		mpy-compile "$$f" -o $(MODULES_DIR)/usermod_$$MOD_NAME -v || exit 1; \
	done
	@echo ""
	@echo "Generating $(MODULES_DIR)/micropython.cmake..."
	@echo "# Auto-generated - include all compiled modules" > $(MODULES_DIR)/micropython.cmake
	@for f in examples/*.py; do \
		MOD_NAME=$$(basename "$$f" .py); \
		if [ "$$MOD_NAME" = "lvgl_app" ]; then continue; fi; \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_$$MOD_NAME/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	done
	@if [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@echo "Done! Ready to build."

compile-lvgl:
	@echo "Compiling LVGL bindings from .pyi stub..."
	@mkdir -p $(LVGL_MODULE_DIR)
	mpy-compile-c $(LVGL_STUB_DIR)/lvgl.pyi -o $(LVGL_MODULE_DIR) --public -v
	@echo "Copying display driver, config, and cmake..."
	@cp $(LVGL_STUB_DIR)/st7789_driver.c $(LVGL_MODULE_DIR)/
	@cp $(LVGL_STUB_DIR)/st7789_driver.h $(LVGL_MODULE_DIR)/
	@cp $(LVGL_STUB_DIR)/lv_conf.h $(LVGL_MODULE_DIR)/
	@cp $(LVGL_STUB_DIR)/micropython.cmake $(LVGL_MODULE_DIR)/
	@echo "Patching lvgl.c with display driver entries..."
	@python3 scripts/patch_lvgl_c.py $(LVGL_MODULE_DIR)/lvgl.c
	@echo "LVGL module compiled successfully."


compile-lvgl-app: compile-lvgl
	@echo "Compiling lvgl_app.py with cross-module LVGL calls..."
	@python3 scripts/compile_lvgl_app.py examples/lvgl_app.py -o $(MODULES_DIR)/usermod_lvgl_app -v
	@echo "lvgl_app module compiled successfully."

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

build-lvgl: check-env compile-all compile-lvgl-app
	@echo "Adding LVGL to module list..."
	@if ! grep -q "usermod_lvgl" $(MODULES_DIR)/micropython.cmake 2>/dev/null; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@if ! grep -q "usermod_lvgl_app" $(MODULES_DIR)/micropython.cmake 2>/dev/null; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl_app/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@echo "Building MicroPython + LVGL firmware for $(BOARD)..."
	@echo "Using custom partition table (2.56MB app) for LVGL"
	@cp $(ROOT_DIR)/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiB.csv
	@bash -c '\
		source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) USER_C_MODULES=$(USER_C_MODULES) \
	'
	@echo "Restoring original partition table..."
	@cd $(MICROPYTHON_DIR) && git checkout ports/esp32/partitions-4MiB.csv

flash: check-env
	@echo "Flashing firmware to $(PORT)..."
	PATH="/usr/bin:$$PATH" bash -c '. $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) deploy'

flash-lvgl: check-env
	@echo "Flashing LVGL firmware to $(PORT)..."
	@cp $(ROOT_DIR)/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiB.csv
	PATH="/usr/bin:$$PATH" bash -c '. $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) deploy'
	@echo "Restoring original partition table..."
	@cd $(MICROPYTHON_DIR) && git checkout ports/esp32/partitions-4MiB.csv

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

deploy-lvgl: build-lvgl flash-lvgl
	@echo "LVGL firmware deployed successfully!"
	@echo "Test with: make test-lvgl PORT=$(PORT)"

# ============================================================================
# TESTING TARGETS
# ============================================================================

test:
	@echo "Running Python tests locally..."
	pytest -x

test-device: compile-all build flash run-device-tests
	@echo "Device testing complete!"

test-device-only:
	@echo "Running comprehensive device tests..."
	@python3 run_device_tests.py --port $(PORT)

run-device-tests:
	@echo "Running comprehensive device tests..."
	@python3 run_device_tests.py --port $(PORT)

benchmark:
	@echo "Running benchmarks: Native C vs Vanilla MicroPython..."
	@python3 run_benchmarks.py --port $(PORT)

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

test-lvgl:
	@echo "Testing LVGL on device..."
	@mpremote connect $(PORT) exec "import lvgl, time; lvgl.init_display(); scr = lvgl.lv_screen_active(); lvgl.lv_obj_clean(scr); label = lvgl.lv_label_create(scr); lvgl.lv_obj_center(label); lvgl.lv_label_set_text(label, 'LVGL Test OK'); [lvgl.timer_handler() or time.sleep_ms(10) for _ in range(100)]; print('LVGL test passed')"

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
