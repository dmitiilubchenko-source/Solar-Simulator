"""Separated orientation/J2/C22 effects, independent RK45 force and JPL residual."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from solar_simulator.diagnostics import model_invariants
from solar_simulator.ephemerides import solar_system
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.oblateness import earth_j2, earth_moon_quadrupoles
from solar_simulator.orientation import PROFILE_SHA256, earth_pole, lunar_rotation
from solar_simulator.relativity import C
from solar_simulator.simulation import AU, G

if __package__:
    from .assess_oblateness import pair_errors
    from .assess_relativity import YEAR, independent_acceleration
    from .assess_resolved_moon import errors, states
else:
    from assess_oblateness import pair_errors
    from assess_relativity import YEAR, independent_acceleration
    from assess_resolved_moon import errors, states


def independent_figure_acceleration(p, mu, figures, names, time):
    """Analytic J2+C22 field in principal axes; no production tensor/force."""
    result = np.zeros_like(p)
    for figure in figures:
        source = names.index(figure.body)
        if figure.body == "Moon":
            rotation, _ = lunar_rotation(float(time))
        else:
            pole, _ = earth_pole(float(time))
        for target in range(len(mu)):
            if source == target:
                continue
            r = p[target]-p[source]
            distance = np.linalg.norm(r)
            n = r/distance
            scale = mu[source]*(figure.reference_radius/AU)**2/distance**4
            if figure.body == "Earth":
                z = n@pole
                field = 1.5*scale*figure.coefficient*((5*z*z-1)*n-2*z*pole)
            else:
                x,y,z = rotation.T@n
                local = 1.5*scale*figure.coefficient*((5*z*z-1)*np.array([x,y,z])-np.array([0.,0.,2*z]))
                local += 3*scale*figure.c22*(np.array([2*x,-2*y,0.])-5*(x*x-y*y)*np.array([x,y,z]))
                field = rotation@local
            result[target] += field
            result[source] -= mu[target]/mu[source]*field
    return result


def independent_reference(initial, figures, times):
    count = len(initial)
    q = states(initial).copy()
    q[:,:3] /= AU; q[:,3:] *= YEAR/AU
    mu = np.array([G*b.mass*YEAR**2/AU**3 for b in initial])
    names = [b.name for b in initial]
    def rhs(t,y):
        state = y.reshape(count,6)
        a = independent_acceleration(state[:,:3],state[:,3:],mu,C*YEAR/AU)
        a += independent_figure_acceleration(state[:,:3],mu,figures,names,t*YEAR)
        return np.concatenate((state[:,3:],a),axis=1).ravel()
    results = []
    for tolerance in (1e-12,1e-13,3e-14):
        solution = solve_ivp(rhs,(0,times[-1]/YEAR),q.ravel(),method="RK45",
                             t_eval=times/YEAR,rtol=tolerance,atol=1e-15)
        if not solution.success or solution.t[-1] != times[-1]/YEAR:
            raise RuntimeError(solution.message)
        value = solution.y.T.reshape(len(times),count,6)
        value[:,:,:3] *= AU; value[:,:,3:] *= AU/YEAR
        results.append(value)
        print("Independent RK45",tolerance,"finished",flush=True)
    consistency = errors(results[-2],results[-1])["maximum_position_metres"]
    if not np.isfinite(consistency) or consistency > 10:
        raise RuntimeError(f"Independent reference not converged: {consistency} m")
    return results[-1],consistency


def sample(initial,origin,times,figures,*,rtol=1e-13):
    state = create_experiment(initial,Settings(3600,integrator="dop853",physics="eih-1pn",
                                               figures=figures,rtol=rtol),origin=origin)
    e0 = model_invariants(initial,"eih-1pn",figures)[0]
    result, max_budget, max_raw = [],0.,0.
    for time in times:
        if time > state.time:
            state = advance(replace(state,settings=replace(state.settings,dt=float(time-state.time))),1)
        result.append(states(state.bodies))
        energy = model_invariants(state.bodies,"eih-1pn",figures,state.time)[0]
        max_budget = max(max_budget,abs((energy-state.orientation_work-e0)/e0))
        max_raw = max(max_raw,abs((energy-e0)/e0))
    return np.array(result),dict(maximum_relative_energy_budget_residual=max_budget,
        maximum_relative_raw_energy_change=max_raw, final_orientation_work_joules=state.orientation_work)


def main():
    source = Path("docs/solar-system-moon-reference.json")
    doc = json.loads(source.read_text())
    initial,origin = solar_system(resolved_moon=True)
    epochs = doc["epochs_jd_tdb"]
    times = (np.array(epochs)-origin.epoch_jd_tdb)*86400
    if (doc["dataset_sha256"] != origin.dataset_sha256 or doc["frame"] != origin.frame
            or doc["center"] != origin.center or doc["ephemeris"] != origin.ephemeris
            or doc["units"] != "SI" or [b["id"] for b in doc["bodies"]] != [399,301,3]
            or len(times) != 45 or times[0] != 0 or times[-1] != YEAR or np.any(np.diff(times)<=0)
            or any([s["jd_tdb"] for s in b["states"]] != epochs for b in doc["bodies"])):
        raise ValueError("Reference does not match the pinned 45-epoch benchmark")
    expected = np.stack([np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in doc["bodies"]],axis=1)
    figures = earth_moon_quadrupoles(initial,origin)
    variants = {"fixed_earth_j2":earth_j2(initial,origin),
                "moving_earth_j2":figures[:1],
                "earth_and_moon_j2":(figures[0],replace(figures[1],c22=0.)),
                "earth_and_moon_j2_c22":figures}
    comparisons = {}
    for name,params in variants.items():
        actual,diagnostics = sample(initial,origin,times,params)
        comparisons[name] = dict(pair=pair_errors(actual,expected,initial,times),**diagnostics)
        print(name,comparisons[name]["pair"]["moon_relative_to_earth"],flush=True)
    tighter,_ = sample(initial,origin,times,figures,rtol=3e-14)
    reference,consistency = independent_reference(initial,figures,times)
    numerical = [dict(name=b.name,agreement=errors(actual[:,i],reference[:,i])) for i,b in enumerate(initial)]
    passed = all(row["agreement"]["maximum_position_metres"]<10
                 and row["agreement"]["maximum_velocity_m_per_s"]<1e-4 for row in numerical)
    report = dict(physics="eih-1pn + prescribed Earth/Moon J2/C22",epoch_jd_tdb=origin.epoch_jd_tdb,
        duration_seconds=YEAR,samples=len(times),dataset_sha256=origin.dataset_sha256,
        reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),profile_sha256=PROFILE_SHA256,
        independent_reference_position_consistency_metres=consistency,numerical_agreement=numerical,
        tolerance_sensitivity=errors(actual,tighter),comparisons=comparisons,checks_passed=passed,
        tighter_tolerance_pair=pair_errors(tighter,expected,initial,times),
        limitation="45 sampled epochs, not a global bound. Lunar orientation is prescribed from DE441 and therefore this is a conditional translational validation, not an autonomous spin prediction. Earth precession and dominant nutation omit fitted frame bias. No tides, time-dependent gravity coefficients, higher harmonics, asteroids, quadrupole/quadrupole or mixed 1PN/figure terms.")
    Path("docs/orientation-validation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("checks_passed",passed,"consistency/m",consistency,"tolerance",report["tolerance_sensitivity"],flush=True)
    if not passed:
        raise RuntimeError("Orientation numerical agreement targets failed")


if __name__ == "__main__":
    main()
