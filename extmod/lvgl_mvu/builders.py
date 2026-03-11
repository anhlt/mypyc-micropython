"""Fluent widget builder DSL for constructing immutable Widget trees.

Usage::

    from lvgl_mvu.builders import WidgetBuilder
    from lvgl_mvu.widget import WidgetKey
    from lvgl_mvu.attrs import AttrKey

    label = (
        WidgetBuilder(WidgetKey.LABEL)
        .set_attr(AttrKey.TEXT, "Hello")
        .text_color(0xFF0000)
        .build()
    )
"""

from __future__ import annotations

from lvgl_mvu.attrs import AttrKey
from lvgl_mvu.widget import ScalarAttr, Widget


class WidgetBuilder:
    """Fluent builder for Widget construction.

    Every setter returns self so calls can be chained.  Call build()
    for leaf nodes or invoke as callable with children to produce Widget.
    """

    _key: int
    _user_key: str
    _attrs: list[ScalarAttr]
    _children: list[Widget]
    _handlers: list[tuple[int, object]]

    def __init__(self, key: int) -> None:
        self._key = key
        self._user_key = ""
        self._attrs = []
        self._children = []
        self._handlers = []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def user_key(self, key: str) -> WidgetBuilder:
        """Set user-provided key for reuse control during diffing."""
        self._user_key = key
        return self

    def set_attr(self, attr_key: int, value: object) -> WidgetBuilder:
        """Set an arbitrary attribute by key."""
        self._attrs.append(ScalarAttr(attr_key, value))
        return self

    def on(self, event: int, msg: object) -> WidgetBuilder:
        """Register an event handler that dispatches msg on event."""
        self._handlers.append((event, msg))
        return self

    def on_value(self, event: int, msg_fn: object) -> WidgetBuilder:
        """Register an event handler with value extraction."""
        self._handlers.append((event, ("value", msg_fn)))
        return self

    def add_child(self, child: Widget) -> WidgetBuilder:
        """Add a pre-built child widget."""
        self._children.append(child)
        return self

    def with_children(self, children: list[Widget]) -> Widget:
        """Build the widget with the given children.

        This is the primary way to compose widget trees::

            VStack(spacing=10).with_children([
                Label("Line 1").build(),
                Label("Line 2").build(),
            ])

        Args:
            children: List of pre-built Widget instances.

        Returns:
            A new Widget with the given children.
        """
        i: int = 0
        while i < len(children):
            self._children.append(children[i])
            i += 1
        return self.build()

    def build(self) -> Widget:
        """Build the widget (with any children added via add_child)."""
        # Sort attributes by key for efficient two-pointer diffing
        sorted_attrs: list[ScalarAttr] = sorted(self._attrs, key=_attr_sort_key)
        return Widget(
            key=self._key,
            user_key=self._user_key,
            scalar_attrs=tuple(sorted_attrs),
            children=tuple(self._children),
            event_handlers=tuple(self._handlers),
        )

    # ------------------------------------------------------------------
    # Position / Size shortcuts
    # ------------------------------------------------------------------

    def width(self, w: int) -> WidgetBuilder:
        """Set width attribute."""
        return self.set_attr(AttrKey.WIDTH, w)

    def height(self, h: int) -> WidgetBuilder:
        """Set height attribute."""
        return self.set_attr(AttrKey.HEIGHT, h)

    def size(self, w: int, h: int) -> WidgetBuilder:
        """Set width and height in one call."""
        return self.width(w).height(h)

    def pos(self, x: int, y: int) -> WidgetBuilder:
        """Set X and Y position."""
        return self.set_attr(AttrKey.X, x).set_attr(AttrKey.Y, y)

    def align(self, align_value: int, x_ofs: int = 0, y_ofs: int = 0) -> WidgetBuilder:
        """Set alignment with optional offsets."""
        return (
            self.set_attr(AttrKey.ALIGN, align_value)
            .set_attr(AttrKey.ALIGN_X_OFS, x_ofs)
            .set_attr(AttrKey.ALIGN_Y_OFS, y_ofs)
        )

    # ------------------------------------------------------------------
    # Background / Border shortcuts
    # ------------------------------------------------------------------

    def bg_color(self, color: int) -> WidgetBuilder:
        """Set background color (hex integer)."""
        return self.set_attr(AttrKey.BG_COLOR, color)

    def bg_opa(self, opa: int) -> WidgetBuilder:
        """Set background opacity (0-255)."""
        return self.set_attr(AttrKey.BG_OPA, opa)

    def border_color(self, color: int) -> WidgetBuilder:
        """Set border color."""
        return self.set_attr(AttrKey.BORDER_COLOR, color)

    def border_width(self, w: int) -> WidgetBuilder:
        """Set border width."""
        return self.set_attr(AttrKey.BORDER_WIDTH, w)

    def radius(self, r: int) -> WidgetBuilder:
        """Set corner radius."""
        return self.set_attr(AttrKey.RADIUS, r)

    # ------------------------------------------------------------------
    # Padding shortcuts
    # ------------------------------------------------------------------

    def padding(self, top: int, right: int, bottom: int, left: int) -> WidgetBuilder:
        """Set all four padding values."""
        return (
            self.set_attr(AttrKey.PAD_TOP, top)
            .set_attr(AttrKey.PAD_RIGHT, right)
            .set_attr(AttrKey.PAD_BOTTOM, bottom)
            .set_attr(AttrKey.PAD_LEFT, left)
        )

    def pad_row(self, gap: int) -> WidgetBuilder:
        """Set row padding (vertical gap between children in flex layout)."""
        return self.set_attr(AttrKey.PAD_ROW, gap)

    def pad_column(self, gap: int) -> WidgetBuilder:
        """Set column padding (horizontal gap between children in flex layout)."""
        return self.set_attr(AttrKey.PAD_COLUMN, gap)

    # ------------------------------------------------------------------
    # Text shortcuts
    # ------------------------------------------------------------------

    def text(self, value: str) -> WidgetBuilder:
        """Set text content."""
        return self.set_attr(AttrKey.TEXT, value)

    def text_color(self, color: int) -> WidgetBuilder:
        """Set text color."""
        return self.set_attr(AttrKey.TEXT_COLOR, color)

    def text_align(self, align_value: int) -> WidgetBuilder:
        """Set text alignment."""
        return self.set_attr(AttrKey.TEXT_ALIGN, align_value)

    # ------------------------------------------------------------------
    # Shadow shortcuts
    # ------------------------------------------------------------------

    def shadow(self, w: int, color: int, ofs_x: int = 0, ofs_y: int = 0) -> WidgetBuilder:
        """Set shadow properties in one call."""
        return (
            self.set_attr(AttrKey.SHADOW_WIDTH, w)
            .set_attr(AttrKey.SHADOW_COLOR, color)
            .set_attr(AttrKey.SHADOW_OFS_X, ofs_x)
            .set_attr(AttrKey.SHADOW_OFS_Y, ofs_y)
        )

    # ------------------------------------------------------------------
    # Layout shortcuts
    # ------------------------------------------------------------------

    def flex_flow(self, flow: int) -> WidgetBuilder:
        """Set flex layout flow direction."""
        return self.set_attr(AttrKey.FLEX_FLOW, flow)

    def flex_grow(self, grow: int) -> WidgetBuilder:
        """Set flex grow factor."""
        return self.set_attr(AttrKey.FLEX_GROW, grow)

    # ------------------------------------------------------------------
    # Widget-specific shortcuts
    # ------------------------------------------------------------------

    def value(self, v: int) -> WidgetBuilder:
        """Set value (for slider, bar, arc, etc.)."""
        return self.set_attr(AttrKey.VALUE, v)

    def set_range(self, min_val: int, max_val: int) -> WidgetBuilder:
        """Set min/max range (for slider, bar, arc, etc.)."""
        return self.set_attr(AttrKey.MIN_VALUE, min_val).set_attr(AttrKey.MAX_VALUE, max_val)

    def checked(self, state: bool) -> WidgetBuilder:
        """Set checked state (for switch, checkbox)."""
        return self.set_attr(AttrKey.CHECKED, state)


def _attr_sort_key(a: ScalarAttr) -> int:
    """Sort key for ScalarAttr -- used by WidgetBuilder.build()."""
    return a.key
