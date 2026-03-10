"""MVU Program definition -- Cmd, Sub, Program.

Core types for the Model-View-Update runtime:
- Effect / Cmd: Side effects that produce messages
- SubDef / Sub: Subscriptions to external events
- Program: Connects init / update / view / subscribe functions
"""

from __future__ import annotations

from typing import Callable, TypeVar

from lvgl_mvu.widget import Widget

# TypeVars for generic model and message types
# These erase to 'object' in compiled C but provide mypy type checking
Model = TypeVar("Model")
Msg = TypeVar("Msg")

# ---------------------------------------------------------------------------
# Effect kind tags
# ---------------------------------------------------------------------------

EFFECT_MSG: int = 0
EFFECT_FN: int = 1


# ---------------------------------------------------------------------------
# Effect
# ---------------------------------------------------------------------------


class Effect:
    """A single side effect to execute.

    Attributes:
        kind: EFFECT_MSG (dispatch data as message) or EFFECT_FN (call data
              with dispatch function).
        data: The message (EFFECT_MSG) or callable (EFFECT_FN).
    """

    kind: int
    data: object

    def __init__(self, kind: int, data: object) -> None:
        self.kind = kind
        self.data = data


# ---------------------------------------------------------------------------
# Cmd
# ---------------------------------------------------------------------------


class Cmd:
    """Side effects that produce messages via dispatch.

    Each Cmd carries a list of Effect instances.  The App runtime iterates
    over them after every model update.

    Attributes:
        effects: List of Effect instances.
    """

    effects: list[Effect]

    def __init__(self) -> None:
        """Create an empty Cmd (no effects)."""
        self.effects = []

    @staticmethod
    def none() -> Cmd:
        """No side effects."""
        return Cmd()

    @staticmethod
    def of_msg(msg: Msg) -> Cmd:
        """Create a command that dispatches a single message.

        Args:
            msg: The message to dispatch.
        """
        cmd = Cmd()
        cmd.effects = [Effect(EFFECT_MSG, msg)]
        return cmd

    @staticmethod
    def batch(cmds: list[Cmd]) -> Cmd:
        """Combine multiple commands into one.

        Effects are concatenated in order.

        Args:
            cmds: List of Cmd instances to combine.
        """
        result = Cmd()
        effects: list[Effect] = []
        i: int = 0
        while i < len(cmds):
            j: int = 0
            while j < len(cmds[i].effects):
                effects.append(cmds[i].effects[j])
                j += 1
            i += 1
        result.effects = effects
        return result

    @staticmethod
    def of_effect(fn: Callable[[Callable[[Msg], None]], None]) -> Cmd:
        """Create a command from a custom effect function.

        The function is called as ``fn(dispatch)`` where dispatch is a
        callable that queues messages.

        Args:
            fn: Callable with signature ``(dispatch) -> None``.
        """
        cmd = Cmd()
        cmd.effects = [Effect(EFFECT_FN, fn)]
        return cmd


# ---------------------------------------------------------------------------
# Subscription kind tags
# ---------------------------------------------------------------------------

SUB_TIMER: int = 0


# ---------------------------------------------------------------------------
# SubDef
# ---------------------------------------------------------------------------


class SubDef:
    """Single subscription definition.

    Attributes:
        kind: Subscription type tag (SUB_TIMER, ...).
        key: Unique string key for deduplication / identity comparison.
        data: Kind-specific payload (e.g. ``(interval_ms, msg)`` for timers).
    """

    kind: int
    key: str
    data: tuple[object, ...]

    def __init__(self, kind: int, key: str, data: tuple[object, ...]) -> None:
        self.kind = kind
        self.key = key
        self.data = data


# ---------------------------------------------------------------------------
# Sub
# ---------------------------------------------------------------------------


class Sub:
    """Subscriptions to external events (timers, streams, etc.).

    Subscriptions are re-evaluated whenever the model changes.  The App
    compares the new subscription keys against the current ones to decide
    which subscriptions to tear down and which to set up.

    Attributes:
        defs: List of SubDef instances.
    """

    defs: list[SubDef]

    def __init__(self) -> None:
        """Create an empty Sub (no subscriptions)."""
        self.defs = []

    @staticmethod
    def none() -> Sub:
        """No subscriptions."""
        return Sub()

    @staticmethod
    def timer(interval_ms: int, msg: Msg) -> Sub:
        """Timer subscription: dispatch msg every interval_ms milliseconds.

        Args:
            interval_ms: Timer interval in milliseconds.
            msg: Message to dispatch on each tick.
        """
        sub = Sub()
        key: str = "timer_" + str(interval_ms)
        sub.defs = [SubDef(SUB_TIMER, key, (interval_ms, msg))]
        return sub

    @staticmethod
    def batch(subs: list[Sub]) -> Sub:
        """Combine multiple subscriptions.

        Args:
            subs: List of Sub instances to combine.
        """
        result = Sub()
        defs: list[SubDef] = []
        i: int = 0
        while i < len(subs):
            j: int = 0
            while j < len(subs[i].defs):
                defs.append(subs[i].defs[j])
                j += 1
            i += 1
        result.defs = defs
        return result


# ---------------------------------------------------------------------------
# Program
# ---------------------------------------------------------------------------


class Program:
    """MVU program definition.

    Connects the four core functions of the MVU architecture:

    - ``init_fn``:  ``() -> tuple[Model, Cmd]``
    - ``update_fn``: ``(Msg, Model) -> tuple[Model, Cmd]``
    - ``view_fn``:  ``(Model) -> Widget``
    - ``subscribe_fn``: ``(Model) -> Sub``  (optional)

    Attributes:
        init_fn: Initialization function.
        update_fn: Message processing function.
        view_fn: View rendering function.
        subscribe_fn: Subscription function, or None.
    """

    init_fn: Callable[[], tuple[Model, Cmd]]
    update_fn: Callable[[Msg, Model], tuple[Model, Cmd]]
    view_fn: Callable[[Model], Widget]
    subscribe_fn: Callable[[Model], Sub] | None

    def __init__(
        self,
        init_fn: Callable[[], tuple[Model, Cmd]],
        update_fn: Callable[[Msg, Model], tuple[Model, Cmd]],
        view_fn: Callable[[Model], Widget],
        subscribe_fn: Callable[[Model], Sub] | None = None,
    ) -> None:
        self.init_fn = init_fn
        self.update_fn = update_fn
        self.view_fn = view_fn
        self.subscribe_fn = subscribe_fn
