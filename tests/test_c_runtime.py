from pathlib import Path

import pytest

pytestmark = pytest.mark.c_runtime


def test_c_sum_range_returns_correct_sum(compile_and_run):
    source = """
def sum_range(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_sum_range(mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"


def test_c_build_squares_returns_expected_list_values(compile_and_run):
    source = """
def build_squares(n: int) -> list:
    result: list = []
    for i in range(n):
        result.append(i * i)
    return result
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_build_squares(mp_obj_new_int(4));
    mp_int_t n = mp_obj_get_int(mp_obj_len(result));
    printf("%ld\\n", (long)n);
    for (mp_int_t i = 0; i < n; i++) {
        mp_obj_t item = mp_obj_subscr(result, mp_obj_new_int(i), MP_OBJ_SENTINEL);
        printf("%ld\\n", (long)mp_obj_get_int(item));
    }
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["4", "0", "1", "4", "9"]


def test_c_sum_list_returns_correct_sum(compile_and_run):
    source = """
def sum_list(lst: list) -> int:
    total: int = 0
    for i in range(len(lst)):
        total += lst[i]
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
        mp_obj_new_int(4),
        mp_obj_new_int(5),
    };
    mp_obj_t list = mp_obj_new_list(5, items);
    mp_obj_t result = test_sum_list(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "15"


def test_c_find_first_negative_returns_index(compile_and_run):
    source = """
def find_first_negative(lst: list) -> int:
    for i in range(len(lst)):
        if lst[i] < 0:
            return i
    return -1
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(3),
        mp_obj_new_int(1),
        mp_obj_new_int(-2),
        mp_obj_new_int(5),
    };
    mp_obj_t list = mp_obj_new_list(4, items);
    mp_obj_t result = test_find_first_negative(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "2"


def test_c_find_first_negative_returns_minus_one_when_absent(compile_and_run):
    source = """
def find_first_negative(lst: list) -> int:
    for i in range(len(lst)):
        if lst[i] < 0:
            return i
    return -1
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
    };
    mp_obj_t list = mp_obj_new_list(3, items);
    mp_obj_t result = test_find_first_negative(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "-1"


def test_c_skip_zeros_returns_correct_sum(compile_and_run):
    source = """
def skip_zeros(n: int) -> int:
    total: int = 0
    for i in range(n):
        if i == 0:
            continue
        total += i
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_skip_zeros(mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"


def test_c_count_until_ten_stops_early(compile_and_run):
    source = """
def count_until_ten(n: int) -> int:
    total: int = 0
    for i in range(n):
        if i == 10:
            break
        total += 1
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_count_until_ten(mp_obj_new_int(20));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"


def test_c_matrix_sum_returns_expected_total(compile_and_run):
    source = """
def matrix_sum(rows: int, cols: int) -> int:
    total: int = 0
    for i in range(rows):
        for j in range(cols):
            total += i + j
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_matrix_sum(mp_obj_new_int(3), mp_obj_new_int(3));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "18"


def test_c_reverse_sum_counts_down_with_negative_step(compile_and_run):
    source = """
def reverse_sum(n: int) -> int:
    total: int = 0
    for i in range(n, 0, -1):
        total += i
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_reverse_sum(mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "15"


def test_c_factorial_example_returns_120(compile_and_run):
    source = (Path(__file__).parents[1] / "examples" / "factorial.py").read_text()
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = factorial_factorial(mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "factorial", test_main_c)
    assert stdout.strip() == "120"


def test_c_list_pop_last_and_pop_at_return_expected_values(compile_and_run):
    source = """
def pop_last(lst: list):
    return lst.pop()

def pop_at(lst: list, i: int):
    return lst.pop(i)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items1[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
    };
    mp_obj_t list1 = mp_obj_new_list(3, items1);
    mp_obj_t popped_last = test_pop_last(list1);
    printf("%ld\\n", (long)mp_obj_get_int(popped_last));

    mp_obj_t items2[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
    };
    mp_obj_t list2 = mp_obj_new_list(3, items2);
    mp_obj_t popped_at = test_pop_at(list2, mp_obj_new_int(0));
    printf("%ld\\n", (long)mp_obj_get_int(popped_at));

    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["3", "1"]


def test_c_float_runtime_support_executes_generated_float_code(compile_and_run):
    source = """
def multiply(a: float, b: float) -> float:
    return a * b
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_multiply(mp_obj_new_float(3.14), mp_obj_new_float(2.0));
    printf("%.2f\\n", mp_obj_float_get(result));
    return 0;
}
"""

    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "6.28"


def test_c_pop_all_elements_empties_list(compile_and_run):
    source = """
def pop_all(lst: list) -> int:
    total: int = 0
    n: int = len(lst)
    for i in range(n):
        total += lst.pop()
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(10),
        mp_obj_new_int(20),
        mp_obj_new_int(30),
    };
    mp_obj_t list = mp_obj_new_list(3, items);
    mp_obj_t result = test_pop_all(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_len(list)));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["60", "0"]


def test_c_pop_at_index_removes_correct_element(compile_and_run):
    source = """
def pop_middle(lst: list) -> int:
    return lst.pop(1)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(100),
        mp_obj_new_int(200),
        mp_obj_new_int(300),
        mp_obj_new_int(400),
    };
    mp_obj_t list = mp_obj_new_list(4, items);
    mp_obj_t popped = test_pop_middle(list);
    printf("%ld\\n", (long)mp_obj_get_int(popped));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_len(list)));
    // remaining: [100, 300, 400]
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(list, mp_obj_new_int(0), MP_OBJ_SENTINEL)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(list, mp_obj_new_int(1), MP_OBJ_SENTINEL)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(list, mp_obj_new_int(2), MP_OBJ_SENTINEL)));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["200", "3", "100", "300", "400"]


