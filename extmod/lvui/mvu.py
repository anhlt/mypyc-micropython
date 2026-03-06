import lvgl as lv
import nav
import screens as ls

SCREEN_HOME = 0
SCREEN_SETTINGS = 1

MSG_INCREMENT = 1
MSG_PUSH_SETTINGS = 2
MSG_POP = 3
MSG_REPLACE_HOME = 4

NAV_CAPACITY = 8

NAV_NONE = 0
NAV_PUSH = 1
NAV_POP = 2
NAV_REPLACE = 3


def _lv_obj_set_size(obj: object, w: int, h: int) -> None:
    lv.lv_obj_set_size(obj, w, h)


def _lv_obj_align(obj: object, align: int, x_ofs: int, y_ofs: int) -> None:
    lv.lv_obj_align(obj, align, x_ofs, y_ofs)


def _lv_label_create(parent: object) -> object:
    return lv.lv_label_create(parent)


def _lv_label_set_text_static(label: object, text: str) -> None:
    lv.lv_label_set_text_static(label, text)


def _lv_bar_create(parent: object) -> object:
    return lv.lv_bar_create(parent)


def _lv_bar_set_range(bar: object, min_v: int, max_v: int) -> None:
    lv.lv_bar_set_range(bar, min_v, max_v)


def _lv_bar_set_value(bar: object, value: int) -> None:
    lv.lv_bar_set_value(bar, value, 0)


def _lv_arc_create(parent: object) -> object:
    return lv.lv_arc_create(parent)


def _lv_arc_set_range(arc: object, min_v: int, max_v: int) -> None:
    lv.lv_arc_set_range(arc, min_v, max_v)


def _lv_arc_set_value(arc: object, value: int) -> None:
    lv.lv_arc_set_value(arc, value)


class ScreenRefs:
    screen_id: int
    label_title: object
    label_count: object
    label_info: object
    label_mode: object
    widget: object
    last_model: int
    last_widget: int

    def __init__(
        self,
        screen_id: int,
        label_title: object,
        label_count: object,
        label_info: object,
        label_mode: object,
        widget: object,
    ) -> None:
        self.screen_id = screen_id
        self.label_title = label_title
        self.label_count = label_count
        self.label_info = label_info
        self.label_mode = label_mode
        self.widget = widget
        self.last_model = -1
        self.last_widget = -1


