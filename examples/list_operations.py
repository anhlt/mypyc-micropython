def sum_range(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i
    return total


def build_squares(n: int) -> list:
    result: list = []
    for i in range(n):
        result.append(i * i)
    return result


def sum_list(lst: list) -> int:
    total: int = 0
    n: int = len(lst)
    for i in range(n):
        total += lst[i]
    return total


def find_first_negative(lst: list) -> int:
    for i in range(len(lst)):
        if lst[i] < 0:
            return i
    return -1


def skip_zeros(n: int) -> int:
    total: int = 0
    for i in range(n):
        if i == 0:
            continue
        total += i
    return total


def count_until_ten(n: int) -> int:
    count: int = 0
    for i in range(n):
        if i >= 10:
            break
        count += 1
    return count


def matrix_sum(rows: int, cols: int) -> int:
    total: int = 0
    for i in range(rows):
        for j in range(cols):
            total += i + j
    return total


def reverse_sum(n: int) -> int:
    total: int = 0
    for i in range(n, 0, -1):
        total += i
    return total


def append_many(n: int) -> int:
    """Benchmark list.append() - build list then sum"""
    lst: list = []
    for i in range(n):
        lst.append(i)
    total: int = 0
    for i in range(len(lst)):
        total += lst[i]
    return total


def pop_all(n: int) -> int:
    """Benchmark list.pop() - build list then pop all elements"""
    lst: list = []
    for i in range(n):
        lst.append(i)
    total: int = 0
    while len(lst) > 0:
        total += lst.pop()
    return total


def append_pop_cycle(n: int) -> int:
    """Benchmark mixed append/pop - stack-like operations"""
    lst: list = []
    total: int = 0
    for i in range(n):
        lst.append(i)
        if len(lst) > 10:
            total += lst.pop()
    # drain remaining
    while len(lst) > 0:
        total += lst.pop()
    return total
