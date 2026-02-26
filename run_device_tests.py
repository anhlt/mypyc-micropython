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
import time
from typing import Callable

# Default configuration
DEFAULT_PORT = "/dev/ttyACM0"

# Global port (set from command line args)
PORT = DEFAULT_PORT

# Test tracking
total_tests = 0
passed_tests = 0
failed_tests: list[tuple[str, str]] = []



# Waveshare ESP32-C6-LCD-1.47 board: RGB LED (WS2812) on GPIO8
RGB_LED_GPIO = 8


def _wait_for_port(port: str, max_retries: int = 20, interval: float = 0.3) -> bool:
    """Wait until the serial port is not held by another process.

    Uses two strategies:
    1. lsof to check if any process holds the port file
    2. Try opening the port directly as a fallback
    """
    import os
    for attempt in range(max_retries):
        # Strategy 1: lsof check
        try:
            result = subprocess.run(
                ["lsof", "-t", port],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode != 0:
                return True  # No process holds the port
        except Exception:
            pass  # lsof failed, try direct open

        # Strategy 2: try opening the device file directly
        try:
            fd = os.open(port, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY)
            os.close(fd)
            return True
        except OSError:
            pass  # Port busy

        time.sleep(interval)
    return False


def run_on_device(
    code: str, port: str = "", timeout: int = 30, max_retries: int = 3,
) -> tuple[bool, str]:
    """Execute Python code on device via mpremote with automatic retry.

    Waits for port availability before each attempt. Retries on port
    contention errors (common on macOS USB serial).
    """
    device_port = port if port else PORT
    last_error = ""
    for attempt in range(max_retries):
        _wait_for_port(device_port)
        try:
            result = subprocess.run(
                ["mpremote", "connect", device_port, "exec", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            last_error = result.stderr.strip()
            # Retry on transient errors (port contention, raw repl)
            retryable = (
                "failed to access" in last_error
                or "it may be in use" in last_error
                or "could not enter raw repl" in last_error
            )
            if retryable:
                time.sleep(0.5 * (attempt + 1))  # Backoff
                continue
            return False, last_error
        except subprocess.TimeoutExpired:
            return False, "Timeout"
        except Exception as e:
            last_error = str(e)
            time.sleep(0.5)
    return False, last_error


def led_rgb(r: int, g: int, b: int) -> None:
    """Set the onboard WS2812 RGB LED to a specific color."""
    code = (
        f"from machine import Pin; from neopixel import NeoPixel; "
        f"np = NeoPixel(Pin({RGB_LED_GPIO}, Pin.OUT), 1); "
        f"np[0] = ({r}, {g}, {b}); np.write()"
    )
    run_on_device(code)


def led_off() -> None:
    """Turn off the onboard RGB LED."""
    led_rgb(0, 0, 0)


def led_cycle_colors() -> None:
    """Cycle RGB LED through R, G, B, White -- visual proof the board responds."""
    import time

    colors = [
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 0, 255),
        ("White", 255, 255, 255),
    ]
    print("[LED] Cycling RGB LED on GPIO8 (visual board check)...")
    for name, r, g, b in colors:
        sys.stdout.write(f"  LED -> {name}... ")
        sys.stdout.flush()
        led_rgb(r, g, b)
        print("OK")
        time.sleep(0.4)
    led_off()
    print("[LED] LED cycle complete -- board is responding!\n")


def test(name: str, code: str, expected: str | Callable[[str], bool]) -> None:
    """Run a single test case."""
    global total_tests, passed_tests
    total_tests += 1

    sys.stdout.write(f"  {name}... ")
    sys.stdout.flush()

    success, output = run_on_device(code)

    if not success:
        failed_tests.append((name, f"Execution failed: {output}"))
        print(f"FAIL")
        print(f"    Error: {output[:80]}")
        return

    if callable(expected):
        passed = expected(output)
    else:
        passed = expected in output

    if passed:
        passed_tests += 1
        print("PASS")
    else:
        failed_tests.append((name, f"Expected: {expected}, Got: {output}"))
        print(f"FAIL")
        print(f"    Expected: {expected}")
        print(f"    Got: {output[:80]}")


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

    # RTuple optimization tests
    test(
        "rtuple_point",
        "import tuple_operations as t; print(t.rtuple_point())",
        "(100, 200)",
    )

    test(
        "rtuple_add_coords",
        "import tuple_operations as t; print(t.rtuple_add_coords(10, 20, 30, 40))",
        "(40, 60)",
    )

    test(
        "rtuple_sum_fields",
        "import tuple_operations as t; print(t.rtuple_sum_fields())",
        "40",
    )

    test(
        "rtuple_distance_squared",
        "import tuple_operations as t; print(t.rtuple_distance_squared(0, 0, 3, 4))",
        "25",
    )

    test(
        "rtuple_rgb",
        "import tuple_operations as t; print(t.rtuple_rgb())",
        "(255, 128, 64)",
    )

    test(
        "rtuple_sum_rgb",
        "import tuple_operations as t; print(t.rtuple_sum_rgb(100, 150, 200))",
        "450",
    )

    test(
        "rtuple_blend_colors",
        "import tuple_operations as t; print(t.rtuple_blend_colors(200, 100, 50, 100, 200, 150))",
        "(150, 150, 100)",
    )

    test(
        "rtuple_benchmark_internal",
        "import tuple_operations as t; print(t.rtuple_benchmark_internal(10))",
        "135",
    )

    test(
        "sum_points_list",
        "import tuple_operations as t; points = [(1, 2, 3), (4, 5, 6), (7, 8, 9)]; print(t.sum_points_list(points, 3))",
        "45",
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


def test_builtins_demo():
    """Test builtins_demo module (bool, min, max, sum)."""
    print("\n[TEST] Testing builtins_demo module...")

    # bool() builtin
    test(
        "is_truthy(1)",
        "import builtins_demo as b; print(b.is_truthy(1))",
        "True",
    )

    test(
        "is_truthy(0)",
        "import builtins_demo as b; print(b.is_truthy(0))",
        "False",
    )

    test(
        "is_list_empty([])",
        "import builtins_demo as b; print(b.is_list_empty([]))",
        "True",
    )

    test(
        "is_list_empty([1])",
        "import builtins_demo as b; print(b.is_list_empty([1]))",
        "False",
    )

    # min() builtin
    test(
        "find_min_two(5, 3)",
        "import builtins_demo as b; print(b.find_min_two(5, 3))",
        "3",
    )

    test(
        "find_min_three(7, 2, 9)",
        "import builtins_demo as b; print(b.find_min_three(7, 2, 9))",
        "2",
    )

    # max() builtin
    test(
        "find_max_two(5, 3)",
        "import builtins_demo as b; print(b.find_max_two(5, 3))",
        "5",
    )

    test(
        "find_max_three(7, 2, 9)",
        "import builtins_demo as b; print(b.find_max_three(7, 2, 9))",
        "9",
    )

    # sum() builtin
    test(
        "sum_list([1, 2, 3, 4, 5])",
        "import builtins_demo as b; print(b.sum_list([1, 2, 3, 4, 5]))",
        "15",
    )

    test(
        "sum_list_with_start([1, 2, 3], 10)",
        "import builtins_demo as b; print(b.sum_list_with_start([1, 2, 3], 10))",
        "16",
    )

    # Combination functions
    test(
        "clamp(5, 0, 10)",
        "import builtins_demo as b; print(b.clamp(5, 0, 10))",
        "5",
    )

    test(
        "clamp(-5, 0, 10)",
        "import builtins_demo as b; print(b.clamp(-5, 0, 10))",
        "0",
    )

    test(
        "clamp(15, 0, 10)",
        "import builtins_demo as b; print(b.clamp(15, 0, 10))",
        "10",
    )

    test(
        "abs_diff(10, 3)",
        "import builtins_demo as b; print(b.abs_diff(10, 3))",
        "7",
    )

    test(
        "abs_diff(3, 10)",
        "import builtins_demo as b; print(b.abs_diff(3, 10))",
        "7",
    )

    test(
        "clamp_list([1, 5, 10, 15], 3, 12)",
        "import builtins_demo as b; print(b.clamp_list([1, 5, 10, 15], 3, 12))",
        "[3, 5, 10, 12]",
    )

    test(
        "find_extremes_sum([1, 5, 3, 9, 2])",
        "import builtins_demo as b; print(b.find_extremes_sum([1, 5, 3, 9, 2]))",
        "10",
    )

    test(
        "sum_int_list([1, 2, 3, 4, 5])",
        "import builtins_demo as b; print(b.sum_int_list([1, 2, 3, 4, 5]))",
        "15",
    )

    test(
        "sum_int_list(range(101))",
        "import builtins_demo as b; print(b.sum_int_list(list(range(101))))",
        "5050",
    )

    test(
        "sum_int_list([])",
        "import builtins_demo as b; print(b.sum_int_list([]))",
        "0",
    )


def test_default_args():
    """Test default_args module (default argument support)."""
    print("\n[TEST] Testing default_args module...")

    test(
        "add_with_default(5, 3)",
        "import default_args as d; print(d.add_with_default(5, 3))",
        "8",
    )

    test(
        "add_with_default(5)",
        "import default_args as d; print(d.add_with_default(5))",
        "15",
    )

    test(
        "clamp(150)",
        "import default_args as d; print(d.clamp(150))",
        "100",
    )

    test(
        "clamp(-10)",
        "import default_args as d; print(d.clamp(-10))",
        "0",
    )

    test(
        "clamp(50)",
        "import default_args as d; print(d.clamp(50))",
        "50",
    )

    test(
        "clamp(50, 10, 40)",
        "import default_args as d; print(d.clamp(50, 10, 40))",
        "40",
    )

    test(
        "increment(10)",
        "import default_args as d; print(d.increment(10))",
        "11",
    )

    test(
        "increment(10, 5)",
        "import default_args as d; print(d.increment(10, 5))",
        "15",
    )

    test(
        "double_if_flag(5)",
        "import default_args as d; print(d.double_if_flag(5))",
        "10",
    )

    test(
        "double_if_flag(5, False)",
        "import default_args as d; print(d.double_if_flag(5, False))",
        "5",
    )

    test(
        "all_defaults()",
        "import default_args as d; print(d.all_defaults())",
        "6",
    )

    test(
        "all_defaults(10)",
        "import default_args as d; print(d.all_defaults(10))",
        "15",
    )

    test(
        "all_defaults(10, 20)",
        "import default_args as d; print(d.all_defaults(10, 20))",
        "33",
    )

    test(
        "all_defaults(10, 20, 30)",
        "import default_args as d; print(d.all_defaults(10, 20, 30))",
        "60",
    )

    test(
        "power(2)",
        "import default_args as d; print(d.power(2))",
        "4",
    )

    test(
        "power(2, 3)",
        "import default_args as d; print(d.power(2, 3))",
        "8",
    )

    test(
        "sum_with_start([1,2,3])",
        "import default_args as d; print(d.sum_with_start([1, 2, 3]))",
        "6",
    )

    test(
        "sum_with_start([1,2,3], 10)",
        "import default_args as d; print(d.sum_with_start([1, 2, 3], 10))",
        "16",
    )


def test_star_args():
    """Test star_args module with *args and **kwargs."""
    print("\n[TEST] Testing star_args module (*args/**kwargs)...")

    test(
        "sum_all(1, 2, 3)",
        "import star_args as s; print(s.sum_all(1, 2, 3))",
        "6",
    )

    test(
        "sum_all()",
        "import star_args as s; print(s.sum_all())",
        "0",
    )

    test(
        "sum_all(10, 20, 30, 40)",
        "import star_args as s; print(s.sum_all(10, 20, 30, 40))",
        "100",
    )

    test(
        "sum_args(5, 10, 15)",
        "import star_args as s; print(s.sum_args(5, 10, 15))",
        "30",
    )

    test(
        "count_args(1, 2, 3, 4, 5)",
        "import star_args as s; print(s.count_args(1, 2, 3, 4, 5))",
        "5",
    )

    test(
        "count_args()",
        "import star_args as s; print(s.count_args())",
        "0",
    )

    test(
        "first_or_default(42, 1, 2)",
        "import star_args as s; print(s.first_or_default(42, 1, 2))",
        "42",
    )

    test(
        "first_or_default()",
        "import star_args as s; print(s.first_or_default())",
        "-1",
    )

    test(
        "log_values(100, 1, 2, 3)",
        "import star_args as s; print(s.log_values(100, 1, 2, 3))",
        "106",
    )

    test(
        "log_values(50)",
        "import star_args as s; print(s.log_values(50))",
        "50",
    )

    test(
        "count_kwargs(a=1, b=2)",
        "import star_args as s; print(s.count_kwargs(a=1, b=2))",
        "2",
    )

    test(
        "count_kwargs()",
        "import star_args as s; print(s.count_kwargs())",
        "0",
    )

    test(
        "make_config(x=1, y=2) is dict",
        "import star_args as s; print(type(s.make_config(x=1, y=2)).__name__)",
        "dict",
    )

    test(
        "process(10, 1, 2, a=1, b=2)",
        "import star_args as s; print(s.process(10, 1, 2, a=1, b=2))",
        "15",
    )

    test(
        "max_of_args(3, 7, 2, 9, 1)",
        "import star_args as s; print(s.max_of_args(3, 7, 2, 9, 1))",
        "9",
    )

    test(
        "min_of_args(3, 7, 2, 9, 1)",
        "import star_args as s; print(s.min_of_args(3, 7, 2, 9, 1))",
        "1",
    )


def test_chained_attr():
    """Test chained_attr module with nested class attribute access."""
    print("\n[TEST] Testing chained_attr module (chained attribute access)...")

    test(
        "get_width(rect)",
        "import chained_attr as ca; tl = ca.Point(0, 0); br = ca.Point(100, 50); r = ca.Rectangle(tl, br); print(ca.get_width(r))",
        "100",
    )

    test(
        "get_height(rect)",
        "import chained_attr as ca; tl = ca.Point(0, 0); br = ca.Point(100, 50); r = ca.Rectangle(tl, br); print(ca.get_height(r))",
        "50",
    )

    test(
        "get_area(rect)",
        "import chained_attr as ca; tl = ca.Point(0, 0); br = ca.Point(10, 5); r = ca.Rectangle(tl, br); print(ca.get_area(r))",
        "50",
    )

    test(
        "get_top_left_x(rect)",
        "import chained_attr as ca; tl = ca.Point(3, 7); br = ca.Point(10, 20); r = ca.Rectangle(tl, br); print(ca.get_top_left_x(r))",
        "3",
    )

    test(
        "get_top_left_y(rect)",
        "import chained_attr as ca; tl = ca.Point(3, 7); br = ca.Point(10, 20); r = ca.Rectangle(tl, br); print(ca.get_top_left_y(r))",
        "7",
    )

    test(
        "get_bottom_right_x(rect)",
        "import chained_attr as ca; tl = ca.Point(3, 7); br = ca.Point(10, 20); r = ca.Rectangle(tl, br); print(ca.get_bottom_right_x(r))",
        "10",
    )

    test(
        "get_bottom_right_y(rect)",
        "import chained_attr as ca; tl = ca.Point(3, 7); br = ca.Point(10, 20); r = ca.Rectangle(tl, br); print(ca.get_bottom_right_y(r))",
        "20",
    )

    test(
        "get_next_value(node) self-ref",
        "import chained_attr as ca; n2 = ca.Node(42, None); n1 = ca.Node(10, n2); print(ca.get_next_value(n1))",
        "42",
    )


def test_container_attrs():
    """Test container_attrs module with list/dict/set class attributes."""
    print("\n[TEST] Testing container_attrs module (container attributes)...")

    test(
        "get_items(Container)",
        "import container_attrs as ca; c = ca.Container([1,2,3], {'a':1}, {1,2}); print(ca.get_items(c))",
        "[1, 2, 3]",
    )

    test(
        "get_mapping(Container)",
        "import container_attrs as ca; c = ca.Container([1], {'x':10}, {1}); print(ca.get_mapping(c))",
        "{'x': 10}",
    )

    test(
        "get_unique(Container)",
        "import container_attrs as ca; c = ca.Container([1], {'a':1}, {5,10,15}); r = ca.get_unique(c); print(5 in r and 10 in r)",
        "True",
    )

    test(
        "get_first_item(Container)",
        "import container_attrs as ca; c = ca.Container([42,2,3], {}, set()); print(ca.get_first_item(c))",
        "42",
    )

    test(
        "get_mapping_key(Container)",
        "import container_attrs as ca; c = ca.Container([], {'key':99}, set()); print(ca.get_mapping_key(c, 'key'))",
        "99",
    )

    test(
        "has_in_unique(Container) True",
        "import container_attrs as ca; c = ca.Container([], {}, {1,2,3}); print(ca.has_in_unique(c, 2))",
        "True",
    )

    test(
        "has_in_unique(Container) False",
        "import container_attrs as ca; c = ca.Container([], {}, {1,2,3}); print(ca.has_in_unique(c, 5))",
        "False",
    )

    test(
        "get_inner_items(Outer)",
        "import container_attrs as ca; i = ca.Inner([10,20,30], {}); o = ca.Outer(i, 'test'); print(ca.get_inner_items(o))",
        "[10, 20, 30]",
    )

    test(
        "get_inner_data(Outer)",
        "import container_attrs as ca; i = ca.Inner([], {'k':5}); o = ca.Outer(i, 'test'); print(ca.get_inner_data(o))",
        "{'k': 5}",
    )

    test(
        "get_first_inner_item(Outer)",
        "import container_attrs as ca; i = ca.Inner([100,200], {}); o = ca.Outer(i, 'test'); print(ca.get_first_inner_item(o))",
        "100",
    )

    test(
        "get_inner_data_key(Outer)",
        "import container_attrs as ca; i = ca.Inner([], {'val':77}); o = ca.Outer(i, 'test'); print(ca.get_inner_data_key(o, 'val'))",
        "77",
    )

    test(
        "count_inner_items(Outer)",
        "import container_attrs as ca; i = ca.Inner([1,2,3,4,5], {}); o = ca.Outer(i, 'test'); print(ca.count_inner_items(o))",
        "5",
    )

    test(
        "sum_inner_items(Outer)",
        "import container_attrs as ca; i = ca.Inner([1,2,3,4,5], {}); o = ca.Outer(i, 'test'); print(ca.sum_inner_items(o))",
        "15",
    )


def test_class_param():
    """Test class_param module with functions taking class parameters."""
    print("\n[TEST] Testing class_param module (class parameters)...")

    test(
        "get_x(Point(10, 20))",
        "import class_param as cp; p = cp.Point(10, 20); print(cp.get_x(p))",
        "10",
    )

    test(
        "get_y(Point(10, 20))",
        "import class_param as cp; p = cp.Point(10, 20); print(cp.get_y(p))",
        "20",
    )

    test(
        "add_coords(Point(3, 4))",
        "import class_param as cp; p = cp.Point(3, 4); print(cp.add_coords(p))",
        "7",
    )

    test(
        "distance_squared two points",
        "import class_param as cp; p1 = cp.Point(0, 0); p2 = cp.Point(3, 4); print(cp.distance_squared(p1, p2))",
        "25",
    )

    test(
        "midpoint_x two points",
        "import class_param as cp; p1 = cp.Point(0, 0); p2 = cp.Point(10, 10); print(cp.midpoint_x(p1, p2))",
        "5",
    )

    test(
        "scale_point(Point(2, 3), 4)",
        "import class_param as cp; p = cp.Point(2, 3); print(cp.scale_point(p, 4))",
        "20",
    )

    test(
        "dot_product vectors",
        "import class_param as cp; v1 = cp.Vector(1.0, 2.0); v2 = cp.Vector(3.0, 4.0); print(cp.dot_product(v1, v2))",
        "11.0",
    )

    test(
        "length_squared vector",
        "import class_param as cp; v = cp.Vector(3.0, 4.0); print(cp.length_squared(v))",
        "25.0",
    )


def test_string_operations():
    """Test string_operations module."""
    print("\n[TEST] Testing string_operations module...")

    test(
        "concat_strings",
        "import string_operations as s; print(s.concat_strings('hello', ' world'))",
        "hello world",
    )

    test(
        "repeat_string",
        "import string_operations as s; print(s.repeat_string('ab', 3))",
        "ababab",
    )

    test(
        "to_upper",
        "import string_operations as s; print(s.to_upper('hello'))",
        "HELLO",
    )

    test(
        "to_lower",
        "import string_operations as s; print(s.to_lower('HELLO'))",
        "hello",
    )

    test(
        "find_substring found",
        "import string_operations as s; print(s.find_substring('hello world', 'world'))",
        "6",
    )

    test(
        "find_substring not found",
        "import string_operations as s; print(s.find_substring('hello world', 'xyz'))",
        "-1",
    )

    test(
        "rfind_substring",
        "import string_operations as s; print(s.rfind_substring('hello hello', 'hello'))",
        "6",
    )

    test(
        "count_substring",
        "import string_operations as s; print(s.count_substring('abababab', 'ab'))",
        "4",
    )

    test(
        "split_string",
        "import string_operations as s; print(s.split_string('a b c'))",
        "['a', 'b', 'c']",
    )

    test(
        "split_on_sep",
        "import string_operations as s; print(s.split_on_sep('a,b,c', ','))",
        "['a', 'b', 'c']",
    )

    test(
        "join_strings",
        "import string_operations as s; print(s.join_strings('-', ['a', 'b', 'c']))",
        "a-b-c",
    )

    test(
        "strip_string",
        "import string_operations as s; print(repr(s.strip_string('  hello  ')))",
        "'hello'",
    )

    test(
        "lstrip_string",
        "import string_operations as s; print(repr(s.lstrip_string('  hello  ')))",
        "'hello  '",
    )

    test(
        "rstrip_string",
        "import string_operations as s; print(repr(s.rstrip_string('  hello  ')))",
        "'  hello'",
    )

    test(
        "strip_chars",
        "import string_operations as s; print(s.strip_chars('xxxhelloxxx', 'x'))",
        "hello",
    )

    test(
        "replace_string",
        "import string_operations as s; print(s.replace_string('hello world', 'world', 'python'))",
        "hello python",
    )

    test(
        "starts_with true",
        "import string_operations as s; print(s.starts_with('hello world', 'hello'))",
        "True",
    )

    test(
        "starts_with false",
        "import string_operations as s; print(s.starts_with('hello world', 'world'))",
        "False",
    )

    test(
        "ends_with true",
        "import string_operations as s; print(s.ends_with('hello world', 'world'))",
        "True",
    )

    test(
        "ends_with false",
        "import string_operations as s; print(s.ends_with('hello world', 'hello'))",
        "False",
    )

    test(
        "center_string",
        "import string_operations as s; print(repr(s.center_string('hi', 6)))",
        "'  hi  '",
    )

    test(
        "partition_string",
        "import string_operations as s; print(s.partition_string('hello=world', '='))",
        "('hello', '=', 'world')",
    )

    test(
        "rpartition_string",
        "import string_operations as s; print(s.rpartition_string('a=b=c', '='))",
        "('a=b', '=', 'c')",
    )

    test(
        "process_csv_line",
        "import string_operations as s; print(s.process_csv_line('a, b, c'))",
        "['a', 'b', 'c']",
    )

    test(
        "normalize_text",
        "import string_operations as s; print(s.normalize_text('  Hello   World  '))",
        "hello world",
    )

    test(
        "build_path",
        "import string_operations as s; print(s.build_path(['home', 'user', 'file.txt']))",
        "home/user/file.txt",
    )

    test(
        "extract_extension",
        "import string_operations as s; print(s.extract_extension('document.pdf'))",
        "pdf",
    )

    test(
        "extract_extension no ext",
        "import string_operations as s; print(repr(s.extract_extension('README')))",
        "''",
    )


def test_itertools_builtins():
    """Test itertools_builtins module (enumerate, zip, sorted)."""
    print("\n[TEST] Testing itertools_builtins module...")

    test(
        "sum_with_indices",
        "import itertools_builtins as ib; print(ib.sum_with_indices([10, 20, 30]))",
        "80",
    )

    test(
        "enumerate_from_start",
        "import itertools_builtins as ib; print(ib.enumerate_from_start(['a', 'b', 'c'], 5))",
        "[5, 6, 7]",
    )

    test(
        "dot_product",
        "import itertools_builtins as ib; print(ib.dot_product([1, 2, 3], [4, 5, 6]))",
        "32",
    )

    test(
        "zip_three_lists",
        "import itertools_builtins as ib; print(ib.zip_three_lists([1, 2], [10, 20], [100, 200]))",
        "[111, 222]",
    )

    test(
        "get_sorted",
        "import itertools_builtins as ib; print(ib.get_sorted([3, 1, 2]))",
        "[1, 2, 3]",
    )

    test(
        "sum_sorted",
        "import itertools_builtins as ib; print(ib.sum_sorted([3, 1, 2]))",
        "6",
    )

    test(
        "get_first_sorted",
        "import itertools_builtins as ib; print(ib.get_first_sorted([30, 10, 20]))",
        "10",
    )

    test(
        "get_last_sorted",
        "import itertools_builtins as ib; print(ib.get_last_sorted([30, 10, 20]))",
        "30",
    )


def test_exception_handling():
    """Test exception_handling module (try/except/finally/raise)."""
    print("\n[TEST] Testing exception_handling module...")

    test(
        "safe_divide(10, 2)",
        "import exception_handling as eh; print(eh.safe_divide(10, 2))",
        "5",
    )

    test(
        "safe_divide(10, 0)",
        "import exception_handling as eh; print(eh.safe_divide(10, 0))",
        "0",
    )

    test(
        "validate_positive(5)",
        "import exception_handling as eh; print(eh.validate_positive(5))",
        "5",
    )

    test(
        "validate_range(50, 0, 100)",
        "import exception_handling as eh; print(eh.validate_range(50, 0, 100))",
        "50",
    )

    test(
        "with_cleanup(5)",
        "import exception_handling as eh; print(eh.with_cleanup(5))",
        "11",
    )

    test(
        "multi_catch(10, 2)",
        "import exception_handling as eh; print(eh.multi_catch(10, 2))",
        "5",
    )

    test(
        "multi_catch(10, 0)",
        "import exception_handling as eh; print(eh.multi_catch(10, 0))",
        "-1",
    )

    test(
        "multi_catch(-5, 2)",
        "import exception_handling as eh; print(eh.multi_catch(-5, 2))",
        "-2",
    )

    test(
        "try_else(3, 4)",
        "import exception_handling as eh; print(eh.try_else(3, 4))",
        "14",
    )

    test(
        "full_try(10, 2)",
        "import exception_handling as eh; print(eh.full_try(10, 2))",
        "105",
    )

    test(
        "full_try(10, 0)",
        "import exception_handling as eh; print(eh.full_try(10, 0))",
        "99",
    )

    test(
        "catch_all(50)",
        "import exception_handling as eh; print(eh.catch_all(50))",
        "50",
    )

    test(
        "catch_all(-5)",
        "import exception_handling as eh; print(eh.catch_all(-5))",
        "-1",
    )

    test(
        "catch_all(150)",
        "import exception_handling as eh; print(eh.catch_all(150))",
        "-1",
    )

    test(
        "nested_try(10, 2, 1)",
        "import exception_handling as eh; print(eh.nested_try(10, 2, 1))",
        "5",
    )

    test(
        "nested_try(10, 0, 2)",
        "import exception_handling as eh; print(eh.nested_try(10, 0, 2))",
        "0",
    )

    test(
        "nested_try(10, 0, 0)",
        "import exception_handling as eh; print(eh.nested_try(10, 0, 0))",
        "-1",
    )


def test_super_calls():
    """Test super_calls module (3-level inheritance with super().__init__)."""
    print("\n[TEST] Testing super_calls module...")

    test(
        "ShowDog creation with chained super().__init__",
        "import super_calls as s; sd = s.ShowDog('Bella', 10, 3); print(sd.name)",
        "Bella",
    )

    test(
        "ShowDog inherits speak from Animal",
        "import super_calls as s; sd = s.ShowDog('Bella', 10, 3); print(sd.speak())",
        "Woof",
    )

    test(
        "ShowDog.describe chains super() through Dog to Animal",
        "import super_calls as s; sd = s.ShowDog('Bella', 10, 3); print(sd.describe())",
        "Bella",
    )

    test(
        "ShowDog.get_awards own method",
        "import super_calls as s; sd = s.ShowDog('Bella', 10, 3); print(sd.get_awards())",
        "3",
    )

    test(
        "ShowDog.get_total_score cross-level field access",
        "import super_calls as s; sd = s.ShowDog('Bella', 10, 3); print(sd.get_total_score())",
        "13",
    )

    test(
        "ShowDog.get_tricks inherited from Dog",
        "import super_calls as s; sd = s.ShowDog('Bella', 10, 3); print(sd.get_tricks())",
        "10",
    )

def test_decorators():
    """Test @property, @staticmethod, @classmethod decorators."""
    print("\n[TEST] Testing decorators module...")

    # @staticmethod
    test(
        "Rectangle.is_square_dims(3, 3) staticmethod",
        "import decorators as d; print(d.Rectangle.is_square_dims(3, 3))",
        "True",
    )

    test(
        "Rectangle.is_square_dims(3, 4) staticmethod",
        "import decorators as d; print(d.Rectangle.is_square_dims(3, 4))",
        "False",
    )

    test(
        "Counter.add(3, 4) staticmethod",
        "import decorators as d; print(d.Counter.add(3, 4))",
        "7",
    )

    # @classmethod
    test(
        "Rectangle.square(5) classmethod returns cls",
        "import decorators as d; r = d.Rectangle.square(5); print(r is d.Rectangle)",
        "True",
    )

    # @property getter
    test(
        "Rectangle.area property",
        "import decorators as d; r = d.Rectangle(3, 4); print(r.area)",
        "12",
    )

    test(
        "Rectangle.perimeter property",
        "import decorators as d; r = d.Rectangle(3, 4); print(r.perimeter)",
        "14",
    )

    test(
        "Temperature.celsius property getter",
        "import decorators as d; t = d.Temperature(25); print(t.celsius)",
        "25",
    )

    # @property setter
    test(
        "Temperature.celsius property setter",
        "import decorators as d; t = d.Temperature(25); t.celsius = 30; print(t.celsius)",
        "30",
    )

    # Counter property + methods
    test(
        "Counter.count property",
        "import decorators as d; c = d.Counter(0); print(c.count)",
        "0",
    )

    test(
        "Counter.count after increment",
        "import decorators as d; c = d.Counter(0); c.increment(); print(c.count)",
        "1",
    )

    # Instance staticmethod call
    test(
        "Counter.add via instance",
        "import decorators as d; c = d.Counter(0); print(c.add(10, 20))",
        "30",
    )

    # Temperature fahrenheit method + property
    test(
        "Temperature.get_fahrenheit with property",
        "import decorators as d; t = d.Temperature(100); print(t.get_fahrenheit())",
        "212",
    )

    # Property after scale
    test(
        "Rectangle.area after scale",
        "import decorators as d; r = d.Rectangle(3, 4); r.scale(2); print(r.area)",
        "48",
    )




def test_classes():
    """Test unified classes module (all class features in one hierarchy)."""
    print("\n[TEST] Testing classes module (unified class hierarchy)...")

    # -- Location (@dataclass, basic fields) --
    test(
        "Location creation",
        "import classes as c; loc = c.Location(10, 20); print(loc.x, loc.y)",
        "10 20",
    )

    # -- Entity (base class, manual __init__, str/int/list fields) --
    test(
        "Entity creation",
        "import classes as c; e = c.Entity('sensor1', 42); print(e.name)",
        "sensor1",
    )

    # @property (read-only)
    test(
        "Entity.id property",
        "import classes as c; e = c.Entity('s', 7); print(e.id)",
        "7",
    )

    # @staticmethod
    test(
        "Entity.validate_name staticmethod",
        "import classes as c; print(c.Entity.validate_name('hello'))",
        "True",
    )

    test(
        "Entity.validate_name empty",
        "import classes as c; print(c.Entity.validate_name(''))",
        "False",
    )

    # Container field (list): add_tag, tag_count, has_tag
    test(
        "Entity.add_tag + tag_count",
        "import classes as c; e = c.Entity('s', 1); e.add_tag(10); e.add_tag(20); print(e.tag_count())",
        "2",
    )

    test(
        "Entity.has_tag found",
        "import classes as c; e = c.Entity('s', 1); e.add_tag(10); print(e.has_tag(10))",
        "True",
    )

    test(
        "Entity.has_tag not found",
        "import classes as c; e = c.Entity('s', 1); e.add_tag(10); print(e.has_tag(99))",
        "False",
    )

    test(
        "Entity.describe",
        "import classes as c; e = c.Entity('myname', 1); print(e.describe())",
        "myname",
    )

    # -- Sensor(Entity): inheritance, super().__init__, float, dict, @property rw --
    test(
        "Sensor inherits Entity.name",
        "import classes as c; s = c.Sensor('temp', 5, c.Location(1, 2)); print(s.name)",
        "temp",
    )

    test(
        "Sensor inherits Entity.id property",
        "import classes as c; s = c.Sensor('t', 5, c.Location(0, 0)); print(s.id)",
        "5",
    )

    # @property getter+setter on child
    test(
        "Sensor.value property getter",
        "import classes as c; s = c.Sensor('t', 1, c.Location(0, 0)); print(s.value)",
        "0.0",
    )

    test(
        "Sensor.value property setter",
        "import classes as c; s = c.Sensor('t', 1, c.Location(0, 0)); s.value = 3.14; print(s.value)",
        "3.14",
    )

    # @classmethod
    test(
        "Sensor.create classmethod",
        "import classes as c; print(c.Sensor.create('x') is c.Sensor)",
        "True",
    )

    # Dict field (readings)
    test(
        "Sensor.record + reading_count",
        "import classes as c; s = c.Sensor('t', 1, c.Location(0, 0)); s.record(100, 25.5); s.record(200, 26.0); print(s.reading_count())",
        "2",
    )

    test(
        "Sensor.get_reading",
        "import classes as c; s = c.Sensor('t', 1, c.Location(0, 0)); s.record(100, 25.5); print(s.get_reading(100))",
        "25.5",
    )

    # Chained attribute access (sensor.location.x)
    test(
        "Sensor.get_location_x chained attr",
        "import classes as c; s = c.Sensor('t', 1, c.Location(30, 40)); print(s.get_location_x())",
        "30",
    )

    test(
        "Sensor.get_location_y chained attr",
        "import classes as c; s = c.Sensor('t', 1, c.Location(30, 40)); print(s.get_location_y())",
        "40",
    )

    # Method override + super().describe()
    test(
        "Sensor.describe override calls super",
        "import classes as c; s = c.Sensor('mysensor', 1, c.Location(0, 0)); print(s.describe())",
        "mysensor",
    )

    # Inherited container: tags from Entity still work on Sensor
    test(
        "Sensor inherits Entity.add_tag",
        "import classes as c; s = c.Sensor('t', 1, c.Location(0, 0)); s.add_tag(42); print(s.has_tag(42))",
        "True",
    )

    # -- SmartSensor(Sensor): 3-level, augmented assign, bool, cross-level --
    test(
        "SmartSensor 3-level inheritance name",
        "import classes as c; ss = c.SmartSensor('smart', 10, c.Location(5, 5), 50.0); print(ss.name)",
        "smart",
    )

    test(
        "SmartSensor inherits id property",
        "import classes as c; ss = c.SmartSensor('s', 10, c.Location(0, 0), 50.0); print(ss.id)",
        "10",
    )

    test(
        "SmartSensor.check_value below threshold",
        "import classes as c; ss = c.SmartSensor('s', 1, c.Location(0, 0), 50.0); ss.value = 30.0; print(ss.check_value())",
        "False",
    )

    test(
        "SmartSensor.check_value above threshold (augmented +=)",
        "import classes as c; ss = c.SmartSensor('s', 1, c.Location(0, 0), 50.0); ss.value = 60.0; print(ss.check_value())",
        "True",
    )

    test(
        "SmartSensor.alert_count after multiple checks",
        "import classes as c; ss = c.SmartSensor('s', 1, c.Location(0, 0), 50.0); ss.value = 60.0; ss.check_value(); ss.check_value(); print(ss.get_alert_count())",
        "2",
    )

    test(
        "SmartSensor.describe chains 3-level super",
        "import classes as c; ss = c.SmartSensor('deep', 1, c.Location(0, 0), 50.0); print(ss.describe())",
        "deep",
    )

    test(
        "SmartSensor.get_total_score cross-level fields",
        "import classes as c; ss = c.SmartSensor('s', 10, c.Location(0, 0), 50.0); ss.value = 60.0; ss.check_value(); print(ss.get_total_score())",
        "11",
    )

    # Staticmethod via instance
    test(
        "Entity.validate_name via Sensor instance",
        "import classes as c; s = c.Sensor('t', 1, c.Location(0, 0)); print(s.validate_name('ok'))",
        "True",
    )

    # -- Free functions taking class params --
    test(
        "distance_between two Locations",
        "import classes as c; print(c.distance_between(c.Location(0, 0), c.Location(3, 4)))",
        "25",
    )

    test(
        "sensor_summary cross-inheritance",
        "import classes as c; s = c.Sensor('t', 10, c.Location(0, 0)); s.record(1, 1.0); s.record(2, 2.0); print(c.sensor_summary(s))",
        "12",
    )


def test_math_ops():
    """Test math_ops module (runtime imports of built-in modules)."""
    print("\n[TEST] Testing math_ops module (runtime imports)...")

    # distance(x1, y1, x2, y2) uses math.sqrt
    test(
        "distance(0, 0, 3, 4)",
        "import math_ops; print(math_ops.distance(0, 0, 3, 4))",
        "5.0",
    )

    test(
        "distance(1, 1, 1, 1)",
        "import math_ops; print(math_ops.distance(1, 1, 1, 1))",
        "0.0",
    )

    # circle_area(radius) uses math.pi
    test(
        "circle_area(1)",
        "import math_ops; r = math_ops.circle_area(1); print(r > 3.14 and r < 3.15)",
        "True",
    )

    test(
        "circle_area(0)",
        "import math_ops; print(math_ops.circle_area(0))",
        "0.0",
    )

    # deg_to_rad(degrees) uses math.pi
    test(
        "deg_to_rad(180)",
        "import math_ops; r = math_ops.deg_to_rad(180); print(r > 3.14 and r < 3.15)",
        "True",
    )

    test(
        "deg_to_rad(0)",
        "import math_ops; print(math_ops.deg_to_rad(0))",
        "0.0",
    )

    # trig_sum(angle) uses math.sin + math.cos
    test(
        "trig_sum(0)",
        "import math_ops; print(math_ops.trig_sum(0))",
        "1.0",
    )

    # timed_sum(n) - basic integer sum (no imports, but in same module)
    test(
        "timed_sum(10)",
        "import math_ops; print(math_ops.timed_sum(10))",
        "45",
    )

def test_cross_import():
    """Test cross_import module (importing other compiled modules at runtime)."""
    print("\n[TEST] Testing cross_import module (cross-module imports)...")

    test(
        "double_factorial(5)",
        "import cross_import; print(cross_import.double_factorial(5))",
        "240",
    )

    test(
        "fib_plus(10, 100)",
        "import cross_import; print(cross_import.fib_plus(10, 100))",
        "155",
    )

    test(
        "combo_add(3, 4)",
        "import cross_import; print(cross_import.combo_add(3, 4))",
        "7",
    )

    test(
        "native_distance(0, 0, 3, 4)",
        "import cross_import; print(cross_import.native_distance(0, 0, 3, 4))",
        "5.0",
    )

    # sum_and_factorial uses both math_ops.timed_sum and factorial.factorial
    # timed_sum(5) = 0+1+2+3+4 = 10, factorial(5) = 120, result = 1200
    test(
        "sum_and_factorial(5)",
        "import cross_import; print(cross_import.sum_and_factorial(5))",
        "1200",
    )

def test_sensor_lib():
    """Test sensor_lib package (nested package compilation)."""
    print("\n[TEST] Testing sensor_lib package (package compilation)...")

    # Top-level submodule: math_helpers
    test(
        "math_helpers.distance(0,0,3,4)",
        "import sensor_lib; print(sensor_lib.math_helpers.distance(0, 0, 3, 4))",
        "25",
    )

    test(
        "math_helpers.midpoint(10,20)",
        "import sensor_lib; print(sensor_lib.math_helpers.midpoint(10, 20))",
        "15",
    )

    test(
        "math_helpers.scale(5,3)",
        "import sensor_lib; print(sensor_lib.math_helpers.scale(5, 3))",
        "15",
    )

    # Top-level submodule: filters
    test(
        "filters.clamp(150,0,100)",
        "import sensor_lib; print(sensor_lib.filters.clamp(150, 0, 100))",
        "100",
    )

    test(
        "filters.clamp(-5,0,100)",
        "import sensor_lib; print(sensor_lib.filters.clamp(-5, 0, 100))",
        "0",
    )

    test(
        "filters.clamp(50,0,100)",
        "import sensor_lib; print(sensor_lib.filters.clamp(50, 0, 100))",
        "50",
    )

    test(
        "filters.moving_avg(100,200,50)",
        "import sensor_lib; print(sensor_lib.filters.moving_avg(100, 200, 50))",
        "150",
    )

    test(
        "filters.threshold(75,50)",
        "import sensor_lib; print(sensor_lib.filters.threshold(75, 50))",
        "True",
    )

    test(
        "filters.threshold(25,50)",
        "import sensor_lib; print(sensor_lib.filters.threshold(25, 50))",
        "False",
    )

    # Top-level submodule: converters
    test(
        "converters.celsius_to_fahrenheit(100)",
        "import sensor_lib; print(sensor_lib.converters.celsius_to_fahrenheit(100))",
        "212",
    )

    test(
        "converters.fahrenheit_to_celsius(212)",
        "import sensor_lib; print(sensor_lib.converters.fahrenheit_to_celsius(212))",
        "100",
    )

    test(
        "converters.mm_to_inches(254)",
        "import sensor_lib; print(sensor_lib.converters.mm_to_inches(254))",
        "100",
    )

    # Nested sub-package: processing
    test(
        "processing.version()",
        "import sensor_lib; print(sensor_lib.processing.version())",
        "1",
    )

    # Nested sub-package leaf: processing.smoothing
    test(
        "processing.smoothing.simple_avg(10,20)",
        "import sensor_lib; print(sensor_lib.processing.smoothing.simple_avg(10, 20))",
        "15",
    )

    test(
        "processing.smoothing.exponential_avg(100,200,50)",
        "import sensor_lib; print(sensor_lib.processing.smoothing.exponential_avg(100, 200, 50))",
        "150",
    )

    # Nested sub-package leaf: processing.calibration
    test(
        "processing.calibration.apply_offset(100,5)",
        "import sensor_lib; print(sensor_lib.processing.calibration.apply_offset(100, 5))",
        "105",
    )

    test(
        "processing.calibration.apply_scale(100,3,2)",
        "import sensor_lib; print(sensor_lib.processing.calibration.apply_scale(100, 3, 2))",
        "150",
    )

def test_private_methods():
    """Test private_methods module (private methods, @final class, Final attrs)."""
    print("\n[TEST] Testing private_methods module (optimization tiers)...")

    # Tier 1: Private method via public wrapper
    test(
        "Calculator(10).compute(5)",
        "import private_methods as pm; c = pm.Calculator(10); print(c.compute(5))",
        "35",
    )

    test(
        "Calculator(0).compute(3)",
        "import private_methods as pm; c = pm.Calculator(0); print(c.compute(3))",
        "9",
    )

    # Tier 2: @final class -- all methods devirtualized
    test(
        "FastCounter increment",
        "import private_methods as pm; fc = pm.FastCounter(3); fc.increment(); fc.increment(); print(fc.get())",
        "6",
    )

    test(
        "FastCounter reset",
        "import private_methods as pm; fc = pm.FastCounter(3); fc.increment(); fc.reset(); print(fc.get())",
        "0",
    )

    test(
        "FastCounter increment returns count",
        "import private_methods as pm; fc = pm.FastCounter(5); print(fc.increment())",
        "5",
    )

    # Tier 3: Final attribute constant folding
    test(
        "Config(7).scaled_value()",
        "import private_methods as pm; cfg = pm.Config(7); print(cfg.scaled_value())",
        "14",
    )

    test(
        "Config.is_within_limit(999) True",
        "import private_methods as pm; cfg = pm.Config(1); print(cfg.is_within_limit(999))",
        "True",
    )

    test(
        "Config.is_within_limit(1000) False",
        "import private_methods as pm; cfg = pm.Config(1); print(cfg.is_within_limit(1000))",
        "False",
    )

    # Benchmark class: public vs private produce same result
    test(
        "Benchmark.run_public(10)",
        "import private_methods as pm; b = pm.Benchmark(5); print(b.run_public(10))",
        "95",
    )

    test(
        "Benchmark.run_private(10)",
        "import private_methods as pm; b = pm.Benchmark(5); print(b.run_private(10))",
        "95",
    )

    # Verify public and private produce identical results for larger input
    test(
        "Benchmark public==private (100)",
        "import private_methods as pm; b = pm.Benchmark(3); print(b.run_public(100) == b.run_private(100))",
        "True",
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
    test_builtins_demo()
    test_default_args()
    test_star_args()
    test_class_param()
    test_chained_attr()
    test_container_attrs()
    test_string_operations()
    test_itertools_builtins()
    test_exception_handling()
    test_super_calls()
    test_decorators()
    test_classes()
    test_math_ops()
    test_cross_import()
    test_sensor_lib()
    test_private_methods()
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
    # Cycle RGB LED to visually confirm the board is responding
    led_cycle_colors()
    success = run_all_tests()
    # Final LED status: green = all pass, red = failures
    if success:
        led_rgb(0, 255, 0)  # Green = all tests passed
    else:
        led_rgb(255, 0, 0)  # Red = some tests failed
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
