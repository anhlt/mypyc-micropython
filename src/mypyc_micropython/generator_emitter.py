from __future__ import annotations

from .function_emitter import BaseEmitter, sanitize_name
from .ir import (
    AnnAssignIR,
    AssignIR,
    AugAssignIR,
    ConstIR,
    CType,
    ForIterIR,
    ForRangeIR,
    FuncIR,
    NameIR,
    ReturnIR,
    StmtIR,
    ValueIR,
    YieldIR,
)

_GEN_DONE_STATE = 0xFFFF


class GeneratorEmitter(BaseEmitter):
    def __init__(self, func_ir: FuncIR):
        self.func_ir = func_ir
        super().__init__(func_ir.max_temp)

    def emit(self) -> tuple[str, str]:
        struct_lines = self._emit_generator_struct()
        iternext_lines = self._emit_iternext()
        wrapper_lines, obj_def = self._emit_wrapper()
        full_code = "\n\n".join(
            [
                "\n".join(struct_lines),
                "\n".join(iternext_lines),
                "\n".join(wrapper_lines),
                obj_def,
            ]
        )
        return full_code, obj_def

    def _emit_generator_struct(self) -> list[str]:
        lines = [
            f"typedef struct _{self.func_ir.c_name}_gen_t {{",
            "    mp_obj_base_t base;",
            "    uint16_t state;",
        ]
        for field_name, field_type in self._all_gen_fields().items():
            lines.append(f"    {field_type.to_c_type_str()} {field_name};")
        lines.append(f"}} {self.func_ir.c_name}_gen_t;")
        return lines

    def _emit_iternext(self) -> list[str]:
        lines = [
            f"static mp_obj_t {self.func_ir.c_name}_gen_iternext(mp_obj_t self_in) {{",
            f"    {self.func_ir.c_name}_gen_t *self = MP_OBJ_TO_PTR(self_in);",
            "    uint16_t st = self->state;",
            f"    self->state = {_GEN_DONE_STATE};",
            "",
            "    switch (st) {",
            "        case 0: goto state_0;",
        ]

        for state_id in self._collect_yield_state_ids(self.func_ir.body):
            lines.append(f"        case {state_id}: goto state_{state_id};")

        lines.extend(
            [
                f"        case {_GEN_DONE_STATE}: return MP_OBJ_STOP_ITERATION;",
                "        default: return MP_OBJ_STOP_ITERATION;",
                "    }",
                "",
                "state_0:",
            ]
        )

        for stmt in self.func_ir.body:
            if isinstance(stmt, YieldIR):
                lines.extend(self._emit_statement(stmt))
                continue
            lines.append("    {")
            for line in self._emit_statement(stmt):
                lines.append(line)
            lines.append("    }")

        lines.extend(
            [
                f"    self->state = {_GEN_DONE_STATE};",
                "    return MP_OBJ_STOP_ITERATION;",
                "}",
                "",
                "MP_DEFINE_CONST_OBJ_TYPE(",
                f"    {self.func_ir.c_name}_gen_type,",
                "    MP_QSTR_generator,",
                "    MP_TYPE_FLAG_ITER_IS_ITERNEXT,",
                f"    iter, {self.func_ir.c_name}_gen_iternext",
                ");",
            ]
        )
        return lines

    def _emit_wrapper(self) -> tuple[list[str], str]:
        signature, obj_def = self._emit_wrapper_signature()
        lines = [signature + " {"]
        lines.append(
            f"    {self.func_ir.c_name}_gen_t *gen = mp_obj_malloc({self.func_ir.c_name}_gen_t, &{self.func_ir.c_name}_gen_type);"
        )
        lines.append("    gen->state = 0;")

        for name, c_type in self._all_gen_fields().items():
            if self._is_param_field(name):
                src = self._param_source_expr(name)
                lines.append(f"    gen->{name} = {self._unbox_arg(src, c_type)};")
            else:
                lines.append(f"    gen->{name} = {self._default_expr_for_type(c_type)};")

        lines.append("    return MP_OBJ_FROM_PTR(gen);")
        lines.append("}")
        return lines, obj_def

    def _emit_wrapper_signature(self) -> tuple[str, str]:
        num_args = len(self.func_ir.params)
        arg_names = [sanitize_name(param[0]) for param in self.func_ir.params]

        if num_args == 0:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(void)",
                f"MP_DEFINE_CONST_FUN_OBJ_0({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        if num_args == 1:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(mp_obj_t {arg_names[0]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_1({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        if num_args == 2:
            return (
                f"static mp_obj_t {self.func_ir.c_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_2({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        if num_args == 3:
            return (
                "static mp_obj_t "
                f"{self.func_ir.c_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj, mp_obj_t {arg_names[2]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_3({self.func_ir.c_name}_obj, {self.func_ir.c_name});",
            )
        return (
            f"static mp_obj_t {self.func_ir.c_name}(size_t n_args, const mp_obj_t *args)",
            f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({self.func_ir.c_name}_obj, {num_args}, {num_args}, {self.func_ir.c_name});",
        )

    def _emit_statement(self, stmt: StmtIR, native: bool = False) -> list[str]:
        del native
        if isinstance(stmt, YieldIR):
            return self._emit_yield(stmt)
        if isinstance(stmt, ReturnIR):
            return self._emit_return(stmt)
        return super()._emit_statement(stmt, native=False)

    def _emit_yield(self, stmt: YieldIR) -> list[str]:
        lines = ["    {"]
        lines.extend(self._emit_prelude(stmt.prelude))
        if stmt.value is None:
            yield_expr = "mp_const_none"
        else:
            expr, expr_type = self._emit_expr(stmt.value)
            yield_expr = self._box_value(expr, expr_type)
        lines.append(f"    self->state = {stmt.state_id};")
        lines.append(f"    return {yield_expr};")
        lines.append("    }")
        lines.append(f"state_{stmt.state_id}:")
        return lines

    def _emit_return(self, stmt: ReturnIR, native: bool = False) -> list[str]:
        del native
        lines = self._emit_prelude(stmt.prelude)
        lines.append(f"    self->state = {_GEN_DONE_STATE};")
        lines.append("    return MP_OBJ_STOP_ITERATION;")
        return lines

    def _emit_for_range(self, stmt: ForRangeIR, native: bool = False) -> list[str]:
        del native
        if not self._is_supported_generator_for_range(stmt):
            return [
                "    /* unsupported generator for-range shape */",
                f"    self->state = {_GEN_DONE_STATE};",
                "    return MP_OBJ_STOP_ITERATION;",
            ]

        lines: list[str] = []
        loop_var = sanitize_name(stmt.c_loop_var)
        start_expr, _ = self._emit_expr(stmt.start)
        end_expr, _ = self._emit_expr(stmt.end)
        lines.append(f"    self->{loop_var} = {start_expr};")
        lines.append(f"    while (self->{loop_var} < {end_expr}) {{")
        self._loop_depth += 1
        for s in stmt.body:
            for line in self._emit_statement(s):
                lines.append("    " + line)
        self._loop_depth -= 1
        lines.append(f"        self->{loop_var}++;")
        lines.append("    }")
        return lines

    def _emit_for_iter(self, stmt: ForIterIR, native: bool = False) -> list[str]:
        """Emit for-iter loop for generator (iterate over arbitrary iterable)."""
        del native
        lines: list[str] = []
        lines.extend(self._emit_prelude(stmt.iter_prelude))

        iter_expr, _ = self._emit_expr(stmt.iterable)
        loop_var = sanitize_name(stmt.c_loop_var)
        iter_field = f"iter_{loop_var}"

        # Initialize iterator from iterable (NULL = let MicroPython manage buffer)
        lines.append(f"    self->{iter_field} = mp_getiter({iter_expr}, NULL);")

        # Loop: get next item, check for stop iteration
        lines.append(f"    while ((self->{loop_var} = mp_iternext(self->{iter_field})) != MP_OBJ_STOP_ITERATION) {{")

        self._loop_depth += 1
        for s in stmt.body:
            for line in self._emit_statement(s):
                lines.append("    " + line)
        self._loop_depth -= 1

        # Add no-op after body to handle labels at end of block (C99 compatibility)
        lines.append("        (void)0;")
        lines.append("    }")
        return lines

    def _emit_assign(self, stmt: AssignIR, native: bool = False) -> list[str]:
        del native
        lines = self._emit_prelude(stmt.prelude)
        expr, expr_type = self._emit_expr(stmt.value)
        target = sanitize_name(stmt.c_target)
        if stmt.c_type != expr_type:
            expr = self._unbox_if_needed(expr, expr_type, stmt.c_type)
        lines.append(f"    self->{target} = {expr};")
        return lines

    def _emit_aug_assign(self, stmt: AugAssignIR, native: bool = False) -> list[str]:
        del native
        lines = self._emit_prelude(stmt.prelude)
        expr, expr_type = self._emit_expr(stmt.value)
        target = sanitize_name(stmt.c_target)
        if stmt.target_c_type != expr_type:
            expr = self._unbox_if_needed(expr, expr_type, stmt.target_c_type)
        lines.append(f"    self->{target} {stmt.op} {expr};")
        return lines

    def _emit_ann_assign(self, stmt: AnnAssignIR, native: bool = False) -> list[str]:
        del native
        lines = self._emit_prelude(stmt.prelude)
        target = sanitize_name(stmt.c_target)
        if stmt.value is None:
            lines.append(f"    self->{target} = {self._default_expr_for_c_type_str(stmt.c_type)};")
            return lines

        expr, expr_type = self._emit_expr(stmt.value)
        expr = self._unbox_if_needed(expr, expr_type, stmt.c_type)
        lines.append(f"    self->{target} = {expr};")
        return lines

    def _emit_expr(self, value: ValueIR, native: bool = False) -> tuple[str, str]:
        if isinstance(value, NameIR):
            return f"self->{sanitize_name(value.c_name)}", value.ir_type.to_c_type_str()
        return super()._emit_expr(value, native)

    def _collect_yield_state_ids(self, body: list[StmtIR]) -> list[int]:
        state_ids: set[int] = set()

        def walk(stmts: list[StmtIR]) -> None:
            for stmt in stmts:
                if isinstance(stmt, YieldIR):
                    state_ids.add(stmt.state_id)
                elif hasattr(stmt, "body") and isinstance(getattr(stmt, "body"), list):
                    walk(getattr(stmt, "body"))
                    if hasattr(stmt, "orelse") and isinstance(getattr(stmt, "orelse"), list):
                        walk(getattr(stmt, "orelse"))

        walk(body)
        return sorted(state_ids)

    def _all_gen_fields(self) -> dict[str, CType]:
        fields: dict[str, CType] = {}
        for name, c_type in self.func_ir.params:
            fields[sanitize_name(name)] = c_type
        for name, c_type in self.func_ir.locals_.items():
            safe = sanitize_name(name)
            if safe not in fields:
                fields[safe] = c_type

        # Add iterator fields for ForIterIR loops
        def walk_for_iter_fields(stmts: list[StmtIR]) -> None:
            for stmt in stmts:
                if isinstance(stmt, ForIterIR):
                    loop_var = sanitize_name(stmt.c_loop_var)
                    # Iterator object field
                    fields[f"iter_{loop_var}"] = CType.MP_OBJ_T
                    # Loop variable field (current item)
                    if loop_var not in fields:
                        fields[loop_var] = CType.MP_OBJ_T
                # Recurse into nested bodies
                if hasattr(stmt, "body") and isinstance(getattr(stmt, "body"), list):
                    walk_for_iter_fields(getattr(stmt, "body"))
                if hasattr(stmt, "orelse") and isinstance(getattr(stmt, "orelse"), list):
                    walk_for_iter_fields(getattr(stmt, "orelse"))

        walk_for_iter_fields(self.func_ir.body)
        return fields

    def _is_supported_generator_for_range(self, stmt: ForRangeIR) -> bool:
        # Allow any constant step=1 range, with any start (const or name)
        if not (stmt.step_is_constant and stmt.step_value == 1):
            return False
        # start must be ConstIR or NameIR
        if not isinstance(stmt.start, (ConstIR, NameIR)):
            return False
        # end must be ConstIR or NameIR
        return isinstance(stmt.end, (ConstIR, NameIR))

    def _is_param_field(self, field_name: str) -> bool:
        return any(sanitize_name(name) == field_name for name, _ in self.func_ir.params)

    def _param_source_expr(self, field_name: str) -> str:
        for i, (param_name, _) in enumerate(self.func_ir.params):
            safe = sanitize_name(param_name)
            if safe != field_name:
                continue
            if len(self.func_ir.params) <= 3:
                return f"{safe}_obj"
            return f"args[{i}]"
        return "mp_const_none"

    def _unbox_arg(self, expr: str, c_type: CType) -> str:
        if c_type == CType.MP_INT_T:
            return f"mp_obj_get_int({expr})"
        if c_type == CType.MP_FLOAT_T:
            return f"mp_get_float_checked({expr})"
        if c_type == CType.BOOL:
            return f"mp_obj_is_true({expr})"
        return expr

    def _default_expr_for_type(self, c_type: CType) -> str:
        if c_type == CType.MP_INT_T:
            return "0"
        if c_type == CType.MP_FLOAT_T:
            return "0.0"
        if c_type == CType.BOOL:
            return "false"
        return "mp_const_none"

    def _default_expr_for_c_type_str(self, c_type: str) -> str:
        if c_type == "mp_int_t":
            return "0"
        if c_type == "mp_float_t":
            return "0.0"
        if c_type == "bool":
            return "false"
        return "mp_const_none"
