"""P0 attribute apply functions for LVGL widget properties.

This module provides functions that apply attribute values to LVGL objects.
Each function is registered with the AttrRegistry and called by the
reconciler when attributes change.

The apply functions follow the signature: (lv_obj, value) -> None

Usage::

    from lvgl_mvu.appliers import register_p0_appliers

    registry = AttrRegistry()
    register_p0_appliers(registry)
"""

from __future__ import annotations

import lvgl as lv

from lvgl_mvu.attrs import AttrDef, AttrKey, AttrRegistry

# ---------------------------------------------------------------------------
# Position / Size Appliers
# ---------------------------------------------------------------------------


def apply_x(lv_obj: object, value: object) -> None:
    """Set X position of an LVGL object."""
    lv.lv_obj_set_x(lv_obj, value)


def apply_y(lv_obj: object, value: object) -> None:
    """Set Y position of an LVGL object."""
    lv.lv_obj_set_y(lv_obj, value)


def apply_width(lv_obj: object, value: object) -> None:
    """Set width of an LVGL object."""
    lv.lv_obj_set_width(lv_obj, value)


def apply_height(lv_obj: object, value: object) -> None:
    """Set height of an LVGL object."""
    lv.lv_obj_set_height(lv_obj, value)


def apply_align(lv_obj: object, value: object) -> None:
    """Set alignment of an LVGL object.

    Uses lv_obj_align with 0 offsets. Alignment offsets (ALIGN_X_OFS,
    ALIGN_Y_OFS) are not currently supported - they require batching
    multiple attributes together which is not yet implemented.
    """
    lv.lv_obj_align(lv_obj, value, 0, 0)

def apply_align_x_ofs(lv_obj: object, value: object) -> None:
    """Set X offset for alignment (requires re-alignment)."""
    # Note: LVGL alignment offsets are applied via lv_obj_align which
    # requires the alignment type. This is a placeholder - the reconciler
    # should batch ALIGN + offsets together.
    pass


def apply_align_y_ofs(lv_obj: object, value: object) -> None:
    """Set Y offset for alignment (requires re-alignment)."""
    # Same as X offset - handled at reconciliation time
    pass


# ---------------------------------------------------------------------------
# Padding Appliers
# ---------------------------------------------------------------------------


def apply_pad_top(lv_obj: object, value: object) -> None:
    """Set top padding."""
    lv.lv_obj_set_style_pad_top(lv_obj, value, 0)


def apply_pad_right(lv_obj: object, value: object) -> None:
    """Set right padding."""
    lv.lv_obj_set_style_pad_right(lv_obj, value, 0)


def apply_pad_bottom(lv_obj: object, value: object) -> None:
    """Set bottom padding."""
    lv.lv_obj_set_style_pad_bottom(lv_obj, value, 0)


def apply_pad_left(lv_obj: object, value: object) -> None:
    """Set left padding."""
    lv.lv_obj_set_style_pad_left(lv_obj, value, 0)


def apply_pad_row(lv_obj: object, value: object) -> None:
    """Set row padding (vertical gap in flex layouts)."""
    lv.lv_obj_set_style_pad_row(lv_obj, value, 0)


def apply_pad_column(lv_obj: object, value: object) -> None:
    """Set column padding (horizontal gap in flex layouts)."""
    lv.lv_obj_set_style_pad_column(lv_obj, value, 0)


# ---------------------------------------------------------------------------
# Background Appliers
# ---------------------------------------------------------------------------


def apply_bg_color(lv_obj: object, value: object) -> None:
    """Set background color."""
    color: object = lv.lv_color_hex(value)
    lv.lv_obj_set_style_bg_color(lv_obj, color, 0)


def apply_bg_opa(lv_obj: object, value: object) -> None:
    """Set background opacity (0-255)."""
    lv.lv_obj_set_style_bg_opa(lv_obj, value, 0)


# ---------------------------------------------------------------------------
# Border Appliers
# ---------------------------------------------------------------------------


def apply_border_color(lv_obj: object, value: object) -> None:
    """Set border color."""
    color: object = lv.lv_color_hex(value)
    lv.lv_obj_set_style_border_color(lv_obj, color, 0)


def apply_border_width(lv_obj: object, value: object) -> None:
    """Set border width."""
    lv.lv_obj_set_style_border_width(lv_obj, value, 0)


def apply_border_opa(lv_obj: object, value: object) -> None:
    """Set border opacity."""
    lv.lv_obj_set_style_border_opa(lv_obj, value, 0)


def apply_radius(lv_obj: object, value: object) -> None:
    """Set corner radius."""
    lv.lv_obj_set_style_radius(lv_obj, value, 0)


# ---------------------------------------------------------------------------
# Text Appliers
# ---------------------------------------------------------------------------


def apply_text(lv_obj: object, value: object) -> None:
    """Set text content of a label or button.

    For labels, sets text directly via lv_label_set_text.
    For buttons, creates/updates a child label.
    """
    # Try setting as label first (most common case)
    try:
        lv.lv_label_set_text(lv_obj, value)
        return
    except Exception:
        pass

    # For buttons, need a child label
    child_cnt: int = lv.lv_obj_get_child_count(lv_obj)
    label: object
    if child_cnt > 0:
        # Update existing child label
        label = lv.lv_obj_get_child(lv_obj, 0)
        try:
            lv.lv_label_set_text(label, value)
            return
        except Exception:
            pass

    # Create new label for button
    label = lv.lv_label_create(lv_obj)
    lv.lv_label_set_text(label, value)
    lv.lv_obj_center(label)
