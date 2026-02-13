"""Tests for the mypyc-micropython compiler."""

import tempfile
from pathlib import Path

import pytest

from mypyc_micropython.compiler import (
    CompilationResult,
    TypedPythonTranslator,
    compile_source,
    compile_to_micropython,
    sanitize_name,
)


class TestSanitizeName:
    """Tests for the sanitize_name function."""

    def test_simple_name(self):
        assert sanitize_name("hello") == "hello"

    def test_name_with_numbers(self):
        assert sanitize_name("hello123") == "hello123"

    def test_name_starting_with_number(self):
        assert sanitize_name("123hello") == "_123hello"

    def test_name_with_special_chars(self):
        assert sanitize_name("hello-world") == "hello_world"
        assert sanitize_name("hello.world") == "hello_world"
        assert sanitize_name("hello@world") == "hello_world"

    def test_empty_name(self):
        assert sanitize_name("") == ""


class TestTypedPythonTranslator:
    """Tests for the TypedPythonTranslator class."""

    def test_simple_function(self):
        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "static mp_obj_t test_add" in result
        assert "mp_obj_get_int" in result
        assert "mp_obj_new_int" in result
        assert "MP_DEFINE_CONST_FUN_OBJ_2" in result

    def test_function_with_no_args(self):
        source = """
def get_answer() -> int:
    return 42
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "static mp_obj_t test_get_answer(void)" in result
        assert "MP_DEFINE_CONST_FUN_OBJ_0" in result
        assert "return mp_obj_new_int(42)" in result

    def test_function_with_one_arg(self):
        source = """
def square(x: int) -> int:
    return x * 2
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "static mp_obj_t test_square(mp_obj_t x_obj)" in result
        assert "MP_DEFINE_CONST_FUN_OBJ_1" in result

    def test_function_with_three_args(self):
        source = """
def add3(a: int, b: int, c: int) -> int:
    return a + b + c
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "MP_DEFINE_CONST_FUN_OBJ_3" in result

    def test_function_with_four_args(self):
        source = """
def add4(a: int, b: int, c: int, d: int) -> int:
    return a + b + c + d
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN" in result
        assert "size_t n_args" in result

    def test_float_function(self):
        source = """
def multiply(a: float, b: float) -> float:
    return a * b
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "mp_float_t" in result
        assert "mp_get_float_checked" in result
        assert "mp_obj_new_float" in result

    def test_bool_function(self):
        source = """
def is_positive(n: int) -> bool:
    return n > 0
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "mp_const_true" in result or "mp_const_false" in result

    def test_if_else_statement(self):
        source = """
def abs_val(n: int) -> int:
    if n < 0:
        return -n
    else:
        return n
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "if (" in result
        assert "} else {" in result

    def test_recursive_function(self):
        source = """
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "test_factorial(" in result
        assert result.count("test_factorial") >= 2

    def test_local_variable(self):
        source = """
def compute(x: int) -> int:
    result = x * 2
    return result
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "result =" in result

    def test_multiple_functions(self):
        source = """
def func1() -> int:
    return 1

def func2() -> int:
    return 2
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "test_func1" in result
        assert "test_func2" in result
        assert "MP_QSTR_func1" in result
        assert "MP_QSTR_func2" in result

    def test_module_registration(self):
        source = """
def hello() -> int:
    return 42
"""
        translator = TypedPythonTranslator("mymod")
        result = translator.translate_source(source)
        
        assert "MP_REGISTER_MODULE(MP_QSTR_mymod" in result
        assert "mymod_module_globals" in result
        assert "mymod_user_cmodule" in result

    def test_while_loop(self):
        source = """
def count_down(n: int) -> int:
    total: int = 0
    while n > 0:
        total = total + n
        n = n - 1
    return total
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "while (" in result
        assert "n > 0" in result

    def test_annotated_assignment(self):
        source = """
