"""isinstance() builtin support demo.

Demonstrates compile-time isinstance() checks that emit mp_obj_is_type()
for efficient type dispatch. Covers:
- Simple class hierarchy type checking
- Type narrowing via annotated assignment
- Dataclass variants (MVU message pattern)
- isinstance with builtin types (int, str)
"""

from __future__ import annotations

from dataclasses import dataclass


# -- Simple class hierarchy --------------------------------------------------


class Shape:
    name: str

    def __init__(self, name: str) -> None:
        self.name = name


class Circle(Shape):
    radius: int

    def __init__(self, radius: int) -> None:
        self.name = "circle"
        self.radius = radius


class Rectangle(Shape):
    width: int
    height: int

    def __init__(self, width: int, height: int) -> None:
        self.name = "rectangle"
        self.width = width
        self.height = height


def is_circle(shape: object) -> bool:
    return isinstance(shape, Circle)


def is_rectangle(shape: object) -> bool:
    return isinstance(shape, Rectangle)


# -- Type narrowing with isinstance ------------------------------------------


def describe_shape(shape: object) -> str:
    if isinstance(shape, Circle):
        c: Circle = shape
        return c.name
    elif isinstance(shape, Rectangle):
        r: Rectangle = shape
        return r.name
    return "unknown"


def get_area(shape: object) -> int:
    """Compute area using isinstance + type narrowing."""
    if isinstance(shape, Circle):
        c: Circle = shape
        return c.radius * c.radius * 3
    elif isinstance(shape, Rectangle):
        r: Rectangle = shape
        return r.width * r.height
    return 0


# -- Dataclass variants (MVU message pattern) --------------------------------


@dataclass(frozen=True)
class Increment:
    amount: int


@dataclass(frozen=True)
class SetValue:
    value: int


class Reset:
    pass


def process_msg(msg: object, count: int) -> int:
    """Process MVU-style messages with isinstance dispatch."""
    if isinstance(msg, Increment):
        inc: Increment = msg
        return count + inc.amount
    elif isinstance(msg, SetValue):
        sv: SetValue = msg
        return sv.value
    elif isinstance(msg, Reset):
        return 0
    return count


# -- Negated isinstance ------------------------------------------------------


def is_not_circle(shape: object) -> bool:
    return not isinstance(shape, Circle)


# -- elif chain dispatch -----------------------------------------------------


def shape_sides(shape: object) -> int:
    """Return number of sides for known shapes."""
    if isinstance(shape, Circle):
        return 0
    elif isinstance(shape, Rectangle):
        return 4
    return -1
