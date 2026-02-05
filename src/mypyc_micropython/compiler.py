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

if TYPE_CHECKING:
    from mypyc.ir.module_ir import ModuleIR


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


def sanitize_name(name: str) -> str:
    result = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if result and result[0].isdigit():
        result = '_' + result
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
            errors=[f"Source file not found: {source_path}"]
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
            errors=[str(e)]
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
        self._temp_counter = 0
    
    def translate_source(self, source: str) -> str:
        tree = ast.parse(source)
        
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                self._translate_function(node)
        
        return self._generate_module()
    
    def _fresh_temp(self) -> str:
        self._temp_counter += 1
        return f"_tmp{self._temp_counter}"
    
    def _translate_function(self, node: ast.FunctionDef) -> None:
        func_name = node.name
        c_func_name = f"{self.c_name}_{sanitize_name(func_name)}"
        
        args = node.args
        num_args = len(args.args)
        arg_names = [arg.arg for arg in args.args]
        
        arg_types = []
        for arg in args.args:
            arg_types.append(self._annotation_to_c_type(arg.annotation) if arg.annotation else "mp_obj_t")
        
        return_type = self._annotation_to_c_type(node.returns) if node.returns else "mp_obj_t"
        
        c_sig, obj_def = self._build_function_signature(c_func_name, arg_names, num_args)
        
        body_lines = self._unbox_arguments(arg_names, arg_types, num_args)
        if body_lines:
            body_lines.append("")
        
        local_vars = list(arg_names)
        for stmt in node.body:
            body_lines.extend(self._translate_statement(stmt, return_type, local_vars))
        
        func_code = [c_sig + " {"] + body_lines + ["}", obj_def, ""]
        self._function_code.append("\n".join(func_code))
        
        self.functions.append(FunctionInfo(
            name=func_name,
            c_name=c_func_name,
            num_args=num_args,
            docstring=ast.get_docstring(node),
        ))
    
    def _build_function_signature(self, c_func_name: str, arg_names: list[str], num_args: int) -> tuple[str, str]:
        if num_args == 0:
            return (f"static mp_obj_t {c_func_name}(void)",
                    f"MP_DEFINE_CONST_FUN_OBJ_0({c_func_name}_obj, {c_func_name});")
        elif num_args == 1:
            return (f"static mp_obj_t {c_func_name}(mp_obj_t {arg_names[0]}_obj)",
                    f"MP_DEFINE_CONST_FUN_OBJ_1({c_func_name}_obj, {c_func_name});")
        elif num_args == 2:
            return (f"static mp_obj_t {c_func_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj)",
                    f"MP_DEFINE_CONST_FUN_OBJ_2({c_func_name}_obj, {c_func_name});")
        elif num_args == 3:
            return (f"static mp_obj_t {c_func_name}(mp_obj_t {arg_names[0]}_obj, mp_obj_t {arg_names[1]}_obj, mp_obj_t {arg_names[2]}_obj)",
                    f"MP_DEFINE_CONST_FUN_OBJ_3({c_func_name}_obj, {c_func_name});")
        else:
            return (f"static mp_obj_t {c_func_name}(size_t n_args, const mp_obj_t *args)",
                    f"MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN({c_func_name}_obj, {num_args}, {num_args}, {c_func_name});")
    
    def _unbox_arguments(self, arg_names: list[str], arg_types: list[str], num_args: int) -> list[str]:
        lines = []
        for i, (arg_name, arg_type) in enumerate(zip(arg_names, arg_types)):
            src = f"{arg_name}_obj" if num_args <= 3 else f"args[{i}]"
            
            if arg_type == "mp_int_t":
                lines.append(f"    mp_int_t {arg_name} = mp_obj_get_int({src});")
            elif arg_type == "mp_float_t":
                lines.append(f"    mp_float_t {arg_name} = mp_get_float_checked({src});")
            else:
                lines.append(f"    mp_obj_t {arg_name} = {src};")
        return lines
    
    def _annotation_to_c_type(self, annotation) -> str:
        if isinstance(annotation, ast.Name):
            type_map = {"int": "mp_int_t", "float": "mp_float_t", "bool": "bool", "str": "const char*", "None": "void"}
            return type_map.get(annotation.id, "mp_obj_t")
        return "mp_obj_t"
    
    def _translate_statement(self, stmt, return_type: str, locals_: list[str]) -> list[str]:
        if isinstance(stmt, ast.Return):
            return self._translate_return(stmt, return_type, locals_)
        elif isinstance(stmt, ast.If):
            return self._translate_if(stmt, return_type, locals_)
        elif isinstance(stmt, ast.While):
            return self._translate_while(stmt, return_type, locals_)
        elif isinstance(stmt, ast.Assign):
            return self._translate_assign(stmt, locals_)
        elif isinstance(stmt, ast.AnnAssign):
            return self._translate_ann_assign(stmt, locals_)
        elif isinstance(stmt, ast.AugAssign):
            return self._translate_aug_assign(stmt, locals_)
        elif isinstance(stmt, ast.Expr):
            expr, _ = self._translate_expr(stmt.value, locals_)
            return [f"    (void){expr};"]
        return []
    
    def _translate_return(self, stmt: ast.Return, return_type: str, locals_: list[str]) -> list[str]:
        if stmt.value is None:
            return ["    return mp_const_none;"]
        
        expr, expr_type = self._translate_expr(stmt.value, locals_)
        
        if return_type == "mp_float_t" or expr_type == "mp_float_t":
            return [f"    return mp_obj_new_float({expr});"]
        elif return_type == "mp_int_t" or expr_type == "mp_int_t":
            return [f"    return mp_obj_new_int({expr});"]
        elif return_type == "bool":
            return [f"    return {expr} ? mp_const_true : mp_const_false;"]
        return [f"    return {expr};"]
    
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
        
        for s in stmt.body:
            for line in self._translate_statement(s, return_type, locals_):
                lines.append("    " + line)
        
        lines.append("    }")
        return lines
    
    def _translate_assign(self, stmt: ast.Assign, locals_: list[str]) -> list[str]:
        if len(stmt.targets) != 1 or not isinstance(stmt.targets[0], ast.Name):
            return []
        
        var_name = stmt.targets[0].id
        expr, expr_type = self._translate_expr(stmt.value, locals_)
        
        if var_name not in locals_:
            locals_.append(var_name)
            return [f"    {expr_type} {var_name} = {expr};"]
        return [f"    {var_name} = {expr};"]
    
    def _translate_ann_assign(self, stmt: ast.AnnAssign, locals_: list[str]) -> list[str]:
        if not isinstance(stmt.target, ast.Name):
            return []
        
        var_name = stmt.target.id
        c_type = self._annotation_to_c_type(stmt.annotation) if stmt.annotation else "mp_int_t"
        
        if stmt.value is not None:
            expr, _ = self._translate_expr(stmt.value, locals_)
            locals_.append(var_name)
            return [f"    {c_type} {var_name} = {expr};"]
        else:
            locals_.append(var_name)
            return [f"    {c_type} {var_name};"]
    
    def _translate_aug_assign(self, stmt: ast.AugAssign, locals_: list[str]) -> list[str]:
        if not isinstance(stmt.target, ast.Name):
            return []
        
        var_name = stmt.target.id
        right, _ = self._translate_expr(stmt.value, locals_)
        
        op_map = {
            ast.Add: "+=", ast.Sub: "-=", ast.Mult: "*=", ast.Div: "/=",
            ast.Mod: "%=", ast.BitAnd: "&=", ast.BitOr: "|=", ast.BitXor: "^=",
            ast.LShift: "<<=", ast.RShift: ">>="
        }
        
        c_op = op_map.get(type(stmt.op), "+=")
        return [f"    {var_name} {c_op} {right};"]
    
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
        return "/* unsupported */", "mp_obj_t"
    
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
        return name, "mp_int_t"
    
    def _translate_binop(self, expr: ast.BinOp, locals_: list[str]) -> tuple[str, str]:
        left, left_type = self._translate_expr(expr.left, locals_)
        right, right_type = self._translate_expr(expr.right, locals_)
        
        op_map = {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
            ast.FloorDiv: "/", ast.Mod: "%", ast.BitAnd: "&", 
            ast.BitOr: "|", ast.BitXor: "^", ast.LShift: "<<", ast.RShift: ">>"
        }
        
        c_op = op_map.get(type(expr.op), "+")
        result_type = "mp_float_t" if (left_type == "mp_float_t" or right_type == "mp_float_t") else "mp_int_t"
        
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
        left, _ = self._translate_expr(expr.left, locals_)
        
        op_map = {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<",
            ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">="
        }
        
        parts = []
        prev = left
        for op, comparator in zip(expr.ops, expr.comparators):
            right, _ = self._translate_expr(comparator, locals_)
            c_op = op_map.get(type(op), "==")
            parts.append(f"({prev} {c_op} {right})")
            prev = right
        
        return ("(" + " && ".join(parts) + ")" if len(parts) > 1 else parts[0]), "bool"
    
    def _translate_call(self, expr: ast.Call, locals_: list[str]) -> tuple[str, str]:
        if not isinstance(expr.func, ast.Name):
            return "/* unsupported call */", "mp_obj_t"
        
        func_name = expr.func.id
        args = [self._translate_expr(arg, locals_)[0] for arg in expr.args]
        
        builtin_map = {
            "abs": lambda a: (f"(({a[0]}) < 0 ? -({a[0]}) : ({a[0]}))", "mp_int_t"),
            "int": lambda a: (f"((mp_int_t)({a[0]}))", "mp_int_t"),
            "float": lambda a: (f"((mp_float_t)({a[0]}))", "mp_float_t"),
        }
        
        if func_name in builtin_map and args:
            return builtin_map[func_name](args)
        
        c_func = f"{self.c_name}_{sanitize_name(func_name)}"
        args_str = ", ".join(f"mp_obj_new_int({a})" for a in args)
        call_expr = f"{c_func}({args_str})"
        return f"mp_obj_get_int({call_expr})", "mp_int_t"
    
    def _generate_module(self) -> str:
        lines = [
            f'#include "py/runtime.h"',
            f'#include "py/obj.h"',
            "",
            "static inline mp_float_t mp_get_float_checked(mp_obj_t obj) {",
            "    if (mp_obj_is_float(obj)) {",
            "        return mp_obj_float_get(obj);",
            "    }",
            "    return (mp_float_t)mp_obj_get_int(obj);",
            "}",
            "",
        ]
        
        for func_code in self._function_code:
            lines.append(func_code)
        
        lines.extend([
            f"static const mp_rom_map_elem_t {self.c_name}_module_globals_table[] = {{",
            f"    {{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_{self.c_name}) }},",
        ])
        
        for func in self.functions:
            lines.append(f"    {{ MP_ROM_QSTR(MP_QSTR_{func.name}), MP_ROM_PTR(&{func.c_name}_obj) }},")
        
        lines.extend([
            "};",
            f"MP_DEFINE_CONST_DICT({self.c_name}_module_globals, {self.c_name}_module_globals_table);",
            "",
            f"const mp_obj_module_t {self.c_name}_user_cmodule = {{",
            "    .base = { &mp_type_module },",
            f"    .globals = (mp_obj_dict_t *)&{self.c_name}_module_globals,",
            "};",
            "",
            f"MP_REGISTER_MODULE(MP_QSTR_{self.c_name}, {self.c_name}_user_cmodule);",
        ])
        
        return "\n".join(lines)


def compile_source(source: str, module_name: str = "mymodule") -> str:
    translator = TypedPythonTranslator(module_name)
    return translator.translate_source(source)
