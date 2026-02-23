"""Parse .pyi stub files into CLibraryDef."""

from __future__ import annotations

import ast
from pathlib import Path

from mypyc_micropython.c_bindings.c_ir import (
    CCallbackDef,
    CEnumDef,
    CFuncDef,
    CLibraryDef,
    CParamDef,
    CStructDef,
    CType,
    CTypeDef,
)

STUB_HELPER_FUNCTIONS = {"c_struct", "c_enum", "c_ptr"}

PRIMITIVE_TYPE_MAP: dict[str, CType] = {
    "c_void": CType.VOID,
    "c_int": CType.INT,
    "c_uint": CType.UINT,
    "c_int8": CType.INT8,
    "c_uint8": CType.UINT8,
    "c_int16": CType.INT16,
    "c_uint16": CType.UINT16,
    "c_int32": CType.INT32,
    "c_uint32": CType.UINT32,
    "c_float": CType.FLOAT,
    "c_double": CType.DOUBLE,
    "c_bool": CType.BOOL,
    "c_str": CType.STR,
    "int": CType.INT,
    "float": CType.DOUBLE,
    "bool": CType.BOOL,
    "str": CType.STR,
    "None": CType.VOID,
}


class StubParser:
    """Parse .pyi stub files into CLibraryDef."""

    def __init__(self) -> None:
        self._library: CLibraryDef | None = None

    def parse_file(self, path: Path) -> CLibraryDef:
        source = path.read_text()
        return self.parse_source(source, path.stem)

    def parse_source(self, source: str, name: str = "module") -> CLibraryDef:
        self._library = CLibraryDef(name=name)
        tree = ast.parse(source)

        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            self._library.docstring = module_docstring

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                self._parse_assign(node)
            elif isinstance(node, ast.ClassDef):
                self._parse_class(node)
            elif isinstance(node, ast.FunctionDef):
                self._parse_function(node)

        return self._library

    def _parse_assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1:
            return
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            return

        name = target.id

        if name == "__c_header__" and isinstance(node.value, ast.Constant):
            self._library.header = node.value.value
        elif name == "__c_include_dirs__" and isinstance(node.value, ast.List):
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self._library.include_dirs.append(elt.value)
        elif name == "__c_libraries__" and isinstance(node.value, ast.List):
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self._library.libraries.append(elt.value)
        elif name == "__c_defines__" and isinstance(node.value, ast.List):
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self._library.defines.append(elt.value)
        elif isinstance(node.value, ast.Subscript):
            if isinstance(node.value.value, ast.Name) and node.value.value.id == "Callable":
                callback = self._parse_callback_alias(name, node.value)
                if callback:
                    self._library.callbacks[name] = callback

    def _parse_callback_alias(self, name: str, subscript: ast.Subscript) -> CCallbackDef | None:
        callback = CCallbackDef(py_name=name)
        if not isinstance(subscript.slice, ast.Tuple) or len(subscript.slice.elts) != 2:
            return callback
        params_node, return_node = subscript.slice.elts
        if isinstance(params_node, ast.List):
            for i, param_ann in enumerate(params_node.elts):
                type_def = self._parse_annotation(param_ann)
                callback.params.append(CParamDef(name=f"arg{i}", type_def=type_def))


        callback.return_type = self._parse_annotation(return_node)
        # Auto-detect user_data parameter: first c_ptr[c_void] / void* param
        for i, p in enumerate(callback.params):
            if p.type_def.base_type == CType.PTR:
                callback.user_data_param = i
                break

        return callback

    def _parse_class(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                if decorator.func.id == "c_struct":
                    self._parse_struct(node, decorator)
                    return
                if decorator.func.id == "c_enum":
                    self._parse_enum(node, decorator)
                    return

    def _parse_struct(self, node: ast.ClassDef, decorator: ast.Call) -> None:
        c_name = node.name
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            c_name = decorator.args[0].value

        is_opaque = True
        for kw in decorator.keywords:
            if kw.arg == "opaque" and isinstance(kw.value, ast.Constant):
                is_opaque = kw.value.value

        struct_def = CStructDef(
            py_name=node.name,
            c_name=c_name,
            is_opaque=is_opaque,
            docstring=ast.get_docstring(node),
        )

        if not is_opaque:
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field_name = item.target.id
                    field_type = self._parse_annotation(item.annotation)
                    struct_def.fields[field_name] = field_type

        self._library.structs[node.name] = struct_def

    def _parse_enum(self, node: ast.ClassDef, decorator: ast.Call) -> None:
        c_name = node.name
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            c_name = decorator.args[0].value

        enum_def = CEnumDef(
            py_name=node.name,
            c_name=c_name,
            docstring=ast.get_docstring(node),
        )

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                val_name = item.target.id
                if item.value and isinstance(item.value, ast.Constant):
                    enum_def.values[val_name] = item.value.value
                elif item.value and isinstance(item.value, ast.BinOp):
                    try:
                        enum_def.values[val_name] = self._eval_const_expr(item.value)
                    except (ValueError, TypeError):
                        pass

        self._library.enums[node.name] = enum_def

    def _eval_const_expr(self, node: ast.expr) -> int:
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.BinOp):
            left = self._eval_const_expr(node.left)
            right = self._eval_const_expr(node.right)
            if isinstance(node.op, ast.LShift):
                return left << right
            if isinstance(node.op, ast.RShift):
                return left >> right
            if isinstance(node.op, ast.BitOr):
                return left | right
            if isinstance(node.op, ast.BitAnd):
                return left & right
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
        raise ValueError(f"Cannot evaluate: {ast.dump(node)}")

    def _parse_function(self, node: ast.FunctionDef) -> None:
        if node.name in STUB_HELPER_FUNCTIONS:
            return
        func_def = CFuncDef(
            py_name=node.name,
            c_name=node.name,
            docstring=ast.get_docstring(node),
        )

        for arg in node.args.args:
            if arg.annotation:
                param = CParamDef(
                    name=arg.arg,
                    type_def=self._parse_annotation(arg.annotation),
                )
                func_def.params.append(param)

        if node.args.vararg is not None:
            func_def.has_var_args = True

        if node.returns:
            func_def.return_type = self._parse_annotation(node.returns)

        self._library.functions[node.name] = func_def

    def _parse_annotation(self, annotation: ast.expr) -> CTypeDef:
        if isinstance(annotation, ast.Name):
            name = annotation.id
            if name in PRIMITIVE_TYPE_MAP:
                return CTypeDef(base_type=PRIMITIVE_TYPE_MAP[name])
            # Check if name matches a known callback alias
            if self._library and name in self._library.callbacks:
                return CTypeDef(base_type=CType.CALLBACK, callback_name=name)
            return CTypeDef(base_type=CType.STRUCT_PTR, struct_name=name)

        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                generic_name = annotation.value.id

                if generic_name == "c_ptr":
                    if isinstance(annotation.slice, ast.Name):
                        slice_name = annotation.slice.id
                        if slice_name in PRIMITIVE_TYPE_MAP:
                            base = PRIMITIVE_TYPE_MAP[slice_name]
                            if base == CType.VOID:
                                return CTypeDef(base_type=CType.PTR)
                        return CTypeDef(
                            base_type=CType.STRUCT_PTR,
                            struct_name=slice_name,
                        )

                if generic_name == "Callable":
                    return CTypeDef(base_type=CType.CALLBACK)

        if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
            left = self._parse_annotation(annotation.left)
            right_is_none = (
                isinstance(annotation.right, ast.Constant) and annotation.right.value is None
            ) or (isinstance(annotation.right, ast.Name) and annotation.right.id == "None")
            if right_is_none:
                left.is_optional = True
                return left
            return left

        if isinstance(annotation, ast.Constant) and annotation.value is None:
            return CTypeDef(base_type=CType.VOID)

        if isinstance(annotation, ast.Attribute):
            return CTypeDef(base_type=CType.PTR)

        return CTypeDef(base_type=CType.PTR)
