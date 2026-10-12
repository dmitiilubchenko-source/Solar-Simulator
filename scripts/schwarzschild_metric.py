"""Exact exterior Schwarzschild metric in SI isotropic Cartesian coordinates.

Research analytic limit, not the multipolar/self-gravitating lunar metric.
Areal R=rho*(1+GM/(2c²rho))², x0=c*t, signature -+++.
Obtained by substituting R into the standard metric, Bini (2005), (2.1).
"""
import math

import numpy as np

from scripts.external_metric import array, light_speed, finite_outputs
from scripts.metric_spin_transport import Metric


def parameters(gm, c):
    c = light_speed(c)
    if type(gm) not in (int, float) or not math.isfinite(gm) or gm <= 0:
        raise ValueError('Positive finite GM in m^3/s^2 required')
    return float(gm), c


def metric(position, gm, c):
    gm, c = parameters(gm, c); x = array(position, (3,), 'position')
    radius = np.linalg.norm(x)
    if not np.isfinite(radius) or radius <= 0:
        raise ValueError('Finite nonzero isotropic radius required')
    u = gm/c**2/2/radius
    if not np.isfinite(u) or not 0 <= u < 1:
        raise ValueError('Only the exterior isotropic branch is supported')
    lapse = (1-u)/(1+u); spatial = (1+u)**4
    g = np.diag([-lapse**2, spatial, spatial, spatial])
    radial_derivative = np.array([-4*lapse*u/(radius*(1+u)**2),
                                  *([-4*u*(1+u)**3/radius]*3)])
    dg = np.zeros((4, 4, 4))
    for axis in range(3):
        dg[axis+1] = np.diag(radial_derivative*x[axis]/radius)
    finite_outputs(g, dg)
    return Metric(g, dg)


def circular_orbit(phase, rho, gm, c):
    """Return x/v/a, frequency and areal radius for a timelike circle."""
    gm, c = parameters(gm, c)
    if (type(rho) not in (float, int) or not math.isfinite(rho) or rho <= 0
            or type(phase) not in (float, int) or not math.isfinite(phase)):
        raise ValueError('Finite phase and positive finite radius required')
    u = gm/c**2/2/rho
    if not 0 <= u < 1:
        raise ValueError('Exterior isotropic circle required')
    radius = rho*(1+u)**2
    epsilon = gm/c**2/radius
    if not math.isfinite(radius) or epsilon >= 1/3:
        raise ValueError('Timelike circular orbit requires areal R > 3GM/c²')
    frequency = math.sqrt(gm/radius/radius/radius)
    if not math.isfinite(frequency) or frequency <= 0:
        raise ValueError('Representable positive circle frequency required')
    x = rho*np.array([math.cos(phase), math.sin(phase), 0.])
    v = frequency*np.array([-x[1], x[0], 0.]); a = -frequency**2*x
    finite_outputs(x, v, a)
    return x, v, a, frequency, radius
