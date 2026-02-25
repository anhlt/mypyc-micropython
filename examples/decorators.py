"""Demonstrate @property, @staticmethod, and @classmethod decorators."""


class Rectangle:
    """A rectangle with computed properties and utility methods."""

    width: int
    height: int

    def __init__(self, w: int, h: int) -> None:
        self.width = w
        self.height = h

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def perimeter(self) -> int:
        return 2 * (self.width + self.height)

    def scale(self, factor: int) -> None:
        self.width = self.width * factor
        self.height = self.height * factor

    @staticmethod
    def is_square_dims(w: int, h: int) -> bool:
        return w == h

    @classmethod
    def square(cls, size: int) -> object:
        """Create a square rectangle."""
        return cls


class Temperature:
    """Temperature with read-write property."""

    _celsius: int

    def __init__(self, c: int) -> None:
        self._celsius = c

    @property
    def celsius(self) -> int:
        return self._celsius

    @celsius.setter
    def celsius(self, value: int) -> None:
        self._celsius = value

    def get_fahrenheit(self) -> int:
        return self._celsius * 9 // 5 + 32


class Counter:
    """Counter with static utility and property."""

    _count: int

    def __init__(self, start: int) -> None:
        self._count = start

    @property
    def count(self) -> int:
        return self._count

    def increment(self) -> None:
        self._count = self._count + 1

    @staticmethod
    def add(a: int, b: int) -> int:
        return a + b