def test() -> int:
    x: int = 10
    return x
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "mp_int_t x = 10" in result

    def test_augmented_assignment(self):
        source = """
def test(n: int) -> int:
    n += 5
    return n
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "n += 5" in result


class TestCompileSource:
    """Tests for the compile_source function."""

    def test_basic_compilation(self):
        source = "def add(a: int, b: int) -> int:\n    return a + b\n"
        result = compile_source(source, "test")
        
        assert '#include "py/runtime.h"' in result
        assert '#include "py/obj.h"' in result
        assert "test_add" in result


class TestCompileToMicropython:
    """Tests for the compile_to_micropython function."""

    def test_file_not_found(self):
        result = compile_to_micropython("/nonexistent/path/file.py")
        
        assert result.success is False
        assert "not found" in result.errors[0].lower()

    def test_successful_compilation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mymodule.py"
            source_path.write_text("def hello() -> int:\n    return 42\n")
            
            result = compile_to_micropython(source_path)
            
            assert result.success is True
            assert result.module_name == "mymodule"
            assert "mymodule_hello" in result.c_code
            
            output_dir = Path(tmpdir) / "usermod_mymodule"
            assert output_dir.exists()
            assert (output_dir / "mymodule.c").exists()
            assert (output_dir / "micropython.mk").exists()
            assert (output_dir / "micropython.cmake").exists()

    def test_custom_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "test.py"
            source_path.write_text("def foo() -> int:\n    return 1\n")
            
            output_dir = Path(tmpdir) / "custom_output"
            result = compile_to_micropython(source_path, output_dir)
            
            assert result.success is True
            assert output_dir.exists()
            assert (output_dir / "test.c").exists()

    def test_mk_file_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mymod.py"
            source_path.write_text("def x() -> int:\n    return 0\n")
            
            result = compile_to_micropython(source_path)
            
            assert "MYMOD_MOD_DIR" in result.mk_code
            assert "SRC_USERMOD" in result.mk_code
            assert "CFLAGS_USERMOD" in result.mk_code

    def test_cmake_file_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "mymod.py"
            source_path.write_text("def x() -> int:\n    return 0\n")
            
            result = compile_to_micropython(source_path)
            
            assert "add_library(usermod_mymod" in result.cmake_code
            assert "target_sources" in result.cmake_code
            assert "target_include_directories" in result.cmake_code
            assert "target_link_libraries" in result.cmake_code


class TestArithmeticOperations:
    """Tests for arithmetic operation translation."""

    @pytest.mark.parametrize("op,c_op", [
        ("+", "+"),
        ("-", "-"),
        ("*", "*"),
        ("/", "/"),
        ("%", "%"),
    ])
    def test_binary_ops(self, op, c_op):
        source = f"def calc(a: int, b: int) -> int:\n    return a {op} b\n"
        result = compile_source(source, "test")
        assert f"(a {c_op} b)" in result

    @pytest.mark.parametrize("op,c_op", [
        ("&", "&"),
        ("|", "|"),
        ("^", "^"),
        ("<<", "<<"),
        (">>", ">>"),
    ])
    def test_bitwise_ops(self, op, c_op):
        source = f"def calc(a: int, b: int) -> int:\n    return a {op} b\n"
        result = compile_source(source, "test")
        assert f"(a {c_op} b)" in result


class TestComparisonOperations:
    """Tests for comparison operation translation."""

    @pytest.mark.parametrize("op,c_op", [
        ("==", "=="),
        ("!=", "!="),
        ("<", "<"),
        (">", ">"),
        ("<=", "<="),
        (">=", ">="),
    ])
    def test_comparison_ops(self, op, c_op):
        source = f"def cmp(a: int, b: int) -> bool:\n    return a {op} b\n"
        result = compile_source(source, "test")
        assert f"(a {c_op} b)" in result


class TestUnaryOperations:
    """Tests for unary operation translation."""

    def test_unary_minus(self):
        source = "def negate(x: int) -> int:\n    return -x\n"
        result = compile_source(source, "test")
        assert "(-x)" in result

    def test_unary_not(self):
        source = "def invert(x: bool) -> bool:\n    return not x\n"
        result = compile_source(source, "test")
        assert "(!x)" in result

    def test_bitwise_not(self):
        source = "def complement(x: int) -> int:\n    return ~x\n"
        result = compile_source(source, "test")
        assert "(~x)" in result


class TestBuiltinFunctions:
    """Tests for builtin function translation."""

    def test_abs_builtin(self):
        source = "def absolute(x: int) -> int:\n    return abs(x)\n"
        result = compile_source(source, "test")
        assert "< 0" in result or "abs" in result.lower()

    def test_int_cast(self):
        source = "def to_int(x: float) -> int:\n    return int(x)\n"
        result = compile_source(source, "test")
        assert "(mp_int_t)" in result

    def test_float_cast(self):
        source = "def to_float(x: int) -> float:\n    return float(x)\n"
        result = compile_source(source, "test")
        assert "(mp_float_t)" in result


class TestTernaryExpression:
    """Tests for ternary expression translation."""

    def test_if_expression(self):
        source = "def max_val(a: int, b: int) -> int:\n    return a if a > b else b\n"
        result = compile_source(source, "test")
        assert "?" in result
        assert ":" in result


class TestConstants:
    """Tests for constant translation."""

    def test_integer_constant(self):
        source = "def get_42() -> int:\n    return 42\n"
        result = compile_source(source, "test")
        assert "42" in result

    def test_float_constant(self):
        source = "def get_pi() -> float:\n    return 3.14\n"
        result = compile_source(source, "test")
        assert "3.14" in result

    def test_bool_true(self):
        source = "def get_true() -> bool:\n    return True\n"
        result = compile_source(source, "test")
        assert "true" in result or "mp_const_true" in result

    def test_bool_false(self):
        source = "def get_false() -> bool:\n    return False\n"
        result = compile_source(source, "test")
        assert "false" in result or "mp_const_false" in result

    def test_none_constant(self):
        source = "def get_none():\n    return None\n"
        result = compile_source(source, "test")
        assert "mp_const_none" in result


class TestListOperations:

    def test_empty_list_literal(self):
        source = """
