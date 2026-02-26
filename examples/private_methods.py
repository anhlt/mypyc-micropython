"""Example demonstrating private method optimization and @final class.

Exercises:
- Private methods (__method) with no MP wrapper (native-only)
- @final class with all methods devirtualized (no vtable)
- Final[int] attribute constant folding
- Benchmark: public vs private method call overhead
"""

from typing import Final, final


# -- Class with private helper method (Tier 1) --------------------------------
# __compute is private: emitted as native C only, no MP wrapper, no vtable entry.
# Called internally via direct C function call.
class Calculator:
    value: int

    def __init__(self, v: int) -> None:
        self.value = v

    def __compute(self, x: int) -> int:
        return self.value + x * x

    def compute(self, x: int) -> int:
        return self.__compute(x)


# -- @final class (Tier 2) ----------------------------------------------------
# All methods devirtualized: no vtable struct, direct calls everywhere.
@final
class FastCounter:
    count: int
    step: int

    def __init__(self, step: int) -> None:
        self.count = 0
        self.step = step

    def increment(self) -> int:
        self.count += self.step
        return self.count

    def reset(self) -> None:
        self.count = 0

    def get(self) -> int:
        return self.count


# -- Final attributes (Tier 3) ------------------------------------------------
# MAX_ITERS is constant-folded: self.MAX_ITERS becomes literal 1000 in C.
class Config:
    MAX_ITERS: Final[int] = 1000
    SCALE: Final[int] = 2
    value: int

    def __init__(self, v: int) -> None:
        self.value = v

    def scaled_value(self) -> int:
        return self.value * self.SCALE

    def is_within_limit(self, n: int) -> bool:
        return n < self.MAX_ITERS


# -- Benchmark: public vs private method CALL OVERHEAD -----------------------
# public_add and __private_add are identical tiny methods.
# run_public calls public_add N times (each call goes through MP wrapper).
# run_private calls __private_add N times (each call is a direct C call).
# The loop measures per-call dispatch overhead, not loop body cost.
class Benchmark:
    data: int

    def __init__(self, d: int) -> None:
        self.data = d

    def public_add(self, x: int) -> int:
        return self.data + x

    def __private_add(self, x: int) -> int:
        return self.data + x

    def run_public(self, n: int) -> int:
        total: int = 0
        for i in range(n):
            total += self.public_add(i)
        return total

    def run_private(self, n: int) -> int:
        total: int = 0
        for i in range(n):
            total += self.__private_add(i)
        return total
