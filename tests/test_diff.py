"""Tests for the LVGL MVU diffing engine (Milestone 2).

Covers:
- Scalar attribute diffing (two-pointer on sorted tuples)
- Child widget diffing (positional)
- can_reuse strategy
- diff_widgets top-level (including prev=None)
- Edge cases: empty trees, identical trees, type changes, user_key handling
"""

from __future__ import annotations

from lvgl_mvu.attrs import AttrKey
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.diff import (
    CHANGE_ADDED,
    CHANGE_REMOVED,
    CHANGE_UPDATED,
    CHILD_INSERT,
    CHILD_REMOVE,
    CHILD_REPLACE,
    CHILD_UPDATE,
    AttrChange,
    WidgetDiff,
    can_reuse,
    diff_children,
    diff_scalars,
    diff_widgets,
)
from lvgl_mvu.widget import ScalarAttr, Widget, WidgetKey

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


def _sa(key: int, value: object) -> ScalarAttr:
    return ScalarAttr(key, value)


# ---------------------------------------------------------------------------
# diff_scalars
# ---------------------------------------------------------------------------


class TestDiffScalars:
    """Two-pointer scalar attribute diffing."""

    def test_identical(self):
        attrs = (_sa(1, "a"), _sa(2, "b"))
        assert diff_scalars(attrs, attrs) == []

    def test_empty_both(self):
        assert diff_scalars((), ()) == []

    def test_all_added(self):
        result = diff_scalars((), (_sa(1, "x"), _sa(5, "y")))
        assert len(result) == 2
        assert result[0].kind == CHANGE_ADDED
        assert result[0].key == 1
        assert result[0].new_value == "x"

    def test_all_removed(self):
        result = diff_scalars((_sa(1, "x"), _sa(5, "y")), ())
        assert len(result) == 2
        assert result[0].kind == CHANGE_REMOVED
        assert result[1].kind == CHANGE_REMOVED

    def test_single_update(self):
        prev = (_sa(AttrKey.TEXT, "old"),)
        next_ = (_sa(AttrKey.TEXT, "new"),)
        result = diff_scalars(prev, next_)
        assert len(result) == 1
        assert result[0].kind == CHANGE_UPDATED
        assert result[0].old_value == "old"
        assert result[0].new_value == "new"

    def test_mixed_add_remove_update(self):
        prev = (_sa(1, "a"), _sa(3, "c"), _sa(5, "e"))
        next_ = (_sa(2, "B"), _sa(3, "C"), _sa(5, "e"))
        result = diff_scalars(prev, next_)
        changes = {(c.kind, c.key): c for c in result}
        assert (CHANGE_REMOVED, 1) in changes
        assert (CHANGE_ADDED, 2) in changes
        assert (CHANGE_UPDATED, 3) in changes
        assert len(result) == 3

    def test_no_false_update_for_equal_values(self):
        prev = (_sa(10, 42), _sa(20, "hello"))
        next_ = (_sa(10, 42), _sa(20, "hello"))
        assert diff_scalars(prev, next_) == []

    def test_interleaved_keys(self):
        prev = (_sa(2, "a"), _sa(4, "b"), _sa(6, "c"))
        next_ = (_sa(1, "x"), _sa(3, "y"), _sa(5, "z"))
        result = diff_scalars(prev, next_)
        assert len(result) == 6
        added = [c for c in result if c.kind == CHANGE_ADDED]
        removed = [c for c in result if c.kind == CHANGE_REMOVED]
        assert len(added) == 3
        assert len(removed) == 3

    def test_large_diff(self):
        prev = tuple(_sa(i, i) for i in range(100))
        next_ = tuple(_sa(i, i if i % 2 == 0 else i + 1000) for i in range(100))
        result = diff_scalars(prev, next_)
        assert len(result) == 50
        assert all(c.kind == CHANGE_UPDATED for c in result)


# ---------------------------------------------------------------------------
# can_reuse
# ---------------------------------------------------------------------------


class TestCanReuse:
    """Widget reuse strategy."""

    def test_same_type_no_keys(self):
        assert can_reuse(_label("a"), _label("b")) is True

    def test_different_type(self):
        assert can_reuse(_label("a"), _button("b")) is False

    def test_same_type_same_user_key(self):
        assert can_reuse(_label("a", user_key="k1"), _label("b", user_key="k1")) is True

    def test_same_type_different_user_key(self):
        assert can_reuse(_label("a", user_key="k1"), _label("b", user_key="k2")) is False

    def test_prev_has_key_next_does_not(self):
        assert can_reuse(_label("a", user_key="k1"), _label("b")) is False

    def test_prev_no_key_next_has_key(self):
        assert can_reuse(_label("a"), _label("b", user_key="k1")) is False

    def test_both_none_keys_same_type(self):
        a = Widget(WidgetKey.CONTAINER, "", (), (), ())
        b = Widget(WidgetKey.CONTAINER, "", (), (), ())
        assert can_reuse(a, b) is True


