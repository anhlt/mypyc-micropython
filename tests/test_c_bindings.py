from __future__ import annotations

from mypyc_micropython.c_bindings.c_emitter import CEmitter
from mypyc_micropython.c_bindings.c_ir import CType
from mypyc_micropython.c_bindings.stub_parser import StubParser


class TestStubParser:
    def test_parse_module_metadata(self):
        source = '''
"""LVGL bindings."""

__c_header__ = "lvgl.h"
__c_include_dirs__ = ["include", "vendor/include"]
__c_libraries__ = ["lvgl", "m"]
__c_defines__ = ["USE_LVGL", "LV_COLOR_DEPTH=16"]
'''
        library = StubParser().parse_source(source, "lv")

        assert library.name == "lv"
        assert library.docstring == "LVGL bindings."
        assert library.header == "lvgl.h"
        assert library.include_dirs == ["include", "vendor/include"]
        assert library.libraries == ["lvgl", "m"]
        assert library.defines == ["USE_LVGL", "LV_COLOR_DEPTH=16"]

    def test_parse_function_with_primitives(self):
        source = """
def mix(a: c_int, b: c_uint, c: c_float, d: c_double, e: c_bool, f: c_str) -> c_int: ...
"""
        library = StubParser().parse_source(source, "mod")
        func = library.functions["mix"]

        assert len(library.functions) == 1
        assert len(func.params) == 6
        assert [p.name for p in func.params] == ["a", "b", "c", "d", "e", "f"]
        assert [p.type_def.base_type for p in func.params] == [
            CType.INT,
            CType.UINT,
            CType.FLOAT,
            CType.DOUBLE,
            CType.BOOL,
            CType.STR,
        ]
        assert func.return_type.base_type == CType.INT

    def test_parse_builtin_name_type_mapping(self):
        source = """
def as_builtin(i: int, f: float, b: bool, s: str) -> None: ...
"""
        library = StubParser().parse_source(source, "mod")
        func = library.functions["as_builtin"]

        assert [p.type_def.base_type for p in func.params] == [
            CType.INT,
            CType.DOUBLE,
            CType.BOOL,
            CType.STR,
        ]
        assert func.return_type.base_type == CType.VOID

    def test_parse_struct_opaque_default(self):
        source = """
@c_struct("widget_t")
class Widget:
    id: c_int
"""
        library = StubParser().parse_source(source, "mod")
        struct = library.structs["Widget"]

        assert len(library.structs) == 1
        assert struct.c_name == "widget_t"
        assert struct.is_opaque is True
        assert struct.fields == {}

    def test_parse_struct_non_opaque_fields(self):
        source = """
@c_struct("event_t", opaque=False)
class Event:
    code: c_int
    user_data: c_ptr[c_void]
"""
        library = StubParser().parse_source(source, "mod")
        struct = library.structs["Event"]

        assert struct.is_opaque is False
        assert set(struct.fields.keys()) == {"code", "user_data"}
        assert struct.fields["code"].base_type == CType.INT
        assert struct.fields["user_data"].base_type == CType.PTR

    def test_parse_enum_and_const_expressions(self):
        source = """
@c_enum("event_code_t")
class EventCode:
    CLICK: int = 1
    READY: int = 1 << 4
    MIXED: int = (1 << 1) | 3
"""
        library = StubParser().parse_source(source, "mod")
        enum = library.enums["EventCode"]

        assert len(library.enums) == 1
        assert enum.c_name == "event_code_t"
        assert enum.values == {"CLICK": 1, "READY": 16, "MIXED": 3}

    def test_parse_callback_alias(self):
        source = """
@c_struct("event_t")
class Event: ...

EventCallback = Callable[[c_ptr[Event], c_int], None]
"""
        library = StubParser().parse_source(source, "mod")
        callback = library.callbacks["EventCallback"]

        assert len(library.callbacks) == 1
        assert callback.py_name == "EventCallback"
        assert len(callback.params) == 2
        assert callback.params[0].type_def.base_type == CType.STRUCT_PTR
        assert callback.params[0].type_def.struct_name == "Event"
        assert callback.params[1].type_def.base_type == CType.INT
        assert callback.return_type.base_type == CType.VOID

    def test_parse_function_with_callable_parameter(self):
        source = """
def set_handler(cb: Callable[[c_int], None]) -> None: ...
"""
        library = StubParser().parse_source(source, "mod")
        func = library.functions["set_handler"]

        assert len(func.params) == 1
        assert func.params[0].type_def.base_type == CType.CALLBACK
        assert func.return_type.base_type == CType.VOID

    def test_parse_optional_struct_pointer(self):
        source = """
@c_struct("node_t")
class Node: ...

def set_parent(node: c_ptr[Node], parent: c_ptr[Node] | None) -> None: ...
"""
        library = StubParser().parse_source(source, "mod")
        func = library.functions["set_parent"]

        assert len(func.params) == 2
        assert func.params[1].type_def.base_type == CType.STRUCT_PTR
        assert func.params[1].type_def.struct_name == "Node"
        assert func.params[1].type_def.is_optional is True

    def test_parse_vararg_function(self):
        source = """
def log(fmt: c_str, *args: c_int) -> None: ...
"""
        library = StubParser().parse_source(source, "mod")
        func = library.functions["log"]

        assert func.has_var_args is True
        assert len(func.params) == 1
        assert func.params[0].name == "fmt"


