#!/usr/bin/env python3
"""
Comprehensive test runner for mypyc-micropython on ESP32 device.

Usage:
    python run_device_tests.py

This script:
1. Runs all tests on the connected ESP32 device via mpremote
2. Tests all compiled modules (factorial, point, counter, sensor, etc.)
3. Reports pass/fail for each test
4. Provides overall success rate

Requires: mpremote, ESP32 device connected
"""

import argparse
import subprocess
import sys
from typing import Callable

# Default configuration
DEFAULT_PORT = "/dev/ttyACM0"

# Global port (set from command line args)
PORT = DEFAULT_PORT

# Test tracking
total_tests = 0
passed_tests = 0
failed_tests: list[tuple[str, str]] = []


def run_on_device(code: str, port: str = "", timeout: int = 30) -> tuple[bool, str]:
    """Execute Python code on device via mpremote."""
    device_port = port if port else PORT
    try:
        result = subprocess.run(
            ["mpremote", "connect", device_port, "exec", code],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def test(name: str, code: str, expected: str | Callable[[str], bool]) -> None:
    """Run a single test case."""
    global total_tests, passed_tests
    total_tests += 1

    success, output = run_on_device(code)

    if not success:
        failed_tests.append((name, f"Execution failed: {output}"))
        print(f"  FAIL {name}: {output}")
        return

    if callable(expected):
        passed = expected(output)
    else:
        passed = expected in output

    if passed:
        passed_tests += 1
        print(f"  PASS {name}")
    else:
        failed_tests.append((name, f"Expected: {expected}, Got: {output}"))
        print(f"  FAIL {name}: Expected '{expected}', got '{output}'")


def test_factorial():
    """Test factorial module functions."""
    print("\n[TEST] Testing factorial module...")

    test("factorial(5)", "import factorial; print(factorial.factorial(5))", "120")

    test("fib(10)", "import factorial; print(factorial.fib(10))", "55")

    test("add(3, 4)", "import factorial; print(factorial.add(3, 4))", "7")

    test("is_even(4)", "import factorial; print(factorial.is_even(4))", "True")

    test("is_even(3)", "import factorial; print(factorial.is_even(3))", "False")

    test("multiply(6, 7)", "import factorial; print(factorial.multiply(6, 7))", "42.0")


def test_point():
    """Test point module with classes and dataclasses."""
    print("\n[TEST] Testing point module (dataclasses)...")

    test("Point creation", "import point; p = point.Point(3, 4); print(p)", "Point(x=3, y=4)")

    test("Point.x field access", "import point; p = point.Point(3, 4); print(p.x)", "3")

    test("Point.y field access", "import point; p = point.Point(3, 4); print(p.y)", "4")

    test(
        "Point.distance_squared()",
        "import point; p = point.Point(3, 4); print(p.distance_squared())",
        "25",
    )

    test("Point.add(1, 2)", "import point; p = point.Point(3, 4); print(p.add(1, 2))", "10")

    test(
        "Point3D creation",
        "import point; p = point.Point3D(1, 2, 3); print(p)",
        "Point3D(x=1, y=2, z=3)",
    )

    test(
        "Point3D field access",
        "import point; p = point.Point3D(1, 2, 3); print(p.x, p.y, p.z)",
        "1 2 3",
    )


def test_counter():
    """Test counter module with classes."""
    print("\n[TEST] Testing counter module...")

    test("Counter creation", "import counter; c = counter.Counter(10, 2); print(c.get())", "10")

    test(
        "Counter.increment()",
        "import counter; c = counter.Counter(10, 2); c.increment(); print(c.get())",
        "12",
    )

    test(
        "Counter.decrement()",
        "import counter; c = counter.Counter(10, 2); c.decrement(); print(c.get())",
        "8",
    )

    test(
        "Counter.reset()",
        "import counter; c = counter.Counter(10, 2); c.reset(); print(c.get())",
        "0",
    )

    # Test BoundedCounter inheritance
    test(
        "BoundedCounter.get() inherited",
        "import counter; bc = counter.BoundedCounter(5, 1, 0, 10); print(bc.get())",
        "5",
    )

    test(
        "BoundedCounter.reset() inherited",
        "import counter; bc = counter.BoundedCounter(5, 1, 0, 10); bc.reset(); print(bc.get())",
        "0",
    )

    test(
        "BoundedCounter.increment() override",
        "import counter; bc = counter.BoundedCounter(9, 1, 0, 10); bc.increment(); print(bc.get())",
        "10",
    )

    test(
        "BoundedCounter.increment() capped",
        "import counter; bc = counter.BoundedCounter(10, 1, 0, 10); bc.increment(); print(bc.get())",
        "10",
    )


def test_sensor():
    """Test sensor module with dataclasses."""
    print("\n[TEST] Testing sensor module...")

    test(
        "SensorReading creation",
        "import sensor; r = sensor.SensorReading(1, 25.5, 60.0); print(r)",
        "SensorReading(sensor_id=1, temperature=25.5, humidity=60.0, valid=True)",
    )

    test(
        "SensorReading valid default",
        "import sensor; r = sensor.SensorReading(1, 25.5, 60.0); print(r.valid)",
        "True",
    )

    test(
        "SensorReading valid=False",
        "import sensor; r = sensor.SensorReading(1, 25.5, 60.0, False); print(r.valid)",
        "False",
    )

    test(
        "SensorBuffer add_reading",
        "import sensor; b = sensor.SensorBuffer(); b.add_reading(25.0, 55.0); print(b.count)",
        "1",
    )

    test(
        "SensorBuffer avg_temperature",
        "import sensor; b = sensor.SensorBuffer(); b.add_reading(25.0, 55.0); b.add_reading(27.0, 65.0); print(b.avg_temperature())",
        "26.0",
    )

    test(
        "SensorBuffer avg_humidity",
        "import sensor; b = sensor.SensorBuffer(); b.add_reading(25.0, 55.0); b.add_reading(27.0, 65.0); print(b.avg_humidity())",
        "60.0",
    )

    test(
        "SensorBuffer reset",
        "import sensor; b = sensor.SensorBuffer(); b.add_reading(25.0, 55.0); b.reset(); print(b.avg_temperature())",
        "0.0",
    )


def test_list_operations():
    """Test list_operations module."""
    print("\n[TEST] Testing list_operations module...")

    test(
        "sum_list", "import list_operations; print(list_operations.sum_list([1, 2, 3, 4, 5]))", "15"
    )

    test(
        "build_squares",
        "import list_operations; print(list_operations.build_squares(5))",
        "[0, 1, 4, 9, 16]",
    )

    test(
        "find_first_negative (found)",
        "import list_operations; print(list_operations.find_first_negative([1, -2, 3]))",
        "1",
    )

    test(
        "find_first_negative (not found)",
        "import list_operations; print(list_operations.find_first_negative([1, 2, 3]))",
        "-1",
    )


def test_math_utils():
    """Test math_utils module."""
    print("\n[TEST] Testing math_utils module...")

    test(
        "celsius_to_fahrenheit",
        "import math_utils; print(math_utils.celsius_to_fahrenheit(0))",
        "32.0",
    )

    test(
        "fahrenheit_to_celsius",
        "import math_utils; print(math_utils.fahrenheit_to_celsius(32))",
        lambda x: "0.0" in x or "-0.0" in x,
    )

    test(
        "clamp (within range)", "import math_utils; print(math_utils.clamp(5.0, 0.0, 10.0))", "5.0"
    )

    test("clamp (below min)", "import math_utils; print(math_utils.clamp(-5.0, 0.0, 10.0))", "0.0")

    test("clamp (above max)", "import math_utils; print(math_utils.clamp(15.0, 0.0, 10.0))", "10.0")

    test("lerp", "import math_utils; print(math_utils.lerp(0.0, 10.0, 0.5))", "5.0")


def test_bitwise():
    """Test bitwise module."""
    print("\n[TEST] Testing bitwise module...")

    test("set_bit(0, 0)", "import bitwise; print(bitwise.set_bit(0, 0))", "1")

    test("set_bit(1, 1)", "import bitwise; print(bitwise.set_bit(1, 1))", "3")

    test("clear_bit(7, 0)", "import bitwise; print(bitwise.clear_bit(7, 0))", "6")

    test("toggle_bit(7, 0)", "import bitwise; print(bitwise.toggle_bit(7, 0))", "6")

    test("check_bit(7, 2)", "import bitwise; print(bitwise.check_bit(7, 2))", "True")

    test("check_bit(7, 3)", "import bitwise; print(bitwise.check_bit(7, 3))", "False")

    test("count_ones(7)", "import bitwise; print(bitwise.count_ones(7))", "3")

    test("count_ones(0)", "import bitwise; print(bitwise.count_ones(0))", "0")

    test("is_power_of_two(4)", "import bitwise; print(bitwise.is_power_of_two(4))", "True")

    test("is_power_of_two(5)", "import bitwise; print(bitwise.is_power_of_two(5))", "False")


def test_algorithms():
    """Test algorithms module."""
    print("\n[TEST] Testing algorithms module...")

    test("is_prime(17)", "import algorithms; print(algorithms.is_prime(17))", "True")

    test("is_prime(18)", "import algorithms; print(algorithms.is_prime(18))", "False")

    test("gcd(48, 18)", "import algorithms; print(algorithms.gcd(48, 18))", "6")

    test("lcm(4, 6)", "import algorithms; print(algorithms.lcm(4, 6))", lambda x: "12" in x)

    test("power(2, 10)", "import algorithms; print(algorithms.power(2, 10))", "1024")


def test_dict_operations():
    """Test dict_operations module."""
    print("\n[TEST] Testing dict_operations module...")

    test(
        "create_config",
        "import dict_operations; print(dict_operations.create_config())",
        lambda x: "name" in x and "value" in x,
    )

    test(
        "get_value",
        "import dict_operations; print(dict_operations.get_value({'x': 10}, 'x'))",
        "10",
    )

    test(
        "count_items",
        "import dict_operations; print(dict_operations.count_items({'a': 1, 'b': 2}))",
        "2",
    )

    test(
        "merge_dicts",
        "import dict_operations; d = dict_operations.merge_dicts({'a': 1}, {'b': 2}); print(len(d))",
        "2",
    )


def test_inventory():
    """Test inventory module."""
    print("\n[TEST] Testing inventory module...")

    test(
        "Inventory instance",
        "import inventory; inv = inventory.Inventory(); print(type(inv).__name__)",
        "Inventory",
    )

    test(
        "Inventory total_count starts at 0",
        "import inventory; inv = inventory.Inventory(); print(inv.total_count)",
        "0",
    )

    test(
        "Inventory add_item and get_quantity",
        "import inventory; inv = inventory.Inventory(); inv.add_item(100, 5); print(inv.get_quantity(100))",
        "5",
    )

    test(
        "Inventory item_count",
        "import inventory; inv = inventory.Inventory(); inv.add_item(100, 5); inv.add_item(200, 3); print(inv.item_count())",
        "2",
    )

    test(
        "Inventory total_quantity",
        "import inventory; inv = inventory.Inventory(); inv.add_item(100, 5); inv.add_item(200, 3); print(inv.total_quantity())",
        "8",
    )

    test(
        "Inventory has_item existing",
        "import inventory; inv = inventory.Inventory(); inv.add_item(100, 5); print(inv.has_item(100))",
        "True",
    )

    test(
        "Inventory has_item missing",
        "import inventory; inv = inventory.Inventory(); print(inv.has_item(999))",
        "False",
    )


def test_tuple_operations():
    """Test tuple_operations module."""
    print("\n[TEST] Testing tuple_operations module...")

    # Tuple creation
    test(
        "make_point",
        "import tuple_operations as t; print(t.make_point())",
        "(10, 20)",
    )

    test(
        "make_triple",
        "import tuple_operations as t; print(t.make_triple(1, 2, 3))",
        "(1, 2, 3)",
    )

    test(
        "empty_tuple",
        "import tuple_operations as t; print(t.empty_tuple())",
        "()",
    )

    test(
        "single_element",
        "import tuple_operations as t; print(t.single_element())",
        "(42,)",
    )

    # Tuple indexing
    test(
        "get_first",
        "import tuple_operations as t; print(t.get_first((10, 20, 30)))",
        "10",
    )

    test(
        "get_last",
        "import tuple_operations as t; print(t.get_last((10, 20, 30)))",
        "30",
    )

    # Tuple operations
    test(
        "tuple_len",
        "import tuple_operations as t; print(t.tuple_len((1, 2, 3, 4, 5)))",
        "5",
    )

    test(
        "tuple_contains (found)",
        "import tuple_operations as t; print(t.tuple_contains((1, 2, 3), 2))",
        "True",
    )

    test(
        "tuple_contains (not found)",
        "import tuple_operations as t; print(t.tuple_contains((1, 2, 3), 5))",
        "False",
    )

    test(
        "tuple_not_contains",
        "import tuple_operations as t; print(t.tuple_not_contains((1, 2, 3), 5))",
        "True",
    )

    # Tuple iteration
    test(
        "sum_tuple",
        "import tuple_operations as t; print(t.sum_tuple((1, 2, 3, 4, 5)))",
        "15",
    )

    test(
        "nested_iteration",
        "import tuple_operations as t; print(t.nested_iteration((10, 20, 30)))",
        "80",
    )

    # Tuple unpacking
    test(
        "unpack_pair",
        "import tuple_operations as t; print(t.unpack_pair((10, 20)))",
        "30",
    )

    test(
        "unpack_triple",
        "import tuple_operations as t; print(t.unpack_triple((2, 3, 4)))",
        "24",
    )

    # Tuple concat/repeat
    test(
        "concat_tuples",
        "import tuple_operations as t; print(t.concat_tuples((1, 2), (3, 4)))",
        "(1, 2, 3, 4)",
    )

    test(
        "repeat_tuple",
        "import tuple_operations as t; print(t.repeat_tuple((1, 2), 3))",
        "(1, 2, 1, 2, 1, 2)",
    )

    # Tuple slicing
    test(
        "slice_tuple",
        "import tuple_operations as t; print(t.slice_tuple((1, 2, 3, 4, 5)))",
        "(2, 3)",
    )

    # Tuple from range
    test(
        "from_range",
        "import tuple_operations as t; print(t.from_range(5))",
        "(0, 1, 2, 3, 4)",
    )


def test_set_operations():
    """Test set_operations module."""
    print("\n[TEST] Testing set_operations module...")

    # Set creation
    test(
        "make_set",
        "import set_operations as s; r = s.make_set(); print(1 in r and 2 in r and 3 in r)",
        "True",
    )

    test(
        "empty_set",
        "import set_operations as s; print(s.empty_set())",
        "set()",
    )

    test(
        "set_from_range",
        "import set_operations as s; r = s.set_from_range(5); print(len(r) == 5 and 0 in r and 4 in r)",
        "True",
    )

    # Set operations
    test(
        "set_len",
        "import set_operations as s; print(s.set_len({1, 2, 3, 4, 5}))",
        "5",
    )

    test(
        "set_contains (found)",
        "import set_operations as s; print(s.set_contains({1, 2, 3}, 2))",
        "True",
    )

    test(
        "set_contains (not found)",
        "import set_operations as s; print(s.set_contains({1, 2, 3}, 5))",
        "False",
    )

    test(
        "set_not_contains",
        "import set_operations as s; print(s.set_not_contains({1, 2, 3}, 5))",
        "True",
    )

    # Set modification
    test(
        "set_add",
        "import set_operations as s; r = s.set_add({1, 2}, 3); print(3 in r)",
        "True",
    )

    test(
        "set_discard",
        "import set_operations as s; r = s.set_discard({1, 2, 3}, 2); print(2 not in r)",
        "True",
    )

    test(
        "set_remove",
        "import set_operations as s; r = s.set_remove({1, 2, 3}, 2); print(2 not in r)",
        "True",
    )

    test(
        "set_clear",
        "import set_operations as s; r = s.set_clear({1, 2, 3}); print(len(r))",
        "0",
    )

    # Set copy and update
    test(
        "set_copy",
        "import set_operations as s; r = s.set_copy({1, 2, 3}); print(len(r))",
        "3",
    )

    test(
        "set_update",
        "import set_operations as s; r = s.set_update({1, 2}, {3, 4}); print(len(r))",
        "4",
    )

    # Set iteration
    test(
        "sum_set",
        "import set_operations as s; print(s.sum_set({1, 2, 3, 4, 5}))",
        "15",
    )

    # Practical examples
    test(
        "build_set_incremental",
        "import set_operations as s; print(s.build_set_incremental(20))",
        "10",
    )

    test(
        "filter_duplicates",
        "import set_operations as s; print(s.filter_duplicates(10))",
        "10",
    )


def run_all_tests():
    """Run all test suites."""
    global total_tests, passed_tests, failed_tests
    total_tests = 0
    passed_tests = 0
    failed_tests = []

    print("=" * 70)
    print("[TEST SUITE] mypyc-micropython Comprehensive Device Test Suite")
    print("=" * 70)
    print(f"Device port: {PORT}")
    print("=" * 70)

    # Run all test suites
    test_factorial()
    test_point()
    test_counter()
    test_sensor()
    test_list_operations()
    test_math_utils()
    test_bitwise()
    test_algorithms()
    test_dict_operations()
    test_inventory()
    test_tuple_operations()
    test_set_operations()

    # Print summary
    print("\n" + "=" * 70)
    print("[SUMMARY] TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests run: {total_tests}")
    print(f"Passed: {passed_tests} PASS")
    print(f"Failed: {len(failed_tests)} FAIL")

    if total_tests > 0:
        success_rate = (passed_tests / total_tests) * 100
        print(f"Success rate: {success_rate:.1f}%")

        if success_rate == 100:
            print("SUCCESS ALL TESTS PASSED! SUCCESS")
        elif success_rate >= 80:
            print("[GOOD] Good results - most tests passing")
        elif success_rate >= 50:
            print("[WARNING]  Mixed results - some issues to address")
        else:
            print("FAIL Poor results - significant issues found")

    if failed_tests:
        print("\nFAIL Failed tests:")
        for name, reason in failed_tests:
            print(f"  - {name}")
            print(f"    {reason[:100]}{'...' if len(reason) > 100 else ''}")

    print("=" * 70)

    return len(failed_tests) == 0


def main():
    """Main entry point with argument parsing."""
    global PORT

    parser = argparse.ArgumentParser(
        description="Comprehensive device test runner for mypyc-micropython"
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help=f"Serial port for ESP32 device (default: {DEFAULT_PORT})",
    )
    args = parser.parse_args()

    PORT = args.port

    print("[CHECK] Checking device connection...")
    success, output = run_on_device("print('Device ready')")
    if not success:
        print(f"FAIL Cannot connect to device on {PORT}")
        print(f"Error: {output}")
        print("\nMake sure:")
        print("  1. ESP32 device is connected via USB")
        print(f"  2. Device port is correct (current: {PORT})")
        print("  3. Firmware has been flashed with 'make deploy'")
        sys.exit(1)

    print("PASS Device connected and responding\n")

    success = run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
