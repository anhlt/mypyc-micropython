"""Tests for the LVGL MVU ViewNode and Reconciler (Milestone 3).

Covers:
- ViewNode creation and lifecycle
- apply_diff for scalar attribute changes
- Child management (add/remove/get)
- Event handler registration
- Reconciler widget factories
- Full tree reconciliation
- Child insertion, removal, update, replacement
- LVGL object lifecycle management
"""

from __future__ import annotations

import pytest
from lvgl_mvu.attrs import AttrDef, AttrKey, register_attr
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.diff import (
    CHANGE_ADDED,
    CHANGE_REMOVED,
    CHANGE_UPDATED,
    AttrChange,
    WidgetDiff,
)
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.viewnode import ViewNode
from lvgl_mvu.widget import Widget, WidgetKey

# ---------------------------------------------------------------------------
# Mock LVGL Objects
# ---------------------------------------------------------------------------


class MockLvObj:
    """Mock LVGL object for testing."""

    obj_id: int
    parent: MockLvObj | None
    deleted: bool
    attrs: dict[int, object]

    _next_id: int = 0

    def __init__(self, parent: MockLvObj | None = None) -> None:
        MockLvObj._next_id += 1
        self.obj_id = MockLvObj._next_id
        self.parent = parent
        self.deleted = False
        self.attrs = {}

    def __repr__(self) -> str:
        return f"MockLvObj({self.obj_id})"


def mock_delete(obj: object) -> None:
    """Mock delete function."""
    if isinstance(obj, MockLvObj):
        obj.deleted = True


# ---------------------------------------------------------------------------
# Test Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_mock_id():
    """Reset mock object ID counter between tests."""
    MockLvObj._next_id = 0


@pytest.fixture
def register_mock_attrs():
    """Register mock attribute definitions for testing."""

    def mock_apply_text(obj: object, value: object) -> None:
        if isinstance(obj, MockLvObj):
            obj.attrs[AttrKey.TEXT] = value

    def mock_apply_bg_color(obj: object, value: object) -> None:
        if isinstance(obj, MockLvObj):
            obj.attrs[AttrKey.BG_COLOR] = value

    def mock_apply_width(obj: object, value: object) -> None:
        if isinstance(obj, MockLvObj):
            obj.attrs[AttrKey.WIDTH] = value

    register_attr(AttrDef(AttrKey.TEXT, "text", "", mock_apply_text))
    register_attr(AttrDef(AttrKey.BG_COLOR, "bg_color", 0, mock_apply_bg_color))
    register_attr(AttrDef(AttrKey.WIDTH, "width", 0, mock_apply_width))


