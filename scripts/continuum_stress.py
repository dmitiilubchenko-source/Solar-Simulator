"""Static Komar mass and diagnostic ordered Hartle-current contributions.

Ordered terms are algebraic bookkeeping, not invariant field-spin pieces.
Same spherical benchmark and linear-Omega limits; no new runtime physics.
"""
import numpy as np

from scripts.continuum_sphere import Sphere, background, compactness, radius_grid
from scripts.external_metric import finite_outputs


def komar_measures(fractional_radius, sphere):
    """Mass-shell stress terms dM/ds and lapse-gradient charge, in kg."""
    if not isinstance(sphere,Sphere):raise ValueError('Explicit SI sphere required')
    s=radius_grid(fractional_radius);c=sphere.compactness;bg=background(s,c)
    u=np.sqrt(bg['radial_inverse_metric']);n=bg['lapse'];p=bg['pressure_ratio']
    energy=3*sphere.gravitational_mass_kg*s*s*n/u
    pressure=3*energy*p
    values=dict(redshifted_energy_rate_kg=energy,pressure_trace_rate_kg=pressure,
        komar_mass_rate_kg=energy+pressure,
        komar_metric_charge_kg=sphere.gravitational_mass_kg*s*s*u*n*bg['nu_rate']/(2*c))
    finite_outputs(*values.values())
    return values


def spin_terms(fractional_radius, normalized_baromega, c):
    """Dimensionless I/(MR²) radial integrands and a deliberate paired omission."""
    s=radius_grid(fractional_radius);c=compactness(c)
    raw=np.asarray(normalized_baromega)
    if raw.dtype.kind not in 'fiu' or raw.shape not in ((),s.shape):
        raise ValueError('Real scalar or radius-shaped Hartle profile required')
    h=np.array(raw,dtype=float,copy=True)
    if np.any(~np.isfinite(h)) or np.any(h<=0) or np.any(h>1):
        raise ValueError('Regular normalized Hartle profile 0<h<=1 required')
    bg=background(s,c);n=bg['lapse'];p=bg['pressure_ratio']
    u=np.sqrt(bg['radial_inverse_metric']);a=np.sqrt(1-2*c);base=2*s**4
    inverse_volume_excess=2*c*s*s/(u*(1+u))
    inverse_lapse_excess=c*(3/(1+a)-s*s/(1+u))/n
    values=dict(newton=base,pressure=base*p,
        proper_volume=base*(1+p)*inverse_volume_excess,
        lapse=base*(1+p)/u*inverse_lapse_excess,
        frame_profile=base*(1+p)/(u*n)*(h-1),
        full=base*h*(1+p)/(u*n),
        paired_omission=base*(1+p)/u)
    finite_outputs(*values.values())
    return values
