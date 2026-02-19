from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int


@dataclass
class Rectangle:
    top_left: Point
    bottom_right: Point


@dataclass
class Node:
    value: int
    next: Node


def get_width(rect: Rectangle) -> int:
    return rect.bottom_right.x - rect.top_left.x


def get_height(rect: Rectangle) -> int:
    return rect.bottom_right.y - rect.top_left.y


def get_area(rect: Rectangle) -> int:
    width = rect.bottom_right.x - rect.top_left.x
    height = rect.bottom_right.y - rect.top_left.y
    return width * height


def get_top_left_x(rect: Rectangle) -> int:
    return rect.top_left.x


def get_top_left_y(rect: Rectangle) -> int:
    return rect.top_left.y


def get_bottom_right_x(rect: Rectangle) -> int:
    return rect.bottom_right.x


def get_bottom_right_y(rect: Rectangle) -> int:
    return rect.bottom_right.y


def get_next_value(node: Node) -> int:
    return node.next.value
