def make_set() -> set:
    """Create a set with initial values"""
    return {1, 2, 3}


def empty_set() -> set:
    """Create an empty set"""
    return set()


def set_from_range(n: int) -> set:
    """Create a set from a range"""
    return set(range(n))


def set_add(s: set, value: int) -> set:
    """Add an element to a set"""
    s.add(value)
    return s


def set_discard(s: set, value: int) -> set:
    """Discard an element from a set (no error if missing)"""
    s.discard(value)
    return s


def set_remove(s: set, value: int) -> set:
    """Remove an element from a set (raises KeyError if missing)"""
    s.remove(value)
    return s


def set_pop(s: set) -> int:
    """Pop an arbitrary element from the set"""
    return s.pop()


def set_clear(s: set) -> set:
    """Clear all elements from a set"""
    s.clear()
    return s


def set_copy(s: set) -> set:
    """Create a copy of a set"""
    return s.copy()


def set_update(s1: set, s2: set) -> set:
    """Update s1 with elements from s2"""
    s1.update(s2)
    return s1


def set_len(s: set) -> int:
    """Get the number of elements in a set"""
    return len(s)


def set_contains(s: set, value: int) -> bool:
    """Check if value is in the set"""
    return value in s


def set_not_contains(s: set, value: int) -> bool:
    """Check if value is NOT in the set"""
    return value not in s


def sum_set(s: set) -> int:
    """Sum all elements in a set using iteration"""
    total: int = 0
    for x in s:
        total += x
    return total


def count_unique(lst: list) -> int:
    """Count unique elements by converting list to set"""
    s: set = set()
    for item in lst:
        s.add(item)
    return len(s)


def build_set_incremental(n: int) -> int:
    """Build a set incrementally and return its size"""
    s: set = set()
    for i in range(n):
        s.add(i % 10)
    return len(s)


def filter_duplicates(n: int) -> int:
    """Use set to filter duplicates, return sum of unique values"""
    s: set = set()
    for i in range(n):
        s.add(i % 5)
    total: int = 0
    for val in s:
        total += val
    return total
