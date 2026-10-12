"""Independent complex-step scalar H in Jacobi variables, matrix/body Euler.

Uses the original EIH scalar action implementation, a second-body geometry
anchor, and direct standard-inertia torque. No production transforms/RHS.
"""
import numpy as np

from scripts.independent_rigid_pn import scalar_hamiltonian, hat


def physical_blocks(orbital, masses, first, second):
    values = np.asarray(orbital)
    b = values.reshape(values.shape[:-1]+(3, len(masses), 3)).copy()
    mass = masses[first]+masses[second]; a = masses[first]/mass; d = masses[second]/mass
    centre = b[..., 0, first, :].copy(); relative = b[..., 0, second, :].copy()
    total = b[..., 1, first, :].copy(); internal = b[..., 1, second, :].copy()
    b[..., 0, :, :] -= centre[..., None, :]+a*relative[..., None, :]
    b[..., 0, first, :] = -relative; b[..., 0, second, :] = 0.
    b[..., 1, first, :] = a*total-internal
    b[..., 1, second, :] = d*total+internal
    return b


def scalar(orbital, matrix, masses, c, moments, figure, first, second):
    b = physical_blocks(orbital, masses, first, second)
    return scalar_hamiltonian(b.reshape(b.shape[:-3]+(9*len(masses),)), matrix, masses, c, moments, figure)


def gradients(orbital, matrix, masses, c, moments, figure, first, second):
    size = len(orbital); step = 1e-25
    batch = np.tile(np.asarray(orbital, dtype=complex), (size, 1))+1j*step*np.eye(size)
    return scalar(batch, matrix, masses, c, moments, figure, first, second).imag/step


def matrix_rhs(time, state, masses, c, moments, figure, first, second):
    count = len(masses); rotation = state[9*count:].reshape(3, 3)
    b = state[:9*count].reshape(3, count, 3).copy()
    pi = b[2, figure].copy(); b[2, figure] = rotation@pi
    gx, gp, gs = gradients(b.ravel(), rotation, masses, c, moments, figure, first, second).reshape(3, count, 3)
    flow = np.stack([gp, -gx, np.cross(gs, b[2])])
    geometry = physical_blocks(b.ravel(), masses, first, second)[0]
    torque = np.zeros(3)
    for j in range(count):
        if j == figure: continue
        relative = geometry[j]-geometry[figure]; radius = np.linalg.norm(relative)
        normal = rotation.T@(relative/radius)
        torque += 3*masses[j]/radius**3*np.cross(normal, np.asarray(moments)*normal)
    flow[2, figure] = np.cross(pi, pi/np.asarray(moments))+torque
    return np.r_[flow.ravel(), (hat(gs[figure])@rotation).ravel()]
