"""Calibration functions for sensor readings."""


def apply_offset(value: int, offset: int) -> int:
    """Apply a calibration offset to a sensor reading."""
    return value + offset


def apply_scale(value: int, scale_num: int, scale_den: int) -> int:
    """Apply a calibration scale factor (numerator/denominator)."""
    return value * scale_num // scale_den
