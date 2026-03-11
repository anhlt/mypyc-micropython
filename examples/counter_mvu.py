"""Counter MVU - First Working Example.

Demonstrates the Model-View-Update architecture with LVGL.
The counter auto-increments every second, proving the MVU
loop works end-to-end with native compiled code.

Usage on device::

    import lvgl as lv
    lv.init_display()

    import counter_mvu
    app = counter_mvu.create_app()
    app.tick()
    lv.lv_screen_load(app.root_node.lv_obj)

    import time
    tick = 0
    while True:
        tick += 1
        if tick >= 100:
            app.dispatch(counter_mvu.MSG_INCREMENT)
            tick = 0
        app.tick()
        lv.timer_handler()
        time.sleep_ms(10)
"""

from __future__ import annotations

from lvgl_mvu.app import App
from lvgl_mvu.appliers import register_p0_appliers
from lvgl_mvu.attrs import AttrRegistry
from lvgl_mvu.dsl import Label, Screen
from lvgl_mvu.factories import delete_lv_obj, register_p0_factories
from lvgl_mvu.layouts import VStack
from lvgl_mvu.program import Cmd, Program
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.widget import Widget


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

MSG_INCREMENT: int = 1


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
    return (model, Cmd.none())


def view(model: Model) -> Widget:
    """Render the counter UI with nice styling."""
    count_text: str = "Count: " + str(model.count)

    # Title - white text
    title: Widget = (
        Label("MVU Counter")
        .text_color(0xFFFFFF)
        .build()
    )

    # Counter value - cyan text
    counter: Widget = (
        Label(count_text)
        .text_color(0x00E5FF)
        .build()
    )

    # VStack container - sized, centered, styled
    stack: Widget = (
        VStack(30)
        .width(300)
        .height(200)
        .align(9, 0, 0)  # LV_ALIGN_CENTER = 9
        .bg_color(0x2D2D44)  # Dark purple-gray
        .bg_opa(255)
        .padding(40, 40, 40, 40)
        .radius(16)
        .add_child(title)
        .add_child(counter)
        .build()
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
    """Create and configure the MVU application."""
    registry: AttrRegistry = AttrRegistry()
    register_p0_appliers(registry)

    reconciler: Reconciler = Reconciler(registry)
    register_p0_factories(reconciler)
    reconciler.set_delete_fn(delete_lv_obj)

    program: Program = Program(init, update, view)

    return App(program, reconciler)


