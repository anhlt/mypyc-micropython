"""LVGL event system for the MVU framework.

Provides:
- LvEvent: Integer constants for all LVGL event codes (using Final[int])
- HandlerKind: Handler type tags (using Final[int])
- EventHandler: Wrapper around a registered LVGL callback
- EventBinder: Registers/deactivates event callbacks on LVGL objects

This module uses closures to capture the dispatch function and message
in event callbacks. The closure captures:
- dispatch_fn: The MVU dispatch function
- msg/msg_fn: The message to dispatch or factory function

Usage::

    from lvgl_mvu.events import EventBinder, LvEvent

    binder = EventBinder(app.dispatch)

    # Simple message dispatch (button click)
    handler = binder.bind(btn_obj, LvEvent.CLICKED, msg)

    # Value extraction (slider change)
    handler = binder.bind_value(slider_obj, LvEvent.VALUE_CHANGED, make_msg_fn)

    # Deactivate (handler becomes no-op)
    binder.unbind(btn_obj, LvEvent.CLICKED, handler)
"""

from __future__ import annotations

from typing import Callable, Final

import lvgl as lv

# ---------------------------------------------------------------------------
# LVGL Event Code Constants (using Final[int] for compile-time constants)
# ---------------------------------------------------------------------------
# Values match LVGL 9.6 lv_event_code_t enum.
# Access via LvEvent.CLICKED, LvEvent.VALUE_CHANGED, etc.


class LvEvent:
    """LVGL event type constants.

    These constants are compile-time values that can be accessed as
    LvEvent.CLICKED, LvEvent.LONG_PRESSED, etc.

    Generated C code will emit #define constants for efficient access.
    """

    # Input events
    ALL: Final[int] = 0
    PRESSED: Final[int] = 1
    PRESSING: Final[int] = 2
    PRESS_LOST: Final[int] = 3
    SHORT_CLICKED: Final[int] = 4
    SINGLE_CLICKED: Final[int] = 5
    DOUBLE_CLICKED: Final[int] = 6
    TRIPLE_CLICKED: Final[int] = 7
    LONG_PRESSED: Final[int] = 8
    LONG_PRESSED_REPEAT: Final[int] = 9
    CLICKED: Final[int] = 10
    RELEASED: Final[int] = 11

    # Scroll events
    SCROLL_BEGIN: Final[int] = 12
    SCROLL_THROW_BEGIN: Final[int] = 13
    SCROLL_END: Final[int] = 14
    SCROLL: Final[int] = 15

    # Gesture / input device events
    GESTURE: Final[int] = 16
    KEY: Final[int] = 17
    ROTARY: Final[int] = 18
    FOCUSED: Final[int] = 19
    DEFOCUSED: Final[int] = 20
    LEAVE: Final[int] = 21
    HIT_TEST: Final[int] = 22
    INDEV_RESET: Final[int] = 23
    HOVER_OVER: Final[int] = 24
    HOVER_LEAVE: Final[int] = 25

    # Drawing events
    COVER_CHECK: Final[int] = 26
    REFR_EXT_DRAW_SIZE: Final[int] = 27
    DRAW_MAIN_BEGIN: Final[int] = 28
    DRAW_MAIN: Final[int] = 29
    DRAW_MAIN_END: Final[int] = 30
    DRAW_POST_BEGIN: Final[int] = 31
    DRAW_POST: Final[int] = 32
    DRAW_POST_END: Final[int] = 33
    DRAW_TASK_ADDED: Final[int] = 34

    # Widget-specific events
    VALUE_CHANGED: Final[int] = 35
    INSERT: Final[int] = 36
    REFRESH: Final[int] = 37
    READY: Final[int] = 38
    CANCEL: Final[int] = 39

    # Object lifecycle events
    STATE_CHANGED: Final[int] = 40
    CREATE: Final[int] = 41
    OBJ_DELETE: Final[int] = 42
    CHILD_CHANGED: Final[int] = 43
    CHILD_CREATED: Final[int] = 44
    CHILD_DELETED: Final[int] = 45

    # Screen events
    SCREEN_UNLOAD_START: Final[int] = 46
    SCREEN_LOAD_START: Final[int] = 47
    SCREEN_LOADED: Final[int] = 48
    SCREEN_UNLOADED: Final[int] = 49

    # Layout/style events
    SIZE_CHANGED: Final[int] = 50
    STYLE_CHANGED: Final[int] = 51
    LAYOUT_CHANGED: Final[int] = 52
    GET_SELF_SIZE: Final[int] = 53


