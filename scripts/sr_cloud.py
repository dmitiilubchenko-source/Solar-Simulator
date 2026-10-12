"""Exact ballistic massive-particle cloud, no binding stress or gravity.

SI, Minkowski -+++, x0=ct. Rest snapshot at local T=0 is explicit.
This is a closed free system with energy/angular momentum conservation,
not a rigid lunar body or a PN inertia model. Active rotationless boosts.
"""
from dataclasses import dataclass
import itertools

import numpy as np

from scripts.external_metric import array, light_speed, finite_outputs
from scripts.local_event_map import scalar


ETA = np.diag([-1., 1., 1., 1.])
EPSILON = np.zeros((4, 4, 4, 4))
for indices in itertools.permutations(range(4)):
    inversions = sum(indices[i] > indices[j] for i in range(4) for j in range(i+1, 4))
    EPSILON[indices] = (-1.)**inversions  # epsilon^0123=+1, as in DJS.


def boost(velocity, c):
    """Rotationless active boost: a resting origin moves with +velocity."""
    c = light_speed(c); beta = array(velocity, (3,), 'boost velocity')/c
    squared = float(beta@beta)
    if not np.isfinite(squared) or squared >= 1: raise ValueError('Subluminal boost required')
    gamma = 1/np.sqrt(1-squared)
    matrix = np.eye(4)
    matrix[0, 0] = gamma; matrix[0, 1:] = matrix[1:, 0] = gamma*beta
    # (gamma-1)/beta²=gamma²/(gamma+1), including the zero-boost limit.
    matrix[1:, 1:] += gamma**2/(gamma+1)*np.outer(beta, beta)
    finite_outputs(matrix)
    return matrix


def four_momenta(masses, velocities, c):
    """Per-particle contravariant (E/c,p), not Newtonian m*v."""
    c = light_speed(c); original = np.asarray(masses)
    if original.ndim != 1 or not len(original): raise ValueError('Nonempty mass vector required')
    m = array(original, original.shape, 'rest masses'); u = array(velocities, (len(m), 3), 'velocities')
    beta2 = np.sum((u/c)**2, axis=1)
    if np.any(m <= 0) or np.any(beta2 >= 1): raise ValueError('Positive masses and subluminal velocities required')
    weights = m/np.sqrt(1-beta2)
    result = np.c_[weights*c, weights[:, None]*u]
    finite_outputs(result)
    return result


@dataclass(frozen=True)
class RestCloud:
    masses: tuple
    positions: tuple
    velocities: tuple
    c: float

    def __post_init__(self):
        p = four_momenta(self.masses, self.velocities, self.c); count = len(p)
        x = array(self.positions, (count, 3), 'rest positions')
        momentum_scale = np.sum(np.linalg.norm(p[:, 1:], axis=1))
        dipole_scale = np.sum(p[:, 0]*np.linalg.norm(x, axis=1))
        if np.linalg.norm(np.sum(p[:, 1:], axis=0)) > 1e-12*momentum_scale:
            raise ValueError('Snapshot must already be in its zero-momentum frame')
        if np.linalg.norm(p[:, 0]@x) > 1e-12*dipole_scale:
            raise ValueError('Snapshot must already have zero energy centroid')
        object.__setattr__(self, 'masses', tuple(np.asarray(self.masses, dtype=float)))
        object.__setattr__(self, 'positions', tuple(map(tuple, x)))
        object.__setattr__(self, 'velocities', tuple(map(tuple, np.asarray(self.velocities, dtype=float))))
        object.__setattr__(self, 'c', light_speed(self.c))

    @property
    def momenta(self):
        return four_momenta(self.masses, self.velocities, self.c)


def snapshot(global_time, frame_velocity, cloud):
    """Intersect EACH ballistic worldline with the same global t surface."""
    if not isinstance(cloud, RestCloud): raise ValueError('Explicit RestCloud required')
    t = scalar(global_time, 'global time'); c = cloud.c
    v = array(frame_velocity, (3,), 'frame velocity'); matrix = boost(v, c)
    x0 = np.asarray(cloud.positions); u = np.asarray(cloud.velocities)
    denominator = 1+u@(v/c)/c
    local_times = (t/matrix[0, 0]-x0@(v/c)/c)/denominator
    x = x0+u*local_times[:, None]
    events = np.c_[c*local_times, x]@matrix.T
    momenta = cloud.momenta@matrix.T
    finite_outputs(local_times, events, momenta)
    return events, momenta, local_times


def charges(events, momenta):
    """Total contravariant P and J, and lab energy centroid for given events."""
    raw = np.asarray(events)
    if raw.ndim != 2 or raw.shape[1:] != (4,) or not len(raw):
        raise ValueError('Nonempty Nx4 event array required')
    x = array(raw, raw.shape, 'events'); p = array(momenta, raw.shape, 'momenta')
    if np.any(p[:, 0] <= 0): raise ValueError('Future positive energies required')
    total_p = np.sum(p, axis=0)
    moment = x.T@p; angular = moment-moment.T
    centroid = p[:, 0]@x[:, 1:]/total_p[0]
    finite_outputs(total_p, angular, centroid)
    return total_p, angular, centroid


def spatial_angular(tensor):
    j = array(tensor, (4, 4), 'angular momentum tensor')
    return np.array([j[2, 3], j[3, 1], j[1, 2]])


def about_centre(angular, momentum, event):
    j = array(angular, (4, 4), 'angular tensor')
    p = array(momentum, (4,), 'momentum'); z = array(event, (4,), 'centre event')
    result = j-np.outer(z, p)+np.outer(p, z)
    finite_outputs(result)
    return result


def spin_vector(momentum, angular):
    """Intrinsic axial spin, epsilon^0123=+1, positive rest spatial angular.

    S^mu=epsilon^(mu nu rho sigma) P_nu J_rho_sigma/(2 M c).
    Translation of the centre cancels from this Pauli-Lubanski construction.
    """
    p = array(momentum, (4,), 'total momentum'); j = array(angular, (4, 4), 'angular tensor')
    if np.linalg.norm(j+j.T) > 1e-12*np.linalg.norm(j): raise ValueError('Antisymmetric angular tensor required')
    mass_c_squared = -float(p@ETA@p)
    if not np.isfinite(mass_c_squared) or mass_c_squared <= 0 or p[0] <= 0:
        raise ValueError('Future timelike total momentum required')
    result = .5*np.einsum('mnrs,n,rs->m', EPSILON, ETA@p, ETA@j@ETA)/np.sqrt(mass_c_squared)
    finite_outputs(result)
    return result
