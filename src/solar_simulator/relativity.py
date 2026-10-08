"""Order-reduced Einstein–Infeld–Hoffmann dynamics in harmonic coordinates.

All massive point particles contribute, including three-body potential terms.
Keep terms through c^-2 only: source accelerations in the correction are
Newtonian. No spin, radiation reaction, extended bodies, or strong fields.
Equations and the EIH Lagrangian: see docs/relativity.md (primary sources).
"""
from math import fsum, isfinite

import numpy as np

from .simulation import G
from .vector3 import Vector3

C = 299_792_458.0  # Exact SI speed of light, m/s.
WEAK_FIELD_LIMIT = 1e-4  # Application domain guard, not an accuracy guarantee.


def _geometry(positions, velocities, masses, c):
    p, v, m = (np.asarray(value, dtype=float) for value in (positions, velocities, masses))
    if (m.ndim != 1 or not m.size or p.shape != (m.size, 3) or v.shape != p.shape
            or not all(np.all(np.isfinite(value)) for value in (p, v, m)) or np.any(m <= 0)):
        raise ValueError("Нужны конечные координаты, скорости и положительные массы")
    if type(c) not in (int, float) or not isfinite(c) or c <= 0 or not isfinite(c*c) or c*c == 0:
        raise ValueError("Неверная скорость света")
    # x_ij points from source j to target i; self interactions are excluded.
    x = p[:, None, :]-p[None, :, :]
    r = np.linalg.norm(x, axis=2)
    np.fill_diagonal(r, np.inf)
    if np.any(r == 0):
        raise ValueError("Совпадающие положения: гравитация не определена")
    inverse = 1/r
    mu = G*m
    potential = np.sum(mu[None, :]*inverse, axis=1)
    speed2 = np.sum(v*v, axis=1)
    if max(float(potential.max()), float(speed2.max()))/(c*c) >= WEAK_FIELD_LIMIT:
        raise ValueError("1PN требует слабого поля и малых скоростей: U/c² и v²/c² < 1e-4")
    newton = -np.sum(x*(mu[None, :]*inverse**3)[:, :, None], axis=1)
    return x, inverse, mu, potential, speed2, newton, v, m


def eih_acceleration(positions, velocities, masses, *, c=C):
    """Full N-body acceleration to 1PN order, in the supplied fixed frame.

    Velocities must belong to that frame; subtracting a fresh COM velocity
    at each checkpoint would change a velocity-dependent force law.
    The optional c is for dimensional/limiting checks, not a GUI setting.
    """
    try:
        return _eih_acceleration(positions, velocities, masses, c)
    except FloatingPointError as error:
        raise ValueError("Переполнение при расчёте 1PN") from error


def _eih_acceleration(positions, velocities, masses, c):
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        x, inv, mu, u, speed2, newton, v, _ = _geometry(positions, velocities, masses, c)
        x_vj = np.einsum("ijk,jk->ij", x, v)
        x_aj = np.einsum("ijk,jk->ij", x, newton)
        scalar = (4*u[:, None]+u[None, :]-speed2[:, None]-2*speed2[None, :]
                  +4*(v@v.T)+1.5*(x_vj*inv)**2+0.5*x_aj)
        radial = x*(mu[None, :]*inv**3*scalar)[:, :, None]
        dv = v[:, None, :]-v[None, :, :]
        dot = np.sum(x*(4*v[:, None, :]-3*v[None, :, :]), axis=2)
        velocity = dv*(mu[None, :]*inv**3*dot)[:, :, None]
        source = 3.5*newton[None, :, :]*(mu[None, :]*inv)[:, :, None]
        return newton+np.sum(radial+velocity+source, axis=1)/(c*c)


def validate_bodies(bodies):
    if any(b.radius != 0 or b.spin.magnitude() != 0 for b in bodies):
        raise ValueError("1PN поддерживает точечные тела без радиусов и вращения")
    eih_acceleration([[b.position.x, b.position.y, b.position.z] for b in bodies],
                     [[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies],
                     [b.mass for b in bodies])


def invariants(bodies):
    """EIH Noether E, P, L through 1PN; rest-mass energy is excluded.

    These are conserved to the retained order, with O(c^-4) truncation
    residuals. Newtonian COM and sum(m*v) are not 1PN invariants.
    """
    validate_bodies(bodies)
    p = np.array([[b.position.x, b.position.y, b.position.z] for b in bodies])
    v = np.array([[b.velocity.x, b.velocity.y, b.velocity.z] for b in bodies])
    m = np.array([b.mass for b in bodies])
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        x, inv, mu, u, speed2, _, v, m = _geometry(p, v, m, C)
        n = x*inv[:, :, None]
        n_vi = np.einsum("ijk,ik->ij", n, v)
        n_vj = np.einsum("ijk,jk->ij", n, v)
        pair = m[:, None]*mu[None, :]*inv
        velocity_term = 3*(speed2[:, None]+speed2[None, :])-7*(v@v.T)-n_vi*n_vj
        energy = fsum(0.5*m*speed2-0.5*m*u)
        energy += (fsum(0.375*m*speed2**2+0.5*m*u**2)
                   +0.25*fsum((pair*velocity_term).ravel()))/(C*C)
        canonical = m[:, None]*v*(1+0.5*speed2[:, None]/(C*C))
        canonical += np.sum(pair[:, :, None]*(6*v[:, None, :]-7*v[None, :, :]
                           -n*n_vj[:, :, None]), axis=1)/(2*C*C)
        momentum = [fsum(canonical[:, k]) for k in range(3)]
        cross = np.cross(p, canonical)
        angular = [fsum(cross[:, k]) for k in range(3)]
    if not all(isfinite(value) for value in [energy]+momentum+angular):
        raise ValueError("Переполнение диагностики 1PN")
    return energy, Vector3(*momentum), Vector3(*angular)
