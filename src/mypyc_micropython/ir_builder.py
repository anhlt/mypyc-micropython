"""
IR Builder: AST -> IR translation.

This module transforms Python AST nodes into IR data structures.
The IR is then consumed by emitters to generate C code.
"""

from __future__ import annotations

import ast
import re
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypyc_micropython.c_bindings.core.c_ir import CLibraryDef

    from .type_checker import ClassTypeInfo, FunctionTypeInfo

from .ir import (
    AnnAssignIR,
    ArgKind,
    AssignIR,
    AttrAccessIR,
    AttrAssignIR,
    AugAssignIR,
    AwaitIR,
    AwaitModuleCallIR,
    BinOpIR,
    BoxIR,
    BreakIR,
    CallIR,
    ClassInstantiationIR,
    ClassIR,
    CompareIR,
    ConstIR,
    ContinueIR,
    CType,
    DataclassInfo,
    DefaultArg,
    DictNewIR,
    DynamicCallIR,
    EnumIR,
    ExceptHandlerIR,
    ExprStmtIR,
    FieldIR,
    ForIterIR,
    ForRangeIR,
    FuncIR,
    FuncRefIR,
    IfExprIR,
    IfIR,
    IRType,
    IsInstanceIR,
    ListCompIR,
    ListNewIR,
    MethodCallIR,
    MethodIR,
    ModuleAttrIR,
    ModuleCallIR,
    ModuleRefIR,
    NameIR,
    ObjAttrAssignIR,
    ParamAttrIR,
    ParamIR,
    PassIR,
    PrintIR,
    PropertyInfo,
    RaiseIR,
    ReturnIR,
    RTuple,
    SelfAttrIR,
    SelfAugAssignIR,
    SelfMethodCallIR,
    SelfMethodRefIR,
    SetNewIR,
    SiblingClassInstantiationIR,
    SiblingModuleCallIR,
    SiblingModuleRefIR,
    SliceIR,
    StmtIR,
    SubscriptAssignIR,
    SubscriptIR,
    SuperCallIR,
    TempIR,
    TryIR,
    TupleNewIR,
    TupleUnpackIR,
    UnaryOpIR,
    ValueIR,
    WhileIR,
    YieldFromIR,
    YieldIR,
)

C_RESERVED_WORDS = {
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "int",
    "long",
    "register",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "inline",
    "restrict",
    "_Bool",
    "_Complex",
    "_Imaginary",
}


# Builtin functions recognized by the compiler
BUILTIN_FUNCTIONS = {
    "abs",
    "int",
    "float",
    "bool",
    "str",
    "len",
    "range",
    "list",
    "tuple",
    "set",
    "dict",
    "min",
    "max",
    "sum",
    "enumerate",
    "zip",
    "sorted",
    "id",
}

# Builtins that return int
INT_BUILTINS = {"abs", "int", "len", "sum", "id"}


def _builtin_ir_type(func_name: str) -> IRType:
    """Return the IR type for a builtin function."""
    if func_name in INT_BUILTINS:
        return IRType.INT
    elif func_name == "float":
        return IRType.FLOAT
    elif func_name == "bool":
        return IRType.BOOL
    return IRType.OBJ


