"""Widget factory functions for creating LVGL objects.

This module provides factory functions that create actual LVGL objects
for each widget type. These factories are registered with the Reconciler.

Each factory takes a parent LVGL object and returns the created widget.
The reconciler calls these when creating new ViewNodes.

Usage::

    from lvgl_mvu.factories import register_p0_factories

    reconciler = Reconciler(attr_registry)
    register_p0_factories(reconciler)
"""

from __future__ import annotations

import lvgl as lv

from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.widget import WidgetKey

# ---------------------------------------------------------------------------
# Factory Functions for P0 Widgets
# ---------------------------------------------------------------------------


def create_screen(parent: object) -> object:
    """Create a screen (root container).

    A screen is created with lv_obj_create(None), ignoring the parent.

    Args:
        parent: Ignored for screens.

    Returns:
        New LVGL screen object.
    """
    return lv.lv_obj_create(None)


def create_container(parent: object) -> object:
    """Create a container widget.

    A container is a generic lv_obj used for grouping children.

    Args:
        parent: Parent LVGL object.

    Returns:
        New LVGL container object.
    """
    return lv.lv_obj_create(parent)


def create_label(parent: object) -> object:
    """Create a label widget.

    Args:
        parent: Parent LVGL object.

    Returns:
        New LVGL label object.
    """
    return lv.lv_label_create(parent)


def create_button(parent: object) -> object:
    """Create a button widget.

    Note: Button text is set via the TEXT attribute, which creates
    a child label automatically.

    Args:
        parent: Parent LVGL object.

    Returns:
        New LVGL button object.
    """
    return lv.lv_button_create(parent)


# ---------------------------------------------------------------------------
# Factory Functions for P1 Widgets (Interactive)
# ---------------------------------------------------------------------------


def create_slider(parent: object) -> object:
    """Create a slider widget."""
    return lv.lv_slider_create(parent)


def create_bar(parent: object) -> object:
    """Create a progress bar widget."""
    return lv.lv_bar_create(parent)


def create_arc(parent: object) -> object:
    """Create an arc widget."""
    return lv.lv_arc_create(parent)


def create_switch(parent: object) -> object:
    """Create a switch widget."""
    return lv.lv_switch_create(parent)


def create_checkbox(parent: object) -> object:
    """Create a checkbox widget."""
    return lv.lv_checkbox_create(parent)


# ---------------------------------------------------------------------------
# Factory Registration
# ---------------------------------------------------------------------------


def register_p0_factories(reconciler: Reconciler) -> None:
    """Register all P0 widget factories with the reconciler.

    This should be called during app initialization to enable
    creation of Screen, Container, Label, and Button widgets.

    Args:
        reconciler: The Reconciler instance to register factories with.

    Example::

        from lvgl_mvu.factories import register_p0_factories

        reconciler = Reconciler(attr_registry)
        register_p0_factories(reconciler)
    """
    reconciler.register_factory(WidgetKey.SCREEN, create_screen)
    reconciler.register_factory(WidgetKey.CONTAINER, create_container)
    reconciler.register_factory(WidgetKey.LABEL, create_label)
    reconciler.register_factory(WidgetKey.BUTTON, create_button)


def register_p1_factories(reconciler: Reconciler) -> None:
    """Register P1 widget factories (interactive widgets)."""
    reconciler.register_factory(WidgetKey.SLIDER, create_slider)
    reconciler.register_factory(WidgetKey.BAR, create_bar)
    reconciler.register_factory(WidgetKey.ARC, create_arc)
    reconciler.register_factory(WidgetKey.SWITCH, create_switch)
    reconciler.register_factory(WidgetKey.CHECKBOX, create_checkbox)


def register_all_factories(reconciler: Reconciler) -> None:
    """Register all widget factories (P0 + P1)."""
    register_p0_factories(reconciler)
    register_p1_factories(reconciler)


def delete_lv_obj(lv_obj: object) -> None:
    """Delete an LVGL object.

    This is the delete function to pass to the reconciler for cleanup.

    Args:
        lv_obj: The LVGL object to delete.
    """
    lv.lv_obj_delete(lv_obj)
