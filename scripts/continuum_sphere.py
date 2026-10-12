"""SI constant-energy-density Schwarzschild fluid sphere / Newton limits.

M is gravitational mass, R areal radius, t asymptotic time. Infinite sound
speed benchmark only; no inferred baryon density/EOS/internal-energy split.
"""
from dataclasses import dataclass

import numpy as np

from scripts.external_metric import finite_outputs


def scalar(value, name, *, positive=False):
    raw=np.asarray(value)
    if raw.shape!=() or raw.dtype.kind not in 'fiu':raise ValueError(f'{name}: real scalar required')
    out=float(raw)
    if not np.isfinite(out) or (positive and out<=0):raise ValueError(f'{name}: finite positive scalar required')
    return out


def compactness(value):
    c=scalar(value,'compactness')
    if not 1e-12<=c<=.3:raise ValueError('Benchmark compactness 1e-12<=C<=0.3 required')
    return c


@dataclass(frozen=True)
class Sphere:
    gravitational_mass_kg: float
    areal_radius_m: float
    gravitational_constant: float
    light_speed_m_s: float

    def __post_init__(self):
        for name in ('gravitational_mass_kg','areal_radius_m','gravitational_constant','light_speed_m_s'):
            object.__setattr__(self,name,scalar(getattr(self,name),name,positive=True))
        try:
            compactness(self.compactness)
            finite_outputs(self.energy_density_mass,self.energy_density_mass*self.light_speed_m_s**2,
                           self.gravitational_mass_kg*self.areal_radius_m**2,self.gravitational_constant*self.gravitational_mass_kg/self.areal_radius_m)
        except (OverflowError,ZeroDivisionError,FloatingPointError) as error:raise ValueError('Sphere SI scales are not representable') from error
        if self.energy_density_mass<=0:raise ValueError('Positive representable energy density required')

    @property
    def compactness(self):
        return self.gravitational_constant*self.gravitational_mass_kg/self.areal_radius_m/self.light_speed_m_s**2

    @property
    def energy_density_mass(self):
        return 3*self.gravitational_mass_kg/(4*np.pi*self.areal_radius_m**3)


def radius_grid(value):
    raw=np.asarray(value)
    if raw.dtype.kind not in 'fiu':raise ValueError('Real fractional radii required')
    s=np.array(raw,dtype=float,copy=True)
    if np.any(~np.isfinite(s)) or np.any(s<0) or np.any(s>1):raise ValueError('Interior fractional radii 0<=s<=1 required')
    return s


def background(fractional_radius, c):
    """Dimensionless exact static metric, pressure and analytic derivatives."""
    s=radius_grid(fractional_radius);c=compactness(c)
    u=np.sqrt(1-2*c*s*s);a=np.sqrt(1-2*c);lapse=a+(a-u)/2
    pressure=c*(1-s*s)/((u+a)*lapse)
    logarithmic_j_rate=-2*c*s/(u*u)-c*s/(u*lapse)
    values=dict(lapse=lapse,radial_inverse_metric=u*u,mass_fraction=s**3,
        pressure_ratio=pressure,pressure_ratio_rate=-a*c*s/(u*lapse*lapse),
        nu_rate=2*c*s/(u*lapse),j=u/lapse,logarithmic_j_rate=logarithmic_j_rate)
    finite_outputs(*values.values())
    return values


def newton_profile(fractional_radius, sphere):
    """Leading Newton density/pressure/positive U/gravity at common M,R."""
    if not isinstance(sphere,Sphere):raise ValueError('Explicit gravitational-mass/areal-radius sphere required')
    s=radius_grid(fractional_radius);m=sphere.gravitational_mass_kg;r=sphere.areal_radius_m;g=sphere.gravitational_constant
    values=dict(density=sphere.energy_density_mass,potential=g*m/r*(3-s*s)/2,
        pressure=sphere.energy_density_mass*g*m/(2*r)*(1-s*s),radial_acceleration=-g*m/r**2*s,
        mass=m*s**3)
    finite_outputs(*values.values())
    return values


def newton_integrals(sphere):
    if not isinstance(sphere,Sphere):raise ValueError('Sphere required')
    m=sphere.gravitational_mass_kg;r=sphere.areal_radius_m;g=sphere.gravitational_constant
    values=dict(inertia=.4*m*r*r,gravitational_energy=-.6*g*m*m/r,pressure_volume_integral=.2*g*m*m/r)
    finite_outputs(*values.values())
    return values
