"""Signal filtering functions."""


def clamp(value: int, low: int, high: int) -> int:
    """Clamp value to [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def moving_avg(prev: int, new_val: int, alpha: int) -> int:
    """Simple integer moving average: (alpha * new + (100 - alpha) * prev) / 100."""
    return (alpha * new_val + (100 - alpha) * prev) // 100


def threshold(value: int, thresh: int) -> bool:
    """Return True if value exceeds threshold."""
    return value > thresh
