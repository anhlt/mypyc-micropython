"""Device test runner for mypyc-micropython. Runs directly on MicroPython.

Usage: mpremote connect /dev/cu.usbmodem101 run run_device_tests.py
"""
# ruff: noqa: E402  # Module imports not at top - intentional for per-suite isolation

import gc

_total = 0
_passed = 0
_failed = 0


def t(name, got, expected):
    global _total, _passed, _failed
    _total += 1
    sg = str(got)
    if expected in sg:
        _passed += 1
        print("  OK: " + name)
    else:
        _failed += 1
        print("FAIL: " + name + " | got: " + sg[:100])


def suite(name):
    gc.collect()
    print("@S:" + name)


# ---- factorial ----
suite("factorial")
import factorial

t("factorial(5)", factorial.factorial(5), "120")
t("fib(10)", factorial.fib(10), "55")
t("add(3,4)", factorial.add(3, 4), "7")
t("is_even(4)", factorial.is_even(4), "True")
t("is_even(3)", factorial.is_even(3), "False")
t("multiply(6,7)", factorial.multiply(6, 7), "42.0")

# ---- point ----
suite("point")
import point

p = point.Point(3, 4)
t("Point creation", p, "Point(x=3, y=4)")
t("Point.x", p.x, "3")
t("Point.y", p.y, "4")
t("Point.distance_squared", p.distance_squared(), "25")
t("Point.add(1,2)", p.add(1, 2), "10")
p3 = point.Point3D(1, 2, 3)
t("Point3D creation", p3, "Point3D(x=1, y=2, z=3)")
t("Point3D fields", str(p3.x) + " " + str(p3.y) + " " + str(p3.z), "1 2 3")

# ---- counter ----
suite("counter")
import counter

c = counter.Counter(10, 2)
t("Counter creation", c.get(), "10")
c2 = counter.Counter(10, 2)
c2.increment()
t("Counter.increment", c2.get(), "12")
c3 = counter.Counter(10, 2)
c3.decrement()
t("Counter.decrement", c3.get(), "8")
c4 = counter.Counter(10, 2)
c4.reset()
t("Counter.reset", c4.get(), "0")
bc = counter.BoundedCounter(5, 1, 0, 10)
t("BoundedCounter.get", bc.get(), "5")
bc2 = counter.BoundedCounter(5, 1, 0, 10)
bc2.reset()
t("BoundedCounter.reset", bc2.get(), "0")
bc3 = counter.BoundedCounter(9, 1, 0, 10)
bc3.increment()
t("BoundedCounter.increment", bc3.get(), "10")
bc4 = counter.BoundedCounter(10, 1, 0, 10)
bc4.increment()
t("BoundedCounter.capped", bc4.get(), "10")

# ---- sensor ----
suite("sensor")
import sensor

r = sensor.SensorReading(1, 25.5, 60.0)
t(
    "SensorReading creation",
    r,
    "SensorReading(sensor_id=1, temperature=25.5, humidity=60.0, valid=True)",
)
t("SensorReading valid", r.valid, "True")
r2 = sensor.SensorReading(1, 25.5, 60.0, False)
t("SensorReading valid=False", r2.valid, "False")
b = sensor.SensorBuffer()
b.add_reading(25.0, 55.0)
t("SensorBuffer add", b.count, "1")
b2 = sensor.SensorBuffer()
b2.add_reading(25.0, 55.0)
b2.add_reading(27.0, 65.0)
t("SensorBuffer avg_temp", b2.avg_temperature(), "26.0")
t("SensorBuffer avg_hum", b2.avg_humidity(), "60.0")
b3 = sensor.SensorBuffer()
b3.add_reading(25.0, 55.0)
b3.reset()
t("SensorBuffer reset", b3.avg_temperature(), "0.0")

# ---- list_operations ----
suite("list_operations")
import list_operations

t("sum_list", list_operations.sum_list([1, 2, 3, 4, 5]), "15")
t("build_squares", list_operations.build_squares(5), "[0, 1, 4, 9, 16]")
t("find_first_neg found", list_operations.find_first_negative([1, -2, 3]), "1")
t("find_first_neg none", list_operations.find_first_negative([1, 2, 3]), "-1")

# ---- math_utils ----
suite("math_utils")
import math_utils

t("c_to_f", math_utils.celsius_to_fahrenheit(0), "32.0")
t("f_to_c", math_utils.fahrenheit_to_celsius(32), "0.0")
t("clamp mid", math_utils.clamp(5.0, 0.0, 10.0), "5.0")
t("clamp low", math_utils.clamp(-5.0, 0.0, 10.0), "0.0")
t("clamp high", math_utils.clamp(15.0, 0.0, 10.0), "10.0")
t("lerp", math_utils.lerp(0.0, 10.0, 0.5), "5.0")

# ---- bitwise ----
suite("bitwise")
import bitwise

t("set_bit(0,0)", bitwise.set_bit(0, 0), "1")
t("set_bit(1,1)", bitwise.set_bit(1, 1), "3")
t("clear_bit(7,0)", bitwise.clear_bit(7, 0), "6")
t("toggle_bit(7,0)", bitwise.toggle_bit(7, 0), "6")
t("check_bit(7,2)", bitwise.check_bit(7, 2), "True")
t("check_bit(7,3)", bitwise.check_bit(7, 3), "False")
t("count_ones(7)", bitwise.count_ones(7), "3")
t("count_ones(0)", bitwise.count_ones(0), "0")
t("is_pow2(4)", bitwise.is_power_of_two(4), "True")
t("is_pow2(5)", bitwise.is_power_of_two(5), "False")

# ---- algorithms ----
suite("algorithms")
import algorithms

t("is_prime(17)", algorithms.is_prime(17), "True")
t("is_prime(18)", algorithms.is_prime(18), "False")
t("gcd(48,18)", algorithms.gcd(48, 18), "6")
t("lcm(4,6)", algorithms.lcm(4, 6), "12")
t("power(2,10)", algorithms.power(2, 10), "1024")

# ---- dict_operations ----
suite("dict_operations")
import dict_operations

t("get_value", dict_operations.get_value({"x": 10}, "x"), "10")
t("count_items", dict_operations.count_items({"a": 1, "b": 2}), "2")
t("merge_dicts", len(dict_operations.merge_dicts({"a": 1}, {"b": 2})), "2")

# ---- inventory ----
suite("inventory")
import inventory

inv = inventory.Inventory()
t("Inventory total_count", inv.total_count, "0")
inv2 = inventory.Inventory()
inv2.add_item(100, 5)
t("Inventory get_qty", inv2.get_quantity(100), "5")
inv3 = inventory.Inventory()
inv3.add_item(100, 5)
inv3.add_item(200, 3)
t("Inventory item_count", inv3.item_count(), "2")
t("Inventory total_qty", inv3.total_quantity(), "8")
inv4 = inventory.Inventory()
inv4.add_item(100, 5)
t("Inventory has_item", inv4.has_item(100), "True")
t("Inventory no_item", inv4.has_item(999), "False")

# ---- tuple_operations ----
suite("tuple_operations")
import tuple_operations as to

t("make_point", to.make_point(), "(10, 20)")
t("make_triple", to.make_triple(1, 2, 3), "(1, 2, 3)")
t("empty_tuple", to.empty_tuple(), "()")
t("single_element", to.single_element(), "(42,)")
t("get_first", to.get_first((10, 20, 30)), "10")
t("get_last", to.get_last((10, 20, 30)), "30")
t("tuple_len", to.tuple_len((1, 2, 3, 4, 5)), "5")
t("tuple_contains T", to.tuple_contains((1, 2, 3), 2), "True")
t("tuple_contains F", to.tuple_contains((1, 2, 3), 5), "False")
t("tuple_not_contains", to.tuple_not_contains((1, 2, 3), 5), "True")
t("sum_tuple", to.sum_tuple((1, 2, 3, 4, 5)), "15")
t("nested_iteration", to.nested_iteration((10, 20, 30)), "80")
t("unpack_pair", to.unpack_pair((10, 20)), "30")
t("unpack_triple", to.unpack_triple((2, 3, 4)), "24")
t("concat_tuples", to.concat_tuples((1, 2), (3, 4)), "(1, 2, 3, 4)")
t("repeat_tuple", to.repeat_tuple((1, 2), 3), "(1, 2, 1, 2, 1, 2)")
t("slice_tuple", to.slice_tuple((1, 2, 3, 4, 5)), "(2, 3)")
t("from_range", to.from_range(5), "(0, 1, 2, 3, 4)")
t("rtuple_point", to.rtuple_point(), "(100, 200)")
t("rtuple_add_coords", to.rtuple_add_coords(10, 20, 30, 40), "(40, 60)")
t("rtuple_sum_fields", to.rtuple_sum_fields(), "40")
t("rtuple_dist_sq", to.rtuple_distance_squared(0, 0, 3, 4), "25")
t("rtuple_rgb", to.rtuple_rgb(), "(255, 128, 64)")
t("rtuple_sum_rgb", to.rtuple_sum_rgb(100, 150, 200), "450")
t("rtuple_blend", to.rtuple_blend_colors(200, 100, 50, 100, 200, 150), "(150, 150, 100)")
t("rtuple_bench", to.rtuple_benchmark_internal(10), "135")
t("sum_points_list", to.sum_points_list([(1, 2, 3), (4, 5, 6), (7, 8, 9)], 3), "45")

