"""Measure a temporary fixed-axis candidate without changing runtime physics."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
from time import perf_counter
from unittest.mock import patch

import numpy as np

from solar_simulator import oblateness as field
from solar_simulator.application_profiles import solar_sandbox
from solar_simulator.simulation import G
from solar_simulator.storage import to_document
from scripts.profile_runtime import digest, track

ROOT = Path(__file__).resolve().parents[1]


def candidate(positions, masses, prepared, time=0., *, _pair_displacement=None):
    """Same arithmetic; only omit the unused fixed-axis tensor allocation."""
    positions = np.asarray(positions, dtype=float)
    result = np.zeros_like(positions)
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        for entry in prepared:
            source, coefficient, radius, axis = entry
            targets = np.arange(len(masses)) != source
            r = field._source_vectors(positions, source, _pair_displacement)
            distance = np.linalg.norm(r, axis=1)
            if np.any(distance <= radius):
                raise ValueError("J2 определена только вне опорного радиуса источника")
            direction = r/distance[:, None]
            if not isinstance(axis, field.PrescribedQuadrupole):
                latitude = direction @ axis
                force = (1.5*G*masses[source]*coefficient*(radius/distance)**2/distance**2)[:, None]*(
                    (5*latitude**2-1)[:, None]*direction-2*latitude[:, None]*axis)
            else:
                q = field.tensors((entry,), time)[0][2]
                qn = direction @ q
                force = (-G*masses[source]/distance**4)[:, None]*(
                    qn-2.5*np.sum(direction*qn, axis=1)[:, None]*direction)
            result[targets] += force
            result[source] -= np.sum(force*(masses[targets]/masses[source])[:, None], axis=0)
    return result


def assess():
    state = solar_sandbox(backend="rust")
    p = np.array([[b.position.x, b.position.y, b.position.z] for b in state.bodies])
    m = np.array([b.mass for b in state.bodies])
    prepared = field.prepare(state.bodies, state.settings.figures)
    old = field.acceleration
    source = ROOT/"src/solar_simulator/oblateness.py"
    before = source.read_bytes()
    rows = {key:dict(force_seconds=[],physics_seconds=[],checkpoints=[]) for key in ("old", "candidate")}
    rng = np.random.default_rng(138)
    for _ in range(100):
        positions = p+rng.normal(size=p.shape)*1e5
        pair = (3, 4, positions[4]-positions[3])
        for relative in (None, pair):
            assert np.array_equal(old(positions, m, prepared, _pair_displacement=relative),
                candidate(positions, m, prepared, _pair_displacement=relative))
    for key, fn in (("old", old), ("candidate", candidate)):
        for _ in range(100):fn(p, m, prepared)
        with patch.object(field, "acceleration", fn):track("rust", False)
    for repeat in range(5):
        order = (("old", old), ("candidate", candidate))
        if repeat % 2:order = order[::-1]
        for key, fn in order:
            start = perf_counter()
            for _ in range(1000):fn(p, m, prepared)
            rows[key]["force_seconds"].append(perf_counter()-start)
            if repeat < 3:
                with patch.object(field, "acceleration", fn):
                    final, elapsed, _, _ = track("rust", False)
                rows[key]["physics_seconds"].append(elapsed)
                rows[key]["checkpoints"].append(digest(to_document(final)))
    assert len(set(rows["old"]["checkpoints"]+rows["candidate"]["checkpoints"])) == 1
    assert source.read_bytes() == before
    for row in rows.values():
        row["force_median_seconds"] = statistics.median(row["force_seconds"])
        row["physics_median_seconds"] = statistics.median(row["physics_seconds"])
    reduction = 1-rows["candidate"]["physics_median_seconds"]/rows["old"]["physics_median_seconds"]
    return dict(protocol="docs/qualification-extension-protocol.md", results=rows,
        settings=asdict(state.settings), origin=asdict(state.origin),
        duration_seconds=4320000, packets=60, force_calls_per_repeat=1000,
        force_equality_cases=200, checkpoint_equal=True, runtime_unchanged=True,
        physics_reduction_fraction=reduction, implementation_gate=reduction >= .15,
        source_sha256={str(p.relative_to(ROOT).as_posix()):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (source, Path(__file__), ROOT/"scripts/profile_runtime.py")},
        limitations="Rust point force plus Python figures; one machine and profile. Temporary candidate, not runtime. No altered tolerances or force equations.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError("Preserve prior measurement")
    result = assess()
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":main()
