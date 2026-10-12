"""Closed Newton point-mass body with central elastic links and self-gravity.

SI research model, one inertial time/slice; not continuum/PN lunar inertia.
No damping, orbit support, state projection, softening or inferred rigidity.
"""
from dataclasses import dataclass

import numpy as np

from scripts.external_metric import array, finite_outputs
from scripts.density_moments import mass_positions, mass_moments


def scalar(value, name, *, minimum=None, strict=False):
    raw = np.asarray(value)
    if raw.shape != () or raw.dtype.kind not in 'fiu':
        raise ValueError(f'{name}: real scalar required')
    result = float(raw)
    if not np.isfinite(result) or (minimum is not None and
            (result <= minimum if strict else result < minimum)):
        raise ValueError(f'{name}: finite scalar within declared domain required')
    return result


@dataclass(frozen=True)
class Parameters:
    masses: tuple
    links: tuple
    gravitational_constant: float
    minimum_distance: float

    def __post_init__(self):
        m, _ = mass_positions(self.masses, np.zeros((len(self.masses), 3)))
        if len(m) < 2: raise ValueError('At least two masses required')
        g = scalar(self.gravitational_constant, 'G', minimum=0.)
        distance = scalar(self.minimum_distance, 'minimum distance', minimum=0., strict=True)
        seen = set(); links = []
        for edge in self.links:
            if len(edge) != 4: raise ValueError('Link must contain i,j,k,l')
            i, j, k, length = edge
            if type(i) is not int or type(j) is not int or not 0 <= i < j < len(m):
                raise ValueError('Canonical integer link indices 0<=i<j<N required')
            if (i, j) in seen: raise ValueError('Duplicate elastic link')
            seen.add((i, j))
            links.append((i, j, scalar(k, 'stiffness', minimum=0., strict=True),
                          scalar(length, 'rest length', minimum=0., strict=True)))
        object.__setattr__(self, 'masses', tuple(m))
        object.__setattr__(self, 'links', tuple(links))
        object.__setattr__(self, 'gravitational_constant', g)
        object.__setattr__(self, 'minimum_distance', distance)


def unpack(state, parameters):
    if not isinstance(parameters, Parameters): raise ValueError('Bound-body parameters required')
    count = len(parameters.masses)
    y = array(state, (6*count,), 'x/p state').reshape(2, count, 3)
    return y[0], y[1], np.asarray(parameters.masses)


def fields(positions, parameters):
    """All-pair reactions, two potential energies and integrated pair virial."""
    if not isinstance(parameters, Parameters): raise ValueError('Bound-body parameters required')
    n = len(parameters.masses); x = array(positions, (n, 3), 'positions')
    m = np.asarray(parameters.masses); links = {(i, j): (k, l) for i, j, k, l in parameters.links}
    force = np.zeros_like(x); virial = np.zeros((3, 3)); gravity = 0.; elastic = 0.
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            for i in range(n):
                for j in range(i+1, n):
                    q = x[j]-x[i]; r = np.linalg.norm(q)
                    if not np.isfinite(r) or r <= parameters.minimum_distance:
                        raise ValueError('Pair outside declared minimum distance required')
                    gm = parameters.gravitational_constant*m[i]*m[j]
                    tension = gm/r**2; gravity -= gm/r
                    if (i, j) in links:
                        k, length = links[i, j]; extension = r-length
                        tension += k*extension; elastic += .5*k*extension**2
                    pair = tension*q/r
                    force[i] += pair; force[j] -= pair
                    virial -= tension/r*np.outer(q, q)
    except FloatingPointError as error:
        raise ValueError('Pair fields are not representable') from error
    finite_outputs(force, gravity, elastic, virial)
    return force, float(gravity), float(elastic), virial


def rhs(time, state, parameters):
    scalar(time, 'time'); x, p, m = unpack(state, parameters)
    force = fields(x, parameters)[0]
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        try: flow = np.r_[(p/m[:, None]).ravel(), force.ravel()]
        except FloatingPointError as error: raise ValueError('Flow is not representable') from error
    finite_outputs(flow)
    return flow


def diagnostics(state, parameters):
    """No state edits: global E/P/J and COM-relative moments/virial identity."""
    x, p, m = unpack(state, parameters); force, gravity, elastic, virial = fields(x, parameters)
    try:
        with np.errstate(over='raise', invalid='raise', divide='raise'):
            total_mass = np.sum(m); momentum = np.sum(p, axis=0)
            centre = np.sum(m[:, None]*x, axis=0)/total_mass
            velocity = momentum/total_mass; r = x-centre; u = p/m[:, None]-velocity
            kinetic = .5*np.sum(p*p/m[:, None]); internal = .5*np.sum(m[:, None]*u*u)
            angular = np.sum(np.cross(x, p), axis=0)
            spin = np.sum(m[:, None]*np.cross(r, u), axis=0)
            d, inertia, multipole = mass_moments(m, r)
            d_dot = r.T@(m[:, None]*u)+u.T@(m[:, None]*r)
            c_dot = np.trace(d_dot)*np.eye(3)-d_dot
            a = u.T@(m[:, None]*u)
            # Direct product rule, independent of the pair-virial construction.
            d_ddot = 2*a+r.T@force+force.T@r
            inertia_rate = float(np.trace(d_dot))
            energy = kinetic+gravity+elastic
    except FloatingPointError as error:
        raise ValueError('Body diagnostics are not representable') from error
    values = dict(energy=float(energy), kinetic=float(kinetic), gravity=gravity, elastic=elastic,
        momentum=momentum, angular=angular, centre=centre, centre_velocity=velocity,
        spin=spin, relative_positions=r, relative_velocities=u, internal_kinetic=float(internal),
        second_moment=d, inertia=inertia, multipole=multipole, inertia_dot=c_dot,
        second_moment_ddot=d_ddot, inertia_trace_dot=inertia_rate,
        kinetic_tensor=a, pair_virial=virial, force=force)
    finite_outputs(*values.values())
    return values


def rotation_split(state, parameters):
    """Instantaneous Newton Tisserand/least-squares rotation, no attitude map.

    Reject singular or ill-conditioned C (condition number >=1e12).
    No pseudoinverse, recentring of the state, or rigid-body assumption.
    """
    out = diagnostics(state, parameters); c = out['inertia']; eig = np.linalg.eigvalsh(c)
    if eig[0] <= 1e-12*eig[-1] or eig[-1] <= 0:
        raise ValueError('Nondegenerate well-conditioned inertia required for unique rotation')
    omega = np.linalg.solve(c, out['spin'])
    residual = out['relative_velocities']-np.cross(omega, out['relative_positions'])
    m = np.asarray(parameters.masses)
    try:
        with np.errstate(over='raise', invalid='raise'):
            rotation_energy = .5*omega@c@omega
            residual_energy = .5*np.sum(m[:, None]*residual*residual)
            residual_spin = np.sum(m[:, None]*np.cross(out['relative_positions'], residual), axis=0)
    except FloatingPointError as error: raise ValueError('Rotation split is not representable') from error
    finite_outputs(omega, residual, rotation_energy, residual_energy, residual_spin)
    return dict(**out, omega=omega, residual_velocities=residual, residual_spin=residual_spin,
                rotation_energy=float(rotation_energy), residual_energy=float(residual_energy))