# ---- set_operations ----
suite("set_operations")
import set_operations as so

r = so.make_set()
t("make_set", 1 in r and 2 in r and 3 in r, "True")
t("empty_set", so.empty_set(), "set()")
t("set_from_range len", len(so.set_from_range(5)) == 5 and 0 in so.set_from_range(5), "True")
t("set_len", so.set_len({1, 2, 3, 4, 5}), "5")
t("set_contains T", so.set_contains({1, 2, 3}, 2), "True")
t("set_contains F", so.set_contains({1, 2, 3}, 5), "False")
t("set_not_contains", so.set_not_contains({1, 2, 3}, 5), "True")
t("set_add", 3 in so.set_add({1, 2}, 3), "True")
t("set_discard", 2 not in so.set_discard({1, 2, 3}, 2), "True")
t("set_remove", 2 not in so.set_remove({1, 2, 3}, 2), "True")
t("set_clear", len(so.set_clear({1, 2, 3})), "0")
t("set_copy", len(so.set_copy({1, 2, 3})), "3")
t("set_update", len(so.set_update({1, 2}, {3, 4})), "4")
t("sum_set", so.sum_set({1, 2, 3, 4, 5}), "15")
t("build_set_incr", so.build_set_incremental(20), "10")
t("filter_dups", so.filter_duplicates(10), "10")

# ---- builtins_demo ----
suite("builtins_demo")
import builtins_demo as bd

t("is_truthy(1)", bd.is_truthy(1), "True")
t("is_truthy(0)", bd.is_truthy(0), "False")
t("is_list_empty([])", bd.is_list_empty([]), "True")
t("is_list_empty([1])", bd.is_list_empty([1]), "False")
t("find_min_two", bd.find_min_two(5, 3), "3")
t("find_min_three", bd.find_min_three(7, 2, 9), "2")
t("find_max_two", bd.find_max_two(5, 3), "5")
t("find_max_three", bd.find_max_three(7, 2, 9), "9")
t("sum_list", bd.sum_list([1, 2, 3, 4, 5]), "15")
t("sum_list_start", bd.sum_list_with_start([1, 2, 3], 10), "16")
t("clamp mid", bd.clamp(5, 0, 10), "5")
t("clamp low", bd.clamp(-5, 0, 10), "0")
t("clamp high", bd.clamp(15, 0, 10), "10")
t("abs_diff 10-3", bd.abs_diff(10, 3), "7")
t("abs_diff 3-10", bd.abs_diff(3, 10), "7")
t("clamp_list", bd.clamp_list([1, 5, 10, 15], 3, 12), "[3, 5, 10, 12]")
t("find_extremes_sum", bd.find_extremes_sum([1, 5, 3, 9, 2]), "10")
t("sum_int_list", bd.sum_int_list([1, 2, 3, 4, 5]), "15")
t("sum_int_list big", bd.sum_int_list(list(range(101))), "5050")
t("sum_int_list empty", bd.sum_int_list([]), "0")

# ---- default_args ----
suite("default_args")
import default_args as da

t("add_default(5,3)", da.add_with_default(5, 3), "8")
t("add_default(5)", da.add_with_default(5), "15")
t("clamp(150)", da.clamp(150), "100")
t("clamp(-10)", da.clamp(-10), "0")
t("clamp(50)", da.clamp(50), "50")
t("clamp(50,10,40)", da.clamp(50, 10, 40), "40")
t("increment(10)", da.increment(10), "11")
t("increment(10,5)", da.increment(10, 5), "15")
t("double_if(5)", da.double_if_flag(5), "10")
t("double_if(5,F)", da.double_if_flag(5, False), "5")
t("all_defaults()", da.all_defaults(), "6")
t("all_defaults(10)", da.all_defaults(10), "15")
t("all_defaults(10,20)", da.all_defaults(10, 20), "33")
t("all_defaults(10,20,30)", da.all_defaults(10, 20, 30), "60")
t("power(2)", da.power(2), "4")
t("power(2,3)", da.power(2, 3), "8")
t("sum_start([1,2,3])", da.sum_with_start([1, 2, 3]), "6")
t("sum_start([1,2,3],10)", da.sum_with_start([1, 2, 3], 10), "16")

# ---- star_args ----
suite("star_args")
import star_args as sa

t("sum_all(1,2,3)", sa.sum_all(1, 2, 3), "6")
t("sum_all()", sa.sum_all(), "0")
t("sum_all(10,20,30,40)", sa.sum_all(10, 20, 30, 40), "100")
t("sum_args(5,10,15)", sa.sum_args(5, 10, 15), "30")
t("count_args(1,2,3,4,5)", sa.count_args(1, 2, 3, 4, 5), "5")
t("count_args()", sa.count_args(), "0")
t("first_or_default(42,1,2)", sa.first_or_default(42, 1, 2), "42")
t("first_or_default()", sa.first_or_default(), "-1")
t("log_values(100,1,2,3)", sa.log_values(100, 1, 2, 3), "106")
t("log_values(50)", sa.log_values(50), "50")
t("count_kwargs", sa.count_kwargs(a=1, b=2), "2")
t("count_kwargs()", sa.count_kwargs(), "0")
t("make_config type", type(sa.make_config(x=1, y=2)).__name__, "dict")
t("process", sa.process(10, 1, 2, a=1, b=2), "15")
t("max_of_args", sa.max_of_args(3, 7, 2, 9, 1), "9")
t("min_of_args", sa.min_of_args(3, 7, 2, 9, 1), "1")

# ---- class_param ----
suite("class_param")
import class_param as cp

pp = cp.Point(10, 20)
t("get_x", cp.get_x(pp), "10")
t("get_y", cp.get_y(pp), "20")
t("add_coords", cp.add_coords(cp.Point(3, 4)), "7")
t("distance_sq", cp.distance_squared(cp.Point(0, 0), cp.Point(3, 4)), "25")
t("midpoint_x", cp.midpoint_x(cp.Point(0, 0), cp.Point(10, 10)), "5")
t("scale_point", cp.scale_point(cp.Point(2, 3), 4), "20")
t("dot_product", cp.dot_product(cp.Vector(1.0, 2.0), cp.Vector(3.0, 4.0)), "11.0")
t("length_sq", cp.length_squared(cp.Vector(3.0, 4.0)), "25.0")

# ---- chained_attr ----
suite("chained_attr")
import chained_attr as ca

tl = ca.Point(0, 0)
br = ca.Point(100, 50)
rect = ca.Rectangle(tl, br)
t("get_width", ca.get_width(rect), "100")
t("get_height", ca.get_height(rect), "50")
rect2 = ca.Rectangle(ca.Point(0, 0), ca.Point(10, 5))
t("get_area", ca.get_area(rect2), "50")
rect3 = ca.Rectangle(ca.Point(3, 7), ca.Point(10, 20))
t("get_tl_x", ca.get_top_left_x(rect3), "3")
t("get_tl_y", ca.get_top_left_y(rect3), "7")
t("get_br_x", ca.get_bottom_right_x(rect3), "10")
t("get_br_y", ca.get_bottom_right_y(rect3), "20")
n2 = ca.Node(42, None)
n1 = ca.Node(10, n2)
t("get_next_value", ca.get_next_value(n1), "42")

