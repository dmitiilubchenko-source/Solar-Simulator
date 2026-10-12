"""Independent scalar-H complex gradients and raw matrix/body-Euler oracle.

No production multipole, rotation, force, torque or quaternion functions.
SI. Body spin Pi; r/p in local frame; R body -> local, never projected.
"""
import numpy as np


def hat(v):
    x, y, z = v
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def scalar(orbital_spin, matrix, parameters):
    r, p, s = np.asarray(orbital_spin).reshape(3, 3)
    distance = np.sqrt(r@r)
    rb = matrix.T@r; pi = matrix.T@s
    a, b, g = parameters.figure_mass, parameters.point_mass, parameters.gravitational_constant
    mu = a*b/(a+b)
    return (p@p/(2*mu)-g*a*b/distance
            +.5*pi@np.linalg.solve(np.asarray(parameters.inertia_body), pi)
            -1.5*g*b*(rb@np.asarray(parameters.multipole_body)@rb)/distance**5)


def gradients(orbital_spin, matrix, parameters):
    step = 1e-25; y = np.asarray(orbital_spin, dtype=complex)
    gradient = np.empty(9)
    for k in range(9):
        probe = y.copy(); probe[k] += 1j*step
        gradient[k] = scalar(probe, matrix, parameters).imag/step
    orientation = np.array([scalar(y, (np.eye(3)+1j*step*hat(axis))@matrix,
                                   parameters).imag/step for axis in np.eye(3)])
    return gradient, orientation


def matrix_rhs(time, state, parameters):
    y = np.asarray(state); r, p, pi = y[:9].reshape(3, 3); matrix = y[9:].reshape(3, 3)
    spatial = np.r_[r, p, matrix@pi]
    gradient, orientation = gradients(spatial, matrix, parameters)
    gx, gp, gs = gradient.reshape(3, 3)
    spin_rate = np.cross(gs, spatial[6:9])-orientation
    body_omega = np.linalg.solve(np.asarray(parameters.inertia_body), pi)
    pi_rate = matrix.T@spin_rate-np.cross(body_omega, pi)
    return np.r_[gp, -gx, pi_rate, (hat(matrix@body_omega)@matrix).ravel()]
