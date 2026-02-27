def countdown(n: int):
    while n > 0:
        yield n
        n -= 1


def squares(n: int):
    for i in range(n):
        yield i * i


def iter_items(items: list[object]):
    """Generator that yields each item from a list."""
    for x in items:
        yield x


def range_with_start(n: int):
    """Generator using range with non-zero start."""
    for i in range(1, n):
        yield i
