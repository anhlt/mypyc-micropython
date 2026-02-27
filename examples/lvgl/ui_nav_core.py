from __future__ import annotations


def call0(f: object) -> object:
    return f()


_builders: dict[str, object] = {}


def register_builder(name: str, builder: object) -> None:
    _builders[name] = builder


def build_screen(name: str) -> object:
    builder = _builders[name]
    return call0(builder)
