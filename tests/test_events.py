from __future__ import annotations

import importlib
import sys
from typing import Callable, Protocol

import pytest
from lvgl_mvu.app import App
from lvgl_mvu.attrs import AttrDef, AttrKey, AttrRegistry
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.program import Cmd, Program
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.widget import Widget, WidgetKey


class MockLvObj:
    obj_id: int
    parent: MockLvObj | None
    deleted: bool
    attrs: dict[int, object]
    callbacks: list[tuple[Callable[[object], None], int, object | None]]
    states: set[int]

    _next_id: int = 0

    def __init__(self, parent: MockLvObj | None = None) -> None:
        MockLvObj._next_id += 1
        self.obj_id = MockLvObj._next_id
        self.parent = parent
        self.deleted = False
        self.attrs = {}
        self.callbacks = []
        self.states = set()


class MockLvEvent:
    target: object

    def __init__(self, target: object) -> None:
        self.target = target


class MockLvModule:
    add_event_cb_calls: list[tuple[object, Callable[[object], None], int, object | None]]

    def __init__(self) -> None:
        self.add_event_cb_calls = []

    def lv_obj_add_event_cb(
        self,
        lv_obj: object,
        callback: Callable[[object], None],
        event_type: int,
        user_data: object | None,
    ) -> None:
        self.add_event_cb_calls.append((lv_obj, callback, event_type, user_data))
        if isinstance(lv_obj, MockLvObj):
            lv_obj.callbacks.append((callback, event_type, user_data))

    def lv_event_get_target_obj(self, event: MockLvEvent) -> object:
        return event.target

    def lv_slider_get_value(self, target: object) -> int:
        value = getattr(target, "slider_value", None)
        if isinstance(value, int):
            return value
        raise RuntimeError("not slider")

    def lv_bar_get_value(self, target: object) -> int:
        value = getattr(target, "bar_value", None)
        if isinstance(value, int):
            return value
        raise RuntimeError("not bar")

    def lv_arc_get_value(self, target: object) -> int:
        value = getattr(target, "arc_value", None)
        if isinstance(value, int):
            return value
        raise RuntimeError("not arc")

    def lv_obj_has_state(self, target: object, state: int) -> bool:
        states = getattr(target, "states", set())
        return state in states


class CapturingEventBinder:
    bind_calls: list[tuple[object, int, object]]
    unbind_calls: list[tuple[object, int, object]]

    def __init__(self, real_binder: EventBinderProtocol) -> None:
        self._real_binder = real_binder
        self.bind_calls = []
        self.unbind_calls = []

    def bind(self, lv_obj: object, event_type: int, msg: object) -> object:
        self.bind_calls.append((lv_obj, event_type, msg))

        if isinstance(msg, tuple) and len(msg) == 2:
            tag = msg[0]
            payload = msg[1]
            if tag == "value":
                return self._real_binder.bind_value(lv_obj, event_type, payload)
            if tag == "checked":
                return self._real_binder.bind_checked(lv_obj, event_type, payload)

        return self._real_binder.bind(lv_obj, event_type, msg)

    def unbind(self, lv_obj: object, event_type: int, handler: object) -> None:
        self.unbind_calls.append((lv_obj, event_type, handler))
        self._real_binder.unbind(lv_obj, event_type, handler)


def mock_delete(obj: object) -> None:
    if isinstance(obj, MockLvObj):
        obj.deleted = True


def _fire_event(lv_obj: MockLvObj, target: object | None = None, callback_index: int = -1) -> None:
    callback = lv_obj.callbacks[callback_index][0]
    event = MockLvEvent(target if target is not None else lv_obj)
    callback(event)


class EventBinderProtocol(Protocol):
    def bind(self, lv_obj: object, event_type: int, msg: object) -> object: ...

    def bind_value(self, lv_obj: object, event_type: int, msg_fn: object) -> object: ...

    def bind_checked(self, lv_obj: object, event_type: int, msg_fn: object) -> object: ...

    def unbind(self, lv_obj: object, event_type: int, handler: object) -> None: ...


def _label(text: str = "") -> Widget:
    return WidgetBuilder(WidgetKey.LABEL).text(text).build()


def _button(text: str = "", msg: object = "click") -> Widget:
    return WidgetBuilder(WidgetKey.BUTTON).text(text).on(10, msg).build()


def _slider(msg_fn: object) -> Widget:
    return WidgetBuilder(WidgetKey.SLIDER).on_value(35, msg_fn).build()


