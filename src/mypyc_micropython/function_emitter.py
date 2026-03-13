"""
Function Emitter: FuncIR -> C code.

This module generates MicroPython-compatible C code from function IR.
"""

from __future__ import annotations

from .base_emitter import BaseEmitter, sanitize_name
from .ir import (
    AnnAssignIR,
    AugAssignIR,
    CType,
    DefaultArg,
    FuncIR,
    NameIR,
    ReturnIR,
    RTuple,
    TupleNewIR,
)


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

    def emit_forward_declaration(self) -> str:
        """Emit a forward declaration for this function."""
        c_sig, obj_def = self._emit_signature()
        lines = [c_sig + ";"]
        if "_lambda_" in self.func_ir.c_name:
            # Determine the correct obj type based on argument count
            num_args = len(self.func_ir.params)
            if num_args > 3 or self.func_ir.has_defaults or self.func_ir.has_star_args:
                extern_decl = f"extern const mp_obj_fun_builtin_var_t {self.func_ir.c_name}_obj;"
            else:
                extern_decl = f"extern const mp_obj_fun_builtin_fixed_t {self.func_ir.c_name}_obj;"
            lines.append(extern_decl)
        return "\n".join(lines)

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
            assert self.func_ir.star_args is not None
            star_args_name = sanitize_name(self.func_ir.star_args.name)
            # Prefix with _star_ to avoid conflict with C parameter 'args'
            c_star_args_name = f"_star_{star_args_name}"
            lines.append(
                f"    mp_obj_t {c_star_args_name} = mp_obj_new_tuple(n_args > {num_args} ? n_args - {num_args} : 0, n_args > {num_args} ? {args_array} + {num_args} : NULL);"
            )

        if has_star_kwargs:
            assert self.func_ir.star_kwargs is not None
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

    def _get_unboxed_default(self, default_arg: DefaultArg, c_type_str: str) -> str:
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
                    elif el_type in (CType.MP_OBJ_T, CType.GENERAL):
                        items_parts.append(f"{expr}.f{i}")
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

    def _emit_rtuple_unbox(self, c_type: str, target: str, src_expr: str, rtuple: RTuple) -> list[str]:
        lines = []
        temp = self._fresh_temp()
        lines.append(f"    mp_obj_tuple_t *{temp} = MP_OBJ_TO_PTR({src_expr});")
        items = []
        for i, el_type in enumerate(rtuple.element_types):
            if el_type == CType.MP_FLOAT_T:
                items.append(f"mp_obj_get_float({temp}->items[{i}])")
            elif el_type == CType.BOOL:
                items.append(f"mp_obj_is_true({temp}->items[{i}])")
            elif el_type in (CType.MP_OBJ_T, CType.GENERAL):
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
