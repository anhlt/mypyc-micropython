"""
Compiler: typed Python (.py) -> MicroPython usermod folder.

Output structure:
  usermod_<name>/
    <name>.c
    micropython.mk
    micropython.cmake
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from .ir import FuncIR, ModuleIR, RTuple


@dataclass
class CompilationResult:
    module_name: str
    c_code: str
    h_code: str | None
    mk_code: str
    cmake_code: str
    success: bool
    errors: list[str] = field(default_factory=list)


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


def compile_to_micropython(
    source_path: str | Path,
    output_dir: str | Path | None = None,
) -> CompilationResult:
    source_path = Path(source_path)

    if not source_path.exists():
        return CompilationResult(
            module_name="",
            c_code="",
            h_code=None,
            mk_code="",
            cmake_code="",
            success=False,
            errors=[f"Source file not found: {source_path}"],
        )

    module_name = source_path.stem

    if output_dir is None:
        output_dir = source_path.parent / f"usermod_{module_name}"
    output_dir = Path(output_dir)

    try:
        source_code = source_path.read_text()
        c_code = compile_source(source_code, module_name)
        mk_code = generate_micropython_mk(module_name)
        cmake_code = generate_micropython_cmake(module_name)

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{module_name}.c").write_text(c_code)
        (output_dir / "micropython.mk").write_text(mk_code)
        (output_dir / "micropython.cmake").write_text(cmake_code)

        return CompilationResult(
            module_name=module_name,
            c_code=c_code,
            h_code=None,
            mk_code=mk_code,
            cmake_code=cmake_code,
            success=True,
        )

    except Exception as e:
        return CompilationResult(
            module_name=module_name,
            c_code="",
            h_code=None,
            mk_code="",
            cmake_code="",
            success=False,
            errors=[str(e)],
        )


def generate_micropython_mk(module_name: str) -> str:
    c_name = sanitize_name(module_name)
    mod_upper = c_name.upper()

    return f"""\
{mod_upper}_MOD_DIR := $(USERMOD_DIR)
SRC_USERMOD += $(wildcard $({mod_upper}_MOD_DIR)/*.c)
CFLAGS_USERMOD += -I$({mod_upper}_MOD_DIR)
"""


def generate_micropython_cmake(module_name: str) -> str:
    c_name = sanitize_name(module_name)

    return f"""\
add_library(usermod_{c_name} INTERFACE)

target_sources(usermod_{c_name} INTERFACE
    ${{CMAKE_CURRENT_LIST_DIR}}/{module_name}.c
)

target_include_directories(usermod_{c_name} INTERFACE
    ${{CMAKE_CURRENT_LIST_DIR}}
)

target_link_libraries(usermod INTERFACE usermod_{c_name})
"""


def compile_source(source: str, module_name: str = "mymodule") -> str:
    """Compile typed Python source to MicroPython C code.

    Uses the IR pipeline: Python AST -> IR -> C code emission.
    """
    from .class_emitter import ClassEmitter
    from .function_emitter import FunctionEmitter, MethodEmitter
    from .ir_builder import IRBuilder
    from .module_emitter import ModuleEmitter

    tree = ast.parse(source)
    c_name = sanitize_name(module_name)
    module_ir = ModuleIR(name=module_name, c_name=c_name)

    ir_builder = IRBuilder(module_name)
    function_irs: list[FuncIR] = []
    function_code: list[str] = []
    forward_decls: list[str] = []
    struct_code: list[str] = []
    class_code: list[str] = []

    uses_print = False
    uses_list_opt = False
    uses_builtins = False
    used_rtuples: set[RTuple] = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_ir = ir_builder.build_class(node)
            module_ir.add_class(class_ir)

        elif isinstance(node, ast.FunctionDef):
            func_ir = ir_builder.build_function(node)
            function_irs.append(func_ir)
            module_ir.add_function(func_ir)

            emitter = FunctionEmitter(func_ir)
            code, _ = emitter.emit()
            function_code.append(code)

            if func_ir.uses_print:
                uses_print = True
            if func_ir.uses_list_opt:
                uses_list_opt = True
            if func_ir.uses_builtins:
                uses_builtins = True
            used_rtuples.update(func_ir.used_rtuples)

    module_ir.resolve_base_classes()

    for class_ir in module_ir.get_classes_in_order():
        class_ir.compute_layout()

    for class_ir in module_ir.get_classes_in_order():
        class_emitter = ClassEmitter(class_ir, c_name)

        forward_decls.extend(class_emitter.emit_forward_declarations())
        struct_code.extend(class_emitter.emit_struct())

        for method_ir in class_ir.methods.values():
            method_emitter = MethodEmitter(method_ir, class_ir)

            if method_ir.is_virtual and not method_ir.is_special:
                native_body = ir_builder.build_method_body(method_ir, class_ir, native=True)
                function_code.append(method_emitter.emit_native(native_body))
                function_code.append("")

            wrapper_body = None
            if not (method_ir.is_virtual and not method_ir.is_special):
                wrapper_body = ir_builder.build_method_body(method_ir, class_ir, native=False)

            function_code.append(method_emitter.emit_mp_wrapper(wrapper_body))
            function_code.append("")

        class_code.append(class_emitter.emit_all_except_struct())

    module_emitter = ModuleEmitter(
        module_ir,
        uses_print=uses_print,
        uses_list_opt=uses_list_opt,
        uses_builtins=uses_builtins,
        used_rtuples=used_rtuples,
    )

    return module_emitter.emit(
        forward_decls=forward_decls,
        struct_code=struct_code,
        function_code=function_code,
        class_code=class_code,
        functions=function_irs,
    )
