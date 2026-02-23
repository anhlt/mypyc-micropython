"""C-specific IR definitions for library bindings."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class CType(Enum):
    """C type categories."""

    VOID = auto()
    INT = auto()
    UINT = auto()
    INT8 = auto()
    UINT8 = auto()
    INT16 = auto()
    UINT16 = auto()
    INT32 = auto()
    UINT32 = auto()
    FLOAT = auto()
    DOUBLE = auto()
    BOOL = auto()
    STR = auto()
    PTR = auto()
    STRUCT_PTR = auto()
    CALLBACK = auto()

    def to_c_decl(self) -> str:
        mapping = {
            CType.VOID: "void",
            CType.INT: "mp_int_t",
            CType.UINT: "mp_uint_t",
            CType.INT8: "int8_t",
            CType.UINT8: "uint8_t",
            CType.INT16: "int16_t",
            CType.UINT16: "uint16_t",
            CType.INT32: "int32_t",
            CType.UINT32: "uint32_t",
            CType.FLOAT: "float",
            CType.DOUBLE: "mp_float_t",
            CType.BOOL: "bool",
            CType.STR: "const char *",
            CType.PTR: "void *",
        }
        return mapping.get(self, "void")

    def to_mp_unbox(self, arg_expr: str) -> str:
        """Generate code to convert mp_obj_t -> C value."""
        mapping = {
            CType.INT: f"mp_obj_get_int({arg_expr})",
            CType.UINT: f"(uint32_t)mp_obj_get_int({arg_expr})",
            CType.INT8: f"(int8_t)mp_obj_get_int({arg_expr})",
            CType.UINT8: f"(uint8_t)mp_obj_get_int({arg_expr})",
            CType.INT16: f"(int16_t)mp_obj_get_int({arg_expr})",
            CType.UINT16: f"(uint16_t)mp_obj_get_int({arg_expr})",
            CType.INT32: f"(int32_t)mp_obj_get_int({arg_expr})",
            CType.UINT32: f"(uint32_t)mp_obj_get_int({arg_expr})",
            CType.FLOAT: f"(float)mp_obj_get_float({arg_expr})",
            CType.DOUBLE: f"mp_obj_get_float({arg_expr})",
            CType.BOOL: f"mp_obj_is_true({arg_expr})",
            CType.STR: f"mp_obj_str_get_str({arg_expr})",
            CType.PTR: f"mp_to_ptr({arg_expr})",
            CType.STRUCT_PTR: f"mp_to_ptr({arg_expr})",
        }
        return mapping.get(self, f"mp_to_ptr({arg_expr})")

    def to_mp_box(self, val_expr: str) -> str:
        """Generate code to convert C value -> mp_obj_t."""
        mapping = {
            CType.VOID: "mp_const_none",
            CType.INT: f"mp_obj_new_int({val_expr})",
            CType.UINT: f"mp_obj_new_int_from_uint({val_expr})",
            CType.INT8: f"mp_obj_new_int({val_expr})",
            CType.UINT8: f"mp_obj_new_int({val_expr})",
            CType.INT16: f"mp_obj_new_int({val_expr})",
            CType.UINT16: f"mp_obj_new_int({val_expr})",
            CType.INT32: f"mp_obj_new_int({val_expr})",
            CType.UINT32: f"mp_obj_new_int_from_uint({val_expr})",
            CType.FLOAT: f"mp_obj_new_float({val_expr})",
            CType.DOUBLE: f"mp_obj_new_float({val_expr})",
            CType.BOOL: f"mp_obj_new_bool({val_expr})",
            CType.STR: f"mp_obj_new_str({val_expr}, strlen({val_expr}))",
            CType.PTR: f"ptr_to_mp({val_expr})",
            CType.STRUCT_PTR: f"ptr_to_mp((void *){val_expr})",
        }
        return mapping.get(self, f"ptr_to_mp({val_expr})")


@dataclass
class CTypeDef:
    """Type definition with optional struct reference."""
    base_type: CType
    struct_name: str | None = None
    callback_name: str | None = None
    is_optional: bool = False

@dataclass
class CStructDef:
    py_name: str
    c_name: str
    is_opaque: bool = True
    fields: dict[str, CTypeDef] = field(default_factory=dict)
    docstring: str | None = None


@dataclass
class CEnumDef:
    py_name: str
    c_name: str
    values: dict[str, int] = field(default_factory=dict)
    docstring: str | None = None


@dataclass
class CParamDef:
    name: str
    type_def: CTypeDef


@dataclass
class CFuncDef:
    py_name: str
    c_name: str
    params: list[CParamDef] = field(default_factory=list)
    return_type: CTypeDef = field(default_factory=lambda: CTypeDef(CType.VOID))
    docstring: str | None = None
    has_var_args: bool = False


@dataclass
class CCallbackDef:
    py_name: str
    params: list[CParamDef] = field(default_factory=list)
    return_type: CTypeDef = field(default_factory=lambda: CTypeDef(CType.VOID))
    user_data_param: int | None = None

@dataclass
class CLibraryDef:
    """Complete C library definition parsed from a .pyi stub."""

    name: str
    header: str = ""
    include_dirs: list[str] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    defines: list[str] = field(default_factory=list)
    structs: dict[str, CStructDef] = field(default_factory=dict)
    enums: dict[str, CEnumDef] = field(default_factory=dict)
    functions: dict[str, CFuncDef] = field(default_factory=dict)
    callbacks: dict[str, CCallbackDef] = field(default_factory=dict)
    docstring: str | None = None