def test_c_pop_and_append_interleaved(compile_and_run):
    source = """
def rotate_left(lst: list) -> int:
    val: int = lst.pop(0)
    lst.append(val)
    return val
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
    };
    mp_obj_t list = mp_obj_new_list(3, items);

    printf("%ld\\n", (long)mp_obj_get_int(test_rotate_left(list)));
    // after first rotate: [2, 3, 1]
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(list, mp_obj_new_int(0), MP_OBJ_SENTINEL)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(list, mp_obj_new_int(1), MP_OBJ_SENTINEL)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(list, mp_obj_new_int(2), MP_OBJ_SENTINEL)));

    printf("%ld\\n", (long)mp_obj_get_int(test_rotate_left(list)));
    // after second rotate: [3, 1, 2]
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(list, mp_obj_new_int(0), MP_OBJ_SENTINEL)));

    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["1", "2", "3", "1", "2", "3"]


def test_c_tuple_literal_returns_expected_values(compile_and_run):
    source = """
def make_point() -> tuple:
    return (10, 20)

def get_first(t: tuple) -> int:
    return t[0]

def get_last(t: tuple) -> int:
    return t[-1]
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t point = test_make_point();
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_len(point)));
    printf("%ld\\n", (long)mp_obj_get_int(test_get_first(point)));
    printf("%ld\\n", (long)mp_obj_get_int(test_get_last(point)));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["2", "10", "20"]


def test_c_tuple_iteration_sums_elements(compile_and_run):
    source = """
def sum_tuple(t: tuple) -> int:
    total: int = 0
    for x in t:
        total += x
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
        mp_obj_new_int(4),
    };
    mp_obj_t tup = mp_obj_new_tuple(4, items);
    mp_obj_t result = test_sum_tuple(tup);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"


def test_c_tuple_contains_finds_element(compile_and_run):
    source = """
def has_value(t: tuple, val: int) -> bool:
    return val in t
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(10),
        mp_obj_new_int(20),
        mp_obj_new_int(30),
    };
    mp_obj_t tup = mp_obj_new_tuple(3, items);
    mp_obj_t found = test_has_value(tup, mp_obj_new_int(20));
    mp_obj_t not_found = test_has_value(tup, mp_obj_new_int(99));
    printf("%d\\n", found == mp_const_true ? 1 : 0);
    printf("%d\\n", not_found == mp_const_false ? 1 : 0);
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["1", "1"]


def test_c_tuple_unpack_extracts_values(compile_and_run):
    source = """
def unpack_pair(t: tuple) -> int:
    a: int
    b: int
    a, b = t
    return a + b
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(7),
        mp_obj_new_int(8),
    };
    mp_obj_t tup = mp_obj_new_tuple(2, items);
    mp_obj_t result = test_unpack_pair(tup);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "15"


def test_c_tuple_concat_joins_tuples(compile_and_run):
    source = """
