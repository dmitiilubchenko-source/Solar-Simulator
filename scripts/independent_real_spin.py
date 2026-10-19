"""Pure LO scalar HSO in the published n/P form; SI, no large orbital H."""
import numpy as np


def hamiltonian(x, v, masses, spin, source, g, c):
    p = np.asarray(masses)[:, None]*v
    value = 0.
    for j in range(len(masses)):
        if j == source:
            continue
        r = x[source]-x[j]; d = np.sqrt(np.dot(r, r)); n = r/d
        value += g/(c*c*d*d)*(1.5*masses[j]/masses[source]*np.dot(np.cross(n, p[source]), spin)
            -2*np.dot(np.cross(n, p[j]), spin))
    return value


def derivatives(x, v, masses, spin, source, g, c):
    h = 1e-20; force = np.empty_like(x); shift = np.empty_like(v)
    for k in range(x.size):
        z = x.astype(complex); z.ravel()[k] += 1j*h
        force.ravel()[k] = -hamiltonian(z, v, masses, spin, source, g, c).imag/h
        z = v.astype(complex); z.ravel()[k] += 1j*h
        shift.ravel()[k] = hamiltonian(x, z, masses, spin, source, g, c).imag/h/masses[k//3]
    omega = np.empty(3)
    for k in range(3):
        z = spin.astype(complex); z[k] += 1j*h
        omega[k] = hamiltonian(x, v, masses, z, source, g, c).imag/h
    return dict(force=force, velocity_shift=shift, omega=omega)
