"""Typed functions: TypeVar, Literal, and general (object/Any) type support.

Demonstrates how the compiler handles advanced type annotations:
- TypeVar (classic): erased to upper bound type
- Literal: erased to underlying type (Literal[3] -> int)
- object: compiled as general mp_obj_t (no unboxing)
"""

from typing import Literal, TypeVar

# --- Classic TypeVar (unbounded) ---

T = TypeVar("T")


def identity(x: T) -> T:
    """Unbounded TypeVar erases to object -> mp_obj_t passthrough."""
    return x


# --- Classic TypeVar (bounded to int) ---

N = TypeVar("N", bound=int)


def int_identity(x: N) -> N:
    """Bounded TypeVar erases to int -> mp_int_t with unbox/box."""
    return x


# --- Literal type erasure ---


def get_status(code: Literal[0, 1, 2]) -> int:
    """Literal[0, 1, 2] erases to int -> mp_int_t."""
    return code + 10


def check_flag(flag: Literal[True, False]) -> bool:
    """Literal[True, False] erases to bool."""
    return flag


def fixed_offset() -> Literal[42]:
    """Literal return type erases to int."""
    return 42


# --- General (object) type ---


def passthrough(x: object) -> object:
    """object type compiles as general mp_obj_t with no unboxing."""
    return x


# --- Mixed typed and general params ---


def add_or_zero(x: int, flag: object) -> int:
    """Mix of typed (int) and general (object) params."""
    if flag:
        return x + x
    return 0


# --- Test function ---


def test_typed_funcs() -> str:
    """Test all typed function patterns."""
    # Classic TypeVar (unbounded -> object passthrough)
    r1: object = identity(42)
    r2: int = identity(10)

    # Classic TypeVar (bounded -> int passthrough)
    r3: int = int_identity(5)

    # Literal erasure
    r4: int = get_status(1)
    r5: bool = check_flag(True)
    r6: int = fixed_offset()

    # General (object)
    r7: object = passthrough(77)

    # Mixed
    r8: int = add_or_zero(6, True)
    r9: int = add_or_zero(6, False)

    results: list[object] = [r1, r2, r3, r4, r5, r6, r7, r8, r9]
    parts: list[str] = []
    for r in results:
        s: str = str(r)
        parts.append(s)
    return ",".join(parts)


# --- TypeVar no-leak: function after TypeVar function uses int correctly ---


def after_typevar(x: int) -> int:
    """Function defined after TypeVar functions. Must unbox as int, not leak TypeVar."""
    return x * 2


# --- General type in class fields ---


class GenericBox:
    """Class with object-typed (GENERAL) field."""

    value: object
    label: str

    def __init__(self, value: object, label: str) -> None:
        self.value = value
        self.label = label

    def get_value(self) -> object:
        return self.value

    def get_label(self) -> str:
        return self.label
