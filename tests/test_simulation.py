from math import atan2, pi

import pytest

from solar_simulator.simulation import (
    AU, G, Body, accelerations, center_of_mass, step, sun_earth,
    total_energy, total_momentum,
)
from solar_simulator.vector3 import Vector3


def test_uniform_motion_without_other_bodies():
    body = Body("free", 1, Vector3(1, 2, 3), Vector3(4, -1, 0))
    result = step([body], 2)[0]
    assert (result.position.x, result.position.y, result.position.z) == (9, 0, 3)
    assert body.position.x == 1
    assert result.velocity.x == 4


def test_pair_gravity_has_correct_direction_and_magnitude():
    bodies = [Body("a", 2, Vector3(0, 0, 0), Vector3(0, 0, 0)),
              Body("b", 3, Vector3(2, 0, 0), Vector3(0, 0, 0))]
    a, b = accelerations(bodies)
    assert a.x == pytest.approx(G * 3 / 4, rel=1e-12, abs=0)
    assert b.x == pytest.approx(-G * 2 / 4, rel=1e-12, abs=0)
    assert a.y == b.y == a.z == b.z == 0
    assert total_energy(bodies) == pytest.approx(-G * 2 * 3 / 2, rel=1e-12, abs=0)


def test_coincident_positions_are_rejected():
    body = Body("a", 1, Vector3(0, 0, 0), Vector3(0, 0, 0))
    for operation in (accelerations, total_energy):
        with pytest.raises(ValueError):
            operation([body, body])


@pytest.mark.parametrize("dt", [0, -1, float("nan"), float("inf")])
def test_invalid_step(dt):
    with pytest.raises(ValueError):
        step(sun_earth()[0], dt)


@pytest.mark.parametrize("mass", [0, -1, float("nan"), float("inf")])
def test_invalid_body_mass(mass):
    with pytest.raises(ValueError):
        Body("a", mass, Vector3(0, 0, 0), Vector3(0, 0, 0))


def orbit_error(steps):
    bodies, period = sun_earth()
    for _ in range(steps):
        bodies = step(bodies, period / steps)
    relative = bodies[1].position.subtract(bodies[0].position)
    return relative.subtract(Vector3(AU, 0, 0)).magnitude() / AU


def test_second_order_convergence():
    coarse, fine = orbit_error(200), orbit_error(400)
    assert 3.8 < coarse / fine < 4.2


def test_ten_orbits_conserve_energy_momentum_and_center_of_mass():
    bodies, period = sun_earth()
    initial_energy = total_energy(bodies)
    momentum_scale = sum(b.mass * b.velocity.magnitude() for b in bodies)
    initial_center = center_of_mass(bodies)
    maximum_error = 0
    elapsed_angle = 0
    previous_angle = 0
    for _ in range(10000):
        bodies = step(bodies, period / 1000)
        maximum_error = max(maximum_error, abs((total_energy(bodies) - initial_energy) / initial_energy))
        relative = bodies[1].position.subtract(bodies[0].position)
        angle = atan2(relative.y, relative.x)
        elapsed_angle += (angle - previous_angle + pi) % (2 * pi) - pi
        previous_angle = angle
    assert maximum_error < 0.001
    measured_period = (10 * period) * (2 * pi / elapsed_angle)
    assert abs(measured_period / period - 1) < 0.001
    assert total_momentum(bodies).magnitude() / momentum_scale < 1e-12
    assert center_of_mass(bodies).distance_to(initial_center) / AU < 1e-12


@pytest.mark.parametrize("eccentricity", [-0.1, 1, 2, float("nan"), float("inf")])
def test_invalid_eccentricity(eccentricity):
    with pytest.raises(ValueError):
        sun_earth(eccentricity)


@pytest.mark.parametrize("eccentricity", [0.0, 0.3, 0.6])
def test_elliptical_orbit_against_independent_scipy_solution(eccentricity):
    # Эталон решает относительное движение в безразмерных единицах.
    # Он не вызывает accelerations/step: ошибки нашей формулы не копируются.
    import numpy as np
    from scipy.integrate import solve_ivp

    def rhs(time, state):
        position = state[:3]
        acceleration = -position / np.linalg.norm(position)**3
        return np.concatenate((state[3:], acceleration))

    from solar_simulator.simulation import SUN_MASS, EARTH_MASS
    speed_unit = (G * (SUN_MASS + EARTH_MASS) / AU)**0.5
    initial = [1 - eccentricity, 0, 0, 0,
               ((1 + eccentricity) / (1 - eccentricity))**0.5, 0]
    times = np.linspace(0, 2 * pi, 101)
    reference = solve_ivp(rhs, (0, 2 * pi), initial, method="DOP853",
                          t_eval=times, rtol=1e-12, atol=1e-14)
    assert reference.success
    # Проверка эталона: замыкание орбиты через аналитический период.
    assert np.linalg.norm(reference.y[:, -1] - initial) < 1e-8
    bodies, period = sun_earth(eccentricity)
    initial_energy = total_energy(bodies)
    positions, velocities, energy_errors = [], [], []
    steps = 8000
    for index in range(steps + 1):
        if index % 80 == 0:
            relative = bodies[1].position.subtract(bodies[0].position)
            velocity = bodies[1].velocity.subtract(bodies[0].velocity)
            positions.append([relative.x / AU, relative.y / AU, relative.z / AU])
            velocities.append([velocity.x / speed_unit, velocity.y / speed_unit, velocity.z / speed_unit])
        energy_errors.append(abs((total_energy(bodies) - initial_energy) / initial_energy))
        if index < steps:
            bodies = step(bodies, period / steps)
    assert np.max(np.linalg.norm(np.array(positions) - reference.y[:3].T, axis=1)) < 5e-4
    assert np.max(np.linalg.norm(np.array(velocities) - reference.y[3:].T, axis=1)) < 0.002
    assert max(energy_errors) < 0.001
    # Апoцентр/перицентр: r = a(1±e); середина периода — апоцентр.
    assert np.linalg.norm(positions[0]) == pytest.approx(1 - eccentricity)
    assert np.linalg.norm(positions[50]) == pytest.approx(1 + eccentricity, rel=5e-4)
