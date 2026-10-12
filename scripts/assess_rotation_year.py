"""Annual free rigid-Moon audit; cache rejects changed sources and corrupt arrays."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.assess_nbody_rotation import reference, represented, differences, internal_invariants
from solar_simulator.ephemerides import solar_system
from solar_simulator.nbody_rotation import integrate, lunar_initial
from solar_simulator.experiment import Settings, create_experiment, advance
from solar_simulator.storage import to_document, save, load


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_arrays(data, samples, bodies):
    if samples < 1 or bodies < 1:
        raise ValueError("Empty audit grid")
    shapes = {"positions": (samples, bodies, 3), "velocities": (samples, bodies, 3),
              "matrices": (samples, 3, 3), "spins": (samples, 3)}
    for key, shape in shapes.items():
        if data[key].shape != shape or not np.all(np.isfinite(data[key])):
            raise ValueError(f"Invalid audit array: {key}")
    if data["quaternions"].shape not in {(0, 4), (samples, 4)}:
        raise ValueError("Invalid quaternion samples")
    for key in ("quaternions", "energy", "momentum", "angular"):
        if not np.all(np.isfinite(data[key])):
            raise ValueError(f"Nonfinite audit array: {key}")
    production = len(data["quaternions"]) != 0
    for key, shape in {"energy": (samples,), "momentum": (samples, 3), "angular": (samples, 3)}.items():
        if data[key].shape != (shape if production else (0,)):
            raise ValueError(f"Invalid invariant samples: {key}")


def pack(values, snapshots=None, times=None):
    data = {key: np.array([v[i] for v in values]) for i, key in
            enumerate(("positions", "velocities", "matrices", "spins"))}
    if snapshots is None:
        data.update({key: np.empty((0, 4) if key == "quaternions" else (0,))
                     for key in ("quaternions", "energy", "momentum", "angular")})
    else:
        inv = internal_invariants(snapshots, times)
        data["quaternions"] = np.array([v[1][0].quaternion for v in snapshots])
        data["energy"] = np.array([v[0] for v in inv])
        data["momentum"] = np.array([[v[1].x, v[1].y, v[1].z] for v in inv])
        data["angular"] = np.array([[v[2].x, v[2].y, v[2].z] for v in inv])
    return data


def unpack(data):
    return list(zip(data["positions"], data["velocities"], data["matrices"], data["spins"]))


def cached_job(directory, name, context, samples, count, run):
    context = json.loads(json.dumps(context, allow_nan=False))
    path = directory / (name + ".npz")
    metadata = directory / (name + ".json")
    if path.exists() or metadata.exists():
        if not (path.exists() and metadata.exists()):
            raise ValueError(f"Incomplete cache: {name}")
        record = json.loads(metadata.read_text(encoding="utf-8"))
        if record["context"] != context or record["npz_sha256"] != sha(path):
            raise ValueError(f"Changed/corrupt cache: {name}")
        with np.load(path, allow_pickle=False) as archive:
            data = {key: archive[key] for key in archive.files}
        validate_arrays(data, samples, count)
        print(name, "verified cache", flush=True)
        return data, record
    print(name, "started", flush=True)
    start = time.perf_counter()
    data = run()
    validate_arrays(data, samples, count)
    np.savez_compressed(path, **data)
    record = dict(context=context, npz_sha256=sha(path), elapsed_seconds=time.perf_counter()-start)
    metadata.write_text(json.dumps(record, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(name, "saved", round(record["elapsed_seconds"], 2), "seconds", flush=True)
    return data, record


def compare(a, b, bodies, spin):
    """Keep every body and Earth-Moon separately; report dimensional pair differences."""
    if len(a["positions"]) != len(b["positions"]):
        raise ValueError("Comparison sample counts differ")
    count = len(bodies)
    for data in (a, b):
        validate_arrays(data, len(a["positions"]), count)
    metrics = differences(unpack(a), unpack(b), bodies, spin)
    initial_p = np.array([[v.position.x, v.position.y, v.position.z] for v in bodies])
    initial_v = np.array([[v.velocity.x, v.velocity.y, v.velocity.z] for v in bodies])
    weights = np.array([v.mass for v in bodies]); weights /= weights.sum()
    pscale = np.maximum(np.linalg.norm(initial_p-weights@initial_p, axis=1), 1.)
    vscale = np.maximum(np.linalg.norm(initial_v-weights@initial_v, axis=1), 1.)
    dp = np.linalg.norm(a["positions"]-b["positions"], axis=2)
    dv = np.linalg.norm(a["velocities"]-b["velocities"], axis=2)
    metrics["per_body"] = {v.name: dict(position_m=float(dp[:, i].max()),
        velocity_m_s=float(dv[:, i].max()), position_scaled=float(dp[:, i].max()/pscale[i]),
        velocity_scaled=float(dv[:, i].max()/vscale[i])) for i, v in enumerate(bodies)}
    metrics["per_body_maximum"] = max(max(v["position_scaled"], v["velocity_scaled"])
                                       for v in metrics["per_body"].values())
    earth = [v.name for v in bodies].index("Earth"); moon = [v.name for v in bodies].index("Moon")
    metrics["relative_position_m"] = float(np.linalg.norm(
        (a["positions"][:, moon]-a["positions"][:, earth])-
        (b["positions"][:, moon]-b["positions"][:, earth]), axis=1).max())
    metrics["relative_velocity_m_s"] = float(np.linalg.norm(
        (a["velocities"][:, moon]-a["velocities"][:, earth])-
        (b["velocities"][:, moon]-b["velocities"][:, earth]), axis=1).max())
    return metrics


def initial_setup(policy):
    bodies, origin = solar_system(resolved_moon=True)
    if len(bodies) != 10:
        raise ValueError("Annual policy requires initial 10 bodies")
    rotations = lunar_initial(bodies, origin)
    times = np.linspace(0., policy["duration_seconds"], policy["samples"])
    start = create_experiment(bodies, Settings(float(times[-1])/sum(policy["checkpoint_steps"]),
        integrator="dop853", rtol=policy["production"]["rtol"],
        position_atol=policy["production"]["position_atol"],
        velocity_atol=policy["production"]["velocity_atol"], relative_pair=("Earth", "Moon")),
        origin=origin, rotations=rotations)
    return bodies, origin, rotations, times, start


def audit(output):
    if output.exists():
        raise FileExistsError("Preserve original annual audit")
    policy_path = ROOT / "scripts/rotation-year-policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    parent_path = ROOT / "docs/rotation-solar-system-validation.json"
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    paths = list(parent["code_sha256"])+["scripts/assess_rotation_year.py", "scripts/rotation-year-policy.json"]
    for path, digest in parent["code_sha256"].items():
        if sha(ROOT/path) != digest:
            raise ValueError(f"Changed parent source: {path}")
    hashes = {path: sha(ROOT/path) for path in paths}
    bodies, origin, rotations, times, start = initial_setup(policy)
    spin = rotations[0]
    steps = policy["checkpoint_steps"]
    context = dict(code_sha256=hashes, policy=policy, initial_document=to_document(start),
                   sample_times_seconds=times.tolist(), parent_audit_sha256=sha(parent_path))
    directory = ROOT / ".tools/rotation54/year"; directory.mkdir(parents=True, exist_ok=True)
    jobs = {}; records = {}
    for name in ("production", "strict", "rust"):
        options = dict(policy["strict" if name == "strict" else "production"])
        factor = options.pop("spin_atol_factor", 1.)
        state = (replace(spin, quaternion_atol=spin.quaternion_atol*factor,
                         momentum_atol=spin.momentum_atol*factor),)
        def run(options=options, state=state, name=name):
            snapshots = integrate(bodies, state, times, relative_pair=("Earth", "Moon"),
                                  backend="rust" if name == "rust" else "python", **options)
            return pack(represented(snapshots), snapshots, times)
        jobs[name], records[name] = cached_job(directory, name, context, len(times), len(bodies), run)
    for i, tolerance in enumerate(policy["reference_rtols"]):
        name = f"reference-{i}"
        jobs[name], records[name] = cached_job(directory, name, context, len(times), len(bodies),
            lambda tol=tolerance: pack(reference(bodies, spin, times, tol, policy["reference_max_step"])))
    print("Disk checkpoint and full-year restart", flush=True)
    whole = advance(start, sum(steps)); half = advance(start, steps[0])
    checkpoint = directory / "checkpoint.json"; save(half, checkpoint)
    continued = advance(load(checkpoint), steps[1])
    def final(experiment):
        return pack(represented([(experiment.bodies, experiment.rotations)]))
    restart = compare(final(whole), final(continued), bodies, spin)
    primary = jobs["production"]; ref = jobs["reference-1"]
    difference = compare(primary, ref, bodies, spin)
    uncertainty = compare(jobs["reference-0"], ref, bodies, spin)
    energy, angular, momentum = (primary[key] for key in ("energy", "angular", "momentum"))
    masses = np.array([v.mass for v in bodies]); initial_v = primary["velocities"][0]
    drift = (masses/masses.sum())@initial_v
    pscale = float(np.sum(masses*np.linalg.norm(initial_v-drift, axis=1)))
    matrices = ref["matrices"]
    metrics = dict(energy_relative=float(np.max(abs(energy-energy[0]))/abs(energy[0])),
        angular_momentum_relative=float(np.linalg.norm(angular-angular[0], axis=1).max()/np.linalg.norm(angular[0])),
        quaternion_norm=float(np.max(abs(np.linalg.norm(primary["quaternions"], axis=1)-1))),
        linear_momentum_scaled=float(np.linalg.norm(momentum-momentum[0], axis=1).max()/pscale),
        reference_difference=difference["maximum"], reference_uncertainty=uncertainty["maximum"],
        per_body_reference_difference=difference["per_body_maximum"],
        per_body_reference_uncertainty=uncertainty["per_body_maximum"],
        reference_matrix_orthogonality=float(np.linalg.norm(matrices.transpose(0, 2, 1)@matrices-np.eye(3), axis=(1, 2)).max()),
        reference_matrix_determinant=float(np.max(abs(np.linalg.det(matrices)-1))),
        restart_difference=restart["maximum"])
    # No future DE441 data is requested until all free trajectories and restart finish.
    print("Descriptive future DE441 attitude comparison", flush=True)
    from solar_simulator.orientation import lunar_rotation
    residuals = []
    for t, matrix in zip(times, primary["matrices"]):
        target, _ = lunar_rotation(float(t))
        residuals.append(float(np.linalg.norm(Rotation.from_matrix(matrix.T@target).as_rotvec())))
    for path, digest in hashes.items():
        if sha(ROOT/path) != digest:
            raise ValueError(f"Source changed during annual run: {path}")
    failures = [key for key, limit in policy["criteria"].items() if metrics[key] >= limit]
    result = dict(model=policy["model"], policy=policy, code_sha256=hashes,
        parent_audit_sha256=sha(parent_path), initial_document=to_document(start),
        epoch_jd_tdb=origin.epoch_jd_tdb, frame=origin.frame, sample_times_seconds=times.tolist(),
        invariant_frame="fixed translating initial COM", energy_normalization_joules=float(abs(energy[0])),
        angular_momentum_normalization_kg_m2_s=float(np.linalg.norm(angular[0])),
        linear_momentum_normalization_kg_m_s=pscale, metrics=metrics, failed_criteria=failures,
        reference_components=difference, reference_uncertainty_components=uncertainty,
        production_sensitivity=compare(primary, jobs["strict"], bodies, spin),
        python_rust_difference=compare(primary, jobs["rust"], bodies, spin), restart_components=restart,
        checkpoint_sha256=sha(checkpoint), checkpoint_time_seconds=half.time,
        DE441_attitude_residuals_rad=residuals, DE441_attitude_maximum_rad=max(residuals),
        jobs=records, passed=not failures)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(metrics, "failed criteria", failures, flush=True)
    return result


if __name__ == "__main__":
    result = audit(ROOT / "docs/rotation-year-validation.json")
    sys.exit(0 if result["passed"] else 1)
