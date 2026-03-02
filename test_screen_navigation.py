"""Test ScreenManager navigation with compiled lvgl_screens module.

This test combines:
- Pure Python ScreenManager for navigation logic (tree structure)
- Compiled lvgl_screens module for native screen building performance

Usage: mpremote connect /dev/cu.usbmodem101 run test_screen_navigation.py
"""

import gc
import time


# ============================================================================
# ScreenNode and ScreenManager (pure Python for tree navigation)
# ============================================================================


class ScreenNode:
    """Node in the screen tree."""

    def __init__(self, name, screen_factory, children=None):
        self.name = name
        self.screen_factory = screen_factory
        self.children = children if children is not None else []


class ScreenManager:
    """Manages navigation through a tree of screens."""

    def __init__(self, root):
        self._root = root
        self._current = root
        self._parent_map = {}  # id(node) -> parent node
        self._current_screen = None
        self._started = False
        self._build_parent_map(root, None)

    def _build_parent_map(self, node, parent):
        """Build parent lookup map for back navigation."""
        self._parent_map[id(node)] = parent
        for child in node.children:
            self._build_parent_map(child, node)

    def start(self):
        """Start navigation at root screen."""
        self._current = self._root
        self._current_screen = self._load_screen(self._root)
        self._started = True
        return self._current_screen

    def goto(self, child_name):
        """Navigate to a child screen by name."""
        if not self._started:
            raise RuntimeError("Call start() first")

        # Find child
        target = None
        for child in self._current.children:
            if child.name == child_name:
                target = child
                break

        if target is None:
            names = [c.name for c in self._current.children]
            raise ValueError(f"No child '{child_name}'. Available: {names}")

        # Navigate
        old_screen = self._current_screen
        self._current_screen = self._load_screen(target)
        self._current = target

        # Cleanup old screen
        if old_screen is not None:
            self._delete_screen(old_screen)

        return self._current_screen

    def back(self):
        """Navigate back to parent screen."""
        if not self._started:
            raise RuntimeError("Call start() first")

        parent = self._parent_map.get(id(self._current))
        if parent is None:
            # Already at root
            return self._current_screen

        old_screen = self._current_screen
        self._current_screen = self._load_screen(parent)
        self._current = parent

        if old_screen is not None:
            self._delete_screen(old_screen)

        return self._current_screen

    def current_name(self):
        """Get current screen name."""
        return self._current.name

    def _load_screen(self, node):
        """Load screen using node's factory and display it."""
        import lvgl_screens as ls

        screen = node.screen_factory()
        ls.screen_load(screen)
        return screen

    def _delete_screen(self, screen):
        """Delete a screen object."""
        import lvgl_screens as ls

        ls.obj_delete(screen)


# ============================================================================
# Screen Factories (using compiled lvgl_screens)
# ============================================================================


def build_home():
    """Build home screen with navigation options."""
    import lvgl_screens as ls

    scr = ls.create_screen()
    cont = ls.create_container(scr, 280, 200)
    ls.set_flex_column(cont)

    ls.create_label(cont, "HOME")
    ls.create_label(cont, "")
    ls.create_button(cont, "-> Settings", 150, 35)
    ls.create_button(cont, "-> About", 150, 35)

    return scr


def build_settings():
    """Build settings screen."""
    import lvgl_screens as ls

    scr = ls.create_screen()
    cont = ls.create_container(scr, 280, 200)
    ls.set_flex_column(cont)

    ls.create_label(cont, "SETTINGS")
    ls.create_label(cont, "")
    ls.create_slider(scr, 0, 100, 50)
    ls.create_checkbox(cont, "Option A", True)
    ls.create_checkbox(cont, "Option B", False)

    return scr


def build_about():
    """Build about screen."""
    import lvgl_screens as ls

    scr = ls.create_screen()
    cont = ls.create_container(scr, 280, 200)
    ls.set_flex_column(cont)

    ls.create_label(cont, "ABOUT")
    ls.create_label(cont, "")
    ls.create_label(cont, "mypyc-micropython")
    ls.create_label(cont, "Compiled Screen Manager")
    ls.create_label(cont, "v1.0")

    return scr


def build_deep_child():
    """Build a deeper nested screen."""
    import lvgl_screens as ls

    scr = ls.create_screen()
    cont = ls.create_container(scr, 280, 200)
    ls.set_flex_column(cont)

    ls.create_label(cont, "DEEP CHILD")
    ls.create_label(cont, "")
    ls.create_label(cont, "3 levels deep")
    ls.create_arc(scr, 0, 100, 75)

    return scr


