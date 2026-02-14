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
