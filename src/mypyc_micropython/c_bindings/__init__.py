"""C library bindings via .pyi stub files.

Generate MicroPython C bindings from Python .pyi stub files.
"""

from __future__ import annotations

from mypyc_micropython.c_bindings.compiler import CBindingCompiler, CompilationResult

__all__ = ["CBindingCompiler", "CompilationResult"]
