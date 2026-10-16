"""Controlled Newton/EIH/fixed-J2 qualification, preserving failed physical goals."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter

import numpy as np
import scipy

from solar_simulator.diagnostics import model_invariants
from solar_simulator.ephemerides import solar_system, RESOLVED_NAMES, EXPECTED_IDS
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.oblateness import solar_j2, earth_j2

if __package__:
    from .assess_sandbox_planets import errors, states, YEAR
    from .assess_relative_coordinates import independent_reference, REFERENCE_SHA256
    from .assess_solar_j2 import PLANET_REFERENCE_SHA256
    from .independent_eih_rust import load_oracle
    from .independent_figure_vector import acceleration as figure_reference
else:
    from assess_sandbox_planets import errors, states, YEAR
    from assess_relative_coordinates import independent_reference, REFERENCE_SHA256
    from assess_solar_j2 import PLANET_REFERENCE_SHA256
    from independent_eih_rust import load_oracle
    from independent_figure_vector import acceleration as figure_reference

ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAMES = ["scripts/assess_sandbox_models.py", "scripts/assess_relative_coordinates.py",
    "scripts/assess_sandbox_planets.py", "scripts/assess_solar_j2.py", "scripts/assess_relativity.py",
    "scripts/validation/eih_scalar.rs", "scripts/independent_eih_rust.py", "scripts/independent_figure_vector.py",
    "src/solar_simulator/experiment.py", "src/solar_simulator/accuracy.py",
    "src/solar_simulator/coordinates.py", "src/solar_simulator/error_control.py",
    "src/solar_simulator/relativity.py", "src/solar_simulator/oblateness.py",
    "src/solar_simulator/native_forces.py", "rust/solar_core/src/relativity.rs"]


def source_hashes():
    return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCE_NAMES}


def load_inputs():
    initial, origin = solar_system(resolved_moon=True)
    _, base_origin = solar_system()
    paths = [ROOT/"docs/solar-system-reference.json", ROOT/"docs/solar-system-moon-reference.json"]
    for path, digest in zip(paths, (PLANET_REFERENCE_SHA256, REFERENCE_SHA256)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Changed pinned JPL benchmark")
    base, moon = [json.loads(p.read_bytes()) for p in paths]
    if (tuple(b.name for b in initial) != RESOLVED_NAMES
            or base["dataset_sha256"] != base_origin.dataset_sha256
            or base_origin.gm_sha256 != origin.gm_sha256 or moon["gm_sha256"] != origin.gm_sha256
            or moon["dataset_sha256"] != origin.dataset_sha256
            or moon["base_dataset_sha256"] != base_origin.dataset_sha256
            or moon["base_reference_sha256"] != PLANET_REFERENCE_SHA256
            or [b["id"] for b in base["bodies"]] != list(EXPECTED_IDS)
            or [b["id"] for b in moon["bodies"]] != [399, 301, 3]):
        raise ValueError("Mismatched pinned JPL lineage")
    for doc in (base, moon):
        if doc["units"] != "SI" or any(doc[k] != getattr(origin, k) for k in ("frame", "center", "ephemeris")):
            raise ValueError("Mismatched benchmark frame/units")
        if any([s["jd_tdb"] for s in b["states"]] != doc["epochs_jd_tdb"] for b in doc["bodies"]):
            raise ValueError("Mismatched benchmark epochs")
    times = (np.array(moon["epochs_jd_tdb"])-origin.epoch_jd_tdb)*86400
    if len(times) != 45 or times[0] != 0 or times[-1] != YEAR or np.any(np.diff(times) <= 0):
        raise ValueError("Expected 45 ordered epochs across one year")
    return initial, origin, times, base, moon


def independent_newton(p, v, mu, c, pair=None):
    """Full matrix, source-to-target directions; does not call runtime forces."""
    delta = p[None, :, :]-p[:, None, :]
    if pair:
        first, second, rho = pair
        delta[first, second], delta[second, first] = rho, -rho
    distance = np.linalg.norm(delta, axis=2)
    np.fill_diagonal(distance, np.inf)
    return np.sum(delta*(mu[None, :]/distance**3)[:, :, None], axis=1)


def sample(initial, origin, times, physics, figures, backend, rtol):
    experiment = create_experiment(initial, Settings(3600, backend=backend,
        integrator="dop853", physics=physics, figures=figures,
        relative_pair=("Earth", "Moon"), rtol=rtol), origin=origin)
    energy0, momentum0, angular0 = model_invariants(initial, physics, figures)
    p_scale = sum(b.mass*b.velocity.magnitude() for b in initial)
    values, energy_error, momentum_error, angular_error = [], 0., 0., 0.
    start = perf_counter()
    for time in times:
        if time > experiment.time:
            experiment = advance(replace(experiment, settings=replace(experiment.settings,
                dt=float(time-experiment.time))), 1)
        values.append(states(experiment.bodies))
        energy, momentum, angular = model_invariants(experiment.bodies, physics, figures)
        energy_error = max(energy_error, abs(energy-energy0)/abs(energy0))
        momentum_error = max(momentum_error, momentum.distance_to(momentum0)/p_scale)
        angular_error = max(angular_error, angular.distance_to(angular0)/angular0.magnitude())
    return np.array(values), dict(wall_seconds=perf_counter()-start,
        relative_energy_drift=energy_error, scaled_momentum_drift=momentum_error,
        relative_orbital_angular_momentum_change=angular_error,
        angular_conservation_expected=not figures,
        scope="Noether E/P/J through 1PN plus Newtonian fixed figure potential; mixed PN-figure terms absent" if physics=="eih-1pn" else "Newtonian E/P/J")


def jpl_errors(actual, names, epochs, base, moon):
    annual = [epochs.index(t) for t in base["epochs_jd_tdb"]]
    moon_expected = {b["name"]:np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in moon["bodies"]}
    base_expected = {b["name"]:np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in base["bodies"]}
    result = {}
    for i, name in enumerate(names):
        result[name] = errors(actual[:, i], moon_expected[name]) if name in ("Earth", "Moon") else errors(actual[annual, i], base_expected[name])
    e, m = names.index("Earth"), names.index("Moon")
    relative = errors(actual[:, m]-actual[:, e], moon_expected["Moon"]-moon_expected["Earth"])
    return result, relative


def assess(name, physics, figures, initial, origin, times, base, moon, oracle):
    print("Start", name, flush=True)
    values, production = {}, {}
    for backend, rtol in (("python",1e-13),("rust",1e-13),("rust_tighter",3e-14)):
        values[backend], production[backend] = sample(initial, origin, times, physics, figures,
            "rust" if backend.startswith("rust") else "python", rtol)
        print(name, backend, production[backend]["wall_seconds"], flush=True)
    start = perf_counter()
    reference, convergence = independent_reference(initial, figures, times,
        levels=((1e-13,1800.),(3e-14,900.)), cache_name="sandbox-models-121-"+name,
        acceleration_function=independent_newton if physics=="newtonian" else oracle,
        figure_acceleration_function=figure_reference)
    reference_wall = perf_counter()-start
    names = [b.name for b in initial]
    e, m = names.index("Earth"), names.index("Moon")
    rows = {}
    for backend in ("python", "rust"):
        actual = values[backend]
        numeric = {b:errors(actual[:, i], reference[:, i]) for i, b in enumerate(names)}
        relative_numeric = errors(actual[:, m]-actual[:, e], reference[:, m]-reference[:, e])
        residuals, lunar_residual = jpl_errors(actual, names, moon["epochs_jd_tdb"], base, moon)
        invariant_ok = (production[backend]["relative_energy_drift"] < 1e-10
            and (bool(figures) or production[backend]["relative_orbital_angular_momentum_change"] < 1e-10))
        numerical_ok = (all(v["position_metres"] < 10 and v["velocity_m_per_s"] < 1e-4 for v in numeric.values())
            and relative_numeric["position_metres"] < .1 and relative_numeric["velocity_m_per_s"] < 1e-5)
        physical_checks = {b:v["position_metres"] < 10000 for b,v in residuals.items()}
        physical_checks["Moon-relative"] = lunar_residual["position_metres"] < 1000
        rows[backend] = dict(numerical_errors=numeric, relative_numerical_error=relative_numeric,
            jpl_residuals=residuals, moon_relative_jpl=lunar_residual,
            numerical_checks_passed=numerical_ok, invariant_checks_passed=invariant_ok,
            physical_goal_checks=physical_checks, physical_goals_passed=all(physical_checks.values()))
    sensitivity = errors(values["rust"], values["rust_tighter"])
    return dict(name=name, physics=physics, figures=[asdict(f) for f in figures],
        production=production, reference_convergence=convergence, reference_wall_seconds=reference_wall,
        python_rust_difference=errors(values["python"],values["rust"]),
        tolerance_sensitivity=sensitivity, results=rows,
        numerical_checks_passed=all(v["numerical_checks_passed"] and v["invariant_checks_passed"] for v in rows.values())), values["rust"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"docs/sandbox-models-validation.json")
    args = parser.parse_args()
    hashes = source_hashes()
    initial, origin, times, base, moon = load_inputs()
    sun, earth = solar_j2(initial, origin), earth_j2(initial, origin)
    profiles = [("newton", "newtonian", ()), ("eih", "eih-1pn", ()),
                ("eih-solar-j2", "eih-1pn", sun), ("eih-solar-earth-j2", "eih-1pn", sun+earth)]
    oracle = load_oracle()
    report = dict(protocol="docs/sandbox-models-protocol.md", origin=asdict(origin), units="SI",
        duration_seconds=YEAR, samples=45, epochs_jd_tdb=moon["epochs_jd_tdb"], source_sha256=hashes,
        oracle_sha256=oracle.source_sha256, compiler=oracle.compiler_version,
        reference_sha256=dict(planets=PLANET_REFERENCE_SHA256, moon=REFERENCE_SHA256),
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        settings=dict(integrator="dop853", rtol=1e-13, tighter_rtol=3e-14,
            position_atol=1e-3, velocity_atol=1e-9, error_control="per-body",
            relative_pair=["Earth", "Moon"], output_dt_seconds="exact epoch intervals"),
        reference_settings=dict(method="RK45", levels=[[1e-13,1800.],[3e-14,900.]], atol=1e-17,
            relative_coordinates="EMB plus Moon minus Earth, independently mapped AU/year"),
        physical_goals=dict(all_body_position_metres=10000., lunar_relative_position_metres=1000.,
                            status="approved for checking before runs; failures retained"),
        results=[], errors=[], limitations="Fixed axes, no coupled rotation/tides. No asteroids or other resolved moons. No mixed PN-figure terms. 45/13 epochs, not global physical error guarantees. No fitting. Timing includes diagnostics, single observations.")
    previous = None
    for name, physics, figures in profiles:
        try:
            result, actual = assess(name, physics, figures, initial, origin, times, base, moon, oracle)
            if previous is not None:
                result["increment_from_previous"] = {b.name:errors(actual[:,i],previous[:,i]) for i,b in enumerate(initial)}
            previous = actual
            report["results"].append(result)
        except Exception as error:
            report["errors"].append(dict(profile=name, type=type(error).__name__, message=str(error)))
            print(name, "FAILED", repr(error), flush=True)
        if source_hashes() != hashes:
            raise RuntimeError("Scientific sources changed during propagation")
        report["numerical_checks_passed"] = not report["errors"] and all(r["numerical_checks_passed"] for r in report["results"])
        report["physical_goals_passed_by_profile"] = {r["name"]:all(v["physical_goals_passed"] for v in r["results"].values()) for r in report["results"]}
        args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    if not report["numerical_checks_passed"]:
        raise RuntimeError("Numerical qualification failed; report preserved")
    print("Numerical criteria passed. Physical goals:",report["physical_goals_passed_by_profile"],flush=True)


if __name__ == "__main__":
    main()
