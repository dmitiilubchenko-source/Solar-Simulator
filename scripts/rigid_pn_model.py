"""Research finite Hamiltonian: ADM point 1PN/LO SO + Newton rotor/Q2, G=1.

One oriented figure, other bodies have canonical point spins. State is
[x(N,3),p(N,3),S(N,3),q(wxyz)]. This is not a complete PN extended body.
The canonical attitude rate includes the LO SO connection, not just I^-1 S.
"""
from dataclasses import dataclass

import numpy as np

from scripts.nbody_pn_spin import Parameters as PointParameters, geometry
from scripts.nbody_pn_spin import hamiltonian as point_hamiltonian, rhs as point_rhs
from solar_simulator.rotation import RigidFigure, rotation_matrix, quaternion_rate


@dataclass(frozen=True)
class Parameters:
    orbital: PointParameters
    figure: RigidFigure
    index: int

    def __post_init__(self):
        if (not isinstance(self.orbital, PointParameters) or not isinstance(self.figure, RigidFigure)
                or type(self.index) is not int or not 0 <= self.index < len(self.orbital.masses)
                or self.figure.mass != self.orbital.masses[self.index]):
            raise ValueError('One figure must match its orbital mass and index')


def fields(state, parameters):
    count = len(parameters.orbital.masses); y = np.asarray(state, dtype=float)
    if y.shape != (9*count+4,) or not np.all(np.isfinite(y)):
        raise ValueError('Finite canonical x/p/S/q required')
    q = y[-4:]
    # RK stages/initial-step probes need not lie exactly on the q sphere.
    # Use the same orientation representative without modifying raw q.
    if np.linalg.norm(q) == 0:
        raise ValueError('Zero quaternion')
    x, p, s, m, delta, d, potential, u = geometry(y[:-4], parameters.orbital)
    a = parameters.index; figure = parameters.figure
    if d[a].min() <= figure.bounding_radius:
        raise ValueError('Figure expansion only outside its bounding sphere')
    rotation = rotation_matrix(q)
    omega = rotation@((rotation.T@s[a])/figure.moments)
    if (np.linalg.norm(omega)*figure.bounding_radius/parameters.orbital.c)**2 >= 1e-4:
        raise ValueError('Outside slow internal rotation research domain')
    tensor = rotation@figure.quadrupole@rotation.T
    forces = np.zeros_like(p); torque = np.zeros(3); energy = 0.; connection = np.zeros(3)
    for j in range(count):
        if a == j: continue
        r = -delta[a, j]; radius = d[a, j]; n = r/radius
        qn = tensor@n; projection = np.dot(n, qn); coupling = m[a]*m[j]
        force = -coupling*(qn-2.5*projection*n)/radius**4
        forces[j] += force; forces[a] -= force
        torque += coupling*np.cross(n, qn)/radius**3
        energy += coupling*projection/(2*radius**3)
        connection += m[j]*np.cross(delta[a, j], 1.5*u[a]-2*u[j])/(parameters.orbital.c**2*radius**3)
    return y, rotation, omega, connection, energy, forces, torque


def validate_initial(state, parameters):
    y, *_ = fields(state, parameters)
    if abs(np.linalg.norm(y[-4:])-1) > 1e-12:
        raise ValueError('Initial quaternion must be unit')
    return y


def hamiltonian(state, parameters):
    y, rotation, omega, connection, u2, forces, torque = fields(state, parameters)
    s = y[:-4].reshape(3, len(parameters.orbital.masses), 3)[2, parameters.index]
    return point_hamiltonian(y[:-4], parameters.orbital) + .5*np.dot(s, omega) + u2


def rhs(time, state, parameters):
    y, rotation, omega, connection, u2, forces, torque = fields(state, parameters)
    count = len(parameters.orbital.masses)
    flow = point_rhs(time, y[:-4], parameters.orbital).reshape(3, count, 3)
    flow[1] += forces
    flow[2, parameters.index] += torque
    # T_rot's orientation derivative cancels omega x S in the spatial S law.
    # The SO connection remains in BOTH Sdot and attitude evolution.
    return np.r_[flow.ravel(), quaternion_rate(y[-4:], omega+connection)]


def invariants(state, parameters):
    y, *_ = fields(state, parameters)
    x, p, s = y[:-4].reshape(3, len(parameters.orbital.masses), 3)
    return hamiltonian(y, parameters), p.sum(axis=0), (np.cross(x, p)+s).sum(axis=0)
