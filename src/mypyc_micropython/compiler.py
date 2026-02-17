"""
Compiler: typed Python (.py) -> MicroPython usermod folder.

Output structure:
  usermod_<name>/
    <name>.c
    micropython.mk
    micropython.cmake
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .class_emitter import ClassEmitter
from .container_emitter import ContainerEmitter
from .ir import (
    ClassIR,
    CType,
    DataclassInfo,
    DictNewIR,
    FieldIR,
    InstrIR,
    IRType,
    ListNewIR,
    MethodCallIR,
    MethodIR,
    ModuleIR,
    NameIR,
    SetNewIR,
    TempIR,
    TupleNewIR,
    ValueIR,
)

if TYPE_CHECKING:
    pass


@dataclass
class CompilationResult:
    module_name: str
    c_code: str
    h_code: str | None
    mk_code: str
    cmake_code: str
    success: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    name: str
    c_name: str
    num_args: int
    has_varargs: bool = False
    docstring: str | None = None


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

VOID_RETURNING_METHODS = {
    "add",
    "append",
    "clear",
    "discard",
    "remove",
    "update",
}


def sanitize_name(name: str) -> str:
    result = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    if result and result[0].isdigit():
        result = "_" + result
    if result in C_RESERVED_WORDS:
        result = result + "_"
    return result


def compile_to_micropython(
    source_path: str | Path,
    output_dir: str | Path | None = None,
) -> CompilationResult:
    source_path = Path(source_path)

    if not source_path.exists():
        return CompilationResult(
            module_name="",
            c_code="",
            h_code=None,
            mk_code="",
            cmake_code="",
            success=False,
            errors=[f"Source file not found: {source_path}"],
        )

    module_name = source_path.stem

    if output_dir is None:
        output_dir = source_path.parent / f"usermod_{module_name}"
    output_dir = Path(output_dir)

    try:
        source_code = source_path.read_text()
        c_code = compile_source(source_code, module_name)
        mk_code = generate_micropython_mk(module_name)
        cmake_code = generate_micropython_cmake(module_name)

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{module_name}.c").write_text(c_code)
        (output_dir / "micropython.mk").write_text(mk_code)
        (output_dir / "micropython.cmake").write_text(cmake_code)

        return CompilationResult(
            module_name=module_name,
            c_code=c_code,
            h_code=None,
            mk_code=mk_code,
            cmake_code=cmake_code,
            success=True,
        )

    except Exception as e:
        return CompilationResult(
            module_name=module_name,
            c_code="",
            h_code=None,
            mk_code="",
            cmake_code="",
            success=False,
            errors=[str(e)],
        )


def generate_micropython_mk(module_name: str) -> str:
    c_name = sanitize_name(module_name)
    mod_upper = c_name.upper()

    return f"""\
{mod_upper}_MOD_DIR := $(USERMOD_DIR)
SRC_USERMOD += $(wildcard $({mod_upper}_MOD_DIR)/*.c)
CFLAGS_USERMOD += -I$({mod_upper}_MOD_DIR)
"""


def generate_micropython_cmake(module_name: str) -> str:
    c_name = sanitize_name(module_name)

    return f"""\
add_library(usermod_{c_name} INTERFACE)

target_sources(usermod_{c_name} INTERFACE
    ${{CMAKE_CURRENT_LIST_DIR}}/{module_name}.c
)

target_include_directories(usermod_{c_name} INTERFACE
    ${{CMAKE_CURRENT_LIST_DIR}}
)

target_link_libraries(usermod INTERFACE usermod_{c_name})
"""


class TypedPythonTranslator:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.c_name = sanitize_name(module_name)
        self.functions: list[FunctionInfo] = []
        self._function_code: list[str] = []
        self._class_code: list[str] = []
        self._forward_decls: list[str] = []
        self._temp_counter = 0
        self._pending_prelude: list[InstrIR] = []
        self._container_emitter = ContainerEmitter()
        self._loop_depth = 0
        self._var_types: dict[str, str] = {}
        self._uses_print = False

        self._module_ir = ModuleIR(name=module_name, c_name=self.c_name)
        self._current_class: ClassIR | None = None
        self._known_classes: dict[str, ClassIR] = {}
        self._struct_code: list[str] = []

    def translate_source(self, source: str) -> str:
        tree = ast.parse(source)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                self._translate_class(node)
            elif isinstance(node, ast.FunctionDef):
                self._translate_function(node)

        self._module_ir.resolve_base_classes()

        for class_ir in self._module_ir.get_classes_in_order():
            class_ir.compute_layout()

        return self._generate_module()

    def _fresh_temp(self) -> str:
        self._temp_counter += 1
        return f"_tmp{self._temp_counter}"

    def _unbox_if_needed(
        self, expr: str, expr_type: str, target_type: str = "mp_int_t"
    ) -> tuple[str, str]:
        """Unbox mp_obj_t to a native C type when needed for arithmetic/comparison."""
        if expr_type == "mp_obj_t" and target_type != "mp_obj_t":
            if target_type == "mp_float_t":
                return f"mp_get_float_checked({expr})", "mp_float_t"
            else:
                return f"mp_obj_get_int({expr})", "mp_int_t"
        return expr, expr_type

    def _translate_class(self, node: ast.ClassDef) -> None:
        class_name = node.name
        c_class_name = f"{self.c_name}_{sanitize_name(class_name)}"

        is_dataclass = False
        dataclass_info = None
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                is_dataclass = True
                dataclass_info = DataclassInfo()
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

        base_name = None
        if node.bases:
            first_base = node.bases[0]
            if isinstance(first_base, ast.Name):
                if first_base.id not in ("object", "Object"):
                    base_name = first_base.id

        class_ir = ClassIR(
            name=class_name,
            c_name=c_class_name,
            module_name=self.module_name,
            base_name=base_name,
            is_dataclass=is_dataclass,
            dataclass_info=dataclass_info,
            ast_node=node,
        )

        if base_name and base_name in self._known_classes:
            class_ir.base = self._known_classes[base_name]

        self._current_class = class_ir
        self._known_classes[class_name] = class_ir

        self._parse_class_body(node, class_ir)

        if is_dataclass and dataclass_info:
            dataclass_info.fields = list(class_ir.fields)

        self._module_ir.add_class(class_ir)

        self._emit_class_code(class_ir)

        self._current_class = None

    def _parse_class_body(self, node: ast.ClassDef, class_ir: ClassIR) -> None:
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id
                py_type = self._annotation_to_py_type(stmt.annotation)
                c_type = CType.from_python_type(py_type)

                has_default = stmt.value is not None
                default_value = None
                if has_default and isinstance(stmt.value, ast.Constant):
                    default_value = stmt.value.value

                field_ir = FieldIR(
                    name=field_name,
                    py_type=py_type,
                    c_type=c_type,
                    has_default=has_default,
                    default_value=default_value,
                    default_ast=stmt.value,
                )
                class_ir.fields.append(field_ir)

            elif isinstance(stmt, ast.FunctionDef):
                self._parse_method(stmt, class_ir)

    def _parse_method(self, node: ast.FunctionDef, class_ir: ClassIR) -> None:
        method_name = node.name
        c_method_name = f"{class_ir.c_name}_{sanitize_name(method_name)}"

        params: list[tuple[str, CType]] = []
        for arg in node.args.args[1:]:
            py_type = self._annotation_to_py_type(arg.annotation) if arg.annotation else "object"
            c_type = CType.from_python_type(py_type)
            params.append((arg.arg, c_type))

        return_type = CType.VOID
        if node.returns:
            py_type = self._annotation_to_py_type(node.returns)
            return_type = CType.from_python_type(py_type)
            if py_type == "None":
                return_type = CType.VOID

        is_special = method_name.startswith("__") and method_name.endswith("__")
        is_virtual = not is_special or method_name in ("__len__", "__getitem__", "__setitem__")

        method_ir = MethodIR(
            name=method_name,
            c_name=c_method_name,
            params=params,
            return_type=return_type,
            body_ast=node,
            is_virtual=is_virtual,
            is_special=is_special,
            docstring=ast.get_docstring(node),
        )

        class_ir.methods[method_name] = method_ir

        if is_virtual and not is_special:
            class_ir.virtual_methods.append(method_name)

        if method_name == "__init__":
            class_ir.has_init = True
        elif method_name == "__repr__":
            class_ir.has_repr = True
        elif method_name == "__eq__":
            class_ir.has_eq = True

    def _emit_class_code(self, class_ir: ClassIR) -> None:
        emitter = ClassEmitter(class_ir, self.c_name)

        self._forward_decls.extend(emitter.emit_forward_declarations())

        struct_code = emitter.emit_struct()
        self._struct_code.extend(struct_code)

        for method_ir in class_ir.methods.values():
            self._emit_method(class_ir, method_ir)

        class_code = emitter.emit_all_except_struct()
        self._class_code.append(class_code)

    def _emit_method(self, class_ir: ClassIR, method_ir: MethodIR) -> None:
        if method_ir.is_virtual and not method_ir.is_special:
            self._emit_native_method(class_ir, method_ir)

        self._emit_mp_wrapper_method(class_ir, method_ir)

    def _emit_native_method(self, class_ir: ClassIR, method_ir: MethodIR) -> None:
        node = method_ir.body_ast
        c_name = method_ir.c_name

        params = [f"{class_ir.c_name}_obj_t *self"]
        for param_name, param_type in method_ir.params:
            params.append(f"{param_type.to_c_type_str()} {param_name}")
        params_str = ", ".join(params)

        ret_type = method_ir.return_type.to_c_type_str()

        lines = [f"static {ret_type} {c_name}_native({params_str}) {{"]

        # Populate _var_types so _translate_name returns correct types for params
        self._var_types = {}
        for param_name, param_type in method_ir.params:
            self._var_types[param_name] = param_type.to_c_type_str()

        local_vars = ["self"] + [p[0] for p in method_ir.params]
        return_type_str = ret_type

        for stmt in node.body:
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                continue
            lines.extend(
                self._translate_method_statement(
                    stmt, return_type_str, local_vars, class_ir, native=True
                )
            )

        if method_ir.return_type == CType.VOID:
            if not any("return" in line for line in lines):
                lines.append("    return;")

        lines.append("}")
        lines.append("")

        self._function_code.append("\n".join(lines))

    def _emit_mp_wrapper_method(self, class_ir: ClassIR, method_ir: MethodIR) -> None:
        node = method_ir.body_ast
        c_name = method_ir.c_name

        self._var_types = {}
        for param_name, param_type in method_ir.params:
            self._var_types[param_name] = param_type.to_c_type_str()

        num_args = len(method_ir.params) + 1

        if num_args == 1:
            sig = f"static mp_obj_t {c_name}_mp(mp_obj_t self_in)"
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_1({c_name}_obj, {c_name}_mp);"
        elif num_args == 2:
            sig = f"static mp_obj_t {c_name}_mp(mp_obj_t self_in, mp_obj_t arg0_obj)"
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_2({c_name}_obj, {c_name}_mp);"
        elif num_args == 3:
            sig = f"static mp_obj_t {c_name}_mp(mp_obj_t self_in, mp_obj_t arg0_obj, mp_obj_t arg1_obj)"
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_3({c_name}_obj, {c_name}_mp);"
        else:
            sig = f"static mp_obj_t {c_name}_mp(size_t n_args, const mp_obj_t *args)"
            obj_def = f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({c_name}_obj, {num_args}, {num_args}, {c_name}_mp);"

        lines = [sig + " {"]
        if num_args <= 3:
            lines.append(f"    {class_ir.c_name}_obj_t *self = MP_OBJ_TO_PTR(self_in);")
        else:
            lines.append(f"    {class_ir.c_name}_obj_t *self = MP_OBJ_TO_PTR(args[0]);")

        for i, (param_name, param_type) in enumerate(method_ir.params):
            if num_args <= 3:
                src = f"arg{i}_obj"
            else:
                src = f"args[{i + 1}]"

            if param_type == CType.MP_INT_T:
                lines.append(f"    mp_int_t {param_name} = mp_obj_get_int({src});")
            elif param_type == CType.MP_FLOAT_T:
                lines.append(f"    mp_float_t {param_name} = mp_obj_get_float({src});")
            elif param_type == CType.BOOL:
                lines.append(f"    bool {param_name} = mp_obj_is_true({src});")
            else:
                lines.append(f"    mp_obj_t {param_name} = {src};")

        if method_ir.is_virtual and not method_ir.is_special:
            args_list = ["self"] + [p[0] for p in method_ir.params]
            args_str = ", ".join(args_list)

            if method_ir.return_type == CType.VOID:
                lines.append(f"    {c_name}_native({args_str});")
                lines.append("    return mp_const_none;")
            elif method_ir.return_type == CType.MP_INT_T:
                lines.append(f"    return mp_obj_new_int({c_name}_native({args_str}));")
            elif method_ir.return_type == CType.MP_FLOAT_T:
                lines.append(f"    return mp_obj_new_float({c_name}_native({args_str}));")
            elif method_ir.return_type == CType.BOOL:
                lines.append(
                    f"    return {c_name}_native({args_str}) ? mp_const_true : mp_const_false;"
                )
            else:
                lines.append(f"    return {c_name}_native({args_str});")
        else:
            local_vars = ["self"] + [p[0] for p in method_ir.params]
            return_type_str = "mp_obj_t"

            for stmt in node.body:
                if (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Constant)
                    and isinstance(stmt.value.value, str)
                ):
                    continue
                lines.extend(
                    self._translate_method_statement(
                        stmt, return_type_str, local_vars, class_ir, native=False
                    )
                )

            if method_ir.return_type == CType.VOID:
                if not any("return" in line for line in lines):
                    lines.append("    return mp_const_none;")

        lines.append("}")
        lines.append(obj_def)
        lines.append("")

        self._function_code.append("\n".join(lines))

    def _translate_method_statement(
        self, stmt, return_type: str, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> list[str]:
        if isinstance(stmt, ast.Return):
            return self._translate_method_return(stmt, return_type, locals_, class_ir, native)
        elif isinstance(stmt, ast.Assign):
            return self._translate_method_assign(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.AnnAssign):
            return self._translate_method_ann_assign(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.If):
            return self._translate_method_if(stmt, return_type, locals_, class_ir, native)
        elif isinstance(stmt, ast.While):
            return self._translate_method_while(stmt, return_type, locals_, class_ir, native)
        elif isinstance(stmt, ast.For):
            return self._translate_for(stmt, return_type, locals_, class_ir=class_ir, native=native)
        elif isinstance(stmt, ast.AugAssign):
            return self._translate_method_aug_assign(stmt, locals_, class_ir, native)
        elif isinstance(stmt, ast.Expr):
            lines = self._flush_ir_prelude()
            expr, _ = self._translate_method_expr(stmt.value, locals_, class_ir, native)
            lines.extend(self._flush_ir_prelude())
            lines.append(f"    (void){expr};")
            return lines
        return self._translate_statement(stmt, return_type, locals_)

    def _translate_method_ann_assign(
        self, stmt: ast.AnnAssign, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> list[str]:
        if not isinstance(stmt.target, ast.Name):
            return []

        var_name = stmt.target.id
        c_type = self._annotation_to_c_type(stmt.annotation) if stmt.annotation else "mp_int_t"

        if stmt.value is not None:
            lines = self._flush_ir_prelude()
            expr, expr_type = self._translate_method_expr(stmt.value, locals_, class_ir, native)
            lines.extend(self._flush_ir_prelude())
            expr, expr_type = self._unbox_if_needed(expr, expr_type, c_type)
            if var_name not in locals_:
                locals_.append(var_name)
                self._var_types[var_name] = c_type
                lines.append(f"    {c_type} {var_name} = {expr};")
                return lines
            lines.append(f"    {var_name} = {expr};")
            return lines
        else:
            if var_name not in locals_:
                locals_.append(var_name)
                if c_type == "mp_int_t":
                    return [f"    {c_type} {var_name} = 0;"]
                elif c_type == "mp_float_t":
                    return [f"    {c_type} {var_name} = 0.0;"]
                elif c_type == "bool":
                    return [f"    {c_type} {var_name} = false;"]
                return [f"    {c_type} {var_name} = mp_const_none;"]
        return []

    def _translate_method_return(
        self,
        stmt: ast.Return,
        return_type: str,
        locals_: list[str],
        class_ir: ClassIR,
        native: bool,
    ) -> list[str]:
        if stmt.value is None:
            if native:
                return ["    return;"]
            return ["    return mp_const_none;"]

        lines = self._flush_ir_prelude()
        expr, expr_type = self._translate_method_expr(stmt.value, locals_, class_ir, native)
        lines.extend(self._flush_ir_prelude())

        if native:
            expr, expr_type = self._unbox_if_needed(expr, expr_type, return_type)
            lines.append(f"    return {expr};")
        else:
            if expr_type == "mp_int_t":
                lines.append(f"    return mp_obj_new_int({expr});")
            elif expr_type == "mp_float_t":
                lines.append(f"    return mp_obj_new_float({expr});")
            elif expr_type == "bool":
                lines.append(f"    return {expr} ? mp_const_true : mp_const_false;")
            else:
                lines.append(f"    return {expr};")
        return lines

    def _translate_method_assign(
        self, stmt: ast.Assign, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> list[str]:
        if len(stmt.targets) != 1:
            return []

        target = stmt.targets[0]

        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            attr_name = target.attr
            lines = self._flush_ir_prelude()
            expr, expr_type = self._translate_method_expr(stmt.value, locals_, class_ir, native)
            lines.extend(self._flush_ir_prelude())

            field_with_path = next(
                ((f, p) for f, p in class_ir.get_all_fields_with_path() if f.name == attr_name),
                None,
            )
            if field_with_path:
                field, path = field_with_path
                if native:
                    lines.append(f"    self->{path} = {expr};")
                else:
                    if field.c_type == CType.MP_INT_T and expr_type != "mp_int_t":
                        lines.append(f"    self->{path} = mp_obj_get_int({expr});")
                    elif field.c_type == CType.MP_FLOAT_T and expr_type != "mp_float_t":
                        lines.append(f"    self->{path} = mp_obj_get_float({expr});")
                    elif field.c_type == CType.BOOL and expr_type != "bool":
                        lines.append(f"    self->{path} = mp_obj_is_true({expr});")
                    else:
                        lines.append(f"    self->{path} = {expr};")
            else:
                lines.append(f"    self->{attr_name} = {expr};")
            return lines

        if isinstance(target, ast.Name):
            var_name = target.id
            lines = self._flush_ir_prelude()
            expr, expr_type = self._translate_method_expr(stmt.value, locals_, class_ir, native)
            lines.extend(self._flush_ir_prelude())

            if var_name not in locals_:
                locals_.append(var_name)
                lines.append(f"    {expr_type} {var_name} = {expr};")
                return lines
            lines.append(f"    {var_name} = {expr};")
            return lines

        if isinstance(target, ast.Subscript):
            lines = self._flush_ir_prelude()
            obj_expr, _ = self._translate_method_expr(target.value, locals_, class_ir, native)
            idx_expr, idx_type = self._translate_method_expr(
                target.slice, locals_, class_ir, native
            )
            val_expr, val_type = self._translate_method_expr(stmt.value, locals_, class_ir, native)
            lines.extend(self._flush_ir_prelude())
            boxed_key = self._box_value(idx_expr, idx_type)
            boxed_val = self._box_value(val_expr, val_type)
            lines.append(f"    mp_obj_subscr({obj_expr}, {boxed_key}, {boxed_val});")
            return lines

        return self._translate_assign(stmt, locals_)

    def _translate_method_aug_assign(
        self, stmt: ast.AugAssign, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> list[str]:
        if (
            isinstance(stmt.target, ast.Attribute)
            and isinstance(stmt.target.value, ast.Name)
            and stmt.target.value.id == "self"
        ):
            attr_name = stmt.target.attr
            right, _ = self._translate_method_expr(stmt.value, locals_, class_ir, native)
            lines = self._flush_ir_prelude()

            field_with_path = next(
                ((f, p) for f, p in class_ir.get_all_fields_with_path() if f.name == attr_name),
                None,
            )
            path = field_with_path[1] if field_with_path else attr_name

            op_map = {
                ast.Add: "+=",
                ast.Sub: "-=",
                ast.Mult: "*=",
                ast.Div: "/=",
                ast.Mod: "%=",
                ast.BitAnd: "&=",
                ast.BitOr: "|=",
                ast.BitXor: "^=",
            }
            c_op = op_map.get(type(stmt.op), "+=")
            lines.append(f"    self->{path} {c_op} {right};")
            return lines

        if not isinstance(stmt.target, ast.Name):
            return self._translate_aug_assign(stmt, locals_)

        var_name = stmt.target.id
        right, right_type = self._translate_method_expr(stmt.value, locals_, class_ir, native)
        lines = self._flush_ir_prelude()
        right, right_type = self._unbox_if_needed(right, right_type)

        op_map = {
            ast.Add: "+=",
            ast.Sub: "-=",
            ast.Mult: "*=",
            ast.Div: "/=",
            ast.Mod: "%=",
            ast.BitAnd: "&=",
            ast.BitOr: "|=",
            ast.BitXor: "^=",
            ast.LShift: "<<=",
            ast.RShift: ">>=",
        }
        c_op = op_map.get(type(stmt.op), "+=")
        lines.append(f"    {var_name} {c_op} {right};")
        return lines

    def _translate_method_if(
        self, stmt: ast.If, return_type: str, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> list[str]:
        cond, _ = self._translate_method_expr(stmt.test, locals_, class_ir, native)
        lines = [f"    if ({cond}) {{"]

        for s in stmt.body:
            for line in self._translate_method_statement(s, return_type, locals_, class_ir, native):
                lines.append("    " + line)

        if stmt.orelse:
            lines.append("    } else {")
            for s in stmt.orelse:
                for line in self._translate_method_statement(
                    s, return_type, locals_, class_ir, native
                ):
                    lines.append("    " + line)

        lines.append("    }")
        return lines

    def _translate_method_while(
        self, stmt: ast.While, return_type: str, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> list[str]:
        cond, _ = self._translate_method_expr(stmt.test, locals_, class_ir, native)
        lines = [f"    while ({cond}) {{"]

        for s in stmt.body:
            for line in self._translate_method_statement(s, return_type, locals_, class_ir, native):
                lines.append("    " + line)

        lines.append("    }")
        return lines

    def _translate_method_expr(
        self, expr, locals_: list[str], class_ir: ClassIR, native: bool
    ) -> tuple[str, str]:
        if (
            isinstance(expr, ast.Attribute)
            and isinstance(expr.value, ast.Name)
            and expr.value.id == "self"
        ):
            attr_name = expr.attr
            # Look up field with path for proper inheritance access (e.g., super.x)
            field_with_path = next(
                ((f, p) for f, p in class_ir.get_all_fields_with_path() if f.name == attr_name),
                None,
            )
            if field_with_path:
                field, path = field_with_path
                c_type_str = field.c_type.to_c_type_str()
                return f"self->{path}", c_type_str
            return f"self->{attr_name}", "mp_obj_t"

        if isinstance(expr, ast.Call):
            # Case 1: self.method(args) — direct method call on self
            if (
                isinstance(expr.func, ast.Attribute)
                and isinstance(expr.func.value, ast.Name)
                and expr.func.value.id == "self"
            ):
                method_name = expr.func.attr
                method = class_ir.methods.get(method_name)

                if method and method.is_virtual and not method.is_special:
                    args = ["self"]
                    for arg in expr.args:
                        arg_expr, _ = self._translate_method_expr(arg, locals_, class_ir, native)
                        args.append(arg_expr)
                    args_str = ", ".join(args)

                    ret_type = method.return_type.to_c_type_str()
                    return f"{method.c_name}_native({args_str})", ret_type

            # Case 2: self.field.method(args) — method call on a field (e.g., self.items.append(x))
            if (
                isinstance(expr.func, ast.Attribute)
                and isinstance(expr.func.value, ast.Attribute)
                and isinstance(expr.func.value.value, ast.Name)
                and expr.func.value.value.id == "self"
            ):
                field_name = expr.func.value.attr
                method_name = expr.func.attr
                field_with_path = next(
                    (
                        (f, p)
                        for f, p in class_ir.get_all_fields_with_path()
                        if f.name == field_name
                    ),
                    None,
                )
                obj_c_expr = (
                    f"self->{field_with_path[1]}" if field_with_path else f"self->{field_name}"
                )

                ir_args: list[ValueIR] = []
                for arg in expr.args:
                    arg_expr, arg_type = self._translate_method_expr(arg, locals_, class_ir, native)
                    boxed = self._box_value(arg_expr, arg_type)
                    ir_args.append(NameIR(ir_type=IRType.OBJ, py_name="", c_name=boxed))

                receiver = NameIR(ir_type=IRType.OBJ, py_name="", c_name=obj_c_expr)
                temp_name = self._fresh_temp()
                result = TempIR(ir_type=IRType.OBJ, name=temp_name)
                self._pending_prelude.append(
                    MethodCallIR(result=result, receiver=receiver, method=method_name, args=ir_args)
                )
                return temp_name, "mp_obj_t"

            # Case 3: builtin(self.field) — e.g., len(self.items)
            if isinstance(expr.func, ast.Name):
                func_name = expr.func.id
                args = [
                    self._translate_method_expr(arg, locals_, class_ir, native) for arg in expr.args
                ]
                arg_exprs = [a[0] for a in args]
                arg_types = [a[1] for a in args]

                if func_name == "len" and len(arg_exprs) == 1:
                    boxed = self._box_value(arg_exprs[0], arg_types[0])
                    return f"mp_obj_get_int(mp_obj_len({boxed}))", "mp_int_t"
                if func_name == "abs" and arg_exprs:
                    a = arg_exprs[0]
                    return f"(({a}) < 0 ? -({a}) : ({a}))", "mp_int_t"
                if func_name == "int" and arg_exprs:
                    return f"((mp_int_t)({arg_exprs[0]}))", "mp_int_t"
                if func_name == "float" and arg_exprs:
                    return f"((mp_float_t)({arg_exprs[0]}))", "mp_float_t"

        if isinstance(expr, ast.BinOp):
            left, left_type = self._translate_method_expr(expr.left, locals_, class_ir, native)
            right, right_type = self._translate_method_expr(expr.right, locals_, class_ir, native)

            op_map = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.Div: "/",
                ast.FloorDiv: "/",
                ast.Mod: "%",
                ast.BitAnd: "&",
                ast.BitOr: "|",
                ast.BitXor: "^",
                ast.LShift: "<<",
                ast.RShift: ">>",
            }
            c_op = op_map.get(type(expr.op), "+")
            result_type = (
                "mp_float_t"
                if (left_type == "mp_float_t" or right_type == "mp_float_t")
                else left_type
            )
            return f"({left} {c_op} {right})", result_type

        if isinstance(expr, ast.UnaryOp):
            operand, op_type = self._translate_method_expr(expr.operand, locals_, class_ir, native)
            if isinstance(expr.op, ast.USub):
                return f"(-{operand})", op_type
            elif isinstance(expr.op, ast.Not):
                return f"(!{operand})", "bool"
            elif isinstance(expr.op, ast.UAdd):
                return f"(+{operand})", op_type
            elif isinstance(expr.op, ast.Invert):
                return f"(~{operand})", op_type
            return operand, op_type

        if isinstance(expr, ast.Compare):
            left, _ = self._translate_method_expr(expr.left, locals_, class_ir, native)
            op_map = {
                ast.Eq: "==",
                ast.NotEq: "!=",
                ast.Lt: "<",
                ast.LtE: "<=",
                ast.Gt: ">",
                ast.GtE: ">=",
            }
            parts = []
            prev = left
            for op, comparator in zip(expr.ops, expr.comparators):
                right, _ = self._translate_method_expr(comparator, locals_, class_ir, native)
                c_op = op_map.get(type(op), "==")
                parts.append(f"({prev} {c_op} {right})")
                prev = right
            return ("(" + " && ".join(parts) + ")" if len(parts) > 1 else parts[0]), "bool"

        if isinstance(expr, ast.IfExp):
            test, _ = self._translate_method_expr(expr.test, locals_, class_ir, native)
            body, body_type = self._translate_method_expr(expr.body, locals_, class_ir, native)
            orelse, _ = self._translate_method_expr(expr.orelse, locals_, class_ir, native)
            return f"(({test}) ? ({body}) : ({orelse}))", body_type

        if isinstance(expr, ast.Subscript):
            value_expr, _ = self._translate_method_expr(expr.value, locals_, class_ir, native)
            slice_expr, slice_type = self._translate_method_expr(
                expr.slice, locals_, class_ir, native
            )
            boxed_key = self._box_value(slice_expr, slice_type)
            return f"mp_obj_subscr({value_expr}, {boxed_key}, MP_OBJ_SENTINEL)", "mp_obj_t"

        return self._translate_expr(expr, locals_)

    def _annotation_to_py_type(self, annotation) -> str:
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return annotation.value.id
        elif isinstance(annotation, ast.Constant):
            if annotation.value is None:
                return "None"
        return "object"

    def _translate_function(self, node: ast.FunctionDef) -> None:
        self._var_types = {}

        func_name = node.name
        c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"

        args = node.args
        num_args = len(args.args)
        arg_names = [arg.arg for arg in args.args]

        arg_types = []
        for arg in args.args:
            c_type = self._annotation_to_c_type(arg.annotation) if arg.annotation else "mp_obj_t"
            arg_types.append(c_type)
            self._var_types[arg.arg] = c_type

        return_type = self._annotation_to_c_type(node.returns) if node.returns else "mp_obj_t"

        c_sig, obj_def = self._build_function_signature(c_func_name, arg_names, num_args)

        body_lines = self._unbox_arguments(arg_names, arg_types, num_args)
        if body_lines:
            body_lines.append("")

        local_vars = list(arg_names)
        for stmt in node.body:
            body_lines.extend(self._translate_statement(stmt, return_type, local_vars))

        needs_fallthrough_return = True
        if node.body and isinstance(node.body[-1], ast.Return):
            needs_fallthrough_return = False

        if needs_fallthrough_return:
            body_lines.append("    return mp_const_none;")

        func_code = [c_sig + " {"] + body_lines + ["}", obj_def, ""]
        self._function_code.append("\n".join(func_code))

        self.functions.append(
            FunctionInfo(
                name=func_name,
                c_name=c_func_name,
                num_args=num_args,
                docstring=ast.get_docstring(node),
            )
        )

    def _build_function_signature(
        self, c_func_name: str, arg_names: list[str], num_args: int
    ) -> tuple[str, str]:
        if num_args == 0:
            return (
                f"static mp_obj_t {c_func_name}(void)",
                f"MP_DEFINE_CONST_FUN_OBJ_0({c_func_name}_obj, {c_func_name});",
            )
        elif num_args == 1:
            return (
                f"static mp_obj_t {c_func_name}(mp_obj_t {arg_names[0]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_1({c_func_name}_obj, {c_func_name});",
            )
        elif num_args == 2:
            return (
                f"static mp_obj_t {c_func_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_2({c_func_name}_obj, {c_func_name});",
            )
        elif num_args == 3:
            return (
                f"static mp_obj_t {c_func_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj, mp_obj_t {arg_names[2]}_obj)",
                f"MP_DEFINE_CONST_FUN_OBJ_3({c_func_name}_obj, {c_func_name});",
            )
        else:
            return (
                f"static mp_obj_t {c_func_name}(size_t n_args, const mp_obj_t *args)",
                f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({c_func_name}_obj, {num_args}, {num_args}, {c_func_name});",
            )

    def _unbox_arguments(
        self, arg_names: list[str], arg_types: list[str], num_args: int
    ) -> list[str]:
        lines = []
        for i, (arg_name, arg_type) in enumerate(zip(arg_names, arg_types)):
            src = f"{arg_name}_obj" if num_args <= 3 else f"args[{i}]"
            c_arg_name = sanitize_name(arg_name)

            if arg_type == "mp_int_t":
                lines.append(f"    mp_int_t {c_arg_name} = mp_obj_get_int({src});")
            elif arg_type == "mp_float_t":
                lines.append(f"    mp_float_t {c_arg_name} = mp_get_float_checked({src});")
            else:
                lines.append(f"    mp_obj_t {c_arg_name} = {src};")
        return lines

    def _annotation_to_c_type(self, annotation) -> str:
        if isinstance(annotation, ast.Name):
            type_map = {
                "int": "mp_int_t",
                "float": "mp_float_t",
                "bool": "bool",
                "str": "const char*",
                "None": "void",
                "list": "mp_obj_t",
                "dict": "mp_obj_t",
                "tuple": "mp_obj_t",
                "set": "mp_obj_t",
            }
            return type_map.get(annotation.id, "mp_obj_t")
        elif isinstance(annotation, ast.Subscript):
            # Handle generic types like list[int], dict[str, int], tuple[int, ...], set[int]
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id in ("list", "dict", "tuple", "set"):
                    return "mp_obj_t"  # All containers are boxed as mp_obj_t
        return "mp_obj_t"

    def _translate_statement(self, stmt, return_type: str, locals_: list[str]) -> list[str]:
        if isinstance(stmt, ast.Return):
            return self._translate_return(stmt, return_type, locals_)
        elif isinstance(stmt, ast.If):
            return self._translate_if(stmt, return_type, locals_)
        elif isinstance(stmt, ast.While):
            return self._translate_while(stmt, return_type, locals_)
        elif isinstance(stmt, ast.For):
            return self._translate_for(stmt, return_type, locals_)
        elif isinstance(stmt, ast.Assign):
            return self._translate_assign(stmt, locals_)
        elif isinstance(stmt, ast.AnnAssign):
            return self._translate_ann_assign(stmt, locals_)
        elif isinstance(stmt, ast.AugAssign):
            return self._translate_aug_assign(stmt, locals_)
        elif isinstance(stmt, ast.Break):
            if self._loop_depth > 0:
                return ["    break;"]
            return ["    /* ERROR: break outside loop */"]
        elif isinstance(stmt, ast.Continue):
            if self._loop_depth > 0:
                return ["    continue;"]
            return ["    /* ERROR: continue outside loop */"]
        elif isinstance(stmt, ast.Expr):
            # Check for print() call - handle as statement
            if (
                isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Name)
                and stmt.value.func.id == "print"
            ):
                return self._translate_print_stmt(stmt.value, locals_)
            lines = self._flush_ir_prelude()
            expr, _ = self._translate_expr(stmt.value, locals_)
            lines.extend(self._flush_ir_prelude())
            lines.append(f"    (void){expr};")
            return lines
        return []

    def _translate_return(
        self, stmt: ast.Return, return_type: str, locals_: list[str]
    ) -> list[str]:
        if stmt.value is None:
            return ["    return mp_const_none;"]

        lines = self._flush_ir_prelude()
        expr, expr_type = self._translate_expr(stmt.value, locals_)
        more_lines = self._flush_ir_prelude()
        lines.extend(more_lines)

        if expr_type == "mp_obj_t" or return_type == "mp_obj_t":
            lines.append(f"    return {expr};")
        elif return_type == "mp_float_t" or expr_type == "mp_float_t":
            lines.append(f"    return mp_obj_new_float({expr});")
        elif return_type == "mp_int_t" or expr_type == "mp_int_t":
            lines.append(f"    return mp_obj_new_int({expr});")
        elif return_type == "bool":
            lines.append(f"    return {expr} ? mp_const_true : mp_const_false;")
        else:
            lines.append(f"    return {expr};")
        return lines

    def _translate_if(self, stmt: ast.If, return_type: str, locals_: list[str]) -> list[str]:
        cond, _ = self._translate_expr(stmt.test, locals_)
        lines = [f"    if ({cond}) {{"]

        for s in stmt.body:
            for line in self._translate_statement(s, return_type, locals_):
                lines.append("    " + line)

        if stmt.orelse:
            lines.append("    } else {")
            for s in stmt.orelse:
                for line in self._translate_statement(s, return_type, locals_):
                    lines.append("    " + line)

        lines.append("    }")
        return lines

    def _translate_while(self, stmt: ast.While, return_type: str, locals_: list[str]) -> list[str]:
        cond, _ = self._translate_expr(stmt.test, locals_)
        lines = [f"    while ({cond}) {{"]

        self._loop_depth += 1
        for s in stmt.body:
            for line in self._translate_statement(s, return_type, locals_):
                lines.append("    " + line)
        self._loop_depth -= 1

        lines.append("    }")
        return lines

    def _translate_print_stmt(self, call: ast.Call, locals_: list[str]) -> list[str]:
        self._uses_print = True
        lines = self._flush_ir_prelude()

        args = []
        for arg in call.args:
            arg_expr, arg_type = self._translate_expr(arg, locals_)
            lines.extend(self._flush_ir_prelude())
            boxed = self._box_value(arg_expr, arg_type)
            args.append(boxed)

        if not args:
            lines.append('    mp_print_str(&mp_plat_print, "\\n");')
        else:
            for i, arg in enumerate(args):
                if i > 0:
                    lines.append('    mp_print_str(&mp_plat_print, " ");')
                lines.append(f"    mp_obj_print_helper(&mp_plat_print, {arg}, PRINT_STR);")
            lines.append('    mp_print_str(&mp_plat_print, "\\n");')

        return lines

    def _translate_for(
        self,
        stmt: ast.For,
        return_type: str,
        locals_: list[str],
        class_ir: ClassIR | None = None,
        native: bool = False,
    ) -> list[str]:
        if not isinstance(stmt.target, ast.Name):
            return ["    /* unsupported for loop target */"]

        loop_var = stmt.target.id

        if isinstance(stmt.iter, ast.Call) and isinstance(stmt.iter.func, ast.Name):
            if stmt.iter.func.id == "range":
                return self._translate_for_range(
                    stmt, loop_var, return_type, locals_, class_ir=class_ir, native=native
                )

        return self._translate_for_iterable(
            stmt, loop_var, return_type, locals_, class_ir=class_ir, native=native
        )

    def _translate_for_range(
        self,
        stmt: ast.For,
        loop_var: str,
        return_type: str,
        locals_: list[str],
        class_ir: ClassIR | None = None,
        native: bool = False,
    ) -> list[str]:
        assert isinstance(stmt.iter, ast.Call)
        args = stmt.iter.args
        lines = []

        step_is_constant = False
        step_constant_value: int | None = None
        step_var: str | None = None

        if len(args) == 1:
            start = "0"
            if class_ir is not None:
                end, _ = self._translate_method_expr(args[0], locals_, class_ir, native)
            else:
                end, _ = self._translate_expr(args[0], locals_)
            step = "1"
            step_is_constant = True
            step_constant_value = 1
        elif len(args) == 2:
            if class_ir is not None:
                start, _ = self._translate_method_expr(args[0], locals_, class_ir, native)
                end, _ = self._translate_method_expr(args[1], locals_, class_ir, native)
            else:
                start, _ = self._translate_expr(args[0], locals_)
                end, _ = self._translate_expr(args[1], locals_)
            step = "1"
            step_is_constant = True
            step_constant_value = 1
        elif len(args) == 3:
            if class_ir is not None:
                start, _ = self._translate_method_expr(args[0], locals_, class_ir, native)
                end, _ = self._translate_method_expr(args[1], locals_, class_ir, native)
            else:
                start, _ = self._translate_expr(args[0], locals_)
                end, _ = self._translate_expr(args[1], locals_)
            if isinstance(args[2], ast.Constant) and isinstance(args[2].value, int):
                step_is_constant = True
                step_constant_value = args[2].value
                step = str(step_constant_value)
            elif isinstance(args[2], ast.UnaryOp) and isinstance(args[2].op, ast.USub):
                if isinstance(args[2].operand, ast.Constant) and isinstance(
                    args[2].operand.value, int
                ):
                    step_is_constant = True
                    step_constant_value = -args[2].operand.value
                    step = str(step_constant_value)
                else:
                    if class_ir is not None:
                        step, _ = self._translate_method_expr(args[2], locals_, class_ir, native)
                    else:
                        step, _ = self._translate_expr(args[2], locals_)
            else:
                if class_ir is not None:
                    step, _ = self._translate_method_expr(args[2], locals_, class_ir, native)
                else:
                    step, _ = self._translate_expr(args[2], locals_)
        else:
            return ["    /* unsupported range() call */"]

        if loop_var not in locals_:
            locals_.append(loop_var)
            self._var_types[loop_var] = "mp_int_t"
            lines.append(f"    mp_int_t {sanitize_name(loop_var)};")

        c_loop_var = sanitize_name(loop_var)

        end_var = self._fresh_temp()
        lines.append(f"    mp_int_t {end_var} = {end};")

        if not step_is_constant:
            step_var = self._fresh_temp()
            lines.append(f"    mp_int_t {step_var} = {step};")

        if step_is_constant and step_constant_value == 1:
            cond = f"{c_loop_var} < {end_var}"
            inc = f"{c_loop_var}++"
        elif step_is_constant and step_constant_value == -1:
            cond = f"{c_loop_var} > {end_var}"
            inc = f"{c_loop_var}--"
        elif step_is_constant and step_constant_value is not None:
            if step_constant_value > 0:
                cond = f"{c_loop_var} < {end_var}"
            else:
                cond = f"{c_loop_var} > {end_var}"
            inc = f"{c_loop_var} += {step}"
        else:
            assert step_var is not None
            cond = f"({step_var} > 0) ? ({c_loop_var} < {end_var}) : ({c_loop_var} > {end_var})"
            inc = f"{c_loop_var} += {step_var}"

        lines.append(f"    for ({c_loop_var} = {start}; {cond}; {inc}) {{")

        self._loop_depth += 1
        for s in stmt.body:
            if class_ir is not None:
                for line in self._translate_method_statement(
                    s, return_type, locals_, class_ir, native
                ):
                    lines.append("    " + line)
            else:
                for line in self._translate_statement(s, return_type, locals_):
                    lines.append("    " + line)
        self._loop_depth -= 1

        lines.append("    }")
        return lines

    def _translate_for_iterable(
        self,
        stmt: ast.For,
        loop_var: str,
        return_type: str,
        locals_: list[str],
        class_ir: ClassIR | None = None,
        native: bool = False,
    ) -> list[str]:
        lines = []
        if class_ir is not None:
            iter_expr, _ = self._translate_method_expr(stmt.iter, locals_, class_ir, native)
        else:
            iter_expr, _ = self._translate_expr(stmt.iter, locals_)
        lines.extend(self._flush_ir_prelude())

        iter_var = self._fresh_temp()
        iter_buf_var = self._fresh_temp()
        c_loop_var = sanitize_name(loop_var)

        if loop_var not in locals_:
            locals_.append(loop_var)
            self._var_types[loop_var] = "mp_obj_t"
            lines.append(f"    mp_obj_t {c_loop_var};")

        lines.append(f"    mp_obj_iter_buf_t {iter_buf_var};")
        lines.append(f"    mp_obj_t {iter_var} = mp_getiter({iter_expr}, &{iter_buf_var});")
        lines.append(
            f"    while (({c_loop_var} = mp_iternext({iter_var})) != MP_OBJ_STOP_ITERATION) {{"
        )

        self._loop_depth += 1
        for s in stmt.body:
            if class_ir is not None:
                for line in self._translate_method_statement(
                    s, return_type, locals_, class_ir, native
                ):
                    lines.append("    " + line)
            else:
                for line in self._translate_statement(s, return_type, locals_):
                    lines.append("    " + line)
        self._loop_depth -= 1

        lines.append("    }")
        return lines

    def _flush_ir_prelude(self) -> list[str]:
        lines = self._container_emitter.emit_prelude(self._pending_prelude)
        self._pending_prelude.clear()
        return lines

    def _translate_assign(self, stmt: ast.Assign, locals_: list[str]) -> list[str]:
        if len(stmt.targets) != 1:
            return []

        target = stmt.targets[0]

        if isinstance(target, ast.Subscript):
            return self._translate_subscript_assign(target, stmt.value, locals_)

        if isinstance(target, ast.Tuple):
            return self._translate_tuple_unpack(target, stmt.value, locals_)

        if not isinstance(target, ast.Name):
            return []

        var_name = target.id
        c_var_name = sanitize_name(var_name)
        lines = self._flush_ir_prelude()
        expr, expr_type = self._translate_expr(stmt.value, locals_)
        more_lines = self._flush_ir_prelude()
        lines.extend(more_lines)

        if var_name not in locals_:
            locals_.append(var_name)
            self._var_types[var_name] = expr_type
            return lines + [f"    {expr_type} {c_var_name} = {expr};"]
        return lines + [f"    {c_var_name} = {expr};"]

    def _translate_tuple_unpack(self, target: ast.Tuple, value, locals_: list[str]) -> list[str]:
        lines = self._flush_ir_prelude()
        tuple_expr, _ = self._translate_expr(value, locals_)
        lines.extend(self._flush_ir_prelude())

        tuple_temp = self._fresh_temp()
        lines.append(f"    mp_obj_t {tuple_temp} = {tuple_expr};")

        for i, elt in enumerate(target.elts):
            if isinstance(elt, ast.Name):
                var_name = elt.id
                c_var_name = sanitize_name(var_name)
                item_expr = f"mp_obj_subscr({tuple_temp}, mp_obj_new_int({i}), MP_OBJ_SENTINEL)"

                if var_name not in locals_:
                    locals_.append(var_name)
                    self._var_types[var_name] = "mp_obj_t"
                    lines.append(f"    mp_obj_t {c_var_name} = {item_expr};")
                else:
                    var_type = self._var_types.get(var_name, "mp_obj_t")
                    if var_type == "mp_int_t":
                        lines.append(f"    {c_var_name} = mp_obj_get_int({item_expr});")
                    elif var_type == "mp_float_t":
                        lines.append(f"    {c_var_name} = mp_obj_float_get({item_expr});")
                    elif var_type == "bool":
                        lines.append(f"    {c_var_name} = mp_obj_is_true({item_expr});")
                    else:
                        lines.append(f"    {c_var_name} = {item_expr};")

        return lines

    def _translate_subscript_assign(
        self, target: ast.Subscript, value, locals_: list[str]
    ) -> list[str]:
        lines = self._flush_ir_prelude()
        obj_expr, _ = self._translate_expr(target.value, locals_)
        idx_expr, idx_type = self._translate_expr(target.slice, locals_)
        val_expr, val_type = self._translate_expr(value, locals_)

        boxed_key = self._box_value(idx_expr, idx_type)
        boxed_val = self._box_value(val_expr, val_type)

        lines.append(f"    mp_obj_subscr({obj_expr}, {boxed_key}, {boxed_val});")
        return lines

    def _translate_ann_assign(self, stmt: ast.AnnAssign, locals_: list[str]) -> list[str]:
        if not isinstance(stmt.target, ast.Name):
            return []

        var_name = stmt.target.id
        c_var_name = sanitize_name(var_name)
        c_type = self._annotation_to_c_type(stmt.annotation) if stmt.annotation else "mp_int_t"

        if stmt.value is not None:
            lines = self._flush_ir_prelude()
            expr, expr_type = self._translate_expr(stmt.value, locals_)
            more_lines = self._flush_ir_prelude()
            lines.extend(more_lines)
            expr, expr_type = self._unbox_if_needed(expr, expr_type, c_type)
            locals_.append(var_name)
            self._var_types[var_name] = c_type
            lines.append(f"    {c_type} {c_var_name} = {expr};")
            return lines
        else:
            locals_.append(var_name)
            self._var_types[var_name] = c_type
            return [f"    {c_type} {c_var_name};"]

    def _translate_aug_assign(self, stmt: ast.AugAssign, locals_: list[str]) -> list[str]:
        if not isinstance(stmt.target, ast.Name):
            return []

        var_name = stmt.target.id
        right, right_type = self._translate_expr(stmt.value, locals_)
        lines = self._flush_ir_prelude()

        # Unbox mp_obj_t for native C augmented assignment
        right, right_type = self._unbox_if_needed(right, right_type)

        op_map = {
            ast.Add: "+=",
            ast.Sub: "-=",
            ast.Mult: "*=",
            ast.Div: "/=",
            ast.Mod: "%=",
            ast.BitAnd: "&=",
            ast.BitOr: "|=",
            ast.BitXor: "^=",
            ast.LShift: "<<=",
            ast.RShift: ">>=",
        }

        c_op = op_map.get(type(stmt.op), "+=")
        lines.append(f"    {var_name} {c_op} {right};")
        return lines

    def _translate_expr(self, expr, locals_: list[str]) -> tuple[str, str]:
        if isinstance(expr, ast.Constant):
            return self._translate_constant(expr)
        elif isinstance(expr, ast.Name):
            return self._translate_name(expr, locals_)
        elif isinstance(expr, ast.BinOp):
            return self._translate_binop(expr, locals_)
        elif isinstance(expr, ast.UnaryOp):
            return self._translate_unaryop(expr, locals_)
        elif isinstance(expr, ast.Compare):
            return self._translate_compare(expr, locals_)
        elif isinstance(expr, ast.Call):
            return self._translate_call(expr, locals_)
        elif isinstance(expr, ast.IfExp):
            test, _ = self._translate_expr(expr.test, locals_)
            body, body_type = self._translate_expr(expr.body, locals_)
            orelse, _ = self._translate_expr(expr.orelse, locals_)
            return f"(({test}) ? ({body}) : ({orelse}))", body_type
        elif isinstance(expr, ast.List):
            return self._translate_list(expr, locals_)
        elif isinstance(expr, ast.Tuple):
            return self._translate_tuple(expr, locals_)
        elif isinstance(expr, ast.Set):
            return self._translate_set(expr, locals_)
        elif isinstance(expr, ast.Dict):
            return self._translate_dict(expr, locals_)
        elif isinstance(expr, ast.Subscript):
            return self._translate_subscript(expr, locals_)
        return "/* unsupported */", "mp_obj_t"

    def _translate_list(self, expr: ast.List, locals_: list[str]) -> tuple[str, str]:
        if not expr.elts:
            return "mp_obj_new_list(0, NULL)", "mp_obj_t"

        items: list[ValueIR] = []
        for elt in expr.elts:
            item_expr, item_type = self._translate_expr(elt, locals_)
            ir_type = IRType.from_c_type_str(item_type)
            items.append(NameIR(ir_type=ir_type, py_name="", c_name=item_expr))

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        self._pending_prelude.append(ListNewIR(result=result, items=items))
        return temp_name, "mp_obj_t"

    def _translate_tuple(self, expr: ast.Tuple, locals_: list[str]) -> tuple[str, str]:
        if not expr.elts:
            return "mp_const_empty_tuple", "mp_obj_t"

        items: list[ValueIR] = []
        for elt in expr.elts:
            item_expr, item_type = self._translate_expr(elt, locals_)
            ir_type = IRType.from_c_type_str(item_type)
            items.append(NameIR(ir_type=ir_type, py_name="", c_name=item_expr))

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        self._pending_prelude.append(TupleNewIR(result=result, items=items))
        return temp_name, "mp_obj_t"

    def _translate_set(self, expr: ast.Set, locals_: list[str]) -> tuple[str, str]:
        if not expr.elts:
            return "mp_obj_new_set(0, NULL)", "mp_obj_t"

        items: list[ValueIR] = []
        for elt in expr.elts:
            item_expr, item_type = self._translate_expr(elt, locals_)
            ir_type = IRType.from_c_type_str(item_type)
            items.append(NameIR(ir_type=ir_type, py_name="", c_name=item_expr))

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        self._pending_prelude.append(SetNewIR(result=result, items=items))
        return temp_name, "mp_obj_t"

    def _translate_dict(self, expr: ast.Dict, locals_: list[str]) -> tuple[str, str]:
        if not expr.keys:
            return "mp_obj_new_dict(0)", "mp_obj_t"

        entries: list[tuple[ValueIR, ValueIR]] = []
        for key, val in zip(expr.keys, expr.values):
            if key is None:
                continue
            key_expr, key_type = self._translate_expr(key, locals_)
            val_expr, val_type = self._translate_expr(val, locals_)

            # Pre-box values and wrap as OBJ-typed NameIR so ContainerEmitter
            # passes them through without double-boxing.
            boxed_key = self._box_value(key_expr, key_type)
            boxed_val = self._box_value(val_expr, val_type)
            key_ir = NameIR(ir_type=IRType.OBJ, py_name="", c_name=boxed_key)
            val_ir = NameIR(ir_type=IRType.OBJ, py_name="", c_name=boxed_val)
            entries.append((key_ir, val_ir))

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)
        self._pending_prelude.append(DictNewIR(result=result, entries=entries))
        return temp_name, "mp_obj_t"

    def _box_value(self, expr: str, expr_type: str) -> str:
        if expr_type == "mp_int_t":
            return f"mp_obj_new_int({expr})"
        elif expr_type == "mp_float_t":
            return f"mp_obj_new_float({expr})"
        elif expr_type == "bool":
            return f"({expr} ? mp_const_true : mp_const_false)"
        return expr

    def _translate_subscript(self, expr: ast.Subscript, locals_: list[str]) -> tuple[str, str]:
        value_expr, value_type = self._translate_expr(expr.value, locals_)

        if isinstance(expr.slice, ast.Slice):
            slice_c = self._translate_slice(expr.slice, locals_)
            return f"mp_obj_subscr({value_expr}, {slice_c}, MP_OBJ_SENTINEL)", "mp_obj_t"

        slice_expr, slice_type = self._translate_expr(expr.slice, locals_)
        boxed_key = self._box_value(slice_expr, slice_type)
        return f"mp_obj_subscr({value_expr}, {boxed_key}, MP_OBJ_SENTINEL)", "mp_obj_t"

    def _translate_slice(self, slice_node: ast.Slice, locals_: list[str]) -> str:
        if slice_node.lower is not None:
            lower_expr, lower_type = self._translate_expr(slice_node.lower, locals_)
            lower = self._box_value(lower_expr, lower_type)
        else:
            lower = "mp_const_none"

        if slice_node.upper is not None:
            upper_expr, upper_type = self._translate_expr(slice_node.upper, locals_)
            upper = self._box_value(upper_expr, upper_type)
        else:
            upper = "mp_const_none"

        if slice_node.step is not None:
            step_expr, step_type = self._translate_expr(slice_node.step, locals_)
            step = self._box_value(step_expr, step_type)
        else:
            step = "mp_const_none"

        return f"mp_obj_new_slice({lower}, {upper}, {step})"

    def _translate_constant(self, expr: ast.Constant) -> tuple[str, str]:
        val = expr.value
        if isinstance(val, bool):
            return ("true" if val else "false"), "bool"
        elif isinstance(val, int):
            return str(val), "mp_int_t"
        elif isinstance(val, float):
            return str(val), "mp_float_t"
        elif val is None:
            return "mp_const_none", "mp_obj_t"
        elif isinstance(val, str):
            escaped = val.replace("\\", "\\\\").replace('"', '\\"')
            return f'mp_obj_new_str("{escaped}", {len(val)})', "mp_obj_t"
        return "/* unknown constant */", "mp_obj_t"

    def _translate_name(self, expr: ast.Name, locals_: list[str]) -> tuple[str, str]:
        name = expr.id
        if name == "True":
            return "true", "bool"
        elif name == "False":
            return "false", "bool"
        elif name == "None":
            return "mp_const_none", "mp_obj_t"
        c_name = sanitize_name(name)
        var_type = self._var_types.get(name, "mp_int_t")
        return c_name, var_type

    def _translate_binop(self, expr: ast.BinOp, locals_: list[str]) -> tuple[str, str]:
        left, left_type = self._translate_expr(expr.left, locals_)
        right, right_type = self._translate_expr(expr.right, locals_)

        is_left_container = isinstance(expr.left, (ast.List, ast.Tuple, ast.Set))
        is_right_container = isinstance(expr.right, (ast.List, ast.Tuple, ast.Set))
        is_left_container_name = (
            isinstance(expr.left, ast.Name)
            and self._var_types.get(expr.left.id) == "mp_obj_t"
            and expr.left.id in self._var_types
        )

        mp_binary_op_map = {
            ast.Add: "MP_BINARY_OP_ADD",
            ast.Sub: "MP_BINARY_OP_SUBTRACT",
            ast.Mult: "MP_BINARY_OP_MULTIPLY",
        }

        if (is_left_container or is_left_container_name) and isinstance(
            expr.op, (ast.Add, ast.Mult)
        ):
            mp_op = mp_binary_op_map[type(expr.op)]
            boxed_right = self._box_value(right, right_type)
            return f"mp_binary_op({mp_op}, {left}, {boxed_right})", "mp_obj_t"

        if is_right_container and isinstance(expr.op, ast.Mult):
            mp_op = mp_binary_op_map[type(expr.op)]
            boxed_left = self._box_value(left, left_type)
            return f"mp_binary_op({mp_op}, {boxed_left}, {right})", "mp_obj_t"

        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.FloorDiv: "/",
            ast.Mod: "%",
            ast.BitAnd: "&",
            ast.BitOr: "|",
            ast.BitXor: "^",
            ast.LShift: "<<",
            ast.RShift: ">>",
        }

        c_op = op_map.get(type(expr.op), "+")

        if left_type == "mp_obj_t" or right_type == "mp_obj_t":
            target = (
                right_type
                if right_type != "mp_obj_t"
                else (left_type if left_type != "mp_obj_t" else "mp_int_t")
            )
            left, left_type = self._unbox_if_needed(left, left_type, target)
            right, right_type = self._unbox_if_needed(right, right_type, target)

        result_type = (
            "mp_float_t"
            if (left_type == "mp_float_t" or right_type == "mp_float_t")
            else "mp_int_t"
        )

        if isinstance(expr.op, ast.Pow):
            return f"/* pow({left}, {right}) - needs runtime */", result_type

        return f"({left} {c_op} {right})", result_type

    def _translate_unaryop(self, expr: ast.UnaryOp, locals_: list[str]) -> tuple[str, str]:
        operand, op_type = self._translate_expr(expr.operand, locals_)

        if isinstance(expr.op, ast.USub):
            return f"(-{operand})", op_type
        elif isinstance(expr.op, ast.Not):
            return f"(!{operand})", "bool"
        elif isinstance(expr.op, ast.UAdd):
            return f"(+{operand})", op_type
        elif isinstance(expr.op, ast.Invert):
            return f"(~{operand})", op_type
        return operand, op_type

    def _translate_compare(self, expr: ast.Compare, locals_: list[str]) -> tuple[str, str]:
        left, left_type = self._translate_expr(expr.left, locals_)

        op_map = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }

        parts = []
        prev = left
        prev_type = left_type
        for op, comparator in zip(expr.ops, expr.comparators):
            right, right_type = self._translate_expr(comparator, locals_)

            # Handle 'in' / 'not in' via MicroPython binary op
            if isinstance(op, (ast.In, ast.NotIn)):
                boxed_prev = self._box_value(prev, prev_type)
                contains_expr = (
                    f"mp_obj_is_true(mp_binary_op(MP_BINARY_OP_IN, {boxed_prev}, {right}))"
                )
                if isinstance(op, ast.NotIn):
                    parts.append(f"(!{contains_expr})")
                else:
                    parts.append(f"({contains_expr})")
                prev = right
                prev_type = right_type
                continue

            # Unbox mp_obj_t operands for native C comparison
            if prev_type == "mp_obj_t" or right_type == "mp_obj_t":
                target = (
                    right_type
                    if right_type != "mp_obj_t"
                    else (prev_type if prev_type != "mp_obj_t" else "mp_int_t")
                )
                prev, prev_type = self._unbox_if_needed(prev, prev_type, target)
                right, right_type = self._unbox_if_needed(right, right_type, target)
            c_op = op_map.get(type(op), "==")
            parts.append(f"({prev} {c_op} {right})")
            prev = right
            prev_type = right_type

        return ("(" + " && ".join(parts) + ")" if len(parts) > 1 else parts[0]), "bool"

    def _translate_call(self, expr: ast.Call, locals_: list[str]) -> tuple[str, str]:
        if isinstance(expr.func, ast.Attribute):
            return self._translate_method_call_expr(expr, locals_)

        if not isinstance(expr.func, ast.Name):
            return "/* unsupported call */", "mp_obj_t"

        func_name = expr.func.id

        if func_name in self._known_classes:
            return self._translate_class_instantiation(expr, func_name, locals_)

        args_with_types = [self._translate_expr(arg, locals_) for arg in expr.args]
        args = [a[0] for a in args_with_types]
        arg_types = [a[1] for a in args_with_types]

        builtin_map = {
            "abs": lambda a: (f"(({a[0]}) < 0 ? -({a[0]}) : ({a[0]}))", "mp_int_t"),
            "int": lambda a: (f"((mp_int_t)({a[0]}))", "mp_int_t"),
            "float": lambda a: (f"((mp_float_t)({a[0]}))", "mp_float_t"),
        }

        if func_name in builtin_map and args:
            return builtin_map[func_name](args)

        if func_name == "len" and len(args) == 1:
            return f"mp_obj_get_int(mp_obj_len({args[0]}))", "mp_int_t"

        if func_name == "range":
            boxed_args = [self._box_value(a, t) for a, t in zip(args, arg_types)]
            if len(boxed_args) == 1:
                return (
                    f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_range), {boxed_args[0]})",
                    "mp_obj_t",
                )
            elif len(boxed_args) == 2:
                return (
                    f"mp_call_function_2(MP_OBJ_FROM_PTR(&mp_type_range), {boxed_args[0]}, {boxed_args[1]})",
                    "mp_obj_t",
                )
            elif len(boxed_args) == 3:
                return (
                    f"mp_call_function_n_kw(MP_OBJ_FROM_PTR(&mp_type_range), 3, 0, "
                    f"(const mp_obj_t[]){{{boxed_args[0]}, {boxed_args[1]}, {boxed_args[2]}}})",
                    "mp_obj_t",
                )
            return "/* unsupported range() call */", "mp_obj_t"

        if func_name == "list" and len(args) == 0:
            return "mp_obj_new_list(0, NULL)", "mp_obj_t"

        if func_name == "tuple" and len(args) == 0:
            return "mp_const_empty_tuple", "mp_obj_t"

        if func_name == "tuple" and len(args) == 1:
            return (
                f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_tuple), {args[0]})",
                "mp_obj_t",
            )

        if func_name == "set" and len(args) == 0:
            return "mp_obj_new_set(0, NULL)", "mp_obj_t"

        if func_name == "set" and len(args) == 1:
            return (
                f"mp_call_function_1(MP_OBJ_FROM_PTR(&mp_type_set), {args[0]})",
                "mp_obj_t",
            )

        if func_name == "dict" and len(args) == 0:
            return "mp_obj_new_dict(0)", "mp_obj_t"

        if func_name == "dict" and len(args) == 1:
            return f"mp_obj_dict_copy({args[0]})", "mp_obj_t"

        c_func = f"{self.c_name}_{sanitize_name(func_name)}"
        args_str = ", ".join(f"mp_obj_new_int({a})" for a in args)
        call_expr = f"{c_func}({args_str})"
        return f"mp_obj_get_int({call_expr})", "mp_int_t"

    def _translate_class_instantiation(
        self, expr: ast.Call, class_name: str, locals_: list[str]
    ) -> tuple[str, str]:
        class_ir = self._known_classes[class_name]
        args = []
        for arg in expr.args:
            arg_expr, arg_type = self._translate_expr(arg, locals_)
            if arg_type == "mp_int_t":
                args.append(f"mp_obj_new_int({arg_expr})")
            elif arg_type == "mp_float_t":
                args.append(f"mp_obj_new_float({arg_expr})")
            elif arg_type == "bool":
                args.append(f"({arg_expr} ? mp_const_true : mp_const_false)")
            else:
                args.append(arg_expr)

        args_str = ", ".join(args)
        n_args = len(args)

        return (
            f"{class_ir.c_name}_make_new(&{class_ir.c_name}_type, {n_args}, 0, (const mp_obj_t[]){{{args_str}}})",
            "mp_obj_t",
        )

    def _translate_method_call_expr(self, expr: ast.Call, locals_: list[str]) -> tuple[str, str]:
        if not isinstance(expr.func, ast.Attribute):
            return "/* unsupported method call */", "mp_obj_t"

        obj_expr, _ = self._translate_expr(expr.func.value, locals_)
        method_name = expr.func.attr
        args = [self._translate_expr(arg, locals_) for arg in expr.args]

        ir_args: list[ValueIR] = []
        for arg_expr, arg_type in args:
            boxed = self._box_value(arg_expr, arg_type)
            ir_args.append(NameIR(ir_type=IRType.OBJ, py_name="", c_name=boxed))

        receiver = NameIR(ir_type=IRType.OBJ, py_name="", c_name=obj_expr)

        if method_name in VOID_RETURNING_METHODS:
            self._pending_prelude.append(
                MethodCallIR(result=None, receiver=receiver, method=method_name, args=ir_args)
            )
            return "mp_const_none", "mp_obj_t"

        temp_name = self._fresh_temp()
        result = TempIR(ir_type=IRType.OBJ, name=temp_name)

        self._pending_prelude.append(
            MethodCallIR(result=result, receiver=receiver, method=method_name, args=ir_args)
        )
        return temp_name, "mp_obj_t"

    def _generate_module(self) -> str:
        lines = [
            '#include "py/runtime.h"',
            '#include "py/obj.h"',
            '#include "py/objtype.h"',
            "#include <stddef.h>",
        ]

        if self._uses_print:
            lines.append('#include "py/mpprint.h"')

        lines.append("")

        if self._forward_decls:
            lines.extend(self._forward_decls)
            lines.append("")

        lines.extend(
            [
                "#if MICROPY_FLOAT_IMPL != MICROPY_FLOAT_IMPL_NONE",
                "static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {",
                "    if (mp_obj_is_float(obj)) {",
                "        return mp_obj_float_get(obj);",
                "    }",
                "    return (mp_float_t)mp_obj_get_int(obj);",
                "}",
                "#endif",
                "",
            ]
        )

        if self._struct_code:
            lines.extend(self._struct_code)
            lines.append("")

        for func_code in self._function_code:
            lines.append(func_code)

        for class_code in self._class_code:
            lines.append(class_code)

        lines.extend(
            [
                f"static const mp_rom_map_elem_t {self.c_name}_module_globals_table[] = {{",
                f"    {{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_{self.c_name}) }},",
            ]
        )

        for func in self.functions:
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{func.name}), MP_ROM_PTR(&{func.c_name}_obj) }},"
            )

        for class_name in self._module_ir.class_order:
            class_ir = self._module_ir.classes[class_name]
            lines.append(
                f"    {{ MP_ROM_QSTR(MP_QSTR_{class_ir.name}), MP_ROM_PTR(&{class_ir.c_name}_type) }},"
            )

        lines.extend(
            [
                "};",
                f"MP_DEFINE_CONST_DICT({self.c_name}_module_globals, {self.c_name}_module_globals_table);",
                "",
                f"const mp_obj_module_t {self.c_name}_user_cmodule = {{",
                "    .base = { &mp_type_module },",
                f"    .globals = (mp_obj_dict_t *)&{self.c_name}_module_globals,",
                "};",
                "",
                f"MP_REGISTER_MODULE(MP_QSTR_{self.c_name}, {self.c_name}_user_cmodule);",
            ]
        )

        return "\n".join(lines)


def compile_source(source: str, module_name: str = "mymodule") -> str:
    translator = TypedPythonTranslator(module_name)
    return translator.translate_source(source)
