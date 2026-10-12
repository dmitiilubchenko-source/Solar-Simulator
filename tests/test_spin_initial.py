import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from solar_simulator import orientation
from solar_simulator.rotation import RigidFigure, angular_velocity, rotation_matrix
from solar_simulator.spin_initial import (PROFILE_NAME, PROFILE_SHA256,
                                         from_rotation_rate, lunar_solid_equivalent_initial)

ROOT = Path(__file__).resolve().parents[1]


def test_snapshot_rate_against_independent_column_kinematics():
    # This oracle was produced by independent CSPICE sxform, not the runtime
    # Rz/Rx/Rz implementation. Cross products of columns avoid Rdot R.T.
    source = json.loads((ROOT/"docs/orientation-spice-reference.json").read_text())
    row = next(row for row in source["samples"] if row["time_seconds"] == 0.)
    r, rd = np.array(row["rotation"]), np.array(row["derivative_per_second"])
    expected = .5*sum(np.cross(r[:, i], rd[:, i]) for i in range(3))
    figure, point, initial, data = lunar_solid_equivalent_initial()
    state = from_rotation_rate(figure, data["rotation"], data["rotation_derivative_per_second"])
    assert np.linalg.norm(rotation_matrix(state.quaternion)-r) < 3e-12
    assert np.linalg.norm(np.array(state.angular_velocity)-expected) < 1e-17
    assert np.linalg.norm(angular_velocity(figure, state.quaternion, state.angular_momentum)-expected) < 1e-17
    spin_expected = r@(np.array(figure.moments)*(r.T@expected))
    assert np.linalg.norm(initial[10:]-spin_expected)/np.linalg.norm(spin_expected) < 3e-12


@pytest.mark.parametrize("rotvec, omega", [([.3, -.2, .4], [.2, -.1, .3]),
    ([np.pi, 0, 0], [0, 0, .1]), ([0, np.pi, 0], [0, .2, 0]),
    ([0, 0, np.pi], [.1, 0, 0]), ([0, 0, 0], [0, 0, 0])])
def test_orientation_branches_and_physical_spin(rotvec, omega):
    figure = RigidFigure(1e15, (2e20, 2.5e20, 3e20), 1000.)
    r = Rotation.from_rotvec(rotvec).as_matrix()
    rd = np.column_stack([np.cross(omega, r[:, i]) for i in range(3)])
    state = from_rotation_rate(figure, r, rd)
    assert np.linalg.norm(rotation_matrix(state.quaternion)-r) < 1e-14
    assert np.linalg.norm(np.array(state.angular_velocity)-omega) < 1e-14
    assert np.linalg.norm(angular_velocity(figure, state.quaternion, state.angular_momentum)-omega) < 1e-14


def test_profile_reproducible_and_only_initial_orientation(monkeypatch):
    from scripts.build_lunar_spin import build
    raw = (ROOT/"src/solar_simulator/data"/PROFILE_NAME).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PROFILE_SHA256
    assert raw == (json.dumps(build(), indent=2, ensure_ascii=False)+"\n").encode("utf-8")
    def forbidden(time):
        raise AssertionError("Future/prescribed orientation must not feed a free run")
    monkeypatch.setattr(orientation, "lunar_rotation", forbidden)
    figure, point, initial, data = lunar_solid_equivalent_initial()
    assert initial.shape == (13,) and np.all(np.isfinite(initial))
    assert data["model"] == "rigid-solid-equivalent"
    # Inertia supplies BOTH the quadrupole and rotational kinetic energy.
    ref = data["reference_radius_m"]
    normalized = np.array(figure.moments)/(figure.mass*ref**2)
    assert np.allclose(normalized, [.3926154, .39270511, .39286349], rtol=0, atol=1e-15)
    j2 = (2*normalized[2]-normalized[0]-normalized[1])/2
    c22 = (normalized[1]-normalized[0])/4
    assert j2 == pytest.approx(.000203235, abs=1e-15)
    assert c22 == pytest.approx(.0000224275, abs=1e-15)
    # Deliberately not the existing DE441 nominal field.
    assert j2 != orientation.profile()["figures"]["Moon"]["j2"]


@pytest.mark.parametrize("matrix, derivative", [(np.diag([1., 1., -1.]), np.zeros((3, 3))),
    (2*np.eye(3), np.zeros((3, 3))), (np.eye(3), np.eye(3)*1e-6),
    (np.eye(3), np.full((3, 3), np.nan)), (np.ones(3), np.zeros((3, 3)))])
def test_invalid_rotation_or_nontangent_rate_rejected(matrix, derivative):
    figure = RigidFigure(1e15, (2e20, 2.5e20, 3e20), 1000.)
    with pytest.raises(ValueError):
        from_rotation_rate(figure, matrix, derivative)