# ---- container_attrs ----
suite("container_attrs")
import container_attrs as cta

cc = cta.Container([1, 2, 3], {"a": 1}, {1, 2})
t("get_items", cta.get_items(cc), "[1, 2, 3]")
cc2 = cta.Container([1], {"x": 10}, {1})
t("get_mapping", cta.get_mapping(cc2), "{'x': 10}")
cc3 = cta.Container([1], {"a": 1}, {5, 10, 15})
uu = cta.get_unique(cc3)
t("get_unique", 5 in uu and 10 in uu, "True")
t("get_first_item", cta.get_first_item(cta.Container([42, 2, 3], {}, set())), "42")
t("get_mapping_key", cta.get_mapping_key(cta.Container([], {"key": 99}, set()), "key"), "99")
t("has_in_unique T", cta.has_in_unique(cta.Container([], {}, {1, 2, 3}), 2), "True")
t("has_in_unique F", cta.has_in_unique(cta.Container([], {}, {1, 2, 3}), 5), "False")
i1 = cta.Inner([10, 20, 30], {})
o1 = cta.Outer(i1, "test")
t("get_inner_items", cta.get_inner_items(o1), "[10, 20, 30]")
i2 = cta.Inner([], {"k": 5})
o2 = cta.Outer(i2, "test")
t("get_inner_data", cta.get_inner_data(o2), "{'k': 5}")
i3 = cta.Inner([100, 200], {})
o3 = cta.Outer(i3, "test")
t("get_first_inner", cta.get_first_inner_item(o3), "100")
i4 = cta.Inner([], {"val": 77})
o4 = cta.Outer(i4, "test")
t("get_inner_data_key", cta.get_inner_data_key(o4, "val"), "77")
i5 = cta.Inner([1, 2, 3, 4, 5], {})
o5 = cta.Outer(i5, "test")
t("count_inner", cta.count_inner_items(o5), "5")
t("sum_inner", cta.sum_inner_items(o5), "15")

# ---- string_operations ----
suite("string_operations")
import string_operations as so2

t("concat", so2.concat_strings("hello", " world"), "hello world")
t("repeat", so2.repeat_string("ab", 3), "ababab")
t("upper", so2.to_upper("hello"), "HELLO")
t("lower", so2.to_lower("HELLO"), "hello")
t("find found", so2.find_substring("hello world", "world"), "6")
t("find miss", so2.find_substring("hello world", "xyz"), "-1")
t("rfind", so2.rfind_substring("hello hello", "hello"), "6")
t("count_sub", so2.count_substring("abababab", "ab"), "4")
t("split", so2.split_string("a b c"), "['a', 'b', 'c']")
t("split_sep", so2.split_on_sep("a,b,c", ","), "['a', 'b', 'c']")
t("join", so2.join_strings("-", ["a", "b", "c"]), "a-b-c")
t("strip", repr(so2.strip_string("  hello  ")), "'hello'")
t("lstrip", repr(so2.lstrip_string("  hello  ")), "'hello  '")
t("rstrip", repr(so2.rstrip_string("  hello  ")), "'  hello'")
t("strip_chars", so2.strip_chars("xxxhelloxxx", "x"), "hello")
t("replace", so2.replace_string("hello world", "world", "python"), "hello python")
t("startswith T", so2.starts_with("hello world", "hello"), "True")
t("startswith F", so2.starts_with("hello world", "world"), "False")
t("endswith T", so2.ends_with("hello world", "world"), "True")
t("endswith F", so2.ends_with("hello world", "hello"), "False")
t("center", repr(so2.center_string("hi", 6)), "'  hi  '")
t("partition", so2.partition_string("hello=world", "="), "('hello', '=', 'world')")
t("rpartition", so2.rpartition_string("a=b=c", "="), "('a=b', '=', 'c')")
t("process_csv", so2.process_csv_line("a, b, c"), "['a', 'b', 'c']")
t("normalize", so2.normalize_text("  Hello   World  "), "hello world")
t("build_path", so2.build_path(["home", "user", "file.txt"]), "home/user/file.txt")
t("extract_ext", so2.extract_extension("document.pdf"), "pdf")
t("extract_ext none", repr(so2.extract_extension("README")), "''")

# ---- itertools_builtins ----
suite("itertools_builtins")
import itertools_builtins as ib

t("sum_with_idx", ib.sum_with_indices([10, 20, 30]), "80")
t("enum_from_start", ib.enumerate_from_start(["a", "b", "c"], 5), "[5, 6, 7]")
t("dot_product", ib.dot_product([1, 2, 3], [4, 5, 6]), "32")
t("zip_three", ib.zip_three_lists([1, 2], [10, 20], [100, 200]), "[111, 222]")
t("get_sorted", ib.get_sorted([3, 1, 2]), "[1, 2, 3]")
t("sum_sorted", ib.sum_sorted([3, 1, 2]), "6")
t("first_sorted", ib.get_first_sorted([30, 10, 20]), "10")
t("last_sorted", ib.get_last_sorted([30, 10, 20]), "30")

# ---- exception_handling ----
suite("exception_handling")
import exception_handling as eh

t("safe_div(10,2)", eh.safe_divide(10, 2), "5")
t("safe_div(10,0)", eh.safe_divide(10, 0), "0")
t("validate_pos(5)", eh.validate_positive(5), "5")
t("validate_range", eh.validate_range(50, 0, 100), "50")
t("with_cleanup(5)", eh.with_cleanup(5), "11")
t("multi_catch(10,2)", eh.multi_catch(10, 2), "5")
t("multi_catch(10,0)", eh.multi_catch(10, 0), "-1")
t("multi_catch(-5,2)", eh.multi_catch(-5, 2), "-2")
t("try_else(3,4)", eh.try_else(3, 4), "14")
t("full_try(10,2)", eh.full_try(10, 2), "105")
t("full_try(10,0)", eh.full_try(10, 0), "99")
t("catch_all(50)", eh.catch_all(50), "50")
t("catch_all(-5)", eh.catch_all(-5), "-1")
t("catch_all(150)", eh.catch_all(150), "-1")
t("nested_try(10,2,1)", eh.nested_try(10, 2, 1), "5")
t("nested_try(10,0,2)", eh.nested_try(10, 0, 2), "0")
t("nested_try(10,0,0)", eh.nested_try(10, 0, 0), "-1")

# ---- super_calls ----
suite("super_calls")
import super_calls as sc

sd = sc.ShowDog("Bella", 10, 3)
t("ShowDog name", sd.name, "Bella")
t("ShowDog speak", sd.speak(), "Woof")
t("ShowDog describe", sd.describe(), "Bella")
t("ShowDog awards", sd.get_awards(), "3")
t("ShowDog total_score", sd.get_total_score(), "13")
t("ShowDog tricks", sd.get_tricks(), "10")

# ---- decorators ----
suite("decorators")
import decorators as dec

t("is_square_dims T", dec.Rectangle.is_square_dims(3, 3), "True")
t("is_square_dims F", dec.Rectangle.is_square_dims(3, 4), "False")
t("Counter.add", dec.Counter.add(3, 4), "7")
t("square classmethod", dec.Rectangle.square(5) is dec.Rectangle, "True")
dr = dec.Rectangle(3, 4)
t("area property", dr.area, "12")
t("perimeter property", dr.perimeter, "14")
dt = dec.Temperature(25)
t("celsius getter", dt.celsius, "25")
dt2 = dec.Temperature(25)
dt2.celsius = 30
t("celsius setter", dt2.celsius, "30")
dc = dec.Counter(0)
t("count property", dc.count, "0")
dc2 = dec.Counter(0)
dc2.increment()
t("count after incr", dc2.count, "1")
t("Counter.add inst", dec.Counter(0).add(10, 20), "30")
t("get_fahrenheit", dec.Temperature(100).get_fahrenheit(), "212")
dr2 = dec.Rectangle(3, 4)
dr2.scale(2)
t("area after scale", dr2.area, "48")

# ---- classes ----
suite("classes")
import classes as cl

