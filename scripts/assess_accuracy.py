"""Compare Verlet and adaptive production solver against analytic Kepler motion."""
import argparse
from dataclasses import replace
import json
import hashlib
import platform
from importlib.metadata import version
from math import cos, sin, sqrt, pi
from pathlib import Path
from time import perf_counter

from solar_simulator.experiment import create_experiment, Settings, advance
from solar_simulator.simulation import AU, sun_earth, total_energy
from solar_simulator.vector3 import Vector3


def kepler_relative(e, fraction, period):
    mean = (2*pi*fraction) % (2*pi)
    low, high = 0.0, 2*pi
    for _ in range(100):
        anomaly = (low+high)/2
        if anomaly-e*sin(anomaly) < mean:
            low = anomaly
        else:
            high = anomaly
    anomaly = (low+high)/2
    scale = 2*pi/period*AU/(1-e*cos(anomaly))
    return (Vector3(AU*(cos(anomaly)-e), AU*sqrt(1-e*e)*sin(anomaly), 0),
            Vector3(-scale*sin(anomaly), scale*sqrt(1-e*e)*cos(anomaly), 0))


def measure(e, integrator, rtol):
    bodies, period = sun_earth(e)
    state = create_experiment(bodies, Settings(period/8000, integrator=integrator, rtol=rtol))
    initial_energy = total_energy(bodies)
    error_r = error_v = energy_error = 0.0
    start = perf_counter()
    for i in range(1, 101):
        state = advance(state, 80)
        expected_r, expected_v = kepler_relative(e, i/100, period)
        actual_r = state.bodies[1].position.subtract(state.bodies[0].position)
        actual_v = state.bodies[1].velocity.subtract(state.bodies[0].velocity)
        error_r = max(error_r, actual_r.distance_to(expected_r))
        error_v = max(error_v, actual_v.distance_to(expected_v))
        energy_error = max(energy_error, abs((total_energy(state.bodies)-initial_energy)/initial_energy))
    return dict(eccentricity=e, integrator=integrator, rtol=rtol,
                maximum_position_error_metres=error_r, maximum_velocity_error_m_per_s=error_v,
                maximum_relative_energy_error=energy_error, seconds=perf_counter()-start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    runs = [measure(e, method, tolerance) for e in (0., .3, .6, .9)
            for method, tolerance in (("verlet", 1e-13), ("dop853", 1e-13), ("dop853", 3e-14))]
    checks = dict(accurate_orbits=all(r['maximum_position_error_metres'] < 100 and
                    r['maximum_velocity_error_m_per_s'] < 1e-3 and r['maximum_relative_energy_error'] < 1e-10
                    for r in runs if r['integrator'] == 'dop853'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fingerprints = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                    (Path(__file__), Path(__file__).resolve().parents[1]/"src/solar_simulator/accuracy.py")}
    args.output.write_text(json.dumps(dict(schema=1, fingerprints_sha256=fingerprints,
        environment=dict(python=platform.python_version(), scipy=version("scipy"), numpy=version("numpy")), reference="Analytic two-body Kepler orbit; bisection of eccentric anomaly",
        interval="one period", samples=100, position_atol_metres=1e-3, velocity_atol_m_per_s=1e-9,
        warning="Sampled global errors on specified orbits; local tolerances are not global guarantees",
        runs=runs, checks=checks), indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(checks))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
