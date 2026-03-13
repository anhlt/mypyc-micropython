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
from typing import Any, cast

from .ir import CType, FuncIR, ModuleIR, RTuple
from .type_checker import TypeCheckResult, type_check_file, type_check_package, type_check_source


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
    class_constants: list[str]  # #define constants for Final class attrs
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


def _get_return_type_from_annotation(returns: ast.expr | None) -> CType:
    """Extract CType from a function's return type annotation.

    Args:
        returns: The AST node for the return type annotation (node.returns)

    Returns:
        CType corresponding to the annotation.
        - None annotation (no return type specified) -> MP_OBJ_T (returns mp_const_none)
        - Unknown type annotations -> MP_OBJ_T (consistent with CType.from_python_type)
    """
    if returns is None:
        # No return annotation - function returns mp_const_none by default
        return CType.MP_OBJ_T

    # Handle ast.Name (simple types like 'int', 'float', 'bool', 'object')
    if isinstance(returns, ast.Name):
        type_name = returns.id
        type_map = {
            "int": CType.MP_INT_T,
            "float": CType.MP_FLOAT_T,
            "bool": CType.BOOL,
            "object": CType.MP_OBJ_T,
            "str": CType.MP_OBJ_T,
            "list": CType.MP_OBJ_T,
            "dict": CType.MP_OBJ_T,
            "tuple": CType.MP_OBJ_T,
            "set": CType.MP_OBJ_T,
            "None": CType.VOID,
        }
        # Default to MP_OBJ_T for unknown types (consistent with CType.from_python_type)
        return type_map.get(type_name, CType.MP_OBJ_T)

    # Handle ast.Constant for None
    if isinstance(returns, ast.Constant) and returns.value is None:
        return CType.VOID

    # Handle ast.Subscript (generic types like list[int], dict[str, int], Optional[int])
    if isinstance(returns, ast.Subscript):
        # For now, treat all generic containers as mp_obj_t
        return CType.MP_OBJ_T

    # Default to MP_OBJ_T for unknown annotations (consistent with CType.from_python_type)
    return CType.MP_OBJ_T


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