loc = cl.Location(10, 20)
t("Location", str(loc.x) + " " + str(loc.y), "10 20")
e = cl.Entity("sensor1", 42)
t("Entity name", e.name, "sensor1")
t("Entity id", e.id, "42")
e2 = cl.Entity("s", 7)
t("Entity.id", e2.id, "7")
t("validate_name T", cl.Entity.validate_name("hello"), "True")
t("validate_name F", cl.Entity.validate_name(""), "False")
e3 = cl.Entity("s", 1)
e3.add_tag(10)
e3.add_tag(20)
t("tag_count", e3.tag_count(), "2")
e4 = cl.Entity("s", 1)
e4.add_tag(10)
t("has_tag T", e4.has_tag(10), "True")
t("has_tag F", e4.has_tag(99), "False")
t("describe", cl.Entity("myname", 1).describe(), "myname")
s = cl.Sensor("temp", 5, cl.Location(1, 2))
t("Sensor name", s.name, "temp")
t("Sensor id", cl.Sensor("t", 5, cl.Location(0, 0)).id, "5")
t("Sensor value", cl.Sensor("t", 1, cl.Location(0, 0)).value, "0.0")
sv = cl.Sensor("t", 1, cl.Location(0, 0))
sv.value = 3.14
t("Sensor value set", sv.value, "3.14")
t("Sensor create cls", cl.Sensor.create("x") is cl.Sensor, "True")
sr = cl.Sensor("t", 1, cl.Location(0, 0))
sr.record(100, 25.5)
sr.record(200, 26.0)
t("reading_count", sr.reading_count(), "2")
sr2 = cl.Sensor("t", 1, cl.Location(0, 0))
sr2.record(100, 25.5)
t("get_reading", sr2.get_reading(100), "25.5")
sl = cl.Sensor("t", 1, cl.Location(30, 40))
t("get_loc_x", sl.get_location_x(), "30")
t("get_loc_y", sl.get_location_y(), "40")
t("Sensor describe", cl.Sensor("mysensor", 1, cl.Location(0, 0)).describe(), "mysensor")
st = cl.Sensor("t", 1, cl.Location(0, 0))
st.add_tag(42)
t("Sensor has_tag", st.has_tag(42), "True")
ss = cl.SmartSensor("smart", 10, cl.Location(5, 5), 50.0)
t("SmartSensor name", ss.name, "smart")
t("SmartSensor id", cl.SmartSensor("s", 10, cl.Location(0, 0), 50.0).id, "10")
ss2 = cl.SmartSensor("s", 1, cl.Location(0, 0), 50.0)
ss2.value = 30.0
t("check_value F", ss2.check_value(), "False")
ss3 = cl.SmartSensor("s", 1, cl.Location(0, 0), 50.0)
ss3.value = 60.0
t("check_value T", ss3.check_value(), "True")
ss4 = cl.SmartSensor("s", 1, cl.Location(0, 0), 50.0)
ss4.value = 60.0
ss4.check_value()
ss4.check_value()
t("alert_count", ss4.get_alert_count(), "2")
t("SS describe", cl.SmartSensor("deep", 1, cl.Location(0, 0), 50.0).describe(), "deep")
ss5 = cl.SmartSensor("s", 10, cl.Location(0, 0), 50.0)
ss5.value = 60.0
ss5.check_value()
t("SS total_score", ss5.get_total_score(), "11")
t("validate via inst", cl.Sensor("t", 1, cl.Location(0, 0)).validate_name("ok"), "True")
t("distance_between", cl.distance_between(cl.Location(0, 0), cl.Location(3, 4)), "25")
ss6 = cl.Sensor("t", 10, cl.Location(0, 0))
ss6.record(1, 1.0)
ss6.record(2, 2.0)
t("sensor_summary", cl.sensor_summary(ss6), "12")
# __repr__ and __str__ - all 4 cases
# Case 1: __repr__ only (Entity) - str() falls back to __repr__
t("Entity repr", repr(cl.Entity("my_entity", 1)), "my_entity")
t("Entity str fallback", str(cl.Entity("my_entity", 1)), "my_entity")
# Case 2: __str__ only (Sensor) - repr() uses default
t("Sensor str", str(cl.Sensor("my_sensor", 1, cl.Location(0, 0))), "my_sensor")
t("Sensor repr default", repr(cl.Sensor("x", 1, cl.Location(0, 0))), "<Sensor object>")
# Case 3: both __str__ and __repr__ (BothStrRepr)
t("BothStrRepr str", str(cl.BothStrRepr(42)), "str:42")
t("BothStrRepr repr", repr(cl.BothStrRepr(42)), "repr:42")
# Case 4: neither (NeitherStrRepr) - both use default
t("NeitherStrRepr str", str(cl.NeitherStrRepr(1)), "<NeitherStrRepr>")
t("NeitherStrRepr repr", repr(cl.NeitherStrRepr(1)), "<NeitherStrRepr>")
# ---- math_ops ----
suite("math_ops")
import math_ops

t("distance(0,0,3,4)", math_ops.distance(0, 0, 3, 4), "5.0")
t("distance(1,1,1,1)", math_ops.distance(1, 1, 1, 1), "0.0")
ca1 = math_ops.circle_area(1)
t("circle_area(1)", ca1 > 3.14 and ca1 < 3.15, "True")
t("circle_area(0)", math_ops.circle_area(0), "0.0")
dr1 = math_ops.deg_to_rad(180)
t("deg_to_rad(180)", dr1 > 3.14 and dr1 < 3.15, "True")
t("deg_to_rad(0)", math_ops.deg_to_rad(0), "0.0")
t("trig_sum(0)", math_ops.trig_sum(0), "1.0")
t("timed_sum(10)", math_ops.timed_sum(10), "45")

# ---- cross_import ----
suite("cross_import")
import cross_import

t("double_factorial(5)", cross_import.double_factorial(5), "240")
t("fib_plus(10,100)", cross_import.fib_plus(10, 100), "155")
t("combo_add(3,4)", cross_import.combo_add(3, 4), "7")
t("native_distance", cross_import.native_distance(0, 0, 3, 4), "5.0")
t("sum_and_factorial(5)", cross_import.sum_and_factorial(5), "1200")

# ---- sensor_lib ----
suite("sensor_lib")
import sensor_lib

t("math_helpers.distance", sensor_lib.math_helpers.distance(0, 0, 3, 4), "25")
t("math_helpers.midpoint", sensor_lib.math_helpers.midpoint(10, 20), "15")
t("math_helpers.scale", sensor_lib.math_helpers.scale(5, 3), "15")
t("filters.clamp high", sensor_lib.filters.clamp(150, 0, 100), "100")
t("filters.clamp low", sensor_lib.filters.clamp(-5, 0, 100), "0")
t("filters.clamp mid", sensor_lib.filters.clamp(50, 0, 100), "50")
t("filters.moving_avg", sensor_lib.filters.moving_avg(100, 200, 50), "150")
t("filters.threshold T", sensor_lib.filters.threshold(75, 50), "True")
t("filters.threshold F", sensor_lib.filters.threshold(25, 50), "False")
t("converters.c_to_f", sensor_lib.converters.celsius_to_fahrenheit(100), "212")
t("converters.f_to_c", sensor_lib.converters.fahrenheit_to_celsius(212), "100")
t("converters.mm_to_in", sensor_lib.converters.mm_to_inches(254), "100")
t("processing.version", sensor_lib.processing.version(), "1")
t("smoothing.simple_avg", sensor_lib.processing.smoothing.simple_avg(10, 20), "15")
t("smoothing.exp_avg", sensor_lib.processing.smoothing.exponential_avg(100, 200, 50), "150")
t("calibration.offset", sensor_lib.processing.calibration.apply_offset(100, 5), "105")
t("calibration.scale", sensor_lib.processing.calibration.apply_scale(100, 3, 2), "150")

# ---- private_methods ----
suite("private_methods")
import private_methods as pm

t("Calculator compute", pm.Calculator(10).compute(5), "35")
t("Calculator(0) compute", pm.Calculator(0).compute(3), "9")
fc = pm.FastCounter(3)
fc.increment()
fc.increment()
t("FastCounter incr", fc.get(), "6")
fc2 = pm.FastCounter(3)
fc2.increment()
fc2.reset()
t("FastCounter reset", fc2.get(), "0")
t("FastCounter ret", pm.FastCounter(5).increment(), "5")
t("Config scaled", pm.Config(7).scaled_value(), "14")
t("Config limit T", pm.Config(1).is_within_limit(999), "True")
t("Config limit F", pm.Config(1).is_within_limit(1000), "False")
t("Bench public", pm.Benchmark(5).run_public(10), "95")
t("Bench private", pm.Benchmark(5).run_private(10), "95")
t("Bench eq", pm.Benchmark(3).run_public(100) == pm.Benchmark(3).run_private(100), "True")


