"""Hartle linear-spin spherical fluid benchmark, normalized radial ODE.

Raw state f=baromega/baromega_c, fprime=df/ds, s=areal_radius/R.
No finite-Omega shape/mass/energy correction, PN chart map, or lunar profile.
"""
import numpy as np

from scripts.continuum_sphere import Sphere, background, compactness, scalar
from scripts.external_metric import array, finite_outputs


def rhs(radius_fraction, state, c):
    s=scalar(radius_fraction,'radial fraction');c=compactness(c)
    y=array(state,(2,),'f/fprime');f,derivative=y
    bg=background(s,c)
    if s==0.:
        if derivative!=0.:raise ValueError('Regular centre requires fprime=0')
        lprime=-c*(2+1/float(bg['lapse']))
        acceleration=-4*lprime*f/5
    else:
        rate=float(bg['logarithmic_j_rate'])
        acceleration=-(4/s+rate)*derivative-4*rate*f/s
    result=np.array([derivative,acceleration]);finite_outputs(result)
    return result


def boundary(state, c):
    c=compactness(c);f,derivative=array(state,(2,),'surface f/fprime')
    frequency=f+derivative/3
    if f<=0 or derivative<=0 or frequency<=0:raise ValueError('Positive regular surface spin solution required')
    a=derivative/(6*c*frequency)
    finite_outputs(a,frequency)
    return dict(inertia_factor=float(a),omega_over_central=float(frequency),
                normalized_surface=float(f/frequency),normalized_surface_derivative=float(derivative/frequency))


def charges(surface_state, sphere, omega):
    """I and linear J for distant-observer Omega; no inferred rotation energy."""
    if not isinstance(sphere,Sphere):raise ValueError('Explicit SI sphere required')
    w=scalar(omega,'distant rotation rate')
    try:
        slow_parameter=(w*sphere.areal_radius_m)**2/(sphere.gravitational_constant*sphere.gravitational_mass_kg/sphere.areal_radius_m)
    except OverflowError as error:raise ValueError('Slow-rotation parameter is not representable') from error
    if not np.isfinite(slow_parameter) or slow_parameter>1e-2:
        raise ValueError('Slow-rotation domain Omega^2 R^3/(GM)<=1e-2 required')
    out=boundary(surface_state,sphere.compactness)
    inertia=out['inertia_factor']*sphere.gravitational_mass_kg*sphere.areal_radius_m**2
    angular=inertia*w
    finite_outputs(inertia,angular)
    return dict(inertia_kg_m2=float(inertia),angular_kg_m2_s=float(angular))


def exterior(radius_fraction, inertia_factor, c):
    """baromega/Omega and its s derivative in vacuum s>=1."""
    c=compactness(c);a=scalar(inertia_factor,'inertia factor',positive=True)
    raw=np.asarray(radius_fraction)
    if raw.dtype.kind not in 'fiu':raise ValueError('Real exterior radii required')
    s=np.array(raw,dtype=float,copy=True)
    if np.any(~np.isfinite(s)) or np.any(s<1):raise ValueError('Exterior radius s>=1 required')
    values=(1-2*c*a/s**3,6*c*a/s**4);finite_outputs(*values)
    return values
