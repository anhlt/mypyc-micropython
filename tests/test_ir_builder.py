"""Unit tests for IRBuilder - AST to IR translation."""

from __future__ import annotations

import ast

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
    ExprStmtIR,
    ForIterIR,
    ForRangeIR,
    IfExprIR,
    IfIR,
    IRType,
    ListNewIR,
    MethodCallIR,
    NameIR,
    PassIR,
    PrintIR,
    ReturnIR,
    SubscriptIR,
    TupleNewIR,
    UnaryOpIR,
    WhileIR,
)
from mypyc_micropython.ir_builder import IRBuilder, sanitize_name


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
