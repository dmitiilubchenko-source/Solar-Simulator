"""Independent inertia-form H derivatives and matrix/body-Euler reference.

Imports the earlier independent EIH-action oracle only, never production
rigid_pn_model, rotation_matrix, Q/force/torque or quaternion differential.
"""
import numpy as np

from scripts.independent_nbody_pn_spin import original_hamiltonian


def hat(vector):
    x, y, z = vector
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def scalar_hamiltonian(orbital, matrix, masses, c, moments, index):
    y = np.asarray(orbital); count = len(masses)
    x, p, s = np.moveaxis(y.reshape(y.shape[:-1]+(3, count, 3)), -3, 0)
    body_spin = np.einsum('...ij,...i->...j', matrix, s[..., index, :])
    result = original_hamiltonian(y, masses, c) + .5*np.sum(body_spin*body_spin/np.array(moments), axis=-1)
    for j in range(count):
        if index == j: continue
        r = x[..., j, :]-x[..., index, :]; d = np.sqrt(np.sum(r*r, axis=-1))
        n_body = np.einsum('...ij,...i->...j', matrix, r/d[..., None])
        result += masses[j]*(3*np.sum(np.array(moments)*n_body*n_body, axis=-1)-sum(moments))/(2*d**3)
    return result


def gradients(orbital, matrix, masses, c, moments, index):
    count = len(orbital); step = 1e-25
    batch = np.tile(np.asarray(orbital, dtype=complex), (count, 1)) + 1j*step*np.eye(count)
    g = scalar_hamiltonian(batch, matrix, masses, c, moments, index).imag/step
    # Left/spatial infinitesimal orientation at fixed inertial S.
    rotations = np.array([(np.eye(3)+1j*step*hat(axis))@matrix for axis in np.eye(3)])
    angle_g = scalar_hamiltonian(orbital, rotations, masses, c, moments, index).imag/step
    return g, angle_g


def orbital_gradient(orbital, matrix, masses, c, moments, index):
    count = len(orbital); step = 1e-25
    batch = np.tile(np.asarray(orbital, dtype=complex), (count, 1)) + 1j*step*np.eye(count)
    return scalar_hamiltonian(batch, matrix, masses, c, moments, index).imag/step


def matrix_rhs(time, state, masses, c, moments, index):
    count = len(masses); y = np.asarray(state); matrix = y[9*count:].reshape(3, 3)
    blocks = y[:9*count].reshape(3, count, 3).copy()
    pi = blocks[2, index].copy(); blocks[2, index] = matrix@pi
    gx, gp, gs = orbital_gradient(blocks.ravel(), matrix, masses, c, moments, index).reshape(3, count, 3)
    flow = np.stack([gp, -gx, np.cross(gs, blocks[2])])
    omega_body = pi/np.array(moments)
    # Direct standard-inertia MacCullagh torque, not production specific Q.
    torque_body = np.zeros(3)
    for j in range(count):
        if index == j: continue
        r = blocks[0, j]-blocks[0, index]; d = np.linalg.norm(r)
        n_body = matrix.T@(r/d)
        torque_body += 3*masses[j]/d**3*np.cross(n_body, np.array(moments)*n_body)
    # SO terms cancel between Euler transport and orientation derivative at
    # fixed body pi. Retain the Newton Euler equation in body coordinates.
    flow[2, index] = np.cross(pi, omega_body)+torque_body
    rotation_rate = hat(gs[index])@matrix
    return np.r_[flow.ravel(), rotation_rate.ravel()]
