"""LVGL event system for the MVU framework.

Provides:
- LvEvent: Integer constants for all LVGL event codes
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

from typing import Callable

import lvgl as lv


# ---------------------------------------------------------------------------
# LVGL Event Code Constants (module-level for static access)
# ---------------------------------------------------------------------------
# Values match LVGL 9.6 lv_event_code_t enum.

# Input events
LvEvent_ALL: int = 0
LvEvent_PRESSED: int = 1
LvEvent_PRESSING: int = 2
LvEvent_PRESS_LOST: int = 3
LvEvent_SHORT_CLICKED: int = 4
LvEvent_SINGLE_CLICKED: int = 5
LvEvent_DOUBLE_CLICKED: int = 6
LvEvent_TRIPLE_CLICKED: int = 7
LvEvent_LONG_PRESSED: int = 8
LvEvent_LONG_PRESSED_REPEAT: int = 9
LvEvent_CLICKED: int = 10
LvEvent_RELEASED: int = 11

# Scroll events
LvEvent_SCROLL_BEGIN: int = 12
LvEvent_SCROLL_THROW_BEGIN: int = 13
LvEvent_SCROLL_END: int = 14
LvEvent_SCROLL: int = 15

# Gesture / input device events
LvEvent_GESTURE: int = 16
LvEvent_KEY: int = 17
LvEvent_ROTARY: int = 18
LvEvent_FOCUSED: int = 19
LvEvent_DEFOCUSED: int = 20
LvEvent_LEAVE: int = 21
LvEvent_HIT_TEST: int = 22
LvEvent_INDEV_RESET: int = 23
LvEvent_HOVER_OVER: int = 24
LvEvent_HOVER_LEAVE: int = 25

# Drawing events
LvEvent_COVER_CHECK: int = 26
LvEvent_REFR_EXT_DRAW_SIZE: int = 27
LvEvent_DRAW_MAIN_BEGIN: int = 28
LvEvent_DRAW_MAIN: int = 29
LvEvent_DRAW_MAIN_END: int = 30
LvEvent_DRAW_POST_BEGIN: int = 31
LvEvent_DRAW_POST: int = 32
LvEvent_DRAW_POST_END: int = 33
LvEvent_DRAW_TASK_ADDED: int = 34

# Widget-specific events
LvEvent_VALUE_CHANGED: int = 35
LvEvent_INSERT: int = 36
LvEvent_REFRESH: int = 37
LvEvent_READY: int = 38
LvEvent_CANCEL: int = 39

# Object lifecycle events
LvEvent_STATE_CHANGED: int = 40
LvEvent_CREATE: int = 41
LvEvent_OBJ_DELETE: int = 42
LvEvent_CHILD_CHANGED: int = 43
LvEvent_CHILD_CREATED: int = 44
LvEvent_CHILD_DELETED: int = 45

# Screen events
LvEvent_SCREEN_UNLOAD_START: int = 46
LvEvent_SCREEN_LOAD_START: int = 47
LvEvent_SCREEN_LOADED: int = 48
LvEvent_SCREEN_UNLOADED: int = 49

# Layout/style events
LvEvent_SIZE_CHANGED: int = 50
LvEvent_STYLE_CHANGED: int = 51
LvEvent_LAYOUT_CHANGED: int = 52
LvEvent_GET_SELF_SIZE: int = 53

# ---------------------------------------------------------------------------
# Handler kind tags
# ---------------------------------------------------------------------------
HANDLER_MSG: int = 0
HANDLER_VALUE: int = 1


# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------


class EventHandler:
    """Reference to a registered LVGL event callback.

    Attributes:
        active: Whether the handler should dispatch messages.
        kind: HANDLER_MSG or HANDLER_VALUE.
        payload: The message (HANDLER_MSG) or message factory (HANDLER_VALUE).
    """

    active: bool
    kind: int
    payload: object

    def __init__(self, kind: int, payload: object) -> None:
        self.active = True
        self.kind = kind
        self.payload = payload

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
        handler = EventHandler(HANDLER_MSG, msg)
        dispatch_fn = self._dispatch_fn

        # Closure captures: handler, dispatch_fn, msg
        callback: Callable[[object], None] = lambda event: _dispatch_msg(handler, dispatch_fn, msg)

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
        handler = EventHandler(HANDLER_VALUE, msg_fn)
        dispatch_fn = self._dispatch_fn

        # Closure captures: handler, dispatch_fn, msg_fn
        callback: Callable[[object], None] = lambda event: _dispatch_value(
            event, handler, dispatch_fn, msg_fn
        )

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
    """Extract value and dispatch msg_fn(value) if handler is active."""
    if not handler.active:
        return

    # Extract value from target widget
    target: object = lv.lv_event_get_target_obj(event)
    value: int = 0
    try:
        value = lv.lv_slider_get_value(target)
    except Exception:
        pass

    # Dispatch msg_fn(value)
    dispatch_fn(msg_fn(value))  # type: ignore[operator]
