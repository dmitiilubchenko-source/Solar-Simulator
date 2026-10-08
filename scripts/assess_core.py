"""Reproducible smooth-orbit accuracy matrix and core-only timings.

Run with the development environment; output contains measured results, not
universal error bounds. No contacts or GUI are involved in these benchmarks.
"""
import argparse
import json
import platform
import hashlib
from datetime import datetime, timezone
from importlib.metadata import version
from math import pi, sqrt
from pathlib import Path
from statistics import median
from time import perf_counter

import numpy as np
from scipy.integrate import solve_ivp

from solar_simulator.diagnostics import angular_momentum
from solar_simulator.rust_backend import evolve
from solar_simulator.simulation import (
    AU, EARTH_MASS, G, SUN_MASS, Body, center_of_mass, step,
    sun_earth, total_energy, total_momentum,
)
from solar_simulator.vector3 import Vector3


def integrate(bodies, dt, steps, backend):
    if backend == "rust":
        return evolve(bodies, dt, steps)
    for _ in range(steps):
        bodies = step(bodies, dt)
    return bodies


def reference(eccentricity, periods=1, samples=101):
    """Independent dimensionless relative motion; no production force call."""
    initial = [1-eccentricity, 0, 0, 0, sqrt((1+eccentricity)/(1-eccentricity)), 0]
    def rhs(time, state):
        r = state[:3]
        return np.concatenate((state[3:], -r / np.linalg.norm(r)**3))
    times = np.linspace(0, 2*pi*periods, samples)
    solution = solve_ivp(rhs, (0, times[-1]), initial, method="DOP853",
                         t_eval=times, rtol=2e-13, atol=2e-15)
    if not solution.success:
        raise RuntimeError(solution.message)
    closure = float(np.linalg.norm(solution.y[:, -1]-initial))
    if closure > 1e-8:
        raise RuntimeError(f"Reference orbit failed closure: {closure}")
    return solution.y.T, closure


def assess_orbit(eccentricity, steps_per_period, backend, truth):
    bodies, period = sun_earth(eccentricity)
    energy = total_energy(bodies)
    momentum = total_momentum(bodies)
    angular = angular_momentum(bodies)
    center = center_of_mass(bodies)
    mass = sum(b.mass for b in bodies)
    momentum_scale = sum(b.mass*b.velocity.magnitude() for b in bodies)
    velocity_unit = sqrt(G*(SUN_MASS+EARTH_MASS)/AU)
    dt = period/steps_per_period
    errors = {key: 0.0 for key in ("position_au", "velocity_units", "energy_relative",
                                  "momentum_scaled", "angular_relative", "com_au")}
    # Each sample includes diagnostics; timing of this loop is not a benchmark.
    stride = steps_per_period//100
    for index, expected in enumerate(truth):
        r = bodies[1].position.subtract(bodies[0].position)
        v = bodies[1].velocity.subtract(bodies[0].velocity)
        errors["position_au"] = max(errors["position_au"], float(np.linalg.norm(
            np.array([r.x, r.y, r.z])/AU-expected[:3])))
        errors["velocity_units"] = max(errors["velocity_units"], float(np.linalg.norm(
            np.array([v.x, v.y, v.z])/velocity_unit-expected[3:])))
        errors["energy_relative"] = max(errors["energy_relative"], abs((total_energy(bodies)-energy)/energy))
        errors["momentum_scaled"] = max(errors["momentum_scaled"], total_momentum(bodies).distance_to(momentum)/momentum_scale)
        errors["angular_relative"] = max(errors["angular_relative"], angular_momentum(bodies).distance_to(angular)/angular.magnitude())
        expected_center = center.add(momentum.multiply(index*stride*dt/mass))
        errors["com_au"] = max(errors["com_au"], center_of_mass(bodies).distance_to(expected_center)/AU)
        if index < len(truth)-1:
            bodies = integrate(bodies, dt, stride, backend)
    return {"backend": backend, "eccentricity": eccentricity,
            "steps_per_period": steps_per_period, "dt_seconds": dt,
            "sample_count": len(truth), "max_sampled_errors": errors}


def benchmark(backends):
    results = []
    # Seeded, well-separated synthetic states; measures pairwise kernel scaling.
    rng = np.random.default_rng(20261008)
    for count in (2, 16, 64):
        bodies = [Body(str(i), 1e22, Vector3(*(rng.normal(size=3)*AU)),
                       Vector3(*(rng.normal(size=3)*1000))) for i in range(count)]
        for backend in backends:
            integrate(bodies, 60, 2, backend)  # Import/warmup outside timing.
            durations, batches = [], []
            for _ in range(3):
                start, calls = perf_counter(), 0
                while True:
                    integrate(bodies, 60, 100, backend)
                    calls += 1
                    elapsed = perf_counter()-start
                    if elapsed >= .05:
                        break
                durations.append(elapsed/calls)
                batches.append(calls)
            results.append({"backend": backend, "bodies": count, "steps": 100,
                            "seconds_per_batch_samples": durations, "batch_counts": batches,
                            "median_seconds": median(durations)})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python-only", action="store_true")
    args = parser.parse_args()
    backends = ["python"] if args.python_only else ["python", "rust"]
    if "rust" in backends:
        import solar_native  # Fail explicitly rather than silently skip the core.
    runs, references = [], []
    for e in (0.0, 0.3, 0.6):
        truth, closure = reference(e)
        references.append({"eccentricity": e, "closure_norm": closure})
        for backend in backends:
            for steps in (2000, 4000, 8000):
                runs.append(assess_orbit(e, steps, backend, truth))
    convergence = []
    for e in (0.0, 0.3, 0.6):
        for backend in backends:
            selected = [r for r in runs if r["eccentricity"] == e and r["backend"] == backend]
            values = [r["max_sampled_errors"]["position_au"] for r in selected]
            convergence.append({"backend": backend, "eccentricity": e,
                                "position_error_ratios": [values[i]/values[i+1] for i in (0, 1)]})
    checks = {
        "all_orbit_thresholds": all(
            r["max_sampled_errors"]["position_au"] < 5e-4 and
            r["max_sampled_errors"]["velocity_units"] < .002 and
            r["max_sampled_errors"]["energy_relative"] < .001 and
            r["max_sampled_errors"]["momentum_scaled"] < 1e-11 and
            r["max_sampled_errors"]["angular_relative"] < 1e-11 and
            r["max_sampled_errors"]["com_au"] < 1e-11
            for r in runs if r["steps_per_period"] == 8000),
        "second_order_position": all(3.7 < ratio < 4.3 for c in convergence for ratio in c["position_error_ratios"]),
    }
    source_files = [Path(__file__), Path(__file__).resolve().parents[1]/"src/solar_simulator/simulation.py"]
    if "rust" in backends:
        source_files.append(Path(solar_native.__file__))
    fingerprints = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    report = {"schema": 1, "generated_utc": datetime.now(timezone.utc).isoformat(),
              "fingerprints_sha256": fingerprints, "environment": {"python": platform.python_version(),
              "platform": platform.platform(), "processor": platform.processor(),
              "numpy": version("numpy"), "scipy": version("scipy")},
              "model": "Newtonian point masses; SI; unsoftened Velocity Verlet; one orbital period",
              "reference": {"method": "DOP853, dimensionless relative motion", "rtol": 2e-13,
                            "atol": 2e-15, "closure_checks": references},
              "sampling_warning": "Maxima are over 101 snapshots, not every physical step",
              "runs": runs, "convergence": convergence, "benchmarks": benchmark(backends), "checks": checks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "checks": checks}))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