def _switch(msg_fn: object) -> Widget:
    return WidgetBuilder(WidgetKey.SWITCH).on(35, ("checked", msg_fn)).build()


def _screen(*children: Widget) -> Widget:
    b = WidgetBuilder(WidgetKey.SCREEN)
    for child in children:
        b = b.add_child(child)
    return b.build()


@pytest.fixture(autouse=True)
def reset_mock_id():
    MockLvObj._next_id = 0


@pytest.fixture
def lv_mock() -> MockLvModule:
    return MockLvModule()


@pytest.fixture
def events_mod(monkeypatch: pytest.MonkeyPatch, lv_mock: MockLvModule):
    monkeypatch.setitem(sys.modules, "lvgl", lv_mock)
    events = importlib.import_module("lvgl_mvu.events")
    return importlib.reload(events)


@pytest.fixture
def attr_registry() -> AttrRegistry:
    registry = AttrRegistry()

    def apply_text(obj: object, value: object) -> None:
        if isinstance(obj, MockLvObj):
            obj.attrs[AttrKey.TEXT] = value

    registry.add(AttrDef(AttrKey.TEXT, "text", "", apply_text))
    return registry


@pytest.fixture
def reconciler(attr_registry: AttrRegistry) -> Reconciler:
    rec = Reconciler(attr_registry)

    def create_screen(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_label(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_button(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_slider(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_switch(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    rec.register_factory(WidgetKey.SCREEN, create_screen)
    rec.register_factory(WidgetKey.LABEL, create_label)
    rec.register_factory(WidgetKey.BUTTON, create_button)
    rec.register_factory(WidgetKey.SLIDER, create_slider)
    rec.register_factory(WidgetKey.SWITCH, create_switch)
    rec.set_delete_fn(mock_delete)
    return rec


@pytest.fixture
def binder(events_mod):
    dispatched: list[object] = []
    real_binder = events_mod.EventBinder(dispatched.append)
    return real_binder, dispatched


class TestLvEventConstants:
    @pytest.mark.parametrize(
        ("name", "value"),
        [
            ("ALL", 0),
            ("PRESSED", 1),
            ("PRESSING", 2),
            ("PRESS_LOST", 3),
            ("SHORT_CLICKED", 4),
            ("SINGLE_CLICKED", 5),
            ("DOUBLE_CLICKED", 6),
            ("TRIPLE_CLICKED", 7),
            ("LONG_PRESSED", 8),
            ("LONG_PRESSED_REPEAT", 9),
            ("CLICKED", 10),
            ("RELEASED", 11),
            ("SCROLL_BEGIN", 12),
            ("SCROLL_THROW_BEGIN", 13),
            ("SCROLL_END", 14),
            ("SCROLL", 15),
            ("GESTURE", 16),
            ("KEY", 17),
            ("ROTARY", 18),
            ("FOCUSED", 19),
            ("DEFOCUSED", 20),
            ("LEAVE", 21),
            ("HIT_TEST", 22),
            ("INDEV_RESET", 23),
            ("HOVER_OVER", 24),
            ("HOVER_LEAVE", 25),
            ("COVER_CHECK", 26),
            ("REFR_EXT_DRAW_SIZE", 27),
            ("DRAW_MAIN_BEGIN", 28),
            ("DRAW_MAIN", 29),
            ("DRAW_MAIN_END", 30),
            ("DRAW_POST_BEGIN", 31),
            ("DRAW_POST", 32),
            ("DRAW_POST_END", 33),
            ("DRAW_TASK_ADDED", 34),
            ("VALUE_CHANGED", 35),
            ("INSERT", 36),
            ("REFRESH", 37),
            ("READY", 38),
            ("CANCEL", 39),
            ("STATE_CHANGED", 40),
            ("CREATE", 41),
            ("OBJ_DELETE", 42),
            ("CHILD_CHANGED", 43),
            ("CHILD_CREATED", 44),
            ("CHILD_DELETED", 45),
            ("SCREEN_UNLOAD_START", 46),
            ("SCREEN_LOAD_START", 47),
            ("SCREEN_LOADED", 48),
            ("SCREEN_UNLOADED", 49),
            ("SIZE_CHANGED", 50),
            ("STYLE_CHANGED", 51),
            ("LAYOUT_CHANGED", 52),
            ("GET_SELF_SIZE", 53),
        ],
    )
    def test_constant_values(self, events_mod, name: str, value: int):
        assert getattr(events_mod.LvEvent, name) == value


class TestHandlerKind:
    def test_msg_is_zero(self, events_mod):
        assert events_mod.HandlerKind.MSG == 0

    def test_value_is_one(self, events_mod):
        assert events_mod.HandlerKind.VALUE == 1

    def test_checked_is_two(self, events_mod):
        assert events_mod.HandlerKind.CHECKED == 2


class TestEventHandler:
    def test_creation_with_kind_and_payload(self, events_mod):
        handler = events_mod.EventHandler(events_mod.HandlerKind.MSG, "hello")
        assert handler.kind == events_mod.HandlerKind.MSG
        assert handler.payload == "hello"

    def test_active_starts_true(self, events_mod):
        handler = events_mod.EventHandler(events_mod.HandlerKind.MSG, "x")
        assert handler.active is True

    def test_deactivate_sets_active_false(self, events_mod):
        handler = events_mod.EventHandler(events_mod.HandlerKind.MSG, "x")
        handler.deactivate()
        assert handler.active is False

    def test_store_callback_stores_reference(self, events_mod):
        handler = events_mod.EventHandler(events_mod.HandlerKind.MSG, "x")
        cb = object()
        handler.store_callback(cb)
        assert handler._callback is cb


class TestEventBinderBind:
    def test_bind_returns_event_handler_with_msg_kind(self, events_mod, lv_mock):
        binder = events_mod.EventBinder(lambda msg: None)
        handler = binder.bind(MockLvObj(), events_mod.LvEvent.CLICKED, "ping")
        assert handler.kind == events_mod.HandlerKind.MSG
        assert handler.payload == "ping"

    def test_bind_calls_lv_obj_add_event_cb_with_correct_args(self, events_mod, lv_mock):
        obj = MockLvObj()
        binder = events_mod.EventBinder(lambda msg: None)
        binder.bind(obj, events_mod.LvEvent.CLICKED, "ping")

        assert len(lv_mock.add_event_cb_calls) == 1
        call = lv_mock.add_event_cb_calls[0]
        assert call[0] is obj
        assert call[2] == events_mod.LvEvent.CLICKED
        assert call[3] is None

    def test_bound_handler_fires_dispatch_when_callback_invoked(self, events_mod, lv_mock):
        dispatched: list[object] = []
        obj = MockLvObj()
        binder = events_mod.EventBinder(dispatched.append)

        binder.bind(obj, events_mod.LvEvent.CLICKED, "clicked")
        _fire_event(obj)

        assert dispatched == ["clicked"]

    def test_bound_handler_does_not_fire_when_deactivated(self, events_mod, lv_mock):
        dispatched: list[object] = []
        obj = MockLvObj()
        binder = events_mod.EventBinder(dispatched.append)

        handler = binder.bind(obj, events_mod.LvEvent.CLICKED, "clicked")
        handler.deactivate()
        _fire_event(obj)

        assert dispatched == []

    def test_multiple_binds_on_same_object(self, events_mod, lv_mock):
        dispatched: list[object] = []
        obj = MockLvObj()
        binder = events_mod.EventBinder(dispatched.append)

        binder.bind(obj, events_mod.LvEvent.CLICKED, "a")
        binder.bind(obj, events_mod.LvEvent.RELEASED, "b")

        _fire_event(obj, callback_index=0)
        _fire_event(obj, callback_index=1)

        assert len(obj.callbacks) == 2
        assert dispatched == ["a", "b"]


class TestEventBinderBindValue:
    def test_bind_value_returns_event_handler_with_value_kind(self, events_mod):
        binder = events_mod.EventBinder(lambda msg: None)
        handler = binder.bind_value(MockLvObj(), events_mod.LvEvent.VALUE_CHANGED, lambda v: v)
        assert handler.kind == events_mod.HandlerKind.VALUE

    def test_bind_value_calls_lv_obj_add_event_cb(self, events_mod, lv_mock):
        obj = MockLvObj()
        binder = events_mod.EventBinder(lambda msg: None)
        binder.bind_value(obj, events_mod.LvEvent.VALUE_CHANGED, lambda v: ("set", v))

        assert len(lv_mock.add_event_cb_calls) == 1
        assert lv_mock.add_event_cb_calls[0][0] is obj
        assert lv_mock.add_event_cb_calls[0][2] == events_mod.LvEvent.VALUE_CHANGED

    def test_value_handler_extracts_slider_value_and_dispatches(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        obj.slider_value = 42
        binder = events_mod.EventBinder(dispatched.append)
        binder.bind_value(obj, events_mod.LvEvent.VALUE_CHANGED, lambda v: ("set", v))

        _fire_event(obj)
        assert dispatched == [("set", 42)]

    def test_value_handler_extracts_bar_value_when_slider_fails(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        obj.bar_value = 33
        binder = events_mod.EventBinder(dispatched.append)
        binder.bind_value(obj, events_mod.LvEvent.VALUE_CHANGED, lambda v: ("set", v))

        _fire_event(obj)
        assert dispatched == [("set", 33)]

    def test_value_handler_extracts_arc_value_when_slider_and_bar_fail(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        obj.arc_value = 77
        binder = events_mod.EventBinder(dispatched.append)
        binder.bind_value(obj, events_mod.LvEvent.VALUE_CHANGED, lambda v: ("set", v))

        _fire_event(obj)
        assert dispatched == [("set", 77)]

    def test_value_handler_returns_zero_when_all_extractions_fail(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        binder = events_mod.EventBinder(dispatched.append)
        binder.bind_value(obj, events_mod.LvEvent.VALUE_CHANGED, lambda v: ("set", v))

        _fire_event(obj)
        assert dispatched == [("set", 0)]

    def test_value_handler_does_not_fire_when_deactivated(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        obj.slider_value = 99
        binder = events_mod.EventBinder(dispatched.append)
        handler = binder.bind_value(obj, events_mod.LvEvent.VALUE_CHANGED, lambda v: ("set", v))

        handler.deactivate()
        _fire_event(obj)
        assert dispatched == []


class TestEventBinderBindChecked:
    def test_bind_checked_returns_event_handler_with_checked_kind(self, events_mod):
        binder = events_mod.EventBinder(lambda msg: None)
        handler = binder.bind_checked(MockLvObj(), events_mod.LvEvent.VALUE_CHANGED, lambda c: c)
        assert handler.kind == events_mod.HandlerKind.CHECKED

    def test_bind_checked_calls_lv_obj_add_event_cb(self, events_mod, lv_mock):
        obj = MockLvObj()
        binder = events_mod.EventBinder(lambda msg: None)
        binder.bind_checked(obj, events_mod.LvEvent.VALUE_CHANGED, lambda c: ("set", c))

        assert len(lv_mock.add_event_cb_calls) == 1
        assert lv_mock.add_event_cb_calls[0][0] is obj
        assert lv_mock.add_event_cb_calls[0][2] == events_mod.LvEvent.VALUE_CHANGED

    def test_checked_handler_extracts_true_state(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        obj.states.add(4)
        binder = events_mod.EventBinder(dispatched.append)
        binder.bind_checked(obj, events_mod.LvEvent.VALUE_CHANGED, lambda c: ("set", c))

        _fire_event(obj)
        assert dispatched == [("set", True)]

    def test_checked_handler_extracts_false_state(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        binder = events_mod.EventBinder(dispatched.append)
        binder.bind_checked(obj, events_mod.LvEvent.VALUE_CHANGED, lambda c: ("set", c))

        _fire_event(obj)
        assert dispatched == [("set", False)]

    def test_checked_handler_does_not_fire_when_deactivated(self, events_mod):
        dispatched: list[object] = []
        obj = MockLvObj()
        obj.states.add(4)
        binder = events_mod.EventBinder(dispatched.append)
        handler = binder.bind_checked(obj, events_mod.LvEvent.VALUE_CHANGED, lambda c: ("set", c))

        handler.deactivate()
        _fire_event(obj)
        assert dispatched == []


class TestEventBinderUnbind:
    def test_unbind_deactivates_handler(self, events_mod):
        binder = events_mod.EventBinder(lambda msg: None)
        obj = MockLvObj()
        handler = binder.bind(obj, events_mod.LvEvent.CLICKED, "x")

        binder.unbind(obj, events_mod.LvEvent.CLICKED, handler)
        assert handler.active is False

    def test_unbind_with_non_event_handler_does_nothing(self, events_mod):
        binder = events_mod.EventBinder(lambda msg: None)
        binder.unbind(MockLvObj(), events_mod.LvEvent.CLICKED, "not-a-handler")


class TestDispatchHelpers:
    def test_dispatch_msg_calls_dispatch_fn_when_active(self, events_mod):
        dispatched: list[object] = []
        handler = events_mod.EventHandler(events_mod.HandlerKind.MSG, "hello")

        events_mod._dispatch_msg(handler, dispatched.append, "hello")
        assert dispatched == ["hello"]

    def test_dispatch_msg_skips_when_inactive(self, events_mod):
        dispatched: list[object] = []
        handler = events_mod.EventHandler(events_mod.HandlerKind.MSG, "hello")
        handler.deactivate()

        events_mod._dispatch_msg(handler, dispatched.append, "hello")
        assert dispatched == []

    def test_dispatch_value_calls_dispatch_fn_with_msg_fn_value(self, events_mod):
        dispatched: list[object] = []
        handler = events_mod.EventHandler(events_mod.HandlerKind.VALUE, lambda v: v)
        target = MockLvObj()
        target.slider_value = 15

        events_mod._dispatch_value(
            MockLvEvent(target),
            handler,
            dispatched.append,
            lambda value: ("value", value),
        )
        assert dispatched == [("value", 15)]

    def test_dispatch_value_skips_when_inactive(self, events_mod):
        dispatched: list[object] = []
        handler = events_mod.EventHandler(events_mod.HandlerKind.VALUE, lambda v: v)
        handler.deactivate()
        target = MockLvObj()
        target.slider_value = 15

        events_mod._dispatch_value(
            MockLvEvent(target),
            handler,
            dispatched.append,
            lambda value: ("value", value),
        )
        assert dispatched == []

    def test_dispatch_checked_calls_dispatch_fn_with_true_and_false(self, events_mod):
        dispatched: list[object] = []
        handler = events_mod.EventHandler(events_mod.HandlerKind.CHECKED, lambda v: v)
        target = MockLvObj()

        target.states.add(4)
        events_mod._dispatch_checked(
            MockLvEvent(target),
            handler,
            dispatched.append,
            lambda checked: ("checked", checked),
        )
        target.states.clear()
        events_mod._dispatch_checked(
            MockLvEvent(target),
            handler,
            dispatched.append,
            lambda checked: ("checked", checked),
        )
        assert dispatched == [("checked", True), ("checked", False)]

    def test_dispatch_checked_skips_when_inactive(self, events_mod):
        dispatched: list[object] = []
        handler = events_mod.EventHandler(events_mod.HandlerKind.CHECKED, lambda v: v)
        handler.deactivate()
        target = MockLvObj()
        target.states.add(4)

        events_mod._dispatch_checked(
            MockLvEvent(target),
            handler,
            dispatched.append,
            lambda checked: ("checked", checked),
        )
        assert dispatched == []


class TestExtractIntValue:
    def test_slider_extraction_path(self, events_mod):
        target = MockLvObj()
        target.slider_value = 21
        assert events_mod._extract_int_value(target) == 21

    def test_bar_fallback_path(self, events_mod):
        target = MockLvObj()
        target.bar_value = 31
        assert events_mod._extract_int_value(target) == 31

    def test_arc_fallback_path(self, events_mod):
        target = MockLvObj()
        target.arc_value = 41
        assert events_mod._extract_int_value(target) == 41

    def test_returns_zero_when_all_fail(self, events_mod):
        assert events_mod._extract_int_value(MockLvObj()) == 0


class TestEventIntegrationWithReconciler:
    def test_reconciler_registers_event_handlers_via_event_binder(self, events_mod, reconciler):
        dispatch_log: list[object] = []
        binder = CapturingEventBinder(events_mod.EventBinder(dispatch_log.append))
        reconciler.set_event_binder(binder)

        widget = _button("Tap", "inc")
        node = reconciler.reconcile(None, widget, None)

        assert len(binder.bind_calls) == 1
        assert 10 in node.handlers

    def test_reconciler_deactivates_old_handlers_on_reconcile(self, events_mod, reconciler):
        dispatch_log: list[object] = []
        binder = CapturingEventBinder(events_mod.EventBinder(dispatch_log.append))
        reconciler.set_event_binder(binder)

        node = reconciler.reconcile(None, _button("Tap", "old"), None)
        old_handler = node.handlers[10]
        node = reconciler.reconcile(node, _button("Tap", "new"), None)

        assert len(binder.unbind_calls) == 1
        assert old_handler.active is False

    def test_reconciler_registers_new_handlers_on_reconcile(self, events_mod, reconciler):
        dispatch_log: list[object] = []
        binder = CapturingEventBinder(events_mod.EventBinder(dispatch_log.append))
        reconciler.set_event_binder(binder)

        node = reconciler.reconcile(None, _button("Tap", "old"), None)
        old_handler = node.handlers[10]
        node = reconciler.reconcile(node, _button("Tap", "new"), None)
        new_handler = node.handlers[10]

        assert len(binder.bind_calls) == 2
        assert new_handler is not old_handler
        assert new_handler.active is True

    def test_event_handlers_cleaned_up_on_dispose(self, events_mod, reconciler):
        dispatch_log: list[object] = []
        binder = CapturingEventBinder(events_mod.EventBinder(dispatch_log.append))
        reconciler.set_event_binder(binder)

        node = reconciler.reconcile(None, _button("Tap", "inc"), None)
        reconciler.dispose_tree(node)

        assert node.handlers == {}
        assert node.is_disposed()
        assert node.lv_obj.deleted is True


class TestEventIntegrationWithApp:
    def test_button_click_dispatches_message_through_full_mvu_cycle(self, events_mod, reconciler):
        real = events_mod.EventBinder(lambda msg: None)

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (
                (model + 1, Cmd.none()) if msg == "inc" else (model, Cmd.none())
            ),
            view_fn=lambda model: _screen(_label(f"Count: {model}"), _button("+", "inc")),
        )
        app = App(prog, reconciler)

        binder = CapturingEventBinder(real)
        setattr(real, "_dispatch_fn", app.dispatch)
        reconciler.set_event_binder(binder)

        app.tick()
        button_node = app.root_node.get_child(1)
        _fire_event(button_node.lv_obj)

        assert app.queue_length() == 1
        app.tick()
        assert app.model == 1
        assert app.root_node.get_child(0).lv_obj.attrs.get(AttrKey.TEXT) == "Count: 1"

    def test_value_change_from_slider_updates_model_through_mvu(self, events_mod, reconciler):
        real = events_mod.EventBinder(lambda msg: None)
        app_ref: App | None = None

        class AppDispatchBinder(CapturingEventBinder):
            def bind(self, lv_obj: object, event_type: int, msg: object) -> object:
                self.bind_calls.append((lv_obj, event_type, msg))
                if app_ref is None:
                    raise RuntimeError("app not initialized")
                setattr(real, "_dispatch_fn", app_ref.dispatch)
                return super().bind(lv_obj, event_type, msg)

        binder = AppDispatchBinder(real)
        reconciler.set_event_binder(binder)

        def update(msg: object, model: int):
            if isinstance(msg, tuple) and len(msg) == 2 and msg[0] == "set":
                return (msg[1], Cmd.none())
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _screen(
                _label(f"Value: {model}"),
                _slider(lambda value: ("set", value)),
            ),
        )
        app_ref = App(prog, reconciler)

        app_ref.tick()
        slider_node = app_ref.root_node.get_child(1)
        slider_node.lv_obj.slider_value = 64
        _fire_event(slider_node.lv_obj)

        assert app_ref.queue_length() == 1
        app_ref.tick()
        assert app_ref.model == 64
        assert app_ref.root_node.get_child(0).lv_obj.attrs.get(AttrKey.TEXT) == "Value: 64"

    def test_checked_change_from_switch_updates_model_through_mvu(self, events_mod, reconciler):
        real = events_mod.EventBinder(lambda msg: None)
        app_ref: App | None = None

        class AppDispatchBinder(CapturingEventBinder):
            def bind(self, lv_obj: object, event_type: int, msg: object) -> object:
                self.bind_calls.append((lv_obj, event_type, msg))
                if app_ref is None:
                    raise RuntimeError("app not initialized")
                setattr(real, "_dispatch_fn", app_ref.dispatch)
                return super().bind(lv_obj, event_type, msg)

        binder = AppDispatchBinder(real)
        reconciler.set_event_binder(binder)

        def update(msg: object, model: bool):
            if isinstance(msg, tuple) and len(msg) == 2 and msg[0] == "checked":
                return (msg[1], Cmd.none())
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (False, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _screen(
                _label(f"Checked: {model}"),
                _switch(lambda checked: ("checked", checked)),
            ),
        )
        app_ref = App(prog, reconciler)

        app_ref.tick()
        switch_node = app_ref.root_node.get_child(1)
        switch_node.lv_obj.states.add(4)
        _fire_event(switch_node.lv_obj)

        assert app_ref.queue_length() == 1
        app_ref.tick()
        assert app_ref.model is True
        assert app_ref.root_node.get_child(0).lv_obj.attrs.get(AttrKey.TEXT) == "Checked: True"
