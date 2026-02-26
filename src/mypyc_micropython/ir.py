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


class ArgKind(Enum):
    """Argument kind for function parameters (following mypyc conventions)."""

    ARG_POS = 0  # Required positional: def f(a)
    ARG_OPT = 1  # Optional positional (has default): def f(a=1)
    ARG_STAR = 2  # Star args: def f(*args)
    ARG_STAR2 = 3  # Star kwargs: def f(**kwargs)
    ARG_NAMED = 4  # Keyword-only required: def f(*, a)
    ARG_NAMED_OPT = 5  # Keyword-only optional: def f(*, a=1)

    def is_optional(self) -> bool:
        """Return True if this argument kind has a default value."""
        return self in (ArgKind.ARG_OPT, ArgKind.ARG_NAMED_OPT)

    def is_star(self) -> bool:
        """Return True if this is *args or **kwargs."""
        return self in (ArgKind.ARG_STAR, ArgKind.ARG_STAR2)


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
    is_final: bool = False  # typing.Final -- constant, cannot be reassigned
    final_value: Any = None  # Resolved literal value for Final fields (for constant folding)

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
    is_private: bool = False  # __method (no trailing __) — class-internal only
    is_final: bool = False  # @final decorator — cannot be overridden
    docstring: str | None = None
    max_temp: int = 0

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
class PropertyInfo:
    name: str
    getter: MethodIR
    setter: MethodIR | None = None


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
    properties: dict[str, PropertyInfo] = field(default_factory=dict)

    # Special methods tracking
    has_init: bool = False
    has_repr: bool = False
    has_eq: bool = False
    has_ne: bool = False
    has_lt: bool = False
    has_le: bool = False
    has_gt: bool = False
    has_ge: bool = False
    has_str: bool = False
    has_hash: bool = False
    has_iter: bool = False
    has_next: bool = False
    # Virtual dispatch
    virtual_methods: list[str] = field(default_factory=list)
    vtable_size: int = 0

    # Dataclass support
    is_dataclass: bool = False
    dataclass_info: DataclassInfo | None = None

    # @final class -- cannot be subclassed, all methods devirtualized
    is_final_class: bool = False

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

    def get_all_properties(self) -> dict[str, PropertyInfo]:
        properties = {}
        if self.base:
            properties.update(self.base.get_all_properties())
        properties.update(self.properties)
        return properties

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
class DefaultArg:
    """Represents a default argument value."""

    value: Any  # Literal value (int, float, bool, str, None)
    c_expr: str | None = None  # Pre-computed C expression for the default


@dataclass
class ParamIR:
    """Represents a function parameter with kind and optional default."""

    name: str
    c_type: CType
    kind: ArgKind = ArgKind.ARG_POS
    default: DefaultArg | None = None


@dataclass
class FuncIR:
    """Function IR (standalone or method context)."""

    name: str
    c_name: str
    params: list[tuple[str, CType]]
    return_type: CType
    body_ast: ast.FunctionDef | None = None
    body: list[StmtIR] = field(default_factory=list)
    is_method: bool = False
    class_ir: ClassIR | None = None
    locals_: dict[str, CType] = field(default_factory=dict)
    docstring: str | None = None
    arg_types: list[str] = field(default_factory=list)
    uses_print: bool = False
    uses_list_opt: bool = False
    uses_builtins: bool = False  # min, max, sum builtins require py/builtin.h
    uses_checked_div: bool = False  # floor divide/modulo inside try blocks
    uses_imports: bool = False  # runtime module imports (mp_import_name)
    used_rtuples: set[RTuple] = field(default_factory=set)
    rtuple_types: dict[str, RTuple] = field(default_factory=dict)
    list_vars: dict[str, str | None] = field(default_factory=dict)
    max_temp: int = 0  # Highest temp counter used by IR builder
    # Default arguments: maps param index to DefaultArg
    defaults: dict[int, DefaultArg] = field(default_factory=dict)
    star_args: ParamIR | None = None
    star_kwargs: ParamIR | None = None

    @property
    def num_required_args(self) -> int:
        """Number of required (non-default) arguments."""
        return len(self.params) - len(self.defaults)

    @property
    def has_defaults(self) -> bool:
        """True if function has any default arguments."""
        return len(self.defaults) > 0

    @property
    def has_star_args(self) -> bool:
        """True if function has *args."""
        return self.star_args is not None

    @property
    def has_star_kwargs(self) -> bool:
        """True if function has **kwargs."""
        return self.star_kwargs is not None

    @property
    def is_variadic(self) -> bool:
        """True if function has *args or **kwargs."""
        return self.has_star_args or self.has_star_kwargs


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


