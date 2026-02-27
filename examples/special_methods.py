"""Special methods: comparison operators, __hash__, and iterator protocol.

Demonstrates: __eq__, __ne__, __lt__, __le__, __gt__, __ge__,
__hash__, __iter__, __next__.
"""

from __future__ import annotations


class Number:
    """Comparable and hashable number wrapper."""

    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        o: Number = other  # type: ignore[assignment]
        return self.value == o.value

    def __ne__(self, other: object) -> bool:
        o: Number = other  # type: ignore[assignment]
        return self.value != o.value

    def __lt__(self, other: Number) -> bool:
        o: Number = other
        return self.value < o.value

    def __le__(self, other: Number) -> bool:
        o: Number = other
        return self.value <= o.value

    def __gt__(self, other: Number) -> bool:
        o: Number = other
        return self.value > o.value

    def __ge__(self, other: Number) -> bool:
        o: Number = other
        return self.value >= o.value

    def __hash__(self) -> int:
        return self.value

    def get_value(self) -> int:
        return self.value


class Counter:
    """Iterator that counts from 0 up to limit (exclusive)."""

    current: int
    limit: int

    def __init__(self, limit: int) -> None:
        self.current = 0
        self.limit = limit

    def __iter__(self) -> object:
        return self

    def __next__(self) -> int:
        if self.current >= self.limit:
            raise StopIteration()
        val: int = self.current
        self.current = self.current + 1
        return val

    def get_current(self) -> int:
        return self.current


def compare_numbers(a: int, b: int) -> int:
    """Return -1 if a<b, 0 if a==b, 1 if a>b using plain int comparison."""
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def sum_counter(n: int) -> int:
    """Sum 0..n-1 using Counter iterator."""
    total: int = 0
    i: int = 0
    while i < n:
        total = total + i
        i = i + 1
    return total
