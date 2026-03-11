"""P0 Widget tests for LVGL MVU framework. Runs directly on MicroPython.

Usage: mpremote connect /dev/cu.usbmodem101 run run_mvu_p0_tests.py

Tests the P0 widgets (Screen, Container, Label, Button) and the MVU
architecture with declarative DSL.
"""

import gc
import time

_total = 0
_passed = 0
_failed = 0


def t(name, got, expected):
    global _total, _passed, _failed
    _total += 1
    sg = str(got)
    if expected in sg:
        _passed += 1
        print("  OK: " + name)
    else:
        _failed += 1
        print("FAIL: " + name + " | got: " + sg[:100] + " | expected: " + expected)


def suite(name):
    gc.collect()
    print("@S:" + name)


def refresh(iterations=5):
    import lvgl as lv

    for _ in range(iterations):
        lv.timer_handler()
        time.sleep_ms(10)


# ---- Widget Module Tests ----
suite("widget_module")

try:
    from lvgl_mvu.widget import ScalarAttr, Widget, WidgetKey

    t("WidgetKey.SCREEN", WidgetKey.SCREEN, "0")
    t("WidgetKey.CONTAINER", WidgetKey.CONTAINER, "1")
    t("WidgetKey.LABEL", WidgetKey.LABEL, "2")
    t("WidgetKey.BUTTON", WidgetKey.BUTTON, "3")

    # Create a widget manually
    w = Widget(
        key=WidgetKey.LABEL,
        user_key="",
        scalar_attrs=(),
        children=(),
        event_handlers=(),
    )
    t("Widget creation", w.key, "2")
except ImportError as e:
    print("  SKIP: widget module not available - " + str(e))


# ---- Attrs Module Tests ----
suite("attrs_module")

try:
    from lvgl_mvu.attrs import AttrDef, AttrKey, AttrRegistry

    t("AttrKey.TEXT", AttrKey.TEXT, "100")
    t("AttrKey.WIDTH", AttrKey.WIDTH, "2")
    t("AttrKey.HEIGHT", AttrKey.HEIGHT, "3")
    t("AttrKey.BG_COLOR", AttrKey.BG_COLOR, "40")

    # Test AttrRegistry
    registry = AttrRegistry()

    def dummy_apply(obj, val):
        pass

    attr_def = AttrDef(AttrKey.TEXT, "text", "", dummy_apply)
    registry.add(attr_def)
    t("AttrRegistry add", registry.get(AttrKey.TEXT) is not None, "True")
    t("AttrRegistry get missing", registry.get(999) is None, "True")
except ImportError as e:
    print("  SKIP: attrs module not available - " + str(e))


# ---- Builders Module Tests ----
suite("builders_module")

try:
    from lvgl_mvu.attrs import AttrKey
    from lvgl_mvu.builders import WidgetBuilder
    from lvgl_mvu.widget import WidgetKey

    # Test basic builder
    builder = WidgetBuilder(WidgetKey.LABEL)
    builder = builder.set_attr(AttrKey.TEXT, "Hello")
    widget = builder.build()
    t("Builder creates widget", widget.key, "2")
    t("Builder sets attr", len(widget.scalar_attrs), "1")

    # Test fluent API
    widget2 = WidgetBuilder(WidgetKey.CONTAINER).width(100).height(50).bg_color(0xFF0000).build()
    t("Fluent width/height/bg_color", len(widget2.scalar_attrs), "3")

    # Test children
    parent = WidgetBuilder(WidgetKey.CONTAINER)
    parent = parent.add_child(widget)
    parent_widget = parent.build()
    t("Builder add_child", len(parent_widget.children), "1")
except ImportError as e:
    print("  SKIP: builders module not available - " + str(e))


# ---- DSL Module Tests ----
suite("dsl_module")

try:
    from lvgl_mvu.attrs import AttrKey
    from lvgl_mvu.dsl import Button, Container, Label, Screen
    from lvgl_mvu.widget import WidgetKey

    # Test Screen
    screen = Screen().build()
    t("Screen widget key", screen.key, "0")

    # Test Container
    container = Container().size(200, 100).build()
    t("Container widget key", container.key, "1")
    t("Container has attrs", len(container.scalar_attrs), "2")

    # Test Label
    label = Label("Hello World").build()
    t("Label widget key", label.key, "2")
    t("Label has text attr", len(label.scalar_attrs), "1")
    t("Label text value", label.scalar_attrs[0].value, "Hello World")

    # Test Button
    button = Button("Click").build()
    t("Button widget key", button.key, "3")
    t("Button has text attr", len(button.scalar_attrs), "1")

    # Test event handler
    button_with_event = Button("Test").on(7, "MSG_CLICKED").build()
    t("Button event handler", len(button_with_event.event_handlers), "1")

    # Test nested widgets
    screen_with_children = Screen()(
        Label("Title").build(),
        Button("OK").build(),
    )
    t("Screen with children", len(screen_with_children.children), "2")
