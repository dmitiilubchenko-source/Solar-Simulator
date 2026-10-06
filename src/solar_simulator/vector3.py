from __future__ import annotations

from math import hypot, acos, cos, sin, isfinite

class Vector3:
    def __init__(self, x: float, y: float, z: float) -> None:
        if not all(isfinite(value) for value in (x, y, z)):
            raise ValueError("Координаты должны быть конечными числами")
        self.x = x
        self.y = y
        self.z = z

    def add(self, other: "Vector3") -> "Vector3":
        return Vector3(
            self.x + other.x,
            self.y + other.y,
            self.z + other.z
        )

    def subtract(self, other: "Vector3") -> "Vector3":
        return Vector3(
            self.x - other.x,
            self.y - other.y,
            self.z - other.z
        )

    def multiply(self, scalar: float) -> "Vector3":
        return Vector3(
            self.x * scalar,
            self.y * scalar,
            self.z * scalar
        )

    def divide(self, scalar: float) -> "Vector3":
        if scalar == 0.0:
            raise ZeroDivisionError("Нельзя делить на ноль")
        return Vector3(
            self.x / scalar,
            self.y / scalar,
            self.z / scalar
            )

    def magnitude(self) -> float:
        return hypot(self.x, self.y, self.z)

    def normalize(self) -> Vector3:
        magni = self.magnitude()
        if magni == 0.0:
            raise ZeroDivisionError("Длина не может быть равно 0")
        divi = self.divide(magni)
        return divi

    def distance_to(self, other: "Vector3") -> float:
        dist = self.subtract(other)
        magni = dist.magnitude()
        return magni

    def __repr__(self) -> str:
        return (f"Vector3({self.x}, {self.y}, {self.z})")

    def dot(self, other: "Vector3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def angle_to(self, other: "Vector3") -> float:
        first_length = self.magnitude()
        second_length = other.magnitude()

        if first_length == 0.0 or second_length == 0.0:
            raise ValueError("Длина не может быть равно 0")

        # Нормализация до произведения уменьшает риск переполнения.
        cosine = self.normalize().dot(other.normalize())
        cosine = max(-1.0, min(1.0, cosine))
        return acos(cosine)

    def cross(self, other: "Vector3") -> "Vector3":
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def project_onto(self, other: "Vector3") -> "Vector3":
        other_length_vector = other.magnitude()

        if other_length_vector == 0.0:
            raise ValueError("Длина не может быть равно 0")

        direction = other.normalize()
        return direction.multiply(self.dot(direction))

    def rotate_2d(self, angle: float) -> Vector3:
        cos_angle = cos(angle)
        sin_angle = sin(angle)

        x_new = self.x * cos_angle - self.y * sin_angle
        y_new = self.x * sin_angle + self.y * cos_angle

        return Vector3(x_new, y_new, self.z)

    @staticmethod
    def circular_position(
        radius: float,
        angular_speed: float,
        time: float,
        ) -> "Vector3":
        if not all(isfinite(value) for value in (radius, angular_speed, time)):
            raise ValueError("Параметры окружности должны быть конечными")
        if radius < 0:
            raise ValueError("Радиус не может быть отрицательным")
        angle = angular_speed * time
        x = radius * cos(angle)
        y = radius * sin(angle)
        return Vector3(x, y, 0.0)

    def direction_to(self, other: "Vector3") -> "Vector3":
        direction = other.subtract(self)
        return direction.normalize()
