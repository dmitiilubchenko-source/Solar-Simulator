"""Qualify explicit tighter settings, retaining the original numerical failure."""
import argparse
from dataclasses import replace, asdict
import hashlib
import json
from pathlib import Path
import statistics

import numpy as np

from scripts.assess_qualification_grid import sample, hashes
from scripts.assess_sandbox_models import load_inputs, independent_reference, load_oracle, figure_reference, jpl_errors
from scripts.assess_sandbox_planets import errors, states
from solar_simulator.application_profiles import solar_sandbox
from solar_simulator.storage import to_document

ROOT = Path(__file__).resolve().parents[1]


def measure(actual, reference, names):
    e, m = names.index("Earth"), names.index("Moon")
    numeric = {name:errors(actual[:, i], reference[:, i]) for i, name in enumerate(names)}
    relative = errors(actual[:, m]-actual[:, e], reference[:, m]-reference[:, e])
    passed = (all(row["position_metres"] < 10 and row["velocity_m_per_s"] < 1e-4 for row in numeric.values())
        and relative["position_metres"] < .1 and relative["velocity_m_per_s"] < 1e-5)
    return dict(numerical_errors=numeric, relative_numerical_error=relative, checks_passed=passed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError("Preserve prior result")
    sources = hashes()
    sources["scripts/qualify_strict_profile.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    prior_path = ROOT/"docs/qualification-grid-validation.json"
    prior = json.loads(prior_path.read_bytes())
    for name, digest in prior["source_sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    for name, digest in prior["reference_sha256"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest
    cache_path = ROOT/".tools/qualification138/production139.npz"
    with np.load(cache_path, allow_pickle=False) as archive:
        times, ref, rust, baseline = [archive[key].copy() for key in ("times", "reference", "rust_tighter", "rust")]
        # Validate the cached production against its previously published metrics.
        names = list(prior["results"]["rust"]["numerical_errors"])
        assert measure(archive["rust"], ref, names)["relative_numerical_error"] == prior["results"]["rust"]["relative_numerical_error"]
    initial, origin, old_times, base, moon = load_inputs()
    assert np.array_equal(times, (np.array(prior["epochs_jd_tdb"])-origin.epoch_jd_tdb)*86400)
    assert np.array_equal(baseline[0], states(initial))
    # The independent AU/year + EMB encoding has a float64 round trip at t0.
    np.testing.assert_allclose(ref[0], states(initial), rtol=8*np.finfo(float).eps, atol=1e-9)
    python, timing = sample(times, "python", 3e-14)
    cost = {"baseline":[], "strict":[]}
    sample(times, "rust", 3e-14)  # warm up both installed backends before timing.
    for repeat in range(3):
        order = (("baseline",1e-13,baseline),("strict",3e-14,rust))
        if repeat % 2:order = order[::-1]
        for key, rtol, expected in order:
            repeated, elapsed = sample(times, "rust", rtol)
            assert np.array_equal(repeated, expected)
            cost[key].append(elapsed["wall_seconds"])
    results = {}
    indices = [int(np.flatnonzero(times == t)[0]) for t in old_times]
    for backend, values in (("python", python), ("rust", rust)):
        row = measure(values, ref, names)
        residuals, lunar = jpl_errors(values[indices], names, moon["epochs_jd_tdb"], base, moon)
        row.update(jpl_residuals_on_original_epochs=residuals,
            moon_relative_jpl_on_original_epochs=lunar,
            physical_goals_passed=all(v["position_metres"] < 10000 for v in residuals.values()) and lunar["position_metres"] < 1000)
        results[backend] = row
    holdout_times = np.array([0., .25, .75, 1.25, 2.25, 4.25, 8.25, 16.25, 32.25])*86400
    oracle = load_oracle()
    holdout_cache = ROOT/".tools/qualification138/reference141-holdout.npz"
    if holdout_cache.exists():raise FileExistsError("Preserve old holdout")
    holdout_reference, convergence = independent_reference(initial, solar_sandbox().settings.figures, holdout_times,
        levels=((1e-13,1800.),(3e-14,900.)), cache_name="qualification138/reference141-holdout",
        acceleration_function=oracle, figure_acceleration_function=figure_reference)
    holdout = {}
    for backend in ("python", "rust"):
        values, elapsed = sample(holdout_times, backend, 3e-14)
        holdout[backend] = dict(**measure(values, holdout_reference, names), production=elapsed)
    state = solar_sandbox(backend="rust")
    state = replace(state, settings=replace(state.settings, rtol=3e-14))
    checkpoint_path = ROOT/"docs/solar-sandbox-strict-checkpoint.json"
    if checkpoint_path.exists():raise FileExistsError("Preserve prior checkpoint")
    checkpoint_path.write_text(json.dumps(to_document(state), indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    assert all(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest for name, digest in sources.items())
    result = dict(protocol="docs/qualification-extension-protocol.md", source_sha256=sources,
        before_report_sha256=hashlib.sha256(prior_path.read_bytes()).hexdigest(),
        cache_sha256=hashlib.sha256(cache_path.read_bytes()).hexdigest(),
        holdout_reference_sha256=hashlib.sha256(holdout_cache.read_bytes()).hexdigest(),
        checkpoint_sha256=hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        origin=asdict(origin), settings=asdict(state.settings), results=results,
        samples=len(times), holdout_times_seconds=holdout_times.tolist(), holdout=holdout,
        holdout_reference_convergence=convergence, python_production=timing,
        before_rust_seconds=prior["results"]["rust"]["production"]["wall_seconds"],
        rust_cost_raw_seconds=cost, rust_cost_median_seconds={key:statistics.median(values) for key,values in cost.items()},
        jpl_new_epochs_checked=False,
        checks_passed=all(row["checks_passed"] and row["physical_goals_passed"] for row in results.values())
            and all(row["checks_passed"] for row in holdout.values()),
        limitations="Separate settings profile, standard profile unchanged. Tighter rtol has no general monotonic/global error guarantee. No new JPL data; original13/45 epochs only. No physical-model change.")
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print("checks_passed", result["checks_passed"], "relative", {k:r["relative_numerical_error"] for k,r in results.items()})
    if not result["checks_passed"]:raise RuntimeError("Strict profile failed; report retained")


if __name__ == "__main__":main()
