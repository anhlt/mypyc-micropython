import lvgl as lv


def _lv_screen_active() -> object:
    return lv.lv_screen_active()


def _lv_obj_clean(obj: object) -> None:
    lv.lv_obj_clean(obj)


def _lv_obj_create(parent: object | None) -> object:
    return lv.lv_obj_create(parent)


def _lv_label_create(parent: object) -> object:
    return lv.lv_label_create(parent)


def _lv_label_set_text_static(label: object, text: str) -> None:
    lv.lv_label_set_text_static(label, text)


def _lv_obj_center(obj: object) -> None:
    lv.lv_obj_center(obj)


def _lv_screen_load(scr: object) -> None:
    lv.lv_screen_load(scr)


def _lv_obj_delete(obj: object) -> None:
    lv.lv_obj_delete(obj)


class App:
    modulo: int
    model: int
    _last_rendered_model: int
    _queue_buf: list[int]
    _queue_capacity: int
    _queue_head: int
    _queue_tail: int
    _queue_size: int
    _texts: list[str]
    _mounted: bool
    root: object | None
    label: object | None

    def __init__(self, model0: int, modulo: int, queue_capacity: int = 32) -> None:
        if modulo <= 0:
            modulo = 1
        if modulo > 8:
            modulo = 8

        if queue_capacity <= 0:
            queue_capacity = 1

        self.modulo = modulo
        self.model = model0 % modulo
        self._last_rendered_model = -1

        self._queue_buf = [0] * queue_capacity
        self._queue_capacity = queue_capacity
        self._queue_head = 0
        self._queue_tail = 0
        self._queue_size = 0
        self._texts = [
            "Count: 0",
            "Count: 1",
            "Count: 2",
            "Count: 3",
            "Count: 4",
            "Count: 5",
            "Count: 6",
            "Count: 7",
        ]
        self._mounted = False

        self.root = None
        self.label = None

    def _text_for(self, i: int) -> str:
        if i <= 0:
            return self._texts[0]
        if i >= 7:
            return self._texts[7]
        return self._texts[i]

    def mount(self) -> object:
        if not self._mounted:
            root: object = _lv_obj_create(None)
            label: object = _lv_label_create(root)
            _lv_label_set_text_static(label, self._text_for(self.model))
            _lv_obj_center(label)
            _lv_screen_load(root)

            self.root = root
            self.label = label
            self._last_rendered_model = self.model
            self._mounted = True
        return self.root

    def dispatch(self, msg: int) -> None:
        if self._queue_size >= self._queue_capacity:
            return
        self._queue_buf[self._queue_tail] = msg
        self._queue_tail = (self._queue_tail + 1) % self._queue_capacity
        self._queue_size += 1

    def tick(self, max_msgs: int = 32) -> None:
        if not self._mounted:
            return

        if max_msgs <= 0:
            return

        processed = 0
        changed = False
        while processed < max_msgs:
            if self._queue_size <= 0:
                break
            msg: int = self._queue_buf[self._queue_head]
            self._queue_head = (self._queue_head + 1) % self._queue_capacity
            self._queue_size -= 1
            if msg == 1:
                self.model = (self.model + 1) % self.modulo
                changed = True
            processed += 1

        if not changed:
            return
        if self.model == self._last_rendered_model:
            return

        label: object = self.label
        _lv_label_set_text_static(label, self._text_for(self.model))
        self._last_rendered_model = self.model

    def dispose(self) -> None:
        if self._mounted:
            root: object = self.root
            _lv_obj_clean(root)
            _lv_obj_delete(root)
            self.root = None
            self.label = None
            self._mounted = False
        self._queue_head = 0
        self._queue_tail = 0
        self._queue_size = 0
