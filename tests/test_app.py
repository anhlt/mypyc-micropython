"""Tests for the LVGL MVU Runtime (Milestone 4).

Covers:
- Cmd creation and static factory methods
- Sub creation and static factory methods
- Program definition
- App initialization and lifecycle
- Message dispatch and tick processing
- View rendering via Reconciler
- Command execution (EFFECT_MSG, EFFECT_FN)
- Subscription management (setup, teardown, key matching)
- App disposal
- Full MVU integration: counter app, cascading messages
"""

from __future__ import annotations

import pytest
from lvgl_mvu.app import App
from lvgl_mvu.attrs import AttrDef, AttrKey, AttrRegistry
from lvgl_mvu.builders import WidgetBuilder
from lvgl_mvu.program import (
    EFFECT_FN,
    EFFECT_MSG,
    SUB_TIMER,
    Cmd,
    Effect,
    Program,
    Sub,
    SubDef,
)
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.widget import Widget, WidgetKey

# ---------------------------------------------------------------------------
# Mock LVGL Objects  (same pattern as test_reconciler.py)
# ---------------------------------------------------------------------------


class MockLvObj:
    """Mock LVGL object for testing."""

    obj_id: int
    parent: MockLvObj | None
    deleted: bool
    attrs: dict[int, object]

    _next_id: int = 0

    def __init__(self, parent: MockLvObj | None = None) -> None:
        MockLvObj._next_id += 1
        self.obj_id = MockLvObj._next_id
        self.parent = parent
        self.deleted = False
        self.attrs = {}

    def __repr__(self) -> str:
        return f"MockLvObj({self.obj_id})"


def mock_delete(obj: object) -> None:
    """Mock delete function."""
    if isinstance(obj, MockLvObj):
        obj.deleted = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_mock_id():
    """Reset mock object ID counter between tests."""
    MockLvObj._next_id = 0


@pytest.fixture
def attr_registry():
    """Create an AttrRegistry with mock attribute definitions."""
    registry = AttrRegistry()

    def mock_apply_text(obj: object, value: object) -> None:
        if isinstance(obj, MockLvObj):
            obj.attrs[AttrKey.TEXT] = value

    def mock_apply_bg_color(obj: object, value: object) -> None:
        if isinstance(obj, MockLvObj):
            obj.attrs[AttrKey.BG_COLOR] = value

    def mock_apply_width(obj: object, value: object) -> None:
        if isinstance(obj, MockLvObj):
            obj.attrs[AttrKey.WIDTH] = value

    registry.add(AttrDef(AttrKey.TEXT, "text", "", mock_apply_text))
    registry.add(AttrDef(AttrKey.BG_COLOR, "bg_color", 0, mock_apply_bg_color))
    registry.add(AttrDef(AttrKey.WIDTH, "width", 0, mock_apply_width))

    return registry


