"""
Module Emitter: ModuleIR -> Complete C file.

This module assembles the final C code including includes, helpers,
function code, class code, and module registration.
"""

from __future__ import annotations

import re
from typing import Any

from .c_bindings.core.c_ir import CType
from .ir import FuncIR, ModuleIR, RTuple

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


class ModuleEmitter:
    """Assembles complete C module code from parts."""

    def __init__(
        self,
        module_ir: ModuleIR,
        uses_print: bool = False,
        uses_list_opt: bool = False,
        uses_builtins: bool = False,
        uses_checked_div: bool = False,
        uses_imports: bool = False,
        used_rtuples: set[RTuple] | None = None,
        external_libs: dict[str, Any] | None = None,
    ):
        self.module_ir = module_ir
        self.c_name = module_ir.c_name
        # QSTR name is always the c_name (flat, no dots)
        # Dotted imports are handled via Python wrapper packages
        self.qstr_name = module_ir.c_name
        self._uses_print = uses_print
        self._uses_list_opt = uses_list_opt
        self._uses_builtins = uses_builtins
        self._uses_checked_div = uses_checked_div
        self._uses_imports = uses_imports
        self._used_rtuples = used_rtuples or set()
        self.external_libs = external_libs or {}

    def emit(
        self,
        forward_decls: list[str],
        struct_code: list[str],
        function_code: list[str],
        class_code: list[str],
        functions: list[FuncIR],
    ) -> str:
        lines: list[str] = []
        module_var_entries = self._collect_module_var_entries()
        module_init_name = f"{self.c_name}__module_init"

        lines.extend(self._emit_includes())
        lines.append("")

        if self.external_libs:
            lines.extend(self._emit_external_wrapper_declarations())
            lines.append("")

        if forward_decls:
            lines.extend(forward_decls)
            lines.append("")

        if self._used_rtuples:
            for rtuple in sorted(self._used_rtuples, key=lambda r: r.get_c_struct_name()):
                lines.append(rtuple.get_c_struct_typedef())
            lines.append("")

        lines.extend(self._emit_float_helper())
        lines.append("")

        if self._uses_checked_div:
            lines.extend(self._emit_checked_div_helper())
            lines.append("")

        if self._uses_list_opt:
            lines.extend(self._emit_list_helpers())
            lines.append("")

        if struct_code:
            lines.extend(struct_code)
            lines.append("")

        if module_var_entries:
            lines.extend(self._emit_module_var_declarations(module_var_entries))
            lines.append("")
            lines.extend(self._emit_module_var_init_helper(module_init_name, module_var_entries))
            lines.append("")

        for func_code in function_code:
            if module_var_entries:
                lines.append(self._inject_module_init_call(func_code, module_init_name))
            else:
                lines.append(func_code)

        for cls_code in class_code:
            lines.append(cls_code)

        lines.extend(self._emit_globals_table(functions))
        lines.extend(self._emit_module_registration())

        return "\n".join(lines)

    def _emit_external_wrapper_declarations(self) -> list[str]:
        parts: list[str] = []
        for lib_name, lib_def in self.external_libs.items():
            parts.append(f"/* External library: {lib_name} */")
            for func_def in lib_def.functions.values():
                if func_def.has_var_args:
                    continue
                n_args = len(func_def.params)
                wrapper_name = f"{func_def.c_name}_wrapper"
                # Check for CALLBACK params - must use VAR_BETWEEN calling convention
                # to match CEmitter._make_wrapper_extern_decl
                has_callback = any(p.type_def.base_type == CType.CALLBACK for p in func_def.params)
                if has_callback or n_args > 3:
                    parts.append(f"extern mp_obj_t {wrapper_name}(size_t, const mp_obj_t *);")
                elif n_args == 0:
                    parts.append(f"extern mp_obj_t {wrapper_name}(void);")
                else:
                    args = ", ".join("mp_obj_t" for _ in range(n_args))
                    parts.append(f"extern mp_obj_t {wrapper_name}({args});")
            parts.append("")
        return parts

    def emit_package(
        self,
        *,
        forward_decls: list[str],
        struct_code: list[str],
        function_code: list[str],
        class_code: list[str],
        parent_functions: list[FuncIR],
        submodules: list[object],
    ) -> str:
        lines: list[str] = []
        module_var_entries = self._collect_module_var_entries(submodules)
        module_init_name = f"{self.c_name}__module_init"

        lines.extend(self._emit_includes())
        lines.append("")

        if forward_decls:
            lines.extend(forward_decls)
            lines.append("")

        if self._used_rtuples:
            for rtuple in sorted(self._used_rtuples, key=lambda r: r.get_c_struct_name()):
                lines.append(rtuple.get_c_struct_typedef())
            lines.append("")

        lines.extend(self._emit_float_helper())
        lines.append("")

        if self._uses_checked_div:
            lines.extend(self._emit_checked_div_helper())
            lines.append("")

        if self._uses_list_opt:
            lines.extend(self._emit_list_helpers())
            lines.append("")

        if struct_code:
            lines.extend(struct_code)
            lines.append("")

        if module_var_entries:
            lines.extend(self._emit_module_var_declarations(module_var_entries))
            lines.append("")
            lines.extend(self._emit_module_var_init_helper(module_init_name, module_var_entries))
            lines.append("")

        for func_code in function_code:
            if module_var_entries:
                lines.append(self._inject_module_init_call(func_code, module_init_name))
            else:
                lines.append(func_code)

        for cls_code in class_code:
            lines.append(cls_code)

        # Emit all submodule globals tables recursively (depth-first)
        self._emit_submodules_recursive(lines, submodules)

        lines.extend(
            self._emit_package_globals_table(
                parent_functions=parent_functions,
                submodules=submodules,
            )
        )
        lines.extend(self._emit_module_registration())

        return "\n".join(lines)

    def _iter_submodules(self, submodules: list[object]) -> list[object]:
        out: list[object] = []
        for submodule in submodules:
            out.append(submodule)
            children = getattr(submodule, "children", None) or []
            out.extend(self._iter_submodules(children))
        return out

    def _collect_module_var_entries(
        self, submodules: list[object] | None = None
    ) -> list[tuple[str, str, str]]:
        entries: list[tuple[str, str, str]] = []
        for name, kind in self.module_ir.module_vars.items():
            entries.append((self.module_ir.c_name, name, kind))
        if submodules:
            for submodule in self._iter_submodules(submodules):
                sub_ir = getattr(submodule, "module_ir")
                for name, kind in sub_ir.module_vars.items():
                    entries.append((sub_ir.c_name, name, kind))
        return entries

    def _emit_module_var_declarations(self, entries: list[tuple[str, str, str]]) -> list[str]:
        lines: list[str] = []
        for module_c_name, var_name, _ in entries:
            lines.append(f"static mp_obj_t {module_c_name}_{sanitize_name(var_name)};")
        return lines

    def _emit_module_var_init_helper(
        self,
        init_name: str,
        entries: list[tuple[str, str, str]],
    ) -> list[str]:
        lines = [
            f"static bool {self.c_name}__module_inited = false;",
            f"static void {init_name}(void) {{",
            f"    if ({self.c_name}__module_inited) {{",
            "        return;",
            "    }",
            f"    {self.c_name}__module_inited = true;",
        ]
        for module_c_name, var_name, kind in entries:
            c_var = f"{module_c_name}_{sanitize_name(var_name)}"
            if kind == "dict":
                lines.append(f"    {c_var} = mp_obj_new_dict(0);")
            else:
                lines.append(f"    {c_var} = mp_obj_new_list(0, NULL);")
        lines.append("}")
        return lines

    def _inject_module_init_call(self, func_code: str, init_name: str) -> str:
        brace_idx = func_code.find("{")
        if brace_idx < 0:
            return func_code
        insert_at = brace_idx + 1
        if insert_at < len(func_code) and func_code[insert_at] == "\n":
            return func_code[: insert_at + 1] + f"    {init_name}();\n" + func_code[insert_at + 1 :]
        return func_code[:insert_at] + f"\n    {init_name}();" + func_code[insert_at:]

    def _emit_includes(self) -> list[str]:
        lines = [
            '#include "py/runtime.h"',
            '#include "py/obj.h"',
            '#include "py/objtype.h"',
            "#include <stddef.h>",
        ]
        if self._uses_print:
            lines.append('#include "py/mpprint.h"')
        if self._uses_builtins:
            lines.append('#include "py/builtin.h"')
        return lines

    def _emit_float_helper(self) -> list[str]:
        return [
            "#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE",
            "static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {",
            "    if (mp_obj_is_float(obj)) {",
            "        return mp_obj_float_get(obj);",
            "    }",
            "    return (mp_float_t)mp_obj_get_int(obj);",
            "}",
            "#endif",
        ]

    def _emit_checked_div_helper(self) -> list[str]:
        return [
            "static inline mp_int_t mp_int_floor_divide_checked(mp_int_t num, mp_int_t denom) {",
            "    if (denom == 0) {",
            '        mp_raise_msg(&mp_type_ZeroDivisionError, MP_ERROR_TEXT("division by zero"));',
            "    }",
            "    if (num >= 0) {",
            "        if (denom < 0) {",
            "            num += -denom - 1;",
            "        }",
            "    } else {",
            "        if (denom >= 0) {",
            "            num += -denom + 1;",
            "        }",
            "    }",
            "    return num / denom;",
            "}",
            "",
            "static inline mp_int_t mp_int_modulo_checked(mp_int_t dividend, mp_int_t divisor) {",
            "    if (divisor == 0) {",
            '        mp_raise_msg(&mp_type_ZeroDivisionError, MP_ERROR_TEXT("division by zero"));',
            "    }",
            "    dividend %= divisor;",
            "    if ((dividend < 0 && divisor > 0) || (dividend > 0 && divisor < 0)) {",
            "        dividend += divisor;",
            "    }",
            "    return dividend;",
            "}",
        ]

    def _emit_list_helpers(self) -> list[str]:
        return [
            '#include "py/objlist.h"',
            "",
            "static inline mp_obj_t mp_list_get_fast(mp_obj_t list, size_t index) {",
            "    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);",
            "    return self->items[index];",
            "}",
            "",
            "static inline mp_obj_t mp_list_get_neg(mp_obj_t list, mp_int_t index) {",
            "    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);",
            "    return self->items[self->len + index];",
            "}",
            "",
            "static inline mp_obj_t mp_list_get_int(mp_obj_t list, mp_int_t index) {",
            "    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);",
            "    if (index < 0) {",
            "        index += self->len;",
            "    }",
            "    return self->items[index];",
            "}",
            "",
            "static inline size_t mp_list_len_fast(mp_obj_t list) {",
            "    return ((mp_obj_list_t *)MP_OBJ_TO_PTR(list))->len;",
            "}",
            "",
            "static inline mp_int_t mp_list_sum_int(mp_obj_t list) {",
            "    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);",
            "    mp_int_t sum = 0;",
            "    for (size_t i = 0; i < self->len; i++) {",
            "        sum += mp_obj_get_int(self->items[i]);",
            "    }",
            "    return sum;",
            "}",
            "",
            "static inline mp_float_t mp_list_sum_float(mp_obj_t list) {",
            "    mp_obj_list_t *self = MP_OBJ_TO_PTR(list);",
            "    mp_float_t sum = 0.0;",
            "    for (size_t i = 0; i < self->len; i++) {",
            "        mp_obj_t item = self->items[i];",
            "        if (mp_obj_is_float(item)) {",
            "            sum += mp_obj_float_get(item);",
            "        } else {",
            "            sum += (mp_float_t)mp_obj_get_int(item);",
            "        }",
            "    }",
            "    return sum;",
            "}",
        ]

    def _emit_globals_table(self, functions: list[FuncIR]) -> list[str]:
        lines = [
            f"static const mp_rom_map_elem_t {self.c_name}_module_globals_table[] = {{",
            f"    {{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_{self.c_name}) }},",
        ]

        # Export module-level constants
        for const_name, const_value in self.module_ir.constants.items():
            if isinstance(const_value, bool):
                mp_val = "mp_const_true" if const_value else "mp_const_false"
                lines.append(f"    {{ MP_ROM_QSTR(MP_QSTR_{const_name}), MP_ROM_PTR({mp_val}) }},")
            elif isinstance(const_value, int):
                lines.append(
                    f"    {{ MP_ROM_QSTR(MP_QSTR_{const_name}), MP_ROM_INT({const_value}) }},"
                )
            elif isinstance(const_value, str):
                # Use QSTR for string constants (escaped for C compatibility)
                lines.append(
                    f"    {{ MP_ROM_QSTR(MP_QSTR_{const_name}), MP_ROM_QSTR(MP_QSTR_{const_name}) }},"
                )
            # Note: float constants require special handling, skip for now


        for func in functions:
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{func.name}), MP_ROM_PTR(&{func.c_name}_obj) }},"
            )

        for class_name in self.module_ir.class_order:
            class_ir = self.module_ir.classes[class_name]
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{class_ir.name}), MP_ROM_PTR(&{class_ir.c_name}_type) }},"
            )

        # Export enum members as module-level integer constants
        # Following C bindings pattern: EnumName_MEMBER = value
        for enum_name in self.module_ir.enum_order:
            enum_ir = self.module_ir.enums[enum_name]
            for member_name, member_value in enum_ir.values.items():
                qstr_name = f"{enum_ir.name}_{member_name}"
                lines.append(
                    f"    {{ MP_ROM_QSTR(MP_QSTR_{qstr_name}), MP_ROM_INT({member_value}) }},"
                )

        lines.append("};")
        lines.append(
            f"MP_DEFINE_CONST_DICT({self.c_name}_module_globals, {self.c_name}_module_globals_table);"
        )
        lines.append("")
        return lines

    def _emit_submodule_globals_table(
        self,
        *,
        symbol_prefix: str,
        submodule_name: str,
        functions: list[FuncIR],
        module_ir: ModuleIR,
        children: list[object] | None = None,
    ) -> list[str]:
        lines = [
            f"static const mp_rom_map_elem_t {symbol_prefix}_globals_table[] = {{",
            f"    {{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_{submodule_name}) }},",
        ]

        for func in functions:
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{func.name}), MP_ROM_PTR(&{func.c_name}_obj) }},"
            )

        for class_name in module_ir.class_order:
            class_ir = module_ir.classes[class_name]
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{class_ir.name}), MP_ROM_PTR(&{class_ir.c_name}_type) }},"
            )


        # Export enum members
        for enum_name in module_ir.enum_order:
            enum_ir = module_ir.enums[enum_name]
            for member_name, member_value in enum_ir.values.items():
                qstr_name = f"{enum_ir.name}_{member_name}"
                lines.append(
                    f"    {{ MP_ROM_QSTR(MP_QSTR_{qstr_name}), MP_ROM_INT({member_value}) }},"
                )

        # Add child sub-package references (for nested packages)
        if children:
            for child in children:
                child_name = sanitize_name(child.name)
                lines.append(
                    f"    {{ MP_ROM_QSTR(MP_QSTR_{child_name}), MP_ROM_PTR(&{child.symbol_prefix}_module) }},"
                )

        lines.append("};")
        lines.append(
            f"MP_DEFINE_CONST_DICT({symbol_prefix}_globals, {symbol_prefix}_globals_table);"
        )
        lines.append("")
        lines.append(f"static const mp_obj_module_t {symbol_prefix}_module = {{")
        lines.append("    .base = { &mp_type_module },")
        lines.append(f"    .globals = (mp_obj_dict_t *)&{symbol_prefix}_globals,")
        lines.append("};")
        lines.append("")
        return lines

    def _emit_submodules_recursive(self, lines: list[str], submodules: list[object]) -> None:
        """Emit submodule globals tables depth-first (children before parents)."""
        for submodule in submodules:
            # Recurse into children first (they must be defined before parent references them)
            if hasattr(submodule, "children") and submodule.children:
                self._emit_submodules_recursive(lines, submodule.children)

            submodule_name = sanitize_name(submodule.name)
            children = getattr(submodule, "children", None) or []
            lines.extend(
                self._emit_submodule_globals_table(
                    symbol_prefix=submodule.symbol_prefix,
                    submodule_name=submodule_name,
                    functions=submodule.functions,
                    module_ir=submodule.module_ir,
                    children=children if children else None,
                )
            )

    def _emit_package_globals_table(
        self,
        *,
        parent_functions: list[FuncIR],
        submodules: list[object],
    ) -> list[str]:
        lines = [
            f"static const mp_rom_map_elem_t {self.c_name}_module_globals_table[] = {{",
            f"    {{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_{self.c_name}) }},",
        ]

        for func in parent_functions:
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{func.name}), MP_ROM_PTR(&{func.c_name}_obj) }},"
            )

        for class_name in self.module_ir.class_order:
            class_ir = self.module_ir.classes[class_name]
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{class_ir.name}), MP_ROM_PTR(&{class_ir.c_name}_type) }},"
            )


        # Export enum members
        for enum_name in self.module_ir.enum_order:
            enum_ir = self.module_ir.enums[enum_name]
            for member_name, member_value in enum_ir.values.items():
                qstr_name = f"{enum_ir.name}_{member_name}"
                lines.append(
                    f"    {{ MP_ROM_QSTR(MP_QSTR_{qstr_name}), MP_ROM_INT({member_value}) }},"
                )

        for submodule in submodules:
            submodule_name = sanitize_name(submodule.name)
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{submodule_name}), MP_ROM_PTR(&{submodule.symbol_prefix}_module) }},"
            )

        lines.append("};")
        lines.append(
            f"MP_DEFINE_CONST_DICT({self.c_name}_module_globals, {self.c_name}_module_globals_table);"
        )
        lines.append("")
        return lines

    def _emit_module_registration(self) -> list[str]:
        return [
            f"const mp_obj_module_t {self.c_name}_user_cmodule = {{",
            "    .base = { &mp_type_module },",
            f"    .globals = (mp_obj_dict_t *)&{self.c_name}_module_globals,",
            "};",
            "",
            # Module name in QSTR uses flat c_name (no dots)
            f"MP_REGISTER_MODULE(MP_QSTR_{self.qstr_name}, {self.c_name}_user_cmodule);",
        ]
