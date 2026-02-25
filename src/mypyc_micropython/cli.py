#!/usr/bin/env python3
import argparse
import ast
import sys
from pathlib import Path

from mypyc_micropython.compiler import compile_package, compile_to_micropython
from mypyc_micropython.ir_builder import IRBuilder
from mypyc_micropython.ir_visualizer import dump_ir


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mpy-compile", description="Compile typed Python to MicroPython native module"
    )
    parser.add_argument("source", help="Input Python file (.py) or package directory")
    parser.add_argument("-o", "--output", help="Output directory (default: usermod_<name>/)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--no-type-check",
        action="store_true",
        help="Disable strict mypy type checking (enabled by default)",
    )
    parser.add_argument(
        "--dump-ir",
        choices=["text", "tree", "json"],
        help="Dump IR instead of compiling (text, tree, or json format)",
    )
    parser.add_argument(
        "--ir-function", help="Dump IR for specific function only (use with --dump-ir)"
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: {source_path} not found", file=sys.stderr)
        return 1

    if args.dump_ir:
        return dump_ir_command(source_path, args.dump_ir, args.ir_function)

    output_dir = Path(args.output) if args.output else None

    type_check = not args.no_type_check
    if source_path.is_dir():
        result = compile_package(
            source_path, output_dir, type_check=type_check, strict_type_check=type_check
        )
    else:
        result = compile_to_micropython(
            source_path, output_dir, type_check=type_check, strict_type_check=type_check
        )

    if not result.success:
        print("Compilation failed:", file=sys.stderr)
        for error in result.errors:
            print(f"  {error}", file=sys.stderr)
        return 1

    actual_output = output_dir or source_path.parent / f"usermod_{result.module_name}"

    if args.verbose:
        print(f"Module: {result.module_name}")
        print(f"Output: {actual_output}/")
        print(f"  - {result.module_name}.c")
        print("  - micropython.mk")
        print("  - micropython.cmake")
    else:
        print(f"Created {actual_output}/")

    return 0


def dump_ir_command(source_path: Path, format: str, function_name: str | None) -> int:
    source = source_path.read_text()
    module_name = source_path.stem

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        return 1

    from mypyc_micropython.compiler import sanitize_name
    from mypyc_micropython.ir import ModuleIR

    classes: dict = {}
    builder = IRBuilder(module_name)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_ir = builder.build_class(node)
            classes[class_ir.name] = class_ir

    builder = IRBuilder(module_name, known_classes=classes)

    module_ir = ModuleIR(name=module_name, c_name=sanitize_name(module_name))

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            func_ir = builder.build_function(node)
            module_ir.functions[func_ir.name] = func_ir
            module_ir.function_order.append(func_ir.name)
        elif isinstance(node, ast.ClassDef):
            class_ir = classes[node.name]
            module_ir.classes[class_ir.name] = class_ir
            module_ir.class_order.append(class_ir.name)

    if function_name:
        if function_name in module_ir.functions:
            func_ir = module_ir.functions[function_name]
            print(dump_ir(func_ir, format))
        else:
            found = False
            for cls in module_ir.classes.values():
                if function_name in cls.methods:
                    print(dump_ir(cls.methods[function_name], format))
                    found = True
                    break
            if not found:
                print(f"Error: Function '{function_name}' not found", file=sys.stderr)
                return 1
    else:
        print(dump_ir(module_ir, format))

    return 0


if __name__ == "__main__":
    sys.exit(main())
