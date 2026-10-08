"""Analytic apsidal advance and independent 1PN integration vs JPL DE441."""
from dataclasses import replace
import json
from math import atan2, pi, sqrt
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

from solar_simulator.accuracy import evolve_accurate
from solar_simulator.diagnostics import model_invariants
from solar_simulator.ephemerides import solar_system, EXPECTED_IDS
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.relativity import C
from solar_simulator.simulation import AU, G, Body
from solar_simulator.vector3 import Vector3

YEAR = 365.25*86400


def mercury_pair():
    """Isolated planar pair: explicit Keplerian starting orbit, not JPL states."""
    real, _ = solar_system()
    mass, small = real[0].mass, real[1].mass
    axis, eccentricity = 0.38709893*AU, 0.20563
    radius = axis*(1-eccentricity)
    mu = G*(mass+small)
    speed = sqrt(mu*(1+eccentricity)/radius)
    fraction = small/(mass+small)
    bodies = [Body("Sun", mass, Vector3(-fraction*radius, 0, 0), Vector3(0, -fraction*speed, 0)),
              Body("Mercury", small, Vector3((1-fraction)*radius, 0, 0), Vector3(0, (1-fraction)*speed, 0))]
    period = 2*pi*sqrt(axis**3/mu)
    expected = 6*pi*mu/(C*C*axis*(1-eccentricity**2))
    return bodies, period, expected


def measure_precession(physics, *, orbits=5, rtol=3e-14):
    """Locate pericentres in production evolutions, not fixed-time snapshots."""
    bodies, period, expected = mercury_pair()
    interval = period/32
    def radial(state):
        return state[1].position.subtract(state[0].position).dot(
               state[1].velocity.subtract(state[0].velocity))
    angles = [0.0]
    for _ in range(orbits*32+4):
        previous = bodies
        bodies = evolve_accurate(previous, interval, physics=physics, rtol=rtol)
        if radial(previous) < 0 < radial(bodies):
            duration = brentq(lambda t: radial(evolve_accurate(previous, float(t), physics=physics, rtol=rtol))
                             if t > 0 else radial(previous), 0, interval, xtol=1e-5)
            event = evolve_accurate(previous, float(duration), physics=physics, rtol=rtol) if duration > 0 else previous
            position = event[1].position.subtract(event[0].position)
            angles.append(atan2(position.y, position.x))
    if len(angles) != orbits+1:
        raise RuntimeError(f"Expected {orbits} complete pericentre intervals, got {len(angles)-1}")
    measured = float(np.mean(np.diff(np.unwrap(angles))))
    scale = 180/pi*3600*100*YEAR/period
    return dict(physics=physics, orbits=orbits, expected_radians_per_orbit=expected,
                measured_radians_per_orbit=measured, expected_arcsec_per_century=expected*scale,
                measured_arcsec_per_century=measured*scale,
                relative_difference=abs(measured-expected)/expected if physics=="eih-1pn" else None)


def independent_acceleration(p, v, mu, light_speed):
    """Scalar target loops, source->target vectors; no production force call.

    Direct EIH equation with Newtonian source acceleration, through 1PN.
    Inputs may be dimensionless; coefficients and c must use matching units.
    """
    count = len(mu)
    inward = p[None, :, :]-p[:, None, :]
    radii = np.linalg.norm(inward, axis=2)
    np.fill_diagonal(radii, np.inf)
    potential = np.sum(mu[None, :]/radii, axis=1)
    newton = np.sum(inward*(mu[None, :]/radii**3)[:, :, None], axis=1)
    result = newton.copy()
    speed2 = np.sum(v*v, axis=1)
    for i in range(count):
        for j in range(count):
            if i == j:
                continue
            r, direction = radii[i, j], inward[i, j]/radii[i, j]
            bracket = (speed2[i]+2*speed2[j]-4*np.dot(v[i], v[j])
                       -1.5*np.dot(direction, v[j])**2-4*potential[i]-potential[j]
                       +0.5*np.dot(inward[i, j], newton[j]))
            result[i] += mu[j]/light_speed**2*(direction/r**2*bracket
                -np.dot(direction, 4*v[i]-3*v[j])*(v[i]-v[j])/r**2+3.5*newton[j]/r)
    return result


def independent_reference(initial, times):
    count = len(initial)
    q = np.array([[b.position.x/AU, b.position.y/AU, b.position.z/AU,
                   b.velocity.x*YEAR/AU, b.velocity.y*YEAR/AU, b.velocity.z*YEAR/AU] for b in initial])
    mu = np.array([G*b.mass*YEAR**2/AU**3 for b in initial])
    def rhs(t, y):
        state = y.reshape(count, 6)
        return np.concatenate((state[:, 3:], independent_acceleration(state[:, :3], state[:, 3:],
                                mu, C*YEAR/AU)), axis=1).ravel()
    results = []
    for tolerance in (1e-12, 1e-13, 3e-14):
        solution = solve_ivp(rhs, (0, times[-1]/YEAR), q.ravel(), method="RK45", t_eval=times/YEAR,
                             rtol=tolerance, atol=1e-15)
        if not solution.success:
            raise RuntimeError(solution.message)
        states = solution.y.T.reshape(len(times), count, 6)
        states[:, :, :3] *= AU
        states[:, :, 3:] *= AU/YEAR
        results.append(states)
    consistency = float(np.linalg.norm(results[-2][:, :, :3]-results[-1][:, :, :3], axis=2).max())
    if not np.isfinite(consistency) or consistency > 10:
        raise RuntimeError(f"Independent 1PN reference not converged: {consistency} m")
    return results[-1], consistency


