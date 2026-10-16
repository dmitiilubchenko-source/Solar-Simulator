"""Qualify the ready ten-body profile through actual bounded time packets."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_sandbox_models import (SOURCE_NAMES, load_inputs, jpl_errors,
    independent_reference, load_oracle, figure_reference)
from scripts.assess_sandbox_planets import errors, states
from solar_simulator.application_profiles import solar_sandbox
from solar_simulator.diagnostics import model_invariants
from solar_simulator.time_control import advance_towards

ROOT=Path(__file__).resolve().parents[1]
NAMES=list(dict.fromkeys(SOURCE_NAMES+["scripts/assess_sandbox_demo.py",
    "src/solar_simulator/application_profiles.py","src/solar_simulator/time_control.py"]))


def hashes():
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in NAMES}


def sample(times,backend):
    state=solar_sandbox(backend=backend); settings=state.settings
    e0,_,_=model_invariants(state.bodies,settings.physics,settings.figures)
    values=[]; packets=0; energy_error=0.
    start=perf_counter()
    for target in times:
        while state.time < target:
            state=advance_towards(state,float(target),20); packets+=1
            assert state.settings == settings and not state.halted
            energy,_,_=model_invariants(state.bodies,settings.physics,settings.figures)
            energy_error=max(energy_error,abs(energy-e0)/abs(e0))
        assert state.time == target
        values.append(states(state.bodies))
    return np.array(values),dict(wall_seconds=perf_counter()-start,packets=packets,
        relative_energy_drift=energy_error,exact_epochs=True,settings_preserved=True)


def main():
    source_hashes=hashes()
    initial,origin,times,base,moon=load_inputs()
    profile=solar_sandbox(); names=[b.name for b in initial]
    assert profile.origin == origin and np.array_equal(states(profile.initial),states(initial))
    assert [b.mass for b in profile.initial] == [b.mass for b in initial]
    assert [b.name for b in profile.initial] == names
    prior_path=ROOT/"docs/sandbox-models-validation.json"
    prior=json.loads(prior_path.read_bytes())
    before=next(row for row in prior["results"] if row["name"]=="eih-solar-earth-j2")
    assert profile.settings.physics == before["physics"] and profile.settings.dt == 3600
    assert json.loads(json.dumps([asdict(f) for f in profile.settings.figures])) == before["figures"]
    for name,digest in prior["source_sha256"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError("Changed qualification source: "+name)
    actual={}; timings={}
    for backend in ("python","rust"):
        actual[backend],timings[backend]=sample(times,backend)
        print(backend,timings[backend],flush=True)
    oracle=load_oracle(); start=perf_counter()
    reference,convergence=independent_reference(initial,profile.settings.figures,times,
        levels=((1e-13,1800.),(3e-14,900.)),cache_name="sandbox-demo-124",
        acceleration_function=oracle,figure_acceleration_function=figure_reference)
    reference_wall=perf_counter()-start
    results={}; e,m=names.index("Earth"),names.index("Moon")
    for backend,values in actual.items():
        numeric={name:errors(values[:,i],reference[:,i]) for i,name in enumerate(names)}
        relative_numeric=errors(values[:,m]-values[:,e],reference[:,m]-reference[:,e])
        residuals,lunar=jpl_errors(values,names,moon["epochs_jd_tdb"],base,moon)
        physical={name:row["position_metres"]<10000 for name,row in residuals.items()}
        physical["Moon-relative"]=lunar["position_metres"]<1000
        numerical=(all(row["position_metres"]<10 and row["velocity_m_per_s"]<1e-4 for row in numeric.values())
                   and relative_numeric["position_metres"]<.1 and relative_numeric["velocity_m_per_s"]<1e-5)
        results[backend]=dict(production=timings[backend],numerical_errors=numeric,
            relative_numerical_error=relative_numeric,jpl_residuals=residuals,moon_relative_jpl=lunar,
            before_production=before["production"][backend],before_jpl=before["results"][backend]["jpl_residuals"],
            before_moon_relative_jpl=before["results"][backend]["moon_relative_jpl"],
            physical_goal_checks=physical,numerical_checks_passed=numerical,
            invariant_checks_passed=timings[backend]["relative_energy_drift"]<1e-10,
            physical_goals_passed=all(physical.values()))
    if hashes()!=source_hashes:raise RuntimeError("Sources changed during propagation")
    import scipy,platform
    report=dict(protocol="docs/sandbox-demo-protocol.md",source_sha256=source_hashes,
        before_report_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        origin=asdict(origin),settings=asdict(profile.settings),batch=20,
        duration_seconds=float(times[-1]),epochs_jd_tdb=moon["epochs_jd_tdb"],units="SI",
        reference_convergence=convergence,reference_wall_seconds=reference_wall,
        versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
        results=results,python_rust_difference=errors(actual["python"],actual["rust"]),
        checks_passed=all(r["numerical_checks_passed"] and r["invariant_checks_passed"]
                          and r["physical_goals_passed"] for r in results.values()),
        limitations="45/13 epochs and original ten-body initial state only. Packet diagnostics included, Tk rendering excluded; timings are single observations, not a speedup comparison. Fixed J2 axes exchange orbital angular momentum; no tides, full rotation, asteroids or mixed PN-figure terms.")
    (ROOT/"docs/sandbox-demo-validation.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2,allow_nan=False))
    if not report["checks_passed"]:raise RuntimeError("Predeclared demo criteria failed")


if __name__ == "__main__":main()
