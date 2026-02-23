from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mypyc_micropython.c_bindings.compiler import CBindingCompiler


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mpy-compile-c",
        description="Generate MicroPython C bindings from .pyi stub files",
    )
    parser.add_argument("stub", type=Path, help="Path to .pyi stub file")
    parser.add_argument("-o", "--output", type=Path, help="Output directory")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if not args.stub.exists():
        print(f"Error: {args.stub} not found", file=sys.stderr)
        return 1

    if not args.stub.suffix == ".pyi":
        print(f"Warning: {args.stub} does not have .pyi extension", file=sys.stderr)

    compiler = CBindingCompiler()
    result = compiler.compile_stub(args.stub, args.output)

    if not result.success:
        for error in result.errors:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.output:
        print(f"Generated: {args.output}/{result.module_name}.c")
        print(f"Generated: {args.output}/micropython.cmake")
        if args.verbose:
            print(f"\nC code ({len(result.c_code)} bytes)")
            print(f"CMake ({len(result.cmake_code)} bytes)")
    else:
        print(result.c_code)

    return 0


if __name__ == "__main__":
    sys.exit(main())
