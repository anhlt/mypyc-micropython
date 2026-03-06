import gc
import time

import lvgl as lv
import lvui
# using lvui.screens

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
    for _ in range(iterations):
        lvui.screens.timer_handler()
        time.sleep_ms(10)


def run_mount_dispose_suite():
    suite("mvu_mount_dispose")
    app = lvui.mvu.App(0, 8, 32)

    root = app.mount()
    refresh(5)
    t("mount returns root", root is not None, "True")
    t("mount nav_size", app.nav_size, "1")
    t("mount active is home", app.active_screen_id, str(lvui.mvu.SCREEN_HOME))

    app.dispose()
    refresh(3)
    t("dispose nav_size reset", app.nav_size, "0")
    t("dispose active reset", app.active_screen_id, str(lvui.mvu.SCREEN_HOME))


def run_nav_push_pop_suite():
    suite("mvu_nav_push_pop")
    app = lvui.mvu.App(0, 8, 32)
    app.mount()
    refresh(5)

    app.dispatch(lvui.mvu.MSG_PUSH_SETTINGS)
    app.tick(1, True)
    refresh(2)
    t("push active settings", app.active_screen_id, str(lvui.mvu.SCREEN_SETTINGS))
    t("push nav_size", app.nav_size, "2")

    app.dispatch(lvui.mvu.MSG_POP)
    app.tick(1, True)
    refresh(2)
    t("pop active home", app.active_screen_id, str(lvui.mvu.SCREEN_HOME))
    t("pop nav_size", app.nav_size, "1")

    app.dispatch(lvui.mvu.MSG_PUSH_SETTINGS)
    app.tick(1, True)
    app.dispatch(lvui.mvu.MSG_REPLACE_HOME)
    app.tick(1, True)
    refresh(2)
    t("replace active home", app.active_screen_id, str(lvui.mvu.SCREEN_HOME))

    app.dispose()


def run_memory_soak_tick_20000_suite():
    suite("mvu_memory_soak_tick_20000")
    app = lvui.mvu.App(0, 8, 32)
    app.mount()

    gc.collect()
    baseline = gc.mem_free()
    min_free = baseline

    for i in range(20000):
        app.dispatch(lvui.mvu.MSG_INCREMENT)
        app.tick(1, True)

        if i % 128 == 0:
            gc.collect()
            free_now = gc.mem_free()
            if free_now < min_free:
                min_free = free_now

    app.dispose()
    gc.collect()
    mem_drop = baseline - min_free
    t("mvu_memory_soak_tick_20000", mem_drop < 4096, "True")
    print("    (mem drop: " + str(mem_drop) + " bytes)")


def run_memory_soak_nav_2000_suite():
    suite("mvu_memory_soak_nav_2000")
    app = lvui.mvu.App(0, 8, 32)
    app.mount()

    gc.collect()
    baseline = gc.mem_free()
    min_free = baseline

    for i in range(2000):
        mod = i % 3
        if mod == 0:
            app.dispatch(lvui.mvu.MSG_PUSH_SETTINGS)
        elif mod == 1:
            app.dispatch(lvui.mvu.MSG_POP)
        else:
            app.dispatch(lvui.mvu.MSG_REPLACE_HOME)

        app.tick(1, True)
        app.dispatch(lvui.mvu.MSG_INCREMENT)
        app.tick(1, True)

        if i % 64 == 0:
            gc.collect()
            free_now = gc.mem_free()
            if free_now < min_free:
                min_free = free_now

    app.dispose()
    gc.collect()
    mem_drop = baseline - min_free
    t("mvu_memory_soak_nav_2000", mem_drop < 6144, "True")
    print("    (mem drop: " + str(mem_drop) + " bytes)")


def run_remount_no_drift_suite():
    suite("mvu_remount_no_drift")
    app = lvui.mvu.App(0, 8, 32)

    gc.collect()
    baseline = gc.mem_free()
    min_free = baseline

    for i in range(500):
        app.mount()
        app.dispatch(lvui.mvu.MSG_INCREMENT)
        app.tick(1, True)
        app.dispose()

        if i % 50 == 0:
            gc.collect()
            free_now = gc.mem_free()
            if free_now < min_free:
                min_free = free_now

    gc.collect()
    drift = baseline - min_free
    t("mvu_remount_no_drift", drift < 1024, "True")
    print("    (drift: " + str(drift) + " bytes)")


def main():
    global _failed

    try:
        lv.init_display()
        refresh(10)

        run_mount_dispose_suite()
        run_nav_push_pop_suite()
        run_memory_soak_tick_20000_suite()
        run_memory_soak_nav_2000_suite()
        run_remount_no_drift_suite()

    except Exception as e:
        print("ERROR: lvgl_mvu tests failed - " + str(e))
        import sys

        sys.print_exception(e)
        _failed += 1

    gc.collect()
    print("@D:" + str(_total) + "|" + str(_passed) + "|" + str(_failed))
    if _failed:
        print("FAILED: " + str(_failed) + " tests")
    else:
        print("ALL " + str(_total) + " TESTS PASSED")


main()
