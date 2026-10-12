"""Validate orientation snapshots and convert R/Rdot to conservative q/S.

No future orientation samples are part of a spin initial condition.
"""
from dataclasses import dataclass
import hashlib
from importlib.resources import files
import json

import numpy as np
from scipy.spatial.transform import Rotation

from .rotation import RigidFigure, rotation_matrix
from .simulation import G


@dataclass(frozen=True)
class SpinInitial:
    quaternion: tuple[float, float, float, float]
    angular_momentum: tuple[float, float, float]
    angular_velocity: tuple[float, float, float]


def from_rotation_rate(figure, matrix, derivative):
    """R: body→inertial; Rdot /s. Reject improper/non-tangent matrices.

    omega_hat = Rdot R.T and S = R Ibody R.T omega.
    SO(3) tolerance covers the independently measured CSPICE roundoff;
    malformed input is not silently orthogonalized by SciPy.
    """
    matrix, derivative = np.array(matrix, dtype=float), np.array(derivative, dtype=float)
    if (matrix.shape != (3, 3) or derivative.shape != (3, 3)
            or not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(derivative))):
        raise ValueError("R/Rdot должны быть конечными матрицами 3×3")
    if (np.linalg.norm(matrix.T@matrix-np.eye(3)) > 1e-12
            or abs(np.linalg.det(matrix)-1) > 1e-12):
        raise ValueError("R должна быть собственным ортогональным вращением")
    hat = derivative@matrix.T
    scale = np.linalg.norm(derivative)
    if np.linalg.norm(hat+hat.T) > 1e-12*scale:
        raise ValueError("Rdot не касается SO(3): нарушена кинематика вращения")
    # Antisymmetric extraction cancels permissible roundoff only.
    hat = .5*(hat-hat.T)
    omega = np.array([hat[2, 1], hat[0, 2], hat[1, 0]])
    q = np.roll(Rotation.from_matrix(matrix).as_quat(), 1)
    if q[np.argmax(abs(q))] < 0:
        q = -q
    if np.linalg.norm(rotation_matrix(q)-matrix) > 1e-12:
        raise ValueError("Кватернион не воспроизводит исходное R")
    spin = matrix@(np.array(figure.moments)*(matrix.T@omega))
    return SpinInitial(tuple(map(float, q)), tuple(map(float, spin)), tuple(map(float, omega)))


PROFILE_NAME = "lunar-spin-solid-equivalent-20261008.json"
# Filled from the explicitly built, independently audited one-epoch profile.
PROFILE_SHA256 = "733d91c85c47f991fa7b39dcf66b61efcf62e0990ab74dbf7756af797a4081ba"


def lunar_solid_equivalent_initial():
    """Offline one-epoch model input, not an exact lunar mantle/core state.

    Return rigid figure, Earth point mass, pair state r=Earth−Moon, and
    provenance. No DE441 interpolation is called during loading or evolution.
    """
    raw = files("solar_simulator.data").joinpath(PROFILE_NAME).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise ValueError("Изменён закреплённый начальный профиль вращения Луны")
    data = json.loads(raw)
    if (data["model"] != "rigid-solid-equivalent"
            or data["frame"] != "Ecliptic J2000" or data["epoch_jd_tdb"] != 2461321.5
            or data["units"] != "SI" or data["relative_position"] != "Earth minus Moon"
            or data["gravitational_constant_m3_kg_s2"] != G):
        raise ValueError("Несовместимый научный договор лунного профиля")
    figure = RigidFigure(data["moon_gm_m3_s2"]/G,
        tuple(data["moments_kg_m2"]), data["exclusion_radius_m"])
    state = from_rotation_rate(figure, data["rotation"], data["rotation_derivative_per_second"])
    initial = np.concatenate((data["earth_minus_moon_position_m"], data["earth_minus_moon_velocity_m_s"],
                               state.quaternion, state.angular_momentum))
    return figure, data["earth_gm_m3_s2"]/G, initial, data
