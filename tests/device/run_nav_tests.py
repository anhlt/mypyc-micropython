import gc
import time

import lvgl as lv
import lvgl_nav
import lvgl_screens as ls

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
        ls.timer_handler()
        time.sleep_ms(10)


class ScreenManager:
    def __init__(self):
        self.stack = []
        self.fps_label = None
        self.last_fps = 0

        self.SCREEN_HOME = 0
        self.SCREEN_SETTINGS = 1
        self.SCREEN_DISPLAY = 2

        self._id_to_name = {
            self.SCREEN_HOME: "Home",
            self.SCREEN_SETTINGS: "Settings",
            self.SCREEN_DISPLAY: "Display",
        }
        self._name_to_id = {
            "Home": self.SCREEN_HOME,
            "Settings": self.SCREEN_SETTINGS,
            "Display": self.SCREEN_DISPLAY,
        }
        self._colors = {
            self.SCREEN_HOME: 0x2196F3,
            self.SCREEN_SETTINGS: 0x4CAF50,
            self.SCREEN_DISPLAY: 0xFF9800,
        }
        builders = (
            (self.SCREEN_HOME, self._build_home),
            (self.SCREEN_SETTINGS, self._build_settings),
            (self.SCREEN_DISPLAY, self._build_display),
        )
        self.nav = lvgl_nav.Nav(8, builders, None)

    def init(self):
        lv.init_display()
        refresh(10)

    def _get_stack_text(self):
        if not self.stack:
            return ""
        return " > ".join(self._id_to_name[sid] for sid in self.stack)

    def _create_fps_overlay(self):
        top_layer = lv.lv_layer_top()
        self.fps_label = lv.lv_label_create(top_layer)
        lv.lv_label_set_text(self.fps_label, "FPS: --")
        lv.lv_obj_align(self.fps_label, lv.LV_ALIGN_BOTTOM_RIGHT, -10, -10)
        lv.lv_obj_set_style_text_color(self.fps_label, lv.lv_color_hex(0xFFFF00), 0)
        lv.lv_obj_set_style_bg_color(self.fps_label, lv.lv_color_hex(0x000000), 0)
        lv.lv_obj_set_style_bg_opa(self.fps_label, 180, 0)
        lv.lv_obj_set_style_pad_all(self.fps_label, 4, 0)

    def _update_fps(self, fps):
        if self.fps_label:
            lv.lv_label_set_text(self.fps_label, "FPS: " + str(fps))
            self.last_fps = fps

    def _delete_fps_overlay(self):
        if self.fps_label:
            lv.lv_obj_delete(self.fps_label)
            self.fps_label = None

    def _create_screen(self, screen_id):
        color = self._colors.get(screen_id, 0x333333)
        name = self._id_to_name[screen_id]

        screen = ls.create_screen()
        lv.lv_obj_set_style_bg_color(screen, lv.lv_color_hex(color), 0)

        stack_text = self._get_stack_text()
        if stack_text:
            nav_label = lv.lv_label_create(screen)
            lv.lv_label_set_text(nav_label, "< " + stack_text)
            lv.lv_obj_align(nav_label, lv.LV_ALIGN_TOP_LEFT, 10, 10)
            lv.lv_obj_set_style_text_color(nav_label, lv.lv_color_hex(0xCCCCCC), 0)

        title = lv.lv_label_create(screen)
        lv.lv_label_set_text(title, name)
        lv.lv_obj_center(title)
        lv.lv_obj_set_style_text_color(title, lv.lv_color_hex(0xFFFFFF), 0)

        depth_label = lv.lv_label_create(screen)
        depth = len(self.stack) + 1
        lv.lv_label_set_text(depth_label, "[" + str(depth) + "]")
        lv.lv_obj_align(depth_label, lv.LV_ALIGN_BOTTOM_LEFT, 10, -10)
        lv.lv_obj_set_style_text_color(depth_label, lv.lv_color_hex(0x888888), 0)

        return screen

    def _build_home(self):
        return self._create_screen(self.SCREEN_HOME)

    def _build_settings(self):
        return self._create_screen(self.SCREEN_SETTINGS)

    def _build_display(self):
        return self._create_screen(self.SCREEN_DISPLAY)

    def _update_op_fps(self, start_ms):
        elapsed = max(1, time.ticks_diff(time.ticks_ms(), start_ms))
        fps = 1000 // elapsed
        self._update_fps(fps)

    def _name_to_screen_id(self, name):
        if name in self._name_to_id:
            return self._name_to_id[name]
        raise ValueError("invalid screen id: " + str(name))

    def push(self, name):
        if not self.fps_label:
            self._create_fps_overlay()

        screen_id = self._name_to_screen_id(name)
        start = time.ticks_ms()
        if not self.stack:
            self.stack = [screen_id]
            screen = self.nav.init_root(screen_id)
        else:
            self.stack.append(screen_id)
            screen = self.nav.push(screen_id)
        self._update_op_fps(start)
        return screen

    def pop(self):
        if len(self.stack) <= 1:
            return None

        start = time.ticks_ms()
        self.stack.pop()
        self.nav.pop()
        self._update_op_fps(start)
        return self._id_to_name[self.stack[-1]]

    def replace(self, name):
        if not self.stack:
            return self.push(name)

        screen_id = self._name_to_screen_id(name)
        start = time.ticks_ms()
        self.stack[-1] = screen_id
        screen = self.nav.replace(screen_id)
        self._update_op_fps(start)
        return screen

    def cleanup(self):
        self._delete_fps_overlay()
        self.nav.dispose()
        self.stack = []
        gc.collect()


suite("nav_smooth")

try:
    sm = ScreenManager()
    sm.init()
    print("  ScreenManager initialized (smooth transitions + FPS counter)")

    print("\n  === PUSH Phase (slide from right) ===")
    print("  Stack grows: Home -> Settings -> Display\n")

    mem_start = gc.mem_free()

    sm.push("Home")
    print("  [PUSH] Home          | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("push_home", len(sm.stack), "1")
    time.sleep(1)

    sm.push("Settings")
    print("  [PUSH] Settings      | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("push_settings", len(sm.stack), "2")
    time.sleep(1)

    sm.push("Display")
    print("  [PUSH] Display       | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("push_display", len(sm.stack), "3")
    time.sleep(1)

    print("\n  === POP Phase (slide to right) ===")
    print("  Stack shrinks: Display -> Settings -> Home\n")

    popped = sm.pop()
    print(
        "  [POP]  -> "
        + str(popped)
        + "    | Stack: "
        + sm._get_stack_text()
        + " | FPS: "
        + str(sm.last_fps)
    )
    t("pop_to_settings", popped, "Settings")
    time.sleep(1)

    popped = sm.pop()
    print(
        "  [POP]  -> "
        + str(popped)
        + "       | Stack: "
        + sm._get_stack_text()
        + " | FPS: "
        + str(sm.last_fps)
    )
    t("pop_to_home", popped, "Home")
    time.sleep(1)

    sm.replace("Home")
    print("  [REPL] Home          | Stack: " + sm._get_stack_text() + " | FPS: " + str(sm.last_fps))
    t("replace_home", len(sm.stack), "1")

    popped = sm.pop()
    t("pop_at_root", popped is None, "True")

    sm.cleanup()
    blank = ls.create_screen()
    lv.lv_screen_load(blank)
    refresh(5)
    mem_end = gc.mem_free()
    mem_diff = mem_start - mem_end
    print(
        "\n  Memory: start=" + str(mem_start) + ", end=" + str(mem_end) + ", diff=" + str(mem_diff)
    )
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