target_compile_options(usermod_{c_name} INTERFACE
    -Wno-error=unused-variable
    -Wno-error=unused-function
    -Wno-error=unused-const-variable
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
    sibling_modules: dict[str, str] | None = None,  # maps import name -> C prefix
    sibling_constants: dict[str, dict[str, int | float | str | bool | None]] | None = None,
    known_classes: dict[str, Any] | None = None,
    known_enums: dict[str, Any] | None = None,
    func_class_returns: dict[str, str] | None = None,
    mypy_type_result: TypeCheckResult | None = None,
) -> _ModuleCompileParts:
    from .async_emitter import AsyncEmitter
    from .class_emitter import ClassEmitter
    from .function_emitter import BaseEmitter, FunctionEmitter, MethodEmitter
    from .generator_emitter import GeneratorEmitter
    from .ir_builder import IRBuilder, MypyTypeInfo

    mypy_types: MypyTypeInfo | None = None
    if mypy_type_result is not None:
        # Use pre-computed package-level type check result (cross-module aware).
        # Don't raise on errors here -- package-level checking may report
        # false positives (e.g. "object not callable" for fields typed as
        # object that are actually callables).  The type *info* is still
        # valuable even when some errors exist.
        mypy_types = MypyTypeInfo(
            functions=mypy_type_result.functions,
            classes=mypy_type_result.classes,
            module_types=mypy_type_result.module_types,
        )
    elif type_check:
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

    ir_builder = IRBuilder(
        module_name,
        known_classes=known_classes,
        known_enums=known_enums,
        mypy_types=mypy_types,
        external_libs=external_libs,
        sibling_modules=sibling_modules,
        sibling_constants=sibling_constants,
        func_class_returns=func_class_returns,
    )
    function_irs: list[FuncIR] = []
    function_code: list[str] = []
    forward_decls: list[str] = []
    struct_code: list[str] = []
    class_code: list[str] = []
    class_constants: list[str] = []  # #define constants for Final class attrs

    uses_print = False
    uses_list_opt = False
    uses_builtins = False
    uses_checked_div = False
    uses_imports = False
    used_rtuples: set[RTuple] = set()

    # Pre-scan: collect all module-level function names so that functions/classes
    # defined earlier can reference functions defined later as first-class values
    # (e.g., sorted(items, key=my_func) where my_func is defined after the caller).
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_c_name = f"{c_name}_{sanitize_name(node.name)}"
            # Extract return type from function annotation
            return_type = _get_return_type_from_annotation(node.returns)
            ir_builder.register_function_name(node.name, func_c_name, return_type)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            ir_builder.register_import(node)
        elif isinstance(node, ast.Assign):
            # Register TypeVar assignments: T = TypeVar('T', bound=int)
            if not ir_builder.register_typevar(node):
                # Register module-level constants (NAME = literal)
                ir_builder.register_constant(node)
        elif isinstance(node, ast.AnnAssign):
            ir_builder.register_module_var(node)
        elif isinstance(node, ast.ClassDef):
            if ir_builder.is_enum_class(node):
                enum_ir = ir_builder.build_enum(node)
                module_ir.add_enum(enum_ir)
            else:
                class_ir = ir_builder.build_class(node)
                module_ir.add_class(class_ir)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_ir = ir_builder.build_function(node)
            function_irs.append(func_ir)
            module_ir.add_function(func_ir)


            # Select appropriate emitter based on function type
            if func_ir.is_async:
                emitter: BaseEmitter = AsyncEmitter(func_ir)
            elif func_ir.is_generator:
                emitter = GeneratorEmitter(func_ir)
            else:
                emitter = FunctionEmitter(func_ir)

            # Generate forward declaration for this function
            forward_decls.append(emitter.emit_forward_declaration())

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
    module_ir.constants = ir_builder.module_constants
    module_ir.module_vars = ir_builder.module_vars
    module_ir.resolve_base_classes()

    for class_ir in module_ir.get_classes_in_order():
        class_ir.compute_layout()

    for class_ir in module_ir.get_classes_in_order():
        class_emitter = ClassEmitter(class_ir, c_name)

        forward_decls.extend(class_emitter.emit_forward_declarations())
        forward_decls.extend(class_emitter.emit_type_forward_declarations())
        forward_decls.extend(class_emitter.emit_native_forward_declarations())
        forward_decls.extend(class_emitter.emit_method_obj_forward_declarations())
        struct_code.extend(class_emitter.emit_struct())

        # Collect #define constants for Final class attributes
        # These must be emitted before function code that uses them
        class_constants.extend(class_emitter.emit_class_constants())

        # Process methods in order: non-__init__ first, then __init__
        # This ensures bound method objects (e.g., self._build_home) are defined
        # before being referenced in __init__
        methods_ordered = sorted(
            class_ir.methods.values(), key=lambda m: (m.name == "__init__", m.name)
        )
        for method_ir in methods_ordered:

            # Private (__method) methods: emit native-only, no MP wrapper.
            # They are only called internally via direct C calls, so boxing/unboxing
            # at the MicroPython boundary is unnecessary.
            if method_ir.is_private:
                native_body = ir_builder.build_method_body(method_ir, class_ir, native=True)
                # Create emitter AFTER build_method_body so max_temp is correct
                method_emitter = MethodEmitter(method_ir, class_ir)
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
                # Create emitter AFTER build_method_body so max_temp is correct
                method_emitter = MethodEmitter(method_ir, class_ir)
                function_code.append(method_emitter.emit_native(native_body))
                function_code.append("")

            wrapper_body = None
            if not needs_native:
                wrapper_body = ir_builder.build_method_body(method_ir, class_ir, native=False)
                # Create emitter AFTER build_method_body so max_temp is correct
                method_emitter = MethodEmitter(method_ir, class_ir)

            function_code.append(method_emitter.emit_mp_wrapper(wrapper_body))
            function_code.append("")

        class_code.append(class_emitter.emit_all_except_struct())

    # Emit all lambda functions generated during function/method building
    # NOTE: Must be after class method processing since methods may contain lambdas
    for lambda_func_ir in ir_builder.lambda_funcs:
        # Add to module (but not to module globals - lambdas are internal)
        lambda_emitter = FunctionEmitter(lambda_func_ir)
        forward_decls.append(lambda_emitter.emit_forward_declaration())
        lambda_code, _ = lambda_emitter.emit()
        function_code.append(lambda_code)
        used_rtuples.update(lambda_func_ir.used_rtuples)

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
        class_constants=class_constants,
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
        class_constants=parts.class_constants,
        function_code=parts.function_code,
        class_code=parts.class_code,
        functions=parts.function_irs,
    )


