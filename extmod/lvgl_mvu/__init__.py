"""LVGL MVU Framework - Fabulous-style Model-View-Update for LVGL widgets.

Compiles to a single MicroPython C module with namespaced submodules::

    import lvgl_mvu

    # Core types
    lvgl_mvu.widget.Widget
    lvgl_mvu.widget.WidgetKey
    lvgl_mvu.attrs.AttrKey
    lvgl_mvu.builders.WidgetBuilder

    # Diffing and reconciliation
    lvgl_mvu.diff.diff_widgets
    lvgl_mvu.viewnode.ViewNode
    lvgl_mvu.reconciler.Reconciler

    # MVU runtime
    lvgl_mvu.program.Program
    lvgl_mvu.program.Cmd
    lvgl_mvu.program.Sub
    lvgl_mvu.app.App

    # P0 Widget DSL (Milestone 5)
    lvgl_mvu.dsl.Screen
    lvgl_mvu.dsl.Container
    lvgl_mvu.dsl.Label
    lvgl_mvu.dsl.Button

    # P1 Widget DSL (Milestone 7)
    lvgl_mvu.dsl.Slider
    lvgl_mvu.dsl.Bar
    lvgl_mvu.dsl.Arc
    lvgl_mvu.dsl.Switch
    lvgl_mvu.dsl.Checkbox

    # Layouts
    lvgl_mvu.layouts.VStack
    lvgl_mvu.layouts.HStack

    # Factories and appliers
    lvgl_mvu.factories.register_p0_factories
    lvgl_mvu.factories.register_p1_factories
    lvgl_mvu.factories.register_all_factories
    lvgl_mvu.appliers.register_p0_appliers
    lvgl_mvu.appliers.register_p1_appliers
    lvgl_mvu.appliers.register_all_appliers

    # Event system (Milestone 6)
    lvgl_mvu.events.LvEvent
    lvgl_mvu.events.EventBinder
    lvgl_mvu.events.EventHandler
    lvgl_mvu.events.setup_events
"""