@pytest.fixture
def reconciler():
    """Create a Reconciler with mock factories."""
    rec = Reconciler()

    def create_screen(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_container(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_label(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_button(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    rec.register_factory(WidgetKey.SCREEN, create_screen)
    rec.register_factory(WidgetKey.CONTAINER, create_container)
    rec.register_factory(WidgetKey.LABEL, create_label)
    rec.register_factory(WidgetKey.BUTTON, create_button)
    rec.set_delete_fn(mock_delete)

    return rec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _label(text: str = "", user_key: str = "") -> Widget:
    b = WidgetBuilder(WidgetKey.LABEL).text(text)
    if user_key != "":
        b = b.user_key(user_key)
    return b.build()


def _button(text: str = "", user_key: str = "") -> Widget:
    b = WidgetBuilder(WidgetKey.BUTTON).text(text)
    if user_key != "":
        b = b.user_key(user_key)
    return b.build()


def _container(*children: Widget) -> Widget:
    b = WidgetBuilder(WidgetKey.CONTAINER)
    for c in children:
        b = b.add_child(c)
    return b.build()


def _screen(*children: Widget) -> Widget:
    b = WidgetBuilder(WidgetKey.SCREEN)
    for c in children:
        b = b.add_child(c)
    return b.build()


# ---------------------------------------------------------------------------
# ViewNode Tests
# ---------------------------------------------------------------------------


class TestViewNodeCreation:
    """ViewNode instantiation and basic properties."""

    def test_create_viewnode(self):
        lv_obj = MockLvObj()
        widget = _label("test")
        node = ViewNode(lv_obj, widget)

        assert node.lv_obj is lv_obj
        assert node.widget is widget
        assert node.children == []
        assert node.handlers == {}
        assert not node.is_disposed()

    def test_viewnode_stores_widget(self):
        lv_obj = MockLvObj()
        widget = _label("hello")
        node = ViewNode(lv_obj, widget)

        assert node.widget.key == WidgetKey.LABEL


class TestViewNodeApplyDiff:
    """ViewNode.apply_diff for scalar changes."""

    def test_apply_added_attr(self, register_mock_attrs):
        lv_obj = MockLvObj()
        widget = _label()
        node = ViewNode(lv_obj, widget)

        diff = WidgetDiff(
            scalar_changes=[AttrChange(CHANGE_ADDED, AttrKey.TEXT, None, "hello")],
            child_changes=[],
        )
        node.apply_diff(diff)

        assert lv_obj.attrs.get(AttrKey.TEXT) == "hello"

    def test_apply_updated_attr(self, register_mock_attrs):
        lv_obj = MockLvObj()
        lv_obj.attrs[AttrKey.TEXT] = "old"
        widget = _label("old")
        node = ViewNode(lv_obj, widget)

        diff = WidgetDiff(
            scalar_changes=[AttrChange(CHANGE_UPDATED, AttrKey.TEXT, "old", "new")],
            child_changes=[],
        )
        node.apply_diff(diff)

        assert lv_obj.attrs.get(AttrKey.TEXT) == "new"

    def test_apply_removed_attr(self, register_mock_attrs):
        lv_obj = MockLvObj()
        lv_obj.attrs[AttrKey.TEXT] = "hello"
        widget = _label("hello")
        node = ViewNode(lv_obj, widget)

        diff = WidgetDiff(
            scalar_changes=[AttrChange(CHANGE_REMOVED, AttrKey.TEXT, "hello", None)],
            child_changes=[],
        )
        node.apply_diff(diff)

        # Should reset to default (empty string)
        assert lv_obj.attrs.get(AttrKey.TEXT) == ""

    def test_apply_multiple_changes(self, register_mock_attrs):
        lv_obj = MockLvObj()
        widget = _label()
        node = ViewNode(lv_obj, widget)

        diff = WidgetDiff(
            scalar_changes=[
                AttrChange(CHANGE_ADDED, AttrKey.TEXT, None, "hello"),
                AttrChange(CHANGE_ADDED, AttrKey.BG_COLOR, None, 0xFF0000),
            ],
            child_changes=[],
        )
        node.apply_diff(diff)

        assert lv_obj.attrs.get(AttrKey.TEXT) == "hello"
        assert lv_obj.attrs.get(AttrKey.BG_COLOR) == 0xFF0000

    def test_apply_diff_skips_unregistered_attrs(self):
        lv_obj = MockLvObj()
        widget = _label()
        node = ViewNode(lv_obj, widget)

        # Use an attr key that's not registered
        diff = WidgetDiff(
            scalar_changes=[AttrChange(CHANGE_ADDED, AttrKey.SHADOW_OPA, None, 128)],
            child_changes=[],
        )
        # Should not raise
        node.apply_diff(diff)


class TestViewNodeChildren:
    """ViewNode child management."""

    def test_add_child(self):
        parent = ViewNode(MockLvObj(), _container())
        child = ViewNode(MockLvObj(), _label())

        parent.add_child(child)

        assert parent.child_count() == 1
        assert parent.get_child(0) is child

    def test_add_multiple_children(self):
        parent = ViewNode(MockLvObj(), _container())
        c1 = ViewNode(MockLvObj(), _label("a"))
        c2 = ViewNode(MockLvObj(), _label("b"))
        c3 = ViewNode(MockLvObj(), _label("c"))

        parent.add_child(c1)
        parent.add_child(c2)
        parent.add_child(c3)

        assert parent.child_count() == 3
        assert parent.get_child(0) is c1
        assert parent.get_child(1) is c2
        assert parent.get_child(2) is c3

    def test_add_child_at_index(self):
        parent = ViewNode(MockLvObj(), _container())
        c1 = ViewNode(MockLvObj(), _label("a"))
        c2 = ViewNode(MockLvObj(), _label("b"))
        c3 = ViewNode(MockLvObj(), _label("c"))

        parent.add_child(c1)
        parent.add_child(c3)
        parent.add_child(c2, index=1)

        assert parent.get_child(0) is c1
        assert parent.get_child(1) is c2
        assert parent.get_child(2) is c3

    def test_remove_child(self):
        parent = ViewNode(MockLvObj(), _container())
        child = ViewNode(MockLvObj(), _label())
        parent.add_child(child)

        removed = parent.remove_child(0)

        assert removed is child
        assert parent.child_count() == 0

    def test_remove_child_from_middle(self):
        parent = ViewNode(MockLvObj(), _container())
        c1 = ViewNode(MockLvObj(), _label("a"))
        c2 = ViewNode(MockLvObj(), _label("b"))
        c3 = ViewNode(MockLvObj(), _label("c"))
        parent.add_child(c1)
        parent.add_child(c2)
        parent.add_child(c3)

        removed = parent.remove_child(1)

        assert removed is c2
        assert parent.child_count() == 2
        assert parent.get_child(0) is c1
        assert parent.get_child(1) is c3

    def test_remove_child_invalid_index(self):
        parent = ViewNode(MockLvObj(), _container())
        assert parent.remove_child(0) is None
        assert parent.remove_child(-1) is None

    def test_get_child_invalid_index(self):
        parent = ViewNode(MockLvObj(), _container())
        assert parent.get_child(0) is None
        assert parent.get_child(-1) is None


class TestViewNodeHandlers:
    """ViewNode event handler management."""

    def test_register_handler(self):
        node = ViewNode(MockLvObj(), _button())
        handler = object()

        node.register_handler(1, handler)

        assert node.handlers.get(1) is handler

    def test_unregister_handler(self):
        node = ViewNode(MockLvObj(), _button())
        handler = object()
        node.register_handler(1, handler)

        removed = node.unregister_handler(1)

        assert removed is handler
        assert 1 not in node.handlers

    def test_unregister_nonexistent_handler(self):
        node = ViewNode(MockLvObj(), _button())
        assert node.unregister_handler(999) is None

    def test_clear_handlers(self):
        node = ViewNode(MockLvObj(), _button())
        h1, h2 = object(), object()
        node.register_handler(1, h1)
        node.register_handler(2, h2)

        old = node.clear_handlers()

        assert old == {1: h1, 2: h2}
        assert node.handlers == {}


class TestViewNodeDispose:
    """ViewNode disposal and cleanup."""

    def test_dispose_marks_disposed(self):
        lv_obj = MockLvObj()
        node = ViewNode(lv_obj, _label())

        node.dispose()

        assert node.is_disposed()

    def test_dispose_calls_delete_fn(self):
        lv_obj = MockLvObj()
        node = ViewNode(lv_obj, _label())

        node.dispose(mock_delete)

        assert lv_obj.deleted

    def test_dispose_children_recursively(self):
        parent_obj = MockLvObj()
        child1_obj = MockLvObj(parent_obj)
        child2_obj = MockLvObj(parent_obj)

        parent = ViewNode(parent_obj, _container())
        child1 = ViewNode(child1_obj, _label("a"))
        child2 = ViewNode(child2_obj, _label("b"))
        parent.add_child(child1)
        parent.add_child(child2)

        parent.dispose(mock_delete)

        assert parent.is_disposed()
        assert child1.is_disposed()
        assert child2.is_disposed()
        assert parent_obj.deleted
        assert child1_obj.deleted
        assert child2_obj.deleted

    def test_dispose_clears_handlers(self):
        node = ViewNode(MockLvObj(), _button())
        node.register_handler(1, object())

        node.dispose()

        assert node.handlers == {}

    def test_dispose_idempotent(self):
        lv_obj = MockLvObj()
        node = ViewNode(lv_obj, _label())

        node.dispose(mock_delete)
        node.dispose(mock_delete)  # Should not raise

        assert node.is_disposed()

    def test_disposed_node_ignores_apply_diff(self, register_mock_attrs):
        lv_obj = MockLvObj()
        node = ViewNode(lv_obj, _label())
        node.dispose()

        diff = WidgetDiff(
            scalar_changes=[AttrChange(CHANGE_ADDED, AttrKey.TEXT, None, "hello")],
            child_changes=[],
        )
        node.apply_diff(diff)

        # Should not have applied - attr was not set
        assert AttrKey.TEXT not in lv_obj.attrs


# ---------------------------------------------------------------------------
# Reconciler Tests
# ---------------------------------------------------------------------------


class TestReconcilerFactories:
    """Reconciler factory registration."""

    def test_register_factory(self):
        rec = Reconciler()

        def factory(parent: object | None) -> MockLvObj:
            return MockLvObj()

        rec.register_factory(WidgetKey.LABEL, factory)
        # No assertion - just verify no error

    def test_reconcile_without_factory_raises(self):
        rec = Reconciler()
        widget = _label("test")

        with pytest.raises(ValueError, match="No factory"):
            rec.reconcile(None, widget, None)


class TestReconcilerCreateNode:
    """Reconciler creating new nodes."""

    def test_create_leaf_node(self, reconciler, register_mock_attrs):
        widget = _label("hello")

        node = reconciler.reconcile(None, widget, None)

        assert node is not None
        assert isinstance(node.lv_obj, MockLvObj)
        assert node.widget is widget
        assert node.lv_obj.attrs.get(AttrKey.TEXT) == "hello"

    def test_create_node_with_parent(self, reconciler, register_mock_attrs):
        parent_obj = MockLvObj()
        widget = _label("child")

        node = reconciler.reconcile(None, widget, parent_obj)

        assert node.lv_obj.parent is parent_obj

    def test_create_node_with_children(self, reconciler, register_mock_attrs):
        widget = _container(_label("a"), _label("b"))

        node = reconciler.reconcile(None, widget, None)

        assert node.child_count() == 2
        assert node.get_child(0) is not None
        assert node.get_child(1) is not None

    def test_create_nested_tree(self, reconciler, register_mock_attrs):
        widget = _screen(_container(_label("deep")))

        node = reconciler.reconcile(None, widget, None)

        assert node.child_count() == 1
        container = node.get_child(0)
        assert container is not None
        assert container.child_count() == 1
        label = container.get_child(0)
        assert label is not None
        assert label.widget.key == WidgetKey.LABEL


class TestReconcilerUpdateNode:
    """Reconciler updating existing nodes."""

    def test_update_scalar_attr(self, reconciler, register_mock_attrs):
        widget1 = _label("old")
        node = reconciler.reconcile(None, widget1, None)

        widget2 = _label("new")
        node = reconciler.reconcile(node, widget2, None)

        assert node.lv_obj.attrs.get(AttrKey.TEXT) == "new"

    def test_update_preserves_lv_obj(self, reconciler, register_mock_attrs):
        widget1 = _label("old")
        node = reconciler.reconcile(None, widget1, None)
        original_obj = node.lv_obj

        widget2 = _label("new")
        node = reconciler.reconcile(node, widget2, None)

        assert node.lv_obj is original_obj

    def test_update_widget_reference(self, reconciler, register_mock_attrs):
        widget1 = _label("old")
        node = reconciler.reconcile(None, widget1, None)

        widget2 = _label("new")
        node = reconciler.reconcile(node, widget2, None)

        assert node.widget is widget2


class TestReconcilerChildReconciliation:
    """Reconciler child add/remove/update operations."""

    def test_add_child(self, reconciler, register_mock_attrs):
        widget1 = _container(_label("a"))
        node = reconciler.reconcile(None, widget1, None)
        assert node.child_count() == 1

        widget2 = _container(_label("a"), _label("b"))
        node = reconciler.reconcile(node, widget2, None)

        assert node.child_count() == 2

    def test_remove_child(self, reconciler, register_mock_attrs):
        widget1 = _container(_label("a"), _label("b"))
        node = reconciler.reconcile(None, widget1, None)
        child_b_obj = node.get_child(1).lv_obj

        widget2 = _container(_label("a"))
        node = reconciler.reconcile(node, widget2, None)

        assert node.child_count() == 1
        assert child_b_obj.deleted

    def test_update_child(self, reconciler, register_mock_attrs):
        widget1 = _container(_label("old"))
        node = reconciler.reconcile(None, widget1, None)
        child_obj = node.get_child(0).lv_obj

        widget2 = _container(_label("new"))
        node = reconciler.reconcile(node, widget2, None)

        assert node.child_count() == 1
        assert node.get_child(0).lv_obj is child_obj  # Same object reused
        assert child_obj.attrs.get(AttrKey.TEXT) == "new"

    def test_replace_child_different_type(self, reconciler, register_mock_attrs):
        widget1 = _container(_label("text"))
        node = reconciler.reconcile(None, widget1, None)
        old_child_obj = node.get_child(0).lv_obj

        widget2 = _container(_button("click"))
        node = reconciler.reconcile(node, widget2, None)

        assert node.child_count() == 1
        new_child = node.get_child(0)
        assert new_child.widget.key == WidgetKey.BUTTON
        assert new_child.lv_obj is not old_child_obj
        assert old_child_obj.deleted

    def test_replace_child_different_user_key(self, reconciler, register_mock_attrs):
        widget1 = _container(_label("a", user_key="key1"))
        node = reconciler.reconcile(None, widget1, None)
        old_child_obj = node.get_child(0).lv_obj

        widget2 = _container(_label("a", user_key="key2"))
        node = reconciler.reconcile(node, widget2, None)

        assert node.get_child(0).lv_obj is not old_child_obj
        assert old_child_obj.deleted


class TestReconcilerReplaceRoot:
    """Reconciler replacing root node on type change."""

    def test_replace_root_different_type(self, reconciler, register_mock_attrs):
        widget1 = _label("label")
        node = reconciler.reconcile(None, widget1, None)
        old_obj = node.lv_obj

        widget2 = _button("button")
        node = reconciler.reconcile(node, widget2, None)

        assert node.lv_obj is not old_obj
        assert node.widget.key == WidgetKey.BUTTON
        assert old_obj.deleted

    def test_replace_root_different_user_key(self, reconciler, register_mock_attrs):
        widget1 = _label("a", user_key="k1")
        node = reconciler.reconcile(None, widget1, None)
        old_obj = node.lv_obj

        widget2 = _label("a", user_key="k2")
        node = reconciler.reconcile(node, widget2, None)

        assert node.lv_obj is not old_obj
        assert old_obj.deleted


class TestReconcilerDisposeTree:
    """Reconciler.dispose_tree for cleanup."""

    def test_dispose_tree(self, reconciler, register_mock_attrs):
        widget = _container(_label("a"), _label("b"))
        node = reconciler.reconcile(None, widget, None)

        reconciler.dispose_tree(node)

        assert node.is_disposed()
        assert node.get_child(0) is None  # Children cleared


class TestReconcilerIntegration:
    """Full reconciliation scenarios."""

    def test_counter_app_update(self, reconciler, register_mock_attrs):
        """Simulate counter app: update label text."""

        def view(count: int) -> Widget:
            return _screen(_label(f"Count: {count}"))

        # Initial render
        node = reconciler.reconcile(None, view(0), None)
        label = node.get_child(0)
        assert label.lv_obj.attrs.get(AttrKey.TEXT) == "Count: 0"

        # Update
        node = reconciler.reconcile(node, view(1), None)
        assert node.get_child(0).lv_obj.attrs.get(AttrKey.TEXT) == "Count: 1"

    def test_list_grow_shrink(self, reconciler, register_mock_attrs):
        """Simulate list that grows and shrinks."""

        def view(items: list[str]) -> Widget:
            children = [_label(item) for item in items]
            b = WidgetBuilder(WidgetKey.CONTAINER)
            for c in children:
                b = b.add_child(c)
            return b.build()

        # Start with 2 items
        node = reconciler.reconcile(None, view(["a", "b"]), None)
        assert node.child_count() == 2

        # Grow to 4
        node = reconciler.reconcile(node, view(["a", "b", "c", "d"]), None)
        assert node.child_count() == 4

        # Shrink to 1
        node = reconciler.reconcile(node, view(["a"]), None)
        assert node.child_count() == 1

    def test_complex_nested_update(self, reconciler, register_mock_attrs):
        """Complex nested structure with multiple changes."""
        widget1 = _screen(
            _container(_label("header")),
            _container(_label("item1"), _label("item2")),
        )
        node = reconciler.reconcile(None, widget1, None)

        # Change header and add item
        widget2 = _screen(
            _container(_label("NEW HEADER")),
            _container(_label("item1"), _label("item2"), _label("item3")),
        )
        node = reconciler.reconcile(node, widget2, None)

        header_container = node.get_child(0)
        header_label = header_container.get_child(0)
        assert header_label.lv_obj.attrs.get(AttrKey.TEXT) == "NEW HEADER"

        items_container = node.get_child(1)
        assert items_container.child_count() == 3
