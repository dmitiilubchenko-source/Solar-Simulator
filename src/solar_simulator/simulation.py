"""Ньютоновские точечные массы и Velocity Verlet. Все величины в SI."""
from dataclasses import dataclass, field
from math import isfinite, pi, sqrt

from .vector3 import Vector3

G = 6.67430e-11
AU = 1.495978707e11
SUN_MASS = 1.9885e30
EARTH_MASS = 5.9722e24


@dataclass(frozen=True)
class Body:
    name: str
    mass: float
    position: Vector3
    velocity: Vector3
    radius: float = 0.0
    spin: Vector3 = field(default_factory=lambda:Vector3(0,0,0))

    def __post_init__(self):
        for vector in (self.position,self.velocity,self.spin):
            if not isinstance(vector,Vector3) or not all(isfinite(v) for v in (vector.x,vector.y,vector.z)):
                raise ValueError("Положение, скорость и spin должны быть конечными Vector3")
        if not isfinite(self.mass) or self.mass <= 0:
            raise ValueError("Масса должна быть положительной и конечной")
        if not isfinite(self.radius) or self.radius < 0:
            raise ValueError("Радиус должен быть конечным и неотрицательным")
        if type(self.name) is not str or not self.name.strip():
            raise ValueError("Имя тела не должно быть пустым")


def accelerations(bodies: list[Body]) -> list[Vector3]:
    """aᵢ = Σ G mⱼ (rⱼ-rᵢ)/|rⱼ-rᵢ|³; пары считаются один раз."""
    result = [Vector3(0, 0, 0) for _ in bodies]
    for i, first in enumerate(bodies):
        for j in range(i + 1, len(bodies)):
            second = bodies[j]
            delta = second.position.subtract(first.position)
            distance = delta.magnitude()
            if distance == 0:
                raise ValueError("Совпадающие положения: гравитация не определена")
            direction = delta.divide(distance)
            factor = G / distance / distance
            result[i] = result[i].add(direction.multiply(factor * second.mass))
            result[j] = result[j].subtract(direction.multiply(factor * first.mass))
    return result


def step(bodies: list[Body], dt: float) -> list[Body]:
    """Возвращает новое состояние, не меняя входное. dt — секунды.

    Положение обновляется со старым ускорением, скорость — со средним
    старым и новым ускорением. Без смягчения и модели столкновений.
    """
    if not isfinite(dt) or dt <= 0:
        raise ValueError("Шаг должен быть положительным и конечным")
    old = accelerations(bodies)
    moved = [Body(body.name, body.mass,
                  body.position.add(body.velocity.multiply(dt)).add(a.multiply(0.5 * dt**2)),
                  body.velocity, body.radius, body.spin)
             for body, a in zip(bodies, old)]
    new = accelerations(moved)
    return [Body(body.name, body.mass, body.position,
                 body.velocity.add(a0.add(a1).multiply(0.5 * dt)), body.radius, body.spin)
            for body, a0, a1 in zip(moved, old, new)]


def total_energy(bodies: list[Body]) -> float:
    energy = sum(0.5 * body.mass * body.velocity.dot(body.velocity) for body in bodies)
    for i, first in enumerate(bodies):
        for second in bodies[i + 1:]:
            distance = first.position.distance_to(second.position)
            if distance == 0:
                raise ValueError("Совпадающие положения: энергия не определена")
            energy -= G * first.mass * second.mass / distance
    return energy


def total_momentum(bodies: list[Body]) -> Vector3:
    result = Vector3(0, 0, 0)
    for body in bodies:
        result = result.add(body.velocity.multiply(body.mass))
    return result


def center_of_mass(bodies: list[Body]) -> Vector3:
    if not bodies:
        raise ValueError("Для центра масс нужны тела")
    total_mass = sum(body.mass for body in bodies)
    result = Vector3(0, 0, 0)
    for body in bodies:
        result = result.add(body.position.multiply(body.mass / total_mass))
    return result


def sun_earth(eccentricity: float = 0.0) -> tuple[list[Body], float]:
    """Двухтельная орбита с большой полуосью AU, старт в перицентре.

    Это учебные начальные условия, а не эфемериды на конкретную дату.
    Возвращает тела и аналитический период относительной орбиты.
    """
    if not isfinite(eccentricity) or not 0 <= eccentricity < 1:
        raise ValueError("Для эллипса требуется 0 <= eccentricity < 1")
    mass = SUN_MASS + EARTH_MASS
    distance = AU * (1 - eccentricity)
    speed = sqrt(G * mass / AU) * sqrt((1 + eccentricity) / (1 - eccentricity))
    bodies = [
        Body("Sun", SUN_MASS, Vector3(-distance * EARTH_MASS / mass, 0, 0),
             Vector3(0, -speed * EARTH_MASS / mass, 0)),
        Body("Earth", EARTH_MASS, Vector3(distance * SUN_MASS / mass, 0, 0),
             Vector3(0, speed * SUN_MASS / mass, 0)),
    ]
    return bodies, 2 * pi * sqrt(AU**3 / (G * mass))
