def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fib(n: int) -> int:
    if n <= 1:
        return n
    return fib(n - 2) + fib(n - 1)


def add(a: int, b: int) -> int:
    return a + b


def multiply(a: float, b: float) -> float:
    return a * b


def is_even(n: int) -> bool:
    return n % 2 == 0
