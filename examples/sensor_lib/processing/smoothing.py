"""Smoothing algorithms for sensor data."""


def exponential_avg(prev: int, new_val: int, weight: int) -> int:
    """Exponential moving average with integer weight (0-100)."""
    return (weight * new_val + (100 - weight) * prev) // 100


def simple_avg(a: int, b: int) -> int:
    """Simple average of two values."""
    return (a + b) // 2
