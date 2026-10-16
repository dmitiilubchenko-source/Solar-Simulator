"""Independent Kepler check of a mass edit; not a Solar System accuracy claim."""
import argparse
from dataclasses import replace
import hashlib
import json
from math import fsum, pi, sqrt, sin, cos
from pathlib import Path
from time import perf_counter

import numpy as np

from solar_simulator.experiment import Settings, advance, create_experiment
from solar_simulator.sandbox import branch_experiment
from solar_simulator.simulation import Body, G
from solar_simulator.storage import to_document
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[1]
M, SMALL_M, R0 = 2e30, 7e29, 1.5e11
U = np.array([1., 1., 0.])/sqrt(2)
W = np.array([0., 0., 1.])
ECC = M/(2*M+SMALL_M)
A = R0/(1+ECC)
MU = G*(2*M+SMALL_M)
PERIOD = 2*pi*sqrt(A**3/MU)


def kepler(time):
    """Eccentric anomaly from monotone bisection, not the runtime solver."""
    mean = pi+2*pi*time/PERIOD
    lo, hi = mean-ECC, mean+ECC
    for _ in range(80):
        middle = (lo+hi)/2
        if middle-ECC*sin(middle) < mean: lo = middle
        else: hi = middle
    e = (lo+hi)/2
    rate = sqrt(MU/A**3)/(1-ECC*cos(e))
    position = A*(ECC-cos(e))*U-A*sqrt(1-ECC**2)*sin(e)*W
    velocity = A*sin(e)*rate*U-A*sqrt(1-ECC**2)*cos(e)*rate*W
    return position, velocity


def arrays(bodies):
    p = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    v = np.array([[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies])
    m = np.array([b.mass for b in bodies])
    return p, v, m


def balances(bodies):
    p, v, m = arrays(bodies)
    energy = fsum(float(.5*mass*np.dot(vel, vel)) for mass, vel in zip(m, v))
    energy -= G*m[0]*m[1]/np.linalg.norm(p[1]-p[0])
    momentum = np.sum(m[:, None]*v, axis=0)
    angular = np.sum(np.cross(p, m[:, None]*v), axis=0)
    return float(energy), momentum, angular


def initial(backend, integrator, count=64):
    speed = sqrt(G*(M+SMALL_M)/R0)
    fraction = SMALL_M/(M+SMALL_M)
    r, v = R0*U, speed*W
    bodies = [Body("Primary", M, Vector3(*map(float, -fraction*r)), Vector3(*map(float, -fraction*v))),
              Body("Companion", SMALL_M, Vector3(*map(float, (1-fraction)*r)), Vector3(*map(float, (1-fraction)*v)))]
    parent = create_experiment(bodies, Settings(PERIOD/count, backend=backend, integrator=integrator))
    changed = [replace(bodies[0], mass=2*M), bodies[1]]
    direct = create_experiment(changed, parent.settings)
    branch = branch_experiment(parent, replacements=(("Primary", changed[0]),))
    assert to_document(branch.child) == to_document(direct)
    return parent, direct, branch


def sample(state, steps_per_output=1):
    e0, p0, j0 = balances(state.bodies)
    momentum_scale = sum(b.mass*b.velocity.magnitude() for b in state.bodies)
    r_error = v_error = e_error = j_error = p_error = 0.
    start = perf_counter()
    for index in range(65):
        if index: state = advance(state, steps_per_output)
        p, v, _ = arrays(state.bodies)
        expected_p, expected_v = kepler(state.time)
        r_error = max(r_error, float(np.linalg.norm(p[1]-p[0]-expected_p)))
        v_error = max(v_error, float(np.linalg.norm(v[1]-v[0]-expected_v)))
        energy, momentum, angular = balances(state.bodies)
        e_error = max(e_error, abs(energy-e0)/abs(e0))
        j_error = max(j_error, float(np.linalg.norm(angular-j0)/np.linalg.norm(j0)))
        p_error = max(p_error, float(np.linalg.norm(momentum-p0)/momentum_scale))
    return dict(position_metres=r_error, velocity_m_per_s=v_error,
                relative_energy_drift=e_error, relative_angular_momentum_drift=j_error,
                scaled_momentum_drift=p_error, wall_seconds=perf_counter()-start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT/"docs/sandbox-branch-validation.json")
    args = parser.parse_args()
    rows = []
    for backend in ("python", "rust"):
        _, direct, branch = initial(backend, "dop853")
        before, after = sample(direct), sample(branch.child)
        numeric_keys = set(before)-{"wall_seconds"}
        assert all(before[k] == after[k] for k in numeric_keys)
        converged = []
        for count in (1024, 2048, 4096):
            _, _, branch = initial(backend, "verlet", count)
            converged.append(dict(steps=count, **sample(branch.child, count//64)))
        ratios = [converged[i]["position_metres"]/converged[i+1]["position_metres"] for i in range(2)]
        passed = (after["position_metres"] < 10 and after["velocity_m_per_s"] < 1e-5
                  and after["relative_energy_drift"] < 1e-10
                  and after["relative_angular_momentum_drift"] < 1e-10
                  and all(3.8 < ratio < 4.2 for ratio in ratios))
        rows.append(dict(backend=backend, before_direct_start=before, after_branch_start=after,
                         verlet=converged, convergence_ratios=ratios, checks_passed=passed))
    source_names = ["scripts/assess_sandbox_branch.py", "src/solar_simulator/sandbox.py",
        "src/solar_simulator/experiment.py", "src/solar_simulator/simulation.py",
        "src/solar_simulator/accuracy.py", "src/solar_simulator/storage.py"]
    import scipy
    import platform
    report = dict(protocol="docs/sandbox-validation-protocol.md", physics="newtonian-point-masses",
        source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_names},
        versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
        units="SI", masses_before=[M, SMALL_M], masses_after=[2*M, SMALL_M], G=G,
        radius_apocentre_metres=R0, eccentricity=ECC, semimajor_axis_metres=A,
        analytic_pericentre_metres=R0*(M+SMALL_M)/(3*M+SMALL_M),
        period_seconds=PERIOD, output_intervals=64, rtol=1e-13,
        position_atol_metres=1e-3, velocity_atol_m_per_s=1e-9, results=rows,
        checks_passed=all(r["checks_passed"] for r in rows),
        limitations="One tilted two-body model. Before/after compares direct versus branched starts with unchanged force code. Timings are single observations, not a speedup benchmark. Kepler bisection also uses float64. No guarantee for close encounters or arbitrary systems.")
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    if not report["checks_passed"]: raise RuntimeError("Predeclared sandbox criteria failed")


if __name__ == "__main__":
    main()
