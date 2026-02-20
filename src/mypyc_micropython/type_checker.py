"""
Type Checker: Validate Python source using mypy's semantic analysis.

This module provides type checking functionality using mypy's build API
to validate type annotations before IR building. It detects type mismatches,
missing annotations, and other type errors at compile time.

Usage:
    from mypyc_micropython.type_checker import type_check_source, TypeCheckResult

    result = type_check_source(source_code, "module_name")
    if not result.success:
        for error in result.errors:
            print(f"Type error: {error}")
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from mypy import build as mypy_build
from mypy.errors import CompileError
from mypy.nodes import AssignmentStmt, ClassDef, FuncDef, MypyFile, NameExpr, Var
from mypy.nodes import TypeInfo as MypyTypeInfo
from mypy.options import Options
from mypy.types import CallableType, Type


@dataclass
class TypeInfo:
    """Type information for a variable or expression."""

    name: str
    py_type: str  # Python type as string (e.g., "int", "list[str]")
    is_optional: bool = False

    @staticmethod
    def from_mypy_type(mypy_type: Type | None) -> TypeInfo:
        """Create TypeInfo from mypy Type object."""
        if mypy_type is None:
            return TypeInfo(name="", py_type="Any", is_optional=False)

        type_str = str(mypy_type)
        is_optional = "None" in type_str or "Optional" in type_str

        return TypeInfo(name="", py_type=type_str, is_optional=is_optional)


@dataclass
class FunctionTypeInfo:
    """Type information for a function."""

    name: str
    params: list[tuple[str, str]]  # (name, type) pairs
    return_type: str
    is_method: bool = False
    local_types: dict[str, str] = field(default_factory=dict)  # local var -> type


@dataclass
class ClassTypeInfo:
    """Type information for a class."""

    name: str
    fields: list[tuple[str, str]]  # (name, type) pairs
    methods: list[FunctionTypeInfo]
    base_class: str | None = None


@dataclass
class TypeCheckResult:
    """Result of type checking a Python source file.

    Attributes:
        success: True if no type errors were found
        errors: List of type error messages
        warnings: List of warning messages
        functions: Dict mapping function name to type information
        classes: Dict mapping class name to type information
        module_types: Dict mapping variable name to type string
    """

    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    functions: dict[str, FunctionTypeInfo] = field(default_factory=dict)
    classes: dict[str, ClassTypeInfo] = field(default_factory=dict)
    module_types: dict[str, str] = field(default_factory=dict)


def create_mypy_options(
    *,
    python_version: tuple[int, int] = (3, 10),
    strict: bool = False,
    check_untyped: bool = True,
) -> Options:
    """Create mypy Options configured for mypyc-micropython.

    Args:
        python_version: Target Python version tuple (major, minor)
        strict: Enable strict mode (all strict checks)
        check_untyped: Require type annotations on all definitions

    Returns:
        Configured mypy Options object
    """
    options = Options()

    options.python_version = python_version
    options.incremental = False
    options.strict_optional = True
    options.preserve_asts = True  # Keep AST bodies for local type extraction

    # Annotation requirements
    if check_untyped:
        options.disallow_untyped_defs = True
        options.disallow_incomplete_defs = True

    # Strict mode enables additional checks
    if strict:
        options.warn_redundant_casts = True
        options.warn_unused_ignores = True
        options.warn_return_any = True
        options.strict_equality = True
        options.disallow_any_generics = True
        options.disallow_subclassing_any = True
        options.disallow_untyped_calls = True
        options.disallow_untyped_decorators = True
        options.implicit_optional = False

    return options


def type_check_source(
    source: str,
    module_name: str = "module",
    *,
    python_version: tuple[int, int] = (3, 10),
    strict: bool = False,
    check_untyped: bool = False,
) -> TypeCheckResult:
    """Type check Python source code using mypy.

    This function runs mypy's semantic analysis and type checking on the
    provided source code, returning detailed type information and any errors.

    Args:
        source: Python source code to type check
        module_name: Name to use for the module
        python_version: Target Python version tuple
        strict: Enable strict type checking mode
        check_untyped: Require type annotations on all definitions

    Returns:
        TypeCheckResult with success status, errors, and type information

    Example:
        >>> source = '''
        ... def add(a: int, b: int) -> int:
        ...     return a + b
        ... '''
        >>> result = type_check_source(source, "example")
        >>> result.success
        True
        >>> result.functions["add"].return_type
        'int'
    """
    # Create temporary file for mypy (it needs a file path)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix=f"{module_name}_"
    ) as f:
        f.write(source)
        temp_path = f.name

    try:
        return _run_type_check(temp_path, module_name, python_version, strict, check_untyped)
    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)


def type_check_file(
    file_path: str | Path,
    *,
    python_version: tuple[int, int] = (3, 10),
    strict: bool = False,
    check_untyped: bool = False,
) -> TypeCheckResult:
    """Type check a Python file using mypy.

    Args:
        file_path: Path to the Python file to check
        python_version: Target Python version tuple
        strict: Enable strict type checking mode
        check_untyped: Require type annotations on all definitions

    Returns:
        TypeCheckResult with success status, errors, and type information
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return TypeCheckResult(
            success=False,
            errors=[f"File not found: {file_path}"],
        )

    module_name = file_path.stem
    return _run_type_check(str(file_path), module_name, python_version, strict, check_untyped)


