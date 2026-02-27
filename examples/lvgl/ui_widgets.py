from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import lvgl


@dataclass(slots=True)
class Widget:
    children: list["Widget"] = field(default_factory=list)

    def build(self, parent: Any) -> Any:
        raise NotImplementedError

    def _build_children(self, parent: Any) -> None:
        for child in self.children:
            child.build(parent)


@dataclass(slots=True)
class Container(Widget):
    def build(self, parent: Any) -> Any:
        obj = lvgl.lv_obj_create(parent)
        self._build_children(obj)
        return obj


@dataclass(slots=True)
class Label(Widget):
    text: str = ""

    def build(self, parent: Any) -> Any:
        label = lvgl.lv_label_create(parent)
        lvgl.lv_label_set_text(label, self.text)
        self._build_children(label)
        return label


@dataclass(slots=True)
class Screen:
    widgets: list[Widget] = field(default_factory=list)

    def build_root(self) -> Any:
        root = lvgl.lv_obj_create(None)
        for widget in self.widgets:
            widget.build(root)
        return root