def apply_text_color(lv_obj: object, value: object) -> None:
    """Set text color."""
    color: object = lv.lv_color_hex(value)
    lv.lv_obj_set_style_text_color(lv_obj, color, 0)


def apply_text_opa(lv_obj: object, value: object) -> None:
    """Set text opacity."""
    lv.lv_obj_set_style_text_opa(lv_obj, value, 0)


def apply_text_align(lv_obj: object, value: object) -> None:
    """Set text alignment."""
    lv.lv_obj_set_style_text_align(lv_obj, value, 0)


# ---------------------------------------------------------------------------
# Layout Appliers
# ---------------------------------------------------------------------------


def apply_flex_flow(lv_obj: object, value: object) -> None:
    """Set flex layout flow direction.

    Note: Flex alignment (main/cross/track) must be set separately via
    FLEX_MAIN_PLACE, FLEX_CROSS_PLACE, FLEX_TRACK_PLACE attributes.
    """
    lv.lv_obj_set_flex_flow(lv_obj, value)

def apply_flex_main_place(lv_obj: object, value: object) -> None:
    """Set flex main axis placement."""
    # Note: LVGL flex_align requires all three params at once.
    # This is handled by storing and applying together.
    pass


def apply_flex_cross_place(lv_obj: object, value: object) -> None:
    """Set flex cross axis placement."""
    pass


def apply_flex_track_place(lv_obj: object, value: object) -> None:
    """Set flex track placement."""
    pass


def apply_flex_grow(lv_obj: object, value: object) -> None:
    """Set flex grow factor."""
    lv.lv_obj_set_flex_grow(lv_obj, value)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_p0_appliers(registry: AttrRegistry) -> None:
    """Register all P0 attribute appliers with the registry.

    This should be called during app initialization to enable
    attribute application for P0 widgets.

    Args:
        registry: The AttrRegistry instance to register appliers with.
    """
    # Position / Size
    registry.add(AttrDef(AttrKey.X, "x", 0, apply_x))
    registry.add(AttrDef(AttrKey.Y, "y", 0, apply_y))
    registry.add(AttrDef(AttrKey.WIDTH, "width", 0, apply_width))
    registry.add(AttrDef(AttrKey.HEIGHT, "height", 0, apply_height))
    registry.add(AttrDef(AttrKey.ALIGN, "align", 0, apply_align))
    registry.add(AttrDef(AttrKey.ALIGN_X_OFS, "align_x_ofs", 0, apply_align_x_ofs))
    registry.add(AttrDef(AttrKey.ALIGN_Y_OFS, "align_y_ofs", 0, apply_align_y_ofs))

    # Padding
    registry.add(AttrDef(AttrKey.PAD_TOP, "pad_top", 0, apply_pad_top))
    registry.add(AttrDef(AttrKey.PAD_RIGHT, "pad_right", 0, apply_pad_right))
    registry.add(AttrDef(AttrKey.PAD_BOTTOM, "pad_bottom", 0, apply_pad_bottom))
    registry.add(AttrDef(AttrKey.PAD_LEFT, "pad_left", 0, apply_pad_left))
    registry.add(AttrDef(AttrKey.PAD_ROW, "pad_row", 0, apply_pad_row))
    registry.add(AttrDef(AttrKey.PAD_COLUMN, "pad_column", 0, apply_pad_column))

    # Background
    registry.add(AttrDef(AttrKey.BG_COLOR, "bg_color", 0x000000, apply_bg_color))
    registry.add(AttrDef(AttrKey.BG_OPA, "bg_opa", 255, apply_bg_opa))

    # Border
    registry.add(AttrDef(AttrKey.BORDER_COLOR, "border_color", 0x000000, apply_border_color))
    registry.add(AttrDef(AttrKey.BORDER_WIDTH, "border_width", 0, apply_border_width))
    registry.add(AttrDef(AttrKey.BORDER_OPA, "border_opa", 255, apply_border_opa))
    registry.add(AttrDef(AttrKey.RADIUS, "radius", 0, apply_radius))

    # Text
    registry.add(AttrDef(AttrKey.TEXT, "text", "", apply_text))
    registry.add(AttrDef(AttrKey.TEXT_COLOR, "text_color", 0xFFFFFF, apply_text_color))
    registry.add(AttrDef(AttrKey.TEXT_OPA, "text_opa", 255, apply_text_opa))
    registry.add(AttrDef(AttrKey.TEXT_ALIGN, "text_align", 0, apply_text_align))

    # Layout
    registry.add(AttrDef(AttrKey.FLEX_FLOW, "flex_flow", 0, apply_flex_flow))
    registry.add(AttrDef(AttrKey.FLEX_MAIN_PLACE, "flex_main_place", 0, apply_flex_main_place))
    registry.add(AttrDef(AttrKey.FLEX_CROSS_PLACE, "flex_cross_place", 0, apply_flex_cross_place))
    registry.add(AttrDef(AttrKey.FLEX_TRACK_PLACE, "flex_track_place", 0, apply_flex_track_place))
    registry.add(AttrDef(AttrKey.FLEX_GROW, "flex_grow", 0, apply_flex_grow))
