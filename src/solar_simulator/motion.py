"""Кинематика в SI. Ускорение в этих формулах постоянно."""
from math import isfinite


def calculate_position(initial_position: float, velocity: float, time: float) -> float:
    """x = x₀ + vt; время может быть массивом NumPy."""
    return initial_position + velocity * time


def _validate_step(*values: float, dt: float) -> None:
    if not all(isfinite(value) for value in (*values, dt)):
        raise ValueError("Параметры движения должны быть конечными")
    if dt < 0:
        raise ValueError("Шаг времени не может быть отрицательным")


def update_velocity(velocity: float, acceleration: float, dt: float) -> float:
    _validate_step(velocity, acceleration, dt=dt)
    return velocity + acceleration * dt


def update_position(position: float, velocity: float, acceleration: float, dt: float) -> float:
    """x = x₀ + v₀·dt + a·dt²/2; не интегратор переменного ускорения."""
    _validate_step(position, velocity, acceleration, dt=dt)
    return position + velocity * dt + 0.5 * acceleration * dt**2