class App:
    modulo: int
    model: int
    nav_stack: list[int]
    nav_size: int
    active_screen_id: int
    _queue_buf: list[int]
    _queue_capacity: int
    _queue_head: int
    _queue_tail: int
    _queue_size: int
    _count_texts: list[str]
    _static_texts: list[str]
    _mounted: bool
    _active_root: object | None
    _nav_pending: int
    _nav: nav.Nav
    _refs_by_root: dict[int, ScreenRefs]

    def __init__(self, model0: int, modulo: int, queue_capacity: int = 32) -> None:
        if modulo <= 0:
            modulo = 1
        if modulo > 8:
            modulo = 8
        if queue_capacity <= 0:
            queue_capacity = 1

        self.modulo = modulo
        self.model = model0 % modulo

        self.nav_stack = [SCREEN_HOME] * NAV_CAPACITY
        self.nav_size = 0
        self.active_screen_id = SCREEN_HOME

        self._queue_buf = [0] * queue_capacity
        self._queue_capacity = queue_capacity
        self._queue_head = 0
        self._queue_tail = 0
        self._queue_size = 0

        self._count_texts = [
            "Count: 0",
            "Count: 1",
            "Count: 2",
            "Count: 3",
            "Count: 4",
            "Count: 5",
            "Count: 6",
            "Count: 7",
        ]
        self._static_texts = [
            "Home",
            "Settings",
            "State: running",
            "Mode: retained",
            "Msg1: increment",
            "Msg2: push settings",
            "Msg3: pop screen",
            "Msg4: replace home",
            "Widget: bar",
            "Widget: arc",
            "Nav: stack",
        ]

        self._mounted = False
        self._active_root = None
        self._nav_pending = NAV_NONE
        self._refs_by_root = {}
        # Bound method references for screen builders
        builders: tuple[tuple[int, object], ...] = (
            (SCREEN_HOME, self._build_home),
            (SCREEN_SETTINGS, self._build_settings),
        )
        self._nav = nav.Nav(NAV_CAPACITY, builders, None)

    def _count_text_for(self, value: int) -> str:
        if value <= 0:
            return self._count_texts[0]
        if value >= 7:
            return self._count_texts[7]
        return self._count_texts[value]

    def _widget_value_for(self, value: int) -> int:
        if self.modulo <= 1:
            return 0
        return (value * 100) // (self.modulo - 1)

    def _new_label(self, parent: object, text: str, y: int) -> object:
        label = _lv_label_create(parent)
        _lv_label_set_text_static(label, text)
        _lv_obj_align(label, 17, 0, y)
        return label

    def _build_home(self) -> object:
        root = ls.create_screen()

        label_title = self._new_label(root, self._static_texts[0], -104)
        label_count = self._new_label(root, self._count_text_for(self.model), -74)
        label_info = self._new_label(root, self._static_texts[2], -44)
        label_mode = self._new_label(root, self._static_texts[3], -14)
        self._new_label(root, self._static_texts[4], 16)
        self._new_label(root, self._static_texts[5], 46)
        self._new_label(root, self._static_texts[7], 76)

        bar = _lv_bar_create(root)
        _lv_obj_set_size(bar, 220, 18)
        _lv_obj_align(bar, 17, 0, 108)
        _lv_bar_set_range(bar, 0, 100)
        _lv_bar_set_value(bar, self._widget_value_for(self.model))

        refs = ScreenRefs(
            SCREEN_HOME,
            label_title,
            label_count,
            label_info,
            label_mode,
            bar,
        )
        self._refs_by_root[id(root)] = refs
        return root

    def _build_settings(self) -> object:
        root = ls.create_screen()

        label_title = self._new_label(root, self._static_texts[1], -104)
        label_count = self._new_label(root, self._count_text_for(self.model), -74)
        label_info = self._new_label(root, self._static_texts[10], -44)
        label_mode = self._new_label(root, self._static_texts[9], -14)
        self._new_label(root, self._static_texts[4], 16)
        self._new_label(root, self._static_texts[6], 46)
        self._new_label(root, self._static_texts[7], 76)

        arc = _lv_arc_create(root)
        _lv_obj_set_size(arc, 150, 150)
        _lv_obj_align(arc, 17, 0, 118)
        _lv_arc_set_range(arc, 0, 100)
        _lv_arc_set_value(arc, self._widget_value_for(self.model))

        refs = ScreenRefs(
            SCREEN_SETTINGS,
            label_title,
            label_count,
            label_info,
            label_mode,
            arc,
        )
        self._refs_by_root[id(root)] = refs
        return root

    def mount(self) -> object:
        if not self._mounted:
            root = self._nav.init_root(SCREEN_HOME)
            self._active_root = root
            self.nav_stack[0] = SCREEN_HOME
            self.nav_size = 1
            self.active_screen_id = SCREEN_HOME
            self._mounted = True
            self._nav_pending = NAV_NONE
            self._render_active()
        active = self._active_root
        if active is None:
            return self._nav.init_root(SCREEN_HOME)
        return active

    def dispatch(self, msg: int) -> None:
        if self._queue_size >= self._queue_capacity:
            return
        self._queue_buf[self._queue_tail] = msg
        self._queue_tail = (self._queue_tail + 1) % self._queue_capacity
        self._queue_size += 1

    def _drain_messages(self, max_msgs: int) -> None:
        if max_msgs <= 0:
            return
        processed = 0
        while processed < max_msgs:
            if self._queue_size <= 0:
                break
            msg = self._queue_buf[self._queue_head]
            self._queue_head = (self._queue_head + 1) % self._queue_capacity
            self._queue_size -= 1

            if msg == MSG_INCREMENT:
                self.model = (self.model + 1) % self.modulo
            elif msg == MSG_PUSH_SETTINGS:
                if self._nav_pending == NAV_NONE:
                    self._nav_pending = NAV_PUSH
            elif msg == MSG_POP:
                if self._nav_pending == NAV_NONE:
                    self._nav_pending = NAV_POP
            elif msg == MSG_REPLACE_HOME:
                if self._nav_pending == NAV_NONE:
                    self._nav_pending = NAV_REPLACE

            processed += 1

    def _apply_nav(self) -> None:
        cmd = self._nav_pending
        if cmd == NAV_NONE:
            return

        old_root = self._active_root
        new_root = old_root

        if cmd == NAV_PUSH:
            new_root = self._nav.push(SCREEN_SETTINGS)
            if self.nav_size < NAV_CAPACITY:
                self.nav_stack[self.nav_size] = SCREEN_SETTINGS
                self.nav_size += 1
            elif self.nav_size > 0:
                self.nav_stack[self.nav_size - 1] = SCREEN_SETTINGS
            self.active_screen_id = SCREEN_SETTINGS
        elif cmd == NAV_POP:
            new_root = self._nav.pop()
            if self.nav_size > 1:
                self.nav_size -= 1
            if self.nav_size > 0:
                self.active_screen_id = self.nav_stack[self.nav_size - 1]
            else:
                self.active_screen_id = SCREEN_HOME
        elif cmd == NAV_REPLACE:
            new_root = self._nav.replace(SCREEN_HOME)
            if self.nav_size <= 0:
                self.nav_stack[0] = SCREEN_HOME
                self.nav_size = 1
            else:
                self.nav_stack[self.nav_size - 1] = SCREEN_HOME
            self.active_screen_id = SCREEN_HOME

        # Prune references only on pop or replace
        if (cmd == NAV_POP or cmd == NAV_REPLACE) and old_root is not None and old_root is not new_root:
            self._refs_by_root.pop(id(old_root), None)

        self._active_root = new_root
        self._nav_pending = NAV_NONE
        cmd = self._nav_pending
        if cmd == NAV_NONE:
            return

        new_root = self._active_root
        if cmd == NAV_PUSH:
            new_root = self._nav.push(SCREEN_SETTINGS)
            if self.nav_size < NAV_CAPACITY:
                self.nav_stack[self.nav_size] = SCREEN_SETTINGS
                self.nav_size += 1
            elif self.nav_size > 0:
                self.nav_stack[self.nav_size - 1] = SCREEN_SETTINGS
            self.active_screen_id = SCREEN_SETTINGS
        elif cmd == NAV_POP:
            new_root = self._nav.pop()
            if self.nav_size > 1:
                self.nav_size -= 1
            if self.nav_size > 0:
                self.active_screen_id = self.nav_stack[self.nav_size - 1]
            else:
                self.active_screen_id = SCREEN_HOME
        elif cmd == NAV_REPLACE:
            new_root = self._nav.replace(SCREEN_HOME)
            if self.nav_size <= 0:
                self.nav_stack[0] = SCREEN_HOME
                self.nav_size = 1
            else:
                self.nav_stack[self.nav_size - 1] = SCREEN_HOME
            self.active_screen_id = SCREEN_HOME

        self._active_root = new_root
        self._nav_pending = NAV_NONE

    def _render_active(self) -> None:
        root = self._active_root
        if root is None:
            return
        refs = self._refs_by_root.get(id(root))
        if refs is None:
            return

        model = self.model
        widget_value = self._widget_value_for(model)
        if refs.last_model != model:
            _lv_label_set_text_static(refs.label_count, self._count_text_for(model))
            refs.last_model = model
        if refs.last_widget != widget_value:
            if refs.screen_id == SCREEN_HOME:
                _lv_bar_set_value(refs.widget, widget_value)
            else:
                _lv_arc_set_value(refs.widget, widget_value)
            refs.last_widget = widget_value

    def tick(self, max_msgs: int = 32, pump_timer: bool = False) -> None:
        if not self._mounted:
            return
        self._drain_messages(max_msgs)
        self._apply_nav()
        self._render_active()
        if pump_timer:
            ls.timer_handler()

    def dispose(self) -> None:
        if self._mounted:
            self._nav.dispose()
            self._active_root = None
            self.nav_size = 0
            self.active_screen_id = SCREEN_HOME
            self._mounted = False
            self._nav_pending = NAV_NONE
        self._queue_head = 0
        self._queue_tail = 0
        self._queue_size = 0
        self._refs_by_root.clear()
