"""
Async Emitter: Emit async functions as coroutine objects.

Async functions are compiled similarly to generators, with additional methods:
- __await__() returns self (makes the coroutine awaitable)
- send(value) resumes the coroutine with a value
- throw(exc) injects an exception into the coroutine
- close() terminates the coroutine

The state machine approach is identical to generators:
- Each await point becomes a state in the switch statement
- Local variables are stored in the coroutine struct
- Resumption jumps to the appropriate state label
"""

from __future__ import annotations

from .generator_emitter import _GEN_DONE_STATE, GeneratorEmitter
from .ir import (
    AwaitIR,
    AwaitModuleCallIR,
    ReturnIR,
    StmtIR,
    YieldIR,
)


class AsyncEmitter(GeneratorEmitter):
    """Emit async functions as MicroPython coroutine objects.

    Extends GeneratorEmitter with:
    - __await__ method (returns self)
    - send() method with value parameter
    - Handling for AwaitIR nodes
    """

    def _emit_generator_struct(self) -> list[str]:
        """Emit coroutine struct with send_value and await_iter fields."""
        lines = [
            f"typedef struct _{self.func_ir.c_name}_coro_t {{",
            "    mp_obj_base_t base;",
            "    uint16_t state;",
            "    mp_obj_t send_value;  // Value passed via send()",
            "    mp_obj_t _await_iter;  // Active awaitable iterator for yield-from",
        ]
        for field_name, field_type in self._all_gen_fields().items():
            lines.append(f"    {field_type.to_c_type_str()} {field_name};")
        lines.append(f"}} {self.func_ir.c_name}_coro_t;")
        return lines

    def _emit_iternext(self) -> list[str]:
        """Emit the coroutine's iternext function (called by send())."""
        lines = [
            f"static mp_obj_t {self.func_ir.c_name}_coro_iternext(mp_obj_t self_in) {{",
            f"    {self.func_ir.c_name}_coro_t *self = MP_OBJ_TO_PTR(self_in);",
            "    uint16_t st = self->state;",
            f"    self->state = {_GEN_DONE_STATE};",
            "",
            "    switch (st) {",
            "        case 0: goto state_0;",
        ]

        # Collect all state IDs from both yield and await
        for state_id in self._collect_all_state_ids(self.func_ir.body):
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
            if isinstance(stmt, (YieldIR, AwaitIR, AwaitModuleCallIR)):
                lines.extend(self._emit_statement(stmt))
                continue
            lines.append("    {")
            for line in self._emit_statement(stmt):
                lines.append(line)
            lines.append("    }")

        lines.extend(
            [
                f"    self->state = {_GEN_DONE_STATE};",
                "    return mp_make_stop_iteration(mp_const_none);",
                "}",
            ]
        )
        return lines

    def _emit_await(self, stmt: AwaitIR) -> list[str]:
        """Emit await expression.

        await expr compiles to:
        1. Evaluate expr to get awaitable
        2. Set state for resumption
        3. Return awaitable (yield to event loop)
        4. State label: receive send_value as result
        """
        lines = ["    {"]
        lines.extend(self._emit_prelude(stmt.prelude))

        # Get the awaitable value
        expr, expr_type = self._emit_expr(stmt.value)
        await_expr = self._box_value(expr, expr_type)

        # Set state for resumption and return awaitable
        lines.append(f"    self->state = {stmt.state_id};")
        lines.append(f"    return {await_expr};")
        lines.append("    }")

        # State label for resumption
        lines.append(f"state_{stmt.state_id}:")

        # If result is stored, get it from send_value
        if stmt.result:
            lines.append("    {")
            lines.append(f"    self->{stmt.result} = self->send_value;")
            lines.append("    }")

        return lines

    def _emit_await_module_call(self, stmt: AwaitModuleCallIR) -> list[str]:
        """Emit await on module function call using mp_iternext.

        await module.func(args) compiles to:
        1. On first entry: import module, get function, call to get awaitable,
           store in _await_iter
        2. Call mp_iternext() to iterate the awaitable
        3. If it yields (non-STOP_ITERATION), stay at same state and return value
        4. If it completes (STOP_ITERATION), clear _await_iter and continue
        """
        lines = []

        # State label comes first (before the await loop body)
        lines.append(f"state_{stmt.state_id}:")
        lines.append("    {")

        # Check if this is first entry (awaitable not yet created)
        lines.append("    if (self->_await_iter == mp_const_none) {")

        # Emit preludes for arguments
        for prelude in stmt.arg_preludes:
            for line in self._emit_prelude(prelude):
                lines.append(f"    {line}")

        # Import module at runtime using dynamic qstr lookup
        lines.append(f'        mp_obj_t _mod = mp_import_name(qstr_from_str("{stmt.module_name}"), mp_const_none, MP_OBJ_NEW_SMALL_INT(0));')

        # Get function attribute using dynamic qstr lookup
        lines.append(f'        mp_obj_t _fn = mp_load_attr(_mod, qstr_from_str("{stmt.func_name}"));')

        # Build args and call function to get awaitable
        if not stmt.args:
            lines.append("        self->_await_iter = mp_call_function_0(_fn);")
        elif len(stmt.args) == 1:
            arg_expr, arg_type = self._emit_expr(stmt.args[0])
            arg_boxed = self._box_value(arg_expr, arg_type)
            lines.append(f"        self->_await_iter = mp_call_function_1(_fn, {arg_boxed});")
        elif len(stmt.args) == 2:
            arg0_expr, arg0_type = self._emit_expr(stmt.args[0])
            arg0_boxed = self._box_value(arg0_expr, arg0_type)
            arg1_expr, arg1_type = self._emit_expr(stmt.args[1])
            arg1_boxed = self._box_value(arg1_expr, arg1_type)
            lines.append(f"        self->_await_iter = mp_call_function_2(_fn, {arg0_boxed}, {arg1_boxed});")
        else:
            # For 3+ args, use mp_call_function_n_kw
            lines.append(f"        mp_obj_t _args[{len(stmt.args)}];")
            for i, arg in enumerate(stmt.args):
                arg_expr, arg_type = self._emit_expr(arg)
                arg_boxed = self._box_value(arg_expr, arg_type)
                lines.append(f"        _args[{i}] = {arg_boxed};")
            lines.append(f"        self->_await_iter = mp_call_function_n_kw(_fn, {len(stmt.args)}, 0, _args);")

        lines.append("    }")

        # Iterate the awaitable using mp_iternext
        lines.append("    mp_obj_t _ret_val = mp_iternext(self->_await_iter);")

        # Check if awaitable yielded or completed
        lines.append("    if (_ret_val != MP_OBJ_STOP_ITERATION) {")
        lines.append("        // Awaitable yielded - stay at this state and yield the value")
        lines.append(f"        self->state = {stmt.state_id};")
        lines.append("        return _ret_val;")
        lines.append("    }")

        # Awaitable completed - get result from stop_iteration_arg
        lines.append("    // Awaitable completed")
        lines.append("    self->_await_iter = mp_const_none;")

        # If result is stored, get the value from stop_iteration_arg
        if stmt.result:
            lines.append(f"    self->{stmt.result} = MP_STATE_THREAD(stop_iteration_arg);")
            lines.append(f"    if (self->{stmt.result} == MP_OBJ_NULL) {{ self->{stmt.result} = mp_const_none; }}")

        lines.append("    }")

        return lines

    def _emit_statement(self, stmt: StmtIR, native: bool = False) -> list[str]:
        """Handle AwaitIR and AwaitModuleCallIR in addition to normal statements."""
        del native
        if isinstance(stmt, AwaitIR):
            return self._emit_await(stmt)
        if isinstance(stmt, AwaitModuleCallIR):
            return self._emit_await_module_call(stmt)
        return super()._emit_statement(stmt, native=False)

    def _emit_return(self, stmt: ReturnIR, native: bool = False) -> list[str]:
        """Emit return statement for async function.

        Unlike generators (which ignore return values), async functions
        must pass return values via mp_make_stop_iteration(value) so that
        the event loop (uasyncio) can retrieve the result.
        """
        del native
        lines = self._emit_prelude(stmt.prelude)
        lines.append(f"    self->state = {_GEN_DONE_STATE};")
        if stmt.value is None:
            lines.append("    return mp_make_stop_iteration(mp_const_none);")
        else:
            expr, expr_type = self._emit_expr(stmt.value)
            ret_expr = self._box_value(expr, expr_type)
            lines.append(f"    return mp_make_stop_iteration({ret_expr});")
        return lines

    def _collect_all_state_ids(self, body: list[StmtIR]) -> list[int]:
        """Collect state IDs from both YieldIR and AwaitIR."""
        state_ids: set[int] = set()

        def walk(stmts: list[StmtIR]) -> None:
            for stmt in stmts:
                if isinstance(stmt, (YieldIR, AwaitIR, AwaitModuleCallIR)):
                    state_ids.add(stmt.state_id)
                elif hasattr(stmt, "body") and isinstance(getattr(stmt, "body"), list):
                    walk(getattr(stmt, "body"))
                    if hasattr(stmt, "orelse") and isinstance(getattr(stmt, "orelse"), list):
                        walk(getattr(stmt, "orelse"))

        walk(body)
        return sorted(state_ids)

    def emit(self) -> tuple[str, str]:
        """Emit the complete async function as a coroutine."""
        struct_lines = self._emit_generator_struct()
        iternext_lines = self._emit_iternext()
        send_lines = self._emit_send()
        await_method_lines = self._emit_await_method()
        close_lines = self._emit_close_method()
        throw_lines = self._emit_throw_method()
        wrapper_lines, obj_def = self._emit_wrapper()
        type_lines = self._emit_coroutine_type()

        full_code = "\n\n".join(
            [
                "\n".join(struct_lines),
                "\n".join(iternext_lines),
                "\n".join(send_lines),
                "\n".join(await_method_lines),
                "\n".join(close_lines),
                "\n".join(throw_lines),
                "\n".join(type_lines),  # Type must come before wrapper
                "\n".join(wrapper_lines),
                obj_def,  # Function object definition
            ]
        )
        return full_code, obj_def

    def _emit_send(self) -> list[str]:
        """Emit send() method for coroutine.

        send(value) stores value in send_value field, then calls iternext.
        When iternext returns MP_OBJ_STOP_ITERATION, send() must raise StopIteration.
        """
        return [
            f"static mp_obj_t {self.func_ir.c_name}_coro_send(mp_obj_t self_in, mp_obj_t value) {{",
            f"    {self.func_ir.c_name}_coro_t *self = MP_OBJ_TO_PTR(self_in);",
            "    self->send_value = value;",
            f"    mp_obj_t result = {self.func_ir.c_name}_coro_iternext(self_in);",
            "    if (result == MP_OBJ_STOP_ITERATION) {",
            "        // Coroutine completed - raise StopIteration with the return value",
            "        // Get the value that was set by mp_make_stop_iteration",
            "        mp_obj_t ret_val = MP_STATE_THREAD(stop_iteration_arg);",
            "        if (ret_val == mp_const_none) {",
            "            ret_val = MP_OBJ_NULL;",
            "        }",
            "        mp_raise_StopIteration(ret_val);",
            "    }",
            "    return result;",
            "}",
            f"static MP_DEFINE_CONST_FUN_OBJ_2({self.func_ir.c_name}_coro_send_obj, {self.func_ir.c_name}_coro_send);",
        ]

    def _emit_await_method(self) -> list[str]:
        """Emit __await__() method that returns self.

        This makes the coroutine object awaitable.
        """
        return [
            f"static mp_obj_t {self.func_ir.c_name}_coro_await(mp_obj_t self_in) {{",
            "    return self_in;  // Coroutine is its own iterator",
            "}",
            f"static MP_DEFINE_CONST_FUN_OBJ_1({self.func_ir.c_name}_coro_await_obj, {self.func_ir.c_name}_coro_await);",
        ]

    def _emit_close_method(self) -> list[str]:
        """Emit close() method for coroutine.

        close() marks the coroutine as done and returns None.
        """
        c_name = self.func_ir.c_name
        return [
            f"static mp_obj_t {c_name}_coro_close(mp_obj_t self_in) {{",
            f"    {c_name}_coro_t *self = MP_OBJ_TO_PTR(self_in);",
            f"    self->state = {_GEN_DONE_STATE};",
            "    return mp_const_none;",
            "}",
            f"static MP_DEFINE_CONST_FUN_OBJ_1({c_name}_coro_close_obj, {c_name}_coro_close);",
        ]

    def _emit_throw_method(self) -> list[str]:
        """Emit throw() method for coroutine.

        throw(type[, value[, traceback]]) raises an exception in the coroutine.
        For simplicity, we just mark it done and re-raise.
        """
        c_name = self.func_ir.c_name
        return [
            f"static mp_obj_t {c_name}_coro_throw(size_t n_args, const mp_obj_t *args) {{",
            f"    {c_name}_coro_t *self = MP_OBJ_TO_PTR(args[0]);",
            f"    self->state = {_GEN_DONE_STATE};",
            "    // Re-raise the exception (n_args >= 2: exception, n_args >= 3: traceback)",
            "    nlr_raise(args[1]);",
            "    return mp_const_none;",
            "}",
            f"static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({c_name}_coro_throw_obj, 2, 4, {c_name}_coro_throw);",
        ]

    def _emit_coroutine_type(self) -> list[str]:
        """Emit the coroutine type object with all methods."""
        c_name = self.func_ir.c_name
        return [
            f"static const mp_rom_map_elem_t {c_name}_coro_locals_dict_table[] = {{",
            f"    {{ MP_ROM_QSTR(MP_QSTR_send), MP_ROM_PTR(&{c_name}_coro_send_obj) }},",
            f"    {{ MP_ROM_QSTR(MP_QSTR___await__), MP_ROM_PTR(&{c_name}_coro_await_obj) }},",
            f"    {{ MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&{c_name}_coro_close_obj) }},",
            f"    {{ MP_ROM_QSTR(MP_QSTR_throw), MP_ROM_PTR(&{c_name}_coro_throw_obj) }},",
            "};",
            f"static MP_DEFINE_CONST_DICT({c_name}_coro_locals_dict, {c_name}_coro_locals_dict_table);",
            "",
            "MP_DEFINE_CONST_OBJ_TYPE(",
            f"    {c_name}_coro_type,",
            "    MP_QSTR_coroutine,",
            "    MP_TYPE_FLAG_ITER_IS_ITERNEXT,",
            f"    iter, {c_name}_coro_iternext,",
            f"    locals_dict, &{c_name}_coro_locals_dict",
            ");",
        ]

    def _emit_wrapper(self) -> tuple[list[str], str]:
        """Emit the wrapper function that creates the coroutine object."""
        signature, obj_def = self._emit_wrapper_signature()
        lines = [signature + " {"]
        lines.append(
            f"    {self.func_ir.c_name}_coro_t *coro = mp_obj_malloc({self.func_ir.c_name}_coro_t, &{self.func_ir.c_name}_coro_type);"
        )
        lines.append("    coro->state = 0;")
        lines.append("    coro->send_value = mp_const_none;")
        lines.append("    coro->_await_iter = mp_const_none;  // No active await")

        for name, c_type in self._all_gen_fields().items():
            if self._is_param_field(name):
                src = self._param_source_expr(name)
                lines.append(f"    coro->{name} = {self._unbox_arg(src, c_type)};")
            else:
                lines.append(f"    coro->{name} = {self._default_expr_for_type(c_type)};")

        lines.append("    return MP_OBJ_FROM_PTR(coro);")
        lines.append("}")
        return lines, obj_def
