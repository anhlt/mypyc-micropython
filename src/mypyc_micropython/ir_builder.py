"""
IR Builder: AST -> IR translation.

This module transforms Python AST nodes into IR data structures.
The IR is then consumed by emitters to generate C code.
"""

from __future__ import annotations

import ast
import re

from .ir import (
    AnnAssignIR,
    AssignIR,
    AttrAssignIR,
    AugAssignIR,
    BinOpIR,
    BreakIR,
    CallIR,
    ClassInstantiationIR,
    ClassIR,
    CompareIR,
    ConstIR,
    ContinueIR,
    CType,
    DataclassInfo,
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
    NameIR,
    PassIR,
    PrintIR,
    ReturnIR,
    RTuple,
    SelfAttrIR,
    SelfAugAssignIR,
    SelfMethodCallIR,
    SetNewIR,
    SliceIR,
    StmtIR,
    SubscriptAssignIR,
    SubscriptIR,
    TempIR,
    TupleNewIR,
    TupleUnpackIR,
    UnaryOpIR,
    ValueIR,
    WhileIR,
)

C_RESERVED_WORDS = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "int",
    "long",
    "register",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "inline",
    "restrict",
    "_Bool",
    "_Complex",
    "_Imaginary",
}


def sanitize_name(name: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if result and result[0].isdigit():
        result = "_" + result
    if result in C_RESERVED_WORDS:
        result = result + "_"
    return result


class IRBuilder:
    """Builds IR from Python AST nodes."""

    def __init__(self, module_name: str, known_classes: dict[str, ClassIR] | None = None):
        self.module_name = module_name
        self.c_name = sanitize_name(module_name)
        self._known_classes = known_classes or {}
        self._temp_counter = 0
        self._var_types: dict[str, str] = {}
        self._list_vars: set[str] = set()
        self._rtuple_types: dict[str, RTuple] = {}
        self._used_rtuples: set[RTuple] = set()
        self._uses_print = False
        self._uses_list_opt = False
        self._loop_depth = 0

    def _fresh_temp(self) -> str:
        self._temp_counter += 1
        return f"_tmp{self._temp_counter}"

    def build_function(self, node: ast.FunctionDef) -> FuncIR:
        self._var_types = {}
        self._list_vars = set()
        self._rtuple_types = {}
        self._used_rtuples = set()
        self._uses_print = False
        self._uses_list_opt = False

        func_name = node.name
        c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"

        params: list[tuple[str, CType]] = []
        arg_types: list[str] = []
        for arg in node.args.args:
            c_type_str = (
                self._annotation_to_c_type(arg.annotation) if arg.annotation else "mp_obj_t"
            )
            c_type = (
                CType.from_python_type(self._annotation_to_py_type(arg.annotation))
                if arg.annotation
                else CType.MP_OBJ_T
            )
            params.append((arg.arg, c_type))
            arg_types.append(c_type_str)
            self._var_types[arg.arg] = c_type_str
            if arg.annotation and self._is_list_annotation(arg.annotation):
                self._list_vars.add(arg.arg)

        return_type = (
            CType.from_python_type(self._annotation_to_py_type(node.returns))
            if node.returns
            else CType.MP_OBJ_T
        )

        local_vars = [arg.arg for arg in node.args.args]
        body_ir: list[StmtIR] = []
        for stmt in node.body:
            stmt_ir = self._build_statement(stmt, local_vars)
            if stmt_ir is not None:
                body_ir.append(stmt_ir)

        return FuncIR(
            name=func_name,
            c_name=c_func_name,
            params=params,
            return_type=return_type,
            body_ast=node,
            body=body_ir,
            is_method=False,
            class_ir=None,
            locals_={
                name: CType.from_python_type(
                    self._c_type_to_py_type(self._var_types.get(name, "mp_obj_t"))
                )
                for name in local_vars
            },
            docstring=ast.get_docstring(node),
            arg_types=arg_types,
            uses_print=self._uses_print,
            uses_list_opt=self._uses_list_opt,
            used_rtuples=set(self._used_rtuples),
            rtuple_types=dict(self._rtuple_types),
            list_vars=set(self._list_vars),
        )

    def _build_statement(self, stmt: ast.stmt, locals_: list[str]) -> StmtIR | None:
        if isinstance(stmt, ast.Return):
            return self._build_return(stmt, locals_)
        elif isinstance(stmt, ast.If):
            return self._build_if(stmt, locals_)
        elif isinstance(stmt, ast.While):
            return self._build_while(stmt, locals_)
        elif isinstance(stmt, ast.For):
            return self._build_for(stmt, locals_)
        elif isinstance(stmt, ast.Assign):
            return self._build_assign(stmt, locals_)
        elif isinstance(stmt, ast.AnnAssign):
            return self._build_ann_assign(stmt, locals_)
        elif isinstance(stmt, ast.AugAssign):
            return self._build_aug_assign(stmt, locals_)
        elif isinstance(stmt, ast.Break):
            return BreakIR()
        elif isinstance(stmt, ast.Continue):
            return ContinueIR()
        elif isinstance(stmt, ast.Pass):
            return PassIR()
        elif isinstance(stmt, ast.Expr):
            if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                return None
            if (
                isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == "print"
            ):
                return self._build_print(stmt.value, locals_)
            value, prelude = self._build_expr(stmt.value, locals_)
            return ExprStmtIR(expr=value, prelude=prelude)
        return None

    def _build_return(self, stmt: ast.Return, locals_: list[str]) -> ReturnIR:
        if stmt.value is None:
            return ReturnIR(value=None, prelude=[])
        value, prelude = self._build_expr(stmt.value, locals_)
        return ReturnIR(value=value, prelude=prelude)

    def _build_if(self, stmt: ast.If, locals_: list[str]) -> IfIR:
        test, test_prelude = self._build_expr(stmt.test, locals_)
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]
        orelse = [self._build_statement(s, locals_) for s in stmt.orelse]
        orelse = [s for s in orelse if s is not None]
        return IfIR(test=test, body=body, orelse=orelse, test_prelude=test_prelude)

    def _build_while(self, stmt: ast.While, locals_: list[str]) -> WhileIR:
        test, test_prelude = self._build_expr(stmt.test, locals_)
        self._loop_depth += 1
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1
        return WhileIR(test=test, body=body, test_prelude=test_prelude)

    def _build_for(self, stmt: ast.For, locals_: list[str]) -> ForRangeIR | ForIterIR:
        if not isinstance(stmt.target, ast.Name):
            raise ValueError("Unsupported for loop target")

        loop_var = stmt.target.id
        c_loop_var = sanitize_name(loop_var)
        is_new_var = loop_var not in locals_
        if is_new_var:
            locals_.append(loop_var)
            self._var_types[loop_var] = "mp_int_t"

        if (
            isinstance(stmt.iter, ast.Call)
            and isinstance(stmt.iter.func, ast.Name)
            and stmt.iter.func.id == "range"
        ):
            return self._build_for_range(stmt, loop_var, c_loop_var, is_new_var, locals_)
        else:
            return self._build_for_iter(stmt, loop_var, c_loop_var, is_new_var, locals_)

    def _build_for_range(
        self, stmt: ast.For, loop_var: str, c_loop_var: str, is_new_var: bool, locals_: list[str]
    ) -> ForRangeIR:
        assert isinstance(stmt.iter, ast.Call)
        args = stmt.iter.args

        step_is_constant = False
        step_value: int | None = None
        step: ValueIR | None = None

        if len(args) == 1:
            start = ConstIR(ir_type=IRType.INT, value=0)
            end, _ = self._build_expr(args[0], locals_)
            step_is_constant = True
            step_value = 1
        elif len(args) == 2:
            start, _ = self._build_expr(args[0], locals_)
            end, _ = self._build_expr(args[1], locals_)
            step_is_constant = True
            step_value = 1
        elif len(args) == 3:
            start, _ = self._build_expr(args[0], locals_)
            end, _ = self._build_expr(args[1], locals_)
            if isinstance(args[2], ast.Constant) and isinstance(args[2].value, int):
                step_is_constant = True
                step_value = args[2].value
            elif isinstance(args[2], ast.UnaryOp) and isinstance(args[2].op, ast.USub):
                if isinstance(args[2].operand, ast.Constant) and isinstance(
                    args[2].operand.value, int
                ):
                    step_is_constant = True
                    step_value = -args[2].operand.value
                else:
                    step, _ = self._build_expr(args[2], locals_)
            else:
                step, _ = self._build_expr(args[2], locals_)
        else:
            raise ValueError("Unsupported range() call")

        self._loop_depth += 1
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1

        return ForRangeIR(
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            start=start,
            end=end,
            step=step,
            step_is_constant=step_is_constant,
            step_value=step_value,
            body=body,
            is_new_var=is_new_var,
        )

    def _build_for_iter(
        self, stmt: ast.For, loop_var: str, c_loop_var: str, is_new_var: bool, locals_: list[str]
    ) -> ForIterIR:
        iterable, iter_prelude = self._build_expr(stmt.iter, locals_)
        self._var_types[loop_var] = "mp_obj_t"

        self._loop_depth += 1
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1

        return ForIterIR(
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            iterable=iterable,
            body=body,
            iter_prelude=iter_prelude,
            is_new_var=is_new_var,
        )

    def _build_assign(self, stmt: ast.Assign, locals_: list[str]) -> StmtIR | None:
        if len(stmt.targets) != 1:
            return None

        target = stmt.targets[0]

        if isinstance(target, ast.Subscript):
            return self._build_subscript_assign(target, stmt.value, locals_)

        if isinstance(target, ast.Tuple):
            return self._build_tuple_unpack(target, stmt.value, locals_)

        if not isinstance(target, ast.Name):
            return None

        var_name = target.id
        c_var_name = sanitize_name(var_name)
        value, prelude = self._build_expr(stmt.value, locals_)
        is_new_var = var_name not in locals_
        if is_new_var:
            locals_.append(var_name)

        value_type = self._get_value_ir_type(value)
        c_type = value_type.to_c_type_str()
        self._var_types[var_name] = c_type

        return AssignIR(
            target=var_name,
            c_target=c_var_name,
            value=value,
            value_type=value_type,
            prelude=prelude,
            is_new_var=is_new_var,
            c_type=c_type,
        )

    def _build_subscript_assign(
        self, target: ast.Subscript, value: ast.expr, locals_: list[str]
    ) -> SubscriptAssignIR:
        container, prelude1 = self._build_expr(target.value, locals_)
        key, prelude2 = self._build_expr(target.slice, locals_)
        val, prelude3 = self._build_expr(value, locals_)
        return SubscriptAssignIR(
            container=container,
            key=key,
            value=val,
            prelude=prelude1 + prelude2 + prelude3,
        )

    def _build_tuple_unpack(
        self, target: ast.Tuple, value: ast.expr, locals_: list[str]
    ) -> TupleUnpackIR:
        tuple_value, prelude = self._build_expr(value, locals_)
        targets: list[tuple[str, str, bool, str]] = []
        for elt in target.elts:
            if isinstance(elt, ast.Name):
                var_name = elt.id
                c_var_name = sanitize_name(var_name)
                is_new = var_name not in locals_
                c_type = self._var_types.get(var_name, "mp_obj_t")
                if is_new:
                    locals_.append(var_name)
                    self._var_types[var_name] = "mp_obj_t"
                    c_type = "mp_obj_t"
                targets.append((var_name, c_var_name, is_new, c_type))
        return TupleUnpackIR(targets=targets, value=tuple_value, prelude=prelude)

    def _build_ann_assign(self, stmt: ast.AnnAssign, locals_: list[str]) -> AnnAssignIR | None:
        if not isinstance(stmt.target, ast.Name):
            return None

        var_name = stmt.target.id
        c_var_name = sanitize_name(var_name)
        c_type = self._annotation_to_c_type(stmt.annotation) if stmt.annotation else "mp_int_t"

        rtuple = self._try_parse_rtuple(stmt.annotation)
        if rtuple is not None:
            self._rtuple_types[var_name] = rtuple
            self._used_rtuples.add(rtuple)
            c_type = rtuple.get_c_struct_name()

        if self._is_list_annotation(stmt.annotation):
            self._list_vars.add(var_name)

        is_new_var = var_name not in locals_
        if is_new_var:
            locals_.append(var_name)
        self._var_types[var_name] = c_type

        value: ValueIR | None = None
        prelude: list = []
        if stmt.value is not None:
            value, prelude = self._build_expr(stmt.value, locals_)

        return AnnAssignIR(
            target=var_name,
            c_target=c_var_name,
            c_type=c_type,
            value=value,
            prelude=prelude,
            is_new_var=is_new_var,
        )

    def _build_aug_assign(self, stmt: ast.AugAssign, locals_: list[str]) -> AugAssignIR | None:
        if not isinstance(stmt.target, ast.Name):
            return None

        var_name = stmt.target.id
        c_var_name = sanitize_name(var_name)
        value, prelude = self._build_expr(stmt.value, locals_)

        op_map = {
            ast.Add: "+=",
            ast.Sub: "-=",
            ast.Mult: "*=",
            ast.Div: "/=",
            ast.Mod: "%=",
            ast.BitAnd: "&=",
            ast.BitOr: "|=",
            ast.BitXor: "^=",
            ast.LShift: "<<=",
            ast.RShift: ">>=",
        }
        c_op = op_map.get(type(stmt.op), "+=")

        return AugAssignIR(
            target=var_name,
            c_target=c_var_name,
            op=c_op,
            value=value,
            prelude=prelude,
        )

    def _build_print(self, call: ast.Call, locals_: list[str]) -> PrintIR:
        self._uses_print = True
        args: list[ValueIR] = []
        preludes: list[list] = []
        for arg in call.args:
            value, prelude = self._build_expr(arg, locals_)
            args.append(value)
            preludes.append(prelude)
        return PrintIR(args=args, preludes=preludes)

    def _build_expr(self, expr: ast.expr, locals_: list[str]) -> tuple[ValueIR, list]:
        if isinstance(expr, ast.Constant):
            return self._build_constant(expr), []
        elif isinstance(expr, ast.Name):
            return self._build_name(expr, locals_), []
        elif isinstance(expr, ast.BinOp):
            return self._build_binop(expr, locals_)
        elif isinstance(expr, ast.UnaryOp):
            return self._build_unaryop(expr, locals_)
        elif isinstance(expr, ast.Compare):
            return self._build_compare(expr, locals_)
        elif isinstance(expr, ast.Call):
            return self._build_call(expr, locals_)
        elif isinstance(expr, ast.IfExp):
            return self._build_ifexp(expr, locals_)
        elif isinstance(expr, ast.List):
            return self._build_list(expr, locals_)
        elif isinstance(expr, ast.Tuple):
            return self._build_tuple(expr, locals_)
        elif isinstance(expr, ast.Set):
            return self._build_set(expr, locals_)
        elif isinstance(expr, ast.Dict):
            return self._build_dict(expr, locals_)
        elif isinstance(expr, ast.Subscript):
            return self._build_subscript(expr, locals_)
        return ConstIR(ir_type=IRType.OBJ, value=None), []

    def _build_constant(self, expr: ast.Constant) -> ConstIR:
        val = expr.value
        if isinstance(val, bool):
            return ConstIR(ir_type=IRType.BOOL, value=val)
        elif isinstance(val, int):
            return ConstIR(ir_type=IRType.INT, value=val)
        elif isinstance(val, float):
            return ConstIR(ir_type=IRType.FLOAT, value=val)
        elif val is None:
            return ConstIR(ir_type=IRType.OBJ, value=None)
        elif isinstance(val, str):
            return ConstIR(ir_type=IRType.OBJ, value=val)
        return ConstIR(ir_type=IRType.OBJ, value=val)

    def _build_name(self, expr: ast.Name, locals_: list[str]) -> ValueIR:
        name = expr.id
        if name == "True":
            return ConstIR(ir_type=IRType.BOOL, value=True)
        elif name == "False":
            return ConstIR(ir_type=IRType.BOOL, value=False)
        elif name == "None":
            return ConstIR(ir_type=IRType.OBJ, value=None)

        c_name = sanitize_name(name)
        var_type = self._var_types.get(name, "mp_int_t")
        ir_type = IRType.from_c_type_str(var_type)
        return NameIR(ir_type=ir_type, py_name=name, c_name=c_name)

    def _build_binop(self, expr: ast.BinOp, locals_: list[str]) -> tuple[BinOpIR, list]:
        left, left_prelude = self._build_expr(expr.left, locals_)
        right, right_prelude = self._build_expr(expr.right, locals_)

        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.FloorDiv: "/",
            ast.Mod: "%",
            ast.BitAnd: "&",
            ast.BitOr: "|",
            ast.BitXor: "^",
            ast.LShift: "<<",
            ast.RShift: ">>",
        }
        c_op = op_map.get(type(expr.op), "+")

        left_type = self._get_value_ir_type(left)
        right_type = self._get_value_ir_type(right)

        if left_type == IRType.OBJ or right_type == IRType.OBJ:
            left_is_subscript = isinstance(left, SubscriptIR)
            right_is_subscript = isinstance(right, SubscriptIR)
            if left_is_subscript or right_is_subscript:
                result_type = IRType.INT
            else:
                result_type = IRType.OBJ
        elif left_type == IRType.FLOAT or right_type == IRType.FLOAT:
            result_type = IRType.FLOAT
        else:
            result_type = IRType.INT

        return BinOpIR(
            ir_type=result_type,
            left=left,
            op=c_op,
            right=right,
            left_prelude=left_prelude,
            right_prelude=right_prelude,
        ), left_prelude + right_prelude

    def _build_unaryop(self, expr: ast.UnaryOp, locals_: list[str]) -> tuple[UnaryOpIR, list]:
        operand, prelude = self._build_expr(expr.operand, locals_)
        op_map = {ast.USub: "-", ast.Not: "!", ast.UAdd: "+", ast.Invert: "~"}
        c_op = op_map.get(type(expr.op), "-")

        result_type = (
            IRType.BOOL if isinstance(expr.op, ast.Not) else self._get_value_ir_type(operand)
        )

        return UnaryOpIR(
            ir_type=result_type,
            op=c_op,
            operand=operand,
            prelude=prelude,
        ), prelude

    def _build_compare(self, expr: ast.Compare, locals_: list[str]) -> tuple[CompareIR, list]:
        left, left_prelude = self._build_expr(expr.left, locals_)

        op_map = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.In: "in",
            ast.NotIn: "not in",
        }

        ops: list[str] = []
        comparators: list[ValueIR] = []
        comparator_preludes: list[list] = []
        has_contains = False

        for op, comparator in zip(expr.ops, expr.comparators):
            c_op = op_map.get(type(op), "==")
            if c_op in ("in", "not in"):
                has_contains = True
            ops.append(c_op)
            comp_val, comp_prelude = self._build_expr(comparator, locals_)
            comparators.append(comp_val)
            comparator_preludes.append(comp_prelude)

        all_preludes = left_prelude + [p for pl in comparator_preludes for p in pl]

        return CompareIR(
            ir_type=IRType.BOOL,
            left=left,
            ops=ops,
            comparators=comparators,
            has_contains=has_contains,
            left_prelude=left_prelude,
            comparator_preludes=comparator_preludes,
        ), all_preludes

    def _build_call(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
        if isinstance(expr.func, ast.Attribute):
            return self._build_method_call(expr, locals_)

        if not isinstance(expr.func, ast.Name):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        func_name = expr.func.id

        if func_name in self._known_classes:
            return self._build_class_instantiation(expr, func_name, locals_)

        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            args.append(val)
            arg_preludes.append(prelude)

        all_preludes = [p for pl in arg_preludes for p in pl]

        builtins = {"abs", "int", "float", "len", "range", "list", "tuple", "set", "dict"}
        if func_name in builtins:
            is_list_len_opt = False
            if func_name == "len" and len(args) == 1:
                arg = args[0]
                if isinstance(arg, NameIR) and arg.py_name in self._list_vars:
                    is_list_len_opt = True
                    self._uses_list_opt = True
            return CallIR(
                ir_type=IRType.INT
                if func_name in ("abs", "int", "len")
                else (IRType.FLOAT if func_name == "float" else IRType.OBJ),
                func_name=func_name,
                c_func_name=func_name,
                args=args,
                arg_preludes=arg_preludes,
                is_builtin=True,
                builtin_kind=func_name,
                is_list_len_opt=is_list_len_opt,
            ), all_preludes

        c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"
        return CallIR(
            ir_type=IRType.INT,
            func_name=func_name,
            c_func_name=c_func_name,
            args=args,
            arg_preludes=arg_preludes,
            is_builtin=False,
            builtin_kind=None,
        ), all_preludes

    def _build_method_call(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
        if not isinstance(expr.func, ast.Attribute):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        receiver, recv_prelude = self._build_expr(expr.func.value, locals_)
        method_name = expr.func.attr

        args: list[ValueIR] = []
        all_preludes = list(recv_prelude)
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            all_preludes.extend(prelude)
            args.append(val)

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        method_call = MethodCallIR(result=result, receiver=receiver, method=method_name, args=args)

        return result, all_preludes + [method_call]

    def _build_class_instantiation(
        self, expr: ast.Call, class_name: str, locals_: list[str]
    ) -> tuple[ClassInstantiationIR, list]:
        class_ir = self._known_classes[class_name]
        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            args.append(val)
            arg_preludes.append(prelude)

        all_preludes = [p for pl in arg_preludes for p in pl]

        return ClassInstantiationIR(
            ir_type=IRType.OBJ,
            class_name=class_name,
            c_class_name=class_ir.c_name,
            args=args,
            arg_preludes=arg_preludes,
        ), all_preludes

    def _build_ifexp(self, expr: ast.IfExp, locals_: list[str]) -> tuple[IfExprIR, list]:
        test, test_prelude = self._build_expr(expr.test, locals_)
        body, body_prelude = self._build_expr(expr.body, locals_)
        orelse, orelse_prelude = self._build_expr(expr.orelse, locals_)

        return IfExprIR(
            ir_type=self._get_value_ir_type(body),
            test=test,
            body=body,
            orelse=orelse,
            test_prelude=test_prelude,
            body_prelude=body_prelude,
            orelse_prelude=orelse_prelude,
        ), test_prelude + body_prelude + orelse_prelude

    def _build_list(self, expr: ast.List, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.elts:
            return ConstIR(ir_type=IRType.OBJ, value=[]), []

        items: list[ValueIR] = []
        for elt in expr.elts:
            val, _ = self._build_expr(elt, locals_)
            items.append(val)

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, [ListNewIR(result=result, items=items)]

    def _build_tuple(self, expr: ast.Tuple, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.elts:
            return ConstIR(ir_type=IRType.OBJ, value=()), []

        items: list[ValueIR] = []
        for elt in expr.elts:
            val, _ = self._build_expr(elt, locals_)
            items.append(val)

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, [TupleNewIR(result=result, items=items)]

    def _build_set(self, expr: ast.Set, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.elts:
            return ConstIR(ir_type=IRType.OBJ, value=set()), []

        items: list[ValueIR] = []
        for elt in expr.elts:
            val, _ = self._build_expr(elt, locals_)
            items.append(val)

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, [SetNewIR(result=result, items=items)]

    def _build_dict(self, expr: ast.Dict, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.keys:
            return ConstIR(ir_type=IRType.OBJ, value={}), []

        entries: list[tuple[ValueIR, ValueIR]] = []
        for key, val in zip(expr.keys, expr.values):
            if key is None:
                continue
            key_val, _ = self._build_expr(key, locals_)
            val_val, _ = self._build_expr(val, locals_)
            entries.append((key_val, val_val))

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, [DictNewIR(result=result, entries=entries)]

    def _build_subscript(self, expr: ast.Subscript, locals_: list[str]) -> tuple[SubscriptIR, list]:
        value, value_prelude = self._build_expr(expr.value, locals_)

        is_rtuple = False
        rtuple_index = None
        is_list_opt = False

        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._rtuple_types:
                rtuple = self._rtuple_types[var_name]
                if isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, int):
                    idx = expr.slice.value
                    if 0 <= idx < rtuple.arity:
                        is_rtuple = True
                        rtuple_index = idx
            if var_name in self._list_vars:
                is_list_opt = True
                self._uses_list_opt = True

        if isinstance(expr.slice, ast.Slice):
            slice_ir = self._build_slice(expr.slice, locals_)
            return SubscriptIR(
                ir_type=IRType.OBJ,
                value=value,
                slice_=slice_ir,
                is_rtuple=is_rtuple,
                rtuple_index=rtuple_index,
                is_list_opt=is_list_opt,
                value_prelude=value_prelude,
                slice_prelude=[],
            ), value_prelude

        slice_val, slice_prelude = self._build_expr(expr.slice, locals_)
        return SubscriptIR(
            ir_type=IRType.OBJ,
            value=value,
            slice_=slice_val,
            is_rtuple=is_rtuple,
            rtuple_index=rtuple_index,
            is_list_opt=is_list_opt,
            value_prelude=value_prelude,
            slice_prelude=slice_prelude,
        ), value_prelude + slice_prelude

    def _build_slice(self, slice_node: ast.Slice, locals_: list[str]) -> SliceIR:
        lower = None
        upper = None
        step = None
        if slice_node.lower is not None:
            lower, _ = self._build_expr(slice_node.lower, locals_)
        if slice_node.upper is not None:
            upper, _ = self._build_expr(slice_node.upper, locals_)
        if slice_node.step is not None:
            step, _ = self._build_expr(slice_node.step, locals_)
        return SliceIR(ir_type=IRType.OBJ, lower=lower, upper=upper, step=step)

    def _get_value_ir_type(self, value: ValueIR) -> IRType:
        return value.ir_type

    def _annotation_to_c_type(self, annotation: ast.expr | None) -> str:
        if annotation is None:
            return "mp_obj_t"
        if isinstance(annotation, ast.Name):
            type_map = {
                "int": "mp_int_t",
                "float": "mp_float_t",
                "bool": "bool",
                "str": "const char*",
                "None": "void",
                "list": "mp_obj_t",
                "dict": "mp_obj_t",
                "tuple": "mp_obj_t",
                "set": "mp_obj_t",
            }
            return type_map.get(annotation.id, "mp_obj_t")
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == "tuple":
                    rtuple = RTuple.from_annotation(annotation)
                    if rtuple is not None:
                        self._used_rtuples.add(rtuple)
                        return rtuple.get_c_struct_name()
                if annotation.value.id in ("list", "dict", "tuple", "set"):
                    return "mp_obj_t"
        return "mp_obj_t"

    def _annotation_to_py_type(self, annotation: ast.expr | None) -> str:
        if annotation is None:
            return "object"
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return annotation.value.id
        elif isinstance(annotation, ast.Constant):
            if annotation.value is None:
                return "None"
        return "object"

    def _c_type_to_py_type(self, c_type: str) -> str:
        type_map = {
            "mp_int_t": "int",
            "mp_float_t": "float",
            "bool": "bool",
            "const char*": "str",
            "void": "None",
            "mp_obj_t": "object",
        }
        return type_map.get(c_type, "object")

    def _is_list_annotation(self, annotation: ast.expr | None) -> bool:
        if annotation is None:
            return False
        if isinstance(annotation, ast.Name) and annotation.id == "list":
            return True
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name) and annotation.value.id == "list":
                return True
        return False

    def _try_parse_rtuple(self, annotation: ast.expr | None) -> RTuple | None:
        if isinstance(annotation, ast.Subscript):
            return RTuple.from_annotation(annotation)
        return None

    # -------------------------------------------------------------------------
    # Class Building
    # -------------------------------------------------------------------------

    def build_class(self, node: ast.ClassDef) -> ClassIR:
        """Build ClassIR from ast.ClassDef."""
        class_name = node.name
        c_class_name = f"{self.c_name}_{sanitize_name(class_name)}"

        # Check for dataclass decorator
        is_dataclass = False
        dataclass_info = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                is_dataclass = True
                dataclass_info = DataclassInfo()
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass":
                    is_dataclass = True
                    dataclass_info = DataclassInfo()
                    for kw in decorator.keywords:
                        if kw.arg == "frozen" and isinstance(kw.value, ast.Constant):
                            dataclass_info.frozen = bool(kw.value.value)
                        elif kw.arg == "eq" and isinstance(kw.value, ast.Constant):
                            dataclass_info.eq = bool(kw.value.value)
                        elif kw.arg == "repr" and isinstance(kw.value, ast.Constant):
                            dataclass_info.repr_ = bool(kw.value.value)

        # Get base class name
        base_name = None
        if node.bases:
            first_base = node.bases[0]
            if isinstance(first_base, ast.Name):
                if first_base.id not in ("object", "Object"):
                    base_name = first_base.id

        class_ir = ClassIR(
            name=class_name,
            c_name=c_class_name,
            module_name=self.module_name,
            base_name=base_name,
            is_dataclass=is_dataclass,
            dataclass_info=dataclass_info,
            ast_node=node,
        )

        # Resolve base class if known
        if base_name and base_name in self._known_classes:
            class_ir.base = self._known_classes[base_name]

        # Parse class body
        self._parse_class_body(node, class_ir)

        if is_dataclass and dataclass_info:
            dataclass_info.fields = list(class_ir.fields)

        # Register in known classes
        self._known_classes[class_name] = class_ir

        return class_ir

    def _parse_class_body(self, node: ast.ClassDef, class_ir: ClassIR) -> None:
        """Parse class body to extract fields and methods."""
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                # Class field annotation
                field_name = stmt.target.id
                py_type = self._annotation_to_py_type(stmt.annotation)
                c_type = CType.from_python_type(py_type)

                has_default = stmt.value is not None
                default_value = None
                if has_default and isinstance(stmt.value, ast.Constant):
                    default_value = stmt.value.value

                field_ir = FieldIR(
                    name=field_name,
                    py_type=py_type,
                    c_type=c_type,
                    has_default=has_default,
                    default_value=default_value,
                    default_ast=stmt.value,
                )
                class_ir.fields.append(field_ir)

            elif isinstance(stmt, ast.FunctionDef):
                self._parse_method(stmt, class_ir)

    def _parse_method(self, node: ast.FunctionDef, class_ir: ClassIR) -> None:
        """Parse a method definition and add to class IR."""
        method_name = node.name
        c_method_name = f"{class_ir.c_name}_{sanitize_name(method_name)}"

        # Parse parameters (skip 'self')
        params: list[tuple[str, CType]] = []
        for arg in node.args.args[1:]:
            py_type = self._annotation_to_py_type(arg.annotation) if arg.annotation else "object"
            c_type = CType.from_python_type(py_type)
            params.append((arg.arg, c_type))

        # Parse return type
        return_type = CType.VOID
        if node.returns:
            py_type = self._annotation_to_py_type(node.returns)
            return_type = CType.from_python_type(py_type)
            if py_type == "None":
                return_type = CType.VOID

        # Determine if virtual/special
        is_special = method_name.startswith("__") and method_name.endswith("__")
        is_virtual = not is_special or method_name in ("__len__", "__getitem__", "__setitem__")

        method_ir = MethodIR(
            name=method_name,
            c_name=c_method_name,
            params=params,
            return_type=return_type,
            body_ast=node,
            is_virtual=is_virtual,
            is_special=is_special,
            docstring=ast.get_docstring(node),
        )

        class_ir.methods[method_name] = method_ir

        if is_virtual and not is_special:
            class_ir.virtual_methods.append(method_name)

        if method_name == "__init__":
            class_ir.has_init = True
        elif method_name == "__repr__":
            class_ir.has_repr = True
        elif method_name == "__eq__":
            class_ir.has_eq = True

    def build_method_body(
        self, method_ir: MethodIR, class_ir: ClassIR, native: bool = False
    ) -> list[StmtIR]:
        """Build IR for a method body with class context.

        Args:
            method_ir: The method IR
            class_ir: The class this method belongs to
            native: Whether building for native (vtable) version vs MP wrapper
        """
        if method_ir.body_ast is None:
            return []

        # Reset state for this method
        self._var_types = {}
        self._list_vars = set()
        self._rtuple_types = {}
        self._used_rtuples = set()
        self._uses_print = False
        self._uses_list_opt = False

        # Set up parameter types
        for param_name, param_type in method_ir.params:
            self._var_types[param_name] = param_type.to_c_type_str()

        # Track self and params as locals
        local_vars = ["self"] + [p[0] for p in method_ir.params]

        body_ir: list[StmtIR] = []
        for stmt in method_ir.body_ast.body:
            # Skip docstrings
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                continue
            stmt_ir = self._build_method_statement(stmt, local_vars, class_ir, native)
            if stmt_ir is not None:
                body_ir.append(stmt_ir)

        return body_ir

    def _build_method_statement(
        self, stmt: ast.stmt, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> StmtIR | None:
        """Build statement IR in method context."""
        if isinstance(stmt, ast.Return):
            return self._build_method_return(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.Assign):
            return self._build_method_assign(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.AnnAssign):
            return self._build_method_ann_assign(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.AugAssign):
            return self._build_method_aug_assign(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.If):
            return self._build_method_if(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.While):
            return self._build_method_while(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.For):
            return self._build_method_for(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.Expr):
            value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)
            return ExprStmtIR(expr=value, prelude=prelude)
        elif isinstance(stmt, ast.Break):
            return BreakIR()
        elif isinstance(stmt, ast.Continue):
            return ContinueIR()
        elif isinstance(stmt, ast.Pass):
            return PassIR()
        return None

    def _build_method_return(
        self, stmt: ast.Return, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> ReturnIR:
        """Build return statement in method context."""
        if stmt.value is None:
            return ReturnIR(value=None, prelude=[])
        value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)
        return ReturnIR(value=value, prelude=prelude)

    def _build_method_assign(
        self, stmt: ast.Assign, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> StmtIR | None:
        """Build assignment in method context, handling self.attr = value."""
        if len(stmt.targets) != 1:
            return None

        target = stmt.targets[0]

        # Handle self.attr = value
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            attr_name = target.attr
            value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)

            # Find field path
            attr_path = attr_name
            for fld, path in class_ir.get_all_fields_with_path():
                if fld.name == attr_name:
                    attr_path = path
                    break

            return AttrAssignIR(
                attr_name=attr_name,
                attr_path=attr_path,
                value=value,
                prelude=prelude,
            )

        # Handle regular assignment
        if isinstance(target, ast.Name):
            var_name = target.id
            c_var_name = sanitize_name(var_name)
            value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)
            is_new = var_name not in locals_
            if is_new:
                locals_.append(var_name)
                self._var_types[var_name] = value.ir_type.to_c_type_str()

            return AssignIR(
                target=var_name,
                c_target=c_var_name,
                value=value,
                value_type=value.ir_type,
                prelude=prelude,
                is_new_var=is_new,
                c_type=value.ir_type.to_c_type_str(),
            )

        # Handle subscript assignment
        if isinstance(target, ast.Subscript):
            container, cont_prelude = self._build_method_expr(
                target.value, locals_, class_ir, native
            )
            key, key_prelude = self._build_method_expr(target.slice, locals_, class_ir, native)
            value, val_prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)
            return SubscriptAssignIR(
                container=container,
                key=key,
                value=value,
                prelude=cont_prelude + key_prelude + val_prelude,
            )

        return None

    def _build_method_ann_assign(
        self, stmt: ast.AnnAssign, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> AnnAssignIR | None:
        """Build annotated assignment in method context."""
        if not isinstance(stmt.target, ast.Name):
            return None

        var_name = stmt.target.id
        c_var_name = sanitize_name(var_name)
        c_type = self._annotation_to_c_type(stmt.annotation) if stmt.annotation else "mp_int_t"

        value = None
        prelude: list = []
        if stmt.value is not None:
            value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)

        is_new = var_name not in locals_
        if is_new:
            locals_.append(var_name)
            self._var_types[var_name] = c_type

        return AnnAssignIR(
            target=var_name,
            c_target=c_var_name,
            c_type=c_type,
            value=value,
            prelude=prelude,
            is_new_var=is_new,
        )

    def _build_method_aug_assign(
        self, stmt: ast.AugAssign, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> AugAssignIR | SelfAugAssignIR | None:
        """Build augmented assignment in method context."""
        op_map = {
            ast.Add: "+=",
            ast.Sub: "-=",
            ast.Mult: "*=",
            ast.Div: "/=",
            ast.Mod: "%=",
            ast.BitAnd: "&=",
            ast.BitOr: "|=",
            ast.BitXor: "^=",
            ast.LShift: "<<=",
            ast.RShift: ">>=",
        }
        c_op = op_map.get(type(stmt.op), "+=")

        if isinstance(stmt.target, ast.Attribute):
            if isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == "self":
                attr_name = stmt.target.attr
                value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)
                return SelfAugAssignIR(
                    attr_name=attr_name,
                    attr_path=attr_name,
                    op=c_op,
                    value=value,
                    prelude=prelude,
                )
            return None

        if not isinstance(stmt.target, ast.Name):
            return None

        var_name = stmt.target.id
        c_var_name = sanitize_name(var_name)
        value, prelude = self._build_method_expr(stmt.value, locals_, class_ir, native)

        return AugAssignIR(
            target=var_name,
            c_target=c_var_name,
            op=c_op,
            value=value,
            prelude=prelude,
        )

    def _build_method_if(
        self, stmt: ast.If, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> IfIR:
        """Build if statement in method context."""
        test, test_prelude = self._build_method_expr(stmt.test, locals_, class_ir, native)
        body = [self._build_method_statement(s, locals_, class_ir, native) for s in stmt.body]
        body = [s for s in body if s is not None]
        orelse = [self._build_method_statement(s, locals_, class_ir, native) for s in stmt.orelse]
        orelse = [s for s in orelse if s is not None]
        return IfIR(test=test, body=body, orelse=orelse, test_prelude=test_prelude)

    def _build_method_while(
        self, stmt: ast.While, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> WhileIR:
        """Build while statement in method context."""
        test, test_prelude = self._build_method_expr(stmt.test, locals_, class_ir, native)
        self._loop_depth += 1
        body = [self._build_method_statement(s, locals_, class_ir, native) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1
        return WhileIR(test=test, body=body, test_prelude=test_prelude)

    def _build_method_for(
        self, stmt: ast.For, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> ForRangeIR | ForIterIR:
        """Build for statement in method context."""
        if not isinstance(stmt.target, ast.Name):
            raise ValueError("Unsupported for loop target")

        loop_var = stmt.target.id
        c_loop_var = sanitize_name(loop_var)
        is_new_var = loop_var not in locals_
        if is_new_var:
            locals_.append(loop_var)
            self._var_types[loop_var] = "mp_int_t"

        if (
            isinstance(stmt.iter, ast.Call)
            and isinstance(stmt.iter.func, ast.Name)
            and stmt.iter.func.id == "range"
        ):
            return self._build_method_for_range(
                stmt, loop_var, c_loop_var, is_new_var, locals_, class_ir, native
            )
        else:
            return self._build_method_for_iter(
                stmt, loop_var, c_loop_var, is_new_var, locals_, class_ir, native
            )

    def _build_method_for_range(
        self,
        stmt: ast.For,
        loop_var: str,
        c_loop_var: str,
        is_new_var: bool,
        locals_: list[str],
        class_ir: ClassIR,
        native: bool,
    ) -> ForRangeIR:
        """Build optimized for-range in method context."""
        assert isinstance(stmt.iter, ast.Call)
        args = stmt.iter.args

        step_is_constant = False
        step_value: int | None = None
        step: ValueIR | None = None

        if len(args) == 1:
            start = ConstIR(ir_type=IRType.INT, value=0)
            end, _ = self._build_method_expr(args[0], locals_, class_ir, native)
            step_is_constant = True
            step_value = 1
        elif len(args) == 2:
            start, _ = self._build_method_expr(args[0], locals_, class_ir, native)
            end, _ = self._build_method_expr(args[1], locals_, class_ir, native)
            step_is_constant = True
            step_value = 1
        elif len(args) == 3:
            start, _ = self._build_method_expr(args[0], locals_, class_ir, native)
            end, _ = self._build_method_expr(args[1], locals_, class_ir, native)
            if isinstance(args[2], ast.Constant) and isinstance(args[2].value, int):
                step_is_constant = True
                step_value = args[2].value
            elif isinstance(args[2], ast.UnaryOp) and isinstance(args[2].op, ast.USub):
                if isinstance(args[2].operand, ast.Constant) and isinstance(
                    args[2].operand.value, int
                ):
                    step_is_constant = True
                    step_value = -args[2].operand.value
                else:
                    step, _ = self._build_method_expr(args[2], locals_, class_ir, native)
            else:
                step, _ = self._build_method_expr(args[2], locals_, class_ir, native)
        else:
            raise ValueError("Unsupported range() call")

        self._loop_depth += 1
        body = [self._build_method_statement(s, locals_, class_ir, native) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1

        return ForRangeIR(
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            start=start,
            end=end,
            step=step,
            step_is_constant=step_is_constant,
            step_value=step_value,
            body=body,
            is_new_var=is_new_var,
        )

    def _build_method_for_iter(
        self,
        stmt: ast.For,
        loop_var: str,
        c_loop_var: str,
        is_new_var: bool,
        locals_: list[str],
        class_ir: ClassIR,
        native: bool,
    ) -> ForIterIR:
        """Build generic for-iter in method context."""
        iterable, iter_prelude = self._build_method_expr(stmt.iter, locals_, class_ir, native)

        self._loop_depth += 1
        body = [self._build_method_statement(s, locals_, class_ir, native) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1

        return ForIterIR(
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            iterable=iterable,
            body=body,
            iter_prelude=iter_prelude,
            is_new_var=is_new_var,
        )

    def _build_method_expr(
        self, expr: ast.expr, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> tuple[ValueIR, list]:
        """Build expression in method context, handling self.attr and self.method()."""
        # Handle self.attr
        if isinstance(expr, ast.Attribute):
            if isinstance(expr.value, ast.Name) and expr.value.id == "self":
                attr_name = expr.attr
                for fld, path in class_ir.get_all_fields_with_path():
                    if fld.name == attr_name:
                        result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                        return SelfAttrIR(
                            ir_type=result_type,
                            attr_name=attr_name,
                            attr_path=path,
                            result_type=result_type,
                        ), []
                return SelfAttrIR(
                    ir_type=IRType.OBJ,
                    attr_name=attr_name,
                    attr_path=attr_name,
                    result_type=IRType.OBJ,
                ), []

        # Handle self.method()
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
            if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "self":
                method_name = expr.func.attr
                method_ir = class_ir.methods.get(method_name)
                c_method_name = f"{class_ir.c_name}_{sanitize_name(method_name)}"

                args: list[ValueIR] = []
                arg_preludes: list[list] = []
                for arg in expr.args:
                    val, prelude = self._build_method_expr(arg, locals_, class_ir, native)
                    args.append(val)
                    arg_preludes.append(prelude)

                return_type = IRType.OBJ
                if method_ir:
                    return_type = IRType.from_c_type_str(method_ir.return_type.to_c_type_str())

                all_preludes = [p for pl in arg_preludes for p in pl]
                return SelfMethodCallIR(
                    ir_type=return_type,
                    method_name=method_name,
                    c_method_name=c_method_name,
                    args=args,
                    return_type=return_type,
                    arg_preludes=arg_preludes,
                ), all_preludes

        # Handle BinOp with recursive method context
        if isinstance(expr, ast.BinOp):
            left, left_prelude = self._build_method_expr(expr.left, locals_, class_ir, native)
            right, right_prelude = self._build_method_expr(expr.right, locals_, class_ir, native)

            op_map = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.Div: "/",
                ast.FloorDiv: "/",
                ast.Mod: "%",
                ast.BitAnd: "&",
                ast.BitOr: "|",
                ast.BitXor: "^",
                ast.LShift: "<<",
                ast.RShift: ">>",
            }
            c_op = op_map.get(type(expr.op), "+")
            result_type = (
                IRType.FLOAT
                if (left.ir_type == IRType.FLOAT or right.ir_type == IRType.FLOAT)
                else IRType.INT
            )
            return BinOpIR(
                ir_type=result_type,
                left=left,
                op=c_op,
                right=right,
                left_prelude=left_prelude,
                right_prelude=right_prelude,
            ), left_prelude + right_prelude

        # Handle UnaryOp with recursive method context
        if isinstance(expr, ast.UnaryOp):
            operand, prelude = self._build_method_expr(expr.operand, locals_, class_ir, native)
            op_map = {ast.USub: "-", ast.Not: "!", ast.UAdd: "+", ast.Invert: "~"}
            c_op = op_map.get(type(expr.op), "-")
            result_type = IRType.BOOL if c_op == "!" else operand.ir_type
            return UnaryOpIR(
                ir_type=result_type,
                op=c_op,
                operand=operand,
                prelude=prelude,
            ), prelude

        # Handle Compare with recursive method context
        if isinstance(expr, ast.Compare):
            left, left_prelude = self._build_method_expr(expr.left, locals_, class_ir, native)
            op_map = {
                ast.Eq: "==",
                ast.NotEq: "!=",
                ast.Lt: "<",
                ast.LtE: "<=",
                ast.Gt: ">",
                ast.GtE: ">=",
                ast.In: "in",
                ast.NotIn: "not in",
            }
            ops: list[str] = []
            comparators: list[ValueIR] = []
            comparator_preludes: list[list] = []
            has_contains = False

            for op, comparator in zip(expr.ops, expr.comparators):
                c_op = op_map.get(type(op), "==")
                if c_op in ("in", "not in"):
                    has_contains = True
                ops.append(c_op)
                comp_val, comp_prelude = self._build_method_expr(
                    comparator, locals_, class_ir, native
                )
                comparators.append(comp_val)
                comparator_preludes.append(comp_prelude)

            all_preludes = left_prelude + [p for pl in comparator_preludes for p in pl]
            return CompareIR(
                ir_type=IRType.BOOL,
                left=left,
                ops=ops,
                comparators=comparators,
                has_contains=has_contains,
                left_prelude=left_prelude,
                comparator_preludes=comparator_preludes,
            ), all_preludes

        # Handle IfExp with recursive method context
        if isinstance(expr, ast.IfExp):
            test, test_prelude = self._build_method_expr(expr.test, locals_, class_ir, native)
            body, body_prelude = self._build_method_expr(expr.body, locals_, class_ir, native)
            orelse, orelse_prelude = self._build_method_expr(expr.orelse, locals_, class_ir, native)
            return IfExprIR(
                ir_type=body.ir_type,
                test=test,
                body=body,
                orelse=orelse,
                test_prelude=test_prelude,
                body_prelude=body_prelude,
                orelse_prelude=orelse_prelude,
            ), test_prelude + body_prelude + orelse_prelude

        # Handle Subscript (e.g., self.items[i])
        if isinstance(expr, ast.Subscript):
            value, value_prelude = self._build_method_expr(expr.value, locals_, class_ir, native)
            if isinstance(expr.slice, ast.Slice):
                slice_ir = self._build_slice(expr.slice, locals_)
                return SubscriptIR(
                    ir_type=IRType.OBJ,
                    value=value,
                    slice_=slice_ir,
                    value_prelude=value_prelude,
                    slice_prelude=[],
                ), value_prelude
            slice_val, slice_prelude = self._build_method_expr(
                expr.slice, locals_, class_ir, native
            )
            return SubscriptIR(
                ir_type=IRType.OBJ,
                value=value,
                slice_=slice_val,
                value_prelude=value_prelude,
                slice_prelude=slice_prelude,
            ), value_prelude + slice_prelude

        # Handle Call (non-self)
        if isinstance(expr, ast.Call):
            return self._build_method_call_general(expr, locals_, class_ir, native)

        # Fall back to regular expression building for simple expressions
        return self._build_expr(expr, locals_)

    def _build_method_call_general(
        self, expr: ast.Call, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> tuple[ValueIR, list]:
        """Build a general call expression in method context."""
        if isinstance(expr.func, ast.Attribute):
            receiver, recv_prelude = self._build_method_expr(
                expr.func.value, locals_, class_ir, native
            )
            method_name = expr.func.attr

            args: list[ValueIR] = []
            for arg in expr.args:
                val, _ = self._build_method_expr(arg, locals_, class_ir, native)
                args.append(val)

            temp_name = self._fresh_temp()
            result = TempIR(ir_type=IRType.OBJ, name=temp_name)
            method_call = MethodCallIR(
                result=result, receiver=receiver, method=method_name, args=args
            )
            return result, recv_prelude + [method_call]

        if not isinstance(expr.func, ast.Name):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        func_name = expr.func.id

        if func_name in self._known_classes:
            return self._build_class_instantiation(expr, func_name, locals_)

        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_method_expr(arg, locals_, class_ir, native)
            args.append(val)
            arg_preludes.append(prelude)

        all_preludes = [p for pl in arg_preludes for p in pl]

        builtins = {"abs", "int", "float", "len", "range", "list", "tuple", "set", "dict"}
        if func_name in builtins:
            return CallIR(
                ir_type=IRType.INT
                if func_name in ("abs", "int", "len")
                else (IRType.FLOAT if func_name == "float" else IRType.OBJ),
                func_name=func_name,
                c_func_name=func_name,
                args=args,
                arg_preludes=arg_preludes,
                is_builtin=True,
                builtin_kind=func_name,
            ), all_preludes

        c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"
        return CallIR(
            ir_type=IRType.INT,
            func_name=func_name,
            c_func_name=c_func_name,
            args=args,
            arg_preludes=arg_preludes,
            is_builtin=False,
            builtin_kind=None,
        ), all_preludes
