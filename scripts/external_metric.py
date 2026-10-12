"""Research SI external monopoles and LEADING local coordinate-clock rate.

Sources explicitly exclude the target. x0=c*t, signature -+++; all inputs
share one coordinate system/time, NOT automatically BCRS/TCB or DE441/TDB.
The finite weak metric omits PN scalar potentials and c^-4 g00 terms.
Its exact inverse does not upgrade it to a complete 1PN metric.
Soffel et al. (2003), (8); Turyshev (2026), Appendix C (182).
"""
from dataclasses import dataclass
import math

import numpy as np


WEAK_LIMIT = 1e-3


def array(value, shape, name):
    raw = np.asarray(value)
    if raw.dtype.kind not in 'fiu' or raw.shape != shape:
        raise ValueError(f'{name}: real finite array of shape {shape} required')
    result = np.array(raw, dtype=float, copy=True)
    if not np.all(np.isfinite(result)):
        raise ValueError(f'{name}: finite values required')
    return result


def light_speed(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('Positive finite c in m/s required')
    squared = float(value)*float(value)
    if not math.isfinite(squared) or squared <= 0:
        raise ValueError('c squared must be representable')
    return float(value)


def finite_outputs(*values):
    if any(not np.all(np.isfinite(v)) for v in values):
        raise ValueError('Derived metric/clock values are not representable')


@dataclass(frozen=True)
class Sources:
    """External GM [m^3/s^2], x [m], v [m/s], a [m/s^2]; no body inference.

    Source accelerations are compulsory, including explicitly zero values.
    Empty arrays of shapes (0,) / (0,3) select Minkowski space.
    """
    gm: tuple
    positions: tuple
    velocities: tuple
    accelerations: tuple
    c: float

    def __post_init__(self):
        c = light_speed(self.c)
        raw = np.asarray(self.gm)
        if raw.ndim != 1:
            raise ValueError('GM must be one-dimensional')
        gm = array(raw, raw.shape, 'GM'); count = len(gm)
        x = array(self.positions, (count, 3), 'source positions')
        v = array(self.velocities, (count, 3), 'source velocities')
        a = array(self.accelerations, (count, 3), 'source accelerations')
        if np.any(gm <= 0) or np.any(np.sum((v/c)**2, axis=1) > WEAK_LIMIT):
            raise ValueError('Positive GM and weak source speeds required')
        object.__setattr__(self, 'c', c)
        object.__setattr__(self, 'gm', tuple(gm))
        for name, value in [('positions', x), ('velocities', v), ('accelerations', a)]:
            object.__setattr__(self, name, tuple(map(tuple, value)))


@dataclass(frozen=True)
class Potentials:
    u: float
    vector: np.ndarray
    # Derivative index first: physical t [s], then x/y/z [m].
    scalar_derivative: np.ndarray
    vector_derivative: np.ndarray


def potentials(position, sources):
    """Monopole fields with analytic partial derivatives, not material ones."""
    if not isinstance(sources, Sources):
        raise ValueError('Explicit external Sources required')
    x = array(position, (3,), 'position'); count = len(sources.gm)
    gm = np.asarray(sources.gm)
    source_x = np.asarray(sources.positions).reshape(count, 3)
    source_v = np.asarray(sources.velocities).reshape(count, 3)
    source_a = np.asarray(sources.accelerations).reshape(count, 3)
    try:
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            delta = x-source_x
            radius = np.linalg.norm(delta, axis=1)
            if np.any(radius <= 0):
                raise ValueError('Coincident target/source: self field is unsupported')
            weight = gm/radius
            gradient = -weight[:, None]*(delta/radius[:, None])/radius[:, None]
            weight_dt = -np.sum(gradient*source_v, axis=1)
            u = float(np.sum(weight)); vector = weight@source_v
            du = np.r_[np.sum(weight_dt), np.sum(gradient, axis=0)]
            dvector = np.vstack([weight_dt@source_v+weight@source_a,
                                 gradient.T@source_v])
    except FloatingPointError as error:
        raise ValueError('External potentials are not representable') from error
    finite_outputs(u, vector, du, dvector)
    if u/sources.c**2 > WEAK_LIMIT:
        raise ValueError('External potential exceeds the declared weak-field domain')
    return Potentials(u, vector, du, dvector)


def weak_metric(position, sources):
    """Return g and dg[lambda,mu,nu]=partial_(x^lambda) g_mu_nu, [1/m].

    g00=-1+2U/c², g0i=-4Ui/c³, gij=(1+2U/c²)delta_ij.
    No c^-4 coefficient, source spin, self-field, or ephemeris conversion.
    """
    field = potentials(position, sources); c = sources.c
    g = np.diag([-1., 1., 1., 1.])
    g[0, 0] += 2*field.u/c**2
    g[1:, 1:] *= 1+2*field.u/c**2
    g[0, 1:] = g[1:, 0] = -4*((field.vector/c)/c)/c
    du = field.scalar_derivative.copy(); dv = field.vector_derivative.copy()
    du[0] /= c; dv[0] /= c
    dg = np.zeros((4, 4, 4))
    dg[:, 0, 0] = 2*du/c**2
    dg[:, 0, 1:] = dg[:, 1:, 0] = -4*((dv/c)/c)/c
    dg[:, 1:, 1:] = (2*du/c**2)[:, None, None]*np.eye(3)
    finite_outputs(g, dg)
    return g, dg


def leading_clock(position, velocity, acceleration, sources):
    """dTCX/dt and its t derivative at the centre, only through c^-2.

    Adot=v²/2+U_ext, rate=1-Adot/c². Origin/epoch and scale offsets
    must be specified separately before integrating any absolute local time.
    This is not the full proper time of a lunar surface clock.
    """
    field = potentials(position, sources)
    v = array(velocity, (3,), 'centre velocity')
    a = array(acceleration, (3,), 'centre acceleration'); c = sources.c
    try:
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            speed_squared = float((v/c)@(v/c))
            rate = 1-.5*speed_squared-field.u/c**2
            material = field.scalar_derivative[0]+field.scalar_derivative[1:]@v
            derivative = -((v/c)@(a/c)+material/c**2)
    except FloatingPointError as error:
        raise ValueError('Clock rate/derivative are not representable') from error
    finite_outputs(rate, derivative)
    if speed_squared > WEAK_LIMIT or rate <= 0:
        raise ValueError('Weak timelike centre speed required')
    return float(rate), float(derivative)
