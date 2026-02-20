from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Container:
    items: list[int]
    mapping: dict[str, int]
    unique: set[int]


@dataclass
class Inner:
    items: list[int]
    data: dict[str, int]


@dataclass
class Outer:
    inner: Inner
    name: str


def get_items(c: Container) -> list[int]:
    return c.items


def get_mapping(c: Container) -> dict[str, int]:
    return c.mapping


def get_unique(c: Container) -> set[int]:
    return c.unique


def get_first_item(c: Container) -> int:
    return c.items[0]


def get_mapping_key(c: Container, key: str) -> int:
    return c.mapping[key]


def has_in_unique(c: Container, val: int) -> bool:
    return val in c.unique


def get_inner_items(o: Outer) -> list[int]:
    return o.inner.items


def get_inner_data(o: Outer) -> dict[str, int]:
    return o.inner.data


def get_first_inner_item(o: Outer) -> int:
    return o.inner.items[0]


def get_inner_data_key(o: Outer, key: str) -> int:
    return o.inner.data[key]


def count_inner_items(o: Outer) -> int:
    return len(o.inner.items)


def sum_inner_items(o: Outer) -> int:
    total: int = 0
    for item in o.inner.items:
        total = total + item
    return total


def benchmark_inner_list_update(o: Outer, iterations: int) -> int:
    i: int = 0
    while i < iterations:
        o.inner.items[0] = i
        i = i + 1
    return o.inner.items[0]
