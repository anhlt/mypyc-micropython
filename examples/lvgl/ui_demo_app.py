from __future__ import annotations

from ui_screen_tree import ScreenManager, ScreenNode
from ui_screens import build_about_screen, build_home_screen, build_settings_screen


def build_demo_tree() -> ScreenNode:
    return ScreenNode(
        "home",
        build_home_screen,
        children=[
            ScreenNode(
                "settings",
                build_settings_screen,
                children=[
                    ScreenNode("about", build_about_screen),
                ],
            ),
        ],
    )


def run_demo() -> ScreenManager:
    manager = ScreenManager(build_demo_tree())
    manager.start()
    manager.goto("settings")
    manager.goto("about")
    manager.back()
    manager.back()
    return manager


if __name__ == "__main__":
    run_demo()
