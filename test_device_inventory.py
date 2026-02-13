"""On-device test script for inventory module on ESP32 (class + list + dict)."""

import inventory

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
print("Inventory Module - On-Device Tests")
print("(class + list + dict integration)")
print("=" * 50)

# --- Construction ---
print("\n[1] Constructor")
inv = inventory.Inventory()
test("creates instance", type(inv).__name__, "Inventory")
test("total_count starts at 0", inv.total_count, 0)

# --- add_item ---
print("\n[2] add_item")
inv.add_item(100, 5)
test("total_count after 1 add", inv.total_count, 5)

inv.add_item(200, 3)
test("total_count after 2 adds", inv.total_count, 8)

inv.add_item(300, 7)
test("total_count after 3 adds", inv.total_count, 15)

# --- get_quantity ---
print("\n[3] get_quantity")
test("quantity of item 100", inv.get_quantity(100), 5)
test("quantity of item 200", inv.get_quantity(200), 3)
test("quantity of item 300", inv.get_quantity(300), 7)

# --- item_count (len of items list) ---
print("\n[4] item_count")
test("3 items added", inv.item_count(), 3)

# --- total_quantity (for loop + nested subscript) ---
print("\n[5] total_quantity (for loop + self.counts[self.items[i]])")
test("sum of quantities", inv.total_quantity(), 15)

# --- has_item (linear search) ---
print("\n[6] has_item (linear search)")
test("has item 100", inv.has_item(100), True)
test("has item 200", inv.has_item(200), True)
test("has item 300", inv.has_item(300), True)
test("does not have 999", inv.has_item(999), False)
test("does not have 0", inv.has_item(0), False)

# --- Multiple instances are independent ---
print("\n[7] Multiple instances")
inv2 = inventory.Inventory()
inv2.add_item(50, 10)
test("inv2 total_count", inv2.total_count, 10)
test("inv2 item_count", inv2.item_count(), 1)
test("original inv unchanged", inv.total_count, 15)
test("original inv item_count", inv.item_count(), 3)

# --- Edge cases ---
print("\n[8] Edge cases")
empty_inv = inventory.Inventory()
test("empty item_count", empty_inv.item_count(), 0)
test("empty total_quantity", empty_inv.total_quantity(), 0)
test("empty has_item", empty_inv.has_item(1), False)

# Large quantity
big_inv = inventory.Inventory()
big_inv.add_item(1, 1000000)
test("large quantity", big_inv.get_quantity(1), 1000000)
test("large total_quantity", big_inv.total_quantity(), 1000000)

# --- Summary ---
print("\n" + "=" * 50)
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"FAILURES: {failed}")
print("=" * 50)
