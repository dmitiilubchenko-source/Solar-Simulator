"""Predeclared ten-body Newton baseline: numerical error versus JPL residuals."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from solar_simulator.ephemerides import solar_system, RESOLVED_NAMES, EXPECTED_IDS
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.storage import to_document

if __package__:
    from .assess_solar_system import independent_reference, YEAR
else:
    from assess_solar_system import independent_reference, YEAR

ROOT = Path(__file__).resolve().parents[1]


def states(bodies):
    return np.array([[b.position.x,b.position.y,b.position.z,
                      b.velocity.x,b.velocity.y,b.velocity.z] for b in bodies])


def errors(a, b):
    delta = a-b
    return dict(position_metres=float(np.linalg.norm(delta[..., :3], axis=-1).max()),
                velocity_m_per_s=float(np.linalg.norm(delta[..., 3:], axis=-1).max()))


def sample(initial, origin, times, backend, rtol):
    experiment = create_experiment(initial, Settings(3600, backend=backend, integrator="dop853",
        relative_pair=("Earth", "Moon"), rtol=rtol), origin=origin)
    before = to_document(experiment)
    values = [states(initial)]
    start = perf_counter()
    for duration in np.diff(times):
        experiment = advance(replace(experiment, settings=replace(experiment.settings, dt=float(duration))), 1)
        values.append(states(experiment.bodies))
    elapsed = perf_counter()-start
    assert states(initial).tolist() == [b["position"]+b["velocity"] for b in before["initial"]]
    return np.array(values), elapsed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"docs/sandbox-planets-validation.json")
    args = parser.parse_args()
    initial, origin = solar_system(resolved_moon=True)
    assert tuple(b.name for b in initial) == RESOLVED_NAMES
    base_initial, base_origin = solar_system()
    base_path = ROOT/"docs/solar-system-reference.json"
    moon_path = ROOT/"docs/solar-system-moon-reference.json"
    base, moon = json.loads(base_path.read_bytes()), json.loads(moon_path.read_bytes())
    if (base["dataset_sha256"] != base_origin.dataset_sha256
            or moon["dataset_sha256"] != origin.dataset_sha256
            or moon["gm_sha256"] != origin.gm_sha256
            or moon["base_dataset_sha256"] != base_origin.dataset_sha256
            or moon["base_reference_sha256"] != hashlib.sha256(base_path.read_bytes()).hexdigest()
            or [b["id"] for b in base["bodies"]] != list(EXPECTED_IDS)
            or [b["id"] for b in moon["bodies"]] != [399, 301, 3]):
        raise ValueError("Reference lineage does not match the pinned initial conditions")
    for document in (base, moon):
        if any(document[k] != getattr(origin, k) for k in ("frame", "center", "ephemeris")) or document["units"] != "SI":
            raise ValueError("Reference frame/time/units mismatch")
        if any([s["jd_tdb"] for s in b["states"]] != document["epochs_jd_tdb"] for b in document["bodies"]):
            raise ValueError("Reference epochs mismatch")
    times = (np.array(moon["epochs_jd_tdb"])-origin.epoch_jd_tdb)*86400
    if len(times) != 45 or times[0] != 0 or times[-1] != YEAR or np.any(np.diff(times) <= 0):
        raise ValueError("Expected 45 ordered epochs over one Julian year")
    names = [b.name for b in initial]
    earth, lunar = names.index("Earth"), names.index("Moon")
    if abs(initial[earth].mass+initial[lunar].mass-base_initial[3].mass)/base_initial[3].mass > 2e-15:
        raise ValueError("Earth/Moon GM double-count or mismatch")
    start = perf_counter()
    reference, consistency = independent_reference(initial, times)
    reference_wall = perf_counter()-start
    annual = [moon["epochs_jd_tdb"].index(t) for t in base["epochs_jd_tdb"]]
    moon_expected = {b["name"]:np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in moon["bodies"]}
    base_expected = {b["name"]:np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in base["bodies"]}
    rows = []
    for backend in ("python", "rust"):
        actual, wall = sample(initial, origin, times, backend, 1e-13)
        tighter, tight_wall = sample(initial, origin, times, backend, 3e-14)
        numeric = {name:errors(actual[:, i], reference[:, i]) for i, name in enumerate(names)}
        residuals = {}
        for i, name in enumerate(names):
            if name in ("Earth", "Moon"):
                residuals[name] = errors(actual[:, i], moon_expected[name])
            else:
                residuals[name] = errors(actual[annual, i], base_expected[name])
        relative = actual[:, lunar]-actual[:, earth]
        relative_expected = moon_expected["Moon"]-moon_expected["Earth"]
        passed = consistency < 100 and all(v["position_metres"] < 100 and v["velocity_m_per_s"] < 1e-3 for v in numeric.values())
        rows.append(dict(backend=backend, numerical_errors=numeric, jpl_residuals=residuals,
            earth_moon_relative_jpl=errors(relative, relative_expected),
            tolerance_sensitivity=errors(actual, tighter), wall_seconds=wall,
            tighter_wall_seconds=tight_wall, checks_passed=passed))
    source_names = ["scripts/assess_sandbox_planets.py", "scripts/assess_solar_system.py",
        "src/solar_simulator/experiment.py", "src/solar_simulator/accuracy.py",
        "src/solar_simulator/coordinates.py", "src/solar_simulator/error_control.py"]
    report = dict(protocol="docs/sandbox-validation-protocol.md", origin=asdict(origin), units="SI",
        physics="newtonian-point-masses", duration_seconds=YEAR, samples=45,
        epochs_jd_tdb=moon["epochs_jd_tdb"], settings=dict(rtol=1e-13, tighter_rtol=3e-14,
        position_atol=1e-3, velocity_atol=1e-9, relative_pair=["Earth", "Moon"], error_control="per-body"),
        reference_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (base_path, moon_path)},
        source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names},
        independent_reference_position_consistency_metres=consistency,
        independent_reference_wall_seconds=reference_wall, results=rows,
        checks_passed=all(row["checks_passed"] for row in rows),
        limitations="45 epochs, only 13 for planets other than Earth/Moon. Newton point masses omit EIH, J2/Q2, tides, asteroids and other resolved moons. RK45 reference is float64 and has finite sensitivity. JPL differences are model residuals, not integrator error or observational uncertainty. Single wall-time observations, not speedup benchmarks.")
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    if not report["checks_passed"]: raise RuntimeError("Predeclared ten-body numerical criteria failed")


if __name__ == "__main__":
    main()