@pytest.fixture
def reconciler(attr_registry):
    """Create a Reconciler with mock factories."""
    rec = Reconciler(attr_registry)

    def create_screen(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_container(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_label(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    def create_button(parent: object | None) -> MockLvObj:
        return MockLvObj(parent if isinstance(parent, MockLvObj) else None)

    rec.register_factory(WidgetKey.SCREEN, create_screen)
    rec.register_factory(WidgetKey.CONTAINER, create_container)
    rec.register_factory(WidgetKey.LABEL, create_label)
    rec.register_factory(WidgetKey.BUTTON, create_button)
    rec.set_delete_fn(mock_delete)

    return rec


# ---------------------------------------------------------------------------
# Widget helpers
# ---------------------------------------------------------------------------


def _label(text: str = "") -> Widget:
    return WidgetBuilder(WidgetKey.LABEL).text(text).build()


def _screen(*children: Widget) -> Widget:
    b = WidgetBuilder(WidgetKey.SCREEN)
    for c in children:
        b = b.add_child(c)
    return b.build()


def _container(*children: Widget) -> Widget:
    b = WidgetBuilder(WidgetKey.CONTAINER)
    for c in children:
        b = b.add_child(c)
    return b.build()


# ---------------------------------------------------------------------------
# Test Cmd
# ---------------------------------------------------------------------------


class TestCmdNone:
    """Cmd.none() creates an empty command."""

    def test_cmd_none_empty(self):
        cmd = Cmd.none()
        assert len(cmd.effects) == 0

    def test_cmd_none_is_cmd(self):
        cmd = Cmd.none()
        assert isinstance(cmd, Cmd)


class TestCmdOfMsg:
    """Cmd.of_msg() creates a single EFFECT_MSG command."""

    def test_of_msg_creates_one_effect(self):
        cmd = Cmd.of_msg("increment")
        assert len(cmd.effects) == 1

    def test_of_msg_effect_is_msg_kind(self):
        cmd = Cmd.of_msg("increment")
        assert cmd.effects[0].kind == EFFECT_MSG

    def test_of_msg_stores_message(self):
        cmd = Cmd.of_msg("increment")
        assert cmd.effects[0].data == "increment"

    def test_of_msg_with_int(self):
        cmd = Cmd.of_msg(42)
        assert cmd.effects[0].data == 42

    def test_of_msg_with_tuple(self):
        cmd = Cmd.of_msg(("set_value", 100))
        assert cmd.effects[0].data == ("set_value", 100)


class TestCmdBatch:
    """Cmd.batch() combines multiple commands."""

    def test_batch_empty(self):
        cmd = Cmd.batch([])
        assert len(cmd.effects) == 0

    def test_batch_single(self):
        cmd = Cmd.batch([Cmd.of_msg("a")])
        assert len(cmd.effects) == 1
        assert cmd.effects[0].data == "a"

    def test_batch_multiple(self):
        cmd = Cmd.batch([Cmd.of_msg("a"), Cmd.of_msg("b"), Cmd.of_msg("c")])
        assert len(cmd.effects) == 3
        assert cmd.effects[0].data == "a"
        assert cmd.effects[1].data == "b"
        assert cmd.effects[2].data == "c"

    def test_batch_with_none(self):
        cmd = Cmd.batch([Cmd.none(), Cmd.of_msg("a"), Cmd.none()])
        assert len(cmd.effects) == 1
        assert cmd.effects[0].data == "a"

    def test_batch_preserves_order(self):
        cmds = [Cmd.of_msg(i) for i in range(5)]
        result = Cmd.batch(cmds)
        for i in range(5):
            assert result.effects[i].data == i


class TestCmdOfEffect:
    """Cmd.of_effect() creates a custom EFFECT_FN command."""

    def test_of_effect_creates_one_effect(self):
        fn = lambda dispatch: None  # noqa: E731
        cmd = Cmd.of_effect(fn)
        assert len(cmd.effects) == 1

    def test_of_effect_is_fn_kind(self):
        fn = lambda dispatch: None  # noqa: E731
        cmd = Cmd.of_effect(fn)
        assert cmd.effects[0].kind == EFFECT_FN

    def test_of_effect_stores_fn(self):
        fn = lambda dispatch: None  # noqa: E731
        cmd = Cmd.of_effect(fn)
        assert cmd.effects[0].data is fn


# ---------------------------------------------------------------------------
# Test Effect
# ---------------------------------------------------------------------------


class TestEffect:
    """Effect dataclass basics."""

    def test_effect_creation(self):
        e = Effect(EFFECT_MSG, "hello")
        assert e.kind == EFFECT_MSG
        assert e.data == "hello"

    def test_effect_fn_kind(self):
        fn = lambda d: None  # noqa: E731
        e = Effect(EFFECT_FN, fn)
        assert e.kind == EFFECT_FN
        assert e.data is fn


# ---------------------------------------------------------------------------
# Test Sub
# ---------------------------------------------------------------------------


class TestSubNone:
    """Sub.none() creates empty subscription."""

    def test_sub_none_empty(self):
        sub = Sub.none()
        assert len(sub.defs) == 0

    def test_sub_none_is_sub(self):
        sub = Sub.none()
        assert isinstance(sub, Sub)


class TestSubTimer:
    """Sub.timer() creates a timer subscription."""

    def test_timer_creates_one_def(self):
        sub = Sub.timer(1000, "tick")
        assert len(sub.defs) == 1

    def test_timer_kind(self):
        sub = Sub.timer(1000, "tick")
        assert sub.defs[0].kind == SUB_TIMER

    def test_timer_key(self):
        sub = Sub.timer(1000, "tick")
        assert sub.defs[0].key == "timer_1000"

    def test_timer_data(self):
        sub = Sub.timer(500, "fast_tick")
        data = sub.defs[0].data
        assert data[0] == 500
        assert data[1] == "fast_tick"


class TestSubBatch:
    """Sub.batch() combines multiple subscriptions."""

    def test_batch_empty(self):
        sub = Sub.batch([])
        assert len(sub.defs) == 0

    def test_batch_multiple(self):
        sub = Sub.batch([Sub.timer(100, "a"), Sub.timer(200, "b")])
        assert len(sub.defs) == 2
        assert sub.defs[0].key == "timer_100"
        assert sub.defs[1].key == "timer_200"

    def test_batch_with_none(self):
        sub = Sub.batch([Sub.none(), Sub.timer(100, "a")])
        assert len(sub.defs) == 1


class TestSubDef:
    """SubDef basics."""

    def test_subdef_creation(self):
        sd = SubDef(SUB_TIMER, "timer_500", (500, "tick"))
        assert sd.kind == SUB_TIMER
        assert sd.key == "timer_500"
        assert sd.data == (500, "tick")


# ---------------------------------------------------------------------------
# Test Program
# ---------------------------------------------------------------------------


class TestProgram:
    """Program definition."""

    def test_program_creation(self):
        def init():
            return (0, Cmd.none())

        def update(msg, model):
            return (model, Cmd.none())

        def view(model):
            return _label(str(model))

        prog = Program(init_fn=init, update_fn=update, view_fn=view)

        assert prog.init_fn is init
        assert prog.update_fn is update
        assert prog.view_fn is view
        assert prog.subscribe_fn is None

    def test_program_with_subscribe(self):
        def init():
            return (0, Cmd.none())

        def update(msg, model):
            return (model, Cmd.none())

        def view(model):
            return _label()

        def subscribe(model):
            return Sub.none()

        prog = Program(init_fn=init, update_fn=update, view_fn=view, subscribe_fn=subscribe)
        assert prog.subscribe_fn is subscribe


# ---------------------------------------------------------------------------
# Test App Creation
# ---------------------------------------------------------------------------


class TestAppCreation:
    """App initialization."""

    def test_app_initializes_model(self, reconciler):
        def init():
            return (42, Cmd.none())

        def update(msg, model):
            return (model, Cmd.none())

        def view(model):
            return _label(str(model))

        prog = Program(init_fn=init, update_fn=update, view_fn=view)
        app = App(prog, reconciler)

        assert app.model == 42

    def test_app_starts_not_disposed(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)

        assert not app.is_disposed()

    def test_app_root_node_is_none_before_tick(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)

        assert app.root_node is None

    def test_app_executes_init_cmd(self, reconciler):
        """Init command with of_msg queues a message."""
        prog = Program(
            init_fn=lambda: ("initial", Cmd.of_msg("start")),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        assert app.queue_length() == 1


# ---------------------------------------------------------------------------
# Test App Dispatch
# ---------------------------------------------------------------------------


class TestAppDispatch:
    """App.dispatch() message queuing."""

    def test_dispatch_queues_message(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)

        app.dispatch("hello")
        assert app.queue_length() == 1

    def test_dispatch_multiple(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)

        app.dispatch("a")
        app.dispatch("b")
        app.dispatch("c")
        assert app.queue_length() == 3

    def test_dispatch_after_dispose_ignored(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.dispose()

        app.dispatch("hello")
        assert app.queue_length() == 0


# ---------------------------------------------------------------------------
# Test App Tick
# ---------------------------------------------------------------------------


class TestAppTick:
    """App.tick() message processing."""

    def test_tick_processes_messages(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        app.dispatch("increment")
        changed = app.tick()

        assert changed is True
        assert app.model == 1
        assert app.queue_length() == 0

    def test_tick_returns_false_when_no_messages(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.tick()  # first render

        changed = app.tick()  # no messages
        assert changed is False

    def test_tick_processes_all_messages(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + msg, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        app.dispatch(10)
        app.dispatch(20)
        app.dispatch(30)
        app.tick()

        assert app.model == 60

    def test_tick_processes_messages_in_order(self, reconciler):
        """Messages should be processed FIFO."""
        history = []

        def update(msg, model):
            history.append(msg)
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)

        app.dispatch("first")
        app.dispatch("second")
        app.dispatch("third")
        app.tick()

        assert history == ["first", "second", "third"]

    def test_tick_handles_cascading_commands(self, reconciler):
        """Cmd.of_msg should be processed in the same tick."""

        def update(msg, model):
            if msg == "start":
                return (model, Cmd.of_msg("cascade"))
            elif msg == "cascade":
                return (model + 1, Cmd.none())
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        app.dispatch("start")
        app.tick()

        # Both "start" and "cascade" processed in one tick
        assert app.model == 1
        assert app.queue_length() == 0

    def test_tick_after_dispose_returns_false(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.dispose()

        assert app.tick() is False


# ---------------------------------------------------------------------------
# Test App Rendering
# ---------------------------------------------------------------------------


class TestAppRendering:
    """App view rendering via Reconciler."""

    def test_first_tick_creates_root_node(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label("hello"),
        )
        app = App(prog, reconciler)

        app.tick()

        assert app.root_node is not None
        assert app.root_node.lv_obj.attrs.get(AttrKey.TEXT) == "hello"

    def test_rendering_updates_on_model_change(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(f"Count: {model}"),
        )
        app = App(prog, reconciler)

        app.tick()  # Render "Count: 0"
        assert app.root_node.lv_obj.attrs.get(AttrKey.TEXT) == "Count: 0"

        app.dispatch("inc")
        app.tick()  # Render "Count: 1"
        assert app.root_node.lv_obj.attrs.get(AttrKey.TEXT) == "Count: 1"

    def test_rendering_preserves_lv_obj(self, reconciler):
        """Same widget type should reuse the LVGL object."""
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(f"Count: {model}"),
        )
        app = App(prog, reconciler)

        app.tick()
        original_obj = app.root_node.lv_obj

        app.dispatch("inc")
        app.tick()

        assert app.root_node.lv_obj is original_obj

    def test_rendering_with_children(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _screen(_label(f"Count: {model}")),
        )
        app = App(prog, reconciler)

        app.tick()

        assert app.root_node is not None
        assert app.root_node.child_count() == 1
        child = app.root_node.get_child(0)
        assert child.lv_obj.attrs.get(AttrKey.TEXT) == "Count: 0"

    def test_rendering_no_rerender_without_change(self, reconciler):
        """If no messages, tick should not re-render after first render."""
        render_count = [0]

        def view(model):
            render_count[0] += 1
            return _label(str(model))

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=view,
        )
        app = App(prog, reconciler)

        app.tick()  # First render
        assert render_count[0] == 1

        app.tick()  # No change
        assert render_count[0] == 1

        app.tick()  # Still no change
        assert render_count[0] == 1


# ---------------------------------------------------------------------------
# Test App Commands
# ---------------------------------------------------------------------------


class TestAppCommands:
    """App command execution (EFFECT_MSG and EFFECT_FN)."""

    def test_cmd_of_msg_dispatches(self, reconciler):
        """Cmd.of_msg should queue message for processing."""

        def update(msg, model):
            if msg == "trigger":
                return (model, Cmd.of_msg("effect_msg"))
            elif msg == "effect_msg":
                return (model + 100, Cmd.none())
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        app.dispatch("trigger")
        app.tick()

        assert app.model == 100

    def test_cmd_batch_executes_all(self, reconciler):
        """Cmd.batch should execute all sub-commands."""
        history = []

        def update(msg, model):
            history.append(msg)
            if msg == "start":
                return (model, Cmd.batch([Cmd.of_msg("a"), Cmd.of_msg("b")]))
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)

        app.dispatch("start")
        app.tick()

        assert "start" in history
        assert "a" in history
        assert "b" in history

    def test_cmd_of_effect_calls_fn(self, reconciler):
        """Cmd.of_effect should call the function with dispatch."""
        called_with = []

        def my_effect(dispatch):
            called_with.append("effect_called")
            dispatch("from_effect")

        def update(msg, model):
            if msg == "trigger":
                return (model, Cmd.of_effect(my_effect))
            elif msg == "from_effect":
                return (model + 1, Cmd.none())
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        app.dispatch("trigger")
        app.tick()

        assert "effect_called" in called_with
        assert app.model == 1

    def test_init_cmd_of_msg(self, reconciler):
        """Init command dispatches message processed on first tick."""

        def update(msg, model):
            if msg == "init_msg":
                return (model + 1, Cmd.none())
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.of_msg("init_msg")),
            update_fn=update,
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)
        app.tick()

        assert app.model == 1


# ---------------------------------------------------------------------------
# Test App Subscriptions
# ---------------------------------------------------------------------------


class TestAppSubscriptions:
    """App subscription management."""

    def test_no_subscribe_fn(self, reconciler):
        """App works fine without subscribe_fn."""
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.tick()

        assert app.is_disposed() is False

    def test_subscribe_none(self, reconciler):
        """Sub.none() produces no active subscriptions."""
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
            subscribe_fn=lambda model: Sub.none(),
        )
        app = App(prog, reconciler)
        app.tick()

        assert len(app._active_teardowns) == 0

    def test_timer_sub_without_factory(self, reconciler):
        """Timer sub without factory does not crash."""
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
            subscribe_fn=lambda model: Sub.timer(1000, "tick"),
        )
        app = App(prog, reconciler)

        # Force subscription setup via model change
        app.dispatch("inc")
        app.tick()

        # No crash, no active teardowns (no factory)
        assert len(app._active_teardowns) == 0

    def test_timer_sub_with_factory(self, reconciler):
        """Timer sub with factory creates subscription."""
        created_timers = []
        torn_down = []

        def timer_factory(interval_ms, app_ref, msg):
            created_timers.append((interval_ms, msg))

            def teardown():
                torn_down.append((interval_ms, msg))

            return teardown

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
            subscribe_fn=lambda model: Sub.timer(1000, "tick"),
        )
        app = App(prog, reconciler)
        app.set_timer_factory(timer_factory)

        # Trigger model change to setup subscriptions
        app.dispatch("inc")
        app.tick()

        assert len(created_timers) == 1
        assert created_timers[0] == (1000, "tick")

    def test_subscription_teardown_on_change(self, reconciler):
        """Subscriptions are torn down and re-created on model change."""
        torn_down = []

        def timer_factory(interval_ms, app_ref, msg):
            def teardown():
                torn_down.append(interval_ms)

            return teardown

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
            subscribe_fn=lambda model: Sub.timer(1000 + model, "tick"),
        )
        app = App(prog, reconciler)
        app.set_timer_factory(timer_factory)

        # First model change: creates timer_1001
        app.dispatch("inc")
        app.tick()
        assert len(torn_down) == 0

        # Second model change: tears down timer_1001, creates timer_1002
        app.dispatch("inc")
        app.tick()
        assert len(torn_down) == 1

    def test_subscription_keys_match_skip(self, reconciler):
        """If subscription keys don't change, skip teardown/setup."""
        setup_count = [0]

        def timer_factory(interval_ms, app_ref, msg):
            setup_count[0] += 1
            return lambda: None

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
            subscribe_fn=lambda model: Sub.timer(1000, "tick"),  # same key always
        )
        app = App(prog, reconciler)
        app.set_timer_factory(timer_factory)

        # First change
        app.dispatch("inc")
        app.tick()
        assert setup_count[0] == 1

        # Second change (same sub key) -- should skip
        app.dispatch("inc")
        app.tick()
        assert setup_count[0] == 1  # Not re-created

    def test_timer_factory_dispatches_message(self, reconciler):
        """Timer factory can dispatch messages via app reference."""
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
            subscribe_fn=lambda model: Sub.timer(100, "tick"),
        )
        app = App(prog, reconciler)

        # Manual timer simulation: dispatch the message directly
        app.dispatch("tick")
        app.tick()

        assert app.model == 1


