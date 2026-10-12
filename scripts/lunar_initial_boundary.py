"""Explicit conditional lunar-profile boundary; no physical PN migration.

Caller supplies x/v in model units and declares the pinned epoch/global frame.
Their canonical-centre interpretation is an assumption, not a transformation.
Only the effective rigid Moon has spin; other bodies are ideal point masses.
"""
import numpy as np

from scripts.canonical_initial import SIUnits,from_velocities_and_rate
from scripts.rigid_pn_model import Parameters
from solar_simulator.spin_initial import lunar_solid_equivalent_initial,PROFILE_SHA256
from solar_simulator.relativity import C
from solar_simulator.simulation import G


# Roundoff consistency of the SAME input parameters, not physical uncertainty.
PARAMETER_RELATIVE_TOLERANCE = 1e-12
PURPOSE = 'conditional-research'


def require_same(actual,expected,name):
    a = np.asarray(actual,dtype=float);e = np.asarray(expected,dtype=float)
    if (a.shape!=e.shape or not np.all(np.isfinite(a)) or not np.all(np.isfinite(e))
            or np.any(e<=0) or np.any(np.abs(a-e)/e>PARAMETER_RELATIVE_TOLERANCE)):
        raise ValueError('Incompatible pinned lunar '+name)


def from_lunar_profile(positions,velocities,parameters,units,body_names,*,
                       purpose,epoch_jd_tdb,frame,velocity_scales,rate_scale,
                       tolerance=1e-13,max_iterations=12):
    """Invert a declared conditional x/v + pinned global-TDB R/Rdot boundary.

    Physical migration is unsupported even if the caller requests it explicitly.
    No clock/basis/SSC transformation, quaternion projection or extra SO is made.
    SI similarity only converts the supplied profile W to model inverse time.
    """
    if type(purpose) is not str or purpose!=PURPOSE:
        raise ValueError('Only explicit conditional-research is supported; physical lunar mapping is not certified')
    if not isinstance(parameters,Parameters) or not isinstance(units,SIUnits):
        raise ValueError('Finite-H parameters and explicit SIUnits required')
    count = len(parameters.orbital.masses)
    if (type(body_names) is not tuple or len(body_names)!=count
            or any(type(n) is not str or not n.strip() for n in body_names)
            or len(set(body_names))!=count or body_names[parameters.index]!='Moon'):
        raise ValueError('Unique ordered body names with the Moon figure required')
    figure,_,pair,profile = lunar_solid_equivalent_initial()
    if (type(epoch_jd_tdb) not in (int,float) or epoch_jd_tdb!=profile['epoch_jd_tdb']
            or type(frame) is not str or frame!=profile['frame']):
        raise ValueError('Pinned global TDB epoch/frame required')
    if units.gravitational_constant!=G:
        raise ValueError('Pinned SI gravitational constant required')
    require_same(parameters.figure.mass*units.mass_kg,figure.mass,'mass/GM')
    require_same(np.array(parameters.figure.moments)*units.inertia_kg_m2,figure.moments,'inertia')
    require_same(parameters.figure.bounding_radius*units.length_m,figure.bounding_radius,'bounding radius')
    require_same(parameters.orbital.c*units.velocity_m_s,C,'speed of light')
    # Loader checks R/Rdot. Use its derivative without an I->S->I round-trip.
    rotation = np.array(profile['rotation'])
    h = np.array(profile['rotation_derivative_per_second'])@rotation.T
    h = .5*(h-h.T);w_si = np.array([h[2,1],h[0,2],h[1,0]])
    state,info = from_velocities_and_rate(positions,velocities,pair[6:10],w_si*units.time_s,
        np.zeros((count,3)),parameters,velocity_scales=velocity_scales,rate_scale=rate_scale,
        tolerance=tolerance,max_iterations=max_iterations)
    info.update(boundary_contract=dict(purpose=PURPOSE,source_profile_sha256=PROFILE_SHA256,
        epoch_jd_tdb=profile['epoch_jd_tdb'],frame=profile['frame'],GM_compatibility='TDB',
        attitude_rate='global derivative per TDB second',coordinate_centres='assumed canonical boundary',
        spin_basis='assumed Euclidean canonical boundary',inertia='effective constant rigid-solid-equivalent',
        inertia_radius_time_compatibility='unqualified',clock_basis_SSC_transform='not applied',
        other_bodies='ideal zero-spin point masses',physical_mapping_certified=False))
    return state,info