# ---------------------------------------------------------------------------
# diff_children
# ---------------------------------------------------------------------------


class TestDiffChildren:
    """Positional child diffing."""

    def test_identical_children(self):
        c = _label("same")
        assert diff_children((c,), (c,)) == []

    def test_empty_both(self):
        assert diff_children((), ()) == []

    def test_all_inserted(self):
        a, b = _label("a"), _label("b")
        result = diff_children((), (a, b))
        assert len(result) == 2
        assert result[0].kind == CHILD_INSERT
        assert result[1].kind == CHILD_INSERT

    def test_all_removed(self):
        a, b = _label("a"), _label("b")
        result = diff_children((a, b), ())
        assert len(result) == 2
        assert result[0].kind == CHILD_REMOVE
        assert result[1].kind == CHILD_REMOVE

    def test_child_updated(self):
        prev = (_label("old"),)
        next_ = (_label("new"),)
        result = diff_children(prev, next_)
        assert len(result) == 1
        assert result[0].kind == CHILD_UPDATE
        assert result[0].index == 0
        assert result[0].diff is not None
        text_changes = [c for c in result[0].diff.scalar_changes if c.key == AttrKey.TEXT]
        assert len(text_changes) == 1
        assert text_changes[0].kind == CHANGE_UPDATED

    def test_child_replaced(self):
        prev = (_label("x"),)
        next_ = (_button("y"),)
        result = diff_children(prev, next_)
        assert len(result) == 1
        assert result[0].kind == CHILD_REPLACE

    def test_grow_children(self):
        a = _label("a")
        b = _label("b")
        result = diff_children((a,), (a, b))
        assert len(result) == 1
        assert result[0].kind == CHILD_INSERT
        assert result[0].index == 1

    def test_shrink_children(self):
        a, b = _label("a"), _label("b")
        result = diff_children((a, b), (a,))
        assert len(result) == 1
        assert result[0].kind == CHILD_REMOVE
        assert result[0].index == 1

    def test_replace_in_middle(self):
        a = _label("a")
        b = _label("b")
        c = _button("c")
        result = diff_children((a, b, a), (a, c, a))
        assert len(result) == 1
        assert result[0].kind == CHILD_REPLACE
        assert result[0].index == 1

    def test_user_key_mismatch_causes_replace(self):
        a = _label("a", user_key="k1")
        b = _label("b", user_key="k2")
        result = diff_children((a,), (b,))
        assert len(result) == 1
        assert result[0].kind == CHILD_REPLACE

    def test_no_changes_when_identical(self):
        children = (_label("a"), _button("b"), _label("c"))
        assert diff_children(children, children) == []

    def test_mixed_operations(self):
        a = _label("a")
        b_old = _label("b_old")
        b_new = _label("b_new")
        c = _label("c")
        result = diff_children((a, b_old, c), (a, b_new))
        kinds = [(ch.kind, ch.index) for ch in result]
        assert (CHILD_UPDATE, 1) in kinds
        assert (CHILD_REMOVE, 2) in kinds


# ---------------------------------------------------------------------------
# diff_widgets  (top-level)
# ---------------------------------------------------------------------------


