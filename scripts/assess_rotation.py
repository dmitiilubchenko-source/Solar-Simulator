"""Independent matrix/body-Euler reference and predeclared model audit.

Run: .venv/Scripts/python.exe -X utf8 scripts/assess_rotation.py
"""
import hashlib
import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.integrate import solve_ivp
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from solar_simulator.rotation import RigidFigure, integrate, invariants, rotation_matrix
from solar_simulator.simulation import G

POLICY = {"energy_relative": 1e-8, "angular_momentum_relative": 1e-8,
          "quaternion_norm": 1e-8, "reference_difference": 1e-7,
          "reference_uncertainty": 1e-8, "analytic_attitude": 1e-6}


def hat(v):
    x, y, z = v
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def reference(figure, initial, times, point_mass, rtol, max_step):
    """Independent RK45: Rdot=R hat(Omega), body Euler equation.

    No production potential/force/torque/quaternion derivative calls.
    Standard inertia tensor, not the production specific Q.
    """
    inertia = np.array(figure.moments)
    pair = point_mass is not None
    q, spin = (initial[6:10], initial[10:]) if pair else (initial[:4], initial[4:])
    # Independent quaternion conversion (SciPy takes xyzw).
    matrix = Rotation.from_quat(np.roll(q, -1)).as_matrix()
    start = np.concatenate((initial[:6] if pair else [], matrix.ravel(), matrix.T@spin))
    scales = np.concatenate(([np.linalg.norm(initial[:3])]*3+
        [np.linalg.norm(initial[3:6])]*3 if pair else [],
        np.ones(9), [np.linalg.norm(spin)]*3))

    def rhs(t, scaled):
        y = scaled*scales
        offset = 6 if pair else 0
        rotation = y[offset:offset+9].reshape(3, 3)
        momentum = y[offset+9:]
        omega = momentum/inertia
        torque_body = np.zeros(3)
        orbit = []
        if pair:
            r, v = y[:3], y[3:6]
            distance = np.linalg.norm(r)
            if distance <= figure.bounding_radius:
                raise ValueError("Reference outside expansion domain")
            n = r/distance
            body_n = rotation.T@n
            projection = np.dot(inertia*body_n, body_n)
            inertia_n = rotation@(inertia*body_n)
            # Different representation: gradient of MacCullagh with I.
            force = -G*figure.mass*point_mass*n/distance**2
            force += G*point_mass/(2*distance**4)*(
                (15*projection-3*sum(inertia))*n-6*inertia_n)
            torque_body = 3*G*point_mass/distance**3*np.cross(body_n, inertia*body_n)
            orbit = np.concatenate((v, force*(1/figure.mass+1/point_mass)))
        return np.concatenate((orbit, (rotation@hat(omega)).ravel(),
                               np.cross(momentum, omega)+torque_body))/scales

    result = solve_ivp(rhs, (times[0], times[-1]), start/scales, method="RK45",
                       rtol=rtol, atol=rtol*.01, t_eval=times, max_step=max_step)
    if not result.success or not np.all(np.isfinite(result.y)):
        raise ValueError("Invalid independent reference")
    return result.y.T*scales


def reference_difference(first, second, initial, pair):
    offset = 6 if pair else 0
    matrices_a = first[:, offset:offset+9].reshape(-1, 3, 3)
    matrices_b = second[:, offset:offset+9].reshape(-1, 3, 3)
    spin_a = np.einsum("nij,nj->ni", matrices_a, first[:, offset+9:])
    spin_b = np.einsum("nij,nj->ni", matrices_b, second[:, offset+9:])
    metrics = [float(np.max(np.linalg.norm(matrices_a-matrices_b, axis=(1, 2)))),
               float(np.max(np.linalg.norm(spin_a-spin_b, axis=1))/
                     np.linalg.norm(initial[10:] if pair else initial[4:]))]
    if pair:
        metrics += [float(np.max(np.linalg.norm(first[:, :3]-second[:, :3], axis=1))/np.linalg.norm(initial[:3])),
                    float(np.max(np.linalg.norm(first[:, 3:6]-second[:, 3:6], axis=1))/np.linalg.norm(initial[3:6]))]
    return max(metrics)


def production_as_matrix(states, pair):
    offset = 6 if pair else 0
    matrices = np.array([rotation_matrix(y[offset:offset+4]) for y in states])
    spins = states[:, offset+4:]
    momenta = np.einsum("nji,nj->ni", matrices, spins)
    return np.concatenate((states[:, :6] if pair else np.empty((len(states), 0)),
                           matrices.reshape(-1, 9), momenta), axis=1)