def sample(initial, origin, times, physics):
    state = create_experiment(initial, Settings(3600, integrator="dop853", physics=physics), origin=origin)
    energy0, momentum0, angular0 = model_invariants(initial, physics)
    maximum_energy = maximum_momentum = maximum_angular = 0.0
    actual = []
    for time in times:
        if time > state.time:
            state = advance(replace(state, settings=replace(state.settings, dt=float(time-state.time))), 1)
        actual.append([[b.position.x, b.position.y, b.position.z, b.velocity.x, b.velocity.y, b.velocity.z]
                       for b in state.bodies])
        energy, momentum, angular = model_invariants(state.bodies, physics)
        maximum_energy = max(maximum_energy, abs((energy-energy0)/energy0))
        maximum_momentum = max(maximum_momentum, momentum.distance_to(momentum0))
        maximum_angular = max(maximum_angular, angular.distance_to(angular0)/angular0.magnitude())
    return np.array(actual), dict(maximum_relative_energy_residual=maximum_energy,
        maximum_momentum_change_kg_m_per_s=maximum_momentum, maximum_relative_angular_change=maximum_angular)


def main():
    initial, origin = solar_system()
    doc = json.loads(Path("docs/solar-system-reference.json").read_text(encoding="utf-8"))
    if (doc["dataset_sha256"] != origin.dataset_sha256 or doc["frame"] != origin.frame
            or doc["center"] != origin.center or doc["units"] != "SI"
            or doc["ephemeris"] != origin.ephemeris or [b["id"] for b in doc["bodies"]] != list(EXPECTED_IDS)):
        raise ValueError("Reference does not match initial dataset")
    times = (np.array(doc["epochs_jd_tdb"])-origin.epoch_jd_tdb)*86400
    if len(times) != 13 or times[0] != 0 or abs(times[-1]-YEAR) > 1e-3:
        raise ValueError("Expected 13 epochs over one Julian year")
    horizons = np.stack([np.array([s["position"]+s["velocity"] for s in b["states"]]) for b in doc["bodies"]], axis=1)
    reference, consistency = independent_reference(initial, times)
    newton, _ = sample(initial, origin, times, "newtonian")
    pn, diagnostics = sample(initial, origin, times, "eih-1pn")
    rows = []
    for i, b in enumerate(initial):
        rows.append(dict(name=b.name,
            newtonian_jpl_position_discrepancy_metres=float(np.linalg.norm(newton[:, i, :3]-horizons[:, i, :3], axis=1).max()),
            eih_1pn_jpl_position_discrepancy_metres=float(np.linalg.norm(pn[:, i, :3]-horizons[:, i, :3], axis=1).max()),
            eih_1pn_jpl_velocity_discrepancy_m_per_s=float(np.linalg.norm(pn[:, i, 3:]-horizons[:, i, 3:], axis=1).max()),
            numerical_position_agreement_metres=float(np.linalg.norm(pn[:, i, :3]-reference[:, i, :3], axis=1).max()),
            numerical_velocity_agreement_m_per_s=float(np.linalg.norm(pn[:, i, 3:]-reference[:, i, 3:], axis=1).max())))
    apsides = [measure_precession(physics) for physics in ("newtonian", "eih-1pn")]
    passed = (all(r["numerical_position_agreement_metres"] < 10 and r["numerical_velocity_agreement_m_per_s"] < 1e-4 for r in rows)
              and apsides[1]["relative_difference"] < 1e-4
              and abs(apsides[0]["measured_radians_per_orbit"]) < 1e-10)
    output = dict(physics="eih-1pn", c_metres_per_second=C, epoch_jd_tdb=origin.epoch_jd_tdb,
        dataset_sha256=origin.dataset_sha256, duration_seconds=YEAR, samples=len(times), bodies=rows,
        independent_reference_position_consistency_metres=consistency, precession=apsides,
        diagnostics=diagnostics, checks_passed=passed,
        limitation="Sampled agreement is not a global bound. 1PN invariant residual includes O(c^-4) truncation. Nine bodies omit resolved moons, asteroids, solar oblateness and higher PN terms.")
    Path("docs/relativity-validation.json").write_text(json.dumps(output, ensure_ascii=False, allow_nan=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, allow_nan=False, indent=2))
    if not passed:
        raise RuntimeError("1PN validation targets failed")


if __name__ == "__main__":
    main()
