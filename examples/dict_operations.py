from typing import Any


def create_config() -> dict[str, Any]:
    return {"name": "test", "value": 42, "enabled": True}


def get_value(d: dict[str, int], key: str) -> int:
    return d[key]


def set_value(d: dict[str, int], key: str, value: int) -> dict[str, int]:
    d[key] = value
    return d


def get_with_default(d: dict[str, int], key: str, default_val: int) -> int:
    result: int = d.get(key, default_val)
    return result


def count_items(d: dict[str, int]) -> int:
    return len(d)


def create_counter(n: int) -> dict[int, int]:
    result: dict[int, int] = {}
    for i in range(n):
        result[i] = i * i
    return result


def merge_dicts(d1: dict[str, int], d2: dict[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for key in d1.keys():
        result[key] = d1[key]
    for key in d2.keys():
        result[key] = d2[key]
    return result


def has_key(d: dict[str, int], key: str) -> bool:
    return key in d


def missing_key(d: dict[str, int], key: str) -> bool:
    return key not in d


def copy_dict(d: dict[str, int]) -> dict[str, int]:
    return d.copy()


def clear_dict(d: dict[str, int]) -> dict[str, int]:
    d.clear()
    return d


def setdefault_key(d: dict[str, int], key: str, value: int) -> int:
    return d.setdefault(key, value)


def pop_key(d: dict[str, int], key: str) -> int:
    return d.pop(key)


def pop_key_default(d: dict[str, int], key: str, default_val: int) -> int:
    return d.pop(key, default_val)


def popitem_last(d: dict[str, int]) -> tuple[str, int]:
    return d.popitem()


def update_dict(d1: dict[str, int], d2: dict[str, int]) -> dict[str, int]:
    d1.update(d2)
    return d1


def copy_constructor(d: dict[str, int]) -> dict[str, int]:
    return dict(d)
