"""LVGL UI Framework package.

This package compiles to a single MicroPython C module with namespaced submodules:
    import lvui
    
    # MVU (Model-View-Update) architecture
    lvui.mvu.Model
    lvui.mvu.Msg
    lvui.mvu.update(model, msg)
    lvui.mvu.view(model)
    
    # Screen management
    lvui.screens.create_screen()
    lvui.screens.create_label(scr, "text")
    lvui.screens.create_button(scr, "Click", 120, 40)
    
    # Navigation
    lvui.nav.ScreenManager
    lvui.nav.navigate_to(screen)

Note: Low-level LVGL bindings are in the `lvgl` module (lv_* functions).
"""
