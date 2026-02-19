"""
Proof of Concept: .pyi Stub Parser and C Code Generator

This is a working prototype that demonstrates the feasibility of
generating MicroPython C bindings from .pyi stub files.

Usage:
    python poc_parser.py

The script will:
1. Parse a sample .pyi stub (embedded in script)
2. Extract type information
3. Generate MicroPython C module code
4. Print the results
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum, auto


# ============================================================================
# C Type Definitions
# ============================================================================


class CType(Enum):
    """C type enumeration."""

    VOID = auto()
    INT = auto()
    UINT = auto()
    INT8 = auto()
    UINT8 = auto()
    INT16 = auto()
    UINT16 = auto()
    INT32 = auto()
    UINT32 = auto()
    FLOAT = auto()
    DOUBLE = auto()
    BOOL = auto()
    STR = auto()
    PTR = auto()
    STRUCT_PTR = auto()
    CALLBACK = auto()

    def to_c_str(self) -> str:
        mapping = {
            CType.VOID: "void",
            CType.INT: "mp_int_t",
            CType.UINT: "mp_uint_t",
            CType.INT8: "int8_t",
            CType.UINT8: "uint8_t",
            CType.INT16: "int16_t",
            CType.UINT16: "uint16_t",
            CType.INT32: "int32_t",
            CType.UINT32: "uint32_t",
            CType.FLOAT: "float",
            CType.DOUBLE: "mp_float_t",
            CType.BOOL: "bool",
            CType.STR: "const char *",
            CType.PTR: "void *",
        }
        return mapping.get(self, "void")


@dataclass
class CTypeDef:
    """Complete type definition."""

    base_type: CType
    struct_name: str | None = None


@dataclass
class CStructDef:
    """C struct definition."""

    py_name: str
    c_name: str
    is_opaque: bool = True
    fields: dict[str, CTypeDef] = field(default_factory=dict)


@dataclass
class CParamDef:
    """Function parameter definition."""

    name: str
    type_def: CTypeDef


@dataclass
class CFuncDef:
    """Function definition."""

    py_name: str
    c_name: str
    params: list[CParamDef] = field(default_factory=list)
    return_type: CTypeDef = field(default_factory=lambda: CTypeDef(CType.VOID))
    docstring: str | None = None


@dataclass
class CLibraryDef:
    """Complete library definition."""

    name: str
    header: str = ""
    structs: dict[str, CStructDef] = field(default_factory=dict)
    functions: dict[str, CFuncDef] = field(default_factory=dict)
    callbacks: dict[str, CTypeDef] = field(default_factory=dict)


# ============================================================================
# Stub Parser
# ============================================================================


class StubParser:
    """Parse .pyi stub files into CLibraryDef."""

    PRIMITIVE_TYPES = {
        "c_void": CType.VOID,
        "c_int": CType.INT,
        "c_uint": CType.UINT,
        "c_int8": CType.INT8,
        "c_uint8": CType.UINT8,
        "c_int16": CType.INT16,
        "c_uint16": CType.UINT16,
        "c_int32": CType.INT32,
        "c_uint32": CType.UINT32,
        "c_float": CType.FLOAT,
        "c_double": CType.DOUBLE,
        "c_bool": CType.BOOL,
        "c_str": CType.STR,
        # Python builtins
        "int": CType.INT,
        "float": CType.DOUBLE,
        "bool": CType.BOOL,
        "str": CType.STR,
        "None": CType.VOID,
    }

    def __init__(self):
        self.library: CLibraryDef | None = None

    def parse(self, source: str, name: str = "module") -> CLibraryDef:
        """Parse source and return CLibraryDef."""
        self.library = CLibraryDef(name=name)
        tree = ast.parse(source)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                self._parse_assign(node)
            elif isinstance(node, ast.ClassDef):
                self._parse_class(node)
            elif isinstance(node, ast.FunctionDef):
                self._parse_function(node)

        return self.library

    def _parse_assign(self, node: ast.Assign) -> None:
        """Parse assignment (module vars, type aliases)."""
        if len(node.targets) != 1:
            return
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return

        name = target.id

        # Module metadata
        if name == "__c_header__" and isinstance(node.value, ast.Constant):
            self.library.header = node.value.value
        # Callback type alias
        elif isinstance(node.value, ast.Subscript):
            if isinstance(node.value.value, ast.Name) and node.value.value.id == "Callable":
                self.library.callbacks[name] = CTypeDef(CType.CALLBACK)

    def _parse_class(self, node: ast.ClassDef) -> None:
        """Parse class definition."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "c_struct":
                    self._parse_struct(node, decorator)
                    return

    def _parse_struct(self, node: ast.ClassDef, decorator: ast.Call) -> None:
        """Parse @c_struct decorated class."""
        # Get c_name from decorator
        c_name = node.name
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            c_name = decorator.args[0].value

        # Check opaque flag
        is_opaque = True
        for kw in decorator.keywords:
            if kw.arg == "opaque" and isinstance(kw.value, ast.Constant):
                is_opaque = kw.value.value

        struct_def = CStructDef(
            py_name=node.name,
            c_name=c_name,
            is_opaque=is_opaque,
        )

        # Parse fields if not opaque
        if not is_opaque:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    field_type = self._parse_annotation(item.annotation)
                    struct_def.fields[field_name] = field_type

        self.library.structs[node.name] = struct_def

    def _parse_function(self, node: ast.FunctionDef) -> None:
        """Parse function definition."""
        func_def = CFuncDef(
            py_name=node.name,
            c_name=node.name,
            docstring=ast.get_docstring(node),
        )

        # Parse parameters
        for arg in node.args.args:
            if arg.annotation:
                param = CParamDef(
                    name=arg.arg,
                    type_def=self._parse_annotation(arg.annotation),
                )
                func_def.params.append(param)

        # Parse return type
        if node.returns:
            func_def.return_type = self._parse_annotation(node.returns)

        self.library.functions[node.name] = func_def

    def _parse_annotation(self, annotation: ast.expr) -> CTypeDef:
        """Parse type annotation to CTypeDef."""
        # Simple name: c_int, str, int, etc.
        if isinstance(annotation, ast.Name):
            name = annotation.id
            if name in self.PRIMITIVE_TYPES:
                return CTypeDef(base_type=self.PRIMITIVE_TYPES[name])
            # Assume struct reference
            return CTypeDef(base_type=CType.STRUCT_PTR, struct_name=name)

        # Subscript: c_ptr[T], Callable[...]
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                generic_name = annotation.value.id

                if generic_name == "c_ptr":
                    if isinstance(annotation.slice, ast.Name):
                        return CTypeDef(
                            base_type=CType.STRUCT_PTR,
                            struct_name=annotation.slice.id,
                        )

                if generic_name == "Callable":
                    return CTypeDef(base_type=CType.CALLBACK)

        # Union with None (optional)
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            # Take the non-None type
            left = self._parse_annotation(annotation.left)
            return left

        # Constant None
        if isinstance(annotation, ast.Constant) and annotation.value is None:
            return CTypeDef(base_type=CType.VOID)

        # Default
        return CTypeDef(base_type=CType.PTR)


