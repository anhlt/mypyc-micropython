"""LVGL Compiled Screen Manager test runner. Runs directly on MicroPython.

Usage: mpremote connect /dev/cu.usbmodem101 run run_lvgl_tests.py

Tests the compiled lvgl_screens module which provides native screen
management functions.
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
    import lvgl_screens as ls

    for _ in range(iterations):
        ls.timer_handler()
        time.sleep_ms(10)


# ---- Compiled Screen Manager Tests ----
suite("lvgl_screens")

try:
    import lvgl as lv
    import lvgl_screens as ls

    # Initialize display
    lv.init_display()
    refresh(10)
    print("  LVGL and lvgl_screens initialized")

    # Test screen creation functions
    scr = ls.create_screen()
    t("create_screen", scr is not None, "True")

    # Test widget creation
    label = ls.create_label(scr, "Test Label")
    t("create_label", label is not None, "True")

    btn = ls.create_button(scr, "Click Me", 120, 40)
    t("create_button", btn is not None, "True")

    slider = ls.create_slider(scr, 0, 100, 50)
    t("create_slider", slider is not None, "True")

    val = ls.get_slider_value(slider)
    t("get_slider_value", val, "50")

    bar = ls.create_bar(scr, 0, 100, 70)
    t("create_bar", bar is not None, "True")

    bar_val = ls.get_bar_value(bar)
    t("get_bar_value", bar_val, "70")

    arc = ls.create_arc(scr, 0, 100, 75)
    t("create_arc", arc is not None, "True")

    arc_val = ls.get_arc_value(arc)
    t("get_arc_value", arc_val, "75")

    # Load and display screen
    ls.screen_load(scr)
    refresh(10)
    t("screen_load", True, "True")

    # Test container with flex layout
    scr2 = ls.create_screen()
    cont = ls.create_container(scr2, 200, 150)
    t("create_container", cont is not None, "True")

    ls.set_flex_column(cont)
    t("set_flex_column", True, "True")

    # Add widgets to container
    ls.create_label(cont, "Title")
    cb = ls.create_checkbox(cont, "Option", True)
    t("create_checkbox", cb is not None, "True")

    sw = ls.create_switch(cont, False)
    t("create_switch", sw is not None, "True")

    ls.screen_load(scr2)
    refresh(10)

    # Test styling
    ls.set_style_bg_color(cont, 0x2196F3, 0)  # Blue background
    t("set_style_bg_color", True, "True")
    refresh(5)

    # Test pre-built screens with proper screen management
    # show_screen(new, old) loads new and deletes old if not None
    home = ls.build_home_screen()
    t("build_home_screen", home is not None, "True")
    ls.show_screen(home, None)  # First screen, no old to delete
    refresh(15)

    slider_scr = ls.build_slider_screen()
    t("build_slider_screen", slider_scr is not None, "True")
    ls.show_screen(slider_scr, home)  # Delete home
    refresh(15)

    progress_scr = ls.build_progress_screen()
    t("build_progress_screen", progress_scr is not None, "True")
    ls.show_screen(progress_scr, slider_scr)  # Delete slider_scr
    refresh(15)

    arc_scr = ls.build_arc_screen()
    t("build_arc_screen", arc_scr is not None, "True")
    ls.show_screen(arc_scr, progress_scr)  # Delete progress_scr
    refresh(15)

    controls_scr = ls.build_controls_screen()
    t("build_controls_screen", controls_scr is not None, "True")
    ls.show_screen(controls_scr, arc_scr)  # Delete arc_scr
    refresh(15)

    # Memory test - cycle through screens
    gc.collect()
    baseline = gc.mem_free()

    old_scr = controls_scr
    for i in range(5):
        new_scr = ls.build_home_screen()
        ls.show_screen(new_scr, old_scr)
        old_scr = new_scr
        refresh(3)

        new_scr = ls.build_slider_screen()
        ls.show_screen(new_scr, old_scr)
        old_scr = new_scr
        refresh(3)

        new_scr = ls.build_progress_screen()
        ls.show_screen(new_scr, old_scr)
        old_scr = new_scr
        refresh(3)
        gc.collect()

    final = gc.mem_free()
    mem_drop = baseline - final
    t("memory stable after screen cycles", mem_drop < 5000, "True")
    print(f"    (mem drop: {mem_drop} bytes)")

    # End with home screen
    final_home = ls.build_home_screen()
    ls.show_screen(final_home, old_scr)
    refresh(20)

except ImportError as e:
    print("SKIP: required modules not available - " + str(e))
except Exception as e:
    print("ERROR: lvgl_screens tests failed - " + str(e))
    import sys

    sys.print_exception(e)
    _failed += 1

# ---- summary ----
gc.collect()
print("@D:" + str(_total) + "|" + str(_passed) + "|" + str(_failed))
if _failed:
    print("FAILED: " + str(_failed) + " tests")
else:
    print("ALL " + str(_total) + " TESTS PASSED")
