"""
Intermediate Representation (IR) for mypyc-micropython.

This module defines IR data structures used between AST parsing and
C code generation.  The design follows mypyc's approach but is adapted
for MicroPython's simpler type system.

Two IR layers coexist:
  • Class IR  – ClassIR / FieldIR / MethodIR / ModuleIR  (struct-level)
  • Expr IR   – ValueIR / InstrIR hierarchy  (expression/statement-level,
                used for container operations: list, dict)
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class CType(Enum):
    """C types for MicroPython integration."""

    MP_OBJ_T = auto()  # mp_obj_t (boxed, GC-visible)
    MP_INT_T = auto()  # mp_int_t (unboxed integer)
    MP_FLOAT_T = auto()  # mp_float_t (unboxed float)
    BOOL = auto()  # bool
    VOID = auto()  # void (for None returns)

    def to_c_type_str(self) -> str:
        """Return the C type string."""
        mapping = {
            CType.MP_OBJ_T: "mp_obj_t",
            CType.MP_INT_T: "mp_int_t",
            CType.MP_FLOAT_T: "mp_float_t",
            CType.BOOL: "bool",
            CType.VOID: "void",
        }
        return mapping[self]

    def to_field_type_id(self) -> int:
        """Return the field type ID for attr slot dispatch."""
        mapping = {
            CType.MP_OBJ_T: 0,
            CType.MP_INT_T: 1,
            CType.MP_FLOAT_T: 2,
            CType.BOOL: 3,
        }
        return mapping.get(self, 0)

    @staticmethod
    def from_python_type(type_str: str) -> CType:
        """Convert Python type annotation string to CType."""
        mapping = {
            "int": CType.MP_INT_T,
            "float": CType.MP_FLOAT_T,
            "bool": CType.BOOL,
            "str": CType.MP_OBJ_T,
            "None": CType.VOID,
            "list": CType.MP_OBJ_T,
            "dict": CType.MP_OBJ_T,
            "tuple": CType.MP_OBJ_T,
            "object": CType.MP_OBJ_T,
        }
        base_type = type_str.split("[")[0].strip()
        return mapping.get(base_type, CType.MP_OBJ_T)


@dataclass
class RTuple:
    """Fixed-length unboxed tuple type (represented as a C struct).

    Similar to mypyc's RTuple - when we know the exact element types at compile
    time, we can use a C struct instead of a Python tuple object. This avoids
    heap allocation and boxing/unboxing overhead.

    Example: tuple[int, int] -> struct { mp_int_t f0; mp_int_t f1; }
    """

    element_types: tuple[CType, ...]

    def __hash__(self) -> int:
        return hash(self.element_types)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RTuple):
            return False
        return self.element_types == other.element_types

    @property
    def arity(self) -> int:
        return len(self.element_types)

    def get_c_struct_name(self) -> str:
        """Generate C struct type name, e.g., 'rtuple_int_int_t'."""
        type_names = []
        for ct in self.element_types:
            if ct == CType.MP_INT_T:
                type_names.append("int")
            elif ct == CType.MP_FLOAT_T:
                type_names.append("float")
            elif ct == CType.BOOL:
                type_names.append("bool")
            else:
                type_names.append("obj")
        return f"rtuple_{'_'.join(type_names)}_t"

    def get_c_struct_typedef(self) -> str:
        """Generate C struct typedef."""
        struct_name = self.get_c_struct_name()
        fields = []
        for i, ct in enumerate(self.element_types):
            fields.append(f"    {ct.to_c_type_str()} f{i};")
        return "typedef struct {\n" + "\n".join(fields) + f"\n}} {struct_name};"

    def is_all_primitive(self) -> bool:
        """Check if all elements are primitive (unboxed) types."""
        return all(
            ct in (CType.MP_INT_T, CType.MP_FLOAT_T, CType.BOOL) for ct in self.element_types
        )

    @staticmethod
    def from_annotation(annotation: ast.Subscript) -> RTuple | None:
        """Parse tuple[int, int] annotation to RTuple, or None if not fixed-length."""
        if not isinstance(annotation.value, ast.Name) or annotation.value.id != "tuple":
            return None

        slice_node = annotation.slice
        if isinstance(slice_node, ast.Tuple):
            element_types = []
            for elt in slice_node.elts:
                if isinstance(elt, ast.Ellipsis):
                    return None
                if isinstance(elt, ast.Name):
                    ct = CType.from_python_type(elt.id)
                    element_types.append(ct)
                else:
                    return None
            if element_types:
                return RTuple(tuple(element_types))
        elif isinstance(slice_node, ast.Name):
            ct = CType.from_python_type(slice_node.id)
            return RTuple((ct,))

        return None


class CallTarget(Enum):
    """How to dispatch a method call."""

    DIRECT = auto()  # Direct C function call (exact type known)
    VTABLE = auto()  # Via vtable slot (virtual call)
    MP_DYNAMIC = auto()  # MicroPython dynamic dispatch (fallback)


@dataclass
class FieldIR:
    """Represents a class field/attribute."""

    name: str
    py_type: str  # Python type annotation as string
    c_type: CType  # Resolved C type
    offset: int = -1  # Byte offset in struct (computed later)
    has_default: bool = False
    default_value: Any = None  # Literal default value
    default_factory: str | None = None  # For dataclass field(default_factory=...)
    default_ast: ast.expr | None = None  # AST node for default value

    def get_c_type_str(self) -> str:
        """Get the C type string for this field."""
        return self.c_type.to_c_type_str()


@dataclass
class MethodIR:
    """Represents a class method."""

    name: str
    c_name: str  # Full C function name
    params: list[tuple[str, CType]]  # (name, type) pairs (excluding self)
    return_type: CType
    body_ast: ast.FunctionDef  # Original AST for body translation
    is_virtual: bool = True  # Can be overridden?
    is_static: bool = False  # @staticmethod
    is_classmethod: bool = False  # @classmethod
    is_property: bool = False  # @property
    vtable_index: int = -1  # Index in vtable (if virtual)
    is_special: bool = False  # __init__, __repr__, etc.
    docstring: str | None = None

    def get_native_signature(self, class_c_name: str) -> str:
        """Get the native C function signature (typed parameters)."""
        if self.is_static:
            params_str = ", ".join(f"{ctype.to_c_type_str()} {name}" for name, ctype in self.params)
            if not params_str:
                params_str = "void"
        else:
            params_str = f"{class_c_name}_obj_t *self"
            if self.params:
                params_str += ", " + ", ".join(
                    f"{ctype.to_c_type_str()} {name}" for name, ctype in self.params
                )

        return f"static {self.return_type.to_c_type_str()} {self.c_name}_native({params_str})"

    def get_mp_wrapper_signature(self) -> str:
        """Get the MicroPython wrapper signature."""
        n_args = len(self.params) + (0 if self.is_static else 1)  # +1 for self
        if n_args == 0:
            return f"static mp_obj_t {self.c_name}_mp(void)"
        elif n_args == 1:
            return f"static mp_obj_t {self.c_name}_mp(mp_obj_t arg0)"
        elif n_args == 2:
            return f"static mp_obj_t {self.c_name}_mp(mp_obj_t arg0, mp_obj_t arg1)"
        elif n_args == 3:
            return f"static mp_obj_t {self.c_name}_mp(mp_obj_t arg0, mp_obj_t arg1, mp_obj_t arg2)"
        else:
            return f"static mp_obj_t {self.c_name}_mp(size_t n_args, const mp_obj_t *args)"


@dataclass
class DataclassInfo:
    """Metadata for @dataclass decorated classes."""

    fields: list[FieldIR] = field(default_factory=list)
    frozen: bool = False
    eq: bool = True
    order: bool = False
    repr_: bool = True
    init: bool = True

    # Flags for which methods to auto-generate
    generate_init: bool = True
    generate_repr: bool = True
    generate_eq: bool = True


@dataclass
class ClassIR:
    """Intermediate representation of a Python class."""

    name: str
    c_name: str  # Sanitized C identifier
    module_name: str

    # Inheritance (single inheritance only)
    base: ClassIR | None = None
    base_name: str | None = None  # For deferred resolution

    # Members
    fields: list[FieldIR] = field(default_factory=list)
    methods: dict[str, MethodIR] = field(default_factory=dict)

    # Special methods tracking
    has_init: bool = False
    has_repr: bool = False
    has_eq: bool = False
    has_hash: bool = False

    # Virtual dispatch
    virtual_methods: list[str] = field(default_factory=list)
    vtable_size: int = 0

    # Dataclass support
    is_dataclass: bool = False
    dataclass_info: DataclassInfo | None = None

    # MicroPython slots to emit
    mp_slots: set[str] = field(default_factory=lambda: {"make_new", "attr"})

    # Computed layout
    struct_size: int = 0

    # Original AST
    ast_node: ast.ClassDef | None = None

    def get_all_fields(self) -> list[FieldIR]:
        """Get fields including inherited ones (base first)."""
        if self.base:
            return self.base.get_all_fields() + self.fields
        return list(self.fields)

    def get_all_fields_with_path(self) -> list[tuple[FieldIR, str]]:
        """Get fields with their C access path (e.g., 'super.x' for inherited)."""
        result: list[tuple[FieldIR, str]] = []
        if self.base:
            for fld, path in self.base.get_all_fields_with_path():
                result.append((fld, f"super.{path}"))
        for fld in self.fields:
            result.append((fld, fld.name))
        return result

    def get_own_fields(self) -> list[FieldIR]:
        """Get only this class's fields (not inherited)."""
        return list(self.fields)

    def get_vtable_entries(self) -> list[tuple[str, MethodIR]]:
        """Get ordered vtable entries including inherited."""
        entries: list[tuple[str, MethodIR]] = []
        if self.base:
            entries = self.base.get_vtable_entries()

        # Add new virtual methods, override existing
        existing_names = {name for name, _ in entries}
        for name in self.virtual_methods:
            if name in self.methods:
                method = self.methods[name]
                # Check if overriding
                existing_idx = next((i for i, (n, _) in enumerate(entries) if n == name), None)
                if existing_idx is not None:
                    entries[existing_idx] = (name, method)
                elif name not in existing_names:
                    entries.append((name, method))

        return entries

    def get_all_methods(self) -> dict[str, MethodIR]:
        """Get all methods including inherited (child overrides parent)."""
        methods = {}
        if self.base:
            methods.update(self.base.get_all_methods())
        methods.update(self.methods)
        return methods

    def get_struct_name(self) -> str:
        """Get the C struct type name."""
        return f"{self.c_name}_obj_t"

    def get_type_name(self) -> str:
        """Get the MicroPython type object name."""
        return f"{self.c_name}_type"

    def get_vtable_type_name(self) -> str:
        """Get the vtable struct type name."""
        return f"{self.c_name}_vtable_t"

    def get_vtable_instance_name(self) -> str:
        """Get the vtable instance name."""
        return f"{self.c_name}_vtable"

    def compute_layout(self) -> None:
        """Compute field offsets and struct size."""
        # Start after the header (base + vtable pointer)
        offset = 0  # Relative to after base struct

        for fld in self.fields:
            # Simple alignment (could be improved)
            fld.offset = offset
            if fld.c_type == CType.MP_OBJ_T:
                offset += 8  # sizeof(mp_obj_t) on 64-bit
            elif fld.c_type == CType.MP_INT_T:
                offset += 8  # sizeof(mp_int_t)
            elif fld.c_type == CType.MP_FLOAT_T:
                offset += 8  # sizeof(mp_float_t)
            elif fld.c_type == CType.BOOL:
                offset += 1  # sizeof(bool)
                # Align to 8 bytes after bool
                offset = (offset + 7) & ~7

        self.struct_size = offset


