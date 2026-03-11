"""Unit tests for emitters - IR to C code generation.

This module tests the emitters in isolation from the IR builder.
By constructing IR nodes manually, we can:
1. Test emitter logic without IR builder dependencies
2. Create edge cases that are hard to trigger via Python source
3. Quickly pinpoint whether bugs are in IR building or code emission

Test naming convention: test_emit_<feature>_<behavior>
"""

from __future__ import annotations

import ast

from mypyc_micropython.function_emitter import FunctionEmitter, MethodEmitter
from mypyc_micropython.generator_emitter import GeneratorEmitter
from mypyc_micropython.ir import (
    AnnAssignIR,
    AssignIR,
    AugAssignIR,
    BinOpIR,
    BreakIR,
    ClassIR,
    CompareIR,
    ConstIR,
    ContinueIR,
    CType,
    DictNewIR,
    ExprStmtIR,
    FieldIR,
    ForIterIR,
    ForRangeIR,
    FuncIR,
    IfExprIR,
    IfIR,
    IRType,
    ListNewIR,
    MethodCallIR,
    MethodIR,
    ModuleCallIR,
    NameIR,
    ObjAttrAssignIR,
    PassIR,
    ReturnIR,
    SelfMethodCallIR,
    SubscriptAssignIR,
    SubscriptIR,
    TempIR,
    TupleNewIR,
    UnaryOpIR,
    WhileIR,
    YieldIR,
)

# ============================================================================
# Helpers: Factory functions for building IR nodes
# ============================================================================


def make_func(
    name: str = "f",
    params: list[tuple[str, CType]] | None = None,
    return_type: CType = CType.MP_INT_T,
    body: list | None = None,
    locals_: dict[str, CType] | None = None,
    list_vars: dict | None = None,
    max_temp: int = 0,
) -> FuncIR:
    """Factory for creating FuncIR with sensible defaults."""
    return FuncIR(
        name=name,
        c_name=f"test_{name}",
        params=params or [],
        return_type=return_type,
        body=body or [],
        locals_=locals_ or {},
        list_vars=list_vars or {},
        max_temp=max_temp,
    )


def make_name(py_name: str, ir_type: IRType = IRType.INT) -> NameIR:
    """Create a NameIR with matching c_name."""
    return NameIR(py_name=py_name, c_name=py_name, ir_type=ir_type)


def make_const_int(value: int) -> ConstIR:
    """Create an integer constant."""
    return ConstIR(value=value, ir_type=IRType.INT)


def make_const_float(value: float) -> ConstIR:
    """Create a float constant."""
    return ConstIR(value=value, ir_type=IRType.FLOAT)


def make_const_bool(value: bool) -> ConstIR:
    """Create a boolean constant."""
    return ConstIR(value=value, ir_type=IRType.BOOL)


def make_const_str(value: str) -> ConstIR:
    """Create a string constant."""
    return ConstIR(value=value, ir_type=IRType.OBJ)


def make_const_none() -> ConstIR:
    """Create a None constant."""
    return ConstIR(value=None, ir_type=IRType.OBJ)


def make_method_ir(
    name: str = "method",
    c_name: str | None = None,
    params: list[tuple[str, CType]] | None = None,
    return_type: CType = CType.MP_OBJ_T,
    max_temp: int = 0,
) -> MethodIR:
    """Factory for creating MethodIR with a dummy body_ast.

    MethodIR requires body_ast (ast.FunctionDef) but for unit tests,
    we pass the actual IR body to emit_native() separately.
    """
    # Create minimal dummy AST node (required by MethodIR)
    dummy_args = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg="self", annotation=None)]
        + [ast.arg(arg=p[0], annotation=None) for p in (params or [])],
        kwonlyargs=[],
        kw_defaults=[],
        defaults=[],
        vararg=None,
        kwarg=None,
    )
    dummy_body_ast = ast.FunctionDef(
        name=name,
        args=dummy_args,
        body=[ast.Pass()],
        decorator_list=[],
        returns=None,
        lineno=1,
        col_offset=0,
    )
    return MethodIR(
        name=name,
        c_name=c_name or f"test_{name}",
        params=params or [],
        return_type=return_type,
        body_ast=dummy_body_ast,
        max_temp=max_temp,
    )


def make_temp(name: str, ir_type: IRType = IRType.OBJ) -> TempIR:
    """Create a temporary variable."""
    return TempIR(name=name, ir_type=ir_type)


# ============================================================================
# Test: Return Statement Emission
# ============================================================================


