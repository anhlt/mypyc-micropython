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


def rtuple_point() -> tuple[int, int]:
    """Create an optimized 2D point using RTuple"""
    point: tuple[int, int] = (100, 200)
    return point


def rtuple_add_coords(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    """Add two coordinate pairs using RTuple optimization"""
    p1: tuple[int, int] = (x1, y1)
    p2: tuple[int, int] = (x2, y2)
    result: tuple[int, int] = (p1[0] + p2[0], p1[1] + p2[1])
    return result


def rtuple_sum_fields() -> int:
    """Sum fields of an RTuple using direct access"""
    point: tuple[int, int] = (15, 25)
    return point[0] + point[1]


def rtuple_distance_squared(x1: int, y1: int, x2: int, y2: int) -> int:
    """Calculate squared distance between two points using RTuple"""
    p1: tuple[int, int] = (x1, y1)
    p2: tuple[int, int] = (x2, y2)
    dx: int = p2[0] - p1[0]
    dy: int = p2[1] - p1[1]
    return dx * dx + dy * dy


def rtuple_rgb() -> tuple[int, int, int]:
    """Create an RGB color tuple using RTuple optimization"""
    color: tuple[int, int, int] = (255, 128, 64)
    return color


def rtuple_sum_rgb(r: int, g: int, b: int) -> int:
    """Sum RGB components using RTuple direct field access"""
    color: tuple[int, int, int] = (r, g, b)
    return color[0] + color[1] + color[2]


def rtuple_blend_colors(
    r1: int, g1: int, b1: int, r2: int, g2: int, b2: int
) -> tuple[int, int, int]:
    """Blend two RGB colors by averaging components"""
    c1: tuple[int, int, int] = (r1, g1, b1)
    c2: tuple[int, int, int] = (r2, g2, b2)
    result: tuple[int, int, int] = (
        (c1[0] + c2[0]) // 2,
        (c1[1] + c2[1]) // 2,
        (c1[2] + c2[2]) // 2,
    )
    return result


def rtuple_benchmark_internal(n: int) -> int:
    """Benchmark RTuple internal ops - returns int to avoid boxing overhead"""
    total: int = 0
    i: int = 0
    while i < n:
        point: tuple[int, int] = (i, i * 2)
        total += point[0] + point[1]
        i += 1
    return total


def sum_points_list(points: list, count: int) -> int:
    """Sum x+y+z for each point in a list of 3D points (RTuple from list)"""
    total: int = 0
    i: int = 0
    while i < count:
        p: tuple[int, int, int] = points[i]
        total = total + p[0] + p[1] + p[2]
        i = i + 1
    return total
