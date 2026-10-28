"""Сравнение фиксированных шагов на одном интервале, без ложных гарантий."""
from dataclasses import replace
from math import isfinite, sqrt

from .experiment import advance
from .simulation import total_energy
from .diagnostics import model_invariants


def compare_steps(experiment, steps: int) -> dict:
    if type(steps) is not int or steps<=0:
        raise ValueError("Для сравнения нужно положительное целое steps")
    if experiment.settings.integrator != "verlet":
        return compare_tolerances(experiment, steps)
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


def compare_tolerances(experiment, steps: int) -> dict:
    """Sensitivity to adaptive tolerances; differences are not global bounds."""
    if type(steps) is not int or steps <= 0 or experiment.halted:
        raise ValueError("Нужен положительный steps и неостановленный эксперимент")
    if experiment.settings.integrator != "dop853":
        raise ValueError("Сравнение допусков требует DOP853")
    base = experiment.settings
    tolerances = [base.rtol, max(3e-14, base.rtol/2), max(3e-14, base.rtol/4)]
    if len(set(tolerances)) < 3:
        raise ValueError("Недостаточно диапазона rtol для трёх запусков: достигнут предел float64")
    runs, states = [], []
    initial_energy = model_invariants(experiment.initial, base.physics, base.figures)[0]
    if experiment.rotations:
        from .nbody_rotation import invariants
        initial_energy = invariants(experiment.initial, experiment.initial_rotations)[0]
    for factor, tolerance in zip((1, 2, 4), tolerances):
        settings = replace(base, rtol=tolerance, position_atol=base.position_atol/factor,
                           velocity_atol=base.velocity_atol/factor)
        start = replace(experiment, settings=settings)
        if experiment.rotations:
            def refine(states):
                return tuple(replace(s, quaternion_atol=s.quaternion_atol/factor,
                    momentum_atol=s.momentum_atol/factor) for s in states)
            start = replace(start, initial_rotations=refine(start.initial_rotations), rotations=refine(start.rotations))
        state = advance(start, steps)
        residual = model_invariants(state.bodies, base.physics, base.figures, state.time)[0]+state.dissipated_energy+state.model_energy_offset-state.orientation_work-initial_energy
        if state.rotations:
            residual = invariants(state.bodies, state.rotations)[0]-initial_energy
        runs.append(dict(rtol=tolerance, position_atol_metres=settings.position_atol,
                         velocity_atol_m_per_s=settings.velocity_atol, final_time_seconds=state.time,
                         energy_budget_residual_joules=residual, orientation_work_joules=state.orientation_work))
        states.append(state)
    def difference(a, b, field):
        return sqrt(sum(getattr(x, field).distance_to(getattr(y, field))**2
                        for x, y in zip(a.bodies, b.bodies)))
    from dataclasses import asdict
    rotation_comparison = None
    if experiment.rotations:
        import numpy as np
        from .rotation import rotation_matrix
        def comparison(k):
            return dict(body=experiment.rotations[k].body,
            attitude_frobenius=[float(np.linalg.norm(rotation_matrix(a.rotations[k].quaternion)-rotation_matrix(b.rotations[k].quaternion)))
                for a, b in zip(states, states[1:])],
            angular_momentum_differences_kg_m2_s=[float(np.linalg.norm(np.array(a.rotations[k].angular_momentum)-b.rotations[k].angular_momentum))
                for a, b in zip(states, states[1:])])
        rotation_comparison=comparison(0) if len(experiment.rotations)==1 else dict(per_body=[comparison(k) for k in range(len(experiment.rotations))])
    relative = None
    if base.relative_pair:
        def relative_difference(a,b,field):
            def value(state):
                bodies = {body.name:body for body in state.bodies}
                return getattr(bodies[base.relative_pair[1]],field).subtract(getattr(bodies[base.relative_pair[0]],field))
            return value(a).distance_to(value(b))
        relative = dict(bodies=list(base.relative_pair),position_differences_metres=[
            relative_difference(states[0],states[1],"position"),relative_difference(states[1],states[2],"position")],
            velocity_differences_m_per_s=[relative_difference(states[0],states[1],"velocity"),relative_difference(states[1],states[2],"velocity")])
    return dict(comparison="adaptive_tolerances", physics=base.physics, figures=[asdict(f) for f in base.figures],
                error_control=base.error_control,
                relative_pair_comparison=relative, runs=runs,
                rotation_comparison=rotation_comparison,
                position_differences_metres=[difference(states[0], states[1], "position"),
                                            difference(states[1], states[2], "position")],
                velocity_differences_m_per_s=[difference(states[0], states[1], "velocity"),
                                             difference(states[1], states[2], "velocity")],
                finest_position_error_estimate_metres=None,
                estimate_assumption="Tolerance sensitivity only; no Richardson order or guaranteed global error bound")
