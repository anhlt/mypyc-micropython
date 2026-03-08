"""Optional type narrowing example.

Demonstrates how the compiler optimizes Optional (X | None) types:
- Before a None check: attribute access uses dynamic dispatch (mp_load_attr)
- After 'if x is not None:' or 'if x is None: return': attribute access
  uses static dispatch (direct struct pointer dereference)

This optimization is critical for performance in patterns like the
LVGL MVU framework's diff_widgets(prev: Widget | None, next_w: Widget).
"""


class Point:
    """Simple class with two fields."""

    x: int
    y: int

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


class Rect:
    """Rectangle defined by two points."""

    top_left: Point
    bottom_right: Point

    def __init__(self, tl: Point, br: Point) -> None:
        self.top_left = tl
        self.bottom_right = br


# --- Pattern 1: if x is not None (narrowing in body) ---


def get_x_or_default(p: Point | None, default: int) -> int:
    """Access attribute after None check with is not None."""
    if p is not None:
        # Narrowed: p is Point -> static dispatch (direct struct access)
        return p.x
    return default


# --- Pattern 2: if x is None: return (early return narrowing) ---


def get_y_with_guard(p: Point | None) -> int:
    """Access attribute after early return None guard."""
    if p is None:
        return -1
    # After the guard, p is narrowed to Point -> static dispatch
    return p.y


# --- Pattern 3: Optional in else branch ---


def describe_point(p: Point | None) -> str:
    """Narrowing in else branch of is None check."""
    if p is None:
        return "no point"
    else:
        # Narrowed: p is Point -> static dispatch
        result: str = str(p.x) + "," + str(p.y)
        return result


# --- Pattern 4: Multiple Optional params ---


def add_points(a: Point | None, b: Point | None) -> int:
    """Multiple Optional params narrowed independently."""
    if a is None:
        return 0
    if b is None:
        return a.x + a.y  # a is narrowed, b is None
    # Both narrowed: static dispatch for both
    return a.x + b.x + a.y + b.y


# --- Pattern 5: Optional class param in methods ---


class Container:
    """Container with optional point reference."""

    value: int
    point: Point

    def __init__(self, value: int, pt: Point) -> None:
        self.value = value
        self.point = pt


def get_container_x(c: Container | None) -> int:
    """Access nested attribute after None guard."""
    if c is None:
        return 0
    return c.value


# --- Pattern 6: Non-Optional class param (baseline) ---


def get_x_direct(p: Point) -> int:
    """Direct access, no Optional, always static dispatch."""
    return p.x


# --- Test function ---


def test_optional_narrowing() -> str:
    """Test all Optional narrowing patterns."""
    p1 = Point(10, 20)
    p2 = Point(30, 40)
    c1 = Container(99, p1)

    r1: int = get_x_or_default(p1, 0)
    r2: int = get_x_or_default(None, 42)

    r3: int = get_y_with_guard(p1)
    r4: int = get_y_with_guard(None)

    r5: str = describe_point(p1)
    r6: str = describe_point(None)

    r7: int = add_points(p1, p2)
    r8: int = add_points(p1, None)
    r9: int = add_points(None, p2)

    r10: int = get_container_x(c1)
    r11: int = get_container_x(None)

    r12: int = get_x_direct(p1)

    results: list[object] = [r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12]
    parts: list[str] = []
    for r in results:
        s: str = str(r)
        parts.append(s)
    return ",".join(parts)
