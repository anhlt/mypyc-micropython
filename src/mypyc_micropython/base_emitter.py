"""
Base Emitter: Core emission logic for FuncIR -> C code.

This module contains the BaseEmitter class with shared emission logic
used by both FunctionEmitter and MethodEmitter.
"""

from __future__ import annotations

import re
from typing import assert_never

from .container_emitter import ContainerEmitter
from .ir import (
    AnnAssignIR,
    AssignIR,
    AttrAssignIR,
    AugAssignIR,
    BinOpIR,
    BreakIR,
    CallIR,
    ClassConstIR,
    ClassInstantiationIR,
    ClassVarIR,
    CLibCallIR,
    CLibEnumIR,
    CompareIR,
    ConstIR,
    ContinueIR,
    CType,
    DynamicCallIR,
    ExprStmtIR,
    ForIterIR,
    ForRangeIR,
    FuncIR,
    FuncRefIR,
    IfExprIR,
    IfIR,
    ImportedClassAttrIR,
    InstrNode,
    IRType,
    IsInstanceIR,
    LambdaIR,
    ModuleAttrIR,
    ModuleCallIR,
    ModuleRefIR,
    NameIR,
    ObjAttrAssignIR,
    ParamAttrIR,
    PassIR,
    PrintIR,
    RaiseIR,
    ReturnIR,
    SelfAttrIR,
    SelfAugAssignIR,
    SelfMethodCallIR,
    SelfMethodRefIR,
    SiblingClassInstantiationIR,
    SiblingModuleCallIR,
    SiblingModuleRefIR,
    SliceIR,
    StmtNode,
    SubscriptAssignIR,
    SubscriptIR,
    SuperCallIR,
    TempIR,
    TryIR,
    TupleUnpackIR,
    UnaryOpIR,
    ValueIR,
    ValueNode,
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


def _emit_dotted_module_import(module_name: str) -> str:
    """Generate C code for importing a (possibly dotted) module name.

    For simple names like 'math', generates:
        mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0))

    For dotted names like 'lvgl_mvu.program', generates chained mp_load_attr:
        mp_load_attr(
            mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
            MP_QSTR_program)
    """
    parts = module_name.split(".")
    # Import the root module
    expr = f"mp_import_name(MP_QSTR_{parts[0]}, mp_const_none, MP_OBJ_NEW_SMALL_INT(0))"
    # Chain mp_load_attr for each subsequent part
    for part in parts[1:]:
        expr = f"mp_load_attr({expr}, MP_QSTR_{part})"
    return expr


class BaseEmitter:
    func_ir: FuncIR  # Set by subclasses

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

    def _emit_return(self, stmt: ReturnIR, native: bool = False) -> list[str]:
        raise NotImplementedError

    def _emit_ann_assign(self, stmt: AnnAssignIR, native: bool = False) -> list[str]:
        raise NotImplementedError

    def emit(self) -> tuple[str, str]:
        raise NotImplementedError

    def emit_forward_declaration(self) -> str:
        raise NotImplementedError

    def _emit_statement(self, stmt: StmtNode, native: bool = False) -> list[str]:
        match stmt:
            case ReturnIR():
                return self._emit_return(stmt, native)
            case IfIR():
                return self._emit_if(stmt, native)
            case WhileIR():
                return self._emit_while(stmt, native)
            case ForRangeIR():
                return self._emit_for_range(stmt, native)
            case ForIterIR():
                return self._emit_for_iter(stmt, native)
            case TryIR():
                return self._emit_try(stmt, native)
            case RaiseIR():
                return self._emit_raise(stmt, native)
            case AssignIR():
                return self._emit_assign(stmt, native)
            case AnnAssignIR():
                return self._emit_ann_assign(stmt, native)
            case AugAssignIR():
                return self._emit_aug_assign(stmt, native)
            case SelfAugAssignIR():
                return self._emit_self_aug_assign(stmt, native)
            case SubscriptAssignIR():
                return self._emit_subscript_assign(stmt, native)
            case TupleUnpackIR():
                return self._emit_tuple_unpack(stmt, native)
            case AttrAssignIR():
                return self._emit_attr_assign(stmt, native)
            case ObjAttrAssignIR():
                return self._emit_obj_attr_assign(stmt, native)
            case ExprStmtIR():
                return self._emit_expr_stmt(stmt, native)
            case PrintIR():
                return self._emit_print(stmt, native)
            case BreakIR():
                if self._loop_depth > 0:
                    return ["    break;"]
                return ["    /* ERROR: break outside loop */"]
            case ContinueIR():
                if self._loop_depth > 0:
                    return ["    continue;"]
                return ["    /* ERROR: continue outside loop */"]
            case PassIR():
                return []
            case _:
                raise ValueError(f"Unhandled statement type in BaseEmitter: {type(stmt).__name__}")

    def _emit_if(self, stmt: IfIR, native: bool = False) -> list[str]:
        lines = self._emit_prelude(stmt.test_prelude)
        cond, cond_type = self._emit_expr(stmt.test, native)
        cond = self._to_bool_expr(cond, cond_type)
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
        cond, cond_type = self._emit_expr(stmt.test, native)
        cond = self._to_bool_expr(cond, cond_type)
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
            # nlr.ret_val is a void* pointing to the exception object
            # Access the type field directly via cast, matching MicroPython's pattern
            lines.append(f"        mp_obj_base_t *{exc_var} = (mp_obj_base_t *){nlr_buf}.ret_val;")

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
                        f"MP_OBJ_FROM_PTR({exc_var}->type), "
                        f"MP_OBJ_FROM_PTR({mp_type}))"
                    )
                    if i == 0:
                        lines.append(f"        if ({cond}) {{")
                    else:
                        lines.append(f"        }} else if ({cond}) {{")

                if handler.exc_var and handler.c_exc_var:
                    # Convert base pointer back to mp_obj_t for user access
                    lines.append(
                        f"            mp_obj_t {handler.c_exc_var} = MP_OBJ_FROM_PTR({exc_var});"
                    )

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
                    f'    mp_raise_msg_varg({mp_type}, MP_ERROR_TEXT("%s"), mp_obj_str_get_str({msg_expr}));'
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

    def _emit_obj_attr_assign(self, stmt: ObjAttrAssignIR, native: bool = False) -> list[str]:
        """Emit attribute assignment on a local variable: obj.attr = value.

        For native classes with known struct layout, use direct struct field
        access with raw (unboxed) values -- matching ``_emit_attr_assign``.
        Otherwise use mp_store_attr with boxed values.
        """
        lines = self._emit_prelude(stmt.prelude)
        value_expr, value_type = self._emit_expr(stmt.value, native)
        if stmt.obj_class is not None:
            # Known native class -- cast and access struct field directly.
            # Use raw value_expr (not boxed) because struct fields store
            # native C types (mp_int_t, mp_obj_t, etc.).
            lines.append(
                f"    (({stmt.obj_class}_obj_t *)MP_OBJ_TO_PTR({stmt.obj_name}))"
                f"->{stmt.attr_path} = {value_expr};"
            )
        else:
            # Generic object -- use mp_store_attr (needs boxed mp_obj_t)
            boxed_value = self._box_value(value_expr, value_type)
            lines.append(
                f"    mp_store_attr({stmt.obj_name}, MP_QSTR_{stmt.attr_name}, {boxed_value});"
            )
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

    def _emit_prelude(self, prelude: list[InstrNode]) -> list[str]:
        return self._container_emitter.emit_prelude(prelude)

    def _emit_expr(self, value: ValueNode, native: bool = False) -> tuple[str, str]:
        match value:
            case ConstIR():
                return self._emit_const(value)
            case NameIR():
                return value.c_name, value.ir_type.to_c_type_str()
            case ClassConstIR():
                # Final class constant - use the pre-generated #define constant name
                return value.c_name, value.value_ctype.to_c_type_str()
            case ClassVarIR():
                # ClassVar - runtime attribute lookup on class type
                expr = f"mp_load_attr(MP_OBJ_FROM_PTR(&{value.class_c_name}_type), MP_QSTR_{value.attr_name})"
                return expr, "mp_obj_t"
            case FuncRefIR():
                return f"MP_OBJ_FROM_PTR(&{value.c_name}_obj)", "mp_obj_t"
            case LambdaIR():
                if value.captured_vars:
                    captured_parts = [f"MP_OBJ_FROM_PTR(&{value.c_name}_obj)"]
                    for var_name, c_type in value.captured_vars:
                        # Box captured variables based on their type
                        if c_type == CType.MP_INT_T:
                            captured_parts.append(f"mp_obj_new_int({var_name})")
                        elif c_type == CType.MP_FLOAT_T:
                            captured_parts.append(f"mp_obj_new_float({var_name})")
                        elif c_type == CType.BOOL:
                            captured_parts.append(f"mp_obj_new_bool({var_name})")
                        else:
                            # Already boxed (mp_obj_t)
                            captured_parts.append(var_name)
                    n_closed = len(value.captured_vars)
                    closed_arr = ", ".join(captured_parts[1:])
                    return (
                        f"mp_obj_new_closure(MP_OBJ_FROM_PTR(&{value.c_name}_obj), "
                        f"{n_closed}, (mp_obj_t[]){{ {closed_arr} }})"
                    ), "mp_obj_t"
                return f"MP_OBJ_FROM_PTR(&{value.c_name}_obj)", "mp_obj_t"
            case TempIR():
                return value.name, value.ir_type.to_c_type_str()
            case BinOpIR():
                return self._emit_binop(value, native)
            case UnaryOpIR():
                return self._emit_unaryop(value, native)
            case CompareIR():
                return self._emit_compare(value, native)
            case IsInstanceIR():
                return self._emit_isinstance(value)
            case CallIR():
                return self._emit_call(value, native)
            case IfExprIR():
                return self._emit_ifexp(value, native)
            case SubscriptIR():
                return self._emit_subscript(value, native)
            case SliceIR():
                return self._emit_slice(value, native)
            case ClassInstantiationIR():
                return self._emit_class_instantiation(value, native)
            case SelfAttrIR():
                return self._emit_self_attr(value)
            case SelfMethodRefIR():
                return self._emit_self_method_ref(value)
            case ParamAttrIR():
                return self._emit_param_attr(value)
            case SelfMethodCallIR():
                return self._emit_self_method_call(value, native)
            case SuperCallIR():
                return self._emit_super_call(value, native)
            case CLibCallIR():
                return self._emit_clib_call(value, native)
            case CLibEnumIR():
                return str(value.c_enum_value), "mp_int_t"
            case ModuleCallIR():
                return self._emit_module_call(value, native)
            case ModuleAttrIR():
                return self._emit_module_attr(value)
            case SiblingModuleCallIR():
                return self._emit_sibling_module_call(value, native)
            case SiblingClassInstantiationIR():
                return self._emit_sibling_class_instantiation(value, native)
            case DynamicCallIR():
                return self._emit_dynamic_call(value, native)
            case ModuleRefIR():
                return _emit_dotted_module_import(value.module_name), "mp_obj_t"
            case SiblingModuleRefIR():
                raise ValueError(
                    f"SiblingModuleRefIR(c_prefix='{value.c_prefix}') cannot be emitted "
                    "as a standalone expression value. Sibling module references should "
                    "only appear as receivers in SiblingModuleCallIR or "
                    "SiblingClassInstantiationIR, not as first-class values."
                )
            case ImportedClassAttrIR():
                return self._emit_imported_class_attr(value)
            case _:
                assert_never(value)

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
        if op.op == "!":
            # Boolean not: convert mp_obj_t to C bool first
            bool_expr = self._to_bool_expr(operand, op_type)
            return f"(!{bool_expr})", "bool"
        result_type = op_type
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
            elif c_op in ("is", "is not"):
                # Identity comparison - use pointer comparison without unboxing
                boxed_prev = self._box_value(prev, prev_type)
                boxed_right = self._box_value(right, right_type)
                if c_op == "is":
                    parts.append(f"({boxed_prev} == {boxed_right})")
                else:
                    parts.append(f"({boxed_prev} != {boxed_right})")
            else:
                # Regular comparison operators (==, !=, <, <=, >, >=)
                if prev_type == "mp_obj_t" or right_type == "mp_obj_t":
                    # Both sides are boxed mp_obj_t with no concrete native type
                    # -> use mp_obj_equal / mp_binary_op instead of unboxing to int
                    both_boxed = prev_type == "mp_obj_t" and right_type == "mp_obj_t"
                    if both_boxed:
                        boxed_prev = self._box_value(prev, prev_type)
                        boxed_right = self._box_value(right, right_type)
                        if c_op == "==":
                            parts.append(f"mp_obj_equal({boxed_prev}, {boxed_right})")
                        elif c_op == "!=":
                            parts.append(f"(!mp_obj_equal({boxed_prev}, {boxed_right}))")
                        else:
                            # Ordering: <, <=, >, >=
                            binary_op_map = {
                                "<": "MP_BINARY_OP_LESS",
                                "<=": "MP_BINARY_OP_LESS_EQUAL",
                                ">": "MP_BINARY_OP_MORE",
                                ">=": "MP_BINARY_OP_MORE_EQUAL",
                            }
                            mp_op = binary_op_map[c_op]
                            parts.append(
                                f"mp_obj_is_true(mp_binary_op({mp_op}, {boxed_prev}, {boxed_right}))"
                            )
                    else:
                        target = right_type if right_type != "mp_obj_t" else prev_type
                        prev = self._unbox_if_needed(prev, prev_type, target)
                        right = self._unbox_if_needed(right, right_type, target)
                        parts.append(f"({prev} {c_op} {right})")
                else:
                    parts.append(f"({prev} {c_op} {right})")

            prev = right
            prev_type = right_type

        if len(parts) > 1:
            return "(" + " && ".join(parts) + ")", "bool"
        return parts[0], "bool"

    def _emit_isinstance(self, node: IsInstanceIR) -> tuple[str, str]:
        """Emit isinstance(obj, ClassName) as mp_obj_is_type() check."""
        obj_expr, obj_type = self._emit_expr(node.obj)
        boxed_obj = self._box_value(obj_expr, obj_type)
        return f"mp_obj_is_type({boxed_obj}, &{node.c_type_name})", "bool"

    def _emit_call(self, call: CallIR, native: bool = False) -> tuple[str, str]:
        if call.is_builtin:
            return self._emit_builtin_call(call, native)

        args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            args.append(self._box_value(arg_expr, arg_type))

        # Functions with 4+ parameters use VAR_BETWEEN calling convention
        # They expect (size_t n_args, const mp_obj_t *args) signature
        if len(args) > 3:
            args_str = ", ".join(args)
            return f"{call.c_func_name}({len(args)}, (const mp_obj_t[]){{{args_str}}})", "mp_obj_t"

        args_str = ", ".join(args)
        return f"{call.c_func_name}({args_str})", "mp_obj_t"

    def _emit_dynamic_call(self, call: DynamicCallIR, native: bool = False) -> tuple[str, str]:
        """Emit a dynamic call to a callable stored in a local variable."""
        del native  # Always use mp_call_function_n

        # Build args list, boxing as needed
        args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, False)
            args.append(self._box_value(arg_expr, arg_type))

        # Build kwargs (interleaved: key, value, key, value, ...)
        boxed_kwargs = []
        for kw_name, kw_val in call.kwargs:
            boxed_kwargs.append(f"MP_OBJ_NEW_QSTR(MP_QSTR_{kw_name})")
            kw_expr, kw_type = self._emit_expr(kw_val, False)
            boxed_kwargs.append(self._box_value(kw_expr, kw_type))

        n_args = len(args)
        n_kw = len(call.kwargs)
        callable_var = call.callable_var

        # If we have kwargs, must use mp_call_function_n_kw
        if n_kw > 0:
            all_args = args + boxed_kwargs
            args_str = ", ".join(all_args)
            return (
                f"mp_call_function_n_kw({callable_var}, "
                f"{n_args}, {n_kw}, (const mp_obj_t[]){{{args_str}}})"
            ), "mp_obj_t"

        if n_args == 0:
            return f"mp_call_function_0({callable_var})", "mp_obj_t"
        elif n_args == 1:
            return f"mp_call_function_1({callable_var}, {args[0]})", "mp_obj_t"
        elif n_args == 2:
            return f"mp_call_function_2({callable_var}, {args[0]}, {args[1]})", "mp_obj_t"
        else:
            # For 3+ args, use mp_call_function_n_kw
            args_str = ", ".join(args)
            return (
                f"mp_call_function_n_kw({callable_var}, {n_args}, 0, "
                f"(const mp_obj_t[]){{{args_str}}})"
            ), "mp_obj_t"

    def _emit_clib_call(self, call: CLibCallIR, native: bool = False) -> tuple[str, str]:
        args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            args.append(self._box_value(arg_expr, arg_type))
        args_str = ", ".join(args)
        if call.uses_var_args:
            n = len(args)
            call_expr = f"{call.c_wrapper_name}({n}, (const mp_obj_t[]){{{args_str}}})"
        else:
            call_expr = f"{call.c_wrapper_name}({args_str})"
        if call.is_void:
            return f"({call_expr}, mp_const_none)", "mp_obj_t"

        return call_expr, "mp_obj_t"

    def _emit_builtin_call(self, call: CallIR, native: bool = False) -> tuple[str, str]:
        del native
        func = call.builtin_kind
        args = [self._emit_expr(arg) for arg in call.args]

        if func == "abs" and args:
            a = args[0][0]
            return f"(({a}) < 0 ? -({a}) : ({a}))", "mp_int_t"
        elif func == "int" and args:
            arg_expr, arg_type = args[0]
            # If already mp_int_t, just cast; otherwise convert from mp_obj_t
            if arg_type == "mp_int_t":
                return f"((mp_int_t)({arg_expr}))", "mp_int_t"
            else:
                return f"mp_obj_get_int({arg_expr})", "mp_int_t"
        elif func == "float" and args:
            arg_expr, arg_type = args[0]
            # If already mp_float_t, just cast; otherwise convert from mp_obj_t
            if arg_type == "mp_float_t":
                return f"((mp_float_t)({arg_expr}))", "mp_float_t"
            else:
                return f"mp_obj_get_float({arg_expr})", "mp_float_t"
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
                boxed_iterable = self._box_value(args[0][0], args[0][1])
                if call.kwargs:
                    boxed_kwargs: list[str] = []
                    for kw_name, kw_val in call.kwargs:
                        kw_expr, kw_type = self._emit_expr(kw_val)
                        boxed_kwargs.append(f"MP_OBJ_NEW_QSTR(MP_QSTR_{kw_name})")
                        boxed_kwargs.append(self._box_value(kw_expr, kw_type))
                    all_args = ", ".join([boxed_iterable] + boxed_kwargs)
                    return (
                        f"mp_call_function_n_kw(mp_load_global(MP_QSTR_sorted) /* mp_builtin_sorted_obj */, 1, {len(call.kwargs)}, "
                        f"(const mp_obj_t[]){{{all_args}}})",
                        "mp_obj_t",
                    )
                return (
                    f"mp_call_function_1(mp_load_global(MP_QSTR_sorted) /* mp_builtin_sorted_obj */, {boxed_iterable})",
                    "mp_obj_t",
                )
        elif func == "id" and args:
            # id(obj) returns the memory address of the object as an integer
            arg_expr, arg_type = args[0]
            boxed = self._box_value(arg_expr, arg_type)
            return f"(mp_int_t)(uintptr_t)({boxed})", "mp_int_t"

        return "/* unsupported builtin */", "mp_obj_t"

    def _emit_ifexp(self, expr: IfExprIR, native: bool = False) -> tuple[str, str]:
        test, test_type = self._emit_expr(expr.test, native)
        test = self._to_bool_expr(test, test_type)
        body, body_type = self._emit_expr(expr.body, native)
        orelse, _ = self._emit_expr(expr.orelse, native)
        return f"(({test}) ? ({body}) : ({orelse}))", body_type

    def _emit_subscript(self, sub: SubscriptIR, native: bool = False) -> tuple[str, str]:
        value_expr, _ = self._emit_expr(sub.value, native)

        if sub.is_rtuple and sub.rtuple_index is not None:
            # Look up element type from RTuple metadata
            el_c_type = "mp_int_t"
            if isinstance(sub.value, NameIR):
                rtuple = self.func_ir.rtuple_types.get(sub.value.py_name)
                if rtuple and sub.rtuple_index < len(rtuple.element_types):
                    el_c_type = rtuple.element_types[sub.rtuple_index].to_c_type_str()
            return f"{value_expr}.f{sub.rtuple_index}", el_c_type

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

        # Build kwargs (interleaved: key, value, key, value, ...)
        boxed_kwargs: list[str] = []
        for kw_name, kw_val in inst.kwargs:
            kw_expr, kw_type = self._emit_expr(kw_val, native)
            boxed_kwargs.append(f"MP_OBJ_NEW_QSTR(MP_QSTR_{kw_name})")
            boxed_kwargs.append(self._box_value(kw_expr, kw_type))

        n_args = len(args)
        n_kw = len(inst.kwargs)

        if n_kw > 0:
            # With kwargs: interleave args and kwargs in the array
            all_args = args + boxed_kwargs
            all_args_str = ", ".join(all_args)
            return (
                f"{inst.c_class_name}_make_new(&{inst.c_class_name}_type, {n_args}, {n_kw}, (const mp_obj_t[]){{{all_args_str}}})",
                "mp_obj_t",
            )
        else:
            # No kwargs - original optimized path
            args_str = ", ".join(args)
            return (
                f"{inst.c_class_name}_make_new(&{inst.c_class_name}_type, {n_args}, 0, (const mp_obj_t[]){{{args_str}}})",
                "mp_obj_t",
            )

    def _emit_self_attr(self, attr: SelfAttrIR) -> tuple[str, str]:
        return f"self->{attr.attr_path}", attr.result_type.to_c_type_str()

    def _emit_self_method_ref(self, ref: SelfMethodRefIR) -> tuple[str, str]:
        """Emit a bound method reference: self.method -> bound method object."""
        # Create a bound method that captures both the method and self
        return (
            f"mp_obj_new_bound_meth(MP_OBJ_FROM_PTR(&{ref.method_c_name}_obj), MP_OBJ_FROM_PTR(self))"
        ), "mp_obj_t"

    def _emit_param_attr(self, attr: ParamAttrIR) -> tuple[str, str]:
        # For trait-typed parameters, use dynamic attribute lookup
        # because the struct layout depends on the implementing class at runtime
        if attr.is_trait_type:
            expr = f"mp_load_attr({attr.c_param_name}, MP_QSTR_{attr.attr_name})"
            return expr, "mp_obj_t"

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
                # Use the IR's expected type as target, not default mp_int_t
                target_type = arg.ir_type.to_c_type_str()
                args.append(self._unbox_if_needed(arg_expr, arg_type, target_type))
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

        Generated C pattern (simple module):
            mp_obj_t _fn = mp_load_attr(
                mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                MP_QSTR_sqrt);
            mp_obj_t result = mp_call_function_1(_fn, arg);

        Generated C pattern (dotted module like lvgl_mvu.program):
            mp_obj_t _fn = mp_load_attr(
                mp_load_attr(
                    mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                    MP_QSTR_program),
                MP_QSTR_func_name);
        """
        mod_import = _emit_dotted_module_import(call.module_name)
        func_name = call.func_name
        fn_expr = f"mp_load_attr({mod_import}, MP_QSTR_{func_name})"

        # Build boxed positional args
        boxed_args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg, native)
            boxed_args.append(self._box_value(arg_expr, arg_type))

        # Build boxed keyword args (interleaved: key, value, key, value, ...)
        boxed_kwargs = []
        for kw_name, kw_val in call.kwargs:
            boxed_kwargs.append(f"MP_OBJ_NEW_QSTR(MP_QSTR_{kw_name})")
            kw_expr, kw_type = self._emit_expr(kw_val, native)
            boxed_kwargs.append(self._box_value(kw_expr, kw_type))

        n_args = len(boxed_args)
        n_kw = len(call.kwargs)

        # If we have kwargs, must use mp_call_function_n_kw
        if n_kw > 0:
            all_args = boxed_args + boxed_kwargs
            args_str = ", ".join(all_args)
            return (
                f"mp_call_function_n_kw({fn_expr}, "
                f"{n_args}, {n_kw}, (const mp_obj_t[]){{{args_str}}})"
            ), "mp_obj_t"

        # No kwargs - use optimized paths
        if n_args == 0:
            return f"mp_call_function_0({fn_expr})", "mp_obj_t"
        elif n_args == 1:
            return f"mp_call_function_1({fn_expr}, {boxed_args[0]})", "mp_obj_t"
        elif n_args == 2:
            return (f"mp_call_function_2({fn_expr}, {boxed_args[0]}, {boxed_args[1]})"), "mp_obj_t"
        else:
            args_str = ", ".join(boxed_args)
            return (
                f"mp_call_function_n_kw({fn_expr}, {n_args}, 0, (const mp_obj_t[]){{{args_str}}})"
            ), "mp_obj_t"

    def _emit_module_attr(self, attr: ModuleAttrIR) -> tuple[str, str]:
        """Emit C code for accessing an attribute on an imported module.

        Generated C pattern (simple):
            mp_load_attr(
                mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                MP_QSTR_pi)

        Generated C pattern (dotted module like lvgl_mvu.program):
            mp_load_attr(
                mp_load_attr(
                    mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                    MP_QSTR_program),
                MP_QSTR_Cmd)
        """
        mod_import = _emit_dotted_module_import(attr.module_name)
        return f"mp_load_attr({mod_import}, MP_QSTR_{attr.attr_name})", "mp_obj_t"

    def _emit_imported_class_attr(self, attr: ImportedClassAttrIR) -> tuple[str, str]:
        """Emit C code for accessing an attribute on an imported class.

        For: from lvgl_mvu.events import LvEvent; LvEvent.CLICKED

        Generated C pattern:
            mp_load_attr(
                mp_load_attr(
                    mp_import_name(MP_QSTR_lvgl_mvu, mp_const_none, MP_OBJ_NEW_SMALL_INT(0)),
                    MP_QSTR_events),
                MP_QSTR_LvEvent),
            MP_QSTR_CLICKED)
        """
        # Import the source module
        mod_import = _emit_dotted_module_import(attr.source_module)
        # Load the class from the module
        class_load = f"mp_load_attr({mod_import}, MP_QSTR_{attr.class_name})"
        # Load the attribute from the class
        return f"mp_load_attr({class_load}, MP_QSTR_{attr.attr_name})", "mp_obj_t"

    def _emit_sibling_module_call(
        self, call: SiblingModuleCallIR, native: bool = False
    ) -> tuple[str, str]:
        """Emit C code for calling a function on a sibling module.

        Since sibling modules are compiled together in the same package,
        we generate a direct C function call instead of mp_import_name.

        Generated C pattern:
            {c_prefix}_{func_name}(arg1, arg2, ...)
        """
        del native  # Always generates boxed call for sibling modules

        # Build boxed args
        boxed_args = []
        for arg in call.args:
            arg_expr, arg_type = self._emit_expr(arg)
            boxed_args.append(self._box_value(arg_expr, arg_type))

        args_str = ", ".join(boxed_args)
        c_func_name = f"{call.c_prefix}_{call.func_name}"

        if args_str:
            return f"{c_func_name}({args_str})", "mp_obj_t"
        else:
            return f"{c_func_name}()", "mp_obj_t"

    def _emit_sibling_class_instantiation(
        self, inst: SiblingClassInstantiationIR, native: bool = False
    ) -> tuple[str, str]:
        """Emit C code for instantiating a class from a sibling module.

        Since sibling modules are compiled together in the same package,
        we generate a direct call to the class's make_new function.

        Generated C pattern:
            {c_prefix}_{class_name}_make_new(&{c_prefix}_{class_name}_type, n_args, 0, args_array)
        """
        del native  # Always generates boxed call

        # Build boxed args
        boxed_args = []
        for arg in inst.args:
            arg_expr, arg_type = self._emit_expr(arg)
            boxed_args.append(self._box_value(arg_expr, arg_type))

        c_class_name = f"{inst.c_prefix}_{inst.class_name}"
        n_args = len(boxed_args)

        if n_args == 0:
            return f"{c_class_name}_make_new(&{c_class_name}_type, 0, 0, NULL)", "mp_obj_t"
        else:
            args_array = ", ".join(boxed_args)
            return (
                f"{c_class_name}_make_new(&{c_class_name}_type, {n_args}, 0, (const mp_obj_t[]){{{args_array}}})",
                "mp_obj_t",
            )

    def _box_value(self, expr: str, expr_type: str) -> str:
        # 'self' in method context is a struct pointer, not an integer.
        # Convert back to mp_obj_t using MP_OBJ_FROM_PTR.
        if expr == "self" and expr_type == "mp_int_t":
            return "MP_OBJ_FROM_PTR(self)"
        if expr_type == "mp_int_t":
            return f"mp_obj_new_int({expr})"
        elif expr_type == "mp_float_t":
            return f"mp_obj_new_float({expr})"
        elif expr_type == "bool":
            return f"mp_obj_new_bool({expr})"
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


# Re-export for backward compatibility
__all__ = [
    "BaseEmitter",
    "C_RESERVED_WORDS",
    "sanitize_name",
    "_emit_dotted_module_import",
]
