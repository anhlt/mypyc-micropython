"""Immutable widget descriptors for the LVGL MVU framework.

Widgets are immutable dataclasses that describe the desired UI state.
They are separate from LVGL objects -- the reconciler bridges the two.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class WidgetKey(IntEnum):
    """Widget type identifiers."""

    SCREEN = 0
    CONTAINER = 1
    LABEL = 2
    BUTTON = 3
    SLIDER = 4
    BAR = 5
    ARC = 6
    SWITCH = 7
    CHECKBOX = 8
    IMAGE = 9
    TEXTAREA = 10
    DROPDOWN = 11
    ROLLER = 12
    TABLE = 13
    CHART = 14
    CALENDAR = 15
    KEYBOARD = 16
    MENU = 17
    TABVIEW = 18
    MSGBOX = 19
    SPINNER = 20
    LED = 21
    LINE = 22
    CANVAS = 23
    WINDOW = 24
    TILEVIEW = 25
    LIST = 26
    SPANGROUP = 27
    SPINBOX = 28
    SCALE = 29
    BUTTONMATRIX = 30


@dataclass(frozen=True)
class ScalarAttr:
    """Single property value, keyed by int for sorted-tuple storage."""

    key: int
    value: object


@dataclass(frozen=True)
class Widget:
    """Immutable virtual UI element.

    Attributes are stored as a sorted tuple of ScalarAttr (sorted by key)
    to enable efficient O(N) two-pointer diffing.
    """

    key: int
    user_key: str
    scalar_attrs: tuple[ScalarAttr, ...]
    children: tuple[Widget, ...]
    event_handlers: tuple[tuple[int, object], ...]
