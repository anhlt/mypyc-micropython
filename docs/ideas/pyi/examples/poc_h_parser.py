#!/usr/bin/env python3
"""
Proof of Concept: Parse C header files to extract type information.

This script demonstrates two approaches:
1. pycparser - Pure Python C parser (requires preprocessing)
2. libclang - LLVM's Clang Python bindings (handles preprocessing)

Usage:
    python poc_h_parser.py [header_file.h]

If no header file is provided, uses an embedded sample.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


# ============================================================================
# Data Structures (shared between parsers)
# ============================================================================


@dataclass
class CStructDef:
    """Parsed C struct definition."""

    name: str
    c_name: str  # Original C name (e.g., "lv_obj_t")
    is_opaque: bool = True  # No fields = opaque
    fields: dict[str, str] = field(default_factory=dict)  # field_name -> c_type


@dataclass
class CEnumDef:
    """Parsed C enum definition."""

    name: str
    values: dict[str, int] = field(default_factory=dict)  # name -> value


@dataclass
class CFuncDef:
    """Parsed C function definition."""

    name: str
    return_type: str
    params: list[tuple[str, str]] = field(default_factory=list)  # [(name, type), ...]


@dataclass
class CTypedefDef:
    """Parsed C typedef."""

    name: str
    target_type: str


@dataclass
class CHeaderInfo:
    """All extracted information from a C header."""

    structs: dict[str, CStructDef] = field(default_factory=dict)
    enums: dict[str, CEnumDef] = field(default_factory=dict)
    functions: dict[str, CFuncDef] = field(default_factory=dict)
    typedefs: dict[str, CTypedefDef] = field(default_factory=dict)


# ============================================================================
# Sample C Header (for testing)
# ============================================================================

SAMPLE_HEADER = """
#ifndef SAMPLE_H
#define SAMPLE_H

#include <stdint.h>
#include <stdbool.h>

// Forward declaration (opaque struct)
typedef struct _lv_obj_t lv_obj_t;

// Non-opaque struct
typedef struct {
    int32_t x;
    int32_t y;
} lv_point_t;

// Enum
typedef enum {
    LV_ALIGN_CENTER = 0,
    LV_ALIGN_TOP_LEFT = 1,
    LV_ALIGN_TOP_MID = 2,
    LV_ALIGN_TOP_RIGHT = 3,
} lv_align_t;

// Function declarations
lv_obj_t * lv_obj_create(lv_obj_t * parent);
void lv_obj_delete(lv_obj_t * obj);
void lv_obj_set_size(lv_obj_t * obj, int32_t w, int32_t h);
void lv_obj_set_pos(lv_obj_t * obj, int32_t x, int32_t y);
const char * lv_obj_get_class_name(const lv_obj_t * obj);
bool lv_obj_is_visible(const lv_obj_t * obj);

// Function pointer typedef
typedef void (*lv_event_cb_t)(lv_obj_t * obj, int event_code);

// Function that takes callback
void lv_obj_add_event_cb(lv_obj_t * obj, lv_event_cb_t cb, int filter);

