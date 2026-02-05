class Counter:
    value: int
    step: int

    def __init__(self, start: int, step: int) -> None:
        self.value = start
        self.step = step

    def increment(self) -> int:
        self.value += self.step
        return self.value

    def decrement(self) -> int:
        self.value -= self.step
        return self.value

    def reset(self) -> None:
        self.value = 0

    def get(self) -> int:
        return self.value


class BoundedCounter(Counter):
    min_val: int
    max_val: int

    def __init__(self, start: int, step: int, min_val: int, max_val: int) -> None:
        self.value = start
        self.step = step
        self.min_val = min_val
        self.max_val = max_val

    def increment(self) -> int:
        new_val: int = self.value + self.step
        if new_val <= self.max_val:
            self.value = new_val
        return self.value

    def decrement(self) -> int:
        new_val: int = self.value - self.step
        if new_val >= self.min_val:
            self.value = new_val
        return self.value