class TestDiffWidgets:
    """Top-level diff_widgets function."""

    def test_prev_none_leaf(self):
        w = _label("hello")
        diff = diff_widgets(None, w)
        assert len(diff.scalar_changes) == 1
        assert diff.scalar_changes[0].kind == CHANGE_ADDED
        assert diff.child_changes == []

    def test_prev_none_with_children(self):
        w = _container(_label("a"), _label("b"))
        diff = diff_widgets(None, w)
        assert len(diff.child_changes) == 2
        assert all(c.kind == CHILD_INSERT for c in diff.child_changes)

    def test_identical_widgets(self):
        w = _label("same")
        diff = diff_widgets(w, w)
        assert diff.is_empty()

    def test_is_empty_method(self):
        diff = WidgetDiff([], [])
        assert diff.is_empty() is True

        diff2 = WidgetDiff([AttrChange(CHANGE_ADDED, 1, None, "x")], [])
        assert diff2.is_empty() is False

    def test_scalar_change_only(self):
        prev = _label("old")
        next_ = _label("new")
        diff = diff_widgets(prev, next_)
        assert len(diff.scalar_changes) == 1
        assert diff.scalar_changes[0].kind == CHANGE_UPDATED
        assert diff.child_changes == []

    def test_child_change_only(self):
        prev = _container(_label("a"))
        next_ = _container(_label("a"), _label("b"))
        diff = diff_widgets(prev, next_)
        assert diff.scalar_changes == []
        assert len(diff.child_changes) == 1
        assert diff.child_changes[0].kind == CHILD_INSERT

    def test_both_scalar_and_child_changes(self):
        prev = WidgetBuilder(WidgetKey.CONTAINER).bg_color(0x000000).add_child(_label("a")).build()
        next_ = (
            WidgetBuilder(WidgetKey.CONTAINER)
            .bg_color(0xFF0000)
            .add_child(_label("a"))
            .add_child(_label("b"))
            .build()
        )
        diff = diff_widgets(prev, next_)
        assert len(diff.scalar_changes) == 1
        assert len(diff.child_changes) == 1

    def test_recursive_diff(self):
        prev = _container(_container(_label("deep_old")))
        next_ = _container(_container(_label("deep_new")))
        diff = diff_widgets(prev, next_)
        assert len(diff.child_changes) == 1
        assert diff.child_changes[0].kind == CHILD_UPDATE
        sub = diff.child_changes[0].diff
        assert sub is not None
        assert len(sub.child_changes) == 1
        assert sub.child_changes[0].kind == CHILD_UPDATE
        leaf = sub.child_changes[0].diff
        assert leaf is not None
        assert len(leaf.scalar_changes) == 1
        assert leaf.scalar_changes[0].old_value == "deep_old"
        assert leaf.scalar_changes[0].new_value == "deep_new"

    def test_event_changes_detected(self):
        prev = WidgetBuilder(WidgetKey.BUTTON).on(1, "click").build()
        next_ = WidgetBuilder(WidgetKey.BUTTON).on(1, "double_click").build()
        diff = diff_widgets(prev, next_)
        assert diff.event_changes is True

    def test_event_no_change(self):
        msg = "click"
        prev = WidgetBuilder(WidgetKey.BUTTON).on(1, msg).build()
        next_ = WidgetBuilder(WidgetKey.BUTTON).on(1, msg).build()
        diff = diff_widgets(prev, next_)
        assert diff.event_changes is False

    def test_prev_none_with_events(self):
        w = WidgetBuilder(WidgetKey.BUTTON).on(1, "click").build()
        diff = diff_widgets(None, w)
        assert diff.event_changes is True

    def test_prev_none_no_events(self):
        w = _label("hi")
        diff = diff_widgets(None, w)
        assert diff.event_changes is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestDiffEdgeCases:
    """Boundary conditions and complex scenarios."""

    def test_empty_to_empty(self):
        prev = WidgetBuilder(WidgetKey.CONTAINER).build()
        next_ = WidgetBuilder(WidgetKey.CONTAINER).build()
        diff = diff_widgets(prev, next_)
        assert diff.is_empty()

    def test_many_children_insert_at_end(self):
        prev_children = tuple(_label(str(i)) for i in range(10))
        next_children = prev_children + (_label("new"),)
        result = diff_children(prev_children, next_children)
        assert len(result) == 1
        assert result[0].kind == CHILD_INSERT
        assert result[0].index == 10

    def test_many_children_remove_from_end(self):
        children = tuple(_label(str(i)) for i in range(10))
        result = diff_children(children, children[:8])
        assert len(result) == 2
        assert all(c.kind == CHILD_REMOVE for c in result)

    def test_completely_different_children(self):
        prev = tuple(_label(str(i)) for i in range(5))
        next_ = tuple(_button(str(i)) for i in range(5))
        result = diff_children(prev, next_)
        assert len(result) == 5
        assert all(c.kind == CHILD_REPLACE for c in result)

    def test_single_attr_added_to_empty(self):
        prev = WidgetBuilder(WidgetKey.LABEL).build()
        next_ = WidgetBuilder(WidgetKey.LABEL).text("hi").build()
        diff = diff_widgets(prev, next_)
        assert len(diff.scalar_changes) == 1
        assert diff.scalar_changes[0].kind == CHANGE_ADDED

    def test_single_attr_removed(self):
        prev = WidgetBuilder(WidgetKey.LABEL).text("hi").build()
        next_ = WidgetBuilder(WidgetKey.LABEL).build()
        diff = diff_widgets(prev, next_)
        assert len(diff.scalar_changes) == 1
        assert diff.scalar_changes[0].kind == CHANGE_REMOVED

    def test_counter_app_update(self):
        def view(count: int) -> Widget:
            return (
                WidgetBuilder(WidgetKey.SCREEN)
                .bg_color(0x000000)
                .add_child(WidgetBuilder(WidgetKey.LABEL).text(f"Count: {count}").build())
                .add_child(WidgetBuilder(WidgetKey.BUTTON).text("+1").on(1, "inc").build())
                .build()
            )

        prev = view(0)
        next_ = view(1)
        diff = diff_widgets(prev, next_)
        assert diff.scalar_changes == []
        assert len(diff.child_changes) == 1
        assert diff.child_changes[0].kind == CHILD_UPDATE
        assert diff.child_changes[0].index == 0
        label_diff = diff.child_changes[0].diff
        assert label_diff is not None
        assert len(label_diff.scalar_changes) == 1
        assert label_diff.scalar_changes[0].old_value == "Count: 0"
        assert label_diff.scalar_changes[0].new_value == "Count: 1"

    def test_form_reorder_is_replace(self):
        a = _label("a")
        b = _button("b")
        result = diff_children((a, b), (b, a))
        assert len(result) == 2
        assert all(c.kind == CHILD_REPLACE for c in result)
