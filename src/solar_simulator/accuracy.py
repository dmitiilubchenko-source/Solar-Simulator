"""Adaptive high-accuracy integration of smooth Newtonian or EIH 1PN masses.

Error tolerances control local estimates, not guaranteed global error bounds.
Work in a translating centre-of-mass frame to reduce coordinate scale effects.
"""
from math import fsum, isfinite

import numpy as np
from scipy.integrate import solve_ivp

from .simulation import Body, G
from .vector3 import Vector3


def evolve_accurate(bodies, duration, *, rtol=1e-13, position_atol=1e-3, velocity_atol=1e-9,
                    physics="newtonian", figures=(), start_time=0., return_work=False):
    if type(duration) not in (float, int) or not isfinite(duration) or duration <= 0:
        raise ValueError("Интервал должен быть положительным конечным числом")
    if not bodies or any(b.radius > 0 for b in bodies):
        raise ValueError("DOP853 поддерживает только точечные тела без контактов")
    if physics not in ("newtonian", "eih-1pn"):
        raise ValueError("Физика: newtonian или eih-1pn")
    if physics == "eih-1pn":
        from .relativity import eih_acceleration, validate_bodies
        validate_bodies(bodies)
    from .oblateness import (prepare, acceleration as figure_acceleration, prescribed,
                             validate_figures, potential_energy, orientation_power)
    if type(start_time) not in (int, float) or not isfinite(start_time) or start_time < 0:
        raise ValueError("Начальное время должно быть неотрицательным конечным числом")
    if type(return_work) is not bool:
        raise ValueError("return_work должен быть bool")
    prepared = prepare(bodies, figures)
    validate_figures(bodies, figures, start_time)
    validate_figures(bodies, figures, start_time+duration)
    moving = prescribed(figures)
    for value in (rtol, position_atol, velocity_atol):
        if type(value) not in (float, int) or not isfinite(value) or value <= 0:
            raise ValueError("Допуски должны быть положительными конечными числами")
    if not 3e-14 <= rtol <= 1e-2:
        raise ValueError("rtol должен быть от 3e-14 до 1e-2; меньший допуск не поддерживается float64")
    masses = np.array([b.mass for b in bodies])
    positions = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    velocities = np.array([[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies])
    # Scale mass weights before summation to avoid overflowing total mass.
    weights = masses / masses.max()
    weights /= fsum(weights)
    center = np.array([fsum(weights*positions[:, k]) for k in range(3)])
    drift = np.array([fsum(weights*velocities[:, k]) for k in range(3)])
    count = len(bodies)
    initial = np.concatenate(((positions-center).ravel(), (velocities-drift).ravel()))
    atol = np.concatenate((np.full(3*count, position_atol), np.full(3*count, velocity_atol)))
    work_scale = max(abs(potential_energy(bodies, figures, start_time)), 1.) if moving else 1.
    if moving:
        initial = np.append(initial, 0.)
        atol = np.append(atol, 1e-15)  # Work is scaled by initial quadrupole potential.
    pairs = np.triu_indices(count, 1)

    def rhs(time, state):
        orientation_time = float(start_time+time)  # SciPy also supplies NumPy scalars.
        p = state[:3*count].reshape(count, 3)
        v = state[3*count:6*count].reshape(count, 3)
        acceleration = np.zeros_like(p)
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            if physics == "eih-1pn":
                # Use original-frame velocities even though the solver state
                # subtracts a constant drift for numerical conditioning.
                acceleration = eih_acceleration(p, v+drift, masses)
            else:
                delta = p[pairs[1]]-p[pairs[0]]
                distance = np.linalg.norm(delta, axis=1)
                if np.any(distance == 0):
                    raise ValueError("Совпадающие положения: гравитация не определена")
                force = delta*(G/distance**3)[:, None]
                np.add.at(acceleration, pairs[0], force*masses[pairs[1], None])
                np.add.at(acceleration, pairs[1], -force*masses[pairs[0], None])
            if prepared:
                acceleration += figure_acceleration(p, masses, prepared, orientation_time)
        derivative = np.concatenate((v.ravel(), acceleration.ravel()))
        if moving:
            derivative = np.append(derivative, orientation_power(p, masses, prepared, orientation_time)/work_scale)
        return derivative

    try:
        result = solve_ivp(rhs, (0, duration), initial, method="DOP853", rtol=rtol,
                           atol=atol, t_eval=[duration])
    except FloatingPointError as error:
        raise ValueError("Переполнение при точном расчёте гравитации") from error
    if not result.success or result.t.size != 1 or result.t[-1] != duration:
        raise RuntimeError("Не удалось достичь конечного времени: "+result.message)
    final = result.y[:, -1]
    if not np.all(np.isfinite(final)):
        raise ValueError("Неконечное состояние точного расчёта")
    p = final[:3*count].reshape(count, 3)+center+drift*duration
    v = final[3*count:6*count].reshape(count, 3)+drift
    bodies = [Body(b.name, b.mass, Vector3(*map(float, position)), Vector3(*map(float, velocity)), b.radius, b.spin)
              for b, position, velocity in zip(bodies, p, v)]
    work = float(final[-1]*work_scale) if moving else 0.
    if not isfinite(work):
        raise ValueError("Неконечная работа заданной ориентации")
    return (bodies, work) if return_work else bodies
