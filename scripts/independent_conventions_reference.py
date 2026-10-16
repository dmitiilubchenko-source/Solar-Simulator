"""Spherical mass/chart/observer oracles, with no production physics imports.

Isotropic mass is integrated in that coordinate using a numerical inverse
of the independent log-radius IVP, not the production rational inverse.
"""
import numpy as np
from scipy.optimize import brentq


def surface_isotropic_fraction(c):
    return (1-c+np.sqrt(1-2*c))/2


def log_radius_rhs(s, state, c):
    """g=log(rho/r), with regular g'=0 at s=0 and no radial cutoff."""
    u=np.sqrt(1-2*c*s*s)
    return np.array([2*c*s/(u*(1+u))])


def gauss_nodes(order, upper=1.):
    nodes,weights=np.polynomial.legendre.leggauss(order)
    return (nodes+1)*upper/2,weights*upper/2


def proper_mass_ratio(c, order):
    s,w=gauss_nodes(order)
    return float(np.dot(w,3*s*s/np.sqrt(1-2*c*s*s)))


def baryon_areal_ratio(c, density_ratio, order):
    s,w=gauss_nodes(order)
    return float(np.dot(w,3*s*s*density_ratio(s)/np.sqrt(1-2*c*s*s)))


def baryon_isotropic_ratio(c, density_ratio, log_solution, order):
    x,w=gauss_nodes(order,surface_isotropic_fraction(c))
    def inverse(value):
        return brentq(lambda s:s*np.exp(log_solution.sol(s)[0])-value,
                      0.,1.,xtol=5e-15,rtol=1e-14)
    s=np.array([inverse(value) for value in x])
    # sqrt(gamma)=(r/rho)^3: independent coordinate integral, not pulled back.
    return float(np.dot(w,3*s**3/x*density_ratio(s))),s,x


def tetrad_rates(radius_m, lapse, dragging_rate, distant_rate):
    """Project dphi/dt through the orthonormal ZAMO coframe, SI.

    Matrix acts on (dt/dtau, dphi/dtau). First output is unit proper-time
    rate, second the physical azimuthal speed. No angular division at r=0.
    """
    coframe=np.array([[lapse,0.],[-radius_m*dragging_rate,radius_m]])
    projected=coframe@np.array([1/lapse,distant_rate/lapse])
    return projected


def response_linear_series(c):
    coefficients=dict(distant_gravitational_areal=12/35,
        distant_proper_energy_areal=18/175,
        distant_gravitational_isotropic=8/7,
        surface_static_gravitational_areal=-2/35,
        surface_zamo_gravitational_areal=46/175)
    return {key:2/5+value*np.asarray(c) for key,value in coefficients.items()}


def proper_volume_series(c):
    return 1+3*np.asarray(c)/5+9*np.asarray(c)**2/14
