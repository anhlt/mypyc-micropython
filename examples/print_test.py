def test_print_string() -> None:
    print("Hello from compiled C!")

def test_print_int() -> None:
    print(42)

def test_print_multiple() -> None:
    print("a", "b", "c")

def test_print_calc() -> None:
    x: int = 10
    y: int = 20
    print(x + y)

def greet(name: str) -> None:
    print("Hello,", name)
