"""
Function Emitter: FuncIR -> C code.

This module generates MicroPython-compatible C code from function IR.
"""

from __future__ import annotations

import re

from .container_emitter import ContainerEmitter
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
    ExprStmtIR,
    ForIterIR,
    ForRangeIR,
    FuncIR,
    IfExprIR,
    IfIR,
    InstrIR,
    IRType,
    MethodIR,
    ModuleAttrIR,
    ModuleCallIR,
    NameIR,
    ParamAttrIR,
    PassIR,
    PrintIR,
    RaiseIR,
    ReturnIR,
    SelfAttrIR,
    SelfAugAssignIR,
    SelfMethodCallIR,
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


class BaseEmitter:
    def __init__(self, max_temp: int):
        self._container_emitter = ContainerEmitter()
        self._temp_counter = max_temp
        self._loop_depth = 0
        self._nlr_stack: list[str] = []  # Stack of nlr_buf variable names for try blocks

    def _fresh_temp(self) -> str:
        self._temp_counter += 1
        return f"_tmp{self._temp_counter}"

    def _mark_uses_builtins(self) -> None:
        if hasattr(self, "func_ir"):
            self.func_ir.uses_builtins = True

    def _mark_uses_checked_div(self) -> None:
        if hasattr(self, "func_ir"):
            self.func_ir.uses_checked_div = True

    def _should_unbox_self_method_args(self, call: SelfMethodCallIR, native: bool) -> bool:
        del native
        return call.return_type in (IRType.INT, IRType.FLOAT, IRType.BOOL)

    def _emit_statement(self, stmt: StmtIR, native: bool = False) -> list[str]:
        if isinstance(stmt, ReturnIR):
            return self._emit_return(stmt, native)
        elif isinstance(stmt, IfIR):
            return self._emit_if(stmt, native)
        elif isinstance(stmt, WhileIR):
            return self._emit_while(stmt, native)
        elif isinstance(stmt, ForRangeIR):
            return self._emit_for_range(stmt, native)
        elif isinstance(stmt, ForIterIR):
            return self._emit_for_iter(stmt, native)
        elif isinstance(stmt, TryIR):
            return self._emit_try(stmt, native)
        elif isinstance(stmt, RaiseIR):
            return self._emit_raise(stmt, native)
        elif isinstance(stmt, AssignIR):
            return self._emit_assign(stmt, native)
        elif isinstance(stmt, AnnAssignIR):
            return self._emit_ann_assign(stmt, native)
        elif isinstance(stmt, AugAssignIR):
            return self._emit_aug_assign(stmt, native)
        elif isinstance(stmt, SelfAugAssignIR):
            return self._emit_self_aug_assign(stmt, native)
        elif isinstance(stmt, SubscriptAssignIR):
            return self._emit_subscript_assign(stmt, native)
        elif isinstance(stmt, TupleUnpackIR):
            return self._emit_tuple_unpack(stmt, native)
        elif isinstance(stmt, AttrAssignIR):
            return self._emit_attr_assign(stmt, native)
        elif isinstance(stmt, ExprStmtIR):
            return self._emit_expr_stmt(stmt, native)
        elif isinstance(stmt, PrintIR):
            return self._emit_print(stmt, native)
        elif isinstance(stmt, BreakIR):
            if self._loop_depth > 0:
                return ["    break;"]
            return ["    /* ERROR: break outside loop */"]
        elif isinstance(stmt, ContinueIR):
            if self._loop_depth > 0:
                return ["    continue;"]
            return ["    /* ERROR: continue outside loop */"]
        elif isinstance(stmt, PassIR):
            return []
        return []

    def _emit_if(self, stmt: IfIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.test_prelude)
        cond, _ = self._emit_expr(stmt.test, native)
        lines.append(f"    if ({cond}) {{")

        for s in stmt.body:
            for line in self._emit_statement(s, native):
                lines.append("    " + line)

        if stmt.orelse:
            lines.append("    } else {")
            for s in stmt.orelse:
                for line in self._emit_statement(s, native):
                    lines.append("    " + line)

        lines.append("    }")
        return lines

    def _emit_while(self, stmt: WhileIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.test_prelude)
        cond, _ = self._emit_expr(stmt.test, native)
        lines.append(f"    while ({cond}) {{")

        self._loop_depth += 1
        for s in stmt.body:
            for line in self._emit_statement(s, native):
                lines.append("    " + line)
        self._loop_depth -= 1

        lines.append("    }")
        return lines

    def _emit_for_range(self, stmt: ForRangeIR, native: bool = False) -> list[str]:
        lines = []
        c_loop_var = stmt.c_loop_var

        if stmt.is_new_var:
            lines.append(f"    mp_int_t {c_loop_var};")

        start_expr, _ = self._emit_expr(stmt.start, native)
        end_expr, _ = self._emit_expr(stmt.end, native)

        end_var = self._fresh_temp()
        lines.append(f"    mp_int_t {end_var} = {end_expr};")

        step_var: str | None = None
        if not stmt.step_is_constant and stmt.step is not None:
            step_var = self._fresh_temp()
            step_expr, _ = self._emit_expr(stmt.step, native)
            lines.append(f"    mp_int_t {step_var} = {step_expr};")

        if stmt.step_is_constant and stmt.step_value == 1:
            cond = f"{c_loop_var} < {end_var}"
            inc = f"{c_loop_var}++"
        elif stmt.step_is_constant and stmt.step_value == -1:
            cond = f"{c_loop_var} > {end_var}"
            inc = f"{c_loop_var}--"
        elif stmt.step_is_constant and stmt.step_value is not None:
            if stmt.step_value > 0:
                cond = f"{c_loop_var} < {end_var}"
            else:
                cond = f"{c_loop_var} > {end_var}"
            inc = f"{c_loop_var} += {stmt.step_value}"
        else:
            assert step_var is not None
            cond = f"({step_var} > 0) ? ({c_loop_var} < {end_var}) : ({c_loop_var} > {end_var})"
            inc = f"{c_loop_var} += {step_var}"

        lines.append(f"    for ({c_loop_var} = {start_expr}; {cond}; {inc}) {{")

        self._loop_depth += 1
        for s in stmt.body:
            for line in self._emit_statement(s, native):
                lines.append("    " + line)
        self._loop_depth -= 1

        lines.append("    }")
        return lines

    def _emit_for_iter(self, stmt: ForIterIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.iter_prelude)
        iter_expr, _ = self._emit_expr(stmt.iterable, native)

        iter_var = self._fresh_temp()
        iter_buf_var = self._fresh_temp()
        c_loop_var = stmt.c_loop_var

        if stmt.is_new_var:
            lines.append(f"    mp_obj_t {c_loop_var};")

        lines.append(f"    mp_obj_iter_buf_t {iter_buf_var};")
        lines.append(f"    mp_obj_t {iter_var} = mp_getiter({iter_expr}, &{iter_buf_var});")
        lines.append(
            f"    while (({c_loop_var} = mp_iternext({iter_var})) != MP_OBJ_STOP_ITERATION) {{"
        )

        self._loop_depth += 1
        for s in stmt.body:
            for line in self._emit_statement(s, native):
                lines.append("    " + line)
        self._loop_depth -= 1

        lines.append("    }")
        return lines

    def _emit_try(self, stmt: TryIR, native: bool = False) -> list[str]:
        lines: list[str] = []
        nlr_buf = self._fresh_temp()
        has_finally = len(stmt.finalbody) > 0
        has_handlers = len(stmt.handlers) > 0

        if has_finally:
            exc_caught_var = self._fresh_temp()
            lines.append(f"    bool {exc_caught_var} = false;")

        lines.append(f"    nlr_buf_t {nlr_buf};")
        lines.append(f"    if (nlr_push(&{nlr_buf}) == 0) {{")

        self._nlr_stack.append(nlr_buf)
        for s in stmt.body:
            for line in self._emit_statement(s, native):
                lines.append("    " + line)
        self._nlr_stack.pop()

        lines.append("        nlr_pop();")

        if stmt.orelse:
            for s in stmt.orelse:
                for line in self._emit_statement(s, native):
                    lines.append("    " + line)

        lines.append("    } else {")

        if has_handlers:
            exc_var = self._fresh_temp()
            lines.append(f"        mp_obj_t {exc_var} = MP_OBJ_FROM_PTR({nlr_buf}.ret_val);")

            for i, handler in enumerate(stmt.handlers):
                if handler.exc_type is None:
                    if i == 0:
                        lines.append("        {")
                    else:
                        lines.append("        } else {")
                else:
                    mp_type = self._get_mp_exception_type(handler.exc_type)
                    cond = (
                        f"mp_obj_is_subclass_fast("
                        f"MP_OBJ_FROM_PTR(mp_obj_get_type({exc_var})), "
                        f"MP_OBJ_FROM_PTR({mp_type}))"
                    )
                    if i == 0:
                        lines.append(f"        if ({cond}) {{")
                    else:
                        lines.append(f"        }} else if ({cond}) {{")

                if handler.exc_var and handler.c_exc_var:
                    lines.append(f"            mp_obj_t {handler.c_exc_var} = {exc_var};")

                for s in handler.body:
                    for line in self._emit_statement(s, native):
                        lines.append("        " + line)

            has_bare_except = any(h.exc_type is None for h in stmt.handlers)
            if not has_bare_except:
                if has_finally:
                    lines.append("        } else {")
                    lines.append(f"            {exc_caught_var} = true;")
                    lines.append("        }")
                else:
                    lines.append("        } else {")
                    lines.append(f"            nlr_jump({nlr_buf}.ret_val);")
                    lines.append("        }")
            else:
                lines.append("        }")
        else:
            if has_finally:
                lines.append(f"        {exc_caught_var} = true;")
            else:
                lines.append(f"        nlr_jump({nlr_buf}.ret_val);")

        lines.append("    }")

        if has_finally:
            for s in stmt.finalbody:
                for line in self._emit_statement(s, native):
                    lines.append(line)

            lines.append(f"    if ({exc_caught_var}) {{")
            lines.append(f"        nlr_jump({nlr_buf}.ret_val);")
            lines.append("    }")

        return lines

    def _emit_raise(self, stmt: RaiseIR, native: bool = False) -> list[str]:
        del native
        lines = self._emit_prelude(stmt.prelude)

        if stmt.is_reraise:
            lines.append("    nlr_jump(nlr.ret_val);")
            return lines

        if stmt.exc_type is None:
            lines.append("    mp_raise_msg(&mp_type_Exception, NULL);")
            return lines

        mp_type = self._get_mp_exception_type(stmt.exc_type)

        if stmt.exc_msg is not None:
            msg_expr, _ = self._emit_expr(stmt.exc_msg, False)
            if isinstance(stmt.exc_msg, ConstIR) and isinstance(stmt.exc_msg.value, str):
                msg_str = stmt.exc_msg.value.replace('"', '\\"')
                lines.append(f'    mp_raise_msg({mp_type}, MP_ERROR_TEXT("{msg_str}"));')
            else:
                lines.append(
                    f'    mp_raise_msg_varg({mp_type}, "%s", mp_obj_str_get_str({msg_expr}));'
                )
        else:
            lines.append(f"    mp_raise_msg({mp_type}, NULL);")

        return lines

    def _get_mp_exception_type(self, exc_type: str) -> str:
        exc_map = {
            "Exception": "&mp_type_Exception",
            "BaseException": "&mp_type_BaseException",
            "TypeError": "&mp_type_TypeError",
            "ValueError": "&mp_type_ValueError",
            "RuntimeError": "&mp_type_RuntimeError",
            "KeyError": "&mp_type_KeyError",
            "IndexError": "&mp_type_IndexError",
            "AttributeError": "&mp_type_AttributeError",
            "StopIteration": "&mp_type_StopIteration",
            "ZeroDivisionError": "&mp_type_ZeroDivisionError",
            "OverflowError": "&mp_type_OverflowError",
            "MemoryError": "&mp_type_MemoryError",
            "OSError": "&mp_type_OSError",
            "NotImplementedError": "&mp_type_NotImplementedError",
            "AssertionError": "&mp_type_AssertionError",
            "ImportError": "&mp_type_ImportError",
            "NameError": "&mp_type_NameError",
            "LookupError": "&mp_type_LookupError",
            "ArithmeticError": "&mp_type_ArithmeticError",
            "EOFError": "&mp_type_EOFError",
            "GeneratorExit": "&mp_type_GeneratorExit",
            "SystemExit": "&mp_type_SystemExit",
            "KeyboardInterrupt": "&mp_type_KeyboardInterrupt",
        }
        return exc_map.get(exc_type, "&mp_type_Exception")

    def _emit_assign(self, stmt: AssignIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        expr, expr_type = self._emit_expr(stmt.value, native)

        if stmt.c_type != expr_type:
            expr = self._unbox_if_needed(expr, expr_type, stmt.c_type)

        if stmt.is_new_var:
            lines.append(f"    {stmt.c_type} {stmt.c_target} = {expr};")
        else:
            lines.append(f"    {stmt.c_target} = {expr};")
        return lines

    def _emit_aug_assign(self, stmt: AugAssignIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        expr, expr_type = self._emit_expr(stmt.value, native)

        if stmt.target_c_type == "mp_obj_t":
            boxed_expr = self._box_value(expr, expr_type)
            op_map = {
                "+=": "MP_BINARY_OP_INPLACE_ADD",
                "-=": "MP_BINARY_OP_INPLACE_SUBTRACT",
                "*=": "MP_BINARY_OP_INPLACE_MULTIPLY",
                "/=": "MP_BINARY_OP_INPLACE_TRUE_DIVIDE",
                "//=": "MP_BINARY_OP_INPLACE_FLOOR_DIVIDE",
                "%=": "MP_BINARY_OP_INPLACE_MODULO",
                "&=": "MP_BINARY_OP_INPLACE_AND",
                "|=": "MP_BINARY_OP_INPLACE_OR",
                "^=": "MP_BINARY_OP_INPLACE_XOR",
                "<<=": "MP_BINARY_OP_INPLACE_LSHIFT",
                ">>=": "MP_BINARY_OP_INPLACE_RSHIFT",
            }
            mp_op = op_map.get(stmt.op, "MP_BINARY_OP_INPLACE_ADD")
            lines.append(
                f"    {stmt.c_target} = mp_binary_op({mp_op}, {stmt.c_target}, {boxed_expr});"
            )
        else:
            expr = self._unbox_if_needed(expr, expr_type)
            lines.append(f"    {stmt.c_target} {stmt.op} {expr};")
        return lines

    def _emit_self_aug_assign(self, stmt: SelfAugAssignIR, native: bool = False) -> list[str]:
        del stmt, native
        return []

    def _emit_subscript_assign(self, stmt: SubscriptAssignIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        obj_expr, _ = self._emit_expr(stmt.container, native)
        idx_expr, idx_type = self._emit_expr(stmt.key, native)
        val_expr, val_type = self._emit_expr(stmt.value, native)
        boxed_key = self._box_value(idx_expr, idx_type)
        boxed_val = self._box_value(val_expr, val_type)
        lines.append(f"    mp_obj_subscr({obj_expr}, {boxed_key}, {boxed_val});")
        return lines

    def _emit_tuple_unpack(self, stmt: TupleUnpackIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        tuple_expr, _ = self._emit_expr(stmt.value, native)

        tuple_temp = self._fresh_temp()
        lines.append(f"    mp_obj_t {tuple_temp} = {tuple_expr};")

        for i, (_, c_name, is_new, c_type) in enumerate(stmt.targets):
            item_expr = f"mp_obj_subscr({tuple_temp}, mp_obj_new_int({i}), MP_OBJ_SENTINEL)"
            unboxed_expr = self._unbox_expr(item_expr, c_type)
            if is_new:
                lines.append(f"    {c_type} {c_name} = {unboxed_expr};")
            else:
                lines.append(f"    {c_name} = {unboxed_expr};")
        return lines

    def _emit_attr_assign(self, stmt: AttrAssignIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        value_expr, _ = self._emit_expr(stmt.value, native)
        lines.append(f"    self->{stmt.attr_path} = {value_expr};")
        return lines

    def _emit_expr_stmt(self, stmt: ExprStmtIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        expr, _ = self._emit_expr(stmt.expr, native)
        lines.append(f"    (void){expr};")
        return lines

    def _emit_print(self, stmt: PrintIR, native: bool = False) -> list[str]:
        lines = []
        for prelude in stmt.preludes:
            lines.extend(self._emit_prelude(prelude))

        if not stmt.args:
            lines.append('    mp_print_str(&mp_plat_print, "\\n");')
        else:
            for i, arg in enumerate(stmt.args):
                if i > 0:
                    lines.append('    mp_print_str(&mp_plat_print, " ");')
                arg_expr, arg_type = self._emit_expr(arg, native)
                boxed = self._box_value(arg_expr, arg_type)
                lines.append(f"    mp_obj_print_helper(&mp_plat_print, {boxed}, PRINT_STR);")
            lines.append('    mp_print_str(&mp_plat_print, "\\n");')
        return lines

    def _emit_prelude(self, prelude: list[InstrIR]) -> list[str]:
        return self._container_emitter.emit_prelude(prelude)

    def _emit_expr(self, value: ValueIR, native: bool = False) -> tuple[str, str]:
        if isinstance(value, ConstIR):
            return self._emit_const(value)
        elif isinstance(value, NameIR):
            return value.c_name, value.ir_type.to_c_type_str()
        elif isinstance(value, TempIR):
            return value.name, value.ir_type.to_c_type_str()
        elif isinstance(value, BinOpIR):
            return self._emit_binop(value, native)
        elif isinstance(value, UnaryOpIR):
            return self._emit_unaryop(value, native)
        elif isinstance(value, CompareIR):
            return self._emit_compare(value, native)
        elif isinstance(value, CallIR):
            return self._emit_call(value, native)
        elif isinstance(value, IfExprIR):
            return self._emit_ifexp(value, native)
        elif isinstance(value, SubscriptIR):
            return self._emit_subscript(value, native)
        elif isinstance(value, SliceIR):
            return self._emit_slice(value, native)
        elif isinstance(value, ClassInstantiationIR):
            return self._emit_class_instantiation(value, native)
        elif isinstance(value, SelfAttrIR):
            return self._emit_self_attr(value)
        elif isinstance(value, ParamAttrIR):
            return self._emit_param_attr(value)
        elif isinstance(value, SelfMethodCallIR):
            return self._emit_self_method_call(value, native)
        elif isinstance(value, SuperCallIR):
            return self._emit_super_call(value, native)
        elif isinstance(value, ModuleCallIR):
            return self._emit_module_call(value, native)
        elif isinstance(value, ModuleAttrIR):
            return self._emit_module_attr(value)
        return "/* unsupported */", "mp_obj_t"

    def _emit_const(self, const: ConstIR) -> tuple[str, str]:
        val = const.value
        if isinstance(val, bool):
            return ("true" if val else "false"), "bool"
        elif isinstance(val, int):
            return str(val), "mp_int_t"
        elif isinstance(val, float):
            return str(val), "mp_float_t"
        elif val is None:
            return "mp_const_none", "mp_obj_t"
        elif isinstance(val, str):
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            return f'mp_obj_new_str("{escaped}", {len(val)})', "mp_obj_t"
        elif isinstance(val, list) and len(val) == 0:
            return "mp_obj_new_list(0, NULL)", "mp_obj_t"
        elif isinstance(val, tuple) and len(val) == 0:
            return "mp_const_empty_tuple", "mp_obj_t"
        elif isinstance(val, set) and len(val) == 0:
            return "mp_obj_new_set(0, NULL)", "mp_obj_t"
        elif isinstance(val, dict) and len(val) == 0:
            return "mp_obj_new_dict(0)", "mp_obj_t"
        return "/* unknown constant */", "mp_obj_t"

    def _emit_binop(self, op: BinOpIR, native: bool = False) -> tuple[str, str]:
        del native
        left, left_type = self._emit_expr(op.left)
        right, right_type = self._emit_expr(op.right)

        target_type = op.ir_type.to_c_type_str() if op.ir_type else "mp_int_t"

        if op.op in ("&&", "||"):
            left = self._to_bool_expr(left, left_type)
            right = self._to_bool_expr(right, right_type)
            return f"({left} {op.op} {right})", "bool"

        if target_type == "mp_obj_t":
            if left_type != "mp_obj_t":
                left = self._box_value(left, left_type)
            if right_type != "mp_obj_t":
                right = self._box_value(right, right_type)
            op_map = {
                "+": "MP_BINARY_OP_ADD",
                "-": "MP_BINARY_OP_SUBTRACT",
                "*": "MP_BINARY_OP_MULTIPLY",
                "/": "MP_BINARY_OP_TRUE_DIVIDE",
                "//": "MP_BINARY_OP_FLOOR_DIVIDE",
                "%": "MP_BINARY_OP_MODULO",
            }
            mp_op = op_map.get(op.op, "MP_BINARY_OP_ADD")
            return f"mp_binary_op({mp_op}, {left}, {right})", "mp_obj_t"

        left = self._unbox_if_needed(left, left_type, target_type)
        right = self._unbox_if_needed(right, right_type, target_type)

        if self._nlr_stack and op.op in ("//", "%") and target_type == "mp_int_t":
            self._mark_uses_checked_div()
            if op.op == "//":
                return f"mp_int_floor_divide_checked({left}, {right})", target_type
            else:
                return f"mp_int_modulo_checked({left}, {right})", target_type

        c_op = "/" if op.op == "//" else op.op
        return f"({left} {c_op} {right})", target_type

    def _to_bool_expr(self, expr: str, expr_type: str) -> str:
        if expr_type == "bool":
            return expr
        elif expr_type == "mp_obj_t":
            return f"mp_obj_is_true({expr})"
        else:
            return f"({expr} != 0)"

    def _emit_unaryop(self, op: UnaryOpIR, native: bool = False) -> tuple[str, str]:
        operand, op_type = self._emit_expr(op.operand, native)
        result_type = "bool" if op.op == "!" else op_type
        return f"({op.op}{operand})", result_type

    def _emit_compare(self, op: CompareIR, native: bool = False) -> tuple[str, str]:
        left, left_type = self._emit_expr(op.left, native)

        parts = []
        prev = left
        prev_type = left_type

        for c_op, comparator in zip(op.ops, op.comparators):
            right, right_type = self._emit_expr(comparator, native)

            if c_op in ("in", "not in"):
                boxed_prev = self._box_value(prev, prev_type)
                contains_expr = (
                    f"mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, {boxed_prev}, {right}))"
                )
                if c_op == "not in":
                    parts.append(f"(!{contains_expr})")
                else:
                    parts.append(f"({contains_expr})")
            else:
                if prev_type == "mp_obj_t" or right_type == "mp_obj_t":
                    target = (
                        right_type
                        if right_type != "mp_obj_t"
                        else (prev_type if prev_type != "mp_obj_t" else "mp_int_t")
                    )
                    prev = self._unbox_if_needed(prev, prev_type, target)
                    right = self._unbox_if_needed(right, right_type, target)
                parts.append(f"({prev} {c_op} {right})")

            prev = right
            prev_type = right_type

        if len(parts) > 1:
            return "(" + " && ".join(parts) + ")", "bool"
        return parts[0], "bool"

    def _emit_call(self, call: CallIR, native: bool = False) -> tuple[str, str]:
        if call.is_builtin:
            return self._emit_builtin_call(call, native)

        args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            args.append(self._box_value(arg_expr, arg_type))
        args_str = ", ".join(args)

        return f"mp_obj_get_int({call.c_func_name}({args_str}))", "mp_int_t"

    def _emit_builtin_call(self, call: CallIR, native: bool = False) -> tuple[str, str]:
        del native
        func = call.builtin_kind
        args = [self._emit_expr(arg) for arg in call.args]

        if func == "abs" and args:
            a = args[0][0]
            return f"(({a}) < 0 ? -({a}) : ({a}))", "mp_int_t"
        elif func == "int" and args:
            return f"((mp_int_t)({args[0][0]}))", "mp_int_t"
        elif func == "float" and args:
            return f"((mp_float_t)({args[0][0]}))", "mp_float_t"
        elif func == "len" and args:
            arg_expr, arg_type = args[0]
            if call.is_list_len_opt:
                return f"mp_list_len_fast({arg_expr})", "mp_int_t"
            boxed = self._box_value(arg_expr, arg_type)
            return f"mp_obj_get_int(mp_obj_len({boxed}))", "mp_int_t"
        elif func == "range":
            boxed_args = [self._box_value(a[0], a[1]) for a in args]
            if len(boxed_args) == 1:
                return (
                    f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_range), {boxed_args[0]})",
                    "mp_obj_t",
                )
            elif len(boxed_args) == 2:
                return (
                    f"mp_call_function_2(MP_OBJ_FROM_PTR(&mp_type_range), {boxed_args[0]}, {boxed_args[1]})",
                    "mp_obj_t",
                )
            elif len(boxed_args) == 3:
                return (
                    f"mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_type_range), 3, 0, (const mp_obj_t[]){{{boxed_args[0]}, {boxed_args[1]}, {boxed_args[2]}}})",
                    "mp_obj_t",
                )
        elif func == "list" and not args:
            return "mp_obj_new_list(0, NULL)", "mp_obj_t"
        elif func == "list" and args:
            return f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_list), {args[0][0]})", "mp_obj_t"
        elif func == "tuple" and not args:
            return "mp_const_empty_tuple", "mp_obj_t"
        elif func == "tuple" and args:
            return f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_tuple), {args[0][0]})", "mp_obj_t"
        elif func == "set" and not args:
            return "mp_obj_new_set(0, NULL)", "mp_obj_t"
        elif func == "set" and args:
            return f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_set), {args[0][0]})", "mp_obj_t"
        elif func == "dict" and not args:
            return "mp_obj_new_dict(0)", "mp_obj_t"
        elif func == "dict" and args:
            return f"mp_obj_dict_copy({args[0][0]})", "mp_obj_t"
        elif func == "bool" and args:
            arg_expr, arg_type = args[0]
            if arg_type == "bool":
                return arg_expr, "bool"
            boxed = self._box_value(arg_expr, arg_type)
            return f"mp_obj_is_true({boxed})", "bool"
        elif func == "str" and args:
            arg_expr, arg_type = args[0]
            boxed = self._box_value(arg_expr, arg_type)
            return f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_str), {boxed})", "mp_obj_t"
        elif func == "min":
            if len(args) == 2:
                a_expr, a_type = args[0]
                b_expr, b_type = args[1]
                if a_type == "mp_int_t" and b_type == "mp_int_t":
                    return f"(({a_expr}) < ({b_expr}) ? ({a_expr}) : ({b_expr}))", "mp_int_t"
                elif a_type == "mp_float_t" and b_type == "mp_float_t":
                    return f"(({a_expr}) < ({b_expr}) ? ({a_expr}) : ({b_expr}))", "mp_float_t"
            elif len(args) == 3:
                a_expr, a_type = args[0]
                b_expr, b_type = args[1]
                c_expr, c_type = args[2]
                if a_type == "mp_int_t" and b_type == "mp_int_t" and c_type == "mp_int_t":
                    return (
                        f"(({a_expr}) < ({b_expr}) ? "
                        f"(({a_expr}) < ({c_expr}) ? ({a_expr}) : ({c_expr})) : "
                        f"(({b_expr}) < ({c_expr}) ? ({b_expr}) : ({c_expr})))",
                        "mp_int_t",
                    )
            self._mark_uses_builtins()
            if len(args) == 1:
                boxed = self._box_value(args[0][0], args[0][1])
                return (
                    f"mp_obj_get_int(mp_call_function_1(MP_OBJ_FROM_PTR(&mp_builtin_min_obj), {boxed}))",
                    "mp_int_t",
                )
            elif len(args) >= 2:
                boxed_args = [self._box_value(a[0], a[1]) for a in args]
                args_str = ", ".join(boxed_args)
                return (
                    f"mp_obj_get_int(mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_builtin_min_obj), {len(args)}, 0, (const mp_obj_t[]){{{args_str}}}))",
                    "mp_int_t",
                )
        elif func == "max":
            if len(args) == 2:
                a_expr, a_type = args[0]
                b_expr, b_type = args[1]
                if a_type == "mp_int_t" and b_type == "mp_int_t":
                    return f"(({a_expr}) > ({b_expr}) ? ({a_expr}) : ({b_expr}))", "mp_int_t"
                elif a_type == "mp_float_t" and b_type == "mp_float_t":
                    return f"(({a_expr}) > ({b_expr}) ? ({a_expr}) : ({b_expr}))", "mp_float_t"
            elif len(args) == 3:
                a_expr, a_type = args[0]
                b_expr, b_type = args[1]
                c_expr, c_type = args[2]
                if a_type == "mp_int_t" and b_type == "mp_int_t" and c_type == "mp_int_t":
                    return (
                        f"(({a_expr}) > ({b_expr}) ? "
                        f"(({a_expr}) > ({c_expr}) ? ({a_expr}) : ({c_expr})) : "
                        f"(({b_expr}) > ({c_expr}) ? ({b_expr}) : ({c_expr})))",
                        "mp_int_t",
                    )
            self._mark_uses_builtins()
            if len(args) == 1:
                boxed = self._box_value(args[0][0], args[0][1])
                return (
                    f"mp_obj_get_int(mp_call_function_1(MP_OBJ_FROM_PTR(&mp_builtin_max_obj), {boxed}))",
                    "mp_int_t",
                )
            elif len(args) >= 2:
                boxed_args = [self._box_value(a[0], a[1]) for a in args]
                args_str = ", ".join(boxed_args)
                return (
                    f"mp_obj_get_int(mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_builtin_max_obj), {len(args)}, 0, (const mp_obj_t[]){{{args_str}}}))",
                    "mp_int_t",
                )
        elif func == "sum":
            if call.is_typed_list_sum and call.sum_list_var and len(args) == 1:
                list_var = sanitize_name(call.sum_list_var)
                if call.sum_element_type == "float":
                    return f"mp_list_sum_float({list_var})", "mp_float_t"
                else:
                    return f"mp_list_sum_int({list_var})", "mp_int_t"
            self._mark_uses_builtins()
            if len(args) == 1:
                boxed = self._box_value(args[0][0], args[0][1])
                return (
                    f"mp_obj_get_int(mp_call_function_1(MP_OBJ_FROM_PTR(&mp_builtin_sum_obj), {boxed}))",
                    "mp_int_t",
                )
            elif len(args) == 2:
                boxed_iter = self._box_value(args[0][0], args[0][1])
                boxed_start = self._box_value(args[1][0], args[1][1])
                return (
                    f"mp_obj_get_int(mp_call_function_2(MP_OBJ_FROM_PTR(&mp_builtin_sum_obj), {boxed_iter}, {boxed_start}))",
                    "mp_int_t",
                )
        elif func == "enumerate":
            boxed_args = [self._box_value(a[0], a[1]) for a in args]
            if len(boxed_args) == 1:
                return (
                    f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_enumerate), {boxed_args[0]})",
                    "mp_obj_t",
                )
            elif len(boxed_args) == 2:
                return (
                    f"mp_call_function_2(MP_OBJ_FROM_PTR(&mp_type_enumerate), {boxed_args[0]}, {boxed_args[1]})",
                    "mp_obj_t",
                )
        elif func == "zip":
            boxed_args = [self._box_value(a[0], a[1]) for a in args]
            if len(boxed_args) == 0:
                return "mp_call_function_0(MP_OBJ_FROM_PTR(&mp_type_zip))", "mp_obj_t"
            elif len(boxed_args) == 1:
                return (
                    f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_zip), {boxed_args[0]})",
                    "mp_obj_t",
                )
            elif len(boxed_args) == 2:
                return (
                    f"mp_call_function_2(MP_OBJ_FROM_PTR(&mp_type_zip), {boxed_args[0]}, {boxed_args[1]})",
                    "mp_obj_t",
                )
            else:
                args_str = ", ".join(boxed_args)
                return (
                    f"mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_type_zip), {len(boxed_args)}, 0, (const mp_obj_t[]){{{args_str}}})",
                    "mp_obj_t",
                )
        elif func == "sorted":
            self._mark_uses_builtins()
            if len(args) >= 1:
                boxed = self._box_value(args[0][0], args[0][1])
                return (
                    f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_builtin_sorted_obj), {boxed})",
                    "mp_obj_t",
                )

        return "/* unsupported builtin */", "mp_obj_t"

    def _emit_ifexp(self, expr: IfExprIR, native: bool = False) -> tuple[str, str]:
        test, _ = self._emit_expr(expr.test, native)
        body, body_type = self._emit_expr(expr.body, native)
        orelse, _ = self._emit_expr(expr.orelse, native)
        return f"(({test}) ? ({body}) : ({orelse}))", body_type

    def _emit_subscript(self, sub: SubscriptIR, native: bool = False) -> tuple[str, str]:
        value_expr, _ = self._emit_expr(sub.value, native)

        if sub.is_rtuple and sub.rtuple_index is not None:
            return f"{value_expr}.f{sub.rtuple_index}", "mp_int_t"

        if isinstance(sub.slice_, SliceIR):
            slice_c = self._emit_slice(sub.slice_, native)[0]
            return f"mp_obj_subscr({value_expr}, {slice_c}, MP_OBJ_SENTINEL)", "mp_obj_t"

        if sub.is_list_opt:
            const_idx = self._get_constant_index(sub.slice_)
            if const_idx is not None:
                if const_idx >= 0:
                    return f"mp_list_get_fast({value_expr}, {const_idx})", "mp_obj_t"
                else:
                    return f"mp_list_get_neg({value_expr}, {const_idx})", "mp_obj_t"
            slice_expr, slice_type = self._emit_expr(sub.slice_, native)
            if slice_type == "mp_int_t":
                return f"mp_list_get_int({value_expr}, {slice_expr})", "mp_obj_t"

        slice_expr, slice_type = self._emit_expr(sub.slice_, native)
        boxed_key = self._box_value(slice_expr, slice_type)
        return f"mp_obj_subscr({value_expr}, {boxed_key}, MP_OBJ_SENTINEL)", "mp_obj_t"

    def _get_constant_index(self, slice_ir: ValueIR) -> int | None:
        if isinstance(slice_ir, ConstIR) and isinstance(slice_ir.value, int):
            return slice_ir.value
        if isinstance(slice_ir, UnaryOpIR) and slice_ir.op == "-":
            if isinstance(slice_ir.operand, ConstIR) and isinstance(slice_ir.operand.value, int):
                return -slice_ir.operand.value
        return None

    def _emit_slice(self, slice_ir: SliceIR, native: bool = False) -> tuple[str, str]:
        lower = "mp_const_none"
        upper = "mp_const_none"
        step = "mp_const_none"

        if slice_ir.lower is not None:
            lower_expr, lower_type = self._emit_expr(slice_ir.lower, native)
            lower = self._box_value(lower_expr, lower_type)
        if slice_ir.upper is not None:
            upper_expr, upper_type = self._emit_expr(slice_ir.upper, native)
            upper = self._box_value(upper_expr, upper_type)
        if slice_ir.step is not None:
            step_expr, step_type = self._emit_expr(slice_ir.step, native)
            step = self._box_value(step_expr, step_type)

        return f"mp_obj_new_slice({lower}, {upper}, {step})", "mp_obj_t"

    def _emit_class_instantiation(
        self, inst: ClassInstantiationIR, native: bool = False
    ) -> tuple[str, str]:
        args = []
        for arg in inst.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            args.append(self._box_value(arg_expr, arg_type))
        args_str = ", ".join(args)
        n_args = len(args)
        return (
            f"{inst.c_class_name}_make_new(&{inst.c_class_name}_type, {n_args}, 0, (const mp_obj_t[]){{{args_str}}})",
            "mp_obj_t",
        )

    def _emit_self_attr(self, attr: SelfAttrIR) -> tuple[str, str]:
        return f"self->{attr.attr_path}", attr.result_type.to_c_type_str()

    def _emit_param_attr(self, attr: ParamAttrIR) -> tuple[str, str]:
        expr = (
            f"(({attr.class_c_name}_obj_t *)MP_OBJ_TO_PTR({attr.c_param_name}))->{attr.attr_path}"
        )
        return expr, attr.result_type.to_c_type_str()

    def _emit_self_method_call(
        self, call: SelfMethodCallIR, native: bool = False
    ) -> tuple[str, str]:
        args = ["self"]
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            if self._should_unbox_self_method_args(call, native):
                args.append(self._unbox_if_needed(arg_expr, arg_type))
            else:
                args.append(arg_expr)
        args_str = ", ".join(args)
        return f"{call.c_method_name}_native({args_str})", call.return_type.to_c_type_str()

    def _emit_super_call(self, call: SuperCallIR, native: bool = False) -> tuple[str, str]:
        if call.is_init:
            boxed_args = []
            for arg in call.args:
                arg_expr, arg_type = self._emit_expr(arg, native)
                boxed_args.append(self._box_value(arg_expr, arg_type))

            total_args = len(boxed_args) + 1
            if total_args <= 3:
                args = ["MP_OBJ_FROM_PTR(self)"] + boxed_args
                args_str = ", ".join(args)
                return f"({call.parent_method_c_name}_mp({args_str}), mp_const_none)", "mp_obj_t"

            args_str = ", ".join(["MP_OBJ_FROM_PTR(self)"] + boxed_args)
            return (
                f"({call.parent_method_c_name}_mp({total_args}, (const mp_obj_t[]){{{args_str}}}), mp_const_none)",
                "mp_obj_t",
            )

        native_args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            native_args.append(
                self._unbox_if_needed(arg_expr, arg_type, arg.ir_type.to_c_type_str())
            )
        args_str = ", ".join(native_args)
        return (
            f"{call.parent_method_c_name}_native(({call.parent_c_name}_obj_t *)self{', ' if args_str else ''}{args_str})",
            call.return_type.to_c_type_str(),
        )



    def _emit_module_call(self, call: ModuleCallIR, native: bool = False) -> tuple[str, str]:
        """Emit C code for calling a function on an imported module.

        Generated C pattern:
            mp_obj_t _mod = mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
            mp_obj_t _fn = mp_load_attr(_mod, MP_QSTR_sqrt);
            mp_obj_t result = mp_call_function_1(_fn, arg);
        """
        mod_name = call.module_name
        func_name = call.func_name

        # Build boxed args
        boxed_args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            boxed_args.append(self._box_value(arg_expr, arg_type))

        # Emit inline expression using compound statement expression (GCC extension)
        # For cleaner code, use sequential calls:
        n_args = len(boxed_args)
        if n_args == 0:
            return (
                f"mp_call_function_0("
                f"mp_load_attr("
                f"mp_import_name(MP_QSTR_{mod_name}, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)), "
                f"MP_QSTR_{func_name}))"
            ), "mp_obj_t"
        elif n_args == 1:
            return (
                f"mp_call_function_1("
                f"mp_load_attr("
                f"mp_import_name(MP_QSTR_{mod_name}, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)), "
                f"MP_QSTR_{func_name}), "
                f"{boxed_args[0]})"
            ), "mp_obj_t"
        elif n_args == 2:
            return (
                f"mp_call_function_2("
                f"mp_load_attr("
                f"mp_import_name(MP_QSTR_{mod_name}, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)), "
                f"MP_QSTR_{func_name}), "
                f"{boxed_args[0]}, {boxed_args[1]})"
            ), "mp_obj_t"
        else:
            args_str = ", ".join(boxed_args)
            return (
                f"mp_call_function_n_kw("
                f"mp_load_attr("
                f"mp_import_name(MP_QSTR_{mod_name}, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)), "
                f"MP_QSTR_{func_name}), "
                f"{n_args}, 0, (const mp_obj_t[]){{{args_str}}})"
            ), "mp_obj_t"

    def _emit_module_attr(self, attr: ModuleAttrIR) -> tuple[str, str]:
        """Emit C code for accessing an attribute on an imported module.

        Generated C pattern:
            mp_obj_t result = mp_load_attr(
                mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                MP_QSTR_pi);
        """
        return (
            f"mp_load_attr("
            f"mp_import_name(MP_QSTR_{attr.module_name}, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)), "
            f"MP_QSTR_{attr.attr_name})"
        ), "mp_obj_t"

    def _box_value(self, expr: str, expr_type: str) -> str:
        if expr_type == "mp_int_t":
            return f"mp_obj_new_int({expr})"
        elif expr_type == "mp_float_t":
            return f"mp_obj_new_float({expr})"
        elif expr_type == "bool":
            return f"({expr} ? mp_const_true : mp_const_false)"
        return expr

    def _unbox_if_needed(self, expr: str, expr_type: str, target_type: str = "mp_int_t") -> str:
        if expr_type == "mp_obj_t" and target_type != "mp_obj_t":
            if target_type == "mp_float_t":
                return f"mp_get_float_checked({expr})"
            else:
                return f"mp_obj_get_int({expr})"
        return expr

    def _unbox_expr(self, expr: str, target_type: str) -> str:
        if target_type == "mp_int_t":
            return f"mp_obj_get_int({expr})"
        elif target_type == "mp_float_t":
            return f"mp_get_float_checked({expr})"
        elif target_type == "bool":
            return f"mp_obj_is_true({expr})"
        return expr


