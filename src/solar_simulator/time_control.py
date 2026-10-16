"""Bounded forward packets; solver settings and physical time stay explicit."""
from dataclasses import replace
from math import isfinite

from .experiment import Experiment, advance


def validate_target(experiment: Experiment, target: float, max_steps: int = 20):
    """Validate before a UI applies pending settings or starts a worker."""
    if type(target) not in (int, float) or not isfinite(target) or target < 0:
        raise ValueError("Целевое время: конечное неотрицательное число секунд")
    if type(experiment.time) not in (int, float) or not isfinite(experiment.time) or experiment.time < 0:
        raise ValueError("Текущее время должно быть конечным и неотрицательным")
    if target < experiment.time:
        raise ValueError("Расчёт только вперёд; для возврата загрузите JSON или сбросьте опыт")
    if type(max_steps) is not int or not 1 <= max_steps <= 2000:
        raise ValueError("Размер пакета: целое число от 1 до 2000")


def _interval(experiment, duration, target):
    end = experiment.time + duration
    if not isfinite(end) or end <= experiment.time or end > target:
        raise ValueError("Интервал не разрешается при текущей точности времени float64")
    if duration == target - experiment.time and end != target:
        raise ValueError("Конечное время не представимо этим интервалом float64")
    settings = experiment.settings
    result = advance(replace(experiment, settings=replace(settings, dt=duration)), 1)
    return replace(result, settings=settings)


def advance_towards(experiment: Experiment, target: float, max_steps: int = 20) -> Experiment:
    """One packet towards elapsed SI seconds, with at most max_steps intervals.

    Verlet retains full dt steps and at most one shorter terminal step.
    DOP853 restarts on a bounded interval without changing any tolerances.
    A stop contact keeps its actual event time, even before the target.
    """
    validate_target(experiment, target, max_steps)
    if experiment.halted or target == experiment.time:
        return experiment
    remaining = target - experiment.time
    dt = experiment.settings.dt
    if experiment.settings.integrator == "dop853":
        # Comparison avoids overflowing dt*max_steps when the target is nearer.
        duration = dt * max_steps if dt <= remaining / max_steps else remaining
        return _interval(experiment, duration, target)

    count = max_steps if dt <= remaining / max_steps else int(remaining / dt)
    # Rounded division/multiplication must never cross the target.
    while count and (dt * count > remaining or experiment.time + dt * count > target):
        count -= 1
    if count:
        experiment = advance(experiment, count)
        if experiment.halted or count == max_steps or experiment.time == target:
            return experiment
    remaining = target - experiment.time
    return _interval(experiment, min(dt, remaining), target)