def get_empty() -> list:
    return []
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_list(0, NULL)" in result

    def test_list_literal_with_ints(self):
        source = """
def get_list() -> list:
    return [1, 2, 3]
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_list(3" in result
        assert "mp_obj_new_int(1)" in result
        assert "mp_obj_new_int(2)" in result
        assert "mp_obj_new_int(3)" in result

    def test_list_indexing_get(self):
        source = """
def get_item(lst: list, i: int):
    return lst[i]
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result
        assert "MP_OBJ_SENTINEL" in result

    def test_list_indexing_set(self):
        source = """
def set_item(lst: list, i: int, val: int) -> None:
    lst[i] = val
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result
        assert "mp_obj_new_int(val)" in result

    def test_list_len(self):
        source = """
def get_len(lst: list) -> int:
    return len(lst)
"""
        result = compile_source(source, "test")
        assert "mp_obj_len" in result
        assert "mp_obj_get_int" in result

    def test_list_append(self):
        source = """
def append_item(lst: list, val: int) -> None:
    lst.append(val)
"""
        result = compile_source(source, "test")
        assert "mp_obj_list_append" in result

    def test_list_type_annotation_generic(self):
        source = """
def process(lst: list[int]) -> int:
    return len(lst)
"""
        result = compile_source(source, "test")
        assert "mp_obj_t lst" in result


class TestForLoop:

    def test_for_range_single_arg(self):
        source = """
