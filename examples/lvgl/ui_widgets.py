import lvgl


class Widget:
    def __init__(self, children=None):
        self.children = children if children is not None else []

    def build(self, parent):
        raise NotImplementedError

    def _build_children(self, parent):
        for child in self.children:
            child.build(parent)


class Container(Widget):
    def __init__(self, children=None):
        super().__init__(children=children)

    def build(self, parent):
        obj = lvgl.lv_obj_create(parent)
        self._build_children(obj)
        return obj


class Label(Widget):
    def __init__(self, text="", children=None):
        super().__init__(children=children)
        self.text = text

    def build(self, parent):
        label = lvgl.lv_label_create(parent)
        lvgl.lv_label_set_text(label, self.text)
        self._build_children(label)
        return label


class Screen:
    def __init__(self, widgets=None):
        self.widgets = widgets if widgets is not None else []

    def build_root(self):
        root = lvgl.lv_obj_create(None)
        for widget in self.widgets:
            widget.build(root)
        return root