def _run_type_check(
    file_path: str,
    module_name: str,
    python_version: tuple[int, int],
    strict: bool,
    check_untyped: bool,
) -> TypeCheckResult:
    """Internal function to run mypy type checking."""
    options = create_mypy_options(
        python_version=python_version,
        strict=strict,
        check_untyped=check_untyped,
    )

    # Create BuildSource
    sources = [mypy_build.BuildSource(file_path, module_name, None)]

    # Run mypy build (semantic analysis + type checking)
    try:
        build_result = mypy_build.build(sources=sources, options=options)
    except CompileError as e:
        return TypeCheckResult(
            success=False,
            errors=list(e.messages) if hasattr(e, "messages") else [str(e)],
        )

    # Check for errors
    errors = list(build_result.errors)
    warnings: list[str] = []

    # Separate errors from warnings (notes)
    actual_errors: list[str] = []
    for msg in errors:
        if ": note:" in msg:
            warnings.append(msg)
        else:
            actual_errors.append(msg)

    # Extract type information from the typed AST
    functions: dict[str, FunctionTypeInfo] = {}
    classes: dict[str, ClassTypeInfo] = {}
    module_types: dict[str, str] = {}

    mypy_file = build_result.files.get(module_name)
    if mypy_file:
        _extract_type_info(mypy_file, functions, classes, module_types)

    return TypeCheckResult(
        success=len(actual_errors) == 0,
        errors=actual_errors,
        warnings=warnings,
        functions=functions,
        classes=classes,
        module_types=module_types,
    )


def _extract_type_info(
    mypy_file: MypyFile,
    functions: dict[str, FunctionTypeInfo],
    classes: dict[str, ClassTypeInfo],
    module_types: dict[str, str],
) -> None:
    """Extract type information from mypy's typed AST.

    Note: mypy stores definitions in the symbol table (names), not defs.
    We iterate over the symbol table to extract type information.
    """
    builtin_names = {
        "__builtins__",
        "__name__",
        "__doc__",
        "__file__",
        "__package__",
        "__annotations__",
        "__spec__",
    }

    for name, sym in mypy_file.names.items():
        if name in builtin_names:
            continue

        node = sym.node
        if node is None:
            continue

        if isinstance(node, FuncDef):
            func_info = _extract_function_info(node)
            functions[func_info.name] = func_info

        elif isinstance(node, MypyTypeInfo):
            class_info = _extract_class_info_from_typeinfo(node)
            classes[class_info.name] = class_info

        elif isinstance(node, ClassDef):
            class_info = _extract_class_info_from_classdef(node)
            classes[class_info.name] = class_info

        elif hasattr(node, "type") and node.type:
            module_types[name] = str(node.type)


def _clean_type_str(type_str: str) -> str:
    """Clean up mypy type string for display."""
    type_str = type_str.replace("builtins.", "")
    type_str = type_str.replace("?", "")
    return type_str


def _extract_function_info(func_def: FuncDef) -> FunctionTypeInfo:
    """Extract type information from a FuncDef node."""
    name = func_def.name
    params: list[tuple[str, str]] = []
    return_type = "Any"
    local_types: dict[str, str] = {}

    if func_def.arguments:
        for arg in func_def.arguments:
            param_name = arg.variable.name
            if arg.type_annotation:
                param_type = _clean_type_str(str(arg.type_annotation))
            else:
                param_type = "Any"
            params.append((param_name, param_type))

    if func_def.type:
        if isinstance(func_def.type, CallableType):
            return_type = _clean_type_str(str(func_def.type.ret_type))
        else:
            return_type = _clean_type_str(str(func_def.type))

    # Extract local variable types from function body
    # mypy stores inferred types on Var nodes via AssignmentStmt lvalues
    _extract_local_types(func_def.body.body, local_types)

    return FunctionTypeInfo(
        name=name,
        params=params,
        return_type=return_type,
        is_method=False,
        local_types=local_types,
    )


