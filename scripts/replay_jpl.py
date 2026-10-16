"""Offline replay of saved trajectories versus JPL; no Solar import or solver."""
import argparse
import csv
import hashlib
import json
from math import hypot, isclose
from pathlib import Path
import re
from time import perf_counter

import numpy as np

NAMES = ["Sun", "Mercury", "Venus", "Earth", "Moon", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"]
IDS = [10, 1, 2, 399, 301, 4, 5, 6, 7, 8]
G = 6.67430e-11


def require(condition, message):
    if not condition:raise ValueError(message)


def read_json(path):
    return json.loads(path.read_bytes())


def verify_files(root):
    root = Path(root).resolve()
    manifest = read_json(root/"manifest.json")
    require(manifest.get("schema") == 1, "Unknown manifest")
    require(manifest["kind"] == "saved-trajectory-jpl-replay", "Wrong verification kind")
    for name, expected in manifest["files"].items():
        path = root/name
        require(not Path(name).is_absolute() and path.resolve().is_relative_to(root) and not path.is_symlink(), "Unsafe payload path")
        require(path.is_file(), "Missing payload: "+name)
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "Payload changed: "+name)
    require(set(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()) ==
        set(manifest["files"]) | {"manifest.json"}, "Unexpected payload file")
    return manifest


def parse_raw(raw, identity, epochs):
    payload = json.loads(raw)
    require(not payload.get("error") and payload["signature"]["source"] == "NASA/JPL Horizons API", "Wrong Horizons response")
    text = payload["result"]
    target = re.search(r"Target body name:.*?\((\d+)\).*?\{source:\s*([^}]+)\}", text)
    alias = "Mercury Barycenter" if identity == 1 else "Venus Barycenter"
    require(target is not None and target[2].strip() == "DE441" and
        (int(target[1]) == identity or (identity in (1,2) and int(target[1]) == identity*100+99 and alias in target[0])), "Wrong target or ephemeris")
    require(all(s in text for s in ("Center body name: Solar System Barycenter (0)",
        "Output units    : KM-S", "Ecliptic of J2000.0", "GEOMETRIC cartesian states", "JDTDB")), "Wrong raw conventions")
    table = text.split("$$SOE",1)[1].split("$$EOE",1)[0]
    rows = []
    for row in csv.reader(table.strip().splitlines()):
        require(len(row) == 9 and not row[-1].strip(), "Wrong vector row")
        rows.append([float(row[0])]+[float(x)*1000 for x in row[2:8]])
    values = np.asarray(rows, dtype=float)
    require(values.shape == (len(epochs),7) and np.all(np.isfinite(values)), "Invalid raw values")
    require(np.all(np.abs(values[:,0]-epochs) <= 1e-8), "Wrong raw epochs")
    return values[:,1:]


def maximum_error(actual, expected):
    difference = actual-expected
    position = [hypot(*row) for row in difference[:,:3]]
    velocity = [hypot(*row) for row in difference[:,3:]]
    return dict(position_metres=max(position), velocity_m_per_s=max(velocity)), int(np.argmax(position))


