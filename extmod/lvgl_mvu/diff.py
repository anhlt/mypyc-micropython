"""O(N) widget tree diffing engine.

Computes the minimal set of changes between two Widget trees.  Both scalar
attributes and children are diffed using two-pointer / positional algorithms
that run in O(N) time.
"""

from __future__ import annotations

from dataclasses import dataclass

from lvgl_mvu.widget import ScalarAttr, Widget


# ---------------------------------------------------------------------------
# Change descriptors
# ---------------------------------------------------------------------------

CHANGE_ADDED: str = "added"
CHANGE_REMOVED: str = "removed"
CHANGE_UPDATED: str = "updated"

CHILD_INSERT: str = "insert"
CHILD_REMOVE: str = "remove"
CHILD_UPDATE: str = "update"
CHILD_REPLACE: str = "replace"


@dataclass
class AttrChange:
    """Single scalar attribute change between two widgets."""

    kind: str
    key: int
    old_value: object | None
    new_value: object | None


@dataclass
class ChildChange:
    """Single child change between two widgets."""

    kind: str
    index: int
    widget: Widget | None
    diff: WidgetDiff | None


@dataclass
class WidgetDiff:
    """Complete diff between two widget snapshots."""

    scalar_changes: list[AttrChange]
    child_changes: list[ChildChange]
    event_changes: bool = False

    def is_empty(self) -> bool:
        """Return True when there are no changes at all."""
        return (
            len(self.scalar_changes) == 0
            and len(self.child_changes) == 0
            and not self.event_changes
        )


# ---------------------------------------------------------------------------
# Scalar attribute diffing  (two-pointer merge on sorted tuples)
# ---------------------------------------------------------------------------


def diff_scalars(
    prev: tuple[ScalarAttr, ...],
    next_attrs: tuple[ScalarAttr, ...],
) -> list[AttrChange]:
    """Diff two sorted scalar-attribute tuples in O(N) time."""
    changes: list[AttrChange] = []
    i: int = 0
    j: int = 0

    while i < len(prev) or j < len(next_attrs):
        if i >= len(prev):
            changes.append(AttrChange(CHANGE_ADDED, next_attrs[j].key, None, next_attrs[j].value))
            j += 1
        elif j >= len(next_attrs):
            changes.append(AttrChange(CHANGE_REMOVED, prev[i].key, prev[i].value, None))
            i += 1
        elif prev[i].key < next_attrs[j].key:
            changes.append(AttrChange(CHANGE_REMOVED, prev[i].key, prev[i].value, None))
            i += 1
        elif prev[i].key > next_attrs[j].key:
            changes.append(AttrChange(CHANGE_ADDED, next_attrs[j].key, None, next_attrs[j].value))
            j += 1
        else:
            # same key -- check value
            if prev[i].value != next_attrs[j].value:
                changes.append(
                    AttrChange(CHANGE_UPDATED, prev[i].key, prev[i].value, next_attrs[j].value)
                )
            i += 1
            j += 1

    return changes


# ---------------------------------------------------------------------------
# Reuse strategy
# ---------------------------------------------------------------------------


def can_reuse(prev: Widget, next_w: Widget) -> bool:
    """Determine whether an existing LVGL object can be reused.

    Rules:
    1. Widget type must match.
    2. If either widget carries a non-empty user_key, the user_keys must be equal.
    3. Otherwise (both user_keys are the empty-string sentinel / unset), reuse is allowed.
    """
    if prev.key != next_w.key:
        return False
    if prev.user_key != "" or next_w.user_key != "":
        return prev.user_key == next_w.user_key
    return True


# ---------------------------------------------------------------------------
# Child diffing  (positional O(N))
# ---------------------------------------------------------------------------


def diff_children(
    prev: tuple[Widget, ...],
    next_children: tuple[Widget, ...],
) -> list[ChildChange]:
    """Diff children using a positional algorithm in O(N) time."""
    changes: list[ChildChange] = []
    prev_len: int = len(prev)
    next_len: int = len(next_children)
    max_len: int = prev_len
    if next_len > max_len:
        max_len = next_len

    i: int = 0
    while i < max_len:
        if i >= next_len:
            changes.append(ChildChange(CHILD_REMOVE, i, prev[i], None))
        elif i >= prev_len:
            changes.append(ChildChange(CHILD_INSERT, i, next_children[i], None))
        elif can_reuse(prev[i], next_children[i]):
            child_diff: WidgetDiff = diff_widgets(prev[i], next_children[i])
            if not child_diff.is_empty():
                changes.append(ChildChange(CHILD_UPDATE, i, next_children[i], child_diff))
        else:
            changes.append(ChildChange(CHILD_REPLACE, i, next_children[i], None))
        i += 1

    return changes


# ---------------------------------------------------------------------------
# Event handler diffing
# ---------------------------------------------------------------------------


def _events_changed(
    prev: tuple[tuple[int, object], ...],
    next_evts: tuple[tuple[int, object], ...],
) -> bool:
    """Quick check whether event handler tuples differ."""
    if len(prev) != len(next_evts):
        return True
    i: int = 0
    while i < len(prev):
        if prev[i][0] != next_evts[i][0]:
            return True
        if prev[i][1] != next_evts[i][1]:
            return True
        i += 1
    return False


# ---------------------------------------------------------------------------
# Top-level diff
# ---------------------------------------------------------------------------


def diff_widgets(prev: Widget | None, next_w: Widget) -> WidgetDiff:
    """Compute the minimal diff between prev and next_w widget trees.

    If prev is None the entire next_w tree is treated as new.
    """
    if prev is None:
        scalar_changes: list[AttrChange] = []
        for a in next_w.scalar_attrs:
            scalar_changes.append(AttrChange(CHANGE_ADDED, a.key, None, a.value))
        child_changes: list[ChildChange] = []
        i: int = 0
        for c in next_w.children:
            child_changes.append(ChildChange(CHILD_INSERT, i, c, None))
            i += 1
        has_events: bool = len(next_w.event_handlers) > 0
        return WidgetDiff(scalar_changes, child_changes, has_events)

    return WidgetDiff(
        diff_scalars(prev.scalar_attrs, next_w.scalar_attrs),
        diff_children(prev.children, next_w.children),
        _events_changed(prev.event_handlers, next_w.event_handlers),
    )
