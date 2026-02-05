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
def double(x: int) -> int:
    return x * 2
"""
        translator = TypedPythonTranslator("test")
        result = translator.translate_source(source)
        
        assert "static mp_obj_t test_double(mp_obj_t x_obj)" in result
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
        assert "for (size_t" in result
        assert "mp_obj_subscr" in result
        assert "mp_obj_len" in result

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
        assert "mp_obj_subscr" in result
        assert "mp_obj_len" in result