except ImportError as e:
    print("  SKIP: dsl module not available - " + str(e))


# ---- Layouts Module Tests ----
suite("layouts_module")

try:
    from lvgl_mvu.attrs import AttrKey
    from lvgl_mvu.layouts import LV_FLEX_FLOW_COLUMN, LV_FLEX_FLOW_ROW, HStack, VStack
    from lvgl_mvu.widget import WidgetKey

    # Test VStack
    vstack = VStack(spacing=10).build()
    t("VStack widget key", vstack.key, "1")  # Container
    t("VStack has flex attrs", len(vstack.scalar_attrs) >= 3, "True")

    # Check flex flow attribute
    flex_flow_found = False
    for attr in vstack.scalar_attrs:
        if attr.key == AttrKey.FLEX_FLOW and attr.value == LV_FLEX_FLOW_COLUMN:
            flex_flow_found = True
            break
    t("VStack flex_flow column", flex_flow_found, "True")

    # Test HStack
    hstack = HStack(spacing=5).build()
    t("HStack widget key", hstack.key, "1")  # Container

    # Check flex flow attribute
    flex_flow_row = False
    for attr in hstack.scalar_attrs:
        if attr.key == AttrKey.FLEX_FLOW and attr.value == LV_FLEX_FLOW_ROW:
            flex_flow_row = True
            break
    t("HStack flex_flow row", flex_flow_row, "True")

    # Test VStack with children
    vstack_with_kids = VStack(spacing=10)(
        Label("Item 1").build(),
        Label("Item 2").build(),
    )
    t("VStack children", len(vstack_with_kids.children), "2")
except ImportError as e:
    print("  SKIP: layouts module not available - " + str(e))


# ---- Diff Module Tests ----
suite("diff_module")

try:
    from lvgl_mvu.attrs import AttrKey
    from lvgl_mvu.diff import can_reuse, diff_scalars, diff_widgets
    from lvgl_mvu.widget import ScalarAttr, Widget, WidgetKey

    # Test can_reuse
    w1 = Widget(WidgetKey.LABEL, "", (), (), ())
    w2 = Widget(WidgetKey.LABEL, "", (), (), ())
    w3 = Widget(WidgetKey.BUTTON, "", (), (), ())
    t("can_reuse same type", can_reuse(w1, w2), "True")
    t("can_reuse diff type", can_reuse(w1, w3), "False")

    # Test user_key
    w4 = Widget(WidgetKey.LABEL, "key1", (), (), ())
    w5 = Widget(WidgetKey.LABEL, "key1", (), (), ())
    w6 = Widget(WidgetKey.LABEL, "key2", (), (), ())
    t("can_reuse same user_key", can_reuse(w4, w5), "True")
    t("can_reuse diff user_key", can_reuse(w4, w6), "False")

    # Test diff_scalars
    attrs1 = (ScalarAttr(AttrKey.TEXT, "Hello"),)
    attrs2 = (ScalarAttr(AttrKey.TEXT, "World"),)
    changes = diff_scalars(attrs1, attrs2)
    t("diff_scalars updated", len(changes), "1")
    t("diff_scalars change kind", changes[0].kind, "updated")

    # Test diff_widgets
    prev = Widget(WidgetKey.LABEL, "", attrs1, (), ())
    next_w = Widget(WidgetKey.LABEL, "", attrs2, (), ())
    diff = diff_widgets(prev, next_w)
    t("diff_widgets scalar_changes", len(diff.scalar_changes), "1")
except ImportError as e:
    print("  SKIP: diff module not available - " + str(e))


# ---- Program Module Tests ----
suite("program_module")

try:
    from lvgl_mvu.program import EFFECT_MSG, Cmd, Program, Sub

    # Test Cmd.none()
    cmd_none = Cmd.none()
    t("Cmd.none", len(cmd_none.effects), "0")

    # Test Cmd.of_msg
    cmd_msg = Cmd.of_msg(42)
    t("Cmd.of_msg", len(cmd_msg.effects), "1")
    t("Cmd.of_msg effect kind", cmd_msg.effects[0].kind, str(EFFECT_MSG))
    t("Cmd.of_msg effect data", cmd_msg.effects[0].data, "42")

    # Test Cmd.batch
    cmd1 = Cmd.of_msg(1)
    cmd2 = Cmd.of_msg(2)
    batched = Cmd.batch([cmd1, cmd2])
    t("Cmd.batch", len(batched.effects), "2")

    # Test Sub.none()
    sub_none = Sub.none()
    t("Sub.none", len(sub_none.defs), "0")

    # Test Sub.timer
    sub_timer = Sub.timer(1000, "TICK")
    t("Sub.timer", len(sub_timer.defs), "1")
    t("Sub.timer key", sub_timer.defs[0].key, "timer_1000")

    # Test Program
    def test_init():
        return (0, Cmd.none())

    def test_update(msg, model):
        return (model + 1, Cmd.none())

    def test_view(model):
        return None

    program = Program(test_init, test_update, test_view)
    t("Program init_fn", program.init_fn is not None, "True")
    t("Program update_fn", program.update_fn is not None, "True")
    t("Program view_fn", program.view_fn is not None, "True")