# ---------------------------------------------------------------------------
# Test App Dispose
# ---------------------------------------------------------------------------


class TestAppDispose:
    """App.dispose() cleanup."""

    def test_dispose_marks_disposed(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.dispose()

        assert app.is_disposed()

    def test_dispose_clears_root_node(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.tick()  # Create root node
        assert app.root_node is not None

        app.dispose()
        assert app.root_node is None

    def test_dispose_deletes_lv_objects(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _screen(_label("child")),
        )
        app = App(prog, reconciler)
        app.tick()

        root_obj = app.root_node.lv_obj
        child_obj = app.root_node.get_child(0).lv_obj

        app.dispose()

        assert root_obj.deleted
        assert child_obj.deleted

    def test_dispose_clears_message_queue(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.dispatch("a")
        app.dispatch("b")

        app.dispose()
        assert app.queue_length() == 0

    def test_dispose_tears_down_subscriptions(self, reconciler):
        torn_down = []

        def timer_factory(interval_ms, app_ref, msg):
            def teardown():
                torn_down.append(interval_ms)

            return teardown

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(str(model)),
            subscribe_fn=lambda model: Sub.timer(1000, "tick"),
        )
        app = App(prog, reconciler)
        app.set_timer_factory(timer_factory)

        # Trigger subscription setup
        app.dispatch("inc")
        app.tick()

        app.dispose()
        assert len(torn_down) == 1

    def test_dispose_idempotent(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model, Cmd.none()),
            view_fn=lambda model: _label(),
        )
        app = App(prog, reconciler)
        app.dispose()
        app.dispose()  # Should not raise

        assert app.is_disposed()


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestAppIntegrationCounter:
    """Full MVU cycle: counter application."""

    def test_counter_lifecycle(self, reconciler):
        """Complete counter: init -> dispatch -> tick -> view."""

        def init():
            return (0, Cmd.none())

        def update(msg, model):
            if msg == "inc":
                return (model + 1, Cmd.none())
            elif msg == "dec":
                return (model - 1, Cmd.none())
            elif msg == "reset":
                return (0, Cmd.none())
            return (model, Cmd.none())

        def view(model):
            return _screen(_label(f"Count: {model}"))

        prog = Program(init_fn=init, update_fn=update, view_fn=view)
        app = App(prog, reconciler)

        # Initial render
        app.tick()
        assert app.root_node.get_child(0).lv_obj.attrs.get(AttrKey.TEXT) == "Count: 0"

        # Increment
        app.dispatch("inc")
        app.tick()
        assert app.model == 1
        assert app.root_node.get_child(0).lv_obj.attrs.get(AttrKey.TEXT) == "Count: 1"

        # Increment again
        app.dispatch("inc")
        app.tick()
        assert app.model == 2

        # Decrement
        app.dispatch("dec")
        app.tick()
        assert app.model == 1

        # Reset
        app.dispatch("reset")
        app.tick()
        assert app.model == 0
        assert app.root_node.get_child(0).lv_obj.attrs.get(AttrKey.TEXT) == "Count: 0"

        # Dispose
        app.dispose()
        assert app.is_disposed()

    def test_counter_multiple_increments_per_tick(self, reconciler):
        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (model + 1, Cmd.none()),
            view_fn=lambda model: _label(f"Count: {model}"),
        )
        app = App(prog, reconciler)
        app.tick()

        # Queue 5 increments
        for _ in range(5):
            app.dispatch("inc")

        app.tick()
        assert app.model == 5
        assert app.root_node.lv_obj.attrs.get(AttrKey.TEXT) == "Count: 5"


