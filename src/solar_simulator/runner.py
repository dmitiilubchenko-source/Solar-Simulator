"""Отделяет физический шаг от частоты выдачи снимков для графиков."""
from math import isfinite

from .simulation import Body, step


def sampled_states(bodies: list[Body], dt: float, steps: int, *, backend: str = "python", every: int = 20):
    """Выдаёт (номер шага, состояние), включая исходное и финальное.

    Rust получает every физических шагов одним вызовом. Этот режим для
    точечных тел; тела с радиусами требуют run_until_contact.
    """
    if not isfinite(dt) or dt <= 0:
        raise ValueError("dt должен быть положительным и конечным")
    if type(steps) is not int or steps < 0 or type(every) is not int or every < 1:
        raise ValueError("Некорректное число шагов или интервал снимков")
    if backend not in ("python","rust"):
        raise ValueError("Неизвестное ядро")
    if any(body.radius > 0 for body in bodies):
        raise ValueError("Для тел с радиусами используйте run_until_contact")
    state=list(bodies)
    index=0
    yield index,state
    while index<steps:
        count=min(every,steps-index)
        if backend=="rust":
            from .rust_backend import evolve
            state=evolve(state,dt,count)
        else:
            for _ in range(count):
                state=step(state,dt)
        index+=count
        yield index,state
