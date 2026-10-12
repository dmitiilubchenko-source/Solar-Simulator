"""Research Jacobi pair for the unchanged finite H57, G=1.

Slots first/second store X,r and P,pr; other positions/momenta and all
spatial spins/quaternion retain their original meaning. X is a mass-weighted
coordinate, not the relativistic centre of energy. No velocity boost.
"""
from dataclasses import dataclass

import numpy as np

from scripts.rigid_pn_model import rhs as cartesian_rhs, hamiltonian as cartesian_h


@dataclass(frozen=True)
class Pair:
    masses: tuple
    first: int
    second: int

    def __post_init__(self):
        if (type(self.masses) is not tuple or len(self.masses) < 2
                or any(type(m) not in (int, float) or not np.isfinite(m) or m <= 0 for m in self.masses)
                or not np.isfinite(sum(self.masses))
                or any(type(i) is not int or not 0 <= i < len(self.masses) for i in [self.first, self.second])
                or self.first == self.second):
            raise ValueError('Distinct pair indices and finite positive masses required')
        if min(self.fractions) <= 0:
            raise ValueError('Unrepresentable mass fraction')

    @property
    def fractions(self):
        total = self.masses[self.first]+self.masses[self.second]
        return self.masses[self.first]/total, self.masses[self.second]/total


def blocks(state, pair):
    y = np.asarray(state, dtype=float)
    if y.shape != (9*len(pair.masses)+4,) or not np.all(np.isfinite(y)):
        raise ValueError('Finite Jacobi x/p/S/q layout required')
    return y, y[:-4].reshape(3, len(pair.masses), 3)


def from_cartesian(state, pair):
    """Explicit one-time linear projection; never recalculate r during evolution."""
    y, b = blocks(state, pair); out = y.copy(); z = out[:-4].reshape(b.shape)
    a, d = pair.first, pair.second; fa, fd = pair.fractions
    relative = b[0, d]-b[0, a]
    z[0, a] = b[0, a]+fd*relative; z[0, d] = relative
    z[1, a] = b[1, a]+b[1, d]
    z[1, d] = fa*b[1, d]-fd*b[1, a]
    return out


def to_cartesian(state, pair, *, anchored=False):
    """Diagnostic absolute export or force geometry anchored at first body.

    The anchor translates ONLY positions for evaluating a translationally
    invariant H. It does not replace the inertial frame or transform p/S/q.
    Absolute export can lose small r below the ulp of X.
    """
    y, b = blocks(state, pair); out = y.copy(); z = out[:-4].reshape(b.shape)
    a, d = pair.first, pair.second; fa, fd = pair.fractions
    centre, relative, total, internal = b[0, a], b[0, d], b[1, a], b[1, d]
    if anchored:
        z[0] = (b[0]-centre)+fd*relative
        z[0, a] = 0.; z[0, d] = relative
    else:
        z[0, a] = centre-fd*relative; z[0, d] = centre+fa*relative
    z[1, a] = fa*total-internal; z[1, d] = fd*total+internal
    if not np.all(np.isfinite(out)):
        raise ValueError('Unrepresentable Cartesian evaluation')
    return out


def matching(parameters, pair):
    if tuple(parameters.orbital.masses) != pair.masses:
        raise ValueError('Pair and finite-H masses differ')


def rhs(time, state, parameters, pair):
    matching(parameters, pair)
    evaluated = to_cartesian(state, pair, anchored=True)
    flow = cartesian_rhs(time, evaluated, parameters)
    b = flow[:-4].reshape(3, len(pair.masses), 3)
    a, d = pair.first, pair.second; fa, fd = pair.fractions
    va, vd, pa, pd = b[0, a].copy(), b[0, d].copy(), b[1, a].copy(), b[1, d].copy()
    b[0, a] = fa*va+fd*vd; b[0, d] = vd-va
    b[1, a] = pa+pd; b[1, d] = fa*pd-fd*pa
    return flow


def invariants(state, parameters, pair):
    matching(parameters, pair); y, b = blocks(state, pair)
    h = cartesian_h(to_cartesian(y, pair, anchored=True), parameters)
    # X cross P + r cross pr is the pair's original orbital angular momentum.
    keep = [i for i in range(len(pair.masses)) if i not in [pair.first, pair.second]]
    momentum = b[1, pair.first]+b[1, keep].sum(axis=0)
    angular = (np.cross(b[0], b[1])+b[2]).sum(axis=0)
    return h, momentum, angular