#endif
"""


# ============================================================================
# Approach 1: pycparser
# ============================================================================


def parse_with_pycparser(header_content: str) -> CHeaderInfo | None:
    """
    Parse C header using pycparser.

    IMPORTANT: pycparser does NOT handle preprocessor directives.
    We must preprocess the file first with gcc/clang -E.
    """
    try:
        from pycparser import c_parser, c_ast, c_generator
    except ImportError:
        print("pycparser not installed. Run: pip install pycparser")
        return None

    info = CHeaderInfo()
    gen = c_generator.CGenerator()

    # pycparser needs preprocessed input - remove includes and use fake stubs
    # For this POC, we'll write to a temp file and preprocess
    with tempfile.NamedTemporaryFile(mode="w", suffix=".h", delete=False) as f:
        f.write(header_content)
        temp_path = f.name

    try:
        # Preprocess with gcc -E
        # Use pycparser's fake_libc_include for standard headers
        import pycparser

        fake_libc = Path(pycparser.__file__).parent / "utils" / "fake_libc_include"

        if not fake_libc.exists():
            # Try alternative location
            fake_libc = Path(pycparser.__file__).parent / "fake_libc_include"

        cmd = ["gcc", "-E", "-std=c99", "-DPYCPARSER"]
        if fake_libc.exists():
            cmd.extend(["-I", str(fake_libc)])
        cmd.append(temp_path)

        try:
            preprocessed = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback: strip includes manually (limited but works for simple cases)
            lines = []
            for line in header_content.split("\n"):
                stripped = line.strip()
                if (
                    stripped.startswith("#include")
                    or stripped.startswith("#ifndef")
                    or stripped.startswith("#define")
                    or stripped.startswith("#endif")
                    or stripped.startswith("#ifdef")
                    or stripped.startswith("#else")
                ):
                    continue
                # Replace stdint types with basic types
                line = line.replace("int32_t", "int")
                line = line.replace("uint32_t", "unsigned int")
                line = line.replace("int8_t", "char")
                line = line.replace("uint8_t", "unsigned char")
                line = line.replace("int16_t", "short")
                line = line.replace("uint16_t", "unsigned short")
                lines.append(line)
            preprocessed = "\n".join(lines)

        # Parse the preprocessed code
        parser = c_parser.CParser()
        ast = parser.parse(preprocessed)

        # Extract information from AST
        for node in ast.ext:
            # Typedefs
            if isinstance(node, c_ast.Typedef):
                typedef_name = node.name

                # Struct typedef
                if isinstance(node.type, c_ast.TypeDecl):
                    if isinstance(node.type.type, c_ast.Struct):
                        struct = node.type.type
                        struct_def = CStructDef(
                            name=typedef_name,
                            c_name=struct.name or typedef_name,
                            is_opaque=(struct.decls is None),
                        )
                        if struct.decls:
                            for decl in struct.decls:
                                if hasattr(decl, "name") and hasattr(decl, "type"):
                                    field_name = decl.name
                                    field_type = gen.visit(decl.type)
                                    struct_def.fields[field_name] = field_type
                        info.structs[typedef_name] = struct_def

                    # Enum typedef
                    elif isinstance(node.type.type, c_ast.Enum):
                        enum = node.type.type
                        enum_def = CEnumDef(name=typedef_name)
                        if enum.values:
                            value = 0
                            for enumerator in enum.values.enumerators:
                                if enumerator.value:
                                    # Try to evaluate constant
                                    try:
                                        value = int(gen.visit(enumerator.value))
                                    except (ValueError, SyntaxError):
                                        pass
                                enum_def.values[enumerator.name] = value
                                value += 1
                        info.enums[typedef_name] = enum_def

                    # Simple typedef (type alias)
                    elif isinstance(node.type.type, c_ast.IdentifierType):
                        info.typedefs[typedef_name] = CTypedefDef(
                            name=typedef_name, target_type=" ".join(node.type.type.names)
                        )

                # Function pointer typedef
                elif isinstance(node.type, c_ast.PtrDecl) and isinstance(
                    node.type.type, c_ast.FuncDecl
                ):
                    func_decl = node.type.type
                    return_type = gen.visit(func_decl.type)
                    params = []
                    if func_decl.args:
                        for param in func_decl.args.params:
                            param_name = param.name or "arg"
                            param_type = gen.visit(param.type)
                            params.append((param_name, param_type))
                    info.typedefs[typedef_name] = CTypedefDef(
                        name=typedef_name, target_type=f"callback({return_type})"
                    )

            # Function declarations
            elif isinstance(node, c_ast.Decl) and isinstance(node.type, c_ast.FuncDecl):
                func_name = node.name
                func_decl = node.type
                return_type = gen.visit(func_decl.type)
                params = []
                if func_decl.args:
                    for param in func_decl.args.params:
                        if isinstance(param, c_ast.EllipsisParam):
                            params.append(("...", "..."))
                        else:
                            param_name = param.name or "arg"
                            param_type = gen.visit(param.type)
                            params.append((param_name, param_type))

                info.functions[func_name] = CFuncDef(
                    name=func_name, return_type=return_type, params=params
                )

        return info

    finally:
        Path(temp_path).unlink(missing_ok=True)


# ============================================================================
# Approach 2: libclang
# ============================================================================


def parse_with_libclang(header_content: str) -> CHeaderInfo | None:
    """
    Parse C header using libclang (Clang Python bindings).

    libclang handles preprocessing automatically!
    """
    try:
        import clang.cindex
        from clang.cindex import CursorKind
    except ImportError:
        print("libclang not installed. Run: pip install libclang")
        return None

    info = CHeaderInfo()

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".h", delete=False) as f:
        f.write(header_content)
        temp_path = f.name

    try:
        # Create index and parse
        index = clang.cindex.Index.create()

        # Parse with proper flags
        tu = index.parse(temp_path, args=["-std=c99"])

        def get_type_spelling(cursor_type) -> str:
            """Get clean type string."""
            return cursor_type.spelling

        def process_cursor(cursor, depth=0):
            """Recursively process AST cursor."""

            # Only process items from our file
            if cursor.location.file and cursor.location.file.name != temp_path:
                return

            kind = cursor.kind

            # Struct declaration
            if kind == CursorKind.STRUCT_DECL:
                struct_name = cursor.spelling
                if struct_name:
                    fields = {}
                    for child in cursor.get_children():
                        if child.kind == CursorKind.FIELD_DECL:
                            fields[child.spelling] = get_type_spelling(child.type)

                    info.structs[struct_name] = CStructDef(
                        name=struct_name,
                        c_name=struct_name,
                        is_opaque=(len(fields) == 0),
                        fields=fields,
                    )

            # Typedef
            elif kind == CursorKind.TYPEDEF_DECL:
                typedef_name = cursor.spelling
                underlying = cursor.underlying_typedef_type

                # Check if it's a struct typedef
                if underlying.kind == clang.cindex.TypeKind.ELABORATED:
                    decl = underlying.get_declaration()
                    if decl.kind == CursorKind.STRUCT_DECL:
                        struct_name = decl.spelling or typedef_name
                        fields = {}
                        for child in decl.get_children():
                            if child.kind == CursorKind.FIELD_DECL:
                                fields[child.spelling] = get_type_spelling(child.type)

                        info.structs[typedef_name] = CStructDef(
                            name=typedef_name,
                            c_name=struct_name,
                            is_opaque=(len(fields) == 0),
                            fields=fields,
                        )
                    elif decl.kind == CursorKind.ENUM_DECL:
                        enum_def = CEnumDef(name=typedef_name)
                        for child in decl.get_children():
                            if child.kind == CursorKind.ENUM_CONSTANT_DECL:
                                enum_def.values[child.spelling] = child.enum_value
                        info.enums[typedef_name] = enum_def

                # Function pointer typedef
                elif underlying.kind == clang.cindex.TypeKind.POINTER:
                    pointee = underlying.get_pointee()
                    if pointee.kind == clang.cindex.TypeKind.FUNCTIONPROTO:
                        info.typedefs[typedef_name] = CTypedefDef(
                            name=typedef_name,
                            target_type=f"callback({get_type_spelling(pointee.get_result())})",
                        )

                # Simple typedef
                else:
                    info.typedefs[typedef_name] = CTypedefDef(
                        name=typedef_name, target_type=get_type_spelling(underlying)
                    )

            # Enum declaration
            elif kind == CursorKind.ENUM_DECL:
                enum_name = cursor.spelling
                if enum_name:
                    enum_def = CEnumDef(name=enum_name)
                    for child in cursor.get_children():
                        if child.kind == CursorKind.ENUM_CONSTANT_DECL:
                            enum_def.values[child.spelling] = child.enum_value
                    info.enums[enum_name] = enum_def

            # Function declaration
            elif kind == CursorKind.FUNCTION_DECL:
                func_name = cursor.spelling
                return_type = get_type_spelling(cursor.result_type)
                params = []

                for child in cursor.get_children():
                    if child.kind == CursorKind.PARM_DECL:
                        param_name = child.spelling or f"arg{len(params)}"
                        param_type = get_type_spelling(child.type)
                        params.append((param_name, param_type))

                info.functions[func_name] = CFuncDef(
                    name=func_name, return_type=return_type, params=params
                )

            # Recurse into children
            for child in cursor.get_children():
                process_cursor(child, depth + 1)

        # Process the translation unit
        process_cursor(tu.cursor)

        return info

    finally:
        Path(temp_path).unlink(missing_ok=True)


# ============================================================================
# Generate .pyi stub from parsed info
# ============================================================================


def generate_pyi_stub(info: CHeaderInfo, module_name: str = "lvgl") -> str:
    """Generate a .pyi stub file from parsed C header info."""

    lines = [
        '"""',
        f"{module_name} bindings for MicroPython.",
        "",
        "Auto-generated from C header - review and edit as needed.",
        '"""',
        "",
        f'__c_header__ = "{module_name}.h"',
        "",
        "from typing import TypeVar, Generic, Callable",
        "",
        "# C type markers",
        'T = TypeVar("T")',
        "",
        "class c_ptr(Generic[T]):",
        '    """C pointer type."""',
        "    pass",
        "",
        "class c_int:",
        '    """C int type."""',
        "    pass",
        "",
        "class c_uint:",
        '    """C unsigned int type."""',
        "    pass",
        "",
        "def c_struct(c_name: str, opaque: bool = True):",
        '    """Decorator marking a class as a C struct."""',
        "    def decorator(cls): return cls",
        "    return decorator",
        "",
    ]

    # Structs
    if info.structs:
        lines.append("# Struct definitions")
        lines.append("")
        for name, struct in info.structs.items():
            opaque_str = "" if struct.is_opaque else ", opaque=False"
            lines.append(f'@c_struct("{struct.c_name}"{opaque_str})')
            lines.append(f"class {name}:")
            if struct.fields:
                for field_name, field_type in struct.fields.items():
                    py_type = c_type_to_py_type(field_type)
                    lines.append(f"    {field_name}: {py_type}")
            else:
                lines.append("    pass")
            lines.append("")

    # Enums
    if info.enums:
        lines.append("# Enum definitions")
        lines.append("")
        for name, enum in info.enums.items():
            lines.append(f"class {name}:")
            lines.append(f'    """Enum values."""')
            for val_name, val in enum.values.items():
                lines.append(f"    {val_name}: int = {val}")
            lines.append("")

    # Callbacks (function pointer typedefs)
    callbacks = {k: v for k, v in info.typedefs.items() if v.target_type.startswith("callback")}
    if callbacks:
        lines.append("# Callback types")
        for name, typedef in callbacks.items():
            lines.append(f"{name} = Callable[..., None]  # TODO: specify params")
        lines.append("")

    # Functions
    if info.functions:
        lines.append("# Function declarations")
        lines.append("")
        for name, func in info.functions.items():
            params_str = ", ".join(
                f"{pname}: {c_type_to_py_type(ptype)}" for pname, ptype in func.params
            )
            return_str = c_type_to_py_type(func.return_type)
            lines.append(f"def {name}({params_str}) -> {return_str}:")
            lines.append(f'    """Auto-generated from C declaration."""')
            lines.append(f"    ...")
            lines.append("")

    return "\n".join(lines)