@dataclass
class FuncIR:
    """Function IR (standalone or method context)."""

    name: str
    c_name: str
    params: list[tuple[str, CType]]  # (name, type) pairs
    return_type: CType
    body_ast: ast.FunctionDef  # Original AST for body translation
    is_method: bool = False
    class_ir: ClassIR | None = None  # Owning class (if method)
    locals_: dict[str, CType] = field(default_factory=dict)
    docstring: str | None = None


class IRType(Enum):
    """Runtime type tag for expression-level IR values."""

    OBJ = auto()  # mp_obj_t (boxed)
    INT = auto()  # mp_int_t (unboxed integer)
    FLOAT = auto()  # mp_float_t (unboxed float)
    BOOL = auto()  # bool

    def to_c_type_str(self) -> str:
        mapping = {
            IRType.OBJ: "mp_obj_t",
            IRType.INT: "mp_int_t",
            IRType.FLOAT: "mp_float_t",
            IRType.BOOL: "bool",
        }
        return mapping[self]

    @staticmethod
    def from_c_type_str(c_type: str) -> IRType:
        mapping = {
            "mp_obj_t": IRType.OBJ,
            "mp_int_t": IRType.INT,
            "mp_float_t": IRType.FLOAT,
            "bool": IRType.BOOL,
        }
        return mapping.get(c_type, IRType.OBJ)