# ============================================================================
# Test Runner
# ============================================================================


def refresh(n=10):
    """Run LVGL timer handler."""
    import lvgl_screens as ls

    for _ in range(n):
        ls.timer_handler()
        time.sleep_ms(10)


def test_navigation():
    """Test ScreenManager navigation."""
    import lvgl as lv
    import lvgl_screens as ls

    print("=== ScreenManager Navigation Test ===")
    print()

    # Initialize display
    lv.init_display()
    refresh(10)
    print("Display initialized")

    # Build screen tree:
    #   home
    #   ├── settings
    #   │   └── deep_child
    #   └── about

    deep_child = ScreenNode("deep_child", build_deep_child)
    settings = ScreenNode("settings", build_settings, children=[deep_child])
    about = ScreenNode("about", build_about)
    home = ScreenNode("home", build_home, children=[settings, about])

    # Create manager
    mgr = ScreenManager(home)
    print("ScreenManager created")
    print()

    # Track memory
    gc.collect()
    mem_start = gc.mem_free()

    # Test navigation
    tests_passed = 0
    tests_total = 0

    def check(name, condition):
        nonlocal tests_passed, tests_total
        tests_total += 1
        if condition:
            tests_passed += 1
            print(f"  OK: {name}")
        else:
            print(f"FAIL: {name}")

    # 1. Start at home
    print("1. Starting at home...")
    mgr.start()
    refresh(15)
    check("start() returns screen", mgr._current_screen is not None)
    check("current is 'home'", mgr.current_name() == "home")

    # 2. Navigate to settings
    print("2. Navigating to settings...")
    mgr.goto("settings")
    refresh(15)
    check("current is 'settings'", mgr.current_name() == "settings")

    # 3. Navigate deeper to deep_child
    print("3. Navigating to deep_child...")
    mgr.goto("deep_child")
    refresh(15)
    check("current is 'deep_child'", mgr.current_name() == "deep_child")

    # 4. Back to settings
    print("4. Going back to settings...")
    mgr.back()
    refresh(15)
    check("current is 'settings'", mgr.current_name() == "settings")

    # 5. Back to home
    print("5. Going back to home...")
    mgr.back()
    refresh(15)
    check("current is 'home'", mgr.current_name() == "home")

    # 6. Navigate to about
    print("6. Navigating to about...")
    mgr.goto("about")
    refresh(15)
    check("current is 'about'", mgr.current_name() == "about")

    # 7. Back to home
    print("7. Going back to home...")
    mgr.back()
    refresh(15)
    check("current is 'home'", mgr.current_name() == "home")

    # 8. Try back at root (should stay at home)
    print("8. Trying back at root...")
    mgr.back()
    refresh(10)
    check("still at 'home' (root)", mgr.current_name() == "home")

    # 9. Memory stability - cycle through screens
    print("9. Memory stability test (10 navigation cycles)...")
    gc.collect()
    mem_before_cycles = gc.mem_free()

    for i in range(10):
        mgr.goto("settings")
        refresh(3)
        mgr.goto("deep_child")
        refresh(3)
        mgr.back()
        refresh(3)
        mgr.back()
        refresh(3)
        mgr.goto("about")
        refresh(3)
        mgr.back()
        refresh(3)
        gc.collect()

    gc.collect()
    mem_after_cycles = gc.mem_free()
    mem_leaked = mem_before_cycles - mem_after_cycles
    check(f"memory stable (leaked: {mem_leaked} bytes)", mem_leaked < 2000)

    # 10. Error handling - invalid child
    print("10. Error handling - invalid child...")
    try:
        mgr.goto("nonexistent")
        check("raises ValueError for invalid child", False)
    except ValueError as e:
        check("raises ValueError for invalid child", True)
        print(f"      (error: {e})")

    # Summary
    print()
    print("=" * 40)
    gc.collect()
    mem_end = gc.mem_free()
    print(f"Memory: start={mem_start}, end={mem_end}, diff={mem_start - mem_end}")
    print(f"Tests: {tests_passed}/{tests_total} passed")

    if tests_passed == tests_total:
        print("ALL TESTS PASSED!")
    else:
        print(f"FAILED: {tests_total - tests_passed} tests")

    # Leave on home screen
    if mgr.current_name() != "home":
        mgr.back()
    refresh(20)

    return tests_passed == tests_total


if __name__ == "__main__":
    test_navigation()
