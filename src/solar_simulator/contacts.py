"""Контакт сфер вдоль параболической интерполяции положения Verlet.

Это детектор численного шага, не точное решение непрерывной гравитации.
Уменьшение dt необходимо для сходимости времени контакта.
"""
from dataclasses import dataclass
from math import isfinite

import numpy as np

from .simulation import Body, accelerations, step


@dataclass(frozen=True)
class Contact:
    first: int
    second: int
    time: float


@dataclass(frozen=True)
class RunResult:
    bodies: list[Body]
    time: float
    contact: Contact | None


def first_contact(bodies: list[Body], dt: float, *, incoming_only: bool = False) -> Contact | None:
    """incoming_only отбирает вход в сферу для цикла последовательных ударов.

    Обычный режим по-прежнему регистрирует касание и начальное перекрытие.
    """
    if not isfinite(dt) or dt <= 0:
        raise ValueError("Шаг должен быть положительным и конечным")
    # Начальный контакт проверяется до силы: совпадение центров сфер допустимо
    # как событие, но не как аргумент гравитационного расчёта.
    pairs = []
    for i, first in enumerate(bodies):
        for j in range(i+1,len(bodies)):
            radius = first.radius + bodies[j].radius
            if not isfinite(radius):
                raise ValueError("Переполнение суммы радиусов")
            if radius <= 0:
                continue
            distance = first.position.distance_to(bodies[j].position)
            if incoming_only:
                if distance < radius*(1-1e-7):
                    raise ValueError("Глубокое перекрытие сфер")
                if abs(distance-radius) <= radius*1e-12:
                    delta = bodies[j].position.subtract(first.position)
                    speed = bodies[j].velocity.subtract(first.velocity).dot(delta)
                    if speed < 0:
                        return Contact(i,j,0.0)
                    if speed == 0:
                        raise ValueError("Покоящийся контакт требует модели контактных сил")
            elif distance <= radius:
                return Contact(i,j,0.0)
            pairs.append((i,j,radius))
    if not pairs:
        return None
    a = accelerations(bodies)
    earliest = None
    for i,j,radius in pairs:
        delta = bodies[j].position.subtract(bodies[i].position)
        velocity = bodies[j].velocity.subtract(bodies[i].velocity)
        acceleration = a[j].subtract(a[i])
        # Размерность исключена: u=t/dt, масштаб длины выбран по данным.
        q = np.array([[delta.x,delta.y,delta.z],
                      [velocity.x*dt,velocity.y*dt,velocity.z*dt],
                      [0.5*acceleration.x*dt*dt,0.5*acceleration.y*dt*dt,0.5*acceleration.z*dt*dt]])
        scale = max(radius,float(np.max(np.abs(q))))
        q /= scale
        polynomial = sum((np.convolve(q[:,axis],q[:,axis]) for axis in range(3)),np.zeros(5))
        polynomial[0] -= (radius/scale)**2
        # Минимум расстояния может быть между двумя непересекающимися концами.
        roots = np.polynomial.polynomial.polyroots(np.polynomial.polynomial.polytrim(polynomial,tol=1e-14*float(np.max(np.abs(polynomial)))))
        for root in roots:
            if abs(root.imag) <= 1e-7 and -1e-12 <= root.real <= 1+1e-12:
                u = min(1.0,max(0.0,float(root.real)))
                point = q[0]+q[1]*u+q[2]*u*u
                if incoming_only:
                    tangent = q[1]+2*q[2]*u
                    # Ошибка корня касания может дать крошечную отрицательную
                    # радиальную скорость. Такое касание не является ударом.
                    tolerance = 64*np.finfo(float).eps*np.linalg.norm(point)*np.linalg.norm(tangent)
                    if np.dot(point,tangent) >= -tolerance:
                        continue
                if abs(np.linalg.norm(point)-radius/scale) > 1e-7:
                    continue
                time = u*dt
                if earliest is None or time < earliest.time:
                    earliest = Contact(i,j,time)
    return earliest


def run_until_contact(bodies: list[Body], dt: float, steps: int, *, backend: str = "python") -> RunResult:
    """Проверочная Python-реализация: остановка, без слияния и отскока."""
    if not isfinite(dt) or dt <= 0 or type(steps) is not int or steps < 0:
        raise ValueError("Нужны положительный dt и неотрицательное целое steps")
    if backend == "rust":
        from .rust_backend import run_until_contact as native_run
        return native_run(bodies,dt,steps)
    if backend != "python":
        raise ValueError("Неизвестное ядро")
    state = list(bodies)
    elapsed = 0.0
    for _ in range(steps):
        event = first_contact(state,dt)
        if event is not None:
            if event.time > 0:
                state = step(state,event.time)
            elapsed += event.time
            return RunResult(state,elapsed,Contact(event.first,event.second,elapsed))
        state = step(state,dt)
        elapsed += dt
    return RunResult(state,elapsed,None)