def concat(t1: tuple, t2: tuple) -> tuple:
    return t1 + t2
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items1[] = { mp_obj_new_int(1), mp_obj_new_int(2) };
    mp_obj_t items2[] = { mp_obj_new_int(3), mp_obj_new_int(4) };
    mp_obj_t t1 = mp_obj_new_tuple(2, items1);
    mp_obj_t t2 = mp_obj_new_tuple(2, items2);
    mp_obj_t result = test_concat(t1, t2);
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_len(result)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(result, mp_obj_new_int(0), MP_OBJ_SENTINEL)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(result, mp_obj_new_int(3), MP_OBJ_SENTINEL)));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["4", "1", "4"]


def test_c_tuple_repeat_multiplies_tuple(compile_and_run):
    source = """
def repeat(t: tuple, n: int) -> tuple:
    return t * n
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = { mp_obj_new_int(1), mp_obj_new_int(2) };
    mp_obj_t t = mp_obj_new_tuple(2, items);
    mp_obj_t result = test_repeat(t, mp_obj_new_int(3));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_len(result)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(result, mp_obj_new_int(0), MP_OBJ_SENTINEL)));
    printf("%ld\\n", (long)mp_obj_get_int(mp_obj_subscr(result, mp_obj_new_int(5), MP_OBJ_SENTINEL)));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["6", "1", "2"]


def test_c_set_literal_returns_unique_elements(compile_and_run):
    source = """
def make_set() -> set:
    return {1, 2, 3}

def set_len(s: set) -> int:
    return len(s)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t s = test_make_set();
    mp_obj_t length = test_set_len(s);
    printf("%ld\\n", (long)mp_obj_get_int(length));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "3"


def test_c_set_add_inserts_element(compile_and_run):
    source = """
def add_values(s: set) -> int:
    s.add(10)
    s.add(20)
    s.add(10)
    return len(s)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t s = mp_obj_new_set(0, NULL);
    mp_obj_t result = test_add_values(s);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "2"


def test_c_set_contains_finds_element(compile_and_run):
    source = """
def has_value(s: set, val: int) -> bool:
    return val in s
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(5),
        mp_obj_new_int(10),
        mp_obj_new_int(15),
    };
    mp_obj_t s = mp_obj_new_set(3, items);
    mp_obj_t found = test_has_value(s, mp_obj_new_int(10));
    mp_obj_t not_found = test_has_value(s, mp_obj_new_int(99));
    printf("%d\\n", found == mp_const_true ? 1 : 0);
    printf("%d\\n", not_found == mp_const_false ? 1 : 0);
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["1", "1"]


def test_c_set_iteration_sums_elements(compile_and_run):
    source = """
def sum_set(s: set) -> int:
    total: int = 0
    for x in s:
        total += x
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
    };
    mp_obj_t s = mp_obj_new_set(3, items);
    mp_obj_t result = test_sum_set(s);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "6"


def test_c_set_build_filters_duplicates(compile_and_run):
    source = """
def count_unique(n: int) -> int:
    s: set = set()
    for i in range(n):
        s.add(i % 5)
    return len(s)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_count_unique(mp_obj_new_int(20));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "5"


def test_c_rtuple_create_and_access(compile_and_run):
    source = """
def make_point() -> tuple[int, int]:
    point: tuple[int, int] = (10, 20)
    return point
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_make_point();
    mp_obj_t x = mp_obj_subscr(result, mp_obj_new_int(0), MP_OBJ_SENTINEL);
    mp_obj_t y = mp_obj_subscr(result, mp_obj_new_int(1), MP_OBJ_SENTINEL);
    printf("%ld %ld\\n", (long)mp_obj_get_int(x), (long)mp_obj_get_int(y));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10 20"


def test_c_rtuple_field_access_optimization(compile_and_run):
    source = """
def get_x_plus_y() -> int:
    point: tuple[int, int] = (15, 25)
    return point[0] + point[1]
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_get_x_plus_y();
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "40"


