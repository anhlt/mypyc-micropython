"""Math helper functions for sensor calculations."""


def distance(x1: int, y1: int, x2: int, y2: int) -> int:
    """Squared distance between two points (integer math)."""
    dx: int = x2 - x1
    dy: int = y2 - y1
    return dx * dx + dy * dy


def midpoint(a: int, b: int) -> int:
    """Integer midpoint of two values."""
    return (a + b) // 2


def scale(value: int, factor: int) -> int:
    """Scale a value by an integer factor."""
    return value * factor
