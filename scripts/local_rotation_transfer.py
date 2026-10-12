"""Canonical SO(3) and clock transfer of the closed SI multipole model.

Local -> target: r,p,S,R rotate by supplied B(t), T'=rate>0.
K=rate*h+W_basis.J. This is not a Lorentz/SSC/metric-spin transformation,
nor compatible quantity scaling. Masses/C/M/SI units stay unchanged.
"""
from dataclasses import dataclass
import math

import numpy as np

from scripts import local_multipole as model
from solar_simulator.rotation import quaternion_rate, rotation_matrix


def hat(v):
    x, y, z = v
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


@dataclass(frozen=True)
class Boundary:
    basis: tuple
    basis_derivative: tuple
    clock_rate: float
    clock_acceleration: float
    basis_acceleration: tuple

    def __post_init__(self):
        b = model.finite(self.basis, (3, 3), 'basis')
        d = model.finite(self.basis_derivative, (3, 3), 'basis derivative')
        a = model.finite(self.basis_acceleration, (3,), 'basis acceleration')
        if (np.linalg.norm(b.T@b-np.eye(3)) > 1e-12
                or abs(np.linalg.det(b)-1) > 1e-12):
            raise ValueError('Explicit proper SO(3) basis required, not a metric spin root')
        h = d@b.T
        if np.linalg.norm(h+h.T) > 1e-12*np.linalg.norm(d):
            raise ValueError('Tangent SO(3) basis derivative required')
        if (type(self.clock_rate) not in (int, float) or not math.isfinite(self.clock_rate)
                or self.clock_rate <= 0):
            raise ValueError('Explicit positive finite clock rate required')
        if (type(self.clock_acceleration) not in (int, float)
                or not math.isfinite(self.clock_acceleration)):
            raise ValueError('Explicit finite clock acceleration required')
        for name, value in (('basis', b), ('basis_derivative', d)):
            object.__setattr__(self, name, tuple(tuple(row) for row in value))
        object.__setattr__(self, 'basis_acceleration', tuple(a))

    @property
    def omega(self):
        h = np.asarray(self.basis_derivative)@np.asarray(self.basis).T
        return .5*np.array([h[2, 1]-h[1, 2], h[0, 2]-h[2, 0], h[1, 0]-h[0, 1]])


def require_boundary(boundary):
    if not isinstance(boundary, Boundary):
        raise ValueError('Supplied clock/basis Boundary required')


def quaternion_product(a, b):
    """Hamilton product, active rotation; no normalization or sign choice."""
    a = model.finite(a, (4,), 'left q'); b = model.finite(b, (4,), 'right q')
    return np.r_[a[0]*b[0]-a[1:]@b[1:], a[0]*b[1:]+b[0]*a[1:]+np.cross(a[1:], b[1:])]


def map_state(state, parameters, boundary, basis_quaternion, *, inverse=False):
    """Rotate canonical variables. Explicit q_B fixes the lift/sign of B.

    Unit q_B must represent B, including on inverse mapping. Raw q in the
    state is multiplied, never projected; changing q_B sign changes its lift.
    """
    require_boundary(boundary)
    if type(inverse) is not bool:
        raise ValueError('Explicit boolean inverse selector required')
    y = model.fields(state, parameters)[0]
    qb = model.finite(basis_quaternion, (4,), 'basis quaternion')
    if abs(np.linalg.norm(qb)-1) > 1e-12:
        raise ValueError('Unit basis quaternion required')
    b = np.asarray(boundary.basis)
    if np.linalg.norm(rotation_matrix(qb)-b) > 1e-12:
        raise ValueError('Basis quaternion must represent the supplied basis')
    if inverse:
        b = b.T; qb = qb*np.array([1., -1., -1., -1.])
    out = np.r_[(b@y[:9].reshape(3, 3).T).T.ravel(), quaternion_product(qb, y[9:])]
    model.fields(out, parameters)
    return out


def hamiltonian(state, parameters, boundary):
    require_boundary(boundary)
    h, j = model.invariants(state, parameters)
    value = float(boundary.clock_rate*h+boundary.omega@j)
    if not math.isfinite(value):
        raise ValueError('Nonfinite transformed Hamiltonian')
    return value


def rhs(time, state, parameters, boundary):
    require_boundary(boundary)
    y, _, _, _, w, force, torque, _ = model.fields(state, parameters)
    wb, rate = boundary.omega, boundary.clock_rate
    flow = np.r_[rate*y[3:6]/parameters.reduced_mass+np.cross(wb, y[:3]),
                 rate*force+np.cross(wb, y[3:6]),
                 rate*torque+np.cross(wb, y[6:9]),
                 quaternion_rate(y[9:], rate*w+wb)]
    if not np.all(np.isfinite(flow)):
        raise ValueError('Nonfinite transformed flow')
    return flow


def from_target_rates(displacement, velocity, quaternion, attitude_rate, parameters, boundary):
    """Invert target vg and Wg; do not assign p=mu vg or S=C Wg."""
    require_boundary(boundary)
    if not isinstance(parameters, model.Parameters):
        raise ValueError('Local multipole parameters required')
    r = model.finite(displacement, (3,), 'displacement')
    v = model.finite(velocity, (3,), 'target velocity')
    q = model.finite(quaternion, (4,), 'target quaternion')
    w = model.finite(attitude_rate, (3,), 'target attitude rate')
    rotation = rotation_matrix(q); wb = boundary.omega; rate = boundary.clock_rate
    p = parameters.reduced_mass*(v-np.cross(wb, r))/rate
    s = rotation@np.asarray(parameters.inertia_body)@rotation.T@(w-wb)/rate
    return model.validate_initial(np.r_[r, p, s, q], parameters)


def explicit_power(state, parameters, boundary):
    """Partial dK/dt at fixed target state, not a physical dissipation rate."""
    require_boundary(boundary)
    h, j = model.invariants(state, parameters)
    value = float(boundary.clock_acceleration*h+np.asarray(boundary.basis_acceleration)@j)
    if not math.isfinite(value):
        raise ValueError('Nonfinite transformed power')
    return value


def local_invariants(state, parameters, boundary):
    """h and B^T Jg are constant; K and Jg generally are not."""
    require_boundary(boundary)
    h, j = model.invariants(state, parameters)
    return h, np.asarray(boundary.basis).T@j
