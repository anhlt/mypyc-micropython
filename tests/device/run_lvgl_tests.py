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
# ---- summary ----
gc.collect()
print("@D:" + str(_total) + "|" + str(_passed) + "|" + str(_failed))
if _failed:
    print("FAILED: " + str(_failed) + " tests")
else:
    print("ALL " + str(_total) + " TESTS PASSED")
