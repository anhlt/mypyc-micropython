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
# ---- summary ----
gc.collect()
print("@D:" + str(_total) + "|" + str(_passed) + "|" + str(_failed))
if _failed:
    print("FAILED: " + str(_failed) + " tests")
else:
    print("ALL " + str(_total) + " TESTS PASSED")