# ---------------------------------------------------------------------------
# Handler kind tags (using Final[int] for compile-time constants)
# ---------------------------------------------------------------------------


class HandlerKind:
    """Handler type constants for EventHandler.

    MSG: Simple message dispatch (button click, etc.)
    VALUE: Integer value extraction (slider, bar, arc)
    CHECKED: Boolean state extraction (switch, checkbox)
    """

    MSG: Final[int] = 0
    VALUE: Final[int] = 1
    CHECKED: Final[int] = 2


# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------


class EventHandler:
    """Reference to a registered LVGL event callback.

    Attributes:
        active: Whether the handler should dispatch messages.
        kind: HandlerKind.MSG or HandlerKind.VALUE.
        payload: The message (MSG) or message factory (VALUE).
        _callback: Reference to the callback to prevent GC.
    """

    active: bool
    kind: int
    payload: object
    _callback: object  # prevent GC of the lambda

    def __init__(self, kind: int, payload: object) -> None:
        self.active = True
        self.kind = kind
        self.payload = payload
        self._callback = None  # set by EventBinder.bind()

    def store_callback(self, callback: object) -> None:
        """Store callback reference to prevent garbage collection."""
        self._callback = callback

    def deactivate(self) -> None:
        """Deactivate this handler. The LVGL callback becomes a no-op."""
        self.active = False


# ---------------------------------------------------------------------------
# EventBinder
# ---------------------------------------------------------------------------


class EventBinder:
    """Registers and manages LVGL event callbacks for the MVU framework.

    Uses closures to capture dispatch function and message in callbacks.
    Since MicroPython's LVGL bindings do not expose lv_obj_remove_event_cb,
    event handlers are deactivated rather than removed.

    Attributes:
        _dispatch_fn: The MVU dispatch function ``(msg) -> None``.
    """

    _dispatch_fn: Callable[[object], None]

    def __init__(self, dispatch_fn: Callable[[object], None]) -> None:
        """Create an EventBinder.

        Args:
            dispatch_fn: The MVU dispatch function.
        """
        self._dispatch_fn = dispatch_fn

    def bind(self, lv_obj: object, event_type: int, msg: object) -> EventHandler:
        """Bind a simple message dispatch to an LVGL event.

        When the event fires, ``dispatch_fn(msg)`` is called.

        Args:
            lv_obj: The LVGL object to listen on.
            event_type: The LVGL event code (from LvEvent).
            msg: The message to dispatch when the event fires.

        Returns:
            An EventHandler reference for later unbinding.
        """
        handler = EventHandler(HandlerKind.MSG, msg)
        dispatch_fn = self._dispatch_fn

        # Closure captures: handler, dispatch_fn, msg
        callback: Callable[[object], None] = lambda event: _dispatch_msg(handler, dispatch_fn, msg)

        # Store callback in handler to prevent garbage collection
        handler.store_callback(callback)

        lv.lv_obj_add_event_cb(lv_obj, callback, event_type, None)
        return handler

    def bind_value(
        self,
        lv_obj: object,
        event_type: int,
        msg_fn: Callable[[int], object],
    ) -> EventHandler:
        """Bind a value-extracting event handler.

        When the event fires, the widget's current value is extracted
        and ``dispatch_fn(msg_fn(value))`` is called.

        Supports value extraction from: slider, bar, arc.

        Args:
            lv_obj: The LVGL object to listen on.
            event_type: The LVGL event code (from LvEvent).
            msg_fn: A callable ``(int) -> Msg`` that wraps the value.

        Returns:
            An EventHandler reference for later unbinding.
        """
        handler = EventHandler(HandlerKind.VALUE, msg_fn)
        dispatch_fn = self._dispatch_fn

        # Closure captures: handler, dispatch_fn, msg_fn
        callback: Callable[[object], None] = lambda event: _dispatch_value(
            event, handler, dispatch_fn, msg_fn
        )

        # Store callback in handler to prevent garbage collection
        handler.store_callback(callback)

        lv.lv_obj_add_event_cb(lv_obj, callback, event_type, None)
        return handler

    def bind_checked(
        self,
        lv_obj: object,
        event_type: int,
        msg_fn: Callable[[bool], object],
    ) -> EventHandler:
        """Bind a boolean state handler for switch/checkbox widgets.

        When the event fires, the widget's checked state is extracted
        and ``dispatch_fn(msg_fn(checked))`` is called.

        Args:
            lv_obj: The LVGL object to listen on.
            event_type: The LVGL event code (from LvEvent).
            msg_fn: A callable ``(bool) -> Msg`` that wraps the state.

        Returns:
            An EventHandler reference for later unbinding.
        """
        handler = EventHandler(HandlerKind.CHECKED, msg_fn)
        dispatch_fn = self._dispatch_fn

        callback: Callable[[object], None] = lambda event: _dispatch_checked(
            event, handler, dispatch_fn, msg_fn
        )

        handler.store_callback(callback)

        lv.lv_obj_add_event_cb(lv_obj, callback, event_type, None)
        return handler

    def unbind(self, lv_obj: object, event_type: int, handler: object) -> None:
        """Deactivate an event handler.

        The LVGL callback remains registered but becomes a no-op.
        It will be fully cleaned up when the LVGL object is deleted.

        Args:
            lv_obj: The LVGL object (unused, kept for API symmetry).
            event_type: The event type (unused, kept for API symmetry).
            handler: The EventHandler to deactivate.
        """
        if isinstance(handler, EventHandler):
            handler.deactivate()