def _extract_local_types(stmts: list, local_types: dict[str, str]) -> None:
    """Recursively extract local variable types from mypy AST statements."""
    from mypy.nodes import Block, ForStmt, IfStmt, WhileStmt, WithStmt

    for stmt in stmts:
        if isinstance(stmt, AssignmentStmt):
            for lvalue in stmt.lvalues:
                if isinstance(lvalue, NameExpr) and isinstance(lvalue.node, Var):
                    var_node = lvalue.node
                    if var_node.type is not None:
                        local_types[lvalue.name] = _clean_type_str(str(var_node.type))

        elif isinstance(stmt, IfStmt):
            for body in stmt.body:
                _extract_local_types(body.body, local_types)
            if stmt.else_body:
                _extract_local_types(stmt.else_body.body, local_types)

        elif isinstance(stmt, WhileStmt):
            _extract_local_types(stmt.body.body, local_types)
            if stmt.else_body:
                _extract_local_types(stmt.else_body.body, local_types)

        elif isinstance(stmt, ForStmt):
            _extract_local_types(stmt.body.body, local_types)
            if stmt.else_body:
                _extract_local_types(stmt.else_body.body, local_types)

        elif isinstance(stmt, WithStmt):
            _extract_local_types(stmt.body.body, local_types)

        elif isinstance(stmt, Block):
            _extract_local_types(stmt.body, local_types)


def _extract_class_info_from_typeinfo(type_info: MypyTypeInfo) -> ClassTypeInfo:
    """Extract type information from a mypy TypeInfo node.

    TypeInfo is mypy's representation of a class after semantic analysis.
    Fields and methods are stored in its symbol table (names), not in the ClassDef.
    """
    name = type_info.name
    fields: list[tuple[str, str]] = []
    methods: list[FunctionTypeInfo] = []
    base_class: str | None = None

    if type_info.bases:
        for base in type_info.bases:
            base_name = str(base)
            if base_name not in ("builtins.object", "object"):
                base_class = base_name.split(".")[-1]
                break

    for member_name, sym in type_info.names.items():
        node = sym.node
        if node is None:
            continue

        if isinstance(node, FuncDef):
            method_info = _extract_function_info(node)
            method_info.is_method = True
            if method_info.params and method_info.params[0][0] == "self":
                method_info.params = method_info.params[1:]
            methods.append(method_info)

        elif isinstance(node, Var):
            field_type = str(node.type) if node.type else "Any"
            field_type = _clean_type_str(field_type)
            fields.append((member_name, field_type))

    return ClassTypeInfo(
        name=name,
        fields=fields,
        methods=methods,
        base_class=base_class,
    )


def _extract_class_info_from_classdef(class_def: ClassDef) -> ClassTypeInfo:
    """Extract type information from a ClassDef node (fallback)."""
    name = class_def.name
    fields: list[tuple[str, str]] = []
    methods: list[FunctionTypeInfo] = []
    base_class: str | None = None

    if class_def.base_type_exprs:
        base_expr = class_def.base_type_exprs[0]
        if hasattr(base_expr, "name"):
            base_name = base_expr.name
            if base_name not in ("object", "Object"):
                base_class = base_name

    for stmt in class_def.defs.body:
        if isinstance(stmt, FuncDef):
            method_info = _extract_function_info(stmt)
            method_info.is_method = True
            if method_info.params and method_info.params[0][0] == "self":
                method_info.params = method_info.params[1:]
            methods.append(method_info)

        elif isinstance(stmt, AssignmentStmt):
            for lvalue in stmt.lvalues:
                if hasattr(lvalue, "name"):
                    field_name = lvalue.name
                    if stmt.type:
                        field_type = str(stmt.type)
                    elif hasattr(lvalue, "type") and lvalue.type:
                        field_type = str(lvalue.type)
                    else:
                        field_type = "Any"
                    fields.append((field_name, field_type))

    return ClassTypeInfo(
        name=name,
        fields=fields,
        methods=methods,
        base_class=base_class,
    )


def format_type_errors(result: TypeCheckResult) -> str:
    """Format type check errors for display.

    Args:
        result: TypeCheckResult from type_check_source or type_check_file

    Returns:
        Formatted string with all errors, suitable for display
    """
    if result.success:
        return "No type errors found."

    lines = [f"Found {len(result.errors)} type error(s):"]
    for error in result.errors:
        # Clean up error message format
        # Typical format: "path:line: error: message [code]"
        if ": error:" in error:
            # Extract just the error message part
            parts = error.split(": error:", 1)
            if len(parts) == 2:
                location = parts[0].split(":")[-1] if ":" in parts[0] else ""
                message = parts[1].strip()
                if location:
                    lines.append(f"  Line {location}: {message}")
                else:
                    lines.append(f"  {message}")
            else:
                lines.append(f"  {error}")
        else:
            lines.append(f"  {error}")

    return "\n".join(lines)
