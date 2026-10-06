import numpy as np
import pytest
from scipy.integrate import solve_ivp

from solar_simulator.scenarios import earth_moon, binary_star, sun_earth_moon, MOON_DISTANCE
from solar_simulator.simulation import AU, G, center_of_mass, step, total_energy, total_momentum


@pytest.mark.parametrize("factory", [earth_moon, binary_star, sun_earth_moon])
def test_scenario_conserves_quantities(factory):
    bodies, period = factory()
    initial_energy = total_energy(bodies)
    initial_center = center_of_mass(bodies)
    scale = sum(b.mass * b.velocity.magnitude() for b in bodies)
    error = 0
    for _ in range(2000):
        bodies = step(bodies, 2 * period / 2000)
        error = max(error, abs((total_energy(bodies) - initial_energy) / initial_energy))
    assert error < 0.001
    assert total_momentum(bodies).magnitude() / scale < 1e-12
    assert center_of_mass(bodies).distance_to(initial_center) / AU < 1e-12


def test_three_body_against_independent_reference():
    bodies, period = sun_earth_moon()
    initial = np.array([[b.position.x, b.position.y, b.position.z,
                         b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies])
    # Единицы: AU и лунный характерный период. Эталон считает полную
    # матрицу взаимодействий независимо от нашего попарного алгоритма.
    initial[:, :3] /= AU
    initial[:, 3:] *= period / AU
    coefficients = np.array([G * b.mass * period**2 / AU**3 for b in bodies])

    def rhs(time, state):
        state = state.reshape(3, 6)
        delta = state[None, :, :3] - state[:, None, :3]
        distances = np.linalg.norm(delta, axis=2)
        np.fill_diagonal(distances, np.inf)
        acceleration = np.sum(delta * (coefficients[None, :] / distances**3)[:, :, None], axis=1)
        return np.concatenate((state[:, 3:], acceleration), axis=1).ravel()

    times = np.linspace(0, 2, 41)
    reference = solve_ivp(rhs, (0, 2), initial.ravel(), method="DOP853",
                          t_eval=times, rtol=1e-12, atol=1e-14)
    assert reference.success
    actual = []
    for index in range(4001):
        if index % 100 == 0:
            delta = bodies[2].position.subtract(bodies[1].position)
            actual.append([delta.x / AU, delta.y / AU, delta.z / AU])
        if index < 4000:
            bodies = step(bodies, 2 * period / 4000)
    states = reference.y.T.reshape(-1, 3, 6)
    relative = states[:, 2, :3] - states[:, 1, :3]
    assert np.max(np.linalg.norm(np.array(actual) - relative, axis=1)) * AU / MOON_DISTANCE < 0.001


def test_binary_star_returns_after_period():
    bodies, period = binary_star()
    initial = bodies[0].position
    for _ in range(2000):
        bodies = step(bodies, period / 2000)
    assert bodies[0].position.distance_to(initial) / AU < 1e-4