class FunctionEmitter(BaseEmitter):
    """Emits C code from FuncIR."""

    def __init__(self, func_ir: FuncIR):
        self.func_ir = func_ir
        super().__init__(func_ir.max_temp)

    def emit(self) -> tuple[str, str]:
        c_sig, obj_def = self._emit_signature()
        body_lines = self._emit_unbox_arguments()
        if body_lines:
            body_lines.append("")

        for stmt_ir in self.func_ir.body:
            body_lines.extend(self._emit_statement(stmt_ir))

        needs_fallthrough_return = True
        if self.func_ir.body and isinstance(self.func_ir.body[-1], ReturnIR):
            needs_fallthrough_return = False

        if needs_fallthrough_return:
            body_lines.append("    return mp_const_none;")

        func_code = c_sig + " {\n" + "\n".join(body_lines) + "\n}\n" + obj_def
        return func_code, obj_def

    def _emit_signature(self) -> tuple[str, str]:
        num_args = len(self.func_ir.params)
        arg_names = [p[0] for p in self.func_ir.params]

        if self.func_ir.has_star_kwargs:
            min_args = self.func_ir.num_required_args
            return (
                f"static mp_obj_t {self.func_ir.c_name}(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args)",
                f"MP_DEFINE_CONST_FUN_OBJ_KW({self.func_ir.c_name}_obj, {min_args}, {self.func_ir.c_name});",
            )

        if self.func_ir.has_star_args:
            min_args = self.func_ir.num_required_args
            return (
                f"static mp_obj_t {self.func_ir.c_name}(size_t n_args, const mp_obj_t *args)",
                f"MP_DEFINE_CONST_FUN_OBJ_VAR({self.func_ir.c_name}_obj, {min_args}, {self.func_ir.c_name});",
            )

        if self.func_ir.has_defaults:
            min_args = self.func_ir.num_required_args
            return (
                f"static mp_obj_t {self.func_ir.c_name}(size_t n_args, const mp_obj_t *args)",
                f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({self.func_ir.c_name}_obj, {min_args}, {num_args}, {self.func_ir.c_name});",
            )

        if num_args == 0:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(void)",
                f"MP_DEFINE_CONST_FUN_OBJ_0({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        elif num_args == 1:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(mp_obj_t {arg_names[0]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_1({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        elif num_args == 2:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_2({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        elif num_args == 3:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj, mp_obj_t {arg_names[2]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_3({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        else:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(size_t n_args, const mp_obj_t *args)",
                f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({self.func_ir.c_name}_obj, {num_args}, {num_args}, {self.func_ir.c_name});",
            )

    def _emit_unbox_arguments(self) -> list[str]:
        lines = []
        num_args = len(self.func_ir.params)
        has_defaults = self.func_ir.has_defaults
        has_star_args = self.func_ir.has_star_args
        has_star_kwargs = self.func_ir.has_star_kwargs

        args_array = "pos_args" if has_star_kwargs else "args"

        for i, (arg_name, _) in enumerate(self.func_ir.params):
            c_arg_name = sanitize_name(arg_name)
            c_type_str = (
                self.func_ir.arg_types[i] if i < len(self.func_ir.arg_types) else "mp_obj_t"
            )

            if has_star_kwargs or has_star_args or has_defaults:
                src = f"{args_array}[{i}]"
                default_arg = self.func_ir.defaults.get(i)

                if default_arg is not None and default_arg.c_expr is not None:
                    default_c = self._get_unboxed_default(default_arg, c_type_str)
                    if c_type_str == "mp_int_t":
                        lines.append(
                            f"    mp_int_t {c_arg_name} = (n_args > {i}) ? mp_obj_get_int({src}) : {default_c};"
                        )
                    elif c_type_str == "mp_float_t":
                        lines.append(
                            f"    mp_float_t {c_arg_name} = (n_args > {i}) ? mp_get_float_checked({src}) : {default_c};"
                        )
                    elif c_type_str == "bool":
                        lines.append(
                            f"    bool {c_arg_name} = (n_args > {i}) ? mp_obj_is_true({src}) : {default_c};"
                        )
                    else:
                        lines.append(
                            f"    mp_obj_t {c_arg_name} = (n_args > {i}) ? {src} : {default_arg.c_expr};"
                        )
                else:
                    if c_type_str == "mp_int_t":
                        lines.append(f"    mp_int_t {c_arg_name} = mp_obj_get_int({src});")
                    elif c_type_str == "mp_float_t":
                        lines.append(f"    mp_float_t {c_arg_name} = mp_get_float_checked({src});")
                    elif c_type_str == "bool":
                        lines.append(f"    bool {c_arg_name} = mp_obj_is_true({src});")
                    else:
                        lines.append(f"    mp_obj_t {c_arg_name} = {src};")
            else:
                src = f"{arg_name}_obj" if num_args <= 3 else f"args[{i}]"
                if c_type_str == "mp_int_t":
                    lines.append(f"    mp_int_t {c_arg_name} = mp_obj_get_int({src});")
                elif c_type_str == "mp_float_t":
                    lines.append(f"    mp_float_t {c_arg_name} = mp_get_float_checked({src});")
                elif c_type_str == "bool":
                    lines.append(f"    bool {c_arg_name} = mp_obj_is_true({src});")
                else:
                    lines.append(f"    mp_obj_t {c_arg_name} = {src};")

        if has_star_args:
            star_args_name = sanitize_name(self.func_ir.star_args.name)
            # Prefix with _star_ to avoid conflict with C parameter 'args'
            c_star_args_name = f"_star_{star_args_name}"
            lines.append(
                f"    mp_obj_t {c_star_args_name} = mp_obj_new_tuple(n_args > {num_args} ? n_args - {num_args} : 0, n_args > {num_args} ? {args_array} + {num_args} : NULL);"
            )

        if has_star_kwargs:
            star_kwargs_name = sanitize_name(self.func_ir.star_kwargs.name)
            # Prefix with _star_ to avoid conflict with C parameter 'kw_args'
            c_star_kwargs_name = f"_star_{star_kwargs_name}"
            lines.append(
                f"    mp_obj_t {c_star_kwargs_name} = mp_obj_new_dict(kw_args ? kw_args->used : 0);"
            )
            lines.append("    if (kw_args) {")
            lines.append("        for (size_t i = 0; i < kw_args->alloc; i++) {")
            lines.append("            if (mp_map_slot_is_filled(kw_args, i)) {")
            lines.append(
                f"                mp_obj_dict_store({c_star_kwargs_name}, kw_args->table[i].key, kw_args->table[i].value);"
            )
            lines.append("            }")
            lines.append("        }")
            lines.append("    }")

        return lines

    def _get_unboxed_default(self, default_arg, c_type_str: str) -> str:
        """Get the unboxed C literal for a default value."""
        val = default_arg.value
        if c_type_str == "mp_int_t":
            return str(int(val)) if isinstance(val, (int, float)) else "0"
        elif c_type_str == "mp_float_t":
            return str(float(val)) if isinstance(val, (int, float)) else "0.0"
        elif c_type_str == "bool":
            return "true" if val else "false"
        return default_arg.c_expr or "mp_const_none"

    def _emit_return(self, stmt: ReturnIR, native: bool = False) -> list[str]:
        del native
        lines = self._emit_prelude(stmt.prelude)

        if stmt.value is None:
            if self._nlr_stack:
                lines.append("        nlr_pop();")
            lines.append("    return mp_const_none;")
            return lines

        expr, expr_type = self._emit_expr(stmt.value)

        if isinstance(stmt.value, NameIR):
            var_name = stmt.value.py_name
            if var_name in self.func_ir.rtuple_types:
                rtuple = self.func_ir.rtuple_types[var_name]
                arity = rtuple.arity
                items_parts = []
                for i, el_type in enumerate(rtuple.element_types):
                    if el_type == CType.MP_FLOAT_T:
                        items_parts.append(f"mp_obj_new_float({expr}.f{i})")
                    else:
                        items_parts.append(f"mp_obj_new_int({expr}.f{i})")
                items = ", ".join(items_parts)
                lines.append(f"    mp_obj_t _ret_items[] = {{{items}}};")
                if self._nlr_stack:
                    lines.append("        nlr_pop();")
                lines.append(f"    return mp_obj_new_tuple({arity}, _ret_items);")
                return lines

        if self._nlr_stack:
            ret_tmp = self._fresh_temp()
            if expr_type == "mp_obj_t" or self.func_ir.return_type == CType.MP_OBJ_T:
                lines.append(f"        mp_obj_t {ret_tmp} = {expr};")
            elif self.func_ir.return_type == CType.MP_FLOAT_T or expr_type == "mp_float_t":
                lines.append(f"        mp_obj_t {ret_tmp} = mp_obj_new_float({expr});")
            elif self.func_ir.return_type == CType.MP_INT_T or expr_type == "mp_int_t":
                lines.append(f"        mp_obj_t {ret_tmp} = mp_obj_new_int({expr});")
            elif self.func_ir.return_type == CType.BOOL:
                lines.append(
                    f"        mp_obj_t {ret_tmp} = {expr} ? mp_const_true : mp_const_false;"
                )
            else:
                lines.append(f"        mp_obj_t {ret_tmp} = {expr};")
            lines.append("        nlr_pop();")
            lines.append(f"        return {ret_tmp};")
        else:
            if expr_type == "mp_obj_t" or self.func_ir.return_type == CType.MP_OBJ_T:
                lines.append(f"    return {expr};")
            elif self.func_ir.return_type == CType.MP_FLOAT_T or expr_type == "mp_float_t":
                lines.append(f"    return mp_obj_new_float({expr});")
            elif self.func_ir.return_type == CType.MP_INT_T or expr_type == "mp_int_t":
                lines.append(f"    return mp_obj_new_int({expr});")
            elif self.func_ir.return_type == CType.BOOL:
                lines.append(f"    return {expr} ? mp_const_true : mp_const_false;")
            else:
                lines.append(f"    return {expr};")
        return lines

    def _emit_ann_assign(self, stmt: AnnAssignIR, native: bool = False) -> list[str]:
        del native
        if stmt.c_type.startswith("rtuple_") and stmt.prelude:
            tuple_new = next((p for p in stmt.prelude if isinstance(p, TupleNewIR)), None)
            if tuple_new:
                items_c = []
                for item in tuple_new.items:
                    expr, _ = self._emit_expr(item)
                    items_c.append(expr)
                items_str = ", ".join(items_c)
                return [f"    {stmt.c_type} {stmt.c_target} = {{{items_str}}};"]

        lines = self._emit_prelude(stmt.prelude)

        if stmt.value is not None:
            expr, expr_type = self._emit_expr(stmt.value)

            if stmt.c_type.startswith("rtuple_") and expr_type == "mp_obj_t":
                rtuple = self.func_ir.rtuple_types.get(stmt.target)
                if rtuple:
                    return self._emit_rtuple_unbox(stmt.c_type, stmt.c_target, expr, rtuple)

            expr = self._unbox_if_needed(expr, expr_type, stmt.c_type)
            lines.append(f"    {stmt.c_type} {stmt.c_target} = {expr};")
        else:
            if stmt.c_type == "mp_int_t":
                lines.append(f"    {stmt.c_type} {stmt.c_target} = 0;")
            elif stmt.c_type == "mp_float_t":
                lines.append(f"    {stmt.c_type} {stmt.c_target} = 0.0;")
            elif stmt.c_type == "bool":
                lines.append(f"    {stmt.c_type} {stmt.c_target} = false;")
            elif stmt.c_type.startswith("rtuple_"):
                lines.append(f"    {stmt.c_type} {stmt.c_target} = {{0}};")
            else:
                lines.append(f"    {stmt.c_type} {stmt.c_target} = mp_const_none;")
        return lines

    def _emit_rtuple_unbox(self, c_type: str, target: str, src_expr: str, rtuple) -> list[str]:
        lines = []
        temp = self._fresh_temp()
        lines.append(f"    mp_obj_tuple_t *{temp} = MP_OBJ_TO_PTR({src_expr});")
        items = []
        for i, el_type in enumerate(rtuple.element_types):
            if el_type == CType.MP_FLOAT_T:
                items.append(f"mp_obj_get_float({temp}->items[{i}])")
            elif el_type == CType.BOOL:
                items.append(f"mp_obj_is_true({temp}->items[{i}])")
            elif el_type == CType.MP_OBJ_T:
                items.append(f"{temp}->items[{i}]")
            else:
                items.append(f"mp_obj_get_int({temp}->items[{i}])")
        lines.append(f"    {c_type} {target} = {{ {', '.join(items)} }};")
        return lines

    def _emit_aug_assign(self, stmt: AugAssignIR, native: bool = False) -> list[str]:
        del native
        lines = self._emit_prelude(stmt.prelude)
        right, right_type = self._emit_expr(stmt.value)

        if stmt.target_c_type == "mp_obj_t":
            boxed_expr = self._box_value(right, right_type)
            op_map = {
                "+=": "MP_BINARY_OP_INPLACE_ADD",
                "-=": "MP_BINARY_OP_INPLACE_SUBTRACT",
                "*=": "MP_BINARY_OP_INPLACE_MULTIPLY",
                "/=": "MP_BINARY_OP_INPLACE_TRUE_DIVIDE",
                "//=": "MP_BINARY_OP_INPLACE_FLOOR_DIVIDE",
                "%=": "MP_BINARY_OP_INPLACE_MODULO",
                "&=": "MP_BINARY_OP_INPLACE_AND",
                "|=": "MP_BINARY_OP_INPLACE_OR",
                "^=": "MP_BINARY_OP_INPLACE_XOR",
                "<<=": "MP_BINARY_OP_INPLACE_LSHIFT",
                ">>=": "MP_BINARY_OP_INPLACE_RSHIFT",
            }
            mp_op = op_map.get(stmt.op, "MP_BINARY_OP_INPLACE_ADD")
            lines.append(
                f"    {stmt.c_target} = mp_binary_op({mp_op}, {stmt.c_target}, {boxed_expr});"
            )
        else:
            right = self._unbox_if_needed(right, right_type, "mp_int_t")
            lines.append(f"    {stmt.c_target} {stmt.op} {right};")
        return lines


