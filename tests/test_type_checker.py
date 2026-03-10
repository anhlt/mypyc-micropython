"""Tests for the type_checker module."""

from __future__ import annotations

import pytest

from mypyc_micropython.type_checker import (
    TypeCheckResult,
    format_type_errors,
    type_check_package,
    type_check_source,
)


class TestTypeCheckSource:
    def test_valid_function(self):
        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        result = type_check_source(source, "test")
        assert result.success
        assert len(result.errors) == 0
        assert "add" in result.functions
        assert result.functions["add"].params == [("a", "int"), ("b", "int")]
        assert result.functions["add"].return_type == "int"

    def test_type_error_unsupported_operand(self):
        source = """
def bad_add(a: int, b: str) -> int:
    return a + b
"""
        result = type_check_source(source, "test")
        assert not result.success
        assert len(result.errors) == 1
        assert "Unsupported operand types" in result.errors[0]

    def test_type_error_return_type_mismatch(self):
        source = """
def get_name() -> str:
    return 42
"""
        result = type_check_source(source, "test")
        assert not result.success
        assert len(result.errors) == 1
        assert "Incompatible return value type" in result.errors[0]

    def test_class_with_fields(self):
        source = """
class Point:
    x: int
    y: int
"""
        result = type_check_source(source, "test")
        assert result.success
        assert "Point" in result.classes
        fields = result.classes["Point"].fields
        assert ("x", "int") in fields
        assert ("y", "int") in fields

    def test_class_with_methods(self):
        source = """
class Counter:
    value: int

    def __init__(self, start: int) -> None:
        self.value = start

    def increment(self) -> int:
        self.value += 1
        return self.value
"""
        result = type_check_source(source, "test")
        assert result.success
        assert "Counter" in result.classes
        class_info = result.classes["Counter"]
        method_names = [m.name for m in class_info.methods]
        assert "__init__" in method_names
        assert "increment" in method_names

    def test_multiple_functions(self):
        source = """
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

def greet(name: str) -> str:
    return "Hello, " + name
"""
        result = type_check_source(source, "test")
        assert result.success
        assert len(result.functions) == 3
        assert "add" in result.functions
        assert "multiply" in result.functions
        assert "greet" in result.functions

    def test_function_with_default_args(self):
        source = """
def greet(name: str, greeting: str = "Hello") -> str:
    return greeting + ", " + name
"""
        result = type_check_source(source, "test")
        assert result.success
        assert "greet" in result.functions
        params = result.functions["greet"].params
        assert len(params) == 2
        assert params[0] == ("name", "str")
        assert params[1][0] == "greeting"

    def test_generic_types(self):
        source = """
def process(items: list[int]) -> int:
    total: int = 0
    for item in items:
        total += item
    return total
"""
        result = type_check_source(source, "test")
        assert result.success
        assert "process" in result.functions

    def test_optional_type(self):
        source = """
from typing import Optional

def find(items: list[int], target: int) -> Optional[int]:
    for i, item in enumerate(items):
        if item == target:
            return i
    return None
"""
        result = type_check_source(source, "test")
        assert result.success
        assert "find" in result.functions

    def test_inheritance(self):
        source = """
class Animal:
    name: str

class Dog(Animal):
    breed: str
"""
        result = type_check_source(source, "test")
        assert result.success
        assert "Animal" in result.classes
        assert "Dog" in result.classes
        assert result.classes["Dog"].base_class == "Animal"


class TestFormatTypeErrors:
    def test_format_no_errors(self):
        result = TypeCheckResult(success=True, errors=[])
        formatted = format_type_errors(result)
        assert "No type errors found" in formatted

    def test_format_single_error(self):
        result = TypeCheckResult(
            success=False, errors=["test.py:5: error: Type mismatch [return-value]"]
        )
        formatted = format_type_errors(result)
        assert "1 type error(s)" in formatted
        assert "Type mismatch" in formatted

    def test_format_multiple_errors(self):
        result = TypeCheckResult(
            success=False,
            errors=[
                "test.py:5: error: Type mismatch [return-value]",
                "test.py:10: error: Missing argument [call-arg]",
            ],
        )
        formatted = format_type_errors(result)
        assert "2 type error(s)" in formatted


class TestCompilerWithTypeCheck:
    def test_compile_source_with_type_check_success(self):
        from mypyc_micropython.compiler import compile_source

        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        c_code = compile_source(source, "test", type_check=True)
        assert "test_add" in c_code
        assert "mp_int_t" in c_code

    def test_compile_source_with_type_check_failure(self):
        from mypyc_micropython.compiler import compile_source

        source = """
def bad(a: int, b: str) -> int:
    return a + b
"""
        with pytest.raises(TypeError) as exc_info:
            compile_source(source, "test", type_check=True)
        assert "Type errors found" in str(exc_info.value)
        assert "Unsupported operand types" in str(exc_info.value)

    def test_compile_source_without_type_check(self):
        from mypyc_micropython.compiler import compile_source

        source = """
def bad(a: int, b: str) -> int:
    return a + b
"""
        c_code = compile_source(source, "test", type_check=False)
        assert "test_bad" in c_code