# ---------------------------------------------------------------------------
# Expression-level IR values
# ---------------------------------------------------------------------------


@dataclass
class ValueIR:
    """Base for IR values (temps, constants, names)."""

    ir_type: IRType


@dataclass
class TempIR(ValueIR):
    """A compiler-generated temporary variable."""

    name: str


@dataclass
class ConstIR(ValueIR):
    """A compile-time constant value."""

    value: object  # int | float | bool | str | None


@dataclass
class NameIR(ValueIR):
    """A reference to a Python local / argument."""

    py_name: str
    c_name: str


# ---------------------------------------------------------------------------
# Expression-level IR instructions
# ---------------------------------------------------------------------------


@dataclass
class InstrIR:
    """Base for IR instructions (each may produce an optional result)."""

    pass


@dataclass
class ListNewIR(InstrIR):
    """Create a new list from *items*."""

    result: TempIR
    items: list[ValueIR]


@dataclass
class TupleNewIR(InstrIR):
    """Create a new tuple from *items*."""

    result: TempIR
    items: list[ValueIR]


@dataclass
class SetNewIR(InstrIR):
    """Create a new set from *items*."""

    result: TempIR
    items: list[ValueIR]


@dataclass
class DictNewIR(InstrIR):
    """Create a new dict from key/value pairs."""

    result: TempIR
    entries: list[tuple[ValueIR, ValueIR]]


