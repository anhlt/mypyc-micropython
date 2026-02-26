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
import os
import subprocess
import sys
import time

DEFAULT_PORT = "/dev/ttyACM0"
PORT = DEFAULT_PORT

# Benchmark definitions: (name, native_code, python_code, iterations)
BENCHMARKS = [
    (
        "sum_range(1000) x100",
        """
import list_operations
import time
start = time.ticks_us()
for _ in range(100):
    list_operations.sum_range(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def sum_range(n):
    total = 0
    for i in range(n):
        total += i
    return total
start = time.ticks_us()
for _ in range(100):
    sum_range(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "build_squares(500) x100",
        """
import list_operations
import time
start = time.ticks_us()
for _ in range(100):
    list_operations.build_squares(500)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def build_squares(n):
    result = []
    for i in range(n):
        result.append(i * i)
    return result
start = time.ticks_us()
for _ in range(100):
    build_squares(500)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "matrix_sum(50,50) x100",
        """
import list_operations
import time
start = time.ticks_us()
for _ in range(100):
    list_operations.matrix_sum(50, 50)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def matrix_sum(rows, cols):
    total = 0
    for i in range(rows):
        for j in range(cols):
            total += i + j
    return total
start = time.ticks_us()
for _ in range(100):
    matrix_sum(50, 50)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "reverse_sum(1000) x100",
        """
import list_operations
import time
start = time.ticks_us()
for _ in range(100):
    list_operations.reverse_sum(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def reverse_sum(n):
    total = 0
    for i in range(n, 0, -1):
        total += i
    return total
start = time.ticks_us()
for _ in range(100):
    reverse_sum(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
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
    (
        "rtuple ops x10000",
        """
import tuple_operations as t
import time
start = time.ticks_us()
for _ in range(10000):
    t.rtuple_sum_fields()
    t.rtuple_distance_squared(0, 0, 3, 4)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def sum_fields():
    point = (15, 25)
    return point[0] + point[1]
def distance_squared(x1, y1, x2, y2):
    p1 = (x1, y1)
    p2 = (x2, y2)
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return dx * dx + dy * dy
start = time.ticks_us()
for _ in range(10000):
    sum_fields()
    distance_squared(0, 0, 3, 4)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "rtuple internal x100",
        """
import tuple_operations as t
import time
start = time.ticks_us()
for _ in range(100):
    t.rtuple_benchmark_internal(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def benchmark_internal(n):
    total = 0
    i = 0
    while i < n:
        point = (i, i * 2)
        total += point[0] + point[1]
        i += 1
    return total
start = time.ticks_us()
for _ in range(100):
    benchmark_internal(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "list[tuple] x500",
        """
import tuple_operations as t
import time
points = [(i, i * 2, i * 3) for i in range(100)]
start = time.ticks_us()
for _ in range(500):
    t.sum_points_list(points, 100)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def sum_points_list(points, count):
    total = 0
    i = 0
    while i < count:
        p = points[i]
        total = total + p[0] + p[1] + p[2]
        i = i + 1
    return total
points = [(i, i * 2, i * 3) for i in range(100)]
start = time.ticks_us()
for _ in range(500):
    sum_points_list(points, 100)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
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
    (
        "Point class x10000",
        """
import point
import time
start = time.ticks_us()
for _ in range(10000):
    p = point.Point(3, 4)
    p.distance_squared()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def distance_squared(self):
        return self.x * self.x + self.y * self.y
start = time.ticks_us()
for _ in range(10000):
    p = Point(3, 4)
    p.distance_squared()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
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
    (
        "sum_builtin(1000) x1000",
        """
import builtins_demo
import time
lst = list(range(1000))
start = time.ticks_us()
for _ in range(1000):
    builtins_demo.sum_list(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
lst = list(range(1000))
start = time.ticks_us()
for _ in range(1000):
    sum(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "sum_typed_list(1000) x1000",
        """
import builtins_demo
import time
lst = list(range(1000))
start = time.ticks_us()
for _ in range(1000):
    builtins_demo.sum_int_list(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
lst = list(range(1000))
start = time.ticks_us()
for _ in range(1000):
    sum(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "clamp_list(200) x1000",
        """
import builtins_demo
import time
values = list(range(-100, 100))
start = time.ticks_us()
for _ in range(1000):
    builtins_demo.clamp_list(values, 0, 50)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def clamp_list(values, low, high):
    result = []
    for v in values:
        clamped = max(low, min(v, high))
        result.append(clamped)
    return result
values = list(range(-100, 100))
start = time.ticks_us()
for _ in range(1000):
    clamp_list(values, 0, 50)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "find_extremes(1000) x1000",
        """
import builtins_demo
import time
lst = list(range(1, 1001))
start = time.ticks_us()
for _ in range(1000):
    builtins_demo.find_extremes_sum(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def find_extremes(lst):
    return min(lst) + max(lst)
lst = list(range(1, 1001))
start = time.ticks_us()
for _ in range(1000):
    find_extremes(lst)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "sum_all(*100) x1000",
        """
import star_args
import time
args = tuple(range(100))
start = time.ticks_us()
for _ in range(1000):
    star_args.sum_all(*args)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def sum_all(*numbers):
    total = 0
    for x in numbers:
        total += x
    return total
args = tuple(range(100))
start = time.ticks_us()
for _ in range(1000):
    sum_all(*args)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "max_of_args(*50) x1000",
        """
import star_args
import time
args = tuple(range(50))
start = time.ticks_us()
for _ in range(1000):
    star_args.max_of_args(*args)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def max_of_args(*nums):
    result = 0
    first = True
    for n in nums:
        if first:
            result = n
            first = False
        elif n > result:
            result = n
    return result
args = tuple(range(50))
start = time.ticks_us()
for _ in range(1000):
    max_of_args(*args)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "chained_attr x10000",
        """
import chained_attr as ca
import time
tl = ca.Point(0, 0)
br = ca.Point(100, 50)
rect = ca.Rectangle(tl, br)
start = time.ticks_us()
for _ in range(10000):
    ca.get_width(rect)
    ca.get_height(rect)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
class Rectangle:
    def __init__(self, tl, br):
        self.top_left = tl
        self.bottom_right = br
def get_width(r):
    return r.bottom_right.x - r.top_left.x
def get_height(r):
    return r.bottom_right.y - r.top_left.y
tl = Point(0, 0)
br = Point(100, 50)
rect = Rectangle(tl, br)
start = time.ticks_us()
for _ in range(10000):
    get_width(rect)
    get_height(rect)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "container_attr x10000",
        """
import container_attrs as ca
import time
inner = ca.Inner([0, 1, 2], {'key': 42})
outer = ca.Outer(inner, 'test')
start = time.ticks_us()
for _ in range(10000):
    ca.benchmark_inner_list_update(outer, 1)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Inner:
    def __init__(self, items, data):
        self.items = items
        self.data = data
class Outer:
    def __init__(self, inner, name):
        self.inner = inner
        self.name = name
def benchmark(o, n):
    i = 0
    while i < n:
        o.inner.items[0] = i
        i += 1
    return o.inner.items[0]
inner = Inner([0, 1, 2], {'key': 42})
outer = Outer(inner, 'test')
start = time.ticks_us()
for _ in range(10000):
    benchmark(outer, 1)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "inner_list_update(10000) x10",
        """
import container_attrs as ca
import time
inner = ca.Inner([0, 1, 2], {})
outer = ca.Outer(inner, 'test')
start = time.ticks_us()
for _ in range(10):
    ca.benchmark_inner_list_update(outer, 10000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Inner:
    def __init__(self, items, data):
        self.items = items
        self.data = data
class Outer:
    def __init__(self, inner, name):
        self.inner = inner
        self.name = name
def benchmark(o, n):
    i = 0
    while i < n:
        o.inner.items[0] = i
        i += 1
    return o.inner.items[0]
inner = Inner([0, 1, 2], {})
outer = Outer(inner, 'test')
start = time.ticks_us()
for _ in range(10):
    benchmark(outer, 10000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "str.upper() x10000",
        """
import string_operations as s
import time
text = "hello world"
start = time.ticks_us()
for _ in range(10000):
    s.to_upper(text)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
text = "hello world"
start = time.ticks_us()
for _ in range(10000):
    text.upper()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "str.replace() x10000",
        """
import string_operations as s
import time
text = "hello world hello"
start = time.ticks_us()
for _ in range(10000):
    s.replace_string(text, "hello", "hi")
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
text = "hello world hello"
start = time.ticks_us()
for _ in range(10000):
    text.replace("hello", "hi")
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "str.find() x10000",
        """
import string_operations as s
import time
text = "hello world hello world"
start = time.ticks_us()
for _ in range(10000):
    s.find_substring(text, "world")
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
text = "hello world hello world"
start = time.ticks_us()
for _ in range(10000):
    text.find("world")
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "str.split() x5000",
        """
import string_operations as s
import time
text = "a,b,c,d,e,f,g,h,i,j"
start = time.ticks_us()
for _ in range(5000):
    s.split_on_sep(text, ",")
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
text = "a,b,c,d,e,f,g,h,i,j"
start = time.ticks_us()
for _ in range(5000):
    text.split(",")
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "str.join() x5000",
        """
import string_operations as s
import time
items = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
start = time.ticks_us()
for _ in range(5000):
    s.join_strings(",", items)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
items = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
start = time.ticks_us()
for _ in range(5000):
    ",".join(items)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "str.strip() x10000",
        """
import string_operations as s
import time
text = "  hello world  "
start = time.ticks_us()
for _ in range(10000):
    s.strip_string(text)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
text = "  hello world  "
start = time.ticks_us()
for _ in range(10000):
    text.strip()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "str concat x10000",
        """
import string_operations as s
import time
a = "hello"
b = " world"
start = time.ticks_us()
for _ in range(10000):
    s.concat_strings(a, b)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
a = "hello"
b = " world"
start = time.ticks_us()
for _ in range(10000):
    a + b
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "normalize_text x1000",
        """
import string_operations as s
import time
text = "  Hello   World  "
start = time.ticks_us()
for _ in range(1000):
    s.normalize_text(text)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def normalize_text(text):
    s = text.lower()
    s = s.strip()
    while "  " in s:
        s = s.replace("  ", " ")
    return s
text = "  Hello   World  "
start = time.ticks_us()
for _ in range(1000):
    normalize_text(text)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "sum_3_points x1000",
        """
import class_param as cp
import time
p1 = cp.Point(1, 2)
p2 = cp.Point(3, 4)
p3 = cp.Point(5, 6)
start = time.ticks_us()
for _ in range(1000):
    cp.sum_three_points(p1, p2, p3)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
def sum_three_points(p1, p2, p3):
    return p1.x + p1.y + p2.x + p2.y + p3.x + p3.y
p1 = Point(1, 2)
p2 = Point(3, 4)
p3 = Point(5, 6)
start = time.ticks_us()
for _ in range(1000):
    sum_three_points(p1, p2, p3)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    # List comprehension benchmarks
    (
        "listcomp squares(500) x100",
        """
import list_comprehension as lc
import time
start = time.ticks_us()
for _ in range(100):
    lc.squares(500)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def squares(n):
    return [x * x for x in range(n)]
start = time.ticks_us()
for _ in range(100):
    squares(500)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "super_init x1000",
        """
import super_calls
import time
start = time.ticks_us()
for _ in range(1000):
    super_calls.Dog("Rex", 5)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound
    def speak(self):
        return self.sound
    def describe(self):
        return self.name
class Dog(Animal):
    def __init__(self, name, tricks):
        super().__init__(name, "Woof")
        self.tricks = tricks
    def describe(self):
        base = super().describe()
        return base
    def get_tricks(self):
        return self.tricks
start = time.ticks_us()
for _ in range(1000):
    Dog("Rex", 5)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "listcomp evens(1000) x100",
        """
import list_comprehension as lc
import time
start = time.ticks_us()
for _ in range(100):
    lc.evens(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
def evens(n):
    return [x for x in range(n) if x % 2 == 0]
start = time.ticks_us()
for _ in range(100):
    evens(1000)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "super_method x10000",
        """
import super_calls
import time
dog = super_calls.Dog("Rex", 5)
start = time.ticks_us()
for _ in range(10000):
    dog.describe()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound
    def speak(self):
        return self.sound
    def describe(self):
        return self.name
class Dog(Animal):
    def __init__(self, name, tricks):
        super().__init__(name, "Woof")
        self.tricks = tricks
    def describe(self):
        base = super().describe()
        return base
    def get_tricks(self):
        return self.tricks
start = time.ticks_us()
for _ in range(10000):
    dog = Dog("Rex", 5)
    dog.describe()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "super_3level x1000",
        """
import super_calls
import time
start = time.ticks_us()
for _ in range(1000):
    sd = super_calls.ShowDog("Bella", 10, 3)
    sd.describe()
    sd.get_total_score()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound
    def speak(self):
        return self.sound
    def describe(self):
        return self.name
class Dog(Animal):
    def __init__(self, name, tricks):
        super().__init__(name, "Woof")
        self.tricks = tricks
    def describe(self):
        base = super().describe()
        return base
    def get_tricks(self):
        return self.tricks
class ShowDog(Dog):
    def __init__(self, name, tricks, awards):
        super().__init__(name, tricks)
        self.awards = awards
    def describe(self):
        base = super().describe()
        return base
    def get_total_score(self):
        return self.tricks + self.awards
start = time.ticks_us()
for _ in range(1000):
    sd = ShowDog("Bella", 10, 3)
    sd.describe()
    sd.get_total_score()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "public_work(100) x100",
        """
import private_methods as pm
import time
b = pm.Benchmark(5)
start = time.ticks_us()
for _ in range(100):
    b.run_public(100)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Benchmark:
    def __init__(self, d):
        self.data = d
    def public_work(self, n):
        total = 0
        for i in range(n):
            total += self.data + i
        return total
    def run_public(self, n):
        return self.public_work(n)
b = Benchmark(5)
start = time.ticks_us()
for _ in range(100):
    b.run_public(100)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "private_work(100) x100",
        """
import private_methods as pm
import time
b = pm.Benchmark(5)
start = time.ticks_us()
for _ in range(100):
    b.run_private(100)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class Benchmark:
    def __init__(self, d):
        self.data = d
    def __private_work(self, n):
        total = 0
        for i in range(n):
            total += self.data + i
        return total
    def run_private(self, n):
        return self.__private_work(n)
b = Benchmark(5)
start = time.ticks_us()
for _ in range(100):
    b.run_private(100)
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
    (
        "@final FastCounter x10000",
        """
import private_methods as pm
import time
fc = pm.FastCounter(1)
start = time.ticks_us()
for _ in range(10000):
    fc.increment()
    fc.reset()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
        """
import time
class FastCounter:
    def __init__(self, step):
        self.count = 0
        self.step = step
    def increment(self):
        self.count += self.step
        return self.count
    def reset(self):
        self.count = 0
fc = FastCounter(1)
start = time.ticks_us()
for _ in range(10000):
    fc.increment()
    fc.reset()
end = time.ticks_us()
print(time.ticks_diff(end, start))
""",
    ),
]


def _wait_for_port(port: str, max_retries: int = 20, base_delay: float = 0.1, max_delay: float = 5.0) -> bool:
    """Wait until the serial port is not held by another process.

    Uses exponential backoff with two strategies:
    1. lsof to check if any process holds the port file
    2. Try opening the port directly as a fallback

    Backoff schedule: base_delay * 2^attempt, capped at max_delay.
    """
    import random
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ["lsof", "-t", port],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode != 0:
                return True
        except Exception:
            pass
        try:
            fd = os.open(port, os.O_RDWR | os.O_NONBLOCK | os.O_NOCTTY)
            os.close(fd)
            return True
        except OSError:
            pass
        # Exponential backoff with jitter
        delay = min(base_delay * (2 ** attempt), max_delay)
        delay *= 0.5 + random.random()  # Add jitter: 50%-150% of delay
        time.sleep(delay)
    return False


def _check_port_lsof(port: str) -> bool:
    """Check if any process is holding the serial port via lsof.

    Returns True if port is free, False if busy.
    """
    try:
        result = subprocess.run(
            ["lsof", "-t", port],
            capture_output=True, text=True, timeout=3,
        )
        return result.returncode != 0
    except Exception:
        return True  # lsof unavailable, assume free


def run_on_device(code: str, timeout: int = 60, max_retries: int = 5,
                  base_delay: float = 0.5, max_delay: float = 10.0) -> tuple[bool, str]:
    """Execute Python code on device via mpremote with automatic retry.

    Uses exponential backoff with jitter on transient failures.
    Checks lsof port availability before each attempt.
    """
    import random
    last_error = ""
    for attempt in range(max_retries):
        # Check port is free before attempting connection
        if not _check_port_lsof(PORT):
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay *= 0.5 + random.random()
            time.sleep(delay)
            continue
        _wait_for_port(PORT)
        try:
            result = subprocess.run(
                ["mpremote", "connect", PORT, "exec", code],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            last_error = result.stderr.strip()
            retryable = (
                "failed to access" in last_error
                or "it may be in use" in last_error
                or "could not enter raw repl" in last_error
            )
            if retryable:
                delay = min(base_delay * (2 ** attempt), max_delay)
                delay *= 0.5 + random.random()  # Jitter
                time.sleep(delay)
                continue
            return False, last_error
        except subprocess.TimeoutExpired:
            last_error = "Timeout"
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay *= 0.5 + random.random()
            time.sleep(delay)
        except Exception as e:
            last_error = str(e)
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay *= 0.5 + random.random()
            time.sleep(delay)
    return False, last_error


def run_benchmark(name: str, native_code: str, python_code: str) -> tuple[int, int] | None:
    """Returns (native_us, python_us) or None on failure."""
    # Ensure port is free before running benchmark
    if not _check_port_lsof(PORT):
        _wait_for_port(PORT)
    success, output = run_on_device(native_code)
    if not success:
        print(f"  Native FAILED: {output}")
        return None
    try:
        native_us = int(output.split("\n")[-1])
    except (ValueError, IndexError):
        print(f"  Native parse error: {output}")
        return None

    # Ensure port is free before running python benchmark
    if not _check_port_lsof(PORT):
        _wait_for_port(PORT)
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
