"""Declarative DSL functions for building LVGL widget trees.

P0 Essential Widgets:
- Screen: Root container (lv_obj_create(None))
- Container: Generic container (lv_obj_create(parent))
- Label: Text display (lv_label_create)
- Button: Clickable button (lv_button_create)

Usage::

    from lvgl_mvu.dsl import Screen, Container, Label, Button

    def view(model: Model) -> Widget:
        return Screen()(
            Label("Counter: " + str(model.count)),
            Button("Increment").on(LV_EVENT_CLICKED, Msg.Increment),
        )
"""

from __future__ import annotations

from lvgl_mvu.attrs import AttrKey
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.widget import WidgetKey

# ---------------------------------------------------------------------------
# P0 Widget DSL Functions
# ---------------------------------------------------------------------------


def Screen() -> WidgetBuilder:
    """Create a screen widget (root container).

    A screen is the top-level container that fills the display.
    It is created with lv_obj_create(None).

    Returns:
        WidgetBuilder configured for SCREEN type.

    Example::

        Screen()(
            Label("Hello"),
            Button("Click me"),
        )
    """
    return WidgetBuilder(WidgetKey.SCREEN)


def Container() -> WidgetBuilder:
    """Create a container widget.

    A container is a generic parent widget for grouping children.
    It is created with lv_obj_create(parent).

    Returns:
        WidgetBuilder configured for CONTAINER type.

    Example::

        Container().size(200, 100).bg_color(0x333333)(
            Label("Grouped"),
        )
    """
    return WidgetBuilder(WidgetKey.CONTAINER)


def Label(text: str) -> WidgetBuilder:
    """Create a label widget with text content.

    A label displays static or dynamic text.
    It is created with lv_label_create(parent).

    Args:
        text: The text content to display.

    Returns:
        WidgetBuilder configured for LABEL type with TEXT attribute set.

    Example::

        Label("Hello World").text_color(0xFFFFFF).build()
    """
    return WidgetBuilder(WidgetKey.LABEL).set_attr(AttrKey.TEXT, text)


def Button(text: str = "") -> WidgetBuilder:
    """Create a button widget with optional text.

    A button is an interactive widget that can respond to clicks.
    It is created with lv_button_create(parent) and optionally
    contains a label child for the button text.

    Args:
        text: Optional button label text. If provided, a label child
              is added automatically.

    Returns:
        WidgetBuilder configured for BUTTON type.

    Example::

        Button("Click me").on(LV_EVENT_CLICKED, Msg.ButtonClicked).build()
    """
    builder = WidgetBuilder(WidgetKey.BUTTON)
    if text != "":
        builder = builder.set_attr(AttrKey.TEXT, text)
    return builder
