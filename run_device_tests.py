"""Device test runner for mypyc-micropython. Runs directly on MicroPython.

Usage: mpremote connect /dev/cu.usbmodem101 run run_device_tests.py
"""

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

# ---- summary ----
gc.collect()
print("@D:" + str(_total) + "|" + str(_passed) + "|" + str(_failed))
if _failed:
    print("FAILED: " + str(_failed) + " tests")
else:
    print("ALL " + str(_total) + " TESTS PASSED")
