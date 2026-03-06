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


def delegate_to_list(items: list[int]):
    """Generator that delegates iteration to a list using yield from."""
    yield from items


def flatten(nested: list[list[int]]):
    """Flatten nested lists using yield from."""
    for inner in nested:
        yield from inner


def chain_iterables(first: list[int], second: list[int]):
    """Chain two iterables together using yield from."""
    yield from first
    yield from second


def prefix_and_delegate(prefix: int, items: list[int], suffix: int):
    """Yield a prefix, delegate to items, then yield a suffix."""
    yield prefix
    yield from items
    yield suffix
