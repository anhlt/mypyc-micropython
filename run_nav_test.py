"""Visual Navigation Test - Stack-based navigation with history display.

Usage: mpremote connect /dev/cu.usbmodem101 run run_nav_test.py

Uses a navigation stack:
  Push: Home -> Settings -> Display
  Pop:  Display -> Settings -> Home (back navigation)

Each screen shows the navigation stack in top-left corner.
2-second delays between transitions for visual verification.
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


# ---- Screen Colors ----
COLOR_HOME = 0x2196F3      # Blue
COLOR_SETTINGS = 0x4CAF50  # Green
COLOR_DISPLAY = 0xFF9800   # Orange

SCREEN_COLORS = {
    "Home": COLOR_HOME,
    "Settings": COLOR_SETTINGS,
    "Display": COLOR_DISPLAY,
}


class ScreenManager:
    """Stack-based screen navigation."""

    def __init__(self):
        self.stack = []  # List of (name, screen_obj)
        self.lv = None
        self.ls = None

    def init(self):
        import lvgl as lv
        import lvgl_screens as ls
        self.lv = lv
        self.ls = ls
        lv.init_display()
        refresh(10)

    def _get_stack_text(self):
        """Get navigation path as text: Home > Settings > Display"""
        if not self.stack:
            return ""
        return " > ".join(name for name, _ in self.stack)

    def _create_screen(self, name: str):
        """Create a screen with stack history in top-left."""
        color = SCREEN_COLORS.get(name, 0x333333)

        screen = self.ls.create_screen()
        self.lv.lv_obj_set_style_bg_color(screen, self.lv.lv_color_hex(color), 0)

        # Navigation stack indicator (top-left)
        stack_text = self._get_stack_text()
        if stack_text:
            # Show: "< Home > Settings" for back navigation hint
            nav_label = self.lv.lv_label_create(screen)
            self.lv.lv_label_set_text(nav_label, "< " + stack_text)
            self.lv.lv_obj_align(nav_label, self.lv.LV_ALIGN_TOP_LEFT, 10, 10)
            self.lv.lv_obj_set_style_text_color(nav_label, self.lv.lv_color_hex(0xCCCCCC), 0)

        # Current screen title (center)
        title = self.lv.lv_label_create(screen)
        self.lv.lv_label_set_text(title, name)
        self.lv.lv_obj_center(title)
        self.lv.lv_obj_set_style_text_color(title, self.lv.lv_color_hex(0xFFFFFF), 0)

        # Stack depth indicator (bottom-right)
        depth_label = self.lv.lv_label_create(screen)
        depth = len(self.stack) + 1
        self.lv.lv_label_set_text(depth_label, "[" + str(depth) + "]")
        self.lv.lv_obj_align(depth_label, self.lv.LV_ALIGN_BOTTOM_RIGHT, -10, -10)
        self.lv.lv_obj_set_style_text_color(depth_label, self.lv.lv_color_hex(0x888888), 0)

        return screen

    def push(self, name: str):
        """Push a new screen onto the stack."""
        screen = self._create_screen(name)
        self.stack.append((name, screen))
        self.ls.screen_load(screen)
        refresh(20)
        return screen

    def pop(self):
        """Pop current screen and go back to previous."""
        if len(self.stack) <= 1:
            return None  # Can't pop the root screen

        # Remove and delete current screen
        name, screen = self.stack.pop()
        self.lv.lv_obj_delete(screen)
        gc.collect()

        # Show previous screen (it's still in stack)
        if self.stack:
            prev_name, prev_screen = self.stack[-1]
            self.ls.screen_load(prev_screen)
            refresh(20)
            return prev_name
        return None

    def cleanup(self):
        """Delete all screens."""
        while self.stack:
            _, screen = self.stack.pop()
            self.lv.lv_obj_delete(screen)
        gc.collect()


# ---- Navigation Test ----
suite("nav_stack")

try:
    sm = ScreenManager()
    sm.init()
    print("  ScreenManager initialized")

    print("\n  === PUSH Phase (forward navigation) ===")
    print("  Stack grows: Home -> Settings -> Display\n")

    mem_start = gc.mem_free()

    # Push Home
    sm.push("Home")
    print("  [PUSH] Home          | Stack: " + sm._get_stack_text())
    t("push_home", len(sm.stack), "1")
    time.sleep(2)

    # Push Settings
    sm.push("Settings")
    print("  [PUSH] Settings      | Stack: " + sm._get_stack_text())
    t("push_settings", len(sm.stack), "2")
    time.sleep(2)

    # Push Display
    sm.push("Display")
    print("  [PUSH] Display       | Stack: " + sm._get_stack_text())
    t("push_display", len(sm.stack), "3")
    time.sleep(2)

    print("\n  === POP Phase (back navigation) ===")
    print("  Stack shrinks: Display -> Settings -> Home\n")

    # Pop back to Settings
    popped = sm.pop()
    print("  [POP]  -> " + str(popped) + "    | Stack: " + sm._get_stack_text())
    t("pop_to_settings", popped, "Settings")
    time.sleep(2)

    # Pop back to Home
    popped = sm.pop()
    print("  [POP]  -> " + str(popped) + "       | Stack: " + sm._get_stack_text())
    t("pop_to_home", popped, "Home")
    time.sleep(2)

    # Try to pop past root (should fail gracefully)
    popped = sm.pop()
    t("pop_at_root", popped is None, "True")

    # Cleanup
    sm.cleanup()

    mem_end = gc.mem_free()
    mem_diff = mem_start - mem_end
    print("\n  Memory: start=" + str(mem_start) + ", end=" + str(mem_end) + ", diff=" + str(mem_diff))
    t("memory_stable", abs(mem_diff) < 1000, "True")

except Exception as e:
    import sys
    sys.print_exception(e)
    print("FAIL: nav_stack exception: " + str(e))
    _failed += 1

# ---- Summary ----
print("\n" + "=" * 40)
print("Stack Navigation Test Results")
print("=" * 40)
print("Total:  " + str(_total))
print("Passed: " + str(_passed))
print("Failed: " + str(_failed))
print("=" * 40)

if _failed == 0:
    print("ALL TESTS PASSED")
else:
    print("FAILURES: " + str(_failed))