def c_type_to_py_type(c_type: str) -> str:
    """Convert C type string to Python type hint."""
    c_type = c_type.strip()

    # Handle const
    if c_type.startswith("const "):
        c_type = c_type[6:]

    # Handle pointers
    if c_type.endswith("*"):
        inner = c_type[:-1].strip()
        if inner == "void":
            return "c_ptr[object]"
        if inner == "char":
            return "str"
        # Remove _t suffix for cleaner type name
        if inner.endswith("_t"):
            inner = inner[:-2].title().replace("_", "")
        return f"c_ptr[{inner}]"

    # Handle basic types
    type_map = {
        "void": "None",
        "int": "c_int",
        "int32_t": "c_int",
        "int16_t": "c_int",
        "int8_t": "c_int",
        "unsigned int": "c_uint",
        "uint32_t": "c_uint",
        "uint16_t": "c_uint",
        "uint8_t": "c_uint",
        "bool": "bool",
        "_Bool": "bool",
        "float": "float",
        "double": "float",
        "char": "c_int",
    }

    return type_map.get(c_type, c_type)


# ============================================================================
# Main
# ============================================================================


def print_info(info: CHeaderInfo, label: str):
    """Pretty print parsed info."""
    print(f"\n{'=' * 60}")
    print(f" {label}")
    print("=" * 60)

    print(f"\nStructs ({len(info.structs)}):")
    for name, struct in info.structs.items():
        opaque = "opaque" if struct.is_opaque else f"fields: {list(struct.fields.keys())}"
        print(f"  - {name} ({struct.c_name}): {opaque}")

    print(f"\nEnums ({len(info.enums)}):")
    for name, enum in info.enums.items():
        print(f"  - {name}: {list(enum.values.keys())[:3]}...")

    print(f"\nFunctions ({len(info.functions)}):")
    for name, func in info.functions.items():
        params = ", ".join(f"{p[0]}: {p[1]}" for p in func.params)
        print(f"  - {name}({params}) -> {func.return_type}")

    print(f"\nTypedefs ({len(info.typedefs)}):")
    for name, typedef in info.typedefs.items():
        print(f"  - {name} -> {typedef.target_type}")


