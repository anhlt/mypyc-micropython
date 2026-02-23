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


class ShowDog(Dog):
    awards: int

    def __init__(self, name: str, tricks: int, awards: int) -> None:
        super().__init__(name, tricks)
        self.awards = awards

    def describe(self) -> str:
        base: str = super().describe()
        return base

    def get_awards(self) -> int:
        return self.awards

    def get_total_score(self) -> int:
        return self.tricks + self.awards
