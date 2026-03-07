from enum import IntEnum


class Color(IntEnum):
    RED = 1
    GREEN = 2
    BLUE = 3


class Priority(IntEnum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10


class Permission(IntEnum):
    READ = 1 << 0
    WRITE = 1 << 1
    EXECUTE = 1 << 2
    ALL = READ | WRITE | EXECUTE


def get_color() -> int:
    return Color.GREEN


def check_color(c: int) -> bool:
    return c == Color.BLUE


def total_priority() -> int:
    return Priority.LOW + Priority.MEDIUM + Priority.HIGH


def is_high_priority(p: int) -> bool:
    return p == Priority.HIGH


def has_write(perm: int) -> bool:
    return (perm & Permission.WRITE) != 0


def default_permissions() -> int:
    return Permission.READ | Permission.WRITE
