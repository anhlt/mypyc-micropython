"""Lambda expression and closure support example.

This module demonstrates:
1. Simple lambdas without closures
2. Lambdas capturing variables from enclosing scope
3. Multiple lambdas with unique IDs
4. Lambdas capturing multiple variables
"""

from typing import Callable


def simple_lambda() -> int:
    """Use a simple lambda that takes two arguments."""
    add: Callable[[int, int], int] = lambda x, y: x + y
    return add(2, 3)


def lambda_with_closure(base: int) -> int:
    """Lambda capturing 'multiplier' from enclosing scope."""
    multiplier: int = 10
    fn: Callable[[int], int] = lambda x: x * multiplier + base
    return fn(5)


def multiple_lambdas() -> int:
    """Use multiple lambdas in the same function."""
    add: Callable[[int, int], int] = lambda x, y: x + y
    sub: Callable[[int, int], int] = lambda x, y: x - y
    mul: Callable[[int, int], int] = lambda x, y: x * y
    return add(10, 5) + sub(10, 5) + mul(10, 5)


def lambda_multi_capture(a: int, b: int) -> int:
    """Lambda capturing multiple variables."""
    x: int = a + 1
    y: int = b + 2
    fn: Callable[[int], int] = lambda z: x + y + z
    return fn(100)


def higher_order(fn: Callable[[int], int], value: int) -> int:
    """Example of passing lambda to another function."""
    return fn(value)


def use_higher_order() -> int:
    """Pass a lambda to a higher-order function."""
    double: Callable[[int], int] = lambda x: x * 2
    return higher_order(double, 21)
