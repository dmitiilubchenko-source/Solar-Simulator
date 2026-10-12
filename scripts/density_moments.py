"""Newton density moments and an SR kinetic-only rotation snapshot limit.

Rest masses/positions on ONE specified local-time slice, SI. No density,
gravitational PN stresses, binding energy, or rigid inertia is inferred.
M is STF(D), matching local_multipole's -3G m n.M.n/(2r^3) convention.
"""
import numpy as np

from scripts.external_metric import array, light_speed, finite_outputs
from scripts.sr_cloud import four_momenta


def mass_positions(masses, positions):
    raw = np.asarray(masses)
    if raw.ndim != 1 or not len(raw): raise ValueError('Nonempty rest-mass vector required')
    m = array(raw, raw.shape, 'rest masses'); x = array(positions, (len(m), 3), 'positions')
    if np.any(m <= 0): raise ValueError('Positive rest masses required')
    return m, x


def mass_moments(masses, positions):
    """D, Euclidean C and STF M about the supplied origin; no recentring."""
    m, x = mass_positions(masses, positions)
    with np.errstate(over='raise', invalid='raise'):
        try:
            d = x.T@(m[:, None]*x)
            inertia = np.trace(d)*np.eye(3)-d
            multipole = d-np.trace(d)*np.eye(3)/3
        except FloatingPointError as error:
            raise ValueError('Density moments are not representable') from error
    finite_outputs(d, inertia, multipole)
    return d, inertia, multipole


def density_pair(inertia, multipole):
    """Check Newton C/M compatibility and PSD D, without adjusting tensors.

    Realizability of a second moment alone is not qualification of PN moments.
    """
    c = array(inertia, (3, 3), 'inertia'); m = array(multipole, (3, 3), 'multipole')
    scale = np.linalg.norm(c)+np.linalg.norm(m)
    if (np.linalg.norm(c-c.T) > 1e-12*scale or np.linalg.norm(m-m.T) > 1e-12*scale
            or abs(np.trace(m)) > 1e-12*scale):
        raise ValueError('Symmetric C and STF M required')
    d = .5*np.trace(c)*np.eye(3)-c
    if np.any(np.linalg.eigvalsh(d) < -1e-12*scale):
        raise ValueError('C violates positive density second-moment realizability')
    expected = -c+np.trace(c)*np.eye(3)/3
    if np.linalg.norm(m-expected) > 1e-12*scale:
        raise ValueError('C and M do not describe the same Newton density')
    finite_outputs(d)
    return d


def rotation_snapshot_spin(masses, positions, omega, c):
    """Exact kinetic angular J, Newton C.Omega, and its c^-2 correction.

    Merely initial rotational velocities of otherwise free particles.
    Does not assert Born rigidity, supply centripetal stresses, or lunar PN I.
    """
    m, x = mass_positions(masses, positions); c = light_speed(c)
    w = array(omega, (3,), 'rotation rate'); u = np.cross(w, x)
    four = four_momenta(m, u, c)
    try:
        with np.errstate(over='raise', invalid='raise'):
            exact = np.sum(np.cross(x, four[:, 1:]), axis=0)
            _, inertia, _ = mass_moments(m, x)
            newton = inertia@w
            correction = .5*np.sum(m[:, None]*np.sum((u/c)**2, axis=1)[:, None]*np.cross(x, u), axis=0)
    except FloatingPointError as error:
        raise ValueError('Rotation snapshot spin is not representable') from error
    finite_outputs(exact, newton, correction)
    return exact, newton, newton+correction
