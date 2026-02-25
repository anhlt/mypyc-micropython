"""Unified class example: a single hierarchy exercising all class features.

One inheritance chain covers: @dataclass, manual __init__, typed fields
(int/float/bool/str/list/dict), single inheritance with vtable override,
3-level super() calls, @property (getter+setter), @staticmethod,
@classmethod, augmented assignment, container fields, chained attribute
access, and functions taking class parameters.
"""

from __future__ import annotations

from dataclasses import dataclass


# -- Helper: small @dataclass for chained attribute access ------------------
@dataclass
class Location:
    x: int
    y: int


# -- Base class: Entity -----------------------------------------------------
# Features: manual __init__, str/int/list fields, @property (read-only),
#           @staticmethod, container field (list), iteration
class Entity:
    name: str
    _id: int
    tags: list[int]

    def __init__(self, name: str, eid: int) -> None:
        self.name = name
        self._id = eid
        self.tags = []

    @property
    def id(self) -> int:
        return self._id

    @staticmethod
    def validate_name(name: str) -> bool:
        return len(name) > 0

    def add_tag(self, tag: int) -> None:
        self.tags.append(tag)

    def tag_count(self) -> int:
        return len(self.tags)

    def has_tag(self, tag: int) -> bool:
        n: int = len(self.tags)
        for i in range(n):
            if self.tags[i] == tag:
                return True
        return False

    def describe(self) -> str:
        return self.name


# -- Child class: Sensor(Entity) -------------------------------------------
# Features: super().__init__(), float field, @property (getter+setter),
#           @classmethod, method override, chained attr (self.location.x),
#           augmented assignment, dict field
class Sensor(Entity):
    _value: float
    location: Location
    readings: dict[int, float]

    def __init__(self, name: str, eid: int, loc: Location) -> None:
        super().__init__(name, eid)
        self._value = 0.0
        self.location = loc
        self.readings = {}

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        self._value = v

    @classmethod
    def create(cls, name: str) -> object:
        """Return the class itself (constructor call not yet supported)."""
        return cls

    def record(self, ts: int, val: float) -> None:
        self.readings[ts] = val
        self._value = val

    def reading_count(self) -> int:
        return len(self.readings)

    def get_reading(self, ts: int) -> float:
        return self.readings[ts]

    def get_location_x(self) -> int:
        return self.location.x

    def get_location_y(self) -> int:
        return self.location.y

    def describe(self) -> str:
        base: str = super().describe()
        return base


# -- Grandchild class: SmartSensor(Sensor) ---------------------------------
# Features: 3-level inheritance, super().__init__(), super().describe(),
#           augmented assignment (+=), cross-level field access, bool field
class SmartSensor(Sensor):
    threshold: float
    alert_count: int
    active: bool

    def __init__(self, name: str, eid: int, loc: Location, threshold: float) -> None:
        super().__init__(name, eid, loc)
        self.threshold = threshold
        self.alert_count = 0
        self.active = True

    def check_value(self) -> bool:
        if self._value > self.threshold:
            self.alert_count += 1
            return True
        return False

    def get_alert_count(self) -> int:
        return self.alert_count

    def describe(self) -> str:
        base: str = super().describe()
        return base

    def get_total_score(self) -> int:
        """Cross-level field access: grandchild reads base _id + own alert_count."""
        return self._id + self.alert_count


# -- Free functions taking class parameters ---------------------------------
def distance_between(a: Location, b: Location) -> int:
    dx: int = b.x - a.x
    dy: int = b.y - a.y
    return dx * dx + dy * dy


def sensor_summary(s: Sensor) -> int:
    """Access fields across inheritance: id (Entity) + reading_count (Sensor)."""
    rc: int = s.reading_count()
    return s._id + rc
