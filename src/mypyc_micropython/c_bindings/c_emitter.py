"""Generate MicroPython C wrapper code from CLibraryDef."""

from __future__ import annotations

import re

from mypyc_micropython.c_bindings.c_ir import (
    CCallbackDef,
    CEnumDef,
    CFuncDef,
    CLibraryDef,
    CStructDef,
    CType,
    CTypeDef,
)


class CEmitter:
    def __init__(self, library: CLibraryDef, emit_public: bool = False) -> None:
        self.lib = library
        self.emit_public = emit_public
        self.lines: list[str] = []

    def emit(self) -> str:
        self._emit_header()
        self._emit_ptr_wrapper_type()
        self._emit_struct_types()
        self._emit_callback_support()
        self._emit_wrappers()
        self._emit_module_def()
        return "\n".join(self.lines)

    def emit_header_file(self) -> str:
        guard = self._header_guard_name()
        lines = [
            f"#ifndef {guard}",
            f"#define {guard}",
            '#include "py/obj.h"',
        ]

        for func in self.lib.functions.values():
            if func.has_var_args:
                continue
            lines.append(self._make_wrapper_extern_decl(func))

        lines.append("#endif")
        return "\n".join(lines)

    def _emit_header(self) -> None:
        if self.lib.docstring:
            first_line = self.lib.docstring.split("\n")[0]
            self.lines.append(f"/* {first_line} */")
        self.lines.append("/* Auto-generated from .pyi stub - do not edit */")
        self.lines.append("")
        self.lines.append('#include "py/runtime.h"')
        self.lines.append('#include "py/obj.h"')
        if self.lib.header:
            self.lines.append(f'#include "{self.lib.header}"')
        self.lines.append("")

    def _emit_ptr_wrapper_type(self) -> None:
        self.lines.extend(
            [
                "#ifndef MP_C_PTR_T_DEFINED",
                "#define MP_C_PTR_T_DEFINED",
                "typedef struct {",
                "    mp_obj_base_t base;",
                "    void *ptr;",
                "} mp_c_ptr_t;",
                "#endif",
                "",
                "static MP_DEFINE_CONST_OBJ_TYPE(",
                "    mp_type_c_ptr,",
                "    MP_QSTR_c_ptr,",
                "    MP_TYPE_FLAG_NONE",
                ");",
                "",
                "static inline mp_obj_t wrap_ptr(void *ptr) {",
                "    if (ptr == NULL) return mp_const_none;",
                "    mp_c_ptr_t *o = mp_obj_malloc(mp_c_ptr_t, &mp_type_c_ptr);",
                "    o->ptr = ptr;",
                "    return MP_OBJ_FROM_PTR(o);",
                "}",
                "",
                "static inline void *unwrap_ptr(mp_obj_t obj) {",
                "    if (obj == mp_const_none) return NULL;",
                "    mp_c_ptr_t *o = MP_OBJ_TO_PTR(obj);",
                "    return o->ptr;",
                "}",
                "",
            ]
        )

    def _emit_struct_types(self) -> None:
        for struct in self.lib.structs.values():
            self._emit_struct_wrapper_type(struct)

    def _emit_struct_wrapper_type(self, struct: CStructDef) -> None:
        self.lines.extend(
            [
                "static MP_DEFINE_CONST_OBJ_TYPE(",
                f"    mp_type_{struct.py_name},",
                f"    MP_QSTR_{struct.py_name},",
                "    MP_TYPE_FLAG_NONE",
                ");",
                "",
                f"static mp_obj_t wrap_{struct.py_name}({struct.c_name} *ptr) {{",
                "    if (ptr == NULL) return mp_const_none;",
                f"    mp_c_ptr_t *o = mp_obj_malloc(mp_c_ptr_t, &mp_type_{struct.py_name});",
                "    o->ptr = ptr;",
                "    return MP_OBJ_FROM_PTR(o);",
                "}",
                "",
                f"static {struct.c_name} *unwrap_{struct.py_name}(mp_obj_t obj) {{",
                "    if (obj == mp_const_none) return NULL;",
                "    mp_c_ptr_t *o = MP_OBJ_TO_PTR(obj);",
                f"    return ({struct.c_name} *)o->ptr;",
                "}",
                "",
            ]
        )

    def _has_callbacks(self) -> bool:
        for func in self.lib.functions.values():
            for param in func.params:
                if param.type_def.base_type == CType.CALLBACK:
                    return True
        return False

    def _emit_callback_support(self) -> None:
        if not self._has_callbacks():
            return

        name = self.lib.name
        upper_name = name.upper()
        self.lines.extend(
            [
                f"#define {upper_name}_MAX_CALLBACKS 32",
                f"static mp_obj_t {name}_cb_registry[{upper_name}_MAX_CALLBACKS];",
                f"static int {name}_cb_count = 0;",
                f"MP_REGISTER_ROOT_POINTER(mp_obj_t *{name}_cb_root);",
                "",
            ]
        )

    def _emit_wrappers(self) -> None:
        for func in self.lib.functions.values():
            if func.has_var_args:
                continue
            has_callback = any(p.type_def.base_type == CType.CALLBACK for p in func.params)
            if has_callback:
                self._emit_callback_wrapper(func)
            else:
                self._emit_function_wrapper(func)
            self.lines.append("")

    def _emit_function_wrapper(self, func: CFuncDef) -> None:
        n_args = len(func.params)

        sig = self._make_wrapper_signature(func)
        self.lines.append(f"{sig} {{")

        for i, param in enumerate(func.params):
            arg_ref = f"arg{i}" if n_args <= 3 else f"args[{i}]"
            conversion = self._gen_arg_conversion(param, arg_ref)
            self.lines.append(f"    {conversion}")

        c_args = ", ".join(f"c_{p.name}" for p in func.params)

        if func.return_type.base_type == CType.VOID:
            self.lines.append(f"    {func.c_name}({c_args});")
            self.lines.append("    return mp_const_none;")
        else:
            ret_c_type = self._get_c_type_str(func.return_type)
            self.lines.append(f"    {ret_c_type}result = {func.c_name}({c_args});")
            ret_conv = self._gen_return_conversion(func.return_type, "result")
            self.lines.append(f"    return {ret_conv};")

        self.lines.append("}")
        self.lines.append(self._make_define_macro(func))

    def _emit_callback_wrapper(self, func: CFuncDef) -> None:
        cb_param_idx = None
        for i, param in enumerate(func.params):
            if param.type_def.base_type == CType.CALLBACK:
                cb_param_idx = i
                break

        if cb_param_idx is None:
            return

        cb_param = func.params[cb_param_idx]
        cb_name = cb_param.name
        trampoline_name = f"{func.c_name}_{cb_name}_trampoline"
        cb_def = self._find_callback_def(cb_param.type_def)

        if cb_def and cb_def.params:
            trampoline_args = ", ".join(
                self._callback_param_decl(param.type_def, i)
                for i, param in enumerate(cb_def.params)
            )
        else:
            trampoline_args = "void *p0"

        self.lines.append(f"static void {trampoline_name}({trampoline_args}) {{")

        if cb_def and cb_def.user_data_param is not None:
            self.lines.append(f"    int idx = (int)(intptr_t)p{cb_def.user_data_param};")
        else:
            user_data_getter = self._infer_user_data_getter(cb_def)
            if user_data_getter:
                self.lines.append(f"    int idx = (int)(intptr_t){user_data_getter}(p0);")
            else:
                self.lines.append("    int idx = (int)(intptr_t)p0;")

        self.lines.append(f"    if (idx >= 0 && idx < {self.lib.name}_cb_count) {{")
        self.lines.append(f"        mp_obj_t cb = {self.lib.name}_cb_registry[idx];")

        if cb_def and cb_def.params:
            if len(cb_def.params) == 1:
                arg_expr = self._callback_arg_to_mp(cb_def.params[0].type_def, "p0")
                self.lines.append(f"        mp_call_function_1(cb, {arg_expr});")
            else:
                self.lines.append(f"        mp_obj_t cb_args[{len(cb_def.params)}];")
                for i, param in enumerate(cb_def.params):
                    arg_expr = self._callback_arg_to_mp(param.type_def, f"p{i}")
                    self.lines.append(f"        cb_args[{i}] = {arg_expr};")
                self.lines.append(
                    f"        mp_call_function_n_kw(cb, {len(cb_def.params)}, 0, cb_args);"
                )
        else:
            self.lines.append("        mp_call_function_0(cb);")

        self.lines.append("    }")
        self.lines.append("}")
        self.lines.append("")

        n_args = len(func.params)
        linkage = self._wrapper_linkage_prefix()
        self.lines.append(
            f"{linkage}mp_obj_t {func.c_name}_wrapper(size_t n_args, const mp_obj_t *args) {{"
        )

        for i, param in enumerate(func.params):
            if i == cb_param_idx:
                self.lines.append(f"    mp_obj_t callback = args[{i}];")
            else:
                conversion = self._gen_arg_conversion(param, f"args[{i}]")
                self.lines.append(f"    {conversion}")

        self.lines.extend(
            [
                f"    if ({self.lib.name}_cb_count >= {self.lib.name.upper()}_MAX_CALLBACKS) {{",
                "        mp_raise_msg(&mp_type_RuntimeError, "
                'MP_ERROR_TEXT("too many event callbacks"));',
                "    }",
                f"    int idx = {self.lib.name}_cb_count++;",
                f"    {self.lib.name}_cb_registry[idx] = callback;",
            ]
        )

        call_args: list[str] = []
        for i, param in enumerate(func.params):
            if i == cb_param_idx:
                call_args.append(trampoline_name)
            elif param.name == "user_data":
                call_args.append("(void *)(intptr_t)idx")
            else:
                call_args.append(f"c_{param.name}")
        call_args_str = ", ".join(call_args)

        self.lines.append(f"    {func.c_name}({call_args_str});")
        self.lines.append("    return mp_const_none;")
        self.lines.append("}")

        min_args = sum(1 for p in func.params if not p.type_def.is_optional)
        max_args = n_args
        self.lines.append(
            f"static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN("
            f"{func.c_name}_obj, {min_args}, {max_args}, {func.c_name}_wrapper);"
        )

    def _find_callback_def(self, callback_type: CTypeDef) -> CCallbackDef | None:
        if callback_type.callback_name:
            named = self.lib.callbacks.get(callback_type.callback_name)
            if named is not None:
                return named

        for cb in self.lib.callbacks.values():
            return cb
        return None

    def _callback_param_decl(self, type_def: CTypeDef, idx: int) -> str:
        if type_def.base_type == CType.STRUCT_PTR and type_def.struct_name:
            struct = self.lib.structs.get(type_def.struct_name)
            if struct:
                return f"{struct.c_name} *p{idx}"
            return f"void *p{idx}"
        if type_def.base_type == CType.PTR:
            return f"void *p{idx}"
        return f"{type_def.base_type.to_c_decl()} p{idx}"

    def _callback_arg_to_mp(self, type_def: CTypeDef, val_expr: str) -> str:
        if type_def.base_type == CType.STRUCT_PTR and type_def.struct_name:
            struct = self.lib.structs.get(type_def.struct_name)
            if struct:
                return f"wrap_{struct.py_name}({val_expr})"
            return f"wrap_ptr({val_expr})"
        if type_def.base_type == CType.PTR:
            return f"wrap_ptr({val_expr})"
        return type_def.base_type.to_mp_box(val_expr)

    def _infer_user_data_getter(self, cb_def: CCallbackDef | None) -> str | None:
        if not cb_def or not cb_def.params:
            return None

        first_type = cb_def.params[0].type_def
        if first_type.base_type != CType.STRUCT_PTR or not first_type.struct_name:
            return None

        struct = self.lib.structs.get(first_type.struct_name)
        if not struct:
            return None

        c_name_without_suffix = struct.c_name.removesuffix("_t")
        return f"{c_name_without_suffix}_get_user_data"

    def _gen_arg_conversion(self, param, arg_expr: str) -> str:
        t = param.type_def
        if t.base_type == CType.STRUCT_PTR and t.struct_name:
            struct = self.lib.structs.get(t.struct_name)
            c_type = struct.c_name if struct else "void"
            unwrap_expr = (
                f"unwrap_{struct.py_name}({arg_expr})"
                if struct
                else f"({c_type} *)unwrap_ptr({arg_expr})"
            )
            if t.is_optional:
                return (
                    f"{c_type} *c_{param.name} = "
                    f"({arg_expr} == mp_const_none) ? NULL : {unwrap_expr};"
                )
            return f"{c_type} *c_{param.name} = {unwrap_expr};"

        if t.base_type == CType.PTR:
            return f"void *c_{param.name} = unwrap_ptr({arg_expr});"

        if t.base_type == CType.STR:
            return f"const char *c_{param.name} = mp_obj_str_get_str({arg_expr});"

        if t.base_type in {
            CType.INT,
            CType.UINT,
            CType.INT8,
            CType.UINT8,
            CType.INT16,
            CType.UINT16,
            CType.INT32,
            CType.UINT32,
            CType.FLOAT,
            CType.DOUBLE,
            CType.BOOL,
        }:
            return (
                f"{t.base_type.to_c_decl()} c_{param.name} = {t.base_type.to_mp_unbox(arg_expr)};"
            )

        return f"void *c_{param.name} = unwrap_ptr({arg_expr});"

    def _gen_return_conversion(self, type_def: CTypeDef, val_expr: str) -> str:
        if type_def.base_type == CType.STRUCT_PTR and type_def.struct_name:
            struct = self.lib.structs.get(type_def.struct_name)
            if struct:
                return f"wrap_{struct.py_name}({val_expr})"
            return f"wrap_ptr((void *){val_expr})"
        if type_def.base_type == CType.PTR:
            return f"wrap_ptr({val_expr})"
        return type_def.base_type.to_mp_box(val_expr)

    def _get_c_type_str(self, type_def: CTypeDef) -> str:
        if type_def.base_type == CType.STRUCT_PTR and type_def.struct_name:
            struct = self.lib.structs.get(type_def.struct_name)
            if struct:
                return f"{struct.c_name} *"
            return "void *"
        if type_def.base_type == CType.STR:
            return "const char *"
        if type_def.base_type == CType.PTR:
            return "void *"
        return type_def.base_type.to_c_decl() + " "

    def _make_wrapper_signature(self, func: CFuncDef) -> str:
        n_args = len(func.params)
        linkage = self._wrapper_linkage_prefix()
        if n_args == 0:
            return f"{linkage}mp_obj_t {func.c_name}_wrapper(void)"
        if n_args <= 3:
            args = ", ".join(f"mp_obj_t arg{i}" for i in range(n_args))
            return f"{linkage}mp_obj_t {func.c_name}_wrapper({args})"
        return f"{linkage}mp_obj_t {func.c_name}_wrapper(size_t n_args, const mp_obj_t *args)"

    def _wrapper_linkage_prefix(self) -> str:
        return "" if self.emit_public else "static "

    def _header_guard_name(self) -> str:
        upper = re.sub(r"[^A-Za-z0-9]", "_", self.lib.name).upper()
        return f"{upper}_WRAPPERS_H"

    def _make_wrapper_extern_decl(self, func: CFuncDef) -> str:
        n_args = len(func.params)
        wrapper_name = f"{func.c_name}_wrapper"
        if any(p.type_def.base_type == CType.CALLBACK for p in func.params) or n_args > 3:
            return f"extern mp_obj_t {wrapper_name}(size_t n_args, const mp_obj_t *args);"
        if n_args == 0:
            return f"extern mp_obj_t {wrapper_name}(void);"
        args = ", ".join(f"mp_obj_t arg{i}" for i in range(n_args))
        return f"extern mp_obj_t {wrapper_name}({args});"

    def _make_define_macro(self, func: CFuncDef) -> str:
        n_args = len(func.params)
        obj_name = f"{func.c_name}_obj"
        wrapper_name = f"{func.c_name}_wrapper"

        if n_args <= 3:
            return f"static MP_DEFINE_CONST_FUN_OBJ_{n_args}({obj_name}, {wrapper_name});"

        min_args = sum(1 for p in func.params if not p.type_def.is_optional)
        return (
            f"static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN("
            f"{obj_name}, {min_args}, {n_args}, {wrapper_name});"
        )

    def _emit_module_def(self) -> None:
        name = self.lib.name
        self.lines.append(f"static const mp_rom_map_elem_t {name}_module_globals_table[] = {{")
        self.lines.append(f"    {{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_{name}) }},")

        for func in self.lib.functions.values():
            if func.has_var_args:
                continue
            self.lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{func.py_name}), MP_ROM_PTR(&{func.c_name}_obj) }},"
            )

        for enum in self.lib.enums.values():
            self._emit_enum_entries(enum)

        self.lines.append("};")
        self.lines.append(
            f"static MP_DEFINE_CONST_DICT({name}_module_globals, {name}_module_globals_table);"
        )
        self.lines.append("")
        self.lines.append(f"const mp_obj_module_t {name}_user_cmodule = {{")
        self.lines.append("    .base = { &mp_type_module },")
        self.lines.append(f"    .globals = (mp_obj_dict_t *)&{name}_module_globals,")
        self.lines.append("};")
        self.lines.append("")
        self.lines.append(f"MP_REGISTER_MODULE(MP_QSTR_{name}, {name}_user_cmodule);")

    def _emit_enum_entries(self, enum: CEnumDef) -> None:
        for val_name, val in enum.values.items():
            qstr_name = f"{enum.c_name.removesuffix('_t').upper()}_{val_name}"
            self.lines.append(f"    {{ MP_ROM_QSTR(MP_QSTR_{qstr_name}), MP_ROM_INT({val}) }},")