@dataclass
class AttrAccessIR(InstrIR):
    """Access an attribute on a class-typed object.

    Generated C: result = ((ClassName_obj_t *)MP_OBJ_TO_PTR(obj))->attr
    """

    result: TempIR
    obj: ValueIR
    attr_name: str
    class_c_name: str
    result_type: IRType


@dataclass
class ListCompIR(InstrIR):
    """List comprehension: [expr for var in iterable] or [expr for var in iterable if cond].

    This IR node represents the entire comprehension. It gets emitted as:
    1. Create empty list
    2. Iterate over iterable
    3. Optionally check condition
    4. Evaluate element expression
    5. Append to list
    """

    result: TempIR
    loop_var: str  # Python variable name
    c_loop_var: str  # C variable name
    iterable: ValueIR
    element: ValueIR  # Expression for each element
    condition: ValueIR | None = None  # Optional filter condition
    # Preludes for iterable, element, and condition
    iter_prelude: list[InstrIR] = field(default_factory=list)
    element_prelude: list[InstrIR] = field(default_factory=list)
    condition_prelude: list[InstrIR] = field(default_factory=list)
    # Whether iterable is a range() call (for optimization)
    is_range: bool = False
    range_start: ValueIR | None = None
    range_end: ValueIR | None = None
    range_step: ValueIR | None = None


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


# ---------------------------------------------------------------------------
# Statement IR - Full statement-level intermediate representation
# ---------------------------------------------------------------------------


@dataclass
class StmtIR:
    """Base class for statement IR nodes."""

    pass


@dataclass
class ReturnIR(StmtIR):
    """Return statement: return [value]."""

    value: ValueIR | None = None
    # Prelude instructions that must execute before the return
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class IfIR(StmtIR):
    """If statement: if test: body else: orelse."""

    test: ValueIR
    body: list[StmtIR]
    orelse: list[StmtIR] = field(default_factory=list)
    # Prelude for test expression
    test_prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class WhileIR(StmtIR):
    """While statement: while test: body."""

    test: ValueIR
    body: list[StmtIR]
    # Prelude for test expression (evaluated each iteration)
    test_prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class ForRangeIR(StmtIR):
    """Optimized for loop over range(): for var in range(start, end, step)."""

    loop_var: str
    c_loop_var: str
    start: ValueIR
    end: ValueIR
    step: ValueIR | None  # None means step=1
    step_is_constant: bool
    step_value: int | None  # If step is constant, its value
    body: list[StmtIR]
    # Whether loop_var is newly declared
    is_new_var: bool = True


@dataclass
class ForIterIR(StmtIR):
    """Generic for loop over iterable: for var in iterable."""

    loop_var: str
    c_loop_var: str
    iterable: ValueIR
    body: list[StmtIR]
    # Prelude for iterable expression
    iter_prelude: list[InstrIR] = field(default_factory=list)
    # Whether loop_var is newly declared
    is_new_var: bool = True


@dataclass
class AssignIR(StmtIR):
    """Assignment statement: target = value."""

    target: str  # Variable name
    c_target: str  # C variable name
    value: ValueIR
    value_type: IRType
    # Prelude instructions
    prelude: list[InstrIR] = field(default_factory=list)
    # Whether this is a new variable declaration
    is_new_var: bool = False
    # Declared C type (for new vars)
    c_type: str = "mp_obj_t"


@dataclass
class AnnAssignIR(StmtIR):
    """Annotated assignment: target: annotation = value."""

    target: str
    c_target: str
    c_type: str
    value: ValueIR | None
    # Prelude instructions
    prelude: list[InstrIR] = field(default_factory=list)
    # Whether this is a new variable declaration
    is_new_var: bool = True


@dataclass
class AugAssignIR(StmtIR):
    """Augmented assignment: target op= value."""

    target: str
    c_target: str
    op: str  # C operator: +=, -=, *=, etc.
    value: ValueIR
    target_c_type: str = "mp_int_t"
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class SubscriptAssignIR(StmtIR):
    """Subscript assignment: container[key] = value."""

    container: ValueIR
    key: ValueIR
    value: ValueIR
    # Prelude instructions
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class AttrAssignIR(StmtIR):
    """Attribute assignment: self.attr = value (for methods)."""

    attr_name: str
    attr_path: str  # C path like "super.x" or "x"
    value: ValueIR
    # Prelude instructions
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class TupleUnpackIR(StmtIR):
    """Tuple unpacking: x, y = tuple_value."""

    targets: list[tuple[str, str, bool, str]]  # (py_name, c_name, is_new, c_type)
    value: ValueIR
    # Prelude instructions
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class ExprStmtIR(StmtIR):
    """Expression statement: expr (for side effects)."""

    expr: ValueIR
    # Prelude instructions
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class PrintIR(StmtIR):
    """Print statement: print(args...)."""

    args: list[ValueIR]
    # Prelude instructions for each arg
    preludes: list[list[InstrIR]] = field(default_factory=list)