def cases():
    mass = 1e15
    q = np.roll(Rotation.from_rotvec([.3, -.2, .4]).as_quat(), 1)
    free = RigidFigure(mass, tuple(mass*np.array([2e5, 2.5e5, 3e5])), 1000.)
    symmetric = RigidFigure(mass, (2e20, 2e20, 3e20), 1000.)
    sphere = RigidFigure(mass, (2e20,)*3, 1000.)
    for name, figure in [("sphere", sphere), ("symmetric", symmetric), ("triaxial", free)]:
        spin = rotation_matrix(q)@(np.array(figure.moments)*np.array([.2, -.1, .3]))
        yield name, figure, None, np.concatenate((q, spin)), np.linspace(0, 100, 401), 1.
    point = 2e14
    distance = 12000.
    mean_motion = np.sqrt(G*(mass+point)/distance**3)
    period = 2*np.pi/mean_motion
    spin = rotation_matrix(q)@(np.array(free.moments)*mean_motion*np.array([.2, -.1, 1.3]))
    initial = np.concatenate(([distance, 0, 0], [0, distance*mean_motion, 0], q, spin))
    yield "figure_point", free, point, initial, np.linspace(0, 20*period, 401), period/100


def audit(reference_rtols=(3e-11, 3e-12)):
    rows = []
    for name, figure, point, initial, times, step in cases():
        pair = point is not None
        spin_scale = np.linalg.norm(initial[10:] if pair else initial[4:])
        atol = np.concatenate(([1e-7]*3+[1e-11]*3 if pair else [],
                               [1e-13]*4, [spin_scale*1e-13]*3))
        states = integrate(figure, initial, times, point_mass=point, rtol=1e-11, atol=atol, max_step=step)
        strict = integrate(figure, initial, times, point_mass=point, rtol=3e-13, atol=atol*.03, max_step=step/2)
        refs = [reference(figure, initial, times, point, tol, step) for tol in reference_rtols]
        values = [invariants(figure, y, point) for y in states]
        energies = np.array([v[0] for v in values])
        angular = np.array([v[1] for v in values])
        # Fixed initial scales, not a near-zero instantaneous residual.
        e_scale = abs(energies[0])
        l_scale = np.linalg.norm(angular[0])
        offset = 6 if pair else 0
        metrics = {"energy_relative": float(np.max(abs(energies-energies[0]))/e_scale),
            "angular_momentum_relative": float(np.max(np.linalg.norm(angular-angular[0], axis=1))/l_scale),
            "quaternion_norm": float(np.max(abs(np.linalg.norm(states[:, offset:offset+4], axis=1)-1))),
            "reference_difference": reference_difference(production_as_matrix(states, pair), refs[-1], initial, pair),
            "reference_uncertainty": reference_difference(refs[0], refs[1], initial, pair),
            "production_sensitivity": reference_difference(production_as_matrix(states, pair), production_as_matrix(strict, pair), initial, pair)}
        if name in ("sphere", "symmetric"):
            # Exact R(t)=exp(hat(S)/A*t) R0 exp(hat(e3)*beta*t).
            r0 = Rotation.from_quat(np.roll(initial[:4], -1)).as_matrix()
            body_spin = r0.T@initial[4:]
            beta = (1/figure.moments[2]-1/figure.moments[0])*body_spin[2]
            expected = np.array([Rotation.from_rotvec(initial[4:]/figure.moments[0]*t).as_matrix()
                @r0@Rotation.from_rotvec([0, 0, beta*t]).as_matrix() for t in times])
            measured = production_as_matrix(states, False)[:, :9].reshape(-1, 3, 3)
            metrics["analytic_attitude"] = float(np.max(np.linalg.norm(expected-measured, axis=(1, 2))))
        passed = all(metrics[k] < limit for k, limit in POLICY.items() if k in metrics)
        rows.append({"name": name, "mass_kg": figure.mass, "moments_kg_m2": figure.moments,
            "bounding_radius_m": figure.bounding_radius, "point_mass_kg": point,
            "initial": initial.tolist(), "duration_seconds": float(times[-1]), "samples": len(times),
            "max_step_seconds": step, "metrics": metrics, "passed": passed})
        print(name, metrics, "PASS" if passed else "FAIL", flush=True)
    paths = ["src/solar_simulator/rotation.py", "scripts/assess_rotation.py", "tests/test_rotation.py"]
    return {"model": "Newtonian rigid figure/point Q2; SI; COM; no tides/EIH/Q2-Q2",
        "policy": POLICY, "production_rtol": [1e-11, 3e-13], "reference_rtol": reference_rtols,
        "code_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        "cases": rows, "passed": all(row["passed"] for row in rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refinement", action="store_true")
    args = parser.parse_args()
    suffix = "refinement-validation" if args.refinement else "validation"
    path = ROOT/f"docs/conservative-rotation-{suffix}.json"
    if path.exists():
        raise FileExistsError("Preserve prior audit; choose an explicit new protocol/output")
    result = audit((3e-12, 3e-13) if args.refinement else (3e-11, 3e-12))
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    sys.exit(0 if result["passed"] else 1)