except ImportError as e:
    print("  SKIP: program module not available - " + str(e))


# ---- ViewNode Module Tests ----
suite("viewnode_module")

try:
    from lvgl_mvu.attrs import AttrRegistry
    from lvgl_mvu.viewnode import ViewNode
    from lvgl_mvu.widget import Widget, WidgetKey

    # Create a mock lv_obj
    mock_obj = {"type": "mock"}

    # Create widget and registry
    w = Widget(WidgetKey.LABEL, "", (), (), ())
    registry = AttrRegistry()

    # Create ViewNode
    node = ViewNode(mock_obj, w, registry)
    t("ViewNode lv_obj", node.lv_obj is mock_obj, "True")
    t("ViewNode widget", node.widget.key, "2")
    t("ViewNode children empty", len(node.children), "0")
    t("ViewNode not disposed", node.is_disposed(), "False")

    # Test add_child
    child_w = Widget(WidgetKey.BUTTON, "", (), (), ())
    child_node = ViewNode({"type": "child"}, child_w, registry)
    node.add_child(child_node)
    t("ViewNode add_child", len(node.children), "1")

    # Test remove_child
    removed = node.remove_child(0)
    t("ViewNode remove_child", removed is child_node, "True")
    t("ViewNode children after remove", len(node.children), "0")
except ImportError as e:
    print("  SKIP: viewnode module not available - " + str(e))


# ---- Counter MVU App Tests ----
suite("counter_mvu_app")

try:
    import counter_mvu as app

    # Test init
    model, cmd = app.init()
    t("counter init model", model.count, "0")
    t("counter init cmd", len(cmd.effects), "0")

    # Test update - increment
    new_model, cmd = app.update(app.MSG_INCREMENT, model)
    t("counter increment", new_model.count, "1")

    # Test update - decrement
    new_model, cmd = app.update(app.MSG_DECREMENT, new_model)
    t("counter decrement", new_model.count, "0")

    # Test update - decrement below zero
    new_model, cmd = app.update(app.MSG_DECREMENT, new_model)
    t("counter below zero", new_model.count, "-1")

    # Test update - reset
    new_model, cmd = app.update(app.MSG_RESET, new_model)
    t("counter reset", new_model.count, "0")

    # Test view returns widget
    widget = app.view(model)
    t("counter view widget", widget is not None, "True")
    t("counter view widget key", widget.key, "0")  # Screen
    t("counter view children", len(widget.children) >= 1, "True")
except ImportError as e:
    print("  SKIP: counter_mvu not available - " + str(e))


# ---- LVGL Integration Tests (requires initialized display) ----
suite("lvgl_integration")

try:
    import lvgl as lv

    # Initialize display
    lv.init_display()
    refresh(10)
    print("  LVGL initialized")

    # Test factories
    from lvgl_mvu.factories import (
        create_button,
        create_container,
        create_label,
        create_screen,
    )

    screen = create_screen(None)
    t("create_screen", screen is not None, "True")

    container = create_container(screen)
    t("create_container", container is not None, "True")

    label = create_label(container)
    t("create_label", label is not None, "True")

    button = create_button(container)
    t("create_button", button is not None, "True")

    # Test appliers
    from lvgl_mvu.appliers import apply_text, apply_text_color, apply_width

    apply_text(label, "Test Label")
    t("apply_text label", True, "True")

    apply_text_color(label, 0xFF0000)
    t("apply_text_color", True, "True")

    apply_width(container, 200)
    t("apply_width", True, "True")

    # Cleanup
    lv.lv_obj_delete(screen)
    refresh(5)
    t("cleanup", True, "True")

except ImportError as e:
    print("  SKIP: LVGL integration not available - " + str(e))
except Exception as e:
    print("  ERROR: LVGL integration failed - " + str(e))
    t("lvgl_integration_exception", False, "True")


# ---- Summary ----
print("")
print("=" * 40)
print("P0 WIDGET TEST RESULTS")
print("=" * 40)
print("Total:  " + str(_total))
print("Passed: " + str(_passed))
print("Failed: " + str(_failed))
print("=" * 40)

if _failed > 0:
    print("SOME TESTS FAILED")
else:
    print("ALL TESTS PASSED")
