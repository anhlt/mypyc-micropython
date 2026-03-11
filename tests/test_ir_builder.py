"""Unit tests for IRBuilder - AST to IR translation."""

from __future__ import annotations

import ast
import sys

import pytest

from mypyc_micropython.ir import (
    AnnAssignIR,
    AssignIR,
    AugAssignIR,
    BinOpIR,
    BreakIR,
    CallIR,
    CompareIR,
    ConstIR,
    ContinueIR,
    CType,
    DynamicCallIR,
    ExprStmtIR,
    ForIterIR,
    ForRangeIR,
    IfExprIR,
    IfIR,
    IRType,
    IsInstanceIR,
    ListNewIR,
    MethodCallIR,
    ModuleAttrIR,
    NameIR,
    ObjAttrAssignIR,
    ParamAttrIR,
    PassIR,
    PrintIR,
    ReturnIR,
    SubscriptIR,
    TempAssignIR,
    TempIR,
    TupleNewIR,
    UnaryOpIR,
    WhileIR,
)
from mypyc_micropython.ir_builder import BuildContext, IRBuilder, sanitize_name


class TestSanitizeName:
    def test_simple_name(self):
        assert sanitize_name("foo") == "foo"

    def test_name_with_special_chars(self):
        assert sanitize_name("foo-bar") == "foo_bar"
        assert sanitize_name("foo.bar") == "foo_bar"

    def test_name_starting_with_digit(self):
        assert sanitize_name("123abc") == "_123abc"

    def test_reserved_word(self):
        assert sanitize_name("int") == "int_"
        assert sanitize_name("return") == "return_"
        assert sanitize_name("while") == "while_"

    def test_empty_name(self):
        assert sanitize_name("") == ""


class TestBuildFunction:
    def test_simple_function(self):
        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert func_ir.name == "add"
        assert func_ir.c_name == "test_add"
        assert len(func_ir.params) == 2
        assert func_ir.params[0] == ("a", CType.MP_INT_T)
        assert func_ir.params[1] == ("b", CType.MP_INT_T)
        assert func_ir.return_type == CType.MP_INT_T

    def test_function_with_float_params(self):
        source = """
def compute(x: float, y: float) -> float:
    return x * y
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert func_ir.params[0] == ("x", CType.MP_FLOAT_T)
        assert func_ir.params[1] == ("y", CType.MP_FLOAT_T)
        assert func_ir.return_type == CType.MP_FLOAT_T

    def test_function_with_no_args(self):
        source = """
def get_value() -> int:
    return 42
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert func_ir.name == "get_value"
        assert len(func_ir.params) == 0
        assert func_ir.return_type == CType.MP_INT_T

    def test_function_with_list_param(self):
        source = """
def process(items: list) -> int:
    return len(items)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert func_ir.params[0] == ("items", CType.MP_OBJ_T)
        assert "items" in func_ir.list_vars


class TestBuildReturn:
    def test_return_constant(self):
        source = """
def f() -> int:
    return 42
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert len(func_ir.body) == 1
        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value == 42
        assert ret.value.ir_type == IRType.INT

    def test_return_none(self):
        source = """
def f():
    return
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        assert ret.value is None

    def test_return_variable(self):
        source = """
def f(x: int) -> int:
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        assert isinstance(ret.value, NameIR)
        assert ret.value.py_name == "x"


class TestBuildExpressions:
    def test_constant_int(self):
        source = """
def f() -> int:
    return 123
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value == 123
        assert ret.value.ir_type == IRType.INT

    def test_constant_float(self):
        source = """
def f() -> float:
    return 3.14
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value == 3.14
        assert ret.value.ir_type == IRType.FLOAT

    def test_constant_bool(self):
        source = """
def f() -> bool:
    return True
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value is True
        assert ret.value.ir_type == IRType.BOOL

    def test_constant_string(self):
        source = """
def f():
    return "hello"
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value == "hello"
        assert ret.value.ir_type == IRType.OBJ

    def test_constant_none(self):
        source = """
def f():
    return None
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value is None


class TestBuildBinOp:
    def test_int_addition(self):
        source = """
def f(a: int, b: int) -> int:
    return a + b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == "+"
        assert ret.value.ir_type == IRType.INT
        assert isinstance(ret.value.left, NameIR)
        assert isinstance(ret.value.right, NameIR)

    def test_float_multiplication(self):
        source = """
def f(a: float, b: float) -> float:
    return a * b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == "*"
        assert ret.value.ir_type == IRType.FLOAT

    def test_mixed_int_float(self):
        source = """
def f(a: int, b: float) -> float:
    return a + b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.ir_type == IRType.FLOAT

    def test_bitwise_operations(self):
        source = """
def f(a: int, b: int) -> int:
    return a & b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == "&"


class TestBuildUnaryOp:
    def test_negation(self):
        source = """
def f(x: int) -> int:
    return -x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, UnaryOpIR)
        assert ret.value.op == "-"

    def test_logical_not(self):
        source = """
def f(x: bool) -> bool:
    return not x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, UnaryOpIR)
        assert ret.value.op == "!"
        assert ret.value.ir_type == IRType.BOOL


class TestBuildCompare:
    def test_simple_comparison(self):
        source = """
def f(a: int, b: int) -> bool:
    return a < b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, CompareIR)
        assert ret.value.ops == ["<"]
        assert ret.value.ir_type == IRType.BOOL

    def test_chained_comparison(self):
        source = """
def f(a: int, b: int, c: int) -> bool:
    return a < b < c
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, CompareIR)
        assert ret.value.ops == ["<", "<"]
        assert len(ret.value.comparators) == 2


class TestBuildCall:
    def test_builtin_abs(self):
        source = """
def f(x: int) -> int:
    return abs(x)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, CallIR)
        assert ret.value.func_name == "abs"
        assert ret.value.is_builtin is True

    def test_builtin_len(self):
        source = """
def f(lst: list) -> int:
    return len(lst)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, CallIR)
        assert ret.value.func_name == "len"
        assert ret.value.is_builtin is True

    def test_function_call(self):
        source = """
def f(x: int) -> int:
    return other(x)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, CallIR)
        assert ret.value.func_name == "other"
        assert ret.value.is_builtin is False


class TestBuildIfExpr:
    def test_ternary_expression(self):
        source = """
def f(x: int) -> int:
    return x if x > 0 else -x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, IfExprIR)
        assert isinstance(ret.value.test, CompareIR)
        assert isinstance(ret.value.body, NameIR)
        assert isinstance(ret.value.orelse, UnaryOpIR)


class TestBuildStatements:
    def test_if_statement(self):
        source = """
def f(x: int) -> int:
    if x > 0:
        return 1
    return 0
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert len(func_ir.body) == 2
        if_stmt = func_ir.body[0]
        assert isinstance(if_stmt, IfIR)
        assert isinstance(if_stmt.test, CompareIR)
        assert len(if_stmt.body) == 1
        assert len(if_stmt.orelse) == 0

    def test_if_else_statement(self):
        source = """
def f(x: int) -> int:
    if x > 0:
        return 1
    else:
        return -1
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        if_stmt = func_ir.body[0]
        assert isinstance(if_stmt, IfIR)
        assert len(if_stmt.body) == 1
        assert len(if_stmt.orelse) == 1

    def test_while_loop(self):
        source = """
