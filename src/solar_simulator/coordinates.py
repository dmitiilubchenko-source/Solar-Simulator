"""Constant linear change of solver coordinates for one selected pair.

One slot stores the pair's Newtonian mass centre, the other stores r2-r1.
These are numerical variables, not a new physical reference frame. Inertial
positions/velocities are reconstructed before evaluating every force.
"""
from dataclasses import dataclass

import numpy as np


def validate_pair_option(pair):
    if pair is not None and (type(pair) is not tuple or len(pair) != 2
            or any(type(name) is not str or not name.strip() for name in pair) or pair[0] == pair[1]):
        raise ValueError("Относительная пара должна содержать два разных имени тел")


@dataclass(frozen=True)
class PairCoordinates:
    first: int
    second: int
    first_fraction: float
    second_fraction: float

    def encode(self, values, *, offset=None):
        """Apply the same linear map to positions, velocities or accelerations."""
        values = np.asarray(values,dtype=float)
        result = values.copy() if offset is None else values-offset
        relative = values[self.second]-values[self.first]
        result[self.first] += self.second_fraction*relative
        result[self.second] = relative
        return result

    def decode(self, values):
        values = np.asarray(values,dtype=float)
        result = values.copy()
        result[self.first] = values[self.first]-self.second_fraction*values[self.second]
        result[self.second] = values[self.first]+self.first_fraction*values[self.second]
        return result


def prepare_pair(bodies, pair):
    validate_pair_option(pair)
    if pair is None:
        return None
    names = [body.name for body in bodies]
    if len(set(names)) != len(names) or any(name not in names for name in pair):
        raise ValueError("Относительная пара требует существующие тела с уникальными именами")
    first, second = map(names.index,pair)
    masses = np.array([bodies[first].mass,bodies[second].mass],dtype=float)
    weights = masses/masses.max()
    weights /= weights.sum()
    if not np.all(np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("Отношение масс пары не представимо в float64")
    return PairCoordinates(first,second,*map(float,weights))
