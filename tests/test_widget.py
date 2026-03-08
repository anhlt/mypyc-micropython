"""Tests for the LVGL MVU widget abstraction layer (Milestone 1).

Covers:
- Widget / ScalarAttr / WidgetKey dataclasses
- AttrKey enum, AttrDef registry
- WidgetBuilder fluent API and attribute sorting
"""

from __future__ import annotations

import pytest
from lvgl_mvu.attrs import AttrDef, AttrKey, get_attr_def, register_attr, registered_attrs
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.widget import ScalarAttr, Widget, WidgetKey

# ---------------------------------------------------------------------------
# Widget & ScalarAttr
# ---------------------------------------------------------------------------


class TestWidgetKey:
    """WidgetKey enum basics."""

    def test_enum_values(self):
        assert WidgetKey.SCREEN == 0
        assert WidgetKey.LABEL == 2
        assert WidgetKey.BUTTON == 3
        assert WidgetKey.BUTTONMATRIX == 30

    def test_enum_count(self):
        assert len(WidgetKey) == 31

    def test_int_comparison(self):
        assert WidgetKey.CONTAINER == 1
        assert WidgetKey.SLIDER > WidgetKey.BUTTON


class TestScalarAttr:
    """ScalarAttr frozen dataclass."""

    def test_creation(self):
        attr = ScalarAttr(key=AttrKey.TEXT, value="hello")
        assert attr.key == AttrKey.TEXT
        assert attr.value == "hello"

    def test_frozen(self):
        attr = ScalarAttr(key=AttrKey.WIDTH, value=100)
        with pytest.raises(AttributeError):
            attr.key = AttrKey.HEIGHT  # type: ignore[misc]

    def test_equality(self):
        a = ScalarAttr(key=AttrKey.WIDTH, value=100)
        b = ScalarAttr(key=AttrKey.WIDTH, value=100)
        assert a == b

    def test_inequality_value(self):
        a = ScalarAttr(key=AttrKey.WIDTH, value=100)
        b = ScalarAttr(key=AttrKey.WIDTH, value=200)
        assert a != b

    def test_inequality_key(self):
        a = ScalarAttr(key=AttrKey.WIDTH, value=100)
        b = ScalarAttr(key=AttrKey.HEIGHT, value=100)
        assert a != b


class TestWidget:
    """Widget frozen dataclass."""

    def test_leaf_widget(self):
        w = Widget(
            key=WidgetKey.LABEL,
            user_key="",
            scalar_attrs=(ScalarAttr(AttrKey.TEXT, "hi"),),
            children=(),
            event_handlers=(),
        )
        assert w.key == WidgetKey.LABEL
        assert w.user_key == ""
        assert len(w.scalar_attrs) == 1
        assert w.scalar_attrs[0].value == "hi"
        assert w.children == ()
        assert w.event_handlers == ()

    def test_widget_with_children(self):
        child = Widget(WidgetKey.LABEL, "", (), (), ())
        parent = Widget(WidgetKey.CONTAINER, "", (), (child,), ())
        assert len(parent.children) == 1
        assert parent.children[0].key == WidgetKey.LABEL

    def test_widget_with_user_key(self):
        w = Widget(WidgetKey.BUTTON, "submit-btn", (), (), ())
        assert w.user_key == "submit-btn"

    def test_widget_with_event_handlers(self):
        w = Widget(WidgetKey.BUTTON, "", (), (), ((1, "clicked"),))
        assert len(w.event_handlers) == 1
        assert w.event_handlers[0] == (1, "clicked")

    def test_frozen(self):
        w = Widget(WidgetKey.LABEL, "", (), (), ())
        with pytest.raises(AttributeError):
            w.key = WidgetKey.BUTTON  # type: ignore[misc]

    def test_widget_equality(self):
        attrs = (ScalarAttr(AttrKey.TEXT, "same"),)
        a = Widget(WidgetKey.LABEL, "", attrs, (), ())
        b = Widget(WidgetKey.LABEL, "", attrs, (), ())
        assert a == b

    def test_widget_inequality(self):
        a = Widget(WidgetKey.LABEL, "", (), (), ())
        b = Widget(WidgetKey.BUTTON, "", (), (), ())
        assert a != b

    def test_nested_tree(self):
        leaf = Widget(WidgetKey.LABEL, "", (ScalarAttr(AttrKey.TEXT, "X"),), (), ())
        mid = Widget(WidgetKey.CONTAINER, "", (), (leaf, leaf), ())
        root = Widget(WidgetKey.SCREEN, "", (), (mid,), ())
        assert root.key == WidgetKey.SCREEN
        assert len(root.children) == 1
        assert root.children[0].key == WidgetKey.CONTAINER
        assert len(root.children[0].children) == 2
        assert root.children[0].children[0].scalar_attrs[0].value == "X"


