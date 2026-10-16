"""Compare SHA-verified free trajectories with newly fetched DE441 states."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_sandbox_models import load_inputs
from scripts.assess_sandbox_planets import errors, states
from solar_simulator.application_profiles import solar_sandbox

ROOT = Path(__file__).resolve().parents[1]


def verified_sources(receipt, root=ROOT):
    for name, expected in receipt["source_sha256"].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Source changed: "+name)


def validate_reference(reference, origin, names, ids, grid):
    if (reference["origin"] != asdict(origin) or reference["units"] != "SI"
            or reference["epochs_jd_tdb"] != grid
            or [b["name"] for b in reference["bodies"]] != names
            or [b["id"] for b in reference["bodies"]] != list(ids)
            or reference["initial_dataset_changed"] or reference["physical_parameters_fitted"]):
        raise ValueError("Reference lineage/frame/time/units/body mismatch")
    for body in reference["bodies"]:
        if len(body["states"]) != len(grid) or any(abs(row["jd_tdb"]-epoch) > 1e-8
                for row, epoch in zip(body["states"], grid)):
            raise ValueError("Reference epochs mismatch")
        if body["overlap_position_metres"] > .01 or body["overlap_velocity_m_per_s"] > 1e-8:
            raise ValueError("Reference overlap failed")
    expected = np.array([[row["position"]+row["velocity"] for row in body["states"]]
        for body in reference["bodies"]], dtype=float).transpose(1,0,2)
    if expected.shape != (len(grid),len(names),6) or not np.all(np.isfinite(expected)):
        raise ValueError("Reference values invalid")
    return expected


def residuals(actual, expected, names, epochs):
    rows = {}
    for index, name in enumerate(names):
        row = errors(actual[:,index], expected[:,index])
        delta = np.linalg.norm(actual[:,index,:3]-expected[:,index,:3], axis=1)
        row["worst_epoch_jd_tdb"] = epochs[int(np.argmax(delta))]
        row["position_goal_passed"] = row["position_metres"] < 10000
        rows[name] = row
    earth, moon = names.index("Earth"), names.index("Moon")
    relative = errors(actual[:,moon]-actual[:,earth], expected[:,moon]-expected[:,earth])
    relative["position_goal_passed"] = relative["position_metres"] < 1000
    return dict(jpl_residuals=rows, moon_relative_jpl=relative,
        physical_goals_passed=all(row["position_goal_passed"] for row in rows.values()) and relative["position_goal_passed"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-cache", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError("Preserve earlier report")
    start = perf_counter()
    dense_path = ROOT/"docs/qualification-grid-reference.json"
    dense = json.loads(dense_path.read_bytes())
    prior_path = ROOT/"docs/qualification-grid-validation.json"
    prior = json.loads(prior_path.read_bytes())
    strict_path = ROOT/"docs/strict-profile-validation.json"
    strict = json.loads(strict_path.read_bytes())
    for receipt in (prior,strict,dense):verified_sources(receipt)
    if hashlib.sha256(prior_path.read_bytes()).hexdigest() != strict["before_report_sha256"]:
        raise ValueError("Original numerical failure audit changed")
    initial, origin, _, _, _ = load_inputs()
    from solar_simulator.ephemerides import RESOLVED_IDS
    names = [b.name for b in initial]
    expected = validate_reference(dense, origin, names, RESOLVED_IDS, prior["epochs_jd_tdb"])
    # Raw response hashes and original parser attest the published data matrix.
    from scripts.fetch_ephemerides import parse_result
    for body in dense["bodies"]:
        rows = []
        for index, request in enumerate(body["requests"]):
            offset = sum(len(r["epochs_jd_tdb"]) for r in body["requests"][:index])
            path = args.raw_cache/f"horizons-{body['id']}-{offset:03d}.json"
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != request["response_sha256"]:
                raise ValueError("Raw response changed")
            rows.extend(parse_result(json.loads(raw), body["id"], request["epochs_jd_tdb"]))
        if rows != body["states"]:raise ValueError("Published reference differs from raw vectors")
    cache = ROOT/".tools/qualification138/production139.npz"
    if hashlib.sha256(cache.read_bytes()).hexdigest() != strict["cache_sha256"]:
        raise ValueError("Free production trajectory changed")
    profiles = {}
    with np.load(cache, allow_pickle=False) as data:
        times = (np.array(dense["epochs_jd_tdb"])-origin.epoch_jd_tdb)*86400
        if not np.array_equal(times,data["times"]):raise ValueError("Trajectory time grid mismatch")
        for name in ("python", "rust", "rust_tighter"):
            actual = data[name]
            if actual.shape != expected.shape or not np.array_equal(actual[0],states(initial)):
                raise ValueError("Trajectory initial conditions mismatch")
            profiles[name] = residuals(actual,expected,names,dense["epochs_jd_tdb"])
    sources = ["scripts/assess_dense_jpl.py", "scripts/fetch_dense_jpl.py"]
    from platform import python_version
    import scipy
    result = dict(protocol="docs/qualification-extension-protocol.md", units="SI", origin=asdict(origin),
        duration_seconds=float(times[-1]), samples=len(times), epochs_jd_tdb=dense["epochs_jd_tdb"],
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources},
        input_sha256={"docs/qualification-grid-reference.json":hashlib.sha256(dense_path.read_bytes()).hexdigest(),
            "docs/qualification-grid-validation.json":hashlib.sha256(prior_path.read_bytes()).hexdigest(),
            "docs/strict-profile-validation.json":hashlib.sha256(strict_path.read_bytes()).hexdigest(),
            ".tools/qualification138/production139.npz":strict["cache_sha256"]},
        standard_settings=asdict(solar_sandbox(backend="rust").settings),
        strict_settings=strict["settings"], results=profiles,
        raw_responses_checked=sum(len(b["requests"]) for b in dense["bodies"]),
        prior_numerical_failure_retained=not prior["results"]["rust"]["numerical_checks_passed"],
        jpl_new_epochs_checked=True, initial_states_fitted=False,
        checks_passed=all(row["physical_goals_passed"] for row in profiles.values()),
        versions=dict(python=python_version(), numpy=np.__version__, scipy=scipy.__version__),
        comparison_wall_seconds=perf_counter()-start,
        limitations="Reused free trajectories after exact SHA/source/time/state validation. New JPL coverage125 epochs for all10 bodies, no continuous error guarantee. Strict numerical qualification141 unchanged; failed standard numerical criterion139 retained. No force/integrator/initial parameter changes.")
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("checks_passed",result["checks_passed"],"samples",len(times),"Moonrelative",{k:v["moon_relative_jpl"] for k,v in profiles.items()})
    if not result["checks_passed"]:raise RuntimeError("Physical goals failed; report retained")


if __name__ == "__main__":main()
