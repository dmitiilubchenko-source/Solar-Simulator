"""Research time-compatible scaling and explicit rotation boundary kinematics.

Uniform t*=F t, x*=F x, GM*=F GM uses the SAME SI units. G and c stay
fixed, model mass=GM/G scales F. This is not an ADM/SSC/tetrad migration.
Local/global boundary helpers require supplied SO(3) basis and clock rates;
they never infer a physical Moon basis or clock from a Newtonian profile.
"""
from dataclasses import dataclass
import math

import numpy as np

from scripts.canonical_initial import finite_array
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.rigid_pn_model import Parameters, fields
from solar_simulator.rotation import RigidFigure


# IAU 2006 B3, as listed by the IAU NSFA working group; exact definition.
L_B = 1.550519768e-8


@dataclass(frozen=True)
class UniformTimeScaling:
    factor: float

    def __post_init__(self):
        if type(self.factor) not in (int,float) or not math.isfinite(self.factor) or self.factor<=0:
            raise ValueError('Positive finite uniform factor required')
        try:powers = [self.factor**n for n in [-3,-2,-1,1,2,3]]
        except (OverflowError,ZeroDivisionError) as e:raise ValueError('Unrepresentable scaling powers') from e
        if any(not math.isfinite(v) or v<=0 for v in powers):raise ValueError('Unrepresentable scaling powers')

    def state_factors(self, count):
        if type(count) is not int or count<2:raise ValueError('N>=2 required')
        return np.r_[np.full(6*count,self.factor),np.full(3*count,self.factor**2),np.ones(4)]

    def parameters(self, parameters):
        if not isinstance(parameters,Parameters):raise ValueError('Finite-H parameters required')
        f = self.factor;p = parameters
        return Parameters(PointParameters(tuple(f*m for m in p.orbital.masses),p.orbital.c),
            RigidFigure(f*p.figure.mass,tuple(f**3*v for v in p.figure.moments),f*p.figure.bounding_radius),p.index)

    def state(self, state, parameters):
        """Scale x,p,S but preserve raw q; validate the original and new domain."""
        y = fields(state,parameters)[0];out = y*self.state_factors(len(parameters.orbital.masses))
        fields(out,self.parameters(parameters))
        return out


def proper_rotation(matrix, name):
    r = finite_array(matrix,(3,3),name)
    if np.linalg.norm(r.T@r-np.eye(3))>1e-12 or abs(np.linalg.det(r)-1)>1e-12:
        raise ValueError(name+': proper SO(3) rotation required')
    return r


def spatial_rate(rotation, derivative):
    r = proper_rotation(rotation,'rotation');d = finite_array(derivative,(3,3),'rotation derivative')
    h = d@r.T;scale = np.linalg.norm(d)
    if np.linalg.norm(h+h.T)>1e-12*scale:raise ValueError('Rotation derivative must be tangent to SO(3)')
    h = .5*(h-h.T)
    return np.array([h[2,1],h[0,2],h[1,0]])


def positive_clock_rate(rate):
    if type(rate) not in (int,float) or not math.isfinite(rate) or rate<=0:
        raise ValueError('Explicit positive dT_local/dt_global required')


def rotation_boundary(local_rotation, local_derivative, basis, basis_derivative, clock_rate):
    """R_global=B R_local(T), dR/dt=Bdot R+B R_T dT/dt.

    B maps the supplied local Euclidean triad to the supplied global triad.
    B/Bdot are explicit providers, not a spin metric root or Lorentz stretch.
    """
    positive_clock_rate(clock_rate)
    local = proper_rotation(local_rotation,'local rotation');b = proper_rotation(basis,'basis')
    spatial_rate(local,local_derivative);spatial_rate(b,basis_derivative)
    derivative = np.asarray(basis_derivative)@local+b@np.asarray(local_derivative)*clock_rate
    rotation = b@local
    return rotation,derivative,spatial_rate(rotation,derivative)


def local_rate(global_rate, basis, basis_derivative, clock_rate):
    """Invert W_global=W_basis+(dT/dt) B W_local at a supplied boundary."""
    positive_clock_rate(clock_rate);b = proper_rotation(basis,'basis')
    wb = spatial_rate(b,basis_derivative);w = finite_array(global_rate,(3,),'global rate')
    return b.T@(w-wb)/clock_rate


def global_acceleration(local_omega, local_alpha, basis, basis_derivative,
                        basis_alpha, clock_rate, clock_acceleration):
    """Time derivative of W_global, including moving-basis and clock terms.

    local_alpha=dW_local/dT, basis_alpha=dW_basis/dt,
    clock_acceleration=d^2 T/dt^2. No gravitational model is inferred.
    """
    positive_clock_rate(clock_rate);b = proper_rotation(basis,'basis')
    wb = spatial_rate(b,basis_derivative);w = finite_array(local_omega,(3,),'local omega')
    a = finite_array(local_alpha,(3,),'local alpha');ab = finite_array(basis_alpha,(3,),'basis alpha')
    if type(clock_acceleration) not in (int,float) or not math.isfinite(clock_acceleration):
        raise ValueError('Finite explicit clock acceleration required')
    return ab+clock_acceleration*(b@w)+clock_rate*np.cross(wb,b@w)+clock_rate**2*(b@a)
