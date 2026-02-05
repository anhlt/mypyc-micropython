def set_bit(value: int, bit: int) -> int:
    return value | (1 << bit)


def clear_bit(value: int, bit: int) -> int:
    return value & ~(1 << bit)


def toggle_bit(value: int, bit: int) -> int:
    return value ^ (1 << bit)


def check_bit(value: int, bit: int) -> bool:
    return (value & (1 << bit)) != 0


def count_ones(n: int) -> int:
    count: int = 0
    while n > 0:
        count = count + (n & 1)
        n = n >> 1
    return count


def is_power_of_two(n: int) -> bool:
    if n <= 0:
        return False
    return (n & (n - 1)) == 0