class TestMypyTypeIntegration:
    def test_ir_builder_uses_mypy_function_types(self):
        import ast

        from mypyc_micropython.ir_builder import IRBuilder, MypyTypeInfo
        from mypyc_micropython.type_checker import FunctionTypeInfo

        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        tree = ast.parse(source)
        func_def = tree.body[0]

        mypy_info = MypyTypeInfo(
            functions={
                "add": FunctionTypeInfo(
                    name="add",
                    params=[("a", "int"), ("b", "int")],
                    return_type="int",
                )
            }
        )

        builder = IRBuilder("test", mypy_types=mypy_info)
        func_ir = builder.build_function(func_def)

        assert func_ir.params[0][0] == "a"
        assert func_ir.params[1][0] == "b"
        from mypyc_micropython.ir import CType

        assert func_ir.params[0][1] == CType.MP_INT_T
        assert func_ir.params[1][1] == CType.MP_INT_T
        assert func_ir.return_type == CType.MP_INT_T

    def test_ir_builder_uses_mypy_class_types(self):
        import ast

        from mypyc_micropython.ir_builder import IRBuilder, MypyTypeInfo
        from mypyc_micropython.type_checker import ClassTypeInfo, FunctionTypeInfo

        source = """
class Point:
    x: int
    y: int

    def get_x(self) -> int:
        return self.x
"""
        tree = ast.parse(source)
        class_def = tree.body[0]

        mypy_info = MypyTypeInfo(
            classes={
                "Point": ClassTypeInfo(
                    name="Point",
                    fields=[("x", "int"), ("y", "int")],
                    methods=[
                        FunctionTypeInfo(name="get_x", params=[], return_type="int", is_method=True)
                    ],
                )
            }
        )

        builder = IRBuilder("test", mypy_types=mypy_info)
        class_ir = builder.build_class(class_def)

        assert len(class_ir.fields) == 2
        assert class_ir.fields[0].name == "x"
        assert class_ir.fields[0].py_type == "int"
        assert class_ir.fields[1].name == "y"
        assert class_ir.fields[1].py_type == "int"

        assert "get_x" in class_ir.methods
        from mypyc_micropython.ir import CType

        assert class_ir.methods["get_x"].return_type == CType.MP_INT_T

    def test_ir_builder_falls_back_to_ast_without_mypy(self):
        import ast

        from mypyc_micropython.ir_builder import IRBuilder

        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        tree = ast.parse(source)
        func_def = tree.body[0]

        builder = IRBuilder("test", mypy_types=None)
        func_ir = builder.build_function(func_def)

        from mypyc_micropython.ir import CType

        assert func_ir.params[0][1] == CType.MP_INT_T
        assert func_ir.params[1][1] == CType.MP_INT_T
        assert func_ir.return_type == CType.MP_INT_T

    def test_compile_with_type_check_uses_mypy_info(self):
        from mypyc_micropython.compiler import compile_source

        source = """
def process(items: list[int]) -> int:
    total: int = 0
    for item in items:
        total += item
    return total
"""
        c_code = compile_source(source, "test", type_check=True)
        assert "test_process" in c_code
        assert "mp_int_t" in c_code


class TestTypeCheckPackage:
    """Tests for type_check_package() — package-level type checking."""

    def _make_package(self, tmp_path, files: dict[str, str]) -> None:
        """Create a package directory with the given files."""
        for name, content in files.items():
            (tmp_path / name).write_text(content)

    def test_basic_package(self, tmp_path):
        """Two-file package where both files have classes."""
        self._make_package(tmp_path, {
            "__init__.py": "",
            "models.py": '''
class Point:
    x: int
    y: int

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
''',
            "utils.py": '''
def add(a: int, b: int) -> int:
    return a + b
''',
        })
        results = type_check_package(tmp_path)
        assert "models" in results
        assert "utils" in results
        assert results["models"].success
        assert results["utils"].success
        assert "Point" in results["models"].classes
        assert "add" in results["utils"].functions

    def test_cross_module_import_resolves_types(self, tmp_path):
        """Cross-module import should resolve to real types, not Any."""
        self._make_package(tmp_path, {
            "__init__.py": "",
            "types.py": '''
class Config:
    name: str
    value: int

    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value
''',
            "app.py": '''
from {pkg}.types import Config

class App:
    config: Config

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_name(self) -> str:
        return self.config.name
'''.replace("{pkg}", tmp_path.name),
        })
        results = type_check_package(tmp_path)
        assert results["app"].success
        # The key test: Config should resolve to real type, not Any
        app_class = results["app"].classes.get("App")
        assert app_class is not None
        field_types = dict(app_class.fields)
        # With package-level checking, config field should resolve to Config, not Any
        assert field_types.get("config") != "Any", (
            f"Expected Config type but got: {field_types.get('config')}"
        )

    def test_missing_init_returns_error(self, tmp_path):
        """Package dir without __init__.py should return error."""
        (tmp_path / "mod.py").write_text("x: int = 1")
        results = type_check_package(tmp_path)
        assert "__init__" in results
        assert not results["__init__"].success

    def test_not_a_directory(self, tmp_path):
        """Non-directory path should return error."""
        fake = tmp_path / "not_a_dir.py"
        fake.write_text("x = 1")
        results = type_check_package(fake)
        assert "__init__" in results
        assert not results["__init__"].success

    def test_type_errors_partitioned_by_file(self, tmp_path):
        """Type errors should be attributed to the correct submodule."""
        self._make_package(tmp_path, {
            "__init__.py": "",
            "good.py": '''
def add(a: int, b: int) -> int:
    return a + b
''',
            "bad.py": '''
def broken(a: int, b: str) -> int:
    return a + b
''',
        })
        results = type_check_package(tmp_path)
        assert results["good"].success
        assert not results["bad"].success
        assert any("Unsupported operand" in e for e in results["bad"].errors)

    def test_package_name_override(self, tmp_path):
        """Custom package name should be used for module qualification."""
        self._make_package(tmp_path, {
            "__init__.py": "",
            "mod.py": '''
def f(x: int) -> int:
    return x
''',
        })
        results = type_check_package(tmp_path, package_name="custom_pkg")
        assert "mod" in results
        assert results["mod"].success
