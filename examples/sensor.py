from dataclasses import dataclass


@dataclass
class SensorReading:
    sensor_id: int
    temperature: float
    humidity: float
    valid: bool = True


class SensorBuffer:
    count: int
    sum_temp: float
    sum_humidity: float

    def __init__(self) -> None:
        self.count = 0
        self.sum_temp = 0.0
        self.sum_humidity = 0.0

    def add_reading(self, temp: float, humidity: float) -> None:
        self.count += 1
        self.sum_temp += temp
        self.sum_humidity += humidity

    def avg_temperature(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_temp / self.count

    def avg_humidity(self) -> float:
        if self.count == 0:
            return 0.0
        return self.sum_humidity / self.count

    def reset(self) -> None:
        self.count = 0
        self.sum_temp = 0.0
        self.sum_humidity = 0.0
