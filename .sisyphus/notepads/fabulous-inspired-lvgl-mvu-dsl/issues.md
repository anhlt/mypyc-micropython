# Issues

- Firmware build can fail even if `make compile` succeeds; verify with `make build BOARD=ESP32_GENERIC_C6`.
- Generated C previously failed when LVGL is imported inside helper functions (observed: `lvgl` undeclared in usermod C).