# ============================================================================
# C Code Generator
# ============================================================================


class CCodeGenerator:
    """Generate C code from CLibraryDef."""

    def __init__(self, library: CLibraryDef):
        self.lib = library
        self.lines: list[str] = []

    def generate(self) -> str:
        """Generate complete C source."""
        self._emit_header()
        self._emit_helpers()
        self._emit_wrappers()
        self._emit_module_def()
        return "\n".join(self.lines)

    def _emit_header(self) -> None:
        self.lines.extend(
            [
                "/*",
                f" * MicroPython bindings for {self.lib.name}",
                " * Auto-generated from .pyi stub - do not edit",
                " */",
                "",
                '#include "py/runtime.h"',
                '#include "py/obj.h"',
            ]
        )
        if self.lib.header:
            self.lines.append(f'#include "{self.lib.header}"')
        self.lines.append("")

    def _emit_helpers(self) -> None:
        self.lines.extend(
            [
                "/* Helper functions */",
                "static inline void *mp_to_ptr(mp_obj_t obj) {",
                "    if (obj == mp_const_none) return NULL;",
                "    return MP_OBJ_TO_PTR(obj);",
                "}",
                "",
                "static inline mp_obj_t ptr_to_mp(void *ptr) {",
                "    if (ptr == NULL) return mp_const_none;",
                "    return MP_OBJ_FROM_PTR(ptr);",
                "}",
                "",
            ]
        )

    def _emit_wrappers(self) -> None:
        self.lines.append("/* Wrapper functions */")
        for func in self.lib.functions.values():
            self._emit_function_wrapper(func)
            self.lines.append("")

    def _emit_function_wrapper(self, func: CFuncDef) -> None:
        n_args = len(func.params)

        # Docstring as comment
        if func.docstring:
            self.lines.append(f"/* {func.docstring.split(chr(10))[0]} */")

        # Function signature
        if n_args == 0:
            sig = f"static mp_obj_t {func.c_name}_wrapper(void)"
        elif n_args <= 3:
            args = ", ".join(f"mp_obj_t arg{i}" for i in range(n_args))
            sig = f"static mp_obj_t {func.c_name}_wrapper({args})"
        else:
            sig = f"static mp_obj_t {func.c_name}_wrapper(size_t n_args, const mp_obj_t *args)"

        self.lines.append(sig + " {")

        # Convert arguments
        for i, param in enumerate(func.params):
            arg_ref = f"arg{i}" if n_args <= 3 else f"args[{i}]"
            conversion = self._generate_arg_conversion(param, arg_ref)
            self.lines.append(f"    {conversion}")

        # Call C function
        c_args = ", ".join(f"c_{p.name}" for p in func.params)

        if func.return_type.base_type == CType.VOID:
            self.lines.append(f"    {func.c_name}({c_args});")
            self.lines.append("    return mp_const_none;")
        else:
            ret_c_type = self._get_c_type_str(func.return_type)
            self.lines.append(f"    {ret_c_type} result = {func.c_name}({c_args});")
            ret_conv = self._generate_return_conversion(func.return_type, "result")
            self.lines.append(f"    return {ret_conv};")

        self.lines.append("}")

        # MP_DEFINE macro
        if n_args == 0:
            macro = f"static MP_DEFINE_CONST_FUN_OBJ_0({func.c_name}_obj, {func.c_name}_wrapper);"
        elif n_args == 1:
            macro = f"static MP_DEFINE_CONST_FUN_OBJ_1({func.c_name}_obj, {func.c_name}_wrapper);"
        elif n_args == 2:
            macro = f"static MP_DEFINE_CONST_FUN_OBJ_2({func.c_name}_obj, {func.c_name}_wrapper);"
        elif n_args == 3:
            macro = f"static MP_DEFINE_CONST_FUN_OBJ_3({func.c_name}_obj, {func.c_name}_wrapper);"
        else:
            macro = f"static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({func.c_name}_obj, {n_args}, {n_args}, {func.c_name}_wrapper);"

        self.lines.append(macro)

    def _generate_arg_conversion(self, param: CParamDef, arg_expr: str) -> str:
        t = param.type_def
        if t.base_type == CType.INT:
            return f"mp_int_t c_{param.name} = mp_obj_get_int({arg_expr});"
        elif t.base_type in (CType.DOUBLE, CType.FLOAT):
            return f"mp_float_t c_{param.name} = mp_obj_get_float({arg_expr});"
        elif t.base_type == CType.BOOL:
            return f"bool c_{param.name} = mp_obj_is_true({arg_expr});"
        elif t.base_type == CType.STR:
            return f"const char *c_{param.name} = mp_obj_str_get_str({arg_expr});"
        elif t.base_type == CType.STRUCT_PTR:
            struct = self.lib.structs.get(t.struct_name)
            c_type = struct.c_name if struct else "void"
            return f"{c_type} *c_{param.name} = mp_to_ptr({arg_expr});"
        else:
            return f"void *c_{param.name} = mp_to_ptr({arg_expr});"

    def _generate_return_conversion(self, type_def: CTypeDef, expr: str) -> str:
        t = type_def.base_type
        if t == CType.VOID:
            return "mp_const_none"
        elif t == CType.INT:
            return f"mp_obj_new_int({expr})"
        elif t in (CType.DOUBLE, CType.FLOAT):
            return f"mp_obj_new_float({expr})"
        elif t == CType.BOOL:
            return f"mp_obj_new_bool({expr})"
        elif t == CType.STR:
            return f"mp_obj_new_str({expr}, strlen({expr}))"
        elif t == CType.STRUCT_PTR:
            return f"ptr_to_mp((void *){expr})"
        else:
            return f"ptr_to_mp({expr})"

    def _get_c_type_str(self, type_def: CTypeDef) -> str:
        if type_def.base_type == CType.STRUCT_PTR:
            struct = self.lib.structs.get(type_def.struct_name)
            if struct:
                return f"{struct.c_name} *"
            return "void *"
        return type_def.base_type.to_c_str()

    def _emit_module_def(self) -> None:
        self.lines.extend(
            [
                "/* Module definition */",
                f"static const mp_rom_map_elem_t {self.lib.name}_globals_table[] = {{",
                f"    {{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_{self.lib.name}) }},",
            ]
        )

        for func in self.lib.functions.values():
            self.lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{func.py_name}), MP_ROM_PTR(&{func.c_name}_obj) }},"
            )

        self.lines.extend(
            [
                "};",
                f"static MP_DEFINE_CONST_DICT({self.lib.name}_globals, {self.lib.name}_globals_table);",
                "",
                f"const mp_obj_module_t {self.lib.name}_user_cmodule = {{",
                "    .base = { &mp_type_module },",
                f"    .globals = (mp_obj_dict_t *)&{self.lib.name}_globals,",
                "};",
                "",
                f"MP_REGISTER_MODULE(MP_QSTR_{self.lib.name}, {self.lib.name}_user_cmodule);",
            ]
        )


