"""Flex layout builders for LVGL MVU framework.

Layout Widgets:
- VStack: Vertical flex container (LV_FLEX_FLOW_COLUMN)
- HStack: Horizontal flex container (LV_FLEX_FLOW_ROW)

These are convenience wrappers around Container that pre-configure
flex layout properties.

Usage::

    from lvgl_mvu.layouts import VStack, HStack

    def view(model: Model) -> Widget:
        return Screen()(
            VStack(spacing=10)(
                Label("Title"),
                HStack(spacing=5)(
                    Button("-"),
                    Label(str(model.count)),
                    Button("+"),
                ),
            ),
        )
"""

from __future__ import annotations

from lvgl_mvu.attrs import AttrKey
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.widget import WidgetKey

# ---------------------------------------------------------------------------
# LVGL Flex Flow Constants
# ---------------------------------------------------------------------------

LV_FLEX_FLOW_ROW: int = 0x00
LV_FLEX_FLOW_COLUMN: int = 0x01
LV_FLEX_FLOW_ROW_WRAP: int = 0x02
LV_FLEX_FLOW_COLUMN_WRAP: int = 0x03
LV_FLEX_FLOW_ROW_REVERSE: int = 0x04
LV_FLEX_FLOW_COLUMN_REVERSE: int = 0x05

# LVGL Flex Align Constants
LV_FLEX_ALIGN_START: int = 0
LV_FLEX_ALIGN_END: int = 1
LV_FLEX_ALIGN_CENTER: int = 2
LV_FLEX_ALIGN_SPACE_EVENLY: int = 3
LV_FLEX_ALIGN_SPACE_AROUND: int = 4
LV_FLEX_ALIGN_SPACE_BETWEEN: int = 5


# ---------------------------------------------------------------------------
# Layout Widget DSL Functions
# ---------------------------------------------------------------------------


def VStack(spacing: int = 0) -> WidgetBuilder:
    """Create a vertical flex container.

    Children are arranged vertically from top to bottom.
    Uses LV_FLEX_FLOW_COLUMN with center alignment.

    Args:
        spacing: Vertical gap between children in pixels.

    Returns:
        WidgetBuilder configured as vertical flex container.

    Example::

        VStack(spacing=10)(
            Label("Line 1"),
            Label("Line 2"),
            Label("Line 3"),
        )
    """
    builder = WidgetBuilder(WidgetKey.CONTAINER)
    builder = builder.set_attr(AttrKey.FLEX_FLOW, LV_FLEX_FLOW_COLUMN)
    builder = builder.set_attr(AttrKey.FLEX_MAIN_PLACE, LV_FLEX_ALIGN_CENTER)
    builder = builder.set_attr(AttrKey.FLEX_CROSS_PLACE, LV_FLEX_ALIGN_CENTER)
    if spacing > 0:
        builder = builder.set_attr(AttrKey.PAD_ROW, spacing)
    return builder


def HStack(spacing: int = 0) -> WidgetBuilder:
    """Create a horizontal flex container.

    Children are arranged horizontally from left to right.
    Uses LV_FLEX_FLOW_ROW with center alignment.

    Args:
        spacing: Horizontal gap between children in pixels.

    Returns:
        WidgetBuilder configured as horizontal flex container.

    Example::

        HStack(spacing=5)(
            Button("-"),
            Label("Count"),
            Button("+"),
        )
    """
    builder = WidgetBuilder(WidgetKey.CONTAINER)
    builder = builder.set_attr(AttrKey.FLEX_FLOW, LV_FLEX_FLOW_ROW)
    builder = builder.set_attr(AttrKey.FLEX_MAIN_PLACE, LV_FLEX_ALIGN_SPACE_EVENLY)
    builder = builder.set_attr(AttrKey.FLEX_CROSS_PLACE, LV_FLEX_ALIGN_CENTER)
    if spacing > 0:
        builder = builder.set_attr(AttrKey.PAD_COLUMN, spacing)
    return builder


def VStackStart(spacing: int = 0) -> WidgetBuilder:
    """Create a vertical flex container with start alignment.

    Children are arranged vertically starting from the top.
    Uses LV_FLEX_FLOW_COLUMN with start alignment.

    Args:
        spacing: Vertical gap between children in pixels.

    Returns:
        WidgetBuilder configured as vertical flex container.
    """
    builder = WidgetBuilder(WidgetKey.CONTAINER)
    builder = builder.set_attr(AttrKey.FLEX_FLOW, LV_FLEX_FLOW_COLUMN)
    builder = builder.set_attr(AttrKey.FLEX_MAIN_PLACE, LV_FLEX_ALIGN_START)
    builder = builder.set_attr(AttrKey.FLEX_CROSS_PLACE, LV_FLEX_ALIGN_CENTER)
    if spacing > 0:
        builder = builder.set_attr(AttrKey.PAD_ROW, spacing)
    return builder


def HStackStart(spacing: int = 0) -> WidgetBuilder:
    """Create a horizontal flex container with start alignment.

    Children are arranged horizontally starting from the left.
    Uses LV_FLEX_FLOW_ROW with start alignment.

    Args:
        spacing: Horizontal gap between children in pixels.

    Returns:
        WidgetBuilder configured as horizontal flex container.
    """
    builder = WidgetBuilder(WidgetKey.CONTAINER)
    builder = builder.set_attr(AttrKey.FLEX_FLOW, LV_FLEX_FLOW_ROW)
    builder = builder.set_attr(AttrKey.FLEX_MAIN_PLACE, LV_FLEX_ALIGN_START)
    builder = builder.set_attr(AttrKey.FLEX_CROSS_PLACE, LV_FLEX_ALIGN_CENTER)
    if spacing > 0:
        builder = builder.set_attr(AttrKey.PAD_COLUMN, spacing)
    return builder