# ---------------------------------------------------------------------------
# Attribute registry
# ---------------------------------------------------------------------------


class TestAttrKey:
    """AttrKey enum ranges and ordering."""

    def test_position_range(self):
        assert AttrKey.X == 0
        assert AttrKey.ALIGN_Y_OFS == 6

    def test_padding_range(self):
        assert AttrKey.PAD_TOP == 20
        assert AttrKey.PAD_COLUMN == 25

    def test_bg_range(self):
        assert AttrKey.BG_COLOR == 40
        assert AttrKey.BG_GRAD_DIR == 43

    def test_text_range(self):
        assert AttrKey.TEXT == 100
        assert AttrKey.TEXT_DECOR == 105

    def test_layout_range(self):
        assert AttrKey.FLEX_FLOW == 120
        assert AttrKey.GRID_CELL_ROW_POS == 128

    def test_widget_specific_range(self):
        assert AttrKey.MIN_VALUE == 140
        assert AttrKey.SELECTED == 147

    def test_keys_are_sorted_within_ranges(self):
        assert AttrKey.X < AttrKey.PAD_TOP
        assert AttrKey.PAD_TOP < AttrKey.BG_COLOR
        assert AttrKey.BG_COLOR < AttrKey.BORDER_COLOR
        assert AttrKey.BORDER_COLOR < AttrKey.SHADOW_WIDTH
        assert AttrKey.SHADOW_WIDTH < AttrKey.TEXT
        assert AttrKey.TEXT < AttrKey.FLEX_FLOW
        assert AttrKey.FLEX_FLOW < AttrKey.MIN_VALUE


class TestAttrRegistry:
    """AttrDef registration and lookup."""

    def test_register_and_get(self):
        def noop(_obj: object, _val: object) -> None:
            pass

        defn = AttrDef(key=AttrKey.WIDTH, name="width", default_val=0, apply_fn=noop)
        register_attr(defn)
        retrieved = get_attr_def(AttrKey.WIDTH)
        assert retrieved is defn
        assert retrieved.name == "width"
        assert retrieved.default_val == 0

    def test_get_unregistered_raises(self):
        with pytest.raises(KeyError):
            get_attr_def(AttrKey.GRID_CELL_ROW_POS)

    def test_register_overwrites(self):
        def fn1(_o: object, _v: object) -> None:
            pass

        def fn2(_o: object, _v: object) -> None:
            pass

        d1 = AttrDef(key=AttrKey.HEIGHT, name="height", default_val=0, apply_fn=fn1)
        d2 = AttrDef(key=AttrKey.HEIGHT, name="height_v2", default_val=10, apply_fn=fn2)
        register_attr(d1)
        register_attr(d2)
        assert get_attr_def(AttrKey.HEIGHT) is d2

    def test_registered_attrs_snapshot(self):
        def noop(_o: object, _v: object) -> None:
            pass

        register_attr(AttrDef(key=AttrKey.BG_COLOR, name="bg_color", default_val=0, apply_fn=noop))
        snap = registered_attrs()
        assert AttrKey.BG_COLOR in snap
        snap.pop(AttrKey.BG_COLOR)
        assert get_attr_def(AttrKey.BG_COLOR).name == "bg_color"

    def test_get_with_raw_int(self):
        def noop(_o: object, _v: object) -> None:
            pass

        register_attr(AttrDef(key=AttrKey.TEXT, name="text", default_val="", apply_fn=noop))
        assert get_attr_def(100).name == "text"

    def test_attr_def_with_compare_fn(self):
        def noop(_o: object, _v: object) -> None:
            pass

        def always_equal(_a: object, _b: object) -> bool:
            return True

        defn = AttrDef(
            key=AttrKey.BORDER_COLOR,
            name="border_color",
            default_val=0,
            apply_fn=noop,
            compare_fn=always_equal,
        )
        register_attr(defn)
        assert get_attr_def(AttrKey.BORDER_COLOR).compare_fn is not None


# ---------------------------------------------------------------------------
# WidgetBuilder
# ---------------------------------------------------------------------------


