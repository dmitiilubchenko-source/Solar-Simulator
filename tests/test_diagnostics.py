from math import pi, sqrt

import pytest

from solar_simulator.diagnostics import angular_momentum, orbit_parameters
from solar_simulator.scenarios import sun_earth_moon
from solar_simulator.simulation import AU, G, Body, step, sun_earth, total_energy
from solar_simulator.vector3 import Vector3


@pytest.mark.parametrize("e", [0, 0.3, 0.6])
def test_initial_orbit_parameters(e):
    bodies, period = sun_earth(e)
    orbit = orbit_parameters(*bodies)
    assert orbit.eccentricity == pytest.approx(e, abs=1e-14)
    assert orbit.semi_major_axis == pytest.approx(AU)
    assert orbit.periapsis == pytest.approx(AU * (1 - e))
    assert orbit.apoapsis == pytest.approx(AU * (1 + e))
    assert orbit.period == pytest.approx(period)
    assert orbit.inclination == 0


@pytest.mark.parametrize("speed_factor", [sqrt(2), 2])
def test_escape_orbits_have_no_period(speed_factor):
    primary = Body("a", 1e30, Vector3(0, 0, 0), Vector3(0, 0, 0))
    secondary = Body("b", 1e24, Vector3(AU, 0, 0),
                     Vector3(0, speed_factor * sqrt(G * (primary.mass + 1e24) / AU), 0))
    orbit = orbit_parameters(primary, secondary)
    assert orbit.period is None
    assert orbit.apoapsis is None
    assert orbit.periapsis == pytest.approx(AU)
    if speed_factor == 2:
        assert orbit.eccentricity == pytest.approx(3)
        assert orbit.semi_major_axis < 0
    else:
        assert orbit.eccentricity == pytest.approx(1)
        assert orbit.semi_major_axis is None


def test_inclined_orbit_and_known_angular_momentum():
    body = Body("a", 2, Vector3(1, 0, 0), Vector3(0, 0, 3))
    result = angular_momentum([body])
    assert (result.x, result.y, result.z) == (0, -6, 0)
    central = Body("b", 1e30, Vector3(0, 0, 0), Vector3(0, 0, 0))
    assert orbit_parameters(central, body).inclination == pytest.approx(pi / 2)


def test_degenerate_orbits():
    a = Body("a", 1, Vector3(0, 0, 0), Vector3(0, 0, 0))
    with pytest.raises(ValueError):
        orbit_parameters(a, a)
    b = Body("b", 1, Vector3(1, 0, 0), Vector3(1, 0, 0))
    with pytest.raises(ValueError):
        orbit_parameters(a, b)


@pytest.mark.parametrize("e", [0, 0.6])
def test_hundred_orbits_have_bounded_energy_and_angular_momentum(e):
    bodies, period = sun_earth(e)
    initial_energy = total_energy(bodies)
    initial_l = angular_momentum(bodies)
    energy_error = 0
    l_error = 0
    for _ in range(200000):
        bodies = step(bodies, period / 2000)
        energy_error = max(energy_error, abs((total_energy(bodies) - initial_energy) / initial_energy))
        l_error = max(l_error, angular_momentum(bodies).distance_to(initial_l) / initial_l.magnitude())
    assert energy_error < 0.001
    assert l_error < 1e-11
    orbit = orbit_parameters(*bodies)
    assert abs(orbit.semi_major_axis / AU - 1) < 0.001
    # Сохранение формы не означает отсутствие накопленной фазовой ошибки.


def test_three_body_angular_momentum():
    bodies, period = sun_earth_moon()
    initial = angular_momentum(bodies)
    for _ in range(4000):
        bodies = step(bodies, period / 2000)
    assert angular_momentum(bodies).distance_to(initial) / initial.magnitude() < 1e-12
