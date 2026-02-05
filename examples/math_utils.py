def celsius_to_fahrenheit(c: float) -> float:
    return c * 1.8 + 32.0


def fahrenheit_to_celsius(f: float) -> float:
    return (f - 32.0) / 1.8


def clamp(value: float, min_val: float, max_val: float) -> float:
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t