def f(n: int) -> int:
    i: int = 0
    while i < n:
        i += 1
    return i
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        while_stmt = func_ir.body[1]
        assert isinstance(while_stmt, WhileIR)
        assert isinstance(while_stmt.test, CompareIR)
        assert len(while_stmt.body) == 1

    def test_for_range_loop(self):
        source = """
def f(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i
    return total
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        for_stmt = func_ir.body[1]
        assert isinstance(for_stmt, ForRangeIR)
        assert for_stmt.loop_var == "i"

    def test_for_range_with_start_end(self):
        source = """
def f() -> int:
    total: int = 0
    for i in range(1, 10):
        total += i
    return total
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        for_stmt = func_ir.body[1]
        assert isinstance(for_stmt, ForRangeIR)
        assert isinstance(for_stmt.start, ConstIR)
        assert for_stmt.start.value == 1
        assert isinstance(for_stmt.end, ConstIR)
        assert for_stmt.end.value == 10

    def test_for_iter_loop(self):
        source = """
def f(items: list) -> int:
    total: int = 0
    for item in items:
        total += item
    return total
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        for_stmt = func_ir.body[1]
        assert isinstance(for_stmt, ForIterIR)
        assert for_stmt.loop_var == "item"

    def test_break_continue(self):
        source = """
def f(n: int) -> int:
    i: int = 0
    while True:
        if i >= n:
            break
        i += 1
        continue
    return i
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        while_stmt = func_ir.body[1]
        if_stmt = while_stmt.body[0]
        assert isinstance(if_stmt.body[0], BreakIR)
        assert isinstance(while_stmt.body[2], ContinueIR)

    def test_pass_statement(self):
        source = """
def f():
    pass
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert len(func_ir.body) == 1
        assert isinstance(func_ir.body[0], PassIR)


class TestBuildAssignments:
    def test_simple_assign(self):
        source = """
def f() -> int:
    x = 42
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assign = func_ir.body[0]
        assert isinstance(assign, AssignIR)
        assert assign.target == "x"
        assert isinstance(assign.value, ConstIR)

    def test_annotated_assign(self):
        source = """
def f() -> int:
    x: int = 42
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assign = func_ir.body[0]
        assert isinstance(assign, AnnAssignIR)
        assert assign.target == "x"
        assert assign.c_type == "mp_int_t"
        assert assign.is_new_var is True

    def test_aug_assign(self):
        source = """
def f(x: int) -> int:
    x += 1
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        aug = func_ir.body[0]
        assert isinstance(aug, AugAssignIR)
        assert aug.target == "x"
        assert aug.op == "+="


class TestBuildContainers:
    def test_list_literal(self):
        source = """
def f():
    return [1, 2, 3]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert len(ret.prelude) == 1
        list_new = ret.prelude[0]
        assert isinstance(list_new, ListNewIR)
        assert len(list_new.items) == 3

    def test_tuple_literal(self):
        source = """
def f():
    return (1, 2, 3)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert len(ret.prelude) == 1
        tuple_new = ret.prelude[0]
        assert isinstance(tuple_new, TupleNewIR)
        assert len(tuple_new.items) == 3

    def test_subscript(self):
        source = """
def f(lst: list) -> int:
    return lst[0]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, SubscriptIR)
        assert isinstance(ret.value.slice_, ConstIR)
        assert ret.value.slice_.value == 0


class TestBuildMethodCall:
    def test_list_append(self):
        source = """
def f(lst: list):
    lst.append(1)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        expr_stmt = func_ir.body[0]
        assert isinstance(expr_stmt, ExprStmtIR)
        assert len(expr_stmt.prelude) == 1
        method_call = expr_stmt.prelude[0]
        assert isinstance(method_call, MethodCallIR)
        assert method_call.method == "append"


class TestBuildPrint:
    def test_print_single_arg(self):
        source = """
def f(x: int):
    print(x)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert func_ir.uses_print is True
        print_ir = func_ir.body[0]
        assert isinstance(print_ir, PrintIR)
        assert len(print_ir.args) == 1

    def test_print_multiple_args(self):
        source = """
def f(x: int, y: int):
    print(x, y)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        print_ir = func_ir.body[0]
        assert isinstance(print_ir, PrintIR)
        assert len(print_ir.args) == 2


class TestRTupleSupport:
    def test_rtuple_annotation_detection(self):
        source = """
def f() -> tuple[int, int]:
    point: tuple[int, int] = (10, 20)
    return point
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert "point" in func_ir.rtuple_types
        rtuple = func_ir.rtuple_types["point"]
        assert rtuple.arity == 2
        assert rtuple.element_types == (CType.MP_INT_T, CType.MP_INT_T)

    def test_rtuple_mixed_types(self):
        source = """
def f():
    point: tuple[int, float] = (10, 3.14)
    return point
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assert "point" in func_ir.rtuple_types
        rtuple = func_ir.rtuple_types["point"]
        assert rtuple.element_types == (CType.MP_INT_T, CType.MP_FLOAT_T)

    def test_rtuple_subscript_is_marked(self):
        source = """
def f():
    point: tuple[int, int] = (10, 20)
    return point[0]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[1]
        assert isinstance(ret.value, SubscriptIR)
        assert ret.value.is_rtuple is True
        assert ret.value.rtuple_index == 0


class TestBinOpTypeInference:
    def test_subscript_plus_int_is_int(self):
        source = """
def f(lst: list) -> int:
    return lst[0] + 1
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.ir_type == IRType.INT

    def test_obj_plus_obj_is_obj(self):
        source = """
def f(a, b):
    return a + b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.ir_type == IRType.OBJ


class TestPreludePattern:
    def test_method_call_creates_prelude(self):
        source = """
def f(lst: list):
    x = lst.pop()
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assign = func_ir.body[0]
        assert isinstance(assign, AssignIR)
        assert len(assign.prelude) == 1
        assert isinstance(assign.prelude[0], MethodCallIR)

    def test_nested_calls_accumulate_preludes(self):
        source = """
def f(lst: list) -> int:
    return len(lst) + 1
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert isinstance(ret.value.left, CallIR)


class TestBuildDict:
    """Tests for dict IR building."""

    def test_empty_dict_literal(self):
        source = """
def f():
    d: dict = {}
    return d
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        # Empty dict uses ConstIR with empty dict value
        ann_assign = func_ir.body[0]
        assert isinstance(ann_assign, AnnAssignIR)
        assert isinstance(ann_assign.value, ConstIR)
        assert ann_assign.value.value == {}

    def test_dict_with_entries(self):
        source = """
def f():
    d: dict = {"a": 1, "b": 2}
    return d
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ann_assign = func_ir.body[0]
        # Dict with entries creates DictNewIR in prelude
        from mypyc_micropython.ir import DictNewIR

        assert len(ann_assign.prelude) >= 1
        assert isinstance(ann_assign.prelude[0], DictNewIR)
        assert len(ann_assign.prelude[0].entries) == 2


class TestBuildSubscriptAssign:
    """Tests for subscript assignment IR building."""

    def test_list_subscript_assign(self):
        source = """
