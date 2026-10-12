"""Independent pressure-source Riccati/TOV and compactness series oracles.

Only numpy; no continuum_sphere/fluid_spin imports. Dimensionless radii.
Pressure from the closed constant-energy-density solution, separate from
production lapse/metric derivative. TOV integration independently checks it.
"""
import numpy as np


def pressure(s, c):
    a=np.sqrt(1-2*c);u=np.sqrt(1-2*c*np.asarray(s)**2)
    # Rationalize u-a separately; deliberately no production lapse helper.
    return 2*c*(1-np.asarray(s)**2)/((u+a)*(3*a-u))


def stress_logj_rate(s, c, *, omit_pressure=False):
    p=0. if omit_pressure else pressure(s,c)
    return -3*c*s*(1+p)/(1-2*c*s*s)


def riccati_rhs(s, state, c, *, omit_pressure=False):
    z=state[0]
    if s==0.:
        if z!=0.:raise ValueError('Regular Riccati centre requires z=0')
        return np.zeros(1)
    rate=stress_logj_rate(s,c,omit_pressure=omit_pressure)
    return np.array([-z*(z+3)/s-rate*(z+4)])


def riccati_inertia(surface_z, c):
    return surface_z/(2*c*(3+surface_z))


def tov_rhs(s, state, c):
    p=state[0]
    return np.array([-c*s*(1+p)*(1+3*p)/(1-2*c*s*s)])


def inertia_series(c, order=1):
    """Chan et al.2015 (3.11), only specified published orders0,1,2."""
    coefficients=(2/5,12/35,212/525)
    if type(order) is not int or not 0<=order<=2:raise ValueError('Published order0,1,2 required')
    return sum(coefficients[k]*np.asarray(c)**k for k in range(order+1))


def raw_profile_series(s,c):
    """Own centre-normalized ODE expansion through C², independently derived."""
    s=np.asarray(s)
    f=1+6/5*s**2*c+(3/5*s**2+99/70*s**4)*c**2
    first=12/5*s*c+(6/5*s+198/35*s**3)*c**2
    second=12/5*c+(6/5+594/35*s**2)*c**2
    return f,first,second


def inertia_integrand(s,c,normalized_profile):
    """Dimensionless matter-current integral, equivalent to Hartle(49)."""
    s=np.asarray(s);u=np.sqrt(1-2*c*s*s);a=np.sqrt(1-2*c)
    return 4*s**4*(1+pressure(s,c))*normalized_profile/(u*(3*a-u))
