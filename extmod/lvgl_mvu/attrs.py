"""Attribute definitions and registry for LVGL widget properties.

Every LVGL property (text, color, size, padding, ...) is assigned a stable
integer key via AttrKey.  Keys are intentionally spaced into ranges so that
new attributes can be added without renumbering.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class AttrKey(IntEnum):
    """Attribute type identifiers (sorted for diffing)."""

    # -- Position / Size (0-19) ------------------------------------------------
    X = 0
    Y = 1
    WIDTH = 2
    HEIGHT = 3
    ALIGN = 4
    ALIGN_X_OFS = 5
    ALIGN_Y_OFS = 6

    # -- Padding / Margin (20-39) ----------------------------------------------
    PAD_TOP = 20
    PAD_RIGHT = 21
    PAD_BOTTOM = 22
    PAD_LEFT = 23
    PAD_ROW = 24
    PAD_COLUMN = 25

    # -- Background (40-59) ----------------------------------------------------
    BG_COLOR = 40
    BG_OPA = 41
    BG_GRAD_COLOR = 42
    BG_GRAD_DIR = 43

    # -- Border (60-79) --------------------------------------------------------
    BORDER_COLOR = 60
    BORDER_WIDTH = 61
    BORDER_OPA = 62
    BORDER_SIDE = 63
    RADIUS = 64

    # -- Shadow (80-99) --------------------------------------------------------
    SHADOW_WIDTH = 80
    SHADOW_COLOR = 81
    SHADOW_OFS_X = 82
    SHADOW_OFS_Y = 83
    SHADOW_SPREAD = 84
    SHADOW_OPA = 85

    # -- Text (100-119) --------------------------------------------------------
    TEXT = 100
    TEXT_COLOR = 101
    TEXT_OPA = 102
    TEXT_FONT = 103
    TEXT_ALIGN = 104
    TEXT_DECOR = 105

    # -- Layout (120-139) ------------------------------------------------------
    FLEX_FLOW = 120
    FLEX_MAIN_PLACE = 121
    FLEX_CROSS_PLACE = 122
    FLEX_TRACK_PLACE = 123
    FLEX_GROW = 124
    GRID_COLUMN_DSC = 125
    GRID_ROW_DSC = 126
    GRID_CELL_COLUMN_POS = 127
    GRID_CELL_ROW_POS = 128

    # -- Widget-specific (140+) ------------------------------------------------
    MIN_VALUE = 140
    MAX_VALUE = 141
    VALUE = 142
    CHECKED = 143
    SRC = 144
    PLACEHOLDER = 145
    OPTIONS = 146
    SELECTED = 147


@dataclass
class AttrDef:
    """Attribute definition with apply function.

    apply_fn: (lv_obj, value) -> None -- pushes value to the LVGL object.
    compare_fn: optional custom equality check, falls back to == when None.
    """

    key: int
    name: str
    default_val: object
    apply_fn: object
    compare_fn: object | None = None


# ---------------------------------------------------------------------------
# AttrRegistry class - instance-based registry to avoid module-level globals
# ---------------------------------------------------------------------------


class AttrRegistry:
    """Registry for attribute definitions.

    Stores AttrDef instances keyed by their integer key. This class replaces
    the module-level global dict to avoid GC issues in compiled C modules.
    """

    _attrs: dict[int, AttrDef]

    def __init__(self) -> None:
        """Create an empty attribute registry."""
        self._attrs = {}

    def add(self, attr_def: AttrDef) -> AttrDef:
        """Add an attribute definition to the registry.

        Args:
            attr_def: The attribute definition to add.

        Returns:
            The same attr_def (for chaining).
        """
        self._attrs[attr_def.key] = attr_def
        return attr_def

    def get(self, key: int) -> AttrDef | None:
        """Look up an attribute definition by key.

        Args:
            key: The attribute key (from AttrKey enum).

        Returns:
            The AttrDef if found, None otherwise.
        """
        if key in self._attrs:
            return self._attrs[key]
        return None

    def get_or_raise(self, key: int) -> AttrDef:
        """Look up an attribute definition by key, raising if not found.

        Args:
            key: The attribute key (from AttrKey enum).

        Returns:
            The AttrDef.

        Raises:
            KeyError: If the key is not registered.
        """
        return self._attrs[key]

    def all_attrs(self) -> dict[int, AttrDef]:
        """Return a copy of all registered attributes.

        Returns:
            A new dict mapping key -> AttrDef.
        """
        result: dict[int, AttrDef] = {}
        for k in self._attrs:
            result[k] = self._attrs[k]
        return result