# ---- special_methods ----
suite("special_methods")
import special_methods as sm

# Number: comparison operators
n3 = sm.Number(3)
n5 = sm.Number(5)
n3b = sm.Number(3)
t("Number eq T", n3 == n3b, "True")
t("Number eq F", n3 == n5, "False")
t("Number ne T", n3 != n5, "True")
t("Number ne F", n3 != n3b, "False")
t("Number lt T", n3 < n5, "True")
t("Number lt F", n5 < n3, "False")
t("Number le T eq", n3 <= n3b, "True")
t("Number le T lt", n3 <= n5, "True")
t("Number le F", n5 <= n3, "False")
t("Number gt T", n5 > n3, "True")
t("Number gt F", n3 > n5, "False")
t("Number ge T eq", n3 >= n3b, "True")
t("Number ge T gt", n5 >= n3, "True")
t("Number ge F", n3 >= n5, "False")
# Number: hash
t("Number hash", hash(sm.Number(42)), "42")
t("Number hash 0", hash(sm.Number(0)), "0")
# Number: get_value
t("Number get_value", sm.Number(7).get_value(), "7")
# Counter: iterator protocol
c = sm.Counter(5)
vals = []
for v in c:
    vals.append(v)
t("Counter iter", str(vals), "[0, 1, 2, 3, 4]")
t("Counter current after", c.get_current(), "5")
# Counter: empty
c0 = sm.Counter(0)
vals0 = []
for v in c0:
    vals0.append(v)
t("Counter empty", str(vals0), "[]")
# Free functions
t("compare lt", sm.compare_numbers(3, 5), "-1")
t("compare gt", sm.compare_numbers(5, 3), "1")
t("compare eq", sm.compare_numbers(4, 4), "0")
t("sum_counter", sm.sum_counter(5), "10")


# ---- generators ----
suite("generators")
import generators as g

vals = []
for v in g.countdown(5):
    vals.append(v)
t("countdown", str(vals), "[5, 4, 3, 2, 1]")

sq = []
for v in g.squares(5):
    sq.append(v)
t("squares", str(sq), "[0, 1, 4, 9, 16]")

# Test new generator patterns: for-iter and range with start
items_result = []
for v in g.iter_items([10, 20, 30]):
    items_result.append(v)
t("iter_items", str(items_result), "[10, 20, 30]")

range_start_result = []
for v in g.range_with_start(5):
    range_start_result.append(v)
t("range_with_start", str(range_start_result), "[1, 2, 3, 4]")

# Test yield from generators
delegate_result = []
for v in g.delegate_to_list([100, 200, 300]):
    delegate_result.append(v)
t("delegate_to_list", str(delegate_result), "[100, 200, 300]")

flatten_result = []
for v in g.flatten([[1, 2], [3, 4, 5]]):
    flatten_result.append(v)
t("flatten", str(flatten_result), "[1, 2, 3, 4, 5]")

chain_result = []
for v in g.chain_iterables([1, 2], [3, 4, 5]):
    chain_result.append(v)
t("chain_iterables", str(chain_result), "[1, 2, 3, 4, 5]")

prefix_result = []
for v in g.prefix_and_delegate(0, [10, 20], 99):
    prefix_result.append(v)
t("prefix_and_delegate", str(prefix_result), "[0, 10, 20, 99]")

# ---- traits ----
suite("traits")
import traits

# Test Person class (Entity + Named + Describable traits)
p = traits.Person(1, "Alice", 30)
t("Person id", p.get_id(), "1")
t("Person name", p.get_name(), "Alice")  # Trait method with field access
t("Person age", p.age, "30")

# Test Pet class (Entity + Named + Describable traits)
cat = traits.Pet(2, "Whiskers", "cat")
t("Pet id", cat.get_id(), "2")
t("Pet name", cat.get_name(), "Whiskers")  # Trait method with field access

# Test Document class (Printable trait)
doc = traits.Document("README", "Hello World")
# Note: to_string() uses f-string with self.attr, skipped due to f-string issue
t("Document title", doc.title, "README")
t("Document body", doc.body, "Hello World")

# Test trait-typed parameters (polymorphism)
# greet_named accepts any Named implementor
t("greet_named(Person)", traits.greet_named(p), "Alice")
t("greet_named(Pet)", traits.greet_named(cat), "Whiskers")

# Direct attribute access on trait-typed parameter
t("get_name_direct(Person)", traits.get_name_direct(p), "Alice")
t("get_name_direct(Pet)", traits.get_name_direct(cat), "Whiskers")

# Test trait param function
t("test_trait_param", traits.test_trait_param(), "Alice,Whiskers,Alice,Whiskers")

# Test is/is not with trait-typed parameters
p2 = traits.Person(3, "Bob", 25)
t("is_same_named(p,p)", traits.is_same_named(p, p), "True")
t("is_same_named(p,p2)", traits.is_same_named(p, p2), "False")
t("is_not_same_named(p,p2)", traits.is_not_same_named(p, p2), "True")
t("is_not_same_named(p,p)", traits.is_not_same_named(p, p), "False")
t("is_not_none_named(p)", traits.is_not_none_named(p), "True")
t("test_trait_identity", traits.test_trait_param(), "Alice,Whiskers,Alice,Whiskers")

# Note: Methods using f-strings with self.attr (describe, greet, to_string)
# are skipped due to pre-existing f-string compilation issue (not trait-related)


# ---- async_demo ----
suite("async_demo")
import asyncio

import async_demo

# Test basic async functions (no await asyncio.sleep)
coro = async_demo.simple_return()
t("simple_return returns coroutine", hasattr(coro, '__await__'), "True")
t("simple_return has send", hasattr(coro, 'send'), "True")
t("simple_return has close", hasattr(coro, 'close'), "True")
t("simple_return has throw", hasattr(coro, 'throw'), "True")

# Run simple async functions with asyncio.run
result = asyncio.run(async_demo.simple_return())
t("simple_return result", result, "42")

result = asyncio.run(async_demo.with_parameters(10, 20))
t("with_parameters(10,20)", result, "30")

result = asyncio.run(async_demo.compute_sum(10))
t("compute_sum(10)", result, "45")

result = asyncio.run(async_demo.sequential_operations())
t("sequential_operations", result, "30")

# Test async functions WITH await asyncio.sleep()
# These use the new yield-from semantics with mp_resume()
result = asyncio.run(async_demo.delayed_double(21))
t("delayed_double(21)", result, "42")

result = asyncio.run(async_demo.countdown_with_delay(5))
t("countdown_with_delay(5)", result, "0")


# ---- isinstance_demo ----
suite("isinstance_demo")
import isinstance_demo

# Simple type checking
c = isinstance_demo.Circle(5)
r = isinstance_demo.Rectangle(3, 4)

t("is_circle(circle)", isinstance_demo.is_circle(c), "True")
t("is_circle(rect)", isinstance_demo.is_circle(r), "False")
t("is_rectangle(rect)", isinstance_demo.is_rectangle(r), "True")
t("is_rectangle(circle)", isinstance_demo.is_rectangle(c), "False")

# Auto-narrowing: field access directly after isinstance (no manual annotation)
t("describe circle", isinstance_demo.describe_shape(c), "circle")
t("describe rect", isinstance_demo.describe_shape(r), "rectangle")

# Auto-narrowing: area calculation with direct field access
t("area circle r=5", isinstance_demo.get_area(c), "75")
t("area rect 3x4", isinstance_demo.get_area(r), "12")

# Auto-narrowing: MVU dataclass variant dispatch
inc = isinstance_demo.Increment(5)
sv = isinstance_demo.SetValue(42)
reset = isinstance_demo.Reset()

t("process Increment", isinstance_demo.process_msg(inc, 10), "15")
t("process SetValue", isinstance_demo.process_msg(sv, 10), "42")
t("process Reset", isinstance_demo.process_msg(reset, 10), "0")

