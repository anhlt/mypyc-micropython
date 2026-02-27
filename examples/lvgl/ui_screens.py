from ui_widgets import Container, Label, Screen


def build_home_screen():
    screen = Screen(
        widgets=[
            Container(
                children=[
                    Label(text="Home"),
                    Label(text="Use ScreenManager.goto('settings')"),
                ]
            )
        ]
    )
    return screen.build_root()


def build_settings_screen():
    screen = Screen(
        widgets=[
            Container(
                children=[
                    Label(text="Settings"),
                    Label(text="Use ScreenManager.back() to return"),
                ]
            )
        ]
    )
    return screen.build_root()


def build_about_screen():
    screen = Screen(
        widgets=[
            Container(
                children=[
                    Label(text="About"),
                    Label(text="Screen tree demo"),
                ]
            )
        ]
    )
    return screen.build_root()
