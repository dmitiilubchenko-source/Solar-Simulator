"""MacCullagh inertia-form derivatives; independent of runtime Q/forces/q.

SI, displacement is point minus figure. Bilinear complex continuation is
used only for differentiation, never complex conjugation or abs in U.
"""
import numpy as np


def hat(vector):
    x, y, z = vector
    return np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])


def potential(displacements, point_masses, moments, matrix, gravitational_constant):
    radius = np.sqrt(np.sum(displacements*displacements, axis=1))
    body_direction = (displacements/radius[:, None])@matrix
    return gravitational_constant*np.sum(point_masses*(
        3*np.sum(body_direction*body_direction*moments, axis=1)-np.sum(moments))/(2*radius**3))


def derivatives(displacements, velocities, point_masses, moments, matrix, omega,
                gravitational_constant):
    """Return point forces, spatial torque, U and directional Udot.

    Source reaction is not manufactured here: callers must explicitly sum
    the opposite point forces. Input velocities are relative to the figure.
    """
    r, v, m, inertia, rotation, w = (np.asarray(x, dtype=float) for x in (
        displacements, velocities, point_masses, moments, matrix, omega))
    if (m.ndim != 1 or not len(m) or r.shape != (len(m), 3) or v.shape != r.shape
            or inertia.shape != (3,) or rotation.shape != (3, 3) or w.shape != (3,)
            or any(not np.isfinite(x).all() for x in (r, v, m, inertia, rotation, w))
            or np.any(m <= 0) or np.any(inertia <= 0) or np.any(np.linalg.norm(r, axis=1) == 0)
            or not np.isfinite(gravitational_constant) or gravitational_constant <= 0
            or np.linalg.norm(rotation.T@rotation-np.eye(3)) > 1e-12
            or abs(np.linalg.det(rotation)-1) > 1e-12):
        raise ValueError('Require finite exterior geometry, positive SI inputs and SO(3)')
    step = 1e-20
    force = np.empty_like(r)
    for j in range(len(m)):
        for k in range(3):
            shifted = r.astype(complex)
            shifted[j, k] += 1j*step
            force[j, k] = -potential(shifted, m, inertia, rotation, gravitational_constant).imag/step
    torque = np.array([-potential(r, m, inertia, (np.eye(3)+1j*step*hat(axis))@rotation,
        gravitational_constant).imag/step for axis in np.eye(3)])
    rate = potential(r+1j*step*v, m, inertia,
        rotation+1j*step*hat(w)@rotation, gravitational_constant).imag/step
    return force, torque, float(potential(r, m, inertia, rotation, gravitational_constant)), float(rate)
