"""Tests for IR visualization utility."""

import ast
import json

import pytest

from mypyc_micropython.ir import (
    BinOpIR,
    CallIR,
    ConstIR,
    CType,
    FuncIR,
    IRType,
    ModuleIR,
    NameIR,
    ReturnIR,
)
from mypyc_micropython.ir_builder import IRBuilder
from mypyc_micropython.ir_visualizer import (
    IRJsonExporter,
    IRPrinter,
    IRTreePrinter,
    dump_ir,
)


class TestIRPrinter:
    def test_print_simple_function(self):
        func_ir = FuncIR(
            name="add",
            c_name="test_add",
            params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            return_type=CType.MP_INT_T,
            body=[
                ReturnIR(
                    value=BinOpIR(
                        ir_type=IRType.INT,
                        left=NameIR(ir_type=IRType.INT, py_name="a", c_name="a"),
                        op="+",
                        right=NameIR(ir_type=IRType.INT, py_name="b", c_name="b"),
                    )
                )
            ],
            locals_={"a": CType.MP_INT_T, "b": CType.MP_INT_T},
        )

        printer = IRPrinter()
        result = printer.print_function(func_ir)

        assert "def add(a: MP_INT_T, b: MP_INT_T) -> MP_INT_T:" in result
        assert "c_name: test_add" in result
        assert "return (a + b)" in result

    def test_print_module(self):
        module_ir = ModuleIR(name="test", c_name="test")
        module_ir.functions["add"] = FuncIR(
            name="add",
            c_name="test_add",
            params=[],
            return_type=CType.MP_INT_T,
            body=[ReturnIR(value=ConstIR(ir_type=IRType.INT, value=42))],
        )
        module_ir.function_order.append("add")

        printer = IRPrinter()
        result = printer.print_module(module_ir)

        assert "Module: test" in result
        assert "Functions:" in result
        assert "def add()" in result

    def test_print_value_const_int(self):
        printer = IRPrinter()
        const = ConstIR(ir_type=IRType.INT, value=42)
        assert printer.print_value(const) == "42"

    def test_print_value_const_string(self):
        printer = IRPrinter()
        const = ConstIR(ir_type=IRType.OBJ, value="hello")
        assert printer.print_value(const) == '"hello"'

    def test_print_value_binop(self):
        printer = IRPrinter()
        binop = BinOpIR(
            ir_type=IRType.INT,
            left=NameIR(ir_type=IRType.INT, py_name="x", c_name="x"),
            op="*",
            right=ConstIR(ir_type=IRType.INT, value=2),
        )
        assert printer.print_value(binop) == "(x * 2)"

    def test_print_value_call(self):
        printer = IRPrinter()
        call = CallIR(
            ir_type=IRType.INT,
            func_name="foo",
            c_func_name="test_foo",
            args=[ConstIR(ir_type=IRType.INT, value=1)],
        )
        assert printer.print_value(call) == "foo(1)"


class TestIRTreePrinter:
    def test_tree_simple_const(self):
        tree_printer = IRTreePrinter()
        const = ConstIR(ir_type=IRType.INT, value=42)
        result = tree_printer.print_tree(const)

        assert "ConstIR" in result
        assert "ir_type: IRType.INT" in result
        assert "value: 42" in result

    def test_tree_binop(self):
        tree_printer = IRTreePrinter()
        binop = BinOpIR(
            ir_type=IRType.INT,
            left=NameIR(ir_type=IRType.INT, py_name="a", c_name="a"),
            op="+",
            right=ConstIR(ir_type=IRType.INT, value=1),
        )
        result = tree_printer.print_tree(binop)

        assert "BinOpIR" in result
        assert "left: NameIR" in result
        assert "right: ConstIR" in result
        assert 'op: "+"' in result

    def test_tree_func_with_body(self):
        tree_printer = IRTreePrinter()
        func_ir = FuncIR(
            name="test",
            c_name="test_test",
            params=[],
            return_type=CType.MP_INT_T,
            body=[ReturnIR(value=ConstIR(ir_type=IRType.INT, value=0))],
        )
        result = tree_printer.print_tree(func_ir)

        assert "FuncIR" in result
        assert "body: list[1]" in result
        assert "ReturnIR" in result


class TestIRJsonExporter:
    def test_export_const(self):
        exporter = IRJsonExporter()
        const = ConstIR(ir_type=IRType.INT, value=42)
        result = exporter.export(const)
        data = json.loads(result)

        assert data["_type"] == "ConstIR"
        assert data["ir_type"] == "IRType.INT"
        assert data["value"] == 42

    def test_export_func(self):
        exporter = IRJsonExporter()
        func_ir = FuncIR(
            name="test",
            c_name="mod_test",
            params=[("x", CType.MP_INT_T)],
            return_type=CType.MP_INT_T,
            body=[],
        )
        result = exporter.export(func_ir)
        data = json.loads(result)

        assert data["_type"] == "FuncIR"
        assert data["name"] == "test"
        assert data["c_name"] == "mod_test"
        assert "params" in data

    def test_export_nested(self):
        exporter = IRJsonExporter()
        binop = BinOpIR(
            ir_type=IRType.INT,
            left=NameIR(ir_type=IRType.INT, py_name="a", c_name="a"),
            op="+",
            right=ConstIR(ir_type=IRType.INT, value=1),
        )
        result = exporter.export(binop)
        data = json.loads(result)

        assert data["_type"] == "BinOpIR"
        assert data["left"]["_type"] == "NameIR"
        assert data["right"]["_type"] == "ConstIR"


class TestDumpIR:
    def test_dump_text_format(self):
        const = ConstIR(ir_type=IRType.INT, value=42)
        result = dump_ir(const, "text")
        assert "42" in result

    def test_dump_tree_format(self):
        const = ConstIR(ir_type=IRType.INT, value=42)
        result = dump_ir(const, "tree")
        assert "ConstIR" in result
        assert "value: 42" in result

    def test_dump_json_format(self):
        const = ConstIR(ir_type=IRType.INT, value=42)
        result = dump_ir(const, "json")
        data = json.loads(result)
        assert data["_type"] == "ConstIR"
        assert data["value"] == 42

    def test_dump_invalid_format(self):
        const = ConstIR(ir_type=IRType.INT, value=42)
        with pytest.raises(ValueError) as exc_info:
            dump_ir(const, "invalid")
        assert "Unknown format" in str(exc_info.value)


class TestIntegration:
    def test_visualize_from_source(self):
        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

                text_output = dump_ir(func_ir, "text")
                assert "def add" in text_output
                assert "return" in text_output

                tree_output = dump_ir(func_ir, "tree")
                assert "FuncIR" in tree_output
                assert "ReturnIR" in tree_output

                json_output = dump_ir(func_ir, "json")
                data = json.loads(json_output)
                assert data["name"] == "add"

    def test_visualize_with_prelude(self):
        source = """
def process(lst: list) -> int:
    total: int = 0
    item: object
    for item in lst:
        total = total + 1
    return total
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)
                text_output = dump_ir(func_ir, "text")

                assert "for item in" in text_output
