# LVGL MVU Framework Implementation Plan

> Fabulous-style Model-View-Update framework for LVGL widgets, compiled to native C via mypyc-micropython.

**Status**: Planning  
**Created**: 2026-03-07  
**Target**: LVGL 9.6 / MicroPython 1.28.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Milestones](#milestones)
4. [Phase Details](#phase-details)
5. [Widget Catalog](#widget-catalog)
6. [API Reference](#api-reference)
7. [File Structure](#file-structure)
8. [Example Application](#example-application)

---

## Executive Summary

### Goals

Create a **declarative UI framework** for LVGL that:

- Provides Fabulous/Elm-style MVU architecture
- Compiles to native C for embedded performance
- Supports all 30+ LVGL widgets
- Enables efficient UI updates via O(N) diffing
- Integrates with existing navigation system

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | MVU (Model-View-Update) | Predictable state, easy testing |
| Diffing | Positional O(N) | Memory-efficient for embedded |
| Widget representation | Immutable dataclasses | mypyc optimization, GC-friendly |
| Attribute storage | Sorted tuples by key | Fast merge-style diffing |
| Event handling | Message dispatch | Decoupled, testable |
| Async support | MicroPython asyncio | Non-blocking I/O, background tasks |
### References

- [Fabulous F# MVU Framework](https://github.com/fabulous-dev/Fabulous)
- [LVGL 9.6 Documentation](https://docs.lvgl.io/master/)
- [Elm Architecture](https://guide.elm-lang.org/architecture/)

---

## Architecture Overview

### Data Flow

```
User Input
    │
    ▼
┌─────────┐     ┌─────────┐     ┌─────────┐
│   Msg   │────▶│ Update  │────▶│  Model  │
└─────────┘     └─────────┘     └─────────┘
                                     │
                                     ▼
                               ┌─────────┐
                               │  View   │
                               └─────────┘
                                     │
                                     ▼
                               ┌─────────┐
                               │ Widget  │ (immutable tree)
                               └─────────┘
                                     │
                                     ▼
                               ┌─────────┐
                               │  Diff   │
                               └─────────┘
                                     │
                                     ▼
                               ┌─────────┐
                               │ViewNode │ (LVGL objects)
                               └─────────┘
```

### Core Abstractions

#### Widget (Immutable)

```python
@dataclass(frozen=True)
class Widget:
    key: int                              # Widget type (LABEL, BUTTON, etc.)
    user_key: str | None                  # Optional key for reuse control
    scalar_attrs: tuple[ScalarAttr, ...]  # Properties (text, color, size)
    children: tuple['Widget', ...]        # Child widgets
    event_handlers: tuple[tuple[int, object], ...]  # (event_type, msg)
```

#### ViewNode (Mutable LVGL Wrapper)

```python
class ViewNode:
    lv_obj: object              # Actual LVGL object
    widget: Widget              # Last applied widget
    children: list['ViewNode']  # Child nodes
    handlers: dict[int, object] # Event handler references
```

#### Program Definition

```python
@dataclass
class Program(Generic[Model, Msg]):
    init: Callable[[], tuple[Model, Cmd[Msg]]]
    update: Callable[[Msg, Model], tuple[Model, Cmd[Msg]]]
    view: Callable[[Model], Widget]
    subscribe: Callable[[Model], Sub[Msg]] | None = None
```

---

## Milestones

### Milestone 1: Foundation (Week 1-2)

**Goal**: Core widget abstraction and builder DSL.

| Task | Description | Status |
|------|-------------|--------|
| 1.1 | Widget dataclass and WidgetKey enum | Pending |
| 1.2 | ScalarAttr and attribute registry | Pending |
| 1.3 | WidgetBuilder base class with fluent API | Pending |
| 1.4 | Base widget attributes (size, pos, color) | Pending |
| 1.5 | Unit tests for widget creation | Pending |

**Deliverables**:
- `src/lvgl_mvu/widget.py`
- `src/lvgl_mvu/attrs.py`
- `src/lvgl_mvu/builders.py`
- `tests/test_widget.py`

**Exit Criteria**:
- Can construct Widget trees programmatically
- All attributes stored in sorted tuples
- 100% test coverage on widget module

---

### Milestone 2: Diffing Engine (Week 2-3)

**Goal**: Efficient O(N) widget tree diffing.

| Task | Description | Status |
|------|-------------|--------|
| 2.1 | AttrChange and WidgetDiff dataclasses | Pending |
| 2.2 | Scalar attribute diffing (two-pointer) | Pending |
| 2.3 | Child widget diffing (positional) | Pending |
| 2.4 | Reuse strategy (can_reuse function) | Pending |
| 2.5 | Unit tests with edge cases | Pending |

**Deliverables**:
- `src/lvgl_mvu/diff.py`
- `tests/test_diff.py`

**Exit Criteria**:
- Diff algorithm is O(N) for N attributes/children
- Correctly identifies added/removed/updated attributes
- Handles widget type changes (full replace)

---

### Milestone 3: ViewNode & Reconciliation (Week 3-4)

**Goal**: Bridge between Widgets and LVGL objects.

| Task | Description | Status |
|------|-------------|--------|
| 3.1 | ViewNode class wrapping LVGL objects | Pending |
| 3.2 | apply_diff method for scalar changes | Pending |
| 3.3 | Child reconciliation (insert/remove/update) | Pending |
| 3.4 | Reconciler class orchestrating updates | Pending |
| 3.5 | LVGL object lifecycle management | Pending |
| 3.6 | Integration tests with mock LVGL | Pending |

**Deliverables**:
- `src/lvgl_mvu/viewnode.py`
- `src/lvgl_mvu/reconciler.py`
- `tests/test_reconciler.py`

**Exit Criteria**:
- ViewNode correctly wraps LVGL objects
- Diffs are applied without object recreation
- Proper cleanup of removed widgets

---

### Milestone 4: MVU Runtime (Week 4)

**Goal**: Complete MVU loop with message dispatch.

| Task | Description | Status |
|------|-------------|--------|
| 4.1 | Program dataclass definition | Pending |
| 4.2 | Cmd (side effects) implementation | Pending |
| 4.3 | App class with message queue | Pending |
| 4.4 | tick() method for main loop | Pending |
| 4.5 | Sub (subscriptions) for timers/events | Pending |
| 4.6 | Integration tests | Pending |

**Deliverables**:
- `src/lvgl_mvu/program.py`
- `src/lvgl_mvu/app.py`
- `tests/test_app.py`

**Exit Criteria**:
- Messages processed in order
- Commands execute side effects
- View re-renders on model change

---

### Milestone 5: P0 Widgets (Week 5)

**Goal**: Essential widgets for basic UIs.

| Task | Description | Status |
|------|-------------|--------|
| 5.1 | Screen widget (root container) | Pending |
| 5.2 | Label widget with text attributes | Pending |
| 5.3 | Button widget with click handler | Pending |
| 5.4 | Container widget (lv_obj) | Pending |
| 5.5 | VStack/HStack flex layouts | Pending |
| 5.6 | Device tests on ESP32 | Pending |

**Deliverables**:
- `src/lvgl_mvu/dsl.py`
- `src/lvgl_mvu/layouts.py`
- `src/lvgl_mvu/widgets/base.py`
- `src/lvgl_mvu/widgets/label.py`
- `src/lvgl_mvu/widgets/button.py`
- `examples/counter_app.py`
- `tests/device/run_mvu_p0_tests.py`

**Exit Criteria**:
- Counter app runs on device
- Button clicks dispatch messages
- Labels update on model change

---

### Milestone 6: Event System (Week 5-6)

**Goal**: Complete event binding and dispatch.

| Task | Description | Status |
|------|-------------|--------|
| 6.1 | LvEvent enum with all event types | Pending |
| 6.2 | Event handler registration in ViewNode | Pending |
| 6.3 | Value extraction (slider value, etc.) | Pending |
| 6.4 | Handler cleanup on widget removal | Pending |
| 6.5 | Event tests | Pending |

**Deliverables**:
- `src/lvgl_mvu/events.py`
- `tests/test_events.py`

**Exit Criteria**:
- All LVGL events mapped
- Handlers properly disposed
- No memory leaks from events

---

### Milestone 7: P1 Widgets (Week 6-7)

**Goal**: Interactive input widgets.

| Task | Description | Status |
|------|-------------|--------|
| 7.1 | Slider widget with value_changed | Pending |
| 7.2 | Bar (progress) widget | Pending |
| 7.3 | Arc widget | Pending |
| 7.4 | Switch widget | Pending |
| 7.5 | Checkbox widget | Pending |
| 7.6 | Device tests | Pending |

**Deliverables**:
- `src/lvgl_mvu/widgets/slider.py`
- `src/lvgl_mvu/widgets/bar.py`
- `src/lvgl_mvu/widgets/arc.py`
- `src/lvgl_mvu/widgets/switch.py`
- `src/lvgl_mvu/widgets/checkbox.py`
- `examples/form_app.py`
- `tests/device/run_mvu_p1_tests.py`

**Exit Criteria**:
- All P1 widgets render correctly
- Value changes dispatch messages
- Form app demo working on device

---

### Milestone 8: Navigation Integration (Week 7)

**Goal**: Multi-screen navigation with MVU.

| Task | Description | Status |
|------|-------------|--------|
| 8.1 | NavCmd (push/pop/replace) | Pending |
| 8.2 | MultiScreenApp orchestrator | Pending |
| 8.3 | Screen transitions with animation | Pending |
| 8.4 | Screen state preservation | Pending |
| 8.5 | Navigation demo app | Pending |

**Deliverables**:
- `src/lvgl_mvu/navigation.py`
- `examples/navigation_app.py`
- `tests/device/run_mvu_nav_tests.py`

**Exit Criteria**:
- Push/pop/replace work with animations
- Screen state preserved on back navigation
- Memory properly cleaned on screen removal

---

### Milestone 9: P2 Widgets (Week 8-9)

**Goal**: Form and data display widgets.

| Task | Description | Status |
|------|-------------|--------|
| 9.1 | Image widget | Pending |
| 9.2 | TextArea widget | Pending |
| 9.3 | Dropdown widget | Pending |
| 9.4 | Roller widget | Pending |
| 9.5 | Table widget | Pending |
| 9.6 | List widget | Pending |
| 9.7 | Device tests | Pending |

**Deliverables**:
- `src/lvgl_mvu/widgets/image.py`
- `src/lvgl_mvu/widgets/textarea.py`
- `src/lvgl_mvu/widgets/dropdown.py`
- `src/lvgl_mvu/widgets/roller.py`
- `src/lvgl_mvu/widgets/table.py`
- `src/lvgl_mvu/widgets/list.py`

**Exit Criteria**:
- All P2 widgets functional
- Text input works correctly
- Selection widgets dispatch values

---

### Milestone 10: Optimizations (Week 9-10)

**Goal**: Performance optimizations for embedded.

| Task | Description | Status |
|------|-------------|--------|
| 10.1 | Memoization (lazy widgets) | Pending |
| 10.2 | Dirty checking (skip unchanged) | Pending |
| 10.3 | Batch updates (reduce redraws) | Pending |
| 10.4 | Memory profiling | Pending |
| 10.5 | Benchmark vs vanilla LVGL | Pending |

**Deliverables**:
- Memoization API in `src/lvgl_mvu/memo.py`
- Benchmark results in `tests/device/run_mvu_benchmarks.py`

**Exit Criteria**:
- Memoized widgets skip reconciliation
- <10% overhead vs direct LVGL calls
- Memory usage stable under stress

---

### Milestone 11: Async Support (Week 10-11)

**Goal**: Full async/await integration with MicroPython asyncio.

| Task | Description | Status |
|------|-------------|--------|
| 11.1 | AsyncCmd for async effects | Pending |
| 11.2 | Async App runner with event loop | Pending |
| 11.3 | Async subscriptions (streams, timers) | Pending |
| 11.4 | Task cancellation and cleanup | Pending |
| 11.5 | Async HTTP/network operations | Pending |
| 11.6 | Background task management | Pending |
| 11.7 | Error handling in async context | Pending |
| 11.8 | Device tests with async patterns | Pending |

**Deliverables**:
- `src/lvgl_mvu/async_cmd.py` - Async command implementation
- `src/lvgl_mvu/async_app.py` - Async application runner
- `src/lvgl_mvu/async_sub.py` - Async subscriptions
- `src/lvgl_mvu/tasks.py` - Background task manager
- `examples/async_http_app.py` - HTTP fetch demo
- `examples/async_sensor_app.py` - Sensor polling demo
- `tests/device/run_mvu_async_tests.py`

**Exit Criteria**:
- Async commands execute without blocking UI
- Background tasks can be cancelled cleanly
- Network operations work with loading states
- No memory leaks from uncompleted tasks

---

### Milestone 12: P3 Widgets (Week 11-13)

**Goal**: Advanced visualization and navigation widgets.

| Task | Description | Status |
|------|-------------|--------|
| 11.1 | Chart widget | Pending |
| 11.2 | Calendar widget | Pending |
| 11.3 | Keyboard widget | Pending |
| 11.4 | Menu widget | Pending |
| 11.5 | TabView widget | Pending |
| 11.6 | MessageBox widget | Pending |
| 11.7 | Spinner widget | Pending |
| 11.8 | LED widget | Pending |
| 11.9 | Line widget | Pending |
| 11.10 | Canvas widget | Pending |
| 11.11 | Window widget | Pending |
| 11.12 | TileView widget | Pending |
| 11.13 | Spangroup widget | Pending |
| 11.14 | Spinbox widget | Pending |
| 11.15 | Scale widget | Pending |
| 11.16 | ButtonMatrix widget | Pending |
| 11.17 | Arc Label widget | Pending |
| 11.18 | Animation Image widget | Pending |

**Deliverables**:
- All P3 widget implementations
- `examples/dashboard_app.py`
- Complete device test suite

**Exit Criteria**:
- All 30+ LVGL widgets supported
- Dashboard demo running on device
- Full test coverage

---

### Milestone 13: Documentation & Release (Week 13-14)

**Goal**: Production-ready release.

| Task | Description | Status |
|------|-------------|--------|
| 13.1 | API documentation | Pending |
| 13.2 | Tutorial: Getting Started | Pending |
| 13.3 | Tutorial: Building Forms | Pending |
| 13.4 | Tutorial: Navigation | Pending |
| 13.5 | Tutorial: Async Patterns | Pending |
| 13.6 | Performance guide | Pending |
| 13.7 | Migration guide (from direct LVGL) | Pending |
| 13.8 | Release notes | Pending |

**Deliverables**:
- `docs/lvgl-mvu-api.md`
- `docs/lvgl-mvu-tutorial.md`
- `docs/lvgl-mvu-async.md`
- `docs/lvgl-mvu-performance.md`
- `CHANGELOG.md` update

**Exit Criteria**:
- Complete API documentation
- Working examples for all features
- Async patterns documented
- Ready for external users
---

## Phase Details

### Phase 1: Core Architecture

#### 1.1 Widget Abstraction Layer

**Goal**: Create immutable widget descriptors separate from LVGL objects.

```python
# src/lvgl_mvu/widget.py

from dataclasses import dataclass
from enum import IntEnum

class WidgetKey(IntEnum):
    """Widget type identifiers."""
    SCREEN = 0
    CONTAINER = 1
    LABEL = 2
    BUTTON = 3
    SLIDER = 4
    BAR = 5
    ARC = 6
    SWITCH = 7
    CHECKBOX = 8
    IMAGE = 9
    TEXTAREA = 10
    DROPDOWN = 11
    ROLLER = 12
    TABLE = 13
    CHART = 14
    CALENDAR = 15
    KEYBOARD = 16
    MENU = 17
    TABVIEW = 18
    MSGBOX = 19
    SPINNER = 20
    LED = 21
    LINE = 22
    CANVAS = 23
    WINDOW = 24
    TILEVIEW = 25
    LIST = 26
    SPANGROUP = 27
    SPINBOX = 28
    SCALE = 29
    BUTTONMATRIX = 30

@dataclass(frozen=True)
class ScalarAttr:
    """Single property value."""
    key: int
    value: object

@dataclass(frozen=True)
class Widget:
    """Immutable virtual UI element."""
    key: WidgetKey
    user_key: str | None
    scalar_attrs: tuple[ScalarAttr, ...]
    children: tuple['Widget', ...]
    event_handlers: tuple[tuple[int, object], ...]
```

#### 1.2 Attribute Definition System

```python
# src/lvgl_mvu/attrs.py

from dataclasses import dataclass
from typing import Callable
from enum import IntEnum

class AttrKey(IntEnum):
    """Attribute type identifiers (sorted for diffing)."""
    # Position/Size (0-19)
    X = 0
    Y = 1
    WIDTH = 2
    HEIGHT = 3
    ALIGN = 4
    ALIGN_X_OFS = 5
    ALIGN_Y_OFS = 6
    
    # Padding/Margin (20-39)
    PAD_TOP = 20
    PAD_RIGHT = 21
    PAD_BOTTOM = 22
    PAD_LEFT = 23
    PAD_ROW = 24
    PAD_COLUMN = 25
    
    # Background (40-59)
    BG_COLOR = 40
    BG_OPA = 41
    BG_GRAD_COLOR = 42
    BG_GRAD_DIR = 43
    
    # Border (60-79)
    BORDER_COLOR = 60
    BORDER_WIDTH = 61
    BORDER_OPA = 62
    BORDER_SIDE = 63
    RADIUS = 64
    
    # Shadow (80-99)
    SHADOW_WIDTH = 80
    SHADOW_COLOR = 81
    SHADOW_OFS_X = 82
    SHADOW_OFS_Y = 83
    SHADOW_SPREAD = 84
    SHADOW_OPA = 85
    
    # Text (100-119)
    TEXT = 100
    TEXT_COLOR = 101
    TEXT_OPA = 102
    TEXT_FONT = 103
    TEXT_ALIGN = 104
    TEXT_DECOR = 105
    
    # Layout (120-139)
    FLEX_FLOW = 120
    FLEX_MAIN_PLACE = 121
    FLEX_CROSS_PLACE = 122
    FLEX_TRACK_PLACE = 123
    FLEX_GROW = 124
    GRID_COLUMN_DSC = 125
    GRID_ROW_DSC = 126
    GRID_CELL_COLUMN_POS = 127
    GRID_CELL_ROW_POS = 128
    
    # Widget-specific (140+)
    MIN_VALUE = 140
    MAX_VALUE = 141
    VALUE = 142
    CHECKED = 143
    SRC = 144
    PLACEHOLDER = 145
    OPTIONS = 146
    SELECTED = 147

@dataclass
class AttrDef:
    """Attribute definition with apply function."""
    key: AttrKey
    name: str
    default: object
    apply_fn: Callable[[object, object], None]
    compare_fn: Callable[[object, object], bool] | None = None

# Global registry
_ATTR_REGISTRY: dict[AttrKey, AttrDef] = {}

def register_attr(attr_def: AttrDef) -> AttrDef:
    """Register an attribute definition."""
    _ATTR_REGISTRY[attr_def.key] = attr_def
    return attr_def

def get_attr_def(key: AttrKey) -> AttrDef:
    """Get attribute definition by key."""
    return _ATTR_REGISTRY[key]
```

#### 1.3 Widget Builder DSL

```python
# src/lvgl_mvu/builders.py

from dataclasses import dataclass, field
from typing import TypeVar, Generic, Callable
from .widget import Widget, WidgetKey, ScalarAttr
from .attrs import AttrKey

Msg = TypeVar('Msg')

@dataclass
class WidgetBuilder(Generic[Msg]):
    """Fluent builder for Widget construction."""
    _key: WidgetKey
    _user_key: str | None = None
    _attrs: list[ScalarAttr] = field(default_factory=list)
    _children: list[Widget] = field(default_factory=list)
    _handlers: list[tuple[int, object]] = field(default_factory=list)
    
    def key(self, user_key: str) -> 'WidgetBuilder[Msg]':
        """Set user-provided key for reuse control."""
        self._user_key = user_key
        return self
    
    def attr(self, attr_key: AttrKey, value: object) -> 'WidgetBuilder[Msg]':
        """Set an attribute."""
        self._attrs.append(ScalarAttr(attr_key, value))
        return self
    
    def on(self, event: int, msg: Msg) -> 'WidgetBuilder[Msg]':
        """Register event handler."""
        self._handlers.append((event, msg))
        return self
    
    def on_value(self, event: int, msg_fn: Callable[[int], Msg]) -> 'WidgetBuilder[Msg]':
        """Register event handler with value extraction."""
        self._handlers.append((event, ("value", msg_fn)))
        return self
    
    def __call__(self, *children: Widget | 'WidgetBuilder') -> Widget:
        """Build widget with children."""
        child_widgets: list[Widget] = []
        for child in children:
            if isinstance(child, WidgetBuilder):
                child_widgets.append(child.build())
            else:
                child_widgets.append(child)
        
        # Sort attributes by key for efficient diffing
        sorted_attrs = tuple(sorted(self._attrs, key=lambda a: a.key))
        
        return Widget(
            key=self._key,
            user_key=self._user_key,
            scalar_attrs=sorted_attrs,
            children=tuple(child_widgets),
            event_handlers=tuple(self._handlers),
        )
    
    def build(self) -> Widget:
        """Build widget without children."""
        return self()
    
    # Common attribute shortcuts
    def width(self, w: int) -> 'WidgetBuilder[Msg]':
        return self.attr(AttrKey.WIDTH, w)
    
    def height(self, h: int) -> 'WidgetBuilder[Msg]':
        return self.attr(AttrKey.HEIGHT, h)
    
    def size(self, w: int, h: int) -> 'WidgetBuilder[Msg]':
        return self.width(w).height(h)
    
    def pos(self, x: int, y: int) -> 'WidgetBuilder[Msg]':
        return self.attr(AttrKey.X, x).attr(AttrKey.Y, y)
    
    def align(self, align: int, x_ofs: int = 0, y_ofs: int = 0) -> 'WidgetBuilder[Msg]':
        return self.attr(AttrKey.ALIGN, align).attr(AttrKey.ALIGN_X_OFS, x_ofs).attr(AttrKey.ALIGN_Y_OFS, y_ofs)
    
    def bg_color(self, color: int) -> 'WidgetBuilder[Msg]':
        return self.attr(AttrKey.BG_COLOR, color)
    
    def text_color(self, color: int) -> 'WidgetBuilder[Msg]':
        return self.attr(AttrKey.TEXT_COLOR, color)
    
    def padding(self, top: int, right: int, bottom: int, left: int) -> 'WidgetBuilder[Msg]':
        return self.attr(AttrKey.PAD_TOP, top).attr(AttrKey.PAD_RIGHT, right).attr(AttrKey.PAD_BOTTOM, bottom).attr(AttrKey.PAD_LEFT, left)
```

### Phase 2: Diffing Engine

```python
# src/lvgl_mvu/diff.py

from dataclasses import dataclass
from typing import Literal
from .widget import Widget, ScalarAttr

@dataclass
class AttrChange:
    """Single attribute change."""
    kind: Literal["added", "removed", "updated"]
    key: int
    old_value: object | None
    new_value: object | None

@dataclass
class ChildChange:
    """Single child change."""
    kind: Literal["insert", "remove", "update", "replace"]
    index: int
    widget: Widget | None
    diff: 'WidgetDiff | None'

@dataclass
class WidgetDiff:
    """Complete diff between two widgets."""
    scalar_changes: tuple[AttrChange, ...]
    child_changes: tuple[ChildChange, ...]

def diff_scalars(
    prev: tuple[ScalarAttr, ...],
    next: tuple[ScalarAttr, ...],
) -> tuple[AttrChange, ...]:
    """Diff sorted scalar attributes using two-pointer algorithm."""
    changes: list[AttrChange] = []
    i, j = 0, 0
    
    while i < len(prev) or j < len(next):
        if i >= len(prev):
            # All remaining are additions
            changes.append(AttrChange("added", next[j].key, None, next[j].value))
            j += 1
        elif j >= len(next):
            # All remaining are removals
            changes.append(AttrChange("removed", prev[i].key, prev[i].value, None))
            i += 1
        elif prev[i].key < next[j].key:
            # Removed
            changes.append(AttrChange("removed", prev[i].key, prev[i].value, None))
            i += 1
        elif prev[i].key > next[j].key:
            # Added
            changes.append(AttrChange("added", next[j].key, None, next[j].value))
            j += 1
        else:
            # Same key - check if value changed
            if prev[i].value != next[j].value:
                changes.append(AttrChange("updated", prev[i].key, prev[i].value, next[j].value))
            i += 1
            j += 1
    
    return tuple(changes)

def can_reuse(prev: Widget, next: Widget) -> bool:
    """Determine if LVGL object can be reused."""
    if prev.key != next.key:
        return False
    if prev.user_key is not None or next.user_key is not None:
        return prev.user_key == next.user_key
    return True

def diff_children(
    prev: tuple[Widget, ...],
    next: tuple[Widget, ...],
) -> tuple[ChildChange, ...]:
    """Diff children using positional algorithm."""
    changes: list[ChildChange] = []
    max_len = max(len(prev), len(next))
    
    for i in range(max_len):
        if i >= len(next):
            # Remove excess children
            changes.append(ChildChange("remove", i, prev[i], None))
        elif i >= len(prev):
            # Insert new children
            changes.append(ChildChange("insert", i, next[i], None))
        elif can_reuse(prev[i], next[i]):
            # Update existing child
            child_diff = diff_widgets(prev[i], next[i])
            if child_diff.scalar_changes or child_diff.child_changes:
                changes.append(ChildChange("update", i, next[i], child_diff))
        else:
            # Replace child (different type or key)
            changes.append(ChildChange("replace", i, next[i], None))
    
    return tuple(changes)

def diff_widgets(prev: Widget | None, next: Widget) -> WidgetDiff:
    """Compute minimal changes between widget trees."""
    if prev is None:
        return WidgetDiff(
            scalar_changes=tuple(
                AttrChange("added", a.key, None, a.value) for a in next.scalar_attrs
            ),
            child_changes=tuple(
                ChildChange("insert", i, c, None) for i, c in enumerate(next.children)
            ),
        )
    
    return WidgetDiff(
        scalar_changes=diff_scalars(prev.scalar_attrs, next.scalar_attrs),
        child_changes=diff_children(prev.children, next.children),
    )
```

### Phase 3: ViewNode & Reconciliation

```python
# src/lvgl_mvu/viewnode.py

from dataclasses import dataclass, field
from .widget import Widget, WidgetKey
from .diff import WidgetDiff, AttrChange, ChildChange
from .attrs import get_attr_def

@dataclass
class ViewNode:
    """Persistent wrapper for LVGL object."""
    lv_obj: object
    widget: Widget
    children: list['ViewNode'] = field(default_factory=list)
    handlers: dict[int, object] = field(default_factory=dict)
    
    def apply_diff(self, diff: WidgetDiff) -> None:
        """Apply changes to LVGL object."""
        for change in diff.scalar_changes:
            attr_def = get_attr_def(change.key)
            if change.kind == "removed":
                attr_def.apply_fn(self.lv_obj, attr_def.default)
            else:
                attr_def.apply_fn(self.lv_obj, change.new_value)
    
    def dispose(self) -> None:
        """Clean up LVGL object and handlers."""
        import lvgl as lv
        
        # Dispose children first
        for child in self.children:
            child.dispose()
        self.children.clear()
        
        # Remove event handlers
        for handler in self.handlers.values():
            # lv.lv_obj_remove_event_cb(self.lv_obj, handler)
            pass
        self.handlers.clear()
        
        # Delete LVGL object
        lv.lv_obj_delete(self.lv_obj)
```

```python
# src/lvgl_mvu/reconciler.py

from .widget import Widget, WidgetKey
from .viewnode import ViewNode
from .diff import diff_widgets, ChildChange, can_reuse

class Reconciler:
    """Reconciles Widget trees with ViewNode trees."""
    
    def __init__(self) -> None:
        self._factories: dict[WidgetKey, callable] = {}
    
    def register_factory(self, key: WidgetKey, factory: callable) -> None:
        """Register factory function for widget type."""
        self._factories[key] = factory
    
    def reconcile(
        self,
        node: ViewNode | None,
        widget: Widget,
        parent_lv_obj: object | None = None,
    ) -> ViewNode:
        """Update or create ViewNode to match Widget."""
        if node is None or not can_reuse(node.widget, widget):
            # Create new node
            if node is not None:
                node.dispose()
            return self._create_node(widget, parent_lv_obj)
        
        # Diff and apply changes
        diff = diff_widgets(node.widget, widget)
        node.apply_diff(diff)
        
        # Reconcile children
        self._reconcile_children(node, widget, diff.child_changes)
        
        # Update event handlers
        self._reconcile_handlers(node, widget)
        
        node.widget = widget
        return node
    
    def _create_node(self, widget: Widget, parent_lv_obj: object | None) -> ViewNode:
        """Create new ViewNode for widget."""
        factory = self._factories.get(widget.key)
        if factory is None:
            raise ValueError(f"No factory for widget type: {widget.key}")
        
        lv_obj = factory(parent_lv_obj)
        node = ViewNode(lv_obj=lv_obj, widget=widget)
        
        # Apply all attributes
        for attr in widget.scalar_attrs:
            from .attrs import get_attr_def
            attr_def = get_attr_def(attr.key)
            attr_def.apply_fn(lv_obj, attr.value)
        
        # Create children
        for child_widget in widget.children:
            child_node = self._create_node(child_widget, lv_obj)
            node.children.append(child_node)
        
        # Register event handlers
        self._register_handlers(node, widget)
        
        return node
    
    def _reconcile_children(
        self,
        node: ViewNode,
        widget: Widget,
        changes: tuple[ChildChange, ...],
    ) -> None:
        """Reconcile child nodes."""
        for change in changes:
            if change.kind == "remove":
                child = node.children.pop(change.index)
                child.dispose()
            elif change.kind == "insert":
                child_node = self._create_node(change.widget, node.lv_obj)
                node.children.insert(change.index, child_node)
            elif change.kind == "update":
                self.reconcile(
                    node.children[change.index],
                    change.widget,
                    node.lv_obj,
                )
            elif change.kind == "replace":
                old_child = node.children[change.index]
                old_child.dispose()
                new_child = self._create_node(change.widget, node.lv_obj)
                node.children[change.index] = new_child
    
    def _register_handlers(self, node: ViewNode, widget: Widget) -> None:
        """Register event handlers on LVGL object."""
        # Implementation depends on event system
        pass
    
    def _reconcile_handlers(self, node: ViewNode, widget: Widget) -> None:
        """Update event handlers."""
        # Implementation depends on event system
        pass
```

### Phase 4: MVU Runtime

```python
# src/lvgl_mvu/program.py

from dataclasses import dataclass
from typing import TypeVar, Generic, Callable

Model = TypeVar('Model')
Msg = TypeVar('Msg')

Dispatch = Callable[[Msg], None]
Effect = Callable[[Dispatch], None]

@dataclass
class Cmd(Generic[Msg]):
    """Side effects that produce messages."""
    effects: list[Effect]
    
    @staticmethod
    def none() -> 'Cmd[Msg]':
        return Cmd([])
    
    @staticmethod
    def of_msg(msg: Msg) -> 'Cmd[Msg]':
        return Cmd([lambda dispatch: dispatch(msg)])
    
    @staticmethod
    def batch(cmds: list['Cmd[Msg]']) -> 'Cmd[Msg]':
        effects: list[Effect] = []
        for cmd in cmds:
            effects.extend(cmd.effects)
        return Cmd(effects)
    
    @staticmethod
    def of_effect(effect: Effect) -> 'Cmd[Msg]':
        return Cmd([effect])

@dataclass
class Sub(Generic[Msg]):
    """Subscriptions to external events."""
    subscriptions: list[tuple[str, Callable[[Dispatch], Callable[[], None]]]]
    
    @staticmethod
    def none() -> 'Sub[Msg]':
        return Sub([])
    
    @staticmethod
    def timer(interval_ms: int, msg: Msg) -> 'Sub[Msg]':
        def subscribe(dispatch: Dispatch) -> Callable[[], None]:
            import lvgl as lv
            
            def timer_cb(timer):
                dispatch(msg)
            
            timer = lv.lv_timer_create(timer_cb, interval_ms, None)
            return lambda: lv.lv_timer_delete(timer)
        
        return Sub([("timer", subscribe)])

@dataclass
class Program(Generic[Model, Msg]):
    """MVU program definition."""
    init: Callable[[], tuple[Model, Cmd[Msg]]]
    update: Callable[[Msg, Model], tuple[Model, Cmd[Msg]]]
    view: Callable[[Model], 'Widget']
    subscribe: Callable[[Model], Sub[Msg]] | None = None
```

```python
# src/lvgl_mvu/app.py

from typing import TypeVar, Generic
from .program import Program, Cmd, Sub, Dispatch
from .widget import Widget
from .viewnode import ViewNode
from .reconciler import Reconciler

Model = TypeVar('Model')
Msg = TypeVar('Msg')

class App(Generic[Model, Msg]):
    """MVU application runner."""
    
    def __init__(self, program: Program[Model, Msg]) -> None:
        self.program = program
        self.reconciler = Reconciler()
        
        # Initialize state
        self.model, init_cmd = program.init()
        self.root_node: ViewNode | None = None
        self.msg_queue: list[Msg] = []
        self._subscriptions: list[Callable[[], None]] = []
        
        # Execute init command
        self._execute_cmd(init_cmd)
        
        # Setup subscriptions
        self._setup_subscriptions()
    
    def dispatch(self, msg: Msg) -> None:
        """Queue a message for processing."""
        self.msg_queue.append(msg)
    
    def tick(self) -> None:
        """Process queued messages and re-render if needed."""
        changed = False
        
        while self.msg_queue:
            msg = self.msg_queue.pop(0)
            self.model, cmd = self.program.update(msg, self.model)
            self._execute_cmd(cmd)
            changed = True
        
        if changed or self.root_node is None:
            widget = self.program.view(self.model)
            self.root_node = self.reconciler.reconcile(self.root_node, widget)
            
            # Re-setup subscriptions if model changed
            if changed:
                self._setup_subscriptions()
    
    def dispose(self) -> None:
        """Clean up resources."""
        for unsub in self._subscriptions:
            unsub()
        self._subscriptions.clear()
        
        if self.root_node is not None:
            self.root_node.dispose()
            self.root_node = None
    
    def _execute_cmd(self, cmd: Cmd[Msg]) -> None:
        """Execute command effects."""
        for effect in cmd.effects:
            effect(self.dispatch)
    
    def _setup_subscriptions(self) -> None:
        """Setup subscriptions based on current model."""
        # Unsubscribe existing
        for unsub in self._subscriptions:
            unsub()
        self._subscriptions.clear()
        
        # Subscribe new
        if self.program.subscribe is not None:
            sub = self.program.subscribe(self.model)
            for name, subscribe_fn in sub.subscriptions:
                unsub = subscribe_fn(self.dispatch)
                self._subscriptions.append(unsub)
```

### Phase 5: Async Support

#### 5.1 Async Command Implementation

**Goal**: Enable async/await for side effects without blocking UI.

```python
# src/lvgl_mvu/async_cmd.py

from dataclasses import dataclass
from typing import TypeVar, Generic, Callable, Coroutine, Any
import asyncio

Model = TypeVar('Model')
Msg = TypeVar('Msg')

Dispatch = Callable[[Msg], None]
AsyncEffect = Callable[[Dispatch], Coroutine[Any, Any, None]]

@dataclass
class AsyncCmd(Generic[Msg]):
    """Async side effects that produce messages."""
    effects: list[AsyncEffect]
    
    @staticmethod
    def none() -> 'AsyncCmd[Msg]':
        return AsyncCmd([])
    
    @staticmethod
    def of_async(coro_fn: Callable[[Dispatch], Coroutine]) -> 'AsyncCmd[Msg]':
        """Create command from async function."""
        return AsyncCmd([coro_fn])
    
    @staticmethod
    def http_get(url: str, on_success: Callable[[str], Msg], on_error: Callable[[str], Msg]) -> 'AsyncCmd[Msg]':
        """HTTP GET request command."""
        async def effect(dispatch: Dispatch) -> None:
            try:
                import urequests  # MicroPython HTTP
                response = urequests.get(url)
                data = response.text
                response.close()
                dispatch(on_success(data))
            except Exception as e:
                dispatch(on_error(str(e)))
        
        return AsyncCmd([effect])
    
    @staticmethod
    def delay(ms: int, msg: Msg) -> 'AsyncCmd[Msg]':
        """Delayed message dispatch."""
        async def effect(dispatch: Dispatch) -> None:
            await asyncio.sleep_ms(ms)
            dispatch(msg)
        
        return AsyncCmd([effect])
    
    @staticmethod
    def batch(cmds: list['AsyncCmd[Msg]']) -> 'AsyncCmd[Msg]':
        """Combine multiple async commands."""
        effects: list[AsyncEffect] = []
        for cmd in cmds:
            effects.extend(cmd.effects)
        return AsyncCmd(effects)
```

#### 5.2 Async Application Runner

```python
# src/lvgl_mvu/async_app.py

from typing import TypeVar, Generic
import asyncio
from .program import Program, Cmd, Sub, Dispatch
from .async_cmd import AsyncCmd
from .widget import Widget
from .viewnode import ViewNode
from .reconciler import Reconciler

Model = TypeVar('Model')
Msg = TypeVar('Msg')

@dataclass
class AsyncProgram(Generic[Model, Msg]):
    """MVU program with async support."""
    init: Callable[[], tuple[Model, Cmd[Msg] | AsyncCmd[Msg]]]
    update: Callable[[Msg, Model], tuple[Model, Cmd[Msg] | AsyncCmd[Msg]]]
    view: Callable[[Model], Widget]
    subscribe: Callable[[Model], Sub[Msg]] | None = None

class AsyncApp(Generic[Model, Msg]):
    """MVU application runner with async support."""
    
    def __init__(self, program: AsyncProgram[Model, Msg]) -> None:
        self.program = program
        self.reconciler = Reconciler()
        
        # Initialize state
        self.model, init_cmd = program.init()
        self.root_node: ViewNode | None = None
        self.msg_queue: list[Msg] = []
        self._subscriptions: list[Callable[[], None]] = []
        self._pending_tasks: list[asyncio.Task] = []
        self._running = False
        
        # Execute init command
        self._schedule_cmd(init_cmd)
    
    def dispatch(self, msg: Msg) -> None:
        """Queue a message for processing."""
        self.msg_queue.append(msg)
    
    def _schedule_cmd(self, cmd: Cmd[Msg] | AsyncCmd[Msg]) -> None:
        """Schedule command for execution."""
        if isinstance(cmd, AsyncCmd):
            for effect in cmd.effects:
                task = asyncio.create_task(effect(self.dispatch))
                self._pending_tasks.append(task)
        elif isinstance(cmd, Cmd):
            for effect in cmd.effects:
                effect(self.dispatch)
    
    async def tick(self) -> None:
        """Process queued messages and re-render if needed."""
        changed = False
        
        # Clean up completed tasks
        self._pending_tasks = [t for t in self._pending_tasks if not t.done()]
        
        while self.msg_queue:
            msg = self.msg_queue.pop(0)
            self.model, cmd = self.program.update(msg, self.model)
            self._schedule_cmd(cmd)
            changed = True
        
        if changed or self.root_node is None:
            widget = self.program.view(self.model)
            self.root_node = self.reconciler.reconcile(self.root_node, widget)
            
            if changed:
                self._setup_subscriptions()
    
    async def run(self, tick_ms: int = 10) -> None:
        """Main async event loop."""
        import lvgl as lv
        
        self._running = True
        while self._running:
            await self.tick()
            lv.timer_handler()
            await asyncio.sleep_ms(tick_ms)
    
    async def cancel_all_tasks(self) -> None:
        """Cancel all pending async tasks."""
        for task in self._pending_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._pending_tasks.clear()
    
    def stop(self) -> None:
        """Stop the application."""
        self._running = False
    
    async def dispose(self) -> None:
        """Clean up resources."""
        self.stop()
        await self.cancel_all_tasks()
        
        for unsub in self._subscriptions:
            unsub()
        self._subscriptions.clear()
        
        if self.root_node is not None:
            self.root_node.dispose()
            self.root_node = None
    
    def _setup_subscriptions(self) -> None:
        """Setup subscriptions based on current model."""
        for unsub in self._subscriptions:
            unsub()
        self._subscriptions.clear()
        
        if self.program.subscribe is not None:
            sub = self.program.subscribe(self.model)
            for name, subscribe_fn in sub.subscriptions:
                unsub = subscribe_fn(self.dispatch)
                self._subscriptions.append(unsub)
```

#### 5.3 Async Subscriptions

```python
# src/lvgl_mvu/async_sub.py

from dataclasses import dataclass
from typing import TypeVar, Generic, Callable, Coroutine, Any
import asyncio

Msg = TypeVar('Msg')
Dispatch = Callable[[Msg], None]

@dataclass
class AsyncSub(Generic[Msg]):
    """Async subscriptions to external events."""
    subscriptions: list[tuple[str, Callable[[Dispatch], Coroutine[Any, Any, Callable[[], None]]]]]
    
    @staticmethod
    def none() -> 'AsyncSub[Msg]':
        return AsyncSub([])
    
    @staticmethod
    def interval(ms: int, msg_fn: Callable[[], Msg]) -> 'AsyncSub[Msg]':
        """Periodic async timer."""
        async def subscribe(dispatch: Dispatch) -> Callable[[], None]:
            running = True
            
            async def loop():
                while running:
                    await asyncio.sleep_ms(ms)
                    dispatch(msg_fn())
            
            task = asyncio.create_task(loop())
            
            def cancel():
                nonlocal running
                running = False
                task.cancel()
            
            return cancel
        
        return AsyncSub([("interval", subscribe)])
    
    @staticmethod
    def stream(reader: asyncio.StreamReader, on_data: Callable[[bytes], Msg]) -> 'AsyncSub[Msg]':
        """Subscribe to async stream data."""
        async def subscribe(dispatch: Dispatch) -> Callable[[], None]:
            running = True
            
            async def read_loop():
                while running:
                    try:
                        data = await reader.read(1024)
                        if data:
                            dispatch(on_data(data))
                    except asyncio.CancelledError:
                        break
            
            task = asyncio.create_task(read_loop())
            
            def cancel():
                nonlocal running
                running = False
                task.cancel()
            
            return cancel
        
        return AsyncSub([("stream", subscribe)])
```

#### 5.4 Background Task Manager

```python
# src/lvgl_mvu/tasks.py

from dataclasses import dataclass, field
from typing import TypeVar, Generic, Callable, Any
import asyncio

Msg = TypeVar('Msg')

@dataclass
class TaskHandle:
    """Handle to a background task."""
    task_id: str
    task: asyncio.Task
    
    def cancel(self) -> None:
        """Cancel the task."""
        self.task.cancel()
    
    def done(self) -> bool:
        """Check if task is complete."""
        return self.task.done()

class TaskManager(Generic[Msg]):
    """Manages background async tasks."""
    
    def __init__(self, dispatch: Callable[[Msg], None]) -> None:
        self.dispatch = dispatch
        self._tasks: dict[str, TaskHandle] = {}
        self._task_counter = 0
    
    def spawn(
        self,
        coro: asyncio.Coroutine,
        task_id: str | None = None,
        on_complete: Msg | None = None,
        on_error: Callable[[Exception], Msg] | None = None,
    ) -> TaskHandle:
        """Spawn a background task."""
        if task_id is None:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"
        
        async def wrapper():
            try:
                result = await coro
                if on_complete is not None:
                    self.dispatch(on_complete)
                return result
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if on_error is not None:
                    self.dispatch(on_error(e))
                else:
                    raise
            finally:
                self._tasks.pop(task_id, None)
        
        task = asyncio.create_task(wrapper())
        handle = TaskHandle(task_id, task)
        self._tasks[task_id] = handle
        return handle
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a specific task."""
        handle = self._tasks.get(task_id)
        if handle:
            handle.cancel()
            return True
        return False
    
    async def cancel_all(self) -> None:
        """Cancel all tasks."""
        for handle in list(self._tasks.values()):
            handle.cancel()
            try:
                await handle.task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
    
    def active_count(self) -> int:
        """Get number of active tasks."""
        return len(self._tasks)
```

---


---

## Widget Catalog

### Priority 0 (Essential)

| Widget | LVGL API | DSL Function | Attributes |
|--------|----------|--------------|------------|
| Screen | `lv_obj_create(None)` | `Screen()` | bg_color, padding |
| Container | `lv_obj_create(parent)` | `Container()` | size, pos, bg_color, padding, flex |
| Label | `lv_label_create` | `Label(text)` | text, text_color, font |
| Button | `lv_button_create` | `Button(text, on_click)` | text, size, bg_color |

### Priority 1 (Interactive)

| Widget | LVGL API | DSL Function | Attributes |
|--------|----------|--------------|------------|
| Slider | `lv_slider_create` | `Slider(min, max, value, on_change)` | range, value |
| Bar | `lv_bar_create` | `Bar(min, max, value)` | range, value |
| Arc | `lv_arc_create` | `Arc(min, max, value, on_change)` | range, value, angles |
| Switch | `lv_switch_create` | `Switch(checked, on_change)` | checked |
| Checkbox | `lv_checkbox_create` | `Checkbox(text, checked, on_change)` | text, checked |

### Priority 2 (Forms)

| Widget | LVGL API | DSL Function | Attributes |
|--------|----------|--------------|------------|
| Image | `lv_image_create` | `Image(src)` | src, size, zoom |
| TextArea | `lv_textarea_create` | `TextArea(text, placeholder, on_change)` | text, placeholder |
| Dropdown | `lv_dropdown_create` | `Dropdown(options, selected, on_change)` | options, selected |
| Roller | `lv_roller_create` | `Roller(options, selected, on_change)` | options, selected, visible |
| Table | `lv_table_create` | `Table(rows, cols, data)` | rows, cols, cell_value |
| List | `lv_list_create` | `List(items)` | items |

### Priority 3 (Advanced)

| Widget | LVGL API | DSL Function | Attributes |
|--------|----------|--------------|------------|
| Chart | `lv_chart_create` | `Chart(type, series)` | type, range, points |
| Calendar | `lv_calendar_create` | `Calendar(date, on_change)` | date, highlighted |
| Keyboard | `lv_keyboard_create` | `Keyboard(target, mode)` | mode, target |
| Menu | `lv_menu_create` | `Menu(items)` | items, selected |
| TabView | `lv_tabview_create` | `TabView(tabs)` | tabs, active |
| MessageBox | `lv_msgbox_create` | `MessageBox(title, text, buttons)` | title, text, buttons |
| Spinner | `lv_spinner_create` | `Spinner()` | arc_length, time |
| LED | `lv_led_create` | `LED(color, brightness)` | color, brightness |
| Line | `lv_line_create` | `Line(points)` | points, width, color |
| Canvas | `lv_canvas_create` | `Canvas(width, height)` | size |
| Window | `lv_win_create` | `Window(title, content)` | title, header_height |
| TileView | `lv_tileview_create` | `TileView(tiles)` | tiles, active |
| Spangroup | `lv_spangroup_create` | `Spangroup(spans)` | spans |
| Spinbox | `lv_spinbox_create` | `Spinbox(min, max, value, on_change)` | range, value, digits |
| Scale | `lv_scale_create` | `Scale(min, max)` | range, ticks |
| ButtonMatrix | `lv_buttonmatrix_create` | `ButtonMatrix(buttons, on_click)` | map, checked |
| ArcLabel | `lv_arclabel_create` | `ArcLabel(text, arc)` | text, offset |
| AnimImg | `lv_animimg_create` | `AnimImg(images, duration)` | images, duration |

---

## API Reference

### DSL Functions

```python
# Containers
Screen(**attrs) -> WidgetBuilder
Container(**attrs) -> WidgetBuilder
VStack(spacing=0, **attrs) -> WidgetBuilder
HStack(spacing=0, **attrs) -> WidgetBuilder
Grid(cols, rows, **attrs) -> WidgetBuilder

# Display
Label(text, **attrs) -> WidgetBuilder
Image(src, **attrs) -> WidgetBuilder

# Buttons
Button(text, on_click, **attrs) -> WidgetBuilder
ButtonMatrix(map, on_click, **attrs) -> WidgetBuilder

# Inputs
Slider(min, max, value, on_change, **attrs) -> WidgetBuilder
TextArea(text, placeholder, on_change, **attrs) -> WidgetBuilder
Dropdown(options, selected, on_change, **attrs) -> WidgetBuilder
Checkbox(text, checked, on_change, **attrs) -> WidgetBuilder
Switch(checked, on_change, **attrs) -> WidgetBuilder

# Progress
Bar(min, max, value, **attrs) -> WidgetBuilder
Arc(min, max, value, on_change, **attrs) -> WidgetBuilder
Spinner(**attrs) -> WidgetBuilder

# Data
Table(data, **attrs) -> WidgetBuilder
List(items, **attrs) -> WidgetBuilder
Chart(type, series, **attrs) -> WidgetBuilder
```

### Common Attributes

```python
# All widgets
.key(str)                    # Reuse key
.width(int) / .height(int)   # Size
.size(w, h)                  # Size shorthand
.pos(x, y)                   # Position
.align(LvAlign, x_ofs, y_ofs) # Alignment
.padding(t, r, b, l)         # Padding
.hidden(bool)                # Visibility
.disabled(bool)              # Interactivity

# Styling
.bg_color(hex)               # Background color
.bg_opa(0-255)               # Background opacity
.border_color(hex)           # Border color
.border_width(int)           # Border width
.radius(int)                 # Corner radius
.shadow_width(int)           # Shadow size

# Text
.text_color(hex)             # Text color
.font_size(int)              # Font size
.text_align(LvTextAlign)     # Text alignment
```

### Program API

```python
# Define program
Program(
    init: () -> (Model, Cmd[Msg]),
    update: (Msg, Model) -> (Model, Cmd[Msg]),
    view: (Model) -> Widget,
    subscribe: (Model) -> Sub[Msg] | None = None,
)

# Run application
app = App(program)
while True:
    app.tick()
    lv.timer_handler()
    time.sleep_ms(10)

# Commands (Sync)
Cmd.none()                   # No side effects
Cmd.of_msg(msg)              # Dispatch message
Cmd.batch([cmd1, cmd2])      # Combine commands
Cmd.of_effect(fn)            # Custom effect

# Async Commands
AsyncCmd.none()              # No async effects
AsyncCmd.of_async(coro_fn)   # From async function
AsyncCmd.http_get(url, on_success, on_error)  # HTTP GET
AsyncCmd.delay(ms, msg)      # Delayed message
AsyncCmd.batch([cmd1, cmd2]) # Combine async commands

# Subscriptions (Sync)
Sub.none()                   # No subscriptions
Sub.timer(interval_ms, msg)  # Timer subscription

# Async Subscriptions
AsyncSub.none()              # No async subscriptions
AsyncSub.interval(ms, msg_fn) # Periodic async timer
AsyncSub.stream(reader, on_data) # Stream subscription
```

### Async API

```python
# Define async program
AsyncProgram(
    init: () -> (Model, Cmd[Msg] | AsyncCmd[Msg]),
    update: (Msg, Model) -> (Model, Cmd[Msg] | AsyncCmd[Msg]),
    view: (Model) -> Widget,
    subscribe: (Model) -> Sub[Msg] | None = None,
)

# Run async application
app = AsyncApp(program)
asyncio.run(app.run(tick_ms=10))

# Or manual control
async def main():
    app = AsyncApp(program)
    try:
        await app.run()
    finally:
        await app.dispose()

asyncio.run(main())

# Task management
task_mgr = TaskManager(app.dispatch)
handle = task_mgr.spawn(some_coro(), on_complete=Msg.DONE)
task_mgr.cancel(handle.task_id)
await task_mgr.cancel_all()

```
---

## File Structure

```
src/lvgl_mvu/
├── __init__.py              # Public API exports
├── widget.py                # Widget, ScalarAttr, WidgetKey
├── attrs.py                 # AttrKey, AttrDef, registry
├── builders.py              # WidgetBuilder base class
├── dsl.py                   # Label, Button, etc. factories
├── diff.py                  # Diffing algorithm
├── viewnode.py              # ViewNode LVGL wrapper
├── reconciler.py            # Reconciliation engine
├── program.py               # Program, Cmd, Sub
├── app.py                   # Sync App runner
├── async_cmd.py             # AsyncCmd implementation
├── async_app.py             # Async App runner
├── async_sub.py             # Async subscriptions
├── tasks.py                 # Background task manager
├── events.py                # LvEvent enum
├── layouts.py               # VStack, HStack, Grid
├── navigation.py            # NavCmd integration
├── memo.py                  # Memoization utilities
└── widgets/                 # Widget implementations
    ├── __init__.py
    ├── base.py              # Base attribute registration
    ├── screen.py
    ├── container.py
    ├── label.py
    ├── button.py
    ├── slider.py
    ├── bar.py
    ├── arc.py
    ├── switch.py
    ├── checkbox.py
    ├── image.py
    ├── textarea.py
    ├── dropdown.py
    ├── roller.py
    ├── table.py
    ├── list.py
    ├── chart.py
    ├── calendar.py
    ├── keyboard.py
    ├── menu.py
    ├── tabview.py
    ├── msgbox.py
    ├── spinner.py
    ├── led.py
    ├── line.py
    ├── canvas.py
    ├── window.py
    ├── tileview.py
    ├── spangroup.py
    ├── spinbox.py
    ├── scale.py
    ├── buttonmatrix.py
    ├── arclabel.py
    └── animimg.py

examples/lvgl_mvu/
├── counter_app.py           # Simple counter
├── form_app.py              # Form inputs
├── navigation_app.py        # Multi-screen
├── dashboard_app.py         # Complex dashboard
├── todo_app.py              # Todo list
├── async_http_app.py        # Async HTTP fetch demo
└── async_sensor_app.py      # Async sensor polling

tests/
├── test_widget.py
├── test_diff.py
├── test_reconciler.py
├── test_app.py
├── test_async_app.py        # Async app tests
└── device/
    ├── run_mvu_p0_tests.py
    ├── run_mvu_p1_tests.py
    ├── run_mvu_nav_tests.py
    ├── run_mvu_async_tests.py # Async tests on device
    └── run_mvu_benchmarks.py

docs/
├── lvgl-mvu-framework-plan.md  # This document
├── lvgl-mvu-api.md             # API reference
├── lvgl-mvu-tutorial.md        # Getting started
└── lvgl-mvu-performance.md     # Optimization guide
```

---

## Example Application

### Counter App (Complete)

```python
"""Counter application demonstrating MVU pattern."""
from dataclasses import dataclass
from lvgl_mvu import App, Program, Cmd, Widget
from lvgl_mvu.dsl import Screen, VStack, Label, Button, Slider
from lvgl_mvu.attrs import LvAlign
import lvgl as lv
import time

# =============================================================================
# Model
# =============================================================================

@dataclass(frozen=True)
class Model:
    count: int
    step: int

# =============================================================================
# Messages
# =============================================================================

class Msg:
    INCREMENT = "increment"
    DECREMENT = "decrement"
    RESET = "reset"
    SET_STEP = "set_step"  # payload: int

# =============================================================================
# Init
# =============================================================================

def init() -> tuple[Model, Cmd]:
    return Model(count=0, step=1), Cmd.none()

# =============================================================================
# Update
# =============================================================================

def update(msg: object, model: Model) -> tuple[Model, Cmd]:
    if msg == Msg.INCREMENT:
        return Model(model.count + model.step, model.step), Cmd.none()
    
    elif msg == Msg.DECREMENT:
        return Model(model.count - model.step, model.step), Cmd.none()
    
    elif msg == Msg.RESET:
        return Model(0, model.step), Cmd.none()
    
    elif isinstance(msg, tuple) and msg[0] == Msg.SET_STEP:
        return Model(model.count, msg[1]), Cmd.none()
    
    return model, Cmd.none()

# =============================================================================
# View
# =============================================================================

def view(model: Model) -> Widget:
    return Screen().bg_color(0x1a1a2e)(
        VStack(spacing=20).align(LvAlign.CENTER)(
            # Title
            Label("Counter Demo")
                .text_color(0xFFFFFF)
                .font_size(28),
            
            # Count display
            Label(f"Count: {model.count}")
                .text_color(0x00FF00 if model.count >= 0 else 0xFF0000)
                .font_size(48),
            
            # Buttons row
            HStack(spacing=20)(
                Button("-", Msg.DECREMENT)
                    .size(80, 50)
                    .bg_color(0xFF6B6B),
                
                Button("Reset", Msg.RESET)
                    .size(80, 50)
                    .bg_color(0x4ECDC4),
                
                Button("+", Msg.INCREMENT)
                    .size(80, 50)
                    .bg_color(0x45B7D1),
            ),
            
            # Step control
            Label(f"Step: {model.step}").text_color(0xAAAAAA),
            
            Slider(1, 10, model.step, lambda v: (Msg.SET_STEP, v))
                .width(200),
        )
    )

# =============================================================================
# Main
# =============================================================================

def main():
    # Initialize LVGL display (platform-specific)
    # ...
    
    # Create and run app
    program = Program(init=init, update=update, view=view)
    app = App(program)
    
    # Main loop
    while True:
        app.tick()
        lv.timer_handler()
        time.sleep_ms(10)

if __name__ == "__main__":
    main()
```

### Navigation App (Multi-Screen)

```python
"""Multi-screen navigation demo."""
from dataclasses import dataclass
from lvgl_mvu import App, Program, Cmd, Widget
from lvgl_mvu.dsl import Screen, VStack, Label, Button
from lvgl_mvu.navigation import NavCmd

# Screens
SCREEN_HOME = 0
SCREEN_SETTINGS = 1
SCREEN_ABOUT = 2

@dataclass(frozen=True)
class Model:
    screen: int
    settings_value: int

class Msg:
    GO_HOME = "go_home"
    GO_SETTINGS = "go_settings"
    GO_ABOUT = "go_about"
    BACK = "back"
    SET_VALUE = "set_value"

def init() -> tuple[Model, Cmd]:
    return Model(screen=SCREEN_HOME, settings_value=50), Cmd.none()

def update(msg: object, model: Model) -> tuple[Model, Cmd]:
    if msg == Msg.GO_SETTINGS:
        return Model(SCREEN_SETTINGS, model.settings_value), NavCmd.push(SCREEN_SETTINGS)
    elif msg == Msg.GO_ABOUT:
        return Model(SCREEN_ABOUT, model.settings_value), NavCmd.push(SCREEN_ABOUT)
    elif msg == Msg.GO_HOME:
        return Model(SCREEN_HOME, model.settings_value), NavCmd.replace(SCREEN_HOME)
    elif msg == Msg.BACK:
        return model, NavCmd.pop()
    elif isinstance(msg, tuple) and msg[0] == Msg.SET_VALUE:
        return Model(model.screen, msg[1]), Cmd.none()
    return model, Cmd.none()

def view(model: Model) -> Widget:
    if model.screen == SCREEN_HOME:
        return view_home(model)
    elif model.screen == SCREEN_SETTINGS:
        return view_settings(model)
    else:
        return view_about(model)

def view_home(model: Model) -> Widget:
    return Screen()(
        VStack(spacing=20)(
            Label("Home").font_size(32),
            Button("Settings", Msg.GO_SETTINGS),
            Button("About", Msg.GO_ABOUT),
        )
    )

def view_settings(model: Model) -> Widget:
    return Screen()(
        VStack(spacing=20)(
            Label("Settings").font_size(32),
            Label(f"Value: {model.settings_value}"),
            Slider(0, 100, model.settings_value, lambda v: (Msg.SET_VALUE, v)),
            Button("Back", Msg.BACK),
        )
    )

def view_about(model: Model) -> Widget:
    return Screen()(
        VStack(spacing=20)(
            Label("About").font_size(32),
            Label("LVGL MVU Framework"),
            Label("Version 1.0.0"),
            Button("Back", Msg.BACK),
        )
    )
```

### Async HTTP App (Async Demo)

```python
"""Async HTTP fetch demo with loading states."""
from dataclasses import dataclass
from lvgl_mvu import AsyncApp, AsyncProgram, Cmd, AsyncCmd, Widget
from lvgl_mvu.dsl import Screen, VStack, HStack, Label, Button, Spinner
import asyncio

# =============================================================================
# Model
# =============================================================================

@dataclass(frozen=True)
class Model:
    loading: bool
    data: str | None
    error: str | None

# =============================================================================
# Messages
# =============================================================================

class Msg:
    FETCH_DATA = "fetch_data"
    DATA_RECEIVED = "data_received"  # payload: str
    FETCH_ERROR = "fetch_error"      # payload: str
    CLEAR = "clear"

# =============================================================================
# Init
# =============================================================================

def init() -> tuple[Model, Cmd]:
    return Model(loading=False, data=None, error=None), Cmd.none()

# =============================================================================
# Update
# =============================================================================

def update(msg: object, model: Model) -> tuple[Model, Cmd | AsyncCmd]:
    if msg == Msg.FETCH_DATA:
        # Start loading, dispatch async HTTP request
        return (
            Model(loading=True, data=None, error=None),
            AsyncCmd.http_get(
                url="https://api.example.com/data",
                on_success=lambda data: (Msg.DATA_RECEIVED, data),
                on_error=lambda err: (Msg.FETCH_ERROR, err),
            )
        )
    
    elif isinstance(msg, tuple) and msg[0] == Msg.DATA_RECEIVED:
        return Model(loading=False, data=msg[1], error=None), Cmd.none()
    
    elif isinstance(msg, tuple) and msg[0] == Msg.FETCH_ERROR:
        return Model(loading=False, data=None, error=msg[1]), Cmd.none()
    
    elif msg == Msg.CLEAR:
        return Model(loading=False, data=None, error=None), Cmd.none()
    
    return model, Cmd.none()

# =============================================================================
# View
# =============================================================================

def view(model: Model) -> Widget:
    return Screen().bg_color(0x1a1a2e)(
        VStack(spacing=20)(
            Label("Async HTTP Demo")
                .font_size(28)
                .text_color(0xFFFFFF),
            
            # Content area
            view_content(model),
            
            # Action buttons
            HStack(spacing=20)(
                Button("Fetch Data", Msg.FETCH_DATA)
                    .width(120)
                    .disabled(model.loading),
                
                Button("Clear", Msg.CLEAR)
                    .width(80)
                    .disabled(model.loading),
            ),
        )
    )

def view_content(model: Model) -> Widget:
    if model.loading:
        return VStack()(
            Spinner().size(50, 50),
            Label("Loading...").text_color(0xAAAAAA),
        )
    elif model.error:
        return Label(f"Error: {model.error}")
            .text_color(0xFF6B6B)
    elif model.data:
        return Label(model.data)
            .text_color(0x4ECDC4)
    else:
        return Label("Press 'Fetch Data' to start")
            .text_color(0x888888)

# =============================================================================
# Main
# =============================================================================

async def main():
    program = AsyncProgram(init=init, update=update, view=view)
    app = AsyncApp(program)
    
    try:
        await app.run(tick_ms=10)
    finally:
        await app.dispose()

if __name__ == "__main__":
    asyncio.run(main())

---

## Timeline Summary

| Week | Milestone | Key Deliverables |
|------|-----------|------------------|
| 1-2 | Foundation | Widget, attrs, builders |
| 2-3 | Diffing | O(N) diff algorithm |
| 3-4 | ViewNode | LVGL wrapper, reconciler |
| 4 | MVU Runtime | Program, Cmd, App |
| 5 | P0 Widgets | Screen, Label, Button |
| 5-6 | Events | Event binding system |
| 6-7 | P1 Widgets | Slider, Bar, Arc, Switch |
| 7 | Navigation | Multi-screen support |
| 8-9 | P2 Widgets | Image, TextArea, Dropdown |
| 9-10 | Optimizations | Memoization, dirty checking |
| 10-11 | **Async Support** | AsyncCmd, AsyncApp, tasks |
| 11-13 | P3 Widgets | Chart, Calendar, etc. |
| 13-14 | Documentation | API docs, tutorials, async guide |

**Total Duration**: ~14 weeks

---

## Success Criteria

### Performance

- [ ] <10% overhead vs direct LVGL calls
- [ ] O(N) diffing complexity verified
- [ ] Memory usage stable under stress test
- [ ] 60 FPS maintained on ESP32-C6
- [ ] Async operations don't block UI thread

### Functionality

- [ ] All 30+ LVGL widgets supported
- [ ] Event handling works correctly
- [ ] Navigation with animations
- [ ] Memoization prevents unnecessary updates
- [ ] Async HTTP/network operations work
- [ ] Background tasks can be cancelled
- [ ] Loading states render correctly

### Quality

- [ ] 100% type coverage (mypy strict)
- [ ] Unit test coverage >90%
- [ ] Device tests pass on ESP32
- [ ] Async tests pass on device
- [ ] Documentation complete

### Usability

- [ ] Declarative DSL is intuitive
- [ ] Error messages are helpful
- [ ] Examples cover common patterns
- [ ] Async patterns documented
- [ ] Migration guide available
