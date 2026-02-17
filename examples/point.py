from dataclasses import dataclass


@dataclass
class Point:
    x: int
    y: int

    def distance_squared(self) -> int:
        return self.x * self.x + self.y * self.y

    def add(self, other_x: int, other_y: int) -> int:
        return self.x + other_x + self.y + other_y


@dataclass
class Point3D(Point):
    z: int

    def distance_squared_3d(self) -> int:
        return self.x * self.x + self.y * self.y + self.z * self.z
