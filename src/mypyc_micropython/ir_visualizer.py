"""
IR Visualizer: Emit and visualize IR structures.

This module provides utilities to:
1. Dump IR to human-readable text format
2. Render IR as ASCII tree diagrams
3. Export IR to JSON for external tools
"""

from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from .ir import (
    AnnAssignIR,
    AssignIR,
    AttrAccessIR,
    AttrAssignIR,
    AugAssignIR,
    BinOpIR,
    BoxIR,
    BreakIR,
    CallIR,
    ClassInstantiationIR,
    ClassIR,
    CompareIR,
    ConstIR,
    ContinueIR,
    DictNewIR,
    ExceptHandlerIR,
    ExprStmtIR,
    FieldIR,
    ForIterIR,
    ForRangeIR,
    FuncIR,
    GetItemIR,
    IfExprIR,
    IfIR,
    InstrIR,
    ListCompIR,
    ListNewIR,
    MethodCallIR,
    MethodIR,
    ModuleAttrIR,
    ModuleCallIR,
    ModuleImportIR,
    ModuleIR,
    NameIR,
    ParamAttrIR,
    PassIR,
    PrintIR,
    RaiseIR,
    ReturnIR,
    SelfAttrIR,
    SelfAugAssignIR,
    SelfMethodCallIR,
    SetItemIR,
    SetNewIR,
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
    UnboxIR,
    ValueIR,
    WhileIR,
    YieldIR,
)


