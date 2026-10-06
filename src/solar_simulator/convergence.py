"""Сравнение фиксированных шагов на одном интервале, без ложных гарантий."""
from dataclasses import replace
from math import isfinite, sqrt

from .experiment import advance
from .simulation import total_energy


def compare_steps(experiment, steps: int) -> dict:
    if type(steps) is not int or steps<=0:
        raise ValueError("Для сравнения нужно положительное целое steps")
    if experiment.halted:
        raise ValueError("Остановленный эксперимент сначала нужно сбросить")
    runs=[]
    values=[]
    initial_energy=total_energy(experiment.initial)
    for factor in (1,2,4):
        start=replace(experiment,settings=replace(experiment.settings,dt=experiment.settings.dt/factor))
        result=advance(start,steps*factor)
        if result.halted:
            raise ValueError("Сравнение на одном интервале невозможно: расчёт остановлен при контакте")
        runs.append(result)
        residual=total_energy(result.bodies)+result.dissipated_energy+result.model_energy_offset-initial_energy
        values.append(dict(dt_seconds=start.settings.dt,steps=steps*factor,
            final_time_seconds=result.time,new_events=len(result.events)-len(experiment.events),
            energy_budget_residual_joules=residual,
            relative_energy_budget_residual=abs(residual/initial_energy) if initial_energy else None))
    def difference(a,b,field):
        if [x.name for x in a.bodies]!=[x.name for x in b.bodies]:
            raise ValueError("Разные шаги дали разный состав тел: сравнение координат невозможно")
        return sqrt(sum(getattr(x,field).subtract(getattr(y,field)).magnitude()**2
                        for x,y in zip(a.bodies,b.bodies)))
    position=[difference(runs[0],runs[1],"position"),difference(runs[1],runs[2],"position")]
    velocity=[difference(runs[0],runs[1],"velocity"),difference(runs[1],runs[2],"velocity")]
    smooth=not any(v["new_events"] for v in values)
    ratio=position[0]/position[1] if position[1]>0 else None
    result=dict(runs=values,position_differences_metres=position,velocity_differences_m_per_s=velocity,
                position_difference_ratio=ratio,
                finest_position_error_estimate_metres=position[1]/3 if smooth else None,
                estimate_assumption="Smooth second-order convergence; inspect ratio near 4, not a guaranteed bound" if smooth
                    else "Impacts present: second-order Richardson estimate disabled")
    if not all(isfinite(v) for v in position+velocity):
        raise ValueError("Переполнение разностей при сравнении")
    return result
