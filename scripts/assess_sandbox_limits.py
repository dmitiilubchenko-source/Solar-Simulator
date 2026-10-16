"""Independent orbital checks after mass, velocity and membership edits."""
import argparse
from dataclasses import replace
import hashlib
import json
from math import cos, sin, sqrt, pi, fsum
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.integrate import solve_ivp

from solar_simulator.experiment import Settings, create_experiment
from solar_simulator.sandbox import branch_experiment, to_branch_document, from_branch_document
from solar_simulator.simulation import Body, G
from solar_simulator.storage import to_document, from_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[1]
U = np.array([1., 1., 0.])/sqrt(2)
W = np.array([0., 0., 1.])
R = 1.5e11
M = 2e30
SMALL = 7e29


def arrays(bodies):
    return (np.array([[b.position.x, b.position.y, b.position.z] for b in bodies]),
        np.array([[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies]),
        np.array([b.mass for b in bodies]))


def balances(bodies):
    p, v, m = arrays(bodies)
    energy = fsum(float(.5*mi*(vi @ vi)) for mi, vi in zip(m, v))
    energy -= G*m[0]*m[1]/np.linalg.norm(p[1]-p[0])
    return energy, np.sum(m[:, None]*v, axis=0), np.sum(np.cross(p, m[:, None]*v), axis=0)


def scenario(name, backend):
    fraction = SMALL/(M+SMALL)
    r, v = R*U, sqrt(G*(M+SMALL)/R)*W
    offset, drift = np.array([3e9, -2e9, 1e9]), np.array([75., -50., 25.])
    bodies = [Body("Primary", M, Vector3(*map(float, offset-fraction*r)), Vector3(*map(float, drift-fraction*v))),
        Body("Companion", SMALL, Vector3(*map(float, offset+(1-fraction)*r)), Vector3(*map(float, drift+(1-fraction)*v)))]
    parent = create_experiment(bodies, Settings(3600., integrator="dop853", backend=backend))
    if name == "mass-double":
        branch = branch_experiment(parent, replacements=(("Primary", replace(bodies[0], mass=2*M)),))
    elif name == "add-companion":
        parent = create_experiment([bodies[0]], parent.settings)
        branch = branch_experiment(parent, additions=(bodies[1],))
    elif name == "remove-primary":
        branch = branch_experiment(parent, removals=("Primary",))
    else:
        factor = {"slow-velocity":.7, "escape-velocity":1.8, "eccentric-095":sqrt(.05)}[name]
        changed = replace(bodies[1], velocity=Vector3(*map(float, np.array([
            bodies[0].velocity.x, bodies[0].velocity.y, bodies[0].velocity.z])+factor*v)))
        branch = branch_experiment(parent, replacements=(("Companion", changed),))
    return parent, branch


def elliptic_reference(times, bodies):
    p, v, m = arrays(bodies)
    relative_v = v[1]-v[0]
    mu = G*float(sum(m))
    energy = .5*(relative_v @ relative_v)-mu/R
    semimajor = -mu/(2*energy)
    eccentricity = R/semimajor-1  # All declared bound cases start at apocentre.
    rate = sqrt(mu/semimajor**3)
    values = []
    for time in times:
        mean = pi+rate*time
        lo, hi = mean-eccentricity, mean+eccentricity
        for _ in range(90):
            middle = (lo+hi)/2
            if middle-eccentricity*sin(middle) < mean:lo = middle
            else:hi = middle
        anomaly = (lo+hi)/2
        derivative = rate/(1-eccentricity*cos(anomaly))
        r = semimajor*(eccentricity-cos(anomaly))*U-semimajor*sqrt(1-eccentricity**2)*sin(anomaly)*W
        speed = semimajor*sin(anomaly)*derivative*U-semimajor*sqrt(1-eccentricity**2)*cos(anomaly)*derivative*W
        values.append(np.concatenate((r, speed)))
    return np.array(values), 2*pi/rate, eccentricity


def hyperbolic_reference(times, bodies):
    p, v, m = arrays(bodies)
    y0 = np.concatenate(((p[1]-p[0])/R, (v[1]-v[0])*1e6/R))
    mu = G*float(sum(m))*1e12/R**3
    def derivative(time, y):
        return np.concatenate((y[3:], -mu*y[:3]/np.linalg.norm(y[:3])**3))
    values = []
    for rtol, max_step in ((1e-12,.001),(3e-14,.0005)):
        result = solve_ivp(derivative, (0., times[-1]/1e6), y0, method="RK45",
            t_eval=times/1e6, rtol=rtol, atol=1e-16, max_step=max_step)
        assert result.success and len(result.t) == len(times)
        value = result.y.T.copy()
        value[:, :3] *= R
        value[:, 3:] *= R/1e6
        values.append(value)
    difference = values[-1]-values[-2]
    uncertainty = dict(position_metres=float(np.linalg.norm(difference[:, :3], axis=1).max()),
        velocity_m_per_s=float(np.linalg.norm(difference[:, 3:], axis=1).max()))
    assert uncertainty["position_metres"] < 1 and uncertainty["velocity_m_per_s"] < 1e-6
    return values[-1], uncertainty


def assess(name, backend):
    parent, branch = scenario(name, backend)
    before = to_document(parent)
    bundle = to_branch_document(branch)
    state = from_branch_document(bundle).child
    child_before = to_document(state)
    start = perf_counter()
    if name == "remove-primary":
        p, v, _ = arrays(state.bodies)
        target = 1e6
        while state.time < target:state = advance_towards(state, target)
        actual_p, actual_v, _ = arrays(state.bodies)
        error = float(np.linalg.norm(actual_p-p-target*v))
        velocity_error = float(np.linalg.norm(actual_v-v))
        assert to_document(parent) == before
        return dict(name=name, backend=backend, position_metres=error, velocity_m_per_s=velocity_error,
            checks_passed=error < 1e-3 and velocity_error == 0, parent_preserved=True,
            duration_seconds=target, wall_seconds=perf_counter()-start)
    p, v, m = arrays(state.bodies)
    mu = G*float(sum(m))
    specific_energy = .5*((v[1]-v[0]) @ (v[1]-v[0]))-mu/R
    if name == "escape-velocity":
        times = np.linspace(0., 1e6, 33)
        reference, uncertainty = hyperbolic_reference(times, state.bodies)
        eccentricity = None
        expected_unbound = True
    else:
        _, period, eccentricity = elliptic_reference([0.], state.bodies)
        times = np.linspace(0., period, 33)
        reference, _, _ = elliptic_reference(times, state.bodies)
        uncertainty = None
        expected_unbound = False
    assert (specific_energy > 0) == expected_unbound
    energy0, momentum0, angular0 = balances(state.bodies)
    momentum_scale = sum(b.mass*b.velocity.magnitude() for b in state.bodies)
    max_position = max_velocity = max_energy = max_momentum = max_angular = max_center = 0.
    weight = m/m.sum()
    center0 = np.sum(weight[:, None]*p, axis=0)
    drift = np.sum(weight[:, None]*v, axis=0)
    checkpoint_preserved = False
    for index, target in enumerate(times):
        while state.time < target:state = advance_towards(state, float(target))
        p, v, _ = arrays(state.bodies)
        expected = reference[index]
        max_position = max(max_position, float(np.linalg.norm(p[1]-p[0]-expected[:3])))
        max_velocity = max(max_velocity, float(np.linalg.norm(v[1]-v[0]-expected[3:])))
        max_center = max(max_center, float(np.linalg.norm(np.sum(weight[:, None]*p, axis=0)-center0-target*drift)))
        energy, momentum, angular = balances(state.bodies)
        max_energy = max(max_energy, abs((energy-energy0)/energy0))
        max_momentum = max(max_momentum, float(np.linalg.norm(momentum-momentum0)/momentum_scale))
        max_angular = max(max_angular, float(np.linalg.norm(angular-angular0)/np.linalg.norm(angular0)))
        if index == 16:
            restored = from_document(to_document(state))
            uninterrupted = advance_towards(state, float(times[17]))
            assert to_document(advance_towards(restored, float(times[17]))) == to_document(uninterrupted)
            state = restored
            checkpoint_preserved = True
    assert to_document(parent) == before and to_branch_document(branch) == bundle
    assert to_document(from_document(child_before)) == child_before
    passed = (max_position < 10 and max_velocity < 1e-5 and max_center < .01
        and max_energy < 1e-10 and max_momentum < 1e-10 and max_angular < 1e-10)
    return dict(name=name, backend=backend, duration_seconds=float(times[-1]), samples=len(times),
        eccentricity=eccentricity, unbound=expected_unbound, position_metres=max_position,
        velocity_m_per_s=max_velocity, center_of_mass_error_metres=max_center,
        relative_energy_drift=max_energy, scaled_momentum_drift=max_momentum,
        relative_angular_momentum_drift=max_angular, reference_uncertainty=uncertainty,
        parent_preserved=True, checkpoint_continue_exact=checkpoint_preserved,
        checks_passed=passed, wall_seconds=perf_counter()-start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():raise FileExistsError("Preserve previous audit")
    sources = ["scripts/assess_sandbox_limits.py", "src/solar_simulator/sandbox.py",
        "src/solar_simulator/simulation.py", "src/solar_simulator/accuracy.py",
        "src/solar_simulator/time_control.py", "src/solar_simulator/storage.py",
        "src/solar_simulator/experiment.py"]
    hashes = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    results = []
    for backend in ("python", "rust"):
        for name in ("mass-double", "slow-velocity", "escape-velocity", "eccentric-095", "add-companion", "remove-primary"):
            row = assess(name, backend)
            results.append(row)
            print(name, backend, row["checks_passed"], row["position_metres"], flush=True)
    assert hashes == {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
    result = dict(protocol="docs/qualification-extension-protocol.md", source_sha256=hashes,
        units="SI", physics="Newtonian point masses, 3D tilted pair, inertial SI frame",
        settings=to_document(scenario("mass-double", "python")[1].child)["settings"], results=results,
        checks_passed=all(row["checks_passed"] for row in results),
        limitations="Six declared scenarios, no Solar System/JPL accuracy claim or arbitrary-encounter guarantee. Fixed J2 exterior guard covered by existing force tests. Kepler and RK45 reference also use float64.")
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    if not result["checks_passed"]:raise RuntimeError("Predeclared sandbox checks failed; report retained")


if __name__ == "__main__":main()