class MethodEmitter(BaseEmitter):
    """Emits C code for class methods from MethodIR + body IR."""

    def __init__(self, method_ir: MethodIR, class_ir: ClassIR):
        self.method_ir = method_ir
        self.class_ir = class_ir
        super().__init__(method_ir.max_temp)

    def _should_unbox_self_method_args(self, call: SelfMethodCallIR, native: bool) -> bool:
        del call
        return native

    def _emit_self_attr(self, attr: SelfAttrIR) -> tuple[str, str]:
        """Override to constant-fold Final field access."""
        # Check if this is a Final field with a known literal value
        for fld in self.class_ir.get_all_fields():
            if fld.name == attr.attr_name and fld.is_final and fld.final_value is not None:
                val = fld.final_value
                if isinstance(val, bool):
                    return ("true" if val else "false"), "bool"
                elif isinstance(val, int):
                    return str(val), "mp_int_t"
                elif isinstance(val, float):
                    return str(val), "mp_float_t"
                elif isinstance(val, str):
                    escaped = val.replace('"', '\\"')
                    return (
                        f'mp_obj_new_str("{escaped}", {len(val)})',
                        "mp_obj_t",
                    )
        return f"self->{attr.attr_path}", attr.result_type.to_c_type_str()

    def emit_native(self, body: list[StmtIR]) -> str:
        method_ir = self.method_ir
        class_ir = self.class_ir

        params: list[str] = []
        if not method_ir.is_static and not method_ir.is_classmethod:
            params.append(f"{class_ir.c_name}_obj_t *self")
        for param_name, param_type in method_ir.params:
            params.append(f"{param_type.to_c_type_str()} {param_name}")
        params_str = ", ".join(params) if params else "void"

        ret_type = method_ir.return_type.to_c_type_str()
        lines = [f"static {ret_type} {method_ir.c_name}_native({params_str}) {{"]

        for stmt_ir in body:
            lines.extend(self._emit_statement(stmt_ir, native=True))

        if method_ir.return_type == CType.VOID:
            if not any("return" in line for line in lines):
                lines.append("    return;")

        lines.append("}")
        return "\n".join(lines)

    def emit_mp_wrapper(self, body: list[StmtIR] | None = None) -> str:
        method_ir = self.method_ir
        class_ir = self.class_ir

        num_args = len(method_ir.params) + (
            0 if (method_ir.is_static or method_ir.is_classmethod) else 1
        )
        obj_name = (
            f"{method_ir.c_name}_fun_obj"
            if (method_ir.is_static or method_ir.is_classmethod)
            else f"{method_ir.c_name}_obj"
        )

        if num_args == 0:
            sig = f"static mp_obj_t {method_ir.c_name}_mp(void)"
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_0({obj_name}, {method_ir.c_name}_mp);"
        elif num_args == 1:
            arg0 = "arg0_obj" if (method_ir.is_static or method_ir.is_classmethod) else "self_in"
            sig = f"static mp_obj_t {method_ir.c_name}_mp(mp_obj_t {arg0})"
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_1({obj_name}, {method_ir.c_name}_mp);"
        elif num_args == 2:
            if method_ir.is_static or method_ir.is_classmethod:
                sig = f"static mp_obj_t {method_ir.c_name}_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj)"
            else:
                sig = f"static mp_obj_t {method_ir.c_name}_mp(mp_obj_t self_in, mp_obj_t arg0_obj)"
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_2({obj_name}, {method_ir.c_name}_mp);"
        elif num_args == 3:
            if method_ir.is_static or method_ir.is_classmethod:
                sig = (
                    f"static mp_obj_t {method_ir.c_name}_mp(mp_obj_t arg0_obj, mp_obj_t arg1_obj, "
                    "mp_obj_t arg2_obj)"
                )
            else:
                sig = (
                    f"static mp_obj_t {method_ir.c_name}_mp(mp_obj_t self_in, mp_obj_t arg0_obj, "
                    "mp_obj_t arg1_obj)"
                )
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_3({obj_name}, {method_ir.c_name}_mp);"
        else:
            sig = f"static mp_obj_t {method_ir.c_name}_mp(size_t n_args, const mp_obj_t *args)"
            obj_def = (
                f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({obj_name}, {num_args}, {num_args}, "
                f"{method_ir.c_name}_mp);"
            )

        lines = [sig + " {"]

        if not method_ir.is_static and not method_ir.is_classmethod:
            if num_args <= 3:
                lines.append(f"    {class_ir.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
            else:
                lines.append(f"    {class_ir.c_name}_obj_t *self = MP_OBJ_TO_PTR(args[0]);")

        for i, (param_name, param_type) in enumerate(method_ir.params):
            if num_args <= 3:
                src = f"arg{i}_obj"
            else:
                src_index = i if (method_ir.is_static or method_ir.is_classmethod) else i + 1
                src = f"args[{src_index}]"

            if param_type == CType.MP_INT_T:
                lines.append(f"    mp_int_t {param_name} = mp_obj_get_int({src});")
            elif param_type == CType.MP_FLOAT_T:
                lines.append(f"    mp_float_t {param_name} = mp_obj_get_float({src});")
            elif param_type == CType.BOOL:
                lines.append(f"    bool {param_name} = mp_obj_is_true({src});")
            else:
                lines.append(f"    mp_obj_t {param_name} = {src};")

        if (
            method_ir.is_static
            or method_ir.is_classmethod
            or method_ir.is_property
            or method_ir.is_final
            or (method_ir.is_virtual and not method_ir.is_special)
        ):
            args_list = [p[0] for p in method_ir.params]
            if not method_ir.is_static and not method_ir.is_classmethod:
                args_list.insert(0, "self")
            args_str = ", ".join(args_list)

            if method_ir.return_type == CType.VOID:
                lines.append(f"    {method_ir.c_name}_native({args_str});")
                lines.append("    return mp_const_none;")
            elif method_ir.return_type == CType.MP_INT_T:
                lines.append(f"    return mp_obj_new_int({method_ir.c_name}_native({args_str}));")
            elif method_ir.return_type == CType.MP_FLOAT_T:
                lines.append(f"    return mp_obj_new_float({method_ir.c_name}_native({args_str}));")
            elif method_ir.return_type == CType.BOOL:
                lines.append(
                    f"    return {method_ir.c_name}_native({args_str}) ? mp_const_true : mp_const_false;"
                )
            else:
                lines.append(f"    return {method_ir.c_name}_native({args_str});")
        else:
            if body:
                for stmt_ir in body:
                    lines.extend(self._emit_statement(stmt_ir, native=False))

            if method_ir.return_type == CType.VOID:
                if not any("return" in line for line in lines):
                    lines.append("    return mp_const_none;")

        lines.append("}")
        lines.append(obj_def)
        return "\n".join(lines)

    def _emit_return(self, stmt: ReturnIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)

        if stmt.value is None:
            if self._nlr_stack:
                lines.append("        nlr_pop();")
            if native:
                lines.append("    return;")
            else:
                lines.append("    return mp_const_none;")
            return lines

        expr, expr_type = self._emit_expr(stmt.value, native)

        # In methods, "return self" should return self_in (the original mp_obj_t)
        # not the struct pointer "self"
        if expr == "self" and not native:
            if self._nlr_stack:
                lines.append("        nlr_pop();")
                lines.append("        return self_in;")
            else:
                lines.append("    return self_in;")
            return lines


        if self._nlr_stack:
            ret_tmp = self._fresh_temp()
            if native:
                ret_type = self.method_ir.return_type.to_c_type_str()
                expr = self._unbox_if_needed(expr, expr_type, ret_type)
                lines.append(f"        {ret_type} {ret_tmp} = {expr};")
            else:
                if expr_type == "mp_int_t":
                    lines.append(f"        mp_obj_t {ret_tmp} = mp_obj_new_int({expr});")
                elif expr_type == "mp_float_t":
                    lines.append(f"        mp_obj_t {ret_tmp} = mp_obj_new_float({expr});")
                elif expr_type == "bool":
                    lines.append(
                        f"        mp_obj_t {ret_tmp} = {expr} ? mp_const_true : mp_const_false;"
                    )
                else:
                    lines.append(f"        mp_obj_t {ret_tmp} = {expr};")
            lines.append("        nlr_pop();")
            lines.append(f"        return {ret_tmp};")
        else:
            if native:
                ret_type = self.method_ir.return_type.to_c_type_str()
                expr = self._unbox_if_needed(expr, expr_type, ret_type)
                lines.append(f"    return {expr};")
            else:
                if expr_type == "mp_int_t":
                    lines.append(f"    return mp_obj_new_int({expr});")
                elif expr_type == "mp_float_t":
                    lines.append(f"    return mp_obj_new_float({expr});")
                elif expr_type == "bool":
                    lines.append(f"    return {expr} ? mp_const_true : mp_const_false;")
                else:
                    lines.append(f"    return {expr};")
        return lines

    def _emit_ann_assign(self, stmt: AnnAssignIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)

        if stmt.value is not None:
            expr, expr_type = self._emit_expr(stmt.value, native)
            expr = self._unbox_if_needed(expr, expr_type, stmt.c_type)
            if stmt.is_new_var:
                lines.append(f"    {stmt.c_type} {stmt.c_target} = {expr};")
            else:
                lines.append(f"    {stmt.c_target} = {expr};")
        elif stmt.is_new_var:
            if stmt.c_type == "mp_int_t":
                lines.append(f"    {stmt.c_type} {stmt.c_target} = 0;")
            elif stmt.c_type == "mp_float_t":
                lines.append(f"    {stmt.c_type} {stmt.c_target} = 0.0;")
            elif stmt.c_type == "bool":
                lines.append(f"    {stmt.c_type} {stmt.c_target} = false;")
            else:
                lines.append(f"    {stmt.c_type} {stmt.c_target} = mp_const_none;")
        return lines

    def _emit_attr_assign(self, stmt: AttrAssignIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        value_expr, value_type = self._emit_expr(stmt.value, native)

        field = next(
            (f for f, _ in self.class_ir.get_all_fields_with_path() if f.name == stmt.attr_name),
            None,
        )

        if native:
            lines.append(f"    self->{stmt.attr_path} = {value_expr};")
        else:
            if field:
                if field.c_type == CType.MP_INT_T and value_type != "mp_int_t":
                    lines.append(f"    self->{stmt.attr_path} = mp_obj_get_int({value_expr});")
                elif field.c_type == CType.MP_FLOAT_T and value_type != "mp_float_t":
                    lines.append(f"    self->{stmt.attr_path} = mp_obj_get_float({value_expr});")
                elif field.c_type == CType.BOOL and value_type != "bool":
                    lines.append(f"    self->{stmt.attr_path} = mp_obj_is_true({value_expr});")
                else:
                    lines.append(f"    self->{stmt.attr_path} = {value_expr};")
            else:
                lines.append(f"    self->{stmt.attr_path} = {value_expr};")
        return lines

    def _emit_self_aug_assign(self, stmt: SelfAugAssignIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.prelude)
        value_expr, value_type = self._emit_expr(stmt.value, native)
        if value_type == "mp_obj_t":
            value_expr = f"mp_obj_get_int({value_expr})"
        lines.append(f"    self->{stmt.attr_path} {stmt.op} {value_expr};")
        return lines
