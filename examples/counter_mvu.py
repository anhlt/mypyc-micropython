"""Counter App - MVU Example with P0 Widgets.

A simple counter application demonstrating the Model-View-Update architecture
with Screen, Label, and Button widgets.

This example shows:
- Program definition with init/update/view functions
- Message-based state updates
- Declarative UI with the DSL
- Event handling via .on() method

Usage on device::

    from counter_mvu import create_app
    import lvgl as lv
    import time

    app = create_app()
    while True:
        app.tick()
        lv.timer_handler()
        time.sleep(0.01)
"""

from __future__ import annotations

from lvgl_mvu.app import App
from lvgl_mvu.appliers import register_p0_appliers
from lvgl_mvu.attrs import AttrRegistry
from lvgl_mvu.dsl import Button, Label, Screen
from lvgl_mvu.factories import delete_lv_obj, register_p0_factories
from lvgl_mvu.layouts import HStack, VStack
from lvgl_mvu.program import Cmd, Program
from lvgl_mvu.reconciler import Reconciler
from lvgl_mvu.widget import Widget

# LVGL event constants
LV_EVENT_CLICKED: int = 0x07

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class Model:
    """Application state."""

    count: int

    def __init__(self, count: int) -> None:
        self.count = count


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


MSG_INCREMENT: int = 1
MSG_DECREMENT: int = 2
MSG_RESET: int = 3


# ---------------------------------------------------------------------------
# MVU Functions
# ---------------------------------------------------------------------------


def init() -> tuple[Model, Cmd]:
    """Initialize the application state.

    Returns:
        Tuple of (initial model, initial command).
    """
    return (Model(0), Cmd.none())


def update(msg: int, model: Model) -> tuple[Model, Cmd]:
    """Update the model based on a message.

    Args:
        msg: The message to process.
        model: The current model state.

    Returns:
        Tuple of (new model, command to execute).
    """
    if msg == MSG_INCREMENT:
        return (Model(model.count + 1), Cmd.none())
    elif msg == MSG_DECREMENT:
        return (Model(model.count - 1), Cmd.none())
    elif msg == MSG_RESET:
        return (Model(0), Cmd.none())
    return (model, Cmd.none())


def view(model: Model) -> Widget:
    """Render the UI based on the model.

    Args:
        model: The current model state.

    Returns:
        A Widget tree describing the UI.
    """
    count_text: str = "Count: " + str(model.count)

    return Screen()(
        VStack(spacing=20).size(320, 240)(
            # Title
            Label("MVU Counter Demo").text_color(0xFFFFFF).build(),
            # Count display
            Label(count_text).text_color(0x00FF00).build(),
            # Button row
            HStack(spacing=10)(
                Button("-").size(60, 40).on(LV_EVENT_CLICKED, MSG_DECREMENT).build(),
                Button("Reset").size(80, 40).on(LV_EVENT_CLICKED, MSG_RESET).build(),
                Button("+").size(60, 40).on(LV_EVENT_CLICKED, MSG_INCREMENT).build(),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------


def create_app() -> App:
    """Create and configure the MVU application.

    Returns:
        Configured App instance ready to run.
    """
    # Create attribute registry and register P0 appliers
    registry: AttrRegistry = AttrRegistry()
    register_p0_appliers(registry)

    # Create reconciler and register P0 factories
    reconciler: Reconciler = Reconciler(registry)
    register_p0_factories(reconciler)
    reconciler.set_delete_fn(delete_lv_obj)

    # Create program definition
    program: Program = Program(init, update, view)

    # Create and return app
    return App(program, reconciler)
