"""
MicroPython benchmark runner - runs directly on device.

Usage:
    mpremote connect /dev/cu.usbmodem2101 run run_benchmarks.py
    # or via Makefile:
    make benchmark PORT=/dev/cu.usbmodem2101

Compares native compiled modules vs vanilla MicroPython interpreter.
"""

import gc
import time

# Results tracking
_results = []
_total_native = 0
_total_python = 0


def b(name, native_fn, python_fn, iterations=100):
    """Run a single benchmark comparing native vs python implementation."""
    global _total_native, _total_python
    gc.collect()

    # Time native implementation
    start = time.ticks_us()
    for _ in range(iterations):
        native_fn()
    native_us = time.ticks_diff(time.ticks_us(), start)

    # Time python implementation
    gc.collect()
    start = time.ticks_us()
    for _ in range(iterations):
        python_fn()
    python_us = time.ticks_diff(time.ticks_us(), start)

    # Calculate speedup
    speedup = python_us / native_us if native_us > 0 else 0

    # Track totals
    _total_native += native_us
    _total_python += python_us
    _results.append((name, native_us, python_us, speedup))

    # Print result
    print(f"{name:<40} {native_us:>10}us {python_us:>10}us {speedup:>8.2f}x")


def print_header():
    print("=" * 70)
    print("mypyc-micropython Benchmark: Native C vs Vanilla MicroPython")
    print("=" * 70)
    print()
    print(f"{'Benchmark':<40} {'Native':>12} {'Python':>12} {'Speedup':>10}")
    print("-" * 70)


def print_summary():
    print("-" * 70)
    if _results:
        avg_speedup = sum(r[3] for r in _results) / len(_results)
        overall_speedup = _total_python / _total_native if _total_native > 0 else 0
        print(f"{'TOTAL':<40} {_total_native:>10}us {_total_python:>10}us {overall_speedup:>8.2f}x")
        print()
        print(f"Benchmarks run: {len(_results)}")
        print(f"Average speedup: {avg_speedup:.2f}x")
        print(f"Overall speedup: {overall_speedup:.2f}x")
        print()
        if avg_speedup >= 5:
            print(f"Excellent! Native code is {avg_speedup:.1f}x faster on average.")
        elif avg_speedup >= 2:
            print(f"Good. Native code is {avg_speedup:.1f}x faster on average.")
        elif avg_speedup >= 1:
            print(f"Native code is {avg_speedup:.1f}x faster on average.")
        else:
            print(f"Warning: Native code is slower ({avg_speedup:.1f}x). Check implementation.")
    print("=" * 70)


# =============================================================================
# BENCHMARKS - List Operations
# =============================================================================


