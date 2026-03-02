#!/usr/bin/env python3
"""Compile a Python file that uses external C library calls (e.g., LVGL).

This script parses the .pyi stub to build a CLibraryDef, then compiles
the Python source with external_libs so that `import lvgl as lv` calls
resolve to direct C wrapper function calls at compile time.

Usage:
    python3 scripts/compile_lvgl_app.py examples/lvgl_app.py -o modules/usermod_lvgl_app

The generated C module calls wrapper functions (e.g., lv_label_create_wrapper)
defined in the LVGL bindings module (modules/usermod_lvgl/lvgl.c).
Both modules must be linked together in the firmware build.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from mypyc_micropython.c_bindings.stub_parser import StubParser
from mypyc_micropython.compiler import (
    compile_source,
    generate_micropython_cmake,
    generate_micropython_mk,
)


LVGL_STUB = (
    project_root / "src" / "mypyc_micropython" / "c_bindings" / "stubs" / "lvgl" / "lvgl.pyi"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile Python source with external C library calls",
    )
    parser.add_argument("source", type=Path, help="Python source file")
    parser.add_argument("-o", "--output", type=Path, help="Output directory")
    parser.add_argument(
        "--stub",
        type=Path,
        default=LVGL_STUB,
        help="Path to .pyi stub file (default: lvgl.pyi)",
    )
    parser.add_argument(
        "--lib-name",
        default="lvgl",
        help="Library name as used in import (default: lvgl)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if not args.source.exists():
        print(f"Error: source file not found: {args.source}", file=sys.stderr)
        return 1

    if not args.stub.exists():
        print(f"Error: stub file not found: {args.stub}", file=sys.stderr)
        return 1

    stub_parser = StubParser()
    lib_def = stub_parser.parse_file(args.stub)

    if args.verbose:
        print(f"Parsed stub: {lib_def.name}")
        print(f"  Functions: {len(lib_def.functions)}")
        print(f"  Enums: {len(lib_def.enums)}")
        print(f"  Structs: {len(lib_def.structs)}")

    source_code = args.source.read_text()
    module_name = args.source.stem
    external_libs = {args.lib_name: lib_def}

    try:
        c_code = compile_source(
            source_code,
            module_name,
            type_check=False,
            external_libs=external_libs,
        )
    except Exception as e:
        print(f"Compilation error: {e}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"\nGenerated C code: {len(c_code)} bytes")

    if args.output:
        output_dir = args.output
        output_dir.mkdir(parents=True, exist_ok=True)

        (output_dir / f"{module_name}.c").write_text(c_code)
        (output_dir / "micropython.mk").write_text(generate_micropython_mk(module_name))
        (output_dir / "micropython.cmake").write_text(generate_micropython_cmake(module_name))

        print(f"Generated: {output_dir}/{module_name}.c")
        print(f"Generated: {output_dir}/micropython.mk")
        print(f"Generated: {output_dir}/micropython.cmake")
    else:
        print(c_code)

    return 0


if __name__ == "__main__":
    sys.exit(main())