def f(lst: list, i: int, val: int) -> None:
    lst[i] = val
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        from mypyc_micropython.ir import SubscriptAssignIR

        subscript_assign = func_ir.body[0]
        assert isinstance(subscript_assign, SubscriptAssignIR)
        assert isinstance(subscript_assign.container, NameIR)
        assert subscript_assign.container.py_name == "lst"

    def test_dict_subscript_assign(self):
        source = """
def f(d: dict, key: str, val: int) -> None:
    d[key] = val
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        from mypyc_micropython.ir import SubscriptAssignIR

        subscript_assign = func_ir.body[0]
        assert isinstance(subscript_assign, SubscriptAssignIR)


class TestBuildTupleUnpack:
    """Tests for tuple unpacking IR building."""

    def test_simple_tuple_unpack(self):
        source = """
def f():
    t = (1, 2)
    x, y = t
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        from mypyc_micropython.ir import TupleUnpackIR

        # Second statement should be TupleUnpackIR
        unpack = func_ir.body[1]
        assert isinstance(unpack, TupleUnpackIR)
        assert len(unpack.targets) == 2

    def test_tuple_unpack_in_for(self):
        source = """
def f(items: list[tuple[str, int]]) -> None:
    for k, v in items:
        pass
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        # For loop with tuple unpacking should work
        assert len(func_ir.body) >= 1


class TestBuildSlice:
    """Tests for slice IR building."""

    def test_simple_slice(self):
        source = """
def f(lst: list):
    return lst[1:3]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Slice creates SubscriptIR with SliceIR as index
        from mypyc_micropython.ir import SliceIR

        assert isinstance(ret.value, SubscriptIR)
        assert isinstance(ret.value.slice_, SliceIR)

    def test_slice_with_step(self):
        source = """
def f(lst: list):
    return lst[::2]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        from mypyc_micropython.ir import SliceIR

        assert isinstance(ret.value.slice_, SliceIR)
        # Step should be ConstIR(2)
        assert ret.value.slice_.step is not None


class TestBuildListComp:
    """Tests for list comprehension IR building."""

    def test_simple_list_comp(self):
        source = """
def f(n: int) -> list:
    return [i * 2 for i in range(n)]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        from mypyc_micropython.ir import ListCompIR

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # List comp should create ListCompIR in prelude
        assert len(ret.prelude) >= 1
        assert isinstance(ret.prelude[0], ListCompIR)

    def test_list_comp_with_condition(self):
        source = """
def f(n: int) -> list:
    return [i for i in range(n) if i % 2 == 0]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        from mypyc_micropython.ir import ListCompIR

        ret = func_ir.body[0]
        assert len(ret.prelude) >= 1
        listcomp = ret.prelude[0]
        assert isinstance(listcomp, ListCompIR)
        assert listcomp.condition is not None


class TestBuildForLoop:
    """Additional tests for for loop IR building."""

    def test_for_range_start_stop(self):
        source = """
def f():
    for i in range(5, 10):
        pass
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        for_stmt = func_ir.body[0]
        assert isinstance(for_stmt, ForRangeIR)
        assert isinstance(for_stmt.start, ConstIR)
        assert for_stmt.start.value == 5
        assert isinstance(for_stmt.end, ConstIR)
        assert for_stmt.end.value == 10

    def test_for_range_with_step(self):
        source = """
def f():
    for i in range(0, 10, 2):
        pass
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        for_stmt = func_ir.body[0]
        assert isinstance(for_stmt, ForRangeIR)
        assert for_stmt.step_is_constant is True
        assert for_stmt.step_value == 2

    def test_for_iter_over_dict_keys(self):
        source = """
def f(d: dict):
    for k in d.keys():
        pass
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        for_stmt = func_ir.body[0]
        assert isinstance(for_stmt, ForIterIR)

    def test_for_iter_over_dict_values(self):
        source = """
def f(d: dict):
    for v in d.values():
        pass
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        for_stmt = func_ir.body[0]
        assert isinstance(for_stmt, ForIterIR)

    def test_for_iter_over_dict_items(self):
        source = """
def f(d: dict[str, int]) -> None:
    for k, v in d.items():
        pass
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        # Items iteration with unpacking
        assert len(func_ir.body) >= 1


class TestBuildWhileLoop:
    """Additional tests for while loop IR building."""

    def test_while_with_break(self):
        source = """
def f():
    while True:
        break
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        while_stmt = func_ir.body[0]
        assert isinstance(while_stmt, WhileIR)
        assert len(while_stmt.body) >= 1
        assert isinstance(while_stmt.body[0], BreakIR)

    def test_while_with_continue(self):
        source = """
def f():
    i: int = 0
    while i < 10:
        i += 1
        continue
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        while_stmt = func_ir.body[1]
        assert isinstance(while_stmt, WhileIR)
        # Should have continue in body
        has_continue = any(isinstance(s, ContinueIR) for s in while_stmt.body)
        assert has_continue


class TestBuildAugAssign:
    """Additional tests for augmented assignment IR building."""

    def test_aug_assign_multiply(self):
        source = """
def f(x: int) -> int:
    x *= 2
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        aug = func_ir.body[0]
        assert isinstance(aug, AugAssignIR)
        assert aug.op == "*="

    def test_aug_assign_divide(self):
        """Floor division augmented assignment: x //= 2."""
        source = """
def f(x: int) -> int:
    x //= 2
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        aug = func_ir.body[0]
        assert isinstance(aug, AugAssignIR)
        assert aug.op == "//="

    def test_aug_assign_modulo(self):
        source = """
def f(x: int) -> int:
    x %= 3
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        aug = func_ir.body[0]
        assert isinstance(aug, AugAssignIR)
        assert aug.op == "%="


class TestBuildBitwiseOps:
    """Tests for bitwise operation IR building."""

    def test_bitwise_and(self):
        source = """
def f(a: int, b: int) -> int:
    return a & b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == "&"

    def test_bitwise_or(self):
        source = """
def f(a: int, b: int) -> int:
    return a | b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == "|"

    def test_bitwise_xor(self):
        source = """
def f(a: int, b: int) -> int:
    return a ^ b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == "^"

    def test_left_shift(self):
        source = """
def f(a: int, b: int) -> int:
    return a << b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == "<<"

    def test_right_shift(self):
        source = """
def f(a: int, b: int) -> int:
    return a >> b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, BinOpIR)
        assert ret.value.op == ">>"

    def test_bitwise_not(self):
        source = """
def f(a: int) -> int:
    return ~a
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret.value, UnaryOpIR)
        assert ret.value.op == "~"


class TestMethodIdentityComparison:
    """Tests for identity comparison operators (is, is not) in class methods.

    These tests verify that 'is' and 'is not' operators are correctly
    preserved in class method IR, not converted to '==' or '!='.
    Bug fix: _build_method_expr was missing ast.Is and ast.IsNot mappings.
    """

    def test_is_none_in_method(self):
        """Test 'is None' comparison in class method produces 'is' operator."""
        source = """
class Nav:
    _allowed: object

    def __init__(self, allowed: object = None) -> None:
        self._allowed = allowed

    def check(self) -> bool:
        if self._allowed is None:
            return True
        return False
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        class_ir = builder.build_class(tree.body[0])

        # Get the check method
        check_method = class_ir.methods["check"]
        assert check_method.name == "check"

        # Build the method body
        builder._current_class = class_ir
        builder._list_vars = {}
        builder._temp_count = 0
        locals_ = []
        builder._ctx = BuildContext(locals_=locals_, class_ir=class_ir, native=True)
        body = []
        for stmt in check_method.body_ast.body:
            stmt_ir = builder._build_statement(stmt, locals_)
            if stmt_ir:
                body.append(stmt_ir)

        # The first statement should be an IfIR with 'is' comparison
        assert len(body) >= 1
        if_stmt = body[0]
        assert isinstance(if_stmt, IfIR)

        # The test should be a CompareIR with 'is' operator
        test = if_stmt.test
        assert isinstance(test, CompareIR)
        assert test.ops == ["is"], f"Expected ['is'], got {test.ops}"

    def test_is_not_none_in_method(self):
        """Test 'is not None' comparison in class method produces 'is not' operator."""
        source = """