def bench_list_operations():
    import list_operations

    # sum_range
    def native_sum_range():
        list_operations.sum_range(1000)

    def python_sum_range():
        total = 0
        for i in range(1000):
            total += i
        return total

    b("sum_range(1000) x100", native_sum_range, python_sum_range, 100)

    # build_squares
    def native_build_squares():
        list_operations.build_squares(500)

    def python_build_squares():
        result = []
        for i in range(500):
            result.append(i * i)
        return result

    b("build_squares(500) x100", native_build_squares, python_build_squares, 100)

    # matrix_sum
    def native_matrix_sum():
        list_operations.matrix_sum(50, 50)

    def python_matrix_sum():
        total = 0
        for i in range(50):
            for j in range(50):
                total += i + j
        return total

    b("matrix_sum(50,50) x100", native_matrix_sum, python_matrix_sum, 100)

    # reverse_sum
    def native_reverse_sum():
        list_operations.reverse_sum(1000)

    def python_reverse_sum():
        total = 0
        for i in range(1000, 0, -1):
            total += i
        return total

    b("reverse_sum(1000) x100", native_reverse_sum, python_reverse_sum, 100)

    # sum_list with iteration
    lst = list(range(100))

    def native_sum_list():
        list_operations.sum_list(lst)

    def python_sum_list():
        total = 0
        for x in lst:
            total += x
        return total

    b("sum_list([1..100]) x1000", native_sum_list, python_sum_list, 1000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Factorial / Fibonacci
# =============================================================================


def bench_factorial():
    import factorial

    def native_factorial():
        factorial.factorial(12)

    def python_factorial(n=12):
        if n <= 1:
            return 1
        return n * python_factorial(n - 1)

    b("factorial(12) x1000", native_factorial, lambda: python_factorial(12), 1000)

    def native_fib():
        factorial.fib(20)

    def python_fib(n=20):
        if n <= 1:
            return n
        return python_fib(n - 2) + python_fib(n - 1)

    b("fib(20) x100", native_fib, lambda: python_fib(20), 100)
    gc.collect()


# =============================================================================
# BENCHMARKS - Algorithms
# =============================================================================


def bench_algorithms():
    import algorithms

    # is_prime
    def native_is_prime():
        algorithms.is_prime(9973)

    def python_is_prime():
        n = 9973
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

    b("is_prime(9973) x1000", native_is_prime, python_is_prime, 1000)

    # gcd
    def native_gcd():
        algorithms.gcd(46368, 28657)

    def python_gcd():
        a, b = 46368, 28657
        while b:
            a, b = b, a % b
        return a

    b("gcd(46368, 28657) x10000", native_gcd, python_gcd, 10000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Tuple Operations
# =============================================================================


def bench_tuple_operations():
    import tuple_operations as t

    # make_point + unpack
    def native_tuple_ops():
        p = t.make_point()
        t.unpack_pair(p)

    def python_tuple_ops():
        p = (10, 20)
        a, b = p
        return a + b

    b("tuple ops x10000", native_tuple_ops, python_tuple_ops, 10000)

    # rtuple ops
    def native_rtuple_ops():
        t.rtuple_sum_fields()
        t.rtuple_distance_squared(0, 0, 3, 4)

    def python_rtuple_ops():
        point = (15, 25)
        _ = point[0] + point[1]
        p1 = (0, 0)
        p2 = (3, 4)
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return dx * dx + dy * dy

    b("rtuple ops x10000", native_rtuple_ops, python_rtuple_ops, 10000)

    # rtuple internal benchmark
    def native_rtuple_internal():
        t.rtuple_benchmark_internal(1000)

    def python_rtuple_internal():
        total = 0
        i = 0
        while i < 1000:
            point = (i, i * 2)
            total += point[0] + point[1]
            i += 1
        return total

    b("rtuple internal x100", native_rtuple_internal, python_rtuple_internal, 100)

    # list[tuple] sum
    points = [(i, i * 2, i * 3) for i in range(100)]

    def native_list_tuple():
        t.sum_points_list(points, 100)

    def python_list_tuple():
        total = 0
        i = 0
        while i < 100:
            p = points[i]
            total = total + p[0] + p[1] + p[2]
            i = i + 1
        return total

    b("list[tuple] x500", native_list_tuple, python_list_tuple, 500)
    gc.collect()


# =============================================================================
# BENCHMARKS - Set Operations
# =============================================================================


def bench_set_operations():
    import set_operations as s

    def native_set_build():
        s.build_set_incremental(50)

    def python_set_build():
        st = set()
        for i in range(50):
            st.add(i % 10)
        return len(st)

    b("set build+check x1000", native_set_build, python_set_build, 1000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Point Class
# =============================================================================


def bench_point_class():
    import point

    def native_point():
        p = point.Point(3, 4)
        p.distance_squared()

    class PyPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

        def distance_squared(self):
            return self.x * self.x + self.y * self.y

    def python_point():
        p = PyPoint(3, 4)
        p.distance_squared()

    b("Point class x10000", native_point, python_point, 10000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Bitwise Operations
# =============================================================================


def bench_bitwise():
    import bitwise

    def native_count_ones():
        bitwise.count_ones(0x7FFFFFFF)

    def python_count_ones():
        n = 0x7FFFFFFF
        count = 0
        while n:
            count += n & 1
            n >>= 1
        return count

    b("count_ones(0x7FFFFFFF) x10000", native_count_ones, python_count_ones, 10000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Builtins (sum, min, max, abs)
# =============================================================================


def bench_builtins():
    import builtins_demo

    lst = list(range(1000))

    # sum_list
    def native_sum_list():
        builtins_demo.sum_list(lst)

    def python_sum_list():
        return sum(lst)

    b("sum_builtin(1000) x1000", native_sum_list, python_sum_list, 1000)

    # sum_int_list (typed)
    def native_sum_int_list():
        builtins_demo.sum_int_list(lst)

    b("sum_typed_list(1000) x1000", native_sum_int_list, python_sum_list, 1000)

    # clamp_list
    values = list(range(-100, 100))

    def native_clamp_list():
        builtins_demo.clamp_list(values, 0, 50)

    def python_clamp_list():
        result = []
        for v in values:
            clamped = max(0, min(v, 50))
            result.append(clamped)
        return result

    b("clamp_list(200) x1000", native_clamp_list, python_clamp_list, 1000)

    # find_extremes_sum
    lst2 = list(range(1, 1001))

    def native_find_extremes():
        builtins_demo.find_extremes_sum(lst2)

    def python_find_extremes():
        return min(lst2) + max(lst2)

    b("find_extremes(1000) x1000", native_find_extremes, python_find_extremes, 1000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Star Args
# =============================================================================


def bench_star_args():
    import star_args

    args100 = tuple(range(100))
    args50 = tuple(range(50))

    def native_sum_all():
        star_args.sum_all(*args100)

    def python_sum_all(*numbers):
        total = 0
        for x in numbers:
            total += x
        return total

    b("sum_all(*100) x1000", native_sum_all, lambda: python_sum_all(*args100), 1000)

    def native_max_of_args():
        star_args.max_of_args(*args50)

    def python_max_of_args(*nums):
        result = 0
        first = True
        for n in nums:
            if first:
                result = n
                first = False
            elif n > result:
                result = n
        return result

    b("max_of_args(*50) x1000", native_max_of_args, lambda: python_max_of_args(*args50), 1000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Chained Attribute Access
# =============================================================================


def bench_chained_attr():
    import chained_attr as ca

    tl = ca.Point(0, 0)
    br = ca.Point(100, 50)
    rect = ca.Rectangle(tl, br)

    def native_chained():
        ca.get_width(rect)
        ca.get_height(rect)

    class PyPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    class PyRectangle:
        def __init__(self, tl, br):
            self.top_left = tl
            self.bottom_right = br

    py_tl = PyPoint(0, 0)
    py_br = PyPoint(100, 50)
    py_rect = PyRectangle(py_tl, py_br)

    def python_chained():
        _ = py_rect.bottom_right.x - py_rect.top_left.x
        _ = py_rect.bottom_right.y - py_rect.top_left.y

    b("chained_attr x10000", native_chained, python_chained, 10000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Container Attributes
# =============================================================================


def bench_container_attrs():
    import container_attrs as ca

    inner = ca.Inner([0, 1, 2], {"key": 42})
    outer = ca.Outer(inner, "test")

    def native_container():
        ca.benchmark_inner_list_update(outer, 1)

    class PyInner:
        def __init__(self, items, data):
            self.items = items
            self.data = data

    class PyOuter:
        def __init__(self, inner, name):
            self.inner = inner
            self.name = name

    py_inner = PyInner([0, 1, 2], {"key": 42})
    py_outer = PyOuter(py_inner, "test")

    def python_container():
        i = 0
        while i < 1:
            py_outer.inner.items[0] = i
            i += 1
        return py_outer.inner.items[0]

    b("container_attr x10000", native_container, python_container, 10000)

    # inner_list_update with more iterations
    inner2 = ca.Inner([0, 1, 2], {})
    outer2 = ca.Outer(inner2, "test")

    def native_inner_list():
        ca.benchmark_inner_list_update(outer2, 10000)

    py_inner2 = PyInner([0, 1, 2], {})
    py_outer2 = PyOuter(py_inner2, "test")

    def python_inner_list():
        i = 0
        while i < 10000:
            py_outer2.inner.items[0] = i
            i += 1
        return py_outer2.inner.items[0]

    b("inner_list_update(10000) x10", native_inner_list, python_inner_list, 10)
    gc.collect()


# =============================================================================
# BENCHMARKS - String Operations
# =============================================================================


def bench_string_operations():
    import string_operations as s

    text = "hello world"

    def native_upper():
        s.to_upper(text)

    def python_upper():
        return text.upper()

    b("str.upper() x10000", native_upper, python_upper, 10000)

    text2 = "hello world hello"

    def native_replace():
        s.replace_string(text2, "hello", "hi")

    def python_replace():
        return text2.replace("hello", "hi")

    b("str.replace() x10000", native_replace, python_replace, 10000)

    text3 = "hello world hello world"

    def native_find():
        s.find_substring(text3, "world")

    def python_find():
        return text3.find("world")

    b("str.find() x10000", native_find, python_find, 10000)

    text4 = "a,b,c,d,e,f,g,h,i,j"

    def native_split():
        s.split_on_sep(text4, ",")

    def python_split():
        return text4.split(",")

    b("str.split() x5000", native_split, python_split, 5000)

    items = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

    def native_join():
        s.join_strings(",", items)

    def python_join():
        return ",".join(items)

    b("str.join() x5000", native_join, python_join, 5000)

    text5 = "  hello world  "

    def native_strip():
        s.strip_string(text5)

    def python_strip():
        return text5.strip()

    b("str.strip() x10000", native_strip, python_strip, 10000)

    a, c = "hello", " world"

    def native_concat():
        s.concat_strings(a, c)

    def python_concat():
        return a + c

    b("str concat x10000", native_concat, python_concat, 10000)

    text6 = "  Hello   World  "

    def native_normalize():
        s.normalize_text(text6)

    def python_normalize():
        st = text6.lower()
        st = st.strip()
        while "  " in st:
            st = st.replace("  ", " ")
        return st

    b("normalize_text x1000", native_normalize, python_normalize, 1000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Class Parameter Access
# =============================================================================


def bench_class_param():
    import class_param as cp

    p1 = cp.Point(1, 2)
    p2 = cp.Point(3, 4)
    p3 = cp.Point(5, 6)

    def native_sum_3_points():
        cp.sum_three_points(p1, p2, p3)

    class PyPoint:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    py_p1 = PyPoint(1, 2)
    py_p2 = PyPoint(3, 4)
    py_p3 = PyPoint(5, 6)

    def python_sum_3_points():
        return py_p1.x + py_p1.y + py_p2.x + py_p2.y + py_p3.x + py_p3.y

    b("sum_3_points x1000", native_sum_3_points, python_sum_3_points, 1000)
    gc.collect()


# =============================================================================
# BENCHMARKS - List Comprehension
# =============================================================================


def bench_list_comprehension():
    import list_comprehension as lc

    def native_squares():
        lc.squares(500)

    def python_squares():
        return [x * x for x in range(500)]

    b("listcomp squares(500) x100", native_squares, python_squares, 100)

    def native_evens():
        lc.evens(1000)

    def python_evens():
        return [x for x in range(1000) if x % 2 == 0]

    b("listcomp evens(1000) x100", native_evens, python_evens, 100)
    gc.collect()


# =============================================================================
# BENCHMARKS - Super Calls
# =============================================================================


def bench_super_calls():
    import super_calls

    def native_super_init():
        super_calls.Dog("Rex", 5)

    class PyAnimal:
        def __init__(self, name, sound):
            self.name = name
            self.sound = sound

        def speak(self):
            return self.sound

        def describe(self):
            return self.name

    class PyDog(PyAnimal):
        def __init__(self, name, tricks):
            super().__init__(name, "Woof")
            self.tricks = tricks

        def describe(self):
            base = super().describe()
            return base

        def get_tricks(self):
            return self.tricks

    def python_super_init():
        PyDog("Rex", 5)

    b("super_init x1000", native_super_init, python_super_init, 1000)

    dog = super_calls.Dog("Rex", 5)

    def native_super_method():
        dog.describe()

    py_dog = PyDog("Rex", 5)

    def python_super_method():
        py_dog.describe()

    b("super_method x10000", native_super_method, python_super_method, 10000)

    class PyShowDog(PyDog):
        def __init__(self, name, tricks, awards):
            super().__init__(name, tricks)
            self.awards = awards

        def describe(self):
            base = super().describe()
            return base

        def get_total_score(self):
            return self.tricks + self.awards

    def native_super_3level():
        sd = super_calls.ShowDog("Bella", 10, 3)
        sd.describe()
        sd.get_total_score()

    def python_super_3level():
        sd = PyShowDog("Bella", 10, 3)
        sd.describe()
        sd.get_total_score()

    b("super_3level x1000", native_super_3level, python_super_3level, 1000)
    gc.collect()


# =============================================================================
# BENCHMARKS - Private Methods
# =============================================================================


def bench_private_methods():
    import private_methods as pm

    native_b = pm.Benchmark(5)

    def native_public_work():
        native_b.run_public(100)

    class PyBenchmark:
        def __init__(self, d):
            self.data = d

        def public_work(self, n):
            total = 0
            for i in range(n):
                total += self.data + i
            return total

        def _PyBenchmark__private_work(self, n):
            total = 0
            for i in range(n):
                total += self.data + i
            return total

        def run_public(self, n):
            return self.public_work(n)

        def run_private(self, n):
            return self._PyBenchmark__private_work(n)

    py_b = PyBenchmark(5)

    def python_public_work():
        py_b.run_public(100)

    b("public_work(100) x100", native_public_work, python_public_work, 100)

    def native_private_work():
        native_b.run_private(100)

    def python_private_work():
        py_b.run_private(100)

    b("private_work(100) x100", native_private_work, python_private_work, 100)

    fc = pm.FastCounter(1)

    def native_fast_counter():
        fc.increment()
        fc.reset()

    class PyFastCounter:
        def __init__(self, step):
            self.count = 0
            self.step = step

        def increment(self):
            self.count += self.step
            return self.count

        def reset(self):
            self.count = 0

    py_fc = PyFastCounter(1)

    def python_fast_counter():
        py_fc.increment()
        py_fc.reset()

    b("@final FastCounter x10000", native_fast_counter, python_fast_counter, 10000)
    gc.collect()


# =============================================================================
# MAIN
# =============================================================================


def run_all_benchmarks():
    print_header()

    bench_list_operations()
    bench_factorial()
    bench_algorithms()
    bench_tuple_operations()
    bench_set_operations()
    bench_point_class()
    bench_bitwise()
    bench_builtins()
    bench_star_args()
    bench_chained_attr()
    bench_container_attrs()
    bench_string_operations()
    bench_class_param()
    bench_list_comprehension()
    bench_super_calls()
    bench_private_methods()

    print_summary()


# Run benchmarks when executed
run_all_benchmarks()
