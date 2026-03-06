import gc
import time

import lvgl as lv
import lvui

# using lvui.screens

SCREEN_HOME = 0
SCREEN_SETTINGS = 1
SCREEN_ABOUT = 2
SCREEN_DEEP_CHILD = 3

SCREEN_NAMES = {
    SCREEN_HOME: "home",
    SCREEN_SETTINGS: "settings",
    SCREEN_ABOUT: "about",
    SCREEN_DEEP_CHILD: "deep_child",
}

ALLOWED_CHILDREN: tuple[tuple[int, tuple[int, ...]], ...] = (
    (SCREEN_HOME, (SCREEN_SETTINGS, SCREEN_ABOUT)),
    (SCREEN_SETTINGS, (SCREEN_DEEP_CHILD,)),
    (SCREEN_ABOUT, ()),
    (SCREEN_DEEP_CHILD, ()),
)


def build_home():
    scr = lvui.screens.create_screen()
    cont = lvui.screens.create_container(scr, 280, 200)
    lvui.screens.set_flex_column(cont)

    lvui.screens.create_label(cont, "HOME")
    lvui.screens.create_label(cont, "")
    lvui.screens.create_button(cont, "-> Settings", 150, 35)
    lvui.screens.create_button(cont, "-> About", 150, 35)
    return scr


def build_settings():
    scr = lvui.screens.create_screen()
    cont = lvui.screens.create_container(scr, 280, 200)
    lvui.screens.set_flex_column(cont)

    lvui.screens.create_label(cont, "SETTINGS")
    lvui.screens.create_label(cont, "")
    lvui.screens.create_slider(scr, 0, 100, 50)
    lvui.screens.create_checkbox(cont, "Option A", True)
    lvui.screens.create_checkbox(cont, "Option B", False)
    return scr


def build_about():
    scr = lvui.screens.create_screen()
    cont = lvui.screens.create_container(scr, 280, 200)
    lvui.screens.set_flex_column(cont)

    lvui.screens.create_label(cont, "ABOUT")
    lvui.screens.create_label(cont, "")
    lvui.screens.create_label(cont, "mypyc-micropython")
    lvui.screens.create_label(cont, "Compiled Screen Manager")
    lvui.screens.create_label(cont, "v1.0")
    return scr


def build_deep_child():
    scr = lvui.screens.create_screen()
    cont = lvui.screens.create_container(scr, 280, 200)
    lvui.screens.set_flex_column(cont)

    lvui.screens.create_label(cont, "DEEP CHILD")
    lvui.screens.create_label(cont, "")
    lvui.screens.create_label(cont, "3 levels deep")
    lvui.screens.create_arc(scr, 0, 100, 75)
    return scr


BUILDERS = (
    (SCREEN_HOME, build_home),
    (SCREEN_SETTINGS, build_settings),
    (SCREEN_ABOUT, build_about),
    (SCREEN_DEEP_CHILD, build_deep_child),
)


class ScreenManager:
    def __init__(self):
        self.nav = lvui.nav.Nav(
            nav_capacity=8, builders=BUILDERS, allowed_children=ALLOWED_CHILDREN
        )
        self._stack = []

    def start(self):
        self._stack = [SCREEN_HOME]
        return self.nav.init_root(SCREEN_HOME)

    def goto(self, child_id):
        self._ensure_started()
        self._stack.append(child_id)
        return self.nav.push(child_id)

    def back(self):
        self._ensure_started()
        if len(self._stack) <= 1:
            return self.nav.pop()

        self._stack.pop()
        return self.nav.pop()

    def current_name(self):
        if not self._stack:
            return "<none>"
        return SCREEN_NAMES[self._stack[-1]]

    def _ensure_started(self):
        if not self._stack:
            raise RuntimeError("Call start() first")


def refresh(n=10):
    for _ in range(n):
        lvui.screens.timer_handler()
        time.sleep_ms(10)


def test_navigation():
    print("=== ScreenManager Navigation Test ===")
    print()

    lv.init_display()
    refresh(10)
    print("Display initialized")

    mgr = ScreenManager()
    print("ScreenManager created")
    print()

    gc.collect()
    mem_start = gc.mem_free()

    tests_passed = 0
    tests_total = 0

    def check(name, condition):
        nonlocal tests_passed, tests_total
        tests_total += 1
        if condition:
            tests_passed += 1
            print("  OK: " + name)
        else:
            print("FAIL: " + name)

    print("1. Starting at home...")
    mgr.start()
    refresh(15)
    check("start() returns screen", lvui.screens.screen_active() is not None)
    check("current is 'home'", mgr.current_name() == "home")

    print("2. Navigating to settings...")
    mgr.goto(SCREEN_SETTINGS)
    refresh(15)
    check("current is 'settings'", mgr.current_name() == "settings")

    print("3. Navigating to deep_child...")
    mgr.goto(SCREEN_DEEP_CHILD)
    refresh(15)
    check("current is 'deep_child'", mgr.current_name() == "deep_child")

    print("4. Going back to settings...")
    mgr.back()
    refresh(15)
    check("current is 'settings'", mgr.current_name() == "settings")

    print("5. Going back to home...")
    mgr.back()
    refresh(15)
    check("current is 'home'", mgr.current_name() == "home")

    print("6. Navigating to about...")
    mgr.goto(SCREEN_ABOUT)
    refresh(15)
    check("current is 'about'", mgr.current_name() == "about")

    print("7. Going back to home...")
    mgr.back()
    refresh(15)
    check("current is 'home'", mgr.current_name() == "home")

    print("8. Trying back at root...")
    mgr.back()
    refresh(10)
    check("still at 'home' (root)", mgr.current_name() == "home")

    print("9. Memory stability test (10 navigation cycles)...")
    gc.collect()
    mem_before_cycles = gc.mem_free()

    for _ in range(10):
        mgr.goto(SCREEN_SETTINGS)
        refresh(3)
        mgr.goto(SCREEN_DEEP_CHILD)
        refresh(3)
        mgr.back()
        refresh(3)
        mgr.back()
        refresh(3)
        mgr.goto(SCREEN_ABOUT)
        refresh(3)
        mgr.back()
        refresh(3)
        gc.collect()

    gc.collect()
    mem_after_cycles = gc.mem_free()
    mem_leaked = mem_before_cycles - mem_after_cycles
    check("memory stable (leaked: " + str(mem_leaked) + " bytes)", mem_leaked < 2000)

    print("10. Error handling - invalid child...")
    try:
        mgr.goto(99)
        check("raises ValueError for invalid child", False)
    except ValueError as e:
        check("raises ValueError for invalid child", str(e) == "invalid screen id: 99")
        print("      (error: " + str(e) + ")")

    print()
    print("=" * 40)
    gc.collect()
    mem_end = gc.mem_free()
    print(
        "Memory: start="
        + str(mem_start)
        + ", end="
        + str(mem_end)
        + ", diff="
        + str(mem_start - mem_end)
    )
    print("Tests: " + str(tests_passed) + "/" + str(tests_total) + " passed")

    if tests_passed == tests_total:
        print("ALL TESTS PASSED!")
    else:
        print("FAILED: " + str(tests_total - tests_passed) + " tests")

    if mgr.current_name() != "home":
        mgr.back()
    refresh(20)

    return tests_passed == tests_total


if __name__ == "__main__":
    test_navigation()
