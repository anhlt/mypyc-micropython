import lvgl_nav

SCREEN_HOME = 0
SCREEN_SETTINGS = 1
SCREEN_ABOUT = 2
SCREEN_DEEP_CHILD = 3

ALLOWED_CHILDREN: tuple[tuple[int, tuple[int, ...]], ...] = (
    (SCREEN_HOME, (SCREEN_SETTINGS, SCREEN_ABOUT)),
    (SCREEN_SETTINGS, (SCREEN_DEEP_CHILD,)),
    (SCREEN_ABOUT, ()),
    (SCREEN_DEEP_CHILD, ()),
)


def _invalid_screen_id(screen_id):
    raise ValueError("invalid screen id: " + str(screen_id))


class ScreenNode:
    def __init__(self, screen_id, screen_factory, children=None):
        self.screen_id = screen_id
        self.screen_factory = screen_factory
        self.children = children if children is not None else []


class ScreenManager:
    def __init__(self, root):
        self._root = root
        self._stack = []
        builders = self._collect_builders(root)
        self._nav = lvgl_nav.Nav(
            nav_capacity=8, builders=builders, allowed_children=ALLOWED_CHILDREN
        )

    def start(self):
        self._validate_screen_id(SCREEN_HOME)
        self._stack = [SCREEN_HOME]
        return self._nav.init_root(SCREEN_HOME)

    def goto(self, child):
        self._ensure_started()
        self._stack.append(child)
        return self._nav.push(child)

    def back(self):
        self._ensure_started()
        if len(self._stack) <= 1:
            return self._nav.pop()

        self._stack.pop()
        return self._nav.pop()

    def _collect_builders(self, root):
        entries = []
        seen = set()

        def visit(node):
            screen_id = node.screen_id
            if screen_id in seen:
                return
            self._validate_screen_id(screen_id)
            seen.add(screen_id)
            entries.append((screen_id, node.screen_factory))
            for child in node.children:
                visit(child)

        visit(root)
        return tuple(entries)

    def _ensure_started(self):
        if not self._stack:
            raise RuntimeError("ScreenManager.start() must be called before navigation")

    def _validate_screen_id(self, screen_id):
        i = 0
        while i < len(ALLOWED_CHILDREN):
            node_id, _children = ALLOWED_CHILDREN[i]
            if node_id == screen_id:
                return
            i += 1
        _invalid_screen_id(screen_id)