def main():
    # Use provided header file or sample
    if len(sys.argv) > 1:
        header_path = Path(sys.argv[1])
        if not header_path.exists():
            print(f"Error: File not found: {header_path}")
            sys.exit(1)
        header_content = header_path.read_text()
        print(f"Parsing: {header_path}")
    else:
        header_content = SAMPLE_HEADER
        print("Using embedded sample header")

    print("\n" + "=" * 60)
    print(" C HEADER PARSING PROOF OF CONCEPT")
    print("=" * 60)

    # Try pycparser
    print("\n>>> Testing pycparser...")
    info_pycparser = parse_with_pycparser(header_content)
    if info_pycparser:
        print_info(info_pycparser, "PYCPARSER RESULTS")
    else:
        print("  Failed or not available")

    # Try libclang
    print("\n>>> Testing libclang...")
    info_libclang = parse_with_libclang(header_content)
    if info_libclang:
        print_info(info_libclang, "LIBCLANG RESULTS")
    else:
        print("  Failed or not available")

    # Generate stub from best result
    info = info_libclang or info_pycparser
    if info:
        print("\n" + "=" * 60)
        print(" GENERATED .pyi STUB")
        print("=" * 60 + "\n")
        stub = generate_pyi_stub(info)
        print(stub)

    # Comparison
    print("\n" + "=" * 60)
    print(" COMPARISON")
    print("=" * 60)
    print("""
| Feature                | pycparser           | libclang           |
|------------------------|---------------------|---------------------|
| Preprocessor           | Requires gcc -E     | Built-in            |
| Installation           | Pure Python         | Needs libclang.so   |
| Struct fields          | Yes                 | Yes                 |
| Enum values            | Yes                 | Yes                 |
| Function signatures    | Yes                 | Yes                 |
| Function pointers      | Yes                 | Yes                 |
| Macros (#define)       | No (after -E)       | Can access macros   |
| Comments               | No                  | Yes                 |
| Error messages         | Good                | Excellent           |
| Speed                  | Fast                | Faster              |

RECOMMENDATION:
- Use libclang if available (better preprocessor handling, macros)
- Fall back to pycparser for pure-Python environments
- Both work well for generating .pyi stubs
""")


if __name__ == "__main__":
    main()
