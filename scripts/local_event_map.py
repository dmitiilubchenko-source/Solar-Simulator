"""Leading c^-2 local event map; SI, x0=ct, Soffel (2003), IAU B1.3.

The central global/local epochs are supplied, not inferred from TDB/DE441.
B is an explicit proper rotation of the kinematically nonrotating map.
No self-field, full time c^-4, ADM centre map, or inertia law is provided.
"""
from dataclasses import dataclass
import math

import numpy as np

from scripts.external_metric import array, light_speed, finite_outputs, potentials, WEAK_LIMIT


def scalar(value, name):
    if type(value) not in (float, int) or not math.isfinite(value):
        raise ValueError(f'{name}: explicit finite real scalar required')
    return float(value)


@dataclass(frozen=True)
class Jet:
    global_epoch: float
    local_epoch: float
    position: tuple
    velocity: tuple
    acceleration: tuple
    jerk: tuple
    potential: float
    potential_rate: float
    basis: tuple
    basis_derivative: tuple
    c: float

    def __post_init__(self):
        c = light_speed(self.c)
        for name in ('global_epoch', 'local_epoch', 'potential', 'potential_rate'):
            object.__setattr__(self, name, scalar(getattr(self, name), name))
        vectors = {name: array(getattr(self, name), (3,), name)
                   for name in ('position', 'velocity', 'acceleration', 'jerk')}
        b = array(self.basis, (3, 3), 'basis')
        db = array(self.basis_derivative, (3, 3), 'basis derivative')
        if (np.linalg.norm(b.T@b-np.eye(3)) > 1e-12 or abs(np.linalg.det(b)-1) > 1e-12
                or np.linalg.norm(db@b.T+b@db.T) > 1e-12*np.linalg.norm(db)):
            raise ValueError('Explicit proper SO(3) basis and tangent derivative required')
        speed = vectors['velocity']/c
        if self.potential < 0 or self.potential/c**2 > WEAK_LIMIT or speed@speed > WEAK_LIMIT:
            raise ValueError('Declared weak external potential and centre speed required')
        for name, value in vectors.items(): object.__setattr__(self, name, tuple(value))
        object.__setattr__(self, 'basis', tuple(map(tuple, b)))
        object.__setattr__(self, 'basis_derivative', tuple(map(tuple, db)))
        object.__setattr__(self, 'c', c)

    @property
    def centre_clock_rate(self):
        beta = np.asarray(self.velocity)/self.c
        return float(1-.5*(beta@beta)-self.potential/self.c**2)


def from_sources(global_epoch, local_epoch, position, velocity, acceleration, jerk,
                 basis, basis_derivative, sources):
    """Construct one consistent external-field jet, with explicit centre jerk."""
    field = potentials(position, sources); v = array(velocity, (3,), 'centre velocity')
    rate = float(field.scalar_derivative[0]+field.scalar_derivative[1:]@v)
    return Jet(global_epoch, local_epoch, position, v, acceleration, jerk,
               field.u, rate, basis, basis_derivative, sources.c)


@dataclass(frozen=True)
class Event:
    local_time: float
    local_position: np.ndarray
    # Blocks in physical seconds/metres, not x0 units.
    time_t: float
    time_x: np.ndarray
    position_t: np.ndarray
    position_x: np.ndarray

    def jacobian_ct(self, c):
        """d(cT,X)/d(ct,x): dimensionless four-dimensional Jacobian."""
        c = light_speed(c)
        return np.block([[np.array([[self.time_t]]), (c*self.time_x)[None, :]],
                         [self.position_t[:, None]/c, self.position_x]])


def event(position, jet):
    """One event at jet.global_epoch and derivatives at fixed global x/t."""
    if not isinstance(jet, Jet): raise ValueError('Explicit centre Jet required')
    x = array(position, (3,), 'global position')
    r = x-np.asarray(jet.position); v = np.asarray(jet.velocity)
    a = np.asarray(jet.acceleration); j = np.asarray(jet.jerk)
    b = np.asarray(jet.basis); db = np.asarray(jet.basis_derivative); c = jet.c
    try:
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            if np.linalg.norm(a/c)*np.linalg.norm(r/c) > WEAK_LIMIT:
                raise ValueError('Acceleration times extent exceeds declared local domain')
            correction = (.5*(v/c)*((v/c)@r)+jet.potential/c**2*r
                          +r*((a/c)@(r/c))-.5*(a/c)*(r@(r/c)))
            f = r+correction
            fr = ((1+jet.potential/c**2+(a/c)@(r/c))*np.eye(3)
                  +.5*np.outer(v/c, v/c)+np.outer(r/c, a/c)-np.outer(a/c, r/c))
            ft = (.5*((a/c)*((v/c)@r)+(v/c)*((a/c)@r))
                  +jet.potential_rate/c**2*r+r*((j/c)@(r/c))-.5*(j/c)*(r@(r/c)))
            position_t = db@f+b@(ft-fr@v)
            position_x = b@fr
            time_x = -(v/c)/c
            time_t = jet.centre_clock_rate-((a/c)@(r/c))+(v/c)@(v/c)
            local_time = jet.local_epoch-(v/c)@(r/c)
    except FloatingPointError as error:
        raise ValueError('Local event map is not representable') from error
    finite_outputs(local_time, f, position_t, position_x, time_t, time_x)
    return Event(float(local_time), b@f, float(time_t), time_x, position_t, position_x)


def velocity(position, global_velocity, jet):
    """dX/dT with simultaneity; return local velocity and material dT/dt."""
    point = event(position, jet); v = array(global_velocity, (3,), 'global material velocity')
    beta = v/jet.c
    if beta@beta >= 1: raise ValueError('Timelike global material velocity required')
    rate = float(point.time_t+point.time_x@v)
    if not np.isfinite(rate) or rate <= 0: raise ValueError('Positive material local clock required')
    result = (point.position_t+point.position_x@v)/rate
    finite_outputs(result)
    return result, rate


def inverse_velocity(position, local_velocity, jet):
    """Invert the projective velocity map, not a spatial-only rotation."""
    point = event(position, jet); u = array(local_velocity, (3,), 'local material velocity')
    matrix = point.position_x-np.outer(u, point.time_x)
    try:
        v = np.linalg.solve(matrix, u*point.time_t-point.position_t)
    except np.linalg.LinAlgError as error:
        raise ValueError('Singular local velocity boundary') from error
    finite_outputs(v)
    # Enforce the same timelike/positive-clock branch as the forward map.
    velocity(position, v, jet)
    return v