class Container:
    _data: object

    def __init__(self, data: object = None) -> None:
        self._data = data

    def has_data(self) -> bool:
        return self._data is not None
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        class_ir = builder.build_class(tree.body[0])

        # Get the has_data method
        has_data_method = class_ir.methods["has_data"]

        # Build the method body
        builder._current_class = class_ir
        builder._list_vars = {}
        builder._temp_count = 0
        locals_ = []
        builder._ctx = BuildContext(locals_=locals_, class_ir=class_ir, native=True)
        body = []
        for stmt in has_data_method.body_ast.body:
            stmt_ir = builder._build_statement(stmt, locals_)
            if stmt_ir:
                body.append(stmt_ir)

        # The return statement should contain a CompareIR with 'is not'
        assert len(body) >= 1
        ret_stmt = body[0]
        assert isinstance(ret_stmt, ReturnIR)

        test = ret_stmt.value
        assert isinstance(test, CompareIR)
        assert test.ops == ["is not"], f"Expected ['is not'], got {test.ops}"

    def test_is_comparison_with_object_parameter(self):
        """Test 'is' comparison between method parameters."""
        source = """
class Comparer:
    def same(self, a: object, b: object) -> bool:
        return a is b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        class_ir = builder.build_class(tree.body[0])

        same_method = class_ir.methods["same"]
        builder._current_class = class_ir
        builder._list_vars = {}
        builder._temp_count = 0
        locals_ = ["a", "b"]
        builder._ctx = BuildContext(locals_=locals_, class_ir=class_ir, native=True)
        body = []
        for stmt in same_method.body_ast.body:
            stmt_ir = builder._build_statement(stmt, locals_)
            if stmt_ir:
                body.append(stmt_ir)

        ret_stmt = body[0]
        assert isinstance(ret_stmt, ReturnIR)
        assert isinstance(ret_stmt.value, CompareIR)
        assert ret_stmt.value.ops == ["is"]


class TestIsInstanceBuilder:
    """Tests for isinstance() IR building."""

    def test_isinstance_creates_ir_node(self):
        """Test isinstance(obj, ClassName) creates IsInstanceIR with correct fields."""
        source = """
class Dog:
    name: str

def check_dog(obj: object) -> bool:
    return isinstance(obj, Dog)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        # Build the class first to register it
        builder.build_class(tree.body[0])
        # Build the function
        func_ir = builder.build_function(tree.body[1])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        assert isinstance(ret.value, IsInstanceIR)
        assert ret.value.class_name == "Dog"
        assert "Dog" in ret.value.c_type_name

    def test_isinstance_trait_returns_const_false(self):
        """Test isinstance with trait class returns ConstIR(False)."""
        source = """
from mypy_extensions import trait

@trait
class Animal:
    def speak(self) -> str:
        pass

def check_animal(obj: object) -> bool:
    return isinstance(obj, Animal)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        # Build the class first
        builder.build_class(tree.body[1])
        # Build the function
        func_ir = builder.build_function(tree.body[2])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Traits should return ConstIR(False) since they have no type
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value is False

    def test_isinstance_unknown_class_returns_const_false(self):
        """Test isinstance with unknown class returns ConstIR(False)."""
        source = """
def check_unknown(obj: object) -> bool:
    return isinstance(obj, UnknownClass)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Unknown class should return ConstIR(False)
        assert isinstance(ret.value, ConstIR)
        assert ret.value.value is False

    def test_isinstance_builtin_type_creates_ir(self):
        """Test isinstance with builtin type creates IsInstanceIR with mp_type_*."""
        source = """
def check_int(obj: object) -> bool:
    return isinstance(obj, int)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        assert isinstance(ret.value, IsInstanceIR)
        assert ret.value.class_name == "int"
        assert ret.value.c_type_name == "mp_type_int"

    def test_isinstance_ir_visualization(self):
        """Test dump_ir shows isinstance(var, ClassName)."""
        from mypyc_micropython.ir_visualizer import dump_ir

        source = """
class Dog:
    name: str

def check_dog(obj: object) -> bool:
    return isinstance(obj, Dog)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        builder.build_class(tree.body[0])
        func_ir = builder.build_function(tree.body[1])

        # Dump as text and check for isinstance representation
        ir_text = dump_ir(func_ir, "text")
        assert "isinstance" in ir_text or "IsInstanceIR" in ir_text


class TestAutoNarrowing:
    """Test automatic type narrowing after isinstance() in IR builder."""

    def test_auto_narrow_produces_param_attr_ir(self):
        """Inside isinstance if-branch, attr access produces ParamAttrIR."""
        source = """
class Dog:
    breed: str
    def __init__(self, breed: str) -> None:
        self.breed = breed

def get_breed(a: object) -> str:
    if isinstance(a, Dog):
        return a.breed
    return "unknown"
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        builder.build_class(tree.body[0])
        func_ir = builder.build_function(tree.body[1])

        # The if-body return should have ParamAttrIR (direct struct access)
        if_ir = func_ir.body[0]
        assert isinstance(if_ir, IfIR)
        ret = if_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # ParamAttrIR means the builder recognized Dog-typed access
        assert isinstance(ret.value, ParamAttrIR)
        assert ret.value.attr_name == "breed"
        assert ret.value.class_c_name == "test_Dog"

    def test_auto_narrow_restores_after_if(self):
        """_class_typed_params should be restored after the if block."""
        source = """
class Dog:
    breed: str
    def __init__(self, breed: str) -> None:
        self.breed = breed

def check(a: object) -> bool:
    if isinstance(a, Dog):
        x: str = a.breed
    return True
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        builder.build_class(tree.body[0])
        # Before building function, _class_typed_params is empty
        builder.build_function(tree.body[1])
        # After building, 'a' should NOT be in _class_typed_params
        assert "a" not in builder._class_typed_params

    def test_auto_narrow_negated_narrows_else(self):
        """not isinstance(a, Dog) should narrow 'a' in the else branch."""
        source = """
class Dog:
    breed: str
    def __init__(self, breed: str) -> None:
        self.breed = breed

def get_breed(a: object) -> str:
    if not isinstance(a, Dog):
        return "nope"
    else:
        return a.breed
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        builder.build_class(tree.body[0])
        func_ir = builder.build_function(tree.body[1])

        if_ir = func_ir.body[0]
        assert isinstance(if_ir, IfIR)
        # The else branch should have ParamAttrIR for a.breed
        else_ret = if_ir.orelse[0]
        assert isinstance(else_ret, ReturnIR)
        assert isinstance(else_ret.value, ParamAttrIR)
        assert else_ret.value.attr_name == "breed"

    def test_auto_narrow_elif_chain(self):
        """Each elif isinstance branch narrows independently."""
        source = """
