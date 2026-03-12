"""Example: Class constants using typing.Final.

This demonstrates the preferred pattern for class constants in compiled code:
- Use `Final[T]` for immutable class-level constants
- Access via `ClassName.CONSTANT` syntax

Generated C code will emit #define constants for efficient access.
"""

from typing import Final


class LvEvent:
    """LVGL event type constants.

    These constants are compile-time values that can be accessed as
    LvEvent.CLICKED, LvEvent.LONG_PRESSED, etc.
    """

    CLICKED: Final[int] = 10
    LONG_PRESSED: Final[int] = 20
    RELEASED: Final[int] = 30
    FOCUSED: Final[int] = 40


class Config:
    """Application configuration constants."""

    DEBUG_MODE: Final[bool] = True
    MAX_ITEMS: Final[int] = 100
    VERSION: Final[int] = 1


def get_click_event() -> int:
    """Return the CLICKED event code."""
    return LvEvent.CLICKED


def get_long_press_event() -> int:
    """Return the LONG_PRESSED event code."""
    return LvEvent.LONG_PRESSED


def is_debug() -> bool:
    """Check if debug mode is enabled."""
    return Config.DEBUG_MODE


def get_max_items() -> int:
    """Return the maximum number of items."""
    return Config.MAX_ITEMS


def check_event(event_code: int) -> bool:
    """Check if event code matches CLICKED."""
    return event_code == LvEvent.CLICKED


def compare_events(a: int, b: int) -> int:
    """Compare two events and return CLICKED if they match."""
    if a == b:
        return LvEvent.CLICKED
    return LvEvent.RELEASED
