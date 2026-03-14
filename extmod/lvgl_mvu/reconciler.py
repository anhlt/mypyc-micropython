"""Reconciler - Bridges Widget trees with ViewNode trees.

The Reconciler is responsible for:
1. Creating new ViewNodes when widgets are added
2. Updating existing ViewNodes when widgets change
3. Disposing ViewNodes when widgets are removed
4. Managing the LVGL object lifecycle

It uses the diff module to compute changes and applies them efficiently.
"""

from typing import Callable

from lvgl_mvu.attrs import AttrRegistry
from lvgl_mvu.diff import (
    CHILD_INSERT,
    CHILD_REMOVE,
    CHILD_REPLACE,
    CHILD_UPDATE,
    ChildChange,
    can_reuse,
    diff_widgets,
)
from lvgl_mvu.viewnode import ViewNode
from lvgl_mvu.widget import Widget

# Type alias for factory functions
WidgetFactory = Callable[[object], object]
DeleteFn = Callable[[object], None]


class Reconciler:
    """Reconciles Widget trees with ViewNode trees.

    The Reconciler maintains:
    - Widget factories: Functions that create LVGL objects for each widget type
    - Delete function: Function to delete LVGL objects during cleanup

    Usage:
        reconciler = Reconciler()
        reconciler.register_factory(WidgetKey.LABEL, create_label)
        reconciler.register_factory(WidgetKey.BUTTON, create_button)
        reconciler.set_delete_fn(delete_lv_obj)

        # First render
        root_node = reconciler.reconcile(None, root_widget, screen_obj)

        # Subsequent updates
        root_node = reconciler.reconcile(root_node, new_widget, screen_obj)
    """

    _factories: dict[int, WidgetFactory]
    _delete_fn: DeleteFn | None
    _event_binder: object | None
    _attr_registry: AttrRegistry

    def __init__(self, attr_registry: AttrRegistry) -> None:
        """Create a new Reconciler.

        Args:
            attr_registry: The attribute registry for looking up AttrDefs.
        """
        self._factories = {}
        self._delete_fn = None
        self._event_binder = None
        self._attr_registry = attr_registry

    def register_factory(self, widget_key: int, factory: WidgetFactory) -> None:
        """Register a factory function for a widget type.

        Args:
            widget_key: The WidgetKey int value.
            factory: A callable (parent_lv_obj) -> lv_obj that creates the widget.
        """
        self._factories[widget_key] = factory

    def set_delete_fn(self, delete_fn: DeleteFn) -> None:
        """Set the function used to delete LVGL objects.

        Args:
            delete_fn: A callable (lv_obj) -> None that deletes the object.
        """
        self._delete_fn = delete_fn

    def set_event_binder(self, binder: object) -> None:
        """Set the event binder for handling widget events.

        Args:
            binder: An object with bind() and unbind() methods.
        """
        self._event_binder = binder

    def reconcile(
        self,
        node: ViewNode | None,
        widget: Widget,
        parent_lv_obj: object | None = None,
    ) -> ViewNode:
        """Reconcile a ViewNode with a Widget.

        This is the main entry point. It will:
        - Create a new node if node is None or widget types don't match
        - Update the existing node if types match

        Args:
            node: The existing ViewNode, or None for first render.
            widget: The new Widget to render.
            parent_lv_obj: The parent LVGL object for new nodes.

        Returns:
            The updated or new ViewNode.
        """
        # Need to create new node?
        if node is None:
            return self._create_node(widget, parent_lv_obj)

        # Check if we can reuse the existing node
        if not can_reuse(node.widget, widget):
            # Widget type or key changed - full replace
            node.dispose(self._delete_fn)
            return self._create_node(widget, parent_lv_obj)

        # Compute diff and apply changes
        diff = diff_widgets(node.widget, widget)
        node.apply_diff(diff)

        # Reconcile children
        self._reconcile_children(node, widget, diff.child_changes)

        # Reconcile event handlers if changed
        if diff.event_changes:
            self._reconcile_handlers(node, widget)

        # Update cached widget
        node.update_widget(widget)

        return node

    def _create_node(self, widget: Widget, parent_lv_obj: object | None) -> ViewNode:
        """Create a new ViewNode for a widget.

        Args:
            widget: The Widget to create a node for.
            parent_lv_obj: The parent LVGL object.

        Returns:
            A new ViewNode wrapping the created LVGL object.

        Raises:
            ValueError: If no factory is registered for the widget type.
        """
        factory = self._factories.get(widget.key)
        if factory is None:
            raise ValueError(f"No factory registered for widget type: {widget.key}")

        # Create LVGL object
        lv_obj = factory(parent_lv_obj)

        # Create ViewNode
        node = ViewNode(lv_obj, widget, self._attr_registry)

        # Apply all initial attributes
        # WORKAROUND: Use index-based while loop instead of for loop.
        # for attr in widget.scalar_attrs: crashes on ESP32-P4 due to
        # struct-cast optimization issue in compiled C code. See docs/known-issues.md
        scalar_attrs = widget.scalar_attrs
        i: int = 0
        while i < len(scalar_attrs):
            attr = scalar_attrs[i]
            attr_def = self._attr_registry.get(attr.key)
            if attr_def is not None:
                attr_def.apply_fn(lv_obj, attr.value)
            i += 1
        # Create child nodes - use while loop to avoid for-loop crash
        children = widget.children
        j: int = 0
        while j < len(children):
            child_widget = children[j]
            child_node = self._create_node(child_widget, lv_obj)
            node.add_child(child_node)
            j += 1
        # Register event handlers
        self._register_handlers(node, widget)

        return node

    def _reconcile_children(
        self,
        node: ViewNode,
        widget: Widget,
        changes: list[ChildChange],
    ) -> None:
        """Apply child changes to a ViewNode.

        Changes must be processed carefully to maintain correct indices.
        We process removals from highest to lowest index, then inserts
        from lowest to highest.

        Args:
            node: The parent ViewNode.
            widget: The new Widget with updated children.
            changes: List of ChildChange operations to apply.
        """
        # Separate changes by type for proper ordering
        removes: list[ChildChange] = []
        inserts: list[ChildChange] = []
        updates: list[ChildChange] = []
        replaces: list[ChildChange] = []

        # Declare variables used across multiple loop iterations
        old_child: ViewNode | None = None
        new_child: ViewNode | None = None

        for change in changes:
            if change.kind == CHILD_REMOVE:
                removes.append(change)
            elif change.kind == CHILD_INSERT:
                inserts.append(change)
            elif change.kind == CHILD_UPDATE:
                updates.append(change)
            elif change.kind == CHILD_REPLACE:
                replaces.append(change)

        # Process updates first (index doesn't change)
        for change in updates:
            if change.diff is not None and change.widget is not None:
                child_node = node.get_child(change.index)
                if child_node is not None:
                    child_node.apply_diff(change.diff)
                    # Recursively reconcile children
                    self._reconcile_children(child_node, change.widget, change.diff.child_changes)
                    if change.diff.event_changes:
                        self._reconcile_handlers(child_node, change.widget)
                    child_node.update_widget(change.widget)

        # Process replaces (same index, but new widget)
        for change in replaces:
            if change.widget is not None:
                old_child = node.remove_child(change.index)
                if old_child is not None:
                    old_child.dispose(self._delete_fn)
                new_child = self._create_node(change.widget, node.lv_obj)
                node.add_child(new_child, change.index)

        # Process removes from highest index to lowest
        removes_sorted = sorted(removes, key=lambda c: c.index, reverse=True)
        for change in removes_sorted:
            old_child = node.remove_child(change.index)
            if old_child is not None:
                old_child.dispose(self._delete_fn)

        # Process inserts from lowest index to highest
        inserts_sorted = sorted(inserts, key=lambda c: c.index)
        for change in inserts_sorted:
            if change.widget is not None:
                new_child = self._create_node(change.widget, node.lv_obj)
                node.add_child(new_child, change.index)

    def _register_handlers(self, node: ViewNode, widget: Widget) -> None:
        """Register event handlers for a widget.

        Args:
            node: The ViewNode to register handlers on.
            widget: The Widget with event handler definitions.
        """
        if self._event_binder is None:
            return

        event_handlers = widget.event_handlers
        eh_idx: int = 0
        while eh_idx < len(event_handlers):
            event_type_msg = event_handlers[eh_idx]
            event_type: int = event_type_msg[0]
            msg: object = event_type_msg[1]

            handler: object
            if isinstance(msg, tuple) and len(msg) == 2:
                tag: object = msg[0]
                msg_fn: object = msg[1]
                if tag == "value":
                    handler = self._event_binder.bind_value(node.lv_obj, event_type, msg_fn)  # type: ignore[attr-defined]
                elif tag == "checked":
                    handler = self._event_binder.bind_checked(node.lv_obj, event_type, msg_fn)  # type: ignore[attr-defined]
                else:
                    handler = self._event_binder.bind(node.lv_obj, event_type, msg)  # type: ignore[attr-defined]
            else:
                handler = self._event_binder.bind(node.lv_obj, event_type, msg)  # type: ignore[attr-defined]

            node.register_handler(event_type, handler)
            eh_idx += 1

    def _reconcile_handlers(self, node: ViewNode, widget: Widget) -> None:
        """Update event handlers on a ViewNode.

        This removes old handlers and registers new ones.

        Args:
            node: The ViewNode to update.
            widget: The Widget with new event handlers.
        """
        if self._event_binder is None:
            # No event binder - just clear handlers
            node.clear_handlers()
            return

        # Unregister old handlers
        old_handlers = node.clear_handlers()
        for event_type, handler in old_handlers.items():
            self._event_binder.unbind(node.lv_obj, event_type, handler)  # type: ignore[attr-defined]

        # Register new handlers
        self._register_handlers(node, widget)

    def dispose_tree(self, node: ViewNode) -> None:
        """Dispose an entire ViewNode tree.

        Args:
            node: The root ViewNode to dispose.
        """
        node.dispose(self._delete_fn)
