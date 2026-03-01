# mypyc-micropython Build System
# ================================
# Compiles typed Python to MicroPython native C modules and builds firmware

# Configuration
BOARD ?= ESP32_GENERIC
PORT ?= /dev/ttyACM0
BAUD ?= 460800
LVGL ?= 0

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

# Auto-detect LVGL: set LVGL=1 if usermod_lvgl exists
HAS_LVGL := $(shell [ -d "$(LVGL_MODULE_DIR)" ] && echo 1 || echo 0)
ifeq ($(HAS_LVGL),1)
LVGL := 1
endif

.PHONY: help setup setup-idf setup-mpy compile build flash monitor clean clean-all \
        test test-device run-device-tests benchmark compile-all check-env \
        compile-lvgl test-lvgl run-lvgl-tests erase run list-boards info repl

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
	@echo "  make compile-all    - Compile all examples to C modules"
	@echo "  make compile-lvgl   - Generate LVGL C bindings from .pyi stub"
	@echo ""
	@echo "BUILD & FLASH:"
	@echo "  make build          - Build firmware (auto-detects LVGL)"
	@echo "  make flash          - Flash firmware to device"
	@echo "  make monitor        - Open serial monitor"
	@echo "  make deploy         - Build + Flash + Monitor (one command)"
	@echo ""
	@echo "  LVGL is auto-detected. To force LVGL build: make build LVGL=1"
	@echo "  LVGL uses larger partition table (2.56MB app) for display support."
	@echo ""
	@echo "TESTING:"
	@echo "  make test           - Run Python tests locally (pytest)"
	@echo "  make test-device    - Full cycle: compile + build + flash + test"
	@echo "  make run-device-tests - Run device tests on flashed firmware"
	@echo "  make run-lvgl-tests - Run LVGL test suite on device"
	@echo "  make test-navigation - Run ScreenManager navigation test"
	@echo "  make test-lvgl      - Quick LVGL display test"
	@echo "  make benchmark      - Run native vs vanilla performance tests"
	@echo "  make repl           - Open MicroPython REPL"
	@echo ""
	@echo "CLEANUP:"
	@echo "  make clean          - Clean build artifacts"
	@echo "  make clean-all      - Clean everything including ESP-IDF build"
	@echo ""
	@echo "CONFIGURATION:"
	@echo "  BOARD=$(BOARD)"
	@echo "  PORT=$(PORT)"
	@echo "  LVGL=$(LVGL) (auto-detected: $(HAS_LVGL))"
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
		f="$$1"; \
		MOD_NAME=$$(basename "$$f" .py); \
		case "$$MOD_NAME" in \
			usermod_*|lvgl_app) exit 0 ;; \
		esac; \
		echo "Compiling $$f -> $(MODULES_DIR)/usermod_$$MOD_NAME/"; \
		mpy-compile "$$f" -o "$(MODULES_DIR)/usermod_$$MOD_NAME" \
	' _
	@for d in examples/*/; do \
		if [ -f "$${d}__init__.py" ]; then \
			PKG_NAME=$$(basename "$$d"); \
			echo "Compiling package $$d -> $(MODULES_DIR)/usermod_$$PKG_NAME/"; \
			mpy-compile "$$d" -o "$(MODULES_DIR)/usermod_$$PKG_NAME" || exit 1; \
		fi; \
	done
	@echo ""
	@echo "Generating $(MODULES_DIR)/micropython.cmake..."
	@echo "# Auto-generated - include all compiled modules" > $(MODULES_DIR)/micropython.cmake
	@for f in examples/*.py; do \
		MOD_NAME=$$(basename "$$f" .py); \
		case "$$MOD_NAME" in \
			usermod_*|lvgl_app) continue ;; \
		esac; \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_$$MOD_NAME/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	done
	@for d in examples/*/; do \
		if [ -f "$${d}__init__.py" ]; then \
			PKG_NAME=$$(basename "$$d"); \
			echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_$$PKG_NAME/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
		fi; \
	done
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
	@echo ""
	@echo "Adding LVGL to micropython.cmake..."
	@if [ -f "$(MODULES_DIR)/micropython.cmake" ]; then \
		if ! grep -q "usermod_lvgl" $(MODULES_DIR)/micropython.cmake 2>/dev/null; then \
			echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
		fi; \
	else \
		echo "# Auto-generated" > $(MODULES_DIR)/micropython.cmake; \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi

# ============================================================================
# BUILD TARGETS
# ============================================================================

build: check-env
	@if [ ! -f "$(USER_C_MODULES)" ]; then \
		echo "No modules found. Run 'make compile-all' first."; \
		exit 1; \
	fi
	@# Add LVGL to cmake if it exists but isn't listed
	@if [ -d "$(LVGL_MODULE_DIR)" ] && ! grep -q "usermod_lvgl" $(MODULES_DIR)/micropython.cmake 2>/dev/null; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@# Add lvgl_screens to cmake if it exists but isn't listed
	@if [ -d "$(MODULES_DIR)/usermod_lvgl_screens" ] && ! grep -q "usermod_lvgl_screens" $(MODULES_DIR)/micropython.cmake 2>/dev/null; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl_screens/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Building MicroPython + LVGL firmware for $(BOARD)..."; \
		echo "Using larger partition table (2.56MB app) for LVGL"; \
		cp $(ROOT_DIR)/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiB.csv; \
	else \
		echo "Building MicroPython firmware for $(BOARD)..."; \
	fi
	@echo "User modules: $(USER_C_MODULES)"
	@bash -c '\
		source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) USER_C_MODULES=$(USER_C_MODULES) \
	'
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Restoring original partition table..."; \
		cd $(MICROPYTHON_DIR) && git checkout ports/esp32/partitions-4MiB.csv; \
	fi

flash: check-env
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Flashing LVGL firmware to $(PORT)..."; \
		cp $(ROOT_DIR)/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiB.csv; \
	else \
		echo "Flashing firmware to $(PORT)..."; \
	fi
	@bash -c 'source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) deploy'
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Restoring original partition table..."; \
		cd $(MICROPYTHON_DIR) && git checkout ports/esp32/partitions-4MiB.csv; \
	fi

erase: check-env
	@echo "Erasing flash..."
	@bash -c 'source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) erase'

monitor: check-env
	@echo "Opening serial monitor on $(PORT)..."
	@echo "(Press Ctrl+] to exit)"
	@bash -c 'source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) PORT=$(PORT) monitor'

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

run-device-tests:
	@echo "Running device tests on $(PORT)..."
	mpremote connect $(PORT) run run_device_tests.py

benchmark:
	@echo "Running benchmarks: Native C vs Vanilla MicroPython..."
	@python3 run_benchmarks.py --port $(PORT)

test-lvgl:
	@echo "Testing LVGL on device..."
	@mpremote connect $(PORT) exec "import lvgl, time; lvgl.init_display(); scr = lvgl.lv_screen_active(); lvgl.lv_obj_clean(scr); label = lvgl.lv_label_create(scr); lvgl.lv_obj_center(label); lvgl.lv_label_set_text(label, 'LVGL Test OK'); [lvgl.timer_handler() or time.sleep_ms(10) for _ in range(100)]; print('LVGL test passed')"

run-lvgl-tests:
	@echo "Running LVGL test suite on $(PORT)..."
	mpremote connect $(PORT) run run_lvgl_tests.py

run-nav-test:
	@echo "Running visual navigation test on $(PORT)..."
	mpremote connect $(PORT) run run_nav_test.py
test-navigation:
	@echo "Running ScreenManager navigation test on $(PORT)..."
	mpremote connect $(PORT) run test_screen_navigation.py

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
	@echo "  LVGL: $(LVGL) (auto-detected: $(HAS_LVGL))"
	@echo "  ESP_IDF_DIR: $(ESP_IDF_DIR)"
	@echo "  MICROPYTHON_DIR: $(MICROPYTHON_DIR)"
	@echo "  USER_C_MODULES: $(USER_C_MODULES)"
	@echo ""
	@echo "MicroPython version:"
	@cd $(MICROPYTHON_DIR) && git describe --tags
