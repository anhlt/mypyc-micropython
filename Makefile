# mypyc-micropython Build System
# ================================
# Compiles typed Python to MicroPython native C modules and builds firmware

# BOARD is REQUIRED - no default value
# Must specify: make <target> BOARD=ESP32_GENERIC_C6 or BOARD=ESP32_GENERIC_P4
PORT ?= /dev/ttyACM0
BAUD ?= 460800
LVGL ?= 1

# Board profile and variant auto-detection
# Override with: make build BOARD_PROFILE=waveshare-c6 BOARD_VARIANT=C6_WIFI
ifeq ($(BOARD),ESP32_GENERIC_P4)
BOARD_PROFILE ?= guition-p4
BOARD_VARIANT ?= C6_WIFI
else ifeq ($(BOARD),ESP32_GENERIC_C6)
BOARD_PROFILE ?= waveshare-c6
BOARD_VARIANT ?=
else
BOARD_PROFILE ?= waveshare-c6
BOARD_VARIANT ?=
endif

# Paths
ROOT_DIR := $(shell pwd)
MICROPYTHON_DIR := $(ROOT_DIR)/deps/micropython
ESP_IDF_DIR ?= $(HOME)/esp/esp-idf
MODULES_DIR := $(ROOT_DIR)/modules
BUILD_DIR := $(ROOT_DIR)/build

# LVGL paths
LVGL_STUB_DIR := $(ROOT_DIR)/src/mypyc_micropython/c_bindings/libraries/lvgl/stubs
LVGL_CONFIG_DIR := $(ROOT_DIR)/src/mypyc_micropython/c_bindings/libraries/lvgl/config
# (removed LVGL_DRIVER_DIR - board profiles now required)
LVGL_MODULE_DIR := $(MODULES_DIR)/usermod_lvgl

# Board profile paths (display/touch drivers)
BOARD_PROFILES_DIR := $(ROOT_DIR)/configs/boards
BOARD_PROFILE_DIR := $(BOARD_PROFILES_DIR)/$(BOARD_PROFILE)

# External modules (first-class application modules)
EXTMOD_DIR := $(ROOT_DIR)/extmod

# MicroPython port
MP_PORT_DIR := $(MICROPYTHON_DIR)/ports/esp32
BOARD_DIR := $(MP_PORT_DIR)/boards/$(BOARD)

# Build variant args (passed to MicroPython Makefile when BOARD_VARIANT is set)
ifneq ($(BOARD_VARIANT),)
VARIANT_ARG := BOARD_VARIANT=$(BOARD_VARIANT)
MP_BUILD_DIR := build-$(BOARD)-$(BOARD_VARIANT)
else
VARIANT_ARG :=
MP_BUILD_DIR := build-$(BOARD)
endif

# User modules cmake file
USER_C_MODULES := $(MODULES_DIR)/micropython.cmake

# Auto-detect LVGL: set LVGL=1 if usermod_lvgl exists
HAS_LVGL := $(shell [ -d "$(LVGL_MODULE_DIR)" ] && echo 1 || echo 0)
ifeq ($(HAS_LVGL),1)
LVGL := 1
endif

.PHONY: help setup setup-idf setup-mpy compile build flash monitor clean clean-all \
        test test-device run-device-tests benchmark compile-all check-env check-board \
        test-lvgl run-lvgl-tests run-lvgl-mvu-tests run-lvgl-tests-all \
        erase run info repl run-nav-tests run-screen-navigation-tests

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
	@echo "DEVELOPMENT (BOARD= required):"
	@echo "  make compile-all BOARD=ESP32_GENERIC_P4"
	@echo "                      - Compile all examples + LVGL for specified board"
	@echo "  make compile SRC=examples/factorial.py"
	@echo "                      - Compile single Python file to C module"
	@echo ""
	@echo "BUILD & FLASH:"
	@echo "  make build          - Build firmware (auto-detects LVGL)"
	@echo "  make flash          - Flash firmware to device"
	@echo "  make monitor        - Open serial monitor"
	@echo "  make deploy         - Build + Flash + Monitor (one command)"
	@echo ""
	@echo "  LVGL is auto-detected. To force LVGL build: make build LVGL=1"
	@echo "  LVGL uses 8MiB partition table (4.5MB app) for display support."
	@echo ""
	@echo "TESTING:"
	@echo "  make test           - Run Python tests locally (pytest)"
	@echo "  make test-device    - Full cycle: compile + build + flash + test"
	@echo "  make run-device-tests - Run device tests on flashed firmware"
	@echo "  make run-lvgl-tests - Run LVGL test suite on device"
	@echo "  make run-lvgl-mvu-tests - Run LVGL MVU-only test suite on device"
	@echo "  make run-lvgl-tests-all - Run all LVGL suites on device"
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
	@echo "  BOARD_VARIANT=$(BOARD_VARIANT)"
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

