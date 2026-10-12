"""Linear test gyro on a geodesic of an explicitly supplied metric.

SI x0=c*t, -+++; covariant SSC and positive-root gauge DJS (2008), (5)-(14).
This is NOT a lunar rotor law, ADM-centre map, or extended-body PN inertia.
All finite metric terms are used as supplied; PN accuracy is provider-specific.
"""
from dataclasses import dataclass

import numpy as np

from scripts.canonical_initial import local_spin_root
from scripts.external_metric import array, light_speed, finite_outputs


@dataclass(frozen=True)
class Metric:
    """g_mu_nu and dg[lambda,mu,nu] in coordinate units [1/m]."""
    covariant: tuple
    derivative: tuple

    def __post_init__(self):
        g = array(self.covariant, (4, 4), 'metric')
        dg = array(self.derivative, (4, 4, 4), 'metric derivative')
        if (np.linalg.norm(g-g.T) > 1e-12*np.linalg.norm(g)
                or np.linalg.norm(dg-dg.transpose(0, 2, 1)) > 1e-12*np.linalg.norm(dg)):
            raise ValueError('Symmetric metric and metric derivatives required')
        eigen = np.linalg.eigvalsh(g)
        if np.count_nonzero(eigen < 0) != 1 or np.count_nonzero(eigen > 0) != 3:
            raise ValueError('Nondegenerate Lorentzian metric required')
        inverse = np.linalg.inv(g)
        finite_outputs(inverse)
        if inverse[0, 0] >= 0:
            raise ValueError('Spacelike coordinate-time slices required')
        object.__setattr__(self, 'covariant', tuple(map(tuple, g)))
        object.__setattr__(self, 'derivative', tuple(tuple(map(tuple, a)) for a in dg))


def christoffel(metric):
    """Levi-Civita Gamma[upper,lower,lower], without order reduction."""
    if not isinstance(metric, Metric):
        raise ValueError('Explicit Metric required')
    g = np.asarray(metric.covariant); dg = np.asarray(metric.derivative)
    inverse = np.linalg.inv(g)
    result = .5*np.einsum('al,lmn->amn', inverse,
                          dg.transpose(1, 0, 2)+dg.transpose(1, 2, 0)-dg)
    finite_outputs(result)
    return result


def root_rate(inverse, inverse_rate, beta, beta_rate):
    """Differentiate H²=G using a Sylvester solve, not a finite epsilon.

    Supplied derivatives must correspond to one trajectory for transport.
    This algebraic utility alone does not enforce geodesic motion.
    """
    inverse = array(inverse, (4, 4), 'inverse metric')
    dinv = array(inverse_rate, (4, 4), 'inverse metric rate')
    beta = array(beta, (3,), 'velocity/c'); dbeta = array(beta_rate, (3,), 'acceleration/c')
    if np.linalg.norm(dinv-dinv.T) > 1e-12*np.linalg.norm(dinv):
        raise ValueError('Symmetric inverse metric derivative required')
    h, spin_metric = local_spin_root(inverse, beta)
    dspin = (dinv[1:, 1:]-np.outer(dinv[0, 1:], beta)-np.outer(beta, dinv[0, 1:])
             -np.outer(inverse[0, 1:], dbeta)-np.outer(dbeta, inverse[0, 1:])
             +dinv[0, 0]*np.outer(beta, beta)
             +inverse[0, 0]*(np.outer(dbeta, beta)+np.outer(beta, dbeta)))
    values, vectors = np.linalg.eigh(h)
    dh = vectors@((vectors.T@dspin@vectors)/(values[:, None]+values[None, :]))@vectors.T
    finite_outputs(h, spin_metric, dh, dspin)
    return h, dh, spin_metric, dspin


@dataclass(frozen=True)
class Transport:
    acceleration: np.ndarray
    proper_rate: float
    root: np.ndarray
    root_derivative: np.ndarray
    covariant_generator: np.ndarray
    generator: np.ndarray
    omega: np.ndarray
    symmetry_defect: float


def transport(metric, velocity, c):
    """Geodesic acceleration, chosen Euclidean spin generator, proper rate.

    proper_rate is exact for this FINITE metric, not a full-PN clock claim.
    Raw V is checked, never antisymmetrized; no arbitrary acceleration input.
    Neither the metric root nor its derivative is an attitude SO(3) map.
    """
    c = light_speed(c); v = array(velocity, (3,), 'coordinate velocity')
    if not isinstance(metric, Metric):
        raise ValueError('Explicit Metric required')
    g = np.asarray(metric.covariant); dg = np.asarray(metric.derivative)
    inverse = np.linalg.inv(g); beta = v/c; tangent = np.r_[1., beta]
    norm = float(tangent@g@tangent)
    if not np.isfinite(norm) or norm >= 0:
        raise ValueError('Timelike coordinate trajectory required')
    connection = christoffel(metric)
    contraction = np.einsum('amn,m,n->a', connection, tangent, tangent)
    acceleration = -c**2*(contraction[1:]-beta*contraction[0])
    dgdt = c*dg[0]+np.einsum('i,imn->mn', v, dg[1:])
    dinv = -inverse@dgdt@inverse
    h, dh, _, _ = root_rate(inverse, dinv, beta, acceleration/c)
    contracted = c*np.einsum('amn,n->am', connection, tangent)
    lower_generator = contracted[1:, 1:].T-np.outer(contracted[0, 1:], beta)
    h_inverse = np.linalg.inv(h)
    root_part = dh@h_inverse; spin_part = h@lower_generator@h_inverse
    generator = root_part+spin_part
    finite_outputs(acceleration, root_part, spin_part, generator)
    scale = np.linalg.norm(root_part)+np.linalg.norm(spin_part)
    defect = float(np.linalg.norm(generator+generator.T)/scale) if scale else 0.
    if defect > 1e-10:
        raise ValueError(f'Inconsistent metric-spin transport: raw symmetry defect {defect}')
    # No projection: these three entries are equivalent only after the raw check.
    omega = np.array([generator[2, 1], generator[0, 2], generator[1, 0]])
    return Transport(acceleration, float(np.sqrt(-norm)), h, dh,
                     lower_generator, generator, omega, defect)