def sum_range(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i
    return total
"""
        result = compile_source(source, "test")
        assert "for (" in result
        assert "i = 0" in result
        assert "i <" in result
        assert "i++" in result

    def test_for_range_two_args(self):
        source = """
def sum_range(start: int, end: int) -> int:
    total: int = 0
    for i in range(start, end):
        total += i
    return total
"""
        result = compile_source(source, "test")
        assert "for (" in result
        assert "i = start" in result

    def test_for_range_three_args(self):
        source = """
def sum_step(n: int) -> int:
    total: int = 0
    for i in range(0, n, 2):
        total += i
    return total
"""
        result = compile_source(source, "test")
        assert "for (" in result
        assert "+=" in result

    def test_for_over_list(self):
        source = """
def sum_list(lst: list) -> int:
    total: int = 0
    for item in lst:
        total += 1
    return total
"""
        result = compile_source(source, "test")
        assert "mp_getiter" in result
        assert "mp_iternext" in result
        assert "MP_OBJ_STOP_ITERATION" in result

    def test_break_statement(self):
        source = """
def find_first(lst: list, target: int) -> int:
    for i in range(10):
        if i == target:
            break
    return i
"""
        result = compile_source(source, "test")
        assert "break;" in result

    def test_continue_statement(self):
        source = """
def skip_evens(n: int) -> int:
    total: int = 0
    for i in range(n):
        if i % 2 == 0:
            continue
        total += i
    return total
"""
        result = compile_source(source, "test")
        assert "continue;" in result

    def test_nested_for_loops(self):
        source = """
def nested(n: int) -> int:
    total: int = 0
    for i in range(n):
        for j in range(n):
            total += 1
    return total
"""
        result = compile_source(source, "test")
        assert result.count("for (") >= 2


class TestListWithForLoop:

    def test_build_list_with_for(self):
        source = """
def build_squares(n: int) -> list:
    result: list = []
    for i in range(n):
        result.append(i * i)
    return result
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_list(0, NULL)" in result
        assert "mp_obj_list_append" in result
        assert "for (" in result

    def test_sum_list_elements(self):
        source = """
def sum_all(lst: list) -> int:
    total: int = 0
    for x in lst:
        total += 1
    return total
"""
        result = compile_source(source, "test")
        assert "mp_getiter" in result
        assert "mp_iternext" in result


class TestDictOperations:

    def test_empty_dict_literal(self):
        source = """
def get_empty() -> dict:
    return {}
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(0)" in result

    def test_dict_literal_with_values(self):
        source = """
def get_config() -> dict:
    return {"name": "test", "value": 42}
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(2)" in result
        assert "mp_obj_dict_store" in result
        assert 'mp_obj_new_str("name"' in result
        assert 'mp_obj_new_str("test"' in result
        assert "mp_obj_new_int(42)" in result

    def test_dict_subscript_get(self):
        source = """
def get_item(d: dict, key: str):
    return d[key]
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result
        assert "MP_OBJ_SENTINEL" in result

    def test_dict_subscript_set(self):
        source = """
def set_item(d: dict, key: str, val: int) -> None:
    d[key] = val
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result
        assert "mp_obj_new_int(val)" in result

    def test_dict_len(self):
        source = """
def get_len(d: dict) -> int:
    return len(d)
"""
        result = compile_source(source, "test")
        assert "mp_obj_len" in result
        assert "mp_obj_get_int" in result

    def test_dict_get_without_default(self):
        source = """
def get_value(d: dict, key: str):
    return d.get(key)
"""
        result = compile_source(source, "test")
        assert "mp_obj_dict_get" in result

    def test_dict_get_with_default(self):
        source = """
def get_value(d: dict, key: str, default_val: int):
    return d.get(key, default_val)
"""
        result = compile_source(source, "test")
        assert "mp_load_attr" in result
        assert "MP_QSTR_get" in result
        assert "mp_call_function_n_kw" in result

    def test_dict_keys(self):
        source = """
def get_keys(d: dict):
    return d.keys()
"""
        result = compile_source(source, "test")
        assert "mp_load_attr" in result
        assert "MP_QSTR_keys" in result
        assert "mp_call_function_0" in result

    def test_dict_values(self):
        source = """
def get_values(d: dict):
    return d.values()
"""
        result = compile_source(source, "test")
        assert "mp_load_attr" in result
        assert "MP_QSTR_values" in result
        assert "mp_call_function_0" in result

    def test_dict_items(self):
        source = """
def get_items(d: dict):
    return d.items()
"""
        result = compile_source(source, "test")
        assert "mp_load_attr" in result
        assert "MP_QSTR_items" in result
        assert "mp_call_function_0" in result

    def test_dict_constructor(self):
        source = """
def make_dict() -> dict:
    return dict()
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(0)" in result

    def test_dict_type_annotation_generic(self):
        source = """
def process(d: dict[str, int]) -> int:
    return len(d)
"""
        result = compile_source(source, "test")
        assert "mp_obj_t d" in result

    def test_for_over_dict_keys(self):
        source = """
def sum_dict(d: dict) -> int:
    total: int = 0
    for key in d.keys():
        total += 1
    return total
"""
        result = compile_source(source, "test")
        assert "mp_getiter" in result
        assert "mp_iternext" in result
        assert "MP_QSTR_keys" in result

    def test_dict_int_keys(self):
        source = """
def create_counter(n: int) -> dict:
    result: dict = {}
    for i in range(n):
        result[i] = i * i
    return result
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(0)" in result
        assert "mp_obj_subscr" in result
        assert "mp_obj_new_int(i)" in result


class TestDictLiteralsEdgeCases:
    """Edge cases for dict literal construction."""

    def test_dict_literal_single_entry(self):
        source = """
def get_single() -> dict:
    return {"key": 1}
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(1)" in result
        assert "mp_obj_dict_store" in result
        assert 'mp_obj_new_str("key"' in result
        assert "mp_obj_new_int(1)" in result

    def test_dict_literal_with_float_values(self):
        source = """
def get_floats() -> dict:
    return {"pi": 3.14, "e": 2.71}
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(2)" in result
        assert "mp_obj_new_float(3.14)" in result
        assert "mp_obj_new_float(2.71)" in result

    def test_dict_literal_with_bool_values(self):
        source = """
def get_flags() -> dict:
    return {"enabled": True, "debug": False}
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(2)" in result
        assert "mp_const_true" in result
        assert "mp_const_false" in result

    def test_dict_literal_mixed_value_types(self):
        source = """
def get_mixed() -> dict:
    return {"name": "test", "count": 42, "rate": 3.14}
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(3)" in result
        assert 'mp_obj_new_str("name"' in result
        assert 'mp_obj_new_str("test"' in result
        assert "mp_obj_new_int(42)" in result
        assert "mp_obj_new_float(3.14)" in result

    def test_dict_literal_many_entries(self):
        source = """
def get_big() -> dict:
    return {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(5)" in result
        assert result.count("mp_obj_dict_store") == 5


class TestDictSubscriptEdgeCases:
    """Edge cases for dict subscript operations."""

    def test_dict_subscript_set_with_float(self):
        source = """
def set_float(d: dict, key: str, val: float) -> None:
    d[key] = val
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result
        assert "mp_obj_new_float(val)" in result

    def test_dict_subscript_set_with_string(self):
        source = """
def set_str(d: dict, key: str, val: str) -> None:
    d[key] = val
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result

    def test_dict_subscript_with_int_key(self):
        source = """
def get_by_int(d: dict, i: int):
    return d[i]
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result
        assert "mp_obj_new_int(i)" in result

    def test_dict_subscript_in_expression(self):
        source = """
def double_value(d: dict, key: str) -> int:
    x: int = d[key]
    return x * 2
"""
        result = compile_source(source, "test")
        assert "mp_obj_subscr" in result
        assert "x * 2" in result

    def test_dict_nested_subscript_set(self):
        """Setting value from another dict lookup."""
        source = """
def copy_value(src: dict, dst: dict, key: str) -> None:
    dst[key] = src[key]
"""
        result = compile_source(source, "test")
        # Should have two subscr calls (one get, one set)
        assert result.count("mp_obj_subscr") == 2


class TestDictWithControlFlow:
    """Tests for dict operations combined with control flow."""

    def test_dict_in_if_else(self):
        source = """
def conditional_dict(flag: bool) -> dict:
    if flag:
        return {"result": 1}
    else:
        return {"result": 0}
"""
        result = compile_source(source, "test")
        assert "if (" in result
        assert "} else {" in result
        assert result.count("mp_obj_new_dict(1)") == 2

    def test_dict_build_in_while_loop(self):
        source = """
def build_dict(n: int) -> dict:
    result: dict = {}
    i: int = 0
    while i < n:
        result[i] = i * i
        i += 1
    return result
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(0)" in result
        assert "while (" in result
        assert "mp_obj_subscr" in result

    def test_dict_iteration_with_conditional(self):
        source = """
def count_positive(d: dict) -> int:
    count: int = 0
    for key in d.keys():
        if key > 0:
            count += 1
    return count
"""
        result = compile_source(source, "test")
        assert "mp_getiter" in result
        assert "mp_iternext" in result
        assert "if (" in result

    def test_for_over_dict_values(self):
        source = """
def sum_values(d: dict) -> int:
    total: int = 0
    for val in d.values():
        total += 1
    return total
"""
        result = compile_source(source, "test")
        assert "mp_getiter" in result
        assert "mp_iternext" in result
        assert "MP_QSTR_values" in result

    def test_for_over_dict_items(self):
        source = """
def process_items(d: dict) -> int:
    count: int = 0
    for item in d.items():
        count += 1
    return count
"""
        result = compile_source(source, "test")
        assert "mp_getiter" in result
        assert "mp_iternext" in result
        assert "MP_QSTR_items" in result


class TestDictWithFunctions:
    """Tests for dict operations combined with functions."""

    def test_dict_as_return_value(self):
        source = """
def make_pair(key: str, val: int) -> dict:
    result: dict = {}
    result[key] = val
    return result
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(0)" in result
        assert "mp_obj_subscr" in result
        assert "return result" in result or "return mp_obj" in result

    def test_dict_as_parameter(self):
        source = """
def get_or_zero(d: dict, key: str) -> int:
    return d.get(key)
"""
        result = compile_source(source, "test")
        assert "mp_obj_t d" in result
        assert "mp_obj_dict_get" in result

    def test_dict_len_in_condition(self):
        source = """
def is_empty(d: dict) -> bool:
    return len(d) == 0
"""
        result = compile_source(source, "test")
        assert "mp_obj_len" in result
        assert "== 0" in result

    def test_dict_len_in_while(self):
        source = """
def drain(d: dict) -> int:
    count: int = 0
    while len(d) > 0:
        count += 1
        break
    return count
"""
        result = compile_source(source, "test")
        assert "mp_obj_len" in result
        assert "while (" in result

    def test_multiple_dict_params(self):
        source = """
def merge_len(d1: dict, d2: dict) -> int:
    return len(d1) + len(d2)
"""
        result = compile_source(source, "test")
        assert result.count("mp_obj_len") == 2

    def test_dict_method_chain_keys_iteration(self):
        """Test iterating over dict keys and accessing values."""
        source = """
def sum_values_by_keys(d: dict) -> int:
    total: int = 0
    for key in d.keys():
        total += 1
    return total
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_keys" in result
        assert "mp_getiter" in result
        assert "mp_iternext" in result


class TestDictGetVariants:
    """Thorough tests for dict.get() method variants."""

    def test_dict_get_with_int_key(self):
        source = """
def get_by_int(d: dict, key: int):
    return d.get(key)
"""
        result = compile_source(source, "test")
        assert "mp_obj_dict_get" in result
        assert "mp_obj_new_int(key)" in result

    def test_dict_get_with_default_int(self):
        source = """
def get_or_default(d: dict, key: str) -> int:
    return d.get(key, 0)
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_get" in result
        assert "mp_obj_new_int(0)" in result

    def test_dict_get_with_default_string(self):
        source = """
def get_or_unknown(d: dict, key: str):
    return d.get(key, "unknown")
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_get" in result
        assert 'mp_obj_new_str("unknown"' in result


class TestDictModuleIntegration:
    """Tests for dict operations in full module context."""

    def test_dict_function_generates_module(self):
        source = """
def create() -> dict:
    return {"x": 1}

def lookup(d: dict, k: str):
    return d[k]
"""
        translator = TypedPythonTranslator("dictmod")
        result = translator.translate_source(source)
        assert "MP_REGISTER_MODULE(MP_QSTR_dictmod" in result
        assert "dictmod_create" in result
        assert "dictmod_lookup" in result
        assert "MP_QSTR_create" in result
        assert "MP_QSTR_lookup" in result

    def test_dict_function_arg_count(self):
        """Dict param functions should have correct MP_DEFINE macro."""
        source = """
def get_len(d: dict) -> int:
    return len(d)
"""
        result = compile_source(source, "test")
        assert "MP_DEFINE_CONST_FUN_OBJ_1" in result

    def test_dict_two_param_function(self):
        source = """
def get_item(d: dict, key: str):
    return d[key]
"""
        result = compile_source(source, "test")
        assert "MP_DEFINE_CONST_FUN_OBJ_2" in result

    def test_dict_three_param_function(self):
        source = """
def set_item(d: dict, key: str, val: int) -> None:
    d[key] = val
"""
        result = compile_source(source, "test")
        assert "MP_DEFINE_CONST_FUN_OBJ_3" in result


class TestDictAssignmentVariants:
    """Tests for dict variable assignment and usage patterns."""

    def test_dict_assigned_to_local(self):
        source = """
def make_dict() -> dict:
    d: dict = {"a": 1}
    return d
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(1)" in result
        assert "mp_obj_t d" in result

    def test_dict_empty_assigned_then_populated(self):
        source = """
def build() -> dict:
    d: dict = {}
    d["x"] = 10
    d["y"] = 20
    return d
"""
        result = compile_source(source, "test")
        assert "mp_obj_new_dict(0)" in result
        assert result.count("mp_obj_subscr") == 2

    def test_dict_overwrite_key(self):
        source = """
def overwrite(d: dict, key: str) -> None:
    d[key] = 1
    d[key] = 2
"""
        result = compile_source(source, "test")
        assert result.count("mp_obj_subscr") == 2
        assert "mp_obj_new_int(1)" in result
        assert "mp_obj_new_int(2)" in result


class TestDictMembership:

    def test_in_operator(self):
        source = """
def has_key(d: dict) -> bool:
    return "name" in d
"""
        result = compile_source(source, "test")
        assert "mp_binary_op(MP_BINARY_OP_IN," in result
        assert "mp_obj_is_true(" in result

    def test_not_in_operator(self):
        source = """
def missing_key(d: dict) -> bool:
    return "name" not in d
"""
        result = compile_source(source, "test")
        assert "mp_binary_op(MP_BINARY_OP_IN," in result
        assert "mp_obj_is_true(" in result
        assert "!" in result

    def test_in_with_int_key(self):
        source = """
def has_int_key(d: dict) -> bool:
    return 42 in d
"""
        result = compile_source(source, "test")
        assert "mp_binary_op(MP_BINARY_OP_IN," in result
        assert "mp_obj_new_int(42)" in result

    def test_in_with_variable_key(self):
        source = """
def has_var_key(d: dict, k: int) -> bool:
    return k in d
"""
        result = compile_source(source, "test")
        assert "mp_binary_op(MP_BINARY_OP_IN," in result

    def test_in_inside_if(self):
        source = """
def check(d: dict) -> int:
    if "x" in d:
        return 1
    return 0
"""
        result = compile_source(source, "test")
        assert "mp_binary_op(MP_BINARY_OP_IN," in result
        assert "if" in result


class TestDictCopy:

    def test_copy_basic(self):
        source = """
def dup(d: dict):
    return d.copy()
"""
        result = compile_source(source, "test")
        assert "mp_load_attr(" in result
        assert "MP_QSTR_copy" in result
        assert "mp_call_function_0(" in result

    def test_copy_assigned(self):
        source = """
def dup(d: dict):
    d2: dict = d.copy()
    return d2
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_copy" in result


class TestDictClear:

    def test_clear_basic(self):
        source = """
def wipe(d: dict):
    d.clear()
"""
        result = compile_source(source, "test")
        assert "mp_load_attr(" in result
        assert "MP_QSTR_clear" in result
        assert "mp_call_function_0(" in result


class TestDictSetdefault:

    def test_setdefault_key_only(self):
        source = """
def get_or_none(d: dict):
    return d.setdefault("key")
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_setdefault" in result
        assert "mp_call_function_1(" in result

    def test_setdefault_with_default_int(self):
        source = """
def get_or_zero(d: dict):
    return d.setdefault("count", 0)
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_setdefault" in result
        assert "mp_call_function_n_kw(" in result
        assert "mp_obj_new_int(0)" in result

    def test_setdefault_with_default_string(self):
        source = """
def get_or_empty(d: dict):
    return d.setdefault("name", "unknown")
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_setdefault" in result
        assert 'mp_obj_new_str("unknown"' in result


class TestDictPop:

    def test_pop_key_only(self):
        source = """
def remove_key(d: dict):
    return d.pop("key")
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_pop" in result
        assert "mp_call_method_n_kw(1, 0," in result

    def test_pop_with_default(self):
        source = """
def remove_or_default(d: dict):
    return d.pop("key", 0)
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_pop" in result
        assert "mp_call_method_n_kw(2, 0," in result
        assert "mp_obj_new_int(0)" in result

    def test_pop_with_string_key(self):
        source = """
def remove_str(d: dict):
    return d.pop("name")
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_pop" in result
        assert 'mp_obj_new_str("name"' in result

    def test_pop_with_int_key(self):
        source = """
def remove_int(d: dict):
    return d.pop(42)
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_pop" in result
        assert "mp_obj_new_int(42)" in result


class TestDictPopitem:

    def test_popitem_basic(self):
        source = """
def take_last(d: dict):
    return d.popitem()
"""
        result = compile_source(source, "test")
        assert "mp_load_attr(" in result
        assert "MP_QSTR_popitem" in result
        assert "mp_call_function_0(" in result


class TestDictUpdate:

    def test_update_basic(self):
        source = """
def merge(d1: dict, d2: dict):
    d1.update(d2)
"""
        result = compile_source(source, "test")
        assert "mp_load_attr(" in result
        assert "MP_QSTR_update" in result
        assert "mp_call_function_1(" in result

    def test_update_with_return(self):
        source = """
def merge_and_return(d1: dict, d2: dict):
    d1.update(d2)
    return d1
"""
        result = compile_source(source, "test")
        assert "MP_QSTR_update" in result


class TestDictCopyConstructor:

    def test_dict_copy_constructor(self):
        source = """
def dup(d: dict) -> dict:
    return dict(d)
"""
        result = compile_source(source, "test")
        assert "mp_obj_dict_copy(" in result

    def test_dict_copy_constructor_assigned(self):
        source = """
def dup(d: dict) -> dict:
    d2: dict = dict(d)
    return d2
"""
        result = compile_source(source, "test")
        assert "mp_obj_dict_copy(" in result


class TestSanitizeReservedWords:

    def test_reserved_word_default(self):
        assert sanitize_name("default") == "default_"

    def test_reserved_word_int(self):
        assert sanitize_name("int") == "int_"

    def test_reserved_word_return(self):
        assert sanitize_name("return") == "return_"

    def test_reserved_word_void(self):
        assert sanitize_name("void") == "void_"

    def test_non_reserved_word(self):
        assert sanitize_name("myvar") == "myvar"

    def test_function_with_default_param(self):
        source = """
def get_with_default(d: dict, key: str, default: int) -> int:
    return d.get(key, default)
"""
        result = compile_source(source, "test")
        assert "default_" in result
        assert "mp_int_t default_" in result


class TestBreakContinueValidation:
    """Tests for break/continue outside loop validation (Fix 3)."""

    def test_break_outside_loop_emits_error_comment(self):
        source = """
def bad_break() -> int:
    break
    return 0
"""
        result = compile_source(source, "test")
        assert "ERROR: break outside loop" in result
        assert "break;" not in result

    def test_continue_outside_loop_emits_error_comment(self):
        source = """
def bad_continue() -> int:
    continue
    return 0
"""
        result = compile_source(source, "test")
        assert "ERROR: continue outside loop" in result
        assert "continue;" not in result

    def test_break_inside_loop_works(self):
        source = """
def ok_break() -> int:
    for i in range(10):
        break
    return 0
"""
        result = compile_source(source, "test")
        assert "break;" in result
        assert "ERROR" not in result

    def test_continue_inside_loop_works(self):
        source = """
def ok_continue() -> int:
    for i in range(10):
        continue
    return 0
"""
        result = compile_source(source, "test")
        assert "continue;" in result
        assert "ERROR" not in result

    def test_break_inside_while_loop_works(self):
        source = """
def ok_while_break() -> int:
    while True:
        break
    return 0
"""
        result = compile_source(source, "test")
        assert "break;" in result
        assert "ERROR" not in result


class TestListPopFix:
    """Tests for list.pop() using method dispatch (mp_load_method + mp_call_method_n_kw)."""

    def test_pop_no_args(self):
        source = """
def pop_last(lst: list):
    return lst.pop()
"""
        result = compile_source(source, "test")
        assert "mp_load_method(" in result
        assert "MP_QSTR_pop" in result
        assert "mp_call_method_n_kw(0, 0," in result

    def test_pop_with_index(self):
        source = """
def pop_at(lst: list, i: int):
    return lst.pop(i)
"""
        result = compile_source(source, "test")
        assert "mp_load_method(" in result
        assert "MP_QSTR_pop" in result
        assert "mp_call_method_n_kw(1, 0," in result


class TestSubscriptUnboxing:
    """Tests for mp_obj_t unboxing when list subscripts are used in arithmetic/comparison."""

    def test_subscript_in_comparison(self):
        """lst[i] < 0 should unbox with mp_obj_get_int."""
        source = """
def check(lst: list, i: int) -> bool:
    return lst[i] < 0
"""
        result = compile_source(source, "test")
        assert "mp_obj_get_int(mp_obj_subscr(" in result

    def test_subscript_in_aug_assign(self):
        """total += lst[i] should unbox the subscript result."""
        source = """
def sum_list(lst: list) -> int:
    total: int = 0
    n: int = len(lst)
    for i in range(n):
        total += lst[i]
    return total
"""
        result = compile_source(source, "test")
        assert "mp_obj_get_int(mp_obj_subscr(" in result

    def test_subscript_in_binop(self):
        """lst[i] + lst[j] should unbox both sides."""
        source = """
def add_elems(lst: list, i: int, j: int) -> int:
    return lst[i] + lst[j]
"""
        result = compile_source(source, "test")
        # Both subscripts should be unboxed
        assert result.count("mp_obj_get_int(mp_obj_subscr(") == 2

    def test_subscript_with_int_no_double_unbox(self):
        """lst[i] + 1 should only unbox the subscript, not the int literal."""
        source = """
def inc_elem(lst: list, i: int) -> int:
    return lst[i] + 1
"""
        result = compile_source(source, "test")
        assert "mp_obj_get_int(mp_obj_subscr(" in result
        # The integer 1 should NOT be wrapped in mp_obj_get_int
        assert "mp_obj_get_int(1)" not in result
