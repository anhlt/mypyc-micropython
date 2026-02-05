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
        total += 1
    return total


def find_first_negative(lst: list) -> int:
    for i in range(len(lst)):
        if i < 0:
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
