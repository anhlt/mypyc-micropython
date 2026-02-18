def sum_all(*numbers) -> int:
    total: int = 0
    for x in numbers:
        total += x
    return total


def sum_args(*args) -> int:
    total: int = 0
    for x in args:
        total += x
    return total


def count_args(*items) -> int:
    count: int = 0
    for _ in items:
        count += 1
    return count


def first_or_default(*values) -> int:
    for v in values:
        return v
    return -1


def log_values(prefix: int, *values) -> int:
    total: int = prefix
    for v in values:
        total += v
    return total


def count_kwargs(**kwargs) -> int:
    count: int = 0
    for k in kwargs:
        count += 1
    return count


def make_config(**options) -> dict:
    return options


def process(name: int, *args, **kwargs) -> int:
    total: int = name
    for a in args:
        total += a
    for k in kwargs:
        total += 1
    return total


def max_of_args(*nums) -> int:
    result: int = 0
    first: bool = True
    for n in nums:
        val: int = n
        if first:
            result = val
            first = False
        elif val > result:
            result = val
    return result


def min_of_args(*nums) -> int:
    result: int = 0
    first: bool = True
    for n in nums:
        val: int = n
        if first:
            result = val
            first = False
        elif val < result:
            result = val
    return result