# ============================================================================
# Main - Demonstration
# ============================================================================

SAMPLE_STUB = '''
"""LVGL bindings for MicroPython."""

__c_header__ = "lvgl.h"

from typing import Callable

# Type markers (would be imported from c_types in real usage)
class c_ptr:
    pass

class c_int:
    pass

def c_struct(c_name: str, opaque: bool = True):
    def decorator(cls):
        return cls
    return decorator

# Struct definitions
@c_struct("lv_obj_t")
class LvObj:
    """Base LVGL widget object."""
    pass

@c_struct("lv_event_t")
class LvEvent:
    """Event object passed to callbacks."""
    pass

# Callback type
EventCallback = Callable[[c_ptr[LvEvent]], None]

# Functions
def lv_scr_act() -> c_ptr[LvObj]:
    """Get the currently active screen."""
    ...

def lv_btn_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """Create a new button widget."""
    ...

def lv_obj_set_size(obj: c_ptr[LvObj], w: c_int, h: c_int) -> None:
    """Set the size of an object in pixels."""
    ...

def lv_label_create(parent: c_ptr[LvObj]) -> c_ptr[LvObj]:
    """Create a new label widget."""
    ...

def lv_label_set_text(label: c_ptr[LvObj], text: str) -> None:
    """Set the text content of a label."""
    ...
'''