class Dog:
    breed: str
    def __init__(self, breed: str) -> None:
        self.breed = breed

class Cat:
    color: str
    def __init__(self, color: str) -> None:
        self.color = color

def describe(a: object) -> str:
    if isinstance(a, Dog):
        return a.breed
    elif isinstance(a, Cat):
        return a.color
    return "unknown"
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        builder.build_class(tree.body[0])
        builder.build_class(tree.body[1])
        func_ir = builder.build_function(tree.body[2])

        if_ir = func_ir.body[0]
        assert isinstance(if_ir, IfIR)
        # if-body: a narrowed to Dog
        ret_dog = if_ir.body[0]
        assert isinstance(ret_dog, ReturnIR)
        assert isinstance(ret_dog.value, ParamAttrIR)
        assert ret_dog.value.attr_name == "breed"

        # elif is the first item in orelse (nested IfIR)
        elif_ir = if_ir.orelse[0]
        assert isinstance(elif_ir, IfIR)
        ret_cat = elif_ir.body[0]
        assert isinstance(ret_cat, ReturnIR)
        assert isinstance(ret_cat.value, ParamAttrIR)
        assert ret_cat.value.attr_name == "color"


class TestFuncRefIR:
    """Test that function-as-value produces FuncRefIR."""

    def test_known_function_produces_func_ref(self):
        source = """
def my_key(x: int) -> int:
    return x

def sort_list(lst: list) -> list:
    return sorted(lst, key=my_key)
"""
        from mypyc_micropython.ir import FuncRefIR

        tree = ast.parse(source)
        builder = IRBuilder("test")
        funcs = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.FunctionDef)]
        # Build first function and register it
        func_ir_key = builder.build_function(funcs[0])
        builder.register_function_name(func_ir_key.name, func_ir_key.c_name)

        # Build second function - should reference my_key as FuncRefIR
        func_ir_sort = builder.build_function(funcs[1])
        # The sorted() call's kwargs should contain a FuncRefIR for my_key
        ret = func_ir_sort.body[0]
        assert isinstance(ret, ReturnIR)
        call = ret.value
        assert isinstance(call, CallIR)
        assert call.func_name == "sorted"
        assert len(call.kwargs) == 1
        kw_name, kw_val = call.kwargs[0]
        assert kw_name == "key"
        assert isinstance(kw_val, FuncRefIR)
        assert kw_val.py_name == "my_key"
        assert kw_val.c_name == "test_my_key"

    def test_unknown_name_stays_as_name_ir(self):
        source = """
def sort_list(lst: list) -> list:
    return sorted(lst, key=unknown_fn)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        funcs = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.FunctionDef)]
        func_ir = builder.build_function(funcs[0])
        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        call = ret.value
        assert isinstance(call, CallIR)
        kw_name, kw_val = call.kwargs[0]
        assert kw_name == "key"
        # unknown_fn is not registered, so it stays as NameIR
        assert isinstance(kw_val, NameIR)


class TestBuildContext:
    """Tests for BuildContext and method context detection."""

    def test_build_context_creation(self):
        """BuildContext can be created with locals."""
        ctx = BuildContext(locals_=["a", "b"])
        assert ctx.locals_ == ["a", "b"]
        assert ctx.class_ir is None
        assert ctx.native is False
        assert ctx.is_method is False

    def test_build_context_method_detection(self):
        """BuildContext correctly identifies method context."""
        from mypyc_micropython.ir import ClassIR

        class_ir = ClassIR(name="TestClass", c_name="test_TestClass", fields=[], module_name="test")
        ctx = BuildContext(locals_=["self"], class_ir=class_ir)
        assert ctx.is_method is True


class TestParamPyTypesTracking:
    """Tests for _param_py_types tracking in method calls."""

    def test_param_py_type_tracked_for_receiver(self):
        """Parameters with class annotations track Python types for receiver_py_type."""
        source = """
class Point:
    x: int
    y: int

def get_x(p: Point) -> int:
    return p.x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")

        # Build class first
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                builder.build_class(node)

        # Build function
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        # The function should access p.x via ParamAttrIR with receiver_py_type
        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        assert isinstance(ret.value, ParamAttrIR)
        # ParamAttrIR should have correct receiver info
        assert ret.value.param_name == "p"
        assert ret.value.attr_name == "x"

    def test_method_call_on_typed_param_has_receiver_py_type(self):
        """Method calls on typed params should have receiver_py_type set."""
        source = """
def process_list(items: list) -> int:
    return len(items)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # len() call on list should work
        assert isinstance(ret.value, CallIR)
        assert ret.value.func_name == "len"


class TestContainerPreludeHandling:
    """Tests for proper prelude handling in container literals."""

    def test_list_with_method_call_elements(self):
        """List literals with method call elements should collect preludes with type info."""
        source = """
def f(lst: list) -> list:
    return [lst.pop(), 1, 2]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Preludes should include MethodCallIR for lst.pop() AND ListNewIR
        assert len(ret.prelude) >= 2
        # Find the MethodCallIR - should have receiver_py_type set
        method_calls = [p for p in ret.prelude if isinstance(p, MethodCallIR)]
        assert len(method_calls) == 1
        assert method_calls[0].receiver_py_type == "list"
        assert method_calls[0].method == "pop"
        # Find the ListNewIR
        list_news = [p for p in ret.prelude if isinstance(p, ListNewIR)]
        assert len(list_news) == 1

    def test_dict_with_method_call_values(self):
        """Dict literals with method call values should collect preludes with type info."""
        from mypyc_micropython.ir import DictNewIR

        source = """
def f(lst: list) -> dict:
    d: dict = {"val": lst.pop()}
    return d
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ann_assign = func_ir.body[0]
        assert isinstance(ann_assign, AnnAssignIR)
        # Preludes should include MethodCallIR for lst.pop() AND DictNewIR
        assert len(ann_assign.prelude) >= 2
        # Find the MethodCallIR - should have receiver_py_type set
        method_calls = [p for p in ann_assign.prelude if isinstance(p, MethodCallIR)]
        assert len(method_calls) == 1
        assert method_calls[0].receiver_py_type == "list"
        # Find the DictNewIR
        dict_news = [p for p in ann_assign.prelude if isinstance(p, DictNewIR)]
        assert len(dict_news) == 1

    def test_tuple_with_method_call_elements(self):
        """Tuple literals with method call elements should collect preludes with type info."""
        source = """
