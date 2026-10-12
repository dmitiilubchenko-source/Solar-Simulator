"""Diagnose change 50's Q2 failure against a known six-point mass source.

Fourth-moment torque is diagnostic only; it is not a runtime force.
"""
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from solar_simulator.rotation import RigidFigure, pair_field
from solar_simulator.simulation import G


def diagnose():
    points = np.concatenate((np.diag([600., 450., 300.]), -np.diag([600., 450., 300.])))
    mass, target = 1e15, 2e14
    second = mass/6*(points.T@points)
    body = RigidFigure(mass, tuple(np.trace(second)-np.diag(second)), 600.)
    rotation = Rotation.from_rotvec([.3, -.2, .4])
    q = np.roll(rotation.as_quat(), 1)
    points = rotation.apply(points)
    rows = []
    for distance in [6000., 12000., 24000., 48000.]:
        r = distance*np.array([.8, .48, .36])
        delta = r-points
        forces = G*(mass/6)*target*delta/np.linalg.norm(delta, axis=1)[:, None]**3
        exact = np.sum(np.cross(points, forces), axis=0)
        q2 = pair_field(body, target, r, q)[2]
        a, b = points@r, np.sum(points**2, axis=1)
        # -dU4/dtheta: U4=-G m sum(w*(35a^4/d^9-30a^2 b/d^7+3b²/d^5))/8.
        q4 = G*target*(mass/6)/8*np.sum((140*a**3/distance**9-60*a*b/distance**7)[:, None]*np.cross(points, r), axis=0)
        residual = np.linalg.norm(q2-exact)/np.linalg.norm(q2)
        corrected = np.linalg.norm(q2+q4-exact)/np.linalg.norm(q2)
        rows.append(dict(distance_m=distance, radius_ratio=distance/600,
            q2_relative_torque_error=float(residual), q2_q4_relative_torque_error=float(corrected),
            reduction_factor=float(residual/corrected)))
    old = rows[2]
    return dict(model="six equal masses at +/- axes, centered and inversion symmetric",
        criterion=dict(radius_ratio=40, error_max=.002, reduction_min=10),
        samples=rows, passed=old["q2_q4_relative_torque_error"] < .002 and old["reduction_factor"] > 10,
        conclusion="Q2 failure is the omitted fourth mass moment for this source; not a wrong Q2 sign/torque",
        limitations="No general Q4 can be reconstructed from the inertia alone; do not apply this synthetic distribution to the Moon")


if __name__ == "__main__":
    path = ROOT/"docs/rotation-limit-diagnosis.json"
    if path.exists():
        raise FileExistsError("Preserve existing diagnosis")
    data = diagnose()
    path.write_text(json.dumps(data, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(data, indent=2))
    sys.exit(0 if data["passed"] else 1)
