"""Unit tests for emitters - IR to C code generation.

This module tests the emitters in isolation from the IR builder.
By constructing IR nodes manually, we can:
1. Test emitter logic without IR builder dependencies
2. Create edge cases that are hard to trigger via Python source
3. Quickly pinpoint whether bugs are in IR building or code emission

Test naming convention: test_emit_<feature>_<behavior>
"""

from __future__ import annotations

from mypyc_micropython.function_emitter import FunctionEmitter
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
    NameIR,
    PassIR,
    ReturnIR,
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