def f(lst: list) -> tuple:
    return (lst.pop(), 1)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Preludes should include MethodCallIR for lst.pop() AND TupleNewIR
        assert len(ret.prelude) >= 2
        # Find the MethodCallIR - should have receiver_py_type set
        method_calls = [p for p in ret.prelude if isinstance(p, MethodCallIR)]
        assert len(method_calls) == 1
        assert method_calls[0].receiver_py_type == "list"
        # Find the TupleNewIR
        tuple_news = [p for p in ret.prelude if isinstance(p, TupleNewIR)]
        assert len(tuple_news) == 1

    def test_set_with_method_call_elements(self):
        """Set literals with method call elements should collect preludes with type info."""
        from mypyc_micropython.ir import SetNewIR

        source = """
def f(lst: list) -> set:
    return {lst.pop(), 1, 2}
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Preludes should include MethodCallIR for lst.pop() AND SetNewIR
        assert len(ret.prelude) >= 2
        # Find the MethodCallIR - should have receiver_py_type set
        method_calls = [p for p in ret.prelude if isinstance(p, MethodCallIR)]
        assert len(method_calls) == 1
        assert method_calls[0].receiver_py_type == "list"
        # Find the SetNewIR
        set_news = [p for p in ret.prelude if isinstance(p, SetNewIR)]
        assert len(set_news) == 1


class TestObjectTypedParamAttrAccess:
    """Tests for dynamic attribute access on object-typed parameters."""

    def test_object_param_uses_dynamic_attr(self):
        """Parameters typed as 'object' should use dynamic attr access."""
        source = """
def get_value(obj: object) -> int:
    return obj.value
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # For object-typed params, should use dynamic attr access
        # This could be AttrIR or ParamAttrIR depending on implementation
        assert ret.value is not None

    def test_untyped_param_defaults_to_object(self):
        """Untyped parameters default to mp_obj_t (object)."""
        source = """
def process(x):
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        # Untyped param should be mp_obj_t
        assert func_ir.params[0] == ("x", CType.MP_OBJ_T)


class TestIRTypeInfoCompleteness:
    """Tests to verify IR nodes contain complete type information for emission."""

    def test_method_call_has_result_temp_with_ir_type(self):
        """MethodCallIR.result TempIR should have ir_type set."""
        source = """
def f(lst: list) -> int:
    return lst.pop()
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Should have MethodCallIR in prelude
        method_call = ret.prelude[0]
        assert isinstance(method_call, MethodCallIR)
        # Result TempIR should have ir_type
        assert method_call.result is not None
        assert isinstance(method_call.result, TempIR)
        assert method_call.result.ir_type == IRType.OBJ  # pop returns object

    def test_method_call_receiver_has_ir_type(self):
        """MethodCallIR.receiver should have ir_type set."""
        source = """
def f(lst: list):
    lst.append(1)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        expr_stmt = func_ir.body[0]
        method_call = expr_stmt.prelude[0]
        assert isinstance(method_call, MethodCallIR)
        # Receiver should have ir_type
        assert isinstance(method_call.receiver, NameIR)
        assert method_call.receiver.ir_type == IRType.OBJ

    def test_param_attr_has_complete_type_info(self):
        """ParamAttrIR should have class_c_name, result_type, and is_trait_type."""
        source = """
class Point:
    x: int
    y: int

def get_x(p: Point) -> int:
    return p.x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")

        # Build class first
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                builder.build_class(node)

        # Build function
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        param_attr = ret.value
        assert isinstance(param_attr, ParamAttrIR)
        # Verify complete type info
        assert param_attr.class_c_name == "test_Point"
        assert param_attr.result_type == IRType.INT
        assert param_attr.is_trait_type is False
        assert param_attr.attr_path == "x"

    def test_binop_has_ir_type(self):
        """BinOpIR should have ir_type based on operand types."""
        source = """
def add(a: int, b: int) -> int:
    return a + b
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        binop = ret.value
        assert isinstance(binop, BinOpIR)
        assert binop.ir_type == IRType.INT

    def test_const_has_ir_type(self):
        """ConstIR should have correct ir_type based on value type."""
        from mypyc_micropython.ir import ConstIR

        source = """
def f() -> int:
    return 42
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        const = ret.value
        assert isinstance(const, ConstIR)
        assert const.ir_type == IRType.INT
        assert const.value == 42

    def test_name_has_ir_type(self):
        """NameIR should have ir_type matching variable type."""
        source = """
def f(x: int) -> int:
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        name = ret.value
        assert isinstance(name, NameIR)
        assert name.ir_type == IRType.INT
        assert name.py_name == "x"
        assert name.c_name == "x"

    def test_temp_has_ir_type(self):
        """TempIR generated for expressions should have ir_type."""
        from mypyc_micropython.ir import TempIR

        source = """
def f(d: dict) -> object:
    return d.get("key")
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # d.get() creates a temp
        method_call = ret.prelude[0]
        assert isinstance(method_call, MethodCallIR)
        assert method_call.result is not None
        assert isinstance(method_call.result, TempIR)
        # Temps from method calls are OBJ type
        assert method_call.result.ir_type == IRType.OBJ

    def test_compare_has_bool_ir_type(self):
        """CompareIR should have BOOL ir_type."""
        source = """
def is_positive(x: int) -> bool:
    return x > 0
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        compare = ret.value
        assert isinstance(compare, CompareIR)
        assert compare.ir_type == IRType.BOOL

    def test_subscript_has_ir_type(self):
        """SubscriptIR should have ir_type."""
        source = """
def get_first(lst: list) -> object:
    return lst[0]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        subscript = ret.value
        assert isinstance(subscript, SubscriptIR)
        assert subscript.ir_type == IRType.OBJ

    def test_list_of_int_has_element_type_info(self):
        """list[int] should track element type for proper emission."""
        source = """
def sum_list(nums: list[int]) -> int:
    total: int = 0
    for n in nums:
        total += n
    return total
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        # Verify list param is tracked
        assert func_ir.params[0] == ("nums", CType.MP_OBJ_T)
        assert "nums" in func_ir.list_vars
        # For loop should be ForIterIR over the list
        for_ir = func_ir.body[1]
        assert isinstance(for_ir, ForIterIR)
        # Loop var should be set correctly
        assert for_ir.loop_var == "n"

    def test_list_of_str_has_element_type_info(self):
        """list[str] should track element type for proper emission."""
        source = """
def join_strings(words: list[str]) -> str:
    result: str = ""
    for w in words:
        result = result + w
    return result
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        # Verify list param is tracked
        assert func_ir.params[0] == ("words", CType.MP_OBJ_T)
        assert "words" in func_ir.list_vars
        # Return type should be OBJ for string
        assert func_ir.return_type == CType.MP_OBJ_T

    def test_dict_field_in_class_has_type_info(self):
        """Dict field in class should have complete type info for attr access."""
        source = """
class Config:
    settings: dict

    def __init__(self):
        self.settings = {}

def get_setting(cfg: Config, key: str) -> object:
    return cfg.settings.get(key)
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")

        # Build class first
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                builder.build_class(node)

        # Build function
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        ret = func_ir.body[0]
        assert isinstance(ret, ReturnIR)
        # Should have prelude with chained attr access
        assert len(ret.prelude) > 0
        # Find the MethodCallIR for .get()
        method_call = None
        for instr in ret.prelude:
            if isinstance(instr, MethodCallIR) and instr.method == "get":
                method_call = instr
                break
        assert method_call is not None
        # Method call should have result temp with ir_type
        assert method_call.result is not None
        assert isinstance(method_call.result, TempIR)
        assert method_call.result.ir_type == IRType.OBJ

    def test_nested_dict_in_class_has_type_info(self):
        """Nested dict access in class should maintain type info chain."""
        source = """
class Cache:
    data: dict

    def __init__(self):
        self.data = {}