def _extract_module_constants(source: str) -> dict[str, int | float | str | bool | None]:
    """Extract module-level constants from Python source.

    Returns a dict mapping constant names to their literal values.
    Only handles simple NAME = literal_value assignments.
    """
    constants: dict[str, int | float | str | bool | None] = {}
    tree = ast.parse(source)

    for node in ast.iter_child_nodes(tree):
        # Handle NAME = literal
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                constants[target.id] = cast(int | float | str | bool | None, node.value.value)
            elif isinstance(target, ast.Name) and isinstance(node.value, ast.UnaryOp):
                # Handle negative numbers: -1, -3.14
                if isinstance(node.value.op, ast.USub) and isinstance(node.value.operand, ast.Constant):
                    if isinstance(node.value.operand.value, (int, float)):
                        constants[target.id] = -node.value.operand.value

        # Handle NAME: Type = literal
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value and isinstance(node.value, ast.Constant):
                constants[node.target.id] = cast(int | float | str | bool | None, node.value.value)
            elif node.value and isinstance(node.value, ast.UnaryOp):
                if isinstance(node.value.op, ast.USub) and isinstance(node.value.operand, ast.Constant):
                    if isinstance(node.value.operand.value, (int, float)):
                        constants[node.target.id] = -node.value.operand.value

    return constants

