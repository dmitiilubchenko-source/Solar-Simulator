"""Research closed SI pair: effective rigid inertia and independent STF M2.

Leading monopole/M2 Hamiltonian only, not a complete PN extended body.
State [relative r, canonical p, spatial S, raw q(wxyz)], body -> local.
No density realizability, PN inertia values, SSC or lunar frame is inferred.
"""
from dataclasses import dataclass
import math

import numpy as np

from solar_simulator.rotation import quaternion_rate, rotation_matrix


def finite(value, shape, name):
    try:
        original = np.asarray(value)
        if original.dtype.kind not in 'fiu':
            raise ValueError(f'{name}: real numeric values required')
        out = np.array(value, dtype=float, copy=True)
    except (TypeError, OverflowError) as error:
        raise ValueError(f'{name}: finite real array required') from error
    if out.shape != shape or not np.all(np.isfinite(out)):
        raise ValueError(f'{name}: finite shape {shape} required')
    return out


def symmetric(value, name, *, trace_free=False):
    out = finite(value, (3, 3), name)
    scale = np.linalg.norm(out)
    if np.linalg.norm(out-out.T) > 1e-12*scale:
        raise ValueError(f'{name}: symmetric tensor required')
    if trace_free and abs(np.trace(out)) > 1e-12*scale:
        raise ValueError(f'{name}: STF tensor required')
    # Check, never silently symmetrize or remove a trace.
    return out


@dataclass(frozen=True)
class Parameters:
    figure_mass: float
    point_mass: float
    gravitational_constant: float
    inertia_body: tuple
    multipole_body: tuple
    minimum_distance: float

    def __post_init__(self):
        for value in (self.figure_mass, self.point_mass,
                      self.gravitational_constant, self.minimum_distance):
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise ValueError('Positive finite SI parameters required')
        c = symmetric(self.inertia_body, 'inertia')
        m = symmetric(self.multipole_body, 'multipole', trace_free=True)
        if np.any(np.linalg.eigvalsh(c) <= 0):
            raise ValueError('Positive definite inertia required')
        object.__setattr__(self, 'inertia_body', tuple(tuple(row) for row in c))
        object.__setattr__(self, 'multipole_body', tuple(tuple(row) for row in m))
        values = (self.reduced_mass,
                  self.gravitational_constant*self.figure_mass*self.point_mass)
        if any(not np.isfinite(v) or v <= 0 for v in values):
            raise ValueError('Unrepresentable pair parameters')

    @property
    def reduced_mass(self):
        small, large = sorted((self.figure_mass, self.point_mass))
        return small/(1+small/large)


def fields(state, parameters):
    if not isinstance(parameters, Parameters):
        raise ValueError('Local multipole parameters required')
    y = finite(state, (13,), 'r/p/S/q')
    r, p, s, q = y[:3], y[3:6], y[6:9], y[9:]
    radius = np.linalg.norm(r)
    if not np.isfinite(radius) or radius <= parameters.minimum_distance:
        raise ValueError('Pair outside declared minimum distance required')
    rotation = rotation_matrix(q)
    c = rotation@np.asarray(parameters.inertia_body)@rotation.T
    m = rotation@np.asarray(parameters.multipole_body)@rotation.T
    omega = rotation@np.linalg.solve(np.asarray(parameters.inertia_body), rotation.T@s)
    n = r/radius; mn = m@n; projection = n@mn
    g, a, b = parameters.gravitational_constant, parameters.figure_mass, parameters.point_mass
    force = -g*a*b*n/radius**2 + 3*g*b*(mn-2.5*projection*n)/radius**4
    torque = -3*g*b*np.cross(n, mn)/radius**3
    potential = -g*a*b/radius-1.5*g*b*projection/radius**3
    if not np.all(np.isfinite(np.r_[c.ravel(), m.ravel(), omega, force, torque, potential])):
        raise ValueError('Nonfinite multipole fields')
    return y, rotation, c, m, omega, force, torque, float(potential)


def validate_initial(state, parameters):
    y = fields(state, parameters)[0]
    if abs(np.linalg.norm(y[9:])-1) > 1e-12:
        raise ValueError('Unit initial raw quaternion required')
    return y


def hamiltonian(state, parameters):
    y, _, _, _, omega, _, _, potential = fields(state, parameters)
    value = y[3:6]@y[3:6]/(2*parameters.reduced_mass)+.5*(y[6:9]@omega)+potential
    if not np.isfinite(value):
        raise ValueError('Nonfinite Hamiltonian')
    return float(value)


def rhs(time, state, parameters):
    y, _, _, _, omega, force, torque, _ = fields(state, parameters)
    flow = np.r_[y[3:6]/parameters.reduced_mass, force, torque, quaternion_rate(y[9:], omega)]
    if not np.all(np.isfinite(flow)):
        raise ValueError('Nonfinite multipole flow')
    return flow


def invariants(state, parameters):
    y = fields(state, parameters)[0]
    return hamiltonian(y, parameters), np.cross(y[:3], y[3:6])+y[6:9]