class TestEmitReturn:
    """Tests for return statement emission."""

    def test_emit_return_int_constant(self):
        """Return statement with integer constant."""
        func_ir = make_func(body=[ReturnIR(value=make_const_int(42))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "return mp_obj_new_int(42)" in c_code

    def test_emit_return_float_constant(self):
        """Return statement with float constant."""
        func_ir = make_func(
            return_type=CType.MP_FLOAT_T,
            body=[ReturnIR(value=make_const_float(3.14))],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "return mp_obj_new_float(3.14)" in c_code

    def test_emit_return_bool_true(self):
        """Return statement with True."""
        func_ir = make_func(return_type=CType.BOOL, body=[ReturnIR(value=make_const_bool(True))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_const_true" in c_code

    def test_emit_return_bool_false(self):
        """Return statement with False."""
        func_ir = make_func(return_type=CType.BOOL, body=[ReturnIR(value=make_const_bool(False))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_const_false" in c_code

    def test_emit_return_string(self):
        """Return statement with string constant."""
        func_ir = make_func(
            return_type=CType.MP_OBJ_T, body=[ReturnIR(value=make_const_str("hello"))]
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert 'mp_obj_new_str("hello", 5)' in c_code

    def test_emit_return_none(self):
        """Return statement with None."""
        func_ir = make_func(return_type=CType.VOID, body=[ReturnIR(value=make_const_none())])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_const_none" in c_code

    def test_emit_return_variable(self):
        """Return statement with variable reference."""
        func_ir = make_func(params=[("x", CType.MP_INT_T)], body=[ReturnIR(value=make_name("x"))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "return mp_obj_new_int(x)" in c_code

    def test_emit_return_none_implicit(self):
        """Return without value (implicit None)."""
        func_ir = make_func(return_type=CType.VOID, body=[ReturnIR(value=None)])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "return mp_const_none" in c_code


# ============================================================================
# Test: Binary Operation Emission
# ============================================================================


class TestEmitBinOp:
    """Tests for binary operation emission."""

    def test_emit_int_addition(self):
        """Integer addition: a + b."""
        func_ir = make_func(
            params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a"),
                        op="+",
                        right=make_name("b"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(a + b)" in c_code

    def test_emit_int_subtraction(self):
        """Integer subtraction: a - b."""
        func_ir = make_func(
            params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a"),
                        op="-",
                        right=make_name("b"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(a - b)" in c_code

    def test_emit_int_multiplication(self):
        """Integer multiplication: a * b."""
        func_ir = make_func(
            params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a"),
                        op="*",
                        right=make_name("b"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(a * b)" in c_code

    def test_emit_int_floor_division(self):
        """Integer floor division: a // b."""
        func_ir = make_func(
            params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a"),
                        op="//",
                        right=make_name("b"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(a / b)" in c_code

    def test_emit_int_modulo(self):
        """Integer modulo: a % b."""
        func_ir = make_func(
            params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a"),
                        op="%",
                        right=make_name("b"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(a % b)" in c_code

    def test_emit_obj_addition_uses_mp_binary_op(self):
        """Object addition uses mp_binary_op."""
        func_ir = make_func(
            params=[("a", CType.MP_OBJ_T), ("b", CType.MP_OBJ_T)],
            return_type=CType.MP_OBJ_T,
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a", IRType.OBJ),
                        op="+",
                        right=make_name("b", IRType.OBJ),
                        ir_type=IRType.OBJ,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_binary_op(MP_BINARY_OP_ADD" in c_code

    def test_emit_logical_and(self):
        """Logical AND: a && b."""
        func_ir = make_func(
            params=[("a", CType.BOOL), ("b", CType.BOOL)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a", IRType.BOOL),
                        op="&&",
                        right=make_name("b", IRType.BOOL),
                        ir_type=IRType.BOOL,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "&&" in c_code

    def test_emit_logical_or(self):
        """Logical OR: a || b."""
        func_ir = make_func(
            params=[("a", CType.BOOL), ("b", CType.BOOL)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a", IRType.BOOL),
                        op="||",
                        right=make_name("b", IRType.BOOL),
                        ir_type=IRType.BOOL,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "||" in c_code


# ============================================================================
# Test: Unary Operation Emission
# ============================================================================


class TestEmitUnaryOp:
    """Tests for unary operation emission."""

    def test_emit_negate_int(self):
        """Negate integer: -x."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T)],
            body=[ReturnIR(value=UnaryOpIR(op="-", operand=make_name("x"), ir_type=IRType.INT))],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(-x)" in c_code

    def test_emit_logical_not(self):
        """Logical NOT: !x."""
        func_ir = make_func(
            params=[("x", CType.BOOL)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=UnaryOpIR(
                        op="!", operand=make_name("x", IRType.BOOL), ir_type=IRType.BOOL
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(!x)" in c_code


# ============================================================================
# Test: Comparison Emission
# ============================================================================


class TestEmitCompare:
    """Tests for comparison operation emission."""

    def test_emit_less_than(self):
        """Less than comparison: x < y."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T), ("y", CType.MP_INT_T)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=CompareIR(
                        left=make_name("x"),
                        ops=["<"],
                        comparators=[make_name("y")],
                        ir_type=IRType.BOOL,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(x < y)" in c_code

    def test_emit_greater_than(self):
        """Greater than comparison: x > y."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T), ("y", CType.MP_INT_T)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=CompareIR(
                        left=make_name("x"),
                        ops=[">"],
                        comparators=[make_name("y")],
                        ir_type=IRType.BOOL,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(x > y)" in c_code

    def test_emit_equality(self):
        """Equality comparison: x == y."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T), ("y", CType.MP_INT_T)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=CompareIR(
                        left=make_name("x"),
                        ops=["=="],
                        comparators=[make_name("y")],
                        ir_type=IRType.BOOL,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(x == y)" in c_code

    def test_emit_chained_comparison(self):
        """Chained comparison: x < y < z."""
        func_ir = make_func(
            params=[
                ("x", CType.MP_INT_T),
                ("y", CType.MP_INT_T),
                ("z", CType.MP_INT_T),
            ],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=CompareIR(
                        left=make_name("x"),
                        ops=["<", "<"],
                        comparators=[make_name("y"), make_name("z")],
                        ir_type=IRType.BOOL,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(x < y)" in c_code
        assert "(y < z)" in c_code
        assert "&&" in c_code


# ============================================================================
# Test: If Statement Emission
# ============================================================================


class TestEmitIf:
    """Tests for if statement emission."""

    def test_emit_simple_if(self):
        """Simple if statement."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T)],
            body=[
                IfIR(
                    test=CompareIR(
                        left=make_name("x"),
                        ops=[">"],
                        comparators=[make_const_int(0)],
                        ir_type=IRType.BOOL,
                    ),
                    body=[ReturnIR(value=make_const_int(1))],
                    orelse=[],
                ),
                ReturnIR(value=make_const_int(0)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "if ((x > 0))" in c_code

    def test_emit_if_else(self):
        """If-else statement."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T)],
            body=[
                IfIR(
                    test=CompareIR(
                        left=make_name("x"),
                        ops=[">"],
                        comparators=[make_const_int(0)],
                        ir_type=IRType.BOOL,
                    ),
                    body=[ReturnIR(value=make_const_int(1))],
                    orelse=[ReturnIR(value=make_const_int(-1))],
                ),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "if ((x > 0))" in c_code
        assert "} else {" in c_code


# ============================================================================
# Test: While Loop Emission
# ============================================================================


class TestEmitWhile:
    """Tests for while loop emission."""

    def test_emit_simple_while(self):
        """Simple while loop."""
        func_ir = make_func(
            params=[("n", CType.MP_INT_T)],
            locals_={"i": CType.MP_INT_T},
            body=[
                AnnAssignIR(
                    target="i",
                    c_target="i",
                    c_type="mp_int_t",
                    value=make_const_int(0),
                    is_new_var=True,
                ),
                WhileIR(
                    test=CompareIR(
                        left=make_name("i"),
                        ops=["<"],
                        comparators=[make_name("n")],
                        ir_type=IRType.BOOL,
                    ),
                    body=[
                        AugAssignIR(
                            target="i",
                            c_target="i",
                            op="+=",
                            value=make_const_int(1),
                        ),
                    ],
                ),
                ReturnIR(value=make_name("i")),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "while ((i < n))" in c_code

    def test_emit_while_with_break(self):
        """While loop with break."""
        func_ir = make_func(
            params=[("n", CType.MP_INT_T)],
            body=[
                WhileIR(
                    test=make_const_bool(True),
                    body=[BreakIR()],
                ),
                ReturnIR(value=make_const_int(0)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "break;" in c_code

    def test_emit_while_with_continue(self):
        """While loop with continue."""
        func_ir = make_func(
            params=[("n", CType.MP_INT_T)],
            body=[
                WhileIR(
                    test=make_const_bool(True),
                    body=[ContinueIR(), BreakIR()],
                ),
                ReturnIR(value=make_const_int(0)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "continue;" in c_code


# ============================================================================
# Test: For Range Loop Emission
# ============================================================================


class TestEmitForRange:
    """Tests for for-range loop emission."""

    def test_emit_for_range_simple(self):
        """Simple for loop: for i in range(n)."""
        func_ir = make_func(
            params=[("n", CType.MP_INT_T)],
            locals_={"i": CType.MP_INT_T},
            body=[
                ForRangeIR(
                    loop_var="i",
                    c_loop_var="i",
                    start=make_const_int(0),
                    end=make_name("n"),
                    step=make_const_int(1),
                    step_is_constant=True,
                    step_value=1,
                    body=[PassIR()],
                    is_new_var=True,
                ),
                ReturnIR(value=make_const_int(0)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "for (i = 0;" in c_code
        assert "i++" in c_code

    def test_emit_for_range_with_start(self):
        """For loop with start: for i in range(5, n)."""
        func_ir = make_func(
            params=[("n", CType.MP_INT_T)],
            locals_={"i": CType.MP_INT_T},
            body=[
                ForRangeIR(
                    loop_var="i",
                    c_loop_var="i",
                    start=make_const_int(5),
                    end=make_name("n"),
                    step=make_const_int(1),
                    step_is_constant=True,
                    step_value=1,
                    body=[PassIR()],
                    is_new_var=True,
                ),
                ReturnIR(value=make_const_int(0)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "for (i = 5;" in c_code

    def test_emit_for_range_negative_step(self):
        """For loop with negative step: for i in range(n, 0, -1)."""
        func_ir = make_func(
            params=[("n", CType.MP_INT_T)],
            locals_={"i": CType.MP_INT_T},
            body=[
                ForRangeIR(
                    loop_var="i",
                    c_loop_var="i",
                    start=make_name("n"),
                    end=make_const_int(0),
                    step=make_const_int(-1),
                    step_is_constant=True,
                    step_value=-1,
                    body=[PassIR()],
                    is_new_var=True,
                ),
                ReturnIR(value=make_const_int(0)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "i--" in c_code
        assert "i > " in c_code


# ============================================================================
# Test: For Iterator Loop Emission
# ============================================================================


class TestEmitForIter:
    """Tests for for-iterator loop emission."""

    def test_emit_for_iter_simple(self):
        """For loop over iterator: for item in lst."""
        func_ir = make_func(
            params=[("lst", CType.MP_OBJ_T)],
            return_type=CType.MP_OBJ_T,
            locals_={"item": CType.MP_OBJ_T},
            max_temp=2,
            body=[
                ForIterIR(
                    loop_var="item",
                    c_loop_var="item",
                    iterable=make_name("lst", IRType.OBJ),
                    body=[PassIR()],
                    is_new_var=True,
                ),
                ReturnIR(value=make_const_none()),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_getiter(" in c_code
        assert "mp_iternext(" in c_code
        assert "MP_OBJ_STOP_ITERATION" in c_code


# ============================================================================
# Test: Assignment Emission
# ============================================================================


class TestEmitAssignment:
    """Tests for assignment statement emission."""

    def test_emit_ann_assign_int(self):
        """Annotated assignment: x: int = 0."""
        func_ir = make_func(
            body=[
                AnnAssignIR(
                    target="x",
                    c_target="x",
                    c_type="mp_int_t",
                    value=make_const_int(0),
                    is_new_var=True,
                ),
                ReturnIR(value=make_name("x")),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_int_t x = 0" in c_code

    def test_emit_assign_existing_var(self):
        """Assignment to existing variable: x = 10."""
        func_ir = make_func(
            body=[
                AnnAssignIR(
                    target="x",
                    c_target="x",
                    c_type="mp_int_t",
                    value=make_const_int(0),
                    is_new_var=True,
                ),
                AssignIR(
                    target="x",
                    c_target="x",
                    value=make_const_int(10),
                    value_type=IRType.INT,
                    is_new_var=False,
                    c_type="mp_int_t",
                ),
                ReturnIR(value=make_name("x")),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # First declaration
        assert "mp_int_t x = 0" in c_code
        # Second assignment (no type declaration)
        lines = c_code.split("\n")
        assign_lines = [line for line in lines if "x = 10" in line]
        assert len(assign_lines) >= 1
        # Should not redeclare type
        assert "mp_int_t x = 10" not in c_code

    def test_emit_aug_assign_int(self):
        """Augmented assignment: x += 1."""
        func_ir = make_func(
            body=[
                AnnAssignIR(
                    target="x",
                    c_target="x",
                    c_type="mp_int_t",
                    value=make_const_int(0),
                    is_new_var=True,
                ),
                AugAssignIR(
                    target="x",
                    c_target="x",
                    op="+=",
                    value=make_const_int(1),
                    target_c_type="mp_int_t",
                ),
                ReturnIR(value=make_name("x")),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "x += 1" in c_code

    def test_emit_aug_assign_obj_uses_mp_binary_op(self):
        """Augmented assignment on object uses mp_binary_op."""
        func_ir = make_func(
            params=[("lst", CType.MP_OBJ_T)],
            return_type=CType.MP_OBJ_T,
            body=[
                AugAssignIR(
                    target="lst",
                    c_target="lst",
                    op="+=",
                    value=make_name("lst", IRType.OBJ),
                    target_c_type="mp_obj_t",
                ),
                ReturnIR(value=make_name("lst", IRType.OBJ)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_binary_op(MP_BINARY_OP_INPLACE_ADD" in c_code


# ============================================================================
# Test: Subscript Emission
# ============================================================================


class TestEmitSubscript:
    """Tests for subscript operation emission."""

    def test_emit_subscript_read(self):
        """Subscript read: lst[i]."""
        func_ir = make_func(
            params=[("lst", CType.MP_OBJ_T), ("i", CType.MP_INT_T)],
            return_type=CType.MP_OBJ_T,
            body=[
                ReturnIR(
                    value=SubscriptIR(
                        value=make_name("lst", IRType.OBJ),
                        slice_=make_name("i"),
                        ir_type=IRType.OBJ,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_subscr(" in c_code
        assert "MP_OBJ_SENTINEL" in c_code

    def test_emit_subscript_assign(self):
        """Subscript assignment: lst[i] = val."""
        func_ir = make_func(
            params=[
                ("lst", CType.MP_OBJ_T),
                ("i", CType.MP_INT_T),
                ("val", CType.MP_INT_T),
            ],
            return_type=CType.VOID,
            body=[
                SubscriptAssignIR(
                    container=make_name("lst", IRType.OBJ),
                    key=make_name("i"),
                    value=make_name("val"),
                ),
                ReturnIR(value=None),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_subscr(" in c_code
        # Should NOT have MP_OBJ_SENTINEL for assignment
        # The value is the third argument instead


# ============================================================================
# Test: Container Creation Emission
# ============================================================================


class TestEmitContainerCreation:
    """Tests for container creation emission (via prelude)."""

    def test_emit_empty_list(self):
        """Empty list literal: []."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                AnnAssignIR(
                    target="result",
                    c_target="result",
                    c_type="mp_obj_t",
                    value=temp,
                    is_new_var=True,
                    prelude=[ListNewIR(result=temp, items=[])],
                ),
                ReturnIR(value=make_name("result", IRType.OBJ)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_new_list(0, NULL)" in c_code

    def test_emit_list_with_items(self):
        """List literal with items: [1, 2, 3]."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                AnnAssignIR(
                    target="result",
                    c_target="result",
                    c_type="mp_obj_t",
                    value=temp,
                    is_new_var=True,
                    prelude=[
                        ListNewIR(
                            result=temp,
                            items=[
                                make_const_int(1),
                                make_const_int(2),
                                make_const_int(3),
                            ],
                        )
                    ],
                ),
                ReturnIR(value=make_name("result", IRType.OBJ)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_new_list(" in c_code

    def test_emit_empty_dict(self):
        """Empty dict literal: {}."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                AnnAssignIR(
                    target="result",
                    c_target="result",
                    c_type="mp_obj_t",
                    value=temp,
                    is_new_var=True,
                    prelude=[DictNewIR(result=temp, entries=[])],
                ),
                ReturnIR(value=make_name("result", IRType.OBJ)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_new_dict(0)" in c_code

    def test_emit_empty_tuple(self):
        """Empty tuple literal: ()."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                AnnAssignIR(
                    target="result",
                    c_target="result",
                    c_type="mp_obj_t",
                    value=temp,
                    is_new_var=True,
                    prelude=[TupleNewIR(result=temp, items=[])],
                ),
                ReturnIR(value=make_name("result", IRType.OBJ)),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_const_empty_tuple" in c_code


# ============================================================================
# Test: Conditional Expression Emission
# ============================================================================


class TestEmitIfExpr:
    """Tests for conditional expression emission."""

    def test_emit_if_expr(self):
        """Conditional expression: a if cond else b."""
        func_ir = make_func(
            params=[("cond", CType.BOOL), ("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=IfExprIR(
                        test=make_name("cond", IRType.BOOL),
                        body=make_name("a"),
                        orelse=make_name("b"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Should emit ternary operator
        assert "?" in c_code
        assert ":" in c_code


# ============================================================================
# Test: Function Signature Emission
# ============================================================================


class TestEmitFunctionSignature:
    """Tests for function signature emission."""

    def test_emit_no_args_function(self):
        """Function with no arguments."""
        func_ir = make_func(name="get_answer", body=[ReturnIR(value=make_const_int(42))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "static mp_obj_t test_get_answer(void)" in c_code
        assert "MP_DEFINE_CONST_FUN_OBJ_0" in c_code

    def test_emit_one_arg_function(self):
        """Function with one argument."""
        func_ir = make_func(
            name="square",
            params=[("x", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("x"),
                        op="*",
                        right=make_name("x"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "static mp_obj_t test_square(mp_obj_t x_obj)" in c_code
        assert "MP_DEFINE_CONST_FUN_OBJ_1" in c_code

    def test_emit_two_args_function(self):
        """Function with two arguments."""
        func_ir = make_func(
            name="add",
            params=[("a", CType.MP_INT_T), ("b", CType.MP_INT_T)],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=make_name("a"),
                        op="+",
                        right=make_name("b"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "MP_DEFINE_CONST_FUN_OBJ_2" in c_code

    def test_emit_three_args_function(self):
        """Function with three arguments."""
        func_ir = make_func(
            name="add3",
            params=[
                ("a", CType.MP_INT_T),
                ("b", CType.MP_INT_T),
                ("c", CType.MP_INT_T),
            ],
            body=[ReturnIR(value=make_const_int(0))],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "MP_DEFINE_CONST_FUN_OBJ_3" in c_code

    def test_emit_four_args_function_uses_var_between(self):
        """Function with four+ arguments uses VAR_BETWEEN."""
        func_ir = make_func(
            name="add4",
            params=[
                ("a", CType.MP_INT_T),
                ("b", CType.MP_INT_T),
                ("c", CType.MP_INT_T),
                ("d", CType.MP_INT_T),
            ],
            body=[ReturnIR(value=make_const_int(0))],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN" in c_code
        assert "size_t n_args" in c_code


# ============================================================================
# Test: Type Unboxing Emission
# ============================================================================


class TestEmitUnboxing:
    """Tests for parameter unboxing emission."""

    def test_emit_int_param_unboxing(self):
        """Integer parameter unboxing when arg_types is set."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T)],
            body=[ReturnIR(value=make_name("x"))],
        )
        # Emitter needs arg_types set to know the unboxed C types
        func_ir.arg_types = ["mp_int_t"]
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_int_t x = mp_obj_get_int(x_obj)" in c_code

    def test_emit_float_param_unboxing(self):
        """Float parameter unboxing when arg_types is set."""
        func_ir = make_func(
            params=[("x", CType.MP_FLOAT_T)],
            return_type=CType.MP_FLOAT_T,
            body=[ReturnIR(value=make_name("x", IRType.FLOAT))],
        )
        func_ir.arg_types = ["mp_float_t"]
        c_code = FunctionEmitter(func_ir).emit()[0]
        # MicroPython uses mp_obj_get_float
        assert "mp_float_t x = " in c_code

    def test_emit_bool_param_unboxing(self):
        """Bool parameter unboxing when arg_types is set."""
        func_ir = make_func(
            params=[("flag", CType.BOOL)],
            return_type=CType.BOOL,
            body=[ReturnIR(value=make_name("flag", IRType.BOOL))],
        )
        func_ir.arg_types = ["bool"]
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_is_true" in c_code

    def test_emit_obj_param_no_unboxing(self):
        """Object parameter needs no unboxing."""
        func_ir = make_func(
            params=[("obj", CType.MP_OBJ_T)],
            return_type=CType.MP_OBJ_T,
            body=[ReturnIR(value=make_name("obj", IRType.OBJ))],
        )
        func_ir.arg_types = ["mp_obj_t"]
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Object params are passed directly
        assert "mp_obj_t obj = obj_obj" in c_code


# ============================================================================
# Test: Expression Statement Emission
# ============================================================================


class TestEmitExprStmt:
    """Tests for expression statement emission."""

    def test_emit_expr_stmt_discards_value(self):
        """Expression statement discards return value."""
        func_ir = make_func(
            params=[("x", CType.MP_INT_T)],
            return_type=CType.VOID,
            body=[
                ExprStmtIR(expr=make_name("x")),
                ReturnIR(value=None),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(void)x" in c_code


# ============================================================================
# Test: Pass Statement Emission
# ============================================================================


class TestEmitPass:
    """Tests for pass statement emission."""

    def test_emit_pass_produces_nothing(self):
        """Pass statement emits nothing."""
        func_ir = make_func(
            return_type=CType.VOID,
            body=[
                PassIR(),
                ReturnIR(value=None),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Pass should not add any specific code
        assert "pass" not in c_code.lower()


# ============================================================================
# Test: Method Call Emission (via MethodCallIR in prelude)
# ============================================================================


class TestEmitMethodCall:
    """Tests for method call emission."""

    def test_emit_list_append_in_prelude(self):
        """List append method call in prelude."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            params=[("lst", CType.MP_OBJ_T), ("x", CType.MP_INT_T)],
            return_type=CType.VOID,
            max_temp=1,
            body=[
                ExprStmtIR(
                    expr=temp,
                    prelude=[
                        MethodCallIR(
                            result=None,
                            receiver=make_name("lst", IRType.OBJ),
                            method="append",
                            args=[make_name("x")],
                        )
                    ],
                ),
                ReturnIR(value=None),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_list_append(" in c_code

    def test_emit_method_call_with_kwargs(self):
        """Method call with keyword arguments: obj.method(a, b=1, c=2)."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            params=[("obj", CType.MP_OBJ_T), ("a", CType.MP_INT_T)],
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                ExprStmtIR(
                    expr=temp,
                    prelude=[
                        MethodCallIR(
                            result=temp,
                            receiver=make_name("obj", IRType.OBJ),
                            method="configure",
                            args=[make_name("a")],
                            kwargs=[
                                ("width", ConstIR(ir_type=IRType.INT, value=100)),
                                ("height", ConstIR(ir_type=IRType.INT, value=200)),
                            ],
                        )
                    ],
                ),
                ReturnIR(value=temp),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Should use mp_call_method_n_kw with n_args=1, n_kw=2
        assert "mp_call_method_n_kw(1, 2," in c_code
        # Should have keyword names as QSTRs
        assert "MP_QSTR_width" in c_code
        assert "MP_QSTR_height" in c_code

    def test_emit_method_call_kwargs_only(self):
        """Method call with only keyword arguments: obj.method(x=1)."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            params=[("obj", CType.MP_OBJ_T)],
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                ExprStmtIR(
                    expr=temp,
                    prelude=[
                        MethodCallIR(
                            result=temp,
                            receiver=make_name("obj", IRType.OBJ),
                            method="set_value",
                            args=[],
                            kwargs=[
                                ("value", ConstIR(ir_type=IRType.INT, value=42)),
                            ],
                        )
                    ],
                ),
                ReturnIR(value=temp),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Should use mp_call_method_n_kw with n_args=0, n_kw=1
        assert "mp_call_method_n_kw(0, 1," in c_code
        assert "MP_QSTR_value" in c_code

    def test_custom_class_method_with_builtin_name(self):
        """Method on custom class with builtin method name uses generic dispatch.

        When calling reg.add(x) where reg is a Registry (custom class),
        should use mp_load_method, NOT mp_obj_set_store (set.add).
        This is a regression test for the bug where method dispatch was
        based purely on method name without checking receiver_py_type.
        """
        temp = make_temp("_tmp0")
        func_ir = make_func(
            params=[("reg", CType.MP_OBJ_T), ("key", CType.MP_INT_T)],
            return_type=CType.VOID,
            max_temp=1,
            body=[
                ExprStmtIR(
                    expr=temp,
                    prelude=[
                        MethodCallIR(
                            result=None,
                            receiver=make_name("reg", IRType.OBJ),
                            method="add",  # Same name as set.add!
                            args=[make_name("key")],
                            receiver_py_type="Registry",  # Custom class, not set
                        )
                    ],
                ),
                ReturnIR(value=None),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Should use generic mp_load_method dispatch
        assert "mp_load_method(" in c_code
        assert "MP_QSTR_add" in c_code
        assert "mp_call_method_n_kw" in c_code
        # Should NOT use set.add optimization
        assert "mp_obj_set_store" not in c_code

# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEmitEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_emit_nested_binop(self):
        """Nested binary operation: (a + b) * c."""
        func_ir = make_func(
            params=[
                ("a", CType.MP_INT_T),
                ("b", CType.MP_INT_T),
                ("c", CType.MP_INT_T),
            ],
            body=[
                ReturnIR(
                    value=BinOpIR(
                        left=BinOpIR(
                            left=make_name("a"),
                            op="+",
                            right=make_name("b"),
                            ir_type=IRType.INT,
                        ),
                        op="*",
                        right=make_name("c"),
                        ir_type=IRType.INT,
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "(a + b)" in c_code
        assert "* c" in c_code

    def test_emit_string_with_special_chars(self):
        """String constant with special characters."""
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            body=[ReturnIR(value=make_const_str('hello "world"'))],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert '\\"world\\"' in c_code

    def test_emit_negative_constant(self):
        """Negative integer constant."""
        func_ir = make_func(body=[ReturnIR(value=make_const_int(-42))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "-42" in c_code

    def test_emit_zero_constant(self):
        """Zero constant."""
        func_ir = make_func(body=[ReturnIR(value=make_const_int(0))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "mp_obj_new_int(0)" in c_code

    def test_emit_large_constant(self):
        """Large integer constant."""
        func_ir = make_func(body=[ReturnIR(value=make_const_int(2147483647))])
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "2147483647" in c_code


# ============================================================================
# Test: Class Emitter
# ============================================================================


class TestClassEmitterStruct:
    """Tests for class struct emission."""

    def test_emit_simple_class_struct(self):
        """Simple class with no fields."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Empty",
            c_name="test_Empty",
            module_name="test",
            fields=[],
        )
        emitter = ClassEmitter(class_ir, "test")
        struct_code = "\n".join(emitter.emit_struct())
        assert "struct _test_Empty_obj_t" in struct_code
        assert "mp_obj_base_t base;" in struct_code

    def test_emit_class_with_int_field(self):
        """Class with integer field."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Point",
            c_name="test_Point",
            module_name="test",
            fields=[
                FieldIR(name="x", py_type="int", c_type=CType.MP_INT_T),
                FieldIR(name="y", py_type="int", c_type=CType.MP_INT_T),
            ],
        )
        emitter = ClassEmitter(class_ir, "test")
        struct_code = "\n".join(emitter.emit_struct())
        assert "mp_int_t x;" in struct_code
        assert "mp_int_t y;" in struct_code

    def test_emit_class_with_obj_field(self):
        """Class with object field."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Container",
            c_name="test_Container",
            module_name="test",
            fields=[
                FieldIR(name="items", py_type="list", c_type=CType.MP_OBJ_T),
            ],
        )
        emitter = ClassEmitter(class_ir, "test")
        struct_code = "\n".join(emitter.emit_struct())
        assert "mp_obj_t items;" in struct_code

    def test_emit_class_with_float_field(self):
        """Class with float field."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Measurement",
            c_name="test_Measurement",
            module_name="test",
            fields=[
                FieldIR(name="value", py_type="float", c_type=CType.MP_FLOAT_T),
            ],
        )
        emitter = ClassEmitter(class_ir, "test")
        struct_code = "\n".join(emitter.emit_struct())
        assert "mp_float_t value;" in struct_code

    def test_emit_class_with_bool_field(self):
        """Class with bool field."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Flag",
            c_name="test_Flag",
            module_name="test",
            fields=[
                FieldIR(name="enabled", py_type="bool", c_type=CType.BOOL),
            ],
        )
        emitter = ClassEmitter(class_ir, "test")
        struct_code = "\n".join(emitter.emit_struct())
        assert "bool enabled;" in struct_code


class TestClassEmitterFieldDescriptors:
    """Tests for field descriptor emission."""

    def test_emit_field_descriptors(self):
        """Field descriptors for attr lookup."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Point",
            c_name="test_Point",
            module_name="test",
            fields=[
                FieldIR(name="x", py_type="int", c_type=CType.MP_INT_T),
                FieldIR(name="y", py_type="int", c_type=CType.MP_INT_T),
            ],
        )
        emitter = ClassEmitter(class_ir, "test")
        desc_code = "\n".join(emitter.emit_field_descriptors())
        assert "MP_QSTR_x" in desc_code
        assert "MP_QSTR_y" in desc_code
        assert "test_Point_field_t" in desc_code

    def test_emit_no_field_descriptors_for_empty_class(self):
        """No field descriptors for class with no fields."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Empty",
            c_name="test_Empty",
            module_name="test",
            fields=[],
        )
        emitter = ClassEmitter(class_ir, "test")
        desc_lines = emitter.emit_field_descriptors()
        assert desc_lines == []


class TestClassEmitterForwardDecl:
    """Tests for forward declaration emission."""

    def test_emit_forward_declarations(self):
        """Forward declarations for struct and vtable."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Widget",
            c_name="test_Widget",
            module_name="test",
            fields=[],
        )
        emitter = ClassEmitter(class_ir, "test")
        fwd_code = "\n".join(emitter.emit_forward_declarations())
        assert "typedef struct _test_Widget_obj_t test_Widget_obj_t;" in fwd_code


class TestClassEmitterAttrHandler:
    """Tests for attribute handler emission."""

    def test_emit_attr_handler_with_fields(self):
        """Attribute handler for class with fields."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Point",
            c_name="test_Point",
            module_name="test",
            fields=[
                FieldIR(name="x", py_type="int", c_type=CType.MP_INT_T),
            ],
        )
        emitter = ClassEmitter(class_ir, "test")
        attr_code = "\n".join(emitter.emit_attr_handler())
        assert "test_Point_attr" in attr_code
        assert "qstr attr" in attr_code
        assert "mp_obj_t *dest" in attr_code

    def test_emit_simple_attr_handler_for_empty_class(self):
        """Simple attribute handler for class with no fields."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Empty",
            c_name="test_Empty",
            module_name="test",
            fields=[],
        )
        emitter = ClassEmitter(class_ir, "test")
        attr_code = "\n".join(emitter.emit_attr_handler())
        assert "test_Empty_attr" in attr_code
        # Simple handler just delegates
        assert "dest[1] = MP_OBJ_SENTINEL" in attr_code


class TestClassEmitterTypeDefinition:
    """Tests for type definition emission."""

    def test_emit_type_definition(self):
        """Type definition with slots."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Widget",
            c_name="test_Widget",
            module_name="test",
            fields=[],
        )
        emitter = ClassEmitter(class_ir, "test")
        type_code = "\n".join(emitter.emit_type_definition())
        assert "MP_DEFINE_CONST_OBJ_TYPE" in type_code
        assert "test_Widget_type" in type_code
        assert "MP_QSTR_Widget" in type_code

class TestClassEmitterMakeNew:
    """Tests for make_new emission with kwargs support."""

    def test_emit_make_new_no_init(self):
        """make_new for class without __init__."""
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="Empty",
            c_name="test_Empty",
            module_name="test",
            fields=[],
        )
        emitter = ClassEmitter(class_ir, "test")
        make_new_code = "\n".join(emitter.emit_make_new())
        # Should just create instance without arg parsing
        assert "test_Empty_make_new" in make_new_code
        assert "mp_arg_parse_all_kw_array" not in make_new_code

    def test_emit_make_new_init_no_params(self):
        """make_new for class with __init__(self) only."""
        import ast

        from mypyc_micropython.class_emitter import ClassEmitter
        from mypyc_micropython.ir import MethodIR

        # Create a minimal __init__ with no params
        init_ast = ast.parse("def __init__(self): pass").body[0]
        init_method = MethodIR(
            name="__init__",
            c_name="test_Point___init__",
            params=[],  # No params besides self
            return_type=CType.VOID,
            body_ast=init_ast,
            is_special=True,
        )

        class_ir = ClassIR(
            name="Point",
            c_name="test_Point",
            module_name="test",
            fields=[],
            methods={"__init__": init_method},
        )
        emitter = ClassEmitter(class_ir, "test")
        make_new_code = "\n".join(emitter.emit_make_new())
        # No params = no arg parsing needed
        assert "test_Point_make_new" in make_new_code
        assert "mp_arg_parse_all_kw_array" not in make_new_code
        assert "allowed_args" not in make_new_code

    def test_emit_make_new_with_required_params(self):
        """make_new for class with required params uses mp_arg_parse_all_kw_array."""
        import ast

        from mypyc_micropython.class_emitter import ClassEmitter
        from mypyc_micropython.ir import FieldIR, MethodIR

        init_ast = ast.parse("def __init__(self, x, y): pass").body[0]
        init_method = MethodIR(
            name="__init__",
            c_name="test_Point___init__",
            params=[("x", CType.MP_INT_T), ("y", CType.MP_INT_T)],
            return_type=CType.VOID,
            body_ast=init_ast,
            is_special=True,
        )

        class_ir = ClassIR(
            name="Point",
            c_name="test_Point",
            module_name="test",
            fields=[
                FieldIR(name="x", py_type="int", c_type=CType.MP_INT_T),
                FieldIR(name="y", py_type="int", c_type=CType.MP_INT_T),
            ],
            methods={"__init__": init_method},
        )
        emitter = ClassEmitter(class_ir, "test")
        make_new_code = "\n".join(emitter.emit_make_new())

        # Should use mp_arg_parse_all_kw_array for kwargs support
        assert "mp_arg_parse_all_kw_array" in make_new_code
        # Should have allowed_args table
        assert "allowed_args" in make_new_code
        # Should have enum for arg indices
        assert "ARG_x" in make_new_code
        assert "ARG_y" in make_new_code
        # Should have QSTR entries
        assert "MP_QSTR_x" in make_new_code
        assert "MP_QSTR_y" in make_new_code
        # Required params should have MP_ARG_REQUIRED
        assert "MP_ARG_REQUIRED" in make_new_code

    def test_emit_make_new_with_default_int_params(self):
        """make_new with int default values."""
        import ast

        from mypyc_micropython.class_emitter import ClassEmitter
        from mypyc_micropython.ir import DefaultArg, FieldIR, MethodIR

        init_ast = ast.parse("def __init__(self, x, y=10): pass").body[0]
        init_method = MethodIR(
            name="__init__",
            c_name="test_Point___init__",
            params=[("x", CType.MP_INT_T), ("y", CType.MP_INT_T)],
            return_type=CType.VOID,
            body_ast=init_ast,
            is_special=True,
            defaults={1: DefaultArg(value=10, c_expr="mp_obj_new_int(10)")},
        )

        class_ir = ClassIR(
            name="Point",
            c_name="test_Point",
            module_name="test",
            fields=[
                FieldIR(name="x", py_type="int", c_type=CType.MP_INT_T),
                FieldIR(name="y", py_type="int", c_type=CType.MP_INT_T),
            ],
            methods={"__init__": init_method},
        )
        emitter = ClassEmitter(class_ir, "test")
        make_new_code = "\n".join(emitter.emit_make_new())

        # Should use mp_arg_parse_all_kw_array
        assert "mp_arg_parse_all_kw_array" in make_new_code
        # x is required
        assert "MP_QSTR_x, MP_ARG_REQUIRED | MP_ARG_INT" in make_new_code
        # y has default value 10
        assert ".u_int = 10" in make_new_code

    def test_emit_make_new_with_default_bool_params(self):
        """make_new with bool default values."""
        import ast

        from mypyc_micropython.class_emitter import ClassEmitter
        from mypyc_micropython.ir import DefaultArg, FieldIR, MethodIR

        init_ast = ast.parse("def __init__(self, enabled=True): pass").body[0]
        init_method = MethodIR(
            name="__init__",
            c_name="test_Flag___init__",
            params=[("enabled", CType.BOOL)],
            return_type=CType.VOID,
            body_ast=init_ast,
            is_special=True,
            defaults={0: DefaultArg(value=True, c_expr="mp_const_true")},
        )

        class_ir = ClassIR(
            name="Flag",
            c_name="test_Flag",
            module_name="test",
            fields=[
                FieldIR(name="enabled", py_type="bool", c_type=CType.BOOL),
            ],
            methods={"__init__": init_method},
        )
        emitter = ClassEmitter(class_ir, "test")
        make_new_code = "\n".join(emitter.emit_make_new())

        # Should have bool default
        assert "MP_ARG_BOOL" in make_new_code
        assert ".u_bool = true" in make_new_code

    def test_emit_make_new_with_obj_params(self):
        """make_new with object (list, dict, str) params."""
        import ast

        from mypyc_micropython.class_emitter import ClassEmitter
        from mypyc_micropython.ir import DefaultArg, FieldIR, MethodIR

        init_ast = ast.parse("def __init__(self, name, items=None): pass").body[0]
        init_method = MethodIR(
            name="__init__",
            c_name="test_Container___init__",
            params=[("name", CType.MP_OBJ_T), ("items", CType.MP_OBJ_T)],
            return_type=CType.VOID,
            body_ast=init_ast,
            is_special=True,
            defaults={1: DefaultArg(value=None, c_expr="mp_const_none")},
        )

        class_ir = ClassIR(
            name="Container",
            c_name="test_Container",
            module_name="test",
            fields=[
                FieldIR(name="name", py_type="str", c_type=CType.MP_OBJ_T),
                FieldIR(name="items", py_type="list", c_type=CType.MP_OBJ_T),
            ],
            methods={"__init__": init_method},
        )
        emitter = ClassEmitter(class_ir, "test")
        make_new_code = "\n".join(emitter.emit_make_new())

        # name is required object
        assert "MP_QSTR_name, MP_ARG_REQUIRED | MP_ARG_OBJ" in make_new_code
        # items has default None
        assert "MP_QSTR_items, MP_ARG_OBJ" in make_new_code
        assert "mp_const_none" in make_new_code

    def test_emit_make_new_parsed_args_passed_to_init(self):
        """Verify parsed args are passed to __init__ call."""
        import ast

        from mypyc_micropython.class_emitter import ClassEmitter
        from mypyc_micropython.ir import FieldIR, MethodIR

        init_ast = ast.parse("def __init__(self, a, b, c): pass").body[0]
        init_method = MethodIR(
            name="__init__",
            c_name="test_Multi___init__",
            params=[
                ("a", CType.MP_INT_T),
                ("b", CType.MP_INT_T),
                ("c", CType.MP_INT_T),
            ],
            return_type=CType.VOID,
            body_ast=init_ast,
            is_special=True,
        )

        class_ir = ClassIR(
            name="Multi",
            c_name="test_Multi",
            module_name="test",
            fields=[
                FieldIR(name="a", py_type="int", c_type=CType.MP_INT_T),
                FieldIR(name="b", py_type="int", c_type=CType.MP_INT_T),
                FieldIR(name="c", py_type="int", c_type=CType.MP_INT_T),
            ],
            methods={"__init__": init_method},
        )
        emitter = ClassEmitter(class_ir, "test")
        make_new_code = "\n".join(emitter.emit_make_new())

        # Should access parsed args by index
        assert "parsed[ARG_a]" in make_new_code
        assert "parsed[ARG_b]" in make_new_code
        assert "parsed[ARG_c]" in make_new_code



class TestGeneratorEmitter:
    def test_emit_generator_while_yield_state_machine(self):
        func_ir = make_func(
            name="gen_count",
            params=[("n", CType.MP_INT_T)],
            return_type=CType.MP_OBJ_T,
            body=[
                AnnAssignIR(
                    target="i",
                    c_target="i",
                    c_type="mp_int_t",
                    value=make_const_int(0),
                    is_new_var=True,
                ),
                WhileIR(
                    test=CompareIR(
                        left=make_name("i"),
                        ops=["<"],
                        comparators=[make_name("n")],
                        ir_type=IRType.BOOL,
                    ),
                    body=[
                        YieldIR(value=make_name("i"), state_id=1),
                        AugAssignIR(
                            target="i",
                            c_target="i",
                            op="+=",
                            value=make_const_int(1),
                            target_c_type="mp_int_t",
                        ),
                    ],
                ),
                ReturnIR(value=None),
            ],
            locals_={"i": CType.MP_INT_T},
        )
        func_ir.is_generator = True

        c_code, _ = GeneratorEmitter(func_ir).emit()

        assert "typedef struct _test_gen_count_gen_t" in c_code
        assert "static mp_obj_t test_gen_count_gen_iternext(mp_obj_t self_in)" in c_code
        assert "state_1:" in c_code
        assert "MP_DEFINE_CONST_OBJ_TYPE" in c_code
        assert "MP_OBJ_STOP_ITERATION" in c_code


class TestSelfMethodCallArgumentTypes:
    """Tests for correct argument type handling in self method calls.

    These tests verify that method arguments are passed with correct types,
    not incorrectly unboxed to mp_int_t when they should remain mp_obj_t.
    Bug fix: _emit_self_method_call now uses arg.ir_type for target type.
    """

    def test_self_method_call_with_obj_arg_no_unbox(self):
        """Self method call with mp_obj_t argument should not unbox."""
        # Create a class with a method that takes an object parameter
        class_ir = ClassIR(
            name="Nav",
            c_name="test_Nav",
            module_name="test",
            fields=[
                FieldIR(name="_size", py_type="int", c_type=CType.MP_INT_T),
            ],
        )

        # Create the method that takes an object (screen) parameter
        helper_method = make_method_ir(
            name="_safe_delete",
            c_name="test_Nav__safe_delete",
            params=[("screen", CType.MP_OBJ_T)],
            return_type=CType.VOID,
        )
        class_ir.methods["_safe_delete"] = helper_method

        # Create a method that calls _safe_delete with an object argument
        caller_method = make_method_ir(
            name="pop",
            c_name="test_Nav_pop",
            params=[],
            return_type=CType.MP_OBJ_T,
        )
        class_ir.methods["pop"] = caller_method

        # Build the body IR separately (this is what emit_native expects)
        # SelfMethodCallIR is an ExprIR, so it goes in the expr field of ExprStmtIR,
        # not in the prelude (which is for InstrIR like AssignIR, TempAssignIR).
        body_ir = [
            ExprStmtIR(
                expr=SelfMethodCallIR(
                    ir_type=IRType.OBJ,
                    method_name="_safe_delete",
                    c_method_name="test_Nav__safe_delete",
                    args=[NameIR(py_name="old_screen", c_name="old_screen", ir_type=IRType.OBJ)],
                    return_type=IRType.OBJ,
                ),
                prelude=[],  # No prelude needed for simple args
            ),
            ReturnIR(value=NameIR(py_name="old_screen", c_name="old_screen", ir_type=IRType.OBJ)),
        ]

        emitter = MethodEmitter(caller_method, class_ir)
        c_code = emitter.emit_native(body_ir)

        # The method call should NOT contain mp_obj_get_int
        # It should pass old_screen directly
        assert "mp_obj_get_int(old_screen)" not in c_code, (
            "Object argument should not be unboxed with mp_obj_get_int"
        )
        assert "test_Nav__safe_delete_native(self, old_screen)" in c_code, (
            "Method call should pass object argument directly"
        )

    def test_self_method_call_with_int_arg_does_unbox(self):
        """Self method call with mp_int_t argument should unbox when needed."""
        class_ir = ClassIR(
            name="Calculator",
            c_name="test_Calculator",
            module_name="test",
            fields=[],
        )

        # Method that takes int parameter
        helper_method = make_method_ir(
            name="add",
            c_name="test_Calculator_add",
            params=[("x", CType.MP_INT_T)],
            return_type=CType.MP_INT_T,
        )
        class_ir.methods["add"] = helper_method

        # Method that calls add with an int argument
        caller_method = make_method_ir(
            name="compute",
            c_name="test_Calculator_compute",
            params=[],
            return_type=CType.MP_INT_T,
        )
        class_ir.methods["compute"] = caller_method

        # Build the body IR
        body_ir = [
            ReturnIR(
                value=SelfMethodCallIR(
                    ir_type=IRType.INT,
                    method_name="add",
                    c_method_name="test_Calculator_add",
                    args=[ConstIR(ir_type=IRType.INT, value=42)],
                    return_type=IRType.INT,
                )
            )
        ]

        emitter = MethodEmitter(caller_method, class_ir)
        c_code = emitter.emit_native(body_ir)

        # Int constant should be passed directly (no boxing/unboxing needed)
        assert "test_Calculator_add_native(self, 42)" in c_code

    def test_self_method_call_mixed_arg_types(self):
        """Self method call with both int and object args handles each correctly."""
        class_ir = ClassIR(
            name="Widget",
            c_name="test_Widget",
            module_name="test",
            fields=[],
        )

        # Method with mixed parameter types
        helper_method = make_method_ir(
            name="update",
            c_name="test_Widget_update",
            params=[("index", CType.MP_INT_T), ("data", CType.MP_OBJ_T)],
            return_type=CType.VOID,
        )
        class_ir.methods["update"] = helper_method

        # Caller method
        caller_method = make_method_ir(
            name="refresh",
            c_name="test_Widget_refresh",
            params=[],
            return_type=CType.VOID,
        )
        class_ir.methods["refresh"] = caller_method

        # Build body with mixed args
        # SelfMethodCallIR is an ExprIR, so it goes in the expr field of ExprStmtIR,
        # not in the prelude (which is for InstrIR like AssignIR, TempAssignIR).
        body_ir = [
            ExprStmtIR(
                expr=SelfMethodCallIR(
                    ir_type=IRType.OBJ,
                    method_name="update",
                    c_method_name="test_Widget_update",
                    args=[
                        ConstIR(ir_type=IRType.INT, value=0),  # int arg
                        NameIR(py_name="obj", c_name="obj", ir_type=IRType.OBJ),  # obj arg
                    ],
                    return_type=IRType.OBJ,
                ),
                prelude=[],  # No prelude needed for simple args
            ),
            ReturnIR(value=None),
        ]

        emitter = MethodEmitter(caller_method, class_ir)
        c_code = emitter.emit_native(body_ir)

        # Should pass int directly and obj directly (no mp_obj_get_int on obj)
        assert "mp_obj_get_int(obj)" not in c_code, "Object argument should not be unboxed"
        assert "test_Widget_update_native(self, 0, obj)" in c_code, (
            "Should pass int constant and object variable correctly"
        )


class TestCompareIdentityEmitter:
    """Tests for identity comparison emission (is, is not).

    These tests verify that 'is' comparisons emit pointer comparison,
    not mp_obj_get_int calls.
    """

    def test_emit_is_none_comparison(self):
        """'is None' should emit pointer comparison, not mp_obj_get_int."""
        func_ir = make_func(
            params=[("x", CType.MP_OBJ_T)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=CompareIR(
                        ir_type=IRType.BOOL,
                        left=NameIR(py_name="x", c_name="x", ir_type=IRType.OBJ),
                        ops=["is"],
                        comparators=[ConstIR(ir_type=IRType.OBJ, value=None)],
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]

        # Should use direct pointer comparison
        assert "x == mp_const_none" in c_code, "'is None' should compile to pointer comparison"
        # Should NOT use mp_obj_get_int
        assert "mp_obj_get_int" not in c_code, "'is None' should not call mp_obj_get_int"

    def test_emit_is_not_none_comparison(self):
        """'is not None' should emit pointer comparison with !=."""
        func_ir = make_func(
            params=[("x", CType.MP_OBJ_T)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=CompareIR(
                        ir_type=IRType.BOOL,
                        left=NameIR(py_name="x", c_name="x", ir_type=IRType.OBJ),
                        ops=["is not"],
                        comparators=[ConstIR(ir_type=IRType.OBJ, value=None)],
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]

        # Should use != for 'is not'
        assert "x != mp_const_none" in c_code, "'is not None' should compile to != comparison"
        assert "mp_obj_get_int" not in c_code

    def test_emit_is_comparison_between_objects(self):
        """'is' between two objects should use pointer comparison."""
        func_ir = make_func(
            params=[("a", CType.MP_OBJ_T), ("b", CType.MP_OBJ_T)],
            return_type=CType.BOOL,
            body=[
                ReturnIR(
                    value=CompareIR(
                        ir_type=IRType.BOOL,
                        left=NameIR(py_name="a", c_name="a", ir_type=IRType.OBJ),
                        ops=["is"],
                        comparators=[NameIR(py_name="b", c_name="b", ir_type=IRType.OBJ)],
                    )
                )
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]

        assert "a == b" in c_code, "'a is b' should compile to pointer comparison"
        assert "mp_obj_get_int" not in c_code


class TestForwardDeclSkipsPrivate:
    def test_forward_decl_emitted_for_regular_methods(self):
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="App",
            c_name="test_App",
            module_name="test",
            fields=[],
        )
        method = make_method_ir(
            name="dispatch",
            c_name="test_App_dispatch",
            params=[("msg", CType.MP_OBJ_T)],
            return_type=CType.VOID,
        )
        class_ir.methods["dispatch"] = method
        emitter = ClassEmitter(class_ir, "test")
        fwd = "\n".join(emitter.emit_method_obj_forward_declarations())
        assert "test_App_dispatch_obj" in fwd

    def test_forward_decl_skipped_for_private_methods(self):
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="App",
            c_name="test_App",
            module_name="test",
            fields=[],
        )
        method = make_method_ir(
            name="__compute",
            c_name="test_App___compute",
            params=[("x", CType.MP_INT_T)],
            return_type=CType.MP_INT_T,
        )
        method.is_private = True
        class_ir.methods["__compute"] = method
        emitter = ClassEmitter(class_ir, "test")
        fwd = "\n".join(emitter.emit_method_obj_forward_declarations())
        assert "test_App___compute_obj" not in fwd

    def test_forward_decl_skipped_for_static_methods(self):
        from mypyc_micropython.class_emitter import ClassEmitter

        class_ir = ClassIR(
            name="App",
            c_name="test_App",
            module_name="test",
            fields=[],
        )
        method = make_method_ir(
            name="create",
            c_name="test_App_create",
            params=[],
            return_type=CType.MP_OBJ_T,
        )
        method.is_static = True
        class_ir.methods["create"] = method
        emitter = ClassEmitter(class_ir, "test")
        fwd = "\n".join(emitter.emit_method_obj_forward_declarations())
        assert "test_App_create_obj" not in fwd


class TestObjAttrAssignEmission:
    """Tests for ObjAttrAssignIR -> C code emission."""

    def test_generic_path_uses_mp_store_attr(self):
        """Unknown class should emit mp_store_attr."""
        stmt = ObjAttrAssignIR(
            obj_name="cmd",
            obj_class=None,
            attr_name="effects",
            attr_path="effects",
            value=make_const_int(42),
            prelude=[],
        )
        func = make_func(
            name="test",
            body=[stmt],
            locals_={"cmd": CType.MP_OBJ_T},
        )
        emitter = FunctionEmitter(func)
        lines = emitter._emit_obj_attr_assign(stmt)
        code = "\n".join(lines)
        assert "mp_store_attr" in code
        assert "MP_QSTR_effects" in code
        assert "cmd" in code

    def test_native_class_path_uses_struct_cast(self):
        """Known native class should emit struct cast and direct field access."""
        stmt = ObjAttrAssignIR(
            obj_name="holder",
            obj_class="test_Holder",
            attr_name="value",
            attr_path="value",
            value=make_const_int(99),
            prelude=[],
        )
        func = make_func(
            name="test",
            body=[stmt],
            locals_={"holder": CType.MP_OBJ_T},
        )
        emitter = FunctionEmitter(func)
        lines = emitter._emit_obj_attr_assign(stmt)
        code = "\n".join(lines)
        assert "test_Holder_obj_t" in code
        assert "MP_OBJ_TO_PTR" in code
        assert "->value" in code
        # Should NOT use mp_store_attr for native path
        assert "mp_store_attr" not in code

    def test_prelude_emitted_before_assignment(self):
        """Prelude instructions should appear before the assignment."""
        from mypyc_micropython.ir import ListNewIR
        prelude_instr = ListNewIR(
            result=TempIR(name="_tmp1", ir_type=IRType.OBJ),
            items=[make_const_int(1), make_const_int(2)],
        )
        stmt = ObjAttrAssignIR(
            obj_name="obj",
            obj_class=None,
            attr_name="items",
            attr_path="items",
            value=TempIR(name="_tmp1", ir_type=IRType.OBJ),
            prelude=[prelude_instr],
        )
        func = make_func(
            name="test",
            body=[stmt],
            locals_={"obj": CType.MP_OBJ_T},
            max_temp=2,
        )
        emitter = FunctionEmitter(func)
        lines = emitter._emit_obj_attr_assign(stmt)
        code = "\n".join(lines)
        # Prelude (list creation) should come before mp_store_attr
        list_pos = code.find("mp_obj_new_list")
        store_pos = code.find("mp_store_attr")
        assert list_pos < store_pos, "Prelude must come before the assignment"


class TestMypyAnyFieldTypeFallback:
    """Bug 5: When field py_type resolves correctly (not Any), chained
    attribute access should generate native struct access, not mp_load_attr."""

    def test_chained_attr_uses_native_access_for_known_class(self):
        """self.config.name should use self->config->name, not mp_load_attr.
        This verifies Bug 5 fix: field typed as known class enables native path."""
        from mypyc_micropython.compiler import compile_source
        source = '''
class Config:
    name: str
    value: int

    def __init__(self, name: str, value: int) -> None:
        self.name = name
        self.value = value

class App:
    config: Config

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_name(self) -> str:
        return self.config.name
'''
        c_code = compile_source(source, "test")
        # With proper type resolution, self.config.name should use native
        # struct access: self->config->name (not mp_load_attr)
        assert "self->config" in c_code, (
            "Expected native struct access for self.config but not found"
        )

    def test_any_typed_field_falls_back_to_generic_access(self):
        """When field type is unresolved (object), chained access uses mp_load_attr."""
        from mypyc_micropython.compiler import compile_source
        # Use 'object' typed field (simulates unresolved Any)
        source = '''
class Container:
    item: object

    def __init__(self, item: object) -> None:
        self.item = item

    def get_label(self) -> object:
        return self.item
'''
        c_code = compile_source(source, "test")
        # 'object' typed field: cannot do chained native access
        # self.item access should still work but won't chain natively
        assert "self->item" in c_code


class TestFuncRefIREmission:
    """Test that FuncRefIR is correctly emitted by container_emitter.

    Bug fixed: container_emitter.py did not handle FuncRefIR, causing
    `/* unknown value */` to be emitted when passing function references
    as method arguments (e.g., reconciler.register_factory(KEY, create_fn)).
    """

    def test_func_ref_emitted_as_ptr(self):
        """FuncRefIR should emit MP_OBJ_FROM_PTR(&func_name_obj)."""
        from mypyc_micropython.container_emitter import ContainerEmitter
        from mypyc_micropython.ir import FuncRefIR, IRType

        emitter = ContainerEmitter()
        func_ref = FuncRefIR(
            ir_type=IRType.OBJ,
            py_name="create_label",
            c_name="factories_create_label",
        )
        result = emitter._value_to_c(func_ref)
        assert result == "MP_OBJ_FROM_PTR(&factories_create_label_obj)"

    def test_func_ref_in_method_call_arg(self):
        """Function reference passed as method argument should not produce 'unknown value'."""
        from mypyc_micropython.compiler import compile_source

        source = '''
class Registry:
    def register(self, key: int, handler: object) -> None:
        pass

def my_handler(x: int) -> int:
    return x

def setup(reg: Registry) -> None:
    reg.register(1, my_handler)
'''
        result = compile_source(source, "test", type_check=False)
        # Should have the function pointer reference, not /* unknown value */
        assert "MP_OBJ_FROM_PTR(&test_my_handler_obj)" in result
        assert "/* unknown value */" not in result

    def test_func_ref_multiple_args_to_method(self):
        """Multiple function references passed to same method call."""
        from mypyc_micropython.compiler import compile_source

        source = '''
class Dispatcher:
    def register(self, success_cb: object, error_cb: object) -> None:
        pass

def on_success(x: int) -> int:
    return x

def on_error(x: int) -> int:
    return -x

def init(d: Dispatcher) -> None:
    d.register(on_success, on_error)
'''
        result = compile_source(source, "test", type_check=False)
        assert "MP_OBJ_FROM_PTR(&test_on_success_obj)" in result
        assert "MP_OBJ_FROM_PTR(&test_on_error_obj)" in result
        assert "/* unknown value */" not in result


# ============================================================================
# Test: Bug C - Dotted module imports (chained mp_load_attr)
# ============================================================================


class TestDottedModuleImport:
    """Test that dotted module names emit chained mp_load_attr calls.

    Bug fixed: `from pkg.sub import func` emitted flat
    `mp_import_name(MP_QSTR_pkg_sub, ...)` instead of chained
    `mp_load_attr(mp_import_name(MP_QSTR_pkg, ...), MP_QSTR_sub)`.
    """

    def test_dotted_module_call_emits_chained_attr(self):
        """ModuleCallIR with 'pkg.sub' module_name -> chained mp_load_attr."""
        func_ir = make_func(
            params=[("x", CType.MP_OBJ_T)],
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                ReturnIR(
                    value=ModuleCallIR(
                        ir_type=IRType.OBJ,
                        module_name="pkg.sub",
                        func_name="func",
                        args=[make_name("x", IRType.OBJ)],
                    ),
                    prelude=[],
                ),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Should have chained import: mp_load_attr(mp_import_name(pkg), sub)
        assert "mp_import_name(MP_QSTR_pkg" in c_code
        assert "mp_load_attr(" in c_code
        assert "MP_QSTR_sub" in c_code
        # Should NOT have flat import with underscore-joined name
        assert "MP_QSTR_pkg_sub" not in c_code

    def test_single_module_call_no_chaining(self):
        """ModuleCallIR with non-dotted name -> simple mp_import_name."""
        func_ir = make_func(
            params=[("x", CType.MP_OBJ_T)],
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                ReturnIR(
                    value=ModuleCallIR(
                        ir_type=IRType.OBJ,
                        module_name="math",
                        func_name="sqrt",
                        args=[make_name("x", IRType.OBJ)],
                    ),
                    prelude=[],
                ),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Simple single-component module
        assert "mp_import_name(MP_QSTR_math" in c_code
        assert "MP_QSTR_sqrt" in c_code

    def test_three_level_dotted_module(self):
        """ModuleCallIR with 'a.b.c' -> double chained mp_load_attr."""
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                ReturnIR(
                    value=ModuleCallIR(
                        ir_type=IRType.OBJ,
                        module_name="a.b.c",
                        func_name="func",
                        args=[],
                    ),
                    prelude=[],
                ),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # Should chain: mp_load_attr(mp_load_attr(mp_import_name(a), b), c)
        assert "mp_import_name(MP_QSTR_a" in c_code
        assert "MP_QSTR_b" in c_code
        assert "MP_QSTR_c" in c_code


# ============================================================================
# Test: Bug D - ModuleCallIR in container_emitter _value_to_c
# ============================================================================


class TestModuleCallIRInValueToC:
    """Test that ModuleCallIR is handled in container_emitter._value_to_c.

    Bug fixed: When ModuleCallIR appears as receiver inside MethodCallIR
    in a prelude (e.g., Button(\"-\").size(60, 40)), _value_to_c returned
    '/* unknown value */' instead of emitting the call properly.
    """

    def test_module_call_as_method_receiver(self):
        """Button('-').size(60, 40) - ModuleCallIR as method receiver."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                ExprStmtIR(
                    expr=temp,
                    prelude=[
                        MethodCallIR(
                            result=temp,
                            receiver=ModuleCallIR(
                                ir_type=IRType.OBJ,
                                module_name="ui",
                                func_name="Button",
                                args=[make_const_str("-")],
                            ),
                            method="size",
                            args=[make_const_int(60), make_const_int(40)],
                            receiver_py_type=None,
                        )
                    ],
                ),
                ReturnIR(value=temp, prelude=[]),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        # The ModuleCallIR should be emitted as a call, not /* unknown value */
        assert "/* unknown value */" not in c_code
        assert "mp_import_name(MP_QSTR_ui" in c_code
        assert "MP_QSTR_Button" in c_code
        assert "MP_QSTR_size" in c_code

    def test_module_call_with_kwargs_as_receiver(self):
        """VStack(spacing=20).children(...) - ModuleCallIR with kwargs."""
        temp = make_temp("_tmp0")
        func_ir = make_func(
            return_type=CType.MP_OBJ_T,
            max_temp=1,
            body=[
                ExprStmtIR(
                    expr=temp,
                    prelude=[
                        MethodCallIR(
                            result=temp,
                            receiver=ModuleCallIR(
                                ir_type=IRType.OBJ,
                                module_name="layouts",
                                func_name="VStack",
                                args=[],
                                kwargs=[("spacing", make_const_int(20))],
                            ),
                            method="children",
                            args=[],
                            receiver_py_type=None,
                        )
                    ],
                ),
                ReturnIR(value=temp, prelude=[]),
            ],
        )
        c_code = FunctionEmitter(func_ir).emit()[0]
        assert "/* unknown value */" not in c_code
        assert "mp_import_name(MP_QSTR_layouts" in c_code
        assert "MP_QSTR_VStack" in c_code
        # kwargs should produce kw call
        assert "MP_QSTR_spacing" in c_code


# ============================================================================
# Test: Bug B - TempAssignIR emission
# ============================================================================


class TestTempAssignIREmission:
    """Test that TempAssignIR is correctly emitted as C temp assignment.

    Bug fixed: Created TempAssignIR(InstrIR) for callable-call-result
    pattern where a complex expression must be stored in temp before use.
    """

    def test_temp_assign_basic(self):
        """TempAssignIR should emit mp_obj_t _tmpN = <value>."""
        from mypyc_micropython.container_emitter import ContainerEmitter
        from mypyc_micropython.ir import TempAssignIR

        emitter = ContainerEmitter()
        temp = TempIR(ir_type=IRType.OBJ, name="_tmp0")
        value = ConstIR(ir_type=IRType.OBJ, value="hello")
        instr = TempAssignIR(result=temp, value=value)
        c_lines = emitter.emit_instr(instr)
        c_line = "\n".join(c_lines)
        assert "_tmp0" in c_line
        # Should assign the string constant to the temp
        assert "mp_obj_new_str" in c_line or "MP_OBJ_NEW_QSTR" in c_line
