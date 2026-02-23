class Animal:
    name: str
    sound: str

    def __init__(self, name: str, sound: str) -> None:
        self.name = name
        self.sound = sound

    def speak(self) -> str:
        return self.sound

    def describe(self) -> str:
        return self.name


class Dog(Animal):
    tricks: int

    def __init__(self, name: str, tricks: int) -> None:
        super().__init__(name, "Woof")
        self.tricks = tricks

    def describe(self) -> str:
        base: str = super().describe()
        return base

    def get_tricks(self) -> int:
        return self.tricks
