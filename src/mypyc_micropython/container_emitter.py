"""
C code generation for container operations (list, dict).

This module generates MicroPython-compatible C code from expression-level
IR nodes (ListNewIR, DictNewIR, GetItemIR, SetItemIR, MethodCallIR, etc.).

The ContainerEmitter mirrors the ClassEmitter pattern: it takes IR nodes
and produces C code lines, with no knowledge of the AST.
"""

from __future__ import annotations

from collections.abc import Callable

from .ir import (
    AttrAccessIR,
    BinOpIR,
    BoxIR,
    CompareIR,
    ConstIR,
    DictNewIR,
    GetItemIR,
    InstrIR,
    IRType,
    ListCompIR,
    ListNewIR,
    MethodCallIR,
    NameIR,
    ParamAttrIR,
    SelfAttrIR,
    SetItemIR,
    SetNewIR,
    SubscriptIR,
    TempIR,
    TupleNewIR,
    UnaryOpIR,
    UnboxIR,
    ValueIR,
)


class ContainerEmitter:
    """Generates C code from expression-level IR instructions."""

    def emit_instr(self, instr: InstrIR) -> list[str]:
        """Dispatch an IR instruction to its specific emitter."""
        if isinstance(instr, ListNewIR):
            return self.emit_list_new(instr)
        elif isinstance(instr, TupleNewIR):
            return self.emit_tuple_new(instr)
        elif isinstance(instr, SetNewIR):
            return self.emit_set_new(instr)
        elif isinstance(instr, DictNewIR):
            return self.emit_dict_new(instr)
        elif isinstance(instr, GetItemIR):
            return self.emit_get_item(instr)
        elif isinstance(instr, SetItemIR):
            return self.emit_set_item(instr)
        elif isinstance(instr, MethodCallIR):
            return self.emit_method_call(instr)
        elif isinstance(instr, BoxIR):
            return self.emit_box(instr)
        elif isinstance(instr, UnboxIR):
            return self.emit_unbox(instr)
        elif isinstance(instr, AttrAccessIR):
            return self.emit_attr_access(instr)
        elif isinstance(instr, ListCompIR):
            return self.emit_list_comp(instr)
        return [f"    /* unsupported IR instruction: {type(instr).__name__} */"]

    def emit_prelude(self, prelude: list[InstrIR]) -> list[str]:
        """Emit all instructions in a prelude, in order."""
        lines: list[str] = []
        for instr in prelude:
            lines.extend(self.emit_instr(instr))
        return lines

    # ------------------------------------------------------------------
    # Instruction emitters
    # ------------------------------------------------------------------

    def emit_list_new(self, instr: ListNewIR) -> list[str]:
        """ListNewIR -> mp_obj_new_list(n, items)."""
        result_name = instr.result.name
        if not instr.items:
            return [f"    mp_obj_t {result_name} = mp_obj_new_list(0, NULL);"]

        items_str = ", ".join(self._box_value_ir(v) for v in instr.items)
        n = len(instr.items)
        return [
            f"    mp_obj_t {result_name}_items[] = {{{items_str}}};",
            f"    mp_obj_t {result_name} = mp_obj_new_list({n}, {result_name}_items);",
        ]

    def emit_tuple_new(self, instr: TupleNewIR) -> list[str]:
        """TupleNewIR -> mp_obj_new_tuple(n, items)."""
        result_name = instr.result.name
        if not instr.items:
            return [f"    mp_obj_t {result_name} = mp_const_empty_tuple;"]

        items_str = ", ".join(self._box_value_ir(v) for v in instr.items)
        n = len(instr.items)
        return [
            f"    mp_obj_t {result_name}_items[] = {{{items_str}}};",
            f"    mp_obj_t {result_name} = mp_obj_new_tuple({n}, {result_name}_items);",
        ]

    def emit_set_new(self, instr: SetNewIR) -> list[str]:
        """SetNewIR -> mp_obj_new_set(n, items)."""
        result_name = instr.result.name
        if not instr.items:
            return [f"    mp_obj_t {result_name} = mp_obj_new_set(0, NULL);"]

        items_str = ", ".join(self._box_value_ir(v) for v in instr.items)
        n = len(instr.items)
        return [
            f"    mp_obj_t {result_name}_items[] = {{{items_str}}};",
            f"    mp_obj_t {result_name} = mp_obj_new_set({n}, {result_name}_items);",
        ]

    def emit_dict_new(self, instr: DictNewIR) -> list[str]:
        """DictNewIR → mp_obj_new_dict + mp_obj_dict_store."""
        result_name = instr.result.name
        if not instr.entries:
            return [f"    mp_obj_t {result_name} = mp_obj_new_dict(0);"]

        lines = [f"    mp_obj_t {result_name} = mp_obj_new_dict({len(instr.entries)});"]
        for key_val, val_val in instr.entries:
            key_c = self._box_value_ir(key_val)
            val_c = self._box_value_ir(val_val)
            lines.append(f"    mp_obj_dict_store({result_name}, {key_c}, {val_c});")
        return lines

    def emit_get_item(self, instr: GetItemIR) -> list[str]:
        """GetItemIR → mp_obj_subscr(container, key, MP_OBJ_SENTINEL)."""
        result_name = instr.result.name
        container_c = self._value_to_c(instr.container)
        key_c = self._box_value_ir(instr.key)
        return [
            f"    mp_obj_t {result_name} = mp_obj_subscr({container_c}, {key_c}, MP_OBJ_SENTINEL);"
        ]

    def emit_set_item(self, instr: SetItemIR) -> list[str]:
        """SetItemIR → mp_obj_subscr(container, key, value)."""
        container_c = self._value_to_c(instr.container)
        key_c = self._box_value_ir(instr.key)
        val_c = self._box_value_ir(instr.value)
        return [f"    mp_obj_subscr({container_c}, {key_c}, {val_c});"]

    def emit_method_call(self, instr: MethodCallIR) -> list[str]:
        """MethodCallIR → method-specific C code via table dispatch."""
        method = instr.method
        receiver_c = self._value_to_c(instr.receiver)

        handler = _METHOD_TABLE.get(method)
        if handler is not None:
            return handler(self, instr, receiver_c)

        # Fallback: generic mp_load_method + mp_call_method pattern
        return self._emit_generic_method_call(instr, receiver_c)

    def emit_box(self, instr: BoxIR) -> list[str]:
        """BoxIR → mp_obj_new_int/float/bool."""
        result_name = instr.result.name
        src_c = self._value_to_c(instr.value)
        src_type = instr.value.ir_type
        boxed = self._box_expr(src_c, src_type)
        return [f"    mp_obj_t {result_name} = {boxed};"]

    def emit_unbox(self, instr: UnboxIR) -> list[str]:
        """UnboxIR → mp_obj_get_int/float/is_true."""
        result_name = instr.result.name
        src_c = self._value_to_c(instr.value)
        target = instr.target_type
        c_type = target.to_c_type_str()

        if target == IRType.INT:
            return [f"    {c_type} {result_name} = mp_obj_get_int({src_c});"]
        elif target == IRType.FLOAT:
            return [f"    {c_type} {result_name} = mp_get_float_checked({src_c});"]
        elif target == IRType.BOOL:
            return [f"    {c_type} {result_name} = mp_obj_is_true({src_c});"]
        return [f"    mp_obj_t {result_name} = {src_c};"]

    def emit_attr_access(self, instr: AttrAccessIR) -> list[str]:
        result_name = instr.result.name
        obj_c = self._value_to_c(instr.obj)
        c_type = instr.result_type.to_c_type_str()
        access_expr = f"(({instr.class_c_name}_obj_t *)MP_OBJ_TO_PTR({obj_c}))->{instr.attr_name}"
        return [f"    {c_type} {result_name} = {access_expr};"]

    def emit_list_comp(self, instr: ListCompIR) -> list[str]:
        """Emit list comprehension as inline loop.

        [expr for var in iterable] becomes:
        result = mp_obj_new_list(0, NULL);
        for (var ...) {
            // optional: if (condition)
            mp_obj_list_append(result, element);
        }
        """
        lines: list[str] = []
        result_name = instr.result.name

        # Create empty result list
        lines.append(f"    mp_obj_t {result_name} = mp_obj_new_list(0, NULL);")

        if instr.is_range:
            # Optimized range-based iteration
            lines.extend(self._emit_list_comp_range(instr, result_name))
        else:
            # Generic iterator-based iteration
            lines.extend(self._emit_list_comp_iter(instr, result_name))

        return lines

    def _emit_list_comp_range(self, instr: ListCompIR, result_name: str) -> list[str]:
        """Emit range-based list comprehension: [expr for i in range(...)]"""
        lines: list[str] = []
        c_loop_var = instr.c_loop_var

        # Declare loop variable
        lines.append(f"    mp_int_t {c_loop_var};")

        # Get range bounds
        start_c = self._value_to_c(instr.range_start) if instr.range_start else "0"
        end_c = self._value_to_c(instr.range_end) if instr.range_end else "0"

        # Store end in temp to avoid re-evaluation
        end_var = f"{result_name}_end"
        lines.append(f"    mp_int_t {end_var} = {end_c};")

        # Determine step and loop condition
        if instr.range_step is None:
            # Default step of 1
            cond = f"{c_loop_var} < {end_var}"
            inc = f"{c_loop_var}++"
        else:
            step_c = self._value_to_c(instr.range_step)
            # Check if step is a constant
            if isinstance(instr.range_step, ConstIR) and isinstance(instr.range_step.value, int):
                step_val = instr.range_step.value
                if step_val > 0:
                    cond = f"{c_loop_var} < {end_var}"
                else:
                    cond = f"{c_loop_var} > {end_var}"
                if step_val == 1:
                    inc = f"{c_loop_var}++"
                elif step_val == -1:
                    inc = f"{c_loop_var}--"
                else:
                    inc = f"{c_loop_var} += {step_val}"
            else:
                # Dynamic step - need runtime check
                step_var = f"{result_name}_step"
                lines.append(f"    mp_int_t {step_var} = {step_c};")
                cond = f"({step_var} > 0) ? ({c_loop_var} < {end_var}) : ({c_loop_var} > {end_var})"
                inc = f"{c_loop_var} += {step_var}"

        lines.append(f"    for ({c_loop_var} = {start_c}; {cond}; {inc}) {{")

        # Emit element prelude inside loop
        for pre_line in self.emit_prelude(instr.element_prelude):
            lines.append("    " + pre_line)

        # Handle condition if present
        if instr.condition is not None:
            # Emit condition prelude
            for pre_line in self.emit_prelude(instr.condition_prelude):
                lines.append("    " + pre_line)
            cond_c = self._value_to_c(instr.condition)
            # Convert to boolean if needed
            if instr.condition.ir_type != IRType.BOOL:
                cond_c = f"mp_obj_is_true({self._box_value_ir(instr.condition)})"
            lines.append(f"        if ({cond_c}) {{")
            element_c = self._box_value_ir(instr.element)
            lines.append(f"            mp_obj_list_append({result_name}, {element_c});")
            lines.append("        }")
        else:
            element_c = self._box_value_ir(instr.element)
            lines.append(f"        mp_obj_list_append({result_name}, {element_c});")

        lines.append("    }")
        return lines

    def _emit_list_comp_iter(self, instr: ListCompIR, result_name: str) -> list[str]:
        """Emit iterator-based list comprehension: [expr for x in iterable]"""
        lines: list[str] = []
        c_loop_var = instr.c_loop_var

        # Emit iter prelude (evaluate iterable)
        lines.extend(self.emit_prelude(instr.iter_prelude))

        # Get iterator
        iter_c = self._value_to_c(instr.iterable)
        iter_var = f"{result_name}_iter"
        iter_buf_var = f"{result_name}_iter_buf"

        # Declare loop variable
        lines.append(f"    mp_obj_t {c_loop_var};")
        lines.append(f"    mp_obj_iter_buf_t {iter_buf_var};")
        lines.append(f"    mp_obj_t {iter_var} = mp_getiter({iter_c}, &{iter_buf_var});")
        lines.append(
            f"    while (({c_loop_var} = mp_iternext({iter_var})) != MP_OBJ_STOP_ITERATION) {{"
        )

        # Emit element prelude inside loop
        for pre_line in self.emit_prelude(instr.element_prelude):
            lines.append("    " + pre_line)

        # Handle condition if present
        if instr.condition is not None:
            # Emit condition prelude
            for pre_line in self.emit_prelude(instr.condition_prelude):
                lines.append("    " + pre_line)
            cond_c = self._value_to_c(instr.condition)
            # Convert to boolean if needed
            if instr.condition.ir_type != IRType.BOOL:
                cond_c = f"mp_obj_is_true({self._box_value_ir(instr.condition)})"
            lines.append(f"        if ({cond_c}) {{")
            element_c = self._box_value_ir(instr.element)
            lines.append(f"            mp_obj_list_append({result_name}, {element_c});")
            lines.append("        }")
        else:
            element_c = self._box_value_ir(instr.element)
            lines.append(f"        mp_obj_list_append({result_name}, {element_c});")

        lines.append("    }")
        return lines

    # ------------------------------------------------------------------
    # Method call handlers (table-driven)
    # ------------------------------------------------------------------

    def _emit_append(self, instr: MethodCallIR, receiver: str) -> list[str]:
        arg = self._box_value_ir(instr.args[0]) if instr.args else "mp_const_none"
        result_part = ""
        if instr.result:
            result_part = f"mp_obj_t {instr.result.name} = "
        return [f"    {result_part}mp_obj_list_append({receiver}, {arg});"]

    def _emit_pop(self, instr: MethodCallIR, receiver: str) -> list[str]:
        n_args = len(instr.args)
        method_size = 2 + n_args

        if instr.result:
            result_name = instr.result.name
        else:
            result_name = "__pop_discard"

        # Build the statement block expression
        parts = [f"mp_obj_t __method[{method_size}]; "]
        parts.append(f"mp_load_method({receiver}, MP_QSTR_pop, __method); ")
        for i, arg in enumerate(instr.args):
            boxed = self._box_value_ir(arg)
            parts.append(f"__method[{2 + i}] = {boxed}; ")
        parts.append(f"mp_call_method_n_kw({n_args}, 0, __method); ")
        block = "".join(parts)
        return [f"    mp_obj_t {result_name} = ({{ {block}}});"]

    def _emit_get(self, instr: MethodCallIR, receiver: str) -> list[str]:
        result_name = instr.result.name if instr.result else "__get_discard"
        if len(instr.args) >= 2:
            key_c = self._box_value_ir(instr.args[0])
            default_c = self._box_value_ir(instr.args[1])
            return [
                f"    mp_obj_t {result_name} = "
                f"mp_call_function_n_kw(mp_load_attr({receiver}, MP_QSTR_get), "
                f"2, 0, (mp_obj_t[]){{{key_c}, {default_c}}});"
            ]
        elif len(instr.args) == 1:
            key_c = self._box_value_ir(instr.args[0])
            return [f"    mp_obj_t {result_name} = mp_obj_dict_get({receiver}, {key_c});"]
        return ["    /* get() requires at least 1 arg */"]

    def _emit_zero_arg_method(self, instr: MethodCallIR, receiver: str) -> list[str]:
        """keys, values, items, copy, clear, popitem — all zero-arg dispatches."""
        method = instr.method
        call = f"mp_call_function_0(mp_load_attr({receiver}, MP_QSTR_{method}))"
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_setdefault(self, instr: MethodCallIR, receiver: str) -> list[str]:
        result_name = instr.result.name if instr.result else "__sd_discard"
        if len(instr.args) >= 2:
            key_c = self._box_value_ir(instr.args[0])
            default_c = self._box_value_ir(instr.args[1])
            return [
                f"    mp_obj_t {result_name} = "
                f"mp_call_function_n_kw(mp_load_attr({receiver}, MP_QSTR_setdefault), "
                f"2, 0, (mp_obj_t[]){{{key_c}, {default_c}}});"
            ]
        elif len(instr.args) == 1:
            key_c = self._box_value_ir(instr.args[0])
            return [
                f"    mp_obj_t {result_name} = "
                f"mp_call_function_1(mp_load_attr({receiver}, MP_QSTR_setdefault), "
                f"{key_c});"
            ]
        return ["    /* setdefault() requires at least 1 arg */"]

    def _emit_update(self, instr: MethodCallIR, receiver: str) -> list[str]:
        if instr.args:
            arg_c = self._box_value_ir(instr.args[0])
            call = f"mp_call_function_1(mp_load_attr({receiver}, MP_QSTR_update), {arg_c})"
        else:
            call = f"mp_call_function_0(mp_load_attr({receiver}, MP_QSTR_update))"
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_set_add(self, instr: MethodCallIR, receiver: str) -> list[str]:
        arg = self._box_value_ir(instr.args[0]) if instr.args else "mp_const_none"
        if instr.result:
            return [
                f"    mp_obj_set_store({receiver}, {arg});",
                f"    mp_obj_t {instr.result.name} = mp_const_none;",
            ]
        return [f"    mp_obj_set_store({receiver}, {arg});"]

    def _emit_extend(self, instr: MethodCallIR, receiver: str) -> list[str]:
        """list.extend(iterable) -> mp_load_attr + mp_call_function_1."""
        if instr.args:
            arg_c = self._box_value_ir(instr.args[0])
            call = f"mp_call_function_1(mp_load_attr({receiver}, MP_QSTR_extend), {arg_c})"
        else:
            call = f"mp_call_function_0(mp_load_attr({receiver}, MP_QSTR_extend))"
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_insert(self, instr: MethodCallIR, receiver: str) -> list[str]:
        """list.insert(i, obj) -> mp_load_attr + mp_call_function_n_kw."""
        if len(instr.args) >= 2:
            idx_c = self._box_value_ir(instr.args[0])
            obj_c = self._box_value_ir(instr.args[1])
            call = (
                f"mp_call_function_n_kw(mp_load_attr({receiver}, MP_QSTR_insert), "
                f"2, 0, (mp_obj_t[]){{{idx_c}, {obj_c}}})"
            )
        else:
            call = "/* insert() requires 2 args */"
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_list_reverse(self, instr: MethodCallIR, receiver: str) -> list[str]:
        """list.reverse() -> mp_load_attr + mp_call_function_0."""
        call = f"mp_call_function_0(mp_load_attr({receiver}, MP_QSTR_reverse))"
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_list_sort(self, instr: MethodCallIR, receiver: str) -> list[str]:
        """list.sort() -> mp_load_attr + mp_call_function_0."""
        call = f"mp_call_function_0(mp_load_attr({receiver}, MP_QSTR_sort))"
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_one_arg_method(self, instr: MethodCallIR, receiver: str) -> list[str]:
        method = instr.method
        if instr.args:
            arg_c = self._box_value_ir(instr.args[0])
            call = f"mp_call_function_1(mp_load_attr({receiver}, MP_QSTR_{method}), {arg_c})"
        else:
            call = f"mp_call_function_0(mp_load_attr({receiver}, MP_QSTR_{method}))"
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_two_arg_method(self, instr: MethodCallIR, receiver: str) -> list[str]:
        """Handler for methods with 1 or 2 arguments (replace, find, etc.)."""
        method = instr.method
        n_args = len(instr.args)
        if n_args == 0:
            call = f"mp_call_function_0(mp_load_attr({receiver}, MP_QSTR_{method}))"
        elif n_args == 1:
            arg_c = self._box_value_ir(instr.args[0])
            call = f"mp_call_function_1(mp_load_attr({receiver}, MP_QSTR_{method}), {arg_c})"
        else:
            args_c = ", ".join(self._box_value_ir(a) for a in instr.args)
            call = (
                f"mp_call_function_n_kw(mp_load_attr({receiver}, MP_QSTR_{method}), "
                f"{n_args}, 0, (mp_obj_t[]){{{args_c}}})"
            )
        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = {call};"]
        return [f"    (void){call};"]

    def _emit_generic_method_call(self, instr: MethodCallIR, receiver: str) -> list[str]:
        """Fallback for unknown methods: mp_load_method + mp_call_method."""
        n_args = len(instr.args)
        method_size = 2 + n_args
        parts = [f"mp_obj_t __method[{method_size}]; "]
        parts.append(f"mp_load_method({receiver}, MP_QSTR_{instr.method}, __method); ")
        for i, arg in enumerate(instr.args):
            boxed = self._box_value_ir(arg)
            parts.append(f"__method[{2 + i}] = {boxed}; ")
        parts.append(f"mp_call_method_n_kw({n_args}, 0, __method); ")
        block = "".join(parts)

        if instr.result:
            return [f"    mp_obj_t {instr.result.name} = ({{ {block}}});"]
        return [f"    (void)({{ {block}}});"]

    # ------------------------------------------------------------------
    # Value helpers
    # ------------------------------------------------------------------

    def _value_to_c(self, value: ValueIR) -> str:
        """Convert a ValueIR to its C expression string."""
        if isinstance(value, TempIR):
            return value.name
        elif isinstance(value, NameIR):
            return value.c_name
        elif isinstance(value, ConstIR):
            return self._const_to_c(value)
        elif isinstance(value, BinOpIR):
            left = self._value_to_c(value.left)
            right = self._value_to_c(value.right)
            # Handle mp_obj_t operands - need mp_binary_op
            left_is_obj = value.left.ir_type == IRType.OBJ
            right_is_obj = value.right.ir_type == IRType.OBJ
            if left_is_obj or right_is_obj:
                # Box operands if needed
                if not left_is_obj:
                    left = self._box_expr(left, value.left.ir_type)
                if not right_is_obj:
                    right = self._box_expr(right, value.right.ir_type)
                op_map = {
                    "+": "MP_BINARY_OP_ADD",
                    "-": "MP_BINARY_OP_SUBTRACT",
                    "*": "MP_BINARY_OP_MULTIPLY",
                    "/": "MP_BINARY_OP_TRUE_DIVIDE",
                    "//": "MP_BINARY_OP_FLOOR_DIVIDE",
                    "%": "MP_BINARY_OP_MODULO",
                }
                mp_op = op_map.get(value.op, "MP_BINARY_OP_ADD")
                return f"mp_binary_op({mp_op}, {left}, {right})"
            return f"({left} {value.op} {right})"
        elif isinstance(value, UnaryOpIR):
            operand = self._value_to_c(value.operand)
            return f"({value.op}{operand})"
        elif isinstance(value, CompareIR):
            left = self._value_to_c(value.left)
            left_is_obj = value.left.ir_type == IRType.OBJ
            # Check if any operand is mp_obj_t
            any_obj = left_is_obj or any(
                comp.ir_type == IRType.OBJ for comp in value.comparators
            )
            if any_obj and len(value.ops) == 1:
                # Use mp_binary_op for mp_obj_t comparisons
                comp_c = self._value_to_c(value.comparators[0])
                # Box operands if needed
                if not left_is_obj:
                    left = self._box_expr(left, value.left.ir_type)
                if value.comparators[0].ir_type != IRType.OBJ:
                    comp_c = self._box_expr(comp_c, value.comparators[0].ir_type)
                op_map = {
                    ">": "MP_BINARY_OP_MORE",
                    "<": "MP_BINARY_OP_LESS",
                    ">=": "MP_BINARY_OP_MORE_EQUAL",
                    "<=": "MP_BINARY_OP_LESS_EQUAL",
                    "==": "MP_BINARY_OP_EQUAL",
                    "!=": "MP_BINARY_OP_NOT_EQUAL",
                }
                mp_op = op_map.get(value.ops[0], "MP_BINARY_OP_EQUAL")
                return f"mp_obj_is_true(mp_binary_op({mp_op}, {left}, {comp_c}))"
            parts = [f"({left}"]
            for op, comp in zip(value.ops, value.comparators):
                comp_c = self._value_to_c(comp)
                parts.append(f" {op} {comp_c}")
            parts.append(")")
            return "".join(parts)
        elif isinstance(value, SelfAttrIR):
            return f"self->{value.attr_path}"
        elif isinstance(value, ParamAttrIR):
            return (
                f"(({value.class_c_name}_obj_t *)MP_OBJ_TO_PTR({value.c_param_name}))"
                f"->{value.attr_name}"
            )
        elif isinstance(value, SubscriptIR):
            val_c = self._value_to_c(value.value)
            if value.is_rtuple and value.rtuple_index is not None:
                return f"{val_c}.f{value.rtuple_index}"
            slice_c = self._value_to_c(value.slice_)
            return f"mp_obj_subscr({val_c}, {self._box_expr(slice_c, value.slice_.ir_type)}, MP_OBJ_SENTINEL)"
        return "/* unknown value */"

    def _const_to_c(self, const: ConstIR) -> str:
        """Convert a ConstIR to its C literal string."""
        v = const.value
        if isinstance(v, bool):
            return "true" if v else "false"
        elif isinstance(v, int):
            return str(v)
        elif isinstance(v, float):
            return str(v)
        elif v is None:
            return "mp_const_none"
        elif isinstance(v, str):
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'mp_obj_new_str("{escaped}", {len(v)})'
        return "/* unknown const */"

    def _box_value_ir(self, value: ValueIR) -> str:
        """Return the C expression for a ValueIR, boxed to mp_obj_t."""
        c_expr = self._value_to_c(value)
        return self._box_expr(c_expr, value.ir_type)

    def _box_expr(self, c_expr: str, ir_type: IRType) -> str:
        """Box a C expression of the given IR type to mp_obj_t."""
        if ir_type == IRType.INT:
            return f"mp_obj_new_int({c_expr})"
        elif ir_type == IRType.FLOAT:
            return f"mp_obj_new_float({c_expr})"
        elif ir_type == IRType.BOOL:
            return f"({c_expr} ? mp_const_true : mp_const_false)"
        return c_expr  # already mp_obj_t


