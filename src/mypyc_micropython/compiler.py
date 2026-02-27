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
from typing import Any

from .ir import FuncIR, ModuleIR, RTuple
from .type_checker import TypeCheckResult, type_check_file, type_check_source


@dataclass
class CompilationResult:
    module_name: str
    c_code: str
    h_code: str | None
    mk_code: str
    cmake_code: str
    success: bool
    errors: list[str] = field(default_factory=list)
    type_check_result: TypeCheckResult | None = None


@dataclass
class _ModuleCompileParts:
    module_ir: ModuleIR
    function_irs: list[FuncIR]
    function_code: list[str]
    forward_decls: list[str]
    struct_code: list[str]
    class_code: list[str]
    uses_print: bool
    uses_list_opt: bool
    uses_builtins: bool
    uses_checked_div: bool
    uses_imports: bool
    used_rtuples: set[RTuple]
    external_libs: dict[str, Any] = field(default_factory=dict)


@dataclass
class _PackageSubmodule:
    name: str
    symbol_prefix: str
    module_ir: ModuleIR
    functions: list[FuncIR]
    children: list[_PackageSubmodule] = field(default_factory=list)  # nested sub-packages


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
    *,
    type_check: bool = True,
    strict_type_check: bool = True,
    external_libs: dict[str, Any] | None = None,
) -> CompilationResult:
    """Compile typed Python file to MicroPython usermod folder.

    Args:
        source_path: Path to the Python source file
        output_dir: Output directory for the usermod folder (default: alongside source)
        type_check: Enable mypy type checking before compilation (default: True)
        strict_type_check: Enable strict mypy type checking (default: True)

    Returns:
        CompilationResult with generated C code and any errors
    """
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

    tc_result: TypeCheckResult | None = None
    if type_check:
        tc_result = type_check_file(source_path, strict=strict_type_check)
        if not tc_result.success:
            return CompilationResult(
                module_name=module_name,
                c_code="",
                h_code=None,
                mk_code="",
                cmake_code="",
                success=False,
                errors=tc_result.errors,
                type_check_result=tc_result,
            )

    try:
        source_code = source_path.read_text()
        c_code = compile_source(
            source_code,
            module_name,
            type_check=type_check,
            strict=strict_type_check,
            external_libs=external_libs,
        )
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
            type_check_result=tc_result,
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
            type_check_result=tc_result,
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


def _compile_module_parts(
    source: str,
    module_name: str,
    *,
    type_check: bool,
    strict: bool,
    external_libs: dict[str, Any] | None = None,
) -> _ModuleCompileParts:
    from .class_emitter import ClassEmitter
    from .function_emitter import FunctionEmitter, MethodEmitter
    from .generator_emitter import GeneratorEmitter
    from .ir_builder import IRBuilder, MypyTypeInfo

    mypy_types: MypyTypeInfo | None = None
    if type_check:
        tc_result = type_check_source(source, module_name, strict=strict)
        if not tc_result.success:
            error_msgs = "; ".join(tc_result.errors)
            raise TypeError(f"Type errors found: {error_msgs}")
        mypy_types = MypyTypeInfo(
            functions=tc_result.functions,
            classes=tc_result.classes,
            module_types=tc_result.module_types,
        )

    tree = ast.parse(source)
    c_name = sanitize_name(module_name)
    module_ir = ModuleIR(name=module_name, c_name=c_name)

    ir_builder = IRBuilder(module_name, mypy_types=mypy_types, external_libs=external_libs)
    function_irs: list[FuncIR] = []
    function_code: list[str] = []
    forward_decls: list[str] = []
    struct_code: list[str] = []
    class_code: list[str] = []

    uses_print = False
    uses_list_opt = False
    uses_builtins = False
    uses_checked_div = False
    uses_imports = False
    used_rtuples: set[RTuple] = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            ir_builder.register_import(node)
        elif isinstance(node, ast.ClassDef):
            class_ir = ir_builder.build_class(node)
            module_ir.add_class(class_ir)
        elif isinstance(node, ast.FunctionDef):
            func_ir = ir_builder.build_function(node)
            function_irs.append(func_ir)
            module_ir.add_function(func_ir)

            emitter = (
                GeneratorEmitter(func_ir) if func_ir.is_generator else FunctionEmitter(func_ir)
            )
            code, _ = emitter.emit()
            function_code.append(code)

            if func_ir.uses_print:
                uses_print = True
            if func_ir.uses_list_opt:
                uses_list_opt = True
            if func_ir.uses_builtins:
                uses_builtins = True
            if func_ir.uses_checked_div:
                uses_checked_div = True
            if func_ir.uses_imports:
                uses_imports = True
            used_rtuples.update(func_ir.used_rtuples)

    module_ir.imported_modules = ir_builder.imported_modules
    module_ir.resolve_base_classes()

    for class_ir in module_ir.get_classes_in_order():
        class_ir.compute_layout()

    for class_ir in module_ir.get_classes_in_order():
        class_emitter = ClassEmitter(class_ir, c_name)

        forward_decls.extend(class_emitter.emit_forward_declarations())
        struct_code.extend(class_emitter.emit_struct())

        for method_ir in class_ir.methods.values():
            method_emitter = MethodEmitter(method_ir, class_ir)

            # Private (__method) methods: emit native-only, no MP wrapper.
            # They are only called internally via direct C calls, so boxing/unboxing
            # at the MicroPython boundary is unnecessary.
            if method_ir.is_private:
                native_body = ir_builder.build_method_body(method_ir, class_ir, native=True)
                function_code.append(method_emitter.emit_native(native_body))
                function_code.append("")
                continue

            needs_native = (
                method_ir.is_static
                or method_ir.is_classmethod
                or method_ir.is_property
                or method_ir.is_final
                or (method_ir.is_virtual and not method_ir.is_special)
            )

            if needs_native:
                native_body = ir_builder.build_method_body(method_ir, class_ir, native=True)
                function_code.append(method_emitter.emit_native(native_body))
                function_code.append("")

            wrapper_body = None
            if not needs_native:
                wrapper_body = ir_builder.build_method_body(method_ir, class_ir, native=False)

            function_code.append(method_emitter.emit_mp_wrapper(wrapper_body))
            function_code.append("")

        class_code.append(class_emitter.emit_all_except_struct())

    used_libs = {
        key: value
        for key, value in (external_libs or {}).items()
        if key in ir_builder.used_external_libs
    }

    return _ModuleCompileParts(
        module_ir=module_ir,
        function_irs=function_irs,
        function_code=function_code,
        forward_decls=forward_decls,
        struct_code=struct_code,
        class_code=class_code,
        uses_print=uses_print,
        uses_list_opt=uses_list_opt,
        uses_builtins=uses_builtins,
        uses_checked_div=uses_checked_div,
        uses_imports=uses_imports,
        used_rtuples=used_rtuples,
        external_libs=used_libs,
    )


