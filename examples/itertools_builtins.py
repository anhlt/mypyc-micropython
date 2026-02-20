from typing import Any


def sum_with_indices(lst: list[int]) -> int:
    e: list[tuple[int, int]] = list(enumerate(lst))
    total: int = 0
    for i in range(len(e)):
        pair: tuple[int, int] = e[i]
        idx: int = pair[0]
        val: int = pair[1]
        total += idx * val
    return total


def enumerate_from_start(lst: list[Any], start: int) -> list[int]:
    e: list[tuple[int, Any]] = list(enumerate(lst, start))
    result: list[int] = []
    for i in range(len(e)):
        pair: tuple[int, Any] = e[i]
        result.append(pair[0])
    return result


def dot_product(a: list[int], b: list[int]) -> int:
    z: list[tuple[int, int]] = list(zip(a, b))
    total: int = 0
    for i in range(len(z)):
        pair: tuple[int, int] = z[i]
        total += pair[0] * pair[1]
    return total


def zip_three_lists(a: list[int], b: list[int], c: list[int]) -> list[int]:
    z: list[tuple[int, int, int]] = list(zip(a, b, c))
    result: list[int] = []
    for i in range(len(z)):
        triple: tuple[int, int, int] = z[i]
        result.append(triple[0] + triple[1] + triple[2])
    return result


def get_sorted(lst: list[int]) -> list[int]:
    return sorted(lst)


def sum_sorted(lst: list[int]) -> int:
    total: int = 0
    for x in sorted(lst):
        total += x
    return total


def get_first_sorted(lst: list[int]) -> int:
    s: list[int] = sorted(lst)
    return s[0]


def get_last_sorted(lst: list[int]) -> int:
    s: list[int] = sorted(lst)
    return s[len(s) - 1]
