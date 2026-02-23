"""List comprehension examples for testing the compiler."""


def squares(n: int) -> list[int]:
    """Generate list of squares using list comprehension."""
    return [x * x for x in range(n)]


def evens(n: int) -> list[int]:
    """Filter even numbers using list comprehension with condition."""
    return [x for x in range(n) if x % 2 == 0]


def doubled(items: list[int]) -> list[int]:
    """Double each item using iterator-based list comprehension."""
    return [x * 2 for x in items]


def filter_positive(items: list[int]) -> list[int]:
    """Filter positive numbers from a list."""
    return [x for x in items if x > 0]


def sum_squares(n: int) -> int:
    """Sum of squares using list comprehension."""
    result: list[int] = [i * i for i in range(n)]
    total: int = 0
    for x in result:
        total += x
    return total


def count_evens(n: int) -> int:
    """Count even numbers using list comprehension."""
    result: list[int] = [x for x in range(n) if x % 2 == 0]
    return len(result)