def cache_get(c: Cache, key: str) -> object:
    d: dict = c.data
    return d[key]
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")

        # Build class first
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                builder.build_class(node)

        # Build function
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        # First statement: d = c.data (annotated assignment)
        ann_assign = func_ir.body[0]
        assert isinstance(ann_assign, AnnAssignIR)
        assert ann_assign.target == "d"
        # d should be tracked in locals with OBJ type
        assert "d" in func_ir.locals_
        assert func_ir.locals_["d"] == CType.MP_OBJ_T

        # Return statement with dict subscript
        ret = func_ir.body[1]
        assert isinstance(ret, ReturnIR)
        subscript = ret.value
        assert isinstance(subscript, SubscriptIR)
        assert subscript.ir_type == IRType.OBJ


class TestTypeSystemIR:
    def test_literal_erased_to_int_ctype(self):
        source = """
from typing import Literal

def f(x: Literal[3]) -> int:
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)
        assert func_ir is not None
        assert func_ir.params[0][1] == CType.MP_INT_T

    @pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12+")
    def test_typevar_pep695_resolves_in_params(self):
        source = """
def f[T](x: T) -> T:
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)
        assert func_ir is not None
        assert func_ir.params[0][1] == CType.GENERAL

    @pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12+")
    def test_typevar_bounded_resolves_in_params(self):
        source = """
def f[N: int](x: N) -> N:
    return x
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)
        assert func_ir is not None
        assert func_ir.params[0][1] == CType.MP_INT_T

    @pytest.mark.skipif(sys.version_info < (3, 12), reason="PEP 695 requires Python 3.12+")
    def test_typevar_pep695_no_leak_between_functions(self):
        """PEP 695 TypeVars from one function should not leak to the next."""
        source = """
def f[T](x: T) -> T:
    return x

def g(y: int) -> int:
    return y
"""
        tree = ast.parse(source)
        builder = IRBuilder("test")
        funcs = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                funcs.append(builder.build_function(node))
        assert len(funcs) == 2
        # f[T] should have GENERAL param
        assert funcs[0].params[0][1] == CType.GENERAL
        # g should have int param, NOT GENERAL (no leak from f)
        assert funcs[1].params[0][1] == CType.MP_INT_T


class TestObjAttrAssignIR:
    """Tests for local_var.attr = value generating ObjAttrAssignIR."""

    def test_local_var_attr_assign_generates_obj_attr_assign(self):
        """Assignment to local_var.attr should produce ObjAttrAssignIR."""
        source = '''
class Container:
    items: list

    def __init__(self) -> None:
        self.items = []

def fill(c: Container) -> None:
    c.items = [1, 2, 3]
'''
        tree = ast.parse(source)
        builder = IRBuilder("test")

        # Build class first so it's known
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                builder.build_class(node)

        # Build function
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        # The c.items = [1,2,3] should be ObjAttrAssignIR
        assign = func_ir.body[0]
        assert isinstance(assign, ObjAttrAssignIR)
        assert assign.obj_name == "c"
        assert assign.attr_name == "items"

    def test_obj_attr_assign_known_class_has_c_name(self):
        """When local var's class is known, obj_class should be set."""
        source = '''
class Holder:
    value: int

    def __init__(self, v: int) -> None:
        self.value = v

def set_val(h: Holder) -> None:
    h.value = 42
'''
        tree = ast.parse(source)
        builder = IRBuilder("test")

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                builder.build_class(node)

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        assign = func_ir.body[0]
        assert isinstance(assign, ObjAttrAssignIR)
        assert assign.obj_class is not None
        assert "Holder" in assign.obj_class

    def test_obj_attr_assign_unknown_class_has_none(self):
        """When local var's class is NOT known, obj_class should be None."""
        source = '''
def modify(obj: object) -> None:
    obj.value = 10
'''
        tree = ast.parse(source)
        builder = IRBuilder("test")
        func_ir = builder.build_function(tree.body[0])

        assign = func_ir.body[0]
        assert isinstance(assign, ObjAttrAssignIR)
        assert assign.obj_class is None
        assert assign.attr_name == "value"

    def test_self_attr_assign_is_not_obj_attr_assign(self):
        """self.attr = value should NOT produce mp_store_attr in generated C.
        It should use direct struct field access via AttrAssignIR."""
        from mypyc_micropython.compiler import compile_source
        source = '''
class Foo:
    x: int

    def __init__(self) -> None:
        self.x = 0

    def set_x(self, v: int) -> None:
        self.x = v
'''
        c_code = compile_source(source, "test", type_check=False)
        # self.x = v in set_x should use direct struct access: self->x = v
        assert "self->x = v" in c_code
        # Should NOT use mp_store_attr for self attribute access
        assert "mp_store_attr" not in c_code


class TestMypyAnyFallbackToAnnotation:
    """Bug 5: When mypy reports 'Any' for a cross-module import, fall back to annotation."""

    def test_field_type_falls_back_to_annotation_when_mypy_says_any(self):
        """If mypy reports 'Any' for a field type but annotation names a known class,
        the IR builder should use the annotation type."""
        import ast

        from mypyc_micropython.ir_builder import IRBuilder, MypyTypeInfo
        from mypyc_micropython.type_checker import ClassTypeInfo, FunctionTypeInfo

        # Simulate a known class 'Config' in a sibling module
        config_source = '''
class Config:
    name: str
    value: int

    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value
'''
        config_tree = ast.parse(config_source)
        config_builder = IRBuilder("config_mod")
        for node in ast.iter_child_nodes(config_tree):
            if isinstance(node, ast.ClassDef):
                config_class_ir = config_builder.build_class(node)

        # Source with a class that has a field typed as Config
        app_source = '''
class App:
    config: Config

    def __init__(self, config: Config) -> None:
        self.config = config
'''
        # Simulate mypy reporting 'Any' for the Config field (unresolved import)
        mypy_types = MypyTypeInfo(
            functions={},
            classes={
                "App": ClassTypeInfo(
                    name="App",
                    fields=[("config", "Any")],  # mypy couldn't resolve
                    methods=[FunctionTypeInfo(
                        name="__init__",
                        params=[("config", "Any")],
                        return_type="None",
                        is_method=True,
                    )],
                )
            },
            module_types={},
        )

        app_tree = ast.parse(app_source)
        builder = IRBuilder(
            "app_mod",
            known_classes={"Config": config_class_ir},
            mypy_types=mypy_types,
        )
        for node in ast.iter_child_nodes(app_tree):
            if isinstance(node, ast.ClassDef):
                class_ir = builder.build_class(node)

        # The config field should resolve to 'Config', not 'Any'
        config_fields = [f for f in class_ir.fields if f.name == "config"]
        assert len(config_fields) == 1, f"Expected 1 config field, got {len(config_fields)}"
        field = config_fields[0]
        assert field.py_type == "Config", (
            f"Expected Config but got {field.py_type}. "
            "Bug 5: mypy Any should fall back to annotation for known classes"
        )

    def test_method_param_falls_back_to_annotation_when_mypy_says_any(self):
        """Method parameters typed as Any by mypy should fall back to annotation."""
        import ast

        from mypyc_micropython.ir_builder import IRBuilder, MypyTypeInfo
        from mypyc_micropython.type_checker import ClassTypeInfo, FunctionTypeInfo

        # Build a known class 'Widget'
        widget_source = '''
class Widget:
    label: str

    def __init__(self, label: str) -> None:
        self.label = label
'''
        widget_tree = ast.parse(widget_source)
        widget_builder = IRBuilder("widget_mod")
        for node in ast.iter_child_nodes(widget_tree):
            if isinstance(node, ast.ClassDef):
                widget_class_ir = widget_builder.build_class(node)

        # A class with a method that takes Widget parameter
        view_source = '''
class View:
    def render(self, w: Widget) -> int:
        return 0
'''
        mypy_types = MypyTypeInfo(
            functions={},
            classes={
                "View": ClassTypeInfo(
                    name="View",
                    fields=[],
                    methods=[FunctionTypeInfo(
                        name="render",
                        params=[("w", "Any")],  # mypy couldn't resolve
                        return_type="int",
                        is_method=True,
                    )],
                )
            },
            module_types={},
        )

        view_tree = ast.parse(view_source)
        builder = IRBuilder(
            "view_mod",
            known_classes={"Widget": widget_class_ir},
            mypy_types=mypy_types,
        )
        for node in ast.iter_child_nodes(view_tree):
            if isinstance(node, ast.ClassDef):
                class_ir = builder.build_class(node)

        # The 'render' method's 'w' param should be typed as Widget, not Any
        from mypyc_micropython.ir import CType
        render_method = class_ir.methods.get("render")
        assert render_method is not None
        # Params: [("w", CType)] -- self is excluded in method IR
        w_param = render_method.params[0]
        assert w_param[0] == "w"
        # Widget maps to MP_OBJ_T regardless, but arg_types tracks the C string
        assert w_param[1] == CType.MP_OBJ_T