check-board:
	@if [ -z "$(BOARD)" ]; then \
		echo "ERROR: BOARD parameter is required"; \
		echo ""; \
		echo "Usage: make <target> BOARD=<board_type>"; \
		echo ""; \
		echo "Available boards:"; \
		echo "  ESP32_GENERIC_C6  - Waveshare ESP32-C6 (172x320 ST7789 SPI)"; \
		echo "  ESP32_GENERIC_P4  - Guition ESP32-P4 (480x800 ST7701 MIPI-DSI)"; \
		echo ""; \
		echo "Example: make compile-all BOARD=ESP32_GENERIC_P4"; \
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
	@echo "Installing ESP-IDF toolchain for ESP32-C3, ESP32-C6 and ESP32-P4 (~20-30 minutes)..."
	cd $(ESP_IDF_DIR) && ./install.sh esp32c3,esp32c6,esp32p4
	@echo ""
	@echo "ESP-IDF installed! Before building, run:"

setup-mpy: check-env
	@echo "Initializing MicroPython submodule..."
	cd $(MICROPYTHON_DIR) && git submodule update --init --recursive
	@echo "Building mpy-cross..."
	$(MAKE) -C $(MICROPYTHON_DIR)/mpy-cross
	@echo "Initializing ESP32 port submodules..."
	$(MAKE) -C $(MP_PORT_DIR) submodules
	@echo "MicroPython setup complete."

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

