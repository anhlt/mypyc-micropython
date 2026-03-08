# 35. LVGL MVU Framework Architecture: Compiling Declarative UI to Native C

*A Fabulous-style Model-View-Update framework where a declarative widget tree compiles down to tight LVGL C calls.*

---

## Table of Contents

1. [Overview](#overview)
2. [Part 1: Compiler Theory](#part-1-compiler-theory)
   - [1.1 MVU as a compilation target](#11-mvu-as-a-compilation-target)
   - [1.2 Widget trees as an intermediate representation](#12-widget-trees-as-an-intermediate-representation)
   - [1.3 Immutable trees and predictable memory](#13-immutable-trees-and-predictable-memory)
   - [1.4 O(N) diffing: positional children, merge-style attributes](#14-on-diffing-positional-children-merge-style-attributes)
   - [1.5 Why this maps cleanly to C](#15-why-this-maps-cleanly-to-c)
3. [Part 2: C Background](#part-2-c-background)
   - [2.1 LVGL object model: `lv_obj_t` and creation APIs](#21-lvgl-object-model-lv_obj_t-and-creation-apis)
   - [2.2 Function pointers for callbacks and dispatch](#22-function-pointers-for-callbacks-and-dispatch)
   - [2.3 Tagged unions for attribute values and widget kinds](#23-tagged-unions-for-attribute-values-and-widget-kinds)
   - [2.4 Struct composition for hierarchies](#24-struct-composition-for-hierarchies)
   - [2.5 MicroPython `mp_obj_t`, boxing, and unboxing](#25-micropython-mp_obj_t-boxing-and-unboxing)
4. [Part 3: Implementation](#part-3-implementation)
   - [3.1 Core data types: `Widget`, `ScalarAttr`, `WidgetKey`](#31-core-data-types-widget-scalarattr-widgetkey)
   - [3.2 Attribute registry: `AttrKey` and `AttrDef.apply_fn`](#32-attribute-registry-attrkey-and-attrdefapply_fn)
   - [3.3 Fluent DSL: `WidgetBuilder` and widget constructors](#33-fluent-dsl-widgetbuilder-and-widget-constructors)
   - [3.4 Diffing engine with a concrete example](#34-diffing-engine-with-a-concrete-example)
   - [3.5 Reconciliation: `ViewNode` bridges Widgets to LVGL](#35-reconciliation-viewnode-bridges-widgets-to-lvgl)
   - [3.6 MVU runtime loop: `Program`, `Cmd`, `Sub`, `App`](#36-mvu-runtime-loop-program-cmd-sub-app)
   - [3.7 Async integration: `AsyncCmd`, `AsyncApp`, background tasks](#37-async-integration-asynccmd-asyncapp-background-tasks)
   - [3.8 Counter app walkthrough](#38-counter-app-walkthrough)
   - [3.9 Widget catalog summary (P0 to P3)](#39-widget-catalog-summary-p0-to-p3)

---

# Overview

This post is the architecture story for an LVGL MVU framework designed for `mypyc-micropython`.

The goal is simple to describe and hard to get right on microcontrollers:

- Write UI in a declarative, message-driven style.
- Keep updates efficient and predictable.
- Compile the whole thing to native C, so the abstraction doesn't cost runtime overhead.

If you read blog 31, you saw MVU used for navigation and screen lifecycles. This post zooms in on the framework core: how a pure `view(model) -> Widget` function turns into a stable LVGL object tree with minimal changes per tick.

The plan that drives this design lives in `docs/lvgl-mvu-framework-plan.md`.

---

# Part 1: Compiler Theory

MVU feels like an application architecture, but it is also a compilation strategy.

When you compile typed Python to a MicroPython C module, you want patterns that:

- are explicit (so the compiler can reason about them),
- avoid dynamic reflection (so emitted C is direct),
- keep memory usage bounded (so your UI does not die slowly from fragmentation).

The MVU approach hits all three.

## 1.1 MVU as a compilation target

The MVU loop is a small state machine:

1. Inputs become messages (`Msg`).
2. An `update(msg, model)` function returns a new `model` plus a command (`Cmd`) describing side effects.
3. A `view(model)` function returns a virtual widget tree (`Widget`).
4. A diff compares the new widget tree with the previous one.
5. A reconciler applies the diff to the real LVGL objects.

That is all. No direct mutation inside `view()`. No scattered event handlers poking at global state.

Here is the core data flow as an ASCII diagram (from the framework plan):

```
User Input
    |
    v
  +-----+     +--------+     +-------+
  | Msg | --> | Update | --> | Model |
  +-----+     +--------+     +-------+
                              |
                              v
                            +------+
                            | View |
                            +------+
                              |
                              v
                   +-----------------------+
                   | Widget (immutable IR) |
                   +-----------------------+
                              |
                              v
                           +------+
                           | Diff |
                           +------+
                              |
                              v
                   +----------------------+
                   | ViewNode (LVGL objs) |
                   +----------------------+
```

From a compiler perspective, this diagram is a pipeline.

- `view()` is a pure function that constructs an immutable data structure.
- `diff()` is deterministic and can be O(N).
- `reconcile()` is a sequence of concrete LVGL API calls.

When these pieces are written in typed Python, `mypyc-micropython` can compile them into direct C calls and C loops.

## 1.2 Widget trees as an intermediate representation

A `Widget` tree is a virtual UI description. It is not an LVGL object. It is closer to an IR.

That matters because an IR has two jobs:

1. Be easy to build (from Python code).
2. Be easy to transform (diff and reconciliation).

In this framework, the IR is deliberately small:

- `WidgetKey`: what kind of widget this is (label, button, slider, container, ...).
- `ScalarAttr`: key/value pairs for properties (text, width, bg color, value, ...).
- `children`: ordered child widgets.
- `event_handlers`: event bindings that produce messages.

Think of the tree like this:

```
Screen
  VStack
    Label("Counter Demo")
    Label("Count: 3")
    HStack
      Button("-")
      Button("Reset")
      Button("+")
    Slider(...)
```

This structure is simple enough that we can build it every tick if needed, then let the diff decide what actually changes in LVGL.

## 1.3 Immutable trees and predictable memory

On a desktop UI framework, you can hide a lot of complexity behind hash maps and dynamic allocations.
On a microcontroller, you pay for that with fragmentation and nondeterministic pauses.

The framework plan makes two choices that are specifically about embedded constraints:

1. `Widget` is an immutable dataclass (`frozen=True`).
2. Attributes and children are stored as tuples.

Immutability gives you:

- A safe "previous value" to diff against.
- No aliasing bugs where two nodes accidentally share a mutable list.
- Better compiler optimization opportunities, since frozen dataclasses often behave like plain structs.

Tuples give you:

- Compact storage.
- Stable iteration without allocating iterators.
- A clean bridge to C loops (indexing and length are explicit).

The key is that immutability moves the mutation boundary.

- The virtual widget tree is immutable and cheap to diff.
- The real LVGL object tree is mutable and expensive to rebuild.
- Reconciliation mutates LVGL objects, but in a controlled, linear way.

## 1.4 O(N) diffing: positional children, merge-style attributes

Diffing is where most declarative UIs either become fast or become "fast in theory".

This framework intentionally does not implement a general-purpose keyed diff for children.
Instead, it targets an embedded-friendly rule:

- Children are diffed positionally.
- Attributes are diffed with a two-pointer merge over sorted keys.

Why positional child diffing?

- It is O(N) with a tiny constant.
- It does not allocate hash maps.
- It fits how embedded UIs are usually structured, a small fixed layout where children rarely reorder.

Why sorted attribute tuples?

- Each widget stores scalar attributes as `tuple[ScalarAttr, ...]` sorted by `AttrKey`.
- A diff between two sorted lists can be done with the same merge logic as merging sorted arrays.
- That becomes a tight loop in C.

### Attribute diffing as a merge

If attributes are sorted, the diff becomes:

```
i = 0  (prev attrs)
j = 0  (next attrs)

while i < len(prev) or j < len(next):
  if prev[i].key < next[j].key: removed
  if prev[i].key > next[j].key: added
  if keys equal: updated if value differs
```

This is exactly the pattern you want to compile to C.

## 1.5 Why this maps cleanly to C

There is a second, less obvious reason MVU maps well to compiled C.

In a typical Python UI, event handlers close over a lot of state, then mutate objects directly.
That style needs dynamic dispatch, runtime attribute lookups, and often reflection.

MVU moves work into a small number of predictable functions:

- `update()` becomes a compiled switch-like function.
- `view()` becomes a compiled constructor for a data tree.
- `diff()` becomes a few tight loops over tuples.
- `apply_fn()` becomes direct LVGL API calls.

So the compiler ends up emitting code that looks like embedded code should look: straight-line calls, predictable loops, and bounded allocations.

---

# Part 2: C Background

This framework is written in typed Python, but the mental model should be "a set of C structs and functions".
This section gives just enough C and LVGL background to make Part 3 feel concrete.

## 2.1 LVGL object model: `lv_obj_t` and creation APIs

LVGL is an object-based C library.

- Every widget instance is an `lv_obj_t *`.
- Widgets are created by functions like `lv_label_create(parent)`.
- Many properties are set by dedicated functions (`lv_label_set_text`, `lv_slider_set_value`, ...).
- Styling often goes through `lv_obj_set_style_*` functions.

Even if you call LVGL from MicroPython, the underlying model is the same.

Here is a simplified view of what the C side looks like:

```c
lv_obj_t *screen = lv_obj_create(NULL);
lv_obj_t *label = lv_label_create(screen);
lv_label_set_text(label, "Hello");
```

Two consequences for our framework:

1. Recreating objects is expensive, you lose state and you risk memory churn.
2. Updating properties is cheap, if you can identify what changed.

That is why we diff and reconcile.

## 2.2 Function pointers for callbacks and dispatch

Event-driven C APIs usually rely on function pointers.

In C, a callback type might look like:

```c
typedef void (*dispatch_fn_t)(mp_obj_t msg);

typedef void (*lv_event_cb_t)(lv_event_t *e);
```

The interesting part is not just "C has function pointers".
It is that a function pointer forces you to decide, at compile time, what information you can reach when an event fires.

In MVU, that information is intentionally small:

- the message to dispatch, and
- the app instance that owns the queue.

Everything else is derived later, when `update()` runs.

## 2.3 Tagged unions for attribute values and widget kinds

In Python, `ScalarAttr.value` is an `object`. That is convenient for authoring.

In C, you usually represent "one of several types" with a tagged union:

```c
typedef enum {
  ATTR_INT,
  ATTR_BOOL,
  ATTR_COLOR,
  ATTR_STR,
} attr_kind_t;

typedef struct {
  uint16_t key;         // AttrKey
  attr_kind_t kind;
  union {
    int32_t i;
    uint8_t b;
    uint32_t color;
    const char *s;
  } v;
} scalar_attr_t;
```

The same pattern applies to widget kinds:

```c
typedef enum {
  W_SCREEN,
  W_CONTAINER,
  W_LABEL,
  W_BUTTON,
  W_SLIDER,
} widget_key_t;
```

Why bring this up if our implementation is in Python?

Because the whole design is shaped so it can be lowered into these representations later.
You want to avoid Python features that do not have a clean C shape.

## 2.4 Struct composition for hierarchies

Our runtime has two trees:

- the immutable `Widget` tree (virtual), and
- the mutable `ViewNode` tree (real LVGL objects).

In C, tree nodes are usually represented as structs with pointers to children.
There are many options, but the idea is stable:

```c
typedef struct view_node {
  lv_obj_t *obj;
  widget_key_t key;
  struct view_node **children;
  uint16_t child_count;
} view_node_t;
```

The important embedded detail is allocation strategy.

- You want child arrays to be bounded or pooled.
- You want cleanup to be explicit and predictable.

The plan keeps the diff algorithm positional so you do not need complex child indexing structures.

## 2.5 MicroPython `mp_obj_t`, boxing, and unboxing

`mypyc-micropython` emits C that talks to MicroPython.
That means most values at the boundary are `mp_obj_t`.

Very roughly:

- Small ints can be stored directly (tagged small-int).
- Everything else is a pointer to a heap object.

Common operations:

```c
mp_int_t n = mp_obj_get_int(obj);
mp_obj_t obj2 = mp_obj_new_int(n + 1);
```

For this framework, `mp_obj_t` shows up in two places:

1. Event callbacks need to call back into Python-level dispatch.
2. The widget DSL is authored in Python, then compiled, so intermediate values may still be `mp_obj_t` during execution.

The design goal is to keep "dynamic" values near the edges.
Most of the framework core can compile to straight C control flow.

---

# Part 3: Implementation

This section describes the actual framework design from `docs/lvgl-mvu-framework-plan.md`.

The high-level idea is:

- The app owns a message queue.
- `update()` returns a new model plus commands.
- `view()` returns a widget tree.
- The reconciler updates a persistent `ViewNode` tree of LVGL objects.
- Async effects schedule tasks and feed messages back into the same queue.

## 3.1 Core data types: `Widget`, `ScalarAttr`, `WidgetKey`

The core "virtual UI" types are deliberately tiny.

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class WidgetKey(IntEnum):
    SCREEN = 0
    CONTAINER = 1
    LABEL = 2
    BUTTON = 3
    SLIDER = 4
    # ... and so on


@dataclass(frozen=True)
class ScalarAttr:
    key: int
    value: object


@dataclass(frozen=True)
class Widget:
    key: WidgetKey
    user_key: str | None
    scalar_attrs: tuple[ScalarAttr, ...]
    children: tuple[Widget, ...]
    event_handlers: tuple[tuple[int, object], ...]  # (event_type, msg or ("value", msg_fn))
```

Two details are easy to gloss over, but they are what make the rest work:

1. `Widget` is frozen.
2. `scalar_attrs` is a tuple sorted by key.

Those two decisions are why we can diff without allocating maps.

### Widget tree structure example

The DSL builds a `Widget` tree, but it is still a plain data structure.
You can imagine a counter screen like this (simplified):

```python
Widget(
    key=WidgetKey.SCREEN,
    user_key=None,
    scalar_attrs=(ScalarAttr(AttrKey.BG_COLOR, 0x1A1A2E),),
    children=(
        Widget(
            key=WidgetKey.LABEL,
            user_key=None,
            scalar_attrs=(
                ScalarAttr(AttrKey.TEXT, "Count: 0"),
                ScalarAttr(AttrKey.TEXT_COLOR, 0x00FF00),
            ),
            children=(),
            event_handlers=(),
        ),
    ),
    event_handlers=(),
)
```

This is the "declarative UI".
It has no pointers to LVGL objects, and it performs no LVGL calls.

## 3.2 Attribute registry: `AttrKey` and `AttrDef.apply_fn`

An attribute is identified by an integer key.
The plan uses an `AttrKey` enum with a carefully chosen ordering.

- Common layout keys live in compact ranges.
- Styling keys are grouped.
- Widget-specific keys come later.

That ordering is not just for readability.
It makes diffs stable and makes attribute lists naturally sorted.

Attributes are applied through a registry:

```python
from dataclasses import dataclass
from typing import Callable


@dataclass
class AttrDef:
    key: int
    name: str
    default: object
    apply_fn: Callable[[object, object], None]
    compare_fn: Callable[[object, object], bool] | None = None


_ATTR_REGISTRY: dict[int, AttrDef] = {}


def register_attr(attr_def: AttrDef) -> AttrDef:
    _ATTR_REGISTRY[attr_def.key] = attr_def
    return attr_def


def get_attr_def(key: int) -> AttrDef:
    return _ATTR_REGISTRY[key]
```

This registry is the bridge between "data" and "effects":

- `Widget` stores attributes as plain values.
- `apply_fn` turns an attribute into an LVGL call.

Example: applying label text might look like:

```python
def apply_text(lv_obj: object, value: object) -> None:
    import lvgl as lv
    lv.lv_label_set_text(lv_obj, value)  # value is a Python string


register_attr(AttrDef(
    key=AttrKey.TEXT,
    name="text",
    default="",
    apply_fn=apply_text,
))
```

When this code is compiled, that `apply_text()` function becomes a direct call into the MicroPython LVGL bindings.

## 3.3 Fluent DSL: `WidgetBuilder` and widget constructors

The DSL is the authoring layer.
It is intentionally a small fluent builder, not a magical macro system.

Key properties:

- builder methods return `self` (chainable),
- `__call__` finalizes the widget and attaches children,
- attributes are sorted at build time, not during diff.

From the plan:

```python
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

Msg = TypeVar("Msg")


@dataclass
class WidgetBuilder(Generic[Msg]):
    _key: WidgetKey
    _user_key: str | None = None
    _attrs: list[ScalarAttr] = field(default_factory=list)
    _children: list[Widget] = field(default_factory=list)
    _handlers: list[tuple[int, object]] = field(default_factory=list)

    def key(self, user_key: str) -> "WidgetBuilder[Msg]":
        self._user_key = user_key
        return self

    def attr(self, attr_key: int, value: object) -> "WidgetBuilder[Msg]":
        self._attrs.append(ScalarAttr(attr_key, value))
        return self

    def on(self, event: int, msg: Msg) -> "WidgetBuilder[Msg]":
        self._handlers.append((event, msg))
        return self

    def on_value(self, event: int, msg_fn: Callable[[int], Msg]) -> "WidgetBuilder[Msg]":
        self._handlers.append((event, ("value", msg_fn)))
        return self

    def __call__(self, *children: Widget | "WidgetBuilder") -> Widget:
        child_widgets: list[Widget] = []
        for child in children:
            if isinstance(child, WidgetBuilder):
                child_widgets.append(child.build())
            else:
                child_widgets.append(child)

        sorted_attrs = tuple(sorted(self._attrs, key=lambda a: a.key))
        return Widget(
            key=self._key,
            user_key=self._user_key,
            scalar_attrs=sorted_attrs,
            children=tuple(child_widgets),
            event_handlers=tuple(self._handlers),
        )

    def build(self) -> Widget:
        return self()
```

In practice you do not instantiate `WidgetBuilder` directly.
You use constructors like `Label(...)`, `Button(...)`, `VStack(...)` that return a preconfigured builder.

This is what authors write:

```python
Screen().bg_color(0x1A1A2E)(
    VStack(spacing=20)(
        Label("Counter Demo").font_size(28),
        Button("+", Msg.INCREMENT).size(80, 50),
    )
)
```

## 3.4 Diffing engine with a concrete example

Diffing is the "compiler pass" between two widget trees.
It finds the minimal set of changes we need to apply to LVGL.

The plan defines these data types:

```python
from dataclasses import dataclass
from typing import Literal


@dataclass
class AttrChange:
    kind: Literal["added", "removed", "updated"]
    key: int
    old_value: object | None
    new_value: object | None


@dataclass
class ChildChange:
    kind: Literal["insert", "remove", "update", "replace"]
    index: int
    widget: Widget | None
    diff: "WidgetDiff | None"


@dataclass
class WidgetDiff:
    scalar_changes: tuple[AttrChange, ...]
    child_changes: tuple[ChildChange, ...]
```

### The two-pointer scalar diff

Scalar attributes are sorted by key.
This lets `diff_scalars(prev, next)` run in O(N) time without any extra allocations.

Here is a concrete, small example.

Assume these sorted attribute lists for a label:

```
prev:
  (TEXT="Count: 0", TEXT_COLOR=0x00FF00)

next:
  (TEXT="Count: 1", TEXT_COLOR=0x00FF00)
```

The merge walk looks like:

```
prev[i]=TEXT        next[j]=TEXT        -> same key, value changed -> updated(TEXT)
prev[i]=TEXT_COLOR  next[j]=TEXT_COLOR  -> same key, value same    -> no change
```

No maps, no lookups. Just comparisons and increments.

### Positional child diff

Children are diffed by index.

The rule is:

- If both sides have a child at index `i`, we attempt to reuse.
- If reuse is possible, we diff recursively.
- If reuse is not possible, we replace.
- If one side has a child and the other does not, we insert or remove.

Reuse is controlled by `WidgetKey` and optional `user_key`:

```python
def can_reuse(prev: Widget, next: Widget) -> bool:
    if prev.key != next.key:
        return False
    if prev.user_key is not None or next.user_key is not None:
        return prev.user_key == next.user_key
    return True
```

The `user_key` is the escape hatch when you need stability.
If you insert a new child at the top of a list, positional diffing would normally shift everything.
With explicit keys, you can keep a particular subtree pinned to a specific LVGL object.

### Before/after diff walkthrough

Let us diff a slightly bigger view change.

Before:

```
Screen
  VStack
    Label("Count: 0")
    Button("+")
```

After (count increments, plus we show a warning label when count >= 10):

```
Screen
  VStack
    Label("Count: 10")
    Label("High value!")
    Button("+")
```

With positional children, the diff at `VStack` children becomes:

1. index 0: `Label` reused, scalar diff updates TEXT.
2. index 1: `Button` cannot be reused with `Label`, so this is a `replace`.
3. index 2: new `Button` inserted (since old button was replaced at index 1).

That sounds bad until you notice the intended usage pattern.

- In embedded UIs, you typically do not insert new children in the middle.
- Conditional UI usually reserves a slot, or uses a container whose child list is stable.
- If you do need stable reordering, you use `user_key` on subtrees you want to reuse.

Here is the same example rewritten to keep the button stable by wrapping the conditional content in a container:

```
Screen
  VStack
    Label("Count: 10")
    Container(key="warning")
      Label("High value!")
    Button("+")
```

Now the `Button` stays at a fixed index.
The conditional content happens inside a keyed container.

This is the embedded mindset: you trade some authoring discipline for predictable update costs.

## 3.5 Reconciliation: `ViewNode` bridges Widgets to LVGL

`Widget` is immutable and cheap.
`lv_obj_t *` objects are expensive and stateful.

`ViewNode` is the persistent bridge.

From the plan:

```python
from dataclasses import dataclass, field


@dataclass
class ViewNode:
    lv_obj: object
    widget: Widget
    children: list["ViewNode"] = field(default_factory=list)
    handlers: dict[int, object] = field(default_factory=dict)

    def apply_diff(self, diff: WidgetDiff) -> None:
        for change in diff.scalar_changes:
            attr_def = get_attr_def(change.key)
            if change.kind == "removed":
                attr_def.apply_fn(self.lv_obj, attr_def.default)
            else:
                attr_def.apply_fn(self.lv_obj, change.new_value)

    def dispose(self) -> None:
        import lvgl as lv
        for child in self.children:
            child.dispose()
        self.children.clear()
        self.handlers.clear()
        lv.lv_obj_delete(self.lv_obj)
```

The reconciler orchestrates the full update.

- If a node cannot be reused, dispose it and create a new LVGL object.
- If it can be reused, apply scalar diffs and reconcile children.
- Event handlers are registered or updated based on the widget description.

The framework plan uses factories per widget type:

```python
class Reconciler:
    def __init__(self) -> None:
        self._factories: dict[WidgetKey, callable] = {}

    def register_factory(self, key: WidgetKey, factory: callable) -> None:
        self._factories[key] = factory
```

### Mapping Widgets to LVGL C calls

Even if you write factories in Python, this is what they represent:

```c
static lv_obj_t *create_label(lv_obj_t *parent) {
  return lv_label_create(parent);
}

static void apply_text(lv_obj_t *obj, const char *s) {
  lv_label_set_text(obj, s);
}
```

Reconciliation is "create or reuse object, then apply functions".
That is why attribute application is centralized.

### Event handlers and lifetime

LVGL stores callbacks on objects.
MicroPython stores Python-callable objects.

If you install an event callback and then drop the last reference to the handler, the GC can collect it.
So `ViewNode.handlers` exists for a very practical reason: keep event handler objects alive as long as the LVGL object needs them.

In a compiled module, the same principle applies.
If you create wrapper objects for callbacks, you must store them somewhere reachable.

## 3.6 MVU runtime loop: `Program`, `Cmd`, `Sub`, `App`

The runtime is the glue.

The plan defines:

- `Program`: init, update, view, optional subscribe.
- `Cmd`: side effects that can dispatch messages.
- `Sub`: subscriptions (timers, streams).
- `App`: owns model, message queue, root `ViewNode`, reconciler.

The key runtime method is `tick()`.
In the sync version, it is a regular function:

```python
def tick(self) -> None:
    changed = False
    while self.msg_queue:
        msg = self.msg_queue.pop(0)
        self.model, cmd = self.program.update(msg, self.model)
        self._execute_cmd(cmd)
        changed = True

    if changed or self.root_node is None:
        widget = self.program.view(self.model)
        self.root_node = self.reconciler.reconcile(self.root_node, widget)
        if changed:
            self._setup_subscriptions()
```

This is the other big reason MVU compiles well.

- The hot loop is just a while loop draining a queue.
- Update and view calls are direct.
- Reconciliation is deterministic.

Subscriptions are treated as resources.
When the model changes, you can re-subscribe based on the new state.
Unsubscribes are stored and called during disposal.

## 3.7 Async integration: `AsyncCmd`, `AsyncApp`, background tasks

Embedded UIs are often IO bound.

- fetch configuration from WiFi,
- poll sensors,
- read from BLE,
- wait for a file read.

If you block the UI thread, LVGL stops animating and input feels broken.

The framework plan adds async support with these ideas:

- `AsyncCmd`: commands whose effects are async coroutines.
- `AsyncApp`: an app runner that schedules async effects with `asyncio.create_task`.
- `TaskManager`: a small registry for background tasks, cancellation, and completion messages.

The key behavior is: async effects do not block `tick()`.

In the plan, scheduling is explicit:

```python
def _schedule_cmd(self, cmd: Cmd[Msg] | AsyncCmd[Msg]) -> None:
    if isinstance(cmd, AsyncCmd):
        for effect in cmd.effects:
            task = asyncio.create_task(effect(self.dispatch))
            self._pending_tasks.append(task)
    else:
        for effect in cmd.effects:
            effect(self.dispatch)
```

The async event loop calls LVGL's timer handler regularly:

```python
async def run(self, tick_ms: int = 10) -> None:
    import lvgl as lv
    self._running = True
    while self._running:
        await self.tick()
        lv.timer_handler()
        await asyncio.sleep_ms(tick_ms)
```

So you get a consistent rhythm:

- UI processing happens every tick.
- async effects run in the background.
- when they finish, they dispatch messages.

### Async message flow

One useful way to visualize async is to see that it is still MVU.
The only change is the time at which messages arrive.

```
Msg.FETCH_DATA
  -> update() returns (Model(loading=True), AsyncCmd.http_get(...))
  -> UI re-renders, shows Spinner
  -> HTTP task runs in background
  -> task dispatches (Msg.DATA_RECEIVED, data)
  -> update() returns (Model(loading=False, data=data), Cmd.none())
  -> UI re-renders, shows data
```

Notice what does not happen:

- `view()` never awaits.
- LVGL timer handling never pauses for network IO.
- UI stays responsive because the main loop keeps pumping.

## 3.8 Counter app walkthrough

The plan includes a complete counter app.
This example is useful because it contains:

- immutable model updates,
- button events that dispatch messages,
- a slider whose event handler extracts a value,
- a `view()` that builds a widget tree.

Here is the counter app (adapted from the plan, with imports made consistent):

```python
"""Counter application demonstrating MVU pattern."""

from dataclasses import dataclass
from enum import IntEnum

import lvgl as lv
import time

from lvgl_mvu import App, Program, Cmd, Widget
from lvgl_mvu.attrs import LvAlign
from lvgl_mvu.dsl import Screen, VStack, HStack, Label, Button, Slider


@dataclass(frozen=True)
class Model:
    count: int
    step: int


class Msg(IntEnum):
    INCREMENT = 1
    DECREMENT = 2
    RESET = 3
    SET_STEP = 4  # payload: int


def init() -> tuple[Model, Cmd]:
    return Model(count=0, step=1), Cmd.none()


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


def view(model: Model) -> Widget:
    return Screen().bg_color(0x1A1A2E)(
        VStack(spacing=20).align(LvAlign.CENTER)(
            Label("Counter Demo")
                .text_color(0xFFFFFF)
                .font_size(28),

            Label(f"Count: {model.count}")
                .text_color(0x00FF00 if model.count >= 0 else 0xFF0000)
                .font_size(48),

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

            Label(f"Step: {model.step}").text_color(0xAAAAAA),
            Slider(1, 10, model.step, lambda v: (Msg.SET_STEP, v)).width(200),
        )
    )


def main() -> None:
    # LVGL display init is platform-specific.
    # Once lv.init() and display driver are ready, run the MVU app.
    program = Program(init=init, update=update, view=view)
    app = App(program)
    while True:
        app.tick()
        lv.timer_handler()
        time.sleep_ms(10)
```

### End-to-end data flow for a button click

Let us follow a single button press.

1. LVGL fires a button click event.
2. The `ViewNode` event callback dispatches `Msg.INCREMENT`.
3. `App.tick()` drains the queue and calls `update(Msg.INCREMENT, model)`.
4. `update()` returns a new `Model` with incremented `count`.
5. `view(new_model)` produces a new `Widget` tree.
6. `diff(old_widget, new_widget)` finds the label TEXT change.
7. The reconciler applies that diff by calling `lv_label_set_text` on the existing LVGL label object.

That is the whole story.

The UI changes because the model changed.
The LVGL calls happen because a diff decided they were needed.

### What compiles to C

Even though the authoring language is Python, the execution can be mostly C-like.

- `update()` becomes a chain of comparisons or a switch.
- `diff_scalars()` becomes a tight loop with two indices.
- attribute application functions become direct LVGL API calls.

The only part that inherently stays dynamic is anything that depends on Python objects that LVGL bindings require at runtime (strings, user data objects, some callback wrappers).
The framework keeps those dynamic bits localized.

## 3.9 Widget catalog summary (P0 to P3)

The plan organizes widgets into priorities so the framework can become usable early.
Here is a condensed version of the catalog.

### Priority 0 (Essential)

| Widget | LVGL API | DSL | Typical attributes |
|--------|----------|-----|--------------------|
| Screen | `lv_obj_create(NULL)` | `Screen()` | bg_color, padding |
| Container | `lv_obj_create(parent)` | `Container()` | size, pos, bg_color, padding, flex |
| Label | `lv_label_create` | `Label(text)` | text, text_color, font |
| Button | `lv_button_create` | `Button(text, on_click)` | text, size, bg_color |

### Priority 1 (Interactive)

| Widget | LVGL API | DSL | Typical attributes |
|--------|----------|-----|--------------------|
| Slider | `lv_slider_create` | `Slider(min, max, value, on_change)` | range, value |
| Bar | `lv_bar_create` | `Bar(min, max, value)` | range, value |
| Arc | `lv_arc_create` | `Arc(min, max, value, on_change)` | range, value, angles |
| Switch | `lv_switch_create` | `Switch(checked, on_change)` | checked |
| Checkbox | `lv_checkbox_create` | `Checkbox(text, checked, on_change)` | text, checked |

### Priority 2 (Forms)

| Widget | LVGL API | DSL | Typical attributes |
|--------|----------|-----|--------------------|
| Image | `lv_image_create` | `Image(src)` | src, size, zoom |
| TextArea | `lv_textarea_create` | `TextArea(text, placeholder, on_change)` | text, placeholder |
| Dropdown | `lv_dropdown_create` | `Dropdown(options, selected, on_change)` | options, selected |
| Roller | `lv_roller_create` | `Roller(options, selected, on_change)` | options, selected, visible |
| Table | `lv_table_create` | `Table(rows, cols, data)` | rows, cols, cell_value |
| List | `lv_list_create` | `List(items)` | items |

### Priority 3 (Advanced)

This tier is the long tail, but it matters for real apps.
The plan includes Chart, Calendar, Keyboard, Menu, TabView, MessageBox, Spinner, LED, Line, Canvas, Window, TileView, Spangroup, Spinbox, Scale, ButtonMatrix, ArcLabel, AnimImg.

The point of the priority split is practical:

- P0 plus P1 is enough for many products.
- P2 makes the framework viable for settings screens and forms.
- P3 turns it into a full dashboard UI toolkit.

---

# Closing

This framework treats declarative UI as a compilation problem.

- The widget tree is a tiny IR.
- Sorting attributes up front enables O(N) diffing without maps.
- Positional child diffing keeps updates predictable.
- ViewNode reconciliation turns diffs into direct LVGL calls.
- Async commands keep IO from freezing the UI, while preserving the same message flow.

The result is a UI architecture that still feels like Python, but can compile down to something that behaves like hand-written embedded C.
