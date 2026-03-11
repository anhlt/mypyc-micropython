"""P0 Widget + Event System tests for LVGL MVU framework.

Runs directly on MicroPython device.

Usage: mpremote connect /dev/cu.usbmodem101 run run_mvu_p0_tests.py

Tests the P0 widgets (Screen, Container, Label, Button), the MVU
architecture with declarative DSL, and the event system (Milestone 6).
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
    from lvgl_mvu import widget

    t("WidgetKey SCREEN", widget.WidgetKey_SCREEN, "0")
    t("WidgetKey CONTAINER", widget.WidgetKey_CONTAINER, "1")
    t("WidgetKey LABEL", widget.WidgetKey_LABEL, "2")
    t("WidgetKey BUTTON", widget.WidgetKey_BUTTON, "3")

    # Create a widget manually
    w = widget.Widget(
        key=widget.WidgetKey_LABEL,
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
    from lvgl_mvu import attrs

    t("AttrKey TEXT", attrs.AttrKey_TEXT, "100")
    t("AttrKey WIDTH", attrs.AttrKey_WIDTH, "2")
    t("AttrKey HEIGHT", attrs.AttrKey_HEIGHT, "3")
    t("AttrKey BG_COLOR", attrs.AttrKey_BG_COLOR, "40")

    # Test AttrRegistry
    registry = attrs.AttrRegistry()

    def dummy_apply(obj, val):
        pass

    attr_def = attrs.AttrDef(attrs.AttrKey_TEXT, "text", "", dummy_apply)
    registry.add(attr_def)
    t("AttrRegistry add", registry.get(attrs.AttrKey_TEXT) is not None, "True")
    t("AttrRegistry get missing", registry.get(999) is None, "True")
except ImportError as e:
    print("  SKIP: attrs module not available - " + str(e))


# ---- Builders Module Tests ----
suite("builders_module")

try:
    from lvgl_mvu import attrs, builders, widget

    # Test basic builder
    builder = builders.WidgetBuilder(widget.WidgetKey_LABEL)
    builder = builder.set_attr(attrs.AttrKey_TEXT, "Hello")
    w = builder.build()
    t("Builder creates widget", w.key, "2")
    t("Builder sets attr", len(w.scalar_attrs), "1")

    # Test fluent API
    widget2 = (
        builders.WidgetBuilder(widget.WidgetKey_CONTAINER)
        .width(100)
        .height(50)
        .bg_color(0xFF0000)
        .build()
    )
    t("Fluent width/height/bg_color", len(widget2.scalar_attrs), "3")

    # Test add_child + build
    child_w = builders.WidgetBuilder(widget.WidgetKey_LABEL).build()
    parent_w = builders.WidgetBuilder(widget.WidgetKey_CONTAINER).add_child(child_w).build()
    t("Builder add_child", len(parent_w.children), "1")

    # Test with_children
    c1 = builders.WidgetBuilder(widget.WidgetKey_LABEL).build()
    c2 = builders.WidgetBuilder(widget.WidgetKey_BUTTON).build()
    parent_wc = builders.WidgetBuilder(widget.WidgetKey_CONTAINER).with_children([c1, c2])
    t("Builder with_children", len(parent_wc.children), "2")
    t("with_children returns Widget", type(parent_wc).__name__, "Widget")
except ImportError as e:
    print("  SKIP: builders module not available - " + str(e))


# ---- DSL Module Tests ----
suite("dsl_module")

try:
    from lvgl_mvu import attrs, dsl, widget

    # Test Screen
    screen = dsl.Screen().build()
    t("Screen widget key", screen.key, "0")

    # Test Container
    container = dsl.Container().size(200, 100).build()
    t("Container widget key", container.key, "1")
    t("Container has attrs", len(container.scalar_attrs), "2")

    # Test Label
    label = dsl.Label("Hello World").build()
    t("Label widget key", label.key, "2")
    t("Label has text attr", len(label.scalar_attrs), "1")
    t("Label text value", label.scalar_attrs[0].value, "Hello World")

    # Test Button
    button = dsl.Button("Click").build()
    t("Button widget key", button.key, "3")
    t("Button has text attr", len(button.scalar_attrs), "1")

    # Test event handler via builder
    button_with_event = dsl.Button("Test").on(10, "MSG_CLICKED").build()
    t("Button event handler", len(button_with_event.event_handlers), "1")

    # Test with_children composition
    screen_with_children = dsl.Screen().with_children(
        [
            dsl.Label("Title").build(),
            dsl.Button("OK").build(),
        ]
    )
    t("Screen with_children", len(screen_with_children.children), "2")
except ImportError as e:
    print("  SKIP: dsl module not available - " + str(e))


# ---- Layouts Module Tests ----
suite("layouts_module")

try:
    from lvgl_mvu import attrs, layouts, widget

    # Test VStack
    vstack = layouts.VStack(spacing=10).build()
    t("VStack widget key", vstack.key, "1")  # Container
    t("VStack has flex attrs", len(vstack.scalar_attrs) >= 3, "True")

    # Check flex flow attribute
    flex_flow_found = False
    for a in vstack.scalar_attrs:
        if a.key == attrs.AttrKey_FLEX_FLOW and a.value == layouts.LV_FLEX_FLOW_COLUMN:
            flex_flow_found = True
            break
    t("VStack flex_flow column", flex_flow_found, "True")

    # Test HStack
    hstack = layouts.HStack(spacing=5).build()
    t("HStack widget key", hstack.key, "1")  # Container

    flex_flow_row = False
    for a in hstack.scalar_attrs:
        if a.key == attrs.AttrKey_FLEX_FLOW and a.value == layouts.LV_FLEX_FLOW_ROW:
            flex_flow_row = True
            break
    t("HStack flex_flow row", flex_flow_row, "True")

    # Test with_children
    vstack_wc = layouts.VStack(spacing=10).with_children(
        [
            dsl.Label("Item 1").build(),
            dsl.Label("Item 2").build(),
        ]
    )
    t("VStack with_children", len(vstack_wc.children), "2")
except ImportError as e:
    print("  SKIP: layouts module not available - " + str(e))


# ---- Diff Module Tests ----
suite("diff_module")

try:
    from lvgl_mvu import attrs, diff, widget

    # Test can_reuse
    w1 = widget.Widget(widget.WidgetKey_LABEL, "", (), (), ())
    w2 = widget.Widget(widget.WidgetKey_LABEL, "", (), (), ())
    w3 = widget.Widget(widget.WidgetKey_BUTTON, "", (), (), ())
    t("can_reuse same type", diff.can_reuse(w1, w2), "True")
    t("can_reuse diff type", diff.can_reuse(w1, w3), "False")

    # Test user_key
    w4 = widget.Widget(widget.WidgetKey_LABEL, "key1", (), (), ())
    w5 = widget.Widget(widget.WidgetKey_LABEL, "key1", (), (), ())
    w6 = widget.Widget(widget.WidgetKey_LABEL, "key2", (), (), ())
    t("can_reuse same user_key", diff.can_reuse(w4, w5), "True")
    t("can_reuse diff user_key", diff.can_reuse(w4, w6), "False")

    # Test diff_scalars
    attrs1 = (widget.ScalarAttr(attrs.AttrKey_TEXT, "Hello"),)
    attrs2 = (widget.ScalarAttr(attrs.AttrKey_TEXT, "World"),)
    changes = diff.diff_scalars(attrs1, attrs2)
    t("diff_scalars updated", len(changes), "1")
    t("diff_scalars change kind", changes[0].kind, "updated")

    # Test diff_widgets
    prev = widget.Widget(widget.WidgetKey_LABEL, "", attrs1, (), ())
    next_w = widget.Widget(widget.WidgetKey_LABEL, "", attrs2, (), ())
    d = diff.diff_widgets(prev, next_w)
    t("diff_widgets scalar_changes", len(d.scalar_changes), "1")

    # Test event_changes detection
    eh1 = ((10, "MSG_A"),)
    eh2 = ((10, "MSG_B"),)
    w_ev1 = widget.Widget(widget.WidgetKey_BUTTON, "", (), (), eh1)
    w_ev2 = widget.Widget(widget.WidgetKey_BUTTON, "", (), (), eh2)
    d_ev = diff.diff_widgets(w_ev1, w_ev2)
    t("diff event_changes detected", d_ev.event_changes, "True")

    w_ev3 = widget.Widget(widget.WidgetKey_BUTTON, "", (), (), eh1)
    d_ev_same = diff.diff_widgets(w_ev1, w_ev3)
    t("diff event_changes same", d_ev_same.event_changes, "False")
except ImportError as e:
    print("  SKIP: diff module not available - " + str(e))


# ---- Program Module Tests ----
suite("program_module")

try:
    from lvgl_mvu import program

    # Test Cmd.none()
    cmd_none = program.Cmd.none()
    t("Cmd.none", len(cmd_none.effects), "0")

    # Test Cmd.of_msg
    cmd_msg = program.Cmd.of_msg(42)
    t("Cmd.of_msg", len(cmd_msg.effects), "1")
    t("Cmd.of_msg effect kind", cmd_msg.effects[0].kind, str(program.EFFECT_MSG))
    t("Cmd.of_msg effect data", cmd_msg.effects[0].data, "42")

    # Test Cmd.batch
    cmd1 = program.Cmd.of_msg(1)
    cmd2 = program.Cmd.of_msg(2)
    batched = program.Cmd.batch([cmd1, cmd2])
    t("Cmd.batch", len(batched.effects), "2")

    # Test Sub.none()
    sub_none = program.Sub.none()
    t("Sub.none", len(sub_none.defs), "0")

    # Test Sub.timer
    sub_timer = program.Sub.timer(1000, "TICK")
    t("Sub.timer", len(sub_timer.defs), "1")
    t("Sub.timer key", sub_timer.defs[0].key, "timer_1000")

    # Test Program
    def test_init():
        return (0, program.Cmd.none())

    def test_update(msg, model):
        return (model + 1, program.Cmd.none())

    def test_view(model):
        return None

    prog = program.Program(test_init, test_update, test_view)
    t("Program init_fn", prog.init_fn is not None, "True")
    t("Program update_fn", prog.update_fn is not None, "True")
    t("Program view_fn", prog.view_fn is not None, "True")
except ImportError as e:
    print("  SKIP: program module not available - " + str(e))


# ---- ViewNode Module Tests ----
suite("viewnode_module")

try:
    from lvgl_mvu import attrs, viewnode, widget

    # Create a mock lv_obj
    mock_obj = {"type": "mock"}

    # Create widget and registry
    w = widget.Widget(widget.WidgetKey_LABEL, "", (), (), ())
    registry = attrs.AttrRegistry()

    # Create ViewNode
    node = viewnode.ViewNode(mock_obj, w, registry)
    t("ViewNode lv_obj", node.lv_obj is mock_obj, "True")
    t("ViewNode widget", node.widget.key, "2")
    t("ViewNode children empty", len(node.children), "0")
    t("ViewNode not disposed", node.is_disposed(), "False")

    # Test add_child
    child_w = widget.Widget(widget.WidgetKey_BUTTON, "", (), (), ())
    child_node = viewnode.ViewNode({"type": "child"}, child_w, registry)
    node.add_child(child_node)
    t("ViewNode add_child", len(node.children), "1")

    # Test remove_child
    removed = node.remove_child(0)
    t("ViewNode remove_child", removed is child_node, "True")
    t("ViewNode children after remove", len(node.children), "0")

    # Test handler registration
    node.register_handler(10, "handler_obj")
    t("ViewNode register_handler", 10 in node.handlers, "True")
    t("ViewNode handler value", node.handlers[10], "handler_obj")

    # Test unregister_handler
    old_h = node.unregister_handler(10)
    t("ViewNode unregister_handler", old_h, "handler_obj")
    t("ViewNode handlers empty", len(node.handlers), "0")
except ImportError as e:
    print("  SKIP: viewnode module not available - " + str(e))


# ---- Events Module Tests ----
suite("events_module")

try:
    from lvgl_mvu import events

    # Test LvEvent constants
    t("LvEvent CLICKED", events.LvEvent.CLICKED, "10")
    t("LvEvent VALUE_CHANGED", events.LvEvent.VALUE_CHANGED, "35")
    t("LvEvent PRESSED", events.LvEvent.PRESSED, "1")
    t("LvEvent RELEASED", events.LvEvent.RELEASED, "11")

    # Test EventHandler
    handler = events.EventHandler(events.HANDLER_MSG, "test_msg")
    t("EventHandler active", handler.active, "True")
    t("EventHandler kind", handler.kind, str(events.HANDLER_MSG))
    t("EventHandler payload", handler.payload, "test_msg")

    handler.deactivate()
    t("EventHandler deactivated", handler.active, "False")

    # Test EventBinder creation
    dispatched = []

    def mock_dispatch(msg):
        dispatched.append(msg)

    binder = events.EventBinder(mock_dispatch)
    t("EventBinder created", binder is not None, "True")
except ImportError as e:
    print("  SKIP: events module not available - " + str(e))


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

    # Check view has buttons with event handlers
    stack = widget.children[0]  # VStack
    has_events = False
    for child in stack.children:
        if len(child.event_handlers) > 0:
            has_events = True
            break
        # Check nested children (HStack with buttons)
        for grandchild in child.children:
            if len(grandchild.event_handlers) > 0:
                has_events = True
                break
    t("counter has event handlers", has_events, "True")
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
    from lvgl_mvu import factories

    screen = factories.create_screen(None)
    t("create_screen", screen is not None, "True")

    container = factories.create_container(screen)
    t("create_container", container is not None, "True")

    label = factories.create_label(container)
    t("create_label", label is not None, "True")

    button = factories.create_button(container)
    t("create_button", button is not None, "True")

    # Test appliers
    from lvgl_mvu import appliers

    appliers.apply_text(label, "Test Label")
    t("apply_text label", True, "True")

    appliers.apply_text_color(label, 0xFF0000)
    t("apply_text_color", True, "True")

    appliers.apply_width(container, 200)
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


# ---- Event System LVGL Integration ----
suite("event_lvgl_integration")

try:
    import lvgl as lv
    from lvgl_mvu import events

    screen = lv.lv_obj_create(None)
    btn = lv.lv_button_create(screen)

    # Test EventBinder.bind with real LVGL objects
    dispatched_msgs = []

    def test_dispatch(msg):
        dispatched_msgs.append(msg)

    binder = events.EventBinder(test_dispatch)
    handler = binder.bind(btn, events.LvEvent.CLICKED, "BTN_CLICKED")
    t("bind returns handler", handler is not None, "True")
    t("handler is active", handler.active, "True")

    # Test unbind (deactivate)
    binder.unbind(btn, events.LvEvent.CLICKED, handler)
    t("handler deactivated", handler.active, "False")

    lv.lv_obj_delete(screen)
    refresh(5)
    t("event cleanup", True, "True")

except ImportError as e:
    print("  SKIP: event LVGL integration not available - " + str(e))
except Exception as e:
    print("  ERROR: event LVGL integration failed - " + str(e))
    t("event_lvgl_exception", False, "True")


# ---- Counter App Full Integration (create + tick) ----
suite("counter_full_integration")

try:
    import counter_mvu
    import lvgl as lv

    app = counter_mvu.create_app()
    t("create_app", app is not None, "True")

    # First tick creates the view tree
    app.tick()
    t("first tick", app.root_node is not None, "True")

    # Load screen
    lv.lv_screen_load(app.root_node.lv_obj)
    refresh(10)
    t("screen loaded", True, "True")

    # Dispatch increment and tick
    app.dispatch(counter_mvu.MSG_INCREMENT)
    app.tick()
    t("increment dispatch", app.model.count, "1")
    refresh(5)

    # Dispatch decrement
    app.dispatch(counter_mvu.MSG_DECREMENT)
    app.tick()
    t("decrement dispatch", app.model.count, "0")
    refresh(5)

    # Cleanup
    app.dispose()
    refresh(5)
    t("app disposed", app.is_disposed(), "True")

except ImportError as e:
    print("  SKIP: counter full integration not available - " + str(e))
except Exception as e:
    print("  ERROR: counter full integration failed - " + str(e))
    import sys

    sys.print_exception(e)
    t("counter_full_exception", False, "True")


# ---- Summary ----
print("")
print("=" * 40)
print("P0 WIDGET + EVENT TEST RESULTS")
print("=" * 40)
print("Total:  " + str(_total))
print("Passed: " + str(_passed))
print("Failed: " + str(_failed))
print("=" * 40)

if _failed > 0:
    print("SOME TESTS FAILED")
else:
    print("ALL TESTS PASSED")
