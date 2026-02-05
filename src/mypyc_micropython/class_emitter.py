"""
C code generation for classes.

This module generates MicroPython-compatible C code for Python classes,
including structs, vtables, constructors, and method wrappers.
"""

from __future__ import annotations

from .ir import ClassIR, FieldIR, MethodIR, CType, DataclassInfo


class ClassEmitter:
    """Generates C code for a single class."""
    
    def __init__(self, class_ir: ClassIR, module_c_name: str):
        self.class_ir = class_ir
        self.module_c_name = module_c_name
        self.c_name = class_ir.c_name
    
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
            lines.append(f"    {{ MP_QSTR_{fld.name}, offsetof({self.c_name}_obj_t, {path}), {type_id} }},")
        
        lines.append(f"    {{ MP_QSTR_NULL, 0, 0 }}")
        lines.append("};")
        lines.append("")
        
        return lines
    
    def emit_attr_handler(self) -> list[str]:
        all_fields = self.class_ir.get_all_fields()
        if not all_fields:
            return self._emit_simple_attr_handler()
        
        lines = []
        lines.append(f"static void {self.c_name}_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {{")
        lines.append(f"    {self.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
        lines.append("")
        lines.append(f"    for (const {self.c_name}_field_t *f = {self.c_name}_fields; f->name != MP_QSTR_NULL; f++) {{")
        lines.append("        if (f->name == attr) {")
        lines.append("            if (dest[0] == MP_OBJ_NULL) {")
        lines.append("                char *ptr = (char *)self + f->offset;")
        lines.append("                switch (f->type) {")
        lines.append("                    case 0: dest[0] = *(mp_obj_t *)ptr; break;")
        lines.append("                    case 1: dest[0] = mp_obj_new_int(*(mp_int_t *)ptr); break;")
        lines.append("                    case 2: dest[0] = mp_obj_new_float(*(mp_float_t *)ptr); break;")
        lines.append("                    case 3: dest[0] = *(bool *)ptr ? mp_const_true : mp_const_false; break;")
        lines.append("                }")
        lines.append("            } else if (dest[1] != MP_OBJ_NULL) {")
        lines.append("                char *ptr = (char *)self + f->offset;")
        lines.append("                switch (f->type) {")
        lines.append("                    case 0: *(mp_obj_t *)ptr = dest[1]; break;")
        lines.append("                    case 1: *(mp_int_t *)ptr = mp_obj_get_int(dest[1]); break;")
        lines.append("                    case 2: *(mp_float_t *)ptr = mp_obj_get_float(dest[1]); break;")
        lines.append("                    case 3: *(bool *)ptr = mp_obj_is_true(dest[1]); break;")
        lines.append("                }")
        lines.append("                dest[0] = MP_OBJ_NULL;")
        lines.append("            }")
        lines.append("            return;")
        lines.append("        }")
        lines.append("    }")
        lines.append("")
        lines.append(f"    dest[1] = MP_OBJ_SENTINEL;")
        lines.append("}")
        lines.append("")
        
        return lines
    
    def _emit_simple_attr_handler(self) -> list[str]:
        lines = []
        lines.append(f"static void {self.c_name}_attr(mp_obj_t self_in, qstr attr, mp_obj_t *dest) {{")
        lines.append("    dest[1] = MP_OBJ_SENTINEL;")
        lines.append("}")
        lines.append("")
        return lines
    
    def emit_make_new(self) -> list[str]:
        lines = []
        all_fields = self.class_ir.get_all_fields()
        vtable_entries = self.class_ir.get_vtable_entries()
        
        if self.class_ir.is_dataclass and self.class_ir.dataclass_info:
            return self._emit_dataclass_make_new()
        
        init_method = self.class_ir.methods.get("__init__")
        
        lines.append(f"static mp_obj_t {self.c_name}_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {{")
        
        if init_method:
            num_params = len(init_method.params)
            lines.append(f"    mp_arg_check_num(n_args, n_kw, {num_params}, {num_params}, false);")
        else:
            lines.append("    mp_arg_check_num(n_args, n_kw, 0, 0, false);")
        
        lines.append("")
        lines.append(f"    {self.c_name}_obj_t *self = mp_obj_malloc({self.c_name}_obj_t, type);")
        
        if vtable_entries and not self.class_ir.base:
            lines.append(f"    self->vtable = &{self.c_name}_vtable_inst;")
        
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
            lines.append("")
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
        
        lines.append(f"static mp_obj_t {self.c_name}_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {{")
        
        lines.append("    enum {")
        for fld, _ in fields_with_path:
            lines.append(f"        ARG_{fld.name},")
        lines.append("    };")
        
        lines.append("    static const mp_arg_t allowed_args[] = {")
        for fld, _ in fields_with_path:
            if fld.c_type == CType.MP_INT_T:
                if fld.has_default:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_INT, {{.u_int = {fld.default_value}}} }},")
                else:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_INT }},")
            elif fld.c_type == CType.MP_FLOAT_T:
                if fld.has_default:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_OBJ, {{.u_obj = mp_const_none}} }},")
                else:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_OBJ }},")
            elif fld.c_type == CType.BOOL:
                if fld.has_default:
                    default_val = "true" if fld.default_value else "false"
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_BOOL, {{.u_bool = {default_val}}} }},")
                else:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_BOOL }},")
            else:
                if fld.has_default:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_OBJ, {{.u_obj = mp_const_none}} }},")
                else:
                    lines.append(f"        {{ MP_QSTR_{fld.name}, MP_ARG_REQUIRED | MP_ARG_OBJ }},")
        lines.append("    };")
        lines.append("")
        
        lines.append(f"    mp_arg_val_t parsed[{len(fields_with_path)}];")
        lines.append(f"    mp_arg_parse_all_kw_array(n_args, n_kw, args, {len(fields_with_path)}, allowed_args, parsed);")
        lines.append("")
        
        lines.append(f"    {self.c_name}_obj_t *self = mp_obj_malloc({self.c_name}_obj_t, type);")
        
        if vtable_entries and not self.class_ir.base:
            lines.append(f"    self->vtable = &{self.c_name}_vtable_inst;")
        
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
        if not self.class_ir.is_dataclass:
            return []
        
        lines = []
        fields_with_path = self.class_ir.get_all_fields_with_path()
        
        lines.append(f"static void {self.c_name}_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {{")
        lines.append(f"    {self.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
        lines.append(f"    (void)kind;")
        lines.append(f'    mp_printf(print, "{self.class_ir.name}(");')
        
        for i, (fld, path) in enumerate(fields_with_path):
            separator = ", " if i > 0 else ""
            if fld.c_type == CType.MP_INT_T:
                lines.append(f'    mp_printf(print, "{separator}{fld.name}=%d", (int)self->{path});')
            elif fld.c_type == CType.MP_FLOAT_T:
                lines.append(f'    mp_printf(print, "{separator}{fld.name}=");')
                lines.append(f"    mp_obj_print_helper(print, mp_obj_new_float(self->{path}), PRINT_REPR);")
            elif fld.c_type == CType.BOOL:
                lines.append(f'    mp_printf(print, "{separator}{fld.name}=%s", self->{path} ? "True" : "False");')
            else:
                lines.append(f'    mp_printf(print, "{separator}{fld.name}=");')
                lines.append(f"    mp_obj_print_helper(print, self->{path}, PRINT_REPR);")
        
        lines.append('    mp_printf(print, ")");')
        lines.append("}")
        lines.append("")
        
        return lines
    
    def emit_binary_op_handler(self) -> list[str]:
        if not (self.class_ir.is_dataclass and self.class_ir.dataclass_info and self.class_ir.dataclass_info.eq):
            return []
        
        lines = []
        fields_with_path = self.class_ir.get_all_fields_with_path()
        
        lines.append(f"static mp_obj_t {self.c_name}_binary_op(mp_binary_op_t op, mp_obj_t lhs_in, mp_obj_t rhs_in) {{")
        lines.append("    if (op != MP_BINARY_OP_EQUAL) {")
        lines.append("        return MP_OBJ_NULL;")
        lines.append("    }")
        lines.append("")
        lines.append(f"    if (!mp_obj_is_type(rhs_in, &{self.c_name}_type)) {{")
        lines.append("        return mp_const_false;")
        lines.append("    }")
        lines.append("")
        lines.append(f"    {self.c_name}_obj_t *lhs = MP_OBJ_TO_PTR(lhs_in);")
        lines.append(f"    {self.c_name}_obj_t *rhs = MP_OBJ_TO_PTR(rhs_in);")
        lines.append("")
        
        conditions = []
        for fld, path in fields_with_path:
            if fld.c_type == CType.MP_OBJ_T:
                conditions.append(f"mp_obj_equal(lhs->{path}, rhs->{path})")
            else:
                conditions.append(f"lhs->{path} == rhs->{path}")
        
        if conditions:
            cond_str = " &&\n        ".join(conditions)
            lines.append(f"    return mp_obj_new_bool(")
            lines.append(f"        {cond_str}")
            lines.append("    );")
        else:
            lines.append("    return mp_const_true;")
        
        lines.append("}")
        lines.append("")
        
        return lines
    
    def emit_vtable_instance(self) -> list[str]:
        vtable_entries = self.class_ir.get_vtable_entries()
        if not vtable_entries:
            return []
        
        lines = []
        lines.append(f"static const {self.c_name}_vtable_t {self.c_name}_vtable_inst = {{")
        
        for method_name, method_ir in vtable_entries:
            lines.append(f"    .{method_name} = {method_ir.c_name}_native,")
        
        lines.append("};")
        lines.append("")
        
        return lines
    
    def emit_locals_dict(self) -> list[str]:
        lines = []
        
        method_names = [name for name in self.class_ir.methods.keys() 
                       if not name.startswith("__") or name in ("__len__", "__getitem__", "__setitem__")]
        
        if not method_names:
            lines.append(f"static const mp_rom_map_elem_t {self.c_name}_locals_dict_table[] = {{")
            lines.append("};")
        else:
            lines.append(f"static const mp_rom_map_elem_t {self.c_name}_locals_dict_table[] = {{")
            for name in method_names:
                method = self.class_ir.methods[name]
                lines.append(f"    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&{method.c_name}_obj) }},")
            lines.append("};")
        
        lines.append(f"static MP_DEFINE_CONST_DICT({self.c_name}_locals_dict, {self.c_name}_locals_dict_table);")
        lines.append("")
        
        return lines
    
    def emit_type_definition(self) -> list[str]:
        lines = []
        
        slots = []
        slots.append(f"    make_new, {self.c_name}_make_new")
        
        if self.class_ir.get_all_fields():
            slots.append(f"    attr, {self.c_name}_attr")
        
        if self.class_ir.is_dataclass:
            slots.append(f"    print, {self.c_name}_print")
            if self.class_ir.dataclass_info and self.class_ir.dataclass_info.eq:
                slots.append(f"    binary_op, {self.c_name}_binary_op")
        
        if self.class_ir.base:
            slots.append(f"    parent, &{self.class_ir.base.c_name}_type")
        
        method_names = [name for name in self.class_ir.methods.keys() 
                       if not name.startswith("__") or name in ("__len__", "__getitem__", "__setitem__")]
        if method_names:
            slots.append(f"    locals_dict, &{self.c_name}_locals_dict")
        
        slots_str = ",\n".join(slots)
        
        lines.append(f"MP_DEFINE_CONST_OBJ_TYPE(")
        lines.append(f"    {self.c_name}_type,")
        lines.append(f"    MP_QSTR_{self.class_ir.name},")
        lines.append("    MP_TYPE_FLAG_NONE,")
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
        sections.extend(self.emit_vtable_instance())
        sections.extend(self.emit_make_new())
        sections.extend(self.emit_locals_dict())
        sections.extend(self.emit_type_definition())
        
        return "\n".join(sections)
