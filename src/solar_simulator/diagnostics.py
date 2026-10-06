"""Диагностика ньютоновского движения. Величины в SI, углы в радианах."""
from dataclasses import dataclass
from math import atan2, hypot, pi, sqrt

from .simulation import Body, G
from .vector3 import Vector3


def angular_momentum(bodies: list[Body]) -> Vector3:
    """Общий L = Σ (r × mv + spin), spin в кг·м²/с."""
    result = Vector3(0, 0, 0)
    for body in bodies:
        result = result.add(body.position.cross(body.velocity).multiply(body.mass))
        result = result.add(body.spin)
    return result


@dataclass(frozen=True)
class OrbitParameters:
    eccentricity: float
    specific_energy: float
    semi_major_axis: float | None
    periapsis: float
    apoapsis: float | None
    period: float | None
    inclination: float


def orbit_parameters(primary: Body, secondary: Body) -> OrbitParameters:
    """Мгновенные (оскулирующие) параметры относительной кеплеровой орбиты.

    Для N тел это диагностическое приближение: остальные тела возмущают
    орбиту. Радиальное движение отвергается как вырожденная орбита.
    Для почти параболического состояния a и период не определяются.
    """
    position = secondary.position.subtract(primary.position)
    velocity = secondary.velocity.subtract(primary.velocity)
    radius = position.magnitude()
    if radius == 0:
        raise ValueError("Совпадающие положения")
    mu = G * (primary.mass + secondary.mass)
    h = position.cross(velocity)
    h_length = h.magnitude()
    if h_length == 0:
        raise ValueError("Радиальная орбита вырождена")
    speed2 = velocity.dot(velocity)
    energy = 0.5 * speed2 - mu / radius
    e_vector = velocity.cross(h).divide(mu).subtract(position.divide(radius))
    eccentricity = e_vector.magnitude()
    parameter = h_length**2 / mu
    periapsis = parameter / (1 + eccentricity)
    inclination = atan2(hypot(h.x, h.y), h.z)
    energy_scale = 0.5 * speed2 + mu / radius
    if abs(energy) <= 1e-12 * energy_scale:
        return OrbitParameters(eccentricity, energy, None, periapsis, None, None, inclination)
    axis = -mu / (2 * energy)
    if energy < 0:
        # r_a = 2a - r_p избегает деления на почти нулевое 1-e.
        return OrbitParameters(eccentricity, energy, axis, periapsis,
                               2 * axis - periapsis, 2 * pi * sqrt(axis**3 / mu), inclination)
    return OrbitParameters(eccentricity, energy, axis, periapsis, None, None, inclination)
