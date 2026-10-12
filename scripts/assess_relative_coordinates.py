"""Check solver conditioning without changing the force model or fitting JPL."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from scipy.integrate import solve_ivp

from solar_simulator.ephemerides import solar_system
from solar_simulator.oblateness import earth_moon_quadrupoles
from solar_simulator.orientation import PROFILE_SHA256
from solar_simulator.relativity import C
from solar_simulator.simulation import AU,G

REFERENCE_SHA256 = "07717d8792d4afa297441a0b1751672de4bc492f41802d9224525f905e15bd24"

if __package__:
    from .assess_orientation import independent_figure_acceleration,sample
    from .assess_oblateness import pair_errors
    from .assess_relativity import YEAR,independent_acceleration
    from .assess_resolved_moon import errors,states
else:
    from assess_orientation import independent_figure_acceleration,sample
    from assess_oblateness import pair_errors
    from assess_relativity import YEAR,independent_acceleration
    from assess_resolved_moon import errors,states


def relative_states(values,initial):
    names = [b.name for b in initial]
    return values[:,names.index("Moon")]-values[:,names.index("Earth")]


def independent_reference(initial,figures,times,*,levels=((1e-12,3600.),(1e-13,1800.),(3e-14,900.)),cache_name="relative-reference-progress",acceleration_function=None,figure_acceleration_function=None):
    """RK45, SI->AU/year, interleaved six-vectors, independently mapped pair.

    Uses scalar EIH and body-frame analytic quadrupole forces; never calls the
    production coordinate class, force, or DOP853 integrator.
    """
    names = [b.name for b in initial]
    acceleration_function = acceleration_function or independent_acceleration
    figure_acceleration_function = figure_acceleration_function or independent_figure_acceleration
    e,m = names.index("Earth"),names.index("Moon")
    fraction = initial[m].mass/(initial[e].mass+initial[m].mass)
    q = states(initial)
    delta = q[m]-q[e]
    q[e] += fraction*delta
    q[m] = delta
    q[:,:3] /= AU; q[:,3:] *= YEAR/AU
    mu = np.array([G*b.mass*YEAR**2/AU**3 for b in initial])
    def rhs(t,y):
        state = y.reshape(len(initial),6)
        absolute = state.copy()
        absolute[e] = state[e]-fraction*state[m]
        absolute[m] = state[e]+(1-fraction)*state[m]
        relative_pair = (e,m,state[m,:3])
        a = acceleration_function(absolute[:,:3],absolute[:,3:],mu,C*YEAR/AU,relative_pair)
        a += figure_acceleration_function(absolute[:,:3],mu,figures,names,t*YEAR,relative_pair)
        relative_a = a[m]-a[e]
        a[e] = (1-fraction)*a[e]+fraction*a[m]
        a[m] = relative_a
        return np.concatenate((state[:,3:],a),axis=1).ravel()
    results = []
    for tolerance,maximum_step in levels:
        solution = solve_ivp(rhs,(0,times[-1]/YEAR),q.ravel(),method="RK45",t_eval=times/YEAR,
                             rtol=tolerance,atol=1e-17,max_step=maximum_step/YEAR)
        if not solution.success or solution.t[-1] != times[-1]/YEAR:
            raise RuntimeError(solution.message)
        internal = solution.y.T.reshape(len(times),len(initial),6)
        value = internal.copy()
        value[:,e] = internal[:,e]-fraction*internal[:,m]
        value[:,m] = internal[:,e]+(1-fraction)*internal[:,m]
        value[:,:,:3] *= AU; value[:,:,3:] *= AU/YEAR
        results.append(value)
        print("Independent relative RK45",tolerance,"max step",maximum_step,"finished",flush=True)
        Path(".tools").mkdir(exist_ok=True)
        np.savez_compressed(Path(".tools")/(cache_name+".npz"),times=times,
                            **{f"level_{i}":value for i,value in enumerate(results)})
    convergence = dict(all_bodies=errors(results[-2],results[-1]),
        moon_relative_to_earth=errors(relative_states(results[-2],initial),relative_states(results[-1],initial)))
    if (convergence["all_bodies"]["maximum_position_metres"]>1
            or convergence["moon_relative_to_earth"]["maximum_position_metres"]>.1):
        raise RuntimeError(f"Relative reference not converged: {convergence}")
    return results[-1],convergence


def main():
    source = Path("docs/solar-system-moon-reference.json")
    if hashlib.sha256(source.read_bytes()).hexdigest() != REFERENCE_SHA256:
        raise ValueError("The pinned JPL validation data changed")
    doc = json.loads(source.read_text())
    initial,origin = solar_system(resolved_moon=True)
    epochs = doc["epochs_jd_tdb"]
    times = (np.array(epochs)-origin.epoch_jd_tdb)*86400
    if (doc["dataset_sha256"]!=origin.dataset_sha256 or doc["frame"]!=origin.frame
            or doc["center"]!=origin.center or doc["ephemeris"]!=origin.ephemeris
            or doc["units"]!="SI" or [b["id"] for b in doc["bodies"]]!=[399,301,3]
            or len(times)!=45 or times[0]!=0 or times[-1]!=YEAR or np.any(np.diff(times)<=0)
            or any([s["jd_tdb"] for s in b["states"]]!=epochs for b in doc["bodies"])):
        raise ValueError("Reference does not match the pinned benchmark")
    expected = np.stack([np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in doc["bodies"]],axis=1)
    figures = earth_moon_quadrupoles(initial,origin)
    variants = {"cartesian":dict(),"cartesian_tighter":dict(rtol=3e-14),
        "relative_pair":dict(relative_pair=("Earth","Moon")),
        "relative_pair_rtol_tighter":dict(relative_pair=("Earth","Moon"),rtol=3e-14),
        "relative_pair_all_tighter":dict(relative_pair=("Earth","Moon"),rtol=3e-14,
                                          position_atol=2.5e-4,velocity_atol=2.5e-10),
        "relative_pair_strict":dict(relative_pair=("Earth","Moon"),position_atol=1e-5,velocity_atol=1e-11),
        "relative_pair_strict_rtol":dict(relative_pair=("Earth","Moon"),rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11),
        "relative_pair_stricter":dict(relative_pair=("Earth","Moon"),rtol=3e-14,position_atol=1e-6,velocity_atol=1e-12)}
    measured,data = {},{}
    for name,options in variants.items():
        start = time.perf_counter()
        actual,diagnostics = sample(initial,origin,times,figures,**options)
        measured[name] = dict(pair=pair_errors(actual,expected,initial,times),**diagnostics,
                             elapsed_seconds=time.perf_counter()-start,options=options)
        data[name] = actual
        print(name,measured[name]["pair"]["moon_relative_to_earth"],flush=True)
    reference,convergence = independent_reference(initial,figures,times)
    write_report(initial,origin,times,source,measured,data,reference,convergence)


def write_report(initial,origin,times,source,measured,data,reference,convergence):
    """Assemble measurements; the strict mode is the recommended pair preset."""
    actual = data["relative_pair_strict"]
    numerical = [dict(name=b.name,agreement=errors(actual[:,i],reference[:,i])) for i,b in enumerate(initial)]
    agreement = errors(relative_states(actual,initial),relative_states(reference,initial))
    def sensitivity(a,b):
        return dict(all_bodies=errors(data[a],data[b]),
                    moon_relative_to_earth=errors(relative_states(data[a],initial),relative_states(data[b],initial)))
    passed = (convergence["all_bodies"]["maximum_position_metres"]<1
              and convergence["moon_relative_to_earth"]["maximum_position_metres"]<.1
              and all(row["agreement"]["maximum_position_metres"]<1
                  and row["agreement"]["maximum_velocity_m_per_s"]<1e-6 for row in numerical)
              and agreement["maximum_position_metres"]<.1)
    report = dict(physics="eih-1pn + prescribed Earth/Moon J2/C22",epoch_jd_tdb=origin.epoch_jd_tdb,
        duration_seconds=YEAR,samples=len(times),dataset_sha256=origin.dataset_sha256,
        reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),profile_sha256=PROFILE_SHA256,
        recommended_variant="relative_pair_strict",
        independent_method="RK45, AU/year, interleaved pair variables; scalar EIH and principal-axis J2/C22; rtol 1e-12/1e-13/3e-14, atol 1e-17, maximum steps 3600/1800/900 seconds",
        independent_reference_convergence=convergence,numerical_agreement=numerical,
        moon_relative_numerical_agreement=agreement,variants=measured,
        cartesian_tolerance_sensitivity=sensitivity("cartesian","cartesian_tighter"),
        relative_rtol_sensitivity=sensitivity("relative_pair","relative_pair_rtol_tighter"),
        relative_all_tolerance_sensitivity=sensitivity("relative_pair","relative_pair_all_tighter"),
        strict_rtol_sensitivity=sensitivity("relative_pair_strict","relative_pair_strict_rtol"),
        strict_all_tolerance_sensitivity=sensitivity("relative_pair_strict","relative_pair_stricter"),
        default_pair_numerical_agreement=errors(relative_states(data["relative_pair"],initial),relative_states(reference,initial)),
        checks_passed=passed,limitation="Only numerical coordinates changed; same physical equations and prescribed DE441 orientation. Local tolerances are applied to the internal pair/centre variables, not separate absolute Earth/Moon states. Results at 45 sampled epochs; no global error bound or complete autonomous spin/tidal model.")
    Path("docs/relative-coordinates-validation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    Path(".tools").mkdir(exist_ok=True)
    np.savez_compressed(".tools/relative-coordinate-states.npz",times=times,reference=reference,**data)
    print("checks_passed",passed,"agreement",agreement,"convergence",convergence,flush=True)
    if not passed:
        raise RuntimeError("Relative-coordinate numerical agreement targets failed")


if __name__ == "__main__":
    main()