@dataclass
class GetItemIR(InstrIR):
    """container[key]  →  result."""

    result: TempIR
    container: ValueIR
    key: ValueIR


@dataclass
class SetItemIR(InstrIR):
    """container[key] = value  (no result)."""

    container: ValueIR
    key: ValueIR
    value: ValueIR


@dataclass
class MethodCallIR(InstrIR):
    """receiver.method(args)  →  optional result."""

    result: TempIR | None
    receiver: ValueIR
    method: str
    args: list[ValueIR]


@dataclass
class BoxIR(InstrIR):
    """Box a native value to mp_obj_t."""

    result: TempIR
    value: ValueIR


@dataclass
class UnboxIR(InstrIR):
    """Unbox mp_obj_t to a native type."""

    result: TempIR
    value: ValueIR
    target_type: IRType


# ---------------------------------------------------------------------------
# Lowered expression: prelude instructions + final value
# ---------------------------------------------------------------------------


@dataclass
class LoweredExpr:
    """Result of lowering an AST expression to IR.

    ``prelude`` contains instructions that must be emitted *before* the
    statement that uses ``value``.
    """

    value: ValueIR
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class ModuleIR:
    name: str
    c_name: str
    classes: dict[str, ClassIR] = field(default_factory=dict)
    functions: dict[str, FuncIR] = field(default_factory=dict)

    # For tracking definition order (important for forward declarations)
    class_order: list[str] = field(default_factory=list)
    function_order: list[str] = field(default_factory=list)

    def add_class(self, class_ir: ClassIR) -> None:
        """Add a class to the module."""
        self.classes[class_ir.name] = class_ir
        if class_ir.name not in self.class_order:
            self.class_order.append(class_ir.name)

    def add_function(self, func_ir: FuncIR) -> None:
        """Add a function to the module."""
        self.functions[func_ir.name] = func_ir
        if func_ir.name not in self.function_order:
            self.function_order.append(func_ir.name)

    def resolve_base_classes(self) -> None:
        """Resolve base class references after all classes are parsed."""
        for class_ir in self.classes.values():
            if class_ir.base_name and class_ir.base is None:
                if class_ir.base_name in self.classes:
                    class_ir.base = self.classes[class_ir.base_name]

    def get_classes_in_order(self) -> list[ClassIR]:
        """Get classes in topological order (base classes first)."""
        visited: set[str] = set()
        result: list[ClassIR] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            class_ir = self.classes[name]
            if class_ir.base_name and class_ir.base_name in self.classes:
                visit(class_ir.base_name)
            result.append(class_ir)

        for name in self.class_order:
            visit(name)

        return result
