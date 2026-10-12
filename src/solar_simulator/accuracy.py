"""Adaptive high-accuracy integration of smooth Newtonian or EIH 1PN masses.

Error tolerances control local estimates, not guaranteed global error bounds.
Work in a translating centre-of-mass frame; optionally integrate one relative
pair separately to reduce the scale of its local error-control variables.
"""
from math import fsum, isfinite

import numpy as np
from scipy.integrate import solve_ivp

from .simulation import Body, G
from .vector3 import Vector3
from .error_control import PerBodyDOP853, validate_error_control


def evolve_accurate(bodies, duration, *, rtol=1e-13, position_atol=1e-3, velocity_atol=1e-9,
                    physics="newtonian", figures=(), start_time=0., return_work=False,
                    relative_pair=None, backend="python", error_control="per-body"):
    validate_error_control(error_control)
    if backend not in ("python", "rust"):
        raise ValueError("Неизвестное ядро точного расчёта")
    if type(duration) not in (float, int) or not isfinite(duration) or duration <= 0:
        raise ValueError("Интервал должен быть положительным конечным числом")
    if not bodies or any(b.radius > 0 for b in bodies):
        raise ValueError("DOP853 поддерживает только точечные тела без контактов")
    if physics not in ("newtonian", "eih-1pn"):
        raise ValueError("Физика: newtonian или eih-1pn")
    if physics == "eih-1pn":
        from .relativity import C, _eih_acceleration, validate_bodies
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
    native_force = None
    if backend == "rust":
        from .native_forces import prepare as prepare_native
        native_force = prepare_native(masses)
    from .coordinates import prepare_pair
    pair_coordinates = prepare_pair(bodies,relative_pair)
    positions = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    velocities = np.array([[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies])
    # Scale mass weights before summation to avoid overflowing total mass.
    weights = masses / masses.max()
    weights /= fsum(weights)
    center = np.array([fsum(weights*positions[:, k]) for k in range(3)])
    drift = np.array([fsum(weights*velocities[:, k]) for k in range(3)])
    count = len(bodies)
    p0, v0 = positions-center, velocities-drift
    if pair_coordinates:
        # Form the small relative vector before subtracting a large common
        # origin, avoiding another round of absolute-coordinate cancellation.
        p0 = pair_coordinates.encode(positions,offset=center)
        v0 = pair_coordinates.encode(velocities,offset=drift)
    initial = np.concatenate((p0.ravel(), v0.ravel()))
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
        solver_velocity = v
        pair_displacement = None
        if pair_coordinates:
            pair_displacement = (pair_coordinates.first,pair_coordinates.second,p[pair_coordinates.second])
            p, v = pair_coordinates.decode(p), pair_coordinates.decode(v)
        acceleration = np.zeros_like(p)
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            if native_force is not None:
                acceleration = native_force(p, v+drift, C if physics == "eih-1pn" else None, pair_displacement)
            elif physics == "eih-1pn":
                # Use original-frame velocities even though the solver state
                # subtracts a constant drift for numerical conditioning.
                acceleration = _eih_acceleration(p, v+drift, masses, C, pair_displacement)
            else:
                delta = p[pairs[1]]-p[pairs[0]]
                if pair_displacement is not None:
                    first,second,relative = pair_displacement
                    selected = (pairs[0]==min(first,second)) & (pairs[1]==max(first,second))
                    delta[selected] = relative if first < second else -relative
                distance = np.linalg.norm(delta, axis=1)
                if np.any(distance == 0):
                    raise ValueError("Совпадающие положения: гравитация не определена")
                force = delta*(G/distance**3)[:, None]
                np.add.at(acceleration, pairs[0], force*masses[pairs[1], None])
                np.add.at(acceleration, pairs[1], -force*masses[pairs[0], None])
            if prepared:
                acceleration += figure_acceleration(p, masses, prepared, orientation_time,
                                                    _pair_displacement=pair_displacement)
        solver_acceleration = pair_coordinates.encode(acceleration) if pair_coordinates else acceleration
        derivative = np.concatenate((solver_velocity.ravel(), solver_acceleration.ravel()))
        if moving:
            derivative = np.append(derivative, orientation_power(p, masses, prepared, orientation_time,
                                  _pair_displacement=pair_displacement)/work_scale)
        return derivative

    try:
        method = PerBodyDOP853 if error_control == "per-body" else "DOP853"
        result = solve_ivp(rhs, (0, duration), initial, method=method, rtol=rtol,
                           atol=atol, t_eval=[duration])
    except FloatingPointError as error:
        raise ValueError("Переполнение при точном расчёте гравитации") from error
    if not result.success or result.t.size != 1 or result.t[-1] != duration:
        raise RuntimeError("Не удалось достичь конечного времени: "+result.message)
    final = result.y[:, -1]
    if not np.all(np.isfinite(final)):
        raise ValueError("Неконечное состояние точного расчёта")
    p = final[:3*count].reshape(count, 3)
    v = final[3*count:6*count].reshape(count, 3)
    if pair_coordinates:
        p, v = pair_coordinates.decode(p), pair_coordinates.decode(v)
    p, v = p+center+drift*duration, v+drift
    bodies = [Body(b.name, b.mass, Vector3(*map(float, position)), Vector3(*map(float, velocity)), b.radius, b.spin)
              for b, position, velocity in zip(bodies, p, v)]
    work = float(final[-1]*work_scale) if moving else 0.
    if not isfinite(work):
        raise ValueError("Неконечная работа заданной ориентации")
    return (bodies, work) if return_work else bodies
