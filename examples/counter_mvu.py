"""Counter MVU - Interactive counter with button events and progress bar.

Demonstrates the Model-View-Update architecture with LVGL:
- Increment / Decrement / Reset buttons with click events
- Progress bar that visually tracks the count (0-100 range)
- Full MVU loop with native compiled code

Usage on device::

    import lvgl as lv
    lv.init_display()

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

from lvgl_mvu.app import App
from lvgl_mvu.appliers import register_all_appliers
from lvgl_mvu.attrs import AttrRegistry
from lvgl_mvu.dsl import Bar, Button, Label, Screen
from lvgl_mvu.events import EventBinder, LvEvent
from lvgl_mvu.factories import delete_lv_obj, register_all_factories
from lvgl_mvu.layouts import HStack, VStack
from lvgl_mvu.program import Cmd, Program
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.widget import Widget

# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

MSG_INCREMENT: int = 1
MSG_DECREMENT: int = 2
MSG_RESET: int = 3


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class Model:
    """Application state."""

    count: int

    def __init__(self, count: int) -> None:
        self.count = count


# ---------------------------------------------------------------------------
# MVU Functions
# ---------------------------------------------------------------------------


def init() -> tuple[Model, Cmd]:
    """Initialize with count = 0."""
    return (Model(0), Cmd.none())


def update(msg: int, model: Model) -> tuple[Model, Cmd]:
    """Handle messages."""
    if msg == MSG_INCREMENT:
        return (Model(model.count + 1), Cmd.none())
    if msg == MSG_DECREMENT:
        return (Model(model.count - 1), Cmd.none())
    if msg == MSG_RESET:
        return (Model(0), Cmd.none())
    return (model, Cmd.none())


def view(model: Model) -> Widget:
    """Render the counter UI with buttons and progress bar."""
    count_text: str = "Count: " + str(model.count)

    # Title - white text
    title: Widget = Label("MVU Counter").text_color(0xFFFFFF).build()

    # Counter value - cyan (positive) or red (negative)
    count_color: int = 0x00E5FF
    if model.count < 0:
        count_color = 0xFF6B6B
    counter: Widget = Label(count_text).text_color(count_color).build()

    # Progress bar showing count (clamped to 0-100 range)
    bar_value: int = model.count
    if bar_value < 0:
        bar_value = 0
    if bar_value > 100:
        bar_value = 100
    progress: Widget = Bar(0, 100, bar_value).size(250, 20).bg_color(0x3D3D5C).build()

    # Buttons row
    btn_dec: Widget = (
        Button("-").size(70, 45).bg_color(0xFF6B6B).on(LvEvent.CLICKED, MSG_DECREMENT).build()
    )
    btn_reset: Widget = (
        Button("0").size(70, 45).bg_color(0x4ECDC4).on(LvEvent.CLICKED, MSG_RESET).build()
    )
    btn_inc: Widget = (
        Button("+").size(70, 45).bg_color(0x45B7D1).on(LvEvent.CLICKED, MSG_INCREMENT).build()
    )

    buttons: Widget = HStack(10).width(280).with_children([btn_dec, btn_reset, btn_inc])

    # VStack container - sized, centered, styled
    stack: Widget = (
        VStack(15)
        .width(320)
        .height(280)
        .align(9, 0, -30)  # LV_ALIGN_CENTER = 9, offset up by 30px
        .bg_color(0x2D2D44)  # Dark purple-gray
        .bg_opa(255)
        .padding(15, 15, 15, 15)
        .radius(16)
        .with_children([title, counter, progress, buttons])
    )

    # Screen with dark background
    return (
        Screen()
        .bg_color(0x1A1A2E)  # Dark blue
        .bg_opa(255)
        .add_child(stack)
        .build()
    )


# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------


def create_app() -> App:
    """Create and configure the MVU application with event support."""
    registry: AttrRegistry = AttrRegistry()
    register_all_appliers(registry)

    reconciler: Reconciler = Reconciler(registry)
    register_all_factories(reconciler)
    reconciler.set_delete_fn(delete_lv_obj)

    program: Program = Program(init, update, view)

    app: App = App(program, reconciler)

    # Wire up event system
    binder: EventBinder = EventBinder(app.dispatch)
    reconciler.set_event_binder(binder)

    return app
