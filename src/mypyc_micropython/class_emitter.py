"""
C code generation for classes.

This module generates MicroPython-compatible C code for Python classes,
including structs, vtables, constructors, and method wrappers.
"""

from __future__ import annotations

from .ir import ClassIR, CType, PropertyInfo


class ClassEmitter:
    """Generates C code for a single class."""

    def __init__(self, class_ir: ClassIR, module_c_name: str):
        self.class_ir = class_ir
        self.module_c_name = module_c_name
        self.c_name = class_ir.c_name

    def _vtable_access_path(self) -> str:
        """Compute the C access path for the vtable pointer.

        Base class: 'vtable'
        Child class: 'super.vtable'
        Grandchild: 'super.super.vtable'
        """
        depth = 0
        cls = self.class_ir
        while cls.base:
            depth += 1
            cls = cls.base
        if depth == 0:
            return "vtable"
        return "super." * depth + "vtable"

    def _root_class_c_name(self) -> str:
        cls = self.class_ir
        while cls.base:
            cls = cls.base
        return cls.c_name

    def emit_forward_declarations(self) -> list[str]:
        lines = []
        lines.append(f"typedef struct _{self.c_name}_obj_t {self.c_name}_obj_t;")

        vtable_entries = self.class_ir.get_vtable_entries()
        if vtable_entries:
            lines.append(f"typedef struct _{self.c_name}_vtable_t {self.c_name}_vtable_t;")

        return lines

    def emit_struct(self) -> list[str]:
        lines = []
        vtable_entries = self.class_ir.get_vtable_entries()

        if vtable_entries:
            lines.append(f"struct _{self.c_name}_vtable_t {{")
            for method_name, method_ir in vtable_entries:
                ret_type = method_ir.return_type.to_c_type_str()
                params = [f"{self.c_name}_obj_t *self"]
                for param_name, param_type in method_ir.params:
                    params.append(f"{param_type.to_c_type_str()} {param_name}")
                params_str = ", ".join(params)
                lines.append(f"    {ret_type} (*{method_name})({params_str});")
            lines.append("};")
            lines.append("")

        lines.append(f"struct _{self.c_name}_obj_t {{")

        if self.class_ir.base:
            lines.append(f"    {self.class_ir.base.c_name}_obj_t super;")
        else:
            lines.append("    mp_obj_base_t base;")
            if vtable_entries:
                lines.append(f"    const {self.c_name}_vtable_t *vtable;")

        for fld in self.class_ir.fields:
            lines.append(f"    {fld.get_c_type_str()} {fld.name};")

        lines.append("};")
        lines.append("")

        return lines

    def emit_field_descriptors(self) -> list[str]:
        fields_with_path = self.class_ir.get_all_fields_with_path()
        if not fields_with_path:
            return []

        lines = []
        lines.append("typedef struct {")
        lines.append("    qstr name;")
        lines.append("    uint16_t offset;")
        lines.append("    uint8_t type;")
        lines.append(f"}} {self.c_name}_field_t;")
        lines.append("")

        lines.append(f"static const {self.c_name}_field_t {self.c_name}_fields[] = {{")

        for fld, path in fields_with_path:
            type_id = fld.c_type.to_field_type_id()
            lines.append(
                f"    {{ MP_QSTR_{fld.name}, offsetof({self.c_name}_obj_t, {path}), {type_id} }},"
            )

        lines.append("    { MP_QSTR_NULL, 0, 0 }")
        lines.append("};")
        lines.append("")

        return lines

    def emit_attr_handler(self) -> list[str]:
        all_fields = self.class_ir.get_all_fields()
        all_properties = self.class_ir.get_all_properties()
        if not all_fields:
            return self._emit_simple_attr_handler()

        lines = []
        lines.append(
            f"static void {self.c_name}_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {{"
        )
        lines.append(f"    {self.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
        lines.append("")
        lines.extend(self._emit_property_dispatch(all_properties))
        lines.append(
            f"    for (const {self.c_name}_field_t *f = {self.c_name}_fields; f->name != MP_QSTR_NULL; f++) {{"
        )
        lines.append("        if (f->name == attr) {")
        lines.append("            if (dest[0] == MP_OBJ_NULL) {")
        lines.append("                char *ptr = (char *)self + f->offset;")
        lines.append("                switch (f->type) {")
        lines.append("                    case 0: dest[0] = *(mp_obj_t *)ptr; break;")
        lines.append(
            "                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;"
        )
        lines.append(
            "                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;"
        )
        lines.append(
            "                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;"
        )
        lines.append("                }")
        lines.append("            } else if (dest[1] != MP_OBJ_NULL) {")
        lines.append("                char *ptr = (char *)self + f->offset;")
        lines.append("                switch (f->type) {")
        lines.append("                    case 0: *(mp_obj_t *)ptr = dest[1]; break;")
        lines.append(
            "                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;"
        )
        lines.append(
            "                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;"
        )
        lines.append("                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;")
        lines.append("                }")
        lines.append("                dest[0] = MP_OBJ_NULL;")
        lines.append("            }")
        lines.append("            return;")
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append("    dest[1] = MP_OBJ_SENTINEL;")
        lines.append("}")
        lines.append("")

        return lines

    def _emit_simple_attr_handler(self) -> list[str]:
        all_properties = self.class_ir.get_all_properties()
        lines = []
        lines.append(
            f"static void {self.c_name}_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {{"
        )
        if all_properties:
            lines.append(f"    {self.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
            lines.append("")
            lines.extend(self._emit_property_dispatch(all_properties))
        lines.append("    dest[1] = MP_OBJ_SENTINEL;")
        lines.append("}")
        lines.append("")
        return lines

    def _box_property_result(self, c_type: CType, expr: str) -> str:
        if c_type == CType.MP_INT_T:
            return f"mp_obj_new_int({expr})"
        if c_type == CType.MP_FLOAT_T:
            return f"mp_obj_new_float({expr})"
        if c_type == CType.BOOL:
            return f"{expr} ? mp_const_true : mp_const_false"
        if c_type == CType.VOID:
            return "mp_const_none"
        return expr

    def _unbox_property_value(self, c_type: CType, expr: str) -> str:
        if c_type == CType.MP_INT_T:
            return f"mp_obj_get_int({expr})"
        if c_type == CType.MP_FLOAT_T:
            return f"mp_obj_get_float({expr})"
        if c_type == CType.BOOL:
            return f"mp_obj_is_true({expr})"
        return expr

    def _property_self_expr(self, method_c_name: str, prop_name: str, setter: bool = False) -> str:
        suffix = f"_{prop_name}_setter" if setter else f"_{prop_name}"
        owner_c_name = self.c_name
        if method_c_name.endswith(suffix):
            owner_c_name = method_c_name[: -len(suffix)]
        if owner_c_name == self.c_name:
            return "self"
        return f"({owner_c_name}_obj_t *)self"

    def _emit_property_dispatch(self, properties: dict[str, PropertyInfo]) -> list[str]:
        if not properties:
            return []

        lines = []
        for prop_name, prop in properties.items():
            lines.append(f"    if (attr == MP_QSTR_{prop_name}) {{")
            lines.append("        if (dest[0] == MP_OBJ_NULL) {")
            getter_self = self._property_self_expr(prop.getter.c_name, prop_name)
            getter_call = f"{prop.getter.c_name}_native({getter_self})"
            lines.append(
                f"            dest[0] = {self._box_property_result(prop.getter.return_type, getter_call)};"
            )
            lines.append("            return;")
            lines.append("        }")
            lines.append("        if (dest[1] != MP_OBJ_NULL) {")
            if prop.setter and prop.setter.params:
                setter_arg_type = prop.setter.params[0][1]
                setter_arg = self._unbox_property_value(setter_arg_type, "dest[1]")
                setter_self = self._property_self_expr(prop.setter.c_name, prop_name, setter=True)
                lines.append(
                    f"            {prop.setter.c_name}_native({setter_self}, {setter_arg});"
                )
                lines.append("            dest[0] = MP_OBJ_NULL;")
            else:
                lines.append("            dest[1] = MP_OBJ_SENTINEL;")
            lines.append("            return;")
            lines.append("        }")
            lines.append("    }")
            lines.append("")
        return lines

    def emit_make_new(self) -> list[str]:
        lines = []
        vtable_entries = self.class_ir.get_vtable_entries()

        if self.class_ir.is_dataclass and self.class_ir.dataclass_info:
            return self._emit_dataclass_make_new()

        init_method = self.class_ir.methods.get("__init__")

        lines.append(
            f"static mp_obj_t {self.c_name}_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {{"
        )

        if init_method:
            num_params = len(init_method.params)
            lines.append(f"    mp_arg_check_num(n_args, n_kw, {num_params}, {num_params}, false);")
        else:
            lines.append("    mp_arg_check_num(n_args, n_kw, 0, 0, false);")

        lines.append("")
        lines.append(f"    {self.c_name}_obj_t *self = mp_obj_malloc({self.c_name}_obj_t, type);")

        if vtable_entries:
            vtable_path = self._vtable_access_path()
            if self.class_ir.base:
                root_c = self._root_class_c_name()
                lines.append(
                    f"    self->{vtable_path} = (const {root_c}_vtable_t *)&{self.c_name}_vtable_inst;"
                )
            else:
                lines.append(f"    self->{vtable_path} = &{self.c_name}_vtable_inst;")

        for fld in self.class_ir.fields:
            if fld.c_type == CType.MP_OBJ_T:
                lines.append(f"    self->{fld.name} = mp_const_none;")
            elif fld.c_type == CType.MP_INT_T:
                lines.append(f"    self->{fld.name} = 0;")
            elif fld.c_type == CType.MP_FLOAT_T:
                lines.append(f"    self->{fld.name} = 0.0;")
            elif fld.c_type == CType.BOOL:
                lines.append(f"    self->{fld.name} = false;")

        if init_method:
            total_args = len(init_method.params) + 1
            lines.append("")
            if total_args > 3:
                # VAR_BETWEEN calling convention: (size_t n_args, const mp_obj_t *args)
                lines.append(f"    mp_obj_t init_args[{total_args}];")
                lines.append("    init_args[0] = MP_OBJ_FROM_PTR(self);")
                for i in range(len(init_method.params)):
                    lines.append(f"    init_args[{i + 1}] = args[{i}];")
                lines.append(f"    {self.c_name}___init___mp({total_args}, init_args);")
            else:
                args_list = ["MP_OBJ_FROM_PTR(self)"]
                for i in range(len(init_method.params)):
                    args_list.append(f"args[{i}]")
                args_str = ", ".join(args_list)
                lines.append(f"    {self.c_name}___init___mp({args_str});")

        lines.append("")
        lines.append("    return MP_OBJ_FROM_PTR(self);")
        lines.append("}")
        lines.append("")

        return lines

    def _emit_dataclass_make_new(self) -> list[str]:
        lines = []
        fields_with_path = self.class_ir.get_all_fields_with_path()
        vtable_entries = self.class_ir.get_vtable_entries()

        lines.append(
            f"static mp_obj_t {self.c_name}_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {{"
        )

        lines.append("    enum {")
        for fld, _ in fields_with_path:
            lines.append(f"        ARG_{fld.name},")
        lines.append("    };")

        lines.append("    static const mp_arg_t allowed_args[] = {")
        for fld, _ in fields_with_path:
            if fld.c_type == CType.MP_INT_T:
                if fld.has_default:
                    lines.append(
                        f"        {{ MP_QSTR_{fld.name}, MP_ARG_INT, {{.u_int = {fld.default_value}}} }},"
                    )
                else:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_INT }},")
            elif fld.c_type == CType.MP_FLOAT_T:
                if fld.has_default:
                    lines.append(
                        f"        {{ MP_QSTR_{fld.name}, MP_ARG_OBJ, {{.u_obj = mp_const_none}} }},"
                    )
                else:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_OBJ }},")
            elif fld.c_type == CType.BOOL:
                if fld.has_default:
                    default_val = "true" if fld.default_value else "false"
                    lines.append(
                        f"        {{ MP_QSTR_{fld.name}, MP_ARG_BOOL, {{.u_bool = {default_val}}} }},"
                    )
                else:
                    lines.append(
                        f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_BOOL }},"
                    )
            else:
                if fld.has_default:
                    lines.append(
                        f"        {{ MP_QSTR_{fld.name}, MP_ARG_OBJ, {{.u_obj = mp_const_none}} }},"
                    )
                else:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_OBJ }},")
        lines.append("    };")
        lines.append("")

        lines.append(f"    mp_arg_val_t parsed[{len(fields_with_path)}];")
        lines.append(
            f"    mp_arg_parse_all_kw_array(n_args, n_kw, args, {len(fields_with_path)}, allowed_args, parsed);"
        )
        lines.append("")

        lines.append(f"    {self.c_name}_obj_t *self = mp_obj_malloc({self.c_name}_obj_t, type);")

        if vtable_entries:
            vtable_path = self._vtable_access_path()
            if self.class_ir.base:
                root_c = self._root_class_c_name()
                lines.append(
                    f"    self->{vtable_path} = (const {root_c}_vtable_t *)&{self.c_name}_vtable_inst;"
                )
            else:
                lines.append(f"    self->{vtable_path} = &{self.c_name}_vtable_inst;")

        for fld, path in fields_with_path:
            if fld.c_type == CType.MP_INT_T:
                lines.append(f"    self->{path} = parsed[ARG_{fld.name}].u_int;")
            elif fld.c_type == CType.MP_FLOAT_T:
                lines.append(f"    self->{path} = mp_obj_get_float(parsed[ARG_{fld.name}].u_obj);")
            elif fld.c_type == CType.BOOL:
                lines.append(f"    self->{path} = parsed[ARG_{fld.name}].u_bool;")
            else:
                lines.append(f"    self->{path} = parsed[ARG_{fld.name}].u_obj;")

        lines.append("")
        lines.append("    return MP_OBJ_FROM_PTR(self);")
        lines.append("}")
        lines.append("")

        return lines

    def emit_print_handler(self) -> list[str]:
        has_user_repr = self.class_ir.has_repr
        has_user_str = self.class_ir.has_str
        has_dataclass_repr = (
            self.class_ir.is_dataclass
            and self.class_ir.dataclass_info
            and self.class_ir.dataclass_info.repr_
            and not has_user_repr
        )

        # Case 1: User-defined __str__ and/or __repr__
        if has_user_str or has_user_repr:
            return self._emit_user_print_handler(has_user_str, has_user_repr)

        # Case 2: Dataclass auto-generated repr (no user override)
        if has_dataclass_repr:
            return self._emit_dataclass_print_handler()

        return []

    def _emit_user_print_handler(
        self, has_str: bool, has_repr: bool
    ) -> list[str]:
        """Emit print handler that dispatches to user __str__/__repr__ methods."""
        lines: list[str] = []
        repr_c_name = self.class_ir.methods.get("__repr__")
        str_c_name = self.class_ir.methods.get("__str__")

        lines.append(
            f"static void {self.c_name}_print(const mp_print_t *print, "
            f"mp_obj_t self_in, mp_print_kind_t kind) {{"
        )

        if has_str and has_repr:
            # Dispatch based on kind
            assert repr_c_name is not None
            assert str_c_name is not None
            lines.append("    mp_obj_t result;")
            lines.append("    if (kind == PRINT_STR) {")
            lines.append(f"        result = {str_c_name.c_name}_mp(self_in);")
            lines.append("    } else {")
            lines.append(f"        result = {repr_c_name.c_name}_mp(self_in);")
            lines.append("    }")
            lines.append("    mp_obj_print_helper(print, result, PRINT_STR);")
        elif has_repr:
            # __repr__ only: Python semantics -- str() falls back to repr()
            assert repr_c_name is not None
            lines.append("    (void)kind;")
            lines.append(
                f"    mp_obj_t result = {repr_c_name.c_name}_mp(self_in);"
            )
            lines.append("    mp_obj_print_helper(print, result, PRINT_STR);")
        else:
            # __str__ only: use for PRINT_STR, default for PRINT_REPR
            assert str_c_name is not None
            lines.append("    if (kind == PRINT_STR) {")
            lines.append(
                f"        mp_obj_t result = {str_c_name.c_name}_mp(self_in);"
            )
            lines.append("        mp_obj_print_helper(print, result, PRINT_STR);")
            lines.append("    } else {")
            lines.append(
                f'        mp_printf(print, "<{self.class_ir.name} object>");'
            )
            lines.append("    }")

        lines.append("}")
        lines.append("")
        return lines

    def _emit_dataclass_print_handler(self) -> list[str]:
        """Emit auto-generated print handler for @dataclass classes."""
        lines: list[str] = []
        fields_with_path = self.class_ir.get_all_fields_with_path()

        lines.append(
            f"static void {self.c_name}_print(const mp_print_t *print, "
            f"mp_obj_t self_in, mp_print_kind_t kind) {{"
        )
        lines.append(f"    {self.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
        lines.append("    (void)kind;")
        lines.append(f'    mp_printf(print, "{self.class_ir.name}(");')

        for i, (fld, path) in enumerate(fields_with_path):
            separator = ", " if i > 0 else ""
            if fld.c_type == CType.MP_INT_T:
                lines.append(
                    f'    mp_printf(print, "{separator}{fld.name}=%d", (int)self->{path});'
                )
            elif fld.c_type == CType.MP_FLOAT_T:
                lines.append(f'    mp_printf(print, "{separator}{fld.name}=");')
                lines.append(
                    f"    mp_obj_print_helper(print, mp_obj_new_float(self->{path}), PRINT_REPR);"
                )
            elif fld.c_type == CType.BOOL:
                lines.append(
                    f'    mp_printf(print, "{separator}{fld.name}=%s", self->{path} ? "True" : "False");'
                )
            else:
                lines.append(f'    mp_printf(print, "{separator}{fld.name}=");')
                lines.append(f"    mp_obj_print_helper(print, self->{path}, PRINT_REPR);")

        lines.append('    mp_printf(print, ")");')
        lines.append("}")
        lines.append("")
        return lines

    def _has_user_comparison_methods(self) -> bool:
        """Check if this class has any user-defined comparison methods."""
        return (
            self.class_ir.has_eq
            or self.class_ir.has_ne
            or self.class_ir.has_lt
            or self.class_ir.has_le
            or self.class_ir.has_gt
            or self.class_ir.has_ge
        )

    def _has_dataclass_eq(self) -> bool:
        """Check if this is a dataclass with auto-generated __eq__."""
        return (
            self.class_ir.is_dataclass
            and self.class_ir.dataclass_info is not None
            and self.class_ir.dataclass_info.eq
            and not self.class_ir.has_eq  # No user override
        )

    def emit_binary_op_handler(self) -> list[str]:
        """Emit binary_op handler for comparison operators."""
        has_user_comparisons = self._has_user_comparison_methods()
        has_dataclass_eq = self._has_dataclass_eq()

        if not has_user_comparisons and not has_dataclass_eq:
            return []

        lines: list[str] = []
        lines.append(
            f"static mp_obj_t {self.c_name}_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {{"
        )

        # Map of comparison ops to methods
        comparison_ops = [
            ("MP_BINARY_OP_EQUAL", "__eq__", self.class_ir.has_eq),
            ("MP_BINARY_OP_NOT_EQUAL", "__ne__", self.class_ir.has_ne),
            ("MP_BINARY_OP_LESS", "__lt__", self.class_ir.has_lt),
            ("MP_BINARY_OP_LESS_EQUAL", "__le__", self.class_ir.has_le),
            ("MP_BINARY_OP_MORE", "__gt__", self.class_ir.has_gt),
            ("MP_BINARY_OP_MORE_EQUAL", "__ge__", self.class_ir.has_ge),
        ]

        # Emit dispatch for user-defined comparison methods
        for mp_op, py_method, has_method in comparison_ops:
            if has_method and py_method in self.class_ir.methods:
                method_ir = self.class_ir.methods[py_method]
                lines.append(f"    if (op == {mp_op}) {{")
                lines.append(f"        return {method_ir.c_name}_mp(lhs_in, rhs_in);")
                lines.append("    }")

        # Handle dataclass auto-generated __eq__
        if has_dataclass_eq:
            lines.append("    if (op == MP_BINARY_OP_EQUAL) {")
            lines.append("        if (!mp_obj_is_type(rhs_in, mp_obj_get_type(lhs_in))) {")
            lines.append("            return mp_const_false;")
            lines.append("        }")
            lines.append(f"        {self.c_name}_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);")
            lines.append(f"        {self.c_name}_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);")

            fields_with_path = self.class_ir.get_all_fields_with_path()
            conditions = []
            for fld, path in fields_with_path:
                if fld.c_type == CType.MP_OBJ_T:
                    conditions.append(f"mp_obj_equal(lhs->{path}, rhs->{path})")
                else:
                    conditions.append(f"lhs->{path} == rhs->{path}")

            if conditions:
                cond_str = " &&\n            ".join(conditions)
                lines.append("        return mp_obj_new_bool(")
                lines.append(f"            {cond_str}")
                lines.append("        );")
            else:
                lines.append("        return mp_const_true;")
            lines.append("    }")

        # Return NULL for unsupported operations
        lines.append("    return MP_OBJ_NULL;")
        lines.append("}")
        lines.append("")

        return lines

    def emit_unary_op_handler(self) -> list[str]:
        """Emit unary_op handler for __hash__."""
        if not self.class_ir.has_hash:
            return []

        if "__hash__" not in self.class_ir.methods:
            return []

        lines: list[str] = []
        method_ir = self.class_ir.methods["__hash__"]

        lines.append(
            f"static mp_obj_t {self.c_name}_unary_op(mp_unary_op_t op, mp_obj_t self_in) {{"
        )
        lines.append("    if (op == MP_UNARY_OP_HASH) {")
        lines.append(f"        return {method_ir.c_name}_mp(self_in);")
        lines.append("    }")
        lines.append("    return MP_OBJ_NULL;")
        lines.append("}")
        lines.append("")

        return lines

    def emit_iter_handlers(self) -> list[str]:
        """Emit getiter and iternext handlers for __iter__ and __next__."""
        if not self.class_ir.has_iter and not self.class_ir.has_next:
            return []

        lines: list[str] = []

        is_self_iterator = self.class_ir.has_iter and self.class_ir.has_next

        if is_self_iterator:
            # Common case: __iter__ returns self, __next__ does the work.
            # Use MP_TYPE_FLAG_ITER_IS_ITERNEXT: the single iter slot IS the
            # iternext function and MicroPython auto-returns self for getiter.
            pass
        elif self.class_ir.has_iter and "__iter__" in self.class_ir.methods:
            # __iter__ only (no __next__): emit a getiter wrapper
            method_ir = self.class_ir.methods["__iter__"]
            lines.append(
                f"static mp_obj_t {self.c_name}_getiter(mp_obj_t self_in, mp_obj_iter_buf_t *iter_buf) {{"
            )
            lines.append("    (void)iter_buf;")
            lines.append(f"    return {method_ir.c_name}_mp(self_in);")
            lines.append("}")
            lines.append("")

        # Emit iternext handler for __next__
        if self.class_ir.has_next and "__next__" in self.class_ir.methods:
            method_ir = self.class_ir.methods["__next__"]
            lines.append(
                f"static mp_obj_t {self.c_name}_iternext(mp_obj_t self_in) {{"
            )
            # Call the user's __next__ method, which should raise StopIteration
            # when done. We need to catch that and return MP_OBJ_STOP_ITERATION.
            lines.append("    nlr_buf_t nlr;")
            lines.append("    if (nlr_push(&nlr) == 0) {")
            lines.append(f"        mp_obj_t result = {method_ir.c_name}_mp(self_in);")
            lines.append("        nlr_pop();")
            lines.append("        return result;")
            lines.append("    } else {")
            lines.append("        // Check if StopIteration was raised")
            lines.append("        mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);")
            lines.append("        if (mp_obj_is_subclass_fast(MP_OBJ_FROM_PTR(mp_obj_get_type(exc)), MP_OBJ_FROM_PTR(&mp_type_StopIteration))) {")
            lines.append("            return MP_OBJ_STOP_ITERATION;")
            lines.append("        }")
            lines.append("        // Re-raise other exceptions")
            lines.append("        nlr_jump(nlr.ret_val);")
            lines.append("    }")
            lines.append("}")
            lines.append("")

        # For MP_TYPE_FLAG_ITER_IS_CUSTOM: emit the getiter_iternext struct
        if is_self_iterator:
            # Self-iterator: no struct needed, use MP_TYPE_FLAG_ITER_IS_ITERNEXT
            pass
        elif self.class_ir.has_iter and self.class_ir.has_next:
            # Custom: separate getiter and iternext
            lines.append(
                f"static const mp_getiter_iternext_custom_t {self.c_name}_iter_custom = {{"
            )
            lines.append(f"    .getiter = {self.c_name}_getiter,")
            lines.append(f"    .iternext = {self.c_name}_iternext,")
            lines.append("}};")
            lines.append("")

        return lines

    def emit_vtable_instance(self) -> list[str]:
        vtable_entries = self.class_ir.get_vtable_entries()
        if not vtable_entries:
            return []

        lines = []
        lines.append(f"static const {self.c_name}_vtable_t {self.c_name}_vtable_inst = {{")

        for method_name, method_ir in vtable_entries:
            # Check if method belongs to a parent class (needs cast)
            method_belongs_to_parent = not method_ir.c_name.startswith(self.c_name + "_")

            if method_belongs_to_parent:
                # Build cast to child's function pointer type
                ret_type = method_ir.return_type.to_c_type_str()
                params = [f"{self.c_name}_obj_t *"]
                for _, param_type in method_ir.params:
                    params.append(param_type.to_c_type_str())
                params_str = ", ".join(params)
                cast = f"({ret_type} (*)({params_str}))"
                lines.append(f"    .{method_name} = {cast}{method_ir.c_name}_native,")
            else:
                lines.append(f"    .{method_name} = {method_ir.c_name}_native,")

        lines.append("};")
        lines.append("")

        return lines

    def emit_locals_dict(self) -> list[str]:
        # Get all methods including inherited ones
        all_methods = self.class_ir.get_all_methods()
        method_names = [
            name
            for name, method in all_methods.items()
            if not method.is_property
            and not name.startswith("_prop_")
            and (
                method.is_static
                or method.is_classmethod
                or not name.startswith("__")
                or name in ("__len__", "__getitem__", "__setitem__")
            )
        ]

        if not method_names:
            return []

        lines = []
        for name in method_names:
            method = all_methods[name]
            if method.is_static or method.is_classmethod:
                # Only emit wrapper struct if method belongs to this class (not inherited)
                is_own_method = name in self.class_ir.methods
                if is_own_method:
                    lines.append(
                        f"static const mp_rom_obj_static_class_method_t {method.c_name}_obj = {{"
                    )
                    method_type = "mp_type_staticmethod" if method.is_static else "mp_type_classmethod"
                    lines.append(f"    {{&{method_type}}}, MP_ROM_PTR(&{method.c_name}_fun_obj)")
                    lines.append("};")
        if any(
            all_methods[name].is_static or all_methods[name].is_classmethod for name in method_names
        ):
            lines.append("")

        lines.append(f"static const mp_rom_map_elem_t {self.c_name}_locals_dict_table[] = {{")
        for name in method_names:
            method = all_methods[name]
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&{method.c_name}_obj) }},"
            )
        lines.append("};")

        lines.append(
            f"static MP_DEFINE_CONST_DICT({self.c_name}_locals_dict, {self.c_name}_locals_dict_table);"
        )
        lines.append("")

        return lines

    def emit_type_definition(self) -> list[str]:
        lines = []

        slots = []
        slots.append(f"    make_new, {self.c_name}_make_new")

        if self.class_ir.get_all_fields() or self.class_ir.get_all_properties():
            slots.append(f"    attr, {self.c_name}_attr")

        # Add print slot when we have a print handler
        has_user_repr = self.class_ir.has_repr
        has_user_str = self.class_ir.has_str
        has_dataclass_repr = (
            self.class_ir.is_dataclass
            and self.class_ir.dataclass_info
            and self.class_ir.dataclass_info.repr_
            and not has_user_repr
        )
        if has_user_str or has_user_repr or has_dataclass_repr:
            slots.append(f"    print, {self.c_name}_print")

        # Add binary_op slot for comparison methods
        has_binary_op = (
            self._has_user_comparison_methods()
            or self._has_dataclass_eq()
        )
        if has_binary_op:
            slots.append(f"    binary_op, {self.c_name}_binary_op")

        # Add unary_op slot for __hash__
        if self.class_ir.has_hash:
            slots.append(f"    unary_op, {self.c_name}_unary_op")

        # Add iter slot for __iter__ and/or __next__
        is_self_iterator = self.class_ir.has_iter and self.class_ir.has_next
        if is_self_iterator:
            # Self-iterator: iter slot = iternext function
            # Flag MP_TYPE_FLAG_ITER_IS_ITERNEXT makes getiter return self
            slots.append(f"    iter, {self.c_name}_iternext")
        elif self.class_ir.has_next:
            # __next__ only: use ITER_IS_ITERNEXT
            slots.append(f"    iter, {self.c_name}_iternext")
        elif self.class_ir.has_iter:
            # __iter__ only: use default getiter
            slots.append(f"    iter, {self.c_name}_getiter")
        if self.class_ir.base:
            slots.append(f"    parent, &{self.class_ir.base.c_name}_type")

        all_methods = self.class_ir.get_all_methods()
        method_names = [
            name
            for name, method in all_methods.items()
            if not method.is_property
            and not name.startswith("_prop_")
            and (
                method.is_static
                or method.is_classmethod
                or not name.startswith("__")
                or name in ("__len__", "__getitem__", "__setitem__")
            )
        ]
        if method_names:
            slots.append(f"    locals_dict, &{self.c_name}_locals_dict")

        slots_str = ",\n".join(slots)

        # Determine type flags
        has_iternext = self.class_ir.has_next
        if has_iternext:
            type_flags = "MP_TYPE_FLAG_ITER_IS_ITERNEXT"
        else:
            type_flags = "MP_TYPE_FLAG_NONE"

        lines.append("MP_DEFINE_CONST_OBJ_TYPE(")
        lines.append(f"    {self.c_name}_type,")
        lines.append(f"    MP_QSTR_{self.class_ir.name},")
        lines.append(f"    {type_flags},")
        lines.append(slots_str)
        lines.append(");")
        lines.append("")

        return lines

    def emit_all(self) -> str:
        sections = []

        sections.extend(self.emit_struct())
        sections.extend(self.emit_field_descriptors())
        sections.extend(self.emit_attr_handler())
        sections.extend(self.emit_print_handler())
        sections.extend(self.emit_binary_op_handler())
        sections.extend(self.emit_unary_op_handler())
        sections.extend(self.emit_iter_handlers())
        sections.extend(self.emit_vtable_instance())
        sections.extend(self.emit_make_new())
        sections.extend(self.emit_locals_dict())
        sections.extend(self.emit_type_definition())

        return "\n".join(sections)

    def emit_all_except_struct(self) -> str:
        sections = []

        sections.extend(self.emit_field_descriptors())
        sections.extend(self.emit_attr_handler())
        sections.extend(self.emit_print_handler())
        sections.extend(self.emit_binary_op_handler())
        sections.extend(self.emit_unary_op_handler())
        sections.extend(self.emit_iter_handlers())
        sections.extend(self.emit_vtable_instance())
        sections.extend(self.emit_make_new())
        sections.extend(self.emit_locals_dict())
        sections.extend(self.emit_type_definition())

        return "\n".join(sections)
