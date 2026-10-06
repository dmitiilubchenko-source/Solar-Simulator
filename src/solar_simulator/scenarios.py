"""Учебные сценарии: начальные условия в SI, без реальных эфемерид."""
from math import pi, sqrt

from .simulation import AU, EARTH_MASS, SUN_MASS, G, Body
from .vector3 import Vector3

MOON_MASS = 7.342e22
MOON_DISTANCE = 384400e3


def circular_pair(name1, mass1, name2, mass2, distance):
    """Две массы на круговой орбите вокруг центра масс; тела и период."""
    mass = mass1 + mass2
    speed = sqrt(G * mass / distance)
    return [
        Body(name1, mass1, Vector3(-distance * mass2 / mass, 0, 0),
             Vector3(0, -speed * mass2 / mass, 0)),
        Body(name2, mass2, Vector3(distance * mass1 / mass, 0, 0),
             Vector3(0, speed * mass1 / mass, 0)),
    ], 2 * pi * sqrt(distance**3 / (G * mass))


def earth_moon():
    return circular_pair("Earth", EARTH_MASS, "Moon", MOON_MASS, MOON_DISTANCE)


def binary_star():
    return circular_pair("Star A", SUN_MASS, "Star B", SUN_MASS, AU)


def sun_earth_moon():
    """Вложенные круговые начальные условия, далее — полная гравитация N тел.

    Внешняя орбита относится к барицентру Земля–Луна. Лунный период
    возвращается лишь как характерный масштаб времени, не точный период
    трёхтельной системы под действием солнечных возмущений.
    """
    inner, moon_period = earth_moon()
    outer, _ = circular_pair("Sun", SUN_MASS, "Earth-Moon", EARTH_MASS + MOON_MASS, AU)
    sun, barycenter = outer
    return [sun] + [Body(body.name, body.mass,
                        body.position.add(barycenter.position),
                        body.velocity.add(barycenter.velocity)) for body in inner], moon_period
