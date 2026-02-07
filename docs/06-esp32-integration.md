# ESP32 Module Integration

How to call ESP32 MicroPython modules (`machine`, `network`, `esp32`, etc.) from mypyc-micropython compiled code.

## Table of Contents

- [Overview](#overview)
- [Available ESP32 Modules](#available-esp32-modules)
- [Calling MicroPython Modules from C](#calling-micropython-modules-from-c)
- [Complete Examples](#complete-examples)
- [Module Registry Design](#module-registry-design)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)

## Overview

ESP32 MicroPython provides hardware access through Python modules like `machine.Pin`, `network.WLAN`, etc. When compiling Python to C with mypyc-micropython, we need to call these modules at runtime since they're part of the MicroPython firmware, not compiled into our C code.

### Two Approaches

| Approach | When to Use | Performance |
|----------|-------------|-------------|
| **Runtime Lookup** | General case, maximum compatibility | Slower (module lookup per call) |
| **Cached References** | Performance-critical code | Fast (one-time lookup) |

## Available ESP32 Modules

### machine Module

| Class/Function | Purpose |
|----------------|---------|
| `machine.Pin` | GPIO control |
| `machine.PWM` | PWM output |
| `machine.ADC` | Analog input |
| `machine.DAC` | Analog output |
| `machine.I2C` | I2C bus |
| `machine.SPI` | SPI bus |
| `machine.UART` | Serial communication |
| `machine.Timer` | Hardware timers |
| `machine.RTC` | Real-time clock |
| `machine.freq()` | CPU frequency |
| `machine.reset()` | Software reset |
| `machine.deepsleep()` | Deep sleep mode |

### network Module

| Class/Function | Purpose |
|----------------|---------|
| `network.WLAN` | WiFi control |
| `network.LAN` | Ethernet (if available) |

### esp32 Module

| Function | Purpose |
|----------|---------|
| `esp32.raw_temperature()` | Internal temperature sensor |
| `esp32.hall_sensor()` | Hall effect sensor |
| `esp32.idf_heap_info()` | Memory info |

### time Module

| Function | Purpose |
|----------|---------|
| `time.sleep(secs)` | Sleep (seconds) |
| `time.sleep_ms(ms)` | Sleep (milliseconds) |
| `time.sleep_us(us)` | Sleep (microseconds) |
| `time.ticks_ms()` | Millisecond counter |
| `time.ticks_us()` | Microsecond counter |
| `time.ticks_diff(t1, t2)` | Time difference |

## Calling MicroPython Modules from C

### Basic Pattern: Runtime Lookup

```c
#include "py/runtime.h"
#include "py/obj.h"

// Import a module at runtime
static mp_obj_t import_module(const char *name) {
    return mp_import_name(
        mp_obj_new_str(name, strlen(name)),  // module name
        mp_const_none,                        // globals (not needed)
        MP_OBJ_NEW_SMALL_INT(0)              // level (absolute import)
    );
}

// Get attribute from module/object
static mp_obj_t get_attr(mp_obj_t obj, const char *attr) {
    return mp_load_attr(obj, qstr_from_str(attr));
}

// Call function with arguments
static mp_obj_t call_func(mp_obj_t func, size_t n_args, const mp_obj_t *args) {
    return mp_call_function_n_kw(func, n_args, 0, args);
}
```

### Example: Blink LED

**Python (what we're compiling):**
```python
from machine import Pin
import time

def blink(pin_num: int, count: int, delay_ms: int) -> None:
    led = Pin(pin_num, Pin.OUT)
    for _ in range(count):
        led.value(1)
        time.sleep_ms(delay_ms)
        led.value(0)
        time.sleep_ms(delay_ms)
```

**Generated C:**
```c
#include "py/runtime.h"
#include "py/obj.h"

static mp_obj_t blink(mp_obj_t pin_num_obj, mp_obj_t count_obj, mp_obj_t delay_ms_obj) {
    mp_int_t pin_num = mp_obj_get_int(pin_num_obj);
    mp_int_t count = mp_obj_get_int(count_obj);
    mp_int_t delay_ms = mp_obj_get_int(delay_ms_obj);
    
    // Import modules
    mp_obj_t machine_mod = mp_import_name(
        MP_OBJ_NEW_QSTR(MP_QSTR_machine), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t time_mod = mp_import_name(
        MP_OBJ_NEW_QSTR(MP_QSTR_time), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    
    // Get Pin class and OUT constant
    mp_obj_t Pin_class = mp_load_attr(machine_mod, MP_QSTR_Pin);
    mp_obj_t Pin_OUT = mp_load_attr(Pin_class, MP_QSTR_OUT);
    
    // Create Pin instance: Pin(pin_num, Pin.OUT)
    mp_obj_t pin_args[] = {mp_obj_new_int(pin_num), Pin_OUT};
    mp_obj_t led = mp_call_function_n_kw(Pin_class, 2, 0, pin_args);
    
    // Get methods
    mp_obj_t led_value = mp_load_attr(led, MP_QSTR_value);
    mp_obj_t sleep_ms = mp_load_attr(time_mod, MP_QSTR_sleep_ms);
    
    // Blink loop
    for (mp_int_t i = 0; i < count; i++) {
        // led.value(1)
        mp_obj_t value_args_on[] = {led, mp_obj_new_int(1)};
        mp_call_method_n_kw(1, 0, value_args_on);
        
        // time.sleep_ms(delay_ms)
        mp_obj_t sleep_args[] = {mp_obj_new_int(delay_ms)};
        mp_call_function_n_kw(sleep_ms, 1, 0, sleep_args);
        
        // led.value(0)
        mp_obj_t value_args_off[] = {led, mp_obj_new_int(0)};
        mp_call_method_n_kw(1, 0, value_args_off);
        
        // time.sleep_ms(delay_ms)
        mp_call_function_n_kw(sleep_ms, 1, 0, sleep_args);
    }
    
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(blink_obj, blink);
```

### Cached References (Optimized)

For frequently called code, cache module/class references:

```c
// Cached references (initialized once)
static mp_obj_t cached_machine_mod = MP_OBJ_NULL;
static mp_obj_t cached_Pin_class = MP_OBJ_NULL;
static mp_obj_t cached_Pin_OUT = MP_OBJ_NULL;
static mp_obj_t cached_time_mod = MP_OBJ_NULL;
static mp_obj_t cached_sleep_ms = MP_OBJ_NULL;

// Initialize caches (call once at module load)
static void init_caches(void) {
    if (cached_machine_mod == MP_OBJ_NULL) {
        cached_machine_mod = mp_import_name(
            MP_OBJ_NEW_QSTR(MP_QSTR_machine), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        cached_Pin_class = mp_load_attr(cached_machine_mod, MP_QSTR_Pin);
        cached_Pin_OUT = mp_load_attr(cached_Pin_class, MP_QSTR_OUT);
        
        cached_time_mod = mp_import_name(
            MP_OBJ_NEW_QSTR(MP_QSTR_time), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        cached_sleep_ms = mp_load_attr(cached_time_mod, MP_QSTR_sleep_ms);
    }
}

// Optimized blink using caches
static mp_obj_t blink_fast(mp_obj_t pin_num_obj, mp_obj_t count_obj, mp_obj_t delay_ms_obj) {
    init_caches();
    
    mp_int_t pin_num = mp_obj_get_int(pin_num_obj);
    mp_int_t count = mp_obj_get_int(count_obj);
    mp_int_t delay_ms = mp_obj_get_int(delay_ms_obj);
    
    // Create Pin using cached class
    mp_obj_t pin_args[] = {mp_obj_new_int(pin_num), cached_Pin_OUT};
    mp_obj_t led = mp_call_function_n_kw(cached_Pin_class, 2, 0, pin_args);
    
    mp_obj_t delay_arg[] = {mp_obj_new_int(delay_ms)};
    
    for (mp_int_t i = 0; i < count; i++) {
        mp_obj_t on_args[] = {led, mp_obj_new_int(1)};
        mp_call_method_n_kw(1, 0, on_args);
        mp_call_function_n_kw(cached_sleep_ms, 1, 0, delay_arg);
        
        mp_obj_t off_args[] = {led, mp_obj_new_int(0)};
        mp_call_method_n_kw(1, 0, off_args);
        mp_call_function_n_kw(cached_sleep_ms, 1, 0, delay_arg);
    }
    
    return mp_const_none;
}
```

## Complete Examples

### Example 1: WiFi Connection

**Python:**
```python
import network
import time

def connect_wifi(ssid: str, password: str, timeout_ms: int = 10000) -> bool:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    
    start = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            return False
        time.sleep_ms(100)
    
    return True
```

**Generated C:**
```c
static mp_obj_t connect_wifi(size_t n_args, const mp_obj_t *args) {
    // Parse arguments
    const char *ssid = mp_obj_str_get_str(args[0]);
    const char *password = mp_obj_str_get_str(args[1]);
    mp_int_t timeout_ms = (n_args > 2) ? mp_obj_get_int(args[2]) : 10000;
    
    // Import network module
    mp_obj_t network_mod = mp_import_name(
        MP_OBJ_NEW_QSTR(MP_QSTR_network), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t time_mod = mp_import_name(
        MP_OBJ_NEW_QSTR(MP_QSTR_time), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    
    // Get WLAN class and STA_IF constant
    mp_obj_t WLAN_class = mp_load_attr(network_mod, MP_QSTR_WLAN);
    mp_obj_t STA_IF = mp_load_attr(network_mod, MP_QSTR_STA_IF);
    
    // wlan = network.WLAN(network.STA_IF)
    mp_obj_t wlan_args[] = {STA_IF};
    mp_obj_t wlan = mp_call_function_n_kw(WLAN_class, 1, 0, wlan_args);
    
    // wlan.active(True)
    mp_obj_t active_method = mp_load_attr(wlan, MP_QSTR_active);
    mp_obj_t active_args[] = {wlan, mp_const_true};
    mp_call_method_n_kw(1, 0, active_args);
    
    // wlan.connect(ssid, password)
    mp_obj_t connect_method = mp_load_attr(wlan, MP_QSTR_connect);
    mp_obj_t connect_args[] = {
        wlan,
        mp_obj_new_str(ssid, strlen(ssid)),
        mp_obj_new_str(password, strlen(password))
    };
    mp_call_method_n_kw(2, 0, connect_args);
    
    // Get time functions
    mp_obj_t ticks_ms = mp_load_attr(time_mod, MP_QSTR_ticks_ms);
    mp_obj_t ticks_diff = mp_load_attr(time_mod, MP_QSTR_ticks_diff);
    mp_obj_t sleep_ms = mp_load_attr(time_mod, MP_QSTR_sleep_ms);
    mp_obj_t isconnected = mp_load_attr(wlan, MP_QSTR_isconnected);
    
    // start = time.ticks_ms()
    mp_obj_t start = mp_call_function_n_kw(ticks_ms, 0, 0, NULL);
    
    // while not wlan.isconnected():
    while (true) {
        mp_obj_t connected_args[] = {wlan};
        mp_obj_t connected = mp_call_method_n_kw(0, 0, connected_args);
        if (mp_obj_is_true(connected)) {
            break;
        }
        
        // Check timeout
        mp_obj_t now = mp_call_function_n_kw(ticks_ms, 0, 0, NULL);
        mp_obj_t diff_args[] = {now, start};
        mp_obj_t elapsed = mp_call_function_n_kw(ticks_diff, 2, 0, diff_args);
        if (mp_obj_get_int(elapsed) > timeout_ms) {
            return mp_const_false;
        }
        
        // time.sleep_ms(100)
        mp_obj_t sleep_args[] = {mp_obj_new_int(100)};
        mp_call_function_n_kw(sleep_ms, 1, 0, sleep_args);
    }
    
    return mp_const_true;
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(connect_wifi_obj, 2, 3, connect_wifi);
```

### Example 2: ADC Reading

**Python:**
```python
from machine import ADC, Pin

def read_adc_average(pin_num: int, samples: int = 10) -> int:
    adc = ADC(Pin(pin_num))
    adc.atten(ADC.ATTN_11DB)  # Full range: 0-3.3V
    
    total = 0
    for _ in range(samples):
        total += adc.read()
    
    return total // samples
```

**Generated C:**
```c
static mp_obj_t read_adc_average(size_t n_args, const mp_obj_t *args) {
    mp_int_t pin_num = mp_obj_get_int(args[0]);
    mp_int_t samples = (n_args > 1) ? mp_obj_get_int(args[1]) : 10;
    
    // Import machine module
    mp_obj_t machine_mod = mp_import_name(
        MP_OBJ_NEW_QSTR(MP_QSTR_machine), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    
    // Get ADC and Pin classes
    mp_obj_t ADC_class = mp_load_attr(machine_mod, MP_QSTR_ADC);
    mp_obj_t Pin_class = mp_load_attr(machine_mod, MP_QSTR_Pin);
    
    // Create Pin: Pin(pin_num)
    mp_obj_t pin_args[] = {mp_obj_new_int(pin_num)};
    mp_obj_t pin = mp_call_function_n_kw(Pin_class, 1, 0, pin_args);
    
    // Create ADC: ADC(pin)
    mp_obj_t adc_args[] = {pin};
    mp_obj_t adc = mp_call_function_n_kw(ADC_class, 1, 0, adc_args);
    
    // adc.atten(ADC.ATTN_11DB)
    mp_obj_t ATTN_11DB = mp_load_attr(ADC_class, MP_QSTR_ATTN_11DB);
    mp_obj_t atten_args[] = {adc, ATTN_11DB};
    mp_call_method_n_kw(1, 0, atten_args);
    
    // Read samples
    mp_obj_t read_method = mp_load_attr(adc, MP_QSTR_read);
    mp_int_t total = 0;
    for (mp_int_t i = 0; i < samples; i++) {
        mp_obj_t read_args[] = {adc};
        mp_obj_t value = mp_call_method_n_kw(0, 0, read_args);
        total += mp_obj_get_int(value);
    }
    
    return mp_obj_new_int(total / samples);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(read_adc_average_obj, 1, 2, read_adc_average);
```

### Example 3: I2C Device Communication

**Python:**
```python
from machine import I2C, Pin

def i2c_scan(sda_pin: int, scl_pin: int) -> list[int]:
    i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
    return i2c.scan()

def i2c_read_register(sda_pin: int, scl_pin: int, addr: int, reg: int) -> int:
    i2c = I2C(0, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
    i2c.writeto(addr, bytes([reg]))
    data = i2c.readfrom(addr, 1)
    return data[0]
```

**Generated C (i2c_scan):**
```c
static mp_obj_t i2c_scan(mp_obj_t sda_pin_obj, mp_obj_t scl_pin_obj) {
    mp_int_t sda_pin = mp_obj_get_int(sda_pin_obj);
    mp_int_t scl_pin = mp_obj_get_int(scl_pin_obj);
    
    // Import machine
    mp_obj_t machine_mod = mp_import_name(
        MP_OBJ_NEW_QSTR(MP_QSTR_machine), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    mp_obj_t I2C_class = mp_load_attr(machine_mod, MP_QSTR_I2C);
    mp_obj_t Pin_class = mp_load_attr(machine_mod, MP_QSTR_Pin);
    
    // Create pins
    mp_obj_t sda_args[] = {mp_obj_new_int(sda_pin)};
    mp_obj_t sda = mp_call_function_n_kw(Pin_class, 1, 0, sda_args);
    
    mp_obj_t scl_args[] = {mp_obj_new_int(scl_pin)};
    mp_obj_t scl = mp_call_function_n_kw(Pin_class, 1, 0, scl_args);
    
    // Create I2C with keyword args: I2C(0, sda=sda, scl=scl, freq=400000)
    mp_obj_t i2c_args[] = {
        mp_obj_new_int(0),              // bus number
        MP_OBJ_NEW_QSTR(MP_QSTR_sda),   // kw name
        sda,                             // kw value
        MP_OBJ_NEW_QSTR(MP_QSTR_scl),   // kw name
        scl,                             // kw value
        MP_OBJ_NEW_QSTR(MP_QSTR_freq),  // kw name
        mp_obj_new_int(400000)          // kw value
    };
    mp_obj_t i2c = mp_call_function_n_kw(I2C_class, 1, 3, i2c_args);
    
    // Call scan()
    mp_obj_t scan_args[] = {i2c};
    return mp_call_method_n_kw(0, 0, scan_args);
}
MP_DEFINE_CONST_FUN_OBJ_2(i2c_scan_obj, i2c_scan);
```

## Module Registry Design

For the mypyc-micropython compiler, we'll maintain a registry of known ESP32 modules:

```python
# In compiler source
MICROPYTHON_MODULES = {
    'machine': {
        'classes': ['Pin', 'PWM', 'ADC', 'DAC', 'I2C', 'SPI', 'UART', 'Timer', 'RTC'],
        'functions': ['freq', 'reset', 'soft_reset', 'deepsleep', 'lightsleep'],
        'constants': {},
    },
    'network': {
        'classes': ['WLAN', 'LAN'],
        'constants': ['STA_IF', 'AP_IF'],
    },
    'esp32': {
        'functions': ['raw_temperature', 'hall_sensor', 'idf_heap_info'],
    },
    'time': {
        'functions': ['sleep', 'sleep_ms', 'sleep_us', 'ticks_ms', 'ticks_us', 
                      'ticks_diff', 'ticks_add', 'time', 'localtime', 'mktime'],
    },
    'gc': {
        'functions': ['collect', 'mem_alloc', 'mem_free', 'enable', 'disable'],
    },
}

# Class method signatures for type checking
PIN_METHODS = {
    '__init__': ['id: int', 'mode: int = -1', 'pull: int = -1', 'value: int = None'],
    'value': ['x: int = None -> int'],
    'on': ['-> None'],
    'off': ['-> None'],
    'irq': ['handler: Callable', 'trigger: int', 'hard: bool = False'],
}
```

## Performance Considerations

### Overhead Analysis

| Operation | Relative Cost | Notes |
|-----------|--------------|-------|
| Module import | High (first time) | Cache result |
| Attribute lookup | Medium | Use qstr for speed |
| Function call | Medium | Optimized in MP |
| Method call | Medium | Binding overhead |
| Boxing/unboxing | Low | Fast for small ints |

### Optimization Strategies

1. **Cache module references** at module initialization
2. **Cache class references** if used repeatedly
3. **Avoid repeated attribute lookups** in loops
4. **Use qstr constants** instead of string lookups
5. **Batch operations** where possible

### When to Use Direct C Calls

For maximum performance, bypass MicroPython entirely:

```c
// Direct GPIO using ESP-IDF (faster but less portable)
#include "driver/gpio.h"

static mp_obj_t fast_gpio_set(mp_obj_t pin_obj, mp_obj_t value_obj) {
    int pin = mp_obj_get_int(pin_obj);
    int value = mp_obj_get_int(value_obj);
    gpio_set_level(pin, value);
    return mp_const_none;
}
```

**Trade-off:** Faster but ties code to specific hardware/SDK.

## Best Practices

### 1. Initialize Once, Use Many

```c
// Good: Initialize in module init
static void module_init(void) {
    if (!initialized) {
        cache_machine_module();
        cache_time_module();
        initialized = true;
    }
}

// Bad: Import every time
static mp_obj_t my_func(void) {
    mp_obj_t machine = mp_import_name(...);  // Slow!
}
```

### 2. Use Proper Error Handling

```c
static mp_obj_t safe_pin_write(mp_obj_t pin_obj, mp_obj_t value_obj) {
    nlr_buf_t nlr;
    if (nlr_push(&nlr) == 0) {
        // ... pin operations ...
        nlr_pop();
        return mp_const_none;
    } else {
        // Handle error (e.g., invalid pin)
        return mp_const_false;
    }
}
```

### 3. Document Hardware Dependencies

```c
/**
 * @brief Read temperature from DHT22 sensor
 * @param pin GPIO pin number (must support input)
 * @return Temperature in Celsius * 10 (e.g., 235 = 23.5°C)
 * @note Requires DHT22 sensor connected to specified pin
 * @hardware ESP32, ESP32-S2, ESP32-S3
 */
static mp_obj_t read_dht22(mp_obj_t pin_obj) {
    // ...
}
```

### 4. Test on Real Hardware

Always test compiled modules on actual ESP32 hardware. The Unix port of MicroPython doesn't have hardware modules.

```bash
# Build for ESP32
cd micropython/ports/esp32
make USER_C_MODULES=/path/to/module/micropython.cmake

# Flash and test
esptool.py --chip esp32 write_flash -z 0x1000 firmware.bin
```

## See Also

- [03-micropython-c-api.md](03-micropython-c-api.md) - C API reference
- [05-roadmap.md](05-roadmap.md) - Implementation roadmap
- [ESP32 MicroPython Quick Reference](https://docs.micropython.org/en/latest/esp32/quickref.html)
- [MicroPython C Modules Guide](https://docs.micropython.org/en/latest/develop/cmodules.html)
