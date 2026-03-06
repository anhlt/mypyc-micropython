"""Core C binding infrastructure - library-agnostic components."""

from __future__ import annotations

from mypyc_micropython.c_bindings.core.c_emitter import CEmitter
from mypyc_micropython.c_bindings.core.c_ir import (
    CCallbackDef,
    CEnumDef,
    CFuncDef,
    CLibraryDef,
    CParamDef,
    CStructDef,
    CType,
    CTypeDef,
)
from mypyc_micropython.c_bindings.core.c_types import (
    c_bool,
    c_double,
    c_enum,
    c_float,
    c_int,
    c_int8,
    c_int16,
    c_int32,
    c_ptr,
    c_str,
    c_struct,
    c_uint,
    c_uint8,
    c_uint16,
    c_uint32,
    c_void,
)
from mypyc_micropython.c_bindings.core.cmake_emitter import CMakeEmitter
from mypyc_micropython.c_bindings.core.compiler import CBindingCompiler, CompilationResult
from mypyc_micropython.c_bindings.core.stub_parser import StubParser

__all__ = [
    # IR types
    "CType",
    "CTypeDef",
    "CStructDef",
    "CEnumDef",
    "CParamDef",
    "CFuncDef",
    "CCallbackDef",
    "CLibraryDef",
    # Emitters
    "CEmitter",
    "CMakeEmitter",
    # Compiler
    "CBindingCompiler",
    "CompilationResult",
    # Parser
    "StubParser",
    # C type markers
    "c_ptr",
    "c_void",
    "c_int",
    "c_uint",
    "c_int8",
    "c_uint8",
    "c_int16",
    "c_uint16",
    "c_int32",
    "c_uint32",
    "c_float",
    "c_double",
    "c_bool",
    "c_str",
    "c_struct",
    "c_enum",
]
