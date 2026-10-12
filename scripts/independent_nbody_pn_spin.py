"""Complex-step oracle: Legendre-transformed EIH action + published LO Omega.

No production Hamiltonian, geometry or analytic field is imported. The EIH
ordered triple uses r_AB*r_BC, including C=A, unlike production U_A squared.
All 9N complex perturbations are evaluated as a batch for practical RK45 cost.
"""
import numpy as np


def original_hamiltonian(states, masses, c, *, omit_distinct_triples=False):
    y = np.asarray(states); count = len(masses)
    x, p, s = np.moveaxis(y.reshape(y.shape[:-1]+(3, count, 3)), -3, 0)
    v = p/np.asarray(masses)[:, None]
    energy = np.sum(p*v, axis=(-2, -1))/2
    lagrangian1 = np.sum(np.asarray(masses)*np.sum(v*v, axis=-1)**2, axis=-1)/8
    spin_energy = 0.
    distances = {}
    for a in range(count):
        for b in range(count):
            if a == b:
                continue
            r = x[..., a, :]-x[..., b, :]
            radius = np.sqrt(np.sum(r*r, axis=-1)); distances[a, b] = radius
            n = r/radius[..., None]; va, vb = v[..., a, :], v[..., b, :]
            energy -= masses[a]*masses[b]/(2*radius)
            bracket = (3*np.sum(va*va, axis=-1)+3*np.sum(vb*vb, axis=-1)
                       -7*np.sum(va*vb, axis=-1)
                       -np.sum(va*n, axis=-1)*np.sum(vb*n, axis=-1))
            lagrangian1 += masses[a]*masses[b]*bracket/(4*radius)
            omega = (1.5*masses[b]/masses[a]*np.cross(n, p[..., a, :])
                     -2*np.cross(n, p[..., b, :]))/radius[..., None]**2
            spin_energy += np.sum(omega*s[..., a, :], axis=-1)
    for a in range(count):
        for b in range(count):
            if a == b:
                continue
            for k in range(count):
                if k != b and not (omit_distinct_triples and k != a):
                    lagrangian1 -= masses[a]*masses[b]*masses[k]/(2*distances[a, b]*distances[b, k])
    # To first PN order H1(x,p)=-L1(x,v=p/m); do not invert v numerically here.
    return energy + (-lagrangian1+spin_energy)/c**2


def gradient(state, masses, c, *, omit_distinct_triples=False):
    perturbations = np.tile(np.asarray(state, dtype=complex), (len(state), 1))
    perturbations += 1e-25j*np.eye(len(state))
    return original_hamiltonian(perturbations, masses, c,
        omit_distinct_triples=omit_distinct_triples).imag/1e-25


def rhs(time, state, masses, c):
    dx, dp, ds = gradient(state, masses, c).reshape(3, len(masses), 3)
    spin = np.asarray(state).reshape(3, len(masses), 3)[2]
    return np.stack([dp, -dx, np.cross(ds, spin)]).ravel()
