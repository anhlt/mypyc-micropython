def add_with_default(a: int, b: int = 10) -> int:
    return a + b


def scale(x: float, factor: float = 2.0) -> float:
    return x * factor


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    if value < low:
        return low
    if value > high:
        return high
    return value


def increment(x: int, step: int = 1) -> int:
    return x + step


def double_if_flag(x: int, flag: bool = True) -> int:
    if flag:
        return x * 2
    return x


def format_number(n: int, prefix: str = "#") -> str:
    return prefix


def sum_with_start(lst: list[int], start: int = 0) -> int:
    total: int = start
    for x in lst:
        total += x
    return total


def all_defaults(a: int = 1, b: int = 2, c: int = 3) -> int:
    return a + b + c


def power(base: int, exp: int = 2) -> int:
    result: int = 1
    for _ in range(exp):
        result *= base
    return result


def lerp(a: float, b: float, t: float = 0.5) -> float:
    return a + (b - a) * t
