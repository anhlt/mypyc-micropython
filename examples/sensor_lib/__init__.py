"""Sensor library package - demonstrates package compilation.

This package compiles to a single MicroPython C module with namespaced submodules:
    import sensor_lib
    sensor_lib.math_helpers.distance(0, 0, 3, 4)
    sensor_lib.filters.clamp(150, 0, 100)
    sensor_lib.converters.celsius_to_fahrenheit(100)
"""
