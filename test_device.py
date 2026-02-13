"""On-device test script for dict_operations module on ESP32-C3."""

import dict_operations

passed = 0
failed = 0


def test(name, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}: got {got!r}, expected {expected!r}")


print("=" * 50)
print("Dict Operations - On-Device Tests")
print("=" * 50)

# --- Original functions ---
print("\n[1] create_config")
cfg = dict_operations.create_config()
test("returns dict", type(cfg).__name__, "dict")
test("has name", cfg["name"], "test")
test("has value", cfg["value"], 42)
test("has enabled", cfg["enabled"], True)

print("\n[2] get_value")
d = {"x": 10, "y": 20}
test("get x", dict_operations.get_value(d, "x"), 10)
test("get y", dict_operations.get_value(d, "y"), 20)

print("\n[3] set_value")
d = {"a": 1}
result = dict_operations.set_value(d, "b", 2)
test("set new key", result["b"], 2)
test("existing key preserved", result["a"], 1)

print("\n[4] get_with_default")
d = {"a": 1}
test("key exists", dict_operations.get_with_default(d, "a", 99), 1)
test("key missing", dict_operations.get_with_default(d, "z", 99), 99)

print("\n[5] count_items")
test("empty dict", dict_operations.count_items({}), 0)
test("3 items", dict_operations.count_items({"a": 1, "b": 2, "c": 3}), 3)

print("\n[6] create_counter")
c = dict_operations.create_counter(4)
test("counter[0]", c[0], 0)
test("counter[1]", c[1], 1)
test("counter[2]", c[2], 4)
test("counter[3]", c[3], 9)

print("\n[7] merge_dicts")
m = dict_operations.merge_dicts({"a": 1}, {"b": 2})
test("has a", m["a"], 1)
test("has b", m["b"], 2)

# --- New dict methods ---
print("\n[8] has_key (in operator)")
d = {"x": 1, "y": 2}
test("key exists", dict_operations.has_key(d, "x"), True)
test("key missing", dict_operations.has_key(d, "z"), False)

print("\n[9] missing_key (not in operator)")
d = {"x": 1}
test("key exists", dict_operations.missing_key(d, "x"), False)
test("key missing", dict_operations.missing_key(d, "z"), True)

print("\n[10] copy_dict")
d = {"a": 1, "b": 2}
c = dict_operations.copy_dict(d)
test("copy equals original", c["a"] == 1 and c["b"] == 2, True)
# Modify original, copy should be unaffected
d["a"] = 999
test("copy is independent", c["a"], 1)

print("\n[11] clear_dict")
d = {"a": 1, "b": 2}
result = dict_operations.clear_dict(d)
test("cleared length", len(result), 0)

print("\n[12] setdefault_key")
d = {"a": 1}
val = dict_operations.setdefault_key(d, "b", 42)
test("new key returns default", val, 42)
test("key was inserted", d["b"], 42)
val2 = dict_operations.setdefault_key(d, "a", 99)
test("existing key returns current", val2, 1)

print("\n[13] pop_key")
d = {"a": 1, "b": 2}
val = dict_operations.pop_key(d, "a")
test("popped value", val, 1)
test("key removed", "a" not in d, True)

print("\n[14] pop_key_default")
d = {"a": 1}
test("existing key", dict_operations.pop_key_default(d, "a", 99), 1)
test("missing key returns default", dict_operations.pop_key_default(d, "z", 99), 99)

print("\n[15] popitem_last")
d = {"only": 42}
item = dict_operations.popitem_last(d)
test("returns tuple", type(item).__name__, "tuple")
test("key-value pair", item, ("only", 42))
test("dict now empty", len(d), 0)

print("\n[16] update_dict")
d1 = {"a": 1}
d2 = {"b": 2, "c": 3}
result = dict_operations.update_dict(d1, d2)
test("has original", result["a"], 1)
test("has new b", result["b"], 2)
test("has new c", result["c"], 3)

print("\n[17] copy_constructor (dict(d))")
d = {"a": 1, "b": 2}
c = dict_operations.copy_constructor(d)
test("copy equals original", c["a"] == 1 and c["b"] == 2, True)
d["a"] = 999
test("copy is independent", c["a"], 1)

# --- Summary ---
print("\n" + "=" * 50)
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"FAILURES: {failed}")
print("=" * 50)
