class ScreenNode:
    def __init__(self, name, screen_factory, children=None):
        self.name = name
        self.screen_factory = screen_factory
        self.children = children if children is not None else []


class ScreenManager:
    def __init__(self, root, nav_core=None):
        self._root = root
        self._current = root
        self._parent_by_node = {}
        self._current_root = None
        self._started = False
        self._nav_core = nav_core
        self._use_nav_core = bool(
            nav_core is not None
            and hasattr(nav_core, "register_builder")
            and hasattr(nav_core, "build_screen")
        )
        if self._use_nav_core:
            self._register_builders(root)
        self._index_tree(root, None)

    def start(self):
        self._current = self._root
        self._current_root = self._load_node(self._root)
        self._started = True
        return self._current_root

    def goto(self, child_name):
        self._ensure_started()
        target = self._direct_child(child_name)
        old_root = self._current_root
        new_root = self._load_node(target)

        self._current = target
        self._current_root = new_root
        if old_root is not None:
            self._obj_delete(old_root)
        return new_root

    def back(self):
        self._ensure_started()
        parent = self._parent_by_node.get(id(self._current))
        if parent is None:
            return self._current_root

        old_root = self._current_root
        new_root = self._load_node(parent)

        self._current = parent
        self._current_root = new_root
        if old_root is not None:
            self._obj_delete(old_root)
        return new_root

    def _load_node(self, node):
        if self._use_nav_core and self._nav_core is not None:
            root = self._nav_core.build_screen(node.name)
        else:
            root = node.screen_factory()
        if root is not None:
            self._screen_load(root)
        return root

    def _register_builders(self, node):
        if self._nav_core is not None:
            self._nav_core.register_builder(node.name, node.screen_factory)
        for child in node.children:
            self._register_builders(child)

    def _screen_load(self, root):
        from ui_lv_compat import screen_load

        screen_load(root)

    def _obj_delete(self, obj):
        from ui_lv_compat import obj_delete

        obj_delete(obj)

    def _ensure_started(self):
        if not self._started:
            raise RuntimeError("ScreenManager.start() must be called before navigation")

    def _direct_child(self, child_name):
        for child in self._current.children:
            if child.name == child_name:
                return child

        allowed = ", ".join(child.name for child in self._current.children) or "<none>"
        raise ValueError(
            f"Unknown child '{child_name}' under '{self._current.name}'. Allowed: {allowed}"
        )

    def _index_tree(self, node, parent):
        self._parent_by_node[id(node)] = parent
        for child in node.children:
            self._index_tree(child, node)