class TestCEmitter:
    def test_emit_function_wrapper_int_and_return(self):
        source = """
__c_header__ = "mylib.h"

def add(a: c_int, b: c_int) -> c_int: ...
"""
        library = StubParser().parse_source(source, "calc")
        c_code = CEmitter(library).emit()

        assert '#include "mylib.h"' in c_code
        assert "typedef struct {" in c_code
        assert "} mp_c_ptr_t;" in c_code
        assert "static inline mp_obj_t wrap_ptr(void *ptr) {" in c_code
        assert "static inline void *unwrap_ptr(mp_obj_t obj) {" in c_code
        assert "static mp_obj_t add_wrapper(mp_obj_t arg0, mp_obj_t arg1)" in c_code
        assert "mp_int_t c_a = mp_obj_get_int(arg0);" in c_code
        assert "mp_int_t c_b = mp_obj_get_int(arg1);" in c_code
        assert "mp_int_t result = add(c_a, c_b);" in c_code
        assert "return mp_obj_new_int(result);" in c_code
        assert "static MP_DEFINE_CONST_FUN_OBJ_2(add_obj, add_wrapper);" in c_code

    def test_emit_module_definition_and_function_entries(self):
        source = """
def ping() -> None: ...
def scale(v: c_int) -> c_int: ...
"""
        library = StubParser().parse_source(source, "core")
        c_code = CEmitter(library).emit()

        assert "static const mp_rom_map_elem_t core_module_globals_table[] = {" in c_code
        assert "{ MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_core) }," in c_code
        assert "{ MP_ROM_QSTR(MP_QSTR_ping), MP_ROM_PTR(&ping_obj) }," in c_code
        assert "{ MP_ROM_QSTR(MP_QSTR_scale), MP_ROM_PTR(&scale_obj) }," in c_code
        assert "const mp_obj_module_t core_user_cmodule = {" in c_code
        assert "MP_REGISTER_MODULE(MP_QSTR_core, core_user_cmodule);" in c_code

    def test_emit_enum_constants(self):
        source = """
@c_enum("mode_t")
class Mode:
    OFF: int = 0
    ON: int = 1
"""
        library = StubParser().parse_source(source, "m")
        c_code = CEmitter(library).emit()

        assert "{ MP_ROM_QSTR(MP_QSTR_MODE_OFF), MP_ROM_INT(0) }," in c_code
        assert "{ MP_ROM_QSTR(MP_QSTR_MODE_ON), MP_ROM_INT(1) }," in c_code

    def test_emit_callback_support_and_wrapper(self):
        source = """
@c_struct("event_t")
class Event: ...

EventCallback = Callable[[c_ptr[Event]], None]

def register_event(target: c_ptr[Event], cb: Callable[[c_ptr[Event]], None], user_data: c_ptr[c_void]) -> None: ...
"""
        library = StubParser().parse_source(source, "events")
        c_code = CEmitter(library).emit()

        assert "static mp_obj_t wrap_Event(event_t *ptr) {" in c_code
        assert "static event_t *unwrap_Event(mp_obj_t obj) {" in c_code
        assert "#define EVENTS_MAX_CALLBACKS 32" in c_code
        assert "static mp_obj_t events_cb_registry[EVENTS_MAX_CALLBACKS];" in c_code
        assert "MP_REGISTER_ROOT_POINTER(mp_obj_t *events_cb_root);" in c_code
        assert "static void register_event_cb_trampoline(event_t *p0) {" in c_code
        assert "int idx = (int)(intptr_t)event_get_user_data(p0);" in c_code
        assert "mp_obj_t callback = args[1];" in c_code
        assert "events_cb_registry[idx] = callback;" in c_code
        assert (
            "register_event(c_target, register_event_cb_trampoline, (void *)(intptr_t)idx);"
            in c_code
        )
        assert "mp_call_function_1(cb, wrap_Event(p0));" in c_code
        assert (
            "static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(register_event_obj, 3, 3, register_event_wrapper);"
            in c_code
        )

    def test_emit_optional_struct_argument(self):
        source = """
@c_struct("node_t")
class Node: ...

def set_parent(node: c_ptr[Node], parent: c_ptr[Node] | None) -> None: ...
"""
        library = StubParser().parse_source(source, "tree")
        c_code = CEmitter(library).emit()

        assert "static mp_obj_t wrap_Node(node_t *ptr) {" in c_code
        assert "static node_t *unwrap_Node(mp_obj_t obj) {" in c_code
        assert "node_t *c_node = unwrap_Node(arg0);" in c_code
        assert "node_t *c_parent = (arg1 == mp_const_none) ? NULL : unwrap_Node(arg1);" in c_code
        assert "set_parent(c_node, c_parent);" in c_code

    def test_emit_vararg_function_is_skipped(self):
        source = """
def fixed(a: c_int) -> None: ...
def varlog(fmt: c_str, *args: c_int) -> None: ...
"""
        library = StubParser().parse_source(source, "logmod")
        c_code = CEmitter(library).emit()

        assert "fixed_wrapper" in c_code
        assert "varlog_wrapper" not in c_code
        assert "&fixed_obj" in c_code
        assert "&varlog_obj" not in c_code


