"""Isolated research stand: ADM COM canonical r/p/S, G=1, one spin.

Not a Solar Simulator force law or a conversion from harmonic/JPL data.
Primary formulae and limitations: docs/pn-spin-contract.md.
"""
from dataclasses import dataclass
import math

import numpy as np
from scipy.spatial.transform import Rotation


@dataclass(frozen=True)
class Parameters:
    mass1: float
    mass2: float
    c: float

    def __post_init__(self):
        if any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0
               for v in (self.mass1, self.mass2, self.c)):
            raise ValueError('Positive finite masses and c required')
        if not math.isfinite(self.c*self.c) or self.c*self.c == 0:
            raise ValueError('Invalid c squared')
        if not math.isfinite(self.total) or not math.isfinite(self.reduced) or self.reduced <= 0:
            raise ValueError('Invalid derived masses')
        if not math.isfinite(self.spin_coefficient):
            raise ValueError('Invalid spin coefficient')

    @property
    def total(self):
        return self.mass1+self.mass2

    @property
    def reduced(self):
        return (self.mass1/self.total)*self.mass2

    @property
    def eta(self):
        return self.reduced/self.total

    @property
    def spin_coefficient(self):
        return (2+1.5*self.mass2/self.mass1)/(self.c*self.c)


def validate(state, parameters):
    y = np.asarray(state, dtype=float)
    if y.shape != (9,) or not np.all(np.isfinite(y)):
        raise ValueError('Finite r/p/S vectors required')
    radius = np.linalg.norm(y[:3])
    if radius == 0:
        raise ValueError('Coincident positions')
    # Research domain guard only; canonical p/mu approximates velocity at LO.
    if max(parameters.total/radius, np.dot(y[3:6], y[3:6])/parameters.reduced**2)/parameters.c**2 >= 1e-4:
        raise ValueError('Outside weak-field/slow-motion research domain')
    if np.linalg.norm(y[6:])/(parameters.mass1*parameters.c*radius) >= 1e-3:
        raise ValueError('Spin expansion research domain exceeded')
    return y


def hamiltonian(state, parameters, *, orbital_pn=True, spin_orbit=True):
    """Analytic expression also accepts complex input for derivative verification."""
    r, p, s = np.asarray(state).reshape(3, 3)
    radius = np.sqrt(np.dot(r, r)); n = r/radius
    p2 = np.dot(p, p); radial = np.dot(n, p)
    mass, mu, eta = parameters.total, parameters.reduced, parameters.eta
    result = p2/(2*mu)-mass*mu/radius
    if orbital_pn:
        result += ((3*eta-1)*p2*p2/(8*mu**3)
            -mass*((3+eta)*p2+eta*radial*radial)/(2*mu*radius)
            +mass*mass*mu/(2*radius*radius))/parameters.c**2
    if spin_orbit:
        result += parameters.spin_coefficient*np.dot(np.cross(r, p), s)/radius**3
    return result


def rhs(time, state, parameters, *, orbital_pn=True, spin_orbit=True, only_so=False):
    r, p, s = validate(state, parameters).reshape(3, 3)
    radius = np.linalg.norm(r); n = r/radius
    p2 = np.dot(p, p); radial = np.dot(n, p)
    mass, mu, eta = parameters.total, parameters.reduced, parameters.eta
    dr = np.zeros(3) if only_so else p/mu
    dp = np.zeros(3) if only_so else -mass*mu*n/radius**2
    ds = np.zeros(3)
    if orbital_pn and not only_so:
        dr += ((3*eta-1)*p2*p/(2*mu**3)
            -mass*((3+eta)*p+eta*radial*n)/(mu*radius))/parameters.c**2
        dp += (-mass*((3+eta)*p2+3*eta*radial**2)*n/(2*mu*radius**2)
            +mass*eta*radial*p/(mu*radius**2)+mass**2*mu*n/radius**3)/parameters.c**2
    if spin_orbit or only_so:
        coefficient = parameters.spin_coefficient/radius**3
        angular = np.cross(r, p); product = np.dot(angular, s)
        dr += coefficient*np.cross(s, r)
        dp += coefficient*(np.cross(s, p)+3*product*n/radius)
        ds = coefficient*np.cross(angular, s)
    return np.r_[dr, dp, ds]


def invariants(state, parameters):
    y = validate(state, parameters)
    return float(hamiltonian(y, parameters)), np.cross(y[:3], y[3:6])+y[6:], float(np.linalg.norm(y[6:]))


def exact_so(state, time, parameters):
    """Derived exact flow of H_SO alone: two rotations and a radial momentum shear."""
    r, p, s = validate(state, parameters).reshape(3, 3)
    radius = np.linalg.norm(r); angular = np.cross(r, p); total = angular+s
    coefficient = parameters.spin_coefficient/radius**3
    outer = Rotation.from_rotvec(coefficient*time*total).as_matrix()
    inner = Rotation.from_rotvec(-coefficient*time*angular).as_matrix()
    evolved_p = p+3*coefficient*np.dot(angular, s)*time*r/radius**2
    return np.r_[outer@inner@r, outer@inner@evolved_p, outer@s]
