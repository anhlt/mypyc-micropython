"""
IR Builder: AST -> IR translation.

This module transforms Python AST nodes into IR data structures.
The IR is then consumed by emitters to generate C code.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .type_checker import ClassTypeInfo, FunctionTypeInfo

from .ir import (
    AnnAssignIR,
    ArgKind,
    AssignIR,
    AttrAccessIR,
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
    DefaultArg,
    DictNewIR,
    ExceptHandlerIR,
    ExprStmtIR,
    FieldIR,
    ForIterIR,
    ForRangeIR,
    FuncIR,
    IfExprIR,
    IfIR,
    IRType,
    ListCompIR,
    ListNewIR,
    MethodCallIR,
    MethodIR,
    ModuleAttrIR,
    ModuleCallIR,
    NameIR,
    ParamAttrIR,
    ParamIR,
    PassIR,
    PrintIR,
    PropertyInfo,
    RaiseIR,
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
    SuperCallIR,
    TempIR,
    TryIR,
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


@dataclass
class MypyTypeInfo:
    """Container for mypy type information passed to IRBuilder."""

    functions: dict[str, "FunctionTypeInfo"] = field(default_factory=dict)
    classes: dict[str, "ClassTypeInfo"] = field(default_factory=dict)
    module_types: dict[str, str] = field(default_factory=dict)


class IRBuilder:
    """Builds IR from Python AST nodes.

    Optionally uses mypy's type information when available for more accurate
    type resolution, including type inference and generic resolution.
    """

    def __init__(
        self,
        module_name: str,
        known_classes: dict[str, ClassIR] | None = None,
        mypy_types: "MypyTypeInfo | None" = None,
    ):
        self.module_name = module_name
        self.c_name = sanitize_name(module_name)
        self._known_classes = known_classes or {}
        self._mypy_types = mypy_types
        self._temp_counter = 0
        self._var_types: dict[str, str] = {}
        self._star_c_names: dict[str, str] = {}
        self._list_vars: dict[str, str | None] = {}
        self._rtuple_types: dict[str, RTuple] = {}
        self._used_rtuples: set[RTuple] = set()
        self._uses_print = False
        self._uses_list_opt = False
        self._uses_imports = False
        self._loop_depth = 0
        self._class_typed_params: dict[str, str] = {}
        self._mypy_local_types: dict[str, str] = {}
        # Import tracking: alias -> module_name (e.g., 'm' -> 'math')
        self._import_aliases: dict[str, str] = {}
        self._imported_modules: set[str] = set()

    def _fresh_temp(self) -> str:
        self._temp_counter += 1
        return f"_tmp{self._temp_counter}"

    def register_import(self, node: ast.Import | ast.ImportFrom) -> None:
        """Register import statements for later resolution of module.func() calls."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                local_name = alias.asname or alias.name
                self._import_aliases[local_name] = module_name
                self._imported_modules.add(module_name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # from X import Y -- track the module
            self._import_aliases[node.module] = node.module
            self._imported_modules.add(node.module)

    @property
    def imported_modules(self) -> set[str]:
        """Set of module names that have been imported."""
        return self._imported_modules

    def build_function(self, node: ast.FunctionDef) -> FuncIR:
        self._temp_counter = 0
        self._var_types = {}
        self._star_c_names: dict[str, str] = {}
        self._list_vars: dict[str, str | None] = {}
        self._rtuple_types = {}
        self._used_rtuples = set()
        self._uses_print = False
        self._uses_list_opt = False
        self._uses_imports = False
        self._class_typed_params = {}
        self._mypy_local_types = {}

        func_name = node.name
        c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"

        mypy_func = self._get_mypy_func_type(func_name)
        mypy_param_types: dict[str, str] = {}
        mypy_return_type: str | None = None
        if mypy_func:
            mypy_param_types = {name: ptype for name, ptype in mypy_func.params}
            mypy_return_type = mypy_func.return_type
            self._mypy_local_types = dict(mypy_func.local_types)

        params: list[tuple[str, CType]] = []
        arg_types: list[str] = []
        for arg in node.args.args:
            if arg.arg in mypy_param_types:
                py_type = self._mypy_type_to_py_type(mypy_param_types[arg.arg])
                c_type_str = self._mypy_type_to_c_type(mypy_param_types[arg.arg])
                c_type = CType.from_python_type(py_type)
            else:
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
            if arg.annotation:
                is_list, elem_type = self._is_list_annotation(arg.annotation)
                if is_list:
                    self._list_vars[arg.arg] = elem_type
                if isinstance(arg.annotation, ast.Name):
                    type_name = arg.annotation.id
                    if type_name in self._known_classes:
                        self._class_typed_params[arg.arg] = type_name

        defaults = self._parse_defaults(node.args, len(params))

        star_args, star_kwargs = self._parse_star_args(node.args)

        if mypy_return_type:
            py_type = self._mypy_type_to_py_type(mypy_return_type)
            return_type = CType.from_python_type(py_type)
        else:
            return_type = (
                CType.from_python_type(self._annotation_to_py_type(node.returns))
                if node.returns
                else CType.MP_OBJ_T
            )

        local_vars = [arg.arg for arg in node.args.args]
        if star_args:
            local_vars.append(star_args.name)
            self._var_types[star_args.name] = "mp_obj_t"
            self._star_c_names[star_args.name] = f"_star_{sanitize_name(star_args.name)}"
        if star_kwargs:
            local_vars.append(star_kwargs.name)
            self._var_types[star_kwargs.name] = "mp_obj_t"
            self._star_c_names[star_kwargs.name] = f"_star_{sanitize_name(star_kwargs.name)}"

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
            uses_imports=self._uses_imports,
            used_rtuples=set(self._used_rtuples),
            rtuple_types=dict(self._rtuple_types),
            list_vars=dict(self._list_vars),
            max_temp=self._temp_counter,
            defaults=defaults,
            star_args=star_args,
            star_kwargs=star_kwargs,
        )

    def _build_statement(self, stmt: ast.stmt, locals_: list[str]) -> StmtIR | None:
        if isinstance(stmt, ast.FunctionDef):
            raise NotImplementedError(
                f"Nested functions are not supported (line {stmt.lineno}): "
                f"def {stmt.name}(...). "
                "Consider refactoring to a module-level function."
            )
        if isinstance(stmt, ast.Return):
            return self._build_return(stmt, locals_)
        elif isinstance(stmt, ast.If):
            return self._build_if(stmt, locals_)
        elif isinstance(stmt, ast.While):
            return self._build_while(stmt, locals_)
        elif isinstance(stmt, ast.For):
            return self._build_for(stmt, locals_)
        elif isinstance(stmt, ast.Try):
            return self._build_try(stmt, locals_)
        elif isinstance(stmt, ast.Raise):
            return self._build_raise(stmt, locals_)
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

    def _build_try(self, stmt: ast.Try, locals_: list[str]) -> TryIR:
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]

        handlers: list[ExceptHandlerIR] = []
        for handler in stmt.handlers:
            exc_type: str | None = None
            if handler.type is not None:
                if isinstance(handler.type, ast.Name):
                    exc_type = handler.type.id
                elif isinstance(handler.type, ast.Attribute):
                    exc_type = handler.type.attr

            exc_var = handler.name
            c_exc_var = sanitize_name(exc_var) if exc_var else None

            if exc_var and exc_var not in locals_:
                locals_.append(exc_var)
                self._var_types[exc_var] = "mp_obj_t"

            handler_body = [self._build_statement(s, locals_) for s in handler.body]
            handler_body = [s for s in handler_body if s is not None]

            handlers.append(
                ExceptHandlerIR(
                    exc_type=exc_type,
                    exc_var=exc_var,
                    c_exc_var=c_exc_var,
                    body=handler_body,
                )
            )

        orelse = [self._build_statement(s, locals_) for s in stmt.orelse]
        orelse = [s for s in orelse if s is not None]

        finalbody = [self._build_statement(s, locals_) for s in stmt.finalbody]
        finalbody = [s for s in finalbody if s is not None]

        return TryIR(body=body, handlers=handlers, orelse=orelse, finalbody=finalbody)

    def _build_raise(self, stmt: ast.Raise, locals_: list[str]) -> RaiseIR:
        if stmt.exc is None:
            return RaiseIR(is_reraise=True)

        exc_type: str | None = None
        exc_msg: ValueIR | None = None
        prelude: list = []

        if isinstance(stmt.exc, ast.Call):
            if isinstance(stmt.exc.func, ast.Name):
                exc_type = stmt.exc.func.id
            elif isinstance(stmt.exc.func, ast.Attribute):
                exc_type = stmt.exc.func.attr

            if stmt.exc.args:
                exc_msg, prelude = self._build_expr(stmt.exc.args[0], locals_)
        elif isinstance(stmt.exc, ast.Name):
            exc_type = stmt.exc.id

        return RaiseIR(exc_type=exc_type, exc_msg=exc_msg, prelude=prelude)

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
            if var_name in self._mypy_local_types:
                c_type = self._mypy_type_to_c_type(self._mypy_local_types[var_name])
            else:
                value_type = self._get_value_ir_type(value)
                c_type = value_type.to_c_type_str()
            self._var_types[var_name] = c_type
        else:
            c_type = self._var_types.get(var_name, "mp_obj_t")

        value_type = IRType.from_c_type_str(c_type)

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

        is_list, elem_type = self._is_list_annotation(stmt.annotation)
        if is_list:
            self._list_vars[var_name] = elem_type

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

        target_c_type = self._var_types.get(var_name, "mp_int_t")

        return AugAssignIR(
            target=var_name,
            c_target=c_var_name,
            op=c_op,
            value=value,
            target_c_type=target_c_type,
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
        elif isinstance(expr, ast.BoolOp):
            return self._build_boolop(expr, locals_)
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
        elif isinstance(expr, ast.Attribute):
            return self._build_attribute(expr, locals_)
        elif isinstance(expr, ast.ListComp):
            return self._build_list_comp(expr, locals_)
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

        c_name = self._star_c_names.get(name, sanitize_name(name))
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
            ast.FloorDiv: "//",  # Keep as // to distinguish from true division
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

    def _build_boolop(self, expr: ast.BoolOp, locals_: list[str]) -> tuple[BinOpIR, list]:
        c_op = "&&" if isinstance(expr.op, ast.And) else "||"

        values = expr.values
        left, left_prelude = self._build_expr(values[0], locals_)
        all_prelude = left_prelude[:]

        for i in range(1, len(values)):
            right, right_prelude = self._build_expr(values[i], locals_)
            all_prelude.extend(right_prelude)

            left = BinOpIR(
                ir_type=IRType.BOOL,
                left=left,
                op=c_op,
                right=right,
                left_prelude=[],
                right_prelude=right_prelude,
            )

        return left, all_prelude

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

        builtins = {
            "abs",
            "int",
            "float",
            "bool",
            "str",
            "len",
            "range",
            "list",
            "tuple",
            "set",
            "dict",
            "min",
            "max",
            "sum",
            "enumerate",
            "zip",
            "sorted",
        }
        if func_name in builtins:
            is_list_len_opt = False
            is_typed_list_sum = False
            sum_list_var: str | None = None
            sum_element_type: str | None = None

            if func_name == "len" and len(args) == 1:
                arg = args[0]
                if isinstance(arg, NameIR) and arg.py_name in self._list_vars:
                    is_list_len_opt = True
                    self._uses_list_opt = True

            if func_name == "sum" and len(args) >= 1:
                arg = args[0]
                if isinstance(arg, NameIR) and arg.py_name in self._list_vars:
                    elem_type = self._list_vars.get(arg.py_name)
                    if elem_type in ("int", "float"):
                        is_typed_list_sum = True
                        sum_list_var = arg.py_name
                        sum_element_type = elem_type
                        self._uses_list_opt = True

            if func_name in ("abs", "int", "len", "sum"):
                ir_type = IRType.INT
            elif func_name == "float":
                ir_type = IRType.FLOAT
            elif func_name == "bool":
                ir_type = IRType.BOOL
            else:
                ir_type = IRType.OBJ
            return CallIR(
                ir_type=ir_type,
                func_name=func_name,
                c_func_name=func_name,
                args=args,
                arg_preludes=arg_preludes,
                is_builtin=True,
                builtin_kind=func_name,
                is_list_len_opt=is_list_len_opt,
                is_typed_list_sum=is_typed_list_sum,
                sum_list_var=sum_list_var,
                sum_element_type=sum_element_type,
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

    @staticmethod
    def _is_private_name(name: str) -> bool:
        """Check if name is a private identifier (__name without trailing __)."""
        return name.startswith("__") and not name.endswith("__")

    def _build_method_call(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
        if not isinstance(expr.func, ast.Attribute):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        # Check if this is a call on an imported module: math.sqrt(x)
        if isinstance(expr.func.value, ast.Name):
            var_name = expr.func.value.id
            if var_name in self._import_aliases:
                return self._build_module_call(expr, var_name, locals_)

        receiver, recv_prelude = self._build_expr(expr.func.value, locals_)
        method_name = expr.func.attr

        # Reject external access to private (__method) members
        if self._is_private_name(method_name):
            raise TypeError(
                f"Cannot access private method '{method_name}' from outside its class"
            )

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

    def _build_module_call(
        self, expr: ast.Call, alias: str, locals_: list[str]
    ) -> tuple[ValueIR, list]:
        """Build IR for a call on an imported module: module.func(args)."""
        if not isinstance(expr.func, ast.Attribute):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        module_name = self._import_aliases[alias]
        func_name = expr.func.attr
        self._uses_imports = True

        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            args.append(val)
            arg_preludes.append(prelude)
        all_preludes = [p for pl in arg_preludes for p in pl]

        return ModuleCallIR(
            ir_type=IRType.OBJ,
            module_name=module_name,
            func_name=func_name,
            args=args,
            arg_preludes=arg_preludes,
        ), all_preludes

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
        result_ir_type = IRType.OBJ

        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._rtuple_types:
                rtuple = self._rtuple_types[var_name]
                if isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, int):
                    idx = expr.slice.value
                    if 0 <= idx < rtuple.arity:
                        is_rtuple = True
                        rtuple_index = idx
                        result_ir_type = IRType.from_c_type_str(
                            rtuple.element_types[idx].to_c_type_str()
                        )
            if var_name in self._list_vars:
                is_list_opt = True
                self._uses_list_opt = True

        if isinstance(expr.slice, ast.Slice):
            slice_ir = self._build_slice(expr.slice, locals_)
            return SubscriptIR(
                ir_type=result_ir_type,
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
            ir_type=result_ir_type,
            value=value,
            slice_=slice_val,
            is_rtuple=is_rtuple,
            rtuple_index=rtuple_index,
            is_list_opt=is_list_opt,
            value_prelude=value_prelude,
            slice_prelude=slice_prelude,
        ), value_prelude + slice_prelude

    def _build_attribute(self, expr: ast.Attribute, locals_: list[str]) -> tuple[ValueIR, list]:
        # Check if this is an attribute on an imported module: math.pi
        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._import_aliases:
                module_name = self._import_aliases[var_name]
                self._uses_imports = True
                return ModuleAttrIR(
                    ir_type=IRType.OBJ,
                    module_name=module_name,
                    attr_name=expr.attr,
                ), []

        attr_name = expr.attr

        # Reject external access to private (__attr) members
        if self._is_private_name(attr_name):
            raise TypeError(
                f"Cannot access private attribute '{attr_name}' from outside its class"
            )
        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._class_typed_params:
                class_name = self._class_typed_params[var_name]
                class_ir = self._known_classes[class_name]

                for fld, path in class_ir.get_all_fields_with_path():
                    if fld.name == attr_name:
                        result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                        return ParamAttrIR(
                            ir_type=result_type,
                            param_name=var_name,
                            c_param_name=sanitize_name(var_name),
                            attr_name=attr_name,
                            attr_path=path,
                            class_c_name=class_ir.c_name,
                            result_type=result_type,
                        ), []

                return ParamAttrIR(
                    ir_type=IRType.OBJ,
                    param_name=var_name,
                    c_param_name=sanitize_name(var_name),
                    attr_name=attr_name,
                    attr_path=attr_name,
                    class_c_name=class_ir.c_name,
                    result_type=IRType.OBJ,
                ), []

        if isinstance(expr.value, ast.Attribute):
            base_value, base_prelude = self._build_attribute(expr.value, locals_)
            base_class_name = self._get_class_type_of_attr(expr.value)

            if base_class_name and base_class_name in self._known_classes:
                base_class_ir = self._known_classes[base_class_name]

                for fld in base_class_ir.get_all_fields():
                    if fld.name == attr_name:
                        result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                        temp_name = self._fresh_temp()
                        result_temp = TempIR(ir_type=result_type, name=temp_name)

                        attr_access = AttrAccessIR(
                            result=result_temp,
                            obj=base_value,
                            attr_name=attr_name,
                            class_c_name=base_class_ir.c_name,
                            result_type=result_type,
                        )

                        return result_temp, base_prelude + [attr_access]

        return ConstIR(ir_type=IRType.OBJ, value=None), []

    def _build_list_comp(self, expr: ast.ListComp, locals_: list[str]) -> tuple[ValueIR, list]:
        """Build IR for list comprehension: [expr for var in iterable] or [expr for var in iterable if cond]."""
        if not expr.generators:
            return ConstIR(ir_type=IRType.OBJ, value=[]), []

        # We only support single generator for now
        gen = expr.generators[0]

        if not isinstance(gen.target, ast.Name):
            # Only support simple variable targets
            return ConstIR(ir_type=IRType.OBJ, value=[]), []

        loop_var = gen.target.id
        c_loop_var = sanitize_name(loop_var)

        # Track the loop variable
        is_new_var = loop_var not in locals_
        if is_new_var:
            locals_.append(loop_var)
            self._var_types[loop_var] = "mp_obj_t"

        # Build iterable expression
        iterable, iter_prelude = self._build_expr(gen.iter, locals_)

        # Check if iterable is range() for optimization
        is_range = False
        range_start: ValueIR | None = None
        range_end: ValueIR | None = None
        range_step: ValueIR | None = None

        if (
            isinstance(gen.iter, ast.Call)
            and isinstance(gen.iter.func, ast.Name)
            and gen.iter.func.id == "range"
        ):
            is_range = True
            range_args = gen.iter.args
            if len(range_args) == 1:
                range_start = ConstIR(ir_type=IRType.INT, value=0)
                range_end, _ = self._build_expr(range_args[0], locals_)
            elif len(range_args) == 2:
                range_start, _ = self._build_expr(range_args[0], locals_)
                range_end, _ = self._build_expr(range_args[1], locals_)
            elif len(range_args) == 3:
                range_start, _ = self._build_expr(range_args[0], locals_)
                range_end, _ = self._build_expr(range_args[1], locals_)
                range_step, _ = self._build_expr(range_args[2], locals_)
            # For range-based comprehensions, loop var is int
            self._var_types[loop_var] = "mp_int_t"

        # Build element expression
        element, element_prelude = self._build_expr(expr.elt, locals_)

        # Build condition if present
        condition: ValueIR | None = None
        condition_prelude: list = []
        if gen.ifs:
            # Combine multiple conditions with AND
            cond_parts = []
            for if_expr in gen.ifs:
                cond, cond_pre = self._build_expr(if_expr, locals_)
                cond_parts.append(cond)
                condition_prelude.extend(cond_pre)
            # For now, just use the first condition (most common case)
            condition = cond_parts[0] if len(cond_parts) == 1 else cond_parts[0]

        # Create result temp
        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)

        # Create ListCompIR instruction
        list_comp = ListCompIR(
            result=result,
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            iterable=iterable,
            element=element,
            condition=condition,
            iter_prelude=iter_prelude,
            element_prelude=element_prelude,
            condition_prelude=condition_prelude,
            is_range=is_range,
            range_start=range_start,
            range_end=range_end,
            range_step=range_step,
        )

        return result, [list_comp]

    def _get_class_type_of_attr(self, expr: ast.Attribute) -> str | None:
        """Get the class type name that an attribute access returns."""
        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._class_typed_params:
                class_name = self._class_typed_params[var_name]
                if class_name in self._known_classes:
                    class_ir = self._known_classes[class_name]
                    for fld in class_ir.get_all_fields():
                        if fld.name == expr.attr:
                            return fld.py_type
        elif isinstance(expr.value, ast.Attribute):
            parent_class = self._get_class_type_of_attr(expr.value)
            if parent_class and parent_class in self._known_classes:
                class_ir = self._known_classes[parent_class]
                for fld in class_ir.get_all_fields():
                    if fld.name == expr.attr:
                        return fld.py_type
        return None

    def _get_method_attr_class_type(self, expr: ast.Attribute, class_ir: ClassIR) -> str | None:
        """Get the class type name of an attribute in method context (handles self.attr)."""
        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name == "self":
                for fld in class_ir.get_all_fields():
                    if fld.name == expr.attr:
                        return fld.py_type
            elif var_name in self._class_typed_params:
                param_class_name = self._class_typed_params[var_name]
                if param_class_name in self._known_classes:
                    param_class_ir = self._known_classes[param_class_name]
                    for fld in param_class_ir.get_all_fields():
                        if fld.name == expr.attr:
                            return fld.py_type
        elif isinstance(expr.value, ast.Attribute):
            parent_type = self._get_method_attr_class_type(expr.value, class_ir)
            if parent_type and parent_type in self._known_classes:
                parent_ir = self._known_classes[parent_type]
                for fld in parent_ir.get_all_fields():
                    if fld.name == expr.attr:
                        return fld.py_type
        return None

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

    def _get_mypy_func_type(self, func_name: str) -> "FunctionTypeInfo | None":
        if self._mypy_types is None:
            return None
        return self._mypy_types.functions.get(func_name)

    def _get_mypy_class_type(self, class_name: str) -> "ClassTypeInfo | None":
        if self._mypy_types is None:
            return None
        return self._mypy_types.classes.get(class_name)

    def _get_mypy_method_type(self, class_name: str, method_name: str) -> "FunctionTypeInfo | None":
        mypy_class = self._get_mypy_class_type(class_name)
        if mypy_class is None:
            return None
        for method in mypy_class.methods:
            if method.name == method_name:
                return method
        return None

    def _mypy_type_to_c_type(self, mypy_type: str) -> str:
        type_map = {
            "int": "mp_int_t",
            "float": "mp_float_t",
            "bool": "bool",
            "str": "mp_obj_t",
            "None": "void",
            "list": "mp_obj_t",
            "dict": "mp_obj_t",
            "tuple": "mp_obj_t",
            "set": "mp_obj_t",
            "object": "mp_obj_t",
            "Any": "mp_obj_t",
        }
        base_type = mypy_type.split("[")[0].strip()
        return type_map.get(base_type, "mp_obj_t")

    def _mypy_type_to_py_type(self, mypy_type: str) -> str:
        base_type = mypy_type.split("[")[0].strip()
        if base_type in ("int", "float", "bool", "str", "list", "dict", "tuple", "set", "None"):
            return base_type
        if "." in base_type:
            return base_type.split(".")[-1]
        return base_type if base_type else "object"

    def _annotation_to_c_type(self, annotation: ast.expr | None) -> str:
        if annotation is None:
            return "mp_obj_t"
        if isinstance(annotation, ast.Name):
            type_map = {
                "int": "mp_int_t",
                "float": "mp_float_t",
                "bool": "bool",
                "str": "mp_obj_t",
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
            "void": "None",
            "mp_obj_t": "object",
        }
        return type_map.get(c_type, "object")

    def _is_list_annotation(self, annotation: ast.expr | None) -> tuple[bool, str | None]:
        """Check if annotation is a list type and extract element type if present.

        Returns (is_list, element_type) where element_type is "int", "float", or None.
        """
        if annotation is None:
            return False, None
        if isinstance(annotation, ast.Name) and annotation.id == "list":
            return True, None
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name) and annotation.value.id == "list":
                element_type = None
                if isinstance(annotation.slice, ast.Name):
                    if annotation.slice.id in ("int", "float"):
                        element_type = annotation.slice.id
                return True, element_type
        return False, None

    def _try_parse_rtuple(self, annotation: ast.expr | None) -> RTuple | None:
        if isinstance(annotation, ast.Subscript):
            return RTuple.from_annotation(annotation)
        return None

    def _parse_defaults(self, args: ast.arguments, num_params: int) -> dict[int, DefaultArg]:
        """Parse default argument values from AST.

        AST stores defaults aligned to the *last* N parameters.
        For `def f(a, b=1, c=2)`, args.defaults = [1, 2] for params at index 1, 2.
        """
        defaults: dict[int, DefaultArg] = {}
        num_defaults = len(args.defaults)
        if num_defaults == 0:
            return defaults

        first_default_idx = num_params - num_defaults
        for i, default_ast in enumerate(args.defaults):
            param_idx = first_default_idx + i
            default_value, c_expr = self._eval_default_value(default_ast)
            defaults[param_idx] = DefaultArg(value=default_value, c_expr=c_expr)

        return defaults

    def _parse_star_args(self, args: ast.arguments) -> tuple[ParamIR | None, ParamIR | None]:
        star_args = None
        star_kwargs = None

        if args.vararg:
            star_args = ParamIR(
                name=args.vararg.arg,
                c_type=CType.MP_OBJ_T,
                kind=ArgKind.ARG_STAR,
            )

        if args.kwarg:
            star_kwargs = ParamIR(
                name=args.kwarg.arg,
                c_type=CType.MP_OBJ_T,
                kind=ArgKind.ARG_STAR2,
            )

        return star_args, star_kwargs

    def _eval_default_value(self, node: ast.expr) -> tuple[object, str | None]:
        """Evaluate a default argument value at compile time.

        Returns (python_value, c_expression) where c_expression is used for code gen.
        """
        if isinstance(node, ast.Constant):
            val = node.value
            if val is None:
                return None, "mp_const_none"
            elif isinstance(val, bool):
                return val, "mp_const_true" if val else "mp_const_false"
            elif isinstance(val, int):
                return val, f"mp_obj_new_int({val})"
            elif isinstance(val, float):
                return val, f"mp_obj_new_float({val})"
            elif isinstance(val, str):
                escaped = val.replace("\\", "\\\\").replace('"', '\\"')
                return val, f'mp_obj_new_str("{escaped}", {len(val)})'
            return val, None

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Constant):
                val = node.operand.value
                if isinstance(val, int):
                    return -val, f"mp_obj_new_int({-val})"
                elif isinstance(val, float):
                    return -val, f"mp_obj_new_float({-val})"

        if isinstance(node, ast.List) and len(node.elts) == 0:
            return [], "mp_obj_new_list(0, NULL)"

        if isinstance(node, ast.Dict) and len(node.keys) == 0:
            return {}, "mp_obj_new_dict(0)"

        if isinstance(node, ast.Tuple) and len(node.elts) == 0:
            return (), "mp_const_empty_tuple"

        if isinstance(node, ast.Set) and len(node.elts) == 0:
            return set(), "mp_obj_new_set(0, NULL)"

        return None, None

    # -------------------------------------------------------------------------
    # Class Building
    # -------------------------------------------------------------------------

    def build_class(self, node: ast.ClassDef) -> ClassIR:
        """Build ClassIR from ast.ClassDef."""
        class_name = node.name
        c_class_name = f"{self.c_name}_{sanitize_name(class_name)}"

        # Check for dataclass and @final decorators
        is_dataclass = False
        is_final_class = False
        dataclass_info = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "dataclass":
                    is_dataclass = True
                    dataclass_info = DataclassInfo()
                elif decorator.id == "final":
                    is_final_class = True
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
            is_final_class=is_final_class,
            ast_node=node,
        )

        # Resolve base class if known
        if base_name and base_name in self._known_classes:
            class_ir.base = self._known_classes[base_name]

        # Parse class body
        self._parse_class_body(node, class_ir)

        # @final class: devirtualize ALL methods (no vtable needed)
        if is_final_class:
            class_ir.virtual_methods.clear()
            for method_ir in class_ir.methods.values():
                method_ir.is_virtual = False
                method_ir.is_final = True

        if is_dataclass and dataclass_info:
            dataclass_info.fields = list(class_ir.fields)

        # Register in known classes
        self._known_classes[class_name] = class_ir

        return class_ir

    def _parse_class_body(self, node: ast.ClassDef, class_ir: ClassIR) -> None:
        """Parse class body to extract fields and methods."""
        mypy_class = self._get_mypy_class_type(class_ir.name)
        mypy_field_types: dict[str, str] = {}
        if mypy_class:
            mypy_field_types = {name: ftype for name, ftype in mypy_class.fields}

        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id

                # Detect Final[type] or bare Final annotation
                is_final_field = False
                inner_annotation = stmt.annotation
                if isinstance(stmt.annotation, ast.Subscript):
                    if (
                        isinstance(stmt.annotation.value, ast.Name)
                        and stmt.annotation.value.id == "Final"
                    ):
                        is_final_field = True
                        inner_annotation = stmt.annotation.slice
                elif isinstance(stmt.annotation, ast.Name) and stmt.annotation.id == "Final":
                    is_final_field = True
                    inner_annotation = None  # type inferred from value

                if field_name in mypy_field_types:
                    py_type = self._mypy_type_to_py_type(mypy_field_types[field_name])
                    c_type = CType.from_python_type(py_type)
                elif inner_annotation is not None:
                    py_type = self._annotation_to_py_type(inner_annotation)
                    c_type = CType.from_python_type(py_type)
                else:
                    # Bare Final without type -- infer from value
                    py_type = "object"
                    if stmt.value and isinstance(stmt.value, ast.Constant):
                        val = stmt.value.value
                        if isinstance(val, bool):
                            py_type = "bool"
                        elif isinstance(val, int):
                            py_type = "int"
                        elif isinstance(val, float):
                            py_type = "float"
                        elif isinstance(val, str):
                            py_type = "str"
                    c_type = CType.from_python_type(py_type)

                has_default = stmt.value is not None
                default_value = None
                final_value = None
                if has_default and isinstance(stmt.value, ast.Constant):
                    default_value = stmt.value.value
                    if is_final_field:
                        final_value = stmt.value.value

                field_ir = FieldIR(
                    name=field_name,
                    py_type=py_type,
                    c_type=c_type,
                    has_default=has_default,
                    default_value=default_value,
                    default_ast=stmt.value,
                    is_final=is_final_field,
                    final_value=final_value,
                )
                class_ir.fields.append(field_ir)

            elif isinstance(stmt, ast.FunctionDef):
                self._parse_method(stmt, class_ir)

    def _parse_method(self, node: ast.FunctionDef, class_ir: ClassIR) -> None:
        """Parse a method definition and add to class IR."""
        method_name = node.name
        c_method_name = f"{class_ir.c_name}_{sanitize_name(method_name)}"

        is_static = False
        is_classmethod = False
        is_property = False
        is_final = False
        property_name: str | None = None
        is_property_setter = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "staticmethod":
                    is_static = True
                elif decorator.id == "classmethod":
                    is_classmethod = True
                elif decorator.id == "property":
                    is_property = True
                elif decorator.id == "final":
                    is_final = True
            elif (
                isinstance(decorator, ast.Attribute)
                and decorator.attr == "setter"
                and isinstance(decorator.value, ast.Name)
            ):
                is_property = True
                is_property_setter = True
                property_name = decorator.value.id
                c_method_name = f"{class_ir.c_name}_{sanitize_name(property_name)}_setter"
        mypy_method = self._get_mypy_method_type(class_ir.name, method_name)
        mypy_param_types: dict[str, str] = {}
        mypy_return_type: str | None = None
        if mypy_method:
            mypy_param_types = {name: ptype for name, ptype in mypy_method.params}
            mypy_return_type = mypy_method.return_type

        params: list[tuple[str, CType]] = []
        method_args = node.args.args if (is_static or is_classmethod) else node.args.args[1:]
        for arg in method_args:
            if arg.arg in mypy_param_types:
                py_type = self._mypy_type_to_py_type(mypy_param_types[arg.arg])
                c_type = CType.from_python_type(py_type)
            else:
                py_type = (
                    self._annotation_to_py_type(arg.annotation) if arg.annotation else "object"
                )
                c_type = CType.from_python_type(py_type)
            params.append((arg.arg, c_type))

        if mypy_return_type:
            py_type = self._mypy_type_to_py_type(mypy_return_type)
            return_type = CType.from_python_type(py_type)
            if py_type == "None":
                return_type = CType.VOID
        else:
            return_type = CType.VOID
            if node.returns:
                py_type = self._annotation_to_py_type(node.returns)
                return_type = CType.from_python_type(py_type)
                if py_type == "None":
                    return_type = CType.VOID

        is_special = method_name.startswith("__") and method_name.endswith("__")
        is_private = method_name.startswith("__") and not method_name.endswith("__")
        is_virtual = (not is_static and not is_classmethod and not is_property) and (
            not is_special or method_name in ("__len__", "__getitem__", "__setitem__")
        )
        # Private (__method) or @final methods cannot be overridden => not virtual
        if is_private or is_final:
            is_virtual = False

        method_ir = MethodIR(
            name=method_name,
            c_name=c_method_name,
            params=params,
            return_type=return_type,
            body_ast=node,
            is_virtual=is_virtual,
            is_static=is_static,
            is_classmethod=is_classmethod,
            is_property=is_property,
            is_special=is_special,
            is_private=is_private,
            is_final=is_final,
            docstring=ast.get_docstring(node),
        )

        if is_property and is_property_setter and property_name is not None:
            class_ir.methods[f"_prop_{property_name}_setter"] = method_ir
            if property_name in class_ir.properties:
                class_ir.properties[property_name].setter = method_ir
        else:
            class_ir.methods[method_name] = method_ir
            if is_property:
                if method_name in class_ir.properties:
                    class_ir.properties[method_name].getter = method_ir
                else:
                    class_ir.properties[method_name] = PropertyInfo(
                        name=method_name, getter=method_ir
                    )

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
        self._temp_counter = 0
        self._var_types = {}
        self._list_vars: dict[str, str | None] = {}
        self._rtuple_types = {}
        self._used_rtuples = set()
        self._uses_print = False
        self._uses_list_opt = False

        # Set up parameter types
        for param_name, param_type in method_ir.params:
            self._var_types[param_name] = param_type.to_c_type_str()

        # Track self and params as locals
        local_vars = [p[0] for p in method_ir.params]
        if not method_ir.is_static and not method_ir.is_classmethod:
            local_vars.insert(0, "self")

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

        method_ir.max_temp = self._temp_counter
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
        # Handle self.attr and param.attr for typed class params
        if isinstance(expr, ast.Attribute):
            if isinstance(expr.value, ast.Name):
                var_name = expr.value.id
                attr_name = expr.attr

                if var_name == "self":
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

                if var_name in self._class_typed_params:
                    param_class_name = self._class_typed_params[var_name]
                    param_class_ir = self._known_classes[param_class_name]

                    for fld, path in param_class_ir.get_all_fields_with_path():
                        if fld.name == attr_name:
                            result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                            return ParamAttrIR(
                                ir_type=result_type,
                                param_name=var_name,
                                c_param_name=sanitize_name(var_name),
                                attr_name=attr_name,
                                attr_path=path,
                                class_c_name=param_class_ir.c_name,
                                result_type=result_type,
                            ), []

                    return ParamAttrIR(
                        ir_type=IRType.OBJ,
                        param_name=var_name,
                        c_param_name=sanitize_name(var_name),
                        attr_name=attr_name,
                        attr_path=attr_name,
                        class_c_name=param_class_ir.c_name,
                        result_type=IRType.OBJ,
                    ), []

            # Handle chained attribute access: self.attr1.attr2 or param.attr1.attr2
            if isinstance(expr.value, ast.Attribute):
                attr_name = expr.attr
                base_class_name = self._get_method_attr_class_type(
                    expr.value, class_ir
                )
                if base_class_name and base_class_name in self._known_classes:
                    base_class_ir = self._known_classes[base_class_name]
                    base_value, base_prelude = self._build_method_expr(
                        expr.value, locals_, class_ir, native
                    )
                    for fld in base_class_ir.get_all_fields():
                        if fld.name == attr_name:
                            result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                            temp_name = self._fresh_temp()
                            result_temp = TempIR(ir_type=result_type, name=temp_name)
                            attr_access = AttrAccessIR(
                                result=result_temp,
                                obj=base_value,
                                attr_name=attr_name,
                                class_c_name=base_class_ir.c_name,
                                result_type=result_type,
                            )
                            return result_temp, base_prelude + [attr_access]

        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
            if (
                isinstance(expr.func.value, ast.Call)
                and isinstance(expr.func.value.func, ast.Name)
                and expr.func.value.func.id == "super"
                and len(expr.func.value.args) == 0
                and len(expr.func.value.keywords) == 0
            ):
                method_name = expr.func.attr

                parent_class = class_ir.base
                while parent_class is not None and method_name not in parent_class.methods:
                    parent_class = parent_class.base

                if parent_class is not None:
                    parent_method = parent_class.methods[method_name]

                    args: list[ValueIR] = []
                    arg_preludes: list[list] = []
                    for arg in expr.args:
                        val, prelude = self._build_method_expr(arg, locals_, class_ir, native)
                        args.append(val)
                        arg_preludes.append(prelude)

                    return_type = IRType.from_c_type_str(parent_method.return_type.to_c_type_str())
                    all_preludes = [p for pl in arg_preludes for p in pl]
                    return SuperCallIR(
                        ir_type=return_type,
                        method_name=method_name,
                        parent_c_name=parent_class.c_name,
                        parent_method_c_name=parent_method.c_name,
                        args=args,
                        return_type=return_type,
                        is_init=method_name == "__init__",
                        arg_preludes=arg_preludes,
                    ), all_preludes

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

            # Allow self.__method() but reject other_obj.__method()
            is_self_call = (
                isinstance(expr.func.value, ast.Name) and expr.func.value.id == "self"
            )
            if self._is_private_name(method_name) and not is_self_call:
                raise TypeError(
                    f"Cannot access private method '{method_name}' from outside its class"
                )
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

        builtins = {
            "abs",
            "int",
            "float",
            "bool",
            "str",
            "len",
            "range",
            "list",
            "tuple",
            "set",
            "dict",
            "min",
            "max",
            "sum",
            "enumerate",
            "zip",
            "sorted",
        }
        if func_name in builtins:
            if func_name in ("abs", "int", "len", "sum"):
                ir_type = IRType.INT
            elif func_name == "float":
                ir_type = IRType.FLOAT
            elif func_name == "bool":
                ir_type = IRType.BOOL
            else:
                ir_type = IRType.OBJ
            return CallIR(
                ir_type=ir_type,
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