class TestWidgetBuilder:
    """Fluent builder API."""

    def test_build_leaf(self):
        w = WidgetBuilder(WidgetKey.LABEL).text("hello").build()
        assert w.key == WidgetKey.LABEL
        assert w.user_key == ""
        assert w.children == ()
        assert w.event_handlers == ()
        assert len(w.scalar_attrs) == 1
        assert w.scalar_attrs[0].key == AttrKey.TEXT
        assert w.scalar_attrs[0].value == "hello"

    def test_build_with_children(self):
        child = WidgetBuilder(WidgetKey.LABEL).text("child").build()
        parent = WidgetBuilder(WidgetKey.CONTAINER).add_child(child).build()
        assert len(parent.children) == 1
        assert parent.children[0].key == WidgetKey.LABEL

    def test_multiple_children(self):
        parent = (
            WidgetBuilder(WidgetKey.SCREEN)
            .add_child(WidgetBuilder(WidgetKey.LABEL).text("A").build())
            .add_child(WidgetBuilder(WidgetKey.LABEL).text("B").build())
            .add_child(WidgetBuilder(WidgetKey.BUTTON).text("C").build())
            .build()
        )
        assert len(parent.children) == 3
        assert parent.children[2].key == WidgetKey.BUTTON

    def test_user_key(self):
        w = WidgetBuilder(WidgetKey.BUTTON).user_key("ok-btn").build()
        assert w.user_key == "ok-btn"

    def test_event_handler(self):
        w = WidgetBuilder(WidgetKey.BUTTON).on(1, "clicked").build()
        assert len(w.event_handlers) == 1
        assert w.event_handlers[0] == (1, "clicked")

    def test_on_value_handler(self):
        fn = lambda v: ("slider_changed", v)  # noqa: E731
        w = WidgetBuilder(WidgetKey.SLIDER).on_value(2, fn).build()
        assert w.event_handlers[0][0] == 2
        assert w.event_handlers[0][1] == ("value", fn)

    def test_multiple_event_handlers(self):
        w = WidgetBuilder(WidgetKey.BUTTON).on(1, "click").on(2, "long_press").build()
        assert len(w.event_handlers) == 2


class TestWidgetBuilderAttributeSorting:
    """Attributes must be sorted by key for efficient diffing."""

    def test_attrs_sorted_after_build(self):
        w = (
            WidgetBuilder(WidgetKey.CONTAINER)
            .set_attr(AttrKey.TEXT, "hello")  # key=100
            .set_attr(AttrKey.BG_COLOR, 0xFF0000)  # key=40
            .set_attr(AttrKey.WIDTH, 200)  # key=2
            .build()
        )
        keys = [a.key for a in w.scalar_attrs]
        assert keys == sorted(keys)
        assert keys == [AttrKey.WIDTH, AttrKey.BG_COLOR, AttrKey.TEXT]

    def test_sorted_with_many_attrs(self):
        w = (
            WidgetBuilder(WidgetKey.CONTAINER)
            .set_attr(AttrKey.SHADOW_WIDTH, 5)
            .set_attr(AttrKey.PAD_TOP, 10)
            .set_attr(AttrKey.BORDER_WIDTH, 2)
            .set_attr(AttrKey.X, 0)
            .set_attr(AttrKey.FLEX_FLOW, 1)
            .build()
        )
        keys = [a.key for a in w.scalar_attrs]
        assert keys == sorted(keys)

    def test_duplicate_keys_preserved(self):
        w = (
            WidgetBuilder(WidgetKey.LABEL)
            .set_attr(AttrKey.TEXT, "first")
            .set_attr(AttrKey.TEXT, "second")
            .build()
        )
        assert len(w.scalar_attrs) == 2
        assert all(a.key == AttrKey.TEXT for a in w.scalar_attrs)