def test_c_rtuple_with_variables(compile_and_run):
    source = """
def make_pair(a: int, b: int) -> tuple[int, int]:
    pair: tuple[int, int] = (a, b)
    return pair
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_make_pair(mp_obj_new_int(100), mp_obj_new_int(200));
    mp_obj_t x = mp_obj_subscr(result, mp_obj_new_int(0), MP_OBJ_SENTINEL);
    mp_obj_t y = mp_obj_subscr(result, mp_obj_new_int(1), MP_OBJ_SENTINEL);
    printf("%ld %ld\\n", (long)mp_obj_get_int(x), (long)mp_obj_get_int(y));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "100 200"


def test_c_rtuple_mixed_types(compile_and_run):
    source = """
def make_record() -> tuple[int, bool]:
    rec: tuple[int, bool] = (42, True)
    return rec
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_make_record();
    mp_obj_t val = mp_obj_subscr(result, mp_obj_new_int(0), MP_OBJ_SENTINEL);
    mp_obj_t flag = mp_obj_subscr(result, mp_obj_new_int(1), MP_OBJ_SENTINEL);
    printf("%ld %d\\n", (long)mp_obj_get_int(val), mp_obj_is_true(flag));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "42 1"


def test_c_rtuple_three_elements(compile_and_run):
    source = """
def make_triple() -> tuple[int, int, int]:
    t: tuple[int, int, int] = (10, 20, 30)
    return t
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_make_triple();
    mp_obj_t a = mp_obj_subscr(result, mp_obj_new_int(0), MP_OBJ_SENTINEL);
    mp_obj_t b = mp_obj_subscr(result, mp_obj_new_int(1), MP_OBJ_SENTINEL);
    mp_obj_t c = mp_obj_subscr(result, mp_obj_new_int(2), MP_OBJ_SENTINEL);
    printf("%ld %ld %ld\\n", (long)mp_obj_get_int(a), (long)mp_obj_get_int(b), (long)mp_obj_get_int(c));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10 20 30"


def test_c_rtuple_three_element_sum(compile_and_run):
    source = """
def sum_triple() -> int:
    t: tuple[int, int, int] = (100, 200, 300)
    return t[0] + t[1] + t[2]
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_sum_triple();
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "600"


def test_c_list_optimized_index(compile_and_run):
    source = """
def sum_first_three(lst: list) -> int:
    return lst[0] + lst[1] + lst[2]
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(10),
        mp_obj_new_int(20),
        mp_obj_new_int(30),
    };
    mp_obj_t list = mp_obj_new_list(3, items);
    mp_obj_t result = test_sum_first_three(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "60"


def test_c_list_optimized_variable_index(compile_and_run):
    source = """
def get_at(lst: list, i: int) -> int:
    return lst[i]
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(100),
        mp_obj_new_int(200),
        mp_obj_new_int(300),
    };
    mp_obj_t list = mp_obj_new_list(3, items);
    mp_obj_t result = test_get_at(list, mp_obj_new_int(1));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "200"


def test_c_list_optimized_negative_index(compile_and_run):
    source = """
def get_last(lst: list) -> int:
    return lst[-1]
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(10),
        mp_obj_new_int(20),
        mp_obj_new_int(30),
    };
    mp_obj_t list = mp_obj_new_list(3, items);
    mp_obj_t result = test_get_last(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "30"


def test_c_list_optimized_len(compile_and_run):
    source = """
