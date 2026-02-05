#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from mypyc_micropython.compiler import compile_to_micropython


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="mpy-compile",
        description="Compile typed Python to MicroPython native module"
    )
    parser.add_argument("source", help="Input Python file (.py)")
    parser.add_argument("-o", "--output", help="Output directory (default: usermod_<name>/)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: {source_path} not found", file=sys.stderr)
        return 1
    
    output_dir = Path(args.output) if args.output else None
    
    result = compile_to_micropython(source_path, output_dir)
    
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
        print(f"  - micropython.mk")
        print(f"  - micropython.cmake")
    else:
        print(f"Created {actual_output}/")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
