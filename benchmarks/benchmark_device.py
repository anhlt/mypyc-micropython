# Benchmark: mypyc-compiled C modules vs vanilla MicroPython
# Run this on ESP32 device with mpremote

import time

# ============================================================
# PURE PYTHON IMPLEMENTATIONS (interpreted by MicroPython VM)
# ============================================================

def py_sum_range(n: int) -> int:
    """Sum 0 to n-1 using for loop"""
    total: int = 0
    for i in range(n):
        total += i
    return total


def py_build_squares(n: int) -> list:
    """Build list of squares [0, 1, 4, 9, ...]"""
    result: list = []
    for i in range(n):
        result.append(i * i)
    return result


def py_matrix_sum(rows: int, cols: int) -> int:
    """Nested loop sum"""
    total: int = 0
    for i in range(rows):
        for j in range(cols):
            total += i + j
    return total


def py_reverse_sum(n: int) -> int:
    """Sum n down to 1"""
    total: int = 0
    for i in range(n, 0, -1):
        total += i
    return total


def py_factorial(n: int) -> int:
    """Recursive factorial"""
    if n <= 1:
        return 1
    return n * py_factorial(n - 1)


def py_fib(n: int) -> int:
    """Recursive fibonacci"""
    if n <= 1:
        return n
    return py_fib(n - 2) + py_fib(n - 1)


# ============================================================
# BENCHMARK RUNNER
# ============================================================

def benchmark(name, func, args, iterations=10):
    """Run benchmark and return average time in microseconds"""
    # Warmup
    for _ in range(3):
        func(*args)
    
    # Timed runs
    times = []
    for _ in range(iterations):
        start = time.ticks_us()
        result = func(*args)
        end = time.ticks_us()
        times.append(time.ticks_diff(end, start))
    
    avg_us = sum(times) // len(times)
    return avg_us, result


def run_benchmarks():
    print("=" * 60)
    print("MYPYC vs VANILLA MICROPYTHON BENCHMARK")
    print("=" * 60)
    print()
    
    # Try importing native modules
    try:
        import list_operations as native_list
        has_list_ops = True
        print("[OK] list_operations (native C module) loaded")
    except ImportError:
        has_list_ops = False
        print("[SKIP] list_operations not available")
    
    try:
        import factorial as native_fact
        has_factorial = True
        print("[OK] factorial (native C module) loaded")
    except ImportError:
        has_factorial = False
        print("[SKIP] factorial not available")
    
    print()
    print("-" * 60)
    print(f"{'Benchmark':<25} {'Native(us)':<12} {'Python(us)':<12} {'Speedup':<10}")
    print("-" * 60)
    
    results = []
    
    # Benchmark 1: sum_range
    if has_list_ops:
        n = 1000
        native_us, native_res = benchmark("sum_range", native_list.sum_range, (n,))
        python_us, python_res = benchmark("sum_range", py_sum_range, (n,))
        speedup = python_us / native_us if native_us > 0 else 0
        print(f"{'sum_range(1000)':<25} {native_us:<12} {python_us:<12} {speedup:.1f}x")
        results.append(("sum_range(1000)", native_us, python_us, speedup))
    
    # Benchmark 2: build_squares (list operations)
    if has_list_ops:
        n = 500
        native_us, native_res = benchmark("build_squares", native_list.build_squares, (n,))
        python_us, python_res = benchmark("build_squares", py_build_squares, (n,))
        speedup = python_us / native_us if native_us > 0 else 0
        print(f"{'build_squares(500)':<25} {native_us:<12} {python_us:<12} {speedup:.1f}x")
        results.append(("build_squares(500)", native_us, python_us, speedup))
    
    # Benchmark 3: matrix_sum (nested loops)
    if has_list_ops:
        rows, cols = 50, 50
        native_us, native_res = benchmark("matrix_sum", native_list.matrix_sum, (rows, cols))
        python_us, python_res = benchmark("matrix_sum", py_matrix_sum, (rows, cols))
        speedup = python_us / native_us if native_us > 0 else 0
        print(f"{'matrix_sum(50,50)':<25} {native_us:<12} {python_us:<12} {speedup:.1f}x")
        results.append(("matrix_sum(50,50)", native_us, python_us, speedup))
    
    # Benchmark 4: reverse_sum
    if has_list_ops:
        n = 1000
        native_us, native_res = benchmark("reverse_sum", native_list.reverse_sum, (n,))
        python_us, python_res = benchmark("reverse_sum", py_reverse_sum, (n,))
        speedup = python_us / native_us if native_us > 0 else 0
        print(f"{'reverse_sum(1000)':<25} {native_us:<12} {python_us:<12} {speedup:.1f}x")
        results.append(("reverse_sum(1000)", native_us, python_us, speedup))
    
    # Benchmark 5: factorial (recursion)
    if has_factorial:
        n = 12
        native_us, native_res = benchmark("factorial", native_fact.factorial, (n,), iterations=100)
        python_us, python_res = benchmark("factorial", py_factorial, (n,), iterations=100)
        speedup = python_us / native_us if native_us > 0 else 0
        print(f"{'factorial(12)':<25} {native_us:<12} {python_us:<12} {speedup:.1f}x")
        results.append(("factorial(12)", native_us, python_us, speedup))
    
    # Benchmark 6: fibonacci (heavy recursion)
    if has_factorial:
        n = 20
        native_us, native_res = benchmark("fib", native_fact.fib, (n,), iterations=5)
        python_us, python_res = benchmark("fib", py_fib, (n,), iterations=5)
        speedup = python_us / native_us if native_us > 0 else 0
        print(f"{'fib(20)':<25} {native_us:<12} {python_us:<12} {speedup:.1f}x")
        results.append(("fib(20)", native_us, python_us, speedup))
    
    print("-" * 60)
    
    # Summary
    if results:
        avg_speedup = sum(r[3] for r in results) / len(results)
        print()
        print(f"AVERAGE SPEEDUP: {avg_speedup:.1f}x")
        print()
        print("Conclusion:")
        if avg_speedup >= 5:
            print(f"  mypyc compilation provides SIGNIFICANT performance gain ({avg_speedup:.1f}x faster)")
        elif avg_speedup >= 2:
            print(f"  mypyc compilation provides GOOD performance gain ({avg_speedup:.1f}x faster)")
        else:
            print(f"  mypyc compilation provides MODERATE performance gain ({avg_speedup:.1f}x faster)")
    else:
        print("No native modules available for benchmarking!")
        print("Build firmware with: make build BOARD=ESP32_GENERIC_C3")


if __name__ == "__main__":
    run_benchmarks()
