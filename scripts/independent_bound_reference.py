"""Independent Newton Hamiltonian gradient / equilateral radial oracle, SI.

Only numpy; no production forces/diagnostics/rotation_split imports.
Uses holomorphic squared distance (no complex conjugate) for complex step.
"""
import numpy as np


def hamiltonian(state, masses, links, g):
    n = len(masses); z = np.asarray(state).reshape(*np.shape(state)[:-1], 2, n, 3)
    x, p = z[..., 0, :, :], z[..., 1, :, :]; m = np.asarray(masses)
    value = .5*np.sum(p*p/m[:, None], axis=(-2, -1))
    for i in range(n):
        for j in range(i+1, n):
            q = x[..., j, :]-x[..., i, :]
            value -= g*m[i]*m[j]/np.sqrt(np.sum(q*q, axis=-1))
    for i, j, k, length in links:
        q = x[..., j, :]-x[..., i, :]
        value += .5*k*(np.sqrt(np.sum(q*q, axis=-1))-length)**2
    return value


def gradient(state, masses, links, g):
    z = np.asarray(state); step = 1e-20
    probes = z[None, :]+1j*step*np.eye(len(z))
    return hamiltonian(probes, masses, links, g).imag/step


def cartesian_rhs(unit_time, state, masses, links, g, duration, length_scale, momentum_scale):
    n = len(masses); scale = np.r_[np.full(3*n, length_scale), np.full(3*n, momentum_scale)]
    derivative = gradient(state*scale, masses, links, g)
    return duration*np.r_[derivative[3*n:]/length_scale, -derivative[:3*n]/momentum_scale]


def radial_rhs(unit_time, state, mass, stiffness, rest_length, g, ell, duration, length_scale, velocity_scale):
    radius = state[0]*length_scale; speed = state[1]*velocity_scale
    acceleration = ell**2/radius**3-g*mass/(np.sqrt(3)*radius**2)-3*stiffness*(radius-rest_length/np.sqrt(3))/mass
    return duration*np.array([speed/length_scale, acceleration/velocity_scale, ell/radius**2])


def radial_cartesian(states, mass, ell, length_scale, velocity_scale, momentum_scale):
    radius = states[:, 0]*length_scale; speed = states[:, 1]*velocity_scale
    angle = states[:, 2, None]+2*np.pi*np.arange(3)[None, :]/3
    e = np.stack([np.cos(angle), np.sin(angle), np.zeros_like(angle)], axis=-1)
    tangent = np.stack([-np.sin(angle), np.cos(angle), np.zeros_like(angle)], axis=-1)
    x = radius[:, None, None]*e
    p = mass*(speed[:, None, None]*e+(ell/radius)[:, None, None]*tangent)
    return np.c_[x.reshape(len(states), -1)/length_scale, p.reshape(len(states), -1)/momentum_scale]