class TestWidgetBuilderShortcuts:
    """Shortcut methods for common attributes."""

    def test_width_height(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).width(100).height(50).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.WIDTH] == 100
        assert attrs[AttrKey.HEIGHT] == 50

    def test_size(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).size(320, 240).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.WIDTH] == 320
        assert attrs[AttrKey.HEIGHT] == 240

    def test_pos(self):
        w = WidgetBuilder(WidgetKey.LABEL).pos(10, 20).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.X] == 10
        assert attrs[AttrKey.Y] == 20

    def test_align(self):
        w = WidgetBuilder(WidgetKey.LABEL).align(5, x_ofs=10, y_ofs=-20).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.ALIGN] == 5
        assert attrs[AttrKey.ALIGN_X_OFS] == 10
        assert attrs[AttrKey.ALIGN_Y_OFS] == -20

    def test_align_defaults(self):
        w = WidgetBuilder(WidgetKey.LABEL).align(9).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.ALIGN_X_OFS] == 0
        assert attrs[AttrKey.ALIGN_Y_OFS] == 0

    def test_bg_color(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).bg_color(0x00FF00).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.BG_COLOR] == 0x00FF00

    def test_bg_opa(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).bg_opa(128).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.BG_OPA] == 128

    def test_border(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).border_color(0xFF).border_width(2).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.BORDER_COLOR] == 0xFF
        assert attrs[AttrKey.BORDER_WIDTH] == 2

    def test_radius(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).radius(8).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.RADIUS] == 8

    def test_padding(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).padding(10, 20, 30, 40).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.PAD_TOP] == 10
        assert attrs[AttrKey.PAD_RIGHT] == 20
        assert attrs[AttrKey.PAD_BOTTOM] == 30
        assert attrs[AttrKey.PAD_LEFT] == 40

    def test_pad_row_column(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).pad_row(5).pad_column(10).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.PAD_ROW] == 5
        assert attrs[AttrKey.PAD_COLUMN] == 10

    def test_text(self):
        w = WidgetBuilder(WidgetKey.LABEL).text("hello world").build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.TEXT] == "hello world"

    def test_text_color(self):
        w = WidgetBuilder(WidgetKey.LABEL).text_color(0xFF0000).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.TEXT_COLOR] == 0xFF0000

    def test_text_align(self):
        w = WidgetBuilder(WidgetKey.LABEL).text_align(1).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.TEXT_ALIGN] == 1

    def test_shadow(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).shadow(10, 0x333333, ofs_x=2, ofs_y=4).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.SHADOW_WIDTH] == 10
        assert attrs[AttrKey.SHADOW_COLOR] == 0x333333
        assert attrs[AttrKey.SHADOW_OFS_X] == 2
        assert attrs[AttrKey.SHADOW_OFS_Y] == 4

    def test_flex_flow(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).flex_flow(1).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.FLEX_FLOW] == 1

    def test_flex_grow(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).flex_grow(2).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.FLEX_GROW] == 2

    def test_value(self):
        w = WidgetBuilder(WidgetKey.SLIDER).value(50).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.VALUE] == 50

    def test_range(self):
        w = WidgetBuilder(WidgetKey.SLIDER).set_range(0, 100).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.MIN_VALUE] == 0
        assert attrs[AttrKey.MAX_VALUE] == 100

    def test_checked(self):
        w = WidgetBuilder(WidgetKey.SWITCH).checked(True).build()
        attrs = {a.key: a.value for a in w.scalar_attrs}
        assert attrs[AttrKey.CHECKED] is True


class TestWidgetBuilderCombined:
    """Integration tests combining multiple builder features."""

    def test_counter_screen(self):
        label = (
            WidgetBuilder(WidgetKey.LABEL)
            .text("Counter: 0")
            .text_color(0xFFFFFF)
            .align(9, y_ofs=-40)
            .build()
        )
        btn = (
            WidgetBuilder(WidgetKey.BUTTON)
            .text("+1")
            .size(100, 50)
            .align(9, y_ofs=20)
            .on(1, "increment")
            .build()
        )
        screen = (
            WidgetBuilder(WidgetKey.SCREEN)
            .bg_color(0x000000)
            .add_child(label)
            .add_child(btn)
            .build()
        )
        assert screen.key == WidgetKey.SCREEN
        assert len(screen.children) == 2
        assert screen.children[0].key == WidgetKey.LABEL
        assert screen.children[1].key == WidgetKey.BUTTON
        assert screen.children[1].event_handlers == ((1, "increment"),)

    def test_settings_form(self):
        form = (
            WidgetBuilder(WidgetKey.CONTAINER)
            .size(300, 400)
            .padding(10, 10, 10, 10)
            .add_child(WidgetBuilder(WidgetKey.LABEL).text("Brightness").build())
            .add_child(WidgetBuilder(WidgetKey.SLIDER).set_range(0, 100).value(75).build())
            .add_child(WidgetBuilder(WidgetKey.LABEL).text("Dark Mode").build())
            .add_child(WidgetBuilder(WidgetKey.SWITCH).checked(False).build())
            .build()
        )
        assert form.key == WidgetKey.CONTAINER
        assert len(form.children) == 4
        slider = form.children[1]
        slider_keys = [a.key for a in slider.scalar_attrs]
        assert slider_keys == sorted(slider_keys)

    def test_empty_widget(self):
        w = WidgetBuilder(WidgetKey.CONTAINER).build()
        assert w.scalar_attrs == ()
        assert w.children == ()
        assert w.event_handlers == ()
        assert w.user_key == ""

    def test_all_shortcut_attrs_sort_correctly(self):
        w = (
            WidgetBuilder(WidgetKey.CONTAINER)
            .value(42)
            .text("hello")
            .shadow(5, 0, 1, 2)
            .border_width(1)
            .bg_color(0x000000)
            .padding(1, 2, 3, 4)
            .size(100, 50)
            .pos(10, 20)
            .build()
        )
        keys = [a.key for a in w.scalar_attrs]
        assert keys == sorted(keys), f"Attrs not sorted: {keys}"