def main():
    print("=" * 70)
    print("PROOF OF CONCEPT: .pyi Stub Parser and C Code Generator")
    print("=" * 70)

    # Parse the stub
    parser = StubParser()
    library = parser.parse(SAMPLE_STUB, name="lvgl")

    print("\n" + "-" * 70)
    print("PARSED LIBRARY DEFINITION")
    print("-" * 70)

    print(f"\nModule: {library.name}")
    print(f"Header: {library.header}")

    print("\nStructs:")
    for name, struct in library.structs.items():
        print(f"  {name} -> {struct.c_name} (opaque={struct.is_opaque})")

    print("\nFunctions:")
    for name, func in library.functions.items():
        params = ", ".join(f"{p.name}: {p.type_def.base_type.name}" for p in func.params)
        ret = func.return_type.base_type.name
        print(f"  {name}({params}) -> {ret}")

    print("\nCallbacks:")
    for name in library.callbacks:
        print(f"  {name}")

    # Generate C code
    generator = CCodeGenerator(library)
    c_code = generator.generate()

    print("\n" + "-" * 70)
    print("GENERATED C CODE")
    print("-" * 70 + "\n")
    print(c_code)

    print("\n" + "=" * 70)
    print("SUCCESS: Proof of concept demonstrates feasibility of Option A")
    print("=" * 70)


if __name__ == "__main__":
    main()
