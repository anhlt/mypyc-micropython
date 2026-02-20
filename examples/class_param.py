from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Vector:
    dx: float
    dy: float


def get_x(p: Point) -> int:
    return p.x


def get_y(p: Point) -> int:
    return p.y


def add_coords(p: Point) -> int:
    return p.x + p.y


def distance_squared(p1: Point, p2: Point) -> int:
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return dx * dx + dy * dy


def midpoint_x(p1: Point, p2: Point) -> int:
    return (p1.x + p2.x) // 2


def scale_point(p: Point, factor: int) -> int:
    return p.x * factor + p.y * factor


def dot_product(v1: Vector, v2: Vector) -> float:
    return v1.dx * v2.dx + v1.dy * v2.dy


def length_squared(v: Vector) -> float:
    return v.dx * v.dx + v.dy * v.dy


def sum_three_points(p1: Point, p2: Point, p3: Point) -> int:
    return p1.x + p1.y + p2.x + p2.y + p3.x + p3.y
