"""MVU Application runtime -- message queue, tick loop, reconciliation.

The App class is the main runtime that:
1. Initializes model and executes the init command
2. Processes queued messages through the update function
3. Re-renders the view when the model changes
4. Reconciles the widget tree with LVGL objects via the Reconciler
5. Manages subscriptions based on model state
"""

from __future__ import annotations

from collections.abc import Callable

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
from lvgl_mvu.viewnode import ViewNode
from lvgl_mvu.widget import Widget


class App:
    """MVU application runner.

    Manages the full MVU lifecycle: model state, message dispatch,
    view rendering via a Reconciler, and subscription management.

    Attributes:
        program: The Program definition.
        reconciler: The Reconciler for widget tree management.
        model: Current application state (opaque to the framework).
        root_node: Root ViewNode, or None before first render.
    """

    program: Program
    reconciler: Reconciler
    model: object
    root_node: ViewNode | None
    _msg_queue: list[object]
    _root_lv_obj: object | None
    _active_teardowns: list[object]
    _sub_keys: list[str]
    _timer_factory: Callable[[int, App, object], Callable[[], None]] | None
    _disposed: bool

    def __init__(
        self,
        program: Program,
        reconciler: Reconciler,
        root_lv_obj: object | None = None,
    ) -> None:
        """Create a new App.

        Calls ``program.init_fn()`` to obtain the initial model and command.
        The command is executed immediately (which may queue messages).

        Args:
            program: The MVU Program definition.
            reconciler: Reconciler with registered widget factories.
            root_lv_obj: Parent LVGL object for the root widget.
        """
        self.program = program
        self.reconciler = reconciler
        self.model = None
        self.root_node = None
        self._msg_queue = []
        self._root_lv_obj = root_lv_obj
        self._active_teardowns = []
        self._sub_keys = []
        self._timer_factory = None
        self._disposed = False

        # Initialize model and execute init command
        init_result = program.init_fn()
        self.model = init_result[0]
        init_cmd: Cmd = init_result[1]
        self._execute_cmd(init_cmd)

        # Setup initial subscriptions
        self._setup_subscriptions()

    def set_timer_factory(self, factory: Callable[[int, App, object], Callable[[], None]]) -> None:
        """Set the timer factory for SUB_TIMER subscriptions.

        The factory is called as ``factory(interval_ms, app, msg)`` and must
        return a teardown callable that stops the timer.

        Args:
            factory: Callable with signature
                ``(interval_ms: int, app: App, msg: object) -> teardown_fn``.
        """
        self._timer_factory = factory

    def dispatch(self, msg: object) -> None:
        """Queue a message for processing on the next tick.

        Args:
            msg: The message to dispatch.
        """
        if not self._disposed:
            self._msg_queue.append(msg)

    def tick(self) -> bool:
        """Process queued messages and re-render if needed.

        This method should be called in the main loop.  It drains the
        message queue, updating the model for each message, then
        re-renders the view if anything changed.

        Returns:
            True if the model was updated, False otherwise.
        """
        if self._disposed:
            return False

        changed: bool = False

        # Process all queued messages (including cascading from Cmd.of_msg)
        while len(self._msg_queue) > 0:
            # Snapshot current batch; _execute_cmd may append new messages
            batch: list[object] = self._msg_queue
            self._msg_queue = []
            for msg in batch:
                update_result = self.program.update_fn(msg, self.model)
                self.model = update_result[0]
                cmd: Cmd = update_result[1]
                self._execute_cmd(cmd)
                changed = True

        # Re-render if model changed or first render
        if changed or self.root_node is None:
            widget: Widget = self.program.view_fn(self.model)
            self.root_node = self.reconciler.reconcile(self.root_node, widget, self._root_lv_obj)

            # Re-setup subscriptions on model change
            if changed and self.program.subscribe_fn is not None:
                self._setup_subscriptions()

        return changed

    def dispose(self) -> None:
        """Clean up all resources.

        Tears down subscriptions, disposes the view tree, and clears the
        message queue.  The app cannot be used after disposal.
        """
        if self._disposed:
            return

        self._disposed = True

        # Tear down subscriptions
        self._teardown_subscriptions()

        # Dispose view tree
        if self.root_node is not None:
            self.reconciler.dispose_tree(self.root_node)
            self.root_node = None

        # Clear message queue
        self._msg_queue = []

    def is_disposed(self) -> bool:
        """Check if the app has been disposed."""
        return self._disposed

    def queue_length(self) -> int:
        """Return the number of pending messages."""
        return len(self._msg_queue)

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def _execute_cmd(self, cmd: Cmd) -> None:
        """Execute all effects in a command.

        EFFECT_MSG effects queue a message via dispatch().
        EFFECT_FN effects are called with dispatch as argument.

        Args:
            cmd: The command whose effects to execute.
        """
        i: int = 0
        while i < len(cmd.effects):
            effect: Effect = cmd.effects[i]
            if effect.kind == EFFECT_MSG:
                self.dispatch(effect.data)
            elif effect.kind == EFFECT_FN:
                # Custom effect: call fn(dispatch)
                effect.data(self.dispatch)  # type: ignore[operator]
            i += 1

    # ------------------------------------------------------------------
    # Subscription management
    # ------------------------------------------------------------------

    def _setup_subscriptions(self) -> None:
        """Set up subscriptions based on current model.

        Compares new subscription keys against existing ones.  If they
        differ, tears down old subscriptions and activates new ones.
        """
        if self.program.subscribe_fn is None:
            return

        sub: Sub = self.program.subscribe_fn(self.model)

        # Collect new keys
        new_keys: list[str] = []
        i: int = 0
        while i < len(sub.defs):
            new_keys.append(sub.defs[i].key)
            i += 1

        # Skip if keys haven't changed
        if self._keys_match(new_keys):
            return

        # Tear down old and set up new
        self._teardown_subscriptions()

        i = 0
        activated_keys: list[str] = []
        while i < len(sub.defs):
            sub_def: SubDef = sub.defs[i]
            teardown: object | None = self._activate_sub(sub_def)
            if teardown is not None:
                self._active_teardowns.append(teardown)
                activated_keys.append(sub_def.key)
            i += 1

        self._sub_keys = activated_keys

    def _teardown_subscriptions(self) -> None:
        """Tear down all active subscriptions."""
        i: int = 0
        while i < len(self._active_teardowns):
            teardown = self._active_teardowns[i]
            teardown()  # type: ignore[operator]
            i += 1
        self._active_teardowns = []
        self._sub_keys = []

    def _activate_sub(self, sub_def: SubDef) -> object | None:
        """Activate a single subscription definition.

        Args:
            sub_def: The subscription to activate.

        Returns:
            A teardown callable, or None if activation was not possible.
        """
        if sub_def.kind == SUB_TIMER:
            return self._activate_timer_sub(sub_def)
        return None

    def _activate_timer_sub(self, sub_def: SubDef) -> object | None:
        """Activate a timer subscription.

        Calls the timer factory as ``factory(interval_ms, app, msg)``.

        Args:
            sub_def: SubDef with data = (interval_ms, msg).

        Returns:
            A teardown callable from the timer factory, or None.
        """
        if self._timer_factory is None:
            return None

        timer_data = sub_def.data
        interval_ms: int = timer_data[0]
        msg: object = timer_data[1]

        teardown = self._timer_factory(interval_ms, self, msg)
        return teardown

    def _keys_match(self, new_keys: list[str]) -> bool:
        """Check if subscription keys match the currently active keys.

        Args:
            new_keys: New subscription key list.

        Returns:
            True if the keys are identical.
        """
        if len(new_keys) != len(self._sub_keys):
            return False
        i: int = 0
        while i < len(new_keys):
            if new_keys[i] != self._sub_keys[i]:
                return False
            i += 1
        return True
