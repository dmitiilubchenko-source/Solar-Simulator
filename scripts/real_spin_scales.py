"""SI diagnostic amplitudes; never a new application force or error bound."""
import numpy as np

from scripts.hybrid_rotation import hessian
from scripts.decimal_real_response import block_responses, agreement
from solar_simulator.relativity import C
from solar_simulator.simulation import G


def mixed_responses(x, v, masses, components, units, c=C):
    m = np.asarray(masses, dtype=float); p = np.asarray(x, dtype=float); velocity = np.asarray(v, dtype=float)
    if (m.ndim != 1 or len(m) < 2 or p.shape != (len(m), 3) or velocity.shape != p.shape
            or any(not np.isfinite(a).all() for a in (m, p, velocity)) or np.any(m <= 0)
            or not components or any(np.shape(a) != p.shape or not np.isfinite(a).all() for a in components.values())
            or not np.isfinite(c) or c <= 0):
        raise ValueError('Finite SI states and nonempty acceleration components required')
    # H1 is obtained in already tested similarity units, then conditioned by M0.
    mu = m/units.mass_kg
    h = hessian(p/units.length_m, velocity/units.velocity_m_s, mu, c/units.velocity_m_s)
    root = np.sqrt(np.repeat(mu, 3))
    k = h/root[:, None]/root[None, :]
    matrix = np.eye(len(root))+k
    eig = np.linalg.eigvalsh(matrix)
    if not np.isfinite(matrix).all() or eig.min() <= 0:
        raise ValueError('Mass-scaled finite-action matrix must be positive definite')
    names = list(components)
    low = block_responses(p, velocity, m, components, units.gravitational_constant, c, 50)
    high = block_responses(p, velocity, m, components, units.gravitational_constant, c, 70)
    first = np.column_stack([np.array(high[name], dtype=float).ravel() for name in names])
    rhs = first*root[:, None]
    solution = np.linalg.solve(matrix, rhs)
    finite = solution/root[:, None]
    residual = matrix@solution-rhs
    diagnostics = dict(block_precision50_to70_relative=agreement(low, high),
        condition_number=float(eig.max()/eig.min()), minimum_eigenvalue=float(eig.min()),
        k_spectral_norm=float(np.max(abs(eig-1))), solve_relative={name:relative(residual[:, j], rhs[:, j])
            for j, name in enumerate(names)})
    return {name:(first[:, j].reshape(p.shape), finite[:, j].reshape(p.shape)) for j, name in enumerate(names)}, diagnostics


def relative(actual_difference, expected):
    a, b = np.asarray(actual_difference), np.asarray(expected)
    if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Finite matching arrays required')
    error, scale = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if scale == 0:
        if error:
            raise ValueError('Nonzero defect against exact zero')
        return 0.
    return error/scale


def vector_relative(difference, expected):
    a, b = np.asarray(difference), np.asarray(expected)
    if a.ndim == 1:
        return relative(a, b)
    if a.ndim != 2 or a.shape != b.shape or a.shape[1] != 3:
        raise ValueError('A vector or per-body vector array is required')
    return max(relative(row, ref) for row, ref in zip(a, b))


def spin_orbit(x, v, masses, spin, source, *, spin_rate=None, g=G, c=C):
    """Isolated LO HSO derivatives and material velocity-shift derivative.

    p=m*v and Euclidean S are a leading/conditional assignment. Return force
    rather than subtracting it from the much larger point-mass force.
    """
    p, velocity, m, s = (np.asarray(a, dtype=float) for a in (x, v, masses, spin))
    sd = np.zeros(3) if spin_rate is None else np.asarray(spin_rate, dtype=float)
    if (m.ndim != 1 or len(m) < 2 or p.shape != (len(m), 3) or velocity.shape != p.shape
            or s.shape != (3,) or sd.shape != (3,) or np.any(m <= 0)
            or any(not np.isfinite(a).all() for a in (p, velocity, m, s, sd))
            or type(source) is not int or not 0 <= source < len(m)
            or not np.isfinite(g) or g <= 0 or not np.isfinite(c) or c <= 0):
        raise ValueError('Finite SI source spin/geometry and positive constants required')
    delta = p[:, None]-p[None, :]; distance = np.linalg.norm(delta, axis=2)
    np.fill_diagonal(distance, np.inf)
    if np.any(distance == 0) or max(float(np.max((1/distance)@(g*m))),
            float(np.sum(velocity*velocity, axis=1).max()))/c**2 >= 1e-4:
        raise ValueError('Spin diagnostic outside distinct weak-field geometry')
    if np.linalg.norm(s)/(m[source]*c*distance[source].min()) >= 1e-3:
        raise ValueError('Spin diagnostic outside small-spin domain')
    force = np.zeros_like(p); shift = np.zeros_like(p); transport = np.zeros_like(p)
    torque_transport = np.zeros_like(p); omega_parts = np.zeros_like(p)
    for j in range(len(m)):
        if j == source:
            continue
        r = p[source]-p[j]; d = distance[source, j]
        w = 1.5*velocity[source]-2*velocity[j]; k = g*m[j]/(c*c*d**3)
        product = np.dot(np.cross(r, w), s)
        f = -k*(np.cross(w, s)-3*product*r/d**2)
        force[source] += f; force[j] -= f
        sr = np.cross(s, r)
        shift[source] += 1.5*k*sr/m[source]; shift[j] -= 2*k*sr/m[j]
        dr = velocity[source]-velocity[j]
        derivative = np.cross(s, dr)-3*np.dot(r, dr)*sr/d**2
        transport[source] += 1.5*k*derivative/m[source]; transport[j] -= 2*k*derivative/m[j]
        spin_derivative = np.cross(sd, r)
        torque_transport[source] += 1.5*k*spin_derivative/m[source]
        torque_transport[j] -= 2*k*spin_derivative/m[j]
        omega_parts[j] = k*np.cross(r, w)
    return dict(force=force, velocity_shift=shift, omega=omega_parts.sum(axis=0),
        omega_by_source=omega_parts, material_transport=transport,
        q_torque_transport=torque_transport, acceleration=force/m[:, None]+transport,
        acceleration_with_q_torque=force/m[:, None]+transport+torque_transport)


def spin_identities(x, v, masses, spin, source, response):
    force, shift, omega = response['force'], response['velocity_shift'], response['omega']
    orbital = np.cross(x, force); velocity = np.cross(shift, np.asarray(masses)[:, None]*v)
    spin_term = np.cross(omega, spin)
    scale = float(np.linalg.norm(orbital, axis=1).sum()+np.linalg.norm(velocity, axis=1).sum()+np.linalg.norm(spin_term))
    total = orbital.sum(axis=0)+velocity.sum(axis=0)+spin_term
    force_scale = np.linalg.norm(force, axis=1).sum()
    ratio = lambda a,b:relative(np.array([a]), np.array([b]))
    return dict(linear=ratio(np.linalg.norm(force.sum(axis=0)), force_scale),
        angular=ratio(np.linalg.norm(total), scale),
        missing_velocity=ratio(np.linalg.norm(orbital.sum(axis=0)+spin_term), scale),
        missing_source_reaction=ratio(np.linalg.norm(force.sum(axis=0)-force[source]), force_scale))


def hat(vector):
    a, b, c = vector
    return np.array([[0., -c, b], [c, 0., -a], [-b, a, 0.]])
