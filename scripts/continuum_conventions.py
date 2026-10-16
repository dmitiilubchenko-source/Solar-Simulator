"""Static spherical measures and linear-spin observer conventions, in SI.

Energy density does not imply a baryon density. The isotropic chart has the
asymptotically normalized Schwarzschild exterior, not an asserted ADM map.
Local J/rate responses are observer-dependent; no rotation energy inferred.
"""
import numpy as np
from scipy.special import hyp2f1

from scripts.continuum_sphere import Sphere, background, compactness, radius_grid, scalar
from scripts.external_metric import finite_outputs
from scripts.fluid_spin import boundary, charges


def isotropic_geometry(fractional_radius, c):
    """rho/R, d(rho/R)/ds and sqrt(gamma) in isotropic Cartesian coordinates."""
    s = radius_grid(fractional_radius); c = compactness(c)
    u = np.sqrt(1-2*c*s*s); a = np.sqrt(1-2*c); k = (1+a)**3/4
    x = k*s/(1+u)
    derivative = k/(u*(1+u))
    conformal_squared = (1+u)/k  # s/x, including its regular centre limit.
    values = dict(isotropic_radius_fraction=x, radius_derivative=derivative,
                  conformal_squared=conformal_squared,
                  isotropic_volume_weight=conformal_squared**3,
                  areal_volume_weight=1/u, surface_isotropic_fraction=(1+a)**2/4)
    finite_outputs(*values.values())
    return values


def areal_from_isotropic(isotropic_radius_fraction, c):
    """Regular interior inverse; only 0<=rho/R<=surface rho/R is supported."""
    c = compactness(c); a = np.sqrt(1-2*c); surface = (1+a)**2/4
    raw = np.asarray(isotropic_radius_fraction)
    if raw.dtype.kind not in 'fiu': raise ValueError('Real isotropic radii required')
    x = np.array(raw, dtype=float, copy=True)
    if np.any(~np.isfinite(x)) or np.any(x<0) or np.any(x>surface):
        raise ValueError('Interior isotropic radius required')
    k = (1+a)**3/4
    s = 2*k*x/(k*k+2*c*x*x)
    finite_outputs(s)
    return s


def proper_volume_fraction(fractional_radius, c):
    """Vproper/(4pi R^3/3); also Mproper/M for constant energy density."""
    s = radius_grid(fractional_radius); c = compactness(c)
    value = s**3*hyp2f1(.5, 1.5, 2.5, 2*c*s*s)
    finite_outputs(value)
    return value


def mass_integrands(fractional_radius, sphere, proper_baryon_density):
    """d mass/ds in kg, with an explicit externally supplied rest-density input.

    Baryon density is a static tracer here, not a thermodynamically inferred
    EOS. Return the coordinate-density weights as well as three mass measures.
    """
    if not isinstance(sphere, Sphere): raise ValueError('Explicit SI sphere required')
    s = radius_grid(fractional_radius)
    raw = np.asarray(proper_baryon_density)
    if raw.dtype.kind not in 'fiu' or raw.shape not in ((), s.shape):
        raise ValueError('Real scalar or radius-shaped proper baryon density required')
    density = np.array(raw, dtype=float, copy=True)
    if np.any(~np.isfinite(density)) or np.any(density<0):
        raise ValueError('Finite nonnegative proper baryon density required')
    geometry = isotropic_geometry(s, sphere.compactness)
    gravitational = 3*sphere.gravitational_mass_kg*s*s
    volume_rate = gravitational/sphere.energy_density_mass
    values = dict(gravitational_mass_rate_kg=gravitational,
        proper_energy_mass_rate_kg=gravitational*geometry['areal_volume_weight'],
        baryon_mass_rate_kg=volume_rate*density*geometry['areal_volume_weight'],
        areal_conserved_density_kg_m3=density*geometry['areal_volume_weight'],
        isotropic_conserved_density_kg_m3=density*geometry['isotropic_volume_weight'])
    finite_outputs(*values.values())
    return values


def observer_rates(fractional_radius, normalized_baromega, sphere, omega, *, surface_state):
    """Static/ZAMO rates and apparent J/rate responses, only linear in Omega.

    normalized_baromega is the caller's Hartle baromega/Omega profile. Its
    scientific radial solution must be verified separately. Zero Omega is
    allowed: linear response coefficients never divide by this supplied rate.
    """
    if not isinstance(sphere, Sphere): raise ValueError('Explicit SI sphere required')
    s = radius_grid(fractional_radius)
    raw = np.asarray(normalized_baromega)
    if raw.dtype.kind not in 'fiu' or raw.shape not in ((), s.shape):
        raise ValueError('Real scalar or radius-shaped Hartle profile required')
    h = np.array(raw, dtype=float, copy=True)
    if np.any(~np.isfinite(h)) or np.any(h<=0) or np.any(h>1):
        raise ValueError('Regular normalized Hartle profile 0<h<=1 required')
    w = scalar(omega, 'distant angular velocity')
    conserved = charges(surface_state, sphere, w)  # Existing slow-rotation guard.
    lapse = background(s, sphere.compactness)['lapse']
    relative_rate = w*h/lapse
    values = dict(distant_rate_s_inv=w, static_rate_s_inv=w/lapse,
        zamo_relative_rate_s_inv=relative_rate, dragging_rate_s_inv=w*(1-h),
        equatorial_zamo_speed_m_s=sphere.areal_radius_m*s*relative_rate,
        apparent_static_response_kg_m2=conserved['inertia_kg_m2']*lapse,
        apparent_zamo_response_kg_m2=conserved['inertia_kg_m2']*lapse/h,
        exterior_angular_momentum_kg_m2_s=conserved['angular_kg_m2_s'])
    finite_outputs(*values.values())
    return values


def surface_responses(surface_state, c):
    """Five normalizations of the same exterior J, not five physical inertias."""
    c = compactness(c); result = boundary(surface_state, c)
    a = result['inertia_factor']; lapse = np.sqrt(1-2*c)
    geometry = isotropic_geometry(1., c)
    values = dict(distant_gravitational_areal=a,
        distant_proper_energy_areal=a/proper_volume_fraction(1., c),
        distant_gravitational_isotropic=a/geometry['surface_isotropic_fraction']**2,
        surface_static_gravitational_areal=a*lapse,
        surface_zamo_gravitational_areal=a*lapse/result['normalized_surface'])
    finite_outputs(*values.values())
    return {key:float(value) for key,value in values.items()}