def replay(root):
    start = perf_counter()
    root = Path(root).resolve()
    manifest = verify_files(root)
    reference = read_json(root/"reference.json")
    trajectories = read_json(root/"trajectories.json")
    report = read_json(root/"dense-report.json")
    initial = read_json(root/"initial.json")
    dataset = read_json(root/"initial-dataset.json")
    strict = read_json(root/"strict-report.json")
    before = read_json(root/"numerical-before.json")
    origin = initial["origin"]
    require(reference["origin"] == report["origin"] == trajectories["origin"] == origin, "Origin mismatch")
    require(origin["frame"] == "Ecliptic J2000" and origin["center"] == "Solar System Barycenter" and
        origin["ephemeris"] == "DE441" and origin["epoch_jd_tdb"] == 2461321.5, "Wrong coordinate/time conventions")
    require(all(doc["units"] == "SI" for doc in (reference,report,trajectories,initial,dataset)), "Wrong units")
    require(hashlib.sha256((root/"initial-dataset.json").read_bytes()).hexdigest() == origin["dataset_sha256"], "Initial dataset changed")
    require(dataset["gm_sha256"] == origin["gm_sha256"], "GM lineage mismatch")
    require(initial["time"] == 0 and initial["initial"] == initial["bodies"], "Wrong checkpoint initial state")
    require([b["name"] for b in initial["initial"]] == NAMES and [b["name"] for b in reference["bodies"]] == NAMES and
        [b["id"] for b in reference["bodies"]] == IDS and [b["id"] for b in dataset["bodies"]] == IDS, "Wrong body order")
    for body, data in zip(initial["initial"], dataset["bodies"]):
        require(body["position"] == data["position"] and body["velocity"] == data["velocity"] and
            body["mass"] == data["gm_m3_s2"]/G, "Initial vectors or GM mismatch")
    epochs = reference["epochs_jd_tdb"]
    times = (np.array(epochs)-origin["epoch_jd_tdb"])*86400
    require(len(epochs) == 125 and np.all(np.diff(times) > 0) and times[0] == 0 and times[-1] == 31557600,
        "Wrong time grid")
    require(epochs == trajectories["epochs_jd_tdb"] == report["epochs_jd_tdb"], "Time grid mismatch")
    require(not reference["initial_dataset_changed"] and not reference["physical_parameters_fitted"], "Fitted or altered initial data")
    require(initial["settings"] == strict["settings"] == report["strict_settings"], "Strict settings mismatch")
    settings = initial["settings"]
    require(settings["physics"] == "eih-1pn" and settings["integrator"] == "dop853" and
        settings["error_control"] == "per-body" and settings["relative_pair"] == ["Earth","Moon"] and
        settings["rtol"] == 3e-14 and settings["dt"] == 3600 and
        settings["position_atol"] == 1e-3 and settings["velocity_atol"] == 1e-9 and
        [f["body"] for f in settings["figures"]] == ["Sun","Earth"], "Unsupported qualified model")
    require(strict["before_report_sha256"] == hashlib.sha256((root/"numerical-before.json").read_bytes()).hexdigest(), "Prior failure changed")
    require(not before["results"]["rust"]["numerical_checks_passed"] and strict["checks_passed"], "Prior failure missing")
    require(manifest["production_cache_sha256"] == strict["cache_sha256"], "Trajectory provenance mismatch")
    expected = []
    for body in reference["bodies"]:
        require(len(body["states"]) == 125 and all(abs(row["jd_tdb"]-epoch) <= 1e-8
            for row,epoch in zip(body["states"],epochs)), "Reference row epochs mismatch")
        require([epoch for request in body["requests"] for epoch in request["epochs_jd_tdb"]] == epochs,
            "Raw request grid mismatch")
        rows = []
        offset = 0
        for request in body["requests"]:
            path = root/f"raw/horizons-{body['id']}-{offset:03d}.json"
            raw = path.read_bytes()
            require(hashlib.sha256(raw).hexdigest() == request["response_sha256"], "Raw SHA mismatch")
            rows.extend(parse_raw(raw,body["id"],request["epochs_jd_tdb"]).tolist())
            offset += len(request["epochs_jd_tdb"])
        values = np.array([row["position"]+row["velocity"] for row in body["states"]])
        require(np.array_equal(rows,values) and len(rows) == 125, "Reference differs from primary vectors")
        require(body["overlap_position_metres"] <= .01 and body["overlap_velocity_m_per_s"] <= 1e-8, "Historic overlap failed")
        expected.append(values)
    expected = np.asarray(expected).transpose(1,0,2)
    initial_vectors = np.array([b["position"]+b["velocity"] for b in initial["initial"]])
    results = {}
    require(set(trajectories["profiles"]) == {"python","rust","rust_tighter"}, "Missing trajectory profile")
    for profile, values in trajectories["profiles"].items():
        settings = dict(report["standard_settings"])
        settings["backend"] = "python" if profile == "python" else "rust"
        if profile == "rust_tighter":settings = report["strict_settings"]
        require(trajectories["settings"][profile] == settings, "Trajectory settings mismatch")
        actual = np.asarray(values,dtype=float)
        require(actual.shape == (125,10,6) and np.all(np.isfinite(actual)) and
            np.array_equal(actual[0],initial_vectors), "Invalid trajectory or initial state")
        rows = {}
        for index,name in enumerate(NAMES):
            row, worst = maximum_error(actual[:,index],expected[:,index])
            published = report["results"][profile]["jpl_residuals"][name]
            require(isclose(row["position_metres"],published["position_metres"],rel_tol=0,abs_tol=1e-9) and
                isclose(row["velocity_m_per_s"],published["velocity_m_per_s"],rel_tol=0,abs_tol=1e-12) and
                epochs[worst] == published["worst_epoch_jd_tdb"], "Published body residual mismatch")
            rows[name] = row
        relative,_ = maximum_error(actual[:,4]-actual[:,3],expected[:,4]-expected[:,3])
        published = report["results"][profile]["moon_relative_jpl"]
        require(isclose(relative["position_metres"],published["position_metres"],rel_tol=0,abs_tol=1e-9) and
            isclose(relative["velocity_m_per_s"],published["velocity_m_per_s"],rel_tol=0,abs_tol=1e-12), "Published pair residual mismatch")
        passed = all(row["position_metres"] < 10000 for row in rows.values()) and relative["position_metres"] < 1000
        require(passed == report["results"][profile]["physical_goals_passed"], "Published goal mismatch")
        results[profile] = dict(jpl_residuals=rows,moon_relative_jpl=relative,physical_goals_passed=passed)
    return dict(checks_passed=all(row["physical_goals_passed"] for row in results.values()),
        samples=125,bodies=10,primary_responses=40,results=results,
        prior_numerical_failure_retained=True,solver_executed=False,
        wall_seconds=perf_counter()-start,manifest_sha256=hashlib.sha256((root/"manifest.json").read_bytes()).hexdigest(),
        limitations="Replay of saved trajectories and comparison only; no new integration or independent force verification. Sampled epochs, not continuous error guarantees.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle",type=Path)
    parser.add_argument("--output",type=Path)
    args = parser.parse_args()
    if args.output is not None:
        require(not args.output.exists(), "Preserve existing output")
        require(not args.output.resolve().is_relative_to(args.bundle.resolve()), "Write result outside verified bundle")
    result = replay(args.bundle)
    if args.output is not None:args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2,allow_nan=False))
    require(result["checks_passed"], "Physical goals failed")


if __name__ == "__main__":main()
