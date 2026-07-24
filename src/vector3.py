from math import sqrt

class Vector3:
    def __init__(self, x: float, y: float, z: float) -> None:
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
        quadr = self.x ** 2 + self.y ** 2 + self.z ** 2
        return sqrt(quadr)
    
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

    
vector = Vector3(1.0, 2.0, 3.0)

print(vector)
print(repr(vector))