class IRPrinter:
    """Pretty-print IR structures in a human-readable format."""

    def __init__(self, indent_size: int = 2):
        self.indent_size = indent_size
        self._indent = 0

    def _i(self) -> str:
        return " " * (self._indent * self.indent_size)

    def _indent_inc(self) -> None:
        self._indent += 1

    def _indent_dec(self) -> None:
        self._indent -= 1

    def print_module(self, module: ModuleIR) -> str:
        lines = [f"Module: {module.name} (c_name: {module.c_name})"]
        lines.append("")

        if module.functions:
            lines.append("Functions:")
            self._indent_inc()
            for name in module.functions:
                func = module.functions[name]
                lines.append(self.print_function(func))
                lines.append("")
            self._indent_dec()

        if module.classes:
            lines.append("Classes:")
            self._indent_inc()
            for name in module.class_order:
                if name in module.classes:
                    cls = module.classes[name]
                    lines.append(self.print_class(cls))
                    lines.append("")
            self._indent_dec()

        return "\n".join(lines)

    def print_class(self, cls: ClassIR) -> str:
        lines = [f"{self._i()}Class: {cls.name} (c_name: {cls.c_name})"]
        self._indent_inc()

        if cls.base_name:
            lines.append(f"{self._i()}Base: {cls.base_name}")

        if cls.is_dataclass:
            lines.append(f"{self._i()}@dataclass")

        if cls.is_final_class:
            lines.append(f"{self._i()}@final")
        if cls.fields:
            lines.append(f"{self._i()}Fields:")
            self._indent_inc()
            for field in cls.fields:
                lines.append(self.print_field(field))
            self._indent_dec()

        if cls.methods:
            lines.append(f"{self._i()}Methods:")
            self._indent_inc()
            for name, method in cls.methods.items():
                lines.append(self.print_method(method))
            self._indent_dec()

        self._indent_dec()
        return "\n".join(lines)

    def print_field(self, field: FieldIR) -> str:
        default_str = ""
        if field.has_default:
            default_str = f" = {field.default_value}"
        final_str = " [Final]" if field.is_final else ""
        return f"{self._i()}{field.name}: {field.py_type} ({field.c_type.name}){default_str}{final_str}"

    def print_method(self, method: MethodIR) -> str:
        params = ", ".join(f"{name}: {ctype.name}" for name, ctype in method.params)
        decorators = []
        if method.is_static:
            decorators.append("@staticmethod")
        if method.is_classmethod:
            decorators.append("@classmethod")
        if method.is_property:
            decorators.append("@property")
        if method.is_final:
            decorators.append("@final")
        if method.is_private:
            decorators.append("[private]")
        dec_str = " ".join(decorators) + " " if decorators else ""
        return f"{self._i()}{dec_str}def {method.name}({params}) -> {method.return_type.name}"

    def print_method_detail(self, method: MethodIR) -> str:
        """Print detailed method info (used when MethodIR is dumped standalone)."""
        lines = []
        params = ", ".join(f"{name}: {ctype.name}" for name, ctype in method.params)
        decorators = []
        if method.is_static:
            decorators.append("@staticmethod")
        if method.is_classmethod:
            decorators.append("@classmethod")
        if method.is_property:
            decorators.append("@property")
        if method.is_final:
            decorators.append("@final")
        if method.is_private:
            decorators.append("[private]")
        for dec in decorators:
            lines.append(f"{self._i()}{dec}")
        lines.append(f"{self._i()}def {method.name}({params}) -> {method.return_type.name}:")
        lines.append(f"{self._i()}  c_name: {method.c_name}")
        lines.append(f"{self._i()}  max_temp: {method.max_temp}")
        if method.is_virtual:
            vtable_str = f", vtable_index={method.vtable_index}" if method.vtable_index >= 0 else ""
            lines.append(f"{self._i()}  virtual: True{vtable_str}")
        if method.is_special:
            lines.append(f"{self._i()}  special: True")
        lines.append(f"{self._i()}  (body from AST -- use cli to build full FuncIR)")
        return "\n".join(lines)

    def print_function(self, func: FuncIR) -> str:
        lines = []
        params = ", ".join(f"{name}: {ctype.name}" for name, ctype in func.params)
        lines.append(f"{self._i()}def {func.name}({params}) -> {func.return_type.name}:")
        lines.append(f"{self._i()}  c_name: {func.c_name}")
        lines.append(f"{self._i()}  max_temp: {func.max_temp}")

        if func.locals_:
            lines.append(
                f"{self._i()}  locals: {{{', '.join(f'{k}: {v.name}' for k, v in func.locals_.items())}}}"
            )

        if func.used_rtuples:
            lines.append(
                f"{self._i()}  rtuples: {[rt.get_c_struct_name() for rt in func.used_rtuples]}"
            )

        if func.body:
            lines.append(f"{self._i()}  body:")
            self._indent_inc()
            self._indent_inc()
            for stmt in func.body:
                lines.append(self.print_stmt(stmt))
            self._indent_dec()
            self._indent_dec()

        return "\n".join(lines)

    def print_stmt(self, stmt: StmtIR) -> str:
        if isinstance(stmt, ReturnIR):
            return self._print_return(stmt)
        elif isinstance(stmt, YieldIR):
            return self._print_yield(stmt)
        elif isinstance(stmt, IfIR):
            return self._print_if(stmt)
        elif isinstance(stmt, WhileIR):
            return self._print_while(stmt)
        elif isinstance(stmt, ForRangeIR):
            return self._print_for_range(stmt)
        elif isinstance(stmt, ForIterIR):
            return self._print_for_iter(stmt)
        elif isinstance(stmt, TryIR):
            return self._print_try(stmt)
        elif isinstance(stmt, RaiseIR):
            return self._print_raise(stmt)
        elif isinstance(stmt, AssignIR):
            return self._print_assign(stmt)
        elif isinstance(stmt, AnnAssignIR):
            return self._print_ann_assign(stmt)
        elif isinstance(stmt, AugAssignIR):
            return self._print_aug_assign(stmt)
        elif isinstance(stmt, SubscriptAssignIR):
            return self._print_subscript_assign(stmt)
        elif isinstance(stmt, AttrAssignIR):
            return self._print_attr_assign(stmt)
        elif isinstance(stmt, TupleUnpackIR):
            return self._print_tuple_unpack(stmt)
        elif isinstance(stmt, ExprStmtIR):
            return self._print_expr_stmt(stmt)
        elif isinstance(stmt, PrintIR):
            return self._print_print(stmt)
        elif isinstance(stmt, BreakIR):
            return f"{self._i()}break"
        elif isinstance(stmt, ContinueIR):
            return f"{self._i()}continue"
        elif isinstance(stmt, PassIR):
            return f"{self._i()}pass"
        elif isinstance(stmt, SelfAugAssignIR):
            return self._print_self_aug_assign(stmt)
        else:
            return f"{self._i()}/* unknown stmt: {type(stmt).__name__} */"

    def _print_return(self, stmt: ReturnIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        value_str = self.print_value(stmt.value) if stmt.value else "None"
        lines.append(f"{self._i()}return {value_str}")
        return "\n".join(lines)

    def _print_yield(self, stmt: YieldIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        value_str = self.print_value(stmt.value) if stmt.value else "None"
        lines.append(f"{self._i()}yield {value_str} [state_id={stmt.state_id}]")
        return "\n".join(lines)

    def _print_if(self, stmt: IfIR) -> str:
        lines = []
        if stmt.test_prelude:
            lines.append(f"{self._i()}# test prelude:")
            self._indent_inc()
            for instr in stmt.test_prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        lines.append(f"{self._i()}if {self.print_value(stmt.test)}:")
        self._indent_inc()
        for s in stmt.body:
            lines.append(self.print_stmt(s))
        self._indent_dec()
        if stmt.orelse:
            lines.append(f"{self._i()}else:")
            self._indent_inc()
            for s in stmt.orelse:
                lines.append(self.print_stmt(s))
            self._indent_dec()
        return "\n".join(lines)

    def _print_while(self, stmt: WhileIR) -> str:
        lines = []
        if stmt.test_prelude:
            lines.append(f"{self._i()}# test prelude:")
            self._indent_inc()
            for instr in stmt.test_prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        lines.append(f"{self._i()}while {self.print_value(stmt.test)}:")
        self._indent_inc()
        for s in stmt.body:
            lines.append(self.print_stmt(s))
        self._indent_dec()
        return "\n".join(lines)

    def _print_for_range(self, stmt: ForRangeIR) -> str:
        lines = []
        start = self.print_value(stmt.start)
        end = self.print_value(stmt.end)
        step = self.print_value(stmt.step) if stmt.step else "1"
        lines.append(f"{self._i()}for {stmt.loop_var} in range({start}, {end}, {step}):")
        self._indent_inc()
        for s in stmt.body:
            lines.append(self.print_stmt(s))
        self._indent_dec()
        return "\n".join(lines)

    def _print_for_iter(self, stmt: ForIterIR) -> str:
        lines = []
        if stmt.iter_prelude:
            lines.append(f"{self._i()}# iter prelude:")
            self._indent_inc()
            for instr in stmt.iter_prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        lines.append(f"{self._i()}for {stmt.loop_var} in {self.print_value(stmt.iterable)}:")
        self._indent_inc()
        for s in stmt.body:
            lines.append(self.print_stmt(s))
        self._indent_dec()
        return "\n".join(lines)

    def _print_try(self, stmt: TryIR) -> str:
        lines = []
        lines.append(f"{self._i()}try:")
        self._indent_inc()
        for s in stmt.body:
            lines.append(self.print_stmt(s))
        self._indent_dec()

        for handler in stmt.handlers:
            lines.append(self._print_except_handler(handler))

        if stmt.orelse:
            lines.append(f"{self._i()}else:")
            self._indent_inc()
            for s in stmt.orelse:
                lines.append(self.print_stmt(s))
            self._indent_dec()

        if stmt.finalbody:
            lines.append(f"{self._i()}finally:")
            self._indent_inc()
            for s in stmt.finalbody:
                lines.append(self.print_stmt(s))
            self._indent_dec()

        return "\n".join(lines)

    def _print_except_handler(self, handler: ExceptHandlerIR) -> str:
        lines = []
        if handler.exc_type is None:
            lines.append(f"{self._i()}except:")
        elif handler.exc_var:
            lines.append(f"{self._i()}except {handler.exc_type} as {handler.exc_var}:")
        else:
            lines.append(f"{self._i()}except {handler.exc_type}:")

        self._indent_inc()
        for s in handler.body:
            lines.append(self.print_stmt(s))
        self._indent_dec()
        return "\n".join(lines)

    def _print_raise(self, stmt: RaiseIR) -> str:
        if stmt.is_reraise:
            return f"{self._i()}raise"
        elif stmt.exc_msg:
            return f"{self._i()}raise {stmt.exc_type}({self.print_value(stmt.exc_msg)})"
        elif stmt.exc_type:
            return f"{self._i()}raise {stmt.exc_type}"
        else:
            return f"{self._i()}raise"

    def _print_assign(self, stmt: AssignIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        new_str = "(new) " if stmt.is_new_var else ""
        lines.append(f"{self._i()}{new_str}{stmt.target} = {self.print_value(stmt.value)}")
        return "\n".join(lines)

    def _print_ann_assign(self, stmt: AnnAssignIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        value_str = f" = {self.print_value(stmt.value)}" if stmt.value else ""
        lines.append(f"{self._i()}{stmt.target}: {stmt.c_type}{value_str}")
        return "\n".join(lines)

    def _print_aug_assign(self, stmt: AugAssignIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        lines.append(f"{self._i()}{stmt.target} {stmt.op} {self.print_value(stmt.value)}")
        return "\n".join(lines)

    def _print_subscript_assign(self, stmt: SubscriptAssignIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        container = self.print_value(stmt.container)
        key = self.print_value(stmt.key)
        value = self.print_value(stmt.value)
        lines.append(f"{self._i()}{container}[{key}] = {value}")
        return "\n".join(lines)

    def _print_attr_assign(self, stmt: AttrAssignIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        value = self.print_value(stmt.value)
        lines.append(f"{self._i()}self.{stmt.attr_name} = {value}")
        return "\n".join(lines)

    def _print_tuple_unpack(self, stmt: TupleUnpackIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        targets = ", ".join(name for name, _, _, _ in stmt.targets)
        lines.append(f"{self._i()}{targets} = {self.print_value(stmt.value)}")
        return "\n".join(lines)

    def _print_expr_stmt(self, stmt: ExprStmtIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        lines.append(f"{self._i()}{self.print_value(stmt.expr)}")
        return "\n".join(lines)

    def _print_print(self, stmt: PrintIR) -> str:
        lines = []
        for i, (arg, prelude) in enumerate(zip(stmt.args, stmt.preludes)):
            if prelude:
                lines.append(f"{self._i()}# arg[{i}] prelude:")
                self._indent_inc()
                for instr in prelude:
                    lines.append(self.print_instr(instr))
                self._indent_dec()
        args = ", ".join(self.print_value(a) for a in stmt.args)
        lines.append(f"{self._i()}print({args})")
        return "\n".join(lines)

    def _print_self_aug_assign(self, stmt: SelfAugAssignIR) -> str:
        lines = []
        if stmt.prelude:
            lines.append(f"{self._i()}# prelude:")
            self._indent_inc()
            for instr in stmt.prelude:
                lines.append(self.print_instr(instr))
            self._indent_dec()
        lines.append(f"{self._i()}self.{stmt.attr_name} {stmt.op} {self.print_value(stmt.value)}")
        return "\n".join(lines)

    def print_instr(self, instr: InstrIR) -> str:
        if isinstance(instr, ListNewIR):
            items = ", ".join(self.print_value(i) for i in instr.items)
            return f"{self._i()}{instr.result.name} = ListNew([{items}])"
        elif isinstance(instr, TupleNewIR):
            items = ", ".join(self.print_value(i) for i in instr.items)
            return f"{self._i()}{instr.result.name} = TupleNew(({items}))"
        elif isinstance(instr, SetNewIR):
            items = ", ".join(self.print_value(i) for i in instr.items)
            return f"{self._i()}{instr.result.name} = SetNew({{{items}}})"
        elif isinstance(instr, DictNewIR):
            entries = ", ".join(
                f"{self.print_value(k)}: {self.print_value(v)}" for k, v in instr.entries
            )
            return f"{self._i()}{instr.result.name} = DictNew({{{entries}}})"
        elif isinstance(instr, MethodCallIR):
            args = ", ".join(self.print_value(a) for a in instr.args)
            result_str = f"{instr.result.name} = " if instr.result else ""
            return (
                f"{self._i()}{result_str}{self.print_value(instr.receiver)}.{instr.method}({args})"
            )
        elif isinstance(instr, GetItemIR):
            return f"{self._i()}{instr.result.name} = {self.print_value(instr.container)}[{self.print_value(instr.key)}]"
        elif isinstance(instr, SetItemIR):
            return f"{self._i()}{self.print_value(instr.container)}[{self.print_value(instr.key)}] = {self.print_value(instr.value)}"
        elif isinstance(instr, BoxIR):
            return f"{self._i()}{instr.result.name} = Box({self.print_value(instr.value)})"
        elif isinstance(instr, UnboxIR):
            return f"{self._i()}{instr.result.name} = Unbox({self.print_value(instr.value)}, {instr.target_type.name})"
        elif isinstance(instr, AttrAccessIR):
            return (
                f"{self._i()}{instr.result.name} = {self.print_value(instr.obj)}.{instr.attr_name}"
            )
        elif isinstance(instr, ListCompIR):
            filter_str = f" if {self.print_value(instr.condition)}" if instr.condition else ""
            return f"{self._i()}{instr.result.name} = [{self.print_value(instr.element)} for {instr.loop_var} in {self.print_value(instr.iterable)}{filter_str}]"
        elif isinstance(instr, ModuleImportIR):
            return f"{self._i()}{instr.result.name} = import {instr.module_name}"
        else:
            return f"{self._i()}/* unknown instr: {type(instr).__name__} */"

    def print_value(self, value: ValueIR | None) -> str:
        if value is None:
            return "None"
        elif isinstance(value, TempIR):
            return value.name
        elif isinstance(value, ConstIR):
            if isinstance(value.value, str):
                return f'"{value.value}"'
            return repr(value.value)
        elif isinstance(value, NameIR):
            return value.py_name
        elif isinstance(value, BinOpIR):
            left = self.print_value(value.left)
            right = self.print_value(value.right)
            return f"({left} {value.op} {right})"
        elif isinstance(value, UnaryOpIR):
            operand = self.print_value(value.operand)
            return f"({value.op}{operand})"
        elif isinstance(value, CompareIR):
            parts = [self.print_value(value.left)]
            for op, comp in zip(value.ops, value.comparators):
                parts.append(op)
                parts.append(self.print_value(comp))
            return f"({' '.join(parts)})"
        elif isinstance(value, CallIR):
            args = ", ".join(self.print_value(a) for a in value.args)
            return f"{value.func_name}({args})"
        elif isinstance(value, SubscriptIR):
            return f"{self.print_value(value.value)}[{self.print_value(value.slice_)}]"
        elif isinstance(value, IfExprIR):
            return f"({self.print_value(value.body)} if {self.print_value(value.test)} else {self.print_value(value.orelse)})"
        elif isinstance(value, SelfAttrIR):
            return f"self.{value.attr_name}"
        elif isinstance(value, ParamAttrIR):
            return f"{value.param_name}.{value.attr_name}"
        elif isinstance(value, SelfMethodCallIR):
            args = ", ".join(self.print_value(a) for a in value.args)
            return f"self.{value.method_name}({args})"
        elif isinstance(value, SuperCallIR):
            args = ", ".join(self.print_value(a) for a in value.args)
            return f"super().{value.method_name}({args})"
        elif isinstance(value, ClassInstantiationIR):
            args = ", ".join(self.print_value(a) for a in value.args)
            return f"{value.class_name}({args})"
        elif isinstance(value, SliceIR):
            lower = self.print_value(value.lower) if value.lower else ""
            upper = self.print_value(value.upper) if value.upper else ""
            step = f":{self.print_value(value.step)}" if value.step else ""
            return f"{lower}:{upper}{step}"
        elif isinstance(value, ModuleCallIR):
            args = ", ".join(self.print_value(a) for a in value.args)
            return f"{value.module_name}.{value.func_name}({args})"
        elif isinstance(value, ModuleAttrIR):
            return f"{value.module_name}.{value.attr_name}"
        else:
            return f"<{type(value).__name__}>"


class IRTreePrinter:
    """Render IR as ASCII tree diagrams."""

    def __init__(self):
        self._lines: list[str] = []

    def print_tree(self, node: Any, name: str = "root") -> str:
        self._lines = []
        self._print_node(node, name, "", True)
        return "\n".join(self._lines)

    def _print_node(self, node: Any, name: str, prefix: str, is_last: bool) -> None:
        connector = "`-- " if is_last else "|-- "
        node_repr = self._node_repr(node)
        self._lines.append(f"{prefix}{connector}{name}: {node_repr}")

        if is_dataclass(node) and not isinstance(node, type):
            child_prefix = prefix + ("    " if is_last else "|   ")
            field_list = list(fields(node))
            for i, f in enumerate(field_list):
                value = getattr(node, f.name)
                if self._should_skip_field(f.name, value):
                    continue
                is_child_last = i == len(field_list) - 1
                self._print_field(value, f.name, child_prefix, is_child_last)
        elif isinstance(node, list) and node:
            child_prefix = prefix + ("    " if is_last else "|   ")
            for i, item in enumerate(node):
                is_child_last = i == len(node) - 1
                self._print_node(item, f"[{i}]", child_prefix, is_child_last)
        elif isinstance(node, dict) and node:
            child_prefix = prefix + ("    " if is_last else "|   ")
            items = list(node.items())
            for i, (k, v) in enumerate(items):
                is_child_last = i == len(items) - 1
                self._print_node(v, str(k), child_prefix, is_child_last)

    def _print_field(self, value: Any, name: str, prefix: str, is_last: bool) -> None:
        if isinstance(value, (list, dict)):
            if value:
                self._print_node(value, name, prefix, is_last)
        elif is_dataclass(value) and not isinstance(value, type):
            self._print_node(value, name, prefix, is_last)
        else:
            connector = "`-- " if is_last else "|-- "
            self._lines.append(f"{prefix}{connector}{name}: {self._simple_repr(value)}")

    def _node_repr(self, node: Any) -> str:
        if is_dataclass(node) and not isinstance(node, type):
            return type(node).__name__
        elif isinstance(node, list):
            return f"list[{len(node)}]"
        elif isinstance(node, dict):
            return f"dict[{len(node)}]"
        else:
            return self._simple_repr(node)

    def _simple_repr(self, value: Any) -> str:
        if isinstance(value, Enum):
            return f"{type(value).__name__}.{value.name}"
        elif isinstance(value, str):
            if len(value) > 40:
                return f'"{value[:37]}..."'
            return f'"{value}"'
        elif value is None:
            return "None"
        elif isinstance(value, bool):
            return str(value)
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, set):
            return f"set[{len(value)}]"
        elif isinstance(value, tuple):
            return f"tuple[{len(value)}]"
        else:
            return repr(value)

    def _should_skip_field(self, name: str, value: Any) -> bool:
        if name == "body_ast":
            return True
        if name == "ast_node":
            return True
        if isinstance(value, list) and not value:
            return True
        if isinstance(value, dict) and not value:
            return True
        if isinstance(value, set) and not value:
            return True
        return False


class IRJsonExporter:
    """Export IR to JSON format for external tools."""

    def export(self, node: Any) -> str:
        return json.dumps(self._to_dict(node), indent=2)

    def _to_dict(self, node: Any) -> Any:
        if is_dataclass(node) and not isinstance(node, type):
            result = {"_type": type(node).__name__}
            for f in fields(node):
                value = getattr(node, f.name)
                if f.name in ("body_ast", "ast_node"):
                    continue
                if isinstance(value, (list, dict, set)) and not value:
                    continue
                result[f.name] = self._to_dict(value)
            return result
        elif isinstance(node, list):
            return [self._to_dict(item) for item in node]
        elif isinstance(node, dict):
            return {str(k): self._to_dict(v) for k, v in node.items()}
        elif isinstance(node, set):
            return [self._to_dict(item) for item in sorted(node, key=str)]
        elif isinstance(node, tuple):
            return [self._to_dict(item) for item in node]
        elif isinstance(node, Enum):
            return f"{type(node).__name__}.{node.name}"
        elif isinstance(node, (str, int, float, bool, type(None))):
            return node
        else:
            return str(node)


def dump_ir(ir_node: Any, format: str = "text") -> str:
    """Dump IR node to string in specified format.

    Args:
        ir_node: Any IR node (ModuleIR, FuncIR, ClassIR, StmtIR, etc.)
        format: Output format - "text", "tree", or "json"

    Returns:
        String representation of the IR
    """
    if format == "text":
        printer = IRPrinter()
        if isinstance(ir_node, ModuleIR):
            return printer.print_module(ir_node)
        elif isinstance(ir_node, FuncIR):
            return printer.print_function(ir_node)
        elif isinstance(ir_node, ClassIR):
            return printer.print_class(ir_node)
        elif isinstance(ir_node, StmtIR):
            return printer.print_stmt(ir_node)
        elif isinstance(ir_node, ValueIR):
            return printer.print_value(ir_node)
        elif isinstance(ir_node, InstrIR):
            return printer.print_instr(ir_node)
        elif isinstance(ir_node, MethodIR):
            return printer.print_method_detail(ir_node)
        else:
            return f"<unsupported: {type(ir_node).__name__}>"
    elif format == "tree":
        tree_printer = IRTreePrinter()
        return tree_printer.print_tree(ir_node)
    elif format == "json":
        exporter = IRJsonExporter()
        return exporter.export(ir_node)
    else:
        raise ValueError(f"Unknown format: {format}. Use 'text', 'tree', or 'json'.")
