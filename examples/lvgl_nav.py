import time
from typing import Callable

import lvgl as lv
import lvgl_screens as ls

OVER_LEFT = 1
OVER_RIGHT = 2
FADE_IN = 9

PUSH_ANIM_MS = 250
POP_ANIM_MS = 250
REPLACE_ANIM_MS = 180
PUMP_STEP_MS = 10
PUMP_PAD_MS = 100

SCREEN_HOME = 0
SCREEN_SLIDER = 1
SCREEN_PROGRESS = 2
SCREEN_ARC = 3
SCREEN_CONTROLS = 4

ScreenBuilder = Callable[[], object]
BuilderEntry = tuple[int, ScreenBuilder]
AllowedChildEntry = tuple[int, tuple[int, ...]]

DEFAULT_BUILDERS: tuple[BuilderEntry, ...] = (
    (SCREEN_HOME, ls.build_home_screen),
    (SCREEN_SLIDER, ls.build_slider_screen),
    (SCREEN_PROGRESS, ls.build_progress_screen),
    (SCREEN_ARC, ls.build_arc_screen),
    (SCREEN_CONTROLS, ls.build_controls_screen),
)


class Nav:
    _capacity: int
    _builders: tuple[BuilderEntry, ...]
    _allowed_children: tuple[AllowedChildEntry, ...] | None
    _screen_ids: list[int]
    _screens: list[object | None]
    _size: int

    def __init__(
        self,
        nav_capacity: int = 8,
        builders: tuple[BuilderEntry, ...] = DEFAULT_BUILDERS,
        allowed_children: tuple[AllowedChildEntry, ...] | None = None,
    ) -> None:
        if nav_capacity <= 0:
            nav_capacity = 1
        self._capacity = nav_capacity
        self._builders = builders
        self._allowed_children = allowed_children
        # Initialize lists - avoid [x] * n pattern for compiler compatibility
        self._screen_ids = []
        self._screens = []
        i = 0
        while i < nav_capacity:
            self._screen_ids.append(0)
            self._screens.append(None)
            i += 1
        self._size = 0

    def init_root(self, screen_id: int) -> object:
        import lvgl as lv

        root = self._build_screen(screen_id)
        old_size = self._size
        old_root = None
        if old_size > 0:
            old_root = self._screens[0]

        self._screen_ids[0] = screen_id
        self._screens[0] = root
        self._size = 1
        lv.lv_screen_load(root)
        self._pump(PUMP_STEP_MS)

        i = 1
        while i < old_size:
            old_screen = self._screens[i]
            if old_screen is not None and old_screen is not root:
                self._safe_delete(old_screen)
            i += 1

        if old_root is not None and old_root is not root:
            self._safe_delete(old_root)

        i = 1
        while i < self._capacity:
            self._screen_ids[i] = 0
            self._screens[i] = None
            i += 1
        return root

    def push(self, screen_id: int) -> object:
        import lvgl as lv

        if self._size == 0:
            return self.init_root(screen_id)
        if not self._is_allowed_child(screen_id):
            raise ValueError("invalid screen id: " + str(screen_id))
        if self._size >= self._capacity:
            return self.replace(screen_id)

        new_screen = self._build_screen(screen_id)
        self._screen_ids[self._size] = screen_id
        self._screens[self._size] = new_screen
        self._size += 1

        lv.lv_screen_load_anim(new_screen, OVER_LEFT, PUSH_ANIM_MS, 0, False)
        self._pump(PUSH_ANIM_MS)
        return new_screen

    def pop(self) -> object:
        import lvgl as lv

        if self._size == 0:
            return lv.lv_screen_active()
        if self._size == 1:
            root = self._screens[0]
            if root is None:
                return lv.lv_screen_active()
            return root

        top_idx = self._size - 1
        prev_idx = top_idx - 1
        old_screen = self._screens[top_idx]
        prev_screen = self._screens[prev_idx]
        if prev_screen is None:
            prev_screen = lv.lv_screen_active()

        lv.lv_screen_load_anim(prev_screen, OVER_RIGHT, POP_ANIM_MS, 0, False)
        self._pump(POP_ANIM_MS)

        self._size = prev_idx + 1
        self._screen_ids[top_idx] = 0
        self._screens[top_idx] = None
        if old_screen is not None:
            self._safe_delete(old_screen)
        return prev_screen

    def replace(self, screen_id: int) -> object:
        import lvgl as lv

        new_screen = self._build_screen(screen_id)
        if self._size == 0:
            self._screen_ids[0] = screen_id
            self._screens[0] = new_screen
            self._size = 1
            lv.lv_screen_load_anim(new_screen, FADE_IN, REPLACE_ANIM_MS, 0, False)
            self._pump(REPLACE_ANIM_MS)
            return new_screen

        top_idx = self._size - 1
        old_screen = self._screens[top_idx]
        self._screen_ids[top_idx] = screen_id
        self._screens[top_idx] = new_screen

        lv.lv_screen_load_anim(new_screen, FADE_IN, REPLACE_ANIM_MS, 0, False)
        self._pump(REPLACE_ANIM_MS)
        if old_screen is not None and old_screen is not new_screen:
            self._safe_delete(old_screen)
        return new_screen

    def current(self) -> int:
        if self._size == 0:
            return -1
        return self._screen_ids[self._size - 1]

    def dispose(self) -> None:
        import lvgl as lv

        if self._size == 0:
            return

        blank = lv.lv_obj_create(None)
        lv.lv_screen_load(blank)
        self._pump(PUMP_STEP_MS)

        i = 0
        while i < self._size:
            screen = self._screens[i]
            if screen is not None and screen is not blank:
                self._safe_delete(screen)
            self._screen_ids[i] = 0
            self._screens[i] = None
            i += 1
        self._size = 0

    def _build_screen(self, screen_id: int) -> object:
        # Direct dispatch to avoid callable-in-tuple limitation
        if screen_id == SCREEN_HOME:
            return ls.build_home_screen()
        if screen_id == SCREEN_SLIDER:
            return ls.build_slider_screen()
        if screen_id == SCREEN_PROGRESS:
            return ls.build_progress_screen()
        if screen_id == SCREEN_ARC:
            return ls.build_arc_screen()
        if screen_id == SCREEN_CONTROLS:
            return ls.build_controls_screen()
        raise ValueError("invalid screen id: " + str(screen_id))

    def _is_allowed_child(self, child_id: int) -> bool:
        if self._allowed_children is None:
            return True
        parent_id = self.current()
        i = 0
        while i < len(self._allowed_children):
            entry = self._allowed_children[i]
            entry_parent_id: int = entry[0]
            children: tuple[int, ...] = entry[1]
            if entry_parent_id == parent_id:
                j = 0
                while j < len(children):
                    if children[j] == child_id:
                        return True
                    j += 1
                return False
            i += 1
        return False

    def _safe_delete(self, screen: object) -> None:
        import lvgl as lv

        if screen is not lv.lv_screen_active():
            lv.lv_obj_delete(screen)

    def _pump(self, duration_ms: int) -> None:
        import time
        import lvgl_screens as ls

        start: int = int(time.ticks_ms())  # type: ignore[attr-defined]
        end_time: int = duration_ms + PUMP_PAD_MS
        elapsed: int = 0
        while elapsed < end_time:
            ls.timer_handler()
            time.sleep_ms(PUMP_STEP_MS)  # type: ignore[attr-defined]
            now: int = int(time.ticks_ms())  # type: ignore[attr-defined]
            elapsed = int(time.ticks_diff(now, start))  # type: ignore[attr-defined]
