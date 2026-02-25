"""Math operations using imported modules.

Demonstrates runtime import support for built-in MicroPython modules.
"""

import math
import time


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Euclidean distance between two points."""
    dx: float = x2 - x1
    dy: float = y2 - y1
    return math.sqrt(dx * dx + dy * dy)


def circle_area(radius: float) -> float:
    """Area of a circle."""
    return math.pi * radius * radius


def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians."""
    return degrees * math.pi / 180.0


def trig_sum(angle: float) -> float:
    """Sum of sin and cos for an angle (in radians)."""
    return math.sin(angle) + math.cos(angle)


def timed_sum(n: int) -> int:
    """Sum integers from 0 to n, using time.ticks_us for benchmarking."""
    total: int = 0
    for i in range(n):
        total += i
    return total
