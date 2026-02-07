def create_config() -> dict:
    return {"name": "test", "value": 42, "enabled": True}


def get_value(d: dict, key: str) -> int:
    return d[key]


def set_value(d: dict, key: str, value: int) -> dict:
    d[key] = value
    return d


def get_with_default(d: dict, key: str, default_val: int) -> int:
    return d.get(key, default_val)


def count_items(d: dict) -> int:
    return len(d)


def create_counter(n: int) -> dict:
    result: dict = {}
    for i in range(n):
        result[i] = i * i
    return result


def merge_dicts(d1: dict, d2: dict) -> dict:
    result: dict = {}
    for key in d1.keys():
        result[key] = d1[key]
    for key in d2.keys():
        result[key] = d2[key]
    return result