class TestAppIntegrationDynamic:
    """Dynamic UI: children change based on model."""

    def test_dynamic_children(self, reconciler):
        """View that adds/removes children based on model."""

        def view(model):
            items = []
            for i in range(model):
                items.append(_label(f"Item {i}"))
            b = WidgetBuilder(WidgetKey.CONTAINER)
            for item in items:
                b = b.add_child(item)
            return b.build()

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=lambda msg, model: (msg, Cmd.none()),
            view_fn=view,
        )
        app = App(prog, reconciler)

        # Render empty
        app.tick()
        assert app.root_node.child_count() == 0

        # Add 3 items
        app.dispatch(3)
        app.tick()
        assert app.root_node.child_count() == 3

        # Shrink to 1
        app.dispatch(1)
        app.tick()
        assert app.root_node.child_count() == 1

    def test_conditional_view(self, reconciler):
        """View changes structure based on model state."""

        def view(model):
            if model == "loading":
                return _label("Loading...")
            elif model == "error":
                return _label("Error!")
            else:
                return _label(f"Data: {model}")

        prog = Program(
            init_fn=lambda: ("loading", Cmd.none()),
            update_fn=lambda msg, model: (msg, Cmd.none()),
            view_fn=view,
        )
        app = App(prog, reconciler)

        # Initial: loading
        app.tick()
        assert app.root_node.lv_obj.attrs.get(AttrKey.TEXT) == "Loading..."

        # Transition to data
        app.dispatch("hello world")
        app.tick()
        assert app.root_node.lv_obj.attrs.get(AttrKey.TEXT) == "Data: hello world"

        # Transition to error
        app.dispatch("error")
        app.tick()
        assert app.root_node.lv_obj.attrs.get(AttrKey.TEXT) == "Error!"