@dataclass
class BreakIR(StmtIR):
    """Break statement."""

    pass


@dataclass
class ContinueIR(StmtIR):
    """Continue statement."""

    pass


@dataclass
class PassIR(StmtIR):
    """Pass statement (no-op)."""

    pass


# ---------------------------------------------------------------------------
# Expression IR - Full expression-level intermediate representation
# ---------------------------------------------------------------------------


@dataclass
class ExprIR(ValueIR):
    """Base class for complex expression IR nodes.

    Simple values (TempIR, ConstIR, NameIR) are also ValueIR but not ExprIR.
    ExprIR represents compound expressions that need evaluation.
    """

    pass


@dataclass
class BinOpIR(ExprIR):
    """Binary operation: left op right."""

    left: ValueIR
    op: str  # C operator: +, -, *, /, %, &, |, ^, <<, >>
    right: ValueIR
    # Prelude for left and right operands
    left_prelude: list[InstrIR] = field(default_factory=list)
    right_prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class UnaryOpIR(ExprIR):
    """Unary operation: op operand."""

    op: str  # C operator: -, !, +, ~
    operand: ValueIR
    # Prelude for operand
    prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class CompareIR(ExprIR):
    """Comparison: left op1 comp1 op2 comp2 ..."""

    left: ValueIR
    ops: list[str]  # C operators: ==, !=, <, <=, >, >=
    comparators: list[ValueIR]
    # Contains 'in' or 'not in' operations
    has_contains: bool = False
    # Preludes for left and each comparator
    left_prelude: list[InstrIR] = field(default_factory=list)
    comparator_preludes: list[list[InstrIR]] = field(default_factory=list)


@dataclass
class CallIR(ExprIR):
    """Function/method call: func(args)."""

    func_name: str
    c_func_name: str
    args: list[ValueIR]
    # Preludes for each arg
    arg_preludes: list[list[InstrIR]] = field(default_factory=list)
    # For builtin calls, the specific handling
    is_builtin: bool = False
    builtin_kind: str | None = None
    is_list_len_opt: bool = False
    is_typed_list_sum: bool = False
    sum_list_var: str | None = None
    sum_element_type: str | None = None


@dataclass
class SubscriptIR(ExprIR):
    """Subscript access: value[slice]."""

    value: ValueIR
    slice_: ValueIR
    # For RTuple optimization
    is_rtuple: bool = False
    rtuple_index: int | None = None
    # For list optimization
    is_list_opt: bool = False
    # Preludes
    value_prelude: list[InstrIR] = field(default_factory=list)
    slice_prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class SliceIR(ExprIR):
    """Slice object: [lower:upper:step]."""

    lower: ValueIR | None
    upper: ValueIR | None
    step: ValueIR | None


@dataclass
class IfExprIR(ExprIR):
    """Conditional expression: body if test else orelse."""

    test: ValueIR
    body: ValueIR
    orelse: ValueIR
    # Preludes
    test_prelude: list[InstrIR] = field(default_factory=list)
    body_prelude: list[InstrIR] = field(default_factory=list)
    orelse_prelude: list[InstrIR] = field(default_factory=list)


@dataclass
class ClassInstantiationIR(ExprIR):
    """Class instantiation: ClassName(args)."""

    class_name: str
    c_class_name: str
    args: list[ValueIR]
    # Preludes for args
    arg_preludes: list[list[InstrIR]] = field(default_factory=list)


@dataclass
class SelfAttrIR(ExprIR):
    """Attribute access on self: self.attr (for methods)."""

    attr_name: str
    attr_path: str  # C path like "super.x" or "x"
    result_type: IRType


@dataclass
class ParamAttrIR(ExprIR):
    """Attribute access on a typed class parameter: param.attr (for functions).

    When a function takes a user-defined class as a parameter (e.g., p: Point),
    accessing p.x requires unboxing the mp_obj_t to the class struct pointer.

    Generated C code: ((ClassName_obj_t *)MP_OBJ_TO_PTR(param))->attr
    """

    param_name: str  # Python parameter name (e.g., "p1")
    c_param_name: str  # C parameter name (sanitized)
    attr_name: str  # Attribute name (e.g., "x")
    attr_path: str  # C access path (e.g., "x" or "super._id" for inherited fields)
    class_c_name: str  # C class name (e.g., "module_Point")
    result_type: IRType


