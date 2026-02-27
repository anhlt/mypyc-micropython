"""Cross-module imports between compiled native modules.

Demonstrates that one compiled C module can import and call functions
from another compiled C module at runtime via mp_import_name.
"""

import factorial
import math_ops


def double_factorial(n: int) -> int:
    """Call factorial from the factorial module and double it."""
    return factorial.factorial(n) * 2


def fib_plus(n: int, extra: int) -> int:
    """Call fib from the factorial module and add extra."""
    return factorial.fib(n) + extra


def combo_add(a: int, b: int) -> int:
    """Use add from factorial module."""
    return factorial.add(a, b)


def native_distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Call distance from math_ops (which itself imports math)."""
    return math_ops.distance(x1, y1, x2, y2)


def sum_and_factorial(n: int) -> int:
    """Sum 0..n using timed_sum from math_ops, then multiply by factorial(n)."""
    s: int = math_ops.timed_sum(n)
    f: int = factorial.factorial(n)
    return s * f
