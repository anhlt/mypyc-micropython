"""LVGL UI Framework test runner. Runs directly on MicroPython.

Usage: mpremote connect /dev/cu.usbmodem101 run run_lvgl_tests.py

Tests the compiled lvui package which provides native screen
management, MVU architecture, and navigation.
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
    import lvui

    for _ in range(iterations):
        lvui.screens.timer_handler()
        time.sleep_ms(10)

# ---- Package Import Tests ----
suite("lvui_package")

try:
    import lvui
    t("import lvui", lvui is not None, "True")

    # Test submodule access via dot notation
    t("lvui.mvu exists", lvui.mvu is not None, "True")
    t("lvui.nav exists", lvui.nav is not None, "True")
    t("lvui.screens exists", lvui.screens is not None, "True")

    # Test that submodules have expected attributes
    t("lvui.mvu has App", hasattr(lvui.mvu, 'App'), "True")
    t("lvui.screens has create_screen", hasattr(lvui.screens, 'create_screen'), "True")
except ImportError as e:
    print("  SKIP: lvui package not available - " + str(e))

# ---- Compiled Screen Manager Tests ----
suite("lvgl_screens")

try:
    import lvgl as lv
    import lvui

    # Initialize display
    lv.init_display()
    refresh(10)
    print("  LVGL and lvgl_screens initialized")

    # Test screen creation functions
    scr = lvui.screens.create_screen()
    t("create_screen", scr is not None, "True")

    # Test widget creation
    label = lvui.screens.create_label(scr, "Test Label")
    t("create_label", label is not None, "True")

    btn = lvui.screens.create_button(scr, "Click Me", 120, 40)
    t("create_button", btn is not None, "True")

    slider = lvui.screens.create_slider(scr, 0, 100, 50)
    t("create_slider", slider is not None, "True")

    val = lvui.screens.get_slider_value(slider)
    t("get_slider_value", val, "50")

    bar = lvui.screens.create_bar(scr, 0, 100, 70)
    t("create_bar", bar is not None, "True")

    bar_val = lvui.screens.get_bar_value(bar)
    t("get_bar_value", bar_val, "70")

    arc = lvui.screens.create_arc(scr, 0, 100, 75)
    t("create_arc", arc is not None, "True")

    arc_val = lvui.screens.get_arc_value(arc)
    t("get_arc_value", arc_val, "75")

    # Load and display screen
    lvui.screens.screen_load(scr)
    refresh(10)
    t("screen_load", True, "True")

    # Test container with flex layout
    scr2 = lvui.screens.create_screen()
    cont = lvui.screens.create_container(scr2, 200, 150)
    t("create_container", cont is not None, "True")

    lvui.screens.set_flex_column(cont)
    t("set_flex_column", True, "True")

    # Add widgets to container
    lvui.screens.create_label(cont, "Title")
    cb = lvui.screens.create_checkbox(cont, "Option", True)
    t("create_checkbox", cb is not None, "True")

    sw = lvui.screens.create_switch(cont, False)
    t("create_switch", sw is not None, "True")

    lvui.screens.screen_load(scr2)
    refresh(10)

    # Test styling
    lvui.screens.set_style_bg_color(cont, 0x2196F3, 0)  # Blue background
    t("set_style_bg_color", True, "True")
    refresh(5)

    # Test pre-built screens with proper screen management
    # show_screen(new, old) loads new and deletes old if not None
    home = lvui.screens.build_home_screen()
    t("build_home_screen", home is not None, "True")
    lvui.screens.show_screen(home, None)  # First screen, no old to delete
    refresh(15)

    slider_scr = lvui.screens.build_slider_screen()
    t("build_slider_screen", slider_scr is not None, "True")
    lvui.screens.show_screen(slider_scr, home)  # Delete home
    refresh(15)

    progress_scr = lvui.screens.build_progress_screen()
    t("build_progress_screen", progress_scr is not None, "True")
    lvui.screens.show_screen(progress_scr, slider_scr)  # Delete slider_scr
    refresh(15)

    arc_scr = lvui.screens.build_arc_screen()
    t("build_arc_screen", arc_scr is not None, "True")
    lvui.screens.show_screen(arc_scr, progress_scr)  # Delete progress_scr
    refresh(15)

    controls_scr = lvui.screens.build_controls_screen()
    t("build_controls_screen", controls_scr is not None, "True")
    lvui.screens.show_screen(controls_scr, arc_scr)  # Delete arc_scr
    refresh(15)

    # Memory test - cycle through screens
    gc.collect()
    baseline = gc.mem_free()

    old_scr = controls_scr
    for i in range(5):
        new_scr = lvui.screens.build_home_screen()
        lvui.screens.show_screen(new_scr, old_scr)
        old_scr = new_scr
        refresh(3)

        new_scr = lvui.screens.build_slider_screen()
        lvui.screens.show_screen(new_scr, old_scr)
        old_scr = new_scr
        refresh(3)

        new_scr = lvui.screens.build_progress_screen()
        lvui.screens.show_screen(new_scr, old_scr)
        old_scr = new_scr
        refresh(3)
        gc.collect()

    final = gc.mem_free()
    mem_drop = baseline - final
    t("memory stable after screen cycles", mem_drop < 5000, "True")
    print(f"    (mem drop: {mem_drop} bytes)")

    # End with home screen
    final_home = lvui.screens.build_home_screen()
    lvui.screens.show_screen(final_home, old_scr)
    refresh(20)

except ImportError as e:
    print("SKIP: required modules not available - " + str(e))
except Exception as e:
    print("ERROR: lvgl_screens tests failed - " + str(e))
    import sys

    sys.print_exception(e)
    _failed += 1

suite("lvgl_mvu")

try:
    import gc

    # lvui already imported above

    # Create app with initial parameters
    app = lvui.mvu.App(0, 8, 32)  # screen_width, screen_height, buffer_size
    app.mount()

    # Memory soak test
    min_free = gc.mem_free()
    baseline = min_free

    for i in range(5000):
        # Dispatch and tick to update UI
        app.dispatch(1)
        app.tick(1)

        # Collect garbage and track memory every 64 iterations
        if i % 64 == 0:
            gc.collect()
            current_free = gc.mem_free()
            min_free = min(min_free, current_free)

        # Occasionally refresh to run LVGL timers
        if i % 32 == 0:
            refresh(1)

    # Check memory stability
    mem_drop = baseline - min_free
    t("lvgl_mvu memory soak", mem_drop < 4000, "True")
    print(f"    (mem drop: {mem_drop} bytes)")

    # Clean up
    app.dispose()

except ImportError as e:
    print("SKIP: lvgl_mvu not available - " + str(e))
except Exception as e:
    print("ERROR: lvgl_mvu tests failed - " + str(e))
    import sys
    sys.print_exception(e)
    _failed += 1

# ---- LVGL MVU Logic Tests (no display required, but need lvgl_mvu module) ----

suite("lvgl_mvu_diff")
import lvgl_mvu

Widget = lvgl_mvu.widget.Widget
ScalarAttr = lvgl_mvu.widget.ScalarAttr
diff_widgets = lvgl_mvu.diff.diff_widgets
diff_scalars = lvgl_mvu.diff.diff_scalars
can_reuse = lvgl_mvu.diff.can_reuse
diff_children = lvgl_mvu.diff.diff_children

# -- Widget & ScalarAttr construction --
LABEL = 2
BUTTON = 3
CONTAINER = 1

a1 = ScalarAttr(1, "hello")
t("scalar_attr key", a1.key, "1")
t("scalar_attr value", a1.value, "hello")

w1 = Widget(LABEL, "", (ScalarAttr(1, "text1"),), (), ())
t("widget key", w1.key, str(LABEL))
t("widget user_key", w1.user_key, "")
t("widget scalar len", len(w1.scalar_attrs), "1")
t("widget children len", len(w1.children), "0")
t("widget events len", len(w1.event_handlers), "0")

# -- diff_scalars: no changes --
attrs_a = (ScalarAttr(1, 10), ScalarAttr(2, 20))
attrs_b = (ScalarAttr(1, 10), ScalarAttr(2, 20))
sc = diff_scalars(attrs_a, attrs_b)
t("scalars no change", len(sc), "0")

# -- diff_scalars: value updated --
attrs_c = (ScalarAttr(1, 10), ScalarAttr(2, 99))
sc2 = diff_scalars(attrs_a, attrs_c)
t("scalars updated len", len(sc2), "1")
t("scalars updated kind", sc2[0].kind, "updated")
t("scalars updated key", sc2[0].key, "2")
t("scalars updated old", sc2[0].old_value, "20")
t("scalars updated new", sc2[0].new_value, "99")

# -- diff_scalars: added --
attrs_d = (ScalarAttr(1, 10), ScalarAttr(2, 20), ScalarAttr(3, 30))
sc3 = diff_scalars(attrs_a, attrs_d)
t("scalars added len", len(sc3), "1")
t("scalars added kind", sc3[0].kind, "added")
t("scalars added key", sc3[0].key, "3")

# -- diff_scalars: removed --
attrs_e = (ScalarAttr(1, 10),)
sc4 = diff_scalars(attrs_a, attrs_e)
t("scalars removed len", len(sc4), "1")
t("scalars removed kind", sc4[0].kind, "removed")
t("scalars removed key", sc4[0].key, "2")

# -- can_reuse: same type, no user_key --
wa = Widget(LABEL, "", (), (), ())
wb = Widget(LABEL, "", (), (), ())
t("reuse same type", can_reuse(wa, wb), "True")

# -- can_reuse: different type --
wc = Widget(BUTTON, "", (), (), ())
t("reuse diff type", can_reuse(wa, wc), "False")

# -- can_reuse: same user_key --
wd = Widget(LABEL, "k1", (), (), ())
we = Widget(LABEL, "k1", (), (), ())
t("reuse same ukey", can_reuse(wd, we), "True")

# -- can_reuse: different user_key --
wf = Widget(LABEL, "k2", (), (), ())
t("reuse diff ukey", can_reuse(wd, wf), "False")

# -- can_reuse: one has user_key, other empty --
t("reuse one ukey", can_reuse(wa, wd), "False")

gc.collect()
# -- diff_children: no changes --
ch_a = (Widget(LABEL, "", (ScalarAttr(1, "x"),), (), ()),)
ch_b = (Widget(LABEL, "", (ScalarAttr(1, "x"),), (), ()),)
cc = diff_children(ch_a, ch_b)
t("children no change", len(cc), "0")

# -- diff_children: child updated --
ch_c = (Widget(LABEL, "", (ScalarAttr(1, "y"),), (), ()),)
cc2 = diff_children(ch_a, ch_c)
t("children updated len", len(cc2), "1")
t("children updated kind", cc2[0].kind, "update")

# -- diff_children: child inserted --
ch_d = (Widget(LABEL, "", (), (), ()), Widget(BUTTON, "", (), (), ()))
cc3 = diff_children(ch_a, ch_d)
# first child reusable (same type LABEL), second is insert
has_insert = False
for c in cc3:
    if c.kind == "insert":
        has_insert = True
t("children has insert", has_insert, "True")

# -- diff_children: child removed --
cc4 = diff_children(ch_d, ch_a)
has_remove = False
for c in cc4:
    if c.kind == "remove":
        has_remove = True
t("children has remove", has_remove, "True")

# -- diff_children: child replaced (type mismatch) --
ch_e = (Widget(BUTTON, "", (), (), ()),)
cc5 = diff_children(ch_a, ch_e)
t("children replace len", len(cc5), "1")
t("children replace kind", cc5[0].kind, "replace")

# -- diff_widgets: identical widgets --
w_prev = Widget(LABEL, "", (ScalarAttr(1, 10),), (), ())
w_next = Widget(LABEL, "", (ScalarAttr(1, 10),), (), ())
d1 = diff_widgets(w_prev, w_next)
t("diff identical empty", d1.is_empty(), "True")
t("diff identical scalars", len(d1.scalar_changes), "0")
t("diff identical children", len(d1.child_changes), "0")
t("diff identical events", d1.event_changes, "False")

# -- diff_widgets: scalar change --
w_next2 = Widget(LABEL, "", (ScalarAttr(1, 99),), (), ())
d2 = diff_widgets(w_prev, w_next2)
t("diff scalar not empty", d2.is_empty(), "False")
t("diff scalar changes", len(d2.scalar_changes), "1")

# -- diff_widgets: child change --
w_prev3 = Widget(CONTAINER, "", (), (Widget(LABEL, "", (), (), ()),), ())
w_next3 = Widget(CONTAINER, "", (), (Widget(LABEL, "", (ScalarAttr(1, 5),), (), ()),), ())
d3 = diff_widgets(w_prev3, w_next3)
t("diff child not empty", d3.is_empty(), "False")
t("diff child changes", len(d3.child_changes), "1")

# -- diff_widgets: event change --
w_prev4 = Widget(BUTTON, "", (), (), ((1, "click"),))
w_next4 = Widget(BUTTON, "", (), (), ((1, "tap"),))
d4 = diff_widgets(w_prev4, w_next4)
t("diff event not empty", d4.is_empty(), "False")
t("diff event flag", d4.event_changes, "True")

# -- diff_widgets: event equal (identity vs equality fix) --
w_prev5 = Widget(BUTTON, "", (), (), ((1, "click"), (2, "hold")))
w_next5 = Widget(BUTTON, "", (), (), ((1, "click"), (2, "hold")))
d5 = diff_widgets(w_prev5, w_next5)
t("diff event eq empty", d5.is_empty(), "True")
t("diff event eq flag", d5.event_changes, "False")

# -- diff_widgets: prev is None (Optional narrowing path) --
w_new = Widget(LABEL, "", (ScalarAttr(1, "hi"), ScalarAttr(2, 42)), (Widget(BUTTON, "", (), (), ()),), ())
d6 = diff_widgets(None, w_new)
t("diff None prev not empty", d6.is_empty(), "False")
t("diff None scalar adds", len(d6.scalar_changes), "2")
t("diff None child inserts", len(d6.child_changes), "1")
t("diff None event flag", d6.event_changes, "False")

# -- diff_widgets: prev None with events --
w_new2 = Widget(BUTTON, "", (), (), ((1, "click"),))
d7 = diff_widgets(None, w_new2)
t("diff None events flag", d7.event_changes, "True")

# ---- lvgl_mvu_viewnode ----
suite("lvgl_mvu_viewnode")
# ViewNode tests - testing without actual LVGL (mocked lv_obj)

ViewNode = lvgl_mvu.viewnode.ViewNode
AttrRegistry = lvgl_mvu.attrs.AttrRegistry
AttrChange = lvgl_mvu.diff.AttrChange
WidgetDiff = lvgl_mvu.diff.WidgetDiff
CHANGE_ADDED = lvgl_mvu.diff.CHANGE_ADDED
CHANGE_UPDATED = lvgl_mvu.diff.CHANGE_UPDATED
CHANGE_REMOVED = lvgl_mvu.diff.CHANGE_REMOVED

# Mock LVGL object - just a dict for testing
class MockLvObj:
    def __init__(self, name):
        self.name = name
        self.attrs = {}

# Create an empty registry for testing
test_registry = AttrRegistry()
# Test ViewNode creation
mock_lv = MockLvObj("test_label")
w = Widget(LABEL, "", (ScalarAttr(1, "hello"),), (), ())
node = ViewNode(mock_lv, w, test_registry)
t("viewnode lv_obj", node.lv_obj.name, "test_label")
t("viewnode widget", node.widget.key, str(LABEL))
t("viewnode children", len(node.children), "0")
t("viewnode handlers", len(node.handlers), "0")
t("viewnode not disposed", node.is_disposed(), "False")

# Test add_child / get_child
child_lv = MockLvObj("child_button")
child_w = Widget(BUTTON, "", (), (), ())
child_node = ViewNode(child_lv, child_w, test_registry)
node.add_child(child_node)
t("viewnode add_child", len(node.children), "1")
t("viewnode get_child", node.get_child(0).lv_obj.name, "child_button")
t("viewnode get_child_none", node.get_child(5), "None")

# Test remove_child
node2 = ViewNode(MockLvObj("p"), w, test_registry)
child_node2 = ViewNode(MockLvObj("c"), child_w, test_registry)
node2.add_child(child_node2)
removed = node2.remove_child(0)
t("viewnode remove_child", removed.lv_obj.name, "c")
t("viewnode after remove", len(node2.children), "0")

# Test handler registration
node3 = ViewNode(MockLvObj("btn"), Widget(BUTTON, "", (), (), ()), test_registry)
node3.register_handler(1, "handler_fn")
t("viewnode register_handler", node3.handlers[1], "handler_fn")
h = node3.unregister_handler(1)
t("viewnode unregister", h, "handler_fn")
t("viewnode after unreg", len(node3.handlers), "0")

# Test clear_handlers
node4 = ViewNode(MockLvObj("btn2"), Widget(BUTTON, "", (), (), ()), test_registry)
node4.register_handler(1, "h1")
node4.register_handler(2, "h2")
old = node4.clear_handlers()
t("viewnode clear len", len(old), "2")
t("viewnode after clear", len(node4.handlers), "0")

# Test update_widget
node5 = ViewNode(MockLvObj("lbl"), Widget(LABEL, "", (ScalarAttr(1, "old"),), (), ()), test_registry)
new_w = Widget(LABEL, "", (ScalarAttr(1, "new"),), (), ())
node5.update_widget(new_w)
t("viewnode update_widget", node5.widget.scalar_attrs[0].value, "new")

# Test dispose
disposed_list = []
def track_delete(obj):
    disposed_list.append(obj.name)

root = ViewNode(MockLvObj("root"), Widget(CONTAINER, "", (), (), ()), test_registry)
c1 = ViewNode(MockLvObj("c1"), Widget(LABEL, "", (), (), ()), test_registry)
c2 = ViewNode(MockLvObj("c2"), Widget(BUTTON, "", (), (), ()), test_registry)
root.add_child(c1)
root.add_child(c2)
root.dispose(track_delete)
t("viewnode dispose root", root.is_disposed(), "True")
t("viewnode dispose c1", c1.is_disposed(), "True")
t("viewnode dispose c2", c2.is_disposed(), "True")
t("viewnode dispose order", "c1" in str(disposed_list), "True")
t("viewnode dispose all", len(disposed_list), "3")

gc.collect()
# ---- lvgl_mvu_reconciler ----
suite("lvgl_mvu_reconciler")

Reconciler = lvgl_mvu.reconciler.Reconciler

# Track created objects for testing
created_objs = []
deleted_objs = []

def make_label(parent):
    obj = MockLvObj("label_" + str(len(created_objs)))
    created_objs.append(obj)
    return obj

def make_button(parent):
    obj = MockLvObj("button_" + str(len(created_objs)))
    created_objs.append(obj)
    return obj

def make_container(parent):
    obj = MockLvObj("container_" + str(len(created_objs)))
    created_objs.append(obj)
    return obj

def delete_obj(obj):
    deleted_objs.append(obj.name)

# Test Reconciler creation and factory registration
rec = Reconciler(test_registry)
rec.register_factory(LABEL, make_label)
rec.register_factory(BUTTON, make_button)
rec.register_factory(CONTAINER, make_container)
rec.set_delete_fn(delete_obj)
t("reconciler created", rec is not None, "True")

# Test reconcile: create new node
created_objs.clear()
w1 = Widget(LABEL, "", (ScalarAttr(1, "test"),), (), ())
n1 = rec.reconcile(None, w1, None)
t("reconcile new", n1 is not None, "True")
t("reconcile lv_obj", "label" in n1.lv_obj.name, "True")
t("reconcile widget", n1.widget.key, str(LABEL))

# Test reconcile: update existing node (same type)
w2 = Widget(LABEL, "", (ScalarAttr(1, "updated"),), (), ())
n2 = rec.reconcile(n1, w2, None)
t("reconcile update same", n2 is n1, "True")  # Should reuse same node
t("reconcile widget updated", n2.widget.scalar_attrs[0].value, "updated")

# Test reconcile: replace node (different type)
created_objs.clear()
deleted_objs.clear()
old_node = ViewNode(MockLvObj("old_label"), Widget(LABEL, "", (), (), ()), test_registry)
w3 = Widget(BUTTON, "", (), (), ())
n3 = rec.reconcile(old_node, w3, None)
t("reconcile replace", "button" in n3.lv_obj.name, "True")
t("reconcile old disposed", old_node.is_disposed(), "True")

# Test reconcile: with children
created_objs.clear()
w_parent = Widget(CONTAINER, "", (), (Widget(LABEL, "", (), (), ()), Widget(BUTTON, "", (), (), ())), ())
n_parent = rec.reconcile(None, w_parent, None)
t("reconcile children", len(n_parent.children), "2")
t("reconcile child0", "label" in n_parent.children[0].lv_obj.name, "True")
t("reconcile child1", "button" in n_parent.children[1].lv_obj.name, "True")

# Test dispose_tree
created_objs.clear()
deleted_objs.clear()
w_tree = Widget(CONTAINER, "", (), (Widget(LABEL, "", (), (), ()),), ())
n_tree = rec.reconcile(None, w_tree, None)
rec.dispose_tree(n_tree)
t("dispose_tree root", n_tree.is_disposed(), "True")
t("dispose_tree count", len(deleted_objs), "2")  # container + label

gc.collect()
# ---- lvgl_mvu_program ----
suite("lvgl_mvu_program")

Effect = lvgl_mvu.program.Effect
Cmd = lvgl_mvu.program.Cmd
SubDef = lvgl_mvu.program.SubDef
Sub = lvgl_mvu.program.Sub
Program = lvgl_mvu.program.Program
EFFECT_MSG = lvgl_mvu.program.EFFECT_MSG
EFFECT_FN = lvgl_mvu.program.EFFECT_FN
SUB_TIMER = lvgl_mvu.program.SUB_TIMER

# -- Effect --
eff = Effect(EFFECT_MSG, 42)
t("effect kind", eff.kind, str(EFFECT_MSG))
t("effect data", eff.data, "42")

eff_fn = Effect(EFFECT_FN, "my_fn")
t("effect fn kind", eff_fn.kind, str(EFFECT_FN))
t("effect fn data", eff_fn.data, "my_fn")

# -- Cmd.none --
cmd_none = Cmd.none()
t("cmd none effects", len(cmd_none.effects), "0")

# -- Cmd.of_msg --
cmd_msg = Cmd.of_msg("hello")
t("cmd of_msg len", len(cmd_msg.effects), "1")
t("cmd of_msg kind", cmd_msg.effects[0].kind, str(EFFECT_MSG))
t("cmd of_msg data", cmd_msg.effects[0].data, "hello")

# -- Cmd.batch --
cmd_a = Cmd.of_msg("a")
cmd_b = Cmd.of_msg("b")
cmd_batch = Cmd.batch([cmd_a, cmd_b])
t("cmd batch len", len(cmd_batch.effects), "2")
t("cmd batch first", cmd_batch.effects[0].data, "a")
t("cmd batch second", cmd_batch.effects[1].data, "b")

# -- Cmd.batch empty --
cmd_empty_batch = Cmd.batch([])
t("cmd batch empty", len(cmd_empty_batch.effects), "0")

# -- Cmd.of_effect --
cmd_eff = Cmd.of_effect("fn_placeholder")
t("cmd of_effect len", len(cmd_eff.effects), "1")
t("cmd of_effect kind", cmd_eff.effects[0].kind, str(EFFECT_FN))

# -- SubDef --
sd = SubDef(SUB_TIMER, "timer_100", (100, "tick"))
t("subdef kind", sd.kind, str(SUB_TIMER))
t("subdef key", sd.key, "timer_100")
t("subdef data", sd.data[0], "100")

# -- Sub.none --
sub_none = Sub.none()
t("sub none defs", len(sub_none.defs), "0")

# -- Sub.timer --
sub_timer = Sub.timer(500, "tick_msg")
t("sub timer len", len(sub_timer.defs), "1")
t("sub timer kind", sub_timer.defs[0].kind, str(SUB_TIMER))
t("sub timer key", sub_timer.defs[0].key, "timer_500")
t("sub timer interval", sub_timer.defs[0].data[0], "500")
t("sub timer msg", sub_timer.defs[0].data[1], "tick_msg")

# -- Sub.batch --
sub_a = Sub.timer(100, "a")
sub_b = Sub.timer(200, "b")
sub_batch = Sub.batch([sub_a, sub_b])
t("sub batch len", len(sub_batch.defs), "2")
t("sub batch first key", sub_batch.defs[0].key, "timer_100")
t("sub batch second key", sub_batch.defs[1].key, "timer_200")

# -- Sub.batch empty --
sub_empty_batch = Sub.batch([])
t("sub batch empty", len(sub_empty_batch.defs), "0")

# -- Program --
def _test_init():
    return (0, Cmd.none())

def _test_update(msg, model):
    return (model + 1, Cmd.none())

def _test_view(model):
    return Widget(LABEL, "", (ScalarAttr(1, str(model)),), (), ())

prog = Program(_test_init, _test_update, _test_view)
t("program init_fn", prog.init_fn is not None, "True")
t("program update_fn", prog.update_fn is not None, "True")
t("program view_fn", prog.view_fn is not None, "True")
t("program subscribe_fn", prog.subscribe_fn, "None")

# -- Program with subscribe --
def _test_subscribe(model):
    return Sub.none()

prog_sub = Program(_test_init, _test_update, _test_view, _test_subscribe)
t("program with sub", prog_sub.subscribe_fn is not None, "True")

gc.collect()

# ---- lvgl_mvu_app ----
suite("lvgl_mvu_app")

App = lvgl_mvu.app.App

# -- Helper functions for testing --
def counter_init():
    return (0, Cmd.none())

def counter_update(msg, model):
    if msg == "inc":
        return (model + 1, Cmd.none())
    if msg == "dec":
        return (model - 1, Cmd.none())
    if msg == "set10":
        return (10, Cmd.none())
    return (model, Cmd.none())

def counter_view(model):
    return Widget(LABEL, "", (ScalarAttr(1, str(model)),), (), ())

counter_prog = Program(counter_init, counter_update, counter_view)

# -- App creation --
app = App(counter_prog, rec)
t("app model init", app.model, "0")
t("app not disposed", app.is_disposed(), "False")
t("app queue empty", app.queue_length(), "0")

# -- App tick (first render) --
changed = app.tick()
t("app first tick", app.root_node is not None, "True")

# -- App dispatch + tick --
app.dispatch("inc")
t("app queue after dispatch", app.queue_length(), "1")
changed = app.tick()
t("app tick changed", changed, "True")
t("app model after inc", app.model, "1")
t("app queue after tick", app.queue_length(), "0")

# -- Multiple dispatches --
app.dispatch("inc")
app.dispatch("inc")
app.dispatch("inc")
changed = app.tick()
t("app model after 3x inc", app.model, "4")

# -- Decrement --
app.dispatch("dec")
app.tick()
t("app model after dec", app.model, "3")

# -- No change tick --
changed = app.tick()
t("app no change tick", changed, "False")

# -- Dispose --
app.dispose()
t("app disposed", app.is_disposed(), "True")
t("app root after dispose", app.root_node, "None")

# -- Dispatch after dispose (should be ignored) --
app.dispatch("inc")
t("app queue after dispose", app.queue_length(), "0")

gc.collect()

# -- App with Cmd.of_msg (cascading messages) --
def cascade_update(msg, model):
    if msg == "start":
        return (model + 1, Cmd.of_msg("chain"))
    if msg == "chain":
        return (model + 10, Cmd.none())
    return (model, Cmd.none())

cascade_prog = Program(counter_init, cascade_update, counter_view)
app2 = App(cascade_prog, rec)
app2.dispatch("start")
app2.tick()
t("app cascade model", app2.model, "11")
app2.dispose()

gc.collect()

# -- App with subscriptions --
_timer_created = [0]
_timer_torn_down = [0]

def mock_timer_factory(interval_ms, app_ref, msg):
    _timer_created[0] += 1
    def teardown():
        _timer_torn_down[0] += 1
    return teardown

def sub_counter_subscribe(model):
    if model > 0:
        return Sub.timer(100, "tick")
    return Sub.none()

sub_prog = Program(counter_init, counter_update, counter_view, sub_counter_subscribe)
app3 = App(sub_prog, rec)
app3.set_timer_factory(mock_timer_factory)

# model=0, subscribe returns Sub.none, no timer created
t("app sub no timer", _timer_created[0], "0")

# Dispatch inc -> model=1 -> subscribe returns timer
app3.dispatch("inc")
app3.tick()
t("app sub timer created", _timer_created[0], "1")

# Dispose should tear down
app3.dispose()
t("app sub timer torn", _timer_torn_down[0], "1")

gc.collect()

# ---- events_callback (test compiled closure callbacks with LVGL) ----
suite("events_callback")

try:
    import lvgl as lv
    import lvgl_mvu
    EventBinder = lvgl_mvu.events.EventBinder
    LvEvent = lvgl_mvu.events.LvEvent

    # Track callback invocations
    _callback_count = [0]
    _last_msg = [None]

    def test_dispatch(msg):
        _callback_count[0] += 1
        _last_msg[0] = msg

    # Create EventBinder with our test dispatch function
    binder = EventBinder(test_dispatch)
    t("EventBinder created", binder is not None, "True")

    # Create a test screen and button
    scr = lv.lv_obj_create(None)
    btn = lv.lv_button_create(scr)
    t("Button created", btn is not None, "True")

    # Bind event using compiled closure
    MSG_TEST = 42
    handler = binder.bind(btn, LvEvent.CLICKED, MSG_TEST)
    t("Event bound", handler is not None, "True")
    t("Handler active", handler.active, "True")

    # NOTE: Cannot trigger events programmatically - lv_obj_send_event is not
    # exposed in our LVGL bindings. The event binding is verified to work via
    # manual testing and the counter_mvu app which handles real button clicks.
    #
    # To fully test event dispatch, we would need to add lv_obj_send_event
    # to the LVGL C bindings generator.

    # Test unbind functionality
    binder.unbind(btn, LvEvent.CLICKED, handler)
    t("Handler inactive after unbind", handler.active, "False")

    # Clean up
    lv.lv_obj_delete(scr)
    t("Cleanup done", True, "True")

except ImportError as e:
    print("SKIP: events modules not available - " + str(e))
except Exception as e:
    print("ERROR: events_callback tests failed - " + str(e))
    import sys
    sys.print_exception(e)
    _failed += 1
gc.collect()


# ---- counter_mvu (real MVU app with display) ----
suite("counter_mvu")

try:
    import time

    import counter_mvu
    import lvgl as lv

    # Create and initialize the app
    app = counter_mvu.create_app()
    t("counter_mvu create_app", app is not None, "True")

    # First tick to render initial view
    app.tick()
    t("counter_mvu root_node", app.root_node is not None, "True")
    t("counter_mvu initial model", app.model.count, "0")

    # Load screen
    lv.lv_screen_load(app.root_node.lv_obj)
    refresh(10)
    t("counter_mvu screen loaded", True, "True")

    # Test increment
    app.dispatch(counter_mvu.MSG_INCREMENT)
    app.tick()
    lv.timer_handler()
    t("counter_mvu after 1 inc", app.model.count, "1")

    # Test multiple increments
    for _ in range(5):
        app.dispatch(counter_mvu.MSG_INCREMENT)
        app.tick()
        lv.timer_handler()
    t("counter_mvu after 6 inc", app.model.count, "6")

    # Fast increment test (no sleep)
    start = time.ticks_ms()
    for i in range(100):
        app.dispatch(counter_mvu.MSG_INCREMENT)
        app.tick()
        lv.timer_handler()
    end = time.ticks_ms()
    elapsed = time.ticks_diff(end, start)
    t("counter_mvu after 106 inc", app.model.count, "106")
    print(f"    (100 updates in {elapsed}ms)")

    # Memory stability test
    gc.collect()
    baseline = gc.mem_free()

    for i in range(500):
        app.dispatch(counter_mvu.MSG_INCREMENT)
        app.tick()
        lv.timer_handler()
        if i % 100 == 0:
            gc.collect()

    gc.collect()
    final = gc.mem_free()
    mem_drop = baseline - final
    t("counter_mvu memory stable", mem_drop < 5000, "True")
    print(f"    (mem drop: {mem_drop} bytes after 500 updates)")
    t("counter_mvu final count", app.model.count, "606")

    # Verify view updates correctly
    view_widget = counter_mvu.view(app.model)
    t("counter_mvu view returns Widget", view_widget is not None, "True")

    # Clean up - create new screen to release counter screen
    cleanup_scr = lv.lv_obj_create(None)
    lv.lv_screen_load(cleanup_scr)
    refresh(5)

except ImportError as e:
    print("SKIP: counter_mvu not available - " + str(e))
except Exception as e:
    print("ERROR: counter_mvu tests failed - " + str(e))
    import sys
    sys.print_exception(e)
    _failed += 1

gc.collect()


# ---- summary ----
gc.collect()
print("@D:" + str(_total) + "|" + str(_passed) + "|" + str(_failed))
if _failed:
    print("FAILED: " + str(_failed) + " tests")
else:
    print("ALL " + str(_total) + " TESTS PASSED")