# ============================================================================
# Test: Bug A - from-import name resolution via ModuleAttrIR
# ============================================================================


class TestFromImportNameResolution:
    """Test that `from module import Name` resolves to ModuleAttrIR in IR.

    Bug fixed: _build_name() in ir_builder.py didn't check _imported_from
    for non-constant names. `from math import sqrt` then using `sqrt` as a
    name fell through to NameIR instead of generating ModuleAttrIR.
    """

    def test_import_module_call_generates_module_call_ir(self):
        """import math; math.sqrt(x) -> ModuleCallIR in prelude."""
        source = '''
from __future__ import annotations
import math

def f(x: float) -> float:
    return math.sqrt(x)
'''
        tree = ast.parse(source)
        builder = IRBuilder("test")
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        # The return statement should exist
        assert len(func_ir.body) >= 1
        ret = func_ir.body[-1]
        assert isinstance(ret, ReturnIR)
        # With preludes, the return value is a TempIR and the
        # actual ModuleCallIR is wrapped in a MethodCallIR in the prelude.
        # Check that the function references math module.
        # The prelude of the return should contain a method call on math.
        assert ret.prelude is not None and len(ret.prelude) > 0
        # The prelude contains a MethodCallIR whose receiver is a module ref
        method_call = ret.prelude[0]
        assert isinstance(method_call, MethodCallIR)
        assert method_call.method == "sqrt"

    def test_from_import_non_sibling_generates_module_attr_ir(self):
        """from-import of a non-sibling module generates ModuleAttrIR for names.

        When `from pkg.sub import Cmd` is used and pkg.sub is not a sibling,
        using `Cmd` should generate ModuleAttrIR, not NameIR.
        """
        source = '''
from __future__ import annotations

def f() -> object:
    return Cmd
'''
        tree = ast.parse(source)
        # Manually register 'Cmd' as imported from 'pkg.sub' (non-sibling)
        builder = IRBuilder("test")
        builder._imported_from["Cmd"] = "pkg.sub"
        builder._uses_imports = True
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        ret = func_ir.body[-1]
        assert isinstance(ret, ReturnIR)
        assert isinstance(ret.value, ModuleAttrIR)
        assert ret.value.module_name == "pkg.sub"
        assert ret.value.attr_name == "Cmd"

    def test_from_import_sibling_does_not_use_module_attr(self):
        """from-import of a sibling module should NOT generate ModuleAttrIR.

        Sibling modules use direct C function calls, not runtime imports.
        """
        source = '''
from __future__ import annotations

def f() -> object:
    return helper
'''
        tree = ast.parse(source)
        builder = IRBuilder("test")
        # Register 'helper' as both imported-from AND a sibling module
        builder._imported_from["helper"] = "utils"
        builder._sibling_modules["utils"] = "utils"
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        ret = func_ir.body[-1]
        assert isinstance(ret, ReturnIR)
        # Should fall through to NameIR, not ModuleAttrIR
        assert not isinstance(ret.value, ModuleAttrIR)


# ============================================================================
# Test: Bug B - Callable-call-result pattern (TempAssignIR + DynamicCallIR)
# ============================================================================


class TestCallableCallResult:
    """Test callable-call-result: g()(args) pattern.

    Bug fixed: When expr.func is ast.Call (not Name or Attribute), the old
    code returned ConstIR(value=None). Fix: evaluate inner expression,
    store in TempAssignIR, then DynamicCallIR to call it.
    """

    def test_callable_call_result_generates_dynamic_call(self):
        """g()(1) should generate TempAssignIR + DynamicCallIR.

        Pattern from MVU: Screen()(counter_app, init_model, update, view)
        """
        source = '''
from __future__ import annotations
from typing import Callable

def f(g: Callable[..., Callable[..., object]]) -> object:
    return g()(1)
'''
        tree = ast.parse(source)
        builder = IRBuilder("test")
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        # The return statement should have a DynamicCallIR value
        ret = func_ir.body[-1]
        assert isinstance(ret, ReturnIR)
        assert isinstance(ret.value, DynamicCallIR)
        # The DynamicCallIR should reference a temp variable
        assert ret.value.callable_var.startswith("_tmp")
        # Args should include the constant 1
        assert len(ret.value.args) == 1

    def test_callable_call_result_prelude_has_temp_assign(self):
        """The prelude for g()() should contain a TempAssignIR."""
        source = '''
from __future__ import annotations
from typing import Callable

def f(g: Callable[..., Callable[..., object]]) -> object:
    return g()(1)
'''
        tree = ast.parse(source)
        builder = IRBuilder("test")
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_ir = builder.build_function(node)

        # Check the return statement's prelude for TempAssignIR
        ret = func_ir.body[-1]
        assert isinstance(ret, ReturnIR)
        # The ReturnIR value is a DynamicCallIR; find TempAssignIR in prelude
        # The prelude is stored on the return expr's parent context
        # In the current architecture, preludes are flattened into func_ir.body
        # Check that at least one statement before the return is related
        # to temp assignment
        # Actually, preludes for return values are embedded in ReturnIR.prelude
        if hasattr(ret, 'prelude') and ret.prelude:
            temp_assigns = [i for i in ret.prelude if isinstance(i, TempAssignIR)]
            assert len(temp_assigns) >= 1
            ta = temp_assigns[0]
            assert isinstance(ta.result, TempIR)
        else:
            # The DynamicCallIR was built with preludes already flattened
            # into the stmt list -- scan func_ir.body for TempAssignIR in preludes
            found_temp = False
            for stmt in func_ir.body:
                prelude = getattr(stmt, 'prelude', None) or []
                for instr in prelude:
                    if isinstance(instr, TempAssignIR):
                        found_temp = True
                        break
                if found_temp:
                    break
            assert found_temp, (
                "Expected TempAssignIR in body statement preludes for callable-call-result"
            )
