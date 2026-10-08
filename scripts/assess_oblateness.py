"""Measure fixed Earth J2 separately from integration error and JPL residual."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from solar_simulator.diagnostics import model_invariants
from solar_simulator.ephemerides import solar_system
from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.oblateness import earth_j2
from solar_simulator.relativity import C
from solar_simulator.simulation import AU, G

if __package__:
    from .assess_relativity import YEAR, independent_acceleration
    from .assess_resolved_moon import errors, states
else:
    from assess_relativity import YEAR, independent_acceleration
    from assess_resolved_moon import errors, states


def independent_j2(p, mu, entries):
    """Different representation: trace-free tensor differentiated potential.

    Phi2 = mu*(r.T Q r)/(2 r^5), Q=J2 R² (3 ss.T - I).
    With this representation the axis-specific production force is not used.
    """
    result = np.zeros_like(p)
    for source, tensor in entries:
        for target in range(len(mu)):
            if target == source:
                continue
            r = p[target]-p[source]
            length = np.linalg.norm(r)
            gradient = tensor @ r/length**5-2.5*(r @ tensor @ r)*r/length**7
            result[target] -= mu[source]*gradient
            result[source] += mu[target]*gradient
    return result


def independent_reference(initial, figures, times):
    count = len(initial)
    q = states(initial).copy()
    q[:, :3] /= AU
    q[:, 3:] *= YEAR/AU
    mu = np.array([G*b.mass*YEAR**2/AU**3 for b in initial])
    names = [b.name for b in initial]
    entries = [(names.index(f.body), f.coefficient*(f.reference_radius/AU)**2*
                (3*np.outer(f.axis, f.axis)-np.eye(3))) for f in figures]
    def rhs(t, y):
        state = y.reshape(count, 6)
        a = independent_acceleration(state[:, :3], state[:, 3:], mu, C*YEAR/AU)
        a += independent_j2(state[:, :3], mu, entries)
        return np.concatenate((state[:, 3:], a), axis=1).ravel()
    results = []
    for tolerance in (1e-12, 1e-13, 3e-14):
        solution = solve_ivp(rhs, (0, times[-1]/YEAR), q.ravel(), method="RK45",
                             t_eval=times/YEAR, rtol=tolerance, atol=1e-15)
        if not solution.success or solution.t[-1] != times[-1]/YEAR:
            raise RuntimeError(solution.message)
        value = solution.y.T.reshape(len(times), count, 6)
        value[:, :, :3] *= AU
        value[:, :, 3:] *= AU/YEAR
        results.append(value)
    consistency = errors(results[-2], results[-1])["maximum_position_metres"]
    if not np.isfinite(consistency) or consistency > 10:
        raise RuntimeError(f"Independent reference not converged: {consistency} m")
    return results[-1], consistency


def sample(initial, origin, times, figures=(), *, rtol=1e-13):
    state = create_experiment(initial, Settings(3600, integrator="dop853", physics="eih-1pn",
                                               figures=figures, rtol=rtol), origin=origin)
    initial_energy = model_invariants(initial, "eih-1pn", figures)[0]
    actual, max_energy = [], 0.0
    for time in times:
        if time > state.time:
            state = advance(replace(state, settings=replace(state.settings, dt=float(time-state.time))), 1)
        actual.append(states(state.bodies))
        energy = model_invariants(state.bodies, "eih-1pn", figures)[0]
        max_energy = max(max_energy, abs((energy-initial_energy)/initial_energy))
    return np.array(actual), max_energy


def pair_errors(actual, expected, initial, times):
    names = [b.name for b in initial]
    e, m = names.index("Earth"), names.index("Moon")
    weight = initial[m].mass/(initial[e].mass+initial[m].mass)
    barycentre = actual[:, e]+weight*(actual[:, m]-actual[:, e])
    relative = actual[:, m]-actual[:, e]
    ref_relative = expected[:, 1]-expected[:, 0]
    dense = times <= 32*86400
    return dict(earth=errors(actual[:, e], expected[:, 0]), moon=errors(actual[:, m], expected[:, 1]),
        barycentre=errors(barycentre, expected[:, 2]), moon_relative_to_earth=errors(relative, ref_relative),
        first_32_days_relative=errors(relative[dense], ref_relative[dense]))


def main():
    source = Path("docs/solar-system-moon-reference.json")
    doc = json.loads(source.read_text(encoding="utf-8"))
    initial, origin = solar_system(resolved_moon=True)
    if (doc["dataset_sha256"] != origin.dataset_sha256 or doc["frame"] != origin.frame
            or doc["center"] != origin.center or doc["ephemeris"] != origin.ephemeris
            or doc["epochs_jd_tdb"][0] != origin.epoch_jd_tdb or doc["units"] != "SI"
            or [b["id"] for b in doc["bodies"]] != [399, 301, 3]):
        raise ValueError("Reference does not match pinned dataset")
    epochs = doc["epochs_jd_tdb"]
    times = (np.array(epochs)-origin.epoch_jd_tdb)*86400
    if (len(times) != 45 or times[0] != 0 or times[-1] != YEAR or np.any(np.diff(times) <= 0)
            or any([s["jd_tdb"] for s in b["states"]] != epochs for b in doc["bodies"])):
        raise ValueError("Expected matching 45-epoch reference")
    expected = np.stack([np.array([s["position"]+s["velocity"] for s in b["states"]])
                         for b in doc["bodies"]], axis=1)
    figures = earth_j2(initial, origin)
    reference, consistency = independent_reference(initial, figures, times)
    actual, energy = sample(initial, origin, times, figures)
    tighter, _ = sample(initial, origin, times, figures, rtol=3e-14)
    before, _ = sample(initial, origin, times)
    numerical = [dict(name=b.name, agreement=errors(actual[:, i], reference[:, i])) for i, b in enumerate(initial)]
    passed = all(row["agreement"]["maximum_position_metres"] < 10
                 and row["agreement"]["maximum_velocity_m_per_s"] < 1e-4 for row in numerical)
    profile = Path("src/solar_simulator/data/earth-j2-20261008.json")
    report = dict(physics="eih-1pn + fixed Earth J2", epoch_jd_tdb=origin.epoch_jd_tdb,
        duration_seconds=YEAR, samples=len(times), dataset_sha256=origin.dataset_sha256,
        reference_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        profile_sha256=hashlib.sha256(profile.read_bytes()).hexdigest(),
        independent_reference_position_consistency_metres=consistency, numerical_agreement=numerical,
        tolerance_sensitivity=errors(actual, tighter), maximum_relative_model_energy_residual=energy,
        point_mass_pair=pair_errors(before, expected, initial, times),
        fixed_earth_j2_pair=pair_errors(actual, expected, initial, times), checks_passed=passed,
        limitation="45 sampled epochs, not a global error bound. Approximate Earth pole frozen at start, constant nominal J2. No lunar figure/rotation/tides, higher harmonics, asteroids or mixed 1PN/J2 terms. Orbital angular momentum need not be conserved with fixed axes.")
    Path("docs/oblateness-validation.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    if not passed:
        raise RuntimeError("Oblateness numerical agreement targets failed")


if __name__ == "__main__":
    main()
