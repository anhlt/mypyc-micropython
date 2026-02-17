def make_point() -> tuple:
    """Create a tuple representing a 2D point"""
    return (10, 20)


def make_triple(a: int, b: int, c: int) -> tuple:
    """Create a tuple from three values"""
    return (a, b, c)


def get_first(t: tuple) -> int:
    """Get the first element of a tuple"""
    return t[0]


def get_last(t: tuple) -> int:
    """Get the last element using negative index"""
    return t[-1]


def tuple_len(t: tuple) -> int:
    """Get the length of a tuple"""
    return len(t)


def sum_tuple(t: tuple) -> int:
    """Sum all elements in a tuple using iteration"""
    total: int = 0
    for x in t:
        total += x
    return total


def tuple_contains(t: tuple, value: int) -> bool:
    """Check if a value is in the tuple"""
    return value in t


def tuple_not_contains(t: tuple, value: int) -> bool:
    """Check if a value is NOT in the tuple"""
    return value not in t


def unpack_pair(t: tuple) -> int:
    """Unpack a tuple into two variables and return their sum"""
    a: int
    b: int
    a, b = t
    return a + b


def unpack_triple(t: tuple) -> int:
    """Unpack a tuple into three variables and return their product"""
    x: int
    y: int
    z: int
    x, y, z = t
    return x * y * z


def concat_tuples(t1: tuple, t2: tuple) -> tuple:
    """Concatenate two tuples"""
    return t1 + t2


def repeat_tuple(t: tuple, n: int) -> tuple:
    """Repeat a tuple n times"""
    return t * n


def empty_tuple() -> tuple:
    """Create an empty tuple"""
    return ()


def single_element() -> tuple:
    """Create a single-element tuple"""
    return (42,)


def nested_iteration(t: tuple) -> int:
    """Iterate over tuple elements with index tracking"""
    total: int = 0
    idx: int = 0
    for val in t:
        total += val * idx
        idx += 1
    return total


def slice_tuple(t: tuple) -> tuple:
    """Get a slice of a tuple"""
    return t[1:3]


def reverse_tuple(t: tuple) -> tuple:
    """Reverse a tuple using slicing"""
    return t[::-1]


def step_slice(t: tuple) -> tuple:
    """Get every other element"""
    return t[::2]


def from_range(n: int) -> tuple:
    """Create a tuple from a range"""
    return tuple(range(n))