# Negated isinstance
t("not_circle(rect)", isinstance_demo.is_not_circle(r), "True")
t("not_circle(circle)", isinstance_demo.is_not_circle(c), "False")

# elif chain
t("sides circle", isinstance_demo.shape_sides(c), "0")
t("sides rect", isinstance_demo.shape_sides(r), "4")

# ---- enum_demo ----
suite("enum_demo")
import enum_demo

t("Color_RED constant", enum_demo.Color_RED, "1")
t("Color_GREEN constant", enum_demo.Color_GREEN, "2")
t("Color_BLUE constant", enum_demo.Color_BLUE, "3")
t("Priority_LOW constant", enum_demo.Priority_LOW, "1")
t("Priority_MEDIUM constant", enum_demo.Priority_MEDIUM, "5")
t("Priority_HIGH constant", enum_demo.Priority_HIGH, "10")
t("Permission_READ constant", enum_demo.Permission_READ, "1")
t("Permission_WRITE constant", enum_demo.Permission_WRITE, "2")
t("Permission_EXECUTE constant", enum_demo.Permission_EXECUTE, "4")
t("Permission_ALL constant", enum_demo.Permission_ALL, "7")
t("get_color()", enum_demo.get_color(), "2")
t("check_color(3)", enum_demo.check_color(3), "True")
t("check_color(1)", enum_demo.check_color(1), "False")
t("total_priority()", enum_demo.total_priority(), "16")
t("is_high_priority(10)", enum_demo.is_high_priority(10), "True")
t("is_high_priority(1)", enum_demo.is_high_priority(1), "False")
t("has_write(3)", enum_demo.has_write(3), "True")
t("has_write(4)", enum_demo.has_write(4), "False")
t("default_permissions()", enum_demo.default_permissions(), "3")

suite("optional_narrowing")
import optional_narrowing as on

p1 = on.Point(10, 20)
p2 = on.Point(30, 40)
c1 = on.Container(99, p1)

# Pattern 1: if x is not None narrowing
t("is_not_none guard", on.get_x_or_default(p1, 0), "10")
t("is_not_none None", on.get_x_or_default(None, 42), "42")

# Pattern 2: early return guard narrowing
t("early return guard", on.get_y_with_guard(p1), "20")
t("early return None", on.get_y_with_guard(None), "-1")

# Pattern 3: else branch narrowing
t("else narrowing T", on.describe_point(p1), "10,20")
t("else narrowing F", on.describe_point(None), "no point")

# Pattern 4: multiple Optional params
t("multi opt both", on.add_points(p1, p2), "100")
t("multi opt a only", on.add_points(p1, None), "30")
t("multi opt none", on.add_points(None, p2), "0")

# Pattern 5: Optional container
t("opt container T", on.get_container_x(c1), "99")
t("opt container F", on.get_container_x(None), "0")

# Pattern 6: non-Optional baseline
t("direct access", on.get_x_direct(p1), "10")

# Full integration test
t("full test", on.test_optional_narrowing(), "10,42,20,-1,10,20,no point,100,30,0,99,0,10")

gc.collect()

# NOTE: LVGL test suites (lvgl_mvu_diff, lvgl_mvu_viewnode, lvgl_mvu_reconciler)
# are in tests/device/run_lvgl_tests.py — run separately with:
#   mpremote connect PORT run tests/device/run_lvgl_tests.py

# ---- typed_funcs ----
suite("typed_funcs")
import typed_funcs as tf

# TypeVar unbounded (identity passthrough)
t("identity(42)", tf.identity(42), "42")
t("identity(str)", tf.identity("hello"), "hello")

# TypeVar bounded to int
t("int_identity(5)", tf.int_identity(5), "5")
t("int_identity(0)", tf.int_identity(0), "0")
t("int_identity(-3)", tf.int_identity(-3), "-3")

# Literal erasure (int)
t("get_status(0)", tf.get_status(0), "10")
t("get_status(1)", tf.get_status(1), "11")
t("get_status(2)", tf.get_status(2), "12")

# Literal erasure (bool)
t("check_flag(T)", tf.check_flag(True), "True")
t("check_flag(F)", tf.check_flag(False), "False")

# Literal return type
t("fixed_offset", tf.fixed_offset(), "42")

# General (object) passthrough
t("passthrough(77)", tf.passthrough(77), "77")
t("passthrough(str)", tf.passthrough("abc"), "abc")

# Mixed typed and general params
t("add_or_zero T", tf.add_or_zero(6, True), "12")
t("add_or_zero F", tf.add_or_zero(6, False), "0")
t("add_or_zero 0", tf.add_or_zero(6, 0), "0")
t("add_or_zero 1", tf.add_or_zero(6, 1), "12")

# Full integration test
t("test_typed_funcs", tf.test_typed_funcs(), "42,10,5,11,True,42,77,12,0")

# TypeVar no-leak: function after TypeVar functions uses int correctly
t("after_typevar(5)", tf.after_typevar(5), "10")
t("after_typevar(0)", tf.after_typevar(0), "0")
t("after_typevar(-3)", tf.after_typevar(-3), "-6")

# GenericBox class with GENERAL (object) field
box1 = tf.GenericBox(99, "num")
t("GenericBox get_value", box1.get_value(), "99")
t("GenericBox get_label", box1.get_label(), "num")
box2 = tf.GenericBox("hello", "str")
t("GenericBox str val", box2.get_value(), "hello")
t("GenericBox str lbl", box2.get_label(), "str")
gc.collect()
# -- diff_children: no changes --
ch_a = (Widget(LABEL, "", (ScalarAttr(1, "x"),), (), ()),)
ch_b = (Widget(LABEL, "", (ScalarAttr(1, "x"),), (), ()),)
cc = diff_children(ch_a, ch_b)
t("children no change", len(cc), "0")

# -- diff_children: child updated --
ch_c = (Widget(LABEL, "", (ScalarAttr(1, "y"),), (), ()),)
cc2 = diff_children(ch_a, ch_c)
t("children updated len", len(cc2), "1")
t("children updated kind", cc2[0].kind, "update")

# -- diff_children: child inserted --
ch_d = (Widget(LABEL, "", (), (), ()), Widget(BUTTON, "", (), (), ()))
cc3 = diff_children(ch_a, ch_d)
# first child reusable (same type LABEL), second is insert
has_insert = False
for c in cc3:
    if c.kind == "insert":
        has_insert = True
t("children has insert", has_insert, "True")

# -- diff_children: child removed --
cc4 = diff_children(ch_d, ch_a)
has_remove = False
for c in cc4:
    if c.kind == "remove":
        has_remove = True
t("children has remove", has_remove, "True")

# -- diff_children: child replaced (type mismatch) --
ch_e = (Widget(BUTTON, "", (), (), ()),)
cc5 = diff_children(ch_a, ch_e)
t("children replace len", len(cc5), "1")
t("children replace kind", cc5[0].kind, "replace")

# -- diff_widgets: identical widgets --
w_prev = Widget(LABEL, "", (ScalarAttr(1, 10),), (), ())
w_next = Widget(LABEL, "", (ScalarAttr(1, 10),), (), ())
d1 = diff_widgets(w_prev, w_next)
t("diff identical empty", d1.is_empty(), "True")
t("diff identical scalars", len(d1.scalar_changes), "0")
t("diff identical children", len(d1.child_changes), "0")
t("diff identical events", d1.event_changes, "False")

# -- diff_widgets: scalar change --
w_next2 = Widget(LABEL, "", (ScalarAttr(1, 99),), (), ())
d2 = diff_widgets(w_prev, w_next2)
t("diff scalar not empty", d2.is_empty(), "False")
t("diff scalar changes", len(d2.scalar_changes), "1")

# -- diff_widgets: child change --
w_prev3 = Widget(CONTAINER, "", (), (Widget(LABEL, "", (), (), ()),), ())
w_next3 = Widget(CONTAINER, "", (), (Widget(LABEL, "", (ScalarAttr(1, 5),), (), ()),), ())
d3 = diff_widgets(w_prev3, w_next3)
t("diff child not empty", d3.is_empty(), "False")
t("diff child changes", len(d3.child_changes), "1")

