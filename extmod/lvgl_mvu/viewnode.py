"""ViewNode - Persistent wrapper around LVGL objects for reconciliation.

A ViewNode represents a live LVGL object in the widget tree. It holds:
- lv_obj: The actual LVGL object reference
- widget: The last Widget snapshot that was applied
- children: List of child ViewNodes
- handlers: Dict of registered event handlers keyed by event type

The ViewNode receives diffs and applies them to the underlying LVGL object,
minimizing LVGL API calls by only updating what changed.
"""

from __future__ import annotations

from typing import Callable

from lvgl_mvu.attrs import AttrDef, get_attr_def_safe
from lvgl_mvu.diff import (
    AttrChange,
    CHANGE_ADDED,
    CHANGE_REMOVED,
    CHANGE_UPDATED,
    WidgetDiff,
)
from lvgl_mvu.widget import Widget

class ViewNode:
    """Persistent wrapper for an LVGL object.

    Attributes:
        lv_obj: The underlying LVGL object (opaque to this module).
        widget: The Widget snapshot that was last applied.
        children: List of child ViewNode instances.
        handlers: Dict mapping event type (int) to handler reference.
        _disposed: Flag indicating if this node has been cleaned up.
    """

    lv_obj: object
    widget: Widget
    children: list[ViewNode]
    handlers: dict[int, object]
    _disposed: bool

    def __init__(self, lv_obj: object, widget: Widget) -> None:
        """Create a ViewNode wrapping an LVGL object.

        Args:
            lv_obj: The LVGL object to wrap.
            widget: The Widget that describes this node's state.
        """
        self.lv_obj = lv_obj
        self.widget = widget
        self.children = []
        self.handlers = {}
        self._disposed = False

    def apply_scalar_change(self, change: AttrChange) -> None:
        """Apply a single scalar attribute change to the LVGL object.

        Args:
            change: The AttrChange describing what to update.

        For REMOVED attributes, we apply the default value.
        For ADDED/UPDATED attributes, we apply the new value.
        """
        if self._disposed:
            return

        # Use safe lookup to avoid try/except
        attr_def: AttrDef | None = get_attr_def_safe(change.key)
        if attr_def is None:
            # Attribute not registered - skip silently
            return

        kind: str = change.kind
        if kind == CHANGE_REMOVED:
            # Reset to default
            attr_def.apply_fn(self.lv_obj, attr_def.default_val)
        elif kind == CHANGE_ADDED or kind == CHANGE_UPDATED:
            attr_def.apply_fn(self.lv_obj, change.new_value)

    def apply_diff(self, diff: WidgetDiff) -> None:
        """Apply all scalar changes from a diff to the LVGL object.

        Note: Child changes are handled by the Reconciler, not here.

        Args:
            diff: The WidgetDiff containing scalar_changes to apply.
        """
        if self._disposed:
            return

        for change in diff.scalar_changes:
            self.apply_scalar_change(change)

    def update_widget(self, widget: Widget) -> None:
        """Update the cached widget snapshot.

        Args:
            widget: The new Widget state.
        """
        self.widget = widget

    def add_child(self, child: ViewNode, index: int = -1) -> None:
        """Add a child ViewNode at the specified index.

        Args:
            child: The ViewNode to add.
            index: Position to insert at. -1 means append.
        """
        if index < 0 or index >= len(self.children):
            self.children.append(child)
        else:
            self.children.insert(index, child)

    def remove_child(self, index: int) -> ViewNode | None:
        """Remove and return the child at the given index.

        Args:
            index: The index to remove from.

        Returns:
            The removed ViewNode, or None if index is invalid.
        """
        if 0 <= index < len(self.children):
            return self.children.pop(index)
        return None

    def get_child(self, index: int) -> ViewNode | None:
        """Get the child at the given index.

        Args:
            index: The index to retrieve.

        Returns:
            The ViewNode at that index, or None if invalid.
        """
        if 0 <= index < len(self.children):
            return self.children[index]
        return None

    def child_count(self) -> int:
        """Return the number of children."""
        return len(self.children)

    def register_handler(self, event_type: int, handler: object) -> None:
        """Register an event handler.

        Args:
            event_type: The LVGL event type (int).
            handler: The handler reference to store.
        """
        self.handlers[event_type] = handler

    def unregister_handler(self, event_type: int) -> object | None:
        """Unregister and return an event handler.

        Args:
            event_type: The LVGL event type.

        Returns:
            The handler that was removed, or None.
        """
        return self.handlers.pop(event_type, None)

    def clear_handlers(self) -> dict[int, object]:
        """Remove all handlers and return them.

        Returns:
            Dict of all handlers that were registered.
        """
        old_handlers = self.handlers
        self.handlers = {}
        return old_handlers

    def dispose(self, delete_fn: Callable[[object], None] | None = None) -> None:
        """Clean up this ViewNode and all children.

        This method:
        1. Recursively disposes all children
        2. Clears all event handlers
        3. Optionally calls delete_fn to delete the LVGL object
        4. Marks this node as disposed

        Args:
            delete_fn: Optional callable (lv_obj) -> None to delete the LVGL object.
        """
        if self._disposed:
            return

        # Dispose children first (depth-first) - use index iteration to avoid temp var conflict
        child_count: int = len(self.children)
        idx: int = 0
        while idx < child_count:
            child_node: ViewNode = self.children[idx]
            child_node.dispose(delete_fn)
            idx += 1

        # Clear collections using assignment instead of .clear()
        self.children = []
        self.handlers = {}

        # Delete LVGL object if callback provided
        if delete_fn is not None:
            delete_fn(self.lv_obj)

        self._disposed = True

    def is_disposed(self) -> bool:
        """Check if this node has been disposed."""
        return self._disposed