compile-all: check-board
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
	@if [ "$(LVGL)" = "1" ]; then \
		echo "Compiling extmod/lvui package..."; \
		if [ -f "$(EXTMOD_DIR)/lvui/__init__.py" ]; then \
			echo "Compiling package $(EXTMOD_DIR)/lvui/ -> $(MODULES_DIR)/usermod_lvui/"; \
			mpy-compile "$(EXTMOD_DIR)/lvui/" -o "$(MODULES_DIR)/usermod_lvui" || exit 1; \
		fi; \
		echo ""; \
		echo "Compiling extmod/lvgl_mvu package..."; \
		if [ -f "$(EXTMOD_DIR)/lvgl_mvu/__init__.py" ]; then \
			echo "Compiling package $(EXTMOD_DIR)/lvgl_mvu/ -> $(MODULES_DIR)/usermod_lvgl_mvu/"; \
			mpy-compile "$(EXTMOD_DIR)/lvgl_mvu/" -o "$(MODULES_DIR)/usermod_lvgl_mvu" || exit 1; \
		fi; \
	else \
		echo "Skipping LVGL packages (LVGL=0)"; \
	fi
	@echo ""
	@if [ "$(LVGL)" = "1" ]; then \
		echo "Compiling LVGL C bindings..."; \
		$(MAKE) compile-lvgl-only; \
	else \
		echo "Skipping LVGL C bindings (LVGL=0)"; \
	fi
	@echo ""
	@echo "Generating $(MODULES_DIR)/micropython.cmake..."
	@echo "# Auto-generated - include all compiled modules" > $(MODULES_DIR)/micropython.cmake
	@if [ "$(LVGL)" = "1" ] && [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
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
	@if [ -d "$(MODULES_DIR)/usermod_lvui" ]; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvui/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@if [ -d "$(MODULES_DIR)/usermod_lvgl_mvu" ]; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl_mvu/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@echo "Done! Ready to build."

compile-lvgl-only:
	@mkdir -p $(LVGL_MODULE_DIR)
	@mpy-compile-c $(LVGL_STUB_DIR)/lvgl.pyi -o $(LVGL_MODULE_DIR) --public
	@echo "Using board profile: $(BOARD_PROFILE)"
	@if [ -f "$(BOARD_PROFILE_DIR)/display_driver.c" ]; then \
		cp $(BOARD_PROFILE_DIR)/display_driver.c $(LVGL_MODULE_DIR)/; \
		cp $(BOARD_PROFILE_DIR)/display_driver.h $(LVGL_MODULE_DIR)/; \
	else \
		echo "ERROR: No display_driver.c found in $(BOARD_PROFILE_DIR)"; \
		echo "Available board profiles: waveshare-c6, guition-p4"; \
		exit 1; \
	fi
	@if [ -d "$(BOARD_PROFILE_DIR)/st7701" ]; then \
		mkdir -p $(LVGL_MODULE_DIR)/st7701; \
		cp $(BOARD_PROFILE_DIR)/st7701/*.c $(LVGL_MODULE_DIR)/st7701/; \
		cp $(BOARD_PROFILE_DIR)/st7701/*.h $(LVGL_MODULE_DIR)/st7701/; \
	fi
	@if [ -f "$(BOARD_PROFILE_DIR)/touch_driver.c" ]; then \
		cp $(BOARD_PROFILE_DIR)/touch_driver.c $(LVGL_MODULE_DIR)/; \
		cp $(BOARD_PROFILE_DIR)/touch_driver.h $(LVGL_MODULE_DIR)/; \
	fi
	@cp $(LVGL_CONFIG_DIR)/lv_conf.h $(LVGL_MODULE_DIR)/
	@cp $(LVGL_CONFIG_DIR)/micropython.cmake $(LVGL_MODULE_DIR)/
	@python3 scripts/patch_lvgl_c.py $(LVGL_MODULE_DIR)/lvgl.c

# ============================================================================
# BUILD TARGETS
# ============================================================================

build: check-env check-board
	@if [ ! -f "$(USER_C_MODULES)" ]; then \
		echo "No modules found. Run 'make compile-all' first."; \
		exit 1; \
	fi
	@# Add LVGL to cmake if it exists but isn't listed
	@if [ -d "$(LVGL_MODULE_DIR)" ] && ! grep -q "usermod_lvgl/micropython.cmake" $(MODULES_DIR)/micropython.cmake 2>/dev/null; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@# Add lvgl_screens to cmake if it exists but isn't listed
	@if [ -d "$(MODULES_DIR)/usermod_lvgl_screens" ] && ! grep -q "usermod_lvgl_screens" $(MODULES_DIR)/micropython.cmake 2>/dev/null; then \
		echo "include(\$${CMAKE_CURRENT_LIST_DIR}/usermod_lvgl_screens/micropython.cmake)" >> $(MODULES_DIR)/micropython.cmake; \
	fi
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Building MicroPython + LVGL firmware for $(BOARD)..."; \
		echo "Using 8MiB flash + LVGL partition table (4.5MB app)"; \
		cp $(ROOT_DIR)/configs/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiB.csv; \
		cp $(ROOT_DIR)/configs/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiBplus.csv; \
		if [ -f "$(BOARD_PROFILE_DIR)/sdkconfig.board" ]; then \
			echo "Using board-specific sdkconfig: $(BOARD_PROFILE_DIR)/sdkconfig.board"; \
			cp $(BOARD_PROFILE_DIR)/sdkconfig.board $(BOARD_DIR)/sdkconfig.board; \
		else \
			cp $(ROOT_DIR)/configs/sdkconfig.lvgl $(BOARD_DIR)/sdkconfig.board; \
		fi; \
		cp $(BOARD_DIR)/mpconfigboard.cmake $(BOARD_DIR)/mpconfigboard.cmake.bak; \
		echo '' >> $(BOARD_DIR)/mpconfigboard.cmake; \
		echo 'list(APPEND SDKCONFIG_DEFAULTS boards/$(BOARD)/sdkconfig.board)' >> $(BOARD_DIR)/mpconfigboard.cmake; \
		rm -f $(MP_PORT_DIR)/$(MP_BUILD_DIR)/sdkconfig; \
	else \
		echo "Building MicroPython firmware for $(BOARD)..."; \
	fi
	@echo "User modules: $(USER_C_MODULES)"
	@bash -c '\
		source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) $(VARIANT_ARG) USER_C_MODULES=$(USER_C_MODULES) \
	'
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Restoring original files..."; \
		cp $(ROOT_DIR)/configs/partitions-default.csv $(MP_PORT_DIR)/partitions-4MiB.csv; \
		cd $(MP_PORT_DIR) && git checkout partitions-4MiBplus.csv 2>/dev/null || true; \
		if [ -f "$(BOARD_DIR)/mpconfigboard.cmake.bak" ]; then \
			mv $(BOARD_DIR)/mpconfigboard.cmake.bak $(BOARD_DIR)/mpconfigboard.cmake; \
		fi; \
		rm -f $(BOARD_DIR)/sdkconfig.board; \
	fi

flash: check-env check-board
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Flashing LVGL firmware to $(PORT)..."; \
		cp $(ROOT_DIR)/configs/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiB.csv; \
		cp $(ROOT_DIR)/configs/partitions-lvgl.csv $(MP_PORT_DIR)/partitions-4MiBplus.csv; \
		if [ -f "$(BOARD_PROFILE_DIR)/sdkconfig.board" ]; then \
			echo "Using board-specific sdkconfig: $(BOARD_PROFILE_DIR)/sdkconfig.board"; \
			cp $(BOARD_PROFILE_DIR)/sdkconfig.board $(BOARD_DIR)/sdkconfig.board; \
		else \
			cp $(ROOT_DIR)/configs/sdkconfig.lvgl $(BOARD_DIR)/sdkconfig.board; \
		fi; \
		cp $(BOARD_DIR)/mpconfigboard.cmake $(BOARD_DIR)/mpconfigboard.cmake.bak; \
		echo '' >> $(BOARD_DIR)/mpconfigboard.cmake; \
		echo 'list(APPEND SDKCONFIG_DEFAULTS boards/$(BOARD)/sdkconfig.board)' >> $(BOARD_DIR)/mpconfigboard.cmake; \
	else \
		echo "Flashing firmware to $(PORT)..."; \
	fi
	@bash -c 'source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) $(VARIANT_ARG) PORT=$(PORT) deploy'
	@if [ "$(LVGL)" = "1" ] || [ -d "$(LVGL_MODULE_DIR)" ]; then \
		echo "Restoring original files..."; \
		cp $(ROOT_DIR)/configs/partitions-default.csv $(MP_PORT_DIR)/partitions-4MiB.csv; \
		cd $(MP_PORT_DIR) && git checkout partitions-4MiBplus.csv 2>/dev/null || true; \
		if [ -f "$(BOARD_DIR)/mpconfigboard.cmake.bak" ]; then \
			mv $(BOARD_DIR)/mpconfigboard.cmake.bak $(BOARD_DIR)/mpconfigboard.cmake; \
		fi; \
		rm -f $(BOARD_DIR)/sdkconfig.board; \
	fi

erase: check-env
	@echo "Erasing flash..."
	@bash -c 'source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) $(VARIANT_ARG) PORT=$(PORT) erase'

monitor: check-env
	@echo "Opening serial monitor on $(PORT)..."
	@echo "(Press Ctrl+] to exit)"
	@bash -c 'source $(ESP_IDF_DIR)/export.sh && \
		$(MAKE) -C $(MP_PORT_DIR) BOARD=$(BOARD) $(VARIANT_ARG) PORT=$(PORT) monitor'

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
	mpremote connect $(PORT) run tests/device/run_device_tests.py

benchmark:
	@echo "Running benchmarks: Native C vs Vanilla MicroPython..."
	mpremote connect $(PORT) run tests/device/run_benchmarks.py

test-lvgl:
	@echo "Testing LVGL on device..."
	@mpremote connect $(PORT) exec "import lvgl, time; lvgl.init_display(); scr = lvgl.lv_screen_active(); lvgl.lv_obj_clean(scr); label = lvgl.lv_label_create(scr); lvgl.lv_obj_center(label); lvgl.lv_label_set_text(label, 'LVGL Test OK'); [lvgl.timer_handler() or time.sleep_ms(10) for _ in range(100)]; print('LVGL test passed')"

run-lvgl-tests:
	@echo "Running LVGL test suite on $(PORT)..."
	mpremote connect $(PORT) run tests/device/run_lvgl_tests.py

run-lvgl-mvu-tests:
	@echo "Running LVGL MVU-only test suite on $(PORT)..."
	mpremote connect $(PORT) run tests/device/run_lvgl_mvu_tests.py

run-lvgl-tests-all: run-lvgl-tests run-lvgl-mvu-tests
	@echo "LVGL full test pass complete"

run-nav-tests:
	@echo "Running navigation tests on $(PORT)..."
	mpremote connect $(PORT) run tests/device/run_nav_tests.py

run-screen-navigation-tests:
	@echo "Running screen navigation tests on $(PORT)..."
	mpremote connect $(PORT) run tests/device/run_screen_navigation_tests.py

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
info:
	@echo "Configuration:"
	@echo "  BOARD: $(BOARD)"
	@echo "  BOARD_VARIANT: $(BOARD_VARIANT)"
	@echo "  BOARD_PROFILE: $(BOARD_PROFILE)"
	@echo "  PORT: $(PORT)"
	@echo "  LVGL: $(LVGL) (auto-detected: $(HAS_LVGL))"
	@echo "  ESP_IDF_DIR: $(ESP_IDF_DIR)"
	@echo "  MICROPYTHON_DIR: $(MICROPYTHON_DIR)"
	@echo "  USER_C_MODULES: $(USER_C_MODULES)"
	@echo "  BOARD_PROFILE_DIR: $(BOARD_PROFILE_DIR)"
	@echo ""
	@echo "MicroPython version:"
	@cd $(MICROPYTHON_DIR) && git describe --tags