# -- diff_widgets: event change --
w_prev4 = Widget(BUTTON, "", (), (), ((1, "click"),))
w_next4 = Widget(BUTTON, "", (), (), ((1, "tap"),))
d4 = diff_widgets(w_prev4, w_next4)
t("diff event not empty", d4.is_empty(), "False")
t("diff event flag", d4.event_changes, "True")

# -- diff_widgets: event equal (identity vs equality fix) --
w_prev5 = Widget(BUTTON, "", (), (), ((1, "click"), (2, "hold")))
w_next5 = Widget(BUTTON, "", (), (), ((1, "click"), (2, "hold")))
d5 = diff_widgets(w_prev5, w_next5)
t("diff event eq empty", d5.is_empty(), "True")
t("diff event eq flag", d5.event_changes, "False")

# -- diff_widgets: prev is None (Optional narrowing path) --
w_new = Widget(LABEL, "", (ScalarAttr(1, "hi"), ScalarAttr(2, 42)), (Widget(BUTTON, "", (), (), ()),), ())
d6 = diff_widgets(None, w_new)
t("diff None prev not empty", d6.is_empty(), "False")
t("diff None scalar adds", len(d6.scalar_changes), "2")
t("diff None child inserts", len(d6.child_changes), "1")
t("diff None event flag", d6.event_changes, "False")

# -- diff_widgets: prev None with events --
w_new2 = Widget(BUTTON, "", (), (), ((1, "click"),))
d7 = diff_widgets(None, w_new2)
t("diff None events flag", d7.event_changes, "True")

# ---- lvgl_mvu_viewnode ----
suite("lvgl_mvu_viewnode")
# ViewNode tests - testing without actual LVGL (mocked lv_obj)

ViewNode = lvgl_mvu.viewnode.ViewNode
AttrRegistry = lvgl_mvu.attrs.AttrRegistry
AttrChange = lvgl_mvu.diff.AttrChange
WidgetDiff = lvgl_mvu.diff.WidgetDiff
CHANGE_ADDED = lvgl_mvu.diff.CHANGE_ADDED
CHANGE_UPDATED = lvgl_mvu.diff.CHANGE_UPDATED
CHANGE_REMOVED = lvgl_mvu.diff.CHANGE_REMOVED

# Mock LVGL object - just a dict for testing
class MockLvObj:
    def __init__(self, name):
        self.name = name
        self.attrs = {}

# Create an empty registry for testing
test_registry = AttrRegistry()
# Test ViewNode creation
mock_lv = MockLvObj("test_label")
w = Widget(LABEL, "", (ScalarAttr(1, "hello"),), (), ())
node = ViewNode(mock_lv, w, test_registry)
t("viewnode lv_obj", node.lv_obj.name, "test_label")
t("viewnode widget", node.widget.key, str(LABEL))
t("viewnode children", len(node.children), "0")
t("viewnode handlers", len(node.handlers), "0")
t("viewnode not disposed", node.is_disposed(), "False")

# Test add_child / get_child
child_lv = MockLvObj("child_button")
child_w = Widget(BUTTON, "", (), (), ())
child_node = ViewNode(child_lv, child_w, test_registry)
node.add_child(child_node)
t("viewnode add_child", len(node.children), "1")
t("viewnode get_child", node.get_child(0).lv_obj.name, "child_button")
t("viewnode get_child_none", node.get_child(5), "None")

# Test remove_child
node2 = ViewNode(MockLvObj("p"), w, test_registry)
child_node2 = ViewNode(MockLvObj("c"), child_w, test_registry)
node2.add_child(child_node2)
removed = node2.remove_child(0)
t("viewnode remove_child", removed.lv_obj.name, "c")
t("viewnode after remove", len(node2.children), "0")

# Test handler registration
node3 = ViewNode(MockLvObj("btn"), Widget(BUTTON, "", (), (), ()), test_registry)
node3.register_handler(1, "handler_fn")
t("viewnode register_handler", node3.handlers[1], "handler_fn")
h = node3.unregister_handler(1)
t("viewnode unregister", h, "handler_fn")
t("viewnode after unreg", len(node3.handlers), "0")

# Test clear_handlers
node4 = ViewNode(MockLvObj("btn2"), Widget(BUTTON, "", (), (), ()), test_registry)
node4.register_handler(1, "h1")
node4.register_handler(2, "h2")
old = node4.clear_handlers()
t("viewnode clear len", len(old), "2")
t("viewnode after clear", len(node4.handlers), "0")

# Test update_widget
node5 = ViewNode(MockLvObj("lbl"), Widget(LABEL, "", (ScalarAttr(1, "old"),), (), ()), test_registry)
new_w = Widget(LABEL, "", (ScalarAttr(1, "new"),), (), ())
node5.update_widget(new_w)
t("viewnode update_widget", node5.widget.scalar_attrs[0].value, "new")

# Test dispose
disposed_list = []
def track_delete(obj):
    disposed_list.append(obj.name)

root = ViewNode(MockLvObj("root"), Widget(CONTAINER, "", (), (), ()), test_registry)
c1 = ViewNode(MockLvObj("c1"), Widget(LABEL, "", (), (), ()), test_registry)
c2 = ViewNode(MockLvObj("c2"), Widget(BUTTON, "", (), (), ()), test_registry)
root.add_child(c1)
root.add_child(c2)
root.dispose(track_delete)
t("viewnode dispose root", root.is_disposed(), "True")
t("viewnode dispose c1", c1.is_disposed(), "True")
t("viewnode dispose c2", c2.is_disposed(), "True")
t("viewnode dispose order", "c1" in str(disposed_list), "True")
t("viewnode dispose all", len(disposed_list), "3")

gc.collect()

# ---- lvgl_mvu_reconciler ----
suite("lvgl_mvu_reconciler")

Reconciler = lvgl_mvu.reconciler.Reconciler

# Track created objects for testing
created_objs = []
deleted_objs = []

def make_label(parent):
    obj = MockLvObj("label_" + str(len(created_objs)))
    created_objs.append(obj)
    return obj

def make_button(parent):
    obj = MockLvObj("button_" + str(len(created_objs)))
    created_objs.append(obj)
    return obj

def make_container(parent):
    obj = MockLvObj("container_" + str(len(created_objs)))
    created_objs.append(obj)
    return obj

def delete_obj(obj):
    deleted_objs.append(obj.name)

# Test Reconciler creation and factory registration
rec = Reconciler(test_registry)
rec.register_factory(LABEL, make_label)
rec.register_factory(BUTTON, make_button)
rec.register_factory(CONTAINER, make_container)
rec.set_delete_fn(delete_obj)
t("reconciler created", rec is not None, "True")

# Test reconcile: create new node
created_objs.clear()
w1 = Widget(LABEL, "", (ScalarAttr(1, "test"),), (), ())
n1 = rec.reconcile(None, w1, None)
t("reconcile new", n1 is not None, "True")
t("reconcile lv_obj", "label" in n1.lv_obj.name, "True")
t("reconcile widget", n1.widget.key, str(LABEL))

# Test reconcile: update existing node (same type)
w2 = Widget(LABEL, "", (ScalarAttr(1, "updated"),), (), ())
n2 = rec.reconcile(n1, w2, None)
t("reconcile update same", n2 is n1, "True")  # Should reuse same node
t("reconcile widget updated", n2.widget.scalar_attrs[0].value, "updated")

# Test reconcile: replace node (different type)
created_objs.clear()
deleted_objs.clear()
old_node = ViewNode(MockLvObj("old_label"), Widget(LABEL, "", (), (), ()), test_registry)
w3 = Widget(BUTTON, "", (), (), ())
n3 = rec.reconcile(old_node, w3, None)
t("reconcile replace", "button" in n3.lv_obj.name, "True")
t("reconcile old disposed", old_node.is_disposed(), "True")

# Test reconcile: with children
created_objs.clear()
w_parent = Widget(CONTAINER, "", (), (Widget(LABEL, "", (), (), ()), Widget(BUTTON, "", (), (), ())), ())
n_parent = rec.reconcile(None, w_parent, None)
t("reconcile children", len(n_parent.children), "2")
t("reconcile child0", "label" in n_parent.children[0].lv_obj.name, "True")
t("reconcile child1", "button" in n_parent.children[1].lv_obj.name, "True")