class TestAppIntegrationCascade:
    """Cascading messages via Cmd.of_msg."""

    def test_multi_level_cascade(self, reconciler):
        """Chain of messages: a -> b -> c."""
        history = []

        def update(msg, model):
            history.append(msg)
            if msg == "a":
                return (model, Cmd.of_msg("b"))
            elif msg == "b":
                return (model, Cmd.of_msg("c"))
            elif msg == "c":
                return (model + 1, Cmd.none())
            return (model, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        app.dispatch("a")
        app.tick()

        assert history == ["a", "b", "c"]
        assert app.model == 1

    def test_batch_cascade(self, reconciler):
        """Batch command dispatches multiple messages."""
        history = []

        def update(msg, model):
            history.append(msg)
            if msg == "start":
                return (
                    model,
                    Cmd.batch(
                        [
                            Cmd.of_msg("x"),
                            Cmd.of_msg("y"),
                            Cmd.of_msg("z"),
                        ]
                    ),
                )
            return (model + 1, Cmd.none())

        prog = Program(
            init_fn=lambda: (0, Cmd.none()),
            update_fn=update,
            view_fn=lambda model: _label(str(model)),
        )
        app = App(prog, reconciler)

        app.dispatch("start")
        app.tick()

        assert history == ["start", "x", "y", "z"]
        assert app.model == 3  # 3 increments from x, y, z
