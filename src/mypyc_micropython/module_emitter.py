"""
Module Emitter: ModuleIR -> Complete C file.

This module assembles the final C code including includes, helpers,
function code, class code, and module registration.
"""

from __future__ import annotations

import re
from typing import Any

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

        for func_code in function_code:
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
                if n_args == 0:
                    parts.append(f"extern mp_obj_t {wrapper_name}(void);")
                elif n_args <= 3:
                    args = ", ".join("mp_obj_t" for _ in range(n_args))
                    parts.append(f"extern mp_obj_t {wrapper_name}({args});")
                else:
                    parts.append(f"extern mp_obj_t {wrapper_name}(size_t, const mp_obj_t *);")
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

        for func_code in function_code:
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

        for func in functions:
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{func.name}), MP_ROM_PTR(&{func.c_name}_obj) }},"
            )

        for class_name in self.module_ir.class_order:
            class_ir = self.module_ir.classes[class_name]
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{class_ir.name}), MP_ROM_PTR(&{class_ir.c_name}_type) }},"
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
            f"MP_REGISTER_MODULE(MP_QSTR_{self.c_name}, {self.c_name}_user_cmodule);",
        ]