def list_length(lst: list) -> int:
    return len(lst)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
        mp_obj_new_int(4),
        mp_obj_new_int(5),
    };
    mp_obj_t list = mp_obj_new_list(5, items);
    mp_obj_t result = test_list_length(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "5"


def test_c_list_optimized_sum_loop(compile_and_run):
    source = """
def sum_list_opt(lst: list) -> int:
    total: int = 0
    n: int = len(lst)
    i: int = 0
    while i < n:
        total += lst[i]
        i += 1
    return total
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
        mp_obj_new_int(4),
        mp_obj_new_int(5),
    };
    mp_obj_t list = mp_obj_new_list(5, items);
    mp_obj_t result = test_sum_list_opt(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "15"


def test_c_bool_builtin_truthy(compile_and_run):
    source = """
def check_truthy(x: int) -> bool:
    return bool(x)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result1 = test_check_truthy(mp_obj_new_int(42));
    mp_obj_t result2 = test_check_truthy(mp_obj_new_int(0));
    mp_obj_t result3 = test_check_truthy(mp_obj_new_int(-1));
    printf("%d\\n", result1 == mp_const_true ? 1 : 0);
    printf("%d\\n", result2 == mp_const_false ? 1 : 0);
    printf("%d\\n", result3 == mp_const_true ? 1 : 0);
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["1", "1", "1"]


def test_c_bool_builtin_list(compile_and_run):
    source = """
def check_bool_int(x: int) -> bool:
    return bool(x)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t zero = test_check_bool_int(mp_obj_new_int(0));
    mp_obj_t nonzero = test_check_bool_int(mp_obj_new_int(5));
    mp_obj_t negative = test_check_bool_int(mp_obj_new_int(-3));
    printf("%d\\n", mp_obj_is_true(zero) ? 1 : 0);
    printf("%d\\n", mp_obj_is_true(nonzero) ? 1 : 0);
    printf("%d\\n", mp_obj_is_true(negative) ? 1 : 0);
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["0", "1", "1"]


def test_c_min_two_args(compile_and_run):
    source = """
def get_smaller(a: int, b: int) -> int:
    return min(a, b)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t r1 = test_get_smaller(mp_obj_new_int(10), mp_obj_new_int(20));
    mp_obj_t r2 = test_get_smaller(mp_obj_new_int(30), mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(r1));
    printf("%ld\\n", (long)mp_obj_get_int(r2));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["10", "5"]


def test_c_max_two_args(compile_and_run):
    source = """
def get_larger(a: int, b: int) -> int:
    return max(a, b)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t r1 = test_get_larger(mp_obj_new_int(10), mp_obj_new_int(20));
    mp_obj_t r2 = test_get_larger(mp_obj_new_int(30), mp_obj_new_int(5));
    printf("%ld\\n", (long)mp_obj_get_int(r1));
    printf("%ld\\n", (long)mp_obj_get_int(r2));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip().splitlines() == ["20", "30"]


def test_c_min_three_args(compile_and_run):
    source = """
def get_smallest(a: int, b: int, c: int) -> int:
    return min(a, b, c)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_get_smallest(mp_obj_new_int(15), mp_obj_new_int(8), mp_obj_new_int(12));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "8"


def test_c_max_three_args(compile_and_run):
    source = """
def get_largest(a: int, b: int, c: int) -> int:
    return max(a, b, c)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t result = test_get_largest(mp_obj_new_int(15), mp_obj_new_int(8), mp_obj_new_int(12));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "15"


def test_c_sum_builtin(compile_and_run):
    source = """
def sum_all(lst: list) -> int:
    return sum(lst)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
        mp_obj_new_int(4),
    };
    mp_obj_t list = mp_obj_new_list(4, items);
    mp_obj_t result = test_sum_all(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "10"


def test_c_sum_with_start(compile_and_run):
    source = """
def sum_with_offset(lst: list, start: int) -> int:
    return sum(lst, start)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(1),
        mp_obj_new_int(2),
        mp_obj_new_int(3),
    };
    mp_obj_t list = mp_obj_new_list(3, items);
    mp_obj_t result = test_sum_with_offset(list, mp_obj_new_int(100));
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "106"


def test_c_sum_typed_list_int_optimized(compile_and_run):
    source = """
def sum_ints(nums: list[int]) -> int:
    return sum(nums)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_int(10),
        mp_obj_new_int(20),
        mp_obj_new_int(30),
        mp_obj_new_int(40),
    };
    mp_obj_t list = mp_obj_new_list(4, items);
    mp_obj_t result = test_sum_ints(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "100"


def test_c_sum_typed_list_float_optimized(compile_and_run):
    source = """
def sum_floats(nums: list[float]) -> float:
    return sum(nums)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t items[] = {
        mp_obj_new_float(1.5),
        mp_obj_new_float(2.5),
        mp_obj_new_float(3.0),
    };
    mp_obj_t list = mp_obj_new_list(3, items);
    mp_obj_t result = test_sum_floats(list);
    printf("%.1f\\n", mp_obj_float_get(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "7.0"


def test_c_sum_typed_list_empty(compile_and_run):
    source = """
def sum_empty(nums: list[int]) -> int:
    return sum(nums)
"""
    test_main_c = """
#include <stdio.h>

int main(void) {
    mp_obj_t list = mp_obj_new_list(0, NULL);
    mp_obj_t result = test_sum_empty(list);
    printf("%ld\\n", (long)mp_obj_get_int(result));
    return 0;
}
"""
    stdout = compile_and_run(source, "test", test_main_c)
    assert stdout.strip() == "0"
