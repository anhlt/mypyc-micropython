"""Unit conversion functions."""


def celsius_to_fahrenheit(c: int) -> int:
    """Convert Celsius to Fahrenheit (integer math, x10 precision)."""
    return c * 9 // 5 + 32


def fahrenheit_to_celsius(f: int) -> int:
    """Convert Fahrenheit to Celsius (integer math)."""
    return (f - 32) * 5 // 9


def mm_to_inches(mm: int) -> int:
    """Convert millimeters to inches x100 (integer precision)."""
    return mm * 100 // 254