def compile_source(
    source: str,
    module_name: str = "mymodule",
    *,
    type_check: bool = True,
    strict: bool = True,
    external_libs: dict[str, Any] | None = None,
) -> str:
    """Compile typed Python source to MicroPython C code.

    Args:
        source: Python source code to compile
        module_name: Name for the generated module
        type_check: Enable mypy type checking before compilation (default: True)
        strict: Enable strict mypy type checking (default: True)

    Returns:
        Generated C code as a string

    Raises:
        TypeError: If type checking is enabled and type errors are found
    """
    from .module_emitter import ModuleEmitter

    parts = _compile_module_parts(
        source,
        module_name,
        type_check=type_check,
        strict=strict,
        external_libs=external_libs,
    )

    module_emitter = ModuleEmitter(
        parts.module_ir,
        uses_print=parts.uses_print,
        uses_list_opt=parts.uses_list_opt,
        uses_builtins=parts.uses_builtins,
        uses_checked_div=parts.uses_checked_div,
        uses_imports=parts.uses_imports,
        used_rtuples=parts.used_rtuples,
        external_libs=parts.external_libs,
    )

    return module_emitter.emit(
        forward_decls=parts.forward_decls,
        struct_code=parts.struct_code,
        function_code=parts.function_code,
        class_code=parts.class_code,
        functions=parts.function_irs,
    )


