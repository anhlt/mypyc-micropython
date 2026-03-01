"""C type markers for .pyi stub files.

These types serve as markers in .pyi stubs to describe C library interfaces.
They are used by:
1. Our stub parser to generate C wrapper code
2. IDEs for autocomplete and type checking
3. mypy/pyright for validation

Usage in .pyi files:
    from mypyc_micropython.c_bindings.c_types import c_ptr, c_int, c_struct

    @c_struct("lv_obj_t")
    class LvObj: ...

    def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]: ...
"""

from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class c_ptr(Generic[T]):
    """C pointer type: c_ptr[LvObj] -> lv_obj_t*"""

    pass



class c_void:
    """C void type."""

    pass


class c_int:
    """C int type (typically mp_int_t / int32_t)."""

    pass


class c_uint:
    """C unsigned int type (typically mp_uint_t / uint32_t)."""

    pass


class c_int8:
    """C int8_t type."""

    pass


class c_uint8:
    """C uint8_t type."""

    pass


class c_int16:
    """C int16_t type."""

    pass


class c_uint16:
    """C uint16_t type."""

    pass


class c_int32:
    """C int32_t type."""

    pass


class c_uint32:
    """C uint32_t type."""

    pass


class c_float:
    """C float type."""

    pass


class c_double:
    """C double type."""

    pass


class c_bool:
    """C bool type."""

    pass


class c_str:
    """C const char* type."""

    pass


def c_struct(c_name: str, opaque: bool = True):
    """Decorator to mark a class as a C struct.

    Args:
        c_name: The C struct name (e.g., "lv_obj_t")
        opaque: If True, struct is opaque (only used via pointers)
    """

    def decorator(cls: type) -> type:
        cls.__c_struct_name__ = c_name  # type: ignore[attr-defined]
        cls.__c_opaque__ = opaque  # type: ignore[attr-defined]
        return cls

    return decorator


def c_enum(c_name: str):
    """Decorator to mark a class as a C enum.

    Args:
        c_name: The C enum name (e.g., "lv_event_code_t")
    """

    def decorator(cls: type) -> type:
        cls.__c_enum_name__ = c_name  # type: ignore[attr-defined]
        return cls

    return decorator
