def make_set() -> set[int]:
    return {1, 2, 3}


def empty_set() -> set[int]:
    return set()


def set_from_range(n: int) -> set[int]:
    return set(range(n))


def set_add(s: set[int], value: int) -> set[int]:
    s.add(value)
    return s


def set_discard(s: set[int], value: int) -> set[int]:
    s.discard(value)
    return s


def set_remove(s: set[int], value: int) -> set[int]:
    s.remove(value)
    return s


def set_pop(s: set[int]) -> int:
    return s.pop()


def set_clear(s: set[int]) -> set[int]:
    s.clear()
    return s


def set_copy(s: set[int]) -> set[int]:
    return s.copy()


def set_update(s1: set[int], s2: set[int]) -> set[int]:
    s1.update(s2)
    return s1


def set_len(s: set[int]) -> int:
    return len(s)


def set_contains(s: set[int], value: int) -> bool:
    return value in s


def set_not_contains(s: set[int], value: int) -> bool:
    return value not in s


def sum_set(s: set[int]) -> int:
    total: int = 0
    for x in s:
        total += x
    return total


def count_unique(lst: list[int]) -> int:
    s: set[int] = set()
    for item in lst:
        s.add(item)
    return len(s)


def build_set_incremental(n: int) -> int:
    s: set[int] = set()
    for i in range(n):
        s.add(i % 10)
    return len(s)


def filter_duplicates(n: int) -> int:
    s: set[int] = set()
    for i in range(n):
        s.add(i % 5)
    total: int = 0
    for val in s:
        total += val
    return total
