from typing import Any


def make_point() -> tuple[int, int]:
    return (10, 20)


def make_triple(a: int, b: int, c: int) -> tuple[int, int, int]:
    return (a, b, c)


def get_first(t: tuple[int, ...]) -> int:
    return t[0]


def get_last(t: tuple[int, ...]) -> int:
    return t[-1]


def tuple_len(t: tuple[int, ...]) -> int:
    return len(t)


def sum_tuple(t: tuple[int, ...]) -> int:
    total: int = 0
    for x in t:
        total += x
    return total


def tuple_contains(t: tuple[int, ...], value: int) -> bool:
    return value in t


def tuple_not_contains(t: tuple[int, ...], value: int) -> bool:
    return value not in t


def unpack_pair(t: tuple[int, int]) -> int:
    a: int
    b: int
    a, b = t
    return a + b


def unpack_triple(t: tuple[int, int, int]) -> int:
    x: int
    y: int
    z: int
    x, y, z = t
    return x * y * z


def concat_tuples(t1: tuple[int, ...], t2: tuple[int, ...]) -> tuple[int, ...]:
    return t1 + t2


def repeat_tuple(t: tuple[int, ...], n: int) -> tuple[int, ...]:
    return t * n


def empty_tuple() -> tuple[()]:
    return ()


def single_element() -> tuple[int]:
    return (42,)


def nested_iteration(t: tuple[int, ...]) -> int:
    total: int = 0
    idx: int = 0
    for val in t:
        total += val * idx
        idx += 1
    return total


def slice_tuple(t: tuple[int, ...]) -> tuple[int, ...]:
    return t[1:3]


def reverse_tuple(t: tuple[int, ...]) -> tuple[int, ...]:
    return t[::-1]


def step_slice(t: tuple[int, ...]) -> tuple[int, ...]:
    return t[::2]


def from_range(n: int) -> tuple[int, ...]:
    return tuple(range(n))


def rtuple_point() -> tuple[int, int]:
    point: tuple[int, int] = (100, 200)
    return point


def rtuple_add_coords(x1: int, y1: int, x2: int, y2: int) -> tuple[int, int]:
    p1: tuple[int, int] = (x1, y1)
    p2: tuple[int, int] = (x2, y2)
    result: tuple[int, int] = (p1[0] + p2[0], p1[1] + p2[1])
    return result


def rtuple_sum_fields() -> int:
    point: tuple[int, int] = (15, 25)
    return point[0] + point[1]


def rtuple_distance_squared(x1: int, y1: int, x2: int, y2: int) -> int:
    p1: tuple[int, int] = (x1, y1)
    p2: tuple[int, int] = (x2, y2)
    dx: int = p2[0] - p1[0]
    dy: int = p2[1] - p1[1]
    return dx * dx + dy * dy


def rtuple_rgb() -> tuple[int, int, int]:
    color: tuple[int, int, int] = (255, 128, 64)
    return color


def rtuple_sum_rgb(r: int, g: int, b: int) -> int:
    color: tuple[int, int, int] = (r, g, b)
    return color[0] + color[1] + color[2]


def rtuple_blend_colors(
    r1: int, g1: int, b1: int, r2: int, g2: int, b2: int
) -> tuple[int, int, int]:
    c1: tuple[int, int, int] = (r1, g1, b1)
    c2: tuple[int, int, int] = (r2, g2, b2)
    result: tuple[int, int, int] = (
        (c1[0] + c2[0]) // 2,
        (c1[1] + c2[1]) // 2,
        (c1[2] + c2[2]) // 2,
    )
    return result


def rtuple_benchmark_internal(n: int) -> int:
    total: int = 0
    i: int = 0
    while i < n:
        point: tuple[int, int] = (i, i * 2)
        total += point[0] + point[1]
        i += 1
    return total


def sum_points_list(points: list[tuple[int, int, int]], count: int) -> int:
    total: int = 0
    i: int = 0
    while i < count:
        p: tuple[int, int, int] = points[i]
        total = total + p[0] + p[1] + p[2]
        i = i + 1
    return total
