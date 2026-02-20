def is_truthy(x: int) -> bool:
    return bool(x)


def is_list_empty(lst: list[int]) -> bool:
    return not bool(lst)


def find_min_two(a: int, b: int) -> int:
    return min(a, b)


def find_min_three(a: int, b: int, c: int) -> int:
    return min(a, b, c)


def find_max_two(a: int, b: int) -> int:
    return max(a, b)


def find_max_three(a: int, b: int, c: int) -> int:
    return max(a, b, c)


def sum_list(lst: list[int]) -> int:
    total: int = 0
    for x in lst:
        total += x
    return total


def sum_list_with_start(lst: list[int], start: int) -> int:
    total: int = start
    for x in lst:
        total += x
    return total


def sum_int_list(nums: list[int]) -> int:
    return sum(nums)


def clamp(val: int, low: int, high: int) -> int:
    return max(low, min(val, high))


def abs_diff(a: int, b: int) -> int:
    return max(a, b) - min(a, b)


def clamp_list(values: list[int], low: int, high: int) -> list[int]:
    result: list[int] = []
    for v in values:
        clamped: int = max(low, min(v, high))
        result.append(clamped)
    return result


def find_extremes_sum(lst: list[int]) -> int:
    min_val: int = lst[0]
    max_val: int = lst[0]
    for x in lst:
        if x < min_val:
            min_val = x
        if x > max_val:
            max_val = x
    return min_val + max_val