@dataclass
class SelfMethodCallIR(ExprIR):
    """Method call on self: self.method(args) (for methods)."""

    method_name: str
    c_method_name: str
    args: list[ValueIR]
    return_type: IRType
    # Preludes for args
    arg_preludes: list[list[InstrIR]] = field(default_factory=list)


@dataclass
class SuperCallIR(ExprIR):
    """super().method(args) call -- compile-time resolved to parent class method.

    Resolves at compile time to a direct call to the parent class's method,
    bypassing vtable dispatch. The parent class is determined from class_ir.base
    during IR building.
    """

    method_name: str
    parent_c_name: str  # Parent class C name (e.g., 'module_Parent')
    parent_method_c_name: str  # Parent method C name (e.g., 'module_Parent___init__')
    args: list[ValueIR]
    return_type: IRType
    is_init: bool = False  # True if calling super().__init__()
    # Preludes for args
    arg_preludes: list[list[InstrIR]] = field(default_factory=list)

@dataclass
class ModuleImportIR(InstrIR):
    """Runtime module import: import X or import X as Y.

    Generated C:
        mp_obj_t _tmp = mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
    """

    module_name: str  # Python module name (e.g., 'math')
    result: TempIR  # Temp var holding the imported module object


@dataclass
class ModuleCallIR(ExprIR):
    """Call a function on an imported module: module.func(args).

    Generated C:
        mp_obj_t mod = mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        mp_obj_t fn = mp_load_attr(mod, MP_QSTR_sqrt);
        mp_obj_t result = mp_call_function_1(fn, arg);
    """

    module_name: str  # Python module name (e.g., 'math')
    func_name: str  # Function name (e.g., 'sqrt')
    args: list[ValueIR]
    arg_preludes: list[list[InstrIR]] = field(default_factory=list)


@dataclass
class ModuleAttrIR(ExprIR):
    """Access an attribute on an imported module: module.attr.

    Used for constants like math.pi, math.e.

    Generated C:
        mp_obj_t mod = mp_import_name(MP_QSTR_math, mp_const_none, MP_OBJ_NEW_SMALL_INT(0));
        mp_obj_t result = mp_load_attr(mod, MP_QSTR_pi);
    """

    module_name: str  # Python module name (e.g., 'math')
    attr_name: str  # Attribute name (e.g., 'pi')

@dataclass
class SelfAugAssignIR(StmtIR):
    """Augmented assignment on self attribute: self.attr op= value."""

    attr_name: str
    attr_path: str
    op: str
    value: ValueIR
    prelude: list[InstrIR] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exception Handling IR
# ---------------------------------------------------------------------------


@dataclass
class ExceptHandlerIR:
    """Represents a single except handler: except ExceptionType as name:

    Example:
        except ValueError as e:
            handle_error(e)

    Generated C uses mp_obj_is_subclass_fast() for type matching.
    """

    exc_type: str | None  # Exception type name (None for bare 'except:')
    exc_var: str | None  # Variable name for 'as name' (None if not bound)
    c_exc_var: str | None  # Sanitized C variable name
    body: list[StmtIR] = field(default_factory=list)


@dataclass
class TryIR(StmtIR):
    """Try/except/else/finally statement.

    Example:
        try:
            risky_operation()
        except ValueError as e:
            handle_value_error(e)
        except TypeError:
            handle_type_error()
        else:
            no_exception_occurred()
        finally:
            cleanup()

    Generated C uses nlr_push/nlr_pop pattern:
        nlr_buf_t nlr;
        if (nlr_push(&nlr) == 0) {
            // try body
            nlr_pop();
            // else block
        } else {
            mp_obj_t exc = MP_OBJ_FROM_PTR(nlr.ret_val);
            if (mp_obj_is_subclass_fast(...)) { ... }
        }
        // finally block
    """

    body: list[StmtIR]
    handlers: list[ExceptHandlerIR] = field(default_factory=list)
    orelse: list[StmtIR] = field(default_factory=list)  # else block
    finalbody: list[StmtIR] = field(default_factory=list)  # finally block


@dataclass
class RaiseIR(StmtIR):
    """Raise statement: raise [exception].

    Example:
        raise ValueError("invalid input")
        raise  # re-raise current exception

    Generated C:
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("invalid input"));
        // or for bare raise:
        nlr_jump(nlr.ret_val);
    """

    exc_type: str | None = None  # Exception type (None for bare raise)
    exc_msg: ValueIR | None = None  # Message argument (if any)
    is_reraise: bool = False  # True for bare 'raise' (re-raise current)
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

    # Imported modules used by compiled functions (for runtime import)
    imported_modules: set[str] = field(default_factory=set)

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