def _scan_package_recursive(
    package_path: Path,
    parent_prefix: str,
    parent_python_name: str,
    *,
    type_check: bool,
    strict: bool,
    accumulated_parts: _ModuleCompileParts,
    sibling_modules: dict[str, str] | None = None,  # maps import name -> C prefix
    pkg_type_results: dict[str, TypeCheckResult] | None = None,
) -> list[_PackageSubmodule]:
    """Recursively scan a package directory and compile all .py files and sub-packages.

    Returns a list of _PackageSubmodule with nested children for sub-packages.
    All function code, forward decls, etc. are accumulated into accumulated_parts.

    If pkg_type_results is provided, it contains pre-computed per-file type
    check results from type_check_package() that properly resolve cross-module
    imports.  Otherwise falls back to per-file type checking.
    """
    submodules: list[_PackageSubmodule] = []

    from .ir_builder import IRBuilder as _IRBuilder

    package_classes: dict[str, Any] = {}
    package_enums: dict[str, Any] = {}
    package_constants: dict[str, dict[str, int | float | str | bool | None]] = {}
    package_func_class_returns: dict[str, str] = {}  # func_name -> class return type
    for py_file in sorted(package_path.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text()
        tree = ast.parse(source)
        scanner = _IRBuilder(sanitize_name(f"{parent_prefix}_{py_file.stem}"))

        # Extract module-level constants
        module_name = f"{parent_prefix}.{py_file.stem}".lstrip('.')
        package_constants[module_name] = _extract_module_constants(source)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                scanner.register_import(node)
            elif isinstance(node, ast.ClassDef):
                if scanner.is_enum_class(node):
                    enum_ir = scanner.build_enum(node)
                    package_enums[enum_ir.name] = enum_ir
                else:
                    class_ir = scanner.build_class(node)
                    package_classes[class_ir.name] = class_ir

    # Second pass: scan function return types that return known classes
    for py_file in sorted(package_path.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns and isinstance(node.returns, ast.Name):
                    ret_name = node.returns.id
                    if ret_name in package_classes:
                        package_func_class_returns[node.name] = ret_name

    # First: compile .py files at this level
    for py_file in sorted(package_path.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        submodule_name = py_file.stem
        symbol_prefix = sanitize_name(f"{parent_prefix}_{submodule_name}")
        source = py_file.read_text()
        # Look up pre-computed type check result for this submodule
        sub_type_result: TypeCheckResult | None = None
        if pkg_type_results is not None:
            sub_type_result = pkg_type_results.get(submodule_name)
        parts = _compile_module_parts(
            source,
            symbol_prefix,
            type_check=type_check and sub_type_result is None,
            strict=strict,
            sibling_modules=sibling_modules,
            sibling_constants=package_constants,
            known_classes=package_classes,
            known_enums=package_enums,
            func_class_returns=package_func_class_returns,
            mypy_type_result=sub_type_result,
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
        accumulated_parts.class_constants.extend(parts.class_constants)

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
        sub_python_name = f"{parent_python_name}.{sub_name}"

        # Compile the sub-package's __init__.py
        init_source = sub_init.read_text()
        # For sub-packages, do package-level type checking
        sub_pkg_type_results: dict[str, TypeCheckResult] | None = None
        if type_check:
            sub_pkg_type_results = type_check_package(
                sub_dir,
                package_name=sub_python_name,
                strict=strict,
            )
        # Use sub-package type result for __init__.py
        init_type_result_sub: TypeCheckResult | None = None
        if sub_pkg_type_results is not None:
            init_type_result_sub = sub_pkg_type_results.get("__init__")
        init_parts = _compile_module_parts(
            init_source,
            sub_prefix,
            type_check=type_check and init_type_result_sub is None,
            strict=strict,
            sibling_modules=sibling_modules,
            mypy_type_result=init_type_result_sub,
        )

        accumulated_parts.forward_decls.extend(init_parts.forward_decls)
        accumulated_parts.struct_code.extend(init_parts.struct_code)
        accumulated_parts.function_code.extend(init_parts.function_code)
        accumulated_parts.class_code.extend(init_parts.class_code)
        accumulated_parts.class_constants.extend(init_parts.class_constants)

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
            sub_python_name,
            type_check=type_check,
            strict=strict,
            accumulated_parts=accumulated_parts,
            sibling_modules=sibling_modules,
            pkg_type_results=sub_pkg_type_results,
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
        # Package-level type checking: type-check all files at once so mypy
        # resolves cross-module imports correctly (not reported as Any).
        pkg_type_results: dict[str, TypeCheckResult] | None = None
        if type_check:
            pkg_type_results = type_check_package(
                package_path,
                package_name=module_name,
                strict=strict_type_check,
            )

        init_source = init_path.read_text()
        # Use the pre-computed result for __init__.py if available
        init_type_result = pkg_type_results.get("__init__") if pkg_type_results else None
        parent_parts = _compile_module_parts(
            init_source,
            module_name,
            type_check=type_check and init_type_result is None,
            strict=strict_type_check,
            mypy_type_result=init_type_result,
        )

        # Build sibling modules map: maps import name -> C prefix
        # This allows submodules to import each other by name (e.g., 'import screens')
        # and have those imports resolved to direct C function calls
        sibling_modules: dict[str, str] = {}
        for py_file in package_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            submod_name = py_file.stem
            c_prefix = sanitize_name(f"{module_name}_{submod_name}")
            # Map both short name and full qualified name
            sibling_modules[submod_name] = c_prefix
            sibling_modules[f"{module_name}.{submod_name}"] = c_prefix

        submodules = _scan_package_recursive(
            package_path,
            module_name,
            module_name,
            type_check=type_check,
            strict=strict_type_check,
            accumulated_parts=parent_parts,
            sibling_modules=sibling_modules,
            pkg_type_results=pkg_type_results,
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
            class_constants=parent_parts.class_constants,
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
