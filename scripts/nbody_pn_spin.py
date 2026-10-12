"""Research-only ADM N-body Hamiltonian: point-mass 1PN + leading SO, G=1.

State is [positions, canonical momenta, canonical constant-norm spins],
each (N,3). No inertia, orientation, quadrupoles, spin-spin or runtime wiring.
See docs/nbody-pn-spin.md for the explicitly selected finite Hamiltonian.
"""
from dataclasses import dataclass
import math

import numpy as np


@dataclass(frozen=True)
class Parameters:
    masses: tuple
    c: float

    def __post_init__(self):
        if (type(self.masses) is not tuple or len(self.masses) < 2
                or any(type(m) not in (int, float) or not math.isfinite(m) or m <= 0
                       for m in self.masses)):
            raise ValueError('At least two positive finite masses required')
        if (type(self.c) not in (int, float) or not math.isfinite(self.c) or self.c <= 0
                or not math.isfinite(self.c*self.c) or self.c*self.c == 0
                or not math.isfinite(sum(self.masses))):
            raise ValueError('Invalid c or total mass')


def geometry(state, parameters):
    y = np.asarray(state, dtype=float)
    m = np.asarray(parameters.masses)
    if y.shape != (9*len(m),) or not np.all(np.isfinite(y)):
        raise ValueError('Finite N-body x/p/S vectors required')
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        x, p, s = y.reshape(3, len(m), 3)
        delta = x[:, None]-x[None, :]
        d = np.linalg.norm(delta, axis=2)
        np.fill_diagonal(d, np.inf)
        if np.any(d == 0):
            raise ValueError('Coincident positions')
        potential = (1/d)@m
        u = p/m[:, None]
        if max(potential.max(), np.sum(u*u, axis=1).max())/parameters.c**2 >= 1e-4:
            raise ValueError('Outside weak-field/slow-motion research domain')
        if np.any(np.linalg.norm(s, axis=1)/(m*parameters.c*d.min(axis=1)) >= 1e-3):
            raise ValueError('Spin expansion research domain exceeded')
    return x, p, s, m, delta, d, potential, u


def hamiltonian(state, parameters, *, orbital_pn=True, spin_orbit=True):
    x, p, s, m, delta, d, potential, u = geometry(state, parameters)
    u2 = np.sum(u*u, axis=1)
    result = np.sum(m*u2)/2
    correction = -np.sum(m*u2*u2)/8 + np.dot(m, potential*potential)/2
    so = 0.
    for i in range(len(m)):
        for j in range(i+1, len(m)):
            n = delta[i, j]/d[i, j]
            result -= m[i]*m[j]/d[i, j]
            b = 3*(u2[i]+u2[j])-7*np.dot(u[i], u[j])-np.dot(n, u[i])*np.dot(n, u[j])
            correction -= m[i]*m[j]*b/(2*d[i, j])
        for j in range(len(m)):
            if i != j:
                so += m[j]*np.dot(np.cross(delta[i, j], 1.5*u[i]-2*u[j]), s[i])/d[i, j]**3
    return float(result + (correction if orbital_pn else 0.)/parameters.c**2
                 + (so if spin_orbit else 0.)/parameters.c**2)


def rhs(time, state, parameters, *, orbital_pn=True, spin_orbit=True):
    x, p, s, m, delta, d, potential, u = geometry(state, parameters)
    dx = u.copy(); dp = np.zeros_like(p); omega = np.zeros_like(s)
    c2 = parameters.c**2; u2 = np.sum(u*u, axis=1)
    if orbital_pn:
        dx -= .5*u2[:, None]*u/c2
    for i in range(len(m)):
        for j in range(i+1, len(m)):
            radius = d[i, j]; n = delta[i, j]/radius
            force = -m[i]*m[j]*n/radius**2
            if orbital_pn:
                ni, nj = np.dot(n, u[i]), np.dot(n, u[j])
                b = 3*(u2[i]+u2[j])-7*np.dot(u[i], u[j])-ni*nj
                dx[i] -= m[j]*(6*u[i]-7*u[j]-n*nj)/(2*c2*radius)
                dx[j] -= m[i]*(6*u[j]-7*u[i]-n*ni)/(2*c2*radius)
                force -= m[i]*m[j]*((b-2*ni*nj)*n+ni*u[j]+nj*u[i])/(2*c2*radius**2)
                force += m[i]*m[j]*(potential[i]+potential[j])*n/(c2*radius**2)
            dp[i] += force; dp[j] -= force
        if spin_orbit:
            for j in range(len(m)):
                if i == j:
                    continue
                r = delta[i, j]; radius = d[i, j]; w = 1.5*u[i]-2*u[j]
                k = m[j]/(c2*radius**3); product = np.dot(np.cross(r, w), s[i])
                force = -k*(np.cross(w, s[i])-3*product*r/radius**2)
                dp[i] += force; dp[j] -= force
                dx[i] += 1.5*k*np.cross(s[i], r)/m[i]
                dx[j] -= 2*k*np.cross(s[i], r)/m[j]
                omega[i] += k*np.cross(r, w)
    return np.stack([dx, dp, np.cross(omega, s)]).ravel()


def invariants(state, parameters):
    x, p, s, *_ = geometry(state, parameters)
    return (hamiltonian(state, parameters), p.sum(axis=0),
            (np.cross(x, p)+s).sum(axis=0), np.linalg.norm(s, axis=1))