def sanitize_name(name: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if result and result[0].isdigit():
        result = "_" + result
    if result in C_RESERVED_WORDS:
        result = result + "_"
    return result


@dataclass
class BuildContext:
    """Context for building IR from AST nodes.

    Encapsulates the differences between function context and method context,
    allowing unified code paths for both.
    """

    locals_: list[str]
    class_ir: ClassIR | None = None
    native: bool = False

    @property
    def is_method(self) -> bool:
        return self.class_ir is not None


@dataclass
class MypyTypeInfo:
    """Container for mypy type information passed to IRBuilder."""

    functions: dict[str, "FunctionTypeInfo"] = field(default_factory=dict)
    classes: dict[str, "ClassTypeInfo"] = field(default_factory=dict)
    module_types: dict[str, str] = field(default_factory=dict)


class IRBuilder:
    """Builds IR from Python AST nodes.

    Optionally uses mypy's type information when available for more accurate
    type resolution, including type inference and generic resolution.
    """

    def __init__(
        self,
        module_name: str,
        known_classes: dict[str, ClassIR] | None = None,
        known_enums: dict[str, EnumIR] | None = None,
        mypy_types: "MypyTypeInfo | None" = None,
        external_libs: dict[str, CLibraryDef] | None = None,
        sibling_modules: dict[str, str] | None = None,  # maps old name -> package prefix
        sibling_constants: dict[str, dict[str, int | float | str | bool | None]] | None = None,
        func_class_returns: dict[str, str] | None = None,  # func_name -> class return type
    ):
        self.module_name = module_name
        self.c_name = sanitize_name(module_name)
        self._known_classes = known_classes or {}
        self._mypy_types = mypy_types
        self._func_class_returns: dict[str, str] = dict(func_class_returns or {})
        self._temp_counter = 0
        self._var_types: dict[str, str] = {}
        self._star_c_names: dict[str, str] = {}
        self._list_vars: dict[str, str | None] = {}
        self._rtuple_types: dict[str, RTuple] = {}
        self._used_rtuples: set[RTuple] = set()
        self._uses_print = False
        self._uses_list_opt = False
        self._uses_imports = False
        self._loop_depth = 0
        self._yield_state_counter = 0
        self._class_typed_params: dict[str, str] = {}
        self._container_element_types: dict[str, str] = {}
        self._optional_class_params: set[str] = set()  # params typed as X | None
        self._class_field_element_types: dict[tuple[str, str], str] = {}
        self._typevar_bounds: dict[str, str] = {}  # TypeVar name -> bound type ("object" if unbounded)
        self._pep695_typevars: set[str] = set()  # PEP 695 function-level TypeVar names (cleared per function)
        for class_ir in self._known_classes.values():
            class_node = class_ir.ast_node
            if class_node is None:
                continue
            for stmt in class_node.body:
                if not isinstance(stmt, ast.AnnAssign) or not isinstance(stmt.target, ast.Name):
                    continue
                inner_annotation: ast.expr | None = stmt.annotation
                if isinstance(stmt.annotation, ast.Subscript):
                    if (
                        isinstance(stmt.annotation.value, ast.Name)
                        and stmt.annotation.value.id == "Final"
                    ):
                        inner_annotation = stmt.annotation.slice
                elif isinstance(stmt.annotation, ast.Name) and stmt.annotation.id == "Final":
                    inner_annotation = None
                elem_class = self._extract_container_element_class(inner_annotation)
                if elem_class:
                    self._class_field_element_types[(class_ir.name, stmt.target.id)] = elem_class
        self._mypy_local_types: dict[str, str] = {}
        self._param_py_types: dict[str, str] = {}  # Python type annotations for params
        self._external_libs: dict[str, CLibraryDef] = external_libs or {}
        self._import_aliases: dict[str, str] = {}
        self._imported_modules: set[str] = set()
        self._imported_from: dict[str, str] = {}  # maps imported name -> source module
        self._uses_external_libs: set[str] = set()
        self._module_constants: dict[str, int | float | str | bool | None] = {}
        self._module_vars: dict[str, str] = {}
        self._sibling_modules: dict[str, str] = (
            sibling_modules or {}
        )  # maps import name -> C prefix
        self._sibling_constants: dict[str, dict[str, int | float | str | bool | None]] = (
            sibling_constants or {}
        )  # maps module_name -> {const_name: value}
        self._known_enums: dict[str, EnumIR] = dict(known_enums or {})
        self._known_functions: dict[str, tuple[str, CType]] = {}  # py_name -> (c_name, return_type)
        self._ctx: BuildContext = BuildContext(locals_=[])

    def _fresh_temp(self) -> str:
        self._temp_counter += 1
        return f"_tmp{self._temp_counter}"

    def _warn_type_tracking_fallback(
        self,
        context: str,
        var_name: str,
        attr_name: str | None = None,
        hint: str | None = None,
    ) -> None:
        """Emit a warning when type tracking falls back to dynamic access.

        Args:
            context: Where the fallback occurred (e.g., 'attribute access', 'method call')
            var_name: The variable name that couldn't be resolved
            attr_name: The attribute being accessed (if applicable)
            hint: Additional hint for fixing the issue
        """
        if attr_name:
            msg = f"Type tracking fallback in {context}: '{var_name}.{attr_name}'"
        else:
            msg = f"Type tracking fallback in {context}: '{var_name}'"

        if hint:
            msg += f". {hint}"

        warnings.warn(msg, stacklevel=3)

    def register_import(self, node: ast.Import | ast.ImportFrom) -> None:
        """Register import statements for later resolution of module.func() calls."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                local_name = alias.asname or alias.name
                self._import_aliases[local_name] = module_name
                self._imported_modules.add(module_name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # from X import Y -- track the module and each imported name
            self._import_aliases[node.module] = node.module
            self._imported_modules.add(node.module)
            # Track each imported name -> source module
            for alias in node.names:
                local_name = alias.asname or alias.name
                self._imported_from[local_name] = node.module

    def register_constant(self, node: ast.Assign) -> bool:
        """Register module-level constant assignment (NAME = literal_value).

        Returns True if successfully registered, False otherwise.
        Only handles simple NAME = literal assignments.
        """
        if len(node.targets) != 1:
            return False
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return False
        name = target.id

        # Extract literal value
        value = node.value
        if isinstance(value, ast.Constant):
            self._module_constants[name] = value.value
            return True
        elif isinstance(value, ast.UnaryOp) and isinstance(value.op, ast.USub):
            # Handle negative numbers: -1, -3.14
            if isinstance(value.operand, ast.Constant) and isinstance(
                value.operand.value, (int, float)
            ):
                self._module_constants[name] = -value.operand.value
                return True
        return False

    def register_module_var(self, node: ast.AnnAssign) -> bool:
        if not isinstance(node.target, ast.Name) or node.value is None:
            return False

        # First: check if this is a literal constant (NAME: type = literal_value)
        # Register as module constant so functions can resolve the value at compile time
        if isinstance(node.value, ast.Constant):
            self._module_constants[node.target.id] = node.value.value
            return True
        if isinstance(node.value, ast.UnaryOp) and isinstance(node.value.op, ast.USub):
            if isinstance(node.value.operand, ast.Constant) and isinstance(
                node.value.operand.value, (int, float)
            ):
                self._module_constants[node.target.id] = -node.value.operand.value
                return True

        ann = node.annotation
        if (
            isinstance(ann, ast.Subscript)
            and isinstance(ann.value, ast.Name)
            and ann.value.id == "Final"
        ):
            ann = ann.slice

        kind: str | None = None
        if isinstance(ann, ast.Subscript) and isinstance(ann.value, ast.Name):
            if ann.value.id in {"dict", "Dict"}:
                kind = "dict"
            elif ann.value.id in {"list", "List"}:
                kind = "list"
        elif isinstance(ann, ast.Name):
            if ann.id in {"dict", "Dict"}:
                kind = "dict"
            elif ann.id in {"list", "List"}:
                kind = "list"

        if kind == "dict" and isinstance(node.value, ast.Dict):
            self._module_vars[node.target.id] = "dict"
            return True
        if kind == "list" and isinstance(node.value, ast.List):
            self._module_vars[node.target.id] = "list"
            return True
        return False

    def register_function_name(
        self, name: str, c_name: str, return_type: CType = CType.MP_INT_T
    ) -> None:
        """Register a module-level function name so it can be referenced as a value.

        Called by the compiler after each function definition so that later
        functions in the same module can use the function as a first-class value
        (e.g., ``sorted(items, key=my_func)``).

        Args:
            name: Python function name
            c_name: C function name
            return_type: The function's return type (default: MP_INT_T for backwards compat)
        """
        self._known_functions[name] = (c_name, return_type)

    @property
    def module_constants(self) -> dict[str, int | float | str | bool | None]:
        """Dict of module-level constants (name -> value)."""
        return self._module_constants

    @property
    def module_vars(self) -> dict[str, str]:
        return self._module_vars

    @property
    def imported_modules(self) -> set[str]:
        """Set of module names that have been imported."""
        return self._imported_modules

    def build_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FuncIR:
        self._temp_counter = 0
        self._var_types = {}
        self._star_c_names: dict[str, str] = {}
        self._list_vars: dict[str, str | None] = {}
        self._rtuple_types = {}
        self._used_rtuples = set()
        self._uses_print = False
        self._uses_list_opt = False
        self._uses_imports = False
        self._yield_state_counter = 0
        self._class_typed_params = {}
        self._optional_class_params = set()
        self._container_element_types = {}
        self._param_py_types: dict[str, str] = {}  # Python type annotations for params
        self._mypy_local_types = {}

        # Clear PEP 695 function-level TypeVars from previous build
        for tv_name in self._pep695_typevars:
            self._typevar_bounds.pop(tv_name, None)
        self._pep695_typevars = set()


        # Scan for PEP 695 type parameters: def f[T](x: T) -> T
        self._scan_typevars(node)

        # Check if this is an async function
        is_async = isinstance(node, ast.AsyncFunctionDef)

        is_generator = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))
        if is_generator:
            unsupported_node = next(
                (n for n in ast.walk(node) if isinstance(n, (ast.Try, ast.With, ast.AsyncWith))),
                None,
            )
            if unsupported_node is not None:
                raise NotImplementedError(
                    f"try/with in generator functions is not supported (line {unsupported_node.lineno})"
                )

            return_with_value = next(
                (n for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None),
                None,
            )
            if return_with_value is not None:
                raise NotImplementedError(
                    f"return value in generator is not supported (line {return_with_value.lineno})"
                )

            for for_node in (n for n in ast.walk(node) if isinstance(n, ast.For)):
                first_yield = next(
                    (x for x in ast.walk(for_node) if isinstance(x, (ast.Yield, ast.YieldFrom))),
                    None,
                )
                if first_yield is None:
                    continue

                # Check if it's a range() call
                is_range_call = (
                    isinstance(for_node.iter, ast.Call)
                    and isinstance(for_node.iter.func, ast.Name)
                    and for_node.iter.func.id == "range"
                )

                if is_range_call:
                    # Validate supported range(...) shapes for generators
                    if not self._is_supported_generator_range_call(for_node.iter):
                        raise NotImplementedError(
                            f"unsupported generator range(...) loop is not supported (line {for_node.lineno})"
                        )
                # else: it's a for-iter loop over iterable, which is now allowed

        func_name = node.name
        c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"

        mypy_func = self._get_mypy_func_type(func_name)
        mypy_param_types: dict[str, str] = {}
        mypy_return_type: str | None = None
        if mypy_func:
            mypy_param_types = {name: ptype for name, ptype in mypy_func.params}
            mypy_return_type = mypy_func.return_type
            self._mypy_local_types = dict(mypy_func.local_types)

        params: list[tuple[str, CType]] = []
        arg_types: list[str] = []
        for arg in node.args.args:
            if arg.arg in mypy_param_types:
                py_type = self._mypy_type_to_py_type(mypy_param_types[arg.arg])
                c_type_str = self._mypy_type_to_c_type(mypy_param_types[arg.arg])
                c_type = CType.from_python_type(py_type)
            else:
                c_type_str = (
                    self._annotation_to_c_type(arg.annotation) if arg.annotation else "mp_obj_t"
                )
                c_type = (
                    CType.from_python_type(self._annotation_to_py_type(arg.annotation))
                    if arg.annotation
                    else CType.MP_OBJ_T
                )
            params.append((arg.arg, c_type))
            arg_types.append(c_type_str)
            self._var_types[arg.arg] = c_type_str
            if arg.annotation:
                is_list, elem_type = self._is_list_annotation(arg.annotation)
                if is_list:
                    self._list_vars[arg.arg] = elem_type
                class_name = self._extract_class_from_annotation(arg.annotation)
                if class_name:
                    self._class_typed_params[arg.arg] = class_name
                    if self._is_optional_class_annotation(arg.annotation):
                        self._optional_class_params.add(arg.arg)
                else:
                    elem_class = self._extract_container_element_class(arg.annotation)
                    if elem_class:
                        self._container_element_types[arg.arg] = elem_class
                # Track Python type annotation for receiver_py_type in MethodCallIR
                py_type = self._annotation_to_py_type(arg.annotation)
                if py_type:
                    self._param_py_types[arg.arg] = py_type

        defaults = self._parse_defaults(node.args, len(params))

        star_args, star_kwargs = self._parse_star_args(node.args)

        if mypy_return_type:
            py_type = self._mypy_type_to_py_type(mypy_return_type)
            return_type = CType.from_python_type(py_type)
        else:
            return_type = (
                CType.from_python_type(self._annotation_to_py_type(node.returns))
                if node.returns
                else CType.MP_OBJ_T
            )

        local_vars = [arg.arg for arg in node.args.args]
        if star_args:
            local_vars.append(star_args.name)
            self._var_types[star_args.name] = "mp_obj_t"
            self._star_c_names[star_args.name] = f"_star_{sanitize_name(star_args.name)}"
        if star_kwargs:
            local_vars.append(star_kwargs.name)
            self._var_types[star_kwargs.name] = "mp_obj_t"
            self._star_c_names[star_kwargs.name] = f"_star_{sanitize_name(star_kwargs.name)}"

        self._ctx = BuildContext(locals_=local_vars)
        body_ir: list[StmtIR] = []
        for stmt in node.body:
            stmt_ir = self._build_statement(stmt, local_vars)
            if stmt_ir is not None:
                body_ir.append(stmt_ir)

        return FuncIR(
            name=func_name,
            c_name=c_func_name,
            params=params,
            return_type=return_type,
            body_ast=node,
            body=body_ir,
            is_generator=is_generator,
            is_async=is_async,
            is_method=False,
            class_ir=None,
            locals_={
                name: CType.from_c_type_str(self._var_types.get(name, "mp_obj_t"))
                for name in local_vars
            },
            docstring=ast.get_docstring(node),
            arg_types=arg_types,
            uses_print=self._uses_print,
            uses_list_opt=self._uses_list_opt,
            uses_imports=self._uses_imports,
            used_rtuples=set(self._used_rtuples),
            rtuple_types=dict(self._rtuple_types),
            list_vars=dict(self._list_vars),
            max_temp=self._temp_counter,
            defaults=defaults,
            star_args=star_args,
            star_kwargs=star_kwargs,
        )

    def _build_statement(self, stmt: ast.stmt, locals_: list[str]) -> StmtIR | None:
        if isinstance(stmt, ast.FunctionDef):
            raise NotImplementedError(
                f"Nested functions are not supported (line {stmt.lineno}): "
                f"def {stmt.name}(...). "
                "Consider refactoring to a module-level function."
            )
        if isinstance(stmt, ast.Return):
            return self._build_return(stmt, locals_)
        elif isinstance(stmt, ast.If):
            return self._build_if(stmt, locals_)
        elif isinstance(stmt, ast.While):
            return self._build_while(stmt, locals_)
        elif isinstance(stmt, ast.For):
            return self._build_for(stmt, locals_)
        elif isinstance(stmt, ast.Try):
            return self._build_try(stmt, locals_)
        elif isinstance(stmt, ast.Raise):
            return self._build_raise(stmt, locals_)
        elif isinstance(stmt, ast.Assign):
            return self._build_assign(stmt, locals_)
        elif isinstance(stmt, ast.AnnAssign):
            return self._build_ann_assign(stmt, locals_)
        elif isinstance(stmt, ast.AugAssign):
            return self._build_aug_assign(stmt, locals_)
        elif isinstance(stmt, ast.Break):
            return BreakIR()
        elif isinstance(stmt, ast.Continue):
            return ContinueIR()
        elif isinstance(stmt, ast.Pass):
            return PassIR()
        elif isinstance(stmt, ast.Expr):
            if isinstance(stmt.value, ast.Yield):
                if stmt.value.value is None:
                    return YieldIR(
                        value=None,
                        prelude=[],
                        state_id=self._next_yield_state_id(),
                    )
                value, prelude = self._build_expr(stmt.value.value, locals_)
                return YieldIR(
                    value=value,
                    prelude=prelude,
                    state_id=self._next_yield_state_id(),
                )
            # Handle yield from expression as statement
            if isinstance(stmt.value, ast.YieldFrom):
                iterable, prelude = self._build_expr(stmt.value.value, locals_)
                return YieldFromIR(
                    iterable=iterable,
                    prelude=prelude,
                    state_id=self._next_yield_state_id(),
                )
            # Handle await expression as statement (result discarded)
            if isinstance(stmt.value, ast.Await):
                return self._build_await(stmt.value, None, locals_)
            if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                return None
            if (
                isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == "print"
            ):
                return self._build_print(stmt.value, locals_)
            value, prelude = self._build_expr(stmt.value, locals_)
            return ExprStmtIR(expr=value, prelude=prelude)
        return None

    def _build_return(self, stmt: ast.Return, locals_: list[str]) -> ReturnIR:
        if stmt.value is None:
            return ReturnIR(value=None, prelude=[])
        value, prelude = self._build_expr(stmt.value, locals_)
        return ReturnIR(value=value, prelude=prelude)

    def _build_await(
        self, await_node: ast.Await, result_var: str | None, locals_: list[str]
    ) -> AwaitIR | AwaitModuleCallIR:
        """Build IR for await expression.

        Detects two patterns:
        1. await module.func(args) -> AwaitModuleCallIR (runtime module call)
        2. await expr -> AwaitIR (awaiting an existing awaitable)
        """
        awaited = await_node.value

        # Pattern 1: await module.func(args) - e.g., await asyncio.sleep(1)
        if isinstance(awaited, ast.Call) and isinstance(awaited.func, ast.Attribute):
            attr = awaited.func
            if isinstance(attr.value, ast.Name):
                module_name = attr.value.id
                func_name = attr.attr

                # Build arguments
                args: list[ValueIR] = []
                arg_preludes: list[list] = []
                for arg in awaited.args:
                    value, prelude = self._build_expr(arg, locals_)
                    args.append(value)
                    arg_preludes.append(prelude)

                return AwaitModuleCallIR(
                    module_name=module_name,
                    func_name=func_name,
                    args=args,
                    arg_preludes=arg_preludes,
                    result=result_var,
                    state_id=self._next_yield_state_id(),
                )

        # Pattern 2: await expr - awaiting an existing awaitable
        value, prelude = self._build_expr(awaited, locals_)
        return AwaitIR(
            value=value,
            result=result_var,
            prelude=prelude,
            state_id=self._next_yield_state_id(),
        )

    def _detect_none_check(self, test: ast.expr) -> tuple[str | None, bool]:
        """Detect 'x is None' or 'x is not None' patterns in an if test.

        Returns (var_name, is_none_check) where:
        - var_name: the variable being checked, or None if not a None check
        - is_none_check: True if 'x is None', False if 'x is not None'
        """
        if not isinstance(test, ast.Compare):
            return None, False
        if len(test.ops) != 1 or len(test.comparators) != 1:
            return None, False
        op = test.ops[0]
        if not isinstance(op, (ast.Is, ast.IsNot)):
            return None, False
        left = test.left
        right = test.comparators[0]
        # Pattern: x is None / x is not None
        if isinstance(left, ast.Name) and isinstance(right, ast.Constant) and right.value is None:
            return left.id, isinstance(op, ast.Is)
        # Pattern: None is x / None is not x (less common but valid)
        if isinstance(right, ast.Name) and isinstance(left, ast.Constant) and left.value is None:
            return right.id, isinstance(op, ast.Is)
        return None, False

    def _build_if(self, stmt: ast.If, locals_: list[str]) -> IfIR:
        test, test_prelude = self._build_expr(stmt.test, locals_)

        # Automatic type narrowing: detect isinstance in the test condition
        narrowing = self._extract_isinstance_narrowing(stmt.test)
        saved_type: str | None = None
        narrow_var: str | None = None

        if narrowing:
            narrow_var, narrow_class, negated = narrowing
            saved_type = self._class_typed_params.get(narrow_var)

            if not negated:
                # isinstance(x, Foo): narrow x to Foo in the if-body
                self._class_typed_params[narrow_var] = narrow_class

        # Detect None-check patterns for Optional type narrowing
        narrowed_var, is_none_check = self._detect_none_check(stmt.test)

        # Apply narrowing: if var is Optional and we have a None check,
        # narrow the type in the appropriate branch
        saved_optional = None
        if narrowed_var and narrowed_var in self._optional_class_params:
            saved_optional = narrowed_var
            if is_none_check:
                # 'if x is None:' -> body: x is None (keep optional), orelse: x narrowed
                body = [self._build_statement(s, locals_) for s in stmt.body]
                body = [s for s in body if s is not None]
                self._optional_class_params.discard(narrowed_var)
                orelse = [self._build_statement(s, locals_) for s in stmt.orelse]
                orelse = [s for s in orelse if s is not None]
                self._optional_class_params.add(narrowed_var)
            else:
                # 'if x is not None:' -> body: x narrowed, orelse: x is None (keep optional)
                self._optional_class_params.discard(narrowed_var)
                body = [self._build_statement(s, locals_) for s in stmt.body]
                body = [s for s in body if s is not None]
                self._optional_class_params.add(narrowed_var)
                orelse = [self._build_statement(s, locals_) for s in stmt.orelse]
                orelse = [s for s in orelse if s is not None]
        else:
            body = [self._build_statement(s, locals_) for s in stmt.body]
            body = [s for s in body if s is not None]

            # Restore isinstance narrowing after body, apply to orelse if negated
            if narrowing:
                narrow_var, narrow_class, negated = narrowing
                if not negated:
                    # Restore original type for orelse branch
                    if saved_type is not None:
                        self._class_typed_params[narrow_var] = saved_type
                    elif narrow_var in self._class_typed_params:
                        del self._class_typed_params[narrow_var]
                else:
                    # not isinstance(x, Foo): narrow x to Foo in the orelse branch
                    self._class_typed_params[narrow_var] = narrow_class

            orelse = [self._build_statement(s, locals_) for s in stmt.orelse]
            orelse = [s for s in orelse if s is not None]

            # Restore isinstance narrowing after orelse (for negated case)
            if narrowing and negated:
                narrow_var = narrowing[0]
                if saved_type is not None:
                    self._class_typed_params[narrow_var] = saved_type
                elif narrow_var in self._class_typed_params:
                    del self._class_typed_params[narrow_var]

        # Early-return narrowing: if 'if x is None: return/raise' pattern,
        # x is not None after the if statement
        if saved_optional and is_none_check and body and isinstance(body[-1], (ReturnIR, RaiseIR)):
            # Body always exits -> everything after this if has x narrowed
            self._optional_class_params.discard(saved_optional)

        return IfIR(test=test, body=body, orelse=orelse, test_prelude=test_prelude)

    def _build_while(self, stmt: ast.While, locals_: list[str]) -> WhileIR:
        test, test_prelude = self._build_expr(stmt.test, locals_)
        self._loop_depth += 1
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1
        return WhileIR(test=test, body=body, test_prelude=test_prelude)

    def _build_try(self, stmt: ast.Try, locals_: list[str]) -> TryIR:
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]

        handlers: list[ExceptHandlerIR] = []
        for handler in stmt.handlers:
            exc_type: str | None = None
            if handler.type is not None:
                if isinstance(handler.type, ast.Name):
                    exc_type = handler.type.id
                elif isinstance(handler.type, ast.Attribute):
                    exc_type = handler.type.attr

            exc_var = handler.name
            c_exc_var = sanitize_name(exc_var) if exc_var else None

            if exc_var and exc_var not in locals_:
                locals_.append(exc_var)
                self._var_types[exc_var] = "mp_obj_t"

            handler_body = [self._build_statement(s, locals_) for s in handler.body]
            handler_body = [s for s in handler_body if s is not None]

            handlers.append(
                ExceptHandlerIR(
                    exc_type=exc_type,
                    exc_var=exc_var,
                    c_exc_var=c_exc_var,
                    body=handler_body,
                )
            )

        orelse = [self._build_statement(s, locals_) for s in stmt.orelse]
        orelse = [s for s in orelse if s is not None]

        finalbody = [self._build_statement(s, locals_) for s in stmt.finalbody]
        finalbody = [s for s in finalbody if s is not None]

        return TryIR(body=body, handlers=handlers, orelse=orelse, finalbody=finalbody)

    def _build_raise(self, stmt: ast.Raise, locals_: list[str]) -> RaiseIR:
        if stmt.exc is None:
            return RaiseIR(is_reraise=True)

        exc_type: str | None = None
        exc_msg: ValueIR | None = None
        prelude: list = []

        if isinstance(stmt.exc, ast.Call):
            if isinstance(stmt.exc.func, ast.Name):
                exc_type = stmt.exc.func.id
            elif isinstance(stmt.exc.func, ast.Attribute):
                exc_type = stmt.exc.func.attr

            if stmt.exc.args:
                exc_msg, prelude = self._build_expr(stmt.exc.args[0], locals_)
        elif isinstance(stmt.exc, ast.Name):
            exc_type = stmt.exc.id

        return RaiseIR(exc_type=exc_type, exc_msg=exc_msg, prelude=prelude)

    def _build_for(self, stmt: ast.For, locals_: list[str]) -> ForRangeIR | ForIterIR:
        # Handle tuple unpacking: for k, v in items
        if isinstance(stmt.target, ast.Tuple):
            return self._build_for_tuple_unpack(stmt, locals_)

        if not isinstance(stmt.target, ast.Name):
            raise ValueError("Unsupported for loop target")

        loop_var = stmt.target.id
        c_loop_var = sanitize_name(loop_var)
        is_new_var = loop_var not in locals_
        is_range = (
            isinstance(stmt.iter, ast.Call)
            and isinstance(stmt.iter.func, ast.Name)
            and stmt.iter.func.id == "range"
        )
        if is_new_var:
            locals_.append(loop_var)
            # range() yields ints; generic iteration yields objects
            self._var_types[loop_var] = "mp_int_t" if is_range else "mp_obj_t"

        if is_range:
            return self._build_for_range(stmt, loop_var, c_loop_var, is_new_var, locals_)
        else:
            return self._build_for_iter(stmt, loop_var, c_loop_var, is_new_var, locals_)

    def _build_for_range(
        self, stmt: ast.For, loop_var: str, c_loop_var: str, is_new_var: bool, locals_: list[str]
    ) -> ForRangeIR:
        assert isinstance(stmt.iter, ast.Call)
        args = stmt.iter.args

        step_is_constant = False
        step_value: int | None = None
        step: ValueIR | None = None

        if len(args) == 1:
            start = ConstIR(ir_type=IRType.INT, value=0)
            end, _ = self._build_expr(args[0], locals_)
            step_is_constant = True
            step_value = 1
        elif len(args) == 2:
            start, _ = self._build_expr(args[0], locals_)
            end, _ = self._build_expr(args[1], locals_)
            step_is_constant = True
            step_value = 1
        elif len(args) == 3:
            start, _ = self._build_expr(args[0], locals_)
            end, _ = self._build_expr(args[1], locals_)
            if isinstance(args[2], ast.Constant) and isinstance(args[2].value, int):
                step_is_constant = True
                step_value = args[2].value
            elif isinstance(args[2], ast.UnaryOp) and isinstance(args[2].op, ast.USub):
                if isinstance(args[2].operand, ast.Constant) and isinstance(
                    args[2].operand.value, int
                ):
                    step_is_constant = True
                    step_value = -args[2].operand.value
                else:
                    step, _ = self._build_expr(args[2], locals_)
            else:
                step, _ = self._build_expr(args[2], locals_)
        else:
            raise ValueError("Unsupported range() call")

        self._loop_depth += 1
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1

        return ForRangeIR(
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            start=start,
            end=end,
            step=step,
            step_is_constant=step_is_constant,
            step_value=step_value,
            body=body,
            is_new_var=is_new_var,
        )

    def _build_for_iter(
        self, stmt: ast.For, loop_var: str, c_loop_var: str, is_new_var: bool, locals_: list[str]
    ) -> ForIterIR:
        iterable, iter_prelude = self._build_expr(stmt.iter, locals_)
        if isinstance(stmt.iter, ast.Name) and stmt.iter.id in self._container_element_types:
            self._class_typed_params[loop_var] = self._container_element_types[stmt.iter.id]
        elif isinstance(stmt.iter, ast.Attribute) and isinstance(stmt.iter.value, ast.Name):
            parent_var = stmt.iter.value.id
            attr_name = stmt.iter.attr
            if parent_var in self._class_typed_params:
                parent_class = self._class_typed_params[parent_var]
                elem_type = self._class_field_element_types.get((parent_class, attr_name))
                if elem_type:
                    self._class_typed_params[loop_var] = elem_type
        self._var_types[loop_var] = "mp_obj_t"

        self._loop_depth += 1
        body = [self._build_statement(s, locals_) for s in stmt.body]
        body = [s for s in body if s is not None]
        self._loop_depth -= 1

        return ForIterIR(
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            iterable=iterable,
            body=body,
            iter_prelude=iter_prelude,
            is_new_var=is_new_var,
        )

    def _build_for_tuple_unpack(self, stmt: ast.For, locals_: list[str]) -> ForIterIR:
        """Build for loop with tuple unpacking: for k, v in items."""
        assert isinstance(stmt.target, ast.Tuple)

        # Generate a temp variable to hold each iteration item
        item_var = f"_item_{self._temp_counter}"
        self._temp_counter += 1
        c_item_var = item_var

        # Item var is always new
        locals_.append(item_var)
        self._var_types[item_var] = "mp_obj_t"

        # Build tuple unpack targets
        unpack_targets: list[tuple[str, str, bool, str]] = []
        for elt in stmt.target.elts:
            if isinstance(elt, ast.Name):
                var_name = elt.id
                c_var_name = sanitize_name(var_name)
                is_new = var_name not in locals_
                if is_new:
                    locals_.append(var_name)
                    self._var_types[var_name] = "mp_obj_t"
                unpack_targets.append((var_name, c_var_name, is_new, "mp_obj_t"))

        # Create tuple unpack IR to prepend to body
        unpack_ir = TupleUnpackIR(
            targets=unpack_targets,
            value=NameIR(py_name=item_var, c_name=c_item_var, ir_type=IRType.OBJ),
            prelude=[],
        )

        # Build iterable expression
        iterable, iter_prelude = self._build_expr(stmt.iter, locals_)

        # Build loop body with unpack prepended
        self._loop_depth += 1
        body_stmts = [self._build_statement(s, locals_) for s in stmt.body]
        body_stmts = [s for s in body_stmts if s is not None]
        self._loop_depth -= 1

        # Prepend tuple unpack to body
        body = [unpack_ir] + body_stmts

        return ForIterIR(
            loop_var=item_var,
            c_loop_var=c_item_var,
            iterable=iterable,
            body=body,
            iter_prelude=iter_prelude,
            is_new_var=True,
        )

    def _build_assign(self, stmt: ast.Assign, locals_: list[str]) -> StmtIR | None:
        if len(stmt.targets) != 1:
            return None

        target = stmt.targets[0]

        if self._ctx.is_method and isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name) and target.value.id == "self":
                attr_name = target.attr
                value, prelude = self._build_expr(stmt.value, locals_)
                attr_path = attr_name
                class_ir = self._ctx.class_ir
                for fld, path in class_ir.get_all_fields_with_path():
                    if fld.name == attr_name:
                        attr_path = path
                        break
                return AttrAssignIR(
                    attr_name=attr_name,
                    attr_path=attr_path,
                    value=value,
                    prelude=prelude,
                )

        if isinstance(target, ast.Subscript):
            return self._build_subscript_assign(target, stmt.value, locals_)

        if isinstance(target, ast.Tuple):
            return self._build_tuple_unpack(target, stmt.value, locals_)


        # Handle local_var.attr = value (not self.attr which is handled above)
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            obj_name = target.value.id
            attr_name = target.attr
            if obj_name != "self" and obj_name in locals_:
                value, prelude = self._build_expr(stmt.value, locals_)
                obj_class_name: str | None = self._class_typed_params.get(obj_name)
                obj_class_c_name: str | None = None
                attr_path = attr_name
                if obj_class_name and obj_class_name in self._known_classes:
                    class_ir = self._known_classes[obj_class_name]
                    obj_class_c_name = class_ir.c_name
                    for fld, path in class_ir.get_all_fields_with_path():
                        if fld.name == attr_name:
                            attr_path = path
                            break
                return ObjAttrAssignIR(
                    obj_name=sanitize_name(obj_name),
                    obj_class=obj_class_c_name,
                    attr_name=attr_name,
                    attr_path=attr_path,
                    value=value,
                    prelude=prelude,
                )
        if not isinstance(target, ast.Name):
            return None

        var_name = target.id
        c_var_name = sanitize_name(var_name)
        # Handle await expression in assignment: result = await something
        if isinstance(stmt.value, ast.Await):
            is_new_var = var_name not in locals_
            if is_new_var:
                locals_.append(var_name)
                c_type = "mp_obj_t"  # await always returns mp_obj_t
                self._var_types[var_name] = c_type
            return self._build_await(stmt.value, c_var_name, locals_)

        value, prelude = self._build_expr(stmt.value, locals_)
        is_new_var = var_name not in locals_
        if is_new_var:
            locals_.append(var_name)
            if var_name in self._mypy_local_types:
                c_type = self._mypy_type_to_c_type(self._mypy_local_types[var_name])
            else:
                value_type = self._get_value_ir_type(value)
                c_type = value_type.to_c_type_str()
            self._var_types[var_name] = c_type
        else:
            c_type = self._var_types.get(var_name, "mp_obj_t")

        # Track class-typed local variables for attribute access
        # First try mypy local types
        if var_name in self._mypy_local_types:
            inferred_class = self._resolve_class_name_from_type_str(
                self._mypy_local_types[var_name]
            )
            if inferred_class:
                self._class_typed_params[var_name] = inferred_class
        # Then try function return type: var = func_call(...)
        if var_name not in self._class_typed_params:
            if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
                func_name = stmt.value.func.id
                if func_name in self._func_class_returns:
                    self._class_typed_params[var_name] = self._func_class_returns[func_name]

        value_type = IRType.from_c_type_str(c_type)

        return AssignIR(
            target=var_name,
            c_target=c_var_name,
            value=value,
            value_type=value_type,
            prelude=prelude,
            is_new_var=is_new_var,
            c_type=c_type,
        )

    def _build_subscript_assign(
        self, target: ast.Subscript, value: ast.expr, locals_: list[str]
    ) -> SubscriptAssignIR:
        container, prelude1 = self._build_expr(target.value, locals_)
        key, prelude2 = self._build_expr(target.slice, locals_)
        val, prelude3 = self._build_expr(value, locals_)
        return SubscriptAssignIR(
            container=container,
            key=key,
            value=val,
            prelude=prelude1 + prelude2 + prelude3,
        )

    def _build_tuple_unpack(
        self, target: ast.Tuple, value: ast.expr, locals_: list[str]
    ) -> TupleUnpackIR:
        tuple_value, prelude = self._build_expr(value, locals_)
        targets: list[tuple[str, str, bool, str]] = []
        for elt in target.elts:
            if isinstance(elt, ast.Name):
                var_name = elt.id
                c_var_name = sanitize_name(var_name)
                is_new = var_name not in locals_
                c_type = self._var_types.get(var_name, "mp_obj_t")
                if is_new:
                    locals_.append(var_name)
                    self._var_types[var_name] = "mp_obj_t"
                    c_type = "mp_obj_t"
                targets.append((var_name, c_var_name, is_new, c_type))
        return TupleUnpackIR(targets=targets, value=tuple_value, prelude=prelude)

    def _build_ann_assign(self, stmt: ast.AnnAssign, locals_: list[str]) -> AnnAssignIR | None:
        if not isinstance(stmt.target, ast.Name):
            return None

        var_name = stmt.target.id
        c_var_name = sanitize_name(var_name)
        c_type = self._annotation_to_c_type(stmt.annotation) if stmt.annotation else "mp_int_t"

        rtuple = self._try_parse_rtuple(stmt.annotation)
        if rtuple is not None:
            self._rtuple_types[var_name] = rtuple
            self._used_rtuples.add(rtuple)
            c_type = rtuple.get_c_struct_name()

        is_list, elem_type = self._is_list_annotation(stmt.annotation)
        if is_list:
            self._list_vars[var_name] = elem_type

        is_new_var = var_name not in locals_
        if is_new_var:
            locals_.append(var_name)
        self._var_types[var_name] = c_type

        # Track class-typed local variables for attribute access
        if stmt.annotation:
            class_name = self._extract_class_from_annotation(stmt.annotation)
            if class_name:
                self._class_typed_params[var_name] = class_name
                if self._is_optional_class_annotation(stmt.annotation):
                    self._optional_class_params.add(var_name)
            else:
                elem_class = self._extract_container_element_class(stmt.annotation)
                if elem_class:
                    self._container_element_types[var_name] = elem_class

        value: ValueIR | None = None
        prelude: list = []
        if stmt.value is not None:
            value, prelude = self._build_expr(stmt.value, locals_)

        return AnnAssignIR(
            target=var_name,
            c_target=c_var_name,
            c_type=c_type,
            value=value,
            prelude=prelude,
            is_new_var=is_new_var,
        )

    def _build_aug_assign(
        self, stmt: ast.AugAssign, locals_: list[str]
    ) -> AugAssignIR | SelfAugAssignIR | None:
        op_map = {
            ast.Add: "+=",
            ast.Sub: "-=",
            ast.Mult: "*=",
            ast.Div: "/=",
            ast.FloorDiv: "//=",
            ast.Mod: "%=",
            ast.BitAnd: "&=",
            ast.BitOr: "|=",
            ast.BitXor: "^=",
            ast.LShift: "<<=",
            ast.RShift: ">>=",
        }
        c_op = op_map.get(type(stmt.op), "+=")

        if self._ctx.is_method and isinstance(stmt.target, ast.Attribute):
            if isinstance(stmt.target.value, ast.Name) and stmt.target.value.id == "self":
                attr_name = stmt.target.attr
                value, prelude = self._build_expr(stmt.value, locals_)
                return SelfAugAssignIR(
                    attr_name=attr_name,
                    attr_path=attr_name,
                    op=c_op,
                    value=value,
                    prelude=prelude,
                )
            return None

        if not isinstance(stmt.target, ast.Name):
            return None

        var_name = stmt.target.id
        c_var_name = sanitize_name(var_name)
        value, prelude = self._build_expr(stmt.value, locals_)

        target_c_type = self._var_types.get(var_name, "mp_int_t")

        return AugAssignIR(
            target=var_name,
            c_target=c_var_name,
            op=c_op,
            value=value,
            target_c_type=target_c_type,
            prelude=prelude,
        )

    def _build_print(self, call: ast.Call, locals_: list[str]) -> PrintIR:
        self._uses_print = True
        args: list[ValueIR] = []
        preludes: list[list] = []
        for arg in call.args:
            value, prelude = self._build_expr(arg, locals_)
            args.append(value)
            preludes.append(prelude)
        return PrintIR(args=args, preludes=preludes)

    def _build_expr(self, expr: ast.expr, locals_: list[str]) -> tuple[ValueIR, list]:
        if isinstance(expr, ast.YieldFrom):
            raise NotImplementedError(
                f"yield from as expression is not supported (use as statement instead) (line {expr.lineno})"
            )
        if isinstance(expr, ast.Yield):
            raise NotImplementedError(
                f"yield as an expression is not supported (line {expr.lineno})"
            )

        if self._ctx.is_method:
            class_ir = self._ctx.class_ir

            if isinstance(expr, ast.Attribute):
                if isinstance(expr.value, ast.Name):
                    var_name = expr.value.id
                    attr_name = expr.attr

                    if var_name == "self":
                        for fld, path in class_ir.get_all_fields_with_path():
                            if fld.name == attr_name:
                                result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                                return SelfAttrIR(
                                    ir_type=result_type,
                                    attr_name=attr_name,
                                    attr_path=path,
                                    result_type=result_type,
                                ), []
                        if attr_name in class_ir.methods:
                            method_ir = class_ir.methods[attr_name]
                            return SelfMethodRefIR(
                                ir_type=IRType.OBJ,
                                method_name=attr_name,
                                method_c_name=method_ir.c_name,
                                class_c_name=class_ir.c_name,
                            ), []
                        self._warn_type_tracking_fallback(
                            "self attribute",
                            "self",
                            attr_name,
                            f"Attribute '{attr_name}' not found in class '{class_ir.name}'",
                        )
                        return SelfAttrIR(
                            ir_type=IRType.OBJ,
                            attr_name=attr_name,
                            attr_path=attr_name,
                            result_type=IRType.OBJ,
                        ), []

                    if var_name in self._class_typed_params:
                        param_class_name = self._class_typed_params[var_name]
                        param_class_ir = self._known_classes[param_class_name]
                        use_dynamic = (
                            param_class_ir.is_trait or var_name in self._optional_class_params
                        )
                        for fld, path in param_class_ir.get_all_fields_with_path():
                            if fld.name == attr_name:
                                result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                                return ParamAttrIR(
                                    ir_type=result_type,
                                    param_name=var_name,
                                    c_param_name=sanitize_name(var_name),
                                    attr_name=attr_name,
                                    attr_path=path,
                                    class_c_name=param_class_ir.c_name,
                                    result_type=result_type,
                                    is_trait_type=use_dynamic,
                                ), []
                        self._warn_type_tracking_fallback(
                            "param attribute",
                            var_name,
                            attr_name,
                            f"Attribute '{attr_name}' not found in class '{param_class_ir.name}'",
                        )
                        return ParamAttrIR(
                            ir_type=IRType.OBJ,
                            param_name=var_name,
                            c_param_name=sanitize_name(var_name),
                            attr_name=attr_name,
                            attr_path=attr_name,
                            class_c_name=param_class_ir.c_name,
                            result_type=IRType.OBJ,
                            is_trait_type=use_dynamic,
                        ), []

                if isinstance(expr.value, ast.Attribute):
                    attr_name = expr.attr
                    base_class_name = self._get_method_attr_class_type(expr.value, class_ir)
                    if base_class_name and base_class_name in self._known_classes:
                        base_class_ir = self._known_classes[base_class_name]
                        base_value, base_prelude = self._build_expr(expr.value, locals_)
                        for fld in base_class_ir.get_all_fields():
                            if fld.name == attr_name:
                                result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                                temp_name = self._fresh_temp()
                                result_temp = TempIR(ir_type=result_type, name=temp_name)
                                attr_access = AttrAccessIR(
                                    result=result_temp,
                                    obj=base_value,
                                    attr_name=attr_name,
                                    class_c_name=base_class_ir.c_name,
                                    result_type=result_type,
                                )
                                return result_temp, base_prelude + [attr_access]
                        self._warn_type_tracking_fallback(
                            "chained attribute",
                            f"{ast.unparse(expr.value)}",
                            attr_name,
                            f"Attribute '{attr_name}' not found in class '{base_class_ir.name}'",
                        )
                    else:
                        self._warn_type_tracking_fallback(
                            "chained attribute",
                            f"{ast.unparse(expr.value)}",
                            expr.attr,
                            "Could not resolve class type for base expression",
                        )

            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
                if (
                    isinstance(expr.func.value, ast.Call)
                    and isinstance(expr.func.value.func, ast.Name)
                    and expr.func.value.func.id == "super"
                    and len(expr.func.value.args) == 0
                    and len(expr.func.value.keywords) == 0
                ):
                    method_name = expr.func.attr
                    parent_class = class_ir.base
                    while parent_class is not None and method_name not in parent_class.methods:
                        parent_class = parent_class.base
                    if parent_class is not None:
                        parent_method = parent_class.methods[method_name]
                        args: list[ValueIR] = []
                        arg_preludes: list[list] = []
                        for arg in expr.args:
                            val, prelude = self._build_expr(arg, locals_)
                            args.append(val)
                            arg_preludes.append(prelude)
                        return_type = IRType.from_c_type_str(
                            parent_method.return_type.to_c_type_str()
                        )
                        all_preludes = [p for pl in arg_preludes for p in pl]
                        return SuperCallIR(
                            ir_type=return_type,
                            method_name=method_name,
                            parent_c_name=parent_class.c_name,
                            parent_method_c_name=parent_method.c_name,
                            args=args,
                            return_type=return_type,
                            is_init=method_name == "__init__",
                            arg_preludes=arg_preludes,
                        ), all_preludes

            if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
                if isinstance(expr.func.value, ast.Name) and expr.func.value.id == "self":
                    method_name = expr.func.attr
                    method_ir = class_ir.methods.get(method_name)
                    args: list[ValueIR] = []
                    arg_preludes: list[list] = []
                    for arg in expr.args:
                        val, prelude = self._build_expr(arg, locals_)
                        args.append(val)
                        arg_preludes.append(prelude)

                    # self.field(...) must not be lowered as a direct native method call
                    # when the attribute is a data field (often typed as object).
                    # Load self->field into a temp and call it dynamically.
                    if method_ir is None:
                        field_with_path = next(
                            (
                                (fld, path)
                                for fld, path in class_ir.get_all_fields_with_path()
                                if fld.name == method_name
                            ),
                            None,
                        )
                        if field_with_path is not None:
                            field_ir, field_path = field_with_path
                            field_type = IRType.from_c_type_str(field_ir.c_type.to_c_type_str())
                            callable_temp = TempIR(ir_type=IRType.OBJ, name=self._fresh_temp())
                            callable_load = BoxIR(
                                result=callable_temp,
                                value=SelfAttrIR(
                                    ir_type=field_type,
                                    attr_name=method_name,
                                    attr_path=field_path,
                                    result_type=field_type,
                                ),
                            )
                            all_preludes = [callable_load]
                            all_preludes.extend(p for pl in arg_preludes for p in pl)
                            return DynamicCallIR(
                                ir_type=IRType.OBJ,
                                callable_var=callable_temp.name,
                                args=args,
                                kwargs=[],
                                arg_preludes=arg_preludes,
                            ), all_preludes

                    c_method_name = f"{class_ir.c_name}_{sanitize_name(method_name)}"
                    return_type = IRType.OBJ
                    if method_ir:
                        return_type = IRType.from_c_type_str(method_ir.return_type.to_c_type_str())
                    all_preludes = [p for pl in arg_preludes for p in pl]
                    param_types: list[IRType] = []
                    if method_ir:
                        for _pname, ptype in method_ir.params:
                            param_types.append(IRType.from_c_type_str(ptype.to_c_type_str()))
                    return SelfMethodCallIR(
                        ir_type=return_type,
                        method_name=method_name,
                        c_method_name=c_method_name,
                        args=args,
                        return_type=return_type,
                        arg_preludes=arg_preludes,
                        param_types=param_types,
                    ), all_preludes

        if isinstance(expr, ast.Constant):
            return self._build_constant(expr), []
        elif isinstance(expr, ast.Name):
            return self._build_name(expr, locals_), []
        elif isinstance(expr, ast.BinOp):
            return self._build_binop(expr, locals_)
        elif isinstance(expr, ast.BoolOp):
            return self._build_boolop(expr, locals_)
        elif isinstance(expr, ast.UnaryOp):
            return self._build_unaryop(expr, locals_)
        elif isinstance(expr, ast.Compare):
            return self._build_compare(expr, locals_)
        elif isinstance(expr, ast.Call):
            return self._build_call(expr, locals_)
        elif isinstance(expr, ast.IfExp):
            return self._build_ifexp(expr, locals_)
        elif isinstance(expr, ast.List):
            return self._build_list(expr, locals_)
        elif isinstance(expr, ast.Tuple):
            return self._build_tuple(expr, locals_)
        elif isinstance(expr, ast.Set):
            return self._build_set(expr, locals_)
        elif isinstance(expr, ast.Dict):
            return self._build_dict(expr, locals_)
        elif isinstance(expr, ast.Subscript):
            return self._build_subscript(expr, locals_)
        elif isinstance(expr, ast.Attribute):
            return self._build_attribute(expr, locals_)
        elif isinstance(expr, ast.ListComp):
            return self._build_list_comp(expr, locals_)
        return ConstIR(ir_type=IRType.OBJ, value=None), []

    def _build_constant(self, expr: ast.Constant) -> ConstIR:
        val = expr.value
        if isinstance(val, bool):
            return ConstIR(ir_type=IRType.BOOL, value=val)
        elif isinstance(val, int):
            return ConstIR(ir_type=IRType.INT, value=val)
        elif isinstance(val, float):
            return ConstIR(ir_type=IRType.FLOAT, value=val)
        elif val is None:
            return ConstIR(ir_type=IRType.OBJ, value=None)
        elif isinstance(val, str):
            return ConstIR(ir_type=IRType.OBJ, value=val)
        return ConstIR(ir_type=IRType.OBJ, value=val)

    def _build_name(self, expr: ast.Name, locals_: list[str]) -> ValueIR:
        name = expr.id
        if name == "True":
            return ConstIR(ir_type=IRType.BOOL, value=True)
        elif name == "False":
            return ConstIR(ir_type=IRType.BOOL, value=False)
        elif name == "None":
            return ConstIR(ir_type=IRType.OBJ, value=None)

        # Check for module-level constants
        if name in self._module_constants:
            const_val = self._module_constants[name]
            if isinstance(const_val, bool):
                return ConstIR(ir_type=IRType.BOOL, value=const_val)
            elif isinstance(const_val, int):
                return ConstIR(ir_type=IRType.INT, value=const_val)
            elif isinstance(const_val, float):
                return ConstIR(ir_type=IRType.FLOAT, value=const_val)
            elif isinstance(const_val, str):
                return ConstIR(ir_type=IRType.OBJ, value=const_val)
            elif const_val is None:
                return ConstIR(ir_type=IRType.OBJ, value=None)

        # Check for cross-module constants (imported from sibling modules)
        # Note: _sibling_constants may be keyed by fully-qualified module names
        # (e.g. 'pkg.diff'), while source_module can be a short name (e.g. 'diff').
        # Try both exact and short-name matches.
        if name in self._imported_from:
            source_module = self._imported_from[name]
            const_val = None
            # Try exact match first
            if source_module in self._sibling_constants:
                if name in self._sibling_constants[source_module]:
                    const_val = self._sibling_constants[source_module][name]
            else:
                # Try matching by short name (last component)
                for mod_key, consts in self._sibling_constants.items():
                    if mod_key.rsplit(".", 1)[-1] == source_module:
                        if name in consts:
                            const_val = consts[name]
                            break
            if const_val is not None or (
                name in self._imported_from
                and any(name in c for c in self._sibling_constants.values())
            ):
                # Check if we found a constant with value None (different from not found)
                found_none = False
                if const_val is None:
                    if source_module in self._sibling_constants:
                        found_none = name in self._sibling_constants[source_module]
                    else:
                        for mod_key, consts in self._sibling_constants.items():
                            if mod_key.rsplit(".", 1)[-1] == source_module:
                                found_none = name in consts
                                break
                if const_val is not None or found_none:
                    if isinstance(const_val, bool):
                        return ConstIR(ir_type=IRType.BOOL, value=const_val)
                    elif isinstance(const_val, int):
                        return ConstIR(ir_type=IRType.INT, value=const_val)
                    elif isinstance(const_val, float):
                        return ConstIR(ir_type=IRType.FLOAT, value=const_val)
                    elif isinstance(const_val, str):
                        return ConstIR(ir_type=IRType.OBJ, value=const_val)
                    elif const_val is None:
                        return ConstIR(ir_type=IRType.OBJ, value=None)

        if name in self._module_vars and name not in self._var_types:
            return NameIR(
                ir_type=IRType.OBJ,
                py_name=name,
                c_name=f"{self.c_name}_{sanitize_name(name)}",
            )

        # Check for module-level function references (function-as-value)
        if name in self._known_functions and name not in self._var_types:
            func_c_name, _ = self._known_functions[name]
            return FuncRefIR(
                ir_type=IRType.OBJ,
                py_name=name,
                c_name=func_c_name,
            )

        # Check for import aliases - return ModuleRefIR for imported modules
        if name in self._import_aliases:
            module_name = self._import_aliases[name]
            # Check if this is a sibling module in the same package
            if module_name in self._sibling_modules:
                c_prefix = self._sibling_modules[module_name]
                return SiblingModuleRefIR(ir_type=IRType.OBJ, c_prefix=c_prefix)
            self._uses_imports = True
            return ModuleRefIR(ir_type=IRType.OBJ, module_name=module_name)

        c_name = self._star_c_names.get(name, sanitize_name(name))
        var_type = self._var_types.get(name, "mp_int_t")
        ir_type = IRType.from_c_type_str(var_type)
        return NameIR(ir_type=ir_type, py_name=name, c_name=c_name)

    def _build_binop(self, expr: ast.BinOp, locals_: list[str]) -> tuple[BinOpIR, list]:
        left, left_prelude = self._build_expr(expr.left, locals_)
        right, right_prelude = self._build_expr(expr.right, locals_)

        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.FloorDiv: "//",  # Keep as // to distinguish from true division
            ast.Mod: "%",
            ast.BitAnd: "&",
            ast.BitOr: "|",
            ast.BitXor: "^",
            ast.LShift: "<<",
            ast.RShift: ">>",
        }
        c_op = op_map.get(type(expr.op), "+")

        left_type = self._get_value_ir_type(left)
        right_type = self._get_value_ir_type(right)

        if left_type == IRType.OBJ or right_type == IRType.OBJ:
            left_is_subscript = isinstance(left, SubscriptIR)
            right_is_subscript = isinstance(right, SubscriptIR)
            if left_is_subscript or right_is_subscript:
                result_type = IRType.INT
            else:
                result_type = IRType.OBJ
        elif left_type == IRType.FLOAT or right_type == IRType.FLOAT:
            result_type = IRType.FLOAT
        else:
            result_type = IRType.INT

        return BinOpIR(
            ir_type=result_type,
            left=left,
            op=c_op,
            right=right,
            left_prelude=left_prelude,
            right_prelude=right_prelude,
        ), left_prelude + right_prelude

    def _build_boolop(self, expr: ast.BoolOp, locals_: list[str]) -> tuple[BinOpIR, list]:
        c_op = "&&" if isinstance(expr.op, ast.And) else "||"

        values = expr.values
        left, left_prelude = self._build_expr(values[0], locals_)
        all_prelude = left_prelude[:]

        for i in range(1, len(values)):
            right, right_prelude = self._build_expr(values[i], locals_)
            all_prelude.extend(right_prelude)

            left = BinOpIR(
                ir_type=IRType.BOOL,
                left=left,
                op=c_op,
                right=right,
                left_prelude=[],
                right_prelude=right_prelude,
            )

        return left, all_prelude

    def _build_unaryop(self, expr: ast.UnaryOp, locals_: list[str]) -> tuple[UnaryOpIR, list]:
        operand, prelude = self._build_expr(expr.operand, locals_)
        op_map = {ast.USub: "-", ast.Not: "!", ast.UAdd: "+", ast.Invert: "~"}
        c_op = op_map.get(type(expr.op), "-")

        result_type = (
            IRType.BOOL if isinstance(expr.op, ast.Not) else self._get_value_ir_type(operand)
        )

        return UnaryOpIR(
            ir_type=result_type,
            op=c_op,
            operand=operand,
            prelude=prelude,
        ), prelude

    def _build_compare(self, expr: ast.Compare, locals_: list[str]) -> tuple[CompareIR, list]:
        left, left_prelude = self._build_expr(expr.left, locals_)

        op_map = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
            ast.In: "in",
            ast.NotIn: "not in",
            ast.Is: "is",
            ast.IsNot: "is not",
        }

        ops: list[str] = []
        comparators: list[ValueIR] = []
        comparator_preludes: list[list] = []
        has_contains = False

        for op, comparator in zip(expr.ops, expr.comparators):
            c_op = op_map.get(type(op), "==")
            if c_op in ("in", "not in"):
                has_contains = True
            ops.append(c_op)
            comp_val, comp_prelude = self._build_expr(comparator, locals_)
            comparators.append(comp_val)
            comparator_preludes.append(comp_prelude)

        all_preludes = left_prelude + [p for pl in comparator_preludes for p in pl]

        return CompareIR(
            ir_type=IRType.BOOL,
            left=left,
            ops=ops,
            comparators=comparators,
            has_contains=has_contains,
            left_prelude=left_prelude,
            comparator_preludes=comparator_preludes,
        ), all_preludes

    def _build_call(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
        if isinstance(expr.func, ast.Attribute):
            return self._build_method_call(expr, locals_)

        if not isinstance(expr.func, ast.Name):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        func_name = expr.func.id

        if func_name in self._known_classes:
            return self._build_class_instantiation(expr, func_name, locals_)

        # isinstance(obj, ClassName) -> IsInstanceIR
        if func_name == "isinstance" and len(expr.args) == 2:
            return self._build_isinstance(expr, locals_)

        if func_name in locals_:
            args: list[ValueIR] = []
            arg_preludes: list[list] = []
            for arg in expr.args:
                val, prelude = self._build_expr(arg, locals_)
                args.append(val)
                arg_preludes.append(prelude)
            kwargs: list[tuple[str, ValueIR]] = []
            kwarg_preludes: list[list] = []
            for kw in expr.keywords:
                if kw.arg is None:
                    continue
                val, prelude = self._build_expr(kw.value, locals_)
                kwargs.append((kw.arg, val))
                kwarg_preludes.append(prelude)
            all_preludes = [p for pl in arg_preludes for p in pl]
            all_preludes.extend(p for pl in kwarg_preludes for p in pl)
            return DynamicCallIR(
                ir_type=IRType.OBJ,
                callable_var=func_name,
                args=args,
                kwargs=kwargs,
                arg_preludes=arg_preludes,
            ), all_preludes

        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            args.append(val)
            arg_preludes.append(prelude)

        kwargs: list[tuple[str, ValueIR]] = []
        kwarg_preludes: list[list] = []
        for kw in expr.keywords:
            if kw.arg is None:
                continue
            val, prelude = self._build_expr(kw.value, locals_)
            kwargs.append((kw.arg, val))
            kwarg_preludes.append(prelude)

        all_preludes = [p for pl in arg_preludes for p in pl]
        all_preludes.extend(p for pl in kwarg_preludes for p in pl)

        if func_name in BUILTIN_FUNCTIONS:
            is_list_len_opt = False
            is_typed_list_sum = False
            sum_list_var: str | None = None
            sum_element_type: str | None = None

            if func_name == "len" and len(args) == 1:
                arg = args[0]
                if isinstance(arg, NameIR) and arg.py_name in self._list_vars:
                    is_list_len_opt = True
                    self._uses_list_opt = True

            if func_name == "sum" and len(args) >= 1:
                arg = args[0]
                if isinstance(arg, NameIR) and arg.py_name in self._list_vars:
                    elem_type = self._list_vars.get(arg.py_name)
                    if elem_type in ("int", "float"):
                        is_typed_list_sum = True
                        sum_list_var = arg.py_name
                        sum_element_type = elem_type
                        self._uses_list_opt = True

            ir_type = _builtin_ir_type(func_name)
            return CallIR(
                ir_type=ir_type,
                func_name=func_name,
                c_func_name=func_name,
                args=args,
                kwargs=kwargs,
                arg_preludes=arg_preludes,
                is_builtin=True,
                builtin_kind=func_name,
                is_list_len_opt=is_list_len_opt,
                is_typed_list_sum=is_typed_list_sum,
                sum_list_var=sum_list_var,
                sum_element_type=sum_element_type,
            ), all_preludes

        # Check if this function was imported from another module
        if func_name in self._imported_from:
            source_module = self._imported_from[func_name]
            # Check if source module is a sibling module in the same package
            # e.g., 'lvgl_mvu.diff' -> look up 'lvgl_mvu.diff' in _sibling_modules
            is_sibling = source_module in self._sibling_modules
            # Also check if it matches by short name
            if not is_sibling:
                for mod_key in self._sibling_modules:
                    if mod_key.rsplit(".", 1)[-1] == source_module:
                        is_sibling = True
                        source_module = mod_key  # Use the full module name
                        break
            if is_sibling:
                c_prefix = self._sibling_modules[source_module]
                c_func_name = f"{c_prefix}_{sanitize_name(func_name)}"
            else:
                # For external/non-sibling modules, there's no compiled C symbol.
                # Fall back to runtime import/call via ModuleCallIR.
                self._uses_imports = True
                return ModuleCallIR(
                    ir_type=IRType.OBJ,
                    module_name=source_module,
                    func_name=func_name,
                    args=args,
                    arg_preludes=arg_preludes,
                    kwargs=kwargs,
                ), all_preludes
        else:
            c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"

        # Look up the return type if this is a known function
        call_ir_type = IRType.OBJ  # default: unknown functions return mp_obj_t
        if func_name in self._known_functions:
            _, return_c_type = self._known_functions[func_name]
            call_ir_type = IRType.from_c_type_str(return_c_type.to_c_type_str())

        return CallIR(
            ir_type=call_ir_type,
            func_name=func_name,
            c_func_name=c_func_name,
            args=args,
            kwargs=kwargs,
            arg_preludes=arg_preludes,
            is_builtin=False,
            builtin_kind=None,
        ), all_preludes

    def _build_isinstance(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
        """Build isinstance(obj, ClassName) -> IsInstanceIR.

        Only supports compile-time-known concrete classes.
        Generates mp_obj_is_type(obj, &ClassName_type) for exact type check.
        """
        obj_expr = expr.args[0]
        class_arg = expr.args[1]

        # Build the object expression
        obj_val, obj_prelude = self._build_expr(obj_expr, locals_)

        # The second argument must be a known class name
        if not isinstance(class_arg, ast.Name):
            # Unsupported: isinstance with non-Name second arg (e.g., tuple of types)
            # With type_check=True, mypy will catch this; with type_check=False,
            # we conservatively return false rather than silently generating wrong code.
            return ConstIR(ir_type=IRType.BOOL, value=False), obj_prelude

        class_name = class_arg.id

        # Must be a known compiled class (not a trait, not a builtin type)
        if class_name not in self._known_classes:
            # Unknown class - fall back to runtime mp_obj_is_type with mp_type_*
            # for builtin types like int, str, list, dict, etc.
            builtin_types = {
                "int": "mp_type_int",
                "str": "mp_type_str",
                "float": "mp_type_float",
                "bool": "mp_type_bool",
                "list": "mp_type_list",
                "dict": "mp_type_dict",
                "tuple": "mp_type_tuple",
                "set": "mp_type_set",
            }
            if class_name in builtin_types:
                return IsInstanceIR(
                    ir_type=IRType.BOOL,
                    obj=obj_val,
                    class_name=class_name,
                    c_type_name=builtin_types[class_name],
                    obj_prelude=obj_prelude,
                ), obj_prelude
            # Unknown class not in compiled module -- with type_check=True, mypy
            # will report an error. With type_check=False, return false to avoid
            # generating a reference to an undefined C type.
            return ConstIR(ir_type=IRType.BOOL, value=False), obj_prelude

        class_ir = self._known_classes[class_name]

        # Traits have no single type object; isinstance(obj, Trait) cannot work
        # at runtime. Return false with a clear comment.
        if class_ir.is_trait:
            return ConstIR(ir_type=IRType.BOOL, value=False), obj_prelude

        c_type_name = f"{class_ir.c_name}_type"

        return IsInstanceIR(
            ir_type=IRType.BOOL,
            obj=obj_val,
            class_name=class_name,
            c_type_name=c_type_name,
            obj_prelude=obj_prelude,
        ), obj_prelude

    def _extract_isinstance_narrowing(self, test: ast.expr) -> tuple[str, str, bool] | None:
        """Extract isinstance narrowing info from an if-test AST node.

        Returns (var_name, class_name, is_negated) if the test is:
          - isinstance(var, ClassName) -> (var, ClassName, False)
          - not isinstance(var, ClassName) -> (var, ClassName, True)

        Only narrows for simple Name variables and known compiled classes.
        Returns None if narrowing cannot be extracted.
        """
        call: ast.Call | None = None
        negated = False

        if isinstance(test, ast.Call):
            call = test
        elif (
            isinstance(test, ast.UnaryOp)
            and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Call)
        ):
            call = test.operand
            negated = True
        else:
            return None

        # Must be isinstance(var, ClassName)
        if not (
            isinstance(call.func, ast.Name) and call.func.id == "isinstance" and len(call.args) == 2
        ):
            return None

        obj_arg = call.args[0]
        class_arg = call.args[1]

        # Only narrow simple variable names, not attribute chains
        if not isinstance(obj_arg, ast.Name):
            return None
        if not isinstance(class_arg, ast.Name):
            return None

        var_name = obj_arg.id
        class_name = class_arg.id

        # Only narrow for known compiled classes (not builtins, not traits)
        if class_name not in self._known_classes:
            return None
        if self._known_classes[class_name].is_trait:
            return None

        return var_name, class_name, negated

    @staticmethod
    def _is_private_name(name: str) -> bool:
        """Check if name is a private identifier (__name without trailing __)."""
        return name.startswith("__") and not name.endswith("__")

    def _build_method_call(self, expr: ast.Call, locals_: list[str]) -> tuple[ValueIR, list]:
        if not isinstance(expr.func, ast.Attribute):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        if isinstance(expr.func.value, ast.Name):
            var_name = expr.func.value.id
            if var_name in self._import_aliases:
                module_name = self._import_aliases[var_name]
                if module_name in self._external_libs:
                    return self._build_clib_call(expr, var_name, locals_)
                return self._build_module_call(expr, var_name, locals_)

        receiver, recv_prelude = self._build_expr(expr.func.value, locals_)
        method_name = expr.func.attr

        # Reject external access to private (__method) members
        is_self_call = isinstance(expr.func.value, ast.Name) and expr.func.value.id == "self"
        if self._is_private_name(method_name) and not (self._ctx.is_method and is_self_call):
            raise TypeError(f"Cannot access private method '{method_name}' from outside its class")

        args: list[ValueIR] = []
        all_preludes = list(recv_prelude)
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            all_preludes.extend(prelude)
            args.append(val)

        kwargs: list[tuple[str, ValueIR]] = []
        for kw in expr.keywords:
            if kw.arg is None:
                continue
            val, prelude = self._build_expr(kw.value, locals_)
            kwargs.append((kw.arg, val))
            all_preludes.extend(prelude)

        # Determine receiver Python type for optimizations (dict.get, etc.)
        receiver_py_type: str | None = None
        if isinstance(receiver, NameIR):
            var_name = receiver.py_name
            # Try mypy types first, then fallback to param annotations
            if var_name in self._mypy_local_types:
                receiver_py_type = self._mypy_local_types[var_name]
            elif var_name in self._param_py_types:
                receiver_py_type = self._param_py_types[var_name]

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        method_call = MethodCallIR(
            result=result,
            receiver=receiver,
            method=method_name,
            args=args,
            kwargs=kwargs,
            receiver_py_type=receiver_py_type,
        )

        return result, all_preludes + [method_call]

    def _build_clib_call(
        self, expr: ast.Call, alias: str, locals_: list[str]
    ) -> tuple[ValueIR, list]:
        from .c_bindings.core.c_ir import CType as CBindingsCType
        from .ir import CLibCallIR

        if not isinstance(expr.func, ast.Attribute):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        lib_name = self._import_aliases[alias]
        lib_def = self._external_libs[lib_name]
        func_name = expr.func.attr
        self._uses_external_libs.add(lib_name)

        func_def = lib_def.functions.get(func_name)

        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            args.append(val)
            arg_preludes.append(prelude)
        all_preludes = [p for pl in arg_preludes for p in pl]

        has_callback = False
        if func_def:
            c_wrapper_name = f"{func_def.c_name}_wrapper"
            is_void = func_def.return_type.base_type == CBindingsCType.VOID
            has_callback = any(
                p.type_def.base_type == CBindingsCType.CALLBACK for p in func_def.params
            )
        else:
            c_wrapper_name = f"{func_name}_wrapper"
            is_void = False

        uses_var_args = len(args) > 3 or has_callback
        return CLibCallIR(
            ir_type=IRType.OBJ,
            lib_name=lib_name,
            func_name=func_name,
            c_wrapper_name=c_wrapper_name,
            args=args,
            arg_preludes=arg_preludes,
            is_void=is_void,
            uses_var_args=uses_var_args,
        ), all_preludes

    def _build_module_call(
        self, expr: ast.Call, alias: str, locals_: list[str]
    ) -> tuple[ValueIR, list]:
        """Build IR for a call on an imported module: module.func(args, **kwargs)."""
        if not isinstance(expr.func, ast.Attribute):
            return ConstIR(ir_type=IRType.OBJ, value=None), []

        module_name = self._import_aliases[alias]
        func_name = expr.func.attr
        self._uses_imports = True

        # Process positional arguments
        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            args.append(val)
            arg_preludes.append(prelude)

        # Process keyword arguments
        kwargs: list[tuple[str, ValueIR]] = []
        kwarg_preludes: list[list] = []
        for kw in expr.keywords:
            if kw.arg is None:  # **kwargs - not supported
                continue
            val, prelude = self._build_expr(kw.value, locals_)
            kwargs.append((kw.arg, val))
            kwarg_preludes.append(prelude)

        all_preludes = [p for pl in arg_preludes for p in pl]
        all_preludes.extend([p for pl in kwarg_preludes for p in pl])

        # Check if this is a sibling module in the same package
        if module_name in self._sibling_modules:
            c_prefix = self._sibling_modules[module_name]
            # Check if this is a class instantiation (class names start with uppercase)
            if func_name and func_name[0].isupper():
                return SiblingClassInstantiationIR(
                    ir_type=IRType.OBJ,
                    c_prefix=c_prefix,
                    class_name=func_name,
                    args=args,
                    arg_preludes=arg_preludes,
                ), all_preludes
            return SiblingModuleCallIR(
                ir_type=IRType.OBJ,
                c_prefix=c_prefix,
                func_name=func_name,
                args=args,
                arg_preludes=arg_preludes,
            ), all_preludes

        return ModuleCallIR(
            ir_type=IRType.OBJ,
            module_name=module_name,
            func_name=func_name,
            args=args,
            arg_preludes=arg_preludes,
            kwargs=kwargs,
            kwarg_preludes=kwarg_preludes,
        ), all_preludes

    def _build_class_instantiation(
        self, expr: ast.Call, class_name: str, locals_: list[str]
    ) -> tuple[ClassInstantiationIR, list]:
        class_ir = self._known_classes[class_name]
        args: list[ValueIR] = []
        arg_preludes: list[list] = []
        for arg in expr.args:
            val, prelude = self._build_expr(arg, locals_)
            args.append(val)
            arg_preludes.append(prelude)

        all_preludes = [p for pl in arg_preludes for p in pl]

        return ClassInstantiationIR(
            ir_type=IRType.OBJ,
            class_name=class_name,
            c_class_name=class_ir.c_name,
            args=args,
            arg_preludes=arg_preludes,
        ), all_preludes

    def _build_ifexp(self, expr: ast.IfExp, locals_: list[str]) -> tuple[IfExprIR, list]:
        test, test_prelude = self._build_expr(expr.test, locals_)
        body, body_prelude = self._build_expr(expr.body, locals_)
        orelse, orelse_prelude = self._build_expr(expr.orelse, locals_)

        return IfExprIR(
            ir_type=self._get_value_ir_type(body),
            test=test,
            body=body,
            orelse=orelse,
            test_prelude=test_prelude,
            body_prelude=body_prelude,
            orelse_prelude=orelse_prelude,
        ), test_prelude + body_prelude + orelse_prelude

    def _build_list(self, expr: ast.List, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.elts:
            return ConstIR(ir_type=IRType.OBJ, value=[]), []

        items: list[ValueIR] = []
        all_preludes: list = []
        for elt in expr.elts:
            val, prelude = self._build_expr(elt, locals_)
            all_preludes.extend(prelude)
            items.append(val)

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, all_preludes + [ListNewIR(result=result, items=items)]

    def _build_tuple(self, expr: ast.Tuple, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.elts:
            return ConstIR(ir_type=IRType.OBJ, value=()), []

        items: list[ValueIR] = []
        all_preludes: list = []
        for elt in expr.elts:
            val, prelude = self._build_expr(elt, locals_)
            all_preludes.extend(prelude)
            items.append(val)

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, all_preludes + [TupleNewIR(result=result, items=items)]

    def _build_set(self, expr: ast.Set, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.elts:
            return ConstIR(ir_type=IRType.OBJ, value=set()), []

        items: list[ValueIR] = []
        all_preludes: list = []
        for elt in expr.elts:
            val, prelude = self._build_expr(elt, locals_)
            all_preludes.extend(prelude)
            items.append(val)

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, all_preludes + [SetNewIR(result=result, items=items)]

    def _build_dict(self, expr: ast.Dict, locals_: list[str]) -> tuple[ValueIR, list]:
        if not expr.keys:
            return ConstIR(ir_type=IRType.OBJ, value={}), []

        entries: list[tuple[ValueIR, ValueIR]] = []
        all_preludes: list = []
        for key, val in zip(expr.keys, expr.values):
            if key is None:
                continue
            key_val, key_prelude = self._build_expr(key, locals_)
            val_val, val_prelude = self._build_expr(val, locals_)
            all_preludes.extend(key_prelude)
            all_preludes.extend(val_prelude)
            entries.append((key_val, val_val))

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        return result, all_preludes + [DictNewIR(result=result, entries=entries)]

    def _build_subscript(self, expr: ast.Subscript, locals_: list[str]) -> tuple[SubscriptIR, list]:
        value, value_prelude = self._build_expr(expr.value, locals_)

        is_rtuple = False
        rtuple_index = None
        is_list_opt = False
        result_ir_type = IRType.OBJ

        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._rtuple_types:
                rtuple = self._rtuple_types[var_name]
                if isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, int):
                    idx = expr.slice.value
                    if 0 <= idx < rtuple.arity:
                        is_rtuple = True
                        rtuple_index = idx
                        result_ir_type = IRType.from_c_type_str(
                            rtuple.element_types[idx].to_c_type_str()
                        )
            if var_name in self._list_vars:
                is_list_opt = True
                self._uses_list_opt = True

        if isinstance(expr.slice, ast.Slice):
            slice_ir = self._build_slice(expr.slice, locals_)
            return SubscriptIR(
                ir_type=result_ir_type,
                value=value,
                slice_=slice_ir,
                is_rtuple=is_rtuple,
                rtuple_index=rtuple_index,
                is_list_opt=is_list_opt,
                value_prelude=value_prelude,
                slice_prelude=[],
            ), value_prelude

        slice_val, slice_prelude = self._build_expr(expr.slice, locals_)
        return SubscriptIR(
            ir_type=result_ir_type,
            value=value,
            slice_=slice_val,
            is_rtuple=is_rtuple,
            rtuple_index=rtuple_index,
            is_list_opt=is_list_opt,
            value_prelude=value_prelude,
            slice_prelude=slice_prelude,
        ), value_prelude + slice_prelude

    def _build_attribute(self, expr: ast.Attribute, locals_: list[str]) -> tuple[ValueIR, list]:
        if isinstance(expr.value, ast.Attribute) and isinstance(expr.value.value, ast.Name):
            module_alias = expr.value.value.id
            if module_alias in self._import_aliases:
                lib_name = self._import_aliases[module_alias]
                if lib_name in self._external_libs:
                    return self._build_clib_enum(expr, module_alias, locals_)

        # Check for local enum member access: Color.RED -> ConstIR(value=1)
        if isinstance(expr.value, ast.Name):
            enum_name = expr.value.id
            if enum_name in self._known_enums:
                enum_ir = self._known_enums[enum_name]
                member_name = expr.attr
                if member_name in enum_ir.values:
                    return ConstIR(ir_type=IRType.INT, value=enum_ir.values[member_name]), []
                # Unknown member on known enum -- return 0 as fallback
                return ConstIR(ir_type=IRType.INT, value=0), []

        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._import_aliases:
                module_name = self._import_aliases[var_name]
                if module_name in self._external_libs:
                    lib_def = self._external_libs[module_name]
                    if expr.attr in lib_def.enums:
                        return ConstIR(ir_type=IRType.OBJ, value=None), []
                self._uses_imports = True
                return ModuleAttrIR(
                    ir_type=IRType.OBJ,
                    module_name=module_name,
                    attr_name=expr.attr,
                ), []

        attr_name = expr.attr

        # Reject external access to private (__attr) members
        if self._is_private_name(attr_name):
            raise TypeError(f"Cannot access private attribute '{attr_name}' from outside its class")
        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._class_typed_params:
                class_name = self._class_typed_params[var_name]
                class_ir = self._known_classes[class_name]

                # Optional params use dynamic dispatch unless narrowed
                use_dynamic = class_ir.is_trait or var_name in self._optional_class_params

                for fld, path in class_ir.get_all_fields_with_path():
                    if fld.name == attr_name:
                        result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                        return ParamAttrIR(
                            ir_type=result_type,
                            param_name=var_name,
                            c_param_name=sanitize_name(var_name),
                            attr_name=attr_name,
                            attr_path=path,
                            class_c_name=class_ir.c_name,
                            result_type=result_type,
                            is_trait_type=use_dynamic,
                        ), []

                return ParamAttrIR(
                    ir_type=IRType.OBJ,
                    param_name=var_name,
                    c_param_name=sanitize_name(var_name),
                    attr_name=attr_name,
                    attr_path=attr_name,
                    class_c_name=class_ir.c_name,
                    result_type=IRType.OBJ,
                    is_trait_type=use_dynamic,
                ), []
            elif var_name in locals_:
                # Handle object-typed params (not a known class)
                return ParamAttrIR(
                    ir_type=IRType.OBJ,
                    param_name=var_name,
                    c_param_name=sanitize_name(var_name),
                    attr_name=attr_name,
                    attr_path=attr_name,
                    class_c_name="",
                    result_type=IRType.OBJ,
                    is_trait_type=True,  # Always use dynamic lookup
                ), []

        if isinstance(expr.value, ast.Attribute):
            base_value, base_prelude = self._build_attribute(expr.value, locals_)
            base_class_name = self._get_class_type_of_attr(expr.value)

            if base_class_name and base_class_name in self._known_classes:
                base_class_ir = self._known_classes[base_class_name]

                for fld in base_class_ir.get_all_fields():
                    if fld.name == attr_name:
                        result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                        temp_name = self._fresh_temp()
                        result_temp = TempIR(ir_type=result_type, name=temp_name)

                        attr_access = AttrAccessIR(
                            result=result_temp,
                            obj=base_value,
                            attr_name=attr_name,
                            class_c_name=base_class_ir.c_name,
                            result_type=result_type,
                        )

                        return result_temp, base_prelude + [attr_access]

        if isinstance(expr.value, ast.Subscript):
            element_class_name = None
            if isinstance(expr.value.value, ast.Name):
                var_name = expr.value.value.id
                if var_name in self._container_element_types:
                    element_class_name = self._container_element_types[var_name]

            if element_class_name and element_class_name in self._known_classes:
                subscript_value, subscript_prelude = self._build_expr(expr.value, locals_)
                element_class_ir = self._known_classes[element_class_name]
                for fld in element_class_ir.get_all_fields():
                    if fld.name == attr_name:
                        result_type = IRType.from_c_type_str(fld.c_type.to_c_type_str())
                        temp_name = self._fresh_temp()
                        result_temp = TempIR(ir_type=result_type, name=temp_name)
                        attr_access = AttrAccessIR(
                            result=result_temp,
                            obj=subscript_value,
                            attr_name=attr_name,
                            class_c_name=element_class_ir.c_name,
                            result_type=result_type,
                        )
                        return result_temp, subscript_prelude + [attr_access]

        return ConstIR(ir_type=IRType.OBJ, value=None), []

    def _build_clib_enum(
        self, expr: ast.Attribute, module_alias: str, locals_: list[str]
    ) -> tuple[ValueIR, list]:
        del locals_
        from .ir import CLibEnumIR

        if not isinstance(expr.value, ast.Attribute):
            return ConstIR(ir_type=IRType.INT, value=0), []

        lib_name = self._import_aliases[module_alias]
        lib_def = self._external_libs[lib_name]
        self._uses_external_libs.add(lib_name)

        enum_class_name = expr.value.attr
        member_name = expr.attr

        enum_def = lib_def.enums.get(enum_class_name)
        if enum_def and member_name in enum_def.values:
            c_value = enum_def.values[member_name]
            return CLibEnumIR(
                ir_type=IRType.INT,
                lib_name=lib_name,
                enum_class=enum_class_name,
                member_name=member_name,
                c_enum_value=c_value,
            ), []

        return ConstIR(ir_type=IRType.INT, value=0), []

    def _build_list_comp(self, expr: ast.ListComp, locals_: list[str]) -> tuple[ValueIR, list]:
        """Build IR for list comprehension: [expr for var in iterable] or [expr for var in iterable if cond]."""
        if not expr.generators:
            return ConstIR(ir_type=IRType.OBJ, value=[]), []

        # We only support single generator for now
        gen = expr.generators[0]

        if not isinstance(gen.target, ast.Name):
            # Only support simple variable targets
            return ConstIR(ir_type=IRType.OBJ, value=[]), []

        loop_var = gen.target.id
        c_loop_var = sanitize_name(loop_var)

        # Track the loop variable
        is_new_var = loop_var not in locals_
        if is_new_var:
            locals_.append(loop_var)
            self._var_types[loop_var] = "mp_obj_t"

        # Build iterable expression
        iterable, iter_prelude = self._build_expr(gen.iter, locals_)

        # Check if iterable is range() for optimization
        is_range = False
        range_start: ValueIR | None = None
        range_end: ValueIR | None = None
        range_step: ValueIR | None = None

        if (
            isinstance(gen.iter, ast.Call)
            and isinstance(gen.iter.func, ast.Name)
            and gen.iter.func.id == "range"
        ):
            is_range = True
            range_args = gen.iter.args
            if len(range_args) == 1:
                range_start = ConstIR(ir_type=IRType.INT, value=0)
                range_end, _ = self._build_expr(range_args[0], locals_)
            elif len(range_args) == 2:
                range_start, _ = self._build_expr(range_args[0], locals_)
                range_end, _ = self._build_expr(range_args[1], locals_)
            elif len(range_args) == 3:
                range_start, _ = self._build_expr(range_args[0], locals_)
                range_end, _ = self._build_expr(range_args[1], locals_)
                range_step, _ = self._build_expr(range_args[2], locals_)
            # For range-based comprehensions, loop var is int
            self._var_types[loop_var] = "mp_int_t"

        # Build element expression
        element, element_prelude = self._build_expr(expr.elt, locals_)

        # Build condition if present
        condition: ValueIR | None = None
        condition_prelude: list = []
        if gen.ifs:
            # Combine multiple conditions with AND
            cond_parts = []
            for if_expr in gen.ifs:
                cond, cond_pre = self._build_expr(if_expr, locals_)
                cond_parts.append(cond)
                condition_prelude.extend(cond_pre)
            # For now, just use the first condition (most common case)
            condition = cond_parts[0] if len(cond_parts) == 1 else cond_parts[0]

        # Create result temp
        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)

        # Create ListCompIR instruction
        list_comp = ListCompIR(
            result=result,
            loop_var=loop_var,
            c_loop_var=c_loop_var,
            iterable=iterable,
            element=element,
            condition=condition,
            iter_prelude=iter_prelude,
            element_prelude=element_prelude,
            condition_prelude=condition_prelude,
            is_range=is_range,
            range_start=range_start,
            range_end=range_end,
            range_step=range_step,
        )

        return result, [list_comp]

    def _resolve_class_name_from_type_str(self, type_str: str) -> str | None:
        """Extract a known class name from a type string, handling Optional/union.

        Handles:
        - Direct class names: 'WidgetDiff'
        - Optional types: 'WidgetDiff | None'
        - Dotted optional types: 'pkg.WidgetDiff | None'
        - Dotted names: 'module.ClassName'
        """
        # Direct match
        if type_str in self._known_classes:
            return type_str

        # First, strip ' | None' or 'None | ' to get the base type
        base_type = type_str
        if "|" in type_str:
            parts = [p.strip() for p in type_str.split("|")]
            non_none = [p for p in parts if p != "None"]
            if len(non_none) == 1:
                base_type = non_none[0]
                # Check if the unwrapped type matches directly
                if base_type in self._known_classes:
                    return base_type

        # Handle dotted names: 'module.ClassName' or 'pkg.module.ClassName' -> 'ClassName'
        if "." in base_type:
            short = base_type.rsplit(".", 1)[-1]
            if short in self._known_classes:
                return short

        return None

    def _get_class_type_of_attr(self, expr: ast.Attribute) -> str | None:
        """Get the class type name that an attribute access returns."""
        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name in self._class_typed_params:
                class_name = self._class_typed_params[var_name]
                if class_name in self._known_classes:
                    class_ir = self._known_classes[class_name]
                    for fld in class_ir.get_all_fields():
                        if fld.name == expr.attr:
                            return self._resolve_class_name_from_type_str(fld.py_type)
        elif isinstance(expr.value, ast.Attribute):
            parent_class = self._get_class_type_of_attr(expr.value)
            if parent_class and parent_class in self._known_classes:
                class_ir = self._known_classes[parent_class]
                for fld in class_ir.get_all_fields():
                    if fld.name == expr.attr:
                        return self._resolve_class_name_from_type_str(fld.py_type)
        return None

    def _get_method_attr_class_type(self, expr: ast.Attribute, class_ir: ClassIR) -> str | None:
        """Get the class type name of an attribute in method context (handles self.attr)."""
        if isinstance(expr.value, ast.Name):
            var_name = expr.value.id
            if var_name == "self":
                for fld in class_ir.get_all_fields():
                    if fld.name == expr.attr:
                        return self._resolve_class_name_from_type_str(fld.py_type)
            elif var_name in self._class_typed_params:
                param_class_name = self._class_typed_params[var_name]
                if param_class_name in self._known_classes:
                    param_class_ir = self._known_classes[param_class_name]
                    for fld in param_class_ir.get_all_fields():
                        if fld.name == expr.attr:
                            return self._resolve_class_name_from_type_str(fld.py_type)
        elif isinstance(expr.value, ast.Attribute):
            parent_type = self._get_method_attr_class_type(expr.value, class_ir)
            if parent_type and parent_type in self._known_classes:
                parent_ir = self._known_classes[parent_type]
                for fld in parent_ir.get_all_fields():
                    if fld.name == expr.attr:
                        return self._resolve_class_name_from_type_str(fld.py_type)
        return None

    def _build_slice(self, slice_node: ast.Slice, locals_: list[str]) -> SliceIR:
        lower = None
        upper = None
        step = None
        if slice_node.lower is not None:
            lower, _ = self._build_expr(slice_node.lower, locals_)
        if slice_node.upper is not None:
            upper, _ = self._build_expr(slice_node.upper, locals_)
        if slice_node.step is not None:
            step, _ = self._build_expr(slice_node.step, locals_)
        return SliceIR(ir_type=IRType.OBJ, lower=lower, upper=upper, step=step)

    def _get_value_ir_type(self, value: ValueIR) -> IRType:
        return value.ir_type

    def _get_mypy_func_type(self, func_name: str) -> "FunctionTypeInfo | None":
        if self._mypy_types is None:
            return None
        return self._mypy_types.functions.get(func_name)

    def _get_mypy_class_type(self, class_name: str) -> "ClassTypeInfo | None":
        if self._mypy_types is None:
            return None
        return self._mypy_types.classes.get(class_name)

    def _get_mypy_method_type(self, class_name: str, method_name: str) -> "FunctionTypeInfo | None":
        mypy_class = self._get_mypy_class_type(class_name)
        if mypy_class is None:
            return None
        for method in mypy_class.methods:
            if method.name == method_name:
                return method
        return None

    def _mypy_type_to_c_type(self, mypy_type: str) -> str:
        # Handle Literal types from mypy: "Literal[3]" -> "int"
        if mypy_type.startswith("Literal["):
            return self._erase_mypy_literal_to_c_type(mypy_type)
        type_map = {
            "int": "mp_int_t",
            "float": "mp_float_t",
            "bool": "bool",
            "str": "mp_obj_t",
            "None": "void",
            "list": "mp_obj_t",
            "dict": "mp_obj_t",
            "tuple": "mp_obj_t",
            "set": "mp_obj_t",
            "object": "mp_obj_t",
            "Any": "mp_obj_t",
        }
        base_type = mypy_type.split("[")[0].strip()
        # Resolve TypeVar names
        resolved = self._resolve_typevar(base_type)
        if resolved is not None:
            base_type = resolved
        return type_map.get(base_type, "mp_obj_t")

    def _mypy_type_to_py_type(self, mypy_type: str) -> str:
        # Handle Literal types from mypy: "Literal[3]" -> "int"
        if mypy_type.startswith("Literal["):
            return self._erase_mypy_literal_to_py_type(mypy_type)
        base_type = mypy_type.split("[")[0].strip()
        # Resolve TypeVar names
        resolved = self._resolve_typevar(base_type)
        if resolved is not None:
            return resolved
        if base_type in ("int", "float", "bool", "str", "list", "dict", "tuple", "set", "None"):
            return base_type
        if "." in base_type:
            return base_type.split(".")[-1]
        return base_type if base_type else "object"

    def _erase_mypy_literal_to_py_type(self, mypy_type: str) -> str:
        """Erase mypy Literal string to Python type: 'Literal[3]' -> 'int'."""
        # Extract value between Literal[ and ]
        inner = mypy_type[len("Literal["):-1].strip() if mypy_type.endswith("]") else ""
        if not inner:
            return "object"
        # Handle union literals: Literal[1, 2, 3] - use first value
        first_val = inner.split(",")[0].strip()
        if first_val in ("True", "False"):
            return "bool"
        if first_val == "None":
            return "None"
        # Try int
        try:
            int(first_val)
            return "int"
        except ValueError:
            pass
        # Try float
        try:
            float(first_val)
            return "float"
        except ValueError:
            pass
        # Must be a string literal (possibly quoted)
        return "str"

    def _erase_mypy_literal_to_c_type(self, mypy_type: str) -> str:
        """Erase mypy Literal string to C type: 'Literal[3]' -> 'mp_int_t'."""
        py_type = self._erase_mypy_literal_to_py_type(mypy_type)
        c_type_map = {
            "int": "mp_int_t",
            "float": "mp_float_t",
            "bool": "bool",
            "str": "mp_obj_t",
            "None": "void",
        }
        return c_type_map.get(py_type, "mp_obj_t")

    def _erase_literal_type(self, annotation: ast.expr) -> ast.expr:
        """Erase Literal[X] to its underlying type.

        Literal[3] -> int, Literal["hello"] -> str, Literal[True] -> bool.
        Following mypyc's strategy of erasing Literal to the underlying type.
        """
        if not isinstance(annotation, ast.Subscript):
            return annotation
        if not isinstance(annotation.value, ast.Name):
            return annotation
        if annotation.value.id != "Literal":
            return annotation

        # Extract the literal value from the slice
        literal_val = annotation.slice
        # Handle Literal[3], Literal["hello"], Literal[True], Literal[None]
        if isinstance(literal_val, ast.Constant):
            val = literal_val.value
            if isinstance(val, bool):
                return ast.Name(id="bool", ctx=ast.Load())
            elif isinstance(val, int):
                return ast.Name(id="int", ctx=ast.Load())
            elif isinstance(val, float):
                return ast.Name(id="float", ctx=ast.Load())
            elif isinstance(val, str):
                return ast.Name(id="str", ctx=ast.Load())
            elif val is None:
                return ast.Constant(value=None)
        # Handle Literal[1, 2, 3] (union of literals) - erase to first element's type
        elif isinstance(literal_val, ast.Tuple) and literal_val.elts:
            first = literal_val.elts[0]
            if isinstance(first, ast.Constant):
                val = first.value
                if isinstance(val, bool):
                    return ast.Name(id="bool", ctx=ast.Load())
                elif isinstance(val, int):
                    return ast.Name(id="int", ctx=ast.Load())
                elif isinstance(val, float):
                    return ast.Name(id="float", ctx=ast.Load())
                elif isinstance(val, str):
                    return ast.Name(id="str", ctx=ast.Load())
        # Fallback: return object for unrecognized literal types
        return ast.Name(id="object", ctx=ast.Load())

    def _resolve_typevar(self, name: str) -> str | None:
        """Resolve a TypeVar name to its bound type string.

        Returns the bound type (e.g., "int") or "object" for unbounded TypeVars.
        Returns None if the name is not a known TypeVar.
        """
        return self._typevar_bounds.get(name)

    def _scan_typevars(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Scan function for TypeVar declarations and PEP 695 type params.

        Populates self._typevar_bounds with mappings from TypeVar name
        to bound type. Unbounded TypeVars map to "object".
        """
        # PEP 695 type_params: def f[T](x: T) -> T, def f[T: int](x: T) -> T
        if hasattr(node, "type_params"):
            for tp in node.type_params:
                if isinstance(tp, ast.TypeVar):
                    if tp.bound is not None and isinstance(tp.bound, ast.Name):
                        self._typevar_bounds[tp.name] = tp.bound.id
                    else:
                        self._typevar_bounds[tp.name] = "object"
                    self._pep695_typevars.add(tp.name)

    def register_typevar(self, node: ast.Assign) -> bool:
        """Register a classic TypeVar assignment: T = TypeVar('T', bound=int).

        Returns True if this was a TypeVar assignment, False otherwise.
        """
        if len(node.targets) != 1:
            return False
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return False
        if not isinstance(node.value, ast.Call):
            return False
        func = node.value.func
        if not isinstance(func, ast.Name) or func.id != "TypeVar":
            return False

        tv_name = target.id
        # Check for bound= keyword argument
        bound_type = "object"
        for kw in node.value.keywords:
            if kw.arg == "bound" and isinstance(kw.value, ast.Name):
                bound_type = kw.value.id
                break
        self._typevar_bounds[tv_name] = bound_type
        return True

    def _annotation_to_c_type(self, annotation: ast.expr | None) -> str:
        if annotation is None:
            return "mp_obj_t"
        # Erase Literal types first: Literal[3] -> int
        annotation = self._erase_literal_type(annotation)
        if isinstance(annotation, ast.Name):
            # Resolve TypeVar names: T -> bound type
            resolved = self._resolve_typevar(annotation.id)
            if resolved is not None:
                name = resolved
            else:
                name = annotation.id
            type_map = {
                "int": "mp_int_t",
                "float": "mp_float_t",
                "bool": "bool",
                "str": "mp_obj_t",
                "None": "void",
                "list": "mp_obj_t",
                "dict": "mp_obj_t",
                "tuple": "mp_obj_t",
                "set": "mp_obj_t",
                "object": "mp_obj_t",
                "Any": "mp_obj_t",
            }
            return type_map.get(name, "mp_obj_t")
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id == "tuple":
                    rtuple = RTuple.from_annotation(annotation)
                    if rtuple is not None:
                        self._used_rtuples.add(rtuple)
                        return rtuple.get_c_struct_name()
                if annotation.value.id in ("list", "dict", "tuple", "set"):
                    return "mp_obj_t"
        return "mp_obj_t"

    def _annotation_to_py_type(self, annotation: ast.expr | None) -> str:
        if annotation is None:
            return "object"
        # Erase Literal types first: Literal[3] -> int
        annotation = self._erase_literal_type(annotation)
        if isinstance(annotation, ast.Name):
            # Resolve TypeVar names: T -> bound type
            resolved = self._resolve_typevar(annotation.id)
            if resolved is not None:
                return resolved
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return annotation.value.id
        elif isinstance(annotation, ast.Constant):
            if annotation.value is None:
                return "None"
        return "object"

    def _extract_class_from_annotation(self, annotation: ast.expr | None) -> str | None:
        if annotation is None:
            return None
        if isinstance(annotation, ast.Name):
            name = annotation.id
            return name if name in self._known_classes else None
        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            # Only handle X | None (Optional) unions -- not arbitrary X | Y
            left_is_none = (
                isinstance(annotation.left, ast.Constant) and annotation.left.value is None
            )
            right_is_none = (
                isinstance(annotation.right, ast.Constant) and annotation.right.value is None
            )
            if left_is_none and not right_is_none:
                return self._extract_class_from_annotation(annotation.right)
            if right_is_none and not left_is_none:
                return self._extract_class_from_annotation(annotation.left)
            # For all other unions (e.g., Point | int, Point | OtherClass), do not infer
            return None
        if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
            name = annotation.value
            return name if name in self._known_classes else None
        return None

    def _is_optional_class_annotation(self, annotation: ast.expr | None) -> bool:
        """Check if annotation is X | None where X is a known class."""
        if not isinstance(annotation, ast.BinOp) or not isinstance(annotation.op, ast.BitOr):
            return False
        # Check if one side is None and the other is a known class
        left_is_none = isinstance(annotation.left, ast.Constant) and annotation.left.value is None
        right_is_none = (
            isinstance(annotation.right, ast.Constant) and annotation.right.value is None
        )
        if left_is_none:
            return self._extract_class_from_annotation(annotation.right) is not None
        if right_is_none:
            return self._extract_class_from_annotation(annotation.left) is not None
        return False

    def _extract_container_element_class(self, annotation: ast.expr | None) -> str | None:
        if not isinstance(annotation, ast.Subscript):
            return None
        if not isinstance(annotation.value, ast.Name):
            return None
        container_type = annotation.value.id
        if container_type not in ("tuple", "list"):
            return None
        if container_type == "tuple" and isinstance(annotation.slice, ast.Tuple):
            elts = annotation.slice.elts
            if len(elts) >= 1 and isinstance(elts[0], ast.Name):
                elem_name = elts[0].id
                if elem_name in self._known_classes:
                    return elem_name
        elif container_type == "list" and isinstance(annotation.slice, ast.Name):
            elem_name = annotation.slice.id
            if elem_name in self._known_classes:
                return elem_name
        return None

    def _c_type_to_py_type(self, c_type: str) -> str:
        type_map = {
            "mp_int_t": "int",
            "mp_float_t": "float",
            "bool": "bool",
            "void": "None",
            "mp_obj_t": "object",
        }
        return type_map.get(c_type, "object")

    def _is_list_annotation(self, annotation: ast.expr | None) -> tuple[bool, str | None]:
        """Check if annotation is a list type and extract element type if present.

        Returns (is_list, element_type) where element_type is "int", "float", or None.
        """
        if annotation is None:
            return False, None
        if isinstance(annotation, ast.Name) and annotation.id == "list":
            return True, None
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name) and annotation.value.id == "list":
                element_type = None
                if isinstance(annotation.slice, ast.Name):
                    if annotation.slice.id in ("int", "float"):
                        element_type = annotation.slice.id
                return True, element_type
        return False, None

    def _try_parse_rtuple(self, annotation: ast.expr | None) -> RTuple | None:
        if isinstance(annotation, ast.Subscript):
            return RTuple.from_annotation(annotation)
        return None

    def _parse_defaults(self, args: ast.arguments, num_params: int) -> dict[int, DefaultArg]:
        """Parse default argument values from AST.

        AST stores defaults aligned to the *last* N parameters.
        For `def f(a, b=1, c=2)`, args.defaults = [1, 2] for params at index 1, 2.
        """
        defaults: dict[int, DefaultArg] = {}
        num_defaults = len(args.defaults)
        if num_defaults == 0:
            return defaults

        first_default_idx = num_params - num_defaults
        for i, default_ast in enumerate(args.defaults):
            param_idx = first_default_idx + i
            default_value, c_expr = self._eval_default_value(default_ast)
            defaults[param_idx] = DefaultArg(value=default_value, c_expr=c_expr)

        return defaults

    def _parse_star_args(self, args: ast.arguments) -> tuple[ParamIR | None, ParamIR | None]:
        star_args = None
        star_kwargs = None

        if args.vararg:
            star_args = ParamIR(
                name=args.vararg.arg,
                c_type=CType.MP_OBJ_T,
                kind=ArgKind.ARG_STAR,
            )

        if args.kwarg:
            star_kwargs = ParamIR(
                name=args.kwarg.arg,
                c_type=CType.MP_OBJ_T,
                kind=ArgKind.ARG_STAR2,
            )

        return star_args, star_kwargs

    @property
    def used_external_libs(self) -> set[str]:
        return self._uses_external_libs

    def _eval_default_value(self, node: ast.expr) -> tuple[object, str | None]:
        """Evaluate a default argument value at compile time.

        Returns (python_value, c_expression) where c_expression is used for code gen.
        """
        if isinstance(node, ast.Constant):
            val = node.value
            if val is None:
                return None, "mp_const_none"
            elif isinstance(val, bool):
                return val, "mp_const_true" if val else "mp_const_false"
            elif isinstance(val, int):
                return val, f"mp_obj_new_int({val})"
            elif isinstance(val, float):
                return val, f"mp_obj_new_float({val})"
            elif isinstance(val, str):
                escaped = val.replace("\\", "\\\\").replace('"', '\\"')
                return val, f'mp_obj_new_str("{escaped}", {len(val)})'
            return val, None

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Constant):
                val = node.operand.value
                if isinstance(val, int):
                    return -val, f"mp_obj_new_int({-val})"
                elif isinstance(val, float):
                    return -val, f"mp_obj_new_float({-val})"

        if isinstance(node, ast.List) and len(node.elts) == 0:
            return [], "mp_obj_new_list(0, NULL)"

        if isinstance(node, ast.Dict) and len(node.keys) == 0:
            return {}, "mp_obj_new_dict(0)"

        if isinstance(node, ast.Tuple) and len(node.elts) == 0:
            return (), "mp_const_empty_tuple"

        if isinstance(node, ast.Set) and len(node.elts) == 0:
            return set(), "mp_obj_new_set(0, NULL)"

        return None, None

    # -------------------------------------------------------------------------
    # Class Building
    # -------------------------------------------------------------------------

    def build_class(self, node: ast.ClassDef) -> ClassIR:
        """Build ClassIR from ast.ClassDef."""
        class_name = node.name
        c_class_name = f"{self.c_name}_{sanitize_name(class_name)}"

        # Check for dataclass, @final, and @trait decorators
        # Supports: @trait, @mypy_extensions.trait, from mypy_extensions import trait
        is_dataclass = False
        is_final_class = False
        is_trait = False
        dataclass_info = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "dataclass":
                    is_dataclass = True
                    dataclass_info = DataclassInfo()
                elif decorator.id == "final":
                    is_final_class = True
                elif decorator.id == "trait":
                    is_trait = True
            elif isinstance(decorator, ast.Attribute):
                # Handle @mypy_extensions.trait
                if (
                    isinstance(decorator.value, ast.Name)
                    and decorator.value.id == "mypy_extensions"
                    and decorator.attr == "trait"
                ):
                    is_trait = True
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass":
                    is_dataclass = True
                    dataclass_info = DataclassInfo()
                    for kw in decorator.keywords:
                        if kw.arg == "frozen" and isinstance(kw.value, ast.Constant):
                            dataclass_info.frozen = bool(kw.value.value)
                        elif kw.arg == "eq" and isinstance(kw.value, ast.Constant):
                            dataclass_info.eq = bool(kw.value.value)
                        elif kw.arg == "repr" and isinstance(kw.value, ast.Constant):
                            dataclass_info.repr_ = bool(kw.value.value)

        # Process base classes: separate concrete base from traits
        # Following mypyc: only ONE concrete base allowed, multiple traits allowed
        base_name: str | None = None
        trait_names: list[str] = []

        for base in node.bases:
            if isinstance(base, ast.Name):
                base_id = base.id
                if base_id in ("object", "Object"):
                    continue  # Skip object base
                # Check if this base is a known trait
                if base_id in self._known_classes:
                    known_base = self._known_classes[base_id]
                    if known_base.is_trait:
                        trait_names.append(base_id)
                    elif base_name is None:
                        base_name = base_id
                    else:
                        # Multiple concrete bases - this is an error
                        # For now, just use the first one (will be caught by type checker)
                        pass
                elif base_name is None:
                    # Unknown base - assume concrete (will be resolved later)
                    base_name = base_id
                else:
                    # Could be a trait defined later, add to trait_names
                    trait_names.append(base_id)

        class_ir = ClassIR(
            name=class_name,
            c_name=c_class_name,
            module_name=self.module_name,
            base_name=base_name,
            trait_names=trait_names,
            is_trait=is_trait,
            is_dataclass=is_dataclass,
            dataclass_info=dataclass_info,
            is_final_class=is_final_class,
            ast_node=node,
        )

        # Resolve base class if known
        if base_name and base_name in self._known_classes:
            class_ir.base = self._known_classes[base_name]

        # Resolve traits if known
        for trait_name in trait_names:
            if trait_name in self._known_classes:
                trait = self._known_classes[trait_name]
                if trait.is_trait:
                    class_ir.traits.append(trait)

        # Register in known classes BEFORE parsing body
        # so that methods can recognize class-typed local variables
        self._known_classes[class_name] = class_ir

        # Parse class body
        self._parse_class_body(node, class_ir)

        # @final class: devirtualize ALL methods (no vtable needed)
        if is_final_class:
            class_ir.virtual_methods.clear()
            for method_ir in class_ir.methods.values():
                method_ir.is_virtual = False
                method_ir.is_final = True

        if is_dataclass and dataclass_info:
            dataclass_info.fields = list(class_ir.fields)

        return class_ir

    def build_enum(self, node: ast.ClassDef) -> EnumIR:
        """Build EnumIR from ast.ClassDef that inherits from IntEnum/Enum.

        Parses enum members as integer constants. Supports:
        - Simple assignments: RED = 1
        - Annotated assignments: RED: int = 1
        - Negative values: OFFSET = -10
        - Bitwise expressions: READ = 1 << 0
        """
        enum_name = node.name
        c_enum_name = f"{self.c_name}_{sanitize_name(enum_name)}"

        docstring = None
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            docstring = node.body[0].value.value

        enum_ir = EnumIR(
            name=enum_name,
            c_name=c_enum_name,
            module_name=self.module_name,
            docstring=docstring,
        )

        for stmt in node.body:
            # Handle: NAME = value
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
                if isinstance(target, ast.Name) and stmt.value is not None:
                    val = self._eval_enum_value(stmt.value, enum_ir.values)
                    if val is not None:
                        enum_ir.values[target.id] = val
            # Handle: NAME: int = value
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                if stmt.value is not None:
                    val = self._eval_enum_value(stmt.value, enum_ir.values)
                    if val is not None:
                        enum_ir.values[stmt.target.id] = val

        self._known_enums[enum_name] = enum_ir
        return enum_ir

    def _eval_enum_value(
        self, node: ast.expr, resolved: dict[str, int] | None = None
    ) -> int | None:
        """Evaluate a constant integer expression for an enum value.

        Supports: int literals, negative ints, bitwise shift (1 << N),
        bitwise OR (a | b), basic arithmetic, and references to
        previously-defined enum members (e.g. ALL = READ | WRITE).
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        # Resolve references to previously-defined enum members
        if isinstance(node, ast.Name) and resolved and node.id in resolved:
            return resolved[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            if isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, int):
                return -node.operand.value
        if isinstance(node, ast.BinOp):
            left = self._eval_enum_value(node.left, resolved)
            right = self._eval_enum_value(node.right, resolved)
            if left is not None and right is not None:
                if isinstance(node.op, ast.LShift):
                    return left << right
                if isinstance(node.op, ast.RShift):
                    return left >> right
                if isinstance(node.op, ast.BitOr):
                    return left | right
                if isinstance(node.op, ast.BitAnd):
                    return left & right
                if isinstance(node.op, ast.BitXor):
                    return left ^ right
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
        return None

    @staticmethod
    def is_enum_class(node: ast.ClassDef) -> bool:
        """Check if a class definition is an enum (inherits from IntEnum, Enum, etc.)."""
        enum_base_names = {"IntEnum", "Enum", "Flag", "IntFlag"}
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in enum_base_names:
                return True
            # Handle enum.IntEnum, enum.Enum
            if (
                isinstance(base, ast.Attribute)
                and isinstance(base.value, ast.Name)
                and base.value.id == "enum"
                and base.attr in enum_base_names
            ):
                return True
        return False

    def _parse_class_body(self, node: ast.ClassDef, class_ir: ClassIR) -> None:
        """Parse class body to extract fields and methods."""
        mypy_class = self._get_mypy_class_type(class_ir.name)
        mypy_field_types: dict[str, str] = {}
        if mypy_class:
            mypy_field_types = {name: ftype for name, ftype in mypy_class.fields}

        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id

                # Detect Final[type] or bare Final annotation
                is_final_field = False
                inner_annotation = stmt.annotation
                if isinstance(stmt.annotation, ast.Subscript):
                    if (
                        isinstance(stmt.annotation.value, ast.Name)
                        and stmt.annotation.value.id == "Final"
                    ):
                        is_final_field = True
                        inner_annotation = stmt.annotation.slice
                elif isinstance(stmt.annotation, ast.Name) and stmt.annotation.id == "Final":
                    is_final_field = True
                    inner_annotation = None  # type inferred from value

                if field_name in mypy_field_types:
                    mypy_py = self._mypy_type_to_py_type(mypy_field_types[field_name])
                    # When mypy reports 'Any' (unresolved import), fall back to
                    # the annotation which may name a known cross-module class.
                    if mypy_py in ("Any", "object") and inner_annotation is not None:
                        ann_py = self._annotation_to_py_type(inner_annotation)
                        # Only prefer annotation if it resolves to a known class
                        if ann_py in self._known_classes:
                            py_type = ann_py
                        else:
                            py_type = mypy_py
                    else:
                        py_type = mypy_py
                    c_type = CType.from_python_type(py_type)
                elif inner_annotation is not None:
                    py_type = self._annotation_to_py_type(inner_annotation)
                    c_type = CType.from_python_type(py_type)
                else:
                    # Bare Final without type -- infer from value
                    py_type = "object"
                    if stmt.value and isinstance(stmt.value, ast.Constant):
                        val = stmt.value.value
                        if isinstance(val, bool):
                            py_type = "bool"
                        elif isinstance(val, int):
                            py_type = "int"
                        elif isinstance(val, float):
                            py_type = "float"
                        elif isinstance(val, str):
                            py_type = "str"
                    c_type = CType.from_python_type(py_type)

                elem_class = self._extract_container_element_class(inner_annotation)
                if elem_class:
                    self._class_field_element_types[(class_ir.name, field_name)] = elem_class

                has_default = stmt.value is not None
                default_value = None
                final_value = None
                if has_default and isinstance(stmt.value, ast.Constant):
                    default_value = stmt.value.value
                    if is_final_field:
                        final_value = stmt.value.value

                field_ir = FieldIR(
                    name=field_name,
                    py_type=py_type,
                    c_type=c_type,
                    has_default=has_default,
                    default_value=default_value,
                    default_ast=stmt.value,
                    is_final=is_final_field,
                    final_value=final_value,
                )
                class_ir.fields.append(field_ir)

            elif isinstance(stmt, ast.FunctionDef):
                self._parse_method(stmt, class_ir)

    def _parse_method(self, node: ast.FunctionDef, class_ir: ClassIR) -> None:
        """Parse a method definition and add to class IR."""
        method_name = node.name
        c_method_name = f"{class_ir.c_name}_{sanitize_name(method_name)}"

        is_static = False
        is_classmethod = False
        is_property = False
        is_final = False
        property_name: str | None = None
        is_property_setter = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id == "staticmethod":
                    is_static = True
                elif decorator.id == "classmethod":
                    is_classmethod = True
                elif decorator.id == "property":
                    is_property = True
                elif decorator.id == "final":
                    is_final = True
            elif (
                isinstance(decorator, ast.Attribute)
                and decorator.attr == "setter"
                and isinstance(decorator.value, ast.Name)
            ):
                is_property = True
                is_property_setter = True
                property_name = decorator.value.id
                c_method_name = f"{class_ir.c_name}_{sanitize_name(property_name)}_setter"
        mypy_method = self._get_mypy_method_type(class_ir.name, method_name)
        mypy_param_types: dict[str, str] = {}
        mypy_return_type: str | None = None
        if mypy_method:
            mypy_param_types = {name: ptype for name, ptype in mypy_method.params}
            mypy_return_type = mypy_method.return_type

        params: list[tuple[str, CType]] = []
        method_args = node.args.args if (is_static or is_classmethod) else node.args.args[1:]
        for arg in method_args:
            if arg.arg in mypy_param_types:
                mypy_py = self._mypy_type_to_py_type(mypy_param_types[arg.arg])
                # Fall back to annotation when mypy says 'Any' (unresolved import)
                if mypy_py in ("Any", "object") and arg.annotation is not None:
                    ann_py = self._annotation_to_py_type(arg.annotation)
                    if ann_py in self._known_classes:
                        py_type = ann_py
                    else:
                        py_type = mypy_py
                else:
                    py_type = mypy_py
                c_type = CType.from_python_type(py_type)
            else:
                py_type = (
                    self._annotation_to_py_type(arg.annotation) if arg.annotation else "object"
                )
                c_type = CType.from_python_type(py_type)
            params.append((arg.arg, c_type))

        if mypy_return_type:
            py_type = self._mypy_type_to_py_type(mypy_return_type)
            return_type = CType.from_python_type(py_type)
            if py_type == "None":
                return_type = CType.VOID
        else:
            return_type = CType.VOID
            if node.returns:
                py_type = self._annotation_to_py_type(node.returns)
                return_type = CType.from_python_type(py_type)
                if py_type == "None":
                    return_type = CType.VOID

        is_special = method_name.startswith("__") and method_name.endswith("__")
        is_private = method_name.startswith("__") and not method_name.endswith("__")
        is_virtual = (not is_static and not is_classmethod and not is_property) and (
            not is_special or method_name in ("__len__", "__getitem__", "__setitem__")
        )
        # Private (__method) or @final methods cannot be overridden => not virtual
        if is_private or is_final:
            is_virtual = False

        # Parse default arguments for methods
        # For methods, defaults are aligned to method params (excluding self)
        defaults = self._parse_defaults(node.args, len(params))
        method_ir = MethodIR(
            name=method_name,
            c_name=c_method_name,
            params=params,
            return_type=return_type,
            body_ast=node,
            is_virtual=is_virtual,
            is_static=is_static,
            is_classmethod=is_classmethod,
            is_property=is_property,
            is_special=is_special,
            is_private=is_private,
            is_final=is_final,
            docstring=ast.get_docstring(node),
            defaults=defaults,
        )

        if is_property and is_property_setter and property_name is not None:
            class_ir.methods[f"_prop_{property_name}_setter"] = method_ir
            if property_name in class_ir.properties:
                class_ir.properties[property_name].setter = method_ir
        else:
            class_ir.methods[method_name] = method_ir
            if is_property:
                if method_name in class_ir.properties:
                    class_ir.properties[method_name].getter = method_ir
                else:
                    class_ir.properties[method_name] = PropertyInfo(
                        name=method_name, getter=method_ir
                    )

        if is_virtual and not is_special:
            class_ir.virtual_methods.append(method_name)

        if method_name == "__init__":
            class_ir.has_init = True
        elif method_name == "__repr__":
            class_ir.has_repr = True
        elif method_name == "__str__":
            class_ir.has_str = True
        elif method_name == "__eq__":
            class_ir.has_eq = True
        elif method_name == "__ne__":
            class_ir.has_ne = True
        elif method_name == "__lt__":
            class_ir.has_lt = True
        elif method_name == "__le__":
            class_ir.has_le = True
        elif method_name == "__gt__":
            class_ir.has_gt = True
        elif method_name == "__ge__":
            class_ir.has_ge = True
        elif method_name == "__hash__":
            class_ir.has_hash = True
        elif method_name == "__iter__":
            class_ir.has_iter = True
        elif method_name == "__next__":
            class_ir.has_next = True

    def build_method_body(
        self, method_ir: MethodIR, class_ir: ClassIR, native: bool = False
    ) -> list[StmtIR]:
        """Build IR for a method body with class context.

        Args:
            method_ir: The method IR
            class_ir: The class this method belongs to
            native: Whether building for native (vtable) version vs MP wrapper
        """
        if method_ir.body_ast is None:
            return []

        # Reset state for this method
        self._temp_counter = 0
        self._var_types = {}
        self._list_vars: dict[str, str | None] = {}
        self._rtuple_types = {}
        self._used_rtuples = set()
        self._uses_print = False
        self._uses_list_opt = False
        self._yield_state_counter = 0

        # Populate mypy local type info for this method
        mypy_method = self._get_mypy_method_type(class_ir.name, method_ir.name)
        if mypy_method:
            self._mypy_local_types = dict(mypy_method.local_types)
        else:
            self._mypy_local_types = {}

        first_yield = next(
            (n for n in ast.walk(method_ir.body_ast) if isinstance(n, (ast.Yield, ast.YieldFrom))),
            None,
        )
        if first_yield is not None:
            raise NotImplementedError(
                f"generator methods are not supported (line {first_yield.lineno})"
            )

        # Set up parameter types
        for param_name, param_type in method_ir.params:
            self._var_types[param_name] = param_type.to_c_type_str()

        # Track class-typed parameters for attribute access
        self._class_typed_params = {}
        self._container_element_types = {}
        self._optional_class_params = set()
        method_args = method_ir.body_ast.args.args
        if not method_ir.is_static and not method_ir.is_classmethod:
            method_args = method_args[1:]  # Skip self
        for arg in method_args:
            if arg.annotation:
                class_name = self._extract_class_from_annotation(arg.annotation)
                if class_name:
                    self._class_typed_params[arg.arg] = class_name
                    if self._is_optional_class_annotation(arg.annotation):
                        self._optional_class_params.add(arg.arg)
                else:
                    elem_class = self._extract_container_element_class(arg.annotation)
                    if elem_class:
                        self._container_element_types[arg.arg] = elem_class

        # Track self and params as locals
        local_vars = [p[0] for p in method_ir.params]
        if not method_ir.is_static and not method_ir.is_classmethod:
            local_vars.insert(0, "self")

        self._ctx = BuildContext(locals_=local_vars, class_ir=class_ir, native=native)
        body_ir: list[StmtIR] = []
        for stmt in method_ir.body_ast.body:
            # Skip docstrings
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                continue
            stmt_ir = self._build_statement(stmt, local_vars)
            if stmt_ir is not None:
                body_ir.append(stmt_ir)

        method_ir.max_temp = self._temp_counter
        return body_ir

    def _next_yield_state_id(self) -> int:
        self._yield_state_counter += 1
        return self._yield_state_counter

    def _is_supported_generator_range_call(self, call: ast.Call) -> bool:
        if not (
            isinstance(call.func, ast.Name) and call.func.id == "range" and len(call.keywords) == 0
        ):
            return False

        def _is_int_name_or_int_const(arg: ast.expr) -> bool:
            if isinstance(arg, ast.Name):
                return True
            return isinstance(arg, ast.Constant) and isinstance(arg.value, int)

        args = call.args
        if len(args) == 1:
            return _is_int_name_or_int_const(args[0])
        if len(args) == 2:
            # Allow range(start, end) where both are int/name
            return _is_int_name_or_int_const(args[0]) and _is_int_name_or_int_const(args[1])
        if len(args) == 3:
            # Allow range(start, end, step) only if step is constant 1
            if not _is_int_name_or_int_const(args[0]):
                return False
            if not _is_int_name_or_int_const(args[1]):
                return False
            return isinstance(args[2], ast.Constant) and args[2].value == 1
        return False
