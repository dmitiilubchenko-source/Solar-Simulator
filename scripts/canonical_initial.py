"""Research initial-data tools for the finite rigid Hamiltonian of change 57.

G=1 model units. Inputs x/v/R/W must ALREADY use the selected canonical
centres, Euclidean spin basis and coordinate time. No JPL/legacy migration.
The metric-spin and LO centre-shift utilities have separate explicit scopes.
"""
from dataclasses import dataclass
import math

import numpy as np

from scripts.nbody_pn_spin import geometry, rhs as point_rhs
from scripts.rigid_pn_model import fields, validate_initial
from solar_simulator.rotation import rotation_matrix


def finite_array(value, shape, name):
    result = np.array(value, dtype=float, copy=True)
    if result.shape != shape or not np.all(np.isfinite(result)):
        raise ValueError(f'{name}: finite array of shape {shape} required')
    return result


@dataclass(frozen=True)
class SIUnits:
    """Explicit M0/L0/G; T0=sqrt(L0^3/(G M0)), not a time-scale conversion."""
    mass_kg: float
    length_m: float
    gravitational_constant: float

    def __post_init__(self):
        base = (self.mass_kg, self.length_m, self.gravitational_constant)
        if any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0 for v in base):
            raise ValueError('Positive finite SI base scales required')
        try:
            values = (self.time_s, self.velocity_m_s, self.momentum_kg_m_s,
                      self.spin_kg_m2_s, self.inertia_kg_m2)
        except (OverflowError, ZeroDivisionError) as error:
            raise ValueError('SI scales are not representable') from error
        if any(not math.isfinite(v) or v <= 0 for v in values):
            raise ValueError('Positive finite, representable SI unit scales required')

    @property
    def time_s(self):
        return math.sqrt(self.length_m**3/(self.gravitational_constant*self.mass_kg))

    @property
    def velocity_m_s(self):
        return self.length_m/self.time_s

    @property
    def momentum_kg_m_s(self):
        return self.mass_kg*self.velocity_m_s

    @property
    def spin_kg_m2_s(self):
        return self.mass_kg*self.length_m*self.velocity_m_s

    @property
    def inertia_kg_m2(self):
        return self.mass_kg*self.length_m**2


def kinematics(state, parameters):
    """Canonical-centre dx/dt and spatial attitude W, not harmonic velocity."""
    y, _, intrinsic, connection, *_ = fields(state, parameters)
    count = len(parameters.orbital.masses)
    velocity = point_rhs(0., y[:-4], parameters.orbital).reshape(3, count, 3)[0]
    return velocity, intrinsic+connection


def from_velocities_and_rate(positions, velocities, quaternion, attitude_rate,
                             point_spins, parameters, *, velocity_scales,
                             rate_scale, tolerance=1e-13, max_iterations=12):
    """Solve v=H_p and W=I^-1 S+Omega(p) on the weak-field branch.

    Fixed-point iteration in u=p/m and S=I(W-Omega); each candidate is
    checked against the actual finite-H kinematics. No order-reduced p=m v,
    norm projection, frame boost, or fallback. Zero target speeds are allowed
    with explicitly supplied positive per-body velocity scales.
    point_spins[figure] MUST be zero; that slot is solved, never ignored.
    """
    count = len(parameters.orbital.masses); a = parameters.index
    x = finite_array(positions, (count, 3), 'positions')
    v = finite_array(velocities, (count, 3), 'velocities')
    q = finite_array(quaternion, (4,), 'quaternion')
    w = finite_array(attitude_rate, (3,), 'attitude rate')
    s = finite_array(point_spins, (count, 3), 'point spins')
    scales = finite_array(velocity_scales, (count,), 'velocity scales')
    if (np.any(scales <= 0) or not math.isfinite(rate_scale) or rate_scale <= 0
            or not math.isfinite(tolerance) or not 0 < tolerance < 1
            or type(max_iterations) is not int or max_iterations < 1):
        raise ValueError('Positive scales/tolerance and integer iteration limit required')
    if np.any(s[a] != 0):
        raise ValueError('The figure spin is an unknown; supply zero in its input slot')
    r = rotation_matrix(q); inertia = np.asarray(parameters.figure.moments)
    apply_inertia = lambda vector: r@(inertia*(r.T@vector))
    s[a] = apply_inertia(w)
    m = np.asarray(parameters.orbital.masses)[:, None]; p = m*v
    y = np.r_[np.stack([x, p, s]).ravel(), q]
    validate_initial(y, parameters)
    for iteration in range(max_iterations+1):
        y = np.r_[np.stack([x, p, s]).ravel(), q]
        actual_v, actual_w = kinematics(y, parameters)
        residual_v = float(np.max(np.linalg.norm(actual_v-v, axis=1)/scales))
        residual_w = float(np.linalg.norm(actual_w-w)/rate_scale)
        if max(residual_v, residual_w) <= tolerance:
            return y, dict(iterations=iteration, velocity_residual=residual_v,
                           attitude_rate_residual=residual_w)
        if iteration == max_iterations:
            raise ValueError(f'Canonical inversion did not converge: v={residual_v}, W={residual_w}')
        p = m*(v-(actual_v-p/m))
        probe = np.r_[np.stack([x, p, s]).ravel(), q]
        connection = fields(probe, parameters)[3]
        s[a] = apply_inertia(w-connection)
    raise AssertionError('Unreachable iteration exit')


def local_spin_root(inverse_metric, velocity_over_c):
    """DJS (2008), (8)-(10): S=sqrt(G) S_tilde, covariant spatial spin.

    Coordinates x0=c t, signature (-+++); G is positive on a timelike
    trajectory. This matrix acts on spin components, NOT on a body attitude.
    The metric is supplied, not silently inferred from a Newtonian profile.
    """
    metric = finite_array(inverse_metric, (4, 4), 'inverse metric')
    beta = finite_array(velocity_over_c, (3,), 'velocity/c')
    if np.linalg.norm(metric-metric.T) > 1e-12*np.linalg.norm(metric):
        raise ValueError('Symmetric inverse metric required')
    eigen = np.linalg.eigvalsh(metric)
    if (np.count_nonzero(eigen < 0) != 1 or np.count_nonzero(eigen > 0) != 3
            or metric[0, 0] >= 0):
        raise ValueError('Lorentzian inverse metric with spacelike t slices required')
    tangent = np.r_[1., beta]
    if tangent@np.linalg.solve(metric, tangent) >= 0:
        raise ValueError('Timelike coordinate trajectory required')
    spatial = (metric[1:, 1:]-np.outer(metric[0, 1:], beta)
               -np.outer(beta, metric[0, 1:])+metric[0, 0]*np.outer(beta, beta))
    values, vectors = np.linalg.eigh(spatial)
    if np.any(values <= 0):
        raise ValueError('Positive spin metric required')
    return (vectors*np.sqrt(values))@vectors.T, spatial


def leading_centre_shift(state, parameters):
    """LO covariant/harmonic minus canonical centre, DJS (58), G=1.

    Linear spin at c^-2 only; not the full PN-Q2 coordinate transformation.
    """
    _, p, s, m, *_ = geometry(state, parameters)
    return np.cross(s, p)/(2*m[:, None]**2*parameters.c**2)


def leading_centre_shift_rate(state, flow, parameters):
    """Derivative along a SUPPLIED flow; retain its mixed higher-order terms."""
    _, p, s, m, *_ = geometry(state, parameters)
    f = finite_array(flow, (len(state),), 'flow').reshape(3, len(m), 3)
    return (np.cross(f[2], p)+np.cross(s, f[1]))/(2*m[:, None]**2*parameters.c**2)