# Method dispatch table: method name -> handler
_METHOD_TABLE: dict[
    str,
    Callable[[ContainerEmitter, MethodCallIR, str], list[str]],
] = {
    # List methods
    "append": ContainerEmitter._emit_append,
    "pop": ContainerEmitter._emit_pop,
    "extend": ContainerEmitter._emit_extend,
    "insert": ContainerEmitter._emit_insert,
    "reverse": ContainerEmitter._emit_list_reverse,
    "sort": ContainerEmitter._emit_list_sort,
    # Dict methods
    "get": ContainerEmitter._emit_get,
    "keys": ContainerEmitter._emit_zero_arg_method,
    "values": ContainerEmitter._emit_zero_arg_method,
    "items": ContainerEmitter._emit_zero_arg_method,
    "copy": ContainerEmitter._emit_zero_arg_method,
    "clear": ContainerEmitter._emit_zero_arg_method,
    "popitem": ContainerEmitter._emit_zero_arg_method,
    "setdefault": ContainerEmitter._emit_setdefault,
    "update": ContainerEmitter._emit_update,
    # Set methods
    "add": ContainerEmitter._emit_set_add,
    "discard": ContainerEmitter._emit_one_arg_method,
    "remove": ContainerEmitter._emit_one_arg_method,
    # String methods - zero arg
    "upper": ContainerEmitter._emit_zero_arg_method,
    "lower": ContainerEmitter._emit_zero_arg_method,
    "isdigit": ContainerEmitter._emit_zero_arg_method,
    "isalpha": ContainerEmitter._emit_zero_arg_method,
    "isspace": ContainerEmitter._emit_zero_arg_method,
    "isupper": ContainerEmitter._emit_zero_arg_method,
    "islower": ContainerEmitter._emit_zero_arg_method,
    "isalnum": ContainerEmitter._emit_zero_arg_method,
    "isnumeric": ContainerEmitter._emit_zero_arg_method,
    "isdecimal": ContainerEmitter._emit_zero_arg_method,
    "isidentifier": ContainerEmitter._emit_zero_arg_method,
    "isprintable": ContainerEmitter._emit_zero_arg_method,
    "istitle": ContainerEmitter._emit_zero_arg_method,
    "title": ContainerEmitter._emit_zero_arg_method,
    "capitalize": ContainerEmitter._emit_zero_arg_method,
    "casefold": ContainerEmitter._emit_zero_arg_method,
    "swapcase": ContainerEmitter._emit_zero_arg_method,
    "splitlines": ContainerEmitter._emit_one_arg_method,
    # String methods - one/two arg
    "strip": ContainerEmitter._emit_one_arg_method,
    "lstrip": ContainerEmitter._emit_one_arg_method,
    "rstrip": ContainerEmitter._emit_one_arg_method,
    "startswith": ContainerEmitter._emit_one_arg_method,
    "endswith": ContainerEmitter._emit_one_arg_method,
    "join": ContainerEmitter._emit_one_arg_method,
    "encode": ContainerEmitter._emit_two_arg_method,
    # String methods - variable args
    "split": ContainerEmitter._emit_two_arg_method,
    "rsplit": ContainerEmitter._emit_two_arg_method,
    "find": ContainerEmitter._emit_two_arg_method,
    "rfind": ContainerEmitter._emit_two_arg_method,
    "index": ContainerEmitter._emit_two_arg_method,
    "rindex": ContainerEmitter._emit_two_arg_method,
    "count": ContainerEmitter._emit_two_arg_method,
    "replace": ContainerEmitter._emit_two_arg_method,
    "partition": ContainerEmitter._emit_one_arg_method,
    "rpartition": ContainerEmitter._emit_one_arg_method,
    "center": ContainerEmitter._emit_two_arg_method,
    "ljust": ContainerEmitter._emit_two_arg_method,
    "rjust": ContainerEmitter._emit_two_arg_method,
    "zfill": ContainerEmitter._emit_one_arg_method,
    "expandtabs": ContainerEmitter._emit_one_arg_method,
}