# Test dispose_tree
created_objs.clear()
deleted_objs.clear()
w_tree = Widget(CONTAINER, "", (), (Widget(LABEL, "", (), (), ()),), ())
n_tree = rec.reconcile(None, w_tree, None)
rec.dispose_tree(n_tree)
t("dispose_tree root", n_tree.is_disposed(), "True")
t("dispose_tree count", len(deleted_objs), "2")  # container + label

gc.collect()

# ---- lvgl_mvu_program ----
suite("lvgl_mvu_program")

Effect = lvgl_mvu.program.Effect
Cmd = lvgl_mvu.program.Cmd
SubDef = lvgl_mvu.program.SubDef
Sub = lvgl_mvu.program.Sub
Program = lvgl_mvu.program.Program
EFFECT_MSG = lvgl_mvu.program.EFFECT_MSG
EFFECT_FN = lvgl_mvu.program.EFFECT_FN
SUB_TIMER = lvgl_mvu.program.SUB_TIMER

# -- Effect --
eff = Effect(EFFECT_MSG, 42)
t("effect kind", eff.kind, str(EFFECT_MSG))
t("effect data", eff.data, "42")

eff_fn = Effect(EFFECT_FN, "my_fn")
t("effect fn kind", eff_fn.kind, str(EFFECT_FN))
t("effect fn data", eff_fn.data, "my_fn")

# -- Cmd.none --
cmd_none = Cmd.none()
t("cmd none effects", len(cmd_none.effects), "0")

# -- Cmd.of_msg --
cmd_msg = Cmd.of_msg("hello")
t("cmd of_msg len", len(cmd_msg.effects), "1")
t("cmd of_msg kind", cmd_msg.effects[0].kind, str(EFFECT_MSG))
t("cmd of_msg data", cmd_msg.effects[0].data, "hello")

# -- Cmd.batch --
cmd_a = Cmd.of_msg("a")
cmd_b = Cmd.of_msg("b")
cmd_batch = Cmd.batch([cmd_a, cmd_b])
t("cmd batch len", len(cmd_batch.effects), "2")
t("cmd batch first", cmd_batch.effects[0].data, "a")
t("cmd batch second", cmd_batch.effects[1].data, "b")

# -- Cmd.batch empty --
cmd_empty_batch = Cmd.batch([])
t("cmd batch empty", len(cmd_empty_batch.effects), "0")

# -- Cmd.of_effect --
cmd_eff = Cmd.of_effect("fn_placeholder")
t("cmd of_effect len", len(cmd_eff.effects), "1")
t("cmd of_effect kind", cmd_eff.effects[0].kind, str(EFFECT_FN))

# -- SubDef --
sd = SubDef(SUB_TIMER, "timer_100", (100, "tick"))
t("subdef kind", sd.kind, str(SUB_TIMER))
t("subdef key", sd.key, "timer_100")
t("subdef data", sd.data[0], "100")

# -- Sub.none --
sub_none = Sub.none()
t("sub none defs", len(sub_none.defs), "0")

# -- Sub.timer --
sub_timer = Sub.timer(500, "tick_msg")
t("sub timer len", len(sub_timer.defs), "1")
t("sub timer kind", sub_timer.defs[0].kind, str(SUB_TIMER))
t("sub timer key", sub_timer.defs[0].key, "timer_500")
t("sub timer interval", sub_timer.defs[0].data[0], "500")
t("sub timer msg", sub_timer.defs[0].data[1], "tick_msg")

# -- Sub.batch --
sub_a = Sub.timer(100, "a")
sub_b = Sub.timer(200, "b")
sub_batch = Sub.batch([sub_a, sub_b])
t("sub batch len", len(sub_batch.defs), "2")
t("sub batch first key", sub_batch.defs[0].key, "timer_100")
t("sub batch second key", sub_batch.defs[1].key, "timer_200")

# -- Sub.batch empty --
sub_empty_batch = Sub.batch([])
t("sub batch empty", len(sub_empty_batch.defs), "0")

# -- Program --
def _test_init():
    return (0, Cmd.none())

def _test_update(msg, model):
    return (model + 1, Cmd.none())

def _test_view(model):
    return Widget(LABEL, "", (ScalarAttr(1, str(model)),), (), ())

prog = Program(_test_init, _test_update, _test_view)
t("program init_fn", prog.init_fn is not None, "True")
t("program update_fn", prog.update_fn is not None, "True")
t("program view_fn", prog.view_fn is not None, "True")
t("program subscribe_fn", prog.subscribe_fn, "None")

# -- Program with subscribe --
def _test_subscribe(model):
    return Sub.none()

prog_sub = Program(_test_init, _test_update, _test_view, _test_subscribe)
t("program with sub", prog_sub.subscribe_fn is not None, "True")

gc.collect()

# ---- lvgl_mvu_app ----
suite("lvgl_mvu_app")

App = lvgl_mvu.app.App

# -- Helper functions for testing --
def counter_init():
    return (0, Cmd.none())

def counter_update(msg, model):
    if msg == "inc":
        return (model + 1, Cmd.none())
    if msg == "dec":
        return (model - 1, Cmd.none())
    if msg == "set10":
        return (10, Cmd.none())
    return (model, Cmd.none())

def counter_view(model):
    return Widget(LABEL, "", (ScalarAttr(1, str(model)),), (), ())

counter_prog = Program(counter_init, counter_update, counter_view)

# -- App creation --
app = App(counter_prog, rec)
t("app model init", app.model, "0")
t("app not disposed", app.is_disposed(), "False")
t("app queue empty", app.queue_length(), "0")

# -- App tick (first render) --
changed = app.tick()
t("app first tick", app.root_node is not None, "True")

# -- App dispatch + tick --
app.dispatch("inc")
t("app queue after dispatch", app.queue_length(), "1")
changed = app.tick()
t("app tick changed", changed, "True")
t("app model after inc", app.model, "1")
t("app queue after tick", app.queue_length(), "0")

# -- Multiple dispatches --
app.dispatch("inc")
app.dispatch("inc")
app.dispatch("inc")
changed = app.tick()
t("app model after 3x inc", app.model, "4")

# -- Decrement --
app.dispatch("dec")
app.tick()
t("app model after dec", app.model, "3")

# -- No change tick --
changed = app.tick()
t("app no change tick", changed, "False")

# -- Dispose --
app.dispose()
t("app disposed", app.is_disposed(), "True")
t("app root after dispose", app.root_node, "None")

# -- Dispatch after dispose (should be ignored) --
app.dispatch("inc")
t("app queue after dispose", app.queue_length(), "0")

gc.collect()

# -- App with Cmd.of_msg (cascading messages) --
def cascade_update(msg, model):
    if msg == "start":
        return (model + 1, Cmd.of_msg("chain"))
    if msg == "chain":
        return (model + 10, Cmd.none())
    return (model, Cmd.none())

cascade_prog = Program(counter_init, cascade_update, counter_view)
app2 = App(cascade_prog, rec)
app2.dispatch("start")
app2.tick()
t("app cascade model", app2.model, "11")
app2.dispose()

gc.collect()

# -- App with subscriptions --
_timer_created = [0]
_timer_torn_down = [0]

def mock_timer_factory(interval_ms, app_ref, msg):
    _timer_created[0] += 1
    def teardown():
        _timer_torn_down[0] += 1
    return teardown

def sub_counter_subscribe(model):
    if model > 0:
        return Sub.timer(100, "tick")
    return Sub.none()

sub_prog = Program(counter_init, counter_update, counter_view, sub_counter_subscribe)
app3 = App(sub_prog, rec)
app3.set_timer_factory(mock_timer_factory)

# model=0, subscribe returns Sub.none, no timer created
t("app sub no timer", _timer_created[0], "0")

# Dispatch inc -> model=1 -> subscribe returns timer
app3.dispatch("inc")
app3.tick()
t("app sub timer created", _timer_created[0], "1")

# Dispose should tear down
app3.dispose()
t("app sub timer torn", _timer_torn_down[0], "1")

gc.collect()

# ---- summary ----
gc.collect()
print("@D:" + str(_total) + "|" + str(_passed) + "|" + str(_failed))
if _failed:
    print("FAILED: " + str(_failed) + " tests")
else:
    print("ALL " + str(_total) + " TESTS PASSED")
