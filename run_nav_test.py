"""Visual Navigation Test - Stack-based navigation with smooth transitions.

Usage: mpremote connect /dev/cu.usbmodem101 run run_nav_test.py

Uses a navigation stack with animated screen transitions:
  Push: Home -> Settings -> Display (slide from right)
  Pop:  Display -> Settings -> Home (slide from left)

Each screen shows the navigation stack in top-left corner.
FPS counter displayed in bottom-right during animations.
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

# Animation duration in ms
ANIM_TIME = 400  # Increased for smoother transitions

# Screen load animation types (from lv_scr_load_anim_t)
ANIM_OVER_LEFT = 1    # New screen slides over from right
ANIM_OVER_RIGHT = 2   # New screen slides over from left  
ANIM_FADE_IN = 9      # New screen fades in


class ScreenManager:
    """Stack-based screen navigation with smooth transitions."""

    def __init__(self):
        self.stack = []  # List of (name, screen_obj)
        self.lv = None
        self.ls = None
        self.fps_label = None  # FPS counter label
        self.last_fps = 0

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

    def _create_fps_overlay(self):
        """Create FPS counter on top layer - floats above all screens."""
        # Use lv_layer_top() so FPS counter persists across screen transitions
        top_layer = self.lv.lv_layer_top()
        self.fps_label = self.lv.lv_label_create(top_layer)
        self.lv.lv_label_set_text(self.fps_label, "FPS: --")
        self.lv.lv_obj_align(self.fps_label, self.lv.LV_ALIGN_BOTTOM_RIGHT, -10, -10)
        self.lv.lv_obj_set_style_text_color(self.fps_label, self.lv.lv_color_hex(0xFFFF00), 0)  # Yellow
        self.lv.lv_obj_set_style_bg_color(self.fps_label, self.lv.lv_color_hex(0x000000), 0)
        self.lv.lv_obj_set_style_bg_opa(self.fps_label, 180, 0)  # Semi-transparent black bg
        self.lv.lv_obj_set_style_pad_all(self.fps_label, 4, 0)

    def _update_fps(self, fps):
        """Update FPS counter display."""
        if self.fps_label:
            self.lv.lv_label_set_text(self.fps_label, "FPS: " + str(fps))
            self.last_fps = fps

    def _delete_fps_overlay(self):
        """Remove FPS counter."""
        if self.fps_label:
            self.lv.lv_obj_delete(self.fps_label)
            self.fps_label = None

    def _create_screen(self, name: str):
        """Create a screen with stack history in top-left."""
        color = SCREEN_COLORS.get(name, 0x333333)

        screen = self.ls.create_screen()
        self.lv.lv_obj_set_style_bg_color(screen, self.lv.lv_color_hex(color), 0)

        # Navigation stack indicator (top-left)
        stack_text = self._get_stack_text()
        if stack_text:
            nav_label = self.lv.lv_label_create(screen)
            self.lv.lv_label_set_text(nav_label, "< " + stack_text)
            self.lv.lv_obj_align(nav_label, self.lv.LV_ALIGN_TOP_LEFT, 10, 10)
            self.lv.lv_obj_set_style_text_color(nav_label, self.lv.lv_color_hex(0xCCCCCC), 0)

        # Current screen title (center)
        title = self.lv.lv_label_create(screen)
        self.lv.lv_label_set_text(title, name)
        self.lv.lv_obj_center(title)
        self.lv.lv_obj_set_style_text_color(title, self.lv.lv_color_hex(0xFFFFFF), 0)

        # Stack depth indicator (bottom-left, moved from bottom-right for FPS)
        depth_label = self.lv.lv_label_create(screen)
        depth = len(self.stack) + 1
        self.lv.lv_label_set_text(depth_label, "[" + str(depth) + "]")
        self.lv.lv_obj_align(depth_label, self.lv.LV_ALIGN_BOTTOM_LEFT, 10, -10)
        self.lv.lv_obj_set_style_text_color(depth_label, self.lv.lv_color_hex(0x888888), 0)

        return screen

    def _animate_transition(self, duration_ms):
        """Run animation loop with FPS counting."""
        start = time.ticks_ms()
        frame_count = 0
        total_frames = 0
        fps_update_interval = 50  # Update FPS display every 50ms
        last_fps_update = start
        
        # Run animation for full duration + extra time to ensure completion
        end_time = duration_ms + 100  # Extra 100ms to ensure animation completes
        while time.ticks_diff(time.ticks_ms(), start) < end_time:
            self.ls.timer_handler()
            frame_count += 1
            total_frames += 1
            
            # Update FPS counter periodically
            now = time.ticks_ms()
            elapsed_since_fps = time.ticks_diff(now, last_fps_update)
            if elapsed_since_fps >= fps_update_interval:
                fps = (frame_count * 1000) // max(1, elapsed_since_fps)
                self._update_fps(fps)
                frame_count = 0
                last_fps_update = now
        
        # Calculate average FPS
        total_time = time.ticks_diff(time.ticks_ms(), start)
        if total_time > 0:
            avg_fps = (total_frames * 1000) // total_time
            self._update_fps(avg_fps)
            return avg_fps
        return 0

    def push(self, name: str):
        """Push a new screen with slide-over animation."""
        # Create FPS overlay once on first push (on top layer)
        if not self.fps_label:
            self._create_fps_overlay()
        
        screen = self._create_screen(name)
        self.stack.append((name, screen))
        
        # Use OVER_LEFT animation - new screen slides over from right
        self.lv.lv_screen_load_anim(screen, ANIM_OVER_LEFT, ANIM_TIME, 0, False)
        fps = self._animate_transition(ANIM_TIME)
        
        return screen

    def pop(self):
        """Pop current screen with slide-over animation."""
        if len(self.stack) <= 1:
            return None

        # Remove current screen
        name, screen = self.stack.pop()

        # Show previous screen with OVER_RIGHT animation - slides over from left
        if self.stack:
            prev_name, prev_screen = self.stack[-1]
            self.lv.lv_screen_load_anim(prev_screen, ANIM_OVER_RIGHT, ANIM_TIME, 0, False)
            fps = self._animate_transition(ANIM_TIME)

        # Delete old screen after animation
        self.lv.lv_obj_delete(screen)
        gc.collect()

        if self.stack:
            return self.stack[-1][0]
        return None

    def cleanup(self):
        """Delete all screens."""
        self._delete_fps_overlay()
        while self.stack:
            _, screen = self.stack.pop()
            self.lv.lv_obj_delete(screen)
        gc.collect()


# ---- Navigation Test ----
suite("nav_smooth")

try:
    sm = ScreenManager()
    sm.init()
    print("  ScreenManager initialized (smooth transitions + FPS counter)")

    print("\n  === PUSH Phase (slide from right) ===")
    print("  Stack grows: Home -> Settings -> Display\n")

    mem_start = gc.mem_free()

    # Push Home (no animation for first screen)
    sm.push("Home")
    print("  [PUSH] Home          | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("push_home", len(sm.stack), "1")
    time.sleep(1)

    # Push Settings (slide from right)
    sm.push("Settings")
    print("  [PUSH] Settings      | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("push_settings", len(sm.stack), "2")
    time.sleep(1)

    # Push Display (slide from right)
    sm.push("Display")
    print("  [PUSH] Display       | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("push_display", len(sm.stack), "3")
    time.sleep(1)

    print("\n  === POP Phase (slide to right) ===")
    print("  Stack shrinks: Display -> Settings -> Home\n")

    # Pop back to Settings (slide to right)
    popped = sm.pop()
    print("  [POP]  -> " + str(popped) + "    | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("pop_to_settings", popped, "Settings")
    time.sleep(1)

    # Pop back to Home (slide to right)
    popped = sm.pop()
    print("  [POP]  -> " + str(popped) + "       | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("pop_to_home", popped, "Home")
    time.sleep(1)

    # Try to pop past root
    popped = sm.pop()
    t("pop_at_root", popped is None, "True")

    # Cleanup
    sm.cleanup()

    mem_end = gc.mem_free()
    mem_diff = mem_start - mem_end
    print("\n  Memory: start=" + str(mem_start) + ", end=" + str(mem_end) + ", diff=" + str(mem_diff))
    t("memory_stable", abs(mem_diff) < 2000, "True")

except Exception as e:
    import sys
    sys.print_exception(e)
    print("FAIL: nav_smooth exception: " + str(e))
    _failed += 1

# ---- Summary ----
print("\n" + "=" * 40)
print("Smooth Navigation Test Results")
print("=" * 40)
print("Total:  " + str(_total))
print("Passed: " + str(_passed))
print("Failed: " + str(_failed))
print("=" * 40)

if _failed == 0:
    print("ALL TESTS PASSED")
else:
    print("FAILURES: " + str(_failed))
