"""Counter MVU - Interactive counter with slider and progress bar.

Demonstrates the Model-View-Update architecture with LVGL:
- Slider for direct value input (0-100 range)
- Progress bar that visually tracks the count
- Increment / Decrement / Reset buttons with click events
- Type-safe message union with exhaustive pattern matching
- Full MVU loop with native compiled code

Usage on device::

    import lvgl as lv
    lv.init_display()
    lv.init_touch()

    import counter_mvu
    app = counter_mvu.create_app()
    app.tick()
    lv.lv_screen_load(app.root_node.lv_obj)

    import time
    while True:
        app.tick()
        lv.timer_handler()
        time.sleep_ms(10)
"""

from __future__ import annotations

from dataclasses import dataclass

from lvgl_mvu.app import App
from lvgl_mvu.appliers import register_all_appliers
from lvgl_mvu.attrs import AttrRegistry
from lvgl_mvu.dsl import Bar, Button, Label, Screen, Slider
from lvgl_mvu.events import EventBinder, LvEvent
from lvgl_mvu.factories import delete_lv_obj, register_all_factories
from lvgl_mvu.layouts import HStack, VStack
from lvgl_mvu.program import Cmd, Program
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.widget import Widget


@dataclass(frozen=True)
class Increment:
    pass


@dataclass(frozen=True)
class Decrement:
    pass


@dataclass(frozen=True)
class Reset:
    pass


@dataclass(frozen=True)
class SetValue:
    value: int


Msg = Increment | Decrement | Reset | SetValue


class Model:
    count: int

    def __init__(self, count: int) -> None:
        self.count = count


def init() -> tuple[Model, Cmd]:
    return (Model(0), Cmd.none())


def update(msg: Msg, model: Model) -> tuple[Model, Cmd]:
    new_count: int
    if isinstance(msg, Increment):
        new_count = model.count + 1
        if new_count > 100:
            new_count = 100
        return (Model(new_count), Cmd.none())
    if isinstance(msg, Decrement):
        new_count = model.count - 1
        if new_count < 0:
            new_count = 0
        return (Model(new_count), Cmd.none())
    if isinstance(msg, Reset):
        return (Model(0), Cmd.none())
    if isinstance(msg, SetValue):
        value: int = msg.value
        if value < 0:
            value = 0
        if value > 100:
            value = 100
        return (Model(value), Cmd.none())
    return (model, Cmd.none())


def make_slider_msg(value: int) -> SetValue:
    return SetValue(value)


def view(model: Model) -> Widget:
    count_text: str = "Count: " + str(model.count)

    title: Widget = Label("MVU Counter").text_color(0xFFFFFF).build()

    count_color: int = 0x00E5FF
    if model.count == 0:
        count_color = 0xFFFFFF
    elif model.count >= 100:
        count_color = 0x4CAF50
    counter: Widget = Label(count_text).text_color(count_color).build()

    slider: Widget = (
        Slider(0, 100, model.count)
        .size(250, 30)
        .on_value(LvEvent.VALUE_CHANGED, make_slider_msg)
        .build()
    )

    progress: Widget = Bar(0, 100, model.count).size(250, 15).bg_color(0x3D3D5C).build()

    btn_dec: Widget = (
        Button("-").size(70, 45).bg_color(0xFF6B6B).on(LvEvent.CLICKED, Decrement()).build()
    )
    btn_reset: Widget = (
        Button("0").size(70, 45).bg_color(0x4ECDC4).on(LvEvent.CLICKED, Reset()).build()
    )
    btn_inc: Widget = (
        Button("+").size(70, 45).bg_color(0x45B7D1).on(LvEvent.CLICKED, Increment()).build()
    )

    buttons: Widget = HStack(10).width(280).with_children([btn_dec, btn_reset, btn_inc])

    stack: Widget = (
        VStack(12)
        .width(320)
        .height(320)
        .align(9, 0, -20)
        .bg_color(0x2D2D44)
        .bg_opa(255)
        .padding(15, 15, 15, 15)
        .radius(16)
        .with_children([title, counter, slider, progress, buttons])
    )

    return Screen().bg_color(0x1A1A2E).bg_opa(255).add_child(stack).build()


def create_app() -> App:
    registry: AttrRegistry = AttrRegistry()
    register_all_appliers(registry)

    reconciler: Reconciler = Reconciler(registry)
    register_all_factories(reconciler)
    reconciler.set_delete_fn(delete_lv_obj)

    program: Program = Program(init, update, view)

    app: App = App(program, reconciler)

    binder: EventBinder = EventBinder(app.dispatch)
    reconciler.set_event_binder(binder)

    return app