def _scan_package_recursive(
    package_path: Path,
    parent_prefix: str,
    *,
    type_check: bool,
    strict: bool,
    accumulated_parts: _ModuleCompileParts,
) -> list[_PackageSubmodule]:
    """Recursively scan a package directory and compile all .py files and sub-packages.

    Returns a list of _PackageSubmodule with nested children for sub-packages.
    All function code, forward decls, etc. are accumulated into accumulated_parts.
    """
    submodules: list[_PackageSubmodule] = []

    # First: compile .py files at this level
    for py_file in sorted(package_path.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        submodule_name = py_file.stem
        symbol_prefix = sanitize_name(f"{parent_prefix}_{submodule_name}")
        source = py_file.read_text()
        parts = _compile_module_parts(
            source,
            symbol_prefix,
            type_check=type_check,
            strict=strict,
        )
        submodules.append(
            _PackageSubmodule(
                name=submodule_name,
                symbol_prefix=symbol_prefix,
                module_ir=parts.module_ir,
                functions=parts.function_irs,
            )
        )

        accumulated_parts.forward_decls.extend(parts.forward_decls)
        accumulated_parts.struct_code.extend(parts.struct_code)
        accumulated_parts.function_code.extend(parts.function_code)
        accumulated_parts.class_code.extend(parts.class_code)

        accumulated_parts.uses_print = accumulated_parts.uses_print or parts.uses_print
        accumulated_parts.uses_list_opt = accumulated_parts.uses_list_opt or parts.uses_list_opt
        accumulated_parts.uses_builtins = accumulated_parts.uses_builtins or parts.uses_builtins
        accumulated_parts.uses_checked_div = (
            accumulated_parts.uses_checked_div or parts.uses_checked_div
        )
        accumulated_parts.uses_imports = accumulated_parts.uses_imports or parts.uses_imports
        accumulated_parts.used_rtuples.update(parts.used_rtuples)

    # Second: recurse into sub-directories with __init__.py
    for sub_dir in sorted(package_path.iterdir()):
        if not sub_dir.is_dir():
            continue
        sub_init = sub_dir / "__init__.py"
        if not sub_init.exists():
            continue

        sub_name = sub_dir.name
        sub_prefix = sanitize_name(f"{parent_prefix}_{sub_name}")

        # Compile the sub-package's __init__.py
        init_source = sub_init.read_text()
        init_parts = _compile_module_parts(
            init_source,
            sub_prefix,
            type_check=type_check,
            strict=strict,
        )

        accumulated_parts.forward_decls.extend(init_parts.forward_decls)
        accumulated_parts.struct_code.extend(init_parts.struct_code)
        accumulated_parts.function_code.extend(init_parts.function_code)
        accumulated_parts.class_code.extend(init_parts.class_code)

        accumulated_parts.uses_print = accumulated_parts.uses_print or init_parts.uses_print
        accumulated_parts.uses_list_opt = (
            accumulated_parts.uses_list_opt or init_parts.uses_list_opt
        )
        accumulated_parts.uses_builtins = (
            accumulated_parts.uses_builtins or init_parts.uses_builtins
        )
        accumulated_parts.uses_checked_div = (
            accumulated_parts.uses_checked_div or init_parts.uses_checked_div
        )
        accumulated_parts.uses_imports = accumulated_parts.uses_imports or init_parts.uses_imports
        accumulated_parts.used_rtuples.update(init_parts.used_rtuples)

        # Recurse into the sub-package
        children = _scan_package_recursive(
            sub_dir,
            sub_prefix,
            type_check=type_check,
            strict=strict,
            accumulated_parts=accumulated_parts,
        )

        submodules.append(
            _PackageSubmodule(
                name=sub_name,
                symbol_prefix=sub_prefix,
                module_ir=init_parts.module_ir,
                functions=init_parts.function_irs,
                children=children,
            )
        )

    return submodules


def compile_package(
    package_dir: str | Path,
    output_dir: str | Path | None = None,
    *,
    type_check: bool = True,
    strict_type_check: bool = True,
) -> CompilationResult:
    from .module_emitter import ModuleEmitter

    package_path = Path(package_dir)

    if not package_path.exists():
        return CompilationResult(
            module_name="",
            c_code="",
            h_code=None,
            mk_code="",
            cmake_code="",
            success=False,
            errors=[f"Package directory not found: {package_path}"],
        )

    if not package_path.is_dir():
        return CompilationResult(
            module_name="",
            c_code="",
            h_code=None,
            mk_code="",
            cmake_code="",
            success=False,
            errors=[f"Not a directory: {package_path}"],
        )

    init_path = package_path / "__init__.py"
    if not init_path.exists():
        return CompilationResult(
            module_name="",
            c_code="",
            h_code=None,
            mk_code="",
            cmake_code="",
            success=False,
            errors=[f"Package missing __init__.py: {package_path}"],
        )

    module_name = package_path.name
    if output_dir is None:
        output_dir = package_path.parent / f"usermod_{module_name}"
    output_dir = Path(output_dir)

    try:
        init_source = init_path.read_text()
        parent_parts = _compile_module_parts(
            init_source,
            module_name,
            type_check=type_check,
            strict=strict_type_check,
        )

        submodules = _scan_package_recursive(
            package_path,
            module_name,
            type_check=type_check,
            strict=strict_type_check,
            accumulated_parts=parent_parts,
        )

        module_emitter = ModuleEmitter(
            parent_parts.module_ir,
            uses_print=parent_parts.uses_print,
            uses_list_opt=parent_parts.uses_list_opt,
            uses_builtins=parent_parts.uses_builtins,
            uses_checked_div=parent_parts.uses_checked_div,
            uses_imports=parent_parts.uses_imports,
            used_rtuples=parent_parts.used_rtuples,
        )
        c_code = module_emitter.emit_package(
            forward_decls=parent_parts.forward_decls,
            struct_code=parent_parts.struct_code,
            function_code=parent_parts.function_code,
            class_code=parent_parts.class_code,
            parent_functions=parent_parts.function_irs,
            submodules=submodules,
        )

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
