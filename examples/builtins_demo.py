def is_truthy(x: int) -> bool:
    return bool(x)


def is_list_empty(lst: list) -> bool:
    return not bool(lst)


def find_min_two(a: int, b: int) -> int:
    return min(a, b)


def find_min_three(a: int, b: int, c: int) -> int:
    return min(a, b, c)


def find_max_two(a: int, b: int) -> int:
    return max(a, b)


def find_max_three(a: int, b: int, c: int) -> int:
    return max(a, b, c)


def sum_list(lst: list) -> int:
    return sum(lst)


def sum_list_with_start(lst: list, start: int) -> int:
    return sum(lst, start)


def sum_int_list(nums: list[int]) -> int:
    return sum(nums)


def clamp(val: int, low: int, high: int) -> int:
    return max(low, min(val, high))


def abs_diff(a: int, b: int) -> int:
    return max(a, b) - min(a, b)


def clamp_list(values: list, low: int, high: int) -> list:
    result: list = []
    for v in values:
        clamped: int = max(low, min(v, high))
        result.append(clamped)
    return result


def find_extremes_sum(lst: list) -> int:
    return min(lst) + max(lst)
