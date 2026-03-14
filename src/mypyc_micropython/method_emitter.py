"""
Method Emitter: MethodIR + ClassIR -> C code.

This module generates MicroPython-compatible C code from class method IR.
"""

from __future__ import annotations

from .base_emitter import BaseEmitter
from .ir import (
    AnnAssignIR,
    AttrAssignIR,
    ClassIR,
    CType,
    MethodIR,
    ReturnIR,
    SelfAttrIR,
    SelfAugAssignIR,
    SelfMethodCallIR,
    SelfMethodRefIR,
    StmtNode,
)


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

    def _emit_self_method_ref(self, ref: SelfMethodRefIR) -> tuple[str, str]:
        """Emit a bound method reference: self.method -> bound method object."""
        return (
            f"mp_obj_new_bound_meth(MP_OBJ_FROM_PTR(&{ref.method_c_name}_obj), MP_OBJ_FROM_PTR(self))"
        ), "mp_obj_t"

    def _emit_self_method_call(
        self, call: SelfMethodCallIR, native: bool = False
    ) -> tuple[str, str]:
        method_ir = self.class_ir.methods.get(call.method_name)
        args = ["self"]
        for i, arg in enumerate(call.args):
            arg_expr, arg_type = self._emit_expr(arg, native)
            target_type = arg.ir_type.to_c_type_str()
            if method_ir is not None and i < len(method_ir.params):
                target_type = method_ir.params[i][1].to_c_type_str()
            if target_type == "mp_obj_t":
                args.append(self._box_value(arg_expr, arg_type))
            elif native:
                args.append(self._unbox_if_needed(arg_expr, arg_type, target_type))
            else:
                args.append(self._unbox_if_needed(arg_expr, arg_type, target_type))
        args_str = ", ".join(args)
        return f"{call.c_method_name}_native({args_str})", call.return_type.to_c_type_str()

    def emit_native(self, body: list[StmtNode]) -> str:
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

    def emit_mp_wrapper(self, body: list[StmtNode] | None = None) -> str:
        method_ir = self.method_ir
        class_ir = self.class_ir

        # For methods: num_args includes self (for instance methods)
        # For static/classmethod: num_args is just params
        self_count = 0 if (method_ir.is_static or method_ir.is_classmethod) else 1
        num_args = len(method_ir.params) + self_count
        min_args = method_ir.num_required_args + self_count
        has_defaults = method_ir.has_defaults
        obj_name = (
            f"{method_ir.c_name}_fun_obj"
            if (method_ir.is_static or method_ir.is_classmethod)
            else f"{method_ir.c_name}_obj"
        )

        # Choose signature and obj_def based on args
        if has_defaults:
            # Methods with defaults use VAR_BETWEEN
            sig = f"static mp_obj_t {method_ir.c_name}_mp(size_t n_args, const mp_obj_t *args)"
            obj_def = (
                f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({obj_name}, {min_args}, {num_args}, "
                f"{method_ir.c_name}_mp);"
            )
        elif num_args == 0:
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

        # Unbox self for instance methods
        if not method_ir.is_static and not method_ir.is_classmethod:
            if has_defaults or num_args > 3:
                lines.append(f"    {class_ir.c_name}_obj_t *self = MP_OBJ_TO_PTR(args[0]);")
            else:
                lines.append(f"    {class_ir.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")

        # Unbox method parameters
        for i, (param_name, param_type) in enumerate(method_ir.params):
            if has_defaults or num_args > 3:
                src_index = i if (method_ir.is_static or method_ir.is_classmethod) else i + 1
                src = f"args[{src_index}]"
            else:
                src = f"arg{i}_obj"

            default_arg = method_ir.defaults.get(i) if has_defaults else None

            if default_arg is not None and default_arg.c_expr is not None:
                # Parameter has default value - check n_args
                arg_index = i if (method_ir.is_static or method_ir.is_classmethod) else i + 1
                if param_type == CType.MP_INT_T:
                    default_val: int | float | str = (
                        default_arg.value if isinstance(default_arg.value, int) else 0
                    )
                    lines.append(
                        f"    mp_int_t {param_name} = (n_args > {arg_index}) ? mp_obj_get_int({src}) : {default_val};"
                    )
                elif param_type == CType.MP_FLOAT_T:
                    default_val = (
                        default_arg.value if isinstance(default_arg.value, (int, float)) else 0.0
                    )
                    lines.append(
                        f"    mp_float_t {param_name} = (n_args > {arg_index}) ? mp_obj_get_float({src}) : {default_val};"
                    )
                elif param_type == CType.BOOL:
                    default_val = "true" if default_arg.value else "false"
                    lines.append(
                        f"    bool {param_name} = (n_args > {arg_index}) ? mp_obj_is_true({src}) : {default_val};"
                    )
                else:
                    lines.append(
                        f"    mp_obj_t {param_name} = (n_args > {arg_index}) ? {src} : {default_arg.c_expr};"
                    )
            else:
                # Required parameter - no default
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

        # Always apply type conversion when assigning to typed fields, even in native mode
        # because the value might come from mp_obj_subscr etc. which returns mp_obj_t
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
