#!/usr/bin/env python3
"""
Benchmark runner comparing native compiled modules vs vanilla MicroPython.

Usage:
    python run_benchmarks.py --port /dev/cu.usbmodem2101

This script runs identical algorithms as both:
1. Native C modules (compiled with mypyc-micropython)
2. Pure Python executed by MicroPython interpreter

Reports timing comparison and speedup factor.
"""

import argparse
import subprocess
import sys

DEFAULT_PORT = "/dev/ttyACM0"
PORT = DEFAULT_PORT

# Benchmark definitions: (name, native_code, python_code, iterations)
BENCHMARKS = [
    # Factorial - recursive function
    (
        "factorial(12) x1000",
        """
import factorial
import time
start = time.ticks_us()
for _ in range(1000):
    factorial.factorial(12)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
start = time.ticks_us()
for _ in range(1000):
    factorial(12)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # Fibonacci - recursive with multiple calls
    (
        "fib(20) x100",
        """
import factorial
import time
start = time.ticks_us()
for _ in range(100):
    factorial.fib(20)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def fib(n):
    if n <= 1:
        return n
    return fib(n - 2) + fib(n - 1)
start = time.ticks_us()
for _ in range(100):
    fib(20)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # Prime check - loop with arithmetic
    (
        "is_prime(9973) x1000",
        """
import algorithms
import time
start = time.ticks_us()
for _ in range(1000):
    algorithms.is_prime(9973)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True
start = time.ticks_us()
for _ in range(1000):
    is_prime(9973)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # GCD - iterative algorithm
    (
        "gcd(46368, 28657) x10000",
        """
import algorithms
import time
start = time.ticks_us()
for _ in range(10000):
    algorithms.gcd(46368, 28657)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a
start = time.ticks_us()
for _ in range(10000):
    gcd(46368, 28657)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # List sum - iteration over container
    (
        "sum_list([1..100]) x1000",
        """
import list_operations
import time
lst = list(range(100))
start = time.ticks_us()
for _ in range(1000):
    list_operations.sum_list(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def sum_list(lst):
    total = 0
    for x in lst:
        total += x
    return total
lst = list(range(100))
start = time.ticks_us()
for _ in range(1000):
    sum_list(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # Tuple operations - creation and unpacking
    (
        "tuple ops x10000",
        """
import tuple_operations as t
import time
start = time.ticks_us()
for _ in range(10000):
    p = t.make_point()
    t.unpack_pair(p)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def make_point():
    return (10, 20)
def unpack_pair(t):
    a, b = t
    return a + b
start = time.ticks_us()
for _ in range(10000):
    p = make_point()
    unpack_pair(p)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # Set operations - add and membership
    (
        "set build+check x1000",
        """
import set_operations as s
import time
start = time.ticks_us()
for _ in range(1000):
    s.build_set_incremental(50)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def build_set_incremental(n):
    s = set()
    for i in range(n):
        s.add(i % 10)
    return len(s)
start = time.ticks_us()
for _ in range(1000):
    build_set_incremental(50)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # Bitwise operations - bit manipulation
    (
        "count_ones(0x7FFFFFFF) x10000",
        """
import bitwise
import time
start = time.ticks_us()
for _ in range(10000):
    bitwise.count_ones(0x7FFFFFFF)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def count_ones(n):
    count = 0
    while n:
        count += n & 1
        n >>= 1
    return count
start = time.ticks_us()
for _ in range(10000):
    count_ones(0x7FFFFFFF)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
]


def run_on_device(code: str, timeout: int = 60) -> tuple[bool, str]:
    """Execute Python code on device via mpremote."""
    try:
        result = subprocess.run(
            ["mpremote", "connect", PORT, "exec", code],
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


def run_benchmark(name: str, native_code: str, python_code: str) -> tuple[int, int] | None:
    """Returns (native_us, python_us) or None on failure."""
    success, output = run_on_device(native_code)
    if not success:
        print(f"  Native FAILED: {output}")
        return None
    try:
        native_us = int(output.split("\n")[-1])
    except (ValueError, IndexError):
        print(f"  Native parse error: {output}")
        return None

    success, output = run_on_device(python_code)
    if not success:
        print(f"  Python FAILED: {output}")
        return None
    try:
        python_us = int(output.split("\n")[-1])
    except (ValueError, IndexError):
        print(f"  Python parse error: {output}")
        return None

    return native_us, python_us


def main():
    global PORT

    parser = argparse.ArgumentParser(description="Benchmark native modules vs vanilla MicroPython")
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help=f"Serial port for ESP32 device (default: {DEFAULT_PORT})",
    )
    args = parser.parse_args()
    PORT = args.port

    print("=" * 70)
    print("mypyc-micropython Benchmark: Native C vs Vanilla MicroPython")
    print("=" * 70)
    print(f"Device port: {PORT}")
    print()

    # Check device connection
    print("Checking device connection...")
    success, output = run_on_device("print('ready')")
    if not success:
        print(f"FAILED: Cannot connect to device: {output}")
        sys.exit(1)
    print("Device connected.\n")

    results = []
    total_native = 0
    total_python = 0

    print(f"{'Benchmark':<30} {'Native':>12} {'Python':>12} {'Speedup':>10}")
    print("-" * 70)

    for name, native_code, python_code in BENCHMARKS:
        result = run_benchmark(name, native_code, python_code)
        if result:
            native_us, python_us = result
            speedup = python_us / native_us if native_us > 0 else 0
            results.append((name, native_us, python_us, speedup))
            total_native += native_us
            total_python += python_us
            print(f"{name:<30} {native_us:>10}us {python_us:>10}us {speedup:>9.2f}x")
        else:
            print(f"{name:<30} {'FAILED':>12} {'FAILED':>12} {'N/A':>10}")

    print("-" * 70)

    if results:
        avg_speedup = sum(r[3] for r in results) / len(results)
        overall_speedup = total_python / total_native if total_native > 0 else 0
        print(f"{'TOTAL':<30} {total_native:>10}us {total_python:>10}us {overall_speedup:>9.2f}x")
        print()
        print(f"Average speedup: {avg_speedup:.2f}x")
        print(f"Overall speedup: {overall_speedup:.2f}x")

        # Performance summary
        print()
        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        if avg_speedup >= 5:
            print(f"Excellent! Native code is {avg_speedup:.1f}x faster on average.")
        elif avg_speedup >= 2:
            print(f"Good. Native code is {avg_speedup:.1f}x faster on average.")
        elif avg_speedup >= 1:
            print(f"Native code is {avg_speedup:.1f}x faster on average.")
        else:
            print(f"Warning: Native code is slower ({avg_speedup:.1f}x). Check implementation.")

    print("=" * 70)
    return 0 if results else 1


if __name__ == "__main__":
    sys.exit(main())