class TestEndToEnd:
    def test_parse_then_emit_full_module_patterns(self):
        source = '''
"""Graphics wrapper."""
__c_header__ = "gfx.h"
__c_include_dirs__ = ["inc"]

@c_struct("gfx_obj_t")
class GfxObj: ...

@c_enum("gfx_mode_t")
class GfxMode:
    RGB: int = 0
    BGR: int = 1

GfxCallback = Callable[[c_ptr[GfxObj]], None]

def create_obj(parent: c_ptr[GfxObj] | None) -> c_ptr[GfxObj]: ...
def set_mode(obj: c_ptr[GfxObj], mode: c_int) -> None: ...
def set_cb(obj: c_ptr[GfxObj], cb: Callable[[c_ptr[GfxObj]], None], user_data: c_ptr[c_void]) -> None: ...
'''
        library = StubParser().parse_source(source, "gfx")
        c_code = CEmitter(library).emit()

        assert library.header == "gfx.h"
        assert library.include_dirs == ["inc"]
        assert len(library.structs) == 1
        assert len(library.enums) == 1
        assert len(library.callbacks) == 1
        assert len(library.functions) == 3

        assert '#include "gfx.h"' in c_code
        assert "static mp_obj_t create_obj_wrapper(mp_obj_t arg0)" in c_code
        assert "static mp_obj_t wrap_GfxObj(gfx_obj_t *ptr) {" in c_code
        assert "static gfx_obj_t *unwrap_GfxObj(mp_obj_t obj) {" in c_code
        assert (
            "gfx_obj_t *c_parent = (arg0 == mp_const_none) ? NULL : unwrap_GfxObj(arg0);" in c_code
        )
        assert "gfx_obj_t *result = create_obj(c_parent);" in c_code
        assert "return wrap_GfxObj(result);" in c_code
        assert "{ MP_ROM_QSTR(MP_QSTR_GFX_MODE_RGB), MP_ROM_INT(0) }," in c_code
        assert "{ MP_ROM_QSTR(MP_QSTR_GFX_MODE_BGR), MP_ROM_INT(1) }," in c_code
        assert "GFX_MAX_CALLBACKS" in c_code
        assert "gfx_cb_registry" in c_code
        assert "MP_REGISTER_ROOT_POINTER(mp_obj_t *gfx_cb_root);" in c_code
        assert "MP_REGISTER_MODULE(MP_QSTR_gfx, gfx_user_cmodule);" in c_code
