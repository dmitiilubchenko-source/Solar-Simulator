"""Complex-step Hamiltonian oracle from the unreduced two-body primary expressions.

No analytic RHS, reduced Hamiltonian, SO coefficient or vector identity from
pn_spin_model is imported. Complex derivatives retain holomorphic dot/sqrt.
"""
import numpy as np


def full_hamiltonian(state, mass1, mass2, c):
    r, p, spin = np.asarray(state).reshape(3, 3)
    masses = [mass1, mass2]; momenta = [p, -p]
    positions = [mass2/(mass1+mass2)*r, -mass1/(mass1+mass2)*r]
    energy = 0.
    for i in range(2):
        j = 1-i; pi, pj = momenta[i], momenta[j]; mi, mj = masses[i], masses[j]
        delta = positions[i]-positions[j]; radius = np.sqrt(np.dot(delta, delta)); n = delta/radius
        energy += np.dot(pi, pi)/(2*mi)-mi*mj/(2*radius)
        correction = -np.dot(pi, pi)**2/(8*mi**3)
        correction += mi*mj/(8*radius)*(-12*np.dot(pi, pi)/mi**2
            +14*np.dot(pi, pj)/(mi*mj)+2*np.dot(n, pi)*np.dot(n, pj)/(mi*mj))
        correction += mi*mj*(mi+mj)/(4*radius**2)
        energy += correction/c**2
        if i == 0:
            omega = (1.5*mj/mi*np.cross(n, pi)-2*np.cross(n, pj))/(c**2*radius**2)
            energy += np.dot(omega, spin)
    return energy


def gradient(state, mass1, mass2, c):
    result = np.empty(9)
    for i in range(9):
        y = np.asarray(state, dtype=complex).copy(); y[i] += 1e-25j
        result[i] = full_hamiltonian(y, mass1, mass2, c).imag/1e-25
    return result


def rhs(time, state, mass1, mass2, c):
    g = gradient(state, mass1, mass2, c)
    return np.r_[g[3:6], -g[:3], np.cross(g[6:], state[6:])]
