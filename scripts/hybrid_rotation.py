"""Synthetic harmonic point EIH + Newton rotor, not a runtime physics mode."""
from dataclasses import dataclass

import numpy as np
from scipy.integrate import DOP853
from scipy.spatial.transform import Rotation

from scripts.canonical_initial import SIUnits
from scripts.eih_year import force_terms
from solar_simulator.nbody_rotation import correction, RotationDOP853
from solar_simulator.rotation import RigidFigure, rotation_matrix, angular_velocity, quaternion_rate
from solar_simulator.simulation import G

UNITS = SIUnits(1e15, 12000., G)


@dataclass(frozen=True)
class Model:
    masses: tuple = (.3, .7, .05)
    c: float = 400.
    moments: tuple = (.002, .0025, .003)
    radius: float = .15
    source: int = 0

    def __post_init__(self):
        m = np.asarray(self.masses)
        if (m.ndim != 1 or len(m) < 2 or not np.isfinite(m).all() or np.any(m <= 0)
                or type(self.source) is not int or not 0 <= self.source < len(m)
                or not np.isfinite(self.c) or self.c <= 0):
            raise ValueError('Positive masses/c and one existing source required')
        RigidFigure(float(m[self.source]), self.moments, self.radius)


def initial(model=Model()):
    if model.masses != (.3, .7, .05) or model.source != 0:
        raise ValueError('Declared synthetic start has three fixed masses/source')
    m = np.asarray(model.masses)
    x = np.array([[.56, 0., 0.], [-.24, 0., 0.], [3.5, .4, .6]])
    v = np.array([[0., .8573214099741123, 0.], [0., -.3674234614174767, 0.], [-.06, .5, .08]])
    x -= np.sum(m[:, None]*x, axis=0)/m.sum()
    v -= np.sum(m[:, None]*v, axis=0)/m.sum()
    r = Rotation.from_rotvec([.3, -.2, .4])
    q = np.roll(r.as_quat(), 1)
    s = r.as_matrix()@(np.array(model.moments)*(r.as_matrix().T@np.array([.2, -.3, .9])))
    return np.r_[x.ravel(), v.ravel(), q, s, np.zeros(14)]


def unpack(state, model):
    n = len(model.masses); y = np.asarray(state, dtype=float)
    if y.shape != (6*n+21,) or not np.isfinite(y).all():
        raise ValueError('Finite x/v/q/S/two-budget state required')
    return y[:3*n].reshape(n, 3), y[3*n:6*n].reshape(n, 3), y[6*n:6*n+4], y[6*n+4:6*n+7]


def hessian(x, v, masses, c):
    """H1=partial² L1/partial v²; symmetric 3N block matrix, G=1."""
    n = len(masses); h = np.zeros((3*n, 3*n)); eye = np.eye(3)
    for i, mass in enumerate(masses):
        a = slice(3*i, 3*i+3)
        h[a, a] = mass*(.5*np.dot(v[i], v[i])*eye+np.outer(v[i], v[i]))
        for j in range(n):
            if i == j:
                continue
            r = x[i]-x[j]; d = np.linalg.norm(r)
            if not np.isfinite(d) or d == 0:
                raise ValueError('Distinct finite positions required')
            normal = r/d; factor = mass*masses[j]/(2*d)
            h[a, a] += 6*factor*eye
            h[a, 3*j:3*j+3] = -factor*(7*eye+np.outer(normal, normal))
    return h/c**2


def mass_solve(masses, h, vector):
    matrix = np.diag(np.repeat(masses, 3))+h
    if not np.isfinite(matrix).all() or np.linalg.eigvalsh(matrix).min() <= 0:
        raise ValueError('Finite-action velocity Hessian must be positive definite')
    return np.linalg.solve(matrix, vector.ravel()).reshape(-1, 3)


def figure_field(x, masses, q, model):
    """Explicit SI similarity bridge to the existing Newton runtime Q2."""
    figure = RigidFigure(model.masses[model.source]*UNITS.mass_kg,
        tuple(i*UNITS.inertia_kg_m2 for i in model.moments), model.radius*UNITS.length_m)
    a, tau, u = correction(x*UNITS.length_m, np.asarray(masses)*UNITS.mass_kg,
        model.source, figure, q)
    acceleration_unit = UNITS.length_m/UNITS.time_s**2
    energy_unit = UNITS.mass_kg*UNITS.velocity_m_s**2
    return a/acceleration_unit, tau/energy_unit, u/energy_unit


def pack(x, v, force):
    return np.r_[np.sum(v*force), force.sum(axis=0), np.cross(x, force).sum(axis=0)]


def fields(state, model, mode):
    x, v, q, s = unpack(state, model)
    if mode not in ('order-reduced', 'finite-action'):
        raise ValueError('Unknown synthetic truncation')
    m = np.array(model.masses)
    an, ap = force_terms(x, v, m, model.c)
    aq, torque, potential = figure_field(x, m, q, model)
    h = hessian(x, v, m, model.c)
    a = an+ap+aq if mode == 'order-reduced' else an+mass_solve(m, h, m[:, None]*(ap+aq))
    response = np.array([pack(x, v, (h@b.ravel()).reshape(-1, 3)) for b in (ap, aq)])
    if mode == 'finite-action':
        response[:] = 0.
    return a, torque, potential, response


def rhs(time, state, model, mode):
    x, v, q, s = unpack(state, model)
    a, torque, _, source = fields(state, model, mode)
    figure = RigidFigure(model.masses[model.source], model.moments, model.radius)
    omega = angular_velocity(figure, q, s)
    return np.r_[v.ravel(), a.ravel(), quaternion_rate(q, omega), torque, source.ravel()]


class HybridDOP853(DOP853):
    """Existing worst-block estimator, extended by the two source budgets."""
    def __init__(self, fun, t0, y0, t_bound, *, body_count, **kwargs):
        n = body_count
        if np.size(y0) != 6*n+21:
            raise ValueError('Wrong hybrid state layout')
        self.blocks = [slice(k, k+3) for k in range(0, 6*n, 3)]
        self.blocks += [slice(6*n, 6*n+4), slice(6*n+4, 6*n+7)]
        for k in (6*n+7, 6*n+14):
            self.blocks += [slice(k, k+1), slice(k+1, k+4), slice(k+4, k+7)]
        super().__init__(fun, t0, y0, t_bound, **kwargs)

    _estimate_error_norm = RotationDOP853._estimate_error_norm
