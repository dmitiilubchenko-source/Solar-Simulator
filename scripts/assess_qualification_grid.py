"""Dense numerical checks; JPL coverage is explicitly limited to available data."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.fetch_qualification_grid import epochs
from scripts.assess_sandbox_models import (SOURCE_NAMES, load_inputs, jpl_errors,
    independent_reference, load_oracle, figure_reference)
from scripts.assess_sandbox_planets import states, errors
from solar_simulator.application_profiles import solar_sandbox
from solar_simulator.diagnostics import model_invariants
from solar_simulator.time_control import advance_towards

ROOT = Path(__file__).resolve().parents[1]
SOURCES = list(dict.fromkeys(SOURCE_NAMES+["scripts/assess_qualification_grid.py",
    "scripts/fetch_qualification_grid.py", "src/solar_simulator/application_profiles.py",
    "src/solar_simulator/time_control.py"]))


def hashes():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}


def sample(times, backend, rtol=1e-13):
    state = solar_sandbox(backend=backend)
    state = replace(state, settings=replace(state.settings, rtol=rtol))
    settings = state.settings
    energy0, _, _ = model_invariants(state.initial, settings.physics, settings.figures)
    values = []
    drift = 0.
    packets = 0
    start = perf_counter()
    for target in times:
        while state.time < target:
            state = advance_towards(state, float(target), 20)
            packets += 1
            assert not state.halted and state.settings == settings
        assert state.time == target
        values.append(states(state.bodies))
        energy, _, _ = model_invariants(state.bodies, settings.physics, settings.figures)
        drift = max(drift, abs(energy-energy0)/abs(energy0))
    return np.array(values), dict(wall_seconds=perf_counter()-start, packets=packets,
        relative_energy_residual=drift, exact_times=True, settings_preserved=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError("Preserve prior audit")
    source_hashes = hashes()
    initial, origin, old_times, base, moon = load_inputs()
    grid = epochs()
    times = (np.array(grid)-origin.epoch_jd_tdb)*86400
    names = [b.name for b in initial]
    actual, timings = {}, {}
    for backend in ("python", "rust", "rust_tighter"):
        actual[backend], timings[backend] = sample(times, "rust" if backend.startswith("rust") else "python",
            3e-14 if backend == "rust_tighter" else 1e-13)
        print(backend, timings[backend], flush=True)
    cache = ROOT/".tools/qualification138/reference139.npz"
    if cache.exists():raise FileExistsError("Preserve old independent reference")
    oracle = load_oracle()
    reference, convergence = independent_reference(initial, solar_sandbox().settings.figures, times,
        levels=((1e-13,1800.),(3e-14,900.)), cache_name="qualification138/reference139",
        acceleration_function=oracle, figure_acceleration_function=figure_reference)
    e, m = names.index("Earth"), names.index("Moon")
    indices = [int(np.flatnonzero(times == t)[0]) for t in old_times]
    results = {}
    for backend in ("python", "rust"):
        values = actual[backend]
        numeric = {name:errors(values[:, i], reference[:, i]) for i, name in enumerate(names)}
        relative = errors(values[:, m]-values[:, e], reference[:, m]-reference[:, e])
        residuals, lunar = jpl_errors(values[indices], names, moon["epochs_jd_tdb"], base, moon)
        numerical = (all(row["position_metres"] < 10 and row["velocity_m_per_s"] < 1e-4 for row in numeric.values())
            and relative["position_metres"] < .1 and relative["velocity_m_per_s"] < 1e-5)
        physical = all(row["position_metres"] < 10000 for row in residuals.values()) and lunar["position_metres"] < 1000
        results[backend] = dict(numerical_errors=numeric, relative_numerical_error=relative,
            jpl_residuals_on_original_epochs=residuals, moon_relative_jpl_on_original_epochs=lunar,
            production=timings[backend], numerical_checks_passed=numerical,
            physical_checks_on_original_epochs_passed=physical,
            energy_check_passed=timings[backend]["relative_energy_residual"] < 1e-10)
    sensitivity = dict(all_bodies=errors(actual["rust"], actual["rust_tighter"]),
        moon_relative=errors(actual["rust"][:, m]-actual["rust"][:, e],
            actual["rust_tighter"][:, m]-actual["rust_tighter"][:, e]))
    sensitivity_ok = sensitivity["all_bodies"]["position_metres"] < 10 and sensitivity["moon_relative"]["position_metres"] < .1
    np.savez_compressed(ROOT/".tools/qualification138/production139.npz", times=times, **actual, reference=reference)
    assert hashes() == source_hashes
    report = dict(protocol="docs/qualification-extension-protocol.md", origin=asdict(origin),
        settings=asdict(solar_sandbox().settings), source_sha256=source_hashes, units="SI",
        epochs_jd_tdb=grid, duration_seconds=float(times[-1]), results=results,
        reference_convergence=convergence, sensitivity=sensitivity, sensitivity_check_passed=sensitivity_ok,
        independent_method="RK45 in AU/year, independent scalar EIH plus body-axis figures and EMB map",
        oracle_sha256=oracle.source_sha256, compiler=oracle.compiler_version,
        jpl_coverage=dict(new_epochs_checked=False, all_body_epochs=13, earth_moon_epochs=45,
            failure="curl(6) DNS resolution failed; alternate official site timed out; remote web API inaccessible"),
        reference_sha256={str(p.relative_to(ROOT).as_posix()):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/"docs/solar-system-reference.json", ROOT/"docs/solar-system-moon-reference.json", cache)},
        checks_passed=sensitivity_ok and all(r["numerical_checks_passed"] and
            r["physical_checks_on_original_epochs_passed"] and r["energy_check_passed"] for r in results.values()),
        limitations="Denser numerical grid is not new JPL coverage. Local sensitivity not a global error bound. Fixed axes and omitted PN-figure terms; no new physics. Single timing observations.")
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print("checks_passed", report["checks_passed"], "samples", len(times), "sensitivity", sensitivity, flush=True)
    if not report["checks_passed"]:raise RuntimeError("Predeclared criteria failed; audit retained")


if __name__ == "__main__":main()