# ---------------------------------------------------------------------------
# Dispatch helper functions (called from closures)
# ---------------------------------------------------------------------------

CHECKED_STATE: int = 4


def _dispatch_msg(handler: EventHandler, dispatch_fn: object, msg: object) -> None:
    """Dispatch a simple message if handler is active."""
    if handler.active:
        dispatch_fn(msg)  # type: ignore[operator]


def _dispatch_value(
    event: object,
    handler: EventHandler,
    dispatch_fn: object,
    msg_fn: object,
) -> None:
    """Extract integer value from target widget and dispatch msg_fn(value)."""
    if not handler.active:
        return

    target: object = lv.lv_event_get_target_obj(event)
    value: int = _extract_int_value(target)

    dispatch_fn(msg_fn(value))  # type: ignore[operator]


def _dispatch_checked(
    event: object,
    handler: EventHandler,
    dispatch_fn: object,
    msg_fn: object,
) -> None:
    """Extract boolean checked state and dispatch msg_fn(checked)."""
    if not handler.active:
        return

    target: object = lv.lv_event_get_target_obj(event)
    checked: bool = lv.lv_obj_has_state(target, CHECKED_STATE)

    dispatch_fn(msg_fn(checked))  # type: ignore[operator]


def setup_events(reconciler: object, dispatch_fn: Callable[[object], None]) -> EventBinder:
    """Wire an EventBinder into a Reconciler.

    Creates an EventBinder from the dispatch function and registers it
    with the reconciler for automatic event handler management.

    Args:
        reconciler: A Reconciler instance (uses set_event_binder).
        dispatch_fn: The MVU dispatch function (typically app.dispatch).

    Returns:
        The created EventBinder for direct use if needed.
    """
    binder = EventBinder(dispatch_fn)
    reconciler.set_event_binder(binder)  # type: ignore[attr-defined]
    return binder


def _extract_int_value(target: object) -> int:
    """Try slider -> bar -> arc value extraction, return 0 on failure."""
    value: int = 0
    try:
        value = lv.lv_slider_get_value(target)
        return value
    except Exception:
        pass
    try:
        value = lv.lv_bar_get_value(target)
        return value
    except Exception:
        pass
    try:
        value = lv.lv_arc_get_value(target)
        return value
    except Exception:
        pass
    return 0
