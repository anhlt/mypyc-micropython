import gc

ITERATIONS = 20
TOLERANCE_BYTES = 10000


def _skip(reason):
    print("SKIP:", reason)


def _has_lvgl():
    try:
        import lvgl  # type: ignore
    except Exception:
        return False
    return hasattr(lvgl, "init_display")


def run(iterations=ITERATIONS, tolerance_bytes=TOLERANCE_BYTES):
    if not _has_lvgl():
        _skip("LVGL firmware not available")
        return True

    import lvgl  # type: ignore
    from ui_screen_tree import ScreenManager, ScreenNode
    from ui_screens import build_home_screen, build_settings_screen

    lvgl.init_display()

    root = ScreenNode(
        "home",
        build_home_screen,
        children=[ScreenNode("settings", build_settings_screen)],
    )
    manager = ScreenManager(root)
    manager.start()

    gc.collect()
    baseline_free = gc.mem_free()
    min_free = baseline_free
    print("mem baseline:", baseline_free)

    for i in range(iterations):
        manager.goto("settings")
        manager.back()

        lvgl.timer_handler()
        gc.collect()
        current_free = gc.mem_free()
        if current_free < min_free:
            min_free = current_free

        print("iter", i + 1, "mem_free", current_free)

    drop = baseline_free - min_free
    print("mem min:", min_free)
    print("mem drop:", drop)
    print("mem tolerance:", tolerance_bytes)

    if drop > tolerance_bytes:
        print("FAIL: memory drop exceeds tolerance")
        return False

    print("PASS: LVGL nav loop within memory tolerance")
    return True


if __name__ == "__main__":
    ok = run()
    if not ok:
        raise SystemExit(1)
