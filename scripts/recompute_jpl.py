"""Free one-year production propagation, distinct from saved-trajectory replay."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
from time import perf_counter

import numpy as np


def recompute(bundle):
    bundle = Path(bundle).resolve()
    spec = importlib.util.spec_from_file_location("sealed_jpl_replay",bundle/"replay_jpl.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    replay = checker.replay(bundle)
    from solar_simulator.storage import load
    from solar_simulator.time_control import advance_towards
    from solar_simulator.diagnostics import model_invariants
    import solar_simulator
    strict = checker.read_json(bundle/"strict-report.json")
    package = Path(solar_simulator.__file__).resolve().parent
    sources = {}
    for name,digest in strict["source_sha256"].items():
        if name.startswith("src/solar_simulator/"):
            path = package/name[len("src/solar_simulator/"):]
            checker.require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, "Runtime scientific source changed: "+name)
            sources[name] = digest
    state = load(bundle/"initial.json")
    settings = state.settings
    reference = checker.read_json(bundle/"reference.json")
    trajectories = checker.read_json(bundle/"trajectories.json")
    epochs = reference["epochs_jd_tdb"]
    times = (np.array(epochs)-state.origin.epoch_jd_tdb)*86400
    expected = np.array([[row["position"]+row["velocity"] for row in body["states"]]
        for body in reference["bodies"]]).transpose(1,0,2)
    stored = np.asarray(trajectories["profiles"]["rust_tighter"])
    energy0,_,_ = model_invariants(state.initial,settings.physics,settings.figures)
    values = []
    packets = 0
    energy_residual = 0.
    start = perf_counter()
    for target in times:
        while state.time < target:
            state = advance_towards(state,float(target),20)
            packets += 1
            checker.require(state.settings == settings and not state.halted, "Unexpected solver settings or stop")
        checker.require(state.time == target, "Target time mismatch")
        values.append([[b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z] for b in state.bodies])
        energy,_,_ = model_invariants(state.bodies,settings.physics,settings.figures)
        energy_residual = max(energy_residual,abs(energy-energy0)/abs(energy0))
    elapsed = perf_counter()-start
    actual = np.array(values)
    rows = {}
    for index,name in enumerate(checker.NAMES):
        physical,_ = checker.maximum_error(actual[:,index],expected[:,index])
        reproduction,_ = checker.maximum_error(actual[:,index],stored[:,index])
        rows[name] = dict(jpl_residual=physical,stored_difference=reproduction)
    lunar,_ = checker.maximum_error(actual[:,4]-actual[:,3],expected[:,4]-expected[:,3])
    lunar_reproduction,_ = checker.maximum_error(actual[:,4]-actual[:,3],stored[:,4]-stored[:,3])
    physical_ok = all(row["jpl_residual"]["position_metres"] < 10000 for row in rows.values()) and lunar["position_metres"] < 1000
    reproduction_ok = (all(row["stored_difference"]["position_metres"] < .1 and
        row["stored_difference"]["velocity_m_per_s"] < 1e-5 for row in rows.values()) and
        lunar_reproduction["position_metres"] < .1 and lunar_reproduction["velocity_m_per_s"] < 1e-5)
    import platform,scipy
    return dict(checks_passed=physical_ok and reproduction_ok,physical_goals_passed=physical_ok,
        stored_reproduction_passed=reproduction_ok,solver_executed=True,samples=len(times),packets=packets,
        duration_seconds=state.time,wall_seconds=elapsed,results=rows,moon_relative_jpl=lunar,
        moon_relative_stored_difference=lunar_reproduction,energy_residual=energy_residual,
        runtime_source_sha256=sources,manifest_sha256=replay["manifest_sha256"],
        versions=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
        limitations="Fresh production propagation at qualified settings; RK45 independence belongs to earlier audit141. FixedJ2 exchanges orbital angular momentum; EIH+J2 omits mixed terms. Sampled JPL goals, no continuous guarantee.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle",type=Path)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    output = args.output or args.bundle.resolve().parent/f"physics-verification-{datetime.now():%Y%m%d-%H%M%S}.json"
    if output.exists():raise FileExistsError("Preserve previous result")
    if output.resolve().is_relative_to(args.bundle.resolve()):raise ValueError("Output must stay outside sealed bundle")
    result = recompute(args.bundle)
    with output.open("x",encoding="utf-8",newline="\n") as stream:
        stream.write(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))
    if not result["checks_passed"]:raise RuntimeError("Physics verification failed; report preserved")


if __name__ == "__main__":main()
